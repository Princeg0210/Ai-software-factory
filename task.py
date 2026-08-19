# task.py: Sandbox Execution Helper Engine
import sys
import subprocess
import json

def run_linter(file_path):
    print(f"[Sandbox Task] Linting {file_path} using flake8...")
    command = [
        "flake8",
        "--isolated",
        "--select=F821,F822,F831,E111,E112,E113,E999,E902",
        file_path
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return {"passes_lint": True, "errors": ""}
    else:
        return {"passes_lint": False, "errors": result.stdout}

def run_tests(test_path):
    print(f"[Sandbox Task] Executing pytest on {test_path}...")
    command = ["pytest", "-q", test_path]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return {"passes_tests": True, "output": result.stdout}
    else:
        return {"passes_tests": False, "output": result.stdout}

if __name__ == "__main__":
    # Mock routing for demonstration
    if len(sys.argv) < 3:
        print("Usage: python3 task.py [lint|test] [file_path]")
        sys.exit(1)
    
    action = sys.argv[1]
    target = sys.argv[2]
    
    if action == "lint":
        print(json.dumps(run_linter(target)))
    elif action == "test":
        print(json.dumps(run_tests(target)))
    else:
        print(f"Unknown action: {action}")
