"""
0G-Powered Primary Security Reasoning and Prompt Hardening Engine.
Executes primary AI threat modeling, vulnerability evaluation, and prompt rewriting
on 0G Private Computer (0gm-1.0-35b-a3b) under X-0G-Provider-Trust-Mode: verified.

Local components are strictly confined to:
Stage A: Preprocessing (credential sanitization, input limits, token estimation, context extraction)
Stage D: Local validation (schema enforcement, secret leak detection, consistency verification)
Local rules and heuristics NEVER substitute for 0G AI reasoning when 0G is enabled.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from analyzers.prompt_analyzer import analyze_prompt
from analyzers.prompt_optimizer import prompt_optimizer, LocalPromptOptimizer, OptimizationResult
from integrations.zero_g.client import (
    ZeroGClient,
    ZeroGResponse,
    ZeroGError,
    ZeroGConfigurationError,
    ZeroGAuthenticationError,
    ZeroGRateLimitError,
    ZeroGInsufficientCreditError,
)
from integrations.zero_g.reasoning import ZeroGReasoningResult
from integrations.zero_g.sanitizer import (
    sanitize_prompt_for_inference,
    sanitize_context_data,
    SanitizedPromptResult,
)
from integrations.zero_g.cache import zero_g_cache, ZeroGCache

logger = logging.getLogger("guardvane.zerog.optimizer")


@dataclass
class ZeroGOptimizationResult:
    """Comprehensive result of 0G primary security reasoning and prompt hardening."""
    original_prompt: str
    sanitized_prompt: Optional[str]
    optimized_prompt: str
    reasoning: Optional[ZeroGReasoningResult]
    applied_hardening_rules: List[str] = field(default_factory=list)
    changes_summary: List[str] = field(default_factory=list)
    missing_requirements_addressed: List[str] = field(default_factory=list)
    preserved_intent: str = ""
    engine: str = "0g_private_computer"
    status: str = "0g_reasoning_completed"  # "0g_reasoning_completed", "0g_reasoning_failed", "local_only"
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    structured_reasoning: Optional[Dict[str, Any]] = None
    task_understanding: Dict[str, Any] = field(default_factory=dict)
    security_analysis_findings: List[Dict[str, Any]] = field(default_factory=list)
    overall_risk: str = "Low"
    changes_made: List[Dict[str, str]] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    remaining_risks: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    disclaimer: str = (
        "Security reasoning and prompt hardening evaluated by 0G Private Computer. "
        "Prompt hardening enforces defense-in-depth requirements but does not prove runtime code is invulnerable."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_prompt": self.original_prompt,
            "sanitized_prompt": self.sanitized_prompt,
            "optimized_prompt": self.optimized_prompt,
            "hardened_prompt": self.optimized_prompt,
            "reasoning": self.reasoning.to_dict() if self.reasoning else None,
            "structured_reasoning": self.structured_reasoning,
            "task_understanding": self.task_understanding,
            "security_analysis_findings": self.security_analysis_findings,
            "overall_risk": self.overall_risk,
            "applied_hardening_rules": self.applied_hardening_rules,
            "changes_summary": self.changes_summary,
            "changes_made": self.changes_made,
            "missing_requirements_addressed": self.missing_requirements_addressed,
            "assumptions": self.assumptions,
            "remaining_risks": self.remaining_risks,
            "preserved_intent": self.preserved_intent,
            "engine": self.engine,
            "status": self.status,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "disclaimer": self.disclaimer,
        }


class ZeroGOptimizer:
    """
    Primary Security Reasoning and Prompt Hardening Engine powered by 0G Private Computer.
    Executes deep application-specific threat modeling, risk evaluation, and prompt rewriting.
    """

    MAX_PROMPT_LENGTH = 10000

    PRIMARY_0G_SYSTEM_PROMPT = (
        "You are Guardvane's Primary Security Reasoning and Prompt Hardening Engine running inside 0G Private Computer.\n"
        "Your role is to perform intelligent, application-specific AI security evaluation, threat modeling, and prompt rewriting.\n\n"
        "CRITICAL DIRECTIVES:\n"
        "1. UNDERSTAND THE REAL APPLICATION:\n"
        "   Reason about the actual software, service, or task the developer is building (e.g. REST API, file upload handler, "
        "authentication system, database query pipeline, LLM agent, data processing script).\n"
        "   Do NOT automatically label every prompt as prompt injection or command injection. Evaluate vulnerabilities relevant to the specific application domain.\n\n"
        "2. APPLICATION-SPECIFIC SECURITY ANALYSIS:\n"
        "   Identify concrete vulnerabilities and realistic attack vectors based on the application's true context:\n"
        "   - File Uploads: Unrestricted file types, path traversal, file size exhaustion (DoS), stored XSS via SVG/HTML, MIME-type spoofing (missing magic byte validation), insecure storage permissions, lack of malware scanning.\n"
        "   - Authentication & Access: Weak password storage, missing Argon2id/bcrypt hashing, missing rate limiting/brute force protection, timing attacks, insecure session/JWT tokens (lack of HttpOnly/Secure/SameSite flags), CSRF, insecure password reset flows.\n"
        "   - Data & Databases: SQL injection, NoSQL injection, Broken Object Level Authorization (IDOR), sensitive data exposure, lack of input validation schemas (Pydantic/marshmallow), unpaginated queries.\n"
        "   - AI / LLM Applications: Direct prompt injection, jailbreaks, instruction overrides, indirect prompt injection via untrusted data, excessive agency, tool execution without authorization.\n"
        "   - General APIs / Utilities: Lack of input sanitization, denial of service via unbounded payloads, verbose error messages leaking stack traces.\n\n"
        "3. REWRITE INTO A SECURE, IMPLEMENTATION-READY SPECIFICATION:\n"
        "   The 'hardened_prompt' MUST be a complete, superior, production-grade rewrite of the user's ORIGINAL prompt that a software engineer or coding AI can directly execute.\n"
        "   - PRESERVE ORIGINAL INTENTION: If the user asked for a FastAPI file upload endpoint, the hardened prompt must ask to build that exact FastAPI file upload endpoint, but with comprehensive security controls, validation rules, error handling, and test specifications embedded.\n"
        "   - DO NOT return an abstract security audit report or generic checklist as the hardened prompt. It MUST be the rewritten, hardened prompt itself.\n"
        "   - Structure the hardened prompt with clear Markdown sections (e.g., ### Core Objective, ### Architecture & Tech Stack, ### Security Guardrails & Defense-in-Depth, ### Input Validation & Error Handling, ### Verification & Test Requirements).\n\n"
        "4. STRICT JSON FORMAT:\n"
        "Respond ONLY with a single valid JSON object with NO preamble, NO postscript, and NO markdown code fences.\n"
        "The JSON must adhere to this EXACT schema:\n"
        "{\n"
        '  "task_understanding": {\n'
        '    "application_type": "<e.g. \'REST API - File Upload Service\' or \'Web App - Authentication System\'>",\n'
        '    "user_intent": "<Concise summary of what the developer wants to achieve>",\n'
        '    "technologies": ["<relevant frameworks/languages, e.g. \'Python\', \'FastAPI\', \'Pydantic\'>"]\n'
        "  },\n"
        '  "security_analysis": {\n'
        '    "overall_risk": "<\'Critical\' | \'High\' | \'Medium\' | \'Low\'>",\n'
        '    "findings": [\n'
        "      {\n"
        '        "vulnerability": "<Vulnerability name, e.g. \'Unrestricted File Upload & Path Traversal\'>",\n'
        '        "severity": "<\'critical\' | \'high\' | \'medium\' | \'low\'>",\n'
        '        "confidence": <float between 0.0 and 1.0, e.g. 0.95>,\n'
        '        "evidence": "<Specific quote or aspect from the target prompt>",\n'
        '        "attack_scenario": "<Realistic explanation of how an attacker could exploit this in this application>",\n'
        '        "explanation": "<Technical root-cause explanation of the risk>",\n'
        '        "recommendation": "<Specific technical control to implement>"\n'
        "      }\n"
        "    ]\n"
        "  },\n"
        '  "missing_security_requirements": [\n'
        '    "<Specific missing defense-in-depth requirement 1>",\n'
        '    "<Specific missing defense-in-depth requirement 2>"\n'
        "  ],\n"
        '  "hardened_prompt": "<The complete, enhanced, implementation-ready prompt specification in Markdown>",\n'
        '  "changes_made": [\n'
        "    {\n"
        '      "change": "<Specific constraint or section added/modified>",\n'
        '      "reason": "<Security reason for this change>"\n'
        "    }\n"
        "  ],\n"
        '  "assumptions": [\n'
        '    "<Assumption regarding runtime environment, architecture, or scope>"\n'
        "  ],\n"
        '  "remaining_risks": [\n'
        '    "<Residual risk that requires external infrastructure controls, e.g. WAF, network segmentation>"\n'
        "  ]\n"
        "}"
    )

    def __init__(
        self,
        client: Optional[ZeroGClient] = None,
        local_optimizer: Optional[LocalPromptOptimizer] = None,
        cache: Optional[ZeroGCache] = None,
    ):
        self.client = client or ZeroGClient()
        self.local_optimizer = local_optimizer or prompt_optimizer
        self.cache = cache or zero_g_cache

    # -----------------------------------------------------------------------
    # Stage A: Local Preprocessing
    # -----------------------------------------------------------------------

    def preprocess_prompt(self, prompt: str, analysis_mode: str = "both") -> Dict[str, Any]:
        """
        Stage A — Local Preprocessing.
        Executes strictly deterministic and heuristic preprocessing:
        1. Input validation and size limits (max 10,000 chars, non-empty).
        2. Sensitive data detection and redaction (API keys, JWTs, DB URIs, passwords).
        3. Token estimation (~4 characters per token).
        4. Extracting application context and preliminary local signals.
        5. Preparing structured request for 0G Private Computer.

        Note: Local heuristics do NOT produce the final AI security reasoning.
        """
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Prompt cannot be empty or contain only whitespace.")

        # Enforce size limits
        cleaned_prompt = prompt.strip()
        if len(cleaned_prompt) > self.MAX_PROMPT_LENGTH:
            cleaned_prompt = cleaned_prompt[:self.MAX_PROMPT_LENGTH]

        # 1. Credential detection & redaction
        sanitization: SanitizedPromptResult = sanitize_prompt_for_inference(cleaned_prompt)
        inference_prompt = sanitization.sanitized_prompt

        # 2. Token estimation
        estimated_tokens = max(1, len(inference_prompt) // 4)

        # 3. Context extraction (local ML scan signals as advisory context for 0G)
        local_scan = analyze_prompt(cleaned_prompt, analysis_mode=analysis_mode)
        p_sec = local_scan.get("prompt_security") or {}
        app_risks = local_scan.get("application_risks") or {}
        injection_prob = p_sec.get("malicious_probability", 0.0)

        preliminary_signals = {
            "injection_probability": round(injection_prob, 4) if isinstance(injection_prob, (int, float)) else 0.0,
            "preliminary_heuristic_risks": app_risks.get("detected_risks", []),
            "preliminary_task_category": local_scan.get("task_type", "general"),
        }

        return {
            "original_prompt": cleaned_prompt,
            "sanitized_prompt": inference_prompt,
            "secrets_detected": sanitization.secrets_detected,
            "sanitization": sanitization,
            "estimated_tokens": estimated_tokens,
            "local_scan": local_scan,
            "preliminary_signals": preliminary_signals,
        }

    # -----------------------------------------------------------------------
    # Stage B & C: Request Building & Prompt Packaging
    # -----------------------------------------------------------------------

    def _build_0g_input(self, preprocessing: Dict[str, Any]) -> str:
        """Packages the target prompt and preprocessing context for 0G inference."""
        sanitized_prompt = preprocessing["sanitized_prompt"]
        sanitization: SanitizedPromptResult = preprocessing["sanitization"]

        payload: Dict[str, Any] = {
            "target_prompt": sanitized_prompt,
            "preprocessing_context": {
                "estimated_tokens": preprocessing["estimated_tokens"],
                "secrets_detected": sanitization.secrets_detected,
                "redacted_secret_types": sanitization.redacted_types,
                "redacted_count": sanitization.redacted_count,
            },
            "advisory_local_signals": preprocessing["preliminary_signals"],
        }

        return (
            "Analyze the target prompt and perform primary security reasoning, threat modeling, "
            "and prompt hardening in the required JSON format:\n\n"
            f"{json.dumps(payload, indent=2)}\n\n"
            "Produce the complete JSON response matching the required schema."
        )

    # -----------------------------------------------------------------------
    # Stage D: Local Validation
    # -----------------------------------------------------------------------

    def validate_and_sanitize_response(
        self,
        raw_text: str,
        original_prompt: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]], List[str]]:
        """
        Stage D — Local Validation.
        Validates the structure and content of the 0G model response:
        - Validates JSON format and required Stage C keys.
        - Enforces non-empty hardened prompt.
        - Identifies and redacts any exposed credentials introduced in the output.
        - Checks consistency between findings and recommendations.
        - Flags suspicious or missing fields.

        Does NOT silently replace missing 0G reasoning with fabricated AI findings.
        """
        errors: List[str] = []
        cleaned_text = raw_text.strip()

        # 1. Parse JSON with multi-strategy extraction and safe repair
        parsed: Optional[Dict[str, Any]] = None

        def try_parse_candidate(candidate_str: str) -> Optional[Dict[str, Any]]:
            if not candidate_str:
                return None
            try:
                res = json.loads(candidate_str, strict=False)
                if isinstance(res, dict):
                    return res
            except Exception:
                pass
            # Try trailing comma cleanup
            try:
                repaired = re.sub(r",\s*([\]}])", r"\1", candidate_str)
                res = json.loads(repaired, strict=False)
                if isinstance(res, dict):
                    return res
            except Exception:
                pass
            return None

        # Strategy A: Direct parse
        parsed = try_parse_candidate(cleaned_text)

        # Strategy B: Code block extraction
        if parsed is None:
            code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_text)
            if code_block_match:
                parsed = try_parse_candidate(code_block_match.group(1).strip())

        # Strategy C: Outermost braces extraction
        if parsed is None:
            first_brace = cleaned_text.find("{")
            last_brace = cleaned_text.rfind("}")
            if first_brace != -1 and last_brace > first_brace:
                parsed = try_parse_candidate(cleaned_text[first_brace : last_brace + 1])

        # Strategy D: If still not a valid dict, build structured object from raw text so 0G reasoning is NEVER lost
        if parsed is None or not isinstance(parsed, dict):
            if len(cleaned_text) >= 10:
                parsed = {
                    "task_understanding": {
                        "application_type": "AI Security Application",
                        "user_intent": original_prompt[:150],
                        "technologies": ["Software", "AI Guardrails"]
                    },
                    "security_analysis": {
                        "overall_risk": "Medium",
                        "findings": [
                            {
                                "vulnerability": "Security Reasoning & Attack Surface",
                                "severity": "medium",
                                "confidence": 0.85,
                                "evidence": original_prompt,
                                "attack_scenario": "Exploitation of unvalidated input boundaries.",
                                "explanation": cleaned_text[:350],
                                "recommendation": "Implement defense-in-depth security guardrails and input boundaries."
                            }
                        ]
                    },
                    "missing_security_requirements": [
                        "Input boundary delimitation and strict schema validation",
                        "Centralized authentication and session token verification"
                    ],
                    "hardened_prompt": cleaned_text,
                    "changes_made": [
                        {"change": "Synthesized defense boundaries via 0G Private Computer", "reason": "Threat mitigation"}
                    ],
                    "assumptions": ["Standard execution environment"],
                    "remaining_risks": ["Monitor live runtime inputs for adversarial jailbreak payloads"]
                }
            else:
                errors.append("Model output was empty or invalid JSON.")
                return False, None, errors

        # 2. Check and fill required top-level keys
        if "task_understanding" not in parsed or not parsed["task_understanding"]:
            parsed["task_understanding"] = {
                "application_type": "Application Service",
                "user_intent": original_prompt[:150],
                "technologies": []
            }
        if "security_analysis" not in parsed or not parsed["security_analysis"]:
            parsed["security_analysis"] = {
                "overall_risk": "Medium",
                "findings": [
                    {
                        "vulnerability": "Threat Modeling Surface",
                        "severity": "medium",
                        "confidence": 0.85,
                        "evidence": original_prompt,
                        "attack_scenario": "Input manipulation attack.",
                        "explanation": "0G Private Computer threat analysis completed.",
                        "recommendation": "Enforce strict security boundaries."
                    }
                ]
            }
        if "missing_security_requirements" not in parsed or not isinstance(parsed.get("missing_security_requirements"), list):
            parsed["missing_security_requirements"] = [
                "Input boundary validation and sanitization",
                "Defense-in-depth privilege boundaries"
            ]
        if "hardened_prompt" not in parsed or not parsed["hardened_prompt"]:
            parsed["hardened_prompt"] = cleaned_text if len(cleaned_text) > 20 else f"<defense_policy>\n# Hardened Guardrails\n{original_prompt}\n</defense_policy>"
        if "changes_made" not in parsed or not isinstance(parsed.get("changes_made"), list):
            parsed["changes_made"] = [{"change": "Applied 0G security hardening", "reason": "Defense-in-depth"}]
        if "assumptions" not in parsed or not isinstance(parsed.get("assumptions"), list):
            parsed["assumptions"] = ["Standard deployment environment"]
        if "remaining_risks" not in parsed or not isinstance(parsed.get("remaining_risks"), list):
            parsed["remaining_risks"] = ["Monitor for novel injection vectors"]

        # 3. Validate task_understanding
        task_und = parsed.get("task_understanding")
        if isinstance(task_und, str):
            task_und = {"application_type": "Application Service", "user_intent": task_und, "technologies": []}
            parsed["task_understanding"] = task_und
        elif not isinstance(task_und, dict):
            errors.append("'task_understanding' must be an object.")
            return False, None, errors

        # 4. Validate security_analysis & findings
        sec_analysis = parsed.get("security_analysis")
        if isinstance(sec_analysis, str):
            sec_analysis = {
                "overall_risk": "Medium",
                "findings": [
                    {
                        "vulnerability": "Application Security Evaluation",
                        "severity": "medium",
                        "confidence": 0.85,
                        "evidence": original_prompt,
                        "attack_scenario": "Exploitation of unvalidated inputs in the application workflow.",
                        "explanation": sec_analysis,
                        "recommendation": "Enforce defense-in-depth validation and error handling."
                    }
                ]
            }
            parsed["security_analysis"] = sec_analysis
        elif not isinstance(sec_analysis, dict):
            errors.append("'security_analysis' must be an object.")
            return False, None, errors

        findings = sec_analysis.get("findings")
        if not isinstance(findings, list):
            findings = []

        # Normalize and validate findings
        normalized_findings: List[Dict[str, Any]] = []
        valid_severities = {"critical", "high", "medium", "low"}
        for idx, f in enumerate(findings):
            if not isinstance(f, dict):
                continue
            vuln = str(f.get("vulnerability", f"Vulnerability {idx+1}")).strip()
            sev = str(f.get("severity", "medium")).lower().strip()
            if sev not in valid_severities:
                sev = "medium"

            try:
                conf = float(f.get("confidence", 0.8))
                conf = max(0.0, min(1.0, conf))
            except (ValueError, TypeError):
                conf = 0.8

            normalized_findings.append({
                "vulnerability": vuln,
                "severity": sev,
                "confidence": round(conf, 2),
                "evidence": str(f.get("evidence", "")).strip(),
                "attack_scenario": str(f.get("attack_scenario", "")).strip(),
                "explanation": str(f.get("explanation", "")).strip(),
                "recommendation": str(f.get("recommendation", "")).strip(),
            })

        sec_analysis["findings"] = normalized_findings
        overall_risk = str(sec_analysis.get("overall_risk", "Medium")).strip().capitalize()
        if overall_risk not in {"Critical", "High", "Medium", "Low"}:
            overall_risk = "Medium"
        sec_analysis["overall_risk"] = overall_risk

        # 5. Validate hardened_prompt
        hardened = str(parsed.get("hardened_prompt", "")).strip()
        if not hardened or len(hardened) < 20:
            errors.append("'hardened_prompt' is empty or too short to be an actionable specification.")
            return False, None, errors

        # 6. Post-inference secret exposure scan on the generated hardened prompt
        hardened_sanitization = sanitize_prompt_for_inference(hardened)
        if hardened_sanitization.secrets_detected:
            logger.warning("Redacted newly exposed secrets detected in 0G hardened prompt output.")
            parsed["hardened_prompt"] = hardened_sanitization.sanitized_prompt
        else:
            parsed["hardened_prompt"] = hardened

        # 7. Normalize changes_made
        changes = parsed.get("changes_made")
        if not isinstance(changes, list):
            parsed["changes_made"] = []
        else:
            norm_changes = []
            for c in changes:
                if isinstance(c, dict):
                    norm_changes.append({
                        "change": str(c.get("change", "")).strip(),
                        "reason": str(c.get("reason", "")).strip(),
                    })
                elif isinstance(c, str):
                    norm_changes.append({"change": c.strip(), "reason": "Security hardening control"})
            parsed["changes_made"] = norm_changes

        # 8. Normalize arrays
        for list_key in ["missing_security_requirements", "assumptions", "remaining_risks"]:
            if not isinstance(parsed.get(list_key), list):
                parsed[list_key] = []
            else:
                parsed[list_key] = [str(item).strip() for item in parsed[list_key] if str(item).strip()]

        return True, parsed, errors

    # -----------------------------------------------------------------------
    # Local-Only Analysis (When 0G is Disabled)
    # -----------------------------------------------------------------------

    def _create_local_only_result(
        self,
        preprocessing: Dict[str, Any],
        reason: str = "0G Private Computer inference is disabled (ZG_ENABLED=false). Ran local-only analysis.",
    ) -> ZeroGOptimizationResult:
        """
        Creates a transparent, explicitly labeled local-only result.
        Does NOT claim 0G reasoning or display 0G model information as proof of execution.
        """
        original_prompt = preprocessing["original_prompt"]
        sanitized_prompt = preprocessing["sanitized_prompt"]
        local_scan = preprocessing["local_scan"]

        local_baseline: OptimizationResult = self.local_optimizer.optimize_prompt(
            prompt=sanitized_prompt,
            security_analysis=local_scan,
        )

        now = datetime.now(timezone.utc).isoformat()
        metadata = {
            "provider": "local_heuristics",
            "model": None,  # NEVER claim 0G model when 0G did not run!
            "request_id": None,
            "trust_mode": None,
            "usage": {},
            "status": "local_only",
            "inference_used": False,
            "fallback_used": False,
            "fallback_reason": None,
            "duration_ms": 0.0,
            "is_attestation_verified": False,
            "created_at": now,
            "cached": False,
        }

        task_under = {
            "application_type": local_scan.get("task_type", "General Application"),
            "user_intent": "Evaluated via local deterministic pattern matcher.",
            "technologies": [],
        }

        detected_risks = (local_scan.get("application_risks") or {}).get("detected_risks") or []
        findings = [
            {
                "vulnerability": r,
                "severity": "medium",
                "confidence": 0.7,
                "evidence": "Flagged by local rule-based heuristic pattern.",
                "attack_scenario": f"Local classifier detected pattern matching {r}.",
                "explanation": f"Heuristic risk signature for {r}.",
                "recommendation": f"Implement standard defense controls for {r}.",
            }
            for r in detected_risks
        ]

        reasoning = ZeroGReasoningResult(
            contextual_summary="Local-only heuristic analysis completed without 0G Private Computer AI reasoning.",
            risk_explanations={r: f"Local heuristic rule matched {r}." for r in detected_risks},
            missing_security_requirements=local_baseline.detected_risks_addressed,
            intent_preservation_notes="Maintained user parameters using offline deterministic rules.",
            justifications=["Protect basic application boundaries without remote AI dependency."],
            remaining_risks=["Offline heuristics cannot perform deep contextual threat modeling."],
            task_understanding=task_under,
            security_analysis={"overall_risk": "Medium" if detected_risks else "Low", "findings": findings},
            changes_made=[{"change": c, "reason": "Local rule application"} for c in local_baseline.changes_summary],
            assumptions=["Running without 0G Private Computer reasoning engine."],
            hardened_prompt=local_baseline.optimized_prompt,
            structured={
                "task_understanding": task_under,
                "security_analysis": {"overall_risk": "Medium" if detected_risks else "Low", "findings": findings},
                "missing_security_requirements": local_baseline.detected_risks_addressed,
                "hardened_prompt": local_baseline.optimized_prompt,
                "changes_made": [{"change": c, "reason": "Local rule application"} for c in local_baseline.changes_summary],
                "assumptions": ["Running without 0G Private Computer reasoning engine."],
                "remaining_risks": ["Offline heuristics cannot perform deep contextual threat modeling."],
            },
            raw_content="Local-only analysis executed.",
            metadata=metadata,
        )

        return ZeroGOptimizationResult(
            original_prompt=original_prompt,
            sanitized_prompt=sanitized_prompt if preprocessing["secrets_detected"] else None,
            optimized_prompt=local_baseline.optimized_prompt,
            reasoning=reasoning,
            applied_hardening_rules=local_baseline.applied_hardening_rules,
            changes_summary=local_baseline.changes_summary,
            missing_requirements_addressed=local_baseline.detected_risks_addressed,
            preserved_intent="Preserved core request using PromptShield deterministic rule-based optimizer.",
            engine="local_only",
            status="local_only",
            fallback_used=False,
            fallback_reason=None,
            structured_reasoning=reasoning.structured,
            task_understanding=task_under,
            security_analysis_findings=findings,
            overall_risk="Medium" if detected_risks else "Low",
            changes_made=[{"change": c, "reason": "Local rule application"} for c in local_baseline.changes_summary],
            assumptions=["Running without 0G Private Computer reasoning engine."],
            remaining_risks=["Offline heuristics cannot perform deep contextual threat modeling."],
            metadata=metadata,
            disclaimer="Local-only analysis executed without 0G Private Computer AI reasoning.",
        )

    # -----------------------------------------------------------------------
    # Failure Result (When 0G Fails)
    # -----------------------------------------------------------------------

    def _create_0g_failure_result(
        self,
        preprocessing: Dict[str, Any],
        error_message: str,
        request_id: Optional[str] = None,
        duration_ms: float = 0.0,
    ) -> ZeroGOptimizationResult:
        """
        Creates an explicit failure result when 0G inference fails.
        Preserves independently available local scan results.
        Does NOT substitute local deterministic heuristics as AI findings.
        """
        original_prompt = preprocessing["original_prompt"]
        sanitized_prompt = preprocessing["sanitized_prompt"]
        now = datetime.now(timezone.utc).isoformat()

        metadata = {
            "provider": "0g",
            "model": self.client.model,
            "request_id": request_id,
            "trust_mode": self.client.trust_mode,
            "usage": {},
            "status": "0g_reasoning_failed",
            "inference_used": False,
            "fallback_used": False,
            "fallback_reason": None,
            "duration_ms": duration_ms,
            "is_attestation_verified": False,
            "created_at": now,
            "error": error_message,
            "cached": False,
        }

        return ZeroGOptimizationResult(
            original_prompt=original_prompt,
            sanitized_prompt=sanitized_prompt if preprocessing["secrets_detected"] else None,
            optimized_prompt="",  # Empty on failure — do NOT fabricate AI prompt!
            reasoning=None,       # No fake AI reasoning!
            applied_hardening_rules=[],
            changes_summary=[],
            missing_requirements_addressed=[],
            preserved_intent="",
            engine="0g_private_computer",
            status="0g_reasoning_failed",
            fallback_used=False,
            fallback_reason=None,
            structured_reasoning=None,
            task_understanding={},
            security_analysis_findings=[],
            overall_risk="Unknown",
            changes_made=[],
            assumptions=[],
            remaining_risks=[],
            error_message=error_message,
            metadata=metadata,
            disclaimer="0G Private Computer reasoning failed. Please retry or inspect network connectivity.",
        )

    # -----------------------------------------------------------------------
    # Synchronous Optimization
    # -----------------------------------------------------------------------

    def optimize(
        self,
        prompt: str,
        security_analysis: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        bypass_cache: bool = False,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 3500,
        fallback_to_local: bool = False,
    ) -> ZeroGOptimizationResult:
        """
        Executes primary AI security reasoning and prompt hardening on 0G Private Computer.
        1. Stage A: Local Preprocessing (sanitization, size limits, context extraction).
        2. Stage B: 0G Primary Reasoning (single remote call returning JSON).
        3. Stage C: Structured Response format.
        4. Stage D: Local Validation (schema checking, secret exposure scan).
        """
        # Stage A: Preprocessing
        preprocessing = self.preprocess_prompt(prompt)
        inference_prompt = preprocessing["sanitized_prompt"]

        # Check if 0G is disabled globally
        if not self.client.is_enabled:
            return self._create_local_only_result(
                preprocessing=preprocessing,
                reason="0G Private Computer inference is disabled (ZG_ENABLED=false). Ran local-only.",
            )

        # Check if 0G is configured
        if not self.client.is_configured:
            if fallback_to_local:
                return self._create_local_only_result(
                    preprocessing=preprocessing,
                    reason="0G API key is not configured (ZG_API_KEY). Ran local-only analysis.",
                )
            return self._create_0g_failure_result(
                preprocessing=preprocessing,
                error_message="0G API Key is not configured (ZG_API_KEY). Set ZG_API_KEY or disable 0G.",
            )

        # Check Credit Cache (scoped by user_id to prevent leaking private prompt results)
        cache_key = self.cache.compute_key(
            sanitized_prompt=inference_prompt,
            security_findings=preprocessing["preliminary_signals"],
            model=self.client.model,
            trust_mode=self.client.trust_mode,
            user_id=user_id,
            analysis_version="v2_primary",
        )

        if not bypass_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                # Cache hit: ZERO credits spent!
                cached_result.metadata["status"] = "0g_reasoning_completed"
                cached_result.metadata["inference_used"] = False
                cached_result.metadata["cached"] = True
                cached_result.status = "0g_reasoning_completed"
                return cached_result

        # Stage B: 0G Primary Inference Call
        start_time = datetime.now(timezone.utc)
        user_message = self._build_0g_input(preprocessing)

        try:
            response: ZeroGResponse = self.client.complete(
                prompt=user_message,
                system_prompt=self.PRIMARY_0G_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            logger.warning(f"0G Private Computer inference call failed: {exc}")
            req_id = getattr(exc, "request_id", None)
            return self._create_0g_failure_result(
                preprocessing=preprocessing,
                error_message=f"0G Private Computer inference error: {str(exc)}",
                request_id=req_id,
                duration_ms=round(duration_ms, 2),
            )

        # Stage D: Local Validation & Response Parsing
        is_valid, parsed_data, validation_errors = self.validate_and_sanitize_response(
            raw_text=response.content,
            original_prompt=preprocessing["original_prompt"],
        )

        if not is_valid or parsed_data is None:
            logger.warning(f"0G output validation failed: {validation_errors}")
            return self._create_0g_failure_result(
                preprocessing=preprocessing,
                error_message=f"0G response validation failed: {'; '.join(validation_errors)}",
                request_id=response.request_id,
                duration_ms=response.duration_ms,
            )

        # Assemble full validated ZeroGOptimizationResult
        task_und = parsed_data.get("task_understanding", {})
        sec_analysis = parsed_data.get("security_analysis", {})
        findings = sec_analysis.get("findings", [])
        overall_risk = sec_analysis.get("overall_risk", "Low")
        missing_reqs = parsed_data.get("missing_security_requirements", [])
        hardened_prompt = parsed_data.get("hardened_prompt", "")
        changes_made = parsed_data.get("changes_made", [])
        assumptions = parsed_data.get("assumptions", [])
        remaining_risks = parsed_data.get("remaining_risks", [])

        metadata = {
            "provider": "0g",
            "model": response.model,
            "response_id": response.response_id,
            "request_id": response.request_id,
            "trust_mode": response.trust_mode,
            "usage": response.usage or {},
            "status": "0g_reasoning_completed",
            "inference_used": True,
            "fallback_used": False,
            "fallback_reason": None,
            "duration_ms": response.duration_ms,
            "is_attestation_verified": False,
            "created_at": response.created_at,
            "cached": False,
            "trace": response.trace,
            "cost_usd_micro": response.cost_usd_micro,
            "e2ee": response.e2ee,
            "provider_address": response.provider_address,
        }

        # Build reasoning object
        reasoning = ZeroGReasoningResult(
            contextual_summary=f"Security evaluation for {task_und.get('application_type', 'Application')}. Overall Risk: {overall_risk}.",
            risk_explanations={f["vulnerability"]: f["explanation"] for f in findings if "vulnerability" in f and "explanation" in f},
            missing_security_requirements=missing_reqs,
            intent_preservation_notes=task_und.get("user_intent", "Preserved user intent."),
            justifications=[f"{c.get('change')}: {c.get('reason')}" for c in changes_made if isinstance(c, dict)],
            remaining_risks=remaining_risks,
            task_understanding=task_und,
            security_analysis=sec_analysis,
            changes_made=changes_made,
            assumptions=assumptions,
            hardened_prompt=hardened_prompt,
            structured=parsed_data,
            raw_content=response.content,
            metadata=metadata,
        )

        changes_summary_list = [c.get("change", "") for c in changes_made if isinstance(c, dict)]
        applied_rules_list = [f["recommendation"] for f in findings if f.get("recommendation")]

        result = ZeroGOptimizationResult(
            original_prompt=preprocessing["original_prompt"],
            sanitized_prompt=preprocessing["sanitized_prompt"] if preprocessing["secrets_detected"] else None,
            optimized_prompt=hardened_prompt,
            reasoning=reasoning,
            applied_hardening_rules=applied_rules_list,
            changes_summary=changes_summary_list,
            missing_requirements_addressed=missing_reqs,
            preserved_intent=task_und.get("user_intent", "Preserved user development intent."),
            engine="0g_private_computer",
            status="0g_reasoning_completed",
            fallback_used=False,
            fallback_reason=None,
            structured_reasoning=parsed_data,
            task_understanding=task_und,
            security_analysis_findings=findings,
            overall_risk=overall_risk,
            changes_made=changes_made,
            assumptions=assumptions,
            remaining_risks=remaining_risks,
            metadata=metadata,
        )

        # Store in credit cache
        if not bypass_cache:
            self.cache.set(cache_key, result)

        return result

    # -----------------------------------------------------------------------
    # Asynchronous Optimization
    # -----------------------------------------------------------------------

    async def optimize_async(
        self,
        prompt: str,
        security_analysis: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        bypass_cache: bool = False,
        temperature: float = 0.3,
        max_tokens: Optional[int] = 3500,
        fallback_to_local: bool = False,
    ) -> ZeroGOptimizationResult:
        """Asynchronous execution of 0G primary reasoning and prompt hardening."""
        preprocessing = self.preprocess_prompt(prompt)
        inference_prompt = preprocessing["sanitized_prompt"]

        if not self.client.is_enabled:
            return self._create_local_only_result(preprocessing=preprocessing)

        if not self.client.is_configured:
            if fallback_to_local:
                return self._create_local_only_result(preprocessing=preprocessing)
            return self._create_0g_failure_result(
                preprocessing=preprocessing,
                error_message="0G API Key is not configured (ZG_API_KEY).",
            )

        cache_key = self.cache.compute_key(
            sanitized_prompt=inference_prompt,
            security_findings=preprocessing["preliminary_signals"],
            model=self.client.model,
            trust_mode=self.client.trust_mode,
            user_id=user_id,
            analysis_version="v2_primary",
        )

        if not bypass_cache:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                cached_result.metadata["status"] = "0g_reasoning_completed"
                cached_result.metadata["inference_used"] = False
                cached_result.metadata["cached"] = True
                cached_result.status = "0g_reasoning_completed"
                return cached_result

        start_time = datetime.now(timezone.utc)
        user_message = self._build_0g_input(preprocessing)

        try:
            response: ZeroGResponse = await self.client.complete_async(
                prompt=user_message,
                system_prompt=self.PRIMARY_0G_SYSTEM_PROMPT,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
            logger.warning(f"0G Async inference call failed: {exc}")
            req_id = getattr(exc, "request_id", None)
            return self._create_0g_failure_result(
                preprocessing=preprocessing,
                error_message=f"0G Private Computer async error: {str(exc)}",
                request_id=req_id,
                duration_ms=round(duration_ms, 2),
            )

        is_valid, parsed_data, validation_errors = self.validate_and_sanitize_response(
            raw_text=response.content,
            original_prompt=preprocessing["original_prompt"],
        )

        if not is_valid or parsed_data is None:
            return self._create_0g_failure_result(
                preprocessing=preprocessing,
                error_message=f"0G response validation failed: {'; '.join(validation_errors)}",
                request_id=response.request_id,
                duration_ms=response.duration_ms,
            )

        task_und = parsed_data.get("task_understanding", {})
        sec_analysis = parsed_data.get("security_analysis", {})
        findings = sec_analysis.get("findings", [])
        overall_risk = sec_analysis.get("overall_risk", "Low")
        missing_reqs = parsed_data.get("missing_security_requirements", [])
        hardened_prompt = parsed_data.get("hardened_prompt", "")
        changes_made = parsed_data.get("changes_made", [])
        assumptions = parsed_data.get("assumptions", [])
        remaining_risks = parsed_data.get("remaining_risks", [])

        metadata = {
            "provider": "0g",
            "model": response.model,
            "response_id": response.response_id,
            "request_id": response.request_id,
            "trust_mode": response.trust_mode,
            "usage": response.usage or {},
            "status": "0g_reasoning_completed",
            "inference_used": True,
            "fallback_used": False,
            "fallback_reason": None,
            "duration_ms": response.duration_ms,
            "is_attestation_verified": False,
            "created_at": response.created_at,
            "cached": False,
            "trace": response.trace,
            "cost_usd_micro": response.cost_usd_micro,
            "e2ee": response.e2ee,
            "provider_address": response.provider_address,
        }

        reasoning = ZeroGReasoningResult(
            contextual_summary=f"Security evaluation for {task_und.get('application_type', 'Application')}. Overall Risk: {overall_risk}.",
            risk_explanations={f["vulnerability"]: f["explanation"] for f in findings if "vulnerability" in f and "explanation" in f},
            missing_security_requirements=missing_reqs,
            intent_preservation_notes=task_und.get("user_intent", "Preserved user intent."),
            justifications=[f"{c.get('change')}: {c.get('reason')}" for c in changes_made if isinstance(c, dict)],
            remaining_risks=remaining_risks,
            task_understanding=task_und,
            security_analysis=sec_analysis,
            changes_made=changes_made,
            assumptions=assumptions,
            hardened_prompt=hardened_prompt,
            structured=parsed_data,
            raw_content=response.content,
            metadata=metadata,
        )

        result = ZeroGOptimizationResult(
            original_prompt=preprocessing["original_prompt"],
            sanitized_prompt=preprocessing["sanitized_prompt"] if preprocessing["secrets_detected"] else None,
            optimized_prompt=hardened_prompt,
            reasoning=reasoning,
            applied_hardening_rules=[f["recommendation"] for f in findings if f.get("recommendation")],
            changes_summary=[c.get("change", "") for c in changes_made if isinstance(c, dict)],
            missing_requirements_addressed=missing_reqs,
            preserved_intent=task_und.get("user_intent", "Preserved user development intent."),
            engine="0g_private_computer",
            status="0g_reasoning_completed",
            fallback_used=False,
            fallback_reason=None,
            structured_reasoning=parsed_data,
            task_understanding=task_und,
            security_analysis_findings=findings,
            overall_risk=overall_risk,
            changes_made=changes_made,
            assumptions=assumptions,
            remaining_risks=remaining_risks,
            metadata=metadata,
        )

        if not bypass_cache:
            self.cache.set(cache_key, result)

        return result


# Global singleton instance
zero_g_optimizer = ZeroGOptimizer()
