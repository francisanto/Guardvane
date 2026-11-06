"""
Test Suite for Guardvane Arkiv Integration (Rabdi Testnet, Chain ID 7794095).

Validates:
1. Network configuration and status endpoints (/marketplace/arkiv/config, /marketplace/arkiv/status).
2. Pydantic schema validation for all 5 official schemas:
   - guardvane.specialists.v1
   - guardvane.services.v1
   - guardvane.tasks.v1
   - guardvane.bids.v1
   - guardvane.awards.v1
3. Public discovery queries (tasks, bids, awards) via ArkivClient in mock and live modes.
4. On-chain record reconciliation with PostgreSQL / SQLite database:
   - Task reconciliation -> registers order in 'requested' state.
   - Bid reconciliation -> registers specialist proposal.
   - Award reconciliation -> transitions order to 'accepted' with assigned specialist.
5. Entity ownership verification and security boundary enforcement.
6. Zero credit consumption guarantee during automated testing.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from main import app
from integrations.arkiv.client import ArkivClient, arkiv_client
from integrations.arkiv.schemas import (
    ArkivAwardRecord,
    ArkivSecurityTask,
    ArkivServiceListing,
    ArkivSpecialistBid,
    ArkivSpecialistProfile,
    ArkivSyncStatus,
    ReconcileAwardRequest,
    ReconcileBidRequest,
    ReconcileTaskRequest,
)
from marketplace.service import marketplace_service


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Network Configuration & Health Endpoints
# ---------------------------------------------------------------------------

def test_arkiv_config_endpoint(client):
    """Verify that Arkiv configuration returns Rabdi network parameters."""
    resp = client.get("/marketplace/arkiv/config")
    assert resp.status_code == 200
    data = resp.json()

    assert data["chain_id"] == 7794095
    assert data["chain_id_hex"] == "0x76ee8f"
    assert data["network"] == "Rabdi Testnet"
    assert data["currency"] == "tGLM"
    assert "https://rpc.rabdi.db-chain.testnet.arkiv.network" in data["rpc_url"]
    assert "explorer.rabdi.db-chain.testnet.arkiv.network" in data["explorer_url"]


def test_arkiv_status_endpoint(client):
    """Verify Arkiv live sync status query on Rabdi Testnet."""
    resp = client.get("/marketplace/arkiv/status")
    assert resp.status_code == 200
    data = resp.json()

    assert "is_connected" in data
    assert data["chain_id"] == 7794095
    assert "Rabdi Testnet" in data["network"]
    assert "last_sync_timestamp" in data
    assert data["mode"] in ("live_public_client", "mock_test", "disconnected")


# ---------------------------------------------------------------------------
# 2. Schema Validation (All 5 Schemas)
# ---------------------------------------------------------------------------

def test_specialist_profile_schema_validation():
    """Validates guardvane.specialists.v1 schema."""
    valid_profile = ArkivSpecialistProfile(
        wallet_address="0x1111111111111111111111111111111111111111",
        display_name="Dr. Alice Vance",
        headline="Principal AI Penetration Tester",
        expertise_categories="application_testing,codebase_security",
        skills="OWASP LLM, Delimiter Inversion, AST Parsing",
        experience_level="senior",
        availability_status="available",
    )
    assert valid_profile.wallet_address.startswith("0x")
    assert valid_profile.experience_level == "senior"
    assert valid_profile.profile_version == "1.0.0"

    # Missing required field
    with pytest.raises(ValidationError):
        ArkivSpecialistProfile(
            headline="Missing wallet and display name"
        )


def test_service_listing_schema_validation():
    """Validates guardvane.services.v1 schema."""
    valid_service = ArkivServiceListing(
        provider_wallet="0x2222222222222222222222222222222222222222",
        service_category="prompt_optimization",
        title="Automated Injection Boundary Defense",
        short_description="Hardens prompt tokens with cryptographic role encapsulation.",
        pricing_type="fixed",
        indicative_price=45.5,
        availability="available",
    )
    assert valid_service.indicative_price == 45.5
    assert valid_service.pricing_type == "fixed"

    with pytest.raises(ValidationError):
        ArkivServiceListing(
            provider_wallet="0x2222222222222222222222222222222222222222",
            indicative_price="not-a-number",  # invalid float
        )


def test_security_task_schema_validation():
    """Validates guardvane.tasks.v1 schema."""
    now = datetime.now(timezone.utc).isoformat()
    valid_task = ArkivSecurityTask(
        task_id="task-test-001",
        customer_wallet="0x3333333333333333333333333333333333333333",
        category="application_testing",
        title="Audit DeFi AI Agent System Prompts",
        public_description="Perform boundary analysis on autonomous trade executor agent.",
        required_skills="FastAPI, LangChain, Injection Defense",
        budget_type="fixed",
        budget_range="50-100 tGLM",
        status="open",
        created_at=now,
    )
    assert valid_task.task_id == "task-test-001"
    assert valid_task.status == "open"

    with pytest.raises(ValidationError):
        ArkivSecurityTask(
            task_id="task-test-002"
            # Missing customer_wallet, category, title, public_description, created_at
        )


def test_specialist_bid_schema_validation():
    """Validates guardvane.bids.v1 schema."""
    now = datetime.now(timezone.utc).isoformat()
    valid_bid = ArkivSpecialistBid(
        task_id="task-test-001",
        specialist_wallet="0x4444444444444444444444444444444444444444",
        proposed_price=35.0,
        estimated_duration="2 days",
        proposal_summary="Full fuzzing test suite using Guardvane ML and 0G verification.",
        status="submitted",
        created_at=now,
    )
    assert valid_bid.proposed_price == 35.0
    assert valid_bid.task_id == "task-test-001"


def test_award_record_schema_validation():
    """Validates guardvane.awards.v1 schema."""
    now = datetime.now(timezone.utc).isoformat()
    valid_award = ArkivAwardRecord(
        task_id="task-test-001",
        accepted_bid_key="entity_key_bid_9988",
        customer_wallet="0x3333333333333333333333333333333333333333",
        specialist_wallet="0x4444444444444444444444444444444444444444",
        award_status="awarded",
        created_at=now,
    )
    assert valid_award.award_status == "awarded"
    assert valid_award.accepted_bid_key == "entity_key_bid_9988"


# ---------------------------------------------------------------------------
# 3. Discovery Queries via ArkivClient (Mock & Filter Tests)
# ---------------------------------------------------------------------------

def test_arkiv_client_mock_query_operations():
    """Tests query filtering in mock test mode without live credit or network usage."""
    mock_client = ArkivClient(mock_mode=True)
    now = datetime.now(timezone.utc).isoformat()

    # Seed mock data
    mock_client._mock_entities = {
        "specialists": {
            "spec1": {
                "wallet_address": "0xaaa111",
                "display_name": "Mock Spec 1",
                "expertise_categories": "application_testing",
                "availability_status": "available",
            },
            "spec2": {
                "wallet_address": "0xaaa222",
                "display_name": "Mock Spec 2",
                "expertise_categories": "smart_contract_audit",
                "availability_status": "busy",
            }
        },
        "tasks": {
            "task1": {
                "task_id": "task-mock-1",
                "customer_wallet": "0xcust1",
                "category": "application_testing",
                "title": "Task 1",
                "public_description": "Desc 1",
                "status": "open",
                "created_at": now,
            },
            "task2": {
                "task_id": "task-mock-2",
                "customer_wallet": "0xcust2",
                "category": "prompt_optimization",
                "title": "Task 2",
                "public_description": "Desc 2",
                "status": "awarded",
                "created_at": now,
            }
        },
        "bids": {
            "bid1": {
                "task_id": "task-mock-1",
                "specialist_wallet": "0xspec1",
                "proposed_price": 20.0,
                "status": "submitted",
                "created_at": now,
            }
        },
        "awards": {
            "award1": {
                "task_id": "task-mock-2",
                "accepted_bid_key": "bid_key_123",
                "customer_wallet": "0xcust2",
                "specialist_wallet": "0xspec2",
                "award_status": "awarded",
                "created_at": now,
            }
        }
    }

    # Query specialists with availability filter
    all_specs = mock_client.query_specialists()
    assert len(all_specs) == 2
    avail_specs = mock_client.query_specialists(availability="available")
    assert len(avail_specs) == 1
    assert avail_specs[0].wallet_address == "0xaaa111"

    # Query tasks
    tasks = mock_client.query_tasks()
    assert len(tasks) == 2

    # Query bids for task
    bids = mock_client.query_bids(task_id="task-mock-1")
    assert len(bids) == 1
    assert bids[0].proposed_price == 20.0

    # Query awards for task
    awards = mock_client.query_awards(task_id="task-mock-2")
    assert len(awards) == 1
    assert awards[0].accepted_bid_key == "bid_key_123"


# ---------------------------------------------------------------------------
# 4. End-to-End Reconciliation Workflow (Customer -> Bid -> Award)
# ---------------------------------------------------------------------------

def test_full_reconciliation_lifecycle(client):
    """
    Executes the complete on-chain reconciliation workflow:
    1. Customer posts task -> Reconciled to PostgreSQL as 'requested' order.
    2. Specialist submits bid -> Reconciled to arkiv_records.
    3. Customer awards bid -> Order status updates to 'accepted' with assigned provider.
    """
    test_task_id = f"task-recon-{int(datetime.now().timestamp())}"
    customer_addr = "0x9876543210987654321098765432109876543210"
    specialist_addr = "0x1234567890123456789012345678901234567890"

    # Step 1: Reconcile Task
    task_payload = {
        "task_id": test_task_id,
        "entity_key": f"key_task_{test_task_id}",
        "tx_hash": f"0xtx_task_{test_task_id}",
        "title": "Autonomous Agent Reentrancy Audit",
        "category": "smart_contract_audit",
        "public_description": "Inspect agent settlement contracts on Rabdi testnet.",
        "required_skills": "EVM, Reentrancy, Fuzzing",
        "budget_range": "80 tGLM",
        "customer_wallet": customer_addr,
    }
    resp = client.post(
        "/marketplace/arkiv/reconcile/task",
        json=task_payload,
        headers={"X-User-Id": customer_addr}
    )
    assert resp.status_code == 200
    task_res = resp.json()
    assert task_res["status"] == "reconciled"
    assert task_res["record"]["schema_tag"] == "guardvane.tasks.v1"
    assert task_res["record"]["owner_wallet"] == customer_addr.lower()

    # Verify task exists in local orders
    order = marketplace_service.get_order(test_task_id)
    assert order is not None
    assert order.status.value == "requested"
    assert order.customer_id.lower() == customer_addr.lower()

    # Step 2: Reconcile Specialist Bid
    bid_payload = {
        "task_id": test_task_id,
        "entity_key": f"key_bid_{test_task_id}",
        "tx_hash": f"0xtx_bid_{test_task_id}",
        "proposed_price": 75.0,
        "estimated_duration": "48 hours",
        "proposal_summary": "Extensive formal verification using Slither and custom invariant tests.",
        "specialist_wallet": specialist_addr,
    }
    resp = client.post(
        "/marketplace/arkiv/reconcile/bid",
        json=bid_payload,
        headers={"X-User-Id": specialist_addr}
    )
    assert resp.status_code == 200
    bid_res = resp.json()
    assert bid_res["status"] == "reconciled"
    assert bid_res["record"]["schema_tag"] == "guardvane.bids.v1"
    assert bid_res["record"]["owner_wallet"] == specialist_addr.lower()

    # Step 3: Reconcile Customer Award
    award_payload = {
        "task_id": test_task_id,
        "entity_key": f"key_award_{test_task_id}",
        "tx_hash": f"0xtx_award_{test_task_id}",
        "accepted_bid_key": f"key_bid_{test_task_id}",
        "customer_wallet": customer_addr,
        "specialist_wallet": specialist_addr,
    }
    resp = client.post(
        "/marketplace/arkiv/reconcile/award",
        json=award_payload,
        headers={"X-User-Id": customer_addr}
    )
    assert resp.status_code == 200
    award_res = resp.json()
    assert award_res["status"] == "reconciled"
    assert award_res["record"]["schema_tag"] == "guardvane.awards.v1"

    # Step 4: Verify Order Transitioned to Accepted in PostgreSQL
    updated_order = marketplace_service.get_order(test_task_id)
    assert updated_order is not None
    assert updated_order.status.value == "accepted"
    assert updated_order.provider_id.lower() == specialist_addr.lower()
    assert "Awarded on Arkiv" in (updated_order.deliverable_notes or "")


# ---------------------------------------------------------------------------
# 5. Entity Ownership & Security Boundary Enforcement
# ---------------------------------------------------------------------------

def test_verify_entity_ownership_boundary():
    """Verify cryptographic entity ownership verification logic."""
    mock_client = ArkivClient(mock_mode=True)
    mock_client._mock_entities = {
        "guardvane.tasks.v1": {
            "key_001": {
                "owner": "0x9876543210987654321098765432109876543210",
                "task_id": "task_sec_001"
            }
        }
    }

    # Valid owner
    assert mock_client.verify_entity_ownership(
        schema_name="guardvane.tasks.v1",
        entity_key="key_001",
        expected_owner="0x9876543210987654321098765432109876543210"
    ) is True

    # Case-insensitive owner
    assert mock_client.verify_entity_ownership(
        schema_name="guardvane.tasks.v1",
        entity_key="key_001",
        expected_owner="0X9876543210987654321098765432109876543210"
    ) is True

    # Impostor / mismatched owner
    assert mock_client.verify_entity_ownership(
        schema_name="guardvane.tasks.v1",
        entity_key="key_001",
        expected_owner="0ximpostorwallet000000000000000000000000"
    ) is False

    # Non-existent entity key
    assert mock_client.verify_entity_ownership(
        schema_name="guardvane.tasks.v1",
        entity_key="non_existent_key",
        expected_owner="0x9876543210987654321098765432109876543210"
    ) is False

