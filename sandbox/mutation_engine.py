import ast
import os
import shutil
import tempfile
import subprocess
from typing import List, Dict, Any, Tuple

class OperatorMutator(ast.NodeTransformer):
    """
    Mutates conditional operators in Python AST:
    == <-> !=
    <  <-> >=
    >  <-> <=
    in <-> not in
    Is <-> IsNot
    """
    def __init__(self, mutation_target_idx: int):
        self.mutation_target_idx = mutation_target_idx
        self.current_idx = 0
        self.applied = False
        self.mutation_description = ""

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        new_ops = []
        for op in node.ops:
            if self.current_idx == self.mutation_target_idx:
                new_op, desc = self._mutate_op(op)
                new_ops.append(new_op)
                self.applied = True
                self.mutation_description = desc
            else:
                new_ops.append(op)
            self.current_idx += 1
        node.ops = new_ops
        return self.generic_visit(node)

    def _mutate_op(self, op: ast.cmpop) -> Tuple[ast.cmpop, str]:
        if isinstance(op, ast.Eq):
            return ast.NotEq(), "Eq (==) -> NotEq (!=)"
        elif isinstance(op, ast.NotEq):
            return ast.Eq(), "NotEq (!=) -> Eq (==)"
        elif isinstance(op, ast.Lt):
            return ast.GtE(), "Lt (<) -> GtE (>=)"
        elif isinstance(op, ast.GtE):
            return ast.Lt(), "GtE (>=) -> Lt (<)"
        elif isinstance(op, ast.Gt):
            return ast.LtE(), "GtE (>) -> LtE (<=)"
        elif isinstance(op, ast.LtE):
            return ast.Gt(), "LtE (<=) -> Gt (>)"
        elif isinstance(op, ast.In):
            return ast.NotIn(), "In -> NotIn"
        elif isinstance(op, ast.NotIn):
            return ast.In(), "NotIn -> In"
        elif isinstance(op, ast.Is):
            return ast.IsNot(), "Is -> IsNot"
        elif isinstance(op, ast.IsNot):
            return ast.Is(), "IsNot -> Is"
        return op, "Identity"


class MutationTestingEngine:
    """
    Applies fault injections to the patched code to determine if the test suite
    fails on erroneous variants (killing the mutant) or passes (mutant survives = weak tests).
    """
    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)

    def count_mutation_points(self, file_path: str) -> int:
        full_path = os.path.join(self.repo_root, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.exists(full_path):
            return 0
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            count = 0
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    count += len(node.ops)
            return count
        except Exception:
            return 0

    def run_mutation_analysis(
        self, 
        target_file: str, 
        test_command: List[str], 
        max_mutants: int = 5
    ) -> Dict[str, Any]:
        """
        Generates up to max_mutants, runs the test command against each mutant,
        and computes the Mutation Score and Mutation Survival Ratio.
        """
        full_path = os.path.join(self.repo_root, target_file) if not os.path.isabs(target_file) else target_file
        if not os.path.exists(full_path):
            return {
                "total_mutants": 0,
                "killed_mutants": 0,
                "survived_mutants": 0,
                "mutation_score": 1.0,
                "survival_ratio": 0.0,
                "details": []
            }

        with open(full_path, "r", encoding="utf-8") as f:
            original_code = f.read()

        total_points = self.count_mutation_points(target_file)
        if total_points == 0:
            return {
                "total_mutants": 0,
                "killed_mutants": 0,
                "survived_mutants": 0,
                "mutation_score": 1.0,
                "survival_ratio": 0.0,
                "details": []
            }

        num_to_test = min(total_points, max_mutants)
        killed = 0
        survived = 0
        details = []

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{self.repo_root}:{env.get('PYTHONPATH', '')}"

        for idx in range(num_to_test):
            try:
                tree = ast.parse(original_code)
                mutator = OperatorMutator(idx)
                mutated_tree = mutator.visit(tree)
                ast.fix_missing_locations(mutated_tree)

                if not mutator.applied:
                    continue

                mutated_code = ast.unparse(mutated_tree)

                # Write mutant to file
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(mutated_code)

                # Run tests against mutant
                res = subprocess.run(
                    test_command, 
                    cwd=self.repo_root, 
                    env=env,
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )

                if res.returncode != 0:
                    # Test failed -> Mutant killed! (Good)
                    killed += 1
                    status = "KILLED"
                else:
                    # Test passed -> Mutant survived! (Weak test)
                    survived += 1
                    status = "SURVIVED"

                details.append({
                    "mutant_index": idx,
                    "description": mutator.mutation_description,
                    "status": status
                })

            except Exception as e:
                # If mutation couldn't compile or threw exception, consider killed
                killed += 1
                details.append({
                    "mutant_index": idx,
                    "description": f"Crash/Uncompilable: {e}",
                    "status": "KILLED"
                })
            finally:
                # Restore original code
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(original_code)

        total = killed + survived
        score = round(killed / total, 4) if total > 0 else 1.0
        survival_ratio = round(survived / total, 4) if total > 0 else 0.0

        return {
            "total_mutants": total,
            "killed_mutants": killed,
            "survived_mutants": survived,
            "mutation_score": score,
            "survival_ratio": survival_ratio,
            "details": details
        }
