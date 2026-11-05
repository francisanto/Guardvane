"""
Hedera x402 Payment Integration Schemas for PromptShield Marketplace.
Defines schemas for autonomous agent payments, micro-invoices, and settlement.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class X402PaymentRequest(BaseModel):
    """
    HTTP 402 Payment Required challenge payload for automated AI service execution.
    """
    service_id: str = Field(..., description="Target service identifier")
    provider_id: str = Field(..., description="Target provider identifier")
    order_id: str = Field(..., description="Marketplace order reference")
    amount_hbars: float = Field(..., description="Payment price in HBAR")
    amount_usd: float = Field(..., description="USD equivalent for reference")
    recipient_account_id: str = Field(..., description="Hedera Account ID of recipient (e.g. 0.0.12345)")
    memo: str = Field(..., description="Transaction memo identifier")
    payment_channel: str = Field(default="hedera_testnet", description="Settlement network")
    challenge_nonce: str = Field(..., description="One-time nonce for anti-replay verification")
    expires_at: str = Field(..., description="Challenge expiration timestamp")


class X402PaymentReceipt(BaseModel):
    """
    Cryptographic payment proof submitted by autonomous client or customer.
    """
    order_id: str
    tx_id: str = Field(..., description="Hedera transaction ID (e.g. 0.0.12345@1700000000.000000000)")
    payer_account_id: str = Field(..., description="Hedera Account ID of payer")
    amount_hbars: float
    status: str = Field(default="settled", description="Payment status: pending, escrowed, settled, refunded")
    consensus_timestamp: str
    is_mock: bool = Field(default=True, description="Indicates simulation status in Phase 1")


class HederaStatus(BaseModel):
    """
    Hedera network integration status.
    """
    is_connected: bool = False
    network: str = "testnet-simulated"
    operator_account_id: Optional[str] = None
    x402_protocol_version: str = "v0.2.0"
    mode: str = "mock_interface"
    notice: str = "Hedera x402 Phase 1 interface initialized. Live HBAR transfers disabled."
