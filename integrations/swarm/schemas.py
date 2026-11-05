"""
Swarm Integration Schemas for PromptShield Marketplace.
Defines data structures for decentralized storage of AI security reports on Ethereum Swarm.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SwarmReportMetadata(BaseModel):
    """
    Metadata associated with a security audit report stored on Swarm.
    """
    report_id: str = Field(..., description="PromptShield report ID")
    order_id: str = Field(..., description="Associated marketplace order ID")
    customer_id: str = Field(..., description="Customer who requested the review")
    provider_id: str = Field(..., description="Provider who authored or executed the review")
    service_id: str = Field(..., description="Associated marketplace service ID")
    created_at: str = Field(..., description="Timestamp of report creation")
    content_hash: str = Field(..., description="SHA-256 digest of unencrypted report payload")
    is_encrypted: bool = Field(default=True, description="Whether report payload is client-side encrypted")
    content_type: str = Field(default="application/json", description="MIME type of report")


class SwarmUploadResult(BaseModel):
    """
    Result returned after uploading report to Swarm.
    """
    success: bool = True
    reference: str = Field(..., description="Swarm reference hash (e.g. bzz://<reference>)")
    raw_hash: str = Field(..., description="Hex representation of Swarm chunk address")
    size_bytes: int = Field(..., description="Size of uploaded data")
    pinned: bool = Field(default=False, description="Whether data is pinned to a Swarm node")
    storage_batch_id: Optional[str] = Field(default=None, description="Postage stamp batch ID")
    timestamp: str = Field(..., description="Upload timestamp")


class SwarmStatus(BaseModel):
    """
    Connection status to Swarm gateway/node.
    """
    is_connected: bool = False
    gateway_url: Optional[str] = None
    postage_batch_configured: bool = False
    mode: str = "mock_interface"
    notice: str = "Swarm Phase 1 interface initialized. Reports stored with simulated bzz:// references."

