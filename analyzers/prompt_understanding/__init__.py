"""
Prompt Understanding Subpackage for PromptShield AI.
Combines Task Classification, Prompt Feature Extraction, and Intent Parsing.
"""

from pathlib import Path

from analyzers.model_comparison.task_classifier import (
    TaskClassificationResult,
    LocalTaskClassifier,
    task_classifier,
)
from analyzers.model_comparison.feature_extractor import (
    PromptFeatures,
    PromptFeatureExtractor,
    feature_extractor,
)
from analyzers.prompt_understanding.intent_analyzer import (
    PromptIntentType,
    IntentAnalysisResult,
    IntentAnalyzer,
    intent_analyzer,
)

if not hasattr(feature_extractor, "extract"):
    feature_extractor.extract = feature_extractor.extract_features


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
    "PromptFeatures",
    "PromptFeatureExtractor",
    "feature_extractor",
    "PromptIntentType",
    "IntentAnalysisResult",
    "IntentAnalyzer",
    "intent_analyzer",
]
