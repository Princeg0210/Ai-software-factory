import os
import tempfile
import pytest
from agents.aci import AgentComputerInterface

def test_aci_view_file_100_lines_limit():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a file with 150 lines
        lines = [f"line content number {i}" for i in range(1, 151)]
        file_path = os.path.join(tmp_dir, "large_file.py")
        with open(file_path, "w") as f:
            f.write("\n".join(lines))

        aci = AgentComputerInterface(tmp_dir)
        
        # Test viewing first 100 lines
        view_1 = aci.view_file("large_file.py", start_line=1, max_lines=100)
        assert view_1["start_line"] == 1
        assert view_1["end_line"] == 100
        assert view_1["total_lines"] == 150
        assert view_1["has_more"] is True
        assert "1: line content number 1" in view_1["content"]
        assert "100: line content number 100" in view_1["content"]
        assert "101: line content number 101" not in view_1["content"]

        # Test viewing remaining lines
        view_2 = aci.view_file("large_file.py", start_line=101, max_lines=100)
        assert view_2["start_line"] == 101
        assert view_2["end_line"] == 150
        assert view_2["has_more"] is False

def test_aci_search_replace_patching():
    with tempfile.TemporaryDirectory() as tmp_dir:
        code = """def calculate(x):
    return x * 2
"""
        file_path = os.path.join(tmp_dir, "calc.py")
        with open(file_path, "w") as f:
            f.write(code)

        aci = AgentComputerInterface(tmp_dir)

        # Apply valid search and replace
        res = aci.apply_search_replace(
            "calc.py",
            "    return x * 2",
            "    if x is None:\n        return 0\n    return x * 2"
        )
        assert res["success"] is True

        with open(file_path, "r") as f:
            new_code = f.read()
        assert "if x is None:" in new_code

        # Attempt invalid search block
        fail_res = aci.apply_search_replace(
            "calc.py",
            "non_existent_code_block",
            "replacement"
        )
        assert fail_res["success"] is False
