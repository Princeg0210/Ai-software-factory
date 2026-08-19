import ast
import os
from typing import Dict, Any, List, Optional

class SymbolMapBuilder:
    """
    Constructs an Abstract Syntax Tree (AST) symbol graph of the codebase,
    extracting class hierarchies, method signatures, line ranges, and docstrings.
    """
    def __init__(self, repo_dir: str):
        self.repo_dir = os.path.abspath(repo_dir)

    def scan_directory(self) -> Dict[str, Any]:
        """
        Scans all python files in repo_dir and parses their AST structure.
        """
        files_map = {}
        for root, _, filenames in os.walk(self.repo_dir):
            for fn in filenames:
                if fn.endswith(".py") and fn != "__init__.py":
                    rel_path = os.path.relpath(os.path.join(root, fn), self.repo_dir)
                    if not rel_path.startswith("tests") and not rel_path.startswith("."):
                        symbols = self.parse_file_symbols(rel_path)
                        files_map[rel_path] = symbols

        # If no non-test files found, fallback to scanning all python files
        if not files_map:
            for root, _, filenames in os.walk(self.repo_dir):
                for fn in filenames:
                    if fn.endswith(".py"):
                        rel_path = os.path.relpath(os.path.join(root, fn), self.repo_dir)
                        symbols = self.parse_file_symbols(rel_path)
                        files_map[rel_path] = symbols

        return {
            "total_files": len(files_map),
            "files": files_map
        }

    def parse_file_symbols(self, rel_path: str) -> Dict[str, Any]:
        """
        Extracts classes, methods, docstrings, and line bounds from a file.
        """
        full_path = os.path.join(self.repo_dir, rel_path)
        if not os.path.exists(full_path):
            return {}

        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        try:
            tree = ast.parse(code, filename=rel_path)
        except Exception:
            return {"classes": [], "functions": []}

        classes = []
        functions = []

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append({
                            "name": item.name,
                            "start_line": item.lineno,
                            "end_line": getattr(item, "end_lineno", item.lineno),
                            "docstring": ast.get_docstring(item)
                        })
                classes.append({
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": ast.get_docstring(node),
                    "methods": methods
                })
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append({
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": ast.get_docstring(node)
                })

        return {
            "classes": classes,
            "functions": functions
        }
