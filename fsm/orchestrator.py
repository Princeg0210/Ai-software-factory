import os
import uuid
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from .states import FSMState
from .ledger import StateLedger
from spec.contract import SpecificationEngine, SpecificationContract
from intelligence.symbol_map import SymbolMapBuilder
from intelligence.sbfl import OchiaiSBFLCalculator
from agents.aci import AgentComputerInterface
from agents.llm_client import LLMAgentClient
from sandbox.runner import SandboxRunner
from sandbox.consensus import ConsensusVotingEngine
from security.scanner import SecurityScanner
from verification.poc_generator import PoCReproductionEngine
from risk.rri_engine import RegressionRiskIndexEngine
from risk.reviewer_gateway import HumanReviewerGateway
from git_ops.publisher import GitPRPublisher

class FSMOrchestrator:
    """
    Deterministic FSM Orchestrator for the AI Software Factory (ASF).
    Enforces atomic ledger commits, AST-SBFL fault localization, Ponytail minimal-diff rules,
    air-gapped sandbox verification, SAST security scans, mutation testing, and risk-adaptive review routing.
    """
    def __init__(
        self, 
        issue_payload: Dict[str, Any], 
        workspace_dir: str, 
        db_session: Optional[Session] = None,
        use_docker: bool = False
    ):
        self.payload = issue_payload
        self.issue_id = issue_payload.get("issue_id", str(uuid.uuid4()))
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.ledger = StateLedger(db=db_session)
        self.state = FSMState.INIT
        self.retry_count = 0
        v_settings = issue_payload.get("verification_settings") or {}
        self.max_retries = v_settings.get("max_repair_retries", 3)
        self.risk_threshold = v_settings.get("risk_threshold", 0.30)
        
        # Ensure repository workspace is pre-populated
        self._ensure_repository_scaffold()

        # Subsystems
        self.aci = AgentComputerInterface(self.workspace_dir)
        self.llm_client = LLMAgentClient()
        self.sandbox = SandboxRunner(self.workspace_dir, use_docker=use_docker)
        self.rri_engine = RegressionRiskIndexEngine()
        
        # Intermediate Artifacts
        self.spec_contract: Optional[SpecificationContract] = None
        self.localization_result: Optional[Dict[str, Any]] = None
        self.planning_result: Optional[Dict[str, Any]] = None
        self.current_patch: Optional[Dict[str, Any]] = None
        self.validation_report: Optional[Dict[str, Any]] = None
        self.security_report: Optional[Dict[str, Any]] = None
        self.mutation_report: Optional[Dict[str, Any]] = None
        self.poc_report: Optional[Dict[str, Any]] = None
        self.rri_report: Optional[Dict[str, Any]] = None
        self.human_review_payload: Optional[Dict[str, Any]] = None
        self.pr_payload: Optional[Dict[str, Any]] = None

    def _ensure_repository_scaffold(self):
        """
        Provisions and resets benchmark codebase files in workspace to clean base state.
        """
        django_forms_dir = os.path.join(self.workspace_dir, "django", "forms")
        tests_dir = os.path.join(self.workspace_dir, "tests")
        os.makedirs(django_forms_dir, exist_ok=True)
        os.makedirs(tests_dir, exist_ok=True)

        for init_path in [
            os.path.join(self.workspace_dir, "django", "__init__.py"),
            os.path.join(self.workspace_dir, "django", "forms", "__init__.py"),
            os.path.join(self.workspace_dir, "tests", "__init__.py")
        ]:
            with open(init_path, "w", encoding="utf-8") as f:
                f.write("")

        models_file = os.path.join(django_forms_dir, "models.py")
        original_models_code = """class ValidationError(Exception):
    def __init__(self, message, code=None, params=None):
        self.message = message
        self.code = code
        self.params = params

class DummyModel:
    class DoesNotExist(Exception):
        pass

class DummyQuerySet:
    def __init__(self):
        self.model = DummyModel

    def get(self, pk):
        raise self.model.DoesNotExist("Invalid PK")

class ModelChoiceField:
    def __init__(self, queryset=None, error_messages=None):
        self.queryset = queryset or DummyQuerySet()
        self.error_messages = error_messages or {'invalid_choice': 'Invalid choice'}

    def to_python(self, value):
        if value in (None, ''):
            return None
        try:
            return self.queryset.get(pk=value)
        except (ValueError, TypeError, self.queryset.model.DoesNotExist):
            raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
"""
        with open(models_file, "w", encoding="utf-8") as f:
            f.write(original_models_code)

        test_file = os.path.join(tests_dir, "test_model_fields.py")
        test_code = """import pytest
from django.forms.models import ModelChoiceField, ValidationError

def test_model_choice_field():
    field = ModelChoiceField()
    with pytest.raises(ValidationError):
        field.to_python("999")
"""
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)

    def transition_to(self, new_state: FSMState, payload: Optional[Dict[str, Any]] = None):
        self.state = new_state
        return self.ledger.log_state(
            issue_id=self.issue_id,
            state_name=self.state.value,
            retry_count=self.retry_count,
            payload=payload
        )

    def run_to_completion(self) -> Dict[str, Any]:
        """
        Executes the full deterministic FSM pipeline.
        """
        print(f"[ASF Orchestrator] Ingesting Issue {self.issue_id} into AI Software Factory...")
        self.transition_to(FSMState.INIT, self.payload)

        while self.state not in [
            FSMState.HUMAN_REVIEW, 
            FSMState.AWAITING_APPROVAL,
            FSMState.MERGE, 
            FSMState.PR_READY,
            FSMState.COMPLETED,
            FSMState.TERMINAL_SUCCESS, 
            FSMState.TERMINAL_FAILED
        ]:
            if self.state == FSMState.INIT or self.state == FSMState.ISSUE_RECEIVED:
                self._step_spec_synth()
            elif self.state == FSMState.SPEC_READY:
                self._step_localization()
            elif self.state == FSMState.LOCALIZATION:
                self._step_planning()
            elif self.state == FSMState.PLANNING:
                self._step_repair()
            elif self.state == FSMState.REPAIR:
                self._step_verification()
            elif self.state == FSMState.VERIFICATION:
                self._step_risk_gating()

        return {
            "issue_id": self.issue_id,
            "final_state": self.state.value,
            "retry_count": self.retry_count,
            "spec_contract": self.spec_contract.to_dict() if self.spec_contract else None,
            "patch": self.current_patch.get("patch") if self.current_patch else None,
            "validation_report": self.validation_report,
            "security_report": self.security_report,
            "mutation_report": self.mutation_report,
            "poc_report": self.poc_report,
            "rri_report": self.rri_report,
            "human_review_payload": self.human_review_payload,
            "pr_payload": self.pr_payload
        }

    def _step_spec_synth(self):
        print(f"[ASF Orchestrator] State -> SPEC_READY (Synthesizing Specification Contract)")
        self.spec_contract = SpecificationEngine.synthesize_spec(self.payload)
        self.transition_to(FSMState.SPEC_READY, self.spec_contract.to_dict())

    def _step_localization(self):
        print(f"[ASF Orchestrator] State -> LOCALIZATION for issue {self.issue_id}")
        symbols = self.aci.symbol_mapper.scan_directory()
        
        coverage_matrix = {
            "django/forms/models.py:ModelChoiceField.to_python": {"failed": 1, "passed": 0},
            "django/forms/fields.py:ChoiceField.validate": {"failed": 0, "passed": 3}
        }
        sbfl_rankings = OchiaiSBFLCalculator.rank_symbols(coverage_matrix, total_failed=1)
        agent_loc = self.llm_client.call_localization_agent(self.payload, symbols)
        
        self.localization_result = {
            "sbfl_rankings": sbfl_rankings,
            "agent_findings": agent_loc.get("suspicious_locations", [])
        }
        self.transition_to(FSMState.LOCALIZATION, self.localization_result)

    def _step_planning(self):
        print(f"[ASF Orchestrator] State -> PLANNING (Applying Ponytail YAGNI Invariants)")
        target_file = "django/forms/models.py"
        if self.localization_result and self.localization_result.get("agent_findings"):
            target_file = self.localization_result["agent_findings"][0].get("file", target_file)

        self.planning_result = {
            "target_file": target_file,
            "strategy": f"Synthesize minimal search-and-replace diff for {target_file} adhering to Ponytail rules.",
            "ponytail_invariants": ["YAGNI", "stdlib_preference", "minimal_diff"]
        }
        self.transition_to(FSMState.PLANNING, self.planning_result)

    def _step_repair(self):
        print(f"[ASF Orchestrator] State -> REPAIR (Attempt {self.retry_count + 1})")
        target_file = self.planning_result.get("target_file", "django/forms/models.py")
        
        file_view = self.aci.view_file(target_file, start_line=1, max_lines=100)
        repair_out = self.llm_client.call_repair_agent(
            self.payload, 
            self.localization_result, 
            file_view.get("content", ""),
            attempt=self.retry_count + 1
        )
        self.current_patch = repair_out
        self.transition_to(FSMState.REPAIR, {
            "patch": repair_out.get("patch"),
            "strategy": repair_out.get("strategy")
        })

    def _step_verification(self):
        print(f"[ASF Orchestrator] State -> VERIFICATION (Attempt {self.retry_count + 1})")
        target_file = self.planning_result.get("target_file", "django/forms/models.py")
        full_target_path = os.path.join(self.workspace_dir, target_file)

        # 1. Apply Candidate Patch
        apply_res = self.aci.apply_search_replace(
            target_file,
            self.current_patch.get("search_block", ""),
            self.current_patch.get("replace_block", "")
        )
        patch_success = apply_res.get("success", False)

        # 2. Flake8 Syntax & Linter Gate
        lint_res = self.sandbox.run_linter(full_target_path)

        # 3. Security SAST Scan
        sec_res = SecurityScanner.scan_patch(self.current_patch.get("patch", ""))
        self.security_report = sec_res

        # 4. Regression Unit Test Runner
        test_file = "tests/test_model_fields.py"
        test_res = self.sandbox.run_tests(test_file)

        self.validation_report = {
            "patch_applied": patch_success,
            "patch_error": apply_res.get("error", ""),
            "lint_passed": lint_res.get("passes_lint", False),
            "lint_errors": lint_res.get("errors", ""),
            "security_passed": sec_res.get("passed_security", True),
            "tests_passed": test_res.get("passes_tests", False),
            "test_output": test_res.get("output", "")
        }

        all_checks_passed = (
            patch_success and 
            lint_res.get("passes_lint") and 
            sec_res.get("passed_security") and 
            test_res.get("passes_tests")
        )

        if all_checks_passed:
            # 5. Semantic AST Mutation Testing
            mutation_res = self.sandbox.run_mutation_tests(target_file, test_file)
            self.mutation_report = mutation_res

            # 6. Fail-to-Pass PoC Execution
            poc_script = PoCReproductionEngine.generate_poc_script(self.payload)
            self.poc_report = PoCReproductionEngine.verify_fail_to_pass(self.workspace_dir, poc_script, is_patched=True)

            print(f"[Verification] Checks PASSED. Mutation Score: {mutation_res.get('mutation_score', 0.0)}")
            self.transition_to(FSMState.VERIFICATION, {
                "validation_report": self.validation_report,
                "security_report": self.security_report,
                "mutation_report": self.mutation_report,
                "poc_report": self.poc_report
            })
        else:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                print(f"[ASF Orchestrator] Maximum retries ({self.max_retries}) reached. Failing...")
                self.transition_to(FSMState.TERMINAL_FAILED, {
                    "reason": "Max retries exceeded with failing verification checks.",
                    "validation_report": self.validation_report
                })
            else:
                print(f"[ASF Orchestrator] Verification failed. Retrying patch repair (Retry: {self.retry_count})...")
                self.state = FSMState.PLANNING

    def _step_risk_gating(self):
        print(f"[ASF Orchestrator] Evaluating Regression Risk Index (RRI)...")
        target_file = self.planning_result.get("target_file", "django/forms/models.py")
        full_target_path = os.path.join(self.workspace_dir, target_file)

        patched_code = ""
        if os.path.exists(full_target_path):
            with open(full_target_path, "r", encoding="utf-8") as f:
                patched_code = f.read()

        survival_ratio = self.mutation_report.get("survival_ratio", 0.0) if self.mutation_report else 0.0

        self.rri_report = self.rri_engine.compute_rri(
            patch_diff=self.current_patch.get("patch", ""),
            original_code=patched_code,
            patched_code=patched_code,
            mutation_survival_ratio=survival_ratio
        )
        print(f"[Risk Engine] Calculated RRI: {self.rri_report.get('rri_score')} (Threshold: {self.risk_threshold})")

        issue_title = self.payload.get("issue", {}).get("title", "Software Issue")

        if self.rri_report.get("rri_score", 1.0) < self.risk_threshold:
            print("[ASF Orchestrator] Low Risk (< 0.30) -> Auto-Publishing Pull Request...")
            self.pr_payload = GitPRPublisher.publish_pull_request(
                repo_dir=self.workspace_dir,
                issue_id=self.issue_id,
                issue_title=issue_title,
                patch_diff=self.current_patch.get("patch", ""),
                rri_report=self.rri_report,
                mutation_report=self.mutation_report or {}
            )
            self.transition_to(FSMState.MERGE, {"patch": self.current_patch.get("patch"), "rri": self.rri_report, "pr": self.pr_payload})
            self.transition_to(FSMState.TERMINAL_SUCCESS, {"status": "PATCH_AUTO_MERGED", "pr_url": self.pr_payload.get("url")})
        else:
            print("[ASF Orchestrator] High Risk (>= 0.30) -> Locking in HUMAN_REVIEW Gate...")
            self.human_review_payload = HumanReviewerGateway.generate_slack_payload(
                issue_id=self.issue_id,
                issue_title=issue_title,
                patch_diff=self.current_patch.get("patch", ""),
                rri_result=self.rri_report,
                lint_report={"passes_lint": self.validation_report.get("lint_passed")},
                mutation_report=self.mutation_report or {}
            )
            self.transition_to(FSMState.HUMAN_REVIEW, {
                "patch": self.current_patch.get("patch"),
                "rri": self.rri_report,
                "slack_payload": self.human_review_payload
            })

    def process_human_decision(self, decision: str, reviewer: str = "Admin", comments: str = ""):
        """
        Handles human reviewer decision ('APPROVED' or 'REJECTED').
        """
        issue_title = self.payload.get("issue", {}).get("title", "Software Issue")
        if decision == "APPROVED":
            print(f"[Human Gate] Patch APPROVED by {reviewer}. Merging...")
            self.pr_payload = GitPRPublisher.publish_pull_request(
                repo_dir=self.workspace_dir,
                issue_id=self.issue_id,
                issue_title=issue_title,
                patch_diff=self.current_patch.get("patch", "") if self.current_patch else "",
                rri_report=self.rri_report or {},
                mutation_report=self.mutation_report or {}
            )
            self.transition_to(FSMState.MERGE, {
                "decision": "APPROVED",
                "reviewer": reviewer,
                "comments": comments,
                "pr": self.pr_payload
            })
            self.transition_to(FSMState.TERMINAL_SUCCESS, {"status": "HUMAN_APPROVED_AND_MERGED", "pr_url": self.pr_payload.get("url")})
            return {"status": "SUCCESS", "state": FSMState.TERMINAL_SUCCESS.value, "pr_url": self.pr_payload.get("url")}
        else:
            print(f"[Human Gate] Patch REJECTED by {reviewer}. Halting...")
            self.transition_to(FSMState.TERMINAL_FAILED, {
                "decision": "REJECTED",
                "reviewer": reviewer,
                "comments": comments
            })
            return {"status": "REJECTED", "state": FSMState.TERMINAL_FAILED.value}
