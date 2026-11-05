"""
Base Prompt Formatting Templates for Prompt Optimizer.
Provides structured layouts for standard software engineering,
feature implementation, and technical education prompts.
"""

from typing import List, Optional


def build_software_engineering_template(
    sanitized_content: str,
    user_clarification: Optional[str],
    detected_tech: List[str],
    security_constraints: List[str]
) -> str:
    """
    Renders structured software engineering prompt layout.
    """
    lines: List[str] = []
    lines.append("### Core Objective")
    if user_clarification:
        lines.append(f"{sanitized_content.strip()} — Objective: {user_clarification.strip()}")
    else:
        lines.append(f"{sanitized_content.strip()}")
    lines.append("")

    lines.append("### Implementation Requirements & Context")
    if detected_tech:
        lines.append(f"• Technology Context: {', '.join(detected_tech).title()}")
    lines.append("• Provide modular, production-ready code with type annotations and clean error handling.")
    lines.append("• Follow separation of concerns between business logic, data models, and API/interface controllers.")
    lines.append("• Include automated unit test cases covering happy path and boundary conditions.")
    lines.append("")

    if security_constraints:
        lines.append("### Security Guardrails & Hardening Constraints")
        for c in security_constraints:
            lines.append(c)
        lines.append("")

    lines.append("### Edge Cases & Input Validation")
    lines.append("• Validate all inputs (length, format, expected types) before processing.")
    lines.append("• Handle missing, invalid, or malformed data gracefully with structured error responses.")
    lines.append("")

    lines.append("### Expected Output Format")
    lines.append("• Complete, production-ready implementation with configuration setup, core modules, and unit test demonstrations.")

    return "\n".join(lines).strip()


def build_educational_template(
    sanitized_content: str,
    user_clarification: Optional[str]
) -> str:
    """
    Renders structured educational and conceptual prompt layout.
    """
    lines: List[str] = []
    lines.append("### Core Objective")
    lines.append(f"{sanitized_content}")
    if user_clarification:
        lines.append(f"Specific focus: {user_clarification.strip()}")
    lines.append("")
    lines.append("### Educational & Technical Requirements")
    lines.append("• Provide a clear, idiomatic implementation with comprehensive explanatory comments.")
    lines.append("• Include concrete step-by-step walkthrough of the underlying mechanism.")
    lines.append("• Explicitly analyze time and space complexity using Big-O notation for best, average, and worst-case scenarios.")
    lines.append("• Address common edge cases (e.g. empty inputs, duplicate elements, boundary values).")
    lines.append("")
    lines.append("### Expected Output Format")
    lines.append("• Clean, production-quality code block followed by structured conceptual explanation and complexity breakdown.")

    return "\n".join(lines).strip()
