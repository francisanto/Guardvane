"""
Targeted Verification Tests for PostgreSQL, MetaMask SIWE Authentication,
Multi-Role Isolation, and Ownership Enforcement.
"""

from datetime import datetime, timedelta, timezone
import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient
import siwe
from sqlalchemy.orm import sessionmaker

from db.database import Base, SessionLocal, engine
from db.models import AuthNonce, Order, Provider, SavedPrompt, Service, User, UserRole
from main import app

client = TestClient(app)


def test_1_database_connection_and_models():
    """Verify PostgreSQL connectivity and schema tables."""
    with engine.connect() as conn:
        assert conn is not None
    session = SessionLocal()
    try:
        users_count = session.query(User).count()
        assert users_count >= 0
    finally:
        session.close()


def test_2_nonce_generation():
    """Verify POST /auth/nonce returns valid EIP-4361 nonce."""
    wallet = Account.create().address
    resp = client.post("/auth/nonce", json={"wallet_address": wallet})
    assert resp.status_code == 200
    data = resp.json()
    assert "nonce" in data
    assert len(data["nonce"]) >= 8
    assert data["wallet_address"] == wallet.lower()
    assert "expires_at" in data


def test_3_valid_signature_flow_and_registration():
    """Verify complete SIWE flow: nonce -> sign -> verify -> user creation + cookie."""
    account = Account.create()
    wallet_address = account.address

    # 1. Request nonce
    nonce_resp = client.post("/auth/nonce", json={"wallet_address": wallet_address})
    assert nonce_resp.status_code == 200
    nonce = nonce_resp.json()["nonce"]

    # 2. Build SIWE message
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

    # 3. Sign message with private key
    signed = account.sign_message(encode_defunct(text=message_str))
    signature = signed.signature.hex()

    # 4. Verify on backend
    verify_resp = client.post("/auth/verify", json={
        "message": message_str,
        "signature": signature
    })
    assert verify_resp.status_code == 200
    res_data = verify_resp.json()
    assert res_data["success"] is True
    assert "guardvane_session" in verify_resp.cookies
    user = res_data["user"]
    assert user["wallet_address"] == wallet_address.lower()
    assert "customer" in user["roles"]

    # 5. Access /auth/me with session cookie
    me_resp = client.get("/auth/me", cookies=verify_resp.cookies)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["wallet_address"] == wallet_address.lower()
    assert me_data["id"] == user["id"]


def test_4_invalid_signature_rejection():
    """Verify that an invalid signature from the wrong key is rejected."""
    account_a = Account.create()
    account_b = Account.create()

    # Nonce for A
    nonce_resp = client.post("/auth/nonce", json={"wallet_address": account_a.address})
    nonce = nonce_resp.json()["nonce"]

    siwe_msg = siwe.SiweMessage(
        domain="localhost:8000",
        address=account_a.address,
        statement="Sign in to Guardvane",
        uri="http://localhost:8000",
        version="1",
        chain_id=1,
        nonce=nonce,
        issued_at=datetime.now(timezone.utc).isoformat()
    )
    message_str = siwe_msg.prepare_message()

    # Sign with account B (mismatched key)
    signed = account_b.sign_message(encode_defunct(text=message_str))
    signature = signed.signature.hex()

    verify_resp = client.post("/auth/verify", json={
        "message": message_str,
        "signature": signature
    })
    assert verify_resp.status_code == 401
    assert "Invalid wallet signature" in verify_resp.json()["detail"]


def test_5_expired_nonce_rejection():
    """Verify that an expired nonce cannot be used."""
    account = Account.create()
    wallet_address = account.address

    # Manually insert an expired nonce using active SessionLocal
    session = SessionLocal()
    expired_nonce_val = siwe.generate_nonce()
    past_time = datetime.now(timezone.utc) - timedelta(minutes=15)
    expired_record = AuthNonce(
        id=f"expired_{expired_nonce_val}",
        wallet_address=wallet_address.lower(),
        nonce=expired_nonce_val,
        expires_at=past_time,
        used=False,
        created_at=past_time - timedelta(minutes=5)
    )
    session.add(expired_record)
    session.commit()
    session.close()

    siwe_msg = siwe.SiweMessage(
        domain="localhost:8000",
        address=wallet_address,
        statement="Sign in to Guardvane",
        uri="http://localhost:8000",
        version="1",
        chain_id=1,
        nonce=expired_nonce_val,
        issued_at=datetime.now(timezone.utc).isoformat()
    )
    message_str = siwe_msg.prepare_message()
    signed = account.sign_message(encode_defunct(text=message_str))
    signature = signed.signature.hex()

    verify_resp = client.post("/auth/verify", json={
        "message": message_str,
        "signature": signature
    })
    assert verify_resp.status_code == 400
    assert "expired" in verify_resp.json()["detail"].lower()


def test_6_reused_nonce_rejection():
    """Verify single-use status: nonce replay is rejected."""
    account = Account.create()
    nonce_resp = client.post("/auth/nonce", json={"wallet_address": account.address})
    nonce = nonce_resp.json()["nonce"]

    siwe_msg = siwe.SiweMessage(
        domain="localhost:8000",
        address=account.address,
        statement="Sign in to Guardvane",
        uri="http://localhost:8000",
        version="1",
        chain_id=1,
        nonce=nonce,
        issued_at=datetime.now(timezone.utc).isoformat()
    )
    message_str = siwe_msg.prepare_message()
    signed = account.sign_message(encode_defunct(text=message_str))
    signature = signed.signature.hex()

    # First attempt: succeeds
    resp1 = client.post("/auth/verify", json={"message": message_str, "signature": signature})
    assert resp1.status_code == 200

    # Second attempt: fails with replay detection
    resp2 = client.post("/auth/verify", json={"message": message_str, "signature": signature})
    assert resp2.status_code == 400
    assert "already been used" in resp2.json()["detail"].lower()


def test_7_existing_wallet_login():
    """Verify logging in with the same wallet retrieves existing account."""
    account = Account.create()

    # First login
    n1 = client.post("/auth/nonce", json={"wallet_address": account.address}).json()["nonce"]
    m1 = siwe.SiweMessage(domain="localhost:8000", address=account.address, statement="Login 1", uri="http://localhost:8000", version="1", chain_id=1, nonce=n1, issued_at=datetime.now(timezone.utc).isoformat()).prepare_message()
    s1 = account.sign_message(encode_defunct(text=m1)).signature.hex()
    r1 = client.post("/auth/verify", json={"message": m1, "signature": s1}).json()
    user_id_1 = r1["user"]["id"]

    # Second login
    n2 = client.post("/auth/nonce", json={"wallet_address": account.address}).json()["nonce"]
    m2 = siwe.SiweMessage(domain="localhost:8000", address=account.address, statement="Login 2", uri="http://localhost:8000", version="1", chain_id=1, nonce=n2, issued_at=datetime.now(timezone.utc).isoformat()).prepare_message()
    s2 = account.sign_message(encode_defunct(text=m2)).signature.hex()
    r2 = client.post("/auth/verify", json={"message": m2, "signature": s2}).json()
    user_id_2 = r2["user"]["id"]

    assert user_id_1 == user_id_2


def test_8_logout():
    """Verify POST /auth/logout clears session."""
    account = Account.create()
    n = client.post("/auth/nonce", json={"wallet_address": account.address}).json()["nonce"]
    m = siwe.SiweMessage(domain="localhost:8000", address=account.address, statement="Login", uri="http://localhost:8000", version="1", chain_id=1, nonce=n, issued_at=datetime.now(timezone.utc).isoformat()).prepare_message()
    s = account.sign_message(encode_defunct(text=m)).signature.hex()
    login_resp = client.post("/auth/verify", json={"message": m, "signature": s})

    # Logout
    logout_resp = client.post("/auth/logout", cookies=login_resp.cookies)
    assert logout_resp.status_code == 200
    # Cookie is deleted
    assert logout_resp.cookies.get("guardvane_session") == "" or "guardvane_session" not in logout_resp.cookies


def test_9_private_prompt_ownership_isolation():
    """Verify that Prompt created by Wallet A cannot be retrieved or accessed by Wallet B."""
    account_a = Account.create()
    account_b = Account.create()

    # Login Wallet A
    n_a = client.post("/auth/nonce", json={"wallet_address": account_a.address}).json()["nonce"]
    m_a = siwe.SiweMessage(domain="localhost:8000", address=account_a.address, statement="Sign A", uri="http://localhost:8000", version="1", chain_id=1, nonce=n_a, issued_at=datetime.now(timezone.utc).isoformat()).prepare_message()
    sig_a = account_a.sign_message(encode_defunct(text=m_a)).signature.hex()
    resp_a = client.post("/auth/verify", json={"message": m_a, "signature": sig_a})
    cookies_a = resp_a.cookies

    # Login Wallet B
    n_b = client.post("/auth/nonce", json={"wallet_address": account_b.address}).json()["nonce"]
    m_b = siwe.SiweMessage(domain="localhost:8000", address=account_b.address, statement="Sign B", uri="http://localhost:8000", version="1", chain_id=1, nonce=n_b, issued_at=datetime.now(timezone.utc).isoformat()).prepare_message()
    sig_b = account_b.sign_message(encode_defunct(text=m_b)).signature.hex()
    resp_b = client.post("/auth/verify", json={"message": m_b, "signature": sig_b})
    cookies_b = resp_b.cookies

    # Wallet A saves a prompt
    create_resp = client.post("/marketplace/prompts", json={
        "title": "Confidential Prompt A",
        "content": "Super secret instructions for Wallet A"
    }, cookies=cookies_a)
    assert create_resp.status_code == 201
    prompt_a_id = create_resp.json()["id"]

    # Wallet A lists prompts: sees prompt
    list_a = client.get("/marketplace/prompts", cookies=cookies_a).json()
    assert any(p["id"] == prompt_a_id for p in list_a)

    # Wallet B lists prompts: does NOT see Wallet A's prompt
    list_b = client.get("/marketplace/prompts", cookies=cookies_b).json()
    assert not any(p["id"] == prompt_a_id for p in list_b)

    # Wallet B attempts to update Wallet A's prompt: rejected (404 not found in user's scope)
    update_resp = client.put(f"/marketplace/prompts/{prompt_a_id}", json={
        "title": "Hacked Title"
    }, cookies=cookies_b)
    assert update_resp.status_code == 404

    # Wallet B attempts to delete Wallet A's prompt: rejected (404 not found)
    delete_resp = client.delete(f"/marketplace/prompts/{prompt_a_id}", cookies=cookies_b)
    assert delete_resp.status_code == 404


def test_10_order_ownership_access_control():
    """Verify that an order created by Customer A cannot be accessed by unrelated Customer B."""
    client_a = TestClient(app)
    client_b = TestClient(app)

    wallet_a = "0x1111111111111111111111111111111111111111"
    wallet_b = "0x2222222222222222222222222222222222222222"

    order_payload = {
        "service_id": "srv_zerog_opt",
        "prompt_content": "Analyze and audit this prompt",
        "requirements": "Target OWASP LLM-01 prompt injection"
    }
    # Customer A creates order
    create_res = client_a.post(
        "/marketplace/orders",
        json=order_payload,
        headers={"X-User-Id": wallet_a, "X-User-Role": "customer"}
    )
    assert create_res.status_code == 201
    order_id = create_res.json()["id"]

    # Customer A can view order
    get_res_1 = client_a.get(
        f"/marketplace/orders/{order_id}",
        headers={"X-User-Id": wallet_a, "X-User-Role": "customer"}
    )
    assert get_res_1.status_code == 200

    # Customer B (unrelated) attempts to view order: 403 Forbidden
    get_res_2 = client_b.get(
        f"/marketplace/orders/{order_id}",
        headers={"X-User-Id": wallet_b, "X-User-Role": "customer"}
    )
    assert get_res_2.status_code == 403
    assert "denied" in get_res_2.json()["detail"].lower()


def test_11_lowercase_address_siwe_verification():
    """Verify that a SIWE message with all-lowercase address (non-EIP-55 format) is gracefully handled."""
    account = Account.create()
    addr_lower = account.address.lower()

    # Request nonce
    nonce_resp = client.post("/auth/nonce", json={"wallet_address": addr_lower})
    assert nonce_resp.status_code == 200
    data = nonce_resp.json()
    nonce = data["nonce"]
    assert "checksum_address" in data

    # Create SIWE message with all lowercase address (like in user screenshot)
    siwe_text_lower = f"""localhost:8000 wants you to sign in with your Ethereum account:
{addr_lower}

Sign in to Guardvane

URI: http://localhost:8000
Version: 1
Chain ID: 1
Nonce: {nonce}
Issued At: {datetime.now(timezone.utc).isoformat()}"""

    signed = account.sign_message(encode_defunct(text=siwe_text_lower))
    signature = signed.signature.hex()

    verify_resp = client.post("/auth/verify", json={
        "message": siwe_text_lower,
        "signature": signature
    })
    assert verify_resp.status_code == 200
    res = verify_resp.json()
    assert res["success"] is True
    assert res["user"]["wallet_address"] == addr_lower

