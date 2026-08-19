import pytest
from intelligence.sbfl import OchiaiSBFLCalculator

def test_ochiai_suspiciousness_formula():
    # Test case 1: Standard values
    # failed = 2, passed = 1, total_failed = 2
    # Suspiciousness = 2 / sqrt(2 * (2 + 1)) = 2 / sqrt(6) = 2 / 2.4494897 = ~0.8165
    score = OchiaiSBFLCalculator.calculate_suspiciousness(failed_m=2, passed_m=1, total_failed=2)
    assert pytest.approx(score, 0.01) == 0.8165

    # Test case 2: Method executed by zero failed tests
    score_zero = OchiaiSBFLCalculator.calculate_suspiciousness(failed_m=0, passed_m=5, total_failed=3)
    assert score_zero == 0.0

    # Test case 3: Method executed by only failed tests
    score_perfect = OchiaiSBFLCalculator.calculate_suspiciousness(failed_m=3, passed_m=0, total_failed=3)
    assert score_perfect == 1.0

    # Test case 4: Zero total failed tests edge case
    score_edge = OchiaiSBFLCalculator.calculate_suspiciousness(failed_m=0, passed_m=0, total_failed=0)
    assert score_edge == 0.0

def test_rank_symbols():
    coverage_matrix = {
        "django/forms/models.py:ModelChoiceField.to_python": {"failed": 2, "passed": 0},
        "django/forms/fields.py:ChoiceField.validate": {"failed": 1, "passed": 3},
        "django/core/exceptions.py:ValidationError.__init__": {"failed": 0, "passed": 4}
    }
    ranked = OchiaiSBFLCalculator.rank_symbols(coverage_matrix, total_failed=2)
    
    assert len(ranked) == 3
    # Top ranked should be ModelChoiceField.to_python
    assert ranked[0]["target"] == "ModelChoiceField.to_python"
    assert ranked[0]["suspiciousness"] == 1.0
    # Bottom ranked should be ValidationError.__init__
    assert ranked[2]["suspiciousness"] == 0.0
