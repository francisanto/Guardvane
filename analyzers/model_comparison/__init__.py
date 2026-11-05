"""
PromptShield AI — Model Comparison Engine Package.
=================================================
Local foundation model comparison, token analysis, cost estimation,
and multi-criteria ranking (WSM/TOPSIS) without external API dependencies.
"""

from analyzers.model_comparison.registry import (
    ModelMetadata,
    ModelPricing,
    LifecycleStatus,
    ProductCategory,
    ProductAvailability,
    IDEProductMetadata,
    AppBuilderMetadata,
    registry
)
from analyzers.model_comparison.tokenizer_adapters import (
    BaseTokenizerAdapter,
    OpenAITokenizerAdapter,
    GeminiTokenizerAdapter,
    ClaudeTokenizerAdapter,
    TokenCountResult,
    get_tokenizer_adapter
)
from analyzers.model_comparison.feature_extractor import PromptFeatures, feature_extractor
from analyzers.model_comparison.task_classifier import (
    LocalTaskClassifier,
    TaskClassificationResult,
    task_classifier
)
from analyzers.model_comparison.cost_calculator import CostBreakdown, calculate_model_cost
from analyzers.model_comparison.suitability import calculate_suitability
from analyzers.model_comparison.ranker import (
    RankingMethod,
    RankingPreset,
    RankedModel,
    rank_models
)
from analyzers.model_comparison.engine import (
    ModelComparisonDetails,
    ModelComparisonReport,
    ModelComparisonEngine,
    comparison_engine
)

__all__ = [
    "ModelMetadata",
    "ModelPricing",
    "LifecycleStatus",
    "ProductCategory",
    "ProductAvailability",
    "IDEProductMetadata",
    "AppBuilderMetadata",
    "registry",
    "BaseTokenizerAdapter",
    "OpenAITokenizerAdapter",
    "GeminiTokenizerAdapter",
    "ClaudeTokenizerAdapter",
    "TokenCountResult",
    "get_tokenizer_adapter",
    "PromptFeatures",
    "feature_extractor",
    "LocalTaskClassifier",
    "TaskClassificationResult",
    "task_classifier",
    "CostBreakdown",
    "calculate_model_cost",
    "calculate_suitability",
    "RankingMethod",
    "RankingPreset",
    "RankedModel",
    "rank_models",
    "ModelComparisonDetails",
    "ModelComparisonReport",
    "ModelComparisonEngine",
    "comparison_engine"
]
