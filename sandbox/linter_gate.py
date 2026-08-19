import subprocess
import os
from typing import Dict, Any

class LinterGate:
    """
    Statically analyzes code files using flake8 targeting only critical syntax
    and undefined name errors (E999, F821, F822, F831, E111, E112, E113, E902).
    """
    CRITICAL_CODES = "F821,F822,F831,E111,E112,E113,E999,E902"

    @classmethod
    def check_file(cls, file_path: str) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"passes_lint": False, "errors": f"File '{file_path}' does not exist."}

        command = [
            "flake8",
            "--isolated",
            f"--select={cls.CRITICAL_CODES}",
            file_path
        ]

        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"passes_lint": True, "errors": ""}
            else:
                return {
                    "passes_lint": False, 
                    "errors": result.stdout.strip() or result.stderr.strip()
                }
        except FileNotFoundError:
            # Fallback to python compile check if flake8 binary is not available
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    compile(f.read(), file_path, "exec")
                return {"passes_lint": True, "errors": ""}
            except SyntaxError as e:
                return {"passes_lint": False, "errors": f"SyntaxError in {file_path}: {e}"}
        except Exception as e:
            return {"passes_lint": False, "errors": f"Linter execution exception: {str(e)}"}
