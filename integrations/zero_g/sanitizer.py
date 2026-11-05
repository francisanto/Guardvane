"""
Sensitive Data Sanitizer for 0G Private Computer Integration.
Guarantees that raw credentials, passwords, private keys, and API tokens
are never transmitted over the wire to external inference nodes.
"""

from dataclasses import dataclass, field
from typing import List, Tuple
import re

from analyzers.sensitive_data_detector import PATTERNS, redact_secret


@dataclass
class SanitizedPromptResult:
    """Result of prompt sanitization prior to inference."""
    original_prompt: str
    sanitized_prompt: str
    secrets_detected: bool
    redacted_types: List[str] = field(default_factory=list)
    redacted_count: int = 0


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
            redacted_count=0
        )

    masked = prompt
    redacted_types: List[str] = []
    seen_spans: List[Tuple[int, int]] = []
    replacements: List[Tuple[Tuple[int, int], str, str]] = []

    # Map pattern types to descriptive, safe redaction tokens
    type_to_placeholder = {
        "openai_api_key": "[REDACTED_OPENAI_API_KEY]",
        "anthropic_api_key": "[REDACTED_ANTHROPIC_API_KEY]",
        "github_token": "[REDACTED_GITHUB_TOKEN]",
        "aws_access_key": "[REDACTED_AWS_ACCESS_KEY]",
        "jwt_token": "[REDACTED_JWT_TOKEN]",
        "private_key": "[REDACTED_PRIVATE_KEY]",
        "db_connection_uri": "[REDACTED_DATABASE_CONNECTION_URI]",
        "hardcoded_password_assignment": "[REDACTED_PASSWORD]"
    }

    for pattern_def in PATTERNS:
        regex = pattern_def["regex"]
        ptype = pattern_def["type"]
        placeholder = type_to_placeholder.get(ptype, "[REDACTED_SECRET]")

        for m in regex.finditer(masked):
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
    for (start, end), placeholder, ptype in replacements:
        sanitized = sanitized[:start] + placeholder + sanitized[end:]
        if ptype not in redacted_types:
            redacted_types.append(ptype)

    return SanitizedPromptResult(
        original_prompt=prompt,
        sanitized_prompt=sanitized,
        secrets_detected=len(replacements) > 0,
        redacted_types=redacted_types,
        redacted_count=len(replacements)
    )
