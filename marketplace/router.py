"""
FastAPI Router for PromptShield Marketplace.
Exposes endpoints for discovery, provider profiles, order lifecycle, security reports,
saved prompts, and integration status queries.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, status

from auth.service import decode_session_token

from integrations.arkiv.client import arkiv_client
from integrations.arkiv.schemas import (
    ArkivSyncStatus,
    ArkivSpecialistProfile,
    ArkivServiceListing,
    ArkivSecurityTask,
    ArkivSpecialistBid,
    ArkivAwardRecord,
    ReconcileTaskRequest,
    ReconcileBidRequest,
    ReconcileAwardRequest,
)
from integrations.hedera.client import hedera_client
from integrations.swarm.client import swarm_client
from integrations.zero_g import zero_g_optimizer, ZeroGClient
from marketplace.schemas import (
    DashboardStats,
    DeliverOrderRequest,
    IntegrationStatusResponse,
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
    PaymentConfirmRequest,
    ProviderCreate,
    ProviderResponse,
    ProviderUpdate,
    SavedPromptCreate,
    SavedPromptResponse,
    SavedPromptUpdate,
    SecurityReportResponse,
    ServiceCreate,
    ServiceUpdate,
    ServiceResponse,
    TicketCreate,
)
from marketplace.service import marketplace_service

router = APIRouter()


def get_current_user(
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    guardvane_session: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """
    Extracts current authenticated identity and active role.
    Prioritizes MetaMask SIWE HttpOnly cookie and Bearer tokens,
    with backward compatibility for X-User-Id and X-Wallet-Address in development and automated testing.
    """
    token = guardvane_session
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    x_wallet = x_wallet_address or request.headers.get("x-wallet-address")

    if token:
        payload = decode_session_token(token)
        if payload and "wallet_address" in payload:
            cookie_wallet = payload["wallet_address"]
            # If user switched accounts in MetaMask, prioritize active header
            wallet_addr = x_wallet if (x_wallet and x_wallet.lower() != cookie_wallet.lower()) else cookie_wallet
            roles = list(payload.get("roles", ["customer"]))
            try:
                prov = marketplace_service.get_provider_by_wallet(wallet_addr)
                if prov and "provider" not in roles:
                    roles.append("provider")
            except Exception:
                pass
            active_role = x_user_role.lower() if (x_user_role and x_user_role.lower() in roles) else (
                "provider" if "provider" in roles and x_user_role == "provider" else (roles[0] if roles else "customer")
            )
            return {
                "user_id": wallet_addr,
                "sub": payload.get("sub"),
                "role": active_role,
                "roles": roles,
                "wallet_address": wallet_addr
            }

    user_id = x_wallet or x_user_id or "francis"
    wallet = x_wallet or (user_id if str(user_id).startswith("0x") else None)
    role = (x_user_role or "customer").lower()
    roles = [role]
    if wallet:
        try:
            prov = marketplace_service.get_provider_by_wallet(wallet)
            if prov and "provider" not in roles:
                roles.append("provider")
                if x_user_role == "provider":
                    role = "provider"
        except Exception:
            pass

    return {
        "user_id": user_id,
        "role": role,
        "roles": roles,
        "wallet_address": wallet
    }


# ---------------------------------------------------------------------------
# Marketplace Discovery & Services
# ---------------------------------------------------------------------------

@router.get("/services", response_model=List[ServiceResponse])
def list_services(
    q: Optional[str] = Query(None, description="Search keyword in service title or description"),
    category: Optional[str] = Query(None, description="Category filter (ai_security, prompt_engineering, rag_security, etc.)"),
    provider_type: Optional[str] = Query(None, description="Filter: 'human' or 'automated'"),
    execution_type: Optional[str] = Query(None, description="Filter: 'manual' or 'automated'"),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Browse published security services with full filtering and search.
    """
    return marketplace_service.list_services(
        query=q,
        category=category,
        provider_type=provider_type,
        execution_type=execution_type,
        min_price=min_price,
        max_price=max_price,
        limit=limit,
        offset=offset
    )


@router.get("/services/{service_id}", response_model=ServiceResponse)
def get_service(service_id: str):
    """
    Retrieve service details including provider credentials and estimated delivery.
    """
    srv = marketplace_service.get_service(service_id)
    if not srv:
        raise HTTPException(status_code=404, detail=f"Service '{service_id}' not found.")
    return srv


@router.post("/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    data: ServiceCreate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Create a new security service listing. Requires provider role or registers under current user ID.
    """
    provider_id = data.provider_id or auth["user_id"]
    # Check if provider exists
    prov = marketplace_service.get_provider(provider_id)
    if not prov:
        raise HTTPException(
            status_code=400,
            detail=f"Provider '{provider_id}' is not registered. Register provider profile before listing services."
        )

    return marketplace_service.create_service(data, provider_id=provider_id)


@router.patch("/services/{service_id}", response_model=ServiceResponse)
def update_service(
    service_id: str,
    data: ServiceUpdate,
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update an existing service offering. Only the owning specialist can modify.
    """
    prov_id = auth.get("wallet_address") or auth.get("user_id")
    prov = marketplace_service.get_provider_by_wallet(prov_id) if prov_id else None
    effective_id = prov.id if prov else prov_id
    try:
        return marketplace_service.update_service(service_id, data, provider_id=effective_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/services/{service_id}")
def delete_service(
    service_id: str,
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a service offering. Only the owning specialist can delete.
    """
    prov_id = auth.get("wallet_address") or auth.get("user_id")
    prov = marketplace_service.get_provider_by_wallet(prov_id) if prov_id else None
    effective_id = prov.id if prov else prov_id
    try:
        marketplace_service.delete_service(service_id, provider_id=effective_id)
        return {"status": "deleted", "service_id": service_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@router.get("/providers", response_model=List[ProviderResponse])
def list_providers(
    q: Optional[str] = Query(None, description="Search specialist name, skills or description"),
    category: Optional[str] = Query(None, description="Expertise category"),
    provider_type: Optional[str] = Query(None, description="Filter: 'human' or 'automated'"),
    availability: Optional[str] = Query(None, description="Filter: 'available', 'busy', 'offline'"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Discover registered AI security specialists and automated defense providers.
    """
    return marketplace_service.list_providers(
        query=q,
        category=category,
        provider_type=provider_type,
        availability=availability,
        limit=limit,
        offset=offset
    )


@router.get("/providers/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: str):
    """
    Retrieve provider profile, capabilities, reputation metrics and published services.
    """
    prov = marketplace_service.get_provider(provider_id)
    if not prov:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    return prov


@router.post("/providers/profile", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED)
def create_provider_profile(
    data: ProviderCreate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Register a new specialist profile (Human Security Provider).
    """
    try:
        return marketplace_service.create_provider_profile(data, user_id=auth["user_id"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch("/providers/{provider_id}", response_model=ProviderResponse)
def update_provider_profile(
    provider_id: str,
    data: ProviderUpdate,
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update provider profile. Enforces ownership: only the wallet that owns this profile
    can edit it. Platform-managed agents cannot be edited by users.
    """
    actor_wallet = auth.get("wallet_address") or auth.get("user_id")
    try:
        return marketplace_service.update_provider_profile(
            provider_id=provider_id,
            data=data,
            actor_wallet=actor_wallet
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))



# ---------------------------------------------------------------------------
# Orders & Requests
# ---------------------------------------------------------------------------

@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    data: OrderCreate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Submit a service request / order.
    Automated services immediately trigger execution and deliver reports.
    Human specialist requests enter the 'requested' state awaiting specialist acceptance.
    """
    try:
        cust_id = auth["user_id"]
        cust_name = data.customer_name or auth.get("wallet_address") or "Francis"
        return marketplace_service.create_order(
            service_id=data.service_id,
            prompt_content=data.prompt_content,
            requirements=data.requirements or "",
            product_link=data.product_link,
            docs_link=data.docs_link,
            test_env_notes=data.test_env_notes,
            is_zero_g_wallet=bool(data.is_zero_g_wallet),
            customer_id=cust_id,
            customer_name=cust_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/orders", response_model=List[OrderResponse])
def list_orders(
    role: Optional[str] = Query(None, description="Filter view: 'customer' (my submitted requests) or 'provider' (incoming requests to me)"),
    status: Optional[str] = Query(None, description="Filter by status (requested, accepted, in_progress, delivered, completed)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    List service orders. Enforces ownership:
    Customers view their submitted requests; Providers view assigned work in their workspace.
    """
    effective_role = role.lower() if role else None
    return marketplace_service.list_orders(
        user_id=auth["user_id"],
        role=effective_role,
        status=status,
        limit=limit,
        offset=offset
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Retrieve detailed order tracking information with ownership validation.
    """
    try:
        ord_item = marketplace_service.get_order(order_id, user_id=auth["user_id"], role=auth["role"])
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    if not ord_item:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")
    return ord_item


@router.patch("/orders/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: str,
    data: OrderStatusUpdate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Update order status following the explicit lifecycle:
    requested -> accepted -> in_progress -> delivered -> completed.
    Also supports rejected and cancelled where appropriate.
    """
    try:
        return marketplace_service.update_order_status(
            order_id=order_id,
            new_status=data.status,
            user_id=auth["user_id"],
            role=auth["role"],
            notes=data.reason_or_notes
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/orders/{order_id}/deliver", response_model=Dict[str, Any])
def deliver_order(
    order_id: str,
    data: DeliverOrderRequest,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Submit completed audit findings and recommendations for an in-progress order.
    Generates a security report and prepares decentralized Swarm reference.
    """
    try:
        order, report = marketplace_service.deliver_order(
            order_id=order_id,
            data=data,
            provider_id=auth["user_id"]
        )
        return {
            "status": "success",
            "order": order.model_dump(),
            "report": report.model_dump()
        }
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/orders/{order_id}/x402-requirements")
def get_order_x402_requirements(
    order_id: str,
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns Hedera x402 v2 exact payment requirements and mirror node pricing for an order.
    """
    ord_item = marketplace_service.get_order(order_id)
    if not ord_item:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")

    from payments.blocky402 import (
        calculate_tinybars_for_usd,
        create_x402_requirements,
        get_facilitator_fee_payer,
        get_hbar_usd_rate,
    )
    from payments.config import HEDERA_MERCHANT_ACCOUNT_ID, X402_ASSET_ID, X402_NETWORK

    reqs = create_x402_requirements(order_id, ord_item.price)
    tinybars, hbars = calculate_tinybars_for_usd(ord_item.price)
    fee_payer = get_facilitator_fee_payer()
    rate = get_hbar_usd_rate()

    return {
        "order_id": order_id,
        "service_title": ord_item.service_title,
        "provider_name": ord_item.provider_name,
        "amount_usd": ord_item.price,
        "amount_hbars": hbars,
        "amount_tinybars": str(tinybars),
        "usd_per_hbar": rate,
        "network": X402_NETWORK,
        "asset": X402_ASSET_ID,
        "merchant_account": HEDERA_MERCHANT_ACCOUNT_ID,
        "fee_payer": fee_payer,
        "paymentRequirements": reqs,
    }


@router.post("/orders/{order_id}/pay", response_model=OrderResponse)
def pay_order(
    order_id: str,
    data: Optional[PaymentConfirmRequest] = None,
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Verify payment for an order through backend gateway.
    Activates the request for provider dashboard upon verification.
    """
    proof = None
    if data:
        if data.paymentRequirements and data.paymentPayload:
            proof = {
                "paymentRequirements": data.paymentRequirements,
                "paymentPayload": data.paymentPayload,
            }
        elif data.proof:
            proof = data.proof

    actor_wallet = auth.get("wallet_address") or auth.get("user_id")
    try:
        return marketplace_service.confirm_order_payment(
            order_id=order_id,
            proof=proof,
            actor_wallet=actor_wallet
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/orders/{order_id}/escrow-config")
def get_order_escrow_config(
    order_id: str,
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Returns MetaMask EVM Escrow parameters (Rabdi Testnet Chain ID 7794095) for human specialist orders.
    """
    ord_item = marketplace_service.get_order(order_id)
    if not ord_item:
        raise HTTPException(status_code=404, detail=f"Order '{order_id}' not found.")

    provider = marketplace_service.get_provider(ord_item.provider_id)
    prov_wallet = provider.wallet_address if provider and provider.wallet_address else "0xaf6b2b8df91a6063a35c3f491183ec35d1fbff54"

    from payments.evm_escrow import evm_escrow_service
    return evm_escrow_service.get_escrow_config(
        order_id=order_id,
        amount_usd=ord_item.price,
        provider_wallet=prov_wallet
    )


@router.post("/orders/{order_id}/escrow-deposit", response_model=OrderResponse)
def deposit_order_escrow(
    order_id: str,
    payload: Dict[str, Any],
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Verifies on-chain depositEscrow transaction on Rabdi Testnet and activates order to requested state.
    """
    tx_hash = payload.get("tx_hash") or payload.get("proof")
    if not tx_hash:
        raise HTTPException(status_code=400, detail="Transaction hash required for escrow deposit verification.")

    payer_wallet = auth.get("wallet_address") or payload.get("payer_wallet") or "0xpayer"
    try:
        return marketplace_service.confirm_escrow_deposit(
            order_id=order_id,
            tx_hash=tx_hash,
            payer_wallet=payer_wallet
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/orders/{order_id}/escrow-release", response_model=OrderResponse)
def release_order_escrow(
    order_id: str,
    payload: Dict[str, Any],
    auth: Dict[str, Any] = Depends(get_current_user)
):
    """
    Verifies on-chain releaseEscrow transaction by customer and completes order.
    """
    tx_hash = payload.get("tx_hash") or payload.get("proof")
    if not tx_hash:
        raise HTTPException(status_code=400, detail="Transaction hash required for escrow release verification.")

    customer_wallet = auth.get("wallet_address") or auth.get("user_id") or "0xcustomer"
    try:
        return marketplace_service.confirm_escrow_release(
            order_id=order_id,
            tx_hash=tx_hash,
            customer_wallet=customer_wallet
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))



@router.post("/orders/{order_id}/ticket")
def raise_order_ticket(
    order_id: str,
    data: TicketCreate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Raise a quality review or revision ticket for an order deliverable.
    Allows customers to report dissatisfaction with specialist audit performance.
    """
    try:
        return marketplace_service.raise_ticket(
            order_id=order_id,
            reason=data.reason,
            feedback=data.feedback,
            customer_id=auth["user_id"]
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/reports/{report_id}/ticket")
def raise_report_ticket(
    report_id: str,
    data: TicketCreate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Raise a quality review or revision ticket directly from a security report deliverable.
    """
    rep = marketplace_service.get_report(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    try:
        return marketplace_service.raise_ticket(
            order_id=rep.order_id,
            reason=data.reason,
            feedback=data.feedback,
            customer_id=auth["user_id"]
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Security Reports
# ---------------------------------------------------------------------------

@router.get("/reports", response_model=List[SecurityReportResponse])
def list_reports(
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Retrieve completed security reports for the authenticated customer or provider.
    """
    return marketplace_service.list_reports(user_id=auth["user_id"], role=auth["role"])


@router.get("/reports/{report_id}", response_model=SecurityReportResponse)
def get_report(report_id: str):
    """
    Retrieve a specific security report and its decentralized storage reference.
    """
    rep = marketplace_service.get_report(report_id)
    if not rep:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    return rep


# ---------------------------------------------------------------------------
# Saved Prompts
# ---------------------------------------------------------------------------

@router.get("/prompts", response_model=List[SavedPromptResponse])
def list_prompts(
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Retrieve user's private saved prompts and associated security findings.
    """
    return marketplace_service.list_prompts(customer_id=auth["user_id"])


@router.post("/prompts", response_model=SavedPromptResponse, status_code=status.HTTP_201_CREATED)
def create_prompt(
    data: SavedPromptCreate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Save a new prompt privately. Prompts are never shared to marketplace without user submission.
    """
    data.customer_id = auth["user_id"]
    return marketplace_service.create_prompt(data)


@router.put("/prompts/{prompt_id}", response_model=SavedPromptResponse)
def update_prompt(
    prompt_id: str,
    data: SavedPromptUpdate,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Update saved prompt content, title, or cached analysis results.
    """
    res = marketplace_service.update_prompt(prompt_id, data, customer_id=auth["user_id"])
    if not res:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found.")
    return res


@router.delete("/prompts/{prompt_id}")
def delete_prompt(
    prompt_id: str,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Delete a saved prompt from user's private repository.
    """
    deleted = marketplace_service.delete_prompt(prompt_id, customer_id=auth["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Prompt '{prompt_id}' not found.")
    return {"status": "deleted", "prompt_id": prompt_id}


# ---------------------------------------------------------------------------
# Dashboard Overview & Integrations Status
# ---------------------------------------------------------------------------

@router.get("/catalogue")
def get_service_catalogue():
    """
    Returns the canonical OpiHub service catalogue.
    """
    from marketplace.catalogue import public_catalogue
    return public_catalogue()


@router.get("/payments/config")
def get_payment_config():
    """
    Retrieve payment network configuration and modular gateway status.
    """
    from payments.service import payment_service
    return payment_service.public_config()


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    auth: Dict[str, str] = Depends(get_current_user)
):
    """
    Dashboard metrics for specialists count, services count, active orders, and recent activity.
    """
    return marketplace_service.get_dashboard_stats(customer_id=auth["user_id"])


@router.get("/integrations/status", response_model=IntegrationStatusResponse)
def get_integrations_status():
    """
    Inspect Phase 1 readiness of external integration boundaries: Arkiv, 0G, Swarm, and Hedera.
    """
    return IntegrationStatusResponse(
        arkiv=arkiv_client.get_status().model_dump(),
        zero_g={
            "is_configured": zero_g_optimizer.client.is_configured,
            "is_enabled": zero_g_optimizer.client.is_enabled,
            "engine": "0g_private_computer",
            "model": zero_g_optimizer.client.model,
            "trust_mode": zero_g_optimizer.client.trust_mode,
            "mode": "verified_inference" if zero_g_optimizer.client.is_configured else "deterministic_fallback_ready",
            "phase": "Verified 0G Inference Ready" if zero_g_optimizer.client.is_configured else "Phase 1 - Local Fallback Ready",
            "notice": "0G Private Computer client active with verified trust-mode header and credential sanitization."
        },
        swarm=swarm_client.get_status().model_dump(),
        hedera=hedera_client.get_status().model_dump()
    )


# ---------------------------------------------------------------------------
# Arkiv Decentralized Marketplace Endpoints
# ---------------------------------------------------------------------------

@router.get("/arkiv/config")
def get_arkiv_config():
    """Returns network parameters and access credentials for frontend Arkiv connection."""
    return {
        "chain_id": arkiv_client.chain_id,
        "chain_id_hex": "0x76ee8f",
        "network": "Rabdi Testnet",
        "currency": "tGLM",
        "rpc_url": arkiv_client.rpc_url,
        "access_key": arkiv_client.access_key,
        "explorer_url": "https://explorer.rabdi.db-chain.testnet.arkiv.network"
    }


@router.get("/arkiv/status", response_model=ArkivSyncStatus)
def get_arkiv_status():
    """Queries live connection state and latest block number on Rabdi testnet."""
    return arkiv_client.get_status()


@router.get("/arkiv/specialists", response_model=List[ArkivSpecialistProfile])
def list_arkiv_specialists(
    availability: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Discovers specialist profiles directly from Arkiv (guardvane.specialists.v1)."""
    return arkiv_client.query_specialists(availability=availability, limit=limit, offset=offset)


@router.get("/arkiv/services", response_model=List[ArkivServiceListing])
def list_arkiv_services(
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Discovers service listings directly from Arkiv (guardvane.services.v1)."""
    return arkiv_client.query_services(category=category, limit=limit, offset=offset)


@router.get("/arkiv/tasks", response_model=List[ArkivSecurityTask])
def list_arkiv_tasks(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    wallet: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Discovers security tasks directly from Arkiv (guardvane.tasks.v1)."""
    return arkiv_client.query_tasks(category=category, status=status, customer_wallet=wallet, limit=limit, offset=offset)


@router.get("/arkiv/tasks/{task_id}/bids", response_model=List[ArkivSpecialistBid])
def list_arkiv_bids(
    task_id: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Retrieves specialist bids for a task directly from Arkiv (guardvane.bids.v1)."""
    return arkiv_client.query_bids(task_id=task_id, limit=limit, offset=offset)


@router.get("/arkiv/tasks/{task_id}/awards", response_model=List[ArkivAwardRecord])
def list_arkiv_awards(
    task_id: str
):
    """Retrieves award records for a task directly from Arkiv (guardvane.awards.v1)."""
    return arkiv_client.query_awards(task_id=task_id)


@router.post("/arkiv/reconcile/task")
def reconcile_task(
    data: ReconcileTaskRequest,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """Reconciles customer-signed on-chain task with PostgreSQL registry."""
    return marketplace_service.reconcile_task(data)


@router.post("/arkiv/reconcile/bid")
def reconcile_bid(
    data: ReconcileBidRequest,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """Reconciles specialist-signed on-chain bid with PostgreSQL registry."""
    return marketplace_service.reconcile_bid(data)


@router.post("/arkiv/reconcile/award")
def reconcile_award(
    data: ReconcileAwardRequest,
    auth: Dict[str, str] = Depends(get_current_user)
):
    """Reconciles customer-signed on-chain award and transitions order to accepted."""
    return marketplace_service.reconcile_award(data)

