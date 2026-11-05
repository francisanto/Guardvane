"""
End-to-End Test Suite for PromptShield AI.
Verifies model artifacts, training metrics, predictor scripts,
sensitive data detection, and FastAPI endpoints.
"""

import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import requests
import uvicorn

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from analyzers.prompt_analyzer import (
    APP_RISK_LABELS,
    analyze_application_risks,
    analyze_prompt,
    get_app_risk_model_path,
)
from analyzers.prompt_security_analyzer import analyze_prompt_security, get_model_path as get_prompt_sec_model_path
from analyzers.sensitive_data_detector import detect_sensitive_data
from ml.predict_security_risk import predict_security_risks
from main import app


def test_1_model_artifacts_exist():
    print("\n[TEST 1] Verifying model artifacts and metrics files...")
    app_risk_model = get_app_risk_model_path()
    prompt_sec_model = get_prompt_sec_model_path()
    app_metrics = REPO_ROOT / "ml" / "results" / "application_risk_metrics.json"
    prompt_metrics = REPO_ROOT / "ml" / "results" / "prompt_security_metrics.json"

    assert app_risk_model.exists(), f"Missing {app_risk_model}"
    assert prompt_sec_model.exists(), f"Missing {prompt_sec_model}"
    assert app_metrics.exists(), f"Missing {app_metrics}"
    assert prompt_metrics.exists(), f"Missing {prompt_metrics}"

    # Verify prompt_security_metrics.json was not overwritten with application risk metrics
    with open(prompt_metrics, "r") as f:
        p_data = json.load(f)
    assert p_data["model_name"] == "Prompt Security Model", "prompt_security_metrics.json was corrupted!"

    with open(app_metrics, "r") as f:
        a_data = json.load(f)
    assert a_data["model_name"] == "Application Risk Model", "application_risk_metrics.json has wrong model_name!"
    assert len(a_data["risk_labels"]) == 15, "Expected 15 risk labels in application risk metrics"
    assert "path_traversal" in a_data["unlearnable_labels"]["labels"], "Expected path_traversal in unlearnable labels"

    print("  ✓ All model artifacts and metrics files exist and have correct headers.")


def test_2_dataset_integrity():
    print("\n[TEST 2] Verifying security risk dataset...")
    data_path = REPO_ROOT / "data" / "security_risk_dataset.csv"
    assert data_path.exists(), f"Missing dataset: {data_path}"
    df = pd.read_csv(data_path)

    assert "prompt" in df.columns, "Missing 'prompt' column"
    assert (df["prompt"].astype(str).str.strip() == "").sum() == 0, "Dataset contains empty prompts"

    for label in APP_RISK_LABELS:
        assert label in df.columns, f"Missing label: {label}"
        unique_vals = set(df[label].dropna().unique())
        assert unique_vals.issubset({0, 1}), f"Non-binary values in {label}"

    assert (df["path_traversal"] == 1).sum() == 0, "path_traversal had positive examples unexpected by policy"
    print("  ✓ Dataset verified with all 15 labels binary and unlearnable label identified.")


def test_3_custom_prompts_inference():
    print("\n[TEST 3] Running inference on both custom prompts...")

    # Custom prompt 1 (complex web app with security controls)
    prompt_1 = (
        "Build a web application with user login, password reset, a database, and profile picture uploads. "
        "Store passwords securely using a suitable password-hashing algorithm, enforce authorization on "
        "every protected resource, validate uploaded files by content and size, store uploads outside the "
        "public web root, and apply rate limiting to authentication endpoints."
    )
    res_1 = predict_security_risks(prompt_1)
    assert res_1["status"] == "success", f"Inference failed for prompt 1: {res_1}"
    print(f"  Prompt 1 status: {res_1['status']}")
    print(f"  Prompt 1 predicted risks: {res_1['detected_risks']}")

    # Custom prompt 2 (simple static portfolio)
    prompt_2 = (
        "Build a simple static personal portfolio website with an About section, project cards, and contact information. "
        "It does not need login, a database, file uploads, or server-side processing."
    )
    res_2 = predict_security_risks(prompt_2)
    assert res_2["status"] == "success", f"Inference failed for prompt 2: {res_2}"
    print(f"  Prompt 2 status: {res_2['status']}")
    print(f"  Prompt 2 predicted risks: {res_2['detected_risks']}")

    # Verification: output is list and not None
    assert isinstance(res_1["detected_risks"], list)
    assert isinstance(res_2["detected_risks"], list)
    print("  ✓ Custom prompts evaluated successfully through real model.")


def test_4_error_handling_and_missing_models():
    print("\n[TEST 4] Verifying missing model and invalid prompt error handling...")

    # Empty prompt validation
    empty_res = predict_security_risks("   ")
    assert empty_res["status"] == "error", "Empty prompt should return error status"
    assert empty_res["detected_risks"] is None, "Empty prompt should not return risk list"

    # Missing model handling
    with patch("ml.predict_security_risk.get_model_path", return_value=Path("models/non_existent.pkl")):
        missing_res = predict_security_risks("Test valid prompt")
        assert missing_res["status"] == "model_unavailable"
        assert missing_res["detected_risks"] is None
        assert "train_security_model.py" in missing_res["error"]

    print("  ✓ Missing model reported with instructions; empty prompt rejected cleanly.")


def test_5_sensitive_data_detector():
    print("\n[TEST 5] Testing sensitive data detector...")
    sample_text = (
        "Project setup with OpenAI key sk-proj-1234567890abcdef1234567890 "
        "and DB connection postgres://app_user:s3cr3tP@ssw0rd@db.host.internal:5432/app_db"
    )
    detection = detect_sensitive_data(sample_text)
    assert detection["detected"] is True, "Sensitive data was not detected"
    assert detection["findings_count"] == 2, f"Expected 2 findings, got {detection['findings_count']}"

    # Verify secrets are redacted
    for finding in detection["findings"]:
        assert "1234567890abcdef" not in finding["redacted"], "Secret was leaked without redaction!"
        assert "s3cr3tP@ssw0rd" not in finding["redacted"], "Password was leaked without redaction!"
        print(f"  Found {finding['type']}: redacted as '{finding['redacted']}'")

    print("  ✓ Sensitive data detector identified tokens and correctly redacted them.")


def test_6_fastapi_endpoints():
    print("\n[TEST 6] Testing FastAPI live server endpoints...")

    server_port = 8009
    def run_server():
        uvicorn.run(app, host="127.0.0.1", port=server_port, log_level="error")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1.2)

    base_url = f"http://127.0.0.1:{server_port}"

    # 1. Root
    resp = requests.get(f"{base_url}/")
    assert resp.status_code == 200
    assert resp.json()["message"] == "PromptShield AI backend is running"

    # 2. Both mode
    payload_both = {
        "prompt": "Build a web application with user login, password reset, a database, and profile picture uploads.",
        "analysis_mode": "both"
    }
    resp = requests.post(f"{base_url}/analyze", json=payload_both)
    assert resp.status_code == 200, f"Both mode failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "success"
    assert "prompt_security" in data and data["prompt_security"]["status"] == "success"
    assert "application_risks" in data and data["application_risks"]["status"] == "success"
    assert "sensitive_data" in data
    assert data["model_availability"]["prompt_security_model"] is True
    assert data["model_availability"]["application_risk_model"] is True

    # 3. Mode application_risk
    payload_app = {
        "prompt": "Build a simple static personal portfolio website with an About section.",
        "analysis_mode": "application_risk"
    }
    resp = requests.post(f"{base_url}/analyze", json=payload_app)
    assert resp.status_code == 200
    data = resp.json()
    assert data["application_risks"]["status"] == "success"
    assert data["prompt_security"]["status"] == "skipped"

    # 4. Mode prompt_security
    payload_sec = {
        "prompt": "Can you explain how photosynthesis works in plants?",
        "analysis_mode": "prompt_security"
    }
    resp = requests.post(f"{base_url}/analyze", json=payload_sec)
    assert resp.status_code == 200
    data = resp.json()
    assert data["prompt_security"]["status"] == "success"
    assert data["application_risks"]["status"] == "skipped"

    # 5. Backward compatibility (omitted mode)
    payload_compat = {
        "prompt": "Build an online bookstore with shopping cart."
    }
    resp = requests.post(f"{base_url}/analyze", json=payload_compat)
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_mode"] == "both"
    assert data["application_risks"]["status"] == "success"
    assert data["prompt_security"]["status"] == "success"

    # 6. Empty prompt rejection
    resp_empty = requests.post(f"{base_url}/analyze", json={"prompt": "    "})
    assert resp_empty.status_code == 422, f"Expected 422, got {resp_empty.status_code}"

    print("  ✓ All FastAPI endpoints, modes, and validations passed.")


def main():
    print("=" * 70)
    print("PROMPTSHIELD AI END-TO-END VERIFICATION TEST SUITE")
    print("=" * 70)

    test_1_model_artifacts_exist()
    test_2_dataset_integrity()
    test_3_custom_prompts_inference()
    test_4_error_handling_and_missing_models()
    test_5_sensitive_data_detector()
    test_6_fastapi_endpoints()

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! (6/6 TEST GROUPS)")
    print("=" * 70)


if __name__ == "__main__":
    main()
