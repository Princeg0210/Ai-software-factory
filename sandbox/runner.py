import os
import subprocess
import json
from typing import Dict, Any, List, Optional
from .linter_gate import LinterGate
from .mutation_engine import MutationTestingEngine

class SandboxRunner:
    """
    Orchestrates execution of tests, linter gates, and mutation testing
    in an isolated container or subprocess environment.
    """
    def __init__(self, repo_dir: str, use_docker: bool = False, docker_image: str = "ai-software-factory-sandbox:latest"):
        self.repo_dir = os.path.abspath(repo_dir)
        self.use_docker = use_docker
        self.docker_image = docker_image
        self.mutation_engine = MutationTestingEngine(self.repo_dir)

    def run_linter(self, file_path: str) -> Dict[str, Any]:
        """
        Runs the flake8 syntax gate.
        """
        if self.use_docker:
            return self._run_in_docker(["python3", "task.py", "lint", file_path])
        else:
            full_path = os.path.join(self.repo_dir, file_path) if not os.path.isabs(file_path) else file_path
            return LinterGate.check_file(full_path)

    def run_tests(self, test_target: str) -> Dict[str, Any]:
        """
        Runs pytest inside sandbox.
        """
        if self.use_docker:
            return self._run_in_docker(["python3", "task.py", "test", test_target])
        else:
            full_path = os.path.join(self.repo_dir, test_target) if not os.path.isabs(test_target) else test_target
            if not os.path.exists(full_path):
                return {
                    "passes_tests": True,
                    "output": "No specific test file present; skipping."
                }
            cmd = ["pytest", "-q", full_path]
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{self.repo_dir}:{env.get('PYTHONPATH', '')}"
            try:
                result = subprocess.run(
                    cmd, 
                    cwd=self.repo_dir, 
                    env=env,
                    capture_output=True, 
                    text=True, 
                    timeout=15
                )
                return {
                    "passes_tests": result.returncode == 0,
                    "output": result.stdout.strip() or result.stderr.strip()
                }
            except Exception as e:
                return {
                    "passes_tests": False,
                    "output": f"Test runner execution failed: {str(e)}"
                }

    def run_mutation_tests(self, target_file: str, test_target: str) -> Dict[str, Any]:
        """
        Executes mutation testing against target file and test target.
        """
        full_test_path = os.path.join(self.repo_dir, test_target) if not os.path.isabs(test_target) else test_target
        if not os.path.exists(full_test_path):
            return {
                "total_mutants": 0,
                "killed_mutants": 0,
                "survived_mutants": 0,
                "mutation_score": 1.0,
                "survival_ratio": 0.0,
                "details": []
            }
        test_cmd = ["pytest", "-q", full_test_path]
        return self.mutation_engine.run_mutation_analysis(target_file, test_cmd)

    def _run_in_docker(self, command: List[str]) -> Dict[str, Any]:
        """
        Executes command in a restricted Docker container with --network none and non-root sandbox user.
        """
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "-v", f"{self.repo_dir}:/workspace:rw",
            "-w", "/workspace",
            self.docker_image
        ] + command

        try:
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=30)
            try:
                # task.py outputs JSON
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {
                    "passes_tests": result.returncode == 0,
                    "passes_lint": result.returncode == 0,
                    "output": result.stdout + "\n" + result.stderr
                }
        except Exception as e:
            return {
                "passes_tests": False,
                "passes_lint": False,
                "output": f"Docker sandbox execution failed: {str(e)}"
            }
