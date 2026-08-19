import pytest
from risk.rri_engine import RegressionRiskIndexEngine
from risk.reviewer_gateway import HumanReviewerGateway

def test_rri_calculation_low_risk():
    engine = RegressionRiskIndexEngine(w_lines=0.30, w_ast=0.40, w_mutation=0.30)
    
    # 2 line change, no AST break, 0 mutation survival
    patch_diff = """--- a.py\n+++ a.py\n@@ -1,1 +1,1 @@\n-old_line\n+new_line"""
    orig = "def foo(x):\n    return x + 1"
    patched = "def foo(x):\n    return x + 2"
    
    res = engine.compute_rri(
        patch_diff=patch_diff,
        original_code=orig,
        patched_code=patched,
        mutation_survival_ratio=0.0
    )
    
    assert res["is_low_risk"] is True
    assert res["rri_score"] < 0.30
    assert res["action"] == "AUTO_MERGE"

def test_rri_calculation_high_risk_on_interface_break():
    engine = RegressionRiskIndexEngine(w_lines=0.30, w_ast=0.40, w_mutation=0.30)
    
    # Deletes public function foo -> AST break
    patch_diff = """--- a.py\n+++ a.py\n@@ -1,3 +0,0 @@\n-def foo(x):\n-    return x"""
    orig = "def foo(x):\n    return x"
    patched = "def bar(y):\n    return y"
    
    res = engine.compute_rri(
        patch_diff=patch_diff,
        original_code=orig,
        patched_code=patched,
        mutation_survival_ratio=0.5
    )
    
    assert res["is_low_risk"] is False
    assert res["rri_score"] >= 0.30
    assert res["action"] == "HUMAN_REVIEW"

def test_slack_payload_generation():
    rri_res = {"rri_score": 0.45}
    payload = HumanReviewerGateway.generate_slack_payload(
        issue_id="django-13933",
        issue_title="ModelChoiceField validation bug",
        patch_diff="--- diff",
        rri_result=rri_res,
        lint_report={"passes_lint": True},
        mutation_report={"mutation_score": 0.8, "killed_mutants": 4, "total_mutants": 5}
    )
    
    assert "django-13933" in payload["text"]
    assert len(payload["blocks"]) >= 4
    # Check for approval actions in block
    action_block = [b for b in payload["blocks"] if b.get("type") == "actions"][0]
    assert len(action_block["elements"]) == 2
