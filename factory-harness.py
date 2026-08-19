import ast
import re
import json
import os
import sys
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Tuple, Optional, Any

# =====================================================================
# 1. ENUMS AND DATA SCHEMAS (CONTRACTS)
# =====================================================================

class FSMState(Enum):
    INGEST = "INGEST"
    SPEC_SYNTH = "SPEC_SYNTH"
    LOCALIZE = "LOCALIZE"
    PLAN = "PLAN"
    EDIT = "EDIT"
    TEST = "TEST"
    DEBUG = "DEBUG"
    SECURITY = "SECURITY"
    VERIFY = "VERIFY"
    PR_OPEN = "PR_OPEN"
    HUMAN_GATE = "HUMAN_GATE"
    TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
    TERMINAL_FAILED = "TERMINAL_FAILED"

class AutonomyTier(Enum):
    LOW = "LOW_AUTONOMOUS_MERGE"
    MEDIUM = "MEDIUM_HUMAN_CONSENT"
    HIGH = "HIGH_MANDATORY_REVIEW"

@dataclass
class IssuePrimitive:
    issue_id: str
    repository_path: str
    description: str
    base_commit: str

@dataclass
class SpecificationContract:
    target_symbols: List[str]
    preconditions: List[str]
    postconditions: List[str]
    property_invariants: List[Dict[str, Any]]
    complexity_cap: int = 15

@dataclass
class EditTransaction:
    file_path: str
    target_node_name: str
    edit_type: str  # "modify_body", "insert_import", "add_function"
    new_source: str

@dataclass
class ExecutionPlan:
    transactions: List[EditTransaction] = field(default_factory=list)

@dataclass
class ValidationReport:
    compiled: bool
    type_checked: bool
    linter_passed: bool
    tests_passed: bool
    stdout: str
    traceback: Optional[str] = None

@dataclass
class RiskProfile:
    score: float
    tier: AutonomyTier
    breakdown: Dict[str, float]

# =====================================================================
# 2. THE AST-TRANSACTIONAL EDITOR (MIDDLE LOOP GUARD)
# =====================================================================

class ASTTransactionalEditor(ast.NodeTransformer):
    """
    Acts as a secure, transactional AST modification engine.
    Applies precise node-level mutations to Python source code,
    verifying syntactic correctness and allowing atomic rollbacks.
    """
    def __init__(self, target_name: str, new_source: str, edit_type: str):
        self.target_name = target_name
        self.new_source = new_source
        self.edit_type = edit_type
        self.modified = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        if node.name == self.target_name and self.edit_type == "modify_body":
            try:
                # Parse the new source and extract its body nodes
                parsed_new = ast.parse(self.new_source)
                if parsed_new.body and isinstance(parsed_new.body[0], ast.FunctionDef):
                    node.body = parsed_new.body[0].body
                else:
                    node.body = parsed_new.body
                self.modified = True
            except SyntaxError as e:
                raise ValueError(f"Failed to parse target AST body modification: {e}")
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        if node.name == self.target_name and self.edit_type == "add_function":
            try:
                parsed_func = ast.parse(self.new_source)
                for element in parsed_func.body:
                    if isinstance(element, ast.FunctionDef):
                        node.body.append(element)
                        self.modified = True
            except SyntaxError as e:
                raise ValueError(f"Failed to parse new method AST: {e}")
        return self.generic_visit(node)

    @staticmethod
    def apply_transaction(file_path: str, transaction: EditTransaction) -> bool:
        """
        Executes an atomic transaction. Reads the file, parses the AST,
        applies structural mutations, validates compilation, and rolls back
        the changes if any compile or syntax boundaries are violated.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found for transaction: {file_path}")

        with open(file_path, "r") as f:
            original_code = f.read()

        try:
            tree = ast.parse(original_code)
            
            # Special case for raw module-level import insertion
            if transaction.edit_type == "insert_import":
                import_node = ast.parse(transaction.new_source).body[0]
                if isinstance(import_node, (ast.Import, ast.ImportFrom)):
                    tree.body.insert(0, import_node)
                else:
                    raise ValueError("Target source is not a valid Import node.")
            else:
                transformer = ASTTransactionalEditor(
                    target_name=transaction.target_node_name,
                    new_source=transaction.new_source,
                    edit_type=transaction.edit_type
                )
                tree = transformer.visit(tree)
                ast.fix_missing_locations(tree)
                if not transformer.modified and transaction.edit_type != "insert_import":
                    raise ValueError(f"Target node '{transaction.target_node_name}' was not located in AST.")

            # Compile the newly generated tree to verify syntactic validity
            compiled_code = compile(tree, filename=file_path, mode="exec")
            
            # Python 3.9+ native unparsing (standard in Python 3.12)
            new_code = ast.unparse(tree)

            with open(file_path, "w") as f:
                f.write(new_code)
            
            print(f"[AST-TX SUCCESS] Successfully applied AST transformation to {file_path}")
            return True

        except Exception as e:
            print(f"[AST-TX ROLLBACK] Aborting AST transformation on {file_path}. Error: {e}")
            # Rollback: write original source back to disk
            with open(file_path, "w") as f:
                f.write(original_code)
            # Re-raise the exception to be captured by FSM State Context
            raise e

# =====================================================================
# 3. TRACEBACK REGEX PARSER (MIDDLE LOOP DIAGNOSTICS)
# =====================================================================

class TracebackParser:
    """
    Parses compiler and unit test output streams, extracting exact failing 
    line numbers, source files, and exception types to target edits precisely.
    """
    PYTEST_FAIL_PATTERN = re.compile(r"FILE:\s*(?P<file>[^\s:]+):(?P<line>\d+):\s*(?P<error>.*)")
    PYTHON_STD_TB_PATTERN = re.compile(r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<func>\w+)')

    @classmethod
    def extract_failure_context(cls, stdout: Optional[str]) -> Optional[Dict[str, Any]]:
        if not stdout:
            return None
        lines = stdout.splitlines()
        for i, line in enumerate(reversed(lines)):
            # Match standard Python tracebacks
            match = cls.PYTHON_STD_TB_PATTERN.search(line)
            if match:
                err_msg = lines[i+1] if (i+1) < len(lines) else "Unknown Exception"
                return {
                    "file_path": match.group("file"),
                    "line_number": int(match.group("line")),
                    "function_name": match.group("func"),
                    "exception_msg": err_msg.strip()
                }
        return None

# =====================================================================
# 4. RISK-AWARE AUTONOMY SCORING ENGINE
# =====================================================================

class RiskScoringEngine:
    """
    Computes the composite Risk Score (R) of a proposed patch:
    R = w_s * S + w_d * D + w_c * C + w_a * A + w_u * U + w_sec * V
    """
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "size": 0.2,       # w_s (LOC delta)
            "dependency": 0.15, # w_d (new package imports)
            "coverage": 0.25,   # w_c (uncovered code paths)
            "arch": 0.2,       # w_a (public API changes)
            "entropy": 0.1,    # w_u (model entropy / edit iterations)
            "security": 0.1    # w_sec (Semgrep vulnerability flags)
        }

    def compute_risk(self, 
                     lines_changed: int, 
                     dependencies_added: int, 
                     uncovered_lines_ratio: float, 
                     is_public_api: bool, 
                     iterations: int, 
                     security_findings: int) -> RiskProfile:
        
        # Normalize variables between 0 and 100
        s_score = min(lines_changed * 2.0, 100.0) # 50+ lines is max weight
        d_score = min(dependencies_added * 25.0, 100.0) # 4+ dependencies is max weight
        c_score = uncovered_lines_ratio * 100.0
        a_score = 100.0 if is_public_api else 10.0
        u_score = min(iterations * 33.3, 100.0) # 3 retries is max entropy
        v_score = min(security_findings * 50.0, 100.0) # 2+ CVE flags is max security risk

        raw_score = (
            self.weights["size"] * s_score +
            self.weights["dependency"] * d_score +
            self.weights["coverage"] * c_score +
            self.weights["arch"] * a_score +
            self.weights["entropy"] * u_score +
            self.weights["security"] * v_score
        )

        composite_score = round(raw_score, 2)

        if composite_score < 30.0:
            tier = AutonomyTier.LOW
        elif composite_score <= 70.0:
            tier = AutonomyTier.MEDIUM
        else:
            tier = AutonomyTier.HIGH

        breakdown = {
            "code_size_impact": s_score,
            "dependency_impact": d_score,
            "coverage_degradation": c_score,
            "architectural_impact": a_score,
            "optimization_entropy": u_score,
            "security_vulnerabilities": v_score
        }

        return RiskProfile(score=composite_score, tier=tier, breakdown=breakdown)

# =====================================================================
# 5. THE DETERMINISTIC ORCHESTRATOR FSM
# =====================================================================

class OrchestratorFSM:
    """
    Deterministic state machine coordinating the Inner, Middle, and Outer Loops.
    Enforces token and monetary limits, tracks retries (N <= 3), and handles 
    asymmetric rollbacks upon validation failures.
    """
    def __init__(self, issue: IssuePrimitive, budget_cap: float = 3.00):
        self.issue = issue
        self.budget_cap = budget_cap
        self.current_state = FSMState.INGEST
        self.retry_count = 0
        self.max_retries = 3
        self.cumulative_cost = 0.0
        
        # State Context Variables
        self.specification: Optional[SpecificationContract] = None
        self.context_map: Optional[List[str]] = None
        self.execution_plan: Optional[ExecutionPlan] = None
        self.last_report: Optional[ValidationReport] = None
        self.risk_profile: Optional[RiskProfile] = None

    def execute_next_state(self):
        """
        Transition function mapping State -> Action -> Next State.
        """
        if self.cumulative_cost >= self.budget_cap:
            print(f"[FSM STATE TERMINATION] Budget Exceeded: Spent ${self.cumulative_cost:.2f} of ${self.budget_cap:.2f}")
            self.current_state = FSMState.TERMINAL_FAILED
            return

        print(f"[FSM TRANSITION] Entering State: {self.current_state.value}")

        if self.current_state == FSMState.INGEST:
            self._handle_ingest()
        elif self.current_state == FSMState.SPEC_SYNTH:
            self._handle_spec_synth()
        elif self.current_state == FSMState.LOCALIZE:
            self._handle_localize()
        elif self.current_state == FSMState.PLAN:
            self._handle_plan()
        elif self.current_state == FSMState.EDIT:
            self._handle_edit()
        elif self.current_state == FSMState.TEST:
            self._handle_test()
        elif self.current_state == FSMState.DEBUG:
            self._handle_debug()
        elif self.current_state == FSMState.SECURITY:
            self._handle_security()
        elif self.current_state == FSMState.VERIFY:
            self._handle_verify()
        elif self.current_state == FSMState.PR_OPEN:
            self._handle_pr_open()
        elif self.current_state == FSMState.HUMAN_GATE:
            self._handle_human_gate()

    def _handle_ingest(self):
        # Programmatically parse issue files
        print(f"Ingested Issue {self.issue.issue_id}. Serializing base environment...")
        self.cumulative_cost += 0.02 # Track API / compute overhead
        self.current_state = FSMState.SPEC_SYNTH

    def _handle_spec_synth(self):
        print("Invoking Outer Loop: Synthesizing Specification Invariants...")
        # Simulating model API call to construct spec contract
        self.specification = SpecificationContract(
            target_symbols=["resolve_bounds"],
            preconditions=["isinstance(x, int)"],
            postconditions=["result >= 0"],
            property_invariants=[{"invariant": "monotonically_increasing"}]
        )
        self.cumulative_cost += 0.15
        self.current_state = FSMState.LOCALIZE

    def _handle_localize(self):
        print("Building PEEK Context Map & AST Symbol Indexes...")
        # Simulate static Tree-sitter file skeleton extraction
        self.context_map = [os.path.join(self.issue.repository_path, "utils.py")]
        self.cumulative_cost += 0.05
        self.current_state = FSMState.PLAN

    def _handle_plan(self):
        print("Synthesizing Hierarchical AST-Transactional Execution Plan...")
        # Create a transaction to rewrite target method behavior
        self.execution_plan = ExecutionPlan(transactions=[
            EditTransaction(
                file_path=self.context_map[0],
                target_node_name="resolve_bounds",
                edit_type="modify_body",
                new_source="""def resolve_bounds(x):\n    if x < 0:\n        return 0\n    return x"""
            )
        ])
        self.cumulative_cost += 0.20
        self.current_state = FSMState.EDIT

    def _handle_edit(self):
        print("Executing Inner Loop: Compiling AST Transactions inside Sandbox...")
        all_applied = True
        last_error_msg = ""
        
        for tx in self.execution_plan.transactions:
            try:
                success = ASTTransactionalEditor.apply_transaction(tx.file_path, tx)
                if not success:
                    all_applied = False
            except Exception as e:
                all_applied = False
                last_error_msg = f"AST Compilation Exception: {str(e)}"
                break
        
        self.cumulative_cost += 0.10
        if all_applied:
            self.current_state = FSMState.TEST
        else:
            # Package compile failure details into ValidationReport for Debug state
            self.last_report = ValidationReport(
                compiled=False,
                type_checked=False,
                linter_passed=False,
                tests_passed=False,
                stdout="",
                traceback=f'  File "{self.context_map[0]}", line 3, in resolve_bounds\n    SyntaxError: {last_error_msg}'
            )
            print("[COMPILATION CRASH] AST transaction rejected by static compiler gate. Moving to Debugging State.")
            self.current_state = FSMState.DEBUG

    def _handle_test(self):
        print("Executing Air-gapped Sandbox Test Runner...")
        # Mocking Pytest / Mypy Gating outcomes
        # Stand-in traceback for demonstration
        mock_stdout = """
  File "utils.py", line 4, in resolve_bounds
    AttributeError: 'NoneType' object has no attribute 'val'
        """
        # In this mock run, let's assume compiling works but type checks fail on the first run
        if self.retry_count == 0:
            self.last_report = ValidationReport(
                compiled=True,
                type_checked=False,
                linter_passed=True,
                tests_passed=False,
                stdout=mock_stdout,
                traceback=mock_stdout
            )
            print("[TEST FAILURE] Local unit testing suite reported errors. Passing to diagnostics.")
            self.current_state = FSMState.DEBUG
        else:
            self.last_report = ValidationReport(
                compiled=True,
                type_checked=True,
                linter_passed=True,
                tests_passed=True,
                stdout="All 14 tests passed successfully."
            )
            print("[TEST SUCCESS] Code complies and all test invariants passed.")
            self.current_state = FSMState.SECURITY

    def _handle_debug(self):
        self.retry_count += 1
        if self.retry_count > self.max_retries:
            print(f"[FSM STATE TERMINATION] Tactical Retry Budget Depleted (N={self.max_retries}). Resetting codebase...")
            # Git rollback
            self.current_state = FSMState.TERMINAL_FAILED
            return

        print(f"[DEBUG TURN {self.retry_count}] Analyzing traceback and patching AST plan...")
        failure = TracebackParser.extract_failure_context(self.last_report.traceback if self.last_report else None)
        if failure:
            print(f"Isolated bug location -> File: {failure['file_path']}, Line: {failure['line_number']}")
        
        # Simulate model updating the plan context with corrected type bounds
        self.execution_plan = ExecutionPlan(transactions=[
            EditTransaction(
                file_path=self.context_map[0],
                target_node_name="resolve_bounds",
                edit_type="modify_body",
                new_source="""def resolve_bounds(x):\n    if x is None:\n        return 0\n    if x < 0:\n        return 0\n    return x"""
            )
        ])
        self.cumulative_cost += 0.35
        self.current_state = FSMState.EDIT

    def _handle_security(self):
        print("Invoking Non-Agentic Middle Loop Security Gates (Semgrep/Bandit)...")
        # Ensure zero credentials/injection threats are present
        self.cumulative_cost += 0.05
        self.current_state = FSMState.VERIFY

    def _handle_verify(self):
        print("Evaluating Outer Loop Spec-Verification contracts...")
        # Calculate Risk Profile
        scoring_engine = RiskScoringEngine()
        self.risk_profile = scoring_engine.compute_risk(
            lines_changed=12,
            dependencies_added=0,
            uncovered_lines_ratio=0.0,
            is_public_api=False,
            iterations=self.retry_count,
            security_findings=0
        )

        print(f"[RISK RATING] Composite Risk Score: {self.risk_profile.score} -> Autonomy Tier: {self.risk_profile.tier.value}")
        self.cumulative_cost += 0.10

        if self.risk_profile.tier == AutonomyTier.LOW:
            self.current_state = FSMState.PR_OPEN
        else:
            self.current_state = FSMState.HUMAN_GATE

    def _handle_pr_open(self):
        print("Compiling Git Patch Delta and publishing Remote Pull Request...")
        self.cumulative_cost += 0.05
        self.current_state = FSMState.TERMINAL_SUCCESS

    def _handle_human_gate(self):
        print("[AWAITING HUMAN CO-SIGN] Pausing FSM. Outputting AST-diff payloads to Canvas...")
        self.current_state = FSMState.TERMINAL_SUCCESS

# =====================================================================
# 6. LOCAL CODEBASE PLAYGROUND SETUP & VALIDATION
# =====================================================================

if __name__ == "__main__":
    print("=== INITIALIZING AI SOFTWARE FACTORY PROTO-ENV ===")
    
    # 1. Spawn a dummy codebase workspace
    repo_path = "/workspace/scratch/mock_repo"
    os.makedirs(repo_path, exist_ok=True)
    file_path = os.path.join(repo_path, "utils.py")
    
    initial_module_code = """
import os

def resolve_bounds(x):
    # Old broken skeleton
    return x.val
"""
    with open(file_path, "w") as f:
        f.write(initial_module_code)
        
    # 2. Fire up the state machine
    mock_issue = IssuePrimitive(
        issue_id="ISSUE-401",
        repository_path=repo_path,
        description="Fix AttributeError when None is passed to resolve_bounds.",
        base_commit="e3b0c44"
    )
    
    orchestrator = OrchestratorFSM(mock_issue)
    
    # Run the state machine until it hits terminal status
    while orchestrator.current_state not in [FSMState.TERMINAL_SUCCESS, FSMState.TERMINAL_FAILED]:
        orchestrator.execute_next_state()

    print("\n=== EXECUTION TRAJECTORY OVERVIEW ===")
    print(f"Final State: {orchestrator.current_state.value}")
    print(f"Total Model/Compiler Turns: {orchestrator.retry_count}")
    print(f"Total Trajectory Cost: ${orchestrator.cumulative_cost:.2f}")
    if orchestrator.risk_profile:
        print(f"Risk Rating: {orchestrator.risk_profile.score}/100 ({orchestrator.risk_profile.tier.value})")
    
    # Inspect final file code
    with open(file_path, "r") as f:
        print("\nFinal Patched Code on Disk:")
        print(f.read())
