"""
PromptShield AI — Model Suitability Assessor.
============================================
Evaluates the architectural suitability of a foundation model for a specific prompt
based on extracted prompt features, predicted task category, model capabilities, and
task-classification confidence.
Produces a normalized relative suitability score in [0.0, 1.0].
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from analyzers.model_comparison.registry import ModelMetadata
from analyzers.model_comparison.feature_extractor import PromptFeatures
from analyzers.model_comparison.task_classifier import TaskClassificationResult


# Default transparent weights for suitability sub-factors
DEFAULT_SUITABILITY_WEIGHTS: Dict[str, float] = {
    "task_alignment": 0.35,
    "code_aptitude": 0.35,
    "complexity_fit": 0.20,
    "context_headroom": 0.10
}


@dataclass
class SuitabilityBreakdown:
    task_alignment_score: float
    code_aptitude_score: float
    complexity_fit_score: float
    context_headroom_score: float
    final_suitability_score: float
    applied_weights: Dict[str, float]


def get_suitability_breakdown(
    model: ModelMetadata,
    features: PromptFeatures,
    predicted_task: str,
    task_confidence: float,
    task_result: Optional[TaskClassificationResult] = None,
    weights: Optional[Dict[str, float]] = None
) -> SuitabilityBreakdown:
    """
    Computes component sub-scores and returns a detailed SuitabilityBreakdown.
    """
    capabilities = set(model.capabilities)
    w = dict(weights or DEFAULT_SUITABILITY_WEIGHTS)

    # 1. Base Task Alignment Score (0.0 to 1.0)
    # Check if top predicted class aligns with model capabilities
    if predicted_task in capabilities:
        task_score = 0.88 + (0.12 * min(1.0, task_confidence))
    elif task_result and task_result.is_low_confidence and any(c in capabilities for c in task_result.top_categories):
        # Confidence-aware fallback: if classifier is uncertain, give partial credit to top-2 classes
        task_score = 0.80
    elif "general_instruction" in capabilities:
        task_score = 0.70
    else:
        task_score = 0.55

    # 2. Engineering & Code Aptitude
    is_coding_task = (
        predicted_task == "code_generation"
        or (task_result and "code_generation" in task_result.top_categories and task_result.is_low_confidence)
        or features.code_proportion > 0.25
        or features.technical_keyword_density > 0.40
    )
    if is_coding_task:
        if model.model_id in [
            "gpt-6-astra", "gpt-5.5", "gpt-5.5-pro", "claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5-5",
            "gemini-4-argon", "deepseek-v4-pro", "deepseek-reasoner", "claude-3-7-sonnet", "o1"
        ]:
            code_score = 0.98
        elif model.model_id in [
            "gpt-6-sol", "gemini-3.8-flash", "gemini-3.7-flash", "grok-4.7", "grok-4-7",
            "deepseek-chat", "deepseek-flash", "o3-mini", "claude-3-5-sonnet"
        ]:
            code_score = 0.96
        elif model.model_id in [
            "gpt-5", "gemini-3.6-flash", "gemini-3.1-pro-preview", "gemini-3.1-pro",
            "gpt-4o", "gemini-1.5-pro"
        ]:
            code_score = 0.94
        elif model.model_id in [
            "gemini-3.5-flash", "grok-4.3", "grok-4-3", "gemini-2.0-flash", "gpt-4-turbo", "gemini-2.5-pro"
        ]:
            code_score = 0.91
        elif model.model_id in [
            "gpt-5-mini", "gpt-6-luna", "gemini-3.5-flash-lite", "claude-haiku-5-5",
            "claude-3-5-haiku", "gemini-2.0-flash-lite", "gemini-2.5-flash"
        ]:
            code_score = 0.88
        elif model.model_id in ["claude-3-opus", "grok-2", "grok-2-vision", "grok-3", "grok-3-mini"]:
            code_score = 0.84
        elif "code_generation" in capabilities:
            code_score = 0.85
        else:
            code_score = 0.70
    else:
        code_score = 0.80

    # 3. Complexity Matching Score
    is_flagship = model.model_id in [
        "gpt-6-astra", "gpt-6-sol", "gpt-5.5", "gpt-5.5-pro", "gpt-5",
        "gemini-4-argon", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.1-pro-preview", "gemini-3.1-pro",
        "claude-fable-5-1", "claude-opus-5-5", "claude-sonnet-5-5", "grok-4.7", "grok-4-7", "deepseek-v4-pro", "deepseek-reasoner",
        "claude-3-7-sonnet", "claude-3-5-sonnet", "o1", "o3-mini", "gpt-4o",
        "gemini-1.5-pro", "claude-3-opus", "deepseek-chat", "grok-2",
        "gemini-2.5-pro", "grok-3", "gpt-4-turbo"
    ] or "complex_reasoning" in capabilities or "hybrid_reasoning" in capabilities or "deep_thinking" in capabilities

    is_lightweight = model.model_id in [
        "gpt-5-mini", "gpt-6-luna", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash",
        "claude-haiku-5-5", "grok-4.3", "grok-4-3", "deepseek-flash",
        "gpt-4o-mini", "gemini-2.0-flash", "gemini-2.0-flash-lite", "claude-3-5-haiku",
        "gemini-1.5-flash", "o1-mini", "gemini-2.5-flash", "grok-3-mini", "gpt-3.5-turbo"
    ] or "fast_inference" in capabilities or "high_speed" in capabilities

    if features.complexity_score >= 0.40:
        complexity_fit = 0.96 if is_flagship else 0.74
    elif features.complexity_score <= 0.25:
        complexity_fit = 0.95 if is_lightweight else 0.80
    else:
        complexity_fit = 0.90 if is_flagship else 0.85

    # 4. Context Headroom Score
    total_tokens = features.word_count * 1.35 + features.estimated_output_tokens
    utilization_ratio = total_tokens / max(1, model.context_window_tokens)
    if utilization_ratio > 0.90:
        context_score = 0.20  # Risk of context overflow
    elif utilization_ratio > 0.50:
        context_score = 0.70
    elif model.context_window_tokens >= 1_000_000 and total_tokens > 10_000:
        context_score = 0.98  # Massive context advantage for long documents
    else:
        context_score = 0.90

    # Weighted blend
    total_w = sum(w.values()) or 1.0
    w_norm = {k: v / total_w for k, v in w.items()}

    final_suitability = (
        (task_score * w_norm.get("task_alignment", 0.35)) +
        (code_score * w_norm.get("code_aptitude", 0.35)) +
        (complexity_fit * w_norm.get("complexity_fit", 0.20)) +
        (context_score * w_norm.get("context_headroom", 0.10))
    )

    final_score = round(float(min(1.0, max(0.1, final_suitability))), 3)

    return SuitabilityBreakdown(
        task_alignment_score=round(task_score, 3),
        code_aptitude_score=round(code_score, 3),
        complexity_fit_score=round(complexity_fit, 3),
        context_headroom_score=round(context_score, 3),
        final_suitability_score=final_score,
        applied_weights=w_norm
    )


def calculate_suitability(
    model: ModelMetadata,
    features: PromptFeatures,
    predicted_task: str,
    task_confidence: float,
    task_result: Optional[TaskClassificationResult] = None,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Computes a multi-factor suitability score in [0.0, 1.0].
    Preserves exact backward compatibility with positional arguments.
    """
    breakdown = get_suitability_breakdown(
        model=model,
        features=features,
        predicted_task=predicted_task,
        task_confidence=task_confidence,
        task_result=task_result,
        weights=weights
    )
    return breakdown.final_suitability_score
