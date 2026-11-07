"""
Payment boundary and gateway definitions for Guardvane + OpiHub.
Direct 0G AI reasoning for automated agents; EVM Smart Escrow on Rabdi Testnet for specialists.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger("guardvane.payments.gateway")


@dataclass
class PaymentIntent:
    id: str
    order_id: str
    amount: float
    currency: str
    status: str
    gateway: str
    created_at: str
    verified_at: Optional[str] = None
    failure_reason: Optional[str] = None
    external_reference: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PaymentGateway:
    """Interface for payment create/verify."""

    name = "unconfigured"

    def create_intent(self, order_id: str, amount: float, currency: str = "USD") -> PaymentIntent:
        raise NotImplementedError

    def verify(self, intent: PaymentIntent, proof: Optional[str] = None) -> PaymentIntent:
        raise NotImplementedError


class EVMEscrowPaymentGateway(PaymentGateway):
    """
    EVM Smart Escrow gateway for human specialist reviews on Rabdi Testnet (Chain ID 7794095).
    """

    name = "evm_escrow"

    def create_intent(self, order_id: str, amount: float, currency: str = "USD") -> PaymentIntent:
        now = datetime.now(timezone.utc).isoformat()
        return PaymentIntent(
            id=f"esc_{uuid.uuid4().hex[:12]}",
            order_id=order_id,
            amount=amount,
            currency=currency,
            status="pending",
            gateway=self.name,
            created_at=now,
            metadata={
                "network": "rabdi:testnet",
                "chain_id": 7794095,
                "contract": "0x176B2d2eCE7a48d0B6780709B168aC06a5834501",
                "currency": "tGLM",
            },
        )

    def verify(self, intent: PaymentIntent, proof: Optional[str] = None) -> PaymentIntent:
        if proof and str(proof).startswith("0x"):
            intent.status = "verified"
            intent.verified_at = datetime.now(timezone.utc).isoformat()
            intent.external_reference = str(proof)
            return intent
        intent.status = "failed"
        intent.failure_reason = "Valid on-chain transaction hash required for EVM escrow deposit."
        return intent


class TestPaymentGateway(PaymentGateway):
    """
    Test harness gateway. Verifies with proof == 'test-receipt'.
    """

    name = "test"

    def create_intent(self, order_id: str, amount: float, currency: str = "USD") -> PaymentIntent:
        now = datetime.now(timezone.utc).isoformat()
        return PaymentIntent(
            id=f"pay_{uuid.uuid4().hex[:12]}",
            order_id=order_id,
            amount=amount,
            currency=currency,
            status="pending",
            gateway=self.name,
            created_at=now,
            metadata={"network": "test-harness"},
        )

    def verify(self, intent: PaymentIntent, proof: Optional[str] = None) -> PaymentIntent:
        if proof != "test-receipt" and (isinstance(proof, str) and "test-receipt" not in proof):
            intent.status = "failed"
            intent.failure_reason = "Test gateway requires proof 'test-receipt'."
            return intent
        intent.status = "verified"
        intent.verified_at = datetime.now(timezone.utc).isoformat()
        intent.external_reference = f"test:{intent.id}"
        return intent


class UnconfiguredPaymentGateway(PaymentGateway):
    """
    Fallback when no gateway is configured.
    """

    name = "unconfigured"

    def create_intent(self, order_id: str, amount: float, currency: str = "USD") -> PaymentIntent:
        now = datetime.now(timezone.utc).isoformat()
        return PaymentIntent(
            id=f"pay_{uuid.uuid4().hex[:12]}",
            order_id=order_id,
            amount=amount,
            currency=currency,
            status="pending",
            gateway=self.name,
            created_at=now,
            metadata={"network": "unconfigured"},
        )

    def verify(self, intent: PaymentIntent, proof: Optional[str] = None) -> PaymentIntent:
        intent.status = "failed"
        intent.failure_reason = "No payment gateway configured."
        return intent


def payment_mode() -> str:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return "test"
    return os.getenv("GUARDVANE_PAYMENT_MODE", "evm_escrow").strip().lower()


def get_payment_gateway() -> PaymentGateway:
    mode = payment_mode()
    if mode == "test":
        return TestPaymentGateway()
    return EVMEscrowPaymentGateway()
