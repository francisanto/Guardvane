"""
IDE Coding Assistant Comparison Subpackage for PromptShield AI.
Evaluates Cursor, Windsurf, GitHub Copilot, and Google Antigravity across
developer workflow criteria, agent autonomy, and enterprise privacy.
"""

from analyzers.ide_comparison.registry import (
    list_ide_assistants,
    get_ide_assistant,
)
from analyzers.ide_comparison.scoring import (
    score_ide_assistant,
)
from analyzers.ide_comparison.engine import (
    IDEComparisonEngine,
    ide_comparison_engine,
)

__all__ = [
    "list_ide_assistants",
    "get_ide_assistant",
    "score_ide_assistant",
    "IDEComparisonEngine",
    "ide_comparison_engine",
]
