"""
Arkiv Integration Package for Guardvane / PromptShield Marketplace.
Provides decentralized provider discovery and verifiable marketplace registry records
on Rabdi Testnet (Chain ID 7794095).
"""

from integrations.arkiv.schemas import (
    ArkivSyncStatus,
    ArkivSpecialistProfile,
    ArkivServiceListing,
    ArkivSecurityTask,
    ArkivSpecialistBid,
    ArkivAwardRecord,
    ReconcileTaskRequest,
    ReconcileBidRequest,
    ReconcileAwardRequest,
)
from integrations.arkiv.client import ArkivClient, arkiv_client

# Backward compatibility alias
ArkivRecord = ArkivSecurityTask

__all__ = [
    "ArkivSyncStatus",
    "ArkivSpecialistProfile",
    "ArkivServiceListing",
    "ArkivSecurityTask",
    "ArkivSpecialistBid",
    "ArkivAwardRecord",
    "ReconcileTaskRequest",
    "ReconcileBidRequest",
    "ReconcileAwardRequest",
    "ArkivRecord",
    "ArkivClient",
    "arkiv_client",
]
