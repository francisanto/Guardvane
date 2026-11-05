"""
Unit and Integration Tests for 0G Private Computer Integration.
All tests use mock fixtures to ensure ZERO actual 0G inference requests,
ZERO network calls, and ZERO credit expenditures.
"""

import json
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.zero_g.client import (
    ZeroGClient,
    ZeroGResponse,
    ZeroGError,
    ZeroGConfigurationError,
    ZeroGAuthenticationError,
    ZeroGTimeoutError,
    ZeroGConnectionError,
    ZeroGAPIError,
)
from integrations.zero_g.sanitizer import (
    sanitize_prompt_for_inference,
    SanitizedPromptResult,
)
from integrations.zero_g.reasoning import (
    ZeroGReasoningEngine,
    ZeroGReasoningResult,
)
from integrations.zero_g.optimization import (
    ZeroGOptimizer,
    ZeroGOptimizationResult,
)
from main import app


# ---------------------------------------------------------------------------
# 1. Sanitizer & Redaction Tests
# ---------------------------------------------------------------------------

def test_sanitizer_redacts_api_keys_and_passwords():
    """Verifies that secrets are masked and never transmitted to 0G."""
    raw_prompt = (
        "Build a FastAPI service. Connect to database using postgresql://postgres:SuperSecretPassword123@db.prod:5432/main "
        "and call OpenAI using sk-proj-1234567890abcdef1234567890abcdef and AWS key AKIAIOSFODNN7EXAMPLE. "
        "Also set password = 'HardcodedPassword456'."
    )
    result = sanitize_prompt_for_inference(raw_prompt)

    assert result.secrets_detected is True
    assert result.redacted_count >= 3

    # Ensure raw secret strings are stripped from the prompt
    assert "SuperSecretPassword123" not in result.sanitized_prompt
    assert "sk-proj-1234567890abcdef1234567890abcdef" not in result.sanitized_prompt
    assert "AKIAIOSFODNN7EXAMPLE" not in result.sanitized_prompt
    assert "HardcodedPassword456" not in result.sanitized_prompt

    # Ensure clean placeholders are present
    assert "[REDACTED_" in result.sanitized_prompt
    assert "openai_api_key" in result.redacted_types
    assert "aws_access_key" in result.redacted_types


def test_sanitizer_preserves_clean_prompts():
    """Verifies clean prompts without credentials pass through unchanged."""
    clean_prompt = "Build a portfolio website with HTML, CSS, and vanilla JavaScript."
    result = sanitize_prompt_for_inference(clean_prompt)
    assert result.secrets_detected is False
    assert result.sanitized_prompt == clean_prompt
    assert len(result.redacted_types) == 0


# ---------------------------------------------------------------------------
# 2. Client Security & Representation Tests
# ---------------------------------------------------------------------------

def test_client_repr_never_exposes_api_key():
    """Verifies that client string representations mask the API key."""
    client = ZeroGClient(
        api_key="zg-secret-super-key-99999",
        base_url="https://api.0g.ai/v1",
        model="0g-deepseek-v3",
    )
    repr_str = repr(client)
    str_str = str(client)

    assert "zg-secret-super-key-99999" not in repr_str
    assert "zg-secret-super-key-99999" not in str_str
    assert "***" in repr_str


def test_client_configuration_validation():
    """Verifies clear exception handling when configuration is missing."""
    empty_client = ZeroGClient(api_key="", base_url="", model="")
    assert empty_client.is_configured() is False

    with pytest.raises(ZeroGConfigurationError) as exc_info:
        empty_client.validate_configuration()
    assert "ZG_API_KEY" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Client Mock Inference & Metadata Capture Tests
# ---------------------------------------------------------------------------

def test_client_sync_inference_metadata_capture():
    """
    Verifies that client accurately captures generated content, model ID,
    response ID, HTTP request ID, and token usage from raw response.
    """
    client = ZeroGClient(
        api_key="mock-key",
        base_url="https://mock.0g.ai/v1",
        model="0g-deepseek-r1",
    )

    # Build mock completion structure
    mock_choice = MagicMock()
    mock_choice.message.content = "Here is the 0G optimized prompt."
    mock_choice.finish_reason = "stop"

    mock_completion = MagicMock()
    mock_completion.id = "chatcmpl-zg-test-12345"
    mock_completion.model = "0g-deepseek-r1-custom"
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 150
    mock_completion.usage.completion_tokens = 85
    mock_completion.usage.total_tokens = 235

    mock_raw_resp = MagicMock()
    mock_raw_resp.request_id = "req-0g-http-998877"
    mock_raw_resp.headers = {"x-request-id": "req-0g-http-998877"}
    mock_raw_resp.status_code = 200
    mock_raw_resp.parse.return_value = mock_completion

    mock_sync_client = MagicMock()
    mock_sync_client.chat.completions.with_raw_response.create.return_value = mock_raw_resp

    with patch.object(client, "_get_sync_client", return_value=mock_sync_client):
        response: ZeroGResponse = client.complete(
            prompt="Optimize my app prompt",
            system_prompt="You are a security optimizer",
            temperature=0.5,
        )

        assert response.content == "Here is the 0G optimized prompt."
        assert response.model == "0g-deepseek-r1-custom"
        assert response.response_id == "chatcmpl-zg-test-12345"
        assert response.request_id == "req-0g-http-998877"
        assert response.usage["total_tokens"] == 235
        assert response.finish_reason == "stop"
        assert response.http_status == 200


def test_client_error_handling_sanitizes_leaked_keys():
    """Verifies that exceptions sanitize any raw API key traces."""
    secret_key = "zg-secret-do-not-leak-12345"
    client = ZeroGClient(api_key=secret_key, base_url="https://mock.0g.ai/v1", model="test-m")

    mock_sync = MagicMock()
    import openai
    # Simulate an error message containing the key
    mock_sync.chat.completions.with_raw_response.create.side_effect = openai.AuthenticationError(
        f"Invalid token '{secret_key}' provided."
    )

    with patch.object(client, "_get_sync_client", return_value=mock_sync):
        with pytest.raises(ZeroGAuthenticationError) as exc_info:
            client.complete(prompt="test")

        err_str = str(exc_info.value)
        assert secret_key not in err_str
        assert "[REDACTED_ZG_API_KEY]" in err_str


# ---------------------------------------------------------------------------
# 4. 0G Reasoning Engine Tests
# ---------------------------------------------------------------------------

def test_reasoning_engine_parses_structured_json():
    """Verifies 0G Reasoning Engine correctly parses structured threat modeling JSON."""
    client = MagicMock(spec=ZeroGClient)
    sample_json = {
        "contextual_summary": "The requested service handles user authentication and SQL database storage.",
        "risk_explanations": {
            "sqli": "Dynamic search queries against PostgreSQL require parameterized queries.",
            "auth_weakness": "User password endpoints require Argon2id hashing and rate limits."
        },
        "missing_security_requirements": [
            "Centralized input schema validation via Pydantic",
            "Rate limiting on /login and /register endpoints",
            "Secure session cookie flags (HttpOnly, SameSite=Strict)"
        ],
        "intent_preservation_notes": "Preserved FastAPI and PostgreSQL architecture requested by user.",
        "justifications": [
            "Prevent brute-force authentication attacks on public endpoints."
        ]
    }

    mock_resp = ZeroGResponse(
        content=json.dumps(sample_json),
        model="0g-deepseek-v3",
        response_id="chatcmpl-reasoning-001",
        request_id="req-reasoning-001",
        usage={"total_tokens": 300},
    )
    client.complete.return_value = mock_resp

    engine = ZeroGReasoningEngine(client=client)
    security_analysis = {
        "application_risks": {
            "detected_risks": ["sqli", "auth_weakness"],
            "unmitigated_surfaces": ["sqli", "auth_weakness"],
        }
    }

    result = engine.reason(
        prompt="Build a FastAPI app with login and database search.",
        security_analysis=security_analysis,
    )

    assert result.contextual_summary.startswith("The requested service")
    assert "sqli" in result.risk_explanations
    assert len(result.missing_security_requirements) == 3
    assert result.metadata["response_id"] == "chatcmpl-reasoning-001"
    assert result.metadata["request_id"] == "req-reasoning-001"


# ---------------------------------------------------------------------------
# 5. 0G Optimizer Flow & Fallback Tests
# ---------------------------------------------------------------------------

def test_optimizer_full_flow_with_mock():
    """Verifies full optimization pipeline with mock 0G client."""
    client = MagicMock(spec=ZeroGClient)
    client.is_configured.return_value = True

    opt_payload = {
        "optimized_prompt": (
            "### Core Objective\nBuild a secure FastAPI service with database storage.\n\n"
            "### Security Guardrails & Defense-in-Depth Constraints\n"
            "• Use SQLAlchemy ORM with prepared statements to prevent SQL injection.\n"
            "• Hash passwords using Argon2id with unique salt.\n"
        ),
        "changes_summary": ["Added SQLAlchemy ORM prepared statements", "Enforced Argon2id password hashing"],
        "applied_hardening_rules": ["Database Hardening: SQLi", "Authentication Hardening: Argon2id"],
        "missing_requirements_addressed": ["Input validation", "Password hashing"],
        "preserved_intent": "Preserved FastAPI framework and core business logic."
    }

    mock_resp = ZeroGResponse(
        content=json.dumps(opt_payload),
        model="0g-deepseek-v3",
        response_id="chatcmpl-opt-999",
        request_id="req-opt-999",
        usage={"prompt_tokens": 100, "completion_tokens": 120, "total_tokens": 220},
    )
    client.complete.return_value = mock_resp

    reasoning_engine = MagicMock(spec=ZeroGReasoningEngine)
    reasoning_engine.reason.return_value = ZeroGReasoningResult(
        contextual_summary="Web application with database access",
        missing_security_requirements=["Prepared statements", "Password hashing"],
        justifications=["Prevent SQLi and credential stuffing"],
    )

    optimizer = ZeroGOptimizer(client=client, reasoning_engine=reasoning_engine)

    prompt = "Build a FastAPI web app with user login and user search in postgresql."
    result = optimizer.optimize(prompt, fallback_to_local=True)

    assert result.engine == "0g_private_computer"
    assert result.fallback_used is False
    assert "Core Objective" in result.optimized_prompt
    assert "SQLAlchemy ORM" in result.optimized_prompt
    assert result.metadata["response_id"] == "chatcmpl-opt-999"
    assert result.metadata["request_id"] == "req-opt-999"


def test_optimizer_fallback_when_unconfigured():
    """Verifies seamless fallback to local deterministic optimizer when 0G is unconfigured."""
    unconfigured_client = ZeroGClient(api_key="", base_url="", model="")
    optimizer = ZeroGOptimizer(client=unconfigured_client)

    prompt = "Build a FastAPI web app with user login and user search in postgresql."
    result = optimizer.optimize(prompt, fallback_to_local=True)

    assert result.fallback_used is True
    assert result.engine == "local_rule_based_fallback"
    assert "Core Objective" in result.optimized_prompt
    assert len(result.applied_hardening_rules) > 0


# ---------------------------------------------------------------------------
# 6. FastAPI POST /optimize Endpoint Tests
# ---------------------------------------------------------------------------

def test_fastapi_post_optimize_endpoint_with_mock():
    """Verifies POST /optimize endpoint through FastAPI TestClient."""
    test_client = TestClient(app)

    opt_payload = {
        "optimized_prompt": (
            "### Core Objective\nBuild a hardened user management API in FastAPI.\n\n"
            "### Security Guardrails & Defense-in-Depth Constraints\n"
            "• Enforce parameterized database queries.\n"
        ),
        "changes_summary": ["Structured requirements", "Added parameterized query constraints"],
        "applied_hardening_rules": ["SQLi mitigation"],
        "missing_requirements_addressed": ["Prepared statements"],
        "preserved_intent": "Preserved FastAPI specification."
    }

    mock_resp = ZeroGResponse(
        content=json.dumps(opt_payload),
        model="0g-model-test",
        response_id="chatcmpl-fastapi-test",
        request_id="req-fastapi-test",
        usage={"prompt_tokens": 80, "completion_tokens": 90, "total_tokens": 170},
    )

    # Patch zero_g_optimizer.client in main
    with patch("main.zero_g_optimizer.client.is_configured", return_value=True), \
         patch("main.zero_g_optimizer.client.complete", return_value=mock_resp), \
         patch("main.zero_g_optimizer.reasoning_engine.reason", return_value=ZeroGReasoningResult(
             contextual_summary="Contextual summary",
             missing_security_requirements=["Prepared statements"],
             justifications=["Defense against SQLi"],
         )):

        response = test_client.post(
            "/optimize",
            json={
                "prompt": "Create a FastAPI endpoint that checks users in postgresql.",
                "analysis_mode": "both",
                "temperature": 0.5,
                "fallback_to_local": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["engine"] == "0g_private_computer"
        assert "optimized_prompt" in data
        assert "security_analysis" in data
        assert data["zero_g_metadata"]["response_id"] == "chatcmpl-fastapi-test"
        assert data["zero_g_metadata"]["request_id"] == "req-fastapi-test"


def test_fastapi_post_optimize_endpoint_fallback():
    """Verifies POST /optimize falls back gracefully when 0G is unconfigured."""
    test_client = TestClient(app)

    with patch("main.zero_g_optimizer.client.is_configured", return_value=False):
        response = test_client.post(
            "/optimize",
            json={
                "prompt": "Create a simple static webpage.",
                "fallback_to_local": True
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "fallback"
        assert data["engine"] == "local_rule_based_fallback"
        assert data["fallback_used"] is True
        assert "optimized_prompt" in data
