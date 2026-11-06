"""
Targeted Verification Tests for Guardvane Direct Security Services Marketplace.
Validates:
1. Canonical Catalogue endpoint (GET /marketplace/catalogue).
2. Human provider registration with canonical catalogue categories.
3. Automated provider registration rejected with 403 for ordinary users.
4. Provider profile editing with strict ownership check (403 for non-owners, 403 for platform agents).
5. User nickname persistence in PostgreSQL via PATCH /auth/me.
6. Direct customer order creation with PaymentStatus.PENDING.
7. Modular Payment Gateway config and payment verification (POST /marketplace/orders/{id}/pay) transitioning to PaymentStatus.VERIFIED.
8. Provider incoming request handling: Accept (transitions to in_progress) and Reject (requires rejection_reason).
"""

import uuid
from datetime import datetime, timezone
import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient
import siwe

from main import app
from marketplace.service import marketplace_service
from marketplace.schemas import OrderStatus, PaymentStatus
from marketplace.catalogue import CATALOGUE, public_catalogue, catalogue_ids

@pytest.fixture
def client():
    return TestClient(app)


def test_canonical_catalogue_endpoint(client):
    """Verify GET /marketplace/catalogue returns the 6 canonical services."""
    resp = client.get("/marketplace/catalogue")
    assert resp.status_code == 200
    catalogue = resp.json()
    assert len(catalogue) == 6

    expected_ids = {
        "prompt_engineering",
        "loop_engineering",
        "prompt_optimization",
        "prompt_security_analysis",
        "codebase_security",
        "application_security_testing"
    }
    actual_ids = {item["id"] for item in catalogue}
    assert expected_ids == actual_ids


def test_human_provider_registration_and_automated_rejection(client):
    """Verify human provider registration succeeds with canonical categories, while automated registration fails."""
    test_wallet = f"0x{uuid.uuid4().hex[:40]}"
    human_payload = {
        "display_name": "Dr. Sarah Connors",
        "title": "Principal AI Red Teamer",
        "provider_type": "human",
        "description": "Deep prompt injection testing and security auditing.",
        "skills": ["Prompt Injection", "OWASP LLM01", "Guardrail Bypasses"],
        "categories": ["prompt_security_analysis", "application_security_testing"],
        "wallet_address": test_wallet,
        "availability": "available",
        "status": "published"
    }

    human_id = None
    try:
        resp = client.post("/marketplace/providers/profile", json=human_payload)
        assert resp.status_code == 201
        data = resp.json()
        human_id = data["id"]
        assert human_id.startswith("prov_")
        assert data["provider_type"] == "human"
        assert data["wallet_address"] == test_wallet.lower()
        assert data["verified"] is False
        assert data.get("is_platform_managed", False) is False

        # Attempt to register automated agent as ordinary user -> 403 Forbidden
        auto_payload = {
            "display_name": "Rogue Agent",
            "title": "Autonomous Defense Bot",
            "provider_type": "automated",
            "description": "Attempting unauthorized automated agent creation.",
            "skills": ["Defense"],
            "categories": ["prompt_optimization"],
            "wallet_address": f"0x{uuid.uuid4().hex[:40]}",
            "endpoint_url": "https://example.com/defense",
            "availability": "available",
            "status": "published"
        }
        auto_resp = client.post("/marketplace/providers/profile", json=auto_payload)
        assert auto_resp.status_code == 403
        assert "Ordinary users cannot register as automated AI agents" in auto_resp.json()["detail"]
    finally:
        if human_id:
            db = marketplace_service.db
            with db._get_connection() as conn:
                conn.execute("DELETE FROM services WHERE provider_id = ?", (human_id,))
                conn.execute("DELETE FROM providers WHERE id = ?", (human_id,))
                conn.commit()


def test_provider_profile_ownership_enforcement(client):
    """Verify PATCH /marketplace/providers/{id} strictly requires matching wallet owner and rejects platform agent modification."""
    test_wallet = f"0x{uuid.uuid4().hex[:40]}"
    other_wallet = f"0x{uuid.uuid4().hex[:40]}"
    prov_id = f"prov_test_{uuid.uuid4().hex[:8]}"

    db = marketplace_service.db
    with db._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO providers (id, display_name, title, provider_type, description, skills, categories, wallet_address, x402_supported, availability, verified, status, is_platform_managed, reputation_metadata, created_at)
            VALUES (?, 'Original Name', 'Original Title', 'human', 'Original description', '[]', '["prompt_engineering"]', ?, 0, 'available', 0, 'published', 0, '{}', '2026-11-06')
            """,
            (prov_id, test_wallet.lower())
        )
        conn.commit()

    try:
        # 1. Update without wallet or with wrong wallet -> 403 Forbidden
        bad_resp = client.patch(
            f"/marketplace/providers/{prov_id}",
            headers={"X-Wallet-Address": other_wallet},
            json={"display_name": "Hacked Name"}
        )
        assert bad_resp.status_code == 403
        assert "only the wallet that owns this profile can edit it" in bad_resp.json()["detail"]

        # 2. Update with matching wallet -> 200 OK
        good_resp = client.patch(
            f"/marketplace/providers/{prov_id}",
            headers={"X-Wallet-Address": test_wallet},
            json={
                "display_name": "Updated Specialist Name",
                "title": "Senior Security Consultant",
                "description": "Updated security capabilities description.",
                "skills": ["Adversarial Testing", "Agent Auditing"],
                "categories": ["prompt_engineering", "codebase_security"],
                "availability": "busy"
            }
        )
        assert good_resp.status_code == 200
        updated = good_resp.json()
        assert updated["display_name"] == "Updated Specialist Name"
        assert updated["title"] == "Senior Security Consultant"
        assert updated["availability"] == "busy"
        assert "codebase_security" in updated["categories"]

        # 3. Attempt to update platform agent (prov_zerog) -> 403 Forbidden
        platform_resp = client.patch(
            "/marketplace/providers/prov_zerog",
            headers={"X-Wallet-Address": test_wallet},
            json={"display_name": "Tampered 0G"}
        )
        assert platform_resp.status_code == 403
        assert "Platform-managed agent profiles cannot be edited" in platform_resp.json()["detail"]
    finally:
        with db._get_connection() as conn:
            conn.execute("DELETE FROM providers WHERE id = ?", (prov_id,))
            conn.commit()


def test_nickname_persistence_patch_me(client):
    """Verify user can update their display name / nickname via PATCH /auth/me and have it persist in PostgreSQL."""
    account = Account.create()
    wallet_address = account.address

    # SIWE login
    nonce_resp = client.post("/auth/nonce", json={"wallet_address": wallet_address})
    assert nonce_resp.status_code == 200
    nonce = nonce_resp.json()["nonce"]

    domain = "localhost:8000"
    uri = "http://localhost:8000"
    issued_at = datetime.now(timezone.utc).isoformat()

    siwe_msg = siwe.SiweMessage(
        domain=domain,
        address=wallet_address,
        statement="Sign in to Guardvane AI Security Platform",
        uri=uri,
        version="1",
        chain_id=1,
        nonce=nonce,
        issued_at=issued_at
    )
    message_str = siwe_msg.prepare_message()
    signed = account.sign_message(encode_defunct(text=message_str))
    signature = signed.signature.hex()

    verify_resp = client.post("/auth/verify", json={
        "message": message_str,
        "signature": signature
    })
    assert verify_resp.status_code == 200
    cookies = verify_resp.cookies

    # Initial profile check
    me_resp = client.get("/auth/me", cookies=cookies)
    assert me_resp.status_code == 200
    assert me_resp.json()["wallet_address"] == wallet_address.lower()

    # Update nickname
    patch_resp = client.patch("/auth/me", json={"nickname": "Satoshi Specialist"}, cookies=cookies)
    assert patch_resp.status_code == 200
    updated_user = patch_resp.json()
    assert updated_user["nickname"] == "Satoshi Specialist"

    # Verify persistent in subsequent GET /auth/me
    me_resp2 = client.get("/auth/me", cookies=cookies)
    assert me_resp2.status_code == 200
    assert me_resp2.json()["nickname"] == "Satoshi Specialist"


def test_direct_order_lifecycle_and_modular_payment(client):
    """Verify order creation with pending payment, payment verification, and provider acceptance/rejection."""
    prov_id = f"prov_direct_{uuid.uuid4().hex[:8]}"
    srv_id = f"srv_direct_{uuid.uuid4().hex[:8]}"
    cust_wallet = f"0x{uuid.uuid4().hex[:40]}"
    prov_wallet = f"0x{uuid.uuid4().hex[:40]}"

    db = marketplace_service.db
    with db._get_connection() as conn:
        conn.execute(
            """
            INSERT INTO providers (id, display_name, title, provider_type, description, skills, categories, wallet_address, x402_supported, availability, verified, status, is_platform_managed, reputation_metadata, created_at)
            VALUES (?, 'Direct Specialist', 'Auditor', 'human', 'Direct auditing specialist.', '[]', '["prompt_engineering"]', ?, 0, 'available', 1, 'published', 0, '{}', '2026-11-06')
            """,
            (prov_id, prov_wallet.lower())
        )
        conn.execute(
            """
            INSERT INTO services (id, provider_id, title, description, category, price, currency, estimated_delivery, supported_tasks, execution_type, is_active, created_at)
            VALUES (?, ?, 'Direct Assessment', 'Detailed prompt security review.', 'prompt_engineering', 150.0, 'USD', '24h', '[]', 'manual', 1, '2026-11-06')
            """,
            (srv_id, prov_id)
        )
        conn.commit()

    order_id = None
    order_id_2 = None
    try:
        # Check payments config endpoint
        cfg_resp = client.get("/marketplace/payments/config")
        assert cfg_resp.status_code == 200
        cfg_data = cfg_resp.json()
        assert "mode" in cfg_data
        assert cfg_data["network"] == "hedera"
        assert cfg_data["separate_from_arkiv"] is True

        # 1. Customer places order
        order_payload = {
            "service_id": srv_id,
            "prompt_content": "Analyze system prompt: You are a financial chatbot.",
            "requirements": "Verify isolation against prompt extraction.",
            "customer_id": cust_wallet.lower(),
            "customer_name": "Financial Corp"
        }
        order_resp = client.post("/marketplace/orders", json=order_payload)
        assert order_resp.status_code == 201
        order = order_resp.json()
        order_id = order["id"]

        assert order["status"] == OrderStatus.REQUESTED.value
        assert order["payment_status"] == PaymentStatus.PENDING.value
        assert order["execution_type"] == "manual"

        # 2. Complete payment via POST /marketplace/orders/{id}/pay
        pay_resp = client.post(
            f"/marketplace/orders/{order_id}/pay",
            json={
                "payment_method": "hedera_x402_escrow",
                "payer_wallet": cust_wallet,
                "proof": "test-receipt"
            }
        )
        assert pay_resp.status_code == 200
        paid_data = pay_resp.json()
        assert paid_data["payment_status"] == PaymentStatus.VERIFIED.value

        # 3. Provider accepts request -> in_progress
        accept_resp = client.patch(
            f"/marketplace/orders/{order_id}/status",
            headers={"X-User-Id": prov_id, "X-User-Role": "provider"},
            json={"status": "in_progress"}
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == OrderStatus.IN_PROGRESS.value

        # 4. Create second order to test provider rejection with required reason
        order_resp_2 = client.post("/marketplace/orders", json=order_payload)
        assert order_resp_2.status_code == 201
        order_id_2 = order_resp_2.json()["id"]

        # Reject without reason should fail with 400
        bad_reject = client.patch(
            f"/marketplace/orders/{order_id_2}/status",
            headers={"X-User-Id": prov_id, "X-User-Role": "provider"},
            json={"status": "rejected"}
        )
        assert bad_reject.status_code == 400
        assert "Rejection reason is required" in bad_reject.json()["detail"]

        # Reject with reason succeeds
        good_reject = client.patch(
            f"/marketplace/orders/{order_id_2}/status",
            headers={"X-User-Id": prov_id, "X-User-Role": "provider"},
            json={
                "status": "rejected",
                "rejection_reason": "Out of capacity for current evaluation cycle"
            }
        )
        assert good_reject.status_code == 200
        rejected_order = good_reject.json()
        assert rejected_order["status"] == OrderStatus.REJECTED.value
        assert rejected_order["rejection_reason"] == "Out of capacity for current evaluation cycle"
    finally:
        with db._get_connection() as conn:
            ids_to_clean = [o for o in [order_id, order_id_2] if o]
            if ids_to_clean:
                conn.execute(f"DELETE FROM orders WHERE id IN ({','.join(['?']*len(ids_to_clean))})", ids_to_clean)
            conn.execute("DELETE FROM services WHERE provider_id = ?", (prov_id,))
            conn.execute("DELETE FROM providers WHERE id = ?", (prov_id,))
            conn.commit()
