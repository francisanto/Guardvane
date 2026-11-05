"""
Prompt Security Prediction CLI.
Classifies whether a prompt is Benign or Malicious using the trained Prompt Security Model.
"""

import sys
from pathlib import Path
import joblib


def load_model(model_path: Path):
    """
    Loads the saved Prompt Security Model artifact.
    """
    if not model_path.exists():
        raise FileNotFoundError(
            f"Prompt Security Model artifact not found at: {model_path.resolve()}.\n"
            "Please run 'python ml/train_prompt_security_model.py' first."
        )
    artifact = joblib.load(model_path)
    return artifact


def predict_prompt(artifact: dict, prompt: str):
    """
    Performs inference on a single prompt.
    Returns prediction label ('Benign' or 'Malicious'), malicious probability, and benign probability.
    """
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

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
    is_malicious = bool(malicious_proba >= threshold)
    prediction = "Malicious" if is_malicious else "Benign"

    return {
        "prediction": prediction,
        "is_malicious": is_malicious,
        "malicious_probability": malicious_proba,
        "benign_probability": benign_proba
    }


def main():
    base_dir = Path(__file__).resolve().parent.parent
    model_path = base_dir / "models" / "prompt_security_model.pkl"

    # Get prompt from CLI argument or interactive input
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        try:
            prompt = input("\nEnter a prompt to analyze:\n> ")
        except (EOFError, KeyboardInterrupt):
            print("\nAnalysis aborted.")
            return

    if not prompt.strip():
        print("Error: Prompt is empty. Please provide valid text to analyze.")
        sys.exit(1)

    try:
        artifact = load_model(model_path)
        result = predict_prompt(artifact, prompt)

        print("\nPrompt Security Analysis")
        print("------------------------")
        print(f"Prediction: {result['prediction']}")
        print(f"Malicious probability: {result['malicious_probability'] * 100:.2f}%")
        print(f"Benign probability: {result['benign_probability'] * 100:.2f}%")

    except Exception as e:
        print(f"Error during prediction: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
