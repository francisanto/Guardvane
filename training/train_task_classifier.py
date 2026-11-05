#!/usr/bin/env python3
"""
PromptShield AI — Local Task Classification Model Training Pipeline.
===================================================================
Trains a local multi-class classifier to predict task categories for prompts:
- code_generation
- security_analysis
- data_analysis
- creative_and_writing
- reasoning_and_math
- general_instruction

Evaluates on a held-out stratified test set and saves:
- Artifact: artifacts/task_classifier/model.pkl
- Compatibility model: models/task_classifier_model.pkl
- Metrics: artifacts/task_classifier/metrics.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

# Import dataset from ml or use the canonical dataset
from ml.train_task_classifier import TASK_DATASET


def train_task_classifier(
    artifact_model_path: Path,
    legacy_model_path: Path,
    artifact_metrics_path: Path,
    legacy_metrics_path: Path,
    test_size: float = 0.20,
    random_state: int = 42
) -> Dict:
    """
    Trains and evaluates the local Task Classification Model,
    saving to both modern artifacts/ and legacy models/ destinations.
    """
    print("=" * 70)
    print("PROMPTSHIELD AI — TASK CLASSIFICATION TRAINING PIPELINE")
    print("=" * 70)

    df = pd.DataFrame(TASK_DATASET, columns=["prompt", "task_category"])
    print(f"Total labeled prompts: {len(df)}")
    print("\nClass Distribution:")
    for cat, count in df["task_category"].value_counts().items():
        print(f"  {cat:<25}: {count} ({count/len(df)*100:.1f}%)")

    X = df["prompt"]
    y = df["task_category"]

    # Stratified Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        stratify=y,
        random_state=random_state
    )

    print(f"\nTrain Split: {len(X_train)} samples")
    print(f"Test Split:  {len(X_test)} samples (held-out)")

    # Build Pipeline: TF-IDF + Logistic Regression
    pipeline = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=6000,
                sublinear_tf=True
            )
        ),
        (
            "classifier",
            LogisticRegression(
                solver="liblinear",
                C=1.5,
                class_weight="balanced",
                random_state=random_state
            )
        )
    ])

    print("\nTraining local task classification pipeline...")
    pipeline.fit(X_train, y_train)

    # Evaluate on Held-Out Test Set
    y_pred = pipeline.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted"))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))

    print("\n" + "=" * 70)
    print("EVALUATION RESULTS (HELD-OUT TEST SET)")
    print("=" * 70)
    print(f"Accuracy:    {accuracy * 100:.2f}%")
    print(f"Weighted F1: {weighted_f1 * 100:.2f}%")
    print(f"Macro F1:    {macro_f1 * 100:.2f}%")

    report_dict = classification_report(y_test, y_pred, output_dict=True)

    # Build Artifacts
    classes = list(pipeline.named_steps["classifier"].classes_)
    artifact = {
        "model_name": "PromptShield Task Classifier",
        "pipeline": pipeline,
        "classes": classes,
        "metrics": {
            "accuracy": round(accuracy, 4),
            "weighted_f1": round(weighted_f1, 4),
            "macro_f1": round(macro_f1, 4)
        }
    }

    # Save to artifacts/
    artifact_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_model_path)
    # Also save with filename task_classifier_model.pkl in artifacts/
    joblib.dump(artifact, artifact_model_path.parent / "task_classifier_model.pkl")

    # Save to models/ for backward compatibility
    legacy_model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, legacy_model_path)
    print(f"Model saved to artifacts: {artifact_model_path.resolve()}")
    print(f"Model saved to models:    {legacy_model_path.resolve()}")

    # Save Metrics JSON
    metrics_data = {
        "model_name": "PromptShield Task Classifier",
        "evaluation_timestamp": pd.Timestamp.now().isoformat(),
        "total_samples": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "overall_metrics": {
            "accuracy": round(accuracy, 4),
            "weighted_f1": round(weighted_f1, 4),
            "macro_f1": round(macro_f1, 4)
        },
        "per_class_metrics": {
            k: {sub_k: round(v, 4) if isinstance(v, float) else v for sub_k, v in val.items()}
            if isinstance(val, dict) else round(val, 4)
            for k, val in report_dict.items()
        }
    }

    artifact_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(artifact_metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    legacy_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(legacy_metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)

    return metrics_data


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent
    artifact_model = repo_root / "artifacts" / "task_classifier" / "model.pkl"
    legacy_model = repo_root / "models" / "task_classifier_model.pkl"
    artifact_metrics = repo_root / "artifacts" / "task_classifier" / "metrics.json"
    legacy_metrics = repo_root / "ml" / "results" / "task_classifier_metrics.json"

    train_task_classifier(artifact_model, legacy_model, artifact_metrics, legacy_metrics)
