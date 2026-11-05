"""
PromptShield AI — Deterministic Prompt Optimizer Package.
Transforms raw application prompts into structured, hardened, production-ready specifications.
"""

from analyzers.prompt_optimizer import (
    OptimizationResult,
    LocalPromptOptimizer,
    prompt_optimizer,
)
from optimizer.rules import (
    generate_security_constraints,
    clarify_objective_and_assumptions,
    prune_filler_phrases,
)
from optimizer.templates import (
    build_software_engineering_template,
    build_educational_template,
    build_sandboxed_adversarial_template,
)

__all__ = [
    "OptimizationResult",
    "LocalPromptOptimizer",
    "prompt_optimizer",
    "generate_security_constraints",
    "clarify_objective_and_assumptions",
    "prune_filler_phrases",
    "build_software_engineering_template",
    "build_educational_template",
    "build_sandboxed_adversarial_template",
]
