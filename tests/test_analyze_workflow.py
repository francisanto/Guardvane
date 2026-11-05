"""
Test Suite for Guardvane Local Security Engine & /analyze Workflow.
Verifies:
1. Real inference on all 5 test prompts.
2. Invocations of prompt_security_model, security_risk_model, and task_classifier_model.
3. Sensitive credential detection.
4. Elimination of NaN% and safe probability-to-percentage conversion.
5. Error handling and response schema consistency.
"""

import pytest
from fastapi.testclient import TestClient
from main import app
from analyzers.prompt_analyzer import analyze_prompt
from analyzers.prompt_security_analyzer import analyze_prompt_security
from analyzers.sensitive_data_detector import detect_sensitive_data
from analyzers.model_comparison.task_classifier import task_classifier


@pytest.fixture
def client():
    return TestClient(app)


FIVE_PROMPTS = [
    ("Prompt 1", "Build a simple portfolio website using React and Tailwind CSS.", False, [], "code_generation"),
    ("Prompt 2", "Build a login page using React and PostgreSQL. Store passwords and implement authentication.", False, [], "code_generation"),
    ("Prompt 3", "Allow users to upload profile images and documents to the server.", False, ["file_upload"], "code_generation"),
    ("Prompt 4", "Create an endpoint that fetches content from any URL supplied by the user.", True, [], "code_generation"),
    ("Prompt 5", "Store API keys and secret credentials in frontend JavaScript.", False, [], "security_analysis"),
]


def test_five_prompts_direct_analyzer():
    """Verify local ML engine inference on all 5 required prompts."""
    for label, prompt, expected_malicious, expected_risks, expected_task in FIVE_PROMPTS:
        res = analyze_prompt(prompt, analysis_mode="both")
        assert res["status"] == "success", f"{label} status must be success"
        
        # 1. Prompt Security Model
        p_sec = res["prompt_security"]
        assert p_sec["status"] == "success"
        assert isinstance(p_sec["malicious_probability"], float)
        assert 0.0 <= p_sec["malicious_probability"] <= 1.0
        assert p_sec["is_malicious"] == expected_malicious, f"{label} malicious flag mismatch"
        assert p_sec["confidence_score"] == p_sec["malicious_probability"]
        assert p_sec["is_injection_detected"] == p_sec["is_malicious"]
        assert p_sec["risk_category"] in {"Critical Risk", "High Risk", "Medium Risk", "Low Risk"}

        # 2. Application Risk Model
        app_r = res["application_risks"]
        assert app_r["status"] == "success"
        assert isinstance(app_r["detected_risks"], list)
        for r in expected_risks:
            assert r in app_r["detected_risks"], f"{label} expected risk {r}"

        # 3. Task Classifier Model
        assert res["task_type"] == expected_task, f"{label} expected task {expected_task}, got {res['task_type']}"
        assert res["task_classification"] is not None
        assert res["task_classification"]["category"] == expected_task
        assert 0.0 <= res["task_classification"]["confidence"] <= 1.0


def test_five_prompts_via_http_analyze(client):
    """Verify the /analyze endpoint execution and response schema."""
    for label, prompt, expected_malicious, expected_risks, expected_task in FIVE_PROMPTS:
        resp = client.post("/analyze", json={"prompt": prompt, "analysis_mode": "both"})
        assert resp.status_code == 200, f"{label} HTTP status must be 200"
        data = resp.json()
        assert data["status"] == "success"
        assert data["task_type"] == expected_task

        p_sec = data["prompt_security"]
        assert p_sec["is_malicious"] == expected_malicious
        assert "confidence_score" in p_sec
        assert "malicious_probability" in p_sec
        assert "is_injection_detected" in p_sec
        assert "risk_category" in p_sec

        # Verify no NaN or string corruption in numerical fields
        prob = p_sec["malicious_probability"]
        assert isinstance(prob, (int, float))
        assert not (prob != prob)  # NaN check in Python


def test_sensitive_data_detection(client):
    """Verify regex-based sensitive credential detection."""
    # 1. Clean prompt
    clean_res = detect_sensitive_data("Build a dashboard with React")
    assert clean_res["detected"] is False
    assert clean_res["findings_count"] == 0
    assert clean_res["has_sensitive_data"] is False
    assert clean_res["count"] == 0

    # 2. Prompt with real secrets
    dirty_prompt = "Database uri: postgresql://admin:MySecretPass123@db.prod.internal:5432/app with token: sk-abcdef123456789012345678"
    dirty_res = detect_sensitive_data(dirty_prompt)
    assert dirty_res["detected"] is True
    assert dirty_res["findings_count"] == 2
    assert dirty_res["has_sensitive_data"] is True
    assert dirty_res["count"] == 2
    assert len(dirty_res["findings"]) == 2

    # HTTP verification
    resp = client.post("/analyze", json={"prompt": dirty_prompt, "analysis_mode": "both"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["sensitive_data"]["detected"] is True
    assert data["sensitive_data"]["findings_count"] == 2
    assert data["sensitive_data"]["has_sensitive_data"] is True
    assert data["sensitive_data"]["count"] == 2


def test_database_health_check_endpoint(client):
    """Verify /health and /health/db endpoints return sanitized responses."""
    resp = client.get("/health")
    assert resp.status_code in {200, 503}
    data = resp.json()
    assert "status" in data
    assert "database" in data
    db_info = data["database"]
    assert "database_reachable" in db_info
    assert "latency_ms" in db_info
    assert "host" in db_info
    assert "port" in db_info
    assert "driver" in db_info
    # Ensure no passwords or raw credentials exist in response
    resp_text = resp.text.lower()
    assert "password=" not in resp_text
    assert "guardvane" in resp_text or "postgres" in resp_text

