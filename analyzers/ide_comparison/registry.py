"""
IDE Coding Assistant Registry for PromptShield AI.
Provides verified metadata, capability scores, and pricing details
for AI developer environments (Cursor, Windsurf, GitHub Copilot, Google Antigravity).
"""

from typing import Dict, List, Optional
from analyzers.model_comparison.registry import (
    IDEProductMetadata,
    registry,
    ProductCategory,
)


def list_ide_assistants(include_discontinued: bool = False) -> List[IDEProductMetadata]:
    """
    Returns list of verified IDE coding assistants.
    """
    return registry.list_ides(include_discontinued=include_discontinued)


def get_ide_assistant(product_id: str) -> Optional[IDEProductMetadata]:
    """
    Retrieves metadata for a specific IDE assistant by product_id.
    """
    return registry.get_ide(product_id)
