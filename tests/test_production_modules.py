import pytest
from spec.contract import SpecificationEngine
from security.scanner import SecurityScanner
from verification.poc_generator import PoCReproductionEngine
from git_ops.publisher import GitPRPublisher
from evaluation.harness import BenchmarkEvaluationHarness
from fsm.orchestrator import FSMOrchestrator

def test_specification_synthesis():
    payload = {
        "issue_id": "django-13933",
        "issue": {
            "title": "ModelChoiceField validation bug",
            "description": "ModelChoiceField should include value in ValidationError params."
        }
    }
    spec = SpecificationEngine.synthesize_spec(payload)
    assert spec.issue_id == "django-13933"
    assert "ModelChoiceField.to_python" in spec.target_symbols
    assert spec.minimal_diff_mandate is True

def test_security_scanner_clean_patch():
    clean_patch = """--- a.py\n+++ a.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2"""
    res = SecurityScanner.scan_patch(clean_patch)
    assert res["passed_security"] is True
    assert res["findings_count"] == 0

def test_security_scanner_detects_secrets_and_rce():
    insecure_patch = """--- a.py\n+++ a.py\n@@ -1,1 +1,2 @@\n+API_KEY = "ghp_1234567890abcdef1234567890abcdef1234"\n+eval("os.system('rm -rf /')")\n+subprocess.Popen("ls", shell=True)"""
    res = SecurityScanner.scan_patch(insecure_patch)
    assert res["passed_security"] is False
    assert res["findings_count"] >= 2
    types = [f["type"] for f in res["findings"]]
    assert "SECRET_LEAK" in types
    assert "INSECURE_EXECUTION" in types

def test_poc_reproduction_generation():
    payload = {"issue_id": "django-13933", "issue": {"title": "ModelChoiceField error value"}}
    poc = PoCReproductionEngine.generate_poc_script(payload)
    assert "test_model_choice_field_reproduction" in poc
    assert "invalid_id_999" in poc

def test_git_pr_publisher():
    pr = GitPRPublisher.publish_pull_request(
        repo_dir=".",
        issue_id="django-13933",
        issue_title="ModelChoiceField error fix",
        patch_diff="--- diff",
        rri_report={"rri_score": 0.05, "action": "AUTO_MERGE"},
        mutation_report={"mutation_score": 1.0}
    )
    assert pr["status"] == "READY_FOR_MERGE"
    assert "django-13933" in pr["title"]
    assert "Ponytail Minimal-Diff Mandate" in pr["body"]

def test_benchmark_evaluation_harness():
    tasks = [
        {
            "issue_id": "django-13933",
            "repository": {"url": "https://github.com/django/django"},
            "issue": {"title": "ModelChoiceField error", "description": "Fix invalid_choice parameter"}
        }
    ]
    report = BenchmarkEvaluationHarness.run_benchmark_suite(
        tasks=tasks,
        orchestrator_cls=FSMOrchestrator,
        workspace_base_dir="./workspace_repo"
    )
    assert report["total_tasks"] == 1
    assert "resolution_rate" in report
    assert "benchmark_results" in report
