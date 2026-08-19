import ast
import os
from typing import Dict, List, Any, Optional

class SymbolMapBuilder:
    """
    Constructs a structural symbolic map of a Python repository.
    Extracts classes, methods, line offsets, argument signatures, and docstrings.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.index: Dict[str, Any] = {
            "files": {},
            "classes": {},
            "methods": {}
        }

    def scan_directory(self) -> Dict[str, Any]:
        for root, _, files in os.walk(self.root_dir):
            # Skip hidden and cache folders
            if "/." in root or "/__pycache__" in root or "/venv" in root or "/.git" in root:
                continue

            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    self.index_file(full_path, rel_path)

        return self.index

    def index_file(self, full_path: str, rel_path: str):
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            tree = ast.parse(content, filename=rel_path)
            file_classes = []
            file_methods = []

            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = self._extract_class_info(node, rel_path)
                    self.index["classes"][f"{rel_path}:{node.name}"] = class_info
                    file_classes.append(node.name)

                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            method_info = self._extract_method_info(item, rel_path, parent_class=node.name)
                            key = f"{rel_path}:{node.name}.{item.name}"
                            self.index["methods"][key] = method_info
                            file_methods.append(f"{node.name}.{item.name}")

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_info = self._extract_method_info(node, rel_path, parent_class=None)
                    key = f"{rel_path}:{node.name}"
                    self.index["methods"][key] = func_info
                    file_methods.append(node.name)

            self.index["files"][rel_path] = {
                "classes": file_classes,
                "methods": file_methods,
                "lines_count": len(content.splitlines())
            }

        except Exception as e:
            # File may contain syntax error
            self.index["files"][rel_path] = {"error": str(e)}

    def _extract_class_info(self, node: ast.ClassDef, file_path: str) -> Dict[str, Any]:
        methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        bases = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
        return {
            "name": node.name,
            "file": file_path,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "bases": bases,
            "methods": methods,
            "docstring": ast.get_docstring(node) or ""
        }

    def _extract_method_info(
        self, 
        node: ast.FunctionDef, 
        file_path: str, 
        parent_class: Optional[str] = None
    ) -> Dict[str, Any]:
        args = [a.arg for a in node.args.args]
        return {
            "name": node.name,
            "file": file_path,
            "parent_class": parent_class,
            "start_line": node.lineno,
            "end_line": getattr(node, "end_lineno", node.lineno),
            "args": args,
            "docstring": ast.get_docstring(node) or ""
        }

    def search_class(self, query: str) -> List[Dict[str, Any]]:
        results = []
        for key, info in self.index["classes"].items():
            if query.lower() in info["name"].lower():
                results.append(info)
        return results

    def search_method(self, query: str) -> List[Dict[str, Any]]:
        results = []
        for key, info in self.index["methods"].items():
            if query.lower() in info["name"].lower():
                results.append(info)
        return results
