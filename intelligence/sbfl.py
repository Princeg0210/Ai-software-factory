import math
from typing import Dict, List, Any, Optional

class OchiaiSBFLCalculator:
    """
    Computes Spectrum-Based Fault Localization (SBFL) using the Ochiai metric:
    
    Suspiciousness(m) = failed(m) / sqrt(total_failed * (failed(m) + passed(m)))
    
    where:
    - failed(m): number of failing test cases that execute method m
    - passed(m): number of passing test cases that execute method m
    - total_failed: total number of failing test cases in test suite
    """

    @staticmethod
    def calculate_suspiciousness(
        failed_m: int, 
        passed_m: int, 
        total_failed: int
    ) -> float:
        if total_failed <= 0 or (failed_m + passed_m) <= 0:
            return 0.0
        
        denominator = math.sqrt(total_failed * (failed_m + passed_m))
        if denominator == 0:
            return 0.0
        
        return round(failed_m / denominator, 4)

    @classmethod
    def rank_symbols(
        cls, 
        coverage_matrix: Dict[str, Dict[str, int]], 
        total_failed: int
    ) -> List[Dict[str, Any]]:
        """
        Takes a coverage matrix of the form:
        {
            "django/forms/models.py:ModelChoiceField.to_python": {"failed": 2, "passed": 1},
            "django/forms/fields.py:ChoiceField.validate": {"failed": 0, "passed": 5}
        }
        and returns a sorted list of suspicious locations.
        """
        ranked = []
        for symbol, stats in coverage_matrix.items():
            failed_m = stats.get("failed", 0)
            passed_m = stats.get("passed", 0)
            score = cls.calculate_suspiciousness(failed_m, passed_m, total_failed)
            
            parts = symbol.split(":")
            file_path = parts[0]
            target_symbol = parts[1] if len(parts) > 1 else ""

            ranked.append({
                "symbol": symbol,
                "file": file_path,
                "target": target_symbol,
                "failed_tests_hit": failed_m,
                "passed_tests_hit": passed_m,
                "suspiciousness": score
            })

        # Sort descending by suspiciousness score
        ranked.sort(key=lambda x: x["suspiciousness"], reverse=True)
        return ranked
