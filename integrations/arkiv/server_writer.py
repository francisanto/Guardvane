"""
Backend-controlled Arkiv write path.

Security design
---------------
Arkiv is an infrastructure data layer, not a user-facing product. Ordinary users
must not be required to switch MetaMask to Rabdi in order to log in, browse
services, or manage private requests.

Writes of public, non-sensitive catalogue metadata may be performed by a
developer-managed signer held only on the server:

- Private key is read from ARKIV_SIGNER_PRIVATE_KEY (or a signing service).
- The key is never sent to the browser, never logged, and never returned by APIs.
- Every write is authorized against the authenticated wallet in PostgreSQL first.
- Payloads are sanitized: no credentials, private instructions, reports, or
  request bodies are published.
- Transaction hashes and entity IDs are stored in arkiv_records for reconciliation.
- Failures do not mutate application truth; the SQL record remains canonical.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("guardvane.arkiv.server_writer")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_PATH = PROJECT_ROOT / "scripts" / "arkiv_cli.mjs"

ALLOWED_PUBLIC_SCHEMAS = {
    "guardvane.specialists.v1",
    "guardvane.services.v1",
}


class ArkivServerWriter:
    def __init__(self) -> None:
        pass

    @property
    def is_configured(self) -> bool:
        return bool(os.getenv("ARKIV_SIGNER_PRIVATE_KEY") or os.getenv("ARKIV_PRIVATE_KEY"))

    def publish_public_entity(
        self,
        schema_tag: str,
        entity_id: str,
        owner_wallet: str,
        public_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        if schema_tag not in ALLOWED_PUBLIC_SCHEMAS:
            return {
                "status": "rejected",
                "reason": f"Schema '{schema_tag}' is not allowed for backend publication.",
            }

        sanitized = self._sanitize(public_payload)
        is_mock = os.getenv("ARKIV_TEST_MOCK") == "1"

        if not self.is_configured and not is_mock:
            logger.info(
                "Arkiv backend write skipped; ARKIV_SIGNER_PRIVATE_KEY is not configured."
            )
            return {
                "status": "not_configured",
                "schema_tag": schema_tag,
                "entity_id": entity_id,
                "owner_wallet": owner_wallet,
                "payload": sanitized,
                "entity_key": None,
                "tx_hash": None,
                "tested_on_testnet": False,
                "notice": (
                    "Backend signer is not configured. Canonical records remain in PostgreSQL. "
                    "No Rabdi write was attempted."
                ),
            }

        # Prepare parameters for CLI execution
        if schema_tag == "guardvane.specialists.v1":
            command = "publish-specialist"
            cli_data = {
                "wallet_address": owner_wallet,
                "display_name": sanitized.get("display_name", "Specialist"),
                "headline": sanitized.get("headline", sanitized.get("title", "")),
                "categories": sanitized.get("categories", [sanitized.get("category", "ai_security")]),
                "skills": sanitized.get("skills", []),
                "experience_level": sanitized.get("experience_level", "senior"),
                "availability_status": sanitized.get("availability", "available"),
                "profile_version": "1.0.0",
            }
        elif schema_tag == "guardvane.services.v1":
            command = "publish-service"
            price_val = sanitized.get("price", 10.0)
            price_str = f"{float(price_val):.2f}" if isinstance(price_val, (int, float)) else str(price_val)
            cli_data = {
                "provider_wallet": owner_wallet,
                "service_category": sanitized.get("category", "ai_security"),
                "title": sanitized.get("title", "Security Service"),
                "short_description": (sanitized.get("description") or sanitized.get("title") or "")[:250],
                "pricing_type": "fixed",
                "indicative_price": price_str,
                "availability": "available",
                "service_version": "1.0.0",
            }
        else:
            return {
                "status": "rejected",
                "reason": f"Unsupported schema: {schema_tag}",
            }

        cmd = [
            "node",
            str(CLI_PATH),
            command,
            "--data",
            json.dumps(cli_data),
        ]
        if is_mock:
            cmd.append("--mock")

        signer_key = os.getenv("ARKIV_SIGNER_PRIVATE_KEY") or os.getenv("ARKIV_PRIVATE_KEY") or ""
        if signer_key and not is_mock:
            cmd.extend(["--privateKey", signer_key])

        env = os.environ.copy()
        if os.getenv("ARKIV_ACCESS_KEY"):
            env["ARKIV_ACCESS_KEY"] = os.getenv("ARKIV_ACCESS_KEY")

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(PROJECT_ROOT),
                env=env,
            )
            if res.returncode != 0:
                err_msg = res.stderr.strip() or "Arkiv CLI write returned non-zero exit code"
                logger.warning(f"Arkiv CLI publishing failed: {err_msg}")
                return {
                    "status": "failed",
                    "schema_tag": schema_tag,
                    "entity_id": entity_id,
                    "owner_wallet": owner_wallet,
                    "payload": sanitized,
                    "error": err_msg,
                    "entity_key": None,
                    "tx_hash": None,
                }

            out_data = json.loads(res.stdout)
            if not out_data.get("success"):
                return {
                    "status": "failed",
                    "schema_tag": schema_tag,
                    "entity_id": entity_id,
                    "owner_wallet": owner_wallet,
                    "payload": sanitized,
                    "error": out_data.get("error", "Unknown publishing error"),
                    "entity_key": None,
                    "tx_hash": None,
                }

            return {
                "status": "confirmed",
                "schema_tag": schema_tag,
                "entity_id": entity_id,
                "owner_wallet": owner_wallet,
                "entity_key": out_data["entityKey"],
                "tx_hash": out_data["txHash"],
                "expires_at": out_data.get("expiresAt"),
                "payload": sanitized,
                "tested_on_testnet": not is_mock,
                "notice": "Successfully published entity to Arkiv on Rabdi testnet." if not is_mock else "Mock testnet transaction recorded.",
            }
        except Exception as e:
            logger.error(f"Failed to publish entity to Arkiv: {e}")
            return {
                "status": "failed",
                "schema_tag": schema_tag,
                "entity_id": entity_id,
                "owner_wallet": owner_wallet,
                "payload": sanitized,
                "error": str(e),
                "entity_key": None,
                "tx_hash": None,
            }

    def _sanitize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        blocked = {
            "prompt_content",
            "requirements",
            "test_env_notes",
            "docs_link",
            "product_link",
            "hardened_prompt",
            "findings",
            "report",
            "private_key",
            "password",
            "secret",
            "token",
        }
        clean = {}
        for key, value in (payload or {}).items():
            if key.lower() in blocked:
                continue
            if isinstance(value, str) and len(value) > 500:
                clean[key] = value[:500]
            else:
                clean[key] = value
        return clean


arkiv_server_writer = ArkivServerWriter()
