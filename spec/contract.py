from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SpecificationContract:
    """
    Formal contract capturing target symbols, preconditions,
    postconditions, property invariants, and complexity limits.
    """
    issue_id: str
    target_symbols: List[str]
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    property_invariants: List[Dict[str, Any]] = field(default_factory=list)
    complexity_cap: int = 15
    minimal_diff_mandate: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "target_symbols": self.target_symbols,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "property_invariants": self.property_invariants,
            "complexity_cap": self.complexity_cap,
            "minimal_diff_mandate": self.minimal_diff_mandate
        }

class SpecificationEngine:
    """
    Synthesizes structured specification contracts from natural language issues.
    """
    @classmethod
    def synthesize_spec(cls, issue_payload: Dict[str, Any]) -> SpecificationContract:
        issue_id = issue_payload.get("issue_id", "issue-001")
        issue = issue_payload.get("issue", {})
        title = issue.get("title", "")
        desc = issue.get("description", "")

        # Extract target symbols based on keywords
        target_symbols = []
        if "ModelChoiceField" in title or "ModelChoiceField" in desc:
            target_symbols.append("ModelChoiceField.to_python")
        else:
            target_symbols.append("resolve_bounds")

        preconditions = ["input_value is not None", "valid_type_contract"]
        postconditions = ["preserves_exception_params", "zero_side_effects"]
        invariants = [{"type": "no_public_signature_break", "status": "enforced"}]

        return SpecificationContract(
            issue_id=issue_id,
            target_symbols=target_symbols,
            preconditions=preconditions,
            postconditions=postconditions,
            property_invariants=invariants,
            complexity_cap=15,
            minimal_diff_mandate=True
        )
