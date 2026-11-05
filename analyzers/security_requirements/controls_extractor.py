"""
Security Controls Extractor Module for PromptShield AI.
Extracts explicitly declared security controls and defensive measures.
"""

from analyzers.security_controls_extractor import (
    CONTROL_PATTERNS,
    extract_security_controls,
    extract_declared_security_controls,
)

__all__ = [
    "CONTROL_PATTERNS",
    "extract_security_controls",
    "extract_declared_security_controls",
]
