"""
Centralized Configuration for 0G Private Computer Integration.
Reads and validates all ZG_* environment variables with strict credential safety.
"""

from dataclasses import dataclass
import os
from typing import Optional, Set
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

VALID_TRUST_MODES: Set[str] = {"standard", "verified", "private"}
DEFAULT_TRUST_MODE: str = "verified"
DEFAULT_BASE_URL: str = "https://router-api.0g.ai/v1"
DEFAULT_MODEL: str = "glm-5.2"
DEFAULT_TIMEOUT: float = 30.0
DEFAULT_MAX_RETRIES: int = 0
DEFAULT_MAX_TOKENS: int = 1500


def _parse_bool(val: Optional[str], default: bool = True) -> bool:
    if val is None:
        return default
    v = val.strip().lower()
    return v not in ("false", "0", "no", "off", "disable", "disabled")


@dataclass
class ZeroGSettings:
    """Immutable, credential-safe configuration settings for 0G Private Computer."""
    enabled: bool = True
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    trust_mode: str = DEFAULT_TRUST_MODE
    timeout: float = DEFAULT_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    max_tokens: int = DEFAULT_MAX_TOKENS
    has_api_key: bool = False

    def validate(self, require_api_key: bool = True) -> None:
        """Validates configuration consistency without exposing credentials."""
        from integrations.zero_g.client import ZeroGConfigurationError

        if self.trust_mode not in VALID_TRUST_MODES:
            raise ZeroGConfigurationError(
                f"Invalid 0G trust mode '{self.trust_mode}'. Must be one of: {sorted(list(VALID_TRUST_MODES))}."
            )
        if not self.base_url or not self.base_url.strip():
            raise ZeroGConfigurationError("0G Base URL is not configured (ZG_BASE_URL).")
        if not self.model or not self.model.strip():
            raise ZeroGConfigurationError("0G Model is not configured (ZG_MODEL).")
        if require_api_key and not self.has_api_key:
            raise ZeroGConfigurationError(
                "0G API key is not configured. Set the 'ZG_API_KEY' environment variable."
            )

    def __repr__(self) -> str:
        return (
            f"ZeroGSettings(enabled={self.enabled}, model='{self.model}', "
            f"trust_mode='{self.trust_mode}', base_url='{self.base_url}', "
            f"timeout={self.timeout}s, max_retries={self.max_retries}, "
            f"max_tokens={self.max_tokens}, has_api_key={self.has_api_key})"
        )


def get_zero_g_settings(
    api_key_override: Optional[str] = None,
    base_url_override: Optional[str] = None,
    model_override: Optional[str] = None,
    trust_mode_override: Optional[str] = None,
    timeout_override: Optional[float] = None,
    max_retries_override: Optional[int] = None,
    max_tokens_override: Optional[int] = None,
) -> tuple[ZeroGSettings, Optional[str]]:
    """
    Constructs and returns (ZeroGSettings, raw_api_key).
    raw_api_key is kept strictly separate from the settings object.
    """
    load_dotenv()

    enabled_env = os.environ.get("ZG_ENABLED")
    enabled = _parse_bool(enabled_env, default=True)

    raw_key = api_key_override or os.environ.get("ZG_API_KEY")
    has_key = bool(raw_key and raw_key.strip())

    base_url = (base_url_override or os.environ.get("ZG_BASE_URL") or DEFAULT_BASE_URL).strip()
    model = (model_override or os.environ.get("ZG_MODEL") or DEFAULT_MODEL).strip()

    trust_mode_raw = (trust_mode_override or os.environ.get("ZG_TRUST_MODE") or DEFAULT_TRUST_MODE).strip().lower()
    trust_mode = trust_mode_raw if trust_mode_raw in VALID_TRUST_MODES else trust_mode_raw

    timeout_val = float(timeout_override or os.environ.get("ZG_TIMEOUT") or DEFAULT_TIMEOUT)
    max_retries_val = int(max_retries_override or os.environ.get("ZG_MAX_RETRIES") or DEFAULT_MAX_RETRIES)
    max_tokens_val = int(max_tokens_override or os.environ.get("ZG_MAX_TOKENS") or DEFAULT_MAX_TOKENS)

    settings = ZeroGSettings(
        enabled=enabled,
        base_url=base_url,
        model=model,
        trust_mode=trust_mode,
        timeout=timeout_val,
        max_retries=max_retries_val,
        max_tokens=max_tokens_val,
        has_api_key=has_key,
    )
    return settings, raw_key

