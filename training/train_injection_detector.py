#!/usr/bin/env python3
"""
PromptShield AI — Prompt Injection & Malicious Prompt Detector Training Pipeline.
================================================================================
Trains a calibrated binary classifier (TF-IDF + Logistic Regression) on the MPDD dataset
to classify prompts as benign (0) or malicious / prompt injection / jailbreak (1).

Saves to:
- artifacts/injection_detector/model.pkl
- artifacts/injection_detector/metrics.json
- models/prompt_security_model.pkl (backward compatibility)
- ml/results/prompt_security_metrics.json
"""

import json
import shutil
import sys
from pathlib import Path
from typing import Dict

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.train_prompt_security_model import train_prompt_security_model


def train_injection_detector(
    data_path: Path,
    artifact_model_path: Path,
    legacy_model_path: Path,
    artifact_metrics_path: Path,
    legacy_metrics_path: Path
) -> Dict:
    """
    Trains the injection detector and saves artifacts to both modern and legacy locations.
    """
    print("=" * 70)
    print("PROMPTSHIELD AI — INJECTION DETECTOR TRAINING PIPELINE")
    print("=" * 70)

    # Execute training via canonical pipeline
    train_prompt_security_model(data_path, legacy_model_path, legacy_metrics_path)

    # Sync to artifacts/
    artifact_model_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(legacy_model_path, artifact_model_path)
    shutil.copyfile(legacy_model_path, artifact_model_path.parent / "prompt_security_model.pkl")

    artifact_metrics_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(legacy_metrics_path, artifact_metrics_path)

    print(f"\nArtifact saved to: {artifact_model_path.resolve()}")
    print(f"Metrics saved to:  {artifact_metrics_path.resolve()}")

    with open(artifact_metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    data = REPO_ROOT / "data" / "processed" / "mpdd_clean.csv"
    artifact_m = REPO_ROOT / "artifacts" / "injection_detector" / "model.pkl"
    legacy_m = REPO_ROOT / "models" / "prompt_security_model.pkl"
    artifact_met = REPO_ROOT / "artifacts" / "injection_detector" / "metrics.json"
    legacy_met = REPO_ROOT / "ml" / "results" / "prompt_security_metrics.json"

    train_injection_detector(data, artifact_m, legacy_m, artifact_met, legacy_met)
