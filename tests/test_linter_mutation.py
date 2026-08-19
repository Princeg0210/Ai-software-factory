import os
import tempfile
import pytest
from sandbox.linter_gate import LinterGate
from sandbox.mutation_engine import MutationTestingEngine, OperatorMutator
from sandbox.consensus import ConsensusVotingEngine

def test_linter_gate_syntax_detection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Valid code
        good_file = os.path.join(tmp_dir, "good.py")
        with open(good_file, "w") as f:
            f.write("def foo():\n    return 42\n")

        res_good = LinterGate.check_file(good_file)
        assert res_good["passes_lint"] is True

        # Code with critical syntax error (E999 / invalid syntax)
        bad_file = os.path.join(tmp_dir, "bad.py")
        with open(bad_file, "w") as f:
            f.write("def foo(\n    return 42\n")

        res_bad = LinterGate.check_file(bad_file)
        assert res_bad["passes_lint"] is False

def test_mutation_engine_operator_inversion():
    with tempfile.TemporaryDirectory() as tmp_dir:
        target_code = """
def check_val(x):
    if x == 10:
        return True
    return False
"""
        target_file = os.path.join(tmp_dir, "target.py")
        with open(target_file, "w") as f:
            f.write(target_code)

        test_code = """
import pytest
from target import check_val

def test_check_val():
    assert check_val(10) is True
    assert check_val(5) is False
"""
        test_file = os.path.join(tmp_dir, "test_target.py")
        with open(test_file, "w") as f:
            f.write(test_code)

        engine = MutationTestingEngine(tmp_dir)
        points = engine.count_mutation_points("target.py")
        assert points == 1

        # Run mutation analysis using pytest
        report = engine.run_mutation_analysis("target.py", ["pytest", "-q", test_file])
        assert report["total_mutants"] == 1
        # The test should kill the mutant (x == 10 mutated to x != 10 fails the assertions)
        assert report["killed_mutants"] == 1
        assert report["mutation_score"] == 1.0
        assert report["survival_ratio"] == 0.0

def test_consensus_voting():
    candidates = [
        {"patch": "--- a.py\n+++ a.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 2", "passes_tests": True, "passes_lint": True, "mutation_score": 0.9},
        {"patch": "--- a.py\n+++ a.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x =  2", "passes_tests": True, "passes_lint": True, "mutation_score": 0.8},
        {"patch": "--- a.py\n+++ a.py\n@@ -1,1 +1,1 @@\n-x = 1\n+x = 99", "passes_tests": False, "passes_lint": True, "mutation_score": 0.1},
    ]
    result = ConsensusVotingEngine.vote_on_candidates(candidates)
    assert result["total_valid"] == 2
    assert result["selected_patch"]["mutation_score"] == 0.9
    assert result["consensus_ratio"] == 1.0  # Normalized syntax makes first two identical
