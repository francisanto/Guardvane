"""
PromptShield AI — Integrations Package.
Third-party and decentralized infrastructure integrations.

- Arkiv: Decentralized provider discovery and marketplace listings
- Zero_G: Confidential AI reasoning and prompt optimization
"""

from integrations.arkiv.client import arkiv_client, ArkivClient
from integrations.zero_g.client import ZeroGClient
from integrations.zero_g.optimization import zero_g_optimizer, ZeroGOptimizer

__all__ = [
    "arkiv_client",
    "ArkivClient",
    "zero_g_optimizer",
    "ZeroGClient",
    "ZeroGOptimizer",
]
