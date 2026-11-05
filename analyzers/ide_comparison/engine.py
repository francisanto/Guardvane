"""
Dedicated IDE Coding Assistant Comparison Engine for PromptShield AI.
Compares developer environments against workflow criteria and prompt specifications.
"""

from typing import Any, Dict, List, Optional
from analyzers.model_comparison.engine import comparison_engine, ModelComparisonReport
from analyzers.model_comparison.registry import ProductCategory
from analyzers.ide_comparison.registry import list_ide_assistants, get_ide_assistant
from analyzers.ide_comparison.scoring import score_ide_assistant


class IDEComparisonEngine:
    """
    Evaluator comparing AI-powered IDE developer assistants.
    """

    def compare(
        self,
        prompt: str = "",
        preset: str = "balanced",
        include_discontinued: bool = False
    ) -> ModelComparisonReport:
        """
        Executes comparison across all eligible IDE assistants.
        """
        return comparison_engine.compare_prompt(
            prompt=prompt,
            category=ProductCategory.IDE_ASSISTANT,
            preset=preset,
            include_deprecated=include_discontinued
        )


ide_comparison_engine = IDEComparisonEngine()
