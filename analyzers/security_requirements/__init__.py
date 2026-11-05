"""
Security Requirements Analyzer Subpackage for PromptShield AI.
Extracts declared architectural controls, defensive specifications,
and anti-pattern negations.
"""

from analyzers.security_requirements.controls_extractor import (
    CONTROL_PATTERNS,
    extract_security_controls,
    extract_declared_security_controls,
)
from analyzers.security_requirements.negation_detector import (
    NEGATION_TARGETS,
    NEGATION_PATTERNS,
    NEGATION_CLAUSE_REGEX,
    extract_declared_negations,
    extract_feature_negations,
    filter_negated_risks,
)

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
