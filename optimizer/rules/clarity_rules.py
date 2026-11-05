"""
Clarity and Specification Rules for Prompt Optimizer.
Ensures prompt objectives, technical constraints, and developer expectations
are unambiguous and actionable.
"""

from typing import List, Optional


def clarify_objective_and_assumptions(
    clean_prompt: str,
    user_clarification: Optional[str],
    detected_tech: List[str],
    is_educational: bool
) -> List[str]:
    """
    Formulates documented assumptions and clarity declarations.
    """
    assumptions: List[str] = []

    if user_clarification and user_clarification.strip():
        assumptions.append(f"Incorporated user clarification: '{user_clarification.strip()}'.")
    elif not detected_tech and not is_educational and len(clean_prompt.split()) < 10:
        assumptions.append("Preserved core request without inventing unstated tech stacks; standard production conventions assumed.")

    return assumptions
