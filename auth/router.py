"""
FastAPI Authentication Router for Guardvane.
Implements /auth/nonce, /auth/verify, /auth/logout, and /auth/me.
"""

from typing import Dict, Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from auth.schemas import NonceRequest, NonceResponse, UserResponse, VerifyRequest
from auth.service import (
    create_session_token,
    decode_session_token,
    generate_nonce,
    verify_siwe,
)
from db.database import get_db
from db.models import User

router = APIRouter()

COOKIE_NAME = "guardvane_session"


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header(None, alias="X-User-Role"),
    guardvane_session: Optional[str] = Cookie(None)
) -> Optional[User]:
    """
    Retrieves the currently authenticated user from HttpOnly cookie or Authorization header.
    Falls back to X-User-Id header for developer console or backwards compatibility.
    """
    token = guardvane_session
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        payload = decode_session_token(token)
        if payload and "sub" in payload:
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if user:
                return user

    if x_user_id:
        # Backward compatibility for existing dev workflows and tests
        user = db.query(User).filter(
            (User.id == x_user_id) | (User.wallet_address == x_user_id.lower())
        ).first()
        return user

    return None


def get_current_user_required(
    request: Request,
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    guardvane_session: Optional[str] = Cookie(None)
) -> User:
    """
    Enforces authentication. Raises 401 Unauthorized if not authenticated.
    """
    user = get_current_user_optional(
        request=request,
        db=db,
        x_user_id=x_user_id,
        guardvane_session=guardvane_session
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please connect your MetaMask wallet."
        )
    return user


@router.post("/nonce", response_model=NonceResponse)
def request_nonce(data: NonceRequest, db: Session = Depends(get_db)):
    """
    Generates a cryptographic single-use EIP-4361 nonce for MetaMask SIWE sign-in.
    """
    from eth_utils import to_checksum_address
    nonce_record = generate_nonce(wallet_address=data.wallet_address, db=db)
    checksum_addr = to_checksum_address(nonce_record.wallet_address)
    return NonceResponse(
        nonce=nonce_record.nonce,
        wallet_address=nonce_record.wallet_address,
        checksum_address=checksum_addr,
        expires_at=nonce_record.expires_at.isoformat()
    )


@router.post("/verify")
def verify_signature(
    data: VerifyRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verifies the MetaMask SIWE signature, creates or loads the user in PostgreSQL,
    and sets an HttpOnly session cookie.
    """
    user = verify_siwe(message_str=data.message, signature=data.signature, db=db)
    token = create_session_token(user)

    is_https = request.url.scheme == "https"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_https,
        max_age=7 * 24 * 3600,
        path="/"
    )

    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "wallet_address": user.wallet_address,
            "display_name": user.display_name,
            "roles": user.role_names(),
            "created_at": user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at)
        }
    }


@router.post("/logout")
def logout(response: Response):
    """
    Logs out the user and clears the session cookie.
    """
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"success": True, "message": "Successfully logged out."}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    user: User = Depends(get_current_user_required)
):
    """
    Retrieves the authenticated user profile, wallet address, and active roles.
    """
    return UserResponse(
        id=user.id,
        wallet_address=user.wallet_address,
        display_name=user.display_name,
        roles=user.role_names(),
        created_at=user.created_at.isoformat() if hasattr(user.created_at, "isoformat") else str(user.created_at)
    )

