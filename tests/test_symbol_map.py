import os
import tempfile
import pytest
from intelligence.symbol_map import SymbolMapBuilder

def test_symbol_map_indexing():
    with tempfile.TemporaryDirectory() as tmp_dir:
        sample_code = """
import os

class ModelChoiceField:
    def __init__(self, queryset):
        self.queryset = queryset

    def to_python(self, value):
        if value in (None, ''):
            return None
        return value

def standalone_helper(x, y):
    return x + y
"""
        file_path = os.path.join(tmp_dir, "sample.py")
        with open(file_path, "w") as f:
            f.write(sample_code)

        builder = SymbolMapBuilder(tmp_dir)
        index = builder.scan_directory()

        assert "sample.py" in index["files"]
        assert len(index["classes"]) == 1
        assert "sample.py:ModelChoiceField" in index["classes"]
        
        class_info = index["classes"]["sample.py:ModelChoiceField"]
        assert "to_python" in class_info["methods"]
        assert "__init__" in class_info["methods"]

        methods_found = builder.search_method("to_python")
        assert len(methods_found) == 1
        assert methods_found[0]["name"] == "to_python"
        assert methods_found[0]["parent_class"] == "ModelChoiceField"
