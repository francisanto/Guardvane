"""
Negation and Anti-Pattern Detector for PromptShield AI.
Extracts declared feature negations, disabled security controls, and filters negated risks.
"""

from analyzers.security_controls_extractor import (
    NEGATION_TARGETS,
    NEGATION_CLAUSE_REGEX,
    extract_declared_negations,
    extract_feature_negations,
    filter_negated_risks,
)

NEGATION_PATTERNS = NEGATION_TARGETS

__all__ = [
    "NEGATION_TARGETS",
    "NEGATION_PATTERNS",
    "NEGATION_CLAUSE_REGEX",
    "extract_declared_negations",
    "extract_feature_negations",
    "filter_negated_risks",
]
