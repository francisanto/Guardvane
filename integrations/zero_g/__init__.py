"""
0G Private Computer Integration for PromptShield AI.
Provides confidential, decentralized AI reasoning and prompt optimization.
"""

from integrations.zero_g.client import (
    ZeroGClient,
    ZeroGResponse,
    ZeroGError,
    ZeroGConfigurationError,
    ZeroGAuthenticationError,
    ZeroGConnectionError,
    ZeroGTimeoutError,
    ZeroGAPIError,
)
from integrations.zero_g.reasoning import (
    ZeroGReasoningEngine,
    ZeroGReasoningResult,
)
from integrations.zero_g.optimization import (
    ZeroGOptimizer,
    ZeroGOptimizationResult,
    zero_g_optimizer,
)
from integrations.zero_g.sanitizer import (
    sanitize_prompt_for_inference,
    SanitizedPromptResult,
)

__all__ = [
    "ZeroGClient",
    "ZeroGResponse",
    "ZeroGError",
    "ZeroGConfigurationError",
    "ZeroGAuthenticationError",
    "ZeroGConnectionError",
    "ZeroGTimeoutError",
    "ZeroGAPIError",
    "ZeroGReasoningEngine",
    "ZeroGReasoningResult",
    "ZeroGOptimizer",
    "ZeroGOptimizationResult",
    "zero_g_optimizer",
    "sanitize_prompt_for_inference",
    "SanitizedPromptResult",
]
