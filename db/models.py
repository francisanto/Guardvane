"""
SQLAlchemy Models for Guardvane.
Includes Wallet Authentication, Multi-Role Access Control, and Marketplace Schemas.
Compatible with PostgreSQL (Supabase / local) and SQLite for testing.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from db.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    """
    User account identified primarily by Ethereum wallet address.
    Supports multiple concurrent roles (customer, human_provider, automated_provider).
    """
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_address = Column(String(42), unique=True, index=True, nullable=False)
    display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", lazy="joined")

    def role_names(self):
        return [r.role for r in self.roles]


class UserRole(Base):
    """
    Roles assigned to a user: 'customer', 'human_provider', 'automated_provider'.
    A single wallet user can hold multiple roles.
    """
    __tablename__ = "user_roles"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User", back_populates="roles")


class AuthNonce(Base):
    """
    Cryptographic single-use nonce for SIWE (Sign-In with Ethereum).
    Tracks expiry (default 5-10 minutes) and prevents replay attacks.
    """
    __tablename__ = "auth_nonces"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    wallet_address = Column(String(42), nullable=False, index=True)
    nonce = Column(String(64), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


# ---------------------------------------------------------------------------
# Marketplace Schema Models
# ---------------------------------------------------------------------------

class Provider(Base):
    """
    Specialist or Automated Provider profile offering security services.
    """
    __tablename__ = "providers"

    id = Column(String(64), primary_key=True)
    display_name = Column(String(120), nullable=False)
    title = Column(String(200), nullable=False)
    provider_type = Column(String(50), nullable=False, index=True)  # human / automated
    description = Column(Text, nullable=False)
    avatar_url = Column(String(500), nullable=True)
    skills = Column(Text, nullable=False)  # JSON-serialized list
    categories = Column(Text, nullable=False)  # JSON-serialized list
    wallet_address = Column(String(42), nullable=True, index=True)
    portfolio_url = Column(String(500), nullable=True)
    endpoint_url = Column(String(500), nullable=True)
    io_format = Column(String(100), nullable=True)
    x402_supported = Column(Integer, default=0, nullable=False)
    availability = Column(String(50), default="available", nullable=False)
    verified = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="published", nullable=False)
    reputation_metadata = Column(Text, nullable=False)  # JSON-serialized dict
    created_at = Column(String(64), nullable=False)

    services = relationship("Service", back_populates="provider", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="provider")


class Service(Base):
    """
    Service listing offered by a Provider in OpiHub marketplace.
    """
    __tablename__ = "services"

    id = Column(String(64), primary_key=True)
    provider_id = Column(String(64), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Float, nullable=False)
    currency = Column(String(20), default="USD", nullable=False)
    estimated_delivery = Column(String(100), nullable=False)
    supported_tasks = Column(Text, nullable=False)  # JSON-serialized list
    execution_type = Column(String(50), default="manual", nullable=False)  # manual / automated
    is_active = Column(Integer, default=1, nullable=False, index=True)
    created_at = Column(String(64), nullable=False)

    provider = relationship("Provider", back_populates="services")
    orders = relationship("Order", back_populates="service")


class Order(Base):
    """
    Service engagement order tracking lifecycle:
    requested -> accepted -> in_progress -> delivered -> completed (or rejected/cancelled).
    """
    __tablename__ = "orders"

    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), nullable=False, index=True)
    customer_name = Column(String(120), nullable=False)
    provider_id = Column(String(64), ForeignKey("providers.id"), nullable=False, index=True)
    provider_name = Column(String(120), nullable=False)
    provider_type = Column(String(50), nullable=False)
    service_id = Column(String(64), ForeignKey("services.id"), nullable=False, index=True)
    service_title = Column(String(200), nullable=False)
    service_category = Column(String(100), nullable=False)
    prompt_content = Column(Text, nullable=False)
    requirements = Column(Text, nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(20), default="USD", nullable=False)
    status = Column(String(50), nullable=False, index=True)
    execution_type = Column(String(50), nullable=False)
    payment_status = Column(String(50), nullable=False)
    report_id = Column(String(64), nullable=True)
    deliverable_notes = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)

    provider = relationship("Provider", back_populates="orders")
    service = relationship("Service", back_populates="orders")
    reports = relationship("Report", back_populates="order")


class Report(Base):
    """
    Security report produced after completing an audit/review order.
    """
    __tablename__ = "reports"

    id = Column(String(64), primary_key=True)
    order_id = Column(String(64), ForeignKey("orders.id"), nullable=False, index=True)
    customer_id = Column(String(64), nullable=False, index=True)
    provider_id = Column(String(64), nullable=False, index=True)
    provider_name = Column(String(120), nullable=False)
    service_title = Column(String(200), nullable=False)
    summary = Column(Text, nullable=False)
    findings = Column(Text, nullable=False)  # JSON-serialized list
    recommendations = Column(Text, nullable=False)  # JSON-serialized list
    hardened_prompt = Column(Text, nullable=True)
    swarm_reference = Column(String(255), nullable=True)
    created_at = Column(String(64), nullable=False)

    order = relationship("Order", back_populates="reports")


class SavedPrompt(Base):
    """
    User's private saved prompts and associated security findings.
    Strictly isolated per customer_id.
    """
    __tablename__ = "saved_prompts"

    id = Column(String(64), primary_key=True)
    customer_id = Column(String(64), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    analysis_result = Column(Text, nullable=True)  # JSON-serialized dict
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=False)


# Indexing for optimal lookups and ownership isolation
Index("ix_orders_customer_status", Order.customer_id, Order.status)
Index("ix_orders_provider_status", Order.provider_id, Order.status)
Index("ix_reports_customer", Report.customer_id)
Index("ix_prompts_customer", SavedPrompt.customer_id)

