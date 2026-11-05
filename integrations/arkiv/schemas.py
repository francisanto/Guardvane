"""
Arkiv Integration Schemas for PromptShield Marketplace.
Defines schemas for decentralized provider discovery and immutable marketplace registry records.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ArkivRecordType(str):
    PROVIDER_REGISTRATION = "provider_registration"
    SERVICE_LISTING = "service_listing"
    ORDER_ATTESTATION = "order_attestation"
    SECURITY_AUDIT_MANIFEST = "security_audit_manifest"


class ArkivRecord(BaseModel):
    """
    Decentralized immutable record schema for Arkiv publication.
    """
    record_id: str = Field(..., description="Unique record identifier or content hash")
    record_type: str = Field(..., description="Record classification on Arkiv network")
    entity_id: str = Field(..., description="Provider, Service, or Order ID associated with record")
    version: str = Field(default="1.0.0", description="Schema version")
    payload: Dict[str, Any] = Field(..., description="Structured payload containing verified entity attributes")
    publisher_wallet: Optional[str] = Field(default=None, description="Public wallet address of publishing authority")
    signature: Optional[str] = Field(default=None, description="Cryptographic signature of payload")
    timestamp: str = Field(..., description="ISO 8601 creation timestamp")
    arkiv_tx_hash: Optional[str] = Field(default=None, description="Arkiv decentralized storage receipt / tx hash")
    verified: bool = Field(default=False, description="Verification status on Arkiv network")


class ArkivQueryFilter(BaseModel):
    """
    Filter parameters for decentralized discovery queries on Arkiv.
    """
    record_type: Optional[str] = None
    category: Optional[str] = None
    provider_type: Optional[str] = None
    min_reputation: Optional[float] = None
    limit: int = 50
    offset: int = 0


class ArkivSyncStatus(BaseModel):
    """
    Status of local-to-Arkiv synchronization.
    """
    is_connected: bool = False
    endpoint: Optional[str] = None
    network: str = "testnet-simulated"
    synced_records_count: int = 0
    last_sync_timestamp: Optional[str] = None
    mode: str = "mock_interface"
    notice: str = "Arkiv Phase 1 interface initialized. Live blockchain transactions disabled."
