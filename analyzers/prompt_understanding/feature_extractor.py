"""
Prompt Feature Extractor Module for Prompt Understanding.
Analyzes lexical, syntactic, structural, and semantic properties of prompts.
"""

from analyzers.model_comparison.feature_extractor import (
    PromptFeatures,
    PromptFeatureExtractor,
    feature_extractor,
)

# Add extract alias for convenience
if not hasattr(feature_extractor, "extract"):
    feature_extractor.extract = feature_extractor.extract_features

__all__ = [
    "PromptFeatures",
    "PromptFeatureExtractor",
    "feature_extractor",
]
