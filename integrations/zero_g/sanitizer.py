"""
Sensitive Data Sanitizer for 0G Private Computer Integration.
Guarantees that raw credentials, passwords, private keys, and API tokens
are redacted prior to transmitting prompts or findings to external 0G inference nodes.

LIMITATIONS OF REGEX-BASED SANITIZATION:
1. Regex sanitization searches for structural syntax markers and entropy profiles of known formats
   (e.g., 'sk-ant-', 'ghp_', 'AKIA...', JWT headers, standard connection strings).
2. It CANNOT guarantee 100% recall of unknown, bespoke, or non-standard credential formats.
3. Obfuscated, base64-encoded, XOR-scrambled, or split tokens will not be recognized by regex without decoding.
4. Users and system architects must employ external secrets managers (e.g. HashiCorp Vault, AWS Secrets Manager)
   rather than relying solely on client-side regex redaction as a security boundary.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import re

from analyzers.sensitive_data_detector import PATTERNS


@dataclass
class SecretFindingMeta:
    """Metadata describing a detected secret without leaking any secret characters."""
    secret_type: str
    placeholder: str
    start_offset: int
    end_offset: int
    matched_length: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "secret_type": self.secret_type,
            "placeholder": self.placeholder,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "matched_length": self.matched_length,
        }


@dataclass
class SanitizedPromptResult:
    """Result of prompt sanitization prior to inference."""
    original_prompt: str
    sanitized_prompt: str
    secrets_detected: bool
    redacted_types: List[str] = field(default_factory=list)
    redacted_count: int = 0
    findings: List[SecretFindingMeta] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_prompt": self.original_prompt,
            "sanitized_prompt": self.sanitized_prompt,
            "secrets_detected": self.secrets_detected,
            "redacted_types": self.redacted_types,
            "redacted_count": self.redacted_count,
            "findings": [f.to_dict() for f in self.findings],
        }


# Mapping of pattern types to descriptive, safe redaction tokens
TYPE_TO_PLACEHOLDER: Dict[str, str] = {
    "openai_api_key": "[REDACTED_OPENAI_API_KEY]",
    "anthropic_api_key": "[REDACTED_ANTHROPIC_API_KEY]",
    "github_token": "[REDACTED_GITHUB_TOKEN]",
    "aws_access_key": "[REDACTED_AWS_ACCESS_KEY]",
    "jwt_token": "[REDACTED_JWT_TOKEN]",
    "private_key": "[REDACTED_PRIVATE_KEY]",
    "db_connection_uri": "[REDACTED_DATABASE_CONNECTION_URI]",
    "hardcoded_password_assignment": "[REDACTED_PASSWORD]",
}


def sanitize_prompt_for_inference(prompt: str) -> SanitizedPromptResult:
    """
    Scans a prompt for all recognized sensitive data patterns (API keys,
    passwords, tokens, database credentials, private keys) and redacts them
    prior to sending the prompt to 0G Private Computer inference.

    Returns:
        SanitizedPromptResult with sanitized prompt text and detection metadata.
    """
    if not prompt or not prompt.strip():
        return SanitizedPromptResult(
            original_prompt=prompt or "",
            sanitized_prompt=prompt or "",
            secrets_detected=False,
            redacted_types=[],
            redacted_count=0,
            findings=[],
        )

    seen_spans: List[Tuple[int, int]] = []
    replacements: List[Tuple[Tuple[int, int], str, str]] = []

    for pattern_def in PATTERNS:
        regex = pattern_def["regex"]
        ptype = pattern_def["type"]
        placeholder = TYPE_TO_PLACEHOLDER.get(ptype, "[REDACTED_SECRET]")

        for m in regex.finditer(prompt):
            if ptype == "hardcoded_password_assignment" and m.lastindex and m.lastindex >= 1:
                span = m.span(1)
            else:
                span = m.span(0)

            # Avoid overlapping replacements
            if any(max(span[0], s[0]) < min(span[1], s[1]) for s in seen_spans):
                continue

            seen_spans.append(span)
            replacements.append((span, placeholder, ptype))

    # Sort replacements by start offset in reverse order to preserve string slicing indices
    replacements.sort(key=lambda x: x[0][0], reverse=True)

    sanitized = prompt
    meta_findings: List[SecretFindingMeta] = []
    redacted_types: List[str] = []

    for (start, end), placeholder, ptype in replacements:
        sanitized = sanitized[:start] + placeholder + sanitized[end:]
        if ptype not in redacted_types:
            redacted_types.append(ptype)
        meta_findings.append(SecretFindingMeta(
            secret_type=ptype,
            placeholder=placeholder,
            start_offset=start,
            end_offset=end,
            matched_length=end - start,
        ))

    # Reverse meta_findings to maintain reading order (top-to-bottom)
    meta_findings.reverse()

    return SanitizedPromptResult(
        original_prompt=prompt,
        sanitized_prompt=sanitized,
        secrets_detected=len(replacements) > 0,
        redacted_types=redacted_types,
        redacted_count=len(replacements),
        findings=meta_findings,
    )


def sanitize_context_data(data: Any) -> Any:
    """
    Recursively scrubs sensitive secret strings from empirical findings,
    recommendations, and dictionaries before embedding them into 0G payloads.
    """
    if isinstance(data, str):
        return sanitize_prompt_for_inference(data).sanitized_prompt
    if isinstance(data, list):
        return [sanitize_context_data(item) for item in data]
    if isinstance(data, dict):
        return {k: sanitize_context_data(v) for k, v in data.items()}
    return data
