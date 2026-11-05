"""
Pydantic Schemas for PromptShield Marketplace.
Defines contracts for providers, services, orders, reports, and prompts.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    HUMAN = "human"
    AUTOMATED = "automated"


class ServiceExecutionType(str, Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"


class OrderStatus(str, Enum):
    REQUESTED = "requested"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    ESCROWED_X402 = "escrowed_x402"
    SETTLED = "settled"
    REFUNDED = "refunded"


# ---------------------------------------------------------------------------
# Provider Schemas
# ---------------------------------------------------------------------------

class ProviderBase(BaseModel):
    display_name: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=150)
    provider_type: ProviderType = Field(default=ProviderType.HUMAN)
    description: str = Field(..., min_length=10, max_length=3000)
    avatar_url: Optional[str] = Field(default="")
    skills: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    wallet_address: Optional[str] = Field(default=None)
    portfolio_url: Optional[str] = Field(default=None)
    endpoint_url: Optional[str] = Field(default=None)
    io_format: Optional[str] = Field(default="JSON / Prompt-in, Hardened-out")
    x402_supported: bool = Field(default=False)
    availability: str = Field(default="available")
    status: str = Field(default="published")


class ProviderCreate(ProviderBase):
    pass


class ProviderResponse(ProviderBase):
    id: str
    verified: bool = False
    reputation_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    services_count: Optional[int] = 0


# ---------------------------------------------------------------------------
# Service Schemas
# ---------------------------------------------------------------------------

class ServiceBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10, max_length=4000)
    category: str = Field(default="ai_security")
    price: float = Field(..., ge=0.0)
    currency: str = Field(default="USD")
    estimated_delivery: str = Field(..., min_length=2, max_length=50)
    supported_tasks: List[str] = Field(default_factory=list)
    execution_type: ServiceExecutionType = Field(default=ServiceExecutionType.MANUAL)
    is_active: bool = Field(default=True)


class ServiceCreate(ServiceBase):
    provider_id: Optional[str] = None


class ServiceResponse(ServiceBase):
    id: str
    provider_id: str
    provider_name: str
    provider_type: ProviderType
    provider_avatar: Optional[str] = ""
    provider_verified: bool = False
    created_at: str


# ---------------------------------------------------------------------------
# Order Schemas
# ---------------------------------------------------------------------------

class OrderCreate(BaseModel):
    service_id: str
    prompt_content: str = Field(..., min_length=2, description="Prompt text or task specification")
    requirements: Optional[str] = Field(default="", max_length=5000, description="Customer-specific constraints")
    product_link: Optional[str] = Field(default=None, description="Product or application testing URL")
    docs_link: Optional[str] = Field(default=None, description="Documentation or codebase repository URL")
    test_env_notes: Optional[str] = Field(default=None, description="Test credentials or staging environment notes")
    is_zero_g_wallet: Optional[bool] = Field(default=False, description="Whether customer uses a 0G-registered wallet eligible for 0G credits")
    customer_id: Optional[str] = Field(default="francis")
    customer_name: Optional[str] = Field(default="francis")

    @field_validator("prompt_content")
    @classmethod
    def check_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Prompt or task content cannot be empty.")
        return v.strip()


class TicketCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=200, description="Reason for raising ticket or requesting revision")
    feedback: str = Field(..., min_length=5, max_length=4000, description="Specific feedback or issues with specialist deliverable")


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason_or_notes: Optional[str] = Field(default=None)


class DeliverOrderRequest(BaseModel):
    summary: str = Field(..., min_length=10, description="Executive summary of audit findings")
    findings: List[Dict[str, Any]] = Field(default_factory=list, description="Structured vulnerability list")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    hardened_prompt: Optional[str] = Field(default=None, description="Hardened or optimized prompt version")
    deliverable_notes: Optional[str] = Field(default=None)


class OrderResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    provider_id: str
    provider_name: str
    provider_type: ProviderType
    service_id: str
    service_title: str
    service_category: str
    prompt_content: str
    requirements: str
    price: float
    currency: str
    status: OrderStatus
    execution_type: ServiceExecutionType
    payment_status: PaymentStatus
    report_id: Optional[str] = None
    deliverable_notes: Optional[str] = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Security Report Schemas
# ---------------------------------------------------------------------------

class SecurityReportResponse(BaseModel):
    id: str
    order_id: str
    customer_id: str
    provider_id: str
    provider_name: str
    service_title: str
    summary: str
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    hardened_prompt: Optional[str] = None
    swarm_reference: Optional[str] = None
    created_at: str


# ---------------------------------------------------------------------------
# Saved Prompts Schemas
# ---------------------------------------------------------------------------

class SavedPromptCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=150)
    content: str = Field(..., min_length=5)
    customer_id: Optional[str] = Field(default="francis")


class SavedPromptUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None


class SavedPromptResponse(BaseModel):
    id: str
    customer_id: str
    title: str
    content: str
    analysis_result: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Dashboard Stats & Integration Schemas
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    registered_specialists_count: int
    available_services_count: int
    my_requests_count: int
    completed_reviews_count: int
    human_specialists_count: int
    automated_providers_count: int
    saved_prompts_count: Optional[int] = 0
    active_requests_count: Optional[int] = 0
    completed_audits_count: Optional[int] = 0
    available_providers_count: Optional[int] = 0
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)


class IntegrationStatusResponse(BaseModel):
    arkiv: Dict[str, Any]
    zero_g: Dict[str, Any]
    swarm: Dict[str, Any]
    hedera: Dict[str, Any]

