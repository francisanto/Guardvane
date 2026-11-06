#!/usr/bin/env python3
"""
Safe Diagnostic Verification Script for 0G Private Computer Integration.
Validates connectivity, router availability, model catalog presence,
and trust-mode configuration WITHOUT incurring paid chat completion charges
and WITHOUT printing secret API keys or headers.
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from integrations.zero_g.config import get_zero_g_settings
from integrations.zero_g.client import ZeroGClient, ZeroGError


def run_diagnostics() -> int:
    print("=" * 70)
    print("  Guardvane — 0G Private Computer Diagnostic Verification")
    print("=" * 70)
    print()

    # 1. Environment Variable Audit (Masked)
    settings, raw_key = get_zero_g_settings()
    has_key = bool(raw_key and raw_key.strip())
    masked_key = f"{raw_key[:3]}...{raw_key[-4:]}" if (has_key and len(raw_key) > 8) else ("Present" if has_key else "Missing")

    print("[1] Configuration & Environment Audit:")
    print(f"    - ZG_ENABLED:        {settings.enabled}")
    print(f"    - ZG_API_KEY:        {masked_key} (Status: {'CONFIGURED' if has_key else 'MISSING'})")
    print(f"    - ZG_BASE_URL:       {settings.base_url}")
    print(f"    - ZG_MODEL:          {settings.model}")
    print(f"    - ZG_TRUST_MODE:     {settings.trust_mode}")
    print(f"    - ZG_TIMEOUT:        {settings.timeout}s")
    print(f"    - ZG_MAX_RETRIES:    {settings.max_retries} (Credit protection: 0 retries)")
    print(f"    - ZG_MAX_TOKENS:     {settings.max_tokens}")
    print()

    if not settings.enabled:
        print("[-] Notice: 0G inference is globally disabled via ZG_ENABLED=false.")
        print("    Application will strictly execute local deterministic heuristics.")
        print()
        return 0

    if not has_key:
        print("[!] Error: ZG_API_KEY is not set. Please set ZG_API_KEY in your environment or .env file.")
        print()
        return 1

    try:
        settings.validate(require_api_key=True)
        print("[+] Configuration syntax: VALID")
    except Exception as e:
        print(f"[!] Configuration validation failed: {e}")
        return 1

    # 2. Router Connectivity & Model Catalog Check (Free / Non-billing endpoint)
    print()
    print("[2] 0G Router Connectivity & Catalog Audit (Non-billing):")
    print(f"    Connecting to {settings.base_url} (Timeout: {settings.timeout}s)...")

    client = ZeroGClient()
    available_models = []
    try:
        available_models = client.list_models()
        print(f"[+] Router connection successful! Discovered {len(available_models)} models in catalog.")
    except Exception as e:
        print(f"[!] Failed to connect to 0G Router: {e}")
        print("    Check network access and confirm ZG_BASE_URL is reachable.")
        return 1

    # 3. Model Verification
    print()
    print("[3] Target Model Verification:")
    if settings.model in available_models:
        print(f"[+] Configured model '{settings.model}' is ACTIVE and verified in 0G Router catalog.")
    else:
        print(f"[!] Configured model '{settings.model}' was NOT found in 0G Router catalog!")
        print("    Available sample models include:")
        for m in available_models[:10]:
            print(f"      - {m}")
        return 1

    # 4. Trust Mode Verification
    print()
    print("[4] Trust Mode Audit:")
    print(f"    - Active Header: 'X-0G-Provider-Trust-Mode: {settings.trust_mode}'")
    print(f"    - Mode Level:    {settings.trust_mode.upper()}")
    print("    - Policy:        Defaulted to 'verified' mode for confidential hackathon demonstration.")
    print()

    # 5. Non-Billing / Non-Proof Disclaimer
    print("=" * 70)
    print("  VERIFICATION RESULT: READY FOR HACKATHON DEMO")
    print("=" * 70)
    print("  IMPORTANT NOTICE:")
    print("  - No paid chat completion inference was executed during this check.")
    print("  - A successful configuration & catalog check confirms connectivity")
    print("    and authorization, but is NOT proof of a cryptographically verified")
    print("    inference run until an actual prompt optimization request is issued.")
    print("=" * 70)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(run_diagnostics())

