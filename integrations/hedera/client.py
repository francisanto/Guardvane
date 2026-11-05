"""
Hedera x402 Autonomous Payment Client for PromptShield Marketplace.
Provides clean interface boundaries for machine-to-machine micropayments,
autonomous service invocation, and payment settlement on Hedera.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from integrations.hedera.schemas import (
    HederaStatus,
    X402PaymentReceipt,
    X402PaymentRequest,
)

logger = logging.getLogger("promptshield.integrations.hedera")


class HederaX402Client:
    """
    Hedera Hashgraph x402 payment protocol client.

    Phase 1 implementation provides mock escrow, autonomous invoice generation,
    and payment challenge handling without requiring actual HBAR gas fees
    or real private key signatures.
    """

    def __init__(
        self,
        operator_account_id: Optional[str] = None,
        operator_private_key: Optional[str] = None,
        network: str = "testnet-simulated"
    ):
        self._operator_account_id = operator_account_id or "0.0.4829103"
        self._operator_private_key = operator_private_key
        self._network = network
        self._invoices: Dict[str, X402PaymentRequest] = {}
        self._receipts: Dict[str, X402PaymentReceipt] = {}
        logger.info(f"HederaX402Client initialized in {network} simulation mode.")

    def get_status(self) -> HederaStatus:
        """
        Returns Hedera network and x402 client configuration status.
        """
        return HederaStatus(
            is_connected=False,
            network=self._network,
            operator_account_id=self._operator_account_id,
            x402_protocol_version="v0.2.0",
            mode="mock_interface",
            notice="Phase 1 architecture ready. Live HBAR transfers disabled."
        )

    def create_payment_request(
        self,
        order_id: str,
        service_id: str,
        provider_id: str,
        amount_usd: float,
        recipient_account_id: Optional[str] = None
    ) -> X402PaymentRequest:
        """
        Generates an HTTP 402 Payment Required challenge payload for automated AI execution.
        Assumes fixed mock conversion rate 1 USD = 20 HBAR for testnet demonstration.
        """
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(minutes=15)).isoformat()
        amount_hbars = round(amount_usd * 20.0, 4)
        nonce = secrets.token_hex(16)
        recipient = recipient_account_id or "0.0.5182910"

        req = X402PaymentRequest(
            service_id=service_id,
            provider_id=provider_id,
            order_id=order_id,
            amount_hbars=amount_hbars,
            amount_usd=amount_usd,
            recipient_account_id=recipient,
            memo=f"PromptShield-Order:{order_id}",
            payment_channel=self._network,
            challenge_nonce=nonce,
            expires_at=expires_at
        )
        self._invoices[order_id] = req
        return req

    def process_autonomous_payment(
        self,
        order_id: str,
        payer_account_id: Optional[str] = None
    ) -> X402PaymentReceipt:
        """
        Simulates autonomous payment settlement for automated AI services.
        Transitions the simulated payment state to 'settled'.
        """
        req = self._invoices.get(order_id)
        amount_hbars = req.amount_hbars if req else 2.0
        now = datetime.now(timezone.utc)
        simulated_tx_id = f"0.0.98421@{int(now.timestamp())}.000182749"

        receipt = X402PaymentReceipt(
            order_id=order_id,
            tx_id=simulated_tx_id,
            payer_account_id=payer_account_id or "0.0.98421",
            amount_hbars=amount_hbars,
            status="settled",
            consensus_timestamp=now.isoformat(),
            is_mock=True
        )
        self._receipts[order_id] = receipt
        return receipt

    def verify_payment(self, order_id: str) -> bool:
        """
        Checks whether payment for an order has been settled.
        """
        return order_id in self._receipts and self._receipts[order_id].status == "settled"


hedera_client = HederaX402Client()

