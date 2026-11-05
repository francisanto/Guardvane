"""
Application Risk Model Training & Evaluation Pipeline for PromptShield AI.
Trains a multi-label classifier (TF-IDF + OneVsRestClassifier with LogisticRegression)
on the application security risk dataset to predict 15 potential application risks.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    f1_score,
    hamming_loss,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline


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


def validate_dataset(df: pd.DataFrame, risk_labels: List[str]) -> Dict[str, Any]:
    """
    Validates dataset columns, binary label integrity, prompt completeness,
    and identifies labels with zero positive or zero negative examples.
    """
    print("=" * 70)
    print("DATASET VALIDATION & PRE-TRAINING CHECKS")
    print("=" * 70)

    # 1. Verify prompt column
    if "prompt" not in df.columns:
        raise ValueError("Missing required column 'prompt' in dataset.")

    null_prompts = int(df["prompt"].isnull().sum())
    empty_prompts = int((df["prompt"].astype(str).str.strip() == "").sum())
    print(f"Total dataset records: {len(df):,}")
    print(f"Null prompts:          {null_prompts}")
    print(f"Empty prompts:         {empty_prompts}")

    if null_prompts > 0 or empty_prompts > 0:
        raise ValueError(f"Found {null_prompts} null and {empty_prompts} empty prompts in dataset.")

    # 2. Verify label columns exist and are binary
    missing_columns = [col for col in risk_labels if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required label columns in dataset: {missing_columns}")

    label_stats = {}
    zero_positive_labels = []
    zero_negative_labels = []

    print("\nPer-Label Class Distribution (Full Dataset):")
    print(f"{'Label':<20} | {'Positives (1)':<15} | {'Negatives (0)':<15} | {'Status'}")
    print("-" * 70)

    for col in risk_labels:
        unique_vals = set(df[col].dropna().unique())
        if not unique_vals.issubset({0, 1}):
            raise ValueError(f"Column '{col}' contains non-binary values: {unique_vals}")

        pos_count = int((df[col] == 1).sum())
        neg_count = int((df[col] == 0).sum())

        status = "OK"
        if pos_count == 0:
            status = "ZERO POSITIVES (Unlearnable)"
            zero_positive_labels.append(col)
        elif neg_count == 0:
            status = "ZERO NEGATIVES (Trivial)"
            zero_negative_labels.append(col)

        label_stats[col] = {
            "positives": pos_count,
            "negatives": neg_count,
            "positive_ratio": round(pos_count / len(df), 4)
        }

        print(f"{col:<20} | {pos_count:<15} | {neg_count:<15} | {status}")

    print("-" * 70)

    if zero_positive_labels:
        print("\n[IMPORTANT NOTICE / MODEL LIMITATION]")
        print(f"Labels with 0 positive examples in dataset: {zero_positive_labels}")
        print("Note: The model CANNOT learn to predict these labels from the training data.")
        print("OneVsRestClassifier will issue a UserWarning and default to predicting 0 for these labels.")
        print("This limitation will be explicitly documented in the evaluation report.\n")

    return {
        "total_records": len(df),
        "label_stats": label_stats,
        "zero_positive_labels": zero_positive_labels,
        "zero_negative_labels": zero_negative_labels
    }


def train_application_risk_model(
    data_path: Path,
    model_output_path: Path,
    metrics_output_path: Path,
    test_size: float = 0.2,
    random_state: int = 42
):
    """
    Executes the training and evaluation workflow for the Application Risk Model.
    """
    print("=" * 70)
    print("APPLICATION RISK MODEL TRAINING & EVALUATION PIPELINE")
    print("=" * 70)
    print(f"Dataset path:        {data_path.resolve()}")
    print(f"Model output path:   {model_output_path.resolve()}")
    print(f"Metrics output path: {metrics_output_path.resolve()}\n")

    if not data_path.exists():
        raise FileNotFoundError(f"Dataset file not found at: {data_path.resolve()}")

    df = pd.read_csv(data_path)

    # Validate dataset
    validation_info = validate_dataset(df, RISK_LABELS)

    X = df["prompt"].astype(str)
    y = df[RISK_LABELS]

    # Reproducible train/test split (avoids data leakage)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state
    )

    print(f"\nTrain/Test Split Summary (random_state={random_state}, test_size={test_size}):")
    print(f"Training examples: {len(X_train):,}")
    print(f"Testing examples:  {len(X_test):,}")

    # Build Pipeline: TF-IDF -> OneVsRest(LogisticRegression)
    # Using solver="liblinear" for stable convergence on sparse TF-IDF with balanced class weights
    print("\nConfiguring model architecture:")
    print("  - TfidfVectorizer(ngram_range=(1, 2), max_features=5000, lowercase=True)")
    print("  - OneVsRestClassifier(LogisticRegression(solver='liblinear', class_weight='balanced', max_iter=1000))")

    model = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000
            )
        ),
        (
            "classifier",
            OneVsRestClassifier(
                LogisticRegression(
                    solver="liblinear",
                    class_weight="balanced",
                    max_iter=1000,
                    random_state=random_state
                )
            )
        )
    ])

    print("\nFitting model on training split...")
    model.fit(X_train, y_train)
    print("Model training completed successfully.")

    # Model Evaluation
    print("\n" + "=" * 70)
    print("MODEL EVALUATION ON HELD-OUT TEST SET")
    print("=" * 70)

    y_pred = model.predict(X_test)

    # Per-label and overall metrics
    report_dict = classification_report(
        y_test,
        y_pred,
        target_names=RISK_LABELS,
        output_dict=True,
        zero_division=0
    )
    report_text = classification_report(
        y_test,
        y_pred,
        target_names=RISK_LABELS,
        zero_division=0
    )

    micro_precision = float(precision_score(y_test, y_pred, average="micro", zero_division=0))
    micro_recall = float(recall_score(y_test, y_pred, average="micro", zero_division=0))
    micro_f1 = float(f1_score(y_test, y_pred, average="micro", zero_division=0))

    macro_precision = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    macro_recall = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
    h_loss = float(hamming_loss(y_test, y_pred))

    print(f"Micro Precision: {micro_precision * 100:.2f}%")
    print(f"Micro Recall:    {micro_recall * 100:.2f}%")
    print(f"Micro F1:        {micro_f1 * 100:.2f}%")
    print(f"Macro Precision: {macro_precision * 100:.2f}%")
    print(f"Macro Recall:    {macro_recall * 100:.2f}%")
    print(f"Macro F1:        {macro_f1 * 100:.2f}%")
    print(f"Weighted F1:     {weighted_f1 * 100:.2f}%")
    print(f"Hamming Loss:    {h_loss:.4f} (proportion of incorrect label predictions)")
    print("\nDetailed Per-Label Classification Report:\n")
    print(report_text)

    # Inspect test misclassifications
    mismatch_count = 0
    print("Sample Test Set Predictions & Mismatches:")
    for i in range(len(X_test)):
        actual = y_test.iloc[i].values
        predicted = y_pred[i]
        if not (actual == predicted).all():
            mismatch_count += 1
            if mismatch_count <= 3:
                actual_risks = [lbl for lbl, val in zip(RISK_LABELS, actual) if val == 1]
                pred_risks = [lbl for lbl, val in zip(RISK_LABELS, predicted) if val == 1]
                print(f"  Prompt: \"{X_test.iloc[i][:100]}...\"")
                print(f"    Actual:    {actual_risks}")
                print(f"    Predicted: {pred_risks}\n")

    print(f"Total prompts with at least one mismatch: {mismatch_count} of {len(X_test)}")

    # Save metrics (ensure prompt_security_metrics.json is NEVER overwritten)
    metrics_data = {
        "model_name": "Application Risk Model",
        "evaluation_date": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(data_path),
        "total_dataset_records": len(df),
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "risk_labels": RISK_LABELS,
        "overall_metrics": {
            "micro_precision": round(micro_precision, 4),
            "micro_recall": round(micro_recall, 4),
            "micro_f1": round(micro_f1, 4),
            "macro_precision": round(macro_precision, 4),
            "macro_recall": round(macro_recall, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_f1": round(weighted_f1, 4),
            "hamming_loss": round(h_loss, 4)
        },
        "classification_report": report_dict,
        "label_distribution": validation_info["label_stats"],
        "unlearnable_labels": {
            "labels": validation_info["zero_positive_labels"],
            "explanation": "Zero positive instances exist in the dataset; model defaults to constant negative predictor."
        },
        "scientific_notes": {
            "model_type": "Multi-label text classification via TF-IDF (5000 max features) and OneVsRest Logistic Regression",
            "solver": "liblinear with balanced class weighting for stable sparse-matrix convergence",
            "validation_method": f"Held-out test set split ({int(test_size*100)}%), random_state={random_state}"
        }
    }

    metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_output_path, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"\nEvaluation metrics successfully saved to: {metrics_output_path.resolve()}")

    # Save model artifact
    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_output_path)
    print(f"Trained model artifact successfully saved to: {model_output_path.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_file = base_dir / "data" / "security_risk_dataset.csv"
    model_file = base_dir / "models" / "security_risk_model.pkl"
    metrics_file = base_dir / "ml" / "results" / "application_risk_metrics.json"

    train_application_risk_model(data_file, model_file, metrics_file)
