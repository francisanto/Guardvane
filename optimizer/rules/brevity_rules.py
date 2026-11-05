"""
Brevity and Token Economy Rules for Prompt Optimizer.
Eliminates conversational filler, avoids redundant instructions,
and promotes concise, high-density prompt directives.
"""

import re
from typing import List, Tuple

FILLER_PHRASES = [
    re.compile(r"^(please|could you please|can you please|kindly|i want you to)\s+", re.IGNORECASE),
    re.compile(r"\b(as an ai language model|as you know)\b", re.IGNORECASE),
]


def prune_filler_phrases(prompt: str) -> Tuple[str, List[str]]:
    """
    Removes conversational fluff while preserving all actionable instructions.
    """
    pruned = prompt
    removed = []
    for pattern in FILLER_PHRASES:
        if pattern.search(pruned):
            pruned = pattern.sub("", pruned).strip()
            removed.append("Trimmed conversational conversational filler for token efficiency.")
    return pruned, removed
