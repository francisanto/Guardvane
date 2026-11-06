"""
0G Private Computer Reusable Client for Guardvane / PromptShield AI.
Connects to 0G Private Computer decentralized inference endpoints
using the OpenAI-compatible API protocol. Enforces strict credential protection,
configurable trust-mode headers, request ID tracking, and credit-saving retries.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

import openai
from openai import OpenAI, AsyncOpenAI

from integrations.zero_g.config import (
    ZeroGSettings,
    get_zero_g_settings,
    VALID_TRUST_MODES,
    DEFAULT_TRUST_MODE,
)

load_dotenv()
logger = logging.getLogger("guardvane.zerog")


# ---------------------------------------------------------------------------
# Custom Exceptions (Credential-Safe)
# ---------------------------------------------------------------------------

class ZeroGError(Exception):
    """Base exception for 0G Private Computer operations. Never exposes API keys."""
    pass


class ZeroGConfigurationError(ZeroGError):
    """Raised when required 0G environment variables or configurations are missing or invalid."""
    pass


class ZeroGAuthenticationError(ZeroGError):
    """Raised when 0G authentication fails (e.g. invalid or revoked API key)."""
    pass


class ZeroGConnectionError(ZeroGError):
    """Raised when connection to the 0G Private Computer endpoint fails."""
    pass


class ZeroGTimeoutError(ZeroGError):
    """Raised when a 0G inference request times out."""
    pass


class ZeroGAPIError(ZeroGError):
    """Raised when 0G returns a non-200 HTTP status response."""
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


class ZeroGRateLimitError(ZeroGAPIError):
    """Raised when 0G router rate limits requests (HTTP 429)."""
    pass


class ZeroGInsufficientCreditError(ZeroGAPIError):
    """Raised when 0G credit quota is exhausted or payment is required (HTTP 402/insufficient credits)."""
    pass


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ZeroGResponse:
    """
    Structured response returned by 0G Private Computer inference.
    Maintains request ID tracking separate from cryptographic attestation verification.
    """
    content: str
    model: str
    response_id: Optional[str] = None
    request_id: Optional[str] = None
    trust_mode: str = DEFAULT_TRUST_MODE
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    http_status: Optional[int] = None
    duration_ms: Optional[float] = None
    is_attestation_verified: bool = False  # Request ID is NOT cryptographic verification
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "response_id": self.response_id,
            "request_id": self.request_id,
            "trust_mode": self.trust_mode,
            "usage": self.usage or {},
            "finish_reason": self.finish_reason,
            "http_status": self.http_status,
            "duration_ms": self.duration_ms,
            "is_attestation_verified": self.is_attestation_verified,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Client Implementation
# ---------------------------------------------------------------------------

class ZeroGClient:
    """
    Production-grade, credit-conservative client for 0G Private Computer.
    Supports synchronous and asynchronous completion calls,
    dynamic model and base URL configuration, request ID tracking,
    X-0G-Provider-Trust-Mode header injection, and credential leak prevention.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        trust_mode: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        max_tokens: Optional[int] = None,
        enabled: Optional[bool] = None,
    ):
        settings, raw_key = get_zero_g_settings(
            api_key_override=api_key,
            base_url_override=base_url,
            model_override=model,
            trust_mode_override=trust_mode,
            timeout_override=timeout,
            max_retries_override=max_retries,
            max_tokens_override=max_tokens,
        )
        if enabled is not None:
            settings.enabled = enabled

        self.settings: ZeroGSettings = settings
        self._raw_api_key: Optional[str] = raw_key
        self._sync_client: Optional[OpenAI] = None
        self._async_client: Optional[AsyncOpenAI] = None

    # -----------------------------------------------------------------------
    # Credential-Safe Properties (Never returns raw API key)
    # -----------------------------------------------------------------------

    @property
    def is_enabled(self) -> bool:
        """Indicates whether 0G remote inference is enabled globally."""
        return self.settings.enabled

    @property
    def is_configured(self) -> bool:
        """Checks if minimum required 0G parameters and API key are present."""
        return bool(self._raw_api_key and self._raw_api_key.strip() and self.settings.enabled)

    @property
    def base_url(self) -> str:
        return self.settings.base_url

    @property
    def model(self) -> str:
        return self.settings.model

    @property
    def trust_mode(self) -> str:
        return self.settings.trust_mode

    @property
    def timeout(self) -> float:
        return self.settings.timeout

    @property
    def max_retries(self) -> int:
        return self.settings.max_retries

    @property
    def max_tokens(self) -> int:
        return self.settings.max_tokens

    # Explicitly do NOT provide self.api_key returning raw key.
    # Provide masked indicator only:
    @property
    def api_key_masked(self) -> str:
        if not self._raw_api_key:
            return "None"
        clean = self._raw_api_key.strip()
        if len(clean) > 8:
            return f"{clean[:3]}...{clean[-4:]}"
        return "***"

    def validate_configuration(self) -> None:
        """Validates configuration presence, raising descriptive errors without exposing credentials."""
        self.settings.validate(require_api_key=True)

    # -----------------------------------------------------------------------
    # Internal Client Construction (Injecting X-0G-Provider-Trust-Mode header)
    # -----------------------------------------------------------------------

    def _build_default_headers(self) -> Dict[str, str]:
        """Injects 0G Router trust-mode header without exposing secrets."""
        return {
            "X-0G-Provider-Trust-Mode": self.trust_mode,
        }

    def _get_sync_client(self) -> OpenAI:
        """Lazily creates and caches the synchronous OpenAI client."""
        self.validate_configuration()
        if self._sync_client is None:
            self._sync_client = OpenAI(
                api_key=self._raw_api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=self.max_retries,  # Defaults to 0 to save credits
                default_headers=self._build_default_headers(),
            )
        return self._sync_client

    def _get_async_client(self) -> AsyncOpenAI:
        """Lazily creates and caches the asynchronous AsyncOpenAI client."""
        self.validate_configuration()
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=self._raw_api_key,
                base_url=self.base_url,
                timeout=self.timeout,
                max_retries=self.max_retries,
                default_headers=self._build_default_headers(),
            )
        return self._async_client

    # -----------------------------------------------------------------------
    # Exception & Credential Sanitization
    # -----------------------------------------------------------------------

    def _sanitize_error_message(self, message: str) -> str:
        """Removes any accidental API key occurrences from error strings and stacktraces."""
        if self._raw_api_key and len(self._raw_api_key) > 4:
            message = message.replace(self._raw_api_key, "[REDACTED_ZG_API_KEY]")
        # Also redact standard Bearer patterns in headers
        message = re.sub(r'Bearer\s+[A-Za-z0-9\-_\.]+', 'Bearer [REDACTED_TOKEN]', message)
        return message

    def _handle_exception(self, exc: Exception) -> None:
        """Translates OpenAI SDK errors into custom 0G exceptions without leaking keys."""
        msg = self._sanitize_error_message(str(exc))
        lower_msg = msg.lower()
        status_code = getattr(exc, "status_code", None)

        if isinstance(exc, openai.AuthenticationError) or status_code == 401 or "401" in lower_msg or "unauthorized" in lower_msg:
            raise ZeroGAuthenticationError(
                f"0G Authentication Failed (HTTP {status_code or 401}): {msg}"
            ) from exc

        if isinstance(exc, openai.RateLimitError) or status_code == 429 or "429" in lower_msg or "rate limit" in lower_msg:
            req_id = getattr(exc, "request_id", None)
            raise ZeroGRateLimitError(
                f"0G Rate Limit Exceeded (HTTP 429): {msg}",
                status_code=429,
                request_id=req_id,
            ) from exc

        if status_code == 402 or "402" in lower_msg or "insufficient" in lower_msg or "quota" in lower_msg:
            req_id = getattr(exc, "request_id", None)
            raise ZeroGInsufficientCreditError(
                f"0G Insufficient Credits / Quota Exceeded: {msg}",
                status_code=402,
                request_id=req_id,
            ) from exc

        if isinstance(exc, openai.APITimeoutError):
            raise ZeroGTimeoutError(f"0G Inference Request Timed Out ({self.timeout}s): {msg}") from exc

        if isinstance(exc, openai.APIConnectionError):
            raise ZeroGConnectionError(f"0G Connection Failed to {self.base_url}: {msg}") from exc

        if isinstance(exc, openai.APIStatusError):
            req_id = getattr(exc, "request_id", None)
            code = getattr(exc, "status_code", None)
            raise ZeroGAPIError(
                f"0G API Error (HTTP {code}): {msg}",
                status_code=code,
                request_id=req_id,
            ) from exc

        if isinstance(exc, ZeroGError):
            raise exc

        raise ZeroGError(f"Unexpected 0G execution error: {msg}") from exc

    def _extract_request_id(self, raw_response: Any) -> Optional[str]:
        """Extracts HTTP request ID from raw response headers or attributes."""
        if raw_response is None:
            return None
        # Check standard SDK request_id attribute
        req_id = getattr(raw_response, "request_id", None)
        if req_id:
            return str(req_id)
        # Check HTTP response headers
        headers = getattr(raw_response, "headers", None)
        if headers:
            for header_name in ["x-request-id", "request-id", "x-zg-request-id", "x-correlation-id"]:
                val = headers.get(header_name)
                if val:
                    return str(val)
        return None

    def _extract_usage(self, parsed: Any) -> Optional[Dict[str, int]]:
        """Extracts token usage metrics from the parsed completion object without inventing values."""
        if not hasattr(parsed, "usage") or parsed.usage is None:
            return None
        u = parsed.usage
        return {
            "prompt_tokens": getattr(u, "prompt_tokens", None),
            "completion_tokens": getattr(u, "completion_tokens", None),
            "total_tokens": getattr(u, "total_tokens", None),
        }

    # -----------------------------------------------------------------------
    # Non-Billing Diagnostic Methods (Model Connectivity)
    # -----------------------------------------------------------------------

    def list_models(self) -> List[str]:
        """
        Queries available models from the 0G router endpoint without incurring
        paid chat completion charges. Used by diagnostics and health checks.
        """
        client = self._get_sync_client()
        try:
            models_data = client.models.list()
            return [m.id for m in models_data.data if hasattr(m, "id")]
        except Exception as e:
            self._handle_exception(e)
            return []

    # -----------------------------------------------------------------------
    # Synchronous Inference Method
    # -----------------------------------------------------------------------

    def complete(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> ZeroGResponse:
        """
        Executes a synchronous completion on 0G Private Computer.
        Enforces X-0G-Provider-Trust-Mode and extracts the HTTP request ID.
        """
        start_time = datetime.now(timezone.utc)
        client = self._get_sync_client()
        target_model = model or self.model
        tokens_limit = max_tokens if max_tokens is not None else self.max_tokens

        # Build message array if not provided directly
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

        create_kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": tokens_limit,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        try:
            raw_response = client.chat.completions.with_raw_response.create(**create_kwargs)
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            parsed = raw_response.parse()

            content = ""
            finish_reason = None
            if parsed.choices:
                choice = parsed.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason

            req_id = self._extract_request_id(raw_response)

            return ZeroGResponse(
                content=content,
                model=getattr(parsed, "model", target_model),
                response_id=getattr(parsed, "id", None),
                request_id=req_id,
                trust_mode=self.trust_mode,
                usage=self._extract_usage(parsed),
                finish_reason=finish_reason,
                http_status=getattr(raw_response, "status_code", 200),
                duration_ms=round(duration_ms, 2),
                is_attestation_verified=False,  # An HTTP request ID is NOT cryptographic verification
            )
        except Exception as e:
            self._handle_exception(e)
            raise

    # -----------------------------------------------------------------------
    # Asynchronous Inference Method
    # -----------------------------------------------------------------------

    async def complete_async(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> ZeroGResponse:
        """
        Executes an asynchronous completion on 0G Private Computer.
        """
        start_time = datetime.now(timezone.utc)
        async_client = self._get_async_client()
        target_model = model or self.model
        tokens_limit = max_tokens if max_tokens is not None else self.max_tokens

        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})

        create_kwargs: Dict[str, Any] = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": tokens_limit,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        try:
            raw_response = await async_client.chat.completions.with_raw_response.create(**create_kwargs)
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            parsed = raw_response.parse()

            content = ""
            finish_reason = None
            if parsed.choices:
                choice = parsed.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason

            req_id = self._extract_request_id(raw_response)

            return ZeroGResponse(
                content=content,
                model=getattr(parsed, "model", target_model),
                response_id=getattr(parsed, "id", None),
                request_id=req_id,
                trust_mode=self.trust_mode,
                usage=self._extract_usage(parsed),
                finish_reason=finish_reason,
                http_status=getattr(raw_response, "status_code", 200),
                duration_ms=round(duration_ms, 2),
                is_attestation_verified=False,
            )
        except Exception as e:
            self._handle_exception(e)
            raise

    # -----------------------------------------------------------------------
    # String representation (Never leaks credentials)
    # -----------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ZeroGClient(model='{self.model}', trust_mode='{self.trust_mode}', "
            f"base_url='{self.base_url}', api_key={self.api_key_masked}, "
            f"timeout={self.timeout}s, max_retries={self.max_retries})"
        )

    def __str__(self) -> str:
        return self.__repr__()
