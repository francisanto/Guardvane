"""
Platform-managed automated agents.

Only Guardvane developers may create or mutate these records. Ordinary users
cannot register as automated agents or edit these profiles.
"""

from typing import Dict, List

PLATFORM_AGENT_IDS = ("prov_zerog", "prov_promptguard")

PLATFORM_AGENTS: List[Dict[str, object]] = [
    {
        "id": "prov_zerog",
        "display_name": "0G Defence Agent",
        "title": "Platform-managed prompt engineering, loop defense, and optimization",
        "provider_type": "automated",
        "description": (
            "Guardvane platform agent. Uses local Guardvane analyzers and optional 0G Private "
            "Computer reasoning to engineer, optimize, and bound prompts. Capabilities are limited "
            "to Prompt Engineering, Prompt Loop Engineering, and Prompt Optimization."
        ),
        "skills": [
            "Prompt Engineering",
            "Prompt Loop Engineering",
            "Prompt Optimization",
            "Instruction-boundary hardening",
        ],
        "categories": ["prompt_engineering", "loop_engineering", "prompt_optimization"],
        "services": [
            {
                "id": "srv_zerog_prompt",
                "title": "Prompt Engineering",
                "category": "prompt_engineering",
                "description": "Generate defensive prompt structure and instruction boundaries.",
                "price": 0.05,
                "estimated_delivery": "After payment verification",
            },
            {
                "id": "srv_zerog_loop",
                "title": "Prompt Loop Engineering",
                "category": "loop_engineering",
                "description": "Analyze agent-loop bounds, recursion, and unconstrained tool use in prompt text.",
                "price": 0.05,
                "estimated_delivery": "After payment verification",
            },
            {
                "id": "srv_zerog_opt",
                "title": "Prompt Optimization",
                "category": "prompt_optimization",
                "description": "Optimize and harden submitted prompts using Guardvane analysis and 0G reasoning when configured.",
                "price": 0.05,
                "estimated_delivery": "After payment verification",
            },
        ],
    },
    {
        "id": "prov_promptguard",
        "display_name": "Prompt Guard Agent",
        "title": "Platform-managed prompt security analysis",
        "provider_type": "automated",
        "description": (
            "Guardvane platform agent. Runs Guardvane prompt-security classifiers and sensitive-data "
            "detectors. Capability is limited to Prompt Security Analysis. It does not perform "
            "codebase, application, or smart-contract audits."
        ),
        "skills": [
            "Prompt injection detection",
            "Secret leakage detection",
            "Application-risk labeling",
        ],
        "categories": ["prompt_security_analysis"],
        "services": [
            {
                "id": "srv_pg_scan",
                "title": "Prompt Security Analysis",
                "category": "prompt_security_analysis",
                "description": "Scan a prompt for injection, credential leakage, and application-risk labels.",
                "price": 0.10,
                "estimated_delivery": "After payment verification",
            },
        ],
    },
]


def is_platform_agent(provider_id: str) -> bool:
    return (provider_id or "") in PLATFORM_AGENT_IDS
