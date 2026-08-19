import os
import re
from typing import Dict, Any, List, Optional
from intelligence.symbol_map import SymbolMapBuilder

class AgentComputerInterface:
    """
    Restricted Agent-Computer Interface (ACI).
    Enforces 100-line chunk viewing, symbolic code queries,
    and unified diff / search-and-replace patching to prevent context blowout
    and file destruction.
    """
    def __init__(self, repo_root: str):
        self.repo_root = os.path.abspath(repo_root)
        self.symbol_mapper = SymbolMapBuilder(self.repo_root)
        self.symbol_mapper.scan_directory()

    def view_file(self, rel_path: str, start_line: int = 1, max_lines: int = 100) -> Dict[str, Any]:
        """
        Returns a 100-line window of the file with prepended line numbers.
        """
        full_path = os.path.join(self.repo_root, rel_path)
        if not os.path.exists(full_path):
            return {"error": f"File '{rel_path}' not found."}

        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, start_idx + min(max_lines, 100))

            numbered_lines = [
                f"{i + 1}: {lines[i].rstrip()}"
                for i in range(start_idx, end_idx)
            ]

            return {
                "file": rel_path,
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "total_lines": total_lines,
                "has_more": end_idx < total_lines,
                "content": "\n".join(numbered_lines)
            }
        except Exception as e:
            return {"error": f"Failed to read file: {e}"}

    def search_class(self, class_name: str) -> List[Dict[str, Any]]:
        return self.symbol_mapper.search_class(class_name)

    def search_method(self, method_name: str) -> List[Dict[str, Any]]:
        return self.symbol_mapper.search_method(method_name)

    def apply_search_replace(
        self, 
        rel_path: str, 
        search_block: str, 
        replace_block: str
    ) -> Dict[str, Any]:
        """
        Applies a clean search-and-replace edit without regenerating entire files.
        Supports exact match as well as indentation-agnostic block alignment.
        """
        full_path = os.path.join(self.repo_root, rel_path)
        if not os.path.exists(full_path):
            return {"success": False, "error": f"File '{rel_path}' not found."}

        with open(full_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        normalized_search = search_block.strip("\r\n")
        normalized_replace = replace_block.strip("\r\n")

        # 1. Exact match
        if normalized_search in original_content:
            new_content = original_content.replace(normalized_search, normalized_replace, 1)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"success": True, "file": rel_path, "message": "Patch replacement applied successfully."}

        # 2. Indentation-agnostic sequence matching
        search_lines = [line.strip() for line in normalized_search.splitlines() if line.strip()]
        replace_lines = normalized_replace.splitlines()
        orig_lines = original_content.splitlines()

        match_start = -1
        for i in range(len(orig_lines) - len(search_lines) + 1):
            candidate_slice = [orig_lines[i + j].strip() for j in range(len(search_lines))]
            if candidate_slice == search_lines:
                match_start = i
                break

        if match_start != -1:
            matched_orig_line = orig_lines[match_start]
            base_indent = matched_orig_line[:len(matched_orig_line) - len(matched_orig_line.lstrip())]

            search_base_indent = ""
            for s_line in normalized_search.splitlines():
                if s_line.strip():
                    search_base_indent = s_line[:len(s_line) - len(s_line.lstrip())]
                    break

            adjusted_replace = []
            for r_line in replace_lines:
                if not r_line.strip():
                    adjusted_replace.append("")
                elif r_line.startswith(search_base_indent):
                    rel_indent = r_line[len(search_base_indent):]
                    adjusted_replace.append(base_indent + rel_indent)
                else:
                    adjusted_replace.append(base_indent + r_line.lstrip())

            new_orig_lines = orig_lines[:match_start] + adjusted_replace + orig_lines[match_start + len(search_lines):]
            new_content = "\n".join(new_orig_lines)
            if original_content.endswith("\n"):
                new_content += "\n"

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"success": True, "file": rel_path, "message": "Indentation-adjusted patch applied successfully."}

        return {
            "success": False, 
            "error": "Target search block was not found in file. Indentation or content mismatch."
        }

    def apply_unified_diff(self, patch_diff: str) -> Dict[str, Any]:
        """
        Parses and applies a standard unified diff block.
        """
        lines = patch_diff.strip().splitlines()
        target_file = None
        
        for line in lines:
            if line.startswith("--- ") or line.startswith("+++ "):
                parts = line.split()
                if len(parts) >= 2:
                    raw_file = parts[1].lstrip("a/").lstrip("b/")
                    if raw_file != "/dev/null":
                        target_file = raw_file
                        break

        if not target_file:
            return {"success": False, "error": "Could not identify target file from diff headers."}

        full_path = os.path.join(self.repo_root, target_file)
        if not os.path.exists(full_path):
            return {"success": False, "error": f"Target file '{target_file}' does not exist."}

        removals = []
        additions = []
        for line in lines:
            if line.startswith("-") and not line.startswith("---"):
                removals.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                additions.append(line[1:])

        if removals and additions:
            search_str = "\n".join(removals)
            replace_str = "\n".join(additions)
            return self.apply_search_replace(target_file, search_str, replace_str)

        return {"success": False, "error": "Invalid unified diff format."}
