"""
Prompt Intent & Conversational Directive Analyzer.
Identifies user prompt communicative intent, interaction modality,
and expected response formatting constraints.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class PromptIntentType(str, Enum):
    GENERATION = "generation"
    ANALYSIS_AUDIT = "analysis_audit"
    INFORMATIONAL_QUERY = "informational_query"
    REFACTORING = "refactoring"
    ADVERSARIAL_PROBE = "adversarial_probe"
    GENERAL_INSTRUCTION = "general_instruction"


@dataclass
class IntentAnalysisResult:
    intent_type: PromptIntentType
    confidence: float
    is_interactive: bool
    requires_code_generation: bool
    requires_security_scrutiny: bool
    detected_modalities: List[str]
    formatting_expectation: str


class IntentAnalyzer:
    """
    Offline heuristic analyzer classifying user prompt intent and directives.
    """

    AUDIT_REGEX = re.compile(
        r"\b(audit|review|threat model|pentest|analyze (?:vulnerabilit|security|weakness)|find bugs?)\b",
        re.IGNORECASE
    )
    REFACTOR_REGEX = re.compile(
        r"\b(refactor|optimize|clean up|rewrite|improve performance|reorganize)\b",
        re.IGNORECASE
    )
    QUERY_REGEX = re.compile(
        r"^(what|why|how|when|where|explain|describe|difference between)\b",
        re.IGNORECASE
    )
    GENERATION_REGEX = re.compile(
        r"\b(build|create|implement|write|develop|generate|scaffold|construct)\b",
        re.IGNORECASE
    )
    ADVERSARIAL_REGEX = re.compile(
        r"\b(ignore (?:all )?previous|jailbreak|unfiltered|dan mode|hypothetical scenario bypass)\b",
        re.IGNORECASE
    )

    def analyze_intent(self, prompt: str) -> IntentAnalysisResult:
        if not isinstance(prompt, str) or not prompt.strip():
            return IntentAnalysisResult(
                intent_type=PromptIntentType.GENERAL_INSTRUCTION,
                confidence=0.5,
                is_interactive=False,
                requires_code_generation=False,
                requires_security_scrutiny=False,
                detected_modalities=["empty"],
                formatting_expectation="general_text"
            )

        text = prompt.strip()
        modalities = []

        if self.ADVERSARIAL_REGEX.search(text):
            return IntentAnalysisResult(
                intent_type=PromptIntentType.ADVERSARIAL_PROBE,
                confidence=0.95,
                is_interactive=True,
                requires_code_generation=False,
                requires_security_scrutiny=True,
                detected_modalities=["adversarial", "probe"],
                formatting_expectation="security_quarantine"
            )

        if self.AUDIT_REGEX.search(text):
            intent = PromptIntentType.ANALYSIS_AUDIT
            confidence = 0.90
            modalities.append("audit")
        elif self.REFACTOR_REGEX.search(text):
            intent = PromptIntentType.REFACTORING
            confidence = 0.85
            modalities.append("refactoring")
        elif self.GENERATION_REGEX.search(text):
            intent = PromptIntentType.GENERATION
            confidence = 0.88
            modalities.append("implementation")
        elif self.QUERY_REGEX.search(text):
            intent = PromptIntentType.INFORMATIONAL_QUERY
            confidence = 0.82
            modalities.append("q_and_a")
        else:
            intent = PromptIntentType.GENERAL_INSTRUCTION
            confidence = 0.70
            modalities.append("instruction")

        needs_code = any(k in text.lower() for k in ["code", "function", "api", "script", "endpoint", "class", "react", "python"])
        needs_sec = any(k in text.lower() for k in ["security", "auth", "token", "password", "sql", "exploit", "audit", "secret"])

        return IntentAnalysisResult(
            intent_type=intent,
            confidence=confidence,
            is_interactive=False,
            requires_code_generation=needs_code,
            requires_security_scrutiny=needs_sec,
            detected_modalities=modalities,
            formatting_expectation="code_and_explanation" if needs_code else "structured_response"
        )


intent_analyzer = IntentAnalyzer()
