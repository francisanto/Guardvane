"""
Platform-managed automated agents.

Only Guardvane developers may create or mutate these records. Ordinary users
cannot register as automated agents or edit these profiles.

NOTE: As of 2026-11, all automated services are consolidated under a single
"0G Defence Agent" (prov_zerog). The former "Prompt Guard Agent"
(prov_promptguard) has been merged into this agent.
"""

from typing import Dict, List

PLATFORM_AGENT_IDS = ("prov_zerog",)

# Legacy ID kept for migration lookups (existing orders referencing the old provider).
LEGACY_AGENT_IDS = ("prov_promptguard",)

PLATFORM_AGENTS: List[Dict[str, object]] = [
    {
        "id": "prov_zerog",
        "display_name": "0G Defence Agent",
        "title": "AI-powered prompt security, engineering, and optimization",
        "provider_type": "automated",
        "description": (
            "Guardvane's unified AI security agent. Uses 0G Private Computer reasoning "
            "for prompt security analysis, injection detection, prompt engineering, "
            "loop defense, and prompt optimization — all in one agent."
        ),
        "skills": [
            "Prompt Security Analysis",
            "Prompt injection detection",
            "Secret leakage detection",
            "Application-risk labeling",
            "Prompt Engineering",
            "Prompt Loop Engineering",
            "Prompt Optimization",
            "Instruction-boundary hardening",
        ],
        "categories": [
            "prompt_engineering",
            "loop_engineering",
            "prompt_optimization",
            "prompt_security_analysis",
        ],
        "services": [
            {
                "id": "srv_zerog_security",
                "title": "Prompt Security Analysis",
                "category": "prompt_security_analysis",
                "description": "Scan a prompt for injection, credential leakage, and application-risk labels.",
                "price": 0.0,
                "estimated_delivery": "Instant 0G AI Reasoning",
            },
            {
                "id": "srv_zerog_prompt",
                "title": "Prompt Engineering",
                "category": "prompt_engineering",
                "description": "Generate defensive prompt structure and instruction boundaries.",
                "price": 0.0,
                "estimated_delivery": "Instant 0G AI Reasoning",
            },
            {
                "id": "srv_zerog_loop",
                "title": "Prompt Loop Engineering",
                "category": "loop_engineering",
                "description": "Analyze agent-loop bounds, recursion, and unconstrained tool use in prompt text.",
                "price": 0.0,
                "estimated_delivery": "Instant 0G AI Reasoning",
            },
            {
                "id": "srv_zerog_opt",
                "title": "Prompt Optimization",
                "category": "prompt_optimization",
                "description": "Optimize and harden submitted prompts using Guardvane analysis and 0G reasoning when configured.",
                "price": 0.0,
                "estimated_delivery": "Instant 0G AI Reasoning",
            },
        ],
    },
]


def is_platform_agent(provider_id: str) -> bool:
    return (provider_id or "") in PLATFORM_AGENT_IDS or (provider_id or "") in LEGACY_AGENT_IDS
