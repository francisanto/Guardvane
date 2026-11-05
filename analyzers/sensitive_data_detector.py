"""
Sensitive Data Detector Module for PromptShield AI.
Provides conservative, rule-based detection for obvious API keys,
passwords, access tokens, private keys, and credential strings.

Note: Rule-based heuristic pattern matching does not guarantee complete
detection of all sensitive information. It is intended as an initial safeguard
layer separate from machine-learning classifiers.
"""

import re
from typing import Any, Dict, List


PATTERNS: List[Dict[str, Any]] = [
    {
        "type": "openai_api_key",
        "description": "OpenAI API Key format",
        "regex": re.compile(r"\b(sk-[a-zA-Z0-9_-]{20,})\b"),
    },
    {
        "type": "anthropic_api_key",
        "description": "Anthropic API Key format",
        "regex": re.compile(r"\b(sk-ant-[a-zA-Z0-9_-]{20,})\b"),
    },
    {
        "type": "github_token",
        "description": "GitHub Personal Access Token format",
        "regex": re.compile(r"\b(ghp_[a-zA-Z0-9]{20,}|github_pat_[a-zA-Z0-9_]{20,})\b"),
    },
    {
        "type": "aws_access_key",
        "description": "AWS Access Key ID format",
        "regex": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    },
    {
        "type": "jwt_token",
        "description": "JSON Web Token (JWT) format",
        "regex": re.compile(r"\b(ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"),
    },
    {
        "type": "private_key",
        "description": "Private Encryption / SSH Key Header",
        "regex": re.compile(r"(-----BEGIN\s+[A-Z\s]+PRIVATE\s+KEY-----)"),
    },
    {
        "type": "db_connection_uri",
        "description": "Database Connection String with Credentials",
        "regex": re.compile(r"((?:postgres|postgresql|mysql|mongodb|redis):\/\/[^:\s]+:([^@\s]+)@[^\s]+)"),
    },
    {
        "type": "hardcoded_password_assignment",
        "description": "Hardcoded Password / Secret Assignment",
        "regex": re.compile(
            r"""(?i)\b(?:password|passwd|pwd|api_key|apikey|secret_key|client_secret)\s*[:=]\s*["']([^"'\s]{6,})["']"""
        ),
    },
]


def redact_secret(secret: str) -> str:
    """
    Safely redacts a sensitive string showing only partial prefix/suffix.
    """
    secret = secret.strip()
    if len(secret) <= 8:
        return "[REDACTED]"
    prefix_len = min(4, len(secret) // 4)
    suffix_len = min(3, len(secret) // 4)
    return f"{secret[:prefix_len]}...{secret[-suffix_len:]}"


def detect_sensitive_data(prompt: str) -> Dict[str, Any]:
    """
    Scans a prompt for common sensitive credential patterns.

    Returns:
        dict:
            - detected (bool): True if at least one sensitive pattern was found.
            - findings_count (int): Number of detected findings.
            - findings (list): List of finding objects with 'type', 'description', and 'redacted'.
            - disclaimer (str): Explanatory note on limitations of regex-based detection.
    """
    if not prompt or not prompt.strip():
        return {
            "detected": False,
            "findings_count": 0,
            "findings": [],
            "disclaimer": "Rule-based heuristic detector; regex alone cannot detect all sensitive data."
        }

    findings: List[Dict[str, str]] = []
    seen_matches = set()

    for pattern_def in PATTERNS:
        matches = pattern_def["regex"].findall(prompt)
        for match in matches:
            # Handle tuple matches from multi-group regex
            matched_str = match[0] if isinstance(match, tuple) else match
            matched_str = matched_str.strip()
            if matched_str and matched_str not in seen_matches:
                seen_matches.add(matched_str)
                findings.append({
                    "type": pattern_def["type"],
                    "description": pattern_def["description"],
                    "redacted": redact_secret(matched_str)
                })

    return {
        "detected": len(findings) > 0,
        "findings_count": len(findings),
        "findings": findings,
        "disclaimer": "Rule-based heuristic detector; regex alone cannot detect all sensitive data."
    }
