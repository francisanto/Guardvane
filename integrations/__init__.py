"""
PromptShield AI — Integrations Package.
Third-party and decentralized infrastructure integrations.

- Arkiv: Decentralized provider discovery and marketplace listings
- Zero_G: Confidential AI reasoning and prompt optimization
- Swarm: Decentralized, content-addressed security report storage
- Hedera: x402 autonomous machine-to-machine micropayments
"""

from integrations.arkiv.client import arkiv_client, ArkivClient
from integrations.swarm.client import swarm_client, SwarmClient
from integrations.hedera.client import hedera_client, HederaX402Client
from integrations.zero_g.client import ZeroGClient
from integrations.zero_g.optimization import zero_g_optimizer, ZeroGOptimizer

__all__ = [
    "arkiv_client",
    "ArkivClient",
    "swarm_client",
    "SwarmClient",
    "hedera_client",
    "HederaX402Client",
    "zero_g_optimizer",
    "ZeroGClient",
    "ZeroGOptimizer",
]
