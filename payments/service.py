"""
Persisted payment intents and verification orchestration.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from payments.gateway import PaymentIntent, get_payment_gateway, payment_mode


class PaymentService:
    def __init__(self, database=None):
        self._db = database

    @property
    def db(self):
        if self._db is None:
            from marketplace.db import db
            self._db = db
        return self._db

    def public_config(self) -> Dict[str, Any]:
        mode = payment_mode()
        is_hedera_x402 = mode in ("testnet", "live")
        from payments.config import (
            HEDERA_MERCHANT_ACCOUNT_ID,
            X402_ASSET_ID,
            X402_FACILITATOR_URL,
            X402_NETWORK,
        )
        from payments.blocky402 import get_facilitator_fee_payer, get_hbar_usd_rate
        return {
            "mode": mode,
            "network": "hedera",
            "x402_network": X402_NETWORK if is_hedera_x402 else "hedera:testnet",
            "asset_id": X402_ASSET_ID if is_hedera_x402 else "0.0.0",
            "facilitator_url": X402_FACILITATOR_URL if is_hedera_x402 else None,
            "merchant_account": HEDERA_MERCHANT_ACCOUNT_ID if is_hedera_x402 else None,
            "fee_payer": get_facilitator_fee_payer() if is_hedera_x402 else None,
            "usd_per_hbar": get_hbar_usd_rate() if is_hedera_x402 else None,
            "separate_from_arkiv": True,
            "x402_implemented": is_hedera_x402,
            "can_confirm_test_payment": mode == "test",
            "notice": (
                "Native Hedera x402 payments via Blocky402 Hosted Testnet facilitator."
                if is_hedera_x402
                else "No live payment gateway configured."
            ),
        }

    def create_intent(self, order_id: str, amount: float, currency: str = "USD") -> PaymentIntent:
        existing = self.get_intent_for_order(order_id)
        if existing:
            return existing
        gateway = get_payment_gateway()
        intent = gateway.create_intent(order_id, amount, currency)
        self._save(intent)
        return intent

    def get_intent_for_order(self, order_id: str) -> Optional[PaymentIntent]:
        conn = self.db._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT * FROM payment_intents WHERE order_id = ? ORDER BY created_at DESC LIMIT 1",
                (order_id,),
            )
        except Exception:
            return None
        row = cursor.fetchone()
        if not row:
            return None
        return self._from_row(row)

    def verify_intent(self, order_id: str, proof: Optional[str] = None) -> PaymentIntent:
        intent = self.get_intent_for_order(order_id)
        if not intent:
            raise ValueError("No payment intent exists for this request.")
        if intent.status == "verified":
            return intent
        gateway = get_payment_gateway()
        updated = gateway.verify(intent, proof=proof)
        self._save(updated)
        return updated

    def mark_refunded(self, order_id: str) -> Optional[PaymentIntent]:
        intent = self.get_intent_for_order(order_id)
        if not intent:
            return None
        intent.status = "refunded"
        self._save(intent)
        return intent

    def _save(self, intent: PaymentIntent) -> None:
        conn = self.db._get_connection()
        now = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(intent.metadata or {})
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM payment_intents WHERE id = ?", (intent.id,))
        exists = cursor.fetchone()
        with conn:
            if exists:
                conn.execute(
                    """
                    UPDATE payment_intents
                    SET status = ?, external_reference = ?, failure_reason = ?,
                        metadata = ?, updated_at = ?, verified_at = ?
                    WHERE id = ?
                    """,
                    (
                        intent.status,
                        intent.external_reference,
                        intent.failure_reason,
                        payload,
                        now,
                        intent.verified_at,
                        intent.id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO payment_intents (
                        id, order_id, amount, currency, status, gateway,
                        external_reference, failure_reason, metadata, created_at, updated_at, verified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intent.id,
                        intent.order_id,
                        intent.amount,
                        intent.currency,
                        intent.status,
                        intent.gateway,
                        intent.external_reference,
                        intent.failure_reason,
                        payload,
                        intent.created_at,
                        now,
                        intent.verified_at,
                    ),
                )

    def _from_row(self, row) -> PaymentIntent:
        metadata = {}
        raw = row["metadata"] if "metadata" in row.keys() else None
        if raw:
            try:
                metadata = json.loads(raw)
            except Exception:
                metadata = {}
        return PaymentIntent(
            id=row["id"],
            order_id=row["order_id"],
            amount=float(row["amount"]),
            currency=row["currency"],
            status=row["status"],
            gateway=row["gateway"],
            created_at=row["created_at"],
            verified_at=row["verified_at"] if "verified_at" in row.keys() else None,
            failure_reason=row["failure_reason"] if "failure_reason" in row.keys() else None,
            external_reference=row["external_reference"] if "external_reference" in row.keys() else None,
            metadata=metadata,
        )


payment_service = PaymentService()
