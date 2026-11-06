"""
Unit and Integration Tests for 0G Private Computer Integration.
All tests use mock fixtures to ensure ZERO actual 0G inference requests,
ZERO network calls, and ZERO credit expenditures.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.zero_g.config import (
    ZeroGSettings,
    get_zero_g_settings,
    VALID_TRUST_MODES,
    DEFAULT_TRUST_MODE,
)
from integrations.zero_g.client import (
    ZeroGClient,
    ZeroGResponse,
    ZeroGError,
    ZeroGConfigurationError,
    ZeroGAuthenticationError,
    ZeroGTimeoutError,
    ZeroGConnectionError,
    ZeroGAPIError,
    ZeroGRateLimitError,
    ZeroGInsufficientCreditError,
)
from integrations.zero_g.sanitizer import (
    sanitize_prompt_for_inference,
    sanitize_context_data,
    SanitizedPromptResult,
    SecretFindingMeta,
)
from integrations.zero_g.reasoning import (
    ZeroGReasoningEngine,
    ZeroGReasoningResult,
)
from integrations.zero_g.optimization import (
    ZeroGOptimizer,
    ZeroGOptimizationResult,
    zero_g_optimizer,
)
from integrations.zero_g.cache import ZeroGCache
from main import app


# ---------------------------------------------------------------------------
# 1. Configuration & Validation Tests
# ---------------------------------------------------------------------------

def test_missing_api_key_raises_configuration_error():
    """Verifies that missing API key raises ZeroGConfigurationError without exposing secrets."""
    settings = ZeroGSettings(enabled=True, base_url="https://api.0g.ai/v1", model="glm-5.2", has_api_key=False)
    with pytest.raises(ZeroGConfigurationError) as exc_info:
        settings.validate(require_api_key=True)
    assert "ZG_API_KEY" in str(exc_info.value)


def test_missing_base_url_or_model_raises_configuration_error():
    """Verifies missing base URL or model raises ZeroGConfigurationError."""
    settings_no_url = ZeroGSettings(enabled=True, base_url="", model="glm-5.2", has_api_key=True)
    with pytest.raises(ZeroGConfigurationError) as exc:
        settings_no_url.validate(require_api_key=True)
    assert "ZG_BASE_URL" in str(exc.value)

    settings_no_model = ZeroGSettings(enabled=True, base_url="https://api.0g.ai/v1", model="", has_api_key=True)
    with pytest.raises(ZeroGConfigurationError) as exc2:
        settings_no_model.validate(require_api_key=True)
    assert "ZG_MODEL" in str(exc2.value)


def test_invalid_trust_mode_raises_configuration_error():
    """Verifies that trust mode outside {standard, verified, private} is rejected."""
    settings = ZeroGSettings(
        enabled=True,
        base_url="https://api.0g.ai/v1",
        model="glm-5.2",
        trust_mode="super_untrusted_mode",
        has_api_key=True
    )
    with pytest.raises(ZeroGConfigurationError) as exc_info:
        settings.validate(require_api_key=True)
    assert "Invalid 0G trust mode" in str(exc_info.value)
    assert "standard" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Client Credential Safety & Headers Tests
# ---------------------------------------------------------------------------

def test_client_repr_and_properties_never_expose_raw_api_key():
    """Verifies that API keys are NEVER exposed via repr, str, or client properties."""
    raw_key = "sk-0g-super-secret-key-1234567890"
    client = ZeroGClient(
        api_key=raw_key,
        base_url="https://router-api.0g.ai/v1",
        model="glm-5.2",
        trust_mode="verified"
    )

    repr_output = repr(client)
    str_output = str(client)

    assert raw_key not in repr_output
    assert raw_key not in str_output
    assert not hasattr(client, "api_key")  # api_key property removed to prevent accidental leakage
    assert client.api_key_masked == "sk-...7890"


def test_client_error_handling_masks_credentials():
    """Verifies that exception handlers scrub any leaked keys from error messages."""
    raw_key = "sk-0g-leaked-key-abcdef"
    client = ZeroGClient(api_key=raw_key, base_url="https://mock.0g.ai/v1", model="glm-5.2")

    import openai
    mock_sync = MagicMock()
    mock_sync.chat.completions.with_raw_response.create.side_effect = openai.AuthenticationError(
        f"Authorization failed with token '{raw_key}' and Bearer {raw_key}",
        response=MagicMock(status_code=401, request=MagicMock()),
        body=None,
    )

    with patch.object(client, "_get_sync_client", return_value=mock_sync):
        with pytest.raises(ZeroGAuthenticationError) as exc_info:
            client.complete(prompt="Hello")

        err_msg = str(exc_info.value)
        assert raw_key not in err_msg
        assert "[REDACTED_ZG_API_KEY]" in err_msg


def test_client_injects_trust_mode_header():
    """Verifies that X-0G-Provider-Trust-Mode header is injected into the client."""
    client = ZeroGClient(
        api_key="mock-key",
        base_url="https://mock.0g.ai/v1",
        model="glm-5.2",
        trust_mode="verified"
    )
    headers = client._build_default_headers()
    assert headers.get("X-0G-Provider-Trust-Mode") == "verified"

    # Support all 3 valid modes
    client_private = ZeroGClient(api_key="mock-key", trust_mode="private")
    assert client_private._build_default_headers().get("X-0G-Provider-Trust-Mode") == "private"


def test_client_sync_and_async_initialization():
    """Verifies both synchronous and asynchronous OpenAI clients are initialized safely."""
    client = ZeroGClient(
        api_key="mock-key",
        base_url="https://mock.0g.ai/v1",
        model="glm-5.2",
        timeout=15.0,
        max_retries=0
    )
    sync_c = client._get_sync_client()
    async_c = client._get_async_client()

    assert sync_c.base_url == "https://mock.0g.ai/v1/"
    assert sync_c.max_retries == 0
    assert async_c.max_retries == 0


def test_client_extracts_request_id_and_does_not_claim_attestation():
    """Verifies that HTTP request ID is captured, but is_attestation_verified remains False."""
    client = ZeroGClient(api_key="mock-key", base_url="https://mock.0g.ai/v1", model="glm-5.2")

    mock_choice = MagicMock()
    mock_choice.message.content = "Hardened test prompt"
    mock_choice.finish_reason = "stop"

    mock_completion = MagicMock()
    mock_completion.id = "chatcmpl-001"
    mock_completion.model = "glm-5.2"
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 40
    mock_completion.usage.completion_tokens = 60
    mock_completion.usage.total_tokens = 100

    mock_raw_resp = MagicMock()
    mock_raw_resp.request_id = "req-0g-track-777"
    mock_raw_resp.status_code = 200
    mock_raw_resp.parse.return_value = mock_completion

    mock_sync = MagicMock()
    mock_sync.chat.completions.with_raw_response.create.return_value = mock_raw_resp

    with patch.object(client, "_get_sync_client", return_value=mock_sync):
        resp = client.complete(prompt="Test prompt")
        assert resp.request_id == "req-0g-track-777"
        assert resp.response_id == "chatcmpl-001"
        assert resp.trust_mode == "verified"
        assert resp.is_attestation_verified is False  # Must NOT claim cryptographic proof


# ---------------------------------------------------------------------------
# 3. Error Handling: Timeout, Rate Limit, Credits
# ---------------------------------------------------------------------------

def test_client_handles_timeout_error():
    """Verifies that APITimeoutError maps to ZeroGTimeoutError."""
    client = ZeroGClient(api_key="mock-key", base_url="https://mock.0g.ai/v1", model="glm-5.2")
    import openai
    mock_sync = MagicMock()
    mock_sync.chat.completions.with_raw_response.create.side_effect = openai.APITimeoutError("Request timed out")

    with patch.object(client, "_get_sync_client", return_value=mock_sync):
        with pytest.raises(ZeroGTimeoutError):
            client.complete(prompt="Test")


def test_client_handles_rate_limit_and_credit_errors():
    """Verifies HTTP 429 and 402/insufficient credit errors map to distinct exceptions."""
    client = ZeroGClient(api_key="mock-key", base_url="https://mock.0g.ai/v1", model="glm-5.2")
    import openai

    # 1. Rate Limit
    mock_sync = MagicMock()
    mock_sync.chat.completions.with_raw_response.create.side_effect = openai.RateLimitError(
        "Rate limit reached", response=MagicMock(status_code=429, request=MagicMock()), body=None
    )
    with patch.object(client, "_get_sync_client", return_value=mock_sync):
        with pytest.raises(ZeroGRateLimitError) as exc_info:
            client.complete(prompt="Test")
        assert exc_info.value.status_code == 429

    # 2. Insufficient Credits
    mock_sync_credits = MagicMock()
    mock_sync_credits.chat.completions.with_raw_response.create.side_effect = openai.APIStatusError(
        "Payment required: Insufficient 0G compute credits.",
        response=MagicMock(status_code=402, request=MagicMock()),
        body=None
    )
    with patch.object(client, "_get_sync_client", return_value=mock_sync_credits):
        with pytest.raises(ZeroGInsufficientCreditError):
            client.complete(prompt="Test")


# ---------------------------------------------------------------------------
# 4. Sensitive Data Sanitizer Tests
# ---------------------------------------------------------------------------

def test_sanitizer_supported_patterns_and_metadata():
    """Verifies all supported sensitive patterns are redacted with safe metadata."""
    prompt = (
        "Here is my config:\n"
        "openai_key = 'sk-proj-1234567890abcdef1234567890abcdef'\n"
        "anthropic_key = 'sk-ant-api03-abcdef1234567890abcdef1234567890'\n"
        "github = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456'\n"
        "aws = 'AKIAIOSFODNN7EXAMPLE'\n"
        "database = 'postgresql://user:secretpass@localhost:5432/db'\n"
        "password = 'MyHardcodedPassword123'\n"
    )
    res = sanitize_prompt_for_inference(prompt)

    assert res.secrets_detected is True
    assert res.redacted_count >= 5
    assert len(res.findings) >= 5

    # Safe metadata inspection (findings contain offsets and types, but ZERO secret strings)
    for f in res.findings:
        assert isinstance(f.secret_type, str)
        assert isinstance(f.placeholder, str)
        assert f.start_offset >= 0
        assert f.end_offset > f.start_offset
        assert not hasattr(f, "raw_secret")

    # Raw secrets scrubbed from sanitized string
    assert "sk-proj-" not in res.sanitized_prompt
    assert "sk-ant-" not in res.sanitized_prompt
    assert "ghp_" not in res.sanitized_prompt
    assert "AKIAIOSFODNN7EXAMPLE" not in res.sanitized_prompt
    assert "secretpass" not in res.sanitized_prompt
    assert "MyHardcodedPassword123" not in res.sanitized_prompt


def test_sanitize_context_data_scrubs_nested_dictionaries():
    """Verifies recursive sanitization of recommendations and empirical dictionaries."""
    data = {
        "finding": "Found key sk-proj-1234567890abcdef1234567890abcdef",
        "nested": [
            "Use password = 'supersecret'",
            {"url": "postgresql://root:dbpass@prod:5432/main"}
        ]
    }
    cleaned = sanitize_context_data(data)
    cleaned_str = json.dumps(cleaned)

    assert "sk-proj-" not in cleaned_str
    assert "supersecret" not in cleaned_str
    assert "dbpass" not in cleaned_str
    assert "[REDACTED_" in cleaned_str


# ---------------------------------------------------------------------------
# 5. Credit Optimization: Single-Call & Cache Tests
# ---------------------------------------------------------------------------

def test_optimizer_executes_exactly_one_remote_call():
    """
    CRITICAL CREDIT VERIFICATION:
    Verifies that the unified optimizer makes EXACTLY ONE 0G completion call,
    combining security reasoning and prompt synthesis without duplicate calls.
    """
    client = MagicMock(spec=ZeroGClient)
    client.is_enabled = True
    client.is_configured = True
    client.model = "glm-5.2"
    client.trust_mode = "verified"

    unified_response_payload = {
        "contextual_summary": "Unified 0G security analysis: web endpoint with SQL backend.",
        "risk_explanations": {
            "sqli": "Dynamic search query requires parameterized execution."
        },
        "missing_security_requirements": [
            "Use parameterized queries with SQLAlchemy"
        ],
        "remaining_risks": [
            "Monitor input rate limits"
        ],
        "optimized_prompt": (
            "### Core Objective\nBuild a hardened user search endpoint.\n\n"
            "### Security Guardrails\n- Use SQLAlchemy parameterized queries."
        ),
        "changes_summary": ["Injected parameterized queries constraint"],
        "applied_hardening_rules": ["Database Hardening: SQLi"],
        "preserved_intent": "Preserved requested search architecture."
    }

    mock_resp = ZeroGResponse(
        content=json.dumps(unified_response_payload),
        model="glm-5.2",
        response_id="chatcmpl-unified-01",
        request_id="req-unified-01",
        trust_mode="verified",
        usage={"prompt_tokens": 120, "completion_tokens": 150, "total_tokens": 270},
        duration_ms=450.0,
    )
    client.complete.return_value = mock_resp

    test_cache = ZeroGCache()
    optimizer = ZeroGOptimizer(client=client, cache=test_cache)

    result = optimizer.optimize(
        prompt="Write a Python script that searches users in SQL.",
        fallback_to_local=True,
        use_cache=True,
    )

    # 1. Verify exactly ONE call was made
    assert client.complete.call_count == 1

    # 2. Verify result contents
    assert result.engine == "0g_private_computer"
    assert result.fallback_used is False
    assert result.metadata["status"] == "0g_success"
    assert result.metadata["request_id"] == "req-unified-01"
    assert result.metadata["trust_mode"] == "verified"
    assert result.metadata["is_attestation_verified"] is False
    assert result.reasoning is not None
    assert "Unified 0G security analysis" in result.reasoning.contextual_summary
    assert "Core Objective" in result.optimized_prompt


def test_optimizer_cache_hit_makes_zero_remote_calls():
    """
    CRITICAL CREDIT VERIFICATION:
    Verifies that identical prompt and findings hit the local cache,
    resulting in ZERO 0G remote calls and saving credits.
    """
    client = MagicMock(spec=ZeroGClient)
    client.is_enabled = True
    client.is_configured = True
    client.model = "glm-5.2"
    client.trust_mode = "verified"

    unified_payload = {
        "contextual_summary": "Analysis for cached prompt.",
        "risk_explanations": {},
        "missing_security_requirements": [],
        "remaining_risks": [],
        "optimized_prompt": "### Hardened Prompt",
        "changes_summary": ["Hardened"],
        "applied_hardening_rules": [],
        "preserved_intent": "Preserved."
    }

    client.complete.return_value = ZeroGResponse(
        content=json.dumps(unified_payload),
        model="glm-5.2",
        response_id="chatcmpl-cache-1",
        request_id="req-cache-1",
    )

    test_cache = ZeroGCache()
    optimizer = ZeroGOptimizer(client=client, cache=test_cache)

    prompt = "Test caching behavior for repeated prompt."

    # Call 1: Miss -> Makes 1 call
    res1 = optimizer.optimize(prompt, use_cache=True)
    assert client.complete.call_count == 1
    assert res1.metadata["status"] == "0g_success"

    # Call 2: Hit -> Makes ZERO additional calls!
    res2 = optimizer.optimize(prompt, use_cache=True)
    assert client.complete.call_count == 1  # Still 1!
    assert res2.metadata["status"] == "0g_success_cached"
    assert res2.metadata["cached"] is True
    assert res2.metadata["inference_used"] is False


def test_optimizer_local_only_when_zg_disabled():
    """Verifies that ZG_ENABLED=False executes strictly locally without network calls."""
    client = MagicMock(spec=ZeroGClient)
    client.is_enabled = False  # Disabled switch

    optimizer = ZeroGOptimizer(client=client)
    res = optimizer.optimize("Test prompt", fallback_to_local=True)

    assert client.complete.call_count == 0
    assert res.fallback_used is False
    assert res.engine == "local_rule_based"
    assert res.metadata["status"] == "local_only"
    assert res.metadata["inference_used"] is False


def test_optimizer_falls_back_when_remote_call_fails():
    """Verifies deterministic fallback when 0G network throws an error."""
    client = MagicMock(spec=ZeroGClient)
    client.is_enabled = True
    client.is_configured = True
    client.model = "glm-5.2"
    client.trust_mode = "verified"
    client.complete.side_effect = ZeroGTimeoutError("0G Router timed out after 30s")

    test_cache = ZeroGCache()
    optimizer = ZeroGOptimizer(client=client, cache=test_cache)

    res = optimizer.optimize("Test prompt for fallback", fallback_to_local=True)

    assert res.fallback_used is True
    assert res.engine == "local_rule_based_fallback"
    assert res.metadata["status"] == "local_fallback"
    assert "timed out" in res.fallback_reason
    assert len(res.applied_hardening_rules) > 0


def test_optimizer_handles_malformed_model_output():
    """Verifies that if the model returns non-JSON text, the optimizer handles it gracefully."""
    client = MagicMock(spec=ZeroGClient)
    client.is_enabled = True
    client.is_configured = True
    client.model = "glm-5.2"
    client.trust_mode = "verified"

    # Return plain markdown without JSON
    client.complete.return_value = ZeroGResponse(
        content="Here is a plain markdown hardened prompt without JSON brackets.",
        model="glm-5.2",
        response_id="chatcmpl-plain-text",
        request_id="req-plain-text",
    )

    optimizer = ZeroGOptimizer(client=client, cache=ZeroGCache())
    res = optimizer.optimize("Test malformed prompt", fallback_to_local=True)

    assert res.engine == "0g_private_computer"
    assert res.fallback_used is False
    assert "Here is a plain markdown" in res.optimized_prompt


# ---------------------------------------------------------------------------
# 6. FastAPI POST /optimize Integration Test
# ---------------------------------------------------------------------------

def test_fastapi_post_optimize_observability_schema():
    """Verifies that POST /optimize returns full 0G metadata and telemetry."""
    test_client = TestClient(app)

    opt_payload = {
        "contextual_summary": "Security reasoning via FastAPI test.",
        "risk_explanations": {},
        "missing_security_requirements": ["Input validation"],
        "remaining_risks": ["Audit logs"],
        "optimized_prompt": "### Hardened API Prompt",
        "changes_summary": ["Applied boundary checks"],
        "applied_hardening_rules": ["Input Validation"],
        "preserved_intent": "Preserved."
    }

    mock_resp = ZeroGResponse(
        content=json.dumps(opt_payload),
        model="glm-5.2",
        response_id="chatcmpl-api-test",
        request_id="req-api-track-999",
        trust_mode="verified",
        usage={"prompt_tokens": 50, "completion_tokens": 70, "total_tokens": 120},
        duration_ms=310.0,
    )

    from unittest.mock import PropertyMock

    with patch.object(ZeroGClient, "is_enabled", new_callable=PropertyMock, return_value=True), \
         patch.object(ZeroGClient, "is_configured", new_callable=PropertyMock, return_value=True), \
         patch.object(zero_g_optimizer.client, "complete", return_value=mock_resp):

        resp = test_client.post(
            "/optimize",
            json={
                "prompt": "Create a simple API endpoint in Python.",
                "analysis_mode": "both",
                "fallback_to_local": True
            }
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["engine"] == "0g_private_computer"
        assert data["zero_g_metadata"]["provider"] == "0g"
        assert data["zero_g_metadata"]["model"] == "glm-5.2"
        assert data["zero_g_metadata"]["trust_mode"] == "verified"
        assert data["zero_g_metadata"]["request_id"] == "req-api-track-999"
        assert data["zero_g_metadata"]["status"] == "0g_success"
        assert data["zero_g_metadata"]["total_tokens"] == 120
        assert data["zero_g_metadata"]["is_attestation_verified"] is False
