"""
Prompt Security Analyzer Module for PromptShield AI.
Provides real-time inference for binary malicious prompt classification using
the Prompt Security Model artifact (TF-IDF + Logistic Regression).
"""

from pathlib import Path
from typing import Any, Dict, Optional
import joblib


_MODEL_ARTIFACT: Optional[Dict[str, Any]] = None


def get_model_path() -> Path:
    """
    Returns the absolute path to the saved Prompt Security Model artifact.
    """
    return Path(__file__).resolve().parent.parent / "models" / "prompt_security_model.pkl"


def load_security_model() -> Dict[str, Any]:
    """
    Loads and caches the Prompt Security Model artifact.
    Raises FileNotFoundError if the artifact is missing.
    """
    global _MODEL_ARTIFACT
    if _MODEL_ARTIFACT is None:
        model_path = get_model_path()
        if not model_path.exists():
            raise FileNotFoundError(
                f"Prompt Security Model artifact not found at: {model_path}. "
                "Train the model using '.venv/bin/python ml/train_prompt_security_model.py'."
            )
        _MODEL_ARTIFACT = joblib.load(model_path)
    return _MODEL_ARTIFACT


def analyze_prompt_security(prompt: str) -> Dict[str, Any]:
    """
    Analyzes whether an input prompt is benign or malicious using the trained Prompt Security Model.

    Returns:
        dict:
            - status (str): 'success', 'model_unavailable', or 'error'
            - is_malicious (bool or None): True if malicious probability >= 0.5, False if benign, None on error/unavailable
            - malicious_probability (float or None): Raw model probability for malicious class
            - benign_probability (float or None): Raw model probability for benign class
            - error (str, optional): Explanatory message when unavailable or failed
            - disclaimer (str): Scientific context on model predictions
    """
    disclaimer = (
        "Statistical classification based on MPDD training distribution. "
        "Predictions indicate prompt pattern similarity, not conclusive proof of malicious intent."
    )

    if not isinstance(prompt, str) or not prompt.strip():
        return {
            "status": "error",
            "is_malicious": None,
            "malicious_probability": None,
            "benign_probability": None,
            "error": "Prompt cannot be empty or contain only whitespace.",
            "disclaimer": disclaimer
        }

    try:
        artifact = load_security_model()
        pipeline = artifact.get("pipeline")

        if pipeline is not None:
            proba = pipeline.predict_proba([prompt])[0]
        else:
            vectorizer = artifact["vectorizer"]
            classifier = artifact["classifier"]
            features = vectorizer.transform([prompt])
            proba = classifier.predict_proba(features)[0]

        benign_proba = float(proba[0])
        malicious_proba = float(proba[1])

        threshold = float(artifact.get("decision_threshold", 0.5))
        return {
            "status": "success",
            "is_malicious": bool(malicious_proba >= threshold),
            "malicious_probability": round(malicious_proba, 4),
            "benign_probability": round(benign_proba, 4),
            "disclaimer": disclaimer
        }
    except FileNotFoundError as e:
        return {
            "status": "model_unavailable",
            "is_malicious": None,
            "malicious_probability": None,
            "benign_probability": None,
            "error": str(e),
            "disclaimer": disclaimer
        }
    except Exception as e:
        return {
            "status": "error",
            "is_malicious": None,
            "malicious_probability": None,
            "benign_probability": None,
            "error": f"Prompt security inference error: {str(e)}",
            "disclaimer": disclaimer
        }
