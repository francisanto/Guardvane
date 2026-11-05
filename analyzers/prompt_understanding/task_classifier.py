"""
Task Classifier Module for Prompt Understanding.
Infers primary domain task categories (code_generation, security_analysis, data_analysis, etc.)
with uncertainty estimation and model fallback.
"""

from pathlib import Path
from analyzers.model_comparison.task_classifier import (
    TaskClassificationResult,
    LocalTaskClassifier,
    task_classifier,
)


def get_task_classifier_model_path() -> Path:
    """Returns path to the task classifier model artifact."""
    root = Path(__file__).resolve().parent.parent.parent
    artifact_path = root / "artifacts" / "task_classifier" / "model.pkl"
    if artifact_path.exists():
        return artifact_path
    return root / "models" / "task_classifier_model.pkl"


__all__ = [
    "TaskClassificationResult",
    "LocalTaskClassifier",
    "task_classifier",
    "get_task_classifier_model_path",
]
