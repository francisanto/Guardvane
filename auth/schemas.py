"""
Authentication Schemas for Guardvane SIWE & Wallet Management.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    nickname: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class NicknameUpdate(BaseModel):
    display_name: Optional[str] = None
    nickname: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_name(cls, data: Any) -> Any:
        if isinstance(data, dict):
            val = data.get("display_name") or data.get("nickname")
            if not val or not isinstance(val, str) or len(val.strip()) < 2:
                raise ValueError("display_name or nickname must be at least 2 characters")
            data["display_name"] = val.strip()
        return data


class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None


class RoleAssignmentRequest(BaseModel):
    role: str = Field(..., description="Role to add: 'customer', 'human_provider', 'automated_provider'")
