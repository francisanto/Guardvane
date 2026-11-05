"""
Multi-Criteria Scoring Engine for IDE Coding Assistants.
Computes weighted scores across developer workflow criteria:
- multi_file_agent
- repo_indexing
- terminal_execution
- model_flexibility
- ecosystem_integration
- privacy_controls
- plan_affordability
"""

from typing import Dict, List, Optional
from analyzers.model_comparison.registry import IDEProductMetadata
from analyzers.model_comparison.ranker import IDE_PRESET_WEIGHTS, RankedProduct


def score_ide_assistant(
    ide: IDEProductMetadata,
    preset: str = "balanced",
    custom_weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Computes a normalized multi-criteria recommendation score [0.0, 1.0] for an IDE assistant.
    """
    weights = custom_weights or IDE_PRESET_WEIGHTS.get(preset, IDE_PRESET_WEIGHTS["balanced"])
    total_weight = sum(weights.values())
    if total_weight <= 0:
        return 0.5

    norm_weights = {k: v / total_weight for k, v in weights.items()}
    score = 0.0
    for criterion, w in norm_weights.items():
        val = ide.criteria_scores.get(criterion, 0.5)
        score += w * val

    return round(score, 4)
