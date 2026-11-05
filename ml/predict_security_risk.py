"""
Application Risk Predictor for PromptShield AI.
Loads the trained Application Risk Model and predicts potential security risks
implied by an application specification or prompt.
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib


RISK_LABELS: List[str] = [
    "sqli",
    "xss",
    "ssrf",
    "idor",
    "auth_weakness",
    "authz_weakness",
    "file_upload",
    "path_traversal",
    "command_injection",
    "csrf",
    "sensitive_data",
    "prompt_injection",
    "data_poisoning",
    "model_extraction",
    "ai_tool_risk"
]


def get_model_path() -> Path:
    """
    Returns the absolute path to the Application Risk Model artifact.
    """
    return Path(__file__).resolve().parent.parent / "models" / "security_risk_model.pkl"


def load_application_risk_model() -> Any:
    """
    Loads the trained model pipeline from the standardized artifact path.
    Raises FileNotFoundError if the artifact is missing.
    """
    model_path = get_model_path()
    if not model_path.exists():
        raise FileNotFoundError(
            f"Application Risk Model artifact not found at: {model_path.resolve()}\n"
            "Please train the model first using:\n"
            "  .venv/bin/python ml/train_security_model.py"
        )
    return joblib.load(model_path)


def predict_security_risks(prompt: str) -> Dict[str, Any]:
    """
    Runs inference on a prompt using the Application Risk Model.

    Returns:
        dict:
            - status: 'success', 'model_unavailable', or 'error'
            - detected_risks: list of detected risk labels, or None on failure
            - risk_count: number of detected risks, or None on failure
            - error: error message if failure
    """
    if not prompt or not prompt.strip():
        return {
            "status": "error",
            "detected_risks": None,
            "risk_count": None,
            "error": "Input prompt cannot be empty or contain only whitespace."
        }

    try:
        model = load_application_risk_model()
        pipeline = model if hasattr(model, "predict") else model.get("pipeline")
        if pipeline is None:
            return {
                "status": "error",
                "detected_risks": None,
                "risk_count": None,
                "error": "Loaded model artifact does not contain a valid predictor."
            }

        prediction = pipeline.predict([prompt])[0]
        detected = [
            label
            for label, value in zip(RISK_LABELS, prediction)
            if value == 1
        ]
        return {
            "status": "success",
            "detected_risks": detected,
            "risk_count": len(detected),
            "error": None
        }
    except FileNotFoundError as e:
        return {
            "status": "model_unavailable",
            "detected_risks": None,
            "risk_count": None,
            "error": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "detected_risks": None,
            "risk_count": None,
            "error": f"Inference execution failed: {str(e)}"
        }


def main():
    parser = argparse.ArgumentParser(
        description="Predict potential application security risks from a software specification prompt."
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        default=None,
        help="Prompt text to analyze. If not provided, you will be prompted interactively."
    )
    args = parser.parse_args()

    prompt = args.prompt
    if prompt is None:
        try:
            print("PromptShield AI — Application Risk Predictor")
            print("---------------------------------------------")
            prompt = input("Enter a prompt to analyze:\n> ")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

    # Validate non-empty
    if not prompt or not prompt.strip():
        print("\n[ERROR] Prompt cannot be empty or contain only whitespace.", file=sys.stderr)
        sys.exit(1)

    print("\nAnalyzing prompt for application security risks...")
    result = predict_security_risks(prompt)

    if result["status"] == "model_unavailable":
        print(f"\n[MODEL UNAVAILABLE ERROR]\n{result['error']}", file=sys.stderr)
        sys.exit(1)

    if result["status"] == "error":
        print(f"\n[INFERENCE ERROR]\n{result['error']}", file=sys.stderr)
        sys.exit(1)

    detected = result["detected_risks"]
    print("\n" + "=" * 60)
    print("APPLICATION SECURITY RISK PREDICTION RESULT")
    print("=" * 60)
    print(f"Prompt:\n\"{prompt}\"\n")

    if detected:
        print(f"Predicted Potential Risks ({len(detected)} detected):")
        for risk in detected:
            print(f"  [!] {risk}")
    else:
        print("No potential application security risks predicted for this prompt.")

    print("\nDisclaimer:")
    print("  These results are machine-learning predictions based on text pattern correlation,")
    print("  not proof or guarantee of actual security vulnerabilities in implemented code.")
    print("=" * 60)


if __name__ == "__main__":
    main()