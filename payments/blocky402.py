"""
Blocky402 Hosted Testnet Facilitator Client for Hedera x402 Micropayments.
Handles dynamic fee payer discovery, live exchange rates, x402 v2 payment requirements,
and backend /verify and /settle requests.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional, Tuple
import httpx

from payments.config import (
    DEFAULT_HBAR_USD_RATE,
    HEDERA_MERCHANT_ACCOUNT_ID,
    X402_ASSET_ID,
    X402_FACILITATOR_URL,
    X402_NETWORK,
)

logger = logging.getLogger("guardvane.payments.blocky402")

# In-memory caches to minimize latency
_fee_payer_cache: Dict[str, Any] = {"fee_payer": "0.0.7162784", "cached_at": 0.0}
_rate_cache: Dict[str, Any] = {"usd_per_hbar": DEFAULT_HBAR_USD_RATE, "cached_at": 0.0}


def get_facilitator_fee_payer(force_refresh: bool = False) -> str:
    """
    Dynamically discover the facilitator fee payer from Blocky402 /supported.
    Caches the fee payer for 10 minutes.
    """
    now = time.time()
    if not force_refresh and (now - _fee_payer_cache["cached_at"] < 600) and _fee_payer_cache["fee_payer"]:
        return _fee_payer_cache["fee_payer"]

    url = f"{X402_FACILITATOR_URL}/supported"
    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                # 1. Search in kinds for hedera:testnet extra.feePayer
                kinds = data.get("kinds", [])
                for k in kinds:
                    if k.get("network") == X402_NETWORK:
                        fp = k.get("extra", {}).get("feePayer")
                        if fp:
                            _fee_payer_cache["fee_payer"] = fp
                            _fee_payer_cache["cached_at"] = now
                            return fp
                # 2. Search in signers for hedera:*
                signers = data.get("signers", {}).get("hedera:*", [])
                if signers and isinstance(signers, list):
                    fp = signers[0]
                    _fee_payer_cache["fee_payer"] = fp
                    _fee_payer_cache["cached_at"] = now
                    return fp
    except Exception as exc:
        logger.warning(f"Failed to fetch fee payer from {url}: {exc}. Using fallback {_fee_payer_cache['fee_payer']}")

    return _fee_payer_cache["fee_payer"] or "0.0.7162784"


def get_hbar_usd_rate(force_refresh: bool = False) -> float:
    """
    Fetch the live HBAR-USD exchange rate from Hedera Mirror Node.
    Caches for 5 minutes.
    """
    now = time.time()
    if not force_refresh and (now - _rate_cache["cached_at"] < 300) and _rate_cache["usd_per_hbar"] > 0:
        return _rate_cache["usd_per_hbar"]

    urls = [
        "https://mainnet-public.mirrornode.hedera.com/api/v1/network/exchangerate",
        "https://testnet.mirrornode.hedera.com/api/v1/network/exchangerate",
    ]

    for url in urls:
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    curr = data.get("current_rate", {})
                    cent = curr.get("cent_equivalent")
                    hbar = curr.get("hbar_equivalent")
                    if cent and hbar:
                        rate = (float(cent) / float(hbar)) / 100.0
                        _rate_cache["usd_per_hbar"] = rate
                        _rate_cache["cached_at"] = now
                        return rate
        except Exception as exc:
            logger.debug(f"Exchange rate lookup failed on {url}: {exc}")

    return _rate_cache["usd_per_hbar"] or DEFAULT_HBAR_USD_RATE


def calculate_tinybars_for_usd(amount_usd: float) -> Tuple[int, float]:
    """
    Converts USD amount to (tinybars, hbar_float).
    1 HBAR = 100,000,000 tinybars.
    """
    rate = get_hbar_usd_rate()
    if rate <= 0:
        rate = DEFAULT_HBAR_USD_RATE
    hbars = amount_usd / rate
    tinybars = int(round(hbars * 100_000_000))
    return tinybars, round(hbars, 4)


def create_x402_requirements(order_id: str, amount_usd: float) -> Dict[str, Any]:
    """
    Generates x402 v2 exact payment requirements matching Blocky402's schema.
    """
    fee_payer = get_facilitator_fee_payer()
    tinybars, hbars = calculate_tinybars_for_usd(amount_usd)

    return {
        "x402Version": 2,
        "scheme": "exact",
        "network": X402_NETWORK,
        "amount": str(tinybars),
        "payTo": HEDERA_MERCHANT_ACCOUNT_ID,
        "maxTimeoutSeconds": 300,
        "asset": X402_ASSET_ID,
        "extra": {
            "feePayer": fee_payer,
        },
    }


def verify_payment(payment_requirements: Dict[str, Any], payment_payload: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    Calls Blocky402 POST /verify.
    Returns (is_valid, payer, invalid_reason).
    """
    url = f"{X402_FACILITATOR_URL}/verify"
    body = {
        "paymentRequirements": payment_requirements,
        "paymentPayload": payment_payload,
    }
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=body)
            if resp.status_code != 200:
                return False, "", f"Facilitator HTTP {resp.status_code}: {resp.text}"
            data = resp.json()
            is_valid = bool(data.get("isValid", False))
            reason = data.get("invalidReason", "")
            payer = data.get("payer", "")
            return is_valid, payer, reason
    except Exception as exc:
        return False, "", f"Verification connection error: {str(exc)}"


def settle_payment(payment_requirements: Dict[str, Any], payment_payload: Dict[str, Any]) -> Tuple[bool, str, str, Dict[str, Any]]:
    """
    Calls Blocky402 POST /settle.
    Returns (success, transaction_id, error_reason, raw_response).
    """
    url = f"{X402_FACILITATOR_URL}/settle"
    body = {
        "paymentRequirements": payment_requirements,
        "paymentPayload": payment_payload,
    }
    try:
        with httpx.Client(timeout=25.0) as client:
            resp = client.post(url, json=body)
            if resp.status_code != 200:
                return False, "", f"Facilitator settle HTTP {resp.status_code}: {resp.text}", {}
            data = resp.json()
            success = bool(data.get("success", False))
            tx_id = data.get("transaction", "")
            err = data.get("errorReason", "")
            return success, tx_id, err, data
    except Exception as exc:
        return False, "", f"Settlement connection error: {str(exc)}", {}

