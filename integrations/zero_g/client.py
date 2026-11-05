"""
0G Private Computer Reusable Client for PromptShield AI.
Connects to 0G Private Computer decentralized inference endpoints
using the OpenAI-compatible API protocol.
"""

from dataclasses import dataclass, field
import os
import re
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

import openai
from openai import OpenAI, AsyncOpenAI

# Automatically load environment variables from .env
load_dotenv()


# ---------------------------------------------------------------------------
# Custom Exceptions (Credential-Safe)
# ---------------------------------------------------------------------------

class ZeroGError(Exception):
    """Base exception for 0G Private Computer operations. Never exposes API keys."""
    pass


class ZeroGConfigurationError(ZeroGError):
    """Raised when required 0G environment variables or configurations are missing."""
    pass


class ZeroGAuthenticationError(ZeroGError):
    """Raised when 0G authentication fails (e.g. invalid API key)."""
    pass


class ZeroGConnectionError(ZeroGError):
    """Raised when connection to the 0G Private Computer endpoint fails."""
    pass


class ZeroGTimeoutError(ZeroGError):
    """Raised when a 0G inference request times out."""
    pass


class ZeroGAPIError(ZeroGError):
    """Raised when 0G returns a non-200 HTTP status response."""
    def __init__(self, message: str, status_code: Optional[int] = None, request_id: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ZeroGResponse:
    """Structured response returned by 0G Private Computer inference."""
    content: str
    model: str
    response_id: Optional[str] = None
    request_id: Optional[str] = None
    usage: Optional[Dict[str, int]] = None
    finish_reason: Optional[str] = None
    http_status: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "response_id": self.response_id,
            "request_id": self.request_id,
            "usage": self.usage or {},
            "finish_reason": self.finish_reason,
            "http_status": self.http_status,
        }


# ---------------------------------------------------------------------------
# Client Implementation
# ---------------------------------------------------------------------------

class ZeroGClient:
    """
    Production-grade client for 0G Private Computer.
    Supports synchronous and asynchronous completion calls,
    dynamic model and base URL configuration, request ID tracking,
    and credential leak prevention.
    """

    DEFAULT_TIMEOUT: float = 60.0
    DEFAULT_MAX_RETRIES: int = 2

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        """
        Initializes the 0G client.
        Values are resolved in the following priority order:
        1. Explicitly passed arguments
        2. Environment variables (ZG_API_KEY, ZG_BASE_URL, ZG_MODEL)
        """
        # Load environment variables in case they were updated after import
        load_dotenv()

        self._api_key = api_key or os.environ.get("ZG_API_KEY")
        self._base_url = base_url or os.environ.get("ZG_BASE_URL")
        self._model = model or os.environ.get("ZG_MODEL")
        self._timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT
        self._max_retries = max_retries if max_retries is not None else self.DEFAULT_MAX_RETRIES

        self._sync_client: Optional[OpenAI] = None
        self._async_client: Optional[AsyncOpenAI] = None

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @property
    def base_url(self) -> Optional[str]:
        return self._base_url

    @property
    def model(self) -> Optional[str]:
        return self._model

    def is_configured(self) -> bool:
        """Checks if minimum required 0G parameters are present."""
        return bool(self._api_key and self._api_key.strip())

    def validate_configuration(self) -> None:
        """Validates configuration presence, raising descriptive errors if missing."""
        if not self._api_key or not self._api_key.strip():
            raise ZeroGConfigurationError(
                "0G API key is not configured. Set the 'ZG_API_KEY' environment variable "
                "or pass 'api_key' to ZeroGClient."
            )
        if not self._base_url or not self._base_url.strip():
            raise ZeroGConfigurationError(
                "0G Base URL is not configured. Set the 'ZG_BASE_URL' environment variable "
                "or pass 'base_url' to ZeroGClient."
            )
        if not self._model or not self._model.strip():
            raise ZeroGConfigurationError(
                "0G Model is not configured. Set the 'ZG_MODEL' environment variable "
                "or pass 'model' to ZeroGClient."
            )

    def _get_sync_client(self) -> OpenAI:
        """Lazily creates and caches the synchronous OpenAI client."""
        self.validate_configuration()
        if self._sync_client is None:
            self._sync_client = OpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        return self._sync_client

    def _get_async_client(self) -> AsyncOpenAI:
        """Lazily creates and caches the asynchronous AsyncOpenAI client."""
        self.validate_configuration()
        if self._async_client is None:
            self._async_client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        return self._async_client

    def _sanitize_error_message(self, message: str) -> str:
        """Removes any accidental API key occurrences from error strings."""
        if self._api_key and len(self._api_key) > 4:
            message = message.replace(self._api_key, "[REDACTED_ZG_API_KEY]")
        return message

    def _handle_exception(self, exc: Exception) -> None:
        """Translates OpenAI SDK errors into custom 0G exceptions without leaking keys."""
        msg = self._sanitize_error_message(str(exc))

        if isinstance(exc, openai.AuthenticationError):
            raise ZeroGAuthenticationError(
                f"0G Authentication Failed (HTTP {getattr(exc, 'status_code', 401)}): {msg}"
            ) from exc
        elif isinstance(exc, openai.APITimeoutError):
            raise ZeroGTimeoutError(f"0G Inference Request Timed Out: {msg}") from exc
        elif isinstance(exc, openai.APIConnectionError):
            raise ZeroGConnectionError(f"0G Connection Failed: {msg}") from exc
        elif isinstance(exc, openai.APIStatusError):
            req_id = getattr(exc, "request_id", None)
            code = getattr(exc, "status_code", None)
            raise ZeroGAPIError(
                f"0G API Error (HTTP {code}): {msg}",
                status_code=code,
                request_id=req_id,
            ) from exc
        elif isinstance(exc, ZeroGError):
            raise exc
        else:
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

    def _extract_usage(self, parsed: Any) -> Dict[str, int]:
        """Extracts token usage metrics from the parsed completion object."""
        usage_data: Dict[str, int] = {}
        if hasattr(parsed, "usage") and parsed.usage is not None:
            u = parsed.usage
            usage_data["prompt_tokens"] = getattr(u, "prompt_tokens", 0)
            usage_data["completion_tokens"] = getattr(u, "completion_tokens", 0)
            usage_data["total_tokens"] = getattr(u, "total_tokens", 0)
        return usage_data

    # -----------------------------------------------------------------------
    # Synchronous Inference Method
    # -----------------------------------------------------------------------

    def complete(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> ZeroGResponse:
        """
        Executes a synchronous completion on 0G Private Computer.

        Args:
            prompt: User prompt text (used if messages is None)
            system_prompt: Optional system prompt text
            messages: Full list of message dicts ({'role': '...', 'content': '...'})
            model: Model override (defaults to configured ZG_MODEL)
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens in generated response
            extra_body: Optional vendor-specific payload arguments

        Returns:
            ZeroGResponse containing content, model ID, response ID, request ID, and token usage.
        """
        client = self._get_sync_client()
        target_model = model or self._model

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
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        try:
            # Use with_raw_response to capture HTTP request headers and request ID
            raw_response = client.chat.completions.with_raw_response.create(**create_kwargs)
            parsed = raw_response.parse()

            content = ""
            finish_reason = None
            if parsed.choices:
                choice = parsed.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason

            return ZeroGResponse(
                content=content,
                model=getattr(parsed, "model", target_model),
                response_id=getattr(parsed, "id", None),
                request_id=self._extract_request_id(raw_response),
                usage=self._extract_usage(parsed),
                finish_reason=finish_reason,
                http_status=getattr(raw_response, "status_code", 200),
            )
        except Exception as e:
            self._handle_exception(e)
            raise  # Unreachable but helps type checkers

    # -----------------------------------------------------------------------
    # Asynchronous Inference Method
    # -----------------------------------------------------------------------

    async def complete_async(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        extra_body: Optional[Dict[str, Any]] = None,
    ) -> ZeroGResponse:
        """
        Executes an asynchronous completion on 0G Private Computer.
        """
        async_client = self._get_async_client()
        target_model = model or self._model

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
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        try:
            raw_response = await async_client.chat.completions.with_raw_response.create(**create_kwargs)
            parsed = raw_response.parse()

            content = ""
            finish_reason = None
            if parsed.choices:
                choice = parsed.choices[0]
                content = choice.message.content or ""
                finish_reason = choice.finish_reason

            return ZeroGResponse(
                content=content,
                model=getattr(parsed, "model", target_model),
                response_id=getattr(parsed, "id", None),
                request_id=self._extract_request_id(raw_response),
                usage=self._extract_usage(parsed),
                finish_reason=finish_reason,
                http_status=getattr(raw_response, "status_code", 200),
            )
        except Exception as e:
            self._handle_exception(e)
            raise

    # -----------------------------------------------------------------------
    # String representation (Never leaks credentials)
    # -----------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ZeroGClient(model='{self._model}', base_url='{self._base_url}', "
            f"api_key={'***' if self._api_key else 'None'}, "
            f"timeout={self._timeout})"
        )

    def __str__(self) -> str:
        return self.__repr__()
