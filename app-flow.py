# app-flow.py: Core FSM Orchestrator for the AI Software Factory
import os
import sys
import json
import uuid

class StateLedger:
    def __init__(self):
        self.ledger = []

    def log_state(self, issue_id, state_name, payload=None):
        entry = {
            "transaction_id": str(uuid.uuid4()),
            "issue_id": issue_id,
            "state": state_name,
            "payload": payload or {},
        }
        self.ledger.append(entry)
        print(f"[Ledger] TRANSITION -> Issue {issue_id}: Current State is {state_name}")
        return entry

class AppFlowOrchestrator:
    def __init__(self, issue_payload):
        self.ledger = StateLedger()
        self.issue_id = issue_payload.get("issue_id", str(uuid.uuid4()))
        self.payload = issue_payload
        self.state = "INIT"
        self.retry_count = 0
        self.max_retries = 3

    def transition_to(self, new_state, payload=None):
        self.state = new_state
        self.ledger.log_state(self.issue_id, self.state, payload)

    def run_fsm(self):
        print("Starting AI Software Factory orchestrator FSM...")
        self.transition_to("INIT", self.payload)
        
        # 1. LOCALIZATION
        self.transition_to("LOCALIZATION")
        print("[Localization] Scanning symbols and running Ochiai SBFL...")
        # Simulating AST symbol mapping and Ochiai SBFL
        localization_result = {
            "suspicious_locations": [
                {"file": "django/forms/models.py", "class": "ModelChoiceField", "method": "to_python", "suspiciousness": 0.85}
            ]
        }
        
        # 2. PLANNING
        self.transition_to("PLANNING", localization_result)
        print("[Planning] Formulating target repair strategy...")
        strategy_payload = {
            "strategy": "Modify ModelChoiceField.to_python to capture value and raise ValidationError with params.",
            "file": "django/forms/models.py"
        }
        
        # 3. REPAIR
        self.transition_to("REPAIR", strategy_payload)
        print("[Repair] Applying CodeAct patch generation...")
        
        # Simulated CodeAct Patch Generation (Search/Replace Diff)
        candidate_patch = """
--- django/forms/models.py
+++ django/forms/models.py
@@ -1283,5 +1283,5 @@
-except (ValueError, TypeError, self.queryset.model.DoesNotExist):
-    raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice')
+except (ValueError, TypeError, self.queryset.model.DoesNotExist):
+    raise ValidationError(self.error_messages['invalid_choice'], code='invalid_choice', params={'value': value})
"""
        
        # 4. VERIFICATION (Retry loop simulation)
        while self.retry_count < self.max_retries:
            self.transition_to("VERIFICATION", {"patch": candidate_patch, "retry": self.retry_count})
            print(f"[Verification] Running syntax checks and execution tests (Attempt {self.retry_count+1})...")
            
            # Static lint pass simulation
            lint_pass = True
            tests_pass = True
            
            if lint_pass and tests_pass:
                print("[Verification] All checks passed successfully!")
                break
            else:
                self.retry_count += 1
                print("[Verification] Test/Lint failed. Retrying patch repair...")
        
        # Calculating regression risk score
        rri = 0.25 # Low risk patch since it only modifies 1 line
        print(f"[Risk Engine] Calculated Regression Risk Index: {rri}")
        
        if rri < 0.3:
            # Low risk -> MERGE directly
            self.transition_to("MERGE", {"merged_patch": candidate_patch})
            print("[Orchestrator] FSM Completed: Patch auto-merged safely!")
        else:
            # High risk -> HUMAN REVIEW
            self.transition_to("HUMAN_REVIEW", {"patch": candidate_patch})
            print("[Orchestrator] FSM Completed: Routed to Human Review gate.")

if __name__ == "__main__":
    payload = {
        "issue_id": "django-13933",
        "repo_url": "https://github.com/django/django",
        "title": "ModelChoiceField invalid_choice validation error shows no value",
        "description": "ModelChoiceField validation error should show the value of the invalid choice in Django forms models."
    }
    orchestrator = AppFlowOrchestrator(payload)
    orchestrator.run_fsm()
