"""
Arkiv Client Integration for Guardvane.
Interfaces with official @arkiv-network/sdk on Rabdi Testnet (Chain ID 7794095).
Executes public read queries and reconciles confirmed MetaMask on-chain records.
"""

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

from integrations.arkiv.schemas import (
    ArkivAwardRecord,
    ArkivSecurityTask,
    ArkivServiceListing,
    ArkivSpecialistBid,
    ArkivSpecialistProfile,
    ArkivSyncStatus,
)

logger = logging.getLogger("guardvane.integrations.arkiv")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_PATH = PROJECT_ROOT / "scripts" / "arkiv_cli.mjs"


class ArkivClient:
    """
    Decentralized provider discovery and marketplace registry client for Arkiv.
    Queries the Rabdi testnet via official @arkiv-network/sdk and verifies on-chain entities.
    """

    def __init__(
        self,
        access_key: Optional[str] = None,
        rpc_url: Optional[str] = None,
        chain_id: int = 7794095,
        mock_mode: Optional[bool] = None,
    ):
        self.access_key = access_key or os.environ.get("ARKIV_ACCESS_KEY", "")
        self.rpc_url = rpc_url or os.environ.get("ARKIV_RPC_URL", "https://rpc.rabdi.db-chain.testnet.arkiv.network")
        self.chain_id = int(os.environ.get("ARKIV_CHAIN_ID", chain_id))
        
        # Test mock mode if explicitly flagged or in unit test environment
        self._mock_mode = (
            mock_mode if mock_mode is not None
            else bool(os.environ.get("ARKIV_TEST_MOCK") == "1")
        )
        self._mock_entities: Dict[str, Dict[str, Any]] = {}

    def _run_cli(self, command: str, args: List[str]) -> Dict[str, Any]:
        """Runs the isolated Node CLI bridge."""
        if self._mock_mode:
            return {"success": True, "mock": True}

        cmd = ["node", str(CLI_PATH), command] + args
        env = os.environ.copy()
        if self.access_key:
            env["ARKIV_ACCESS_KEY"] = self.access_key

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(PROJECT_ROOT),
                env=env,
            )
            if res.returncode != 0:
                logger.warning(f"Arkiv CLI error ({command}): {res.stderr.strip()}")
                return {"success": False, "error": res.stderr.strip() or "CLI execution failed"}
            return json.loads(res.stdout)
        except Exception as e:
            logger.warning(f"Failed to execute Arkiv CLI: {e}")
            return {"success": False, "error": str(e)}

    # -----------------------------------------------------------------------
    # Status & Health Check
    # -----------------------------------------------------------------------

    def get_status(self) -> ArkivSyncStatus:
        """Queries node health, sync state, and latest block number on Rabdi Testnet."""
        now = datetime.now(timezone.utc).isoformat()
        if self._mock_mode:
            return ArkivSyncStatus(
                is_connected=True,
                chain_id=self.chain_id,
                network="Rabdi Testnet (Mock)",
                current_block=278800,
                last_sync_timestamp=now,
                mode="mock_test",
                notice="Mock mode active for isolated testing.",
            )

        cli_res = self._run_cli("status", [])
        if cli_res.get("success"):
            return ArkivSyncStatus(
                is_connected=True,
                chain_id=cli_res.get("chain_id", self.chain_id),
                network=cli_res.get("network", "Rabdi Testnet"),
                currency=cli_res.get("currency", "tGLM"),
                rpc_url=cli_res.get("rpc_url", self.rpc_url),
                explorer_url=cli_res.get("explorer_url", "https://rabdi.explorer.arkiv.network"),
                current_block=cli_res.get("current_block"),
                last_sync_timestamp=now,
                mode="live_public_client",
                notice="Connected to Rabdi Testnet via @arkiv-network/sdk.",
            )

        return ArkivSyncStatus(
            is_connected=False,
            chain_id=self.chain_id,
            network="Rabdi Testnet",
            currency="tGLM",
            rpc_url=self.rpc_url,
            last_sync_timestamp=now,
            mode="disconnected",
            error=cli_res.get("error", "Unable to query Rabdi node"),
            notice="Failed to connect to Rabdi Testnet RPC.",
        )

    # -----------------------------------------------------------------------
    # Public Discovery Queries
    # -----------------------------------------------------------------------

    def query_specialists(
        self,
        availability: Optional[str] = None,
        wallet: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ArkivSpecialistProfile]:
        """Queries specialist profiles registered on Arkiv (guardvane.specialists.v1)."""
        if self._mock_mode:
            results = []
            for v in self._mock_entities.get("specialists", {}).values():
                if availability and availability != "all" and v.get("availability_status") != availability:
                    continue
                if wallet and v.get("wallet_address", "").lower() != wallet.lower():
                    continue
                results.append(ArkivSpecialistProfile(**v))
            return results[offset : offset + limit]

        cli_args = ["--schema", "specialists", "--limit", str(limit), "--offset", str(offset)]
        if availability:
            cli_args.extend(["--status", availability])
        if wallet:
            cli_args.extend(["--wallet", wallet])

        res = self._run_cli("query", cli_args)
        if not res.get("success"):
            return []

        profiles = []
        for row in res.get("entities", []):
            try:
                profiles.append(ArkivSpecialistProfile(
                    entity_key=row.get("entity_key"),
                    owner=row.get("owner"),
                    wallet_address=row.get("wallet_address", row.get("owner", "")),
                    display_name=row.get("display_name", "Specialist"),
                    headline=row.get("headline", ""),
                    expertise_categories=row.get("expertise_categories", "ai_security"),
                    skills=row.get("skills", ""),
                    experience_level=row.get("experience_level", "senior"),
                    availability_status=row.get("availability_status", "available"),
                    profile_version=row.get("profile_version", "1.0.0"),
                    created_at_block=row.get("created_at_block"),
                    expires_at=row.get("expires_at"),
                ))
            except Exception as e:
                logger.debug(f"Row mapping skipped: {e}")
        return profiles

    def query_services(
        self,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ArkivServiceListing]:
        """Queries service listings published on Arkiv (guardvane.services.v1)."""
        if self._mock_mode:
            results = []
            for v in self._mock_entities.get("services", {}).values():
                if category and category != "all" and v.get("service_category") != category:
                    continue
                results.append(ArkivServiceListing(**v))
            return results[offset : offset + limit]

        cli_args = ["--schema", "services", "--limit", str(limit), "--offset", str(offset)]
        if category and category != "all":
            cli_args.extend(["--category", category])

        res = self._run_cli("query", cli_args)
        if not res.get("success"):
            return []

        services = []
        for row in res.get("entities", []):
            try:
                price = float(row.get("indicative_price") or 10.0)
                services.append(ArkivServiceListing(
                    entity_key=row.get("entity_key"),
                    owner=row.get("owner"),
                    provider_wallet=row.get("provider_wallet", row.get("owner", "")),
                    service_category=row.get("service_category", "ai_security"),
                    title=row.get("title", "Security Service"),
                    short_description=row.get("short_description", ""),
                    pricing_type=row.get("pricing_type", "fixed"),
                    indicative_price=price,
                    availability=row.get("availability", "available"),
                    service_version=row.get("service_version", "1.0.0"),
                    created_at_block=row.get("created_at_block"),
                    expires_at=row.get("expires_at"),
                ))
            except Exception as e:
                logger.debug(f"Row mapping skipped: {e}")
        return services

    def query_tasks(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        customer_wallet: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ArkivSecurityTask]:
        """Queries security tasks on Arkiv (guardvane.tasks.v1)."""
        if self._mock_mode:
            results = []
            for v in self._mock_entities.get("tasks", {}).values():
                if status and status != "all" and v.get("status") != status:
                    continue
                if category and category != "all" and v.get("category") != category:
                    continue
                if customer_wallet and v.get("customer_wallet", "").lower() != customer_wallet.lower():
                    continue
                if task_id and v.get("task_id") != task_id:
                    continue
                results.append(ArkivSecurityTask(**v))
            return results[offset : offset + limit]

        cli_args = ["--schema", "tasks", "--limit", str(limit), "--offset", str(offset)]
        if status and status != "all":
            cli_args.extend(["--status", status])
        if category and category != "all":
            cli_args.extend(["--category", category])
        if customer_wallet:
            cli_args.extend(["--wallet", customer_wallet])
        if task_id:
            cli_args.extend(["--taskId", task_id])

        res = self._run_cli("query", cli_args)
        if not res.get("success"):
            return []

        tasks = []
        for row in res.get("entities", []):
            try:
                tasks.append(ArkivSecurityTask(
                    entity_key=row.get("entity_key"),
                    owner=row.get("owner"),
                    task_id=row.get("task_id", ""),
                    customer_wallet=row.get("customer_wallet", row.get("owner", "")),
                    category=row.get("category", "application_security"),
                    title=row.get("title", "Security Review"),
                    public_description=row.get("public_description", ""),
                    required_skills=row.get("required_skills", ""),
                    budget_type=row.get("budget_type", "fixed"),
                    budget_range=row.get("budget_range", "50-100 tGLM"),
                    status=row.get("status", "open"),
                    created_at=row.get("created_at", datetime.now(timezone.utc).isoformat()),
                    deadline=row.get("deadline", ""),
                    task_version=row.get("task_version", "1.0.0"),
                    created_at_block=row.get("created_at_block"),
                    expires_at=row.get("expires_at"),
                ))
            except Exception as e:
                logger.debug(f"Task row mapping skipped: {e}")
        return tasks

    def query_bids(
        self,
        task_id: Optional[str] = None,
        specialist_wallet: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ArkivSpecialistBid]:
        """Queries specialist bids on Arkiv (guardvane.bids.v1)."""
        if self._mock_mode:
            return [
                ArkivSpecialistBid(**v)
                for v in self._mock_entities.get("bids", {}).values()
                if (not task_id or v.get("task_id") == task_id)
            ]

        cli_args = ["--schema", "bids", "--limit", str(limit), "--offset", str(offset)]
        if task_id:
            cli_args.extend(["--taskId", task_id])
        if specialist_wallet:
            cli_args.extend(["--specialist", specialist_wallet])
        if status:
            cli_args.extend(["--status", status])

        res = self._run_cli("query", cli_args)
        if not res.get("success"):
            return []

        bids = []
        for row in res.get("entities", []):
            try:
                price = float(row.get("proposed_price") or 25.0)
                bids.append(ArkivSpecialistBid(
                    entity_key=row.get("entity_key"),
                    owner=row.get("owner"),
                    task_id=row.get("task_id", ""),
                    specialist_wallet=row.get("specialist_wallet", row.get("owner", "")),
                    proposed_price=price,
                    estimated_duration=row.get("estimated_duration", "3 days"),
                    proposal_summary=row.get("proposal_summary", ""),
                    status=row.get("status", "submitted"),
                    created_at=row.get("created_at", datetime.now(timezone.utc).isoformat()),
                    bid_version=row.get("bid_version", "1.0.0"),
                    created_at_block=row.get("created_at_block"),
                    expires_at=row.get("expires_at"),
                ))
            except Exception as e:
                logger.debug(f"Bid row mapping skipped: {e}")
        return bids

    def query_awards(
        self,
        task_id: Optional[str] = None,
        customer_wallet: Optional[str] = None,
        limit: int = 10,
    ) -> List[ArkivAwardRecord]:
        """Queries award records on Arkiv (guardvane.awards.v1)."""
        if self._mock_mode:
            return [
                ArkivAwardRecord(**v)
                for v in self._mock_entities.get("awards", {}).values()
                if (not task_id or v.get("task_id") == task_id)
            ]

        cli_args = ["--schema", "awards", "--limit", str(limit)]
        if task_id:
            cli_args.extend(["--taskId", task_id])
        if customer_wallet:
            cli_args.extend(["--wallet", customer_wallet])

        res = self._run_cli("query", cli_args)
        if not res.get("success"):
            return []

        awards = []
        for row in res.get("entities", []):
            try:
                awards.append(ArkivAwardRecord(
                    entity_key=row.get("entity_key"),
                    owner=row.get("owner"),
                    task_id=row.get("task_id", ""),
                    accepted_bid_key=row.get("accepted_bid_key", ""),
                    customer_wallet=row.get("customer_wallet", row.get("owner", "")),
                    specialist_wallet=row.get("specialist_wallet", ""),
                    award_status=row.get("award_status", "awarded"),
                    created_at=row.get("created_at", datetime.now(timezone.utc).isoformat()),
                    created_at_block=row.get("created_at_block"),
                    expires_at=row.get("expires_at"),
                ))
            except Exception as e:
                logger.debug(f"Award row mapping skipped: {e}")
        return awards

    # -----------------------------------------------------------------------
    # Verification & Integrity
    # -----------------------------------------------------------------------

    def get_entity(
        self,
        schema_name: str,
        entity_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single entity directly from Arkiv via client.getEntity().
        Returns the decoded on-chain entity dictionary or None if not found.
        """
        if self._mock_mode:
            return self._mock_entities.get(schema_name, {}).get(entity_key)

        res = self._run_cli("get", ["--schema", schema_name, "--entityKey", entity_key])
        if not res.get("success") or not res.get("entity"):
            return None
        return res["entity"]

    def verify_entity_ownership(
        self,
        schema_name: str,
        entity_key: str,
        expected_owner: str,
    ) -> bool:
        """
        Verifies that an on-chain entity exists, conforms to the schema,
        and is owned by the expected wallet address.
        """
        if self._mock_mode:
            entity = self._mock_entities.get(schema_name, {}).get(entity_key)
            if not entity:
                return False
            return str(entity.get("owner", "")).lower() == expected_owner.lower()

        res = self._run_cli("get", ["--schema", schema_name, "--entityKey", entity_key])
        if not res.get("success") or not res.get("entity"):
            return False

        entity = res["entity"]
        actual_owner = str(entity.get("owner") or "").lower()
        return actual_owner == expected_owner.lower()

    # -----------------------------------------------------------------------
    # Backwards Compatibility Helpers (Legacy Phase 1 Simulation)
    # -----------------------------------------------------------------------

    def publish_provider_record(self, provider_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Backwards-compatible helper for legacy provider registration hooks."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "record_id": f"arkiv_{provider_id}",
            "entity_id": provider_id,
            "status": "published_simulated",
            "timestamp": now,
        }

    def publish_record(self, entity_type: str, entity_id: str, payload_data: Dict[str, Any]) -> Dict[str, Any]:
        """Backwards-compatible helper for legacy record hooks."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "record_id": f"arkiv_{entity_type}_{entity_id}",
            "entity_type": entity_type,
            "entity_id": entity_id,
            "status": "published_simulated",
            "timestamp": now,
        }


# Default singleton instance
arkiv_client = ArkivClient()
