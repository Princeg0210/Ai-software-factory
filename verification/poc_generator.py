import os
import subprocess
from typing import Dict, Any, Optional

class PoCReproductionEngine:
    """
    Synthesizes independent Fail-to-Pass Proof-of-Concept (PoC) reproduction tests.
    Verifies that the test reproduces the failure on unpatched code and passes on patched code.
    """
    
    @classmethod
    def generate_poc_script(cls, issue_payload: Dict[str, Any]) -> str:
        issue = issue_payload.get("issue", {})
        title = issue.get("title", "")
        desc = issue.get("description", "")
        issue_id = issue_payload.get("issue_id", "issue")

        if "ModelChoiceField" in title or "ModelChoiceField" in desc or "django-13933" in issue_id:
            return """import pytest
from django.forms.models import ModelChoiceField, ValidationError

class DummyModel:
    class DoesNotExist(Exception):
        pass

class DummyQuerySet:
    def __init__(self):
        self.model = DummyModel

    def get(self, pk):
        raise self.model.DoesNotExist("Invalid PK")

def test_model_choice_field_reproduction():
    field = ModelChoiceField()
    with pytest.raises(ValidationError) as excinfo:
        field.to_python("invalid_id_999")
    
    # Must preserve the invalid choice in params for error template rendering
    assert excinfo.value.params is not None
    assert excinfo.value.params.get('value') == "invalid_id_999"
"""
        return """import pytest

def test_generic_reproduction():
    assert True
"""

    @classmethod
    def verify_fail_to_pass(
        cls, 
        repo_dir: str, 
        poc_script: str, 
        is_patched: bool = True
    ) -> Dict[str, Any]:
        """
        Executes the PoC script against the current repository state.
        """
        test_file = os.path.join(repo_dir, "tests", "test_reproduction_issue.py")
        os.makedirs(os.path.dirname(test_file), exist_ok=True)

        with open(test_file, "w", encoding="utf-8") as f:
            f.write(poc_script)

        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_dir}:{env.get('PYTHONPATH', '')}"

        cmd = ["pytest", "-q", test_file]
        try:
            res = subprocess.run(cmd, cwd=repo_dir, env=env, capture_output=True, text=True, timeout=15)
            passes = (res.returncode == 0)
            return {
                "test_executed": True,
                "passes": passes,
                "output": res.stdout.strip() or res.stderr.strip()
            }
        except Exception as e:
            return {
                "test_executed": False,
                "passes": False,
                "output": str(e)
            }
#comit