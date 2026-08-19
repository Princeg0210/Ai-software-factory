import time
from typing import List, Dict, Any, Optional

class BenchmarkEvaluationHarness:
    """
    Empirical Evaluation Harness for evaluating AI Software Factory
    against standard SWE-bench (Verified, Pro, Lite) and HumanEval datasets.
    """

    @classmethod
    def run_benchmark_suite(
        cls, 
        tasks: List[Dict[str, Any]], 
        orchestrator_cls, 
        workspace_base_dir: str
    ) -> Dict[str, Any]:
        results = []
        total_tasks = len(tasks)
        resolved_count = 0
        verified_count = 0
        security_passed_count = 0
        total_latency = 0.0
        total_cost = 0.0

        for task in tasks:
            start_time = time.time()
            task_id = task.get("issue_id", "unknown")
            
            # Execute through orchestrator
            orch = orchestrator_cls(
                issue_payload=task,
                workspace_dir=workspace_base_dir,
                use_docker=False
            )
            out = orch.run_to_completion()
            elapsed = time.time() - start_time

            is_resolved = out.get("final_state") in ["MERGE", "TERMINAL_SUCCESS", "PR_READY"]
            has_strong_mutation = (out.get("mutation_report", {}) or {}).get("mutation_score", 0.0) >= 0.70
            is_verified = is_resolved and has_strong_mutation
            
            if is_resolved:
                resolved_count += 1
            if is_verified:
                verified_count += 1
            if (out.get("validation_report") or {}).get("lint_passed"):
                security_passed_count += 1

            total_latency += elapsed
            total_cost += 0.15 # Simulated token & compute cost per run

            results.append({
                "task_id": task_id,
                "final_state": out.get("final_state"),
                "resolved": is_resolved,
                "verified": is_verified,
                "rri_score": (out.get("rri_report") or {}).get("rri_score"),
                "latency_seconds": round(elapsed, 2)
            })

        res_rate = round(resolved_count / total_tasks, 4) if total_tasks > 0 else 0.0
        ver_rate = round(verified_count / total_tasks, 4) if total_tasks > 0 else 0.0

        return {
            "total_tasks": total_tasks,
            "resolved_tasks": resolved_count,
            "resolution_rate": res_rate,
            "verified_resolution_rate": ver_rate,
            "average_latency_seconds": round(total_latency / total_tasks, 2) if total_tasks > 0 else 0.0,
            "total_cost_usd": round(total_cost, 2),
            "benchmark_results": results
        }
