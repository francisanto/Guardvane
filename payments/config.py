"""
Hedera x402 payment configuration.
Reads and validates environment settings for Blocky402 facilitator and Hedera Testnet.
"""

from __future__ import annotations

import os
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Network and Asset configuration
X402_NETWORK: str = os.getenv("X402_NETWORK", "hedera:testnet").strip()
X402_ASSET_ID: str = os.getenv("X402_ASSET_ID", "0.0.0").strip()
X402_FACILITATOR_URL: str = os.getenv("X402_FACILITATOR_URL", "https://api.testnet.blocky402.com").strip().rstrip("/")
HEDERA_MERCHANT_ACCOUNT_ID: str = os.getenv("HEDERA_MERCHANT_ACCOUNT_ID", "0.0.10946394").strip()
X402_PAYMENT_MODE: str = os.getenv("X402_PAYMENT_MODE", "testnet").strip().lower()

# Fallback conversion rate: 1 USD = ~14.54 HBAR (~$0.0687 per HBAR)
DEFAULT_HBAR_USD_RATE: float = 0.0687


def is_valid_hedera_account_id(account_id: Optional[str]) -> bool:
    """Validates Hedera account ID format (e.g. 0.0.12345)."""
    if not account_id:
        return False
    return bool(re.match(r"^0\.0\.[1-9][0-9]*$", account_id.strip()))


def validate_config() -> None:
    """Sanity-checks critical configuration."""
    if not is_valid_hedera_account_id(HEDERA_MERCHANT_ACCOUNT_ID):
        raise ValueError(
            f"Invalid HEDERA_MERCHANT_ACCOUNT_ID '{HEDERA_MERCHANT_ACCOUNT_ID}'. Must be in 0.0.x format."
        )

