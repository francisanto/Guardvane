"""
Canonical OpiHub service catalogue.

All user-facing category lists, provider registration options, and automated
agent offerings must use this module. Unsupported services are not advertised.
"""

from typing import Dict, List, Optional

from marketplace.schemas import ServiceExecutionType


# Services that have a real Guardvane backend implementation.
CATALOGUE: List[Dict[str, object]] = [
    {
        "id": "prompt_engineering",
        "label": "Prompt Engineering",
        "description": "Design defensive system prompts, instruction boundaries, and few-shot examples.",
        "human_offered": True,
        "automated_backends": ["prov_zerog"],
    },
    {
        "id": "loop_engineering",
        "label": "Prompt Loop Engineering",
        "description": "Detect unbounded agent loops, recursive tool calls, and unconstrained state mutation.",
        "human_offered": True,
        "automated_backends": ["prov_zerog"],
    },
    {
        "id": "prompt_optimization",
        "label": "Prompt Optimization",
        "description": "Compress, clarify, and harden prompts using Guardvane analysis and 0G reasoning.",
        "human_offered": True,
        "automated_backends": ["prov_zerog"],
    },
    {
        "id": "prompt_security_analysis",
        "label": "Prompt Security Analysis",
        "description": "Scan prompts for injection, secret leakage, and application-risk labels.",
        "human_offered": True,
        "automated_backends": ["prov_promptguard"],
    },
    {
        "id": "codebase_security",
        "label": "Codebase Security Audit",
        "description": "Manual repository and architecture review delivered by a human security provider.",
        "human_offered": True,
        "automated_backends": [],
    },
    {
        "id": "application_security_testing",
        "label": "Application Security Testing",
        "description": "Manual application security testing delivered by a human security provider.",
        "human_offered": True,
        "automated_backends": [],
    },
]


# Smart contract audit is not a implemented Guardvane product surface.
EXCLUDED_UNSUPPORTED = ["smart_contract_audit", "ai_security", "llm_optimization", "rag_security"]


def catalogue_ids() -> List[str]:
    return [str(item["id"]) for item in CATALOGUE]


def get_catalogue_item(category_id: str) -> Optional[Dict[str, object]]:
    wanted = (category_id or "").strip().lower()
    for item in CATALOGUE:
        if item["id"] == wanted:
            return item
    return None


def human_offered_ids() -> List[str]:
    return [str(item["id"]) for item in CATALOGUE if item.get("human_offered")]


def validate_human_category(category_id: str) -> str:
    item = get_catalogue_item(category_id)
    if not item or not item.get("human_offered"):
        raise ValueError(
            f"Service '{category_id}' is not in the OpiHub catalogue. "
            f"Supported services: {', '.join(human_offered_ids())}."
        )
    return str(item["id"])


def public_catalogue() -> List[Dict[str, object]]:
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "description": item["description"],
            "human_offered": item["human_offered"],
            "has_automated_agent": bool(item.get("automated_backends")),
            "default_execution_type": (
                ServiceExecutionType.AUTOMATED.value
                if item.get("automated_backends")
                else ServiceExecutionType.MANUAL.value
            ),
        }
        for item in CATALOGUE
    ]
