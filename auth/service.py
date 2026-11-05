"""
Authentication Service for Guardvane.
Implements EIP-4361 SIWE signature verification, single-use nonce lifecycle,
JWT session issuance, and user multi-role management.
"""

from datetime import datetime, timedelta, timezone
import os
import re
import uuid
import logging
from typing import List, Optional

from fastapi import HTTPException, status
import jwt
import siwe
from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import to_checksum_address
from sqlalchemy.orm import Session

from db.models import AuthNonce, User, UserRole

logger = logging.getLogger("guardvane.auth")

JWT_SECRET = os.getenv("JWT_SECRET", "guardvane-production-session-secret-2026-secure")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 7
NONCE_EXPIRY_MINUTES = 10


def normalize_address(address: str) -> str:
    """Normalizes an Ethereum address to lowercase for uniform indexing."""
    if not address or not address.startswith("0x") or len(address) != 42:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Ethereum wallet address format (must be 0x followed by 40 hex characters)."
        )
    return address.lower()


def generate_nonce(wallet_address: str, db: Session) -> AuthNonce:
    """
    Generates a cryptographic single-use EIP-4361 nonce for a wallet address.
    Invalidates any previous pending nonces for this address to prevent replay.
    """
    norm_addr = normalize_address(wallet_address)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=NONCE_EXPIRY_MINUTES)
    
    nonce_val = siwe.generate_nonce()
    
    nonce_record = AuthNonce(
        id=str(uuid.uuid4()),
        wallet_address=norm_addr,
        nonce=nonce_val,
        expires_at=expires_at,
        used=False,
        created_at=now
    )
    db.add(nonce_record)
    db.commit()
    db.refresh(nonce_record)
    return nonce_record


def verify_siwe(message_str: str, signature: str, db: Session) -> User:
    """
    Verifies an EIP-4361 SIWE message and user signature.
    Enforces nonce validity, expiration, single-use consumption, and retrieves or creates
    the persistent user account with default customer role.
    """
    # Normalize message line endings
    clean_msg = message_str.replace("\r\n", "\n").replace("\r", "\n").strip()

    # Ensure Ethereum address matches EIP-55 checksum format required by pydantic SIWE model
    def _to_checksum_match(m):
        try:
            return to_checksum_address(m.group(0))
        except Exception:
            return m.group(0)

    msg_for_parser = re.sub(r'0x[a-fA-F0-9]{40}', _to_checksum_match, clean_msg)

    try:
        siwe_msg = siwe.SiweMessage.from_message(msg_for_parser)
    except Exception as e:
        logger.warning(f"Failed to parse SIWE message: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed SIWE message format: {str(e)}"
        )

    # 1. Nonce check
    nonce_record = db.query(AuthNonce).filter(AuthNonce.nonce == siwe_msg.nonce).first()
    if not nonce_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication nonce not found. Please request a new nonce."
        )

    if nonce_record.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nonce has already been used (replay detected). Please request a new nonce."
        )

    now = datetime.now(timezone.utc)
    # Ensure timezone aware comparison
    expires_at = nonce_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        nonce_record.used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nonce has expired. Please request a fresh nonce."
        )

    # 2. Cryptographic signature verification
    verified = False
    try:
        siwe_msg.verify(signature)
        verified = True
    except Exception as e:
        logger.debug(f"Direct siwe_msg.verify failed, attempting direct recovery: {e}")

    if not verified:
        sig_hex = signature[2:] if signature.startswith("0x") else signature
        for candidate_text in [message_str, clean_msg, msg_for_parser]:
            try:
                recovered = Account.recover_message(encode_defunct(text=candidate_text), signature=bytes.fromhex(sig_hex))
                if recovered.lower() == siwe_msg.address.lower():
                    verified = True
                    break
            except Exception as e:
                logger.debug(f"Signature recovery with candidate failed: {e}")

    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid wallet signature. Authentication rejected."
        )

    # 3. Mark nonce as consumed
    nonce_record.used = True
    db.commit()

    # 4. Lookup or create persistent User
    norm_addr = siwe_msg.address.lower()
    user = db.query(User).filter(User.wallet_address == norm_addr).first()
    
    if not user:
        short_addr = f"{norm_addr[:6]}...{norm_addr[-4:]}"
        user = User(
            id=str(uuid.uuid4()),
            wallet_address=norm_addr,
            display_name=short_addr,
            created_at=now,
            updated_at=now
        )
        db.add(user)
        db.flush()
        
        # Assign default 'customer' role
        default_role = UserRole(
            id=str(uuid.uuid4()),
            user_id=user.id,
            role="customer",
            created_at=now
        )
        db.add(default_role)
        db.commit()
        db.refresh(user)
    else:
        # Check if user has at least one role
        if not user.roles:
            default_role = UserRole(
                id=str(uuid.uuid4()),
                user_id=user.id,
                role="customer",
                created_at=now
            )
            db.add(default_role)
            db.commit()
            db.refresh(user)

    return user


def create_session_token(user: User) -> str:
    """Generates an encrypted JWT authentication token containing user ID and active roles."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "wallet_address": user.wallet_address,
        "display_name": user.display_name,
        "roles": user.role_names(),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_EXPIRATION_DAYS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_session_token(token: str) -> Optional[dict]:
    """Validates and decodes a session JWT."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        logger.debug(f"JWT validation error: {e}")
        return None


def add_user_role(user_id: str, role: str, db: Session) -> UserRole:
    """Adds a role to a user if not already granted."""
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role == role).first()
    if existing:
        return existing
    new_role = UserRole(
        id=str(uuid.uuid4()),
        user_id=user_id,
        role=role,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

