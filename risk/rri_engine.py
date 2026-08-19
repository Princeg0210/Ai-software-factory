import ast
from typing import Dict, Any, Optional

class RegressionRiskIndexEngine:
    """
    Computes the Regression Risk Index (RRI):
    RRI = (w_1 * Lines_Changed_Normalized) + (w_2 * AST_Interface_Breaks) + (w_3 * Mutation_Survival_Ratio)
    
    Thresholds:
    - RRI < 0.30: LOW RISK -> Autonomous Merge
    - RRI >= 0.30: HIGH RISK -> Human Review Gate Required
    """
    def __init__(
        self, 
        w_lines: float = 0.30, 
        w_ast: float = 0.40, 
        w_mutation: float = 0.30
    ):
        self.w_lines = w_lines
        self.w_ast = w_ast
        self.w_mutation = w_mutation

    def count_diff_lines(self, patch_diff: str) -> int:
        lines = patch_diff.splitlines()
        changed = 0
        for line in lines:
            if (line.startswith("+") and not line.startswith("+++")) or \
               (line.startswith("-") and not line.startswith("---")):
                changed += 1
        return changed

    def check_ast_interface_breaks(self, original_code: str, patched_code: str) -> float:
        """
        Calculates interface disruption: checks if public method signatures,
        class names, or argument lists have changed or been removed.
        Returns 0.0 (no breaks) to 1.0 (major interface break).
        """
        try:
            tree_orig = ast.parse(original_code)
            tree_patch = ast.parse(patched_code)

            orig_funcs = {
                n.name: [a.arg for a in n.args.args]
                for n in ast.walk(tree_orig)
                if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
            }

            patch_funcs = {
                n.name: [a.arg for a in n.args.args]
                for n in ast.walk(tree_patch)
                if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
            }

            # If no public functions in original, no break
            if not orig_funcs:
                return 0.0

            breaks = 0
            for name, args in orig_funcs.items():
                if name not in patch_funcs:
                    # Public function deleted!
                    breaks += 1
                elif args != patch_funcs[name]:
                    # Arguments changed!
                    breaks += 1

            return min(round(breaks / len(orig_funcs), 4), 1.0)
        except Exception:
            return 0.5  # Neutral default if AST parsing is ambiguous

    def compute_rri(
        self, 
        patch_diff: str, 
        original_code: str = "", 
        patched_code: str = "", 
        mutation_survival_ratio: float = 0.0
    ) -> Dict[str, Any]:
        lines_changed = self.count_diff_lines(patch_diff)
        
        # Max cap of 50 lines changes gives normalized score of 1.0
        lines_norm = min(lines_changed / 50.0, 1.0)

        ast_break_score = 0.0
        if original_code and patched_code:
            ast_break_score = self.check_ast_interface_breaks(original_code, patched_code)

        rri = (
            (self.w_lines * lines_norm) +
            (self.w_ast * ast_break_score) +
            (self.w_mutation * mutation_survival_ratio)
        )
        rri = round(min(max(rri, 0.0), 1.0), 4)

        is_low_risk = rri < 0.30

        return {
            "rri_score": rri,
            "is_low_risk": is_low_risk,
            "action": "AUTO_MERGE" if is_low_risk else "HUMAN_REVIEW",
            "breakdown": {
                "lines_changed": lines_changed,
                "lines_score": round(lines_norm, 4),
                "ast_interface_breaks": round(ast_break_score, 4),
                "mutation_survival_ratio": round(mutation_survival_ratio, 4)
            }
        }
