"""
Swarm Integration Client for PromptShield Marketplace.
Provides clean interface boundaries for decentralized security report storage
and retrieval on Ethereum Swarm (Bzz protocol).
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from integrations.swarm.schemas import SwarmReportMetadata, SwarmStatus, SwarmUploadResult

logger = logging.getLogger("promptshield.integrations.swarm")


class SwarmClient:
    """
    Decentralized storage client for Ethereum Swarm.

    Phase 1 implementation provides mock/simulated content-addressable storage
    and generates valid bzz:// URI references for security reports without
    requiring an active Bee node or postage stamp expenditure.
    """

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        postage_batch_id: Optional[str] = None
    ):
        self._gateway_url = gateway_url or "http://localhost:1633"
        self._postage_batch_id = postage_batch_id
        self._stored_payloads: Dict[str, Dict[str, Any]] = {}
        logger.info("SwarmClient initialized in local simulation mode.")

    def get_status(self) -> SwarmStatus:
        """
        Returns Swarm node connectivity and configuration status.
        """
        return SwarmStatus(
            is_connected=False,
            gateway_url=self._gateway_url,
            postage_batch_configured=bool(self._postage_batch_id),
            mode="mock_interface",
            notice="Phase 1 architecture ready. Active Swarm node connection disabled."
        )

    def upload_security_report(
        self,
        report_id: str,
        order_id: str,
        customer_id: str,
        provider_id: str,
        service_id: str,
        report_data: Dict[str, Any]
    ) -> SwarmUploadResult:
        """
        Simulates uploading a security report to Swarm.
        Calculates SHA-256 hash to mimic Swarm content-addressed chunk reference (64 hex characters).
        """
        serialized = json.dumps(report_data, sort_keys=True).encode("utf-8")
        raw_hash = hashlib.sha256(serialized).hexdigest()
        bzz_ref = f"bzz://{raw_hash}"

        now = datetime.now(timezone.utc).isoformat()
        metadata = SwarmReportMetadata(
            report_id=report_id,
            order_id=order_id,
            customer_id=customer_id,
            provider_id=provider_id,
            service_id=service_id,
            created_at=now,
            content_hash=raw_hash,
            is_encrypted=True,
            content_type="application/json"
        )

        self._stored_payloads[raw_hash] = {
            "metadata": metadata.model_dump(),
            "payload": report_data
        }

        return SwarmUploadResult(
            success=True,
            reference=bzz_ref,
            raw_hash=raw_hash,
            size_bytes=len(serialized),
            pinned=False,
            storage_batch_id=self._postage_batch_id or "simulated_batch_stamp_0000",
            timestamp=now
        )

    def retrieve_security_report(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        Simulates retrieving a report from Swarm by its bzz:// reference or raw hash.
        """
        raw_hash = reference.replace("bzz://", "").strip()
        record = self._stored_payloads.get(raw_hash)
        if record:
            return record.get("payload")
        return None


swarm_client = SwarmClient()

