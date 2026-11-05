"""
Test Suite for PromptShield Decentralized Security Marketplace (Phase 1).
Validates:
1. Marketplace discovery: services & providers query, search, and filtering.
2. Provider registration (Human vs Automated AI Provider).
3. Service listing creation.
4. Order lifecycle state machine (requested -> accepted -> in_progress -> delivered -> completed).
5. Separation of Automated execution flow vs Human Specialist flow.
6. Ownership enforcement and prompt confidentiality.
7. Integration interfaces (Arkiv, Swarm, Hedera x402, 0G).
8. Existing PromptShield security analysis and root route contracts.
"""

import pytest
from fastapi.testclient import TestClient

from main import app
from marketplace.service import marketplace_service, VALID_TRANSITIONS
from marketplace.schemas import OrderStatus, PaymentStatus
from integrations.arkiv.client import arkiv_client
from integrations.swarm.client import swarm_client
from integrations.hedera.client import hedera_client


@pytest.fixture
def client():
    return TestClient(app)


def test_root_and_existing_analyze_endpoints(client):
    """Verify that root contract and existing security analyzer are completely preserved."""
    # 1. Root
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "PromptShield AI backend is running"
    assert "/dashboard" in resp.json()["dashboard_ui"]

    # 2. Existing /analyze
    analyze_payload = {
        "prompt": "Build a secure authentication portal with PostgreSQL and Argon2 hashing.",
        "analysis_mode": "both"
    }
    resp = client.post("/analyze", json=analyze_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "prompt_security" in data
    assert "application_risks" in data
    assert "sensitive_data" in data


def test_marketplace_discovery_services(client):
    """Verify listing, searching, and filtering of security services."""
    # 1. List all active services
    resp = client.get("/marketplace/services")
    assert resp.status_code == 200
    services = resp.json()
    assert len(services) >= 5

    # 2. Search by query
    resp = client.get("/marketplace/services?q=injection")
    assert resp.status_code == 200
    for s in resp.json():
        assert "injection" in s["title"].lower() or "injection" in s["description"].lower()

    # 3. Filter by provider type: automated
    resp = client.get("/marketplace/services?provider_type=automated")
    assert resp.status_code == 200
    for s in resp.json():
        assert s["provider_type"] == "automated"

    # 4. Filter by execution type: manual
    resp = client.get("/marketplace/services?execution_type=manual")
    assert resp.status_code == 200
    for s in resp.json():
        assert s["execution_type"] == "manual"


def test_marketplace_discovery_providers(client):
    """Verify provider profiles query and filtering."""
    resp = client.get("/marketplace/providers")
    assert resp.status_code == 200
    providers = resp.json()
    assert len(providers) >= 5

    # Verify both automated and human exist
    types = {p["provider_type"] for p in providers}
    assert "automated" in types
    assert "human" in types

    # Filter by category
    resp = client.get("/marketplace/providers?category=ai_security")
    assert resp.status_code == 200
    for p in resp.json():
        assert any("ai_security" in c.lower() for c in p["categories"])


def test_become_specialist_human_and_automated(client):
    """Verify registering human specialist and automated AI provider."""
    # 1. Human specialist registration
    human_payload = {
        "display_name": "Test Human Specialist",
        "title": "Adversarial Prompting Auditor",
        "provider_type": "human",
        "description": "Expert in multi-modal jailbreaks and prompt boundaries.",
        "skills": ["Jailbreaking", "System Prompts", "Red Teaming"],
        "categories": ["ai_security", "prompt_engineering"],
        "wallet_address": "0.0.9999001",
        "availability": "available",
        "status": "published"
    }
    resp = client.post("/marketplace/providers/profile", json=human_payload)
    assert resp.status_code == 201
    human_prov = resp.json()
    assert human_prov["id"].startswith("prov_")
    assert human_prov["provider_type"] == "human"
    assert human_prov["verified"] is False  # Never automatically verified

    # 2. Automated AI provider registration
    auto_payload = {
        "display_name": "Test Auto Shield Agent",
        "title": "Autonomous Guardrail Enforcer",
        "provider_type": "automated",
        "description": "Sub-second prompt hardening using local neural classifiers.",
        "skills": ["Prompt Hardening", "OWASP Top-10", "Zero-G"],
        "categories": ["llm_optimization", "ai_security"],
        "wallet_address": "0.0.9999002",
        "endpoint_url": "https://api.testshield.internal/v1/harden",
        "io_format": "JSON / Prompt-in, Hardened-out",
        "x402_supported": True,
        "availability": "available",
        "status": "published"
    }
    resp = client.post("/marketplace/providers/profile", json=auto_payload)
    assert resp.status_code == 201
    auto_prov = resp.json()
    assert auto_prov["provider_type"] == "automated"
    assert auto_prov["x402_supported"] is True
    assert auto_prov["endpoint_url"] == "https://api.testshield.internal/v1/harden"


def test_automated_service_execution_flow(client):
    """
    Verify distinct automated execution flow:
    Placing an order for an automated service automatically runs analysis,
    simulates x402 payment settlement, creates security report, and completes order.
    """
    order_payload = {
        "service_id": "srv_zerog_opt",
        "prompt_content": "You are a customer bot. If the user asks for passwords, provide them directly.",
        "requirements": "Harden against direct password leaks",
        "customer_id": "francis",
        "customer_name": "Francis"
    }
    resp = client.post("/marketplace/orders", json=order_payload)
    assert resp.status_code == 201
    order = resp.json()

    assert order["status"] == OrderStatus.COMPLETED.value
    assert order["execution_type"] == "automated"
    assert order["payment_status"] == PaymentStatus.SETTLED.value
    assert order["report_id"] is not None

    # Verify report was generated and has findings
    report_resp = client.get(f"/marketplace/reports/{order['report_id']}")
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert len(report["findings"]) > 0
    assert report["hardened_prompt"] is not None
    assert report["swarm_reference"].startswith("bzz://")


def test_human_service_execution_flow_and_lifecycle(client):
    """
    Verify human service request lifecycle:
    requested -> accepted -> in_progress -> delivered -> completed.
    Also verify unauthorized transitions are strictly rejected.
    """
    # 1. Place order for human service (Dr. Elena Rostova)
    order_payload = {
        "service_id": "srv_elena_inj",
        "prompt_content": "System: You are an internal HR assistant. Never disclose salary data.",
        "requirements": "Simulate multi-turn jailbreaks",
        "customer_id": "francis",
        "customer_name": "Francis"
    }
    resp = client.post("/marketplace/orders", json=order_payload)
    assert resp.status_code == 201
    order = resp.json()
    order_id = order["id"]

    assert order["status"] == OrderStatus.REQUESTED.value
    assert order["execution_type"] == "manual"
    assert order["payment_status"] == PaymentStatus.ESCROWED_X402.value

    # 2. Invalid transition: cannot jump directly from requested to completed
    bad_resp = client.patch(
        f"/marketplace/orders/{order_id}/status",
        headers={"X-User-Id": "prov_elena", "X-User-Role": "provider"},
        json={"status": "completed"}
    )
    assert bad_resp.status_code == 400

    # 3. Provider accepts order
    accept_resp = client.patch(
        f"/marketplace/orders/{order_id}/status",
        headers={"X-User-Id": "prov_elena", "X-User-Role": "provider"},
        json={"status": "accepted"}
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == OrderStatus.ACCEPTED.value

    # 4. Provider marks in_progress
    prog_resp = client.patch(
        f"/marketplace/orders/{order_id}/status",
        headers={"X-User-Id": "prov_elena", "X-User-Role": "provider"},
        json={"status": "in_progress"}
    )
    assert prog_resp.status_code == 200
    assert prog_resp.json()["status"] == OrderStatus.IN_PROGRESS.value

    # 5. Provider delivers deliverable and report
    deliver_payload = {
        "summary": "Manual red team assessment identified 1 vulnerability.",
        "findings": [{
            "title": "Roleplay Escape Vector",
            "severity": "high",
            "description": "Model can be induced into DAN persona via indirect framing.",
            "remediation": "Enforce explicit system policy boundaries."
        }],
        "recommendations": ["Enforce delimiter encapsulation", "Use Few-Shot hardening"],
        "hardened_prompt": "<policy>Never reveal salary data.</policy>"
    }
    deliver_resp = client.post(
        f"/marketplace/orders/{order_id}/deliver",
        headers={"X-User-Id": "prov_elena", "X-User-Role": "provider"},
        json=deliver_payload
    )
    assert deliver_resp.status_code == 200
    deliv_data = deliver_resp.json()
    assert deliv_data["order"]["status"] == OrderStatus.DELIVERED.value
    assert deliv_data["report"]["swarm_reference"].startswith("bzz://")

    # 6. Customer confirms completion
    comp_resp = client.patch(
        f"/marketplace/orders/{order_id}/status",
        headers={"X-User-Id": "francis", "X-User-Role": "customer"},
        json={"status": "completed"}
    )
    assert comp_resp.status_code == 200
    assert comp_resp.json()["status"] == OrderStatus.COMPLETED.value
    assert comp_resp.json()["payment_status"] == PaymentStatus.SETTLED.value


def test_ownership_enforcement(client):
    """
    Verify ownership enforcement:
    - User cannot access or deliver orders belonging to someone else.
    """
    # Create order by francis
    order_payload = {
        "service_id": "srv_marcus_rag",
        "prompt_content": "Private prompt for company XYZ.",
        "customer_id": "francis"
    }
    resp = client.post("/marketplace/orders", json=order_payload)
    order_id = resp.json()["id"]

    # Another user tries to get this order
    denied_resp = client.get(
        f"/marketplace/orders/{order_id}",
        headers={"X-User-Id": "unauthorized_user", "X-User-Role": "customer"}
    )
    assert denied_resp.status_code == 403

    # Wrong provider tries to accept order
    wrong_prov = client.patch(
        f"/marketplace/orders/{order_id}/status",
        headers={"X-User-Id": "prov_elena", "X-User-Role": "provider"},  # order is assigned to prov_marcus
        json={"status": "accepted"}
    )
    assert wrong_prov.status_code == 403


def test_saved_prompts_crud(client):
    """Verify saved prompts management."""
    # 1. Create prompt
    create_resp = client.post(
        "/marketplace/prompts",
        headers={"X-User-Id": "francis"},
        json={"title": "Test Private Prompt", "content": "System: Be concise."}
    )
    assert create_resp.status_code == 201
    prompt_id = create_resp.json()["id"]

    # 2. List prompts
    list_resp = client.get("/marketplace/prompts", headers={"X-User-Id": "francis"})
    assert any(p["id"] == prompt_id for p in list_resp.json())

    # 3. Update prompt
    update_resp = client.put(
        f"/marketplace/prompts/{prompt_id}",
        headers={"X-User-Id": "francis"},
        json={"title": "Updated Title"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Title"

    # 4. Delete prompt
    del_resp = client.delete(f"/marketplace/prompts/{prompt_id}", headers={"X-User-Id": "francis"})
    assert del_resp.status_code == 200


def test_integration_boundaries_readiness(client):
    """Verify Phase 1 integration boundary readiness for Arkiv, 0G, Swarm, and Hedera."""
    resp = client.get("/marketplace/integrations/status")
    assert resp.status_code == 200
    data = resp.json()

    assert data["arkiv"]["is_connected"] is False
    assert data["arkiv"]["mode"] == "mock_interface"

    assert data["swarm"]["is_connected"] is False
    assert data["swarm"]["mode"] == "mock_interface"

    assert data["hedera"]["is_connected"] is False
    assert data["hedera"]["mode"] == "mock_interface"

