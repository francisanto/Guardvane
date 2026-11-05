"""
Security Requirements Analyzer Subpackage for PromptShield AI.
Extracts declared architectural controls, defensive specifications,
and anti-pattern negations.
"""

from analyzers.security_controls_extractor import (
    CONTROL_PATTERNS,
    NEGATION_CLAUSE_REGEX,
    NEGATION_TARGETS,
    extract_declared_negations,
    extract_declared_security_controls,
    extract_feature_negations,
    extract_security_controls,
    filter_negated_risks,
)

NEGATION_PATTERNS = NEGATION_TARGETS

__all__ = [
    "CONTROL_PATTERNS",
    "NEGATION_TARGETS",
    "NEGATION_PATTERNS",
    "NEGATION_CLAUSE_REGEX",
    "extract_security_controls",
    "extract_declared_security_controls",
    "extract_declared_negations",
    "extract_feature_negations",
    "filter_negated_risks",
]
