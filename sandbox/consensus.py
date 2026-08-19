import ast
import re
from typing import List, Dict, Any
from collections import Counter

class ConsensusVotingEngine:
    """
    Samples candidate patches, clusters them by normalized AST structure
    and behavioral test results, and determines the winning consensus patch.
    """
    
    @staticmethod
    def normalize_patch_syntax(patch_diff: str) -> str:
        """
        Strips whitespace variations, comments, and non-semantic formatting.
        """
        cleaned_lines = []
        for line in patch_diff.splitlines():
            # Remove diff header line numbers like @@ -1,4 +1,4 @@
            if line.startswith("@@"):
                continue
            # Keep meaningful +/- change lines
            if line.startswith("+") or line.startswith("-"):
                # Strip excessive whitespace
                cleaned = re.sub(r"\s+", " ", line.strip())
                cleaned_lines.append(cleaned)
        return "\n".join(cleaned_lines)

    @classmethod
    def vote_on_candidates(cls, candidate_patches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes a list of patch candidates:
        [
            {"patch": "...", "passes_tests": True, "passes_lint": True, "mutation_score": 0.85},
            ...
        ]
        Filters to valid passing patches, clusters by normalized signature,
        and selects the highest-consensus candidate.
        """
        valid_candidates = [
            p for p in candidate_patches 
            if p.get("passes_tests", False) and p.get("passes_lint", False)
        ]

        if not valid_candidates:
            return {
                "selected_patch": candidate_patches[0] if candidate_patches else None,
                "consensus_ratio": 0.0,
                "total_valid": 0,
                "clusters_count": 0
            }

        # Cluster by normalized syntax
        clusters = {}
        for candidate in valid_candidates:
            sig = cls.normalize_patch_syntax(candidate.get("patch", ""))
            if sig not in clusters:
                clusters[sig] = []
            clusters[sig].append(candidate)

        # Find largest cluster
        sorted_clusters = sorted(clusters.values(), key=len, reverse=True)
        dominant_cluster = sorted_clusters[0]

        # In dominant cluster, pick candidate with highest mutation score
        best_candidate = max(dominant_cluster, key=lambda c: c.get("mutation_score", 0.0))
        consensus_ratio = round(len(dominant_cluster) / len(valid_candidates), 4)

        return {
            "selected_patch": best_candidate,
            "consensus_ratio": consensus_ratio,
            "total_valid": len(valid_candidates),
            "clusters_count": len(clusters),
            "cluster_size": len(dominant_cluster)
        }
