"""
Arkiv Schemas and Pydantic Models for Guardvane.
Defines data structures matching the 5 official Arkiv schemas on Rabdi Testnet:
1. guardvane.specialists.v1 (Specialist Profiles)
2. guardvane.services.v1 (Service Listings)
3. guardvane.tasks.v1 (Security Tasks)
4. guardvane.bids.v1 (Specialist Bids)
5. guardvane.awards.v1 (Award Records)
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ArkivSyncStatus(BaseModel):
    """Status of Rabdi testnet connection and node synchronization."""
    is_connected: bool = False
    chain_id: int = 7794095
    network: str = "Rabdi Testnet"
    currency: str = "tGLM"
    rpc_url: str = "https://rpc.rabdi.db-chain.testnet.arkiv.network"
    explorer_url: str = "https://explorer.rabdi.db-chain.testnet.arkiv.network"
    current_block: Optional[int] = None
    last_sync_timestamp: Optional[str] = None
    mode: str = "live_public_client"
    notice: str = "Connected to Rabdi Testnet via @arkiv-network/sdk."
    error: Optional[str] = None


class ArkivSpecialistProfile(BaseModel):
    """Schema: guardvane.specialists.v1"""
    entity_key: Optional[str] = None
    owner: Optional[str] = None
    wallet_address: str
    display_name: str
    headline: Optional[str] = ""
    expertise_categories: str = "ai_security"
    skills: str = ""
    experience_level: str = "senior"
    availability_status: str = "available"
    profile_version: str = "1.0.0"
    created_at_block: Optional[int] = None
    expires_at: Optional[int] = None


class ArkivServiceListing(BaseModel):
    """Schema: guardvane.services.v1"""
    entity_key: Optional[str] = None
    owner: Optional[str] = None
    provider_wallet: str
    service_category: str
    title: str
    short_description: str
    pricing_type: str = "fixed"
    indicative_price: float = 10.0
    availability: str = "available"
    service_version: str = "1.0.0"
    created_at_block: Optional[int] = None
    expires_at: Optional[int] = None


class ArkivSecurityTask(BaseModel):
    """Schema: guardvane.tasks.v1"""
    entity_key: Optional[str] = None
    owner: Optional[str] = None
    task_id: str
    customer_wallet: str
    category: str
    title: str
    public_description: str
    required_skills: str = ""
    budget_type: str = "fixed"
    budget_range: str = "50-100 tGLM"
    status: str = "open"
    created_at: str
    deadline: str = ""
    task_version: str = "1.0.0"
    bids_count: Optional[int] = 0
    created_at_block: Optional[int] = None
    expires_at: Optional[int] = None


class ArkivSpecialistBid(BaseModel):
    """Schema: guardvane.bids.v1"""
    entity_key: Optional[str] = None
    owner: Optional[str] = None
    task_id: str
    specialist_wallet: str
    proposed_price: float
    estimated_duration: str = "3 days"
    proposal_summary: str = ""
    status: str = "submitted"
    created_at: str
    bid_version: str = "1.0.0"
    created_at_block: Optional[int] = None
    expires_at: Optional[int] = None


class ArkivAwardRecord(BaseModel):
    """Schema: guardvane.awards.v1"""
    entity_key: Optional[str] = None
    owner: Optional[str] = None
    task_id: str
    accepted_bid_key: str
    customer_wallet: str
    specialist_wallet: str
    award_status: str = "awarded"
    created_at: str
    created_at_block: Optional[int] = None
    expires_at: Optional[int] = None


# ---------------------------------------------------------------------------
# Reconcile Requests from Frontend (Transmitted After MetaMask Confirmation)
# ---------------------------------------------------------------------------

class ReconcileTaskRequest(BaseModel):
    task_id: str
    entity_key: str
    tx_hash: str
    title: str
    category: str
    public_description: str
    required_skills: Optional[str] = ""
    budget_range: Optional[str] = ""
    customer_wallet: str


class ReconcileBidRequest(BaseModel):
    task_id: str
    entity_key: str
    tx_hash: str
    proposed_price: float
    estimated_duration: str
    proposal_summary: str
    specialist_wallet: str


class ReconcileAwardRequest(BaseModel):
    task_id: str
    entity_key: str
    tx_hash: str
    accepted_bid_key: str
    customer_wallet: str
    specialist_wallet: str
