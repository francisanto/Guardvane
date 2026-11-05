"""
Prompt Templates Subpackage for PromptShield AI.
Includes Base Software Engineering, Educational, and Sandboxed Threat Modeling templates.
"""

from optimizer.templates.base_templates import (
    build_software_engineering_template,
    build_educational_template,
)
from optimizer.templates.threat_modeling import (
    build_sandboxed_adversarial_template,
)

__all__ = [
    "build_software_engineering_template",
    "build_educational_template",
    "build_sandboxed_adversarial_template",
]
