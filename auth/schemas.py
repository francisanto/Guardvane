"""
Authentication Schemas for Guardvane SIWE & Wallet Management.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NonceRequest(BaseModel):
    wallet_address: str = Field(..., description="Ethereum wallet address (0x...)")


class NonceResponse(BaseModel):
    nonce: str
    wallet_address: str
    checksum_address: Optional[str] = None
    expires_at: str


class VerifyRequest(BaseModel):
    message: str = Field(..., description="EIP-4361 SIWE formatted message string")
    signature: str = Field(..., description="Hex-encoded signature from personal_sign")


class UserResponse(BaseModel):
    id: str
    wallet_address: str
    display_name: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None


class RoleAssignmentRequest(BaseModel):
    role: str = Field(..., description="Role to add: 'customer', 'human_provider', 'automated_provider'")
