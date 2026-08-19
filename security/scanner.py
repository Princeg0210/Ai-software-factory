import re
import ast
from typing import Dict, Any, List

class SecurityScanner:
    """
    Static Application Security Testing (SAST) Scanner for AI Software Factory.
    Audits candidate patches for hardcoded secrets, dangerous built-ins,
    RCE execution vulnerabilities, and unsafe deserialization.
    """
    
    SECRET_PATTERNS = [
        re.compile(r'(?i)(api[_-]?key|secret|password|auth[_-]?token|bearer)\s*=\s*["\'][a-zA-Z0-9_\-]{8,}["\']'),
        re.compile(r'(?i)AKIA[0-9A-Z]{16}'), # AWS Access Key
        re.compile(r'(?i)ghp_[a-zA-Z0-9]{36}'), # GitHub Personal Access Token
    ]

    DANGEROUS_CALLS = [
        "eval",
        "exec",
        "pickle.loads",
        "yaml.unsafe_load",
        "os.system"
    ]

    @classmethod
    def scan_patch(cls, patch_diff: str, file_content: str = "") -> Dict[str, Any]:
        findings = []

        # 1. Check for leaked credentials/secrets
        for pattern in cls.SECRET_PATTERNS:
            if pattern.search(patch_diff):
                findings.append({
                    "type": "SECRET_LEAK",
                    "severity": "CRITICAL",
                    "message": "Potential hardcoded secret or API key detected in candidate patch."
                })

        # 2. Check for dangerous calls in added lines
        for line in patch_diff.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                for dangerous in cls.DANGEROUS_CALLS:
                    if dangerous in line:
                        findings.append({
                            "type": "INSECURE_EXECUTION",
                            "severity": "HIGH",
                            "message": f"Dangerous call '{dangerous}' detected in added code."
                        })
                if "shell=True" in line:
                    findings.append({
                        "type": "RCE_RISK",
                        "severity": "HIGH",
                        "message": "subprocess execution with shell=True detected."
                    })

        is_clean = len(findings) == 0
        return {
            "passed_security": is_clean,
            "findings_count": len(findings),
            "findings": findings,
            "severity_score": 0.0 if is_clean else max(
                1.0 if f["severity"] == "CRITICAL" else 0.5 for f in findings
            )
        }
