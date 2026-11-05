"""
FastAPI Router for PromptShield Marketplace.
Exposes endpoints for discovery, provider profiles, order lifecycle, security reports,
saved prompts, and integration status queries.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, status

from auth.service import decode_session_token

from integrations.arkiv.client import arkiv_client
from integrations.hedera.client import hedera_client
from integrations.swarm.client import swarm_client
from integrations.zero_g.client import ZeroGClient
from marketplace.schemas import (
    DashboardStats,
    DeliverOrderRequest,
    IntegrationStatusResponse,
    OrderCreate,
    OrderResponse,
    OrderStatus,
    OrderStatusUpdate,
    ProviderCreate,
    ProviderResponse,
    SavedPromptCreate,
    SavedPromptResponse,
    SavedPromptUpdate,
    SecurityReportResponse,
    ServiceCreate,
    ServiceResponse,
)
from marketplace.service import marketplace_service

router = APIRouter()


def get_current_user(
    request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    guardvane_session: Optional[str] = Cookie(None)
) -> Dict[str, Any]:
    """
    Extracts current authenticated identity and active role.
    Prioritizes MetaMask SIWE HttpOnly cookie and Bearer tokens,
    with backward compatibility for X-User-Id in development and automated testing.
    """
    token = guardvane_session
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        payload = decode_session_token(token)
        if payload and "wallet_address" in payload:
            roles = payload.get("roles", ["customer"])
            active_role = x_user_role.lower() if (x_user_role and x_user_role.lower() in roles) else (roles[0] if roles else "customer")
            return {
                "user_id": payload["wallet_address"],
                "sub": payload.get("sub"),
                "role": active_role,
                "roles": roles,
                "wallet_address": payload["wallet_address"]
            }

    user_id = x_user_id or "francis"
    role = (x_user_role or "customer").lower()
    return {
        "user_id": user_id,
        "role": role,
        "roles": [role],
        "wallet_address": user_id if user_id.startswith("0x") else None
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
    Register a new specialist profile (Human or Automated AI Provider).
    """
    return marketplace_service.create_provider_profile(data, user_id=auth["user_id"])


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
            "is_configured": False,
            "engine": "0g_private_computer",
            "mode": "deterministic_fallback_ready",
            "phase": "Phase 1 - Interface Ready",
            "notice": "Zero-G inference client initialized with sanitization."
        },
        swarm=swarm_client.get_status().model_dump(),
        hedera=hedera_client.get_status().model_dump()
    )

