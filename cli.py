#!/usr/bin/env python3
"""
PromptShield AI — Terminal Command-Line Interface (CLI).
Local Prompt Security & Model Recommendation Workspace.

Unified terminal workspace providing:
1. Prompt Security Analysis: Evaluates adversarial malice, prompt injection, and jailbreaks.
2. Application Risk Model: Predicts 15 architectural attack surfaces implied by requested features.
3. Sensitive Data Detector: Flags hardcoded API keys, secrets, and credentials (rule-based proof with masking).
4. Offline Multi-Model Comparison: Evaluates foundation models via WSM and TOPSIS without provider API calls.
5. IDE Coding Assistant Comparison: Multi-file agents, repo indexing, and terminal execution comparison.
6. AI App Builder Comparison: Full-stack backend, database/auth support, and code export comparison.
7. Model & Product Catalogue Inspection: Verifies exact model IDs, pricing status, tokenizers, and lifecycle.
8. Text File Analysis: Validated local file ingestion for security analysis and model comparison.
"""

import argparse
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analyzers.prompt_analyzer import analyze_prompt
from analyzers.sensitive_data_detector import PATTERNS, redact_secret
from analyzers.model_comparison.engine import comparison_engine, ModelComparisonReport
from analyzers.model_comparison.registry import (
    registry,
    ProductCategory,
    LifecycleStatus,
    ProductAvailability,
    ModelMetadata,
    IDEProductMetadata,
    AppBuilderMetadata,
)
from analyzers.model_comparison.ranker import RankingMethod, RankingPreset, PRESET_WEIGHTS
from analyzers.model_comparison.task_classifier import task_classifier
from analyzers.model_comparison.tokenizer_adapters import get_tokenizer_adapter
from analyzers.prompt_optimizer import prompt_optimizer, OptimizationResult



# ANSI Colors with automatic TTY / NO_COLOR detection
class Colors:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    @property
    def RESET(self) -> str:
        return "\033[0m" if self.enabled else ""

    @property
    def BOLD(self) -> str:
        return "\033[1m" if self.enabled else ""

    @property
    def DIM(self) -> str:
        return "\033[2m" if self.enabled else ""

    @property
    def RED(self) -> str:
        return "\033[91m" if self.enabled else ""

    @property
    def GREEN(self) -> str:
        return "\033[92m" if self.enabled else ""

    @property
    def YELLOW(self) -> str:
        return "\033[93m" if self.enabled else ""

    @property
    def BLUE(self) -> str:
        return "\033[94m" if self.enabled else ""

    @property
    def CYAN(self) -> str:
        return "\033[96m" if self.enabled else ""

    @property
    def MAGENTA(self) -> str:
        return "\033[95m" if self.enabled else ""


def is_color_supported() -> bool:
    """Checks whether ANSI color output is appropriate."""
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# Risk Metadata Mapping for the 15 Application Risk Labels
RISK_METADATA: Dict[str, Dict[str, str]] = {
    "sqli": {
        "title": "SQL Injection (SQLi)",
        "description": "Risk of SQL query manipulation via unparameterized database inputs.",
        "recommendation": "Use parameterized queries or an ORM (e.g., SQLAlchemy) for all DB operations; never concatenate raw user input into SQL."
    },
    "xss": {
        "title": "Cross-Site Scripting (XSS)",
        "description": "Risk of client-side script execution in user browsers via unescaped dynamic output.",
        "recommendation": "Contextually encode and sanitize dynamic output in HTML templates; implement a strict Content Security Policy (CSP)."
    },
    "ssrf": {
        "title": "Server-Side Request Forgery (SSRF)",
        "description": "Risk of unauthorized outbound server requests targeting internal infrastructure.",
        "recommendation": "Validate and whitelist destination URLs/IPs; block requests to internal subnets (127.0.0.1, 10.0.0.0/8, 169.254.169.254)."
    },
    "idor": {
        "title": "Insecure Direct Object References (IDOR)",
        "description": "Risk of accessing unauthorized records by manipulating object identifiers.",
        "recommendation": "Enforce object-level access control verifying the requesting user owns or is authorized for the target record ID."
    },
    "auth_weakness": {
        "title": "Authentication Weakness",
        "description": "Risk of credential brute-forcing, weak password hashing, or improper session creation.",
        "recommendation": "Use adaptive hashing (bcrypt, Argon2id), enforce strong password complexity policies, require Multi-Factor Authentication (MFA), and rate-limit login endpoints."
    },
    "authz_weakness": {
        "title": "Authorization Weakness",
        "description": "Risk of privilege escalation or missing role enforcement on sensitive endpoints.",
        "recommendation": "Implement centralized Role-Based Access Control (RBAC) or Attribute-Based Access Control (ABAC); default to deny-by-default on all endpoints."
    },
    "file_upload": {
        "title": "Insecure File Upload",
        "description": "Risk of arbitrary file upload, webshell execution, or storage exhaustion.",
        "recommendation": "Validate uploaded files by magic bytes and MIME type, enforce size limits, randomize stored file names, and store files outside the public web root in isolated object storage."
    },
    "path_traversal": {
        "title": "Path Traversal / Directory Traversal",
        "description": "Risk of reading arbitrary filesystem files via dot-dot-slash (../) manipulation.",
        "recommendation": "Canonicalize file paths and validate against a strict directory allowlist; avoid passing raw user input into filesystem APIs."
    },
    "command_injection": {
        "title": "Command Injection",
        "description": "Risk of executing arbitrary OS commands on the host server.",
        "recommendation": "Avoid shell execution (shell=True); use parameterized subprocess calls with structured argument lists and sanitize all input."
    },
    "csrf": {
        "title": "Cross-Site Request Forgery (CSRF)",
        "description": "Risk of unauthorized state-changing actions performed on behalf of authenticated users.",
        "recommendation": "Implement anti-CSRF tokens for all state-changing HTTP methods (POST, PUT, DELETE) and set SameSite=Lax or SameSite=Strict on session cookies."
    },
    "sensitive_data": {
        "title": "Sensitive Data Exposure",
        "description": "Risk of leaking PII, credentials, or internal system details via logs or unencrypted channels.",
        "recommendation": "Encrypt sensitive data at rest (AES-256) and in transit (TLS 1.3); redact secrets and PII from application logs and error traces."
    },
    "prompt_injection": {
        "title": "Prompt Injection / AI Evasion",
        "description": "Risk of untrusted external input overriding intended LLM system instructions.",
        "recommendation": "Isolate untrusted application inputs with clear delimiter boundaries before passing to LLMs; implement input/output guardrail checks."
    },
    "data_poisoning": {
        "title": "Data Poisoning",
        "description": "Risk of adversarial data corrupting ML training sets, fine-tuning pipelines, or RAG indexes.",
        "recommendation": "Verify provenance and cryptographic hashes of training datasets; audit data sources and sanitize inputs."
    },
    "model_extraction": {
        "title": "Model Extraction / Inversion",
        "description": "Risk of proprietary model reverse engineering via repetitive systematic querying.",
        "recommendation": "Enforce strict query rate limits, monitor for systematic extraction patterns, and avoid returning raw log probabilities."
    },
    "ai_tool_risk": {
        "title": "AI Tool / Agent Execution Risk",
        "description": "Risk of autonomous AI agents executing destructive tool actions without verification.",
        "recommendation": "Apply least privilege to agent tool capabilities; require explicit human-in-the-loop authorization for sensitive or irreversible operations."
    }
}


def mask_sensitive_text(prompt: str) -> str:
    """
    Safely redacts detected sensitive credentials in prompt text to prevent
    secret leakage in terminal displays or logs.
    """
    masked = prompt
    for pattern_def in PATTERNS:
        regex = pattern_def["regex"]
        matches = list(regex.finditer(masked))
        for m in reversed(matches):
            if pattern_def["type"] == "hardcoded_password_assignment":
                span = m.span(1)
            else:
                span = m.span(0)
            val = masked[span[0]:span[1]]
            masked = masked[:span[0]] + redact_secret(val) + masked[span[1]:]
    return masked


def generate_recommendations(analysis_result: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Synthesizes targeted, actionable security recommendations based on actual
    findings from all three analyzers, distinguishing declared controls from
    unmitigated risks and decoupling severity from raw model scores.
    """
    recommendations: List[Dict[str, str]] = []

    # 1. Deterministic Rule-Based Evidence (Sensitive Data Exposure)
    sensitive_data = analysis_result.get("sensitive_data") or {}
    if sensitive_data.get("detected"):
        findings = sensitive_data.get("findings", [])
        types_detected = list({f.get("type", "unknown") for f in findings})
        types_str = ", ".join(types_detected)
        recommendations.append({
            "priority": "CRITICAL",
            "category": "Credential Protection",
            "title": f"Revoke and remove exposed credentials ({types_str})",
            "guidance": (
                f"Identified {len(findings)} exposed secret pattern(s). Immediately revoke/rotate "
                "these keys. Remove all credentials from prompt text; inject secrets securely at runtime "
                "via environment variables or a secret manager (e.g., Vault, AWS Secrets Manager)."
            )
        })

    # 2. Prompt Security Analysis (Adversarial Malice & Injections)
    prompt_sec = analysis_result.get("prompt_security") or {}
    sec_status = prompt_sec.get("status")

    if sec_status == "success":
        if prompt_sec.get("is_malicious") is True:
            prob = prompt_sec.get("malicious_probability", 0.0)
            prio = "HIGH" if prob >= 0.80 else "MEDIUM"
            recommendations.append({
                "priority": prio,
                "category": "Prompt Security",
                "title": f"Mitigate adversarial prompt injection / jailbreak ({prob * 100:.1f}% confidence)",
                "guidance": (
                    "Prompt matches patterns characteristic of adversarial injection, jailbreaks, or instruction override. "
                    "Do not pass this prompt to downstream LLMs without strict input sandboxing, delimiter tags "
                    "(e.g., <user_input>), and an instruction-hierarchy safety layer."
                )
            })
        else:
            prob = prompt_sec.get("benign_probability", 0.0)
            recommendations.append({
                "priority": "INFORMATIONAL",
                "category": "Prompt Security",
                "title": f"Prompt appears non-adversarial ({prob * 100:.1f}% confidence)",
                "guidance": (
                    "Prompt demonstrates low adversarial pattern correlation. Continue applying standard defensive "
                    "delimiters when passing dynamic user inputs to AI components."
                )
            })
    elif sec_status in {"model_unavailable", "error"}:
        recommendations.append({
            "priority": "HIGH",
            "category": "Model Integrity",
            "title": "Prompt Security Model is offline or unverified",
            "guidance": (
                "Unable to evaluate adversarial prompt risk. DO NOT assume this prompt is benign. "
                "Train or restore the model artifact using: '.venv/bin/python ml/train_prompt_security_model.py'."
            )
        })

    # 3. Application Security: Declared Defenses vs. Unmitigated Surfaces
    app_risk = analysis_result.get("application_risks") or {}
    app_status = app_risk.get("status")

    if app_status == "success":
        detected_risks = app_risk.get("detected_risks") or []
        mitigated_surfaces = app_risk.get("mitigated_surfaces") or {}
        if "unmitigated_surfaces" in app_risk:
            unmitigated_surfaces = app_risk.get("unmitigated_surfaces") or []
        elif "mitigated_surfaces" in app_risk:
            unmitigated_surfaces = [r for r in detected_risks if r not in mitigated_surfaces]
        else:
            unmitigated_surfaces = detected_risks

        # 3A. Surfaces with Declared Defenses (Residual Risk Review)
        if mitigated_surfaces:
            for risk_label, controls_list in mitigated_surfaces.items():
                meta = RISK_METADATA.get(risk_label, {"title": risk_label.replace("_", " ").title()})
                ctrl_str = ", ".join(controls_list)
                recommendations.append({
                    "priority": "DEFENSE-DECLARED",
                    "category": "Residual Risk Audit",
                    "title": f"{meta['title']} — Declared Controls Identified ({ctrl_str})",
                    "guidance": (
                        f"Prompt specifies defensive controls ({ctrl_str}). Residual risk review: "
                        "Audit algorithm parameters (e.g., memory/time costs for hashing, session expiration, "
                        "strict token revocation) during code implementation."
                    )
                })

        # 3B. Unmitigated Attack Surfaces
        if unmitigated_surfaces:
            for risk_label in unmitigated_surfaces:
                meta = RISK_METADATA.get(risk_label, {
                    "title": risk_label.replace("_", " ").title(),
                    "recommendation": "Review and harden application implementation for this risk area."
                })
                recommendations.append({
                    "priority": "HIGH",
                    "category": "Application Hardening",
                    "title": meta["title"],
                    "guidance": meta["recommendation"]
                })

        # 3C. Informational when no active attack surfaces
        if not detected_risks:
            recommendations.append({
                "priority": "INFORMATIONAL",
                "category": "Application Architecture",
                "title": "No active application attack surfaces detected by baseline model",
                "guidance": (
                    "The application description does not trigger common risk categories or explicitly negates them. "
                    "Regularly audit your codebase against the OWASP Top 10 as additional features are introduced."
                )
            })

    elif app_status in {"model_unavailable", "error"}:
        recommendations.append({
            "priority": "HIGH",
            "category": "Model Integrity",
            "title": "Application Risk Model is offline or unverified",
            "guidance": (
                "Unable to predict application attack surfaces. DO NOT assume the requested application is risk-free. "
                "Train or restore the model artifact using: '.venv/bin/python ml/train_security_model.py'."
            )
        })

    return recommendations


def get_banner(colors: Colors) -> str:
    """Returns the PromptShield AI banner formatted for terminal display."""
    banner_text = r"""
================================================================================
  ____                            _   ____  _     _      _     _      _    ___ 
 |  _ \ _ __ ___  _ __ ___  _ __ | |_/ ___|| |__ (_) ___| | __| |    / \  |_ _|
 | |_) | '__/ _ \| '_ ` _ \| '_ \| __\___ \| '_ \| |/ _ \ |/ _` |   / _ \  | | 
 |  __/| | | (_) | | | | | | |_) | |_ ___) | | | | |  __/ | (_| |  / ___ \ | | 
 |_|   |_|  \___/|_| |_| |_| .__/ \__|____/|_| |_|_|\___|_|\__,_| /_/   \_\___|
                           |_|                                                  
      PromptShield AI — Unified Security & Risk Intelligence Platform
================================================================================
"""
    return f"{colors.CYAN}{banner_text}{colors.RESET}"


def format_security_report(
    prompt: str,
    analysis_result: Dict[str, Any],
    colors: Optional[Colors] = None
) -> str:
    """
    Formats the complete PromptShield AI unified security report.
    Integrates Prompt Security, Application Risks, Declared Controls, and Sensitive Data.
    """
    if colors is None:
        colors = Colors(enabled=False)

    lines: List[str] = []
    rule = "=" * 80
    subrule = "-" * 80

    lines.append(rule)
    lines.append(f"{colors.BOLD}{colors.CYAN}              PROMPTSHIELD AI — UNIFIED SECURITY REPORT{colors.RESET}")
    lines.append(rule)

    # Prompt Summary
    sanitized_prompt = mask_sensitive_text(prompt)
    preview = sanitized_prompt if len(sanitized_prompt) <= 300 else f"{sanitized_prompt[:297]}..."

    char_count = len(prompt)
    word_count = len(prompt.split())
    line_count = len(prompt.splitlines())

    lines.append(f"\n{colors.BOLD}[ PROMPT SUMMARY ]{colors.RESET}")
    lines.append(f"  Length: {char_count} chars | {word_count} words | {line_count} line(s)")
    lines.append("  Prompt Content (Secrets Redacted for Display):")
    for pline in preview.splitlines():
        lines.append(f"    {pline}")

    # Section 1: Prompt Security Analysis
    prompt_sec = analysis_result.get("prompt_security") or {}
    sec_status = prompt_sec.get("status", "unknown")

    lines.append(f"\n{subrule}")
    lines.append(f"{colors.BOLD}1. PROMPT SECURITY ANALYSIS (Adversarial Malice & Injection){colors.RESET}")
    lines.append(subrule)

    if sec_status == "success":
        is_mal = prompt_sec.get("is_malicious")
        mal_prob = prompt_sec.get("malicious_probability", 0.0)
        ben_prob = prompt_sec.get("benign_probability", 0.0)

        if is_mal:
            verdict_badge = f"{colors.BOLD}{colors.RED}[ ADVERSARIAL / MALICIOUS ]{colors.RESET}"
        else:
            verdict_badge = f"{colors.BOLD}{colors.GREEN}[ BENIGN ]{colors.RESET}"

        lines.append(f"  Analyzer Status:       {colors.GREEN}SUCCESS{colors.RESET}")
        lines.append(f"  Classification:        {verdict_badge}")
        lines.append(f"  Malicious Probability: {mal_prob * 100:.2f}%")
        lines.append(f"  Benign Probability:    {ben_prob * 100:.2f}%")
        lines.append(f"  Model Context:         {prompt_sec.get('disclaimer', '')}")
    elif sec_status == "model_unavailable":
        lines.append(f"  Analyzer Status:       {colors.RED}MODEL UNAVAILABLE{colors.RESET}")
        lines.append(f"  Classification:        {colors.YELLOW}[ UNVERIFIED — MODEL OFFLINE ]{colors.RESET}")
        lines.append(f"  {colors.RED}[!] CRITICAL WARNING: Model artifact missing!{colors.RESET}")
        lines.append("      DO NOT assume this prompt is benign.")
        lines.append("      To train/restore: python ml/train_prompt_security_model.py")
        if prompt_sec.get("error"):
            lines.append(f"      Details: {prompt_sec['error']}")
    else:
        lines.append(f"  Analyzer Status:       {colors.RED}ERROR{colors.RESET}")
        lines.append(f"  Classification:        {colors.YELLOW}[ UNVERIFIED — INFERENCE ERROR ]{colors.RESET}")
        lines.append(f"  {colors.RED}[!] WARNING: Inference failed; prompt safety cannot be confirmed.{colors.RESET}")
        if prompt_sec.get("error"):
            lines.append(f"      Error: {prompt_sec['error']}")

    # Section 2: Application Attack Surfaces & Declared Controls
    app_risk = analysis_result.get("application_risks") or {}
    app_status = app_risk.get("status", "unknown")

    lines.append(f"\n{subrule}")
    lines.append(f"{colors.BOLD}2. APPLICATION ATTACK SURFACES & SECURITY CONTROLS (Architectural Evaluation){colors.RESET}")
    lines.append(subrule)

    if app_status == "success":
        declared_controls = app_risk.get("declared_controls") or []
        declared_negations = app_risk.get("declared_negations") or []
        suppressed_risks = app_risk.get("suppressed_risks") or []
        detected_risks = app_risk.get("detected_risks") or []
        mitigated_surfaces = app_risk.get("mitigated_surfaces") or {}

        # 2A. Explicitly Stated Security Controls
        lines.append(f"  {colors.BOLD}Explicitly Stated Security Controls:{colors.RESET}")
        if declared_controls:
            for ctrl in declared_controls:
                lines.append(f"    {colors.GREEN}[✓]{colors.RESET} {colors.BOLD}{ctrl['name']}{colors.RESET} (Matched: \"{ctrl['matched_text']}\")")
                lines.append(f"        {colors.DIM}{ctrl['description']}{colors.RESET}")
        else:
            lines.append(f"    {colors.DIM}None explicitly stated in prompt.{colors.RESET}")

        # 2B. Declared Feature Negations
        if declared_negations:
            lines.append(f"\n  {colors.BOLD}Declared Feature Negations (Excluded Attack Surfaces):{colors.RESET}")
            for neg in declared_negations:
                lines.append(f"    {colors.CYAN}[i]{colors.RESET} Excluded: {colors.BOLD}{neg['feature']}{colors.RESET} — \"{neg['matched_text']}\"")
            if suppressed_risks:
                lines.append(f"    {colors.DIM}Suppressed model risk predictions: {', '.join(suppressed_risks)}{colors.RESET}")

        # 2C. Model Predicted Potential Attack Surfaces
        lines.append(f"\n  {colors.BOLD}Predicted Potential Attack Surfaces ({len(detected_risks)} active):{colors.RESET}")
        if detected_risks:
            for risk in detected_risks:
                meta = RISK_METADATA.get(risk, {"title": risk, "description": "Application attack surface"})
                if risk in mitigated_surfaces:
                    ctrls_str = ", ".join(mitigated_surfaces[risk])
                    lines.append(f"    {colors.GREEN}[✓]{colors.RESET} {colors.BOLD}{risk:<18}{colors.RESET} — {meta['title']} {colors.GREEN}[Declared Controls: {ctrls_str}]{colors.RESET}")
                else:
                    lines.append(f"    {colors.YELLOW}[!]{colors.RESET} {colors.BOLD}{risk:<18}{colors.RESET} — {meta['title']} {colors.YELLOW}[No Declared Defenses]{colors.RESET}")
                lines.append(f"        {colors.DIM}{meta['description']}{colors.RESET}")
        else:
            lines.append(f"    {colors.GREEN}✓ No active application attack surfaces detected by baseline model.{colors.RESET}")

        lines.append("")
        lines.append(f"  {colors.CYAN}[i] IMPORTANT ARCHITECTURAL DISTINCTION:{colors.RESET}")
        lines.append("      These findings represent POTENTIAL ATTACK SURFACES in the requested")
        lines.append("      software design (e.g., authentication, database, uploads). They are")
        lines.append("      architectural areas to defend, NOT confirmed vulnerabilities or proof of malice.")
        lines.append(f"  Model Context:         {app_risk.get('disclaimer', '')}")
    elif app_status == "model_unavailable":
        lines.append(f"  Analyzer Status:       {colors.RED}MODEL UNAVAILABLE{colors.RESET}")
        lines.append(f"  Identified Surfaces:   {colors.YELLOW}[ UNVERIFIED — MODEL OFFLINE ]{colors.RESET}")
        lines.append(f"  {colors.RED}[!] CRITICAL WARNING: Model artifact missing!{colors.RESET}")
        lines.append("      DO NOT assume the requested application has no attack surfaces.")
        lines.append("      To train/restore: python ml/train_security_model.py")
        if app_risk.get("error"):
            lines.append(f"      Details: {app_risk['error']}")
    else:
        lines.append(f"  Analyzer Status:       {colors.RED}ERROR{colors.RESET}")
        lines.append(f"  Identified Surfaces:   {colors.YELLOW}[ UNVERIFIED — INFERENCE ERROR ]{colors.RESET}")
        lines.append(f"  {colors.RED}[!] WARNING: Inference failed; risk assessment unavailable.{colors.RESET}")
        if app_risk.get("error"):
            lines.append(f"      Error: {app_risk['error']}")

    # Section 3: Sensitive Data Detection
    sensitive_data = analysis_result.get("sensitive_data") or {}
    has_sensitive = sensitive_data.get("detected", False)
    findings = sensitive_data.get("findings", [])

    lines.append(f"\n{subrule}")
    lines.append(f"{colors.BOLD}3. SENSITIVE DATA & CREDENTIAL EXPOSURE DETECTION (Deterministic Rule Evidence){colors.RESET}")
    lines.append(subrule)

    if has_sensitive:
        badge = f"{colors.BOLD}{colors.RED}[ EXPOSURE DETECTED — EMPIRICAL EVIDENCE ]{colors.RESET}"
        lines.append(f"  Status:                {badge}")
        lines.append(f"  Findings Count:        {len(findings)}")
        lines.append("  Detected Sensitive Strings (Redacted):")
        for finding in findings:
            desc = finding.get("description", "Unknown Secret")
            ftype = finding.get("type", "generic")
            redacted = finding.get("redacted", "[REDACTED]")
            lines.append(f"    {colors.RED}[!] {desc} ({ftype}): {redacted}{colors.RESET}")
    else:
        badge = f"{colors.BOLD}{colors.GREEN}[ CLEAN — NO SECRETS FOUND ]{colors.RESET}"
        lines.append(f"  Status:                {badge}")
        lines.append(f"  {colors.GREEN}✓ No API keys, passwords, private keys, or tokens detected.{colors.RESET}")

    lines.append(f"  Detector Note:         {sensitive_data.get('disclaimer', '')}")

    # Section 4: Actionable Security Recommendations
    recommendations = generate_recommendations(analysis_result)

    lines.append(f"\n{subrule}")
    lines.append(f"{colors.BOLD}4. ACTIONABLE SECURITY RECOMMENDATIONS & RESIDUAL RISK REVIEW{colors.RESET}")
    lines.append(subrule)

    if recommendations:
        for rec in recommendations:
            prio = rec["priority"]
            if prio == "CRITICAL":
                prio_str = f"{colors.BOLD}{colors.RED}[CRITICAL]{colors.RESET}"
            elif prio == "HIGH":
                prio_str = f"{colors.BOLD}{colors.YELLOW}[HIGH]{colors.RESET}"
            elif prio in {"MEDIUM", "DEFENSE-DECLARED"}:
                prio_str = f"{colors.BOLD}{colors.BLUE}[DEFENSE-DECLARED]{colors.RESET}"
            else:
                prio_str = f"{colors.BOLD}{colors.CYAN}[INFO]{colors.RESET}"

            lines.append(f"  {prio_str} {colors.BOLD}{rec['title']}{colors.RESET}")
            lines.append(f"         Category: {rec['category']}")
            lines.append(f"         Action:   {rec['guidance']}")
            lines.append("")
    else:
        lines.append("  No specific security recommendations generated for this prompt.")

    # Section 5: Diagnostic Summary
    avail = analysis_result.get("model_availability") or {}
    sec_model_ok = avail.get("prompt_security_model", False)
    app_model_ok = avail.get("application_risk_model", False)
    overall_status = analysis_result.get("status", "unknown")

    lines.append(subrule)
    lines.append(f"{colors.BOLD}5. SYSTEM & MODEL DIAGNOSTICS{colors.RESET}")
    lines.append(subrule)
    lines.append(f"  Prompt Security Model:     {colors.GREEN}ONLINE{colors.RESET}" if sec_model_ok else f"  Prompt Security Model:     {colors.RED}OFFLINE{colors.RESET}")
    lines.append(f"  Application Risk Model:    {colors.GREEN}ONLINE{colors.RESET}" if app_model_ok else f"  Application Risk Model:    {colors.RED}OFFLINE{colors.RESET}")
    lines.append(f"  Sensitive Data Detector:   {colors.GREEN}ACTIVE (Rule-based heuristics){colors.RESET}")

    status_color = colors.GREEN if overall_status == "success" else (colors.YELLOW if overall_status == "partial_success" else colors.RED)
    lines.append(f"  Overall Orchestrator:      {status_color}{overall_status.upper()}{colors.RESET}")
    lines.append(rule)

    return "\n".join(lines)


def read_multiline_prompt(
    colors: Colors,
    prompt_label: str = "Enter custom application prompt below.",
    sentinel: str = "END"
) -> Optional[str]:
    """
    Interactively reads a multiline prompt from the terminal until
    the user types 'END' on a line by itself.
    Returns None if the user issues an exit/cancel command or interrupts.
    """
    print(f"\n{colors.BOLD}{prompt_label}{colors.RESET}")
    print("• You may paste or enter multi-line text.")
    print(f"• Type {colors.BOLD}'{sentinel}'{colors.RESET} on a new line when finished to proceed.")
    print(f"• Type {colors.BOLD}'exit'{colors.RESET}, {colors.BOLD}'quit'{colors.RESET}, or {colors.BOLD}'cancel'{colors.RESET} on the first line to return.")
    print("-" * 80)

    lines: List[str] = []
    while True:
        try:
            line = input(f"{colors.CYAN}>{colors.RESET} ")
        except (KeyboardInterrupt, EOFError):
            return None

        # Check for immediate exit/cancel
        if not lines and line.strip().lower() in {"exit", "quit", "q", "cancel", ":cancel", ":q"}:
            return None

        # Check for END sentinel (case-insensitive)
        if line.strip().upper() == sentinel.upper():
            break

        lines.append(line)

    prompt_text = "\n".join(lines).strip()
    return prompt_text


def show_prompt_improvement_notice(colors: Colors) -> None:
    """Displays feature status notice for automated prompt improvement."""
    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}       PROMPT IMPROVEMENT & OPTIMIZATION (PLANNED FEATURE){colors.RESET}")
    print("=" * 80)
    print(f"  {colors.YELLOW}[!] Feature Status: Scheduled for future development phase.{colors.RESET}")
    print("\n  Currently Implemented Capabilities in PromptShield AI:")
    print(f"    {colors.GREEN}✓{colors.RESET} Calibrated Prompt Security Model (Adversarial / Malice Classification)")
    print(f"    {colors.GREEN}✓{colors.RESET} Application Risk Assessment (15 Multi-label Architectural Risks)")
    print(f"    {colors.GREEN}✓{colors.RESET} Security Controls & Constraints Extractor (Argon2id, CSP, RBAC, etc.)")
    print(f"    {colors.GREEN}✓{colors.RESET} Sensitive Data Detection (Credentials, API Keys, Private Keys)")
    print(f"    {colors.GREEN}✓{colors.RESET} Decoupled Severity & Actionable Remediation Engine")
    print(f"    {colors.GREEN}✓{colors.RESET} Multi-Category Offline Comparison (Foundation Models, IDEs, App Builders)")
    print(f"    {colors.GREEN}✓{colors.RESET} Multi-Criteria WSM and TOPSIS Ranking")
    print("=" * 80)


def handle_next_action_menu(colors: Colors) -> str:
    """
    Presents post-report action menu (preserved for test backwards-compatibility).
    Returns: 'improve', 'another', or 'exit'.
    """
    while True:
        print("\n" + "=" * 80)
        print(f"{colors.BOLD}NEXT ACTION MENU{colors.RESET}")
        print("=" * 80)
        print("  [1] Improve this prompt")
        print("  [2] Analyze another prompt")
        print("  [3] Exit PromptShield AI")
        print("=" * 80)

        try:
            choice = input(f"{colors.CYAN}Select an option (1-3) or type 'exit':{colors.RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return "exit"

        if choice in {"1", "improve", "improve this prompt"}:
            show_prompt_improvement_notice(colors)
            try:
                sub_choice = input(f"\n{colors.CYAN}Press [Enter] to return to menu, or 'exit' to quit:{colors.RESET} ").strip().lower()
                if sub_choice in {"exit", "quit", "q"}:
                    return "exit"
            except (KeyboardInterrupt, EOFError):
                return "exit"
            continue
        elif choice in {"2", "another", "analyze another prompt", "a"}:
            return "another"
        elif choice in {"3", "exit", "quit", "q"}:
            return "exit"
        else:
            print(f"{colors.RED}[!] Invalid choice. Please enter 1, 2, or 3.{colors.RESET}")


# ===========================================================================
# File Saving Utility
# ===========================================================================

def save_prompt_to_file(colors: Colors, text: str) -> None:
    """Saves text content to a user-specified file with overwrite confirmation."""
    try:
        path_str = input(f"\n{colors.CYAN}Enter destination file path to save prompt (or 'c' to cancel):{colors.RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if path_str.lower() in {"c", "cancel", ""}:
        print(f"{colors.YELLOW}[i] File save cancelled.{colors.RESET}")
        return

    dest_path = Path(path_str).expanduser().resolve()
    if dest_path.exists():
        print(f"{colors.YELLOW}[!] File '{dest_path.name}' already exists. Overwrite? (y/N):{colors.RESET}")
        try:
            confirm = input(f"{colors.YELLOW}Overwrite file? (y/N): {colors.RESET}").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return
        if confirm not in {"y", "yes"}:
            print(f"{colors.YELLOW}[i] File save cancelled: existing file preserved.{colors.RESET}")
            return

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_text(text, encoding="utf-8")
        print(f"{colors.GREEN}✓ Successfully saved optimized prompt to: {dest_path}{colors.RESET}")
        print(f"  Size: {len(text)} characters, {len(text.encode('utf-8'))} bytes, {len(text.splitlines())} lines.")
    except Exception as e:
        print(f"{colors.RED}[!] Error writing file: {e}{colors.RESET}")


# ===========================================================================
# Option 1: Complete End-to-End Workflow (Analyse, Compare, and Optimize)
# ===========================================================================

def cli_complete_end_to_end_workflow(colors: Colors, preloaded_prompt: Optional[str] = None) -> None:
    """
    Executes the primary sequential PromptShield AI workflow:
    1. Accept original prompt
    2. Clarify objective if brief / unclear
    3. Analyze security risks in original prompt
    4. Compare eligible foundation models locally
    5. Recommend suitable model for original prompt
    6. Generate optimized prompt deterministically & locally
    7. Re-analyse optimized prompt for security risks
    8. Re-compare models for optimized prompt
    9. Recommend model for optimized prompt
    10. Present clear before-and-after summary (Sections A-H)
    11. Offer next actions: save to file, re-optimize, compare models, new analysis, or exit.
    """
    active_prompt = preloaded_prompt.strip() if preloaded_prompt else None

    while True:
        print("\n" + "=" * 80)
        print(f"{colors.BOLD}{colors.CYAN}1. ANALYSE, COMPARE AND OPTIMIZE A PROMPT (COMPLETE WORKFLOW){colors.RESET}")
        print("=" * 80)
        print("Sequential local workflow: Security Analysis → Model Recommendation →")
        print("Deterministic Optimization → Security Re-analysis → Model Re-recommendation → Summary")
        print("=" * 80)

        # Stage 1: Accept prompt
        if active_prompt:
            prompt = active_prompt
            print(f"{colors.GREEN}✓ Using preloaded prompt ({len(prompt)} chars, {len(prompt.split())} words){colors.RESET}")
        else:
            prompt = read_multiline_prompt(
                colors,
                prompt_label="Enter original prompt for complete end-to-end analysis & optimization:",
                sentinel="END"
            )
            if not prompt or prompt.lower() in {"cancel", "c"}:
                print(f"\n{colors.YELLOW}[i] Workflow cancelled. Returning to main menu.{colors.RESET}")
                return

        # Stage 2: Clarify objective if brief / unclear
        user_clarification: Optional[str] = None
        word_count = len(prompt.split())
        if word_count < 6:
            print(f"\n{colors.YELLOW}[!] The prompt appears very brief ({word_count} words). Clarifying the desired outcome helps produce a better optimization.{colors.RESET}")
            print(f"{colors.CYAN}What specific result do you want to achieve? (or press [Enter] to proceed with defaults, 'c' to cancel):{colors.RESET}")
            try:
                clarif_in = input(f"{colors.CYAN}> {colors.RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                return
            if clarif_in.lower() in {"c", "cancel"}:
                print(f"{colors.YELLOW}[i] Workflow cancelled. Returning to main menu.{colors.RESET}")
                return
            if clarif_in:
                user_clarification = clarif_in

        # Settings for model comparison
        selected_ids: Optional[List[str]] = None
        method = RankingMethod.WEIGHTED_SUM
        preset = RankingPreset.BALANCED

        # Workflow execution loop (allows re-optimization or model selection without re-entering prompt)
        while True:
            # ------------------------------------------------------------------
            # Stage 3: Original Prompt Security Analysis
            # ------------------------------------------------------------------
            print(f"\n{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.BOLD}[STAGE 1/6] ORIGINAL PROMPT SECURITY ANALYSIS{colors.RESET}")
            print(f"{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.CYAN}Evaluating adversarial malice, 15 application risk surfaces, and credentials...{colors.RESET}\n")

            orig_analysis = analyze_prompt(prompt, analysis_mode="both")

            # Educational intent check
            is_educational = bool(re.search(r"\b(explain|how does|what is|describe the concept|time complexity|difference between|overview of)\b", prompt, re.IGNORECASE))
            if is_educational:
                print(f"  {colors.CYAN}ℹ Educational Intent Detected: Prompt appears to request conceptual explanation or technical comparison rather than instructing an unsafe exploitation.{colors.RESET}\n")

            # 1. Prompt Injection
            sec_prob = orig_analysis.get("prompt_security", {})
            is_mal = sec_prob.get("is_malicious", False)
            prob_val = sec_prob.get("malicious_probability", 0.0)
            conf_val = max(prob_val, 1.0 - prob_val)
            if is_mal:
                print(f"  • Category:   {colors.BOLD}Prompt Injection & Instruction Override{colors.RESET}")
                print(f"    Severity:   {colors.RED}{colors.BOLD}HIGH{colors.RESET}")
                print(f"    Confidence: {prob_val:.1%} (Adversarial probability)")
                print(f"    Evidence:   Potential system instruction override, jailbreak, or boundary escaping pattern.")
                print(f"    Explanation: Prompt attempts to alter system directives or jailbreak the downstream LLM.")
                print(f"    Mitigation: Wrap dynamic inputs in strict `<user_input>` delimiters and enforce instruction hierarchy.")
                print()
            else:
                print(f"  • Category:   {colors.BOLD}Prompt Injection & Instruction Override{colors.RESET}")
                print(f"    Severity:   {colors.GREEN}LOW / BENIGN{colors.RESET}")
                print(f"    Confidence: {conf_val:.1%} (Non-adversarial probability: {1.0 - prob_val:.1%})")
                print(f"    Explanation: Prompt does not exhibit adversarial jailbreak patterns.")
                print(f"    Mitigation: Maintain standard input boundary tagging when accepting external inputs.")
                print()

            # 2. Sensitive Data Leakage
            sens = orig_analysis.get("sensitive_data", {})
            if sens.get("detected"):
                findings = sens.get("findings", [])
                for item in findings:
                    print(f"  • Category:   {colors.BOLD}Sensitive Data Exposure ({item.get('type')}){colors.RESET}")
                    print(f"    Severity:   {colors.RED}{colors.BOLD}CRITICAL{colors.RESET}")
                    print(f"    Evidence:   {colors.YELLOW}{item.get('redacted')}{colors.RESET} (safely masked)")
                    print(f"    Explanation: {item.get('description')} detected in raw prompt text.")
                    print(f"    Mitigation: Remove secrets from prompt text; inject securely via environment variables (`os.environ`).")
                    print()
            else:
                print(f"  • Category:   {colors.BOLD}Sensitive Data Exposure{colors.RESET}")
                print(f"    Status:     {colors.GREEN}[ None detected ]{colors.RESET} (No hardcoded API keys, tokens, or passwords)")
                print()

            # 3. Application Architectural Risks
            app_risks = orig_analysis.get("application_risks", {})
            detected_risks = app_risks.get("detected_risks", [])
            risk_probs = app_risks.get("risk_probabilities", {})
            mitigated_surfaces = app_risks.get("mitigated_surfaces", {})
            declared_controls = app_risks.get("declared_controls", [])

            if detected_risks:
                for r in detected_risks:
                    meta = RISK_METADATA.get(r, {
                        "title": r.replace("_", " ").title(),
                        "description": "Implied architectural attack surface in requested features.",
                        "recommendation": "Apply defensive controls."
                    })
                    title = meta.get("title", r)
                    expl = meta.get("description", "")
                    mit = meta.get("recommendation", "")
                    prob = risk_probs.get(r, 0.5)
                    sev = "HIGH" if prob >= 0.70 else "MEDIUM"
                    sev_color = colors.RED if sev == "HIGH" else colors.YELLOW
                    is_mitigated = r in mitigated_surfaces
                    status_str = f"{colors.GREEN}[Declared Mitigations Present]{colors.RESET}" if is_mitigated else f"{sev_color}[UNMITIGATED]{colors.RESET}"
                    print(f"  • Category:   {colors.BOLD}{title} ({r}){colors.RESET} {status_str}")
                    print(f"    Severity:   {sev_color}{sev}{colors.RESET} (Detection confidence: {prob:.1%})")
                    print(f"    Explanation: {expl}")
                    print(f"    Mitigation: {mit}")
                    if is_mitigated:
                        print(f"    Declared:   Detected controls in prompt: {', '.join(mitigated_surfaces[r])}")
                    print()
            else:
                print(f"  • Application Risks: {colors.GREEN}[ None detected ]{colors.RESET} (No high-risk architectural attack surfaces detected)\n")

            print(f"  {colors.DIM}Static Analysis Note: Analysis evaluates prompt text heuristically. Static analysis cannot guarantee that code generated or executed downstream is secure.{colors.RESET}")

            # ------------------------------------------------------------------
            # Stage 4: Local Model Comparison (Original Prompt)
            # ------------------------------------------------------------------
            print(f"\n{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.BOLD}[STAGE 2/6] FOUNDATION MODEL COMPARISON (ORIGINAL PROMPT){colors.RESET}")
            print(f"{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")

            include_preview = False
            eligible_models = registry.list_models(include_deprecated=False, include_preview=False)
            print(f"Evaluating across {len(eligible_models)} active eligible foundation models.")
            print(f"Default comparison: Automatic comparison using Weighted Sum Model (WSM, balanced preset).")

            try:
                choice_config = input(f"{colors.CYAN}Press [Enter] to run default comparison, or 's' to customize models/preset (or 'c' to cancel):{colors.RESET} ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                return

            if choice_config in {"c", "cancel"}:
                print(f"\n{colors.YELLOW}[i] Workflow cancelled. Returning to main menu.{colors.RESET}")
                return

            if choice_config == "s":
                print(f"\nInclude preview models in evaluation? [y/N]")
                try:
                    prev_in = input(f"{colors.CYAN}Include preview models (y/n) [n]:{colors.RESET} ").strip().lower()
                except (KeyboardInterrupt, EOFError):
                    return
                if prev_in in {"y", "yes"}:
                    include_preview = True
                    eligible_models = registry.list_models(include_deprecated=False, include_preview=True)

                print(f"\n{colors.BOLD}Eligible Foundation Models ({len(eligible_models)} models):{colors.RESET}")
                for idx, m in enumerate(eligible_models, 1):
                    preview_tag = f" [{colors.YELLOW}PREVIEW{colors.RESET}]" if m.lifecycle_status.value == "preview" else ""
                    print(f"  [{idx:2d}] {m.model_id:<24} ({m.display_name}, {m.provider}){preview_tag}")
                try:
                    sel_in = input(f"\n{colors.CYAN}Enter comma-separated numbers or IDs (or [Enter] for all {len(eligible_models)}):{colors.RESET} ").strip()
                except (KeyboardInterrupt, EOFError):
                    return
                if sel_in:
                    parts = [p.strip() for p in sel_in.split(",") if p.strip()]
                    resolved: List[str] = []
                    for p in parts:
                        if p.isdigit():
                            num = int(p)
                            if 1 <= num <= len(eligible_models):
                                resolved.append(eligible_models[num - 1].model_id)
                        elif registry.get_foundation_model(p):
                            resolved.append(p)
                    if resolved:
                        selected_ids = list(dict.fromkeys(resolved))

                print("\nRanking Method: [1] WSM (default)  [2] TOPSIS")
                try:
                    m_in = input(f"{colors.CYAN}Select method (1-2) [1]:{colors.RESET} ").strip()
                except (KeyboardInterrupt, EOFError):
                    return
                if m_in == "2":
                    method = RankingMethod.TOPSIS

                print("\nPreset: [1] balanced  [2] cost_optimized  [3] quality_optimized  [4] long_context")
                try:
                    p_in = input(f"{colors.CYAN}Select preset (1-4) [1]:{colors.RESET} ").strip()
                except (KeyboardInterrupt, EOFError):
                    return
                preset_map = {
                    "1": RankingPreset.BALANCED,
                    "2": RankingPreset.COST_OPTIMIZED,
                    "3": RankingPreset.QUALITY_OPTIMIZED,
                    "4": RankingPreset.LONG_CONTEXT
                }
                preset = preset_map.get(p_in, RankingPreset.BALANCED)

            is_single_model = (selected_ids is not None and len(selected_ids) == 1)
            if is_single_model:
                print(f"\n{colors.YELLOW}[NOTE: Single model selected ({selected_ids[0]}). This evaluation is a suitability assessment against your prompt requirements, not a comparative multi-model ranking.]{colors.RESET}")

            print(f"\n{colors.CYAN}Evaluating candidate models locally ({method.value.upper()}, {preset.value} preset)...{colors.RESET}")
            orig_report = comparison_engine.compare_prompt(
                prompt=prompt,
                category=ProductCategory.FOUNDATION_MODEL,
                method=method,
                preset=preset,
                model_ids=selected_ids,
                include_preview=include_preview
            )

            # Concise Table
            print("\n" + "-" * 88)
            print(f" {'Rank':<5} {'Model ID':<22} {'Suit':<6} {'Tokens (in/out)':<17} {'Est. Cost':<11} {'Context':<8} {'Tok. Conf':<10} {'Lifecycle'}")
            print("-" * 88)
            for rm in orig_report.ranked_models:
                det = orig_report.model_details.get(rm.model_id)
                cost_str = f"${rm.estimated_cost_usd:.5f}" if rm.estimated_cost_usd is not None else "N/A"
                tok_in = det.token_count if det else rm.token_count
                tok_out = det.estimated_output_tokens if det else 350
                tok_str = f"{tok_in} / {tok_out}"
                ctx_str = f"{det.context_window_tokens // 1000}K" if (det and det.context_window_tokens < 1_000_000) else f"{det.context_window_tokens // 1_000_000}M" if det else "N/A"
                conf_str = f"{rm.token_count_method} ({rm.token_count_confidence:.2f})"
                life_str = "active" if rm.lifecycle_status == "active" else rm.lifecycle_status
                print(f" #{rm.rank:<4} {rm.model_id:<22} {rm.suitability_score:<6.2f} {tok_str:<17} {cost_str:<11} {ctx_str:<8} {conf_str:<10} {life_str}")
            print("-" * 88)

            # Stage 5: Recommend Model for Original Prompt
            orig_top = orig_report.ranked_models[0] if orig_report.ranked_models else None
            if orig_top:
                orig_det = orig_report.model_details.get(orig_top.model_id)
                top_cost_str = f"${orig_top.estimated_cost_usd:.5f}" if orig_top.estimated_cost_usd is not None else "N/A"
                if is_single_model:
                    print(f"\n{colors.BOLD}SUITABILITY ASSESSMENT FOR ORIGINAL PROMPT:{colors.RESET}")
                    print(f"  Model ID:               {colors.BOLD}{orig_top.model_id}{colors.RESET} ({orig_top.display_name})")
                    print(f"  Assessment Type:        Suitability assessment (1 model evaluated)")
                else:
                    print(f"\n{colors.BOLD}RECOMMENDED MODEL FOR ORIGINAL PROMPT:{colors.RESET}")
                    print(f"  Model ID:               {colors.BOLD}{orig_top.model_id}{colors.RESET} ({orig_top.display_name})")
                    print(f"  Recommendation Label:   Best estimated fit based on local heuristics (not measured benchmark quality)")

                print(f"  Task Suitability:       {orig_top.suitability_score:.2f} / 1.00 (Task: {orig_report.task_classification.predicted_category})")
                print(f"  Estimated Token Usage:  {orig_top.token_count} prompt tokens ({orig_top.token_count_method}, confidence {orig_top.token_count_confidence:.2f})")
                print(f"  Estimated Cost:         {top_cost_str}")
                print(f"  Context Fit:            {orig_det.context_window_tokens:,} tokens capacity" if orig_det else "Standard context")
                print(f"  Recommendation Rationale: {orig_top.reasoning}")
                if orig_top.token_count_disclaimer:
                    print(f"  Token Limitation:       {colors.DIM}{orig_top.token_count_disclaimer}{colors.RESET}")
            else:
                print(f"\n{colors.YELLOW}[!] No verified eligible model available matching selection criteria.{colors.RESET}")

            # ------------------------------------------------------------------
            # Stage 6: Local Prompt Optimization
            # ------------------------------------------------------------------
            print(f"\n{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.BOLD}[STAGE 3/6] LOCAL PROMPT OPTIMIZATION{colors.RESET}")
            print(f"{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.CYAN}Generating deterministic rule-based optimization (zero external API calls)...{colors.RESET}\n")

            opt_res = prompt_optimizer.optimize_prompt(
                prompt=prompt,
                security_analysis=orig_analysis,
                task_category=orig_report.task_classification.predicted_category,
                user_clarification=user_clarification
            )

            print(f"{colors.BOLD}OPTIMIZATION SUMMARY:{colors.RESET}")
            print(f"  • Disclaimer: {colors.DIM}{opt_res.optimizer_disclaimer}{colors.RESET}")
            if opt_res.clarifications_or_assumptions:
                print(f"  • Assumptions & Clarifications:")
                for a in opt_res.clarifications_or_assumptions:
                    print(f"    - {a}")
            if opt_res.detected_risks_addressed:
                print(f"  • Security Hardening Applied: {', '.join(opt_res.detected_risks_addressed)}")
            print(f"  • Meaningful Changes:")
            for c in opt_res.changes_summary:
                print(f"    - {c}")

            print(f"\n{colors.BOLD}OPTIMIZED PROMPT PREVIEW:{colors.RESET}")
            print("┌" + "─" * 78 + "┐")
            for line in opt_res.optimized_prompt.splitlines():
                print(f"│ {line:<76} │")
            print("└" + "─" * 78 + "┘")

            # ------------------------------------------------------------------
            # Stage 7: Reanalyse Optimized Prompt
            # ------------------------------------------------------------------
            print(f"\n{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.BOLD}[STAGE 4/6] OPTIMIZED PROMPT SECURITY RE-ANALYSIS{colors.RESET}")
            print(f"{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.CYAN}Re-evaluating optimized prompt with the same security classifier pipeline...{colors.RESET}\n")

            opt_analysis = analyze_prompt(opt_res.optimized_prompt, analysis_mode="both")

            def _extract_ctrl_names(ctrl_list: Any) -> Set[str]:
                names: Set[str] = set()
                if isinstance(ctrl_list, list):
                    for c in ctrl_list:
                        if isinstance(c, dict):
                            n = c.get("name") or c.get("matched_text")
                            if n:
                                names.add(str(n))
                        elif isinstance(c, str):
                            names.add(c)
                return names

            orig_sens = orig_analysis.get("sensitive_data", {})
            opt_sens = opt_analysis.get("sensitive_data", {})
            orig_sec_prob = orig_analysis.get("prompt_security", {}).get("malicious_probability", 0.0)
            opt_sec_prob = opt_analysis.get("prompt_security", {}).get("malicious_probability", 0.0)
            orig_risks_set = set(orig_analysis.get("application_risks", {}).get("detected_risks", []))
            opt_risks_set = set(opt_analysis.get("application_risks", {}).get("detected_risks", []))
            orig_controls_set = _extract_ctrl_names(orig_analysis.get("application_risks", {}).get("declared_controls", []))
            opt_controls_set = _extract_ctrl_names(opt_analysis.get("application_risks", {}).get("declared_controls", []))

            mitigated_surfaces_list = sorted(list(orig_risks_set - opt_risks_set))
            new_controls_list = sorted(list(opt_controls_set - orig_controls_set))
            remaining_risks_list = sorted(list(opt_risks_set))
            unmitigated_after = opt_analysis.get("application_risks", {}).get("unmitigated_surfaces", [])

            print(f"  • Prompt Injection Probability: {orig_sec_prob:.1%} → {opt_sec_prob:.1%}")
            if orig_sens.get("detected") and not opt_sens.get("detected"):
                print(f"  • Sensitive Data:               {colors.GREEN}[ RESOLVED ]{colors.RESET} Hardcoded secrets redacted and replaced with environment variables.")
            elif opt_sens.get("detected"):
                print(f"  • Sensitive Data:               {colors.RED}[ UNRESOLVED ]{colors.RESET} {opt_sens.get('findings_count')} secret(s) still present.")
            else:
                print(f"  • Sensitive Data:               {colors.GREEN}[ CLEAN ]{colors.RESET} No sensitive data in optimized prompt.")

            if new_controls_list:
                print(f"  • Declared Security Controls:   {colors.GREEN}[ +{len(new_controls_list)} ADDED ]{colors.RESET} ({', '.join(new_controls_list)})")

            if mitigated_surfaces_list:
                print(f"  • Mitigated Attack Surfaces:    {colors.GREEN}✓ {', '.join(mitigated_surfaces_list)}{colors.RESET}")

            if remaining_risks_list:
                print(f"  • Remaining Attack Surfaces:    {colors.YELLOW}! {', '.join(remaining_risks_list)}{colors.RESET}")
                if unmitigated_after:
                    print(f"    Unmitigated in prompt:        {', '.join(unmitigated_after)}")
            else:
                print(f"  • Remaining Attack Surfaces:    {colors.GREEN}[ None unmitigated in prompt ]{colors.RESET}")

            print(f"\n  {colors.DIM}Verification Note: Declared mitigations in prompt instructions guide model generation, but static prompt analysis cannot prove an application is secure. Defense-in-depth and runtime verification remain essential.{colors.RESET}")

            # ------------------------------------------------------------------
            # Stage 8: Recompare Models for Optimized Prompt
            # ------------------------------------------------------------------
            print(f"\n{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.BOLD}[STAGE 5/6] FOUNDATION MODEL RE-COMPARISON (OPTIMIZED PROMPT){colors.RESET}")
            print(f"{colors.BOLD}──────────────────────────────────────────────────────────────────────────────{colors.RESET}")
            print(f"{colors.CYAN}Re-evaluating models with the optimized prompt using identical ranking parameters ({method.value.upper()}, {preset.value})...{colors.RESET}\n")

            opt_report = comparison_engine.compare_prompt(
                prompt=opt_res.optimized_prompt,
                category=ProductCategory.FOUNDATION_MODEL,
                method=method,
                preset=preset,
                model_ids=selected_ids,
                include_preview=include_preview
            )

            opt_top = opt_report.ranked_models[0] if opt_report.ranked_models else None
            opt_det = opt_report.model_details.get(opt_top.model_id) if opt_top else None

            if orig_top and opt_top:
                same_winner = (orig_top.model_id == opt_top.model_id)
                tok_delta = opt_top.token_count - orig_top.token_count
                suit_delta = opt_top.suitability_score - orig_top.suitability_score
                orig_cost_val = orig_top.estimated_cost_usd or 0.0
                opt_cost_val = opt_top.estimated_cost_usd or 0.0
                cost_delta = opt_cost_val - orig_cost_val

                print(f"  • Recommended Model: {colors.BOLD}{orig_top.model_id}{colors.RESET} → {colors.BOLD}{opt_top.model_id}{colors.RESET} ({'UNCHANGED' if same_winner else 'CHANGED'})")
                print(f"  • Suitability Score: {orig_top.suitability_score:.2f} → {opt_top.suitability_score:.2f} ({suit_delta:+.2f})")
                print(f"  • Prompt Tokens:     {orig_top.token_count} → {opt_top.token_count} ({tok_delta:+d} tokens)")
                print(f"  • Estimated Cost:    ${orig_cost_val:.5f} → ${opt_cost_val:.5f} ({cost_delta:+.5f})")

                if same_winner:
                    print(f"\n  Rationale: {opt_top.model_id} remains the top-recommended model for the optimized prompt, providing the strongest suitability balance for {opt_report.task_classification.predicted_category}.")
                else:
                    print(f"\n  Rationale: Recommendation changed from {orig_top.model_id} to {opt_top.model_id} due to expanded constraints and context requirements in the optimized prompt.")

                print(f"\n  {colors.DIM}Cost & Token Note: The optimized prompt includes explicit security guardrails, edge cases, and output formatting, which naturally increases token count. We do not claim optimization reduced cost; explicit requirements improve specification quality.{colors.RESET}")

            # ------------------------------------------------------------------
            # Stage 9: Final Before-and-After Summary (Sections A to H)
            # ------------------------------------------------------------------
            print(f"\n" + "=" * 80)
            print(f"{colors.BOLD}{colors.CYAN}                     COMPREHENSIVE BEFORE-AND-AFTER SUMMARY{colors.RESET}")
            print("=" * 80)

            # A. Original Prompt Security Summary
            print(f"\n{colors.BOLD}A. ORIGINAL PROMPT SECURITY SUMMARY{colors.RESET}")
            print(f"   • Prompt Injection Status: {'Malicious / Adversarial' if is_mal else 'Benign / Non-adversarial'} ({prob_val:.1%})")
            print(f"   • Application Risks:       {', '.join(detected_risks) if detected_risks else 'None detected'}")
            print(f"   • Hardcoded Secrets:       {sens.get('findings_count', 0)} detected (masked in reports)")
            orig_ctrl_names = sorted(list(_extract_ctrl_names(declared_controls)))
            print(f"   • Declared Controls:       {', '.join(orig_ctrl_names) if orig_ctrl_names else 'None'}")

            # B. Original Prompt Model Recommendation
            print(f"\n{colors.BOLD}B. ORIGINAL PROMPT MODEL RECOMMENDATION{colors.RESET}")
            if orig_top:
                rec_prefix = "Suitability Assessment:" if is_single_model else "Top Recommendation (Heuristic Fit):"
                print(f"   • {rec_prefix} {orig_top.display_name} ({orig_top.model_id})")
                print(f"   • Suitability Rating: {orig_top.suitability_score:.2f} / 1.00 | Est. Cost: ${orig_top.estimated_cost_usd or 0.0:.5f}")
                print(f"   • Evaluation Rationale: {orig_top.reasoning}")

            # C. Optimized Prompt
            print(f"\n{colors.BOLD}C. OPTIMIZED PROMPT{colors.RESET}")
            print("┌" + "─" * 78 + "┐")
            for line in opt_res.optimized_prompt.splitlines():
                print(f"│ {line:<76} │")
            print("└" + "─" * 78 + "┘")

            # D. Optimization Changes and Assumptions
            print(f"\n{colors.BOLD}D. OPTIMIZATION CHANGES AND ASSUMPTIONS{colors.RESET}")
            print(f"   • Rule-Based Rewrite Disclaimer: {opt_res.optimizer_disclaimer}")
            print(f"   • Assumptions Made:")
            for a in opt_res.clarifications_or_assumptions:
                print(f"     - {a}")
            print(f"   • Key Modifications:")
            for c in opt_res.changes_summary:
                print(f"     - {c}")

            # E. Optimized Prompt Security Summary
            print(f"\n{colors.BOLD}E. OPTIMIZED PROMPT SECURITY SUMMARY{colors.RESET}")
            print(f"   • Prompt Injection Probability: {opt_sec_prob:.1%}")
            print(f"   • Controls Injected & Verified: {', '.join(opt_controls_set) if opt_controls_set else 'Standard controls'}")
            print(f"   • Mitigated Risks in Prompt:    {', '.join(mitigated_surfaces_list) if mitigated_surfaces_list else 'None'}")
            print(f"   • Remaining Risk Surfaces:      {', '.join(remaining_risks_list) if remaining_risks_list else 'None'}")

            # F. Model Recommendation for Optimized Prompt
            print(f"\n{colors.BOLD}F. MODEL RECOMMENDATION FOR OPTIMIZED PROMPT{colors.RESET}")
            if opt_top:
                rec_prefix = "Suitability Assessment:" if is_single_model else "Top Recommendation (Heuristic Fit):"
                print(f"   • {rec_prefix} {opt_top.display_name} ({opt_top.model_id})")
                print(f"   • Suitability Rating: {opt_top.suitability_score:.2f} / 1.00 | Est. Cost: ${opt_top.estimated_cost_usd or 0.0:.5f}")
                print(f"   • Evaluation Rationale: {opt_top.reasoning}")

            # G. Before-and-After Token, Cost, and Suitability Comparison
            print(f"\n{colors.BOLD}G. BEFORE-AND-AFTER TOKEN, COST, AND SUITABILITY COMPARISON{colors.RESET}")
            print(f"   {'Metric':<25} {'Original Prompt':<22} {'Optimized Prompt':<22} {'Delta'}")
            print(f"   " + "-" * 75)
            orig_id_str = orig_top.model_id if orig_top else "N/A"
            opt_id_str = opt_top.model_id if opt_top else "N/A"
            orig_s_str = f"{orig_top.suitability_score:.2f}" if orig_top else "N/A"
            opt_s_str = f"{opt_top.suitability_score:.2f}" if opt_top else "N/A"
            s_delta_str = f"{(opt_top.suitability_score - orig_top.suitability_score):+.2f}" if (orig_top and opt_top) else "N/A"
            orig_t_str = f"{orig_top.token_count}" if orig_top else "N/A"
            opt_t_str = f"{opt_top.token_count}" if opt_top else "N/A"
            t_delta_str = f"{(opt_top.token_count - orig_top.token_count):+d}" if (orig_top and opt_top) else "N/A"
            orig_c_str = f"${orig_top.estimated_cost_usd:.5f}" if (orig_top and orig_top.estimated_cost_usd is not None) else "N/A"
            opt_c_str = f"${opt_top.estimated_cost_usd:.5f}" if (opt_top and opt_top.estimated_cost_usd is not None) else "N/A"
            c_delta_str = f"${(opt_top.estimated_cost_usd - orig_top.estimated_cost_usd):+.5f}" if (orig_top and opt_top and orig_top.estimated_cost_usd is not None and opt_top.estimated_cost_usd is not None) else "N/A"

            print(f"   {'Top Model':<25} {orig_id_str:<22} {opt_id_str:<22} {'Same' if orig_id_str == opt_id_str else 'Changed'}")
            print(f"   {'Suitability Score':<25} {orig_s_str:<22} {opt_s_str:<22} {s_delta_str}")
            print(f"   {'Prompt Tokens':<25} {orig_t_str:<22} {opt_t_str:<22} {t_delta_str}")
            print(f"   {'Total Est. Cost':<25} {orig_c_str:<22} {opt_c_str:<22} {c_delta_str}")

            # H. Remaining Risks, Unverified Data, and Limitations
            print(f"\n{colors.BOLD}H. REMAINING RISKS, UNVERIFIED DATA, AND LIMITATIONS{colors.RESET}")
            print("   • Static Analysis Ceiling: Prompt analysis cannot verify downstream runtime execution, server config, or database permissions.")
            print("   • Tokenizer Calibration: Non-OpenAI models use calibrated offline SentencePiece/BPE estimates.")
            print("   • Pricing Data: Derived from verified public pricing (2026-10-26); unverified/preview models were excluded from ranking.")
            print("   • Recommendation Heuristic: Scores reflect relative multi-criteria trade-offs [0.0, 1.0], not empirical benchmark performance.")
            print("=" * 80)

            # ------------------------------------------------------------------
            # Stage 10: Next Actions Menu
            # ------------------------------------------------------------------
            sub_action = None
            while True:
                print(f"\n{colors.BOLD}Next Actions:{colors.RESET}")
                print("  [1] Save the optimized prompt to a text file")
                print("  [2] Optimize again with a different objective or constraints")
                print("  [3] Compare selected models for this prompt")
                print("  [4] Start a new prompt analysis")
                print("  [5] Return to the main menu")

                try:
                    choice_act = input(f"{colors.CYAN}Select an action (1-5):{colors.RESET} ").strip()
                except (KeyboardInterrupt, EOFError):
                    return

                if choice_act == "1":
                    save_prompt_to_file(colors, opt_res.optimized_prompt)
                elif choice_act == "2":
                    try:
                        new_obj = input(f"\n{colors.CYAN}Enter new objective or extra requirements (or 'c' to cancel):{colors.RESET} ").strip()
                    except (KeyboardInterrupt, EOFError):
                        return
                    if new_obj.lower() not in {"c", "cancel", ""}:
                        user_clarification = new_obj
                        sub_action = "reoptimize"
                        break
                elif choice_act == "3":
                    print(f"\n{colors.BOLD}Eligible Active Foundation Models:{colors.RESET}")
                    for idx, m in enumerate(eligible_models, 1):
                        print(f"  [{idx:2d}] {m.model_id:<24} ({m.display_name})")
                    try:
                        custom_in = input(f"\n{colors.CYAN}Enter comma-separated numbers or IDs (or 'c' to cancel):{colors.RESET} ").strip()
                    except (KeyboardInterrupt, EOFError):
                        return
                    if custom_in.lower() not in {"c", "cancel", ""}:
                        parts = [p.strip() for p in custom_in.split(",") if p.strip()]
                        custom_ids: List[str] = []
                        for p in parts:
                            if p.isdigit() and 1 <= int(p) <= len(eligible_models):
                                custom_ids.append(eligible_models[int(p) - 1].model_id)
                            elif registry.get_foundation_model(p):
                                custom_ids.append(p)
                        if custom_ids:
                            selected_ids = list(dict.fromkeys(custom_ids))
                            sub_action = "recompare"
                            break
                elif choice_act == "4":
                    sub_action = "new"
                    break
                elif choice_act in {"5", "return", "menu", "c", "cancel"}:
                    return
                else:
                    print(f"{colors.RED}[!] Invalid selection '{choice_act}'. Please choose between 1 and 5.{colors.RESET}")

            if sub_action in {"reoptimize", "recompare"}:
                continue
            elif sub_action == "new":
                active_prompt = None
                break


# ===========================================================================
# Option 2: Standalone Prompt Security Analysis
# ===========================================================================

def cli_prompt_security_analysis(colors: Colors, preloaded_prompt: Optional[str] = None) -> None:
    """Runs interactive prompt security and architectural risk analysis."""
    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}2. STANDALONE PROMPT SECURITY & ARCHITECTURAL RISK ANALYSIS{colors.RESET}")
    print("=" * 80)


    if preloaded_prompt:
        prompt = preloaded_prompt.strip()
    else:
        prompt = read_multiline_prompt(
            colors,
            prompt_label="Enter the prompt to analyze for security vulnerabilities:",
            sentinel="END"
        )

    if prompt is None:
        print(f"\n{colors.YELLOW}[i] Security analysis cancelled. Returning to main menu.{colors.RESET}")
        return

    if not prompt:
        print(f"\n{colors.YELLOW}[!] Warning: Prompt cannot be empty or contain only whitespace.{colors.RESET}")
        return

    print(f"\n{colors.CYAN}Running unified security analysis (100% offline)...{colors.RESET}")
    try:
        analysis_result = analyze_prompt(prompt, analysis_mode="both")
    except Exception as e:
        print(f"\n{colors.RED}[ERROR] Unexpected error during analysis: {e}{colors.RESET}")
        analysis_result = {
            "prompt": prompt,
            "analysis_mode": "both",
            "status": "error",
            "error": str(e),
            "model_availability": {"prompt_security_model": False, "application_risk_model": False},
            "prompt_security": {"status": "error", "error": str(e)},
            "application_risks": {"status": "error", "error": str(e)},
            "sensitive_data": {"detected": False, "findings_count": 0, "findings": []}
        }

    report_text = format_security_report(prompt, analysis_result, colors=colors)
    print(report_text)

    try:
        input(f"\n{colors.CYAN}Press [Enter] to return to main menu...{colors.RESET}")
    except (KeyboardInterrupt, EOFError):
        pass


# ===========================================================================
# Option 3: Offline Foundation Model Comparison
# ===========================================================================

def cli_compare_foundation_models(colors: Colors, preloaded_prompt: Optional[str] = None) -> None:
    """Interactively compares verified foundation models 100% locally."""
    while True:
        print("\n" + "=" * 80)
        print(f"{colors.BOLD}{colors.CYAN}3. OFFLINE FOUNDATION MODEL COMPARISON{colors.RESET}")
        print("=" * 80)

        print(f"{colors.DIM}Strictly 100% offline. Zero provider API calls, zero telemetry.{colors.RESET}")

        if preloaded_prompt:
            prompt = preloaded_prompt.strip()
        else:
            prompt = read_multiline_prompt(
                colors,
                prompt_label="Describe the coding, reasoning, or instruction task (or paste prompt):",
                sentinel="END"
            )

        if prompt is None:
            print(f"\n{colors.YELLOW}[i] Model comparison cancelled. Returning to main menu.{colors.RESET}")
            return

        if not prompt:
            print(f"\n{colors.YELLOW}[!] Warning: Task description cannot be empty.{colors.RESET}")
            return

        # 1. Local Task Classification
        task_res = task_classifier.classify_task(prompt)
        inferred_task = task_res.predicted_category
        conf = task_res.confidence

        print(f"\n{colors.BOLD}Task Classification (Local Model):{colors.RESET}")
        print(f"  Inferred Category:   {colors.GREEN}{inferred_task}{colors.RESET} ({conf * 100:.1f}% confidence)")
        print("  Available categories: [1] code_generation  [2] code_explanation  [3] security_analysis")
        print("                        [4] general_instruction  [5] reasoning_math  [6] data_extraction")

        try:
            task_choice = input(f"{colors.CYAN}Press [Enter] to accept inferred task, or enter number (1-6) / 'c' to cancel:{colors.RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return

        if task_choice in {"c", "cancel"}:
            return

        task_mapping = {
            "1": "code_generation",
            "2": "code_explanation",
            "3": "security_analysis",
            "4": "general_instruction",
            "5": "reasoning_math",
            "6": "data_extraction"
        }
        chosen_task = task_mapping.get(task_choice, inferred_task)

        # 2. Show Eligible Foundation Models
        include_preview = False
        eligible = registry.list_models(include_deprecated=False, include_preview=False)
        print(f"\n{colors.BOLD}Eligible Active Foundation Models ({len(eligible)} models):{colors.RESET}")
        print("-" * 80)
        print(f" {'#':<3} {'Model ID':<22} {'Provider':<11} {'Context':<9} {'Pricing ($/1M in/out)':<24} {'Tokenizer'}")
        print("-" * 80)
        for idx, m in enumerate(eligible, 1):
            ctx_str = f"{m.context_window_tokens // 1000}K" if m.context_window_tokens < 1_000_000 else f"{m.context_window_tokens // 1_000_000}M"
            pricing_str = f"${m.pricing.input_cost_per_m:.2f} / ${m.pricing.output_cost_per_m:.2f}"
            tok_method = "exact" if m.provider == "openai" else "approx"
            print(f" {idx:<3} {m.model_id:<22} {m.provider:<11} {ctx_str:<9} {pricing_str:<24} {m.tokenizer_name} ({tok_method})")
        print("-" * 80)

        # 3. Model Selection
        try:
            model_sel = input(f"{colors.CYAN}Select models [Enter for all {len(eligible)}, or comma-separated numbers/IDs, 'p' for preview, 'c' to cancel]:{colors.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if model_sel.lower() in {"c", "cancel"}:
            return

        if model_sel.lower() in {"p", "preview"}:
            include_preview = True
            eligible = registry.list_models(include_deprecated=False, include_preview=True)
            print(f"\n{colors.BOLD}Eligible Foundation Models including Preview ({len(eligible)} models):{colors.RESET}")
            print("-" * 80)
            print(f" {'#':<3} {'Model ID':<24} {'Provider':<11} {'Context':<9} {'Pricing ($/1M in/out)':<24} {'Status'}")
            print("-" * 80)
            for idx, m in enumerate(eligible, 1):
                ctx_str = f"{m.context_window_tokens // 1000}K" if m.context_window_tokens < 1_000_000 else f"{m.context_window_tokens // 1_000_000}M"
                pricing_str = f"${m.pricing.input_cost_per_m:.2f} / ${m.pricing.output_cost_per_m:.2f}" if m.pricing.input_cost_per_m is not None else "UNVERIFIED"
                print(f" {idx:<3} {m.model_id:<24} {m.provider:<11} {ctx_str:<9} {pricing_str:<24} {m.lifecycle_status.value.upper()}")
            print("-" * 80)
            try:
                model_sel = input(f"{colors.CYAN}Select models [Enter for all {len(eligible)}, or comma-separated numbers/IDs, 'c' to cancel]:{colors.RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                return
            if model_sel.lower() in {"c", "cancel"}:
                return

        selected_ids: Optional[List[str]] = None
        if model_sel:
            parts = [p.strip() for p in model_sel.split(",") if p.strip()]
            resolved: List[str] = []
            for p in parts:
                if p.isdigit():
                    num = int(p)
                    if 1 <= num <= len(eligible):
                        resolved.append(eligible[num - 1].model_id)
                elif registry.get_foundation_model(p):
                    resolved.append(p)
            if resolved:
                selected_ids = list(dict.fromkeys(resolved))

        # 4. Ranking Method Selection
        print(f"\n{colors.BOLD}Ranking Algorithm:{colors.RESET}")
        print("  [1] Weighted Sum Model (WSM) [default]")
        print("  [2] TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)")
        try:
            method_input = input(f"{colors.CYAN}Select ranking method (1-2) [default=1]:{colors.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        method = RankingMethod.TOPSIS if method_input == "2" else RankingMethod.WEIGHTED_SUM

        # 5. Ranking Preset Selection
        print(f"\n{colors.BOLD}Optimization Preset:{colors.RESET}")
        print("  [1] balanced (45% suitability, 35% cost, 20% context) [default]")
        print("  [2] cost_optimized (20% suitability, 70% cost, 10% context)")
        print("  [3] quality_optimized (80% suitability, 5% cost, 15% context)")
        print("  [4] long_context (25% suitability, 25% cost, 50% context)")
        try:
            preset_input = input(f"{colors.CYAN}Select preset (1-4) [default=1]:{colors.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        preset_map = {
            "1": RankingPreset.BALANCED,
            "2": RankingPreset.COST_OPTIMIZED,
            "3": RankingPreset.QUALITY_OPTIMIZED,
            "4": RankingPreset.LONG_CONTEXT
        }
        preset = preset_map.get(preset_input, RankingPreset.BALANCED)

        # 6. Run Comparison
        print(f"\n{colors.CYAN}Evaluating models locally using {method.value.upper()} ({preset.value} preset)...{colors.RESET}")
        report = comparison_engine.compare_prompt(
            prompt=prompt,
            category=ProductCategory.FOUNDATION_MODEL,
            method=method,
            preset=preset,
            model_ids=selected_ids,
            include_preview=include_preview
        )

        # 7. Display Results Table
        print("\n" + "=" * 80)
        print(f"{colors.BOLD}{colors.CYAN}             FOUNDATION MODEL RECOMMENDATION RANKINGS ({method.value.upper()}){colors.RESET}")
        print("=" * 80)
        print(f" {'Rank':<5} {'Model ID':<22} {'Provider':<10} {'Score':<8} {'Suitability':<12} {'Est. Cost':<11} {'Method'}")
        print("-" * 80)
        for rm in report.ranked_models:
            cost_str = f"${rm.estimated_cost_usd:.5f}" if rm.estimated_cost_usd is not None else "N/A"
            conf_str = f"{rm.token_count_method} ({rm.token_count_confidence:.2f})"
            print(f" #{rm.rank:<4} {rm.model_id:<22} {rm.provider:<10} {rm.score:<8.4f} {rm.suitability_score:<12.2f} {cost_str:<11} {conf_str}")
        print("-" * 80)

        # 8. Detailed breakdown of Top 3 models
        print(f"\n{colors.BOLD}TOP RECOMMENDATION BREAKDOWN:{colors.RESET}")
        for rm in report.ranked_models[:3]:
            details = report.model_details.get(rm.model_id)
            print(f"\n  {colors.BOLD}#{rm.rank} — {rm.display_name} ({rm.provider}){colors.RESET}")
            print(f"     Recommendation Score: {colors.GREEN}{rm.score:.4f}{colors.RESET} (Heuristic score [0.0 - 1.0], not measured benchmark)")
            print(f"     Suitability Rating:   {rm.suitability_score:.2f} / 1.00")
            if details and details.cost_breakdown:
                cb = details.cost_breakdown
                print(f"     Estimated Cost:       ${cb.total_estimated_cost_usd:.5f} (Input: ${cb.input_cost_usd:.5f}, Output: ${cb.output_cost_usd:.5f})")
                print(f"     Pricing Rates:        ${cb.input_cost_per_m:.2f} in / ${cb.output_cost_per_m:.2f} out per 1M tokens")
            print(f"     Token Count:          {rm.token_count} prompt tokens ({rm.token_count_method}, confidence {rm.token_count_confidence:.2f})")
            if rm.token_count_disclaimer:
                print(f"     Token Disclaimer:     {colors.DIM}{rm.token_count_disclaimer}{colors.RESET}")
            print(f"     Evaluation Rationale: {rm.reasoning}")

        # 9. Excluded Models Explanation
        print("\n" + "-" * 80)
        print(f"{colors.BOLD}EXCLUDED MODELS & MISSING DATA POLICY:{colors.RESET}")
        print("  • Gemini 1.x models (1.0-pro, 1.5-pro, 1.5-flash): RETIRED legacy models (removed from active pool).")
        print("  • gemini-3.1-pro-preview:                           PREVIEW status (excluded by default unless preview enabled).")
        print("  • gemini-2.5-pro, gemini-2.5-flash:                UNVERIFIED future releases (missing public pricing, ID, context).")
        print("  • grok-3, grok-3-mini:                             PREVIEW status (missing production API endpoint, public pricing).")
        print("  • gpt-4o, gpt-4o-mini, o1, claude-3-7-sonnet:      HISTORICAL legacy models (superseded by modern GPT-5.x/6 and Claude 5.5).")
        print("  • gpt-4-turbo, gpt-3.5-turbo:                      RETIRED legacy models.")
        print("  Policy: Default rankings strictly exclude unverified, preview, and retired models.")
        print("          Missing prices receive maximum cost penalty and are never treated as free.")
        print("=" * 80)

        # 10. Post-comparison options
        if preloaded_prompt:
            try:
                input(f"\n{colors.CYAN}Press [Enter] to return to main menu...{colors.RESET}")
            except (KeyboardInterrupt, EOFError):
                pass
            return

        print(f"\n  [1] Compare another task or prompt")
        print(f"  [2] Return to main menu")
        try:
            next_act = input(f"{colors.CYAN}Select option (1-2) [default=2]:{colors.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if next_act != "1":
            return


# ===========================================================================
# Option 4: IDE Coding Assistant Comparison
# ===========================================================================

def cli_compare_ide_assistants(colors: Colors, preloaded_prompt: Optional[str] = None) -> None:
    """Compares verified IDE coding assistants using workflow and tooling criteria."""
    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}4. IDE CODING ASSISTANT COMPARISON{colors.RESET}")
    print("=" * 80)

    print(f"{colors.DIM}Evaluates multi-file agents, repo indexing, terminal execution, and privacy.{colors.RESET}")

    if preloaded_prompt:
        prompt = preloaded_prompt.strip()
    else:
        try:
            print("\nEnter coding task or workflow requirements (or press [Enter] for general coding):")
            user_input = input(f"{colors.CYAN}>{colors.RESET} ").strip()
            prompt = user_input or "Multi-file repository refactoring, terminal execution, and code completions"
        except (KeyboardInterrupt, EOFError):
            return

    # Ranking method selection
    print("\nRanking Algorithm: [1] Weighted Sum Model (WSM) [default]  [2] TOPSIS")
    try:
        method_input = input(f"{colors.CYAN}Select method (1-2) [default=1]:{colors.RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        return
    method = RankingMethod.TOPSIS if method_input == "2" else RankingMethod.WEIGHTED_SUM

    print(f"\n{colors.CYAN}Evaluating IDE assistants locally using {method.value.upper()}...{colors.RESET}")
    report = comparison_engine.compare_prompt(
        prompt=prompt,
        category=ProductCategory.IDE_ASSISTANT,
        method=method
    )

    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}              IDE CODING ASSISTANT RANKINGS ({method.value.upper()}){colors.RESET}")
    print("=" * 80)
    print(f" {'Rank':<5} {'Product ID':<18} {'Display Name':<20} {'Vendor':<18} {'Score':<8} {'Pricing Summary'}")
    print("-" * 80)
    for rp in report.ranked_products or []:
        print(f" #{rp.rank:<4} {rp.product_id:<18} {rp.display_name:<20} {rp.vendor:<18} {rp.score:<8.4f} {rp.pricing_summary}")
    print("-" * 80)

    # Detailed product cards
    for rp in report.ranked_products or []:
        ide = registry.get_ide(rp.product_id)
        print(f"\n  {colors.BOLD}#{rp.rank} — {rp.display_name} ({rp.vendor}){colors.RESET}")
        print(f"     Recommendation Score: {colors.GREEN}{rp.score:.4f}{colors.RESET} (Heuristic recommendation score)")
        print(f"     Pricing:              {rp.pricing_summary}")
        if ide:
            print(f"     Editor Integration:   {', '.join(ide.editor_integration)}")
            print(f"     Supported Models:     {', '.join(ide.supported_models[:3])}")
            print(f"     Key Capabilities:     {', '.join(ide.key_capabilities[:3])}")
            print(f"     Privacy Controls:     {ide.privacy_statement}")
            print(f"     Source URL:           {ide.source_url} (Audited: {ide.last_audit_date})")
        print(f"     Reasoning:            {rp.reasoning}")

    print("\n" + "-" * 80)
    print(f"{colors.BOLD}CATEGORY PROVENANCE & ISOLATION NOTE:{colors.RESET}")
    print("  IDE assistants are scored on agent workflows, indexing, terminal automation, and privacy.")
    print("  They use monthly subscription tiers, NOT per-token foundation model pricing.")
    print("=" * 80)

    try:
        input(f"\n{colors.CYAN}Press [Enter] to return to main menu...{colors.RESET}")
    except (KeyboardInterrupt, EOFError):
        pass


# ===========================================================================
# Option 5: AI App Builder Comparison
# ===========================================================================

def cli_compare_app_builders(colors: Colors, preloaded_prompt: Optional[str] = None) -> None:
    """Compares verified AI app builders using full-stack capabilities and deployment."""
    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}5. AI APP BUILDER COMPARISON{colors.RESET}")
    print("=" * 80)

    print(f"{colors.DIM}Evaluates full-stack backends, database/auth support, UI quality, and code export.{colors.RESET}")

    if preloaded_prompt:
        prompt = preloaded_prompt.strip()
    else:
        try:
            print("\nEnter application requirements (or press [Enter] for full-stack web prototype):")
            user_input = input(f"{colors.CYAN}>{colors.RESET} ").strip()
            prompt = user_input or "Full-stack web application with user authentication, database persistence, and cloud hosting"
        except (KeyboardInterrupt, EOFError):
            return

    # Ranking method selection
    print("\nRanking Algorithm: [1] Weighted Sum Model (WSM) [default]  [2] TOPSIS")
    try:
        method_input = input(f"{colors.CYAN}Select method (1-2) [default=1]:{colors.RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        return
    method = RankingMethod.TOPSIS if method_input == "2" else RankingMethod.WEIGHTED_SUM

    print(f"\n{colors.CYAN}Evaluating app builders locally using {method.value.upper()}...{colors.RESET}")
    report = comparison_engine.compare_prompt(
        prompt=prompt,
        category=ProductCategory.APP_BUILDER,
        method=method
    )

    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}                AI APP BUILDER RANKINGS ({method.value.upper()}){colors.RESET}")
    print("=" * 80)
    print(f" {'Rank':<5} {'Product ID':<16} {'Display Name':<16} {'Vendor':<14} {'Score':<8} {'Primary Stacks'}")
    print("-" * 80)
    for rp in report.ranked_products or []:
        builder = registry.get_app_builder(rp.product_id)
        stacks_str = ", ".join(builder.primary_stacks[:3]) if builder else "Web"
        print(f" #{rp.rank:<4} {rp.product_id:<16} {rp.display_name:<16} {rp.vendor:<14} {rp.score:<8.4f} {stacks_str}")
    print("-" * 80)

    # Detailed product cards
    for rp in report.ranked_products or []:
        builder = registry.get_app_builder(rp.product_id)
        print(f"\n  {colors.BOLD}#{rp.rank} — {rp.display_name} ({rp.vendor}){colors.RESET}")
        print(f"     Recommendation Score: {colors.GREEN}{rp.score:.4f}{colors.RESET} (Heuristic recommendation score)")
        print(f"     Pricing Model:        {rp.pricing_summary}")
        if builder:
            print(f"     Primary Stacks:       {', '.join(builder.primary_stacks)}")
            print(f"     Supported Backends:   {', '.join(builder.supported_backends)}")
            print(f"     Database & Auth:      {', '.join(builder.database_auth_support)}")
            print(f"     Deployment:           {', '.join(builder.deployment_options)}")
            print(f"     GitHub Integration:   {builder.github_integration}")
            print(f"     Source Code Export:   {builder.source_code_export}")
            print(f"     Limitations:          {'; '.join(builder.documented_limitations)}")
            print(f"     Source URL:           {builder.source_url} (Audited: {builder.last_audit_date})")
        print(f"     Reasoning:            {rp.reasoning}")

    print("\n" + "-" * 80)
    print(f"{colors.BOLD}CATEGORY PROVENANCE & ISOLATION NOTE:{colors.RESET}")
    print("  App builders are scored on full-stack backends, database/auth, and exportability.")
    print("  They use freemium credit/tier plans, NOT per-token foundation model pricing.")
    print("=" * 80)

    try:
        input(f"\n{colors.CYAN}Press [Enter] to return to main menu...{colors.RESET}")
    except (KeyboardInterrupt, EOFError):
        pass


# ===========================================================================
# Option 6: Inspect Model/Product Catalogue
# ===========================================================================

def cli_inspect_catalogue(colors: Colors) -> None:
    """Inspects verified metadata, lifecycle status, pricing, and provenance across categories."""
    while True:
        print("\n" + "=" * 80)
        print(f"{colors.BOLD}{colors.CYAN}6. INSPECT MODEL & PRODUCT CATALOGUE{colors.RESET}")
        print("=" * 80)

        print("Select category to inspect:")
        print("  [1] Foundation Models (21 active GA, 5 preview/unverified, 20 historical/retired)")
        print("  [2] IDE Coding Assistants (4 verified products)")
        print("  [3] AI App Builders (4 verified platforms)")
        print("  [0] Back to Main Menu")

        try:
            choice = input(f"{colors.CYAN}Select option (0-3):{colors.RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if choice in {"0", "back", "b"}:
            return

        # -------------------------------------------------------------------
        # Category 1: Foundation Models
        # -------------------------------------------------------------------
        if choice == "1":
            active_models = registry.list_active_models()
            preview_models = registry.list_preview_models()
            historical_models = registry.list_historical_models()
            excluded_models = preview_models + historical_models

            while True:
                print("\n" + "-" * 80)
                print(f"{colors.BOLD}ACTIVE FOUNDATION MODELS ({len(active_models)} models eligible for default rankings):{colors.RESET}")
                print("-" * 80)
                print(f" {'#':<3} {'Model ID':<22} {'Provider':<10} {'Context':<9} {'Pricing ($/1M in/out)':<24} {'Status'}")
                print("-" * 80)
                for idx, m in enumerate(active_models, 1):
                    ctx_str = f"{m.context_window_tokens // 1000}K" if m.context_window_tokens < 1_000_000 else f"{m.context_window_tokens // 1_000_000}M"
                    p_str = f"${m.pricing.input_cost_per_m:.2f} / ${m.pricing.output_cost_per_m:.2f}"
                    print(f" {idx:<3} {m.model_id:<22} {m.provider:<10} {ctx_str:<9} {p_str:<24} {m.lifecycle_status.value.upper()}")
                print("-" * 80)
                print(f"• Enter model # (1-{len(active_models)}) or exact Model ID to inspect full metadata")
                print("• Type 'p' or 'preview' to view preview models")
                print("• Type 'e' or 'excluded' to view unverified, preview, and legacy models")
                print("• Type '0' or 'back' to return to category selection")

                try:
                    sub = input(f"{colors.CYAN}Select model to inspect:{colors.RESET} ").strip()
                except (KeyboardInterrupt, EOFError):
                    break

                if sub in {"0", "back", "b"}:
                    break

                if sub.lower() in {"p", "preview"}:
                    print("\n" + "-" * 80)
                    print(f"{colors.BOLD}PREVIEW FOUNDATION MODELS ({len(preview_models)} models - opt-in required):{colors.RESET}")
                    print("-" * 80)
                    for pm in preview_models:
                        print(f"  • {colors.BOLD}{pm.model_id:<26}{colors.RESET} [{pm.lifecycle_status.value.upper()}] Provider: {pm.provider}")
                        if pm.pricing.input_cost_per_m is not None:
                            print(f"      Verified pricing: ${pm.pricing.input_cost_per_m:.2f} in / ${pm.pricing.output_cost_per_m:.2f} out per 1M")
                        if pm.unverified_fields:
                            print(f"      Unverified critical fields: {', '.join(pm.unverified_fields)}")
                    print("-" * 80)
                    try:
                        input(f"{colors.CYAN}Press [Enter] to continue...{colors.RESET}")
                    except (KeyboardInterrupt, EOFError):
                        pass
                    continue

                if sub.lower() in {"e", "excluded"}:
                    print("\n" + "-" * 80)
                    print(f"{colors.BOLD}EXCLUDED / UNVERIFIED / PREVIEW / RETIRED MODELS ({len(excluded_models)} models):{colors.RESET}")
                    print("-" * 80)
                    for em in excluded_models:
                        print(f"  • {colors.BOLD}{em.model_id:<20}{colors.RESET} [{em.lifecycle_status.value.upper()}] Provider: {em.provider}")
                        if em.unverified_fields:
                            print(f"      Unverified critical fields: {', '.join(em.unverified_fields)}")
                        if em.deprecation_date:
                            print(f"      Deprecation date: {em.deprecation_date} (Replacement: {em.replacement_model_id or 'None'})")
                    print("-" * 80)
                    try:
                        input(f"{colors.CYAN}Press [Enter] to continue...{colors.RESET}")
                    except (KeyboardInterrupt, EOFError):
                        pass
                    continue

                target_model: Optional[ModelMetadata] = None
                if sub.isdigit():
                    num = int(sub)
                    if 1 <= num <= len(active_models):
                        target_model = active_models[num - 1]
                else:
                    target_model = registry.get_foundation_model(sub)

                if not target_model:
                    print(f"{colors.RED}[!] Model '{sub}' not found in registry.{colors.RESET}")
                    continue

                # Display detailed model card
                print("\n" + "=" * 80)
                print(f"{colors.BOLD}{colors.CYAN}FOUNDATION MODEL INSPECTION: {target_model.model_id}{colors.RESET}")
                print("=" * 80)
                print(f"  Display Name:             {target_model.display_name}")
                print(f"  Provider:                 {target_model.provider}")
                print(f"  Model Family:             {target_model.family}")
                print(f"  Category:                 {target_model.category.value}")
                print(f"  Lifecycle Status:         {target_model.lifecycle_status.value.upper()}")
                print(f"  Default Ranking Eligible: {'YES' if registry.is_model_eligible(target_model.model_id) else 'NO (Excluded by lifecycle/provenance policy)'}")
                print(f"  Context Window:           {target_model.context_window_tokens:,} tokens")
                print(f"  Max Output Tokens:        {target_model.max_output_tokens:,} tokens")
                if target_model.pricing.input_cost_per_m is not None:
                    print(f"  Pricing:                  ${target_model.pricing.input_cost_per_m:.2f} in / ${target_model.pricing.output_cost_per_m:.2f} out per 1M tokens ({target_model.pricing.currency})")
                    print(f"  Pricing Effective Date:   {target_model.pricing.pricing_effective_date} (Audited: {target_model.pricing.pricing_verification_date})")
                    print(f"  Pricing Status:           {'STALE' if target_model.pricing.is_stale else 'KNOWN & CURRENT'}")
                else:
                    print(f"  Pricing:                  UNKNOWN / UNVERIFIED (Penalized; never treated as free)")
                print(f"  Local Tokenizer Adapter:  {target_model.tokenizer_name}")
                adapter = get_tokenizer_adapter(target_model.model_id)
                tok_info = adapter.count_tokens("Test")
                print(f"  Token Count Method:       {tok_info.token_count_method} (Confidence: {tok_info.token_count_confidence:.2f})")
                print(f"  Token Count Disclaimer:   {tok_info.token_count_disclaimer}")
                print(f"  Capabilities:             {', '.join(target_model.capabilities)}")
                print(f"  Key Strengths:            {'; '.join(target_model.strengths)}")
                print(f"  Description:              {target_model.description}")
                print(f"  Documentation URL:        {target_model.source_url}")
                print(f"  Source Verification Date: {target_model.verification_date}")
                print(f"  Last Audit Date:          {target_model.last_audit_date}")
                unv = getattr(target_model, "unverified_fields", [])
                print(f"  Unverified Fields:        {', '.join(unv) if unv else 'None (All critical fields officially verified)'}")
                print("=" * 80)

                try:
                    input(f"\n{colors.CYAN}Press [Enter] to return to model list...{colors.RESET}")
                except (KeyboardInterrupt, EOFError):
                    pass

        # -------------------------------------------------------------------
        # Category 2: IDE Coding Assistants
        # -------------------------------------------------------------------
        elif choice == "2":
            ides = registry.list_ides()
            print("\n" + "-" * 80)
            print(f"{colors.BOLD}VERIFIED IDE CODING ASSISTANTS ({len(ides)} products):{colors.RESET}")
            print("-" * 80)
            for idx, ide in enumerate(ides, 1):
                print(f" [{idx}] {ide.product_id:<20} {ide.display_name:<20} {ide.vendor:<18} {ide.pricing_tier_summary}")
            print("-" * 80)

            try:
                sub = input(f"{colors.CYAN}Enter product # (1-{len(ides)}) or ID to inspect [Enter to return]:{colors.RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                continue

            if not sub:
                continue

            target_ide: Optional[IDEProductMetadata] = None
            if sub.isdigit():
                num = int(sub)
                if 1 <= num <= len(ides):
                    target_ide = ides[num - 1]
            else:
                target_ide = registry.get_ide(sub)

            if not target_ide:
                print(f"{colors.RED}[!] IDE product '{sub}' not found.{colors.RESET}")
                continue

            print("\n" + "=" * 80)
            print(f"{colors.BOLD}{colors.CYAN}IDE PRODUCT INSPECTION: {target_ide.product_id}{colors.RESET}")
            print("=" * 80)
            print(f"  Display Name:           {target_ide.display_name}")
            print(f"  Vendor:                 {target_ide.vendor}")
            print(f"  Availability:           {target_ide.availability.value.upper()}")
            print(f"  Supported OS:           {', '.join(target_ide.supported_os)}")
            print(f"  Editor Integration:     {', '.join(target_ide.editor_integration)}")
            print(f"  Supported Models:       {', '.join(target_ide.supported_models)}")
            print(f"  Key Capabilities:       {'; '.join(target_ide.key_capabilities)}")
            print(f"  Context Features:       {'; '.join(target_ide.context_features)}")
            print(f"  Execution Capabilities: {'; '.join(target_ide.execution_capabilities)}")
            print(f"  Pricing Tier Summary:   {target_ide.pricing_tier_summary}")
            print(f"  Free Tier:              {target_ide.free_tier}")
            print(f"  Paid Tiers:             {', '.join(target_ide.paid_tiers)}")
            print(f"  Privacy Statement:      {target_ide.privacy_statement}")
            print(f"  Documentation URL:      {target_ide.source_url}")
            print(f"  Verification Date:      {target_ide.verification_date} (Audited: {target_ide.last_audit_date})")
            print("=" * 80)

            try:
                input(f"\n{colors.CYAN}Press [Enter] to return...{colors.RESET}")
            except (KeyboardInterrupt, EOFError):
                pass

        # -------------------------------------------------------------------
        # Category 3: AI App Builders
        # -------------------------------------------------------------------
        elif choice == "3":
            builders = registry.list_app_builders()
            print("\n" + "-" * 80)
            print(f"{colors.BOLD}VERIFIED AI APP BUILDERS ({len(builders)} platforms):{colors.RESET}")
            print("-" * 80)
            for idx, b in enumerate(builders, 1):
                print(f" [{idx}] {b.product_id:<16} {b.display_name:<18} {b.vendor:<16} {b.pricing_tier_summary}")
            print("-" * 80)

            try:
                sub = input(f"{colors.CYAN}Enter platform # (1-{len(builders)}) or ID to inspect [Enter to return]:{colors.RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                continue

            if not sub:
                continue

            target_builder: Optional[AppBuilderMetadata] = None
            if sub.isdigit():
                num = int(sub)
                if 1 <= num <= len(builders):
                    target_builder = builders[num - 1]
            else:
                target_builder = registry.get_app_builder(sub)

            if not target_builder:
                print(f"{colors.RED}[!] App builder '{sub}' not found.{colors.RESET}")
                continue

            print("\n" + "=" * 80)
            print(f"{colors.BOLD}{colors.CYAN}APP BUILDER INSPECTION: {target_builder.product_id}{colors.RESET}")
            print("=" * 80)
            print(f"  Display Name:           {target_builder.display_name}")
            print(f"  Vendor:                 {target_builder.vendor}")
            print(f"  Availability:           {target_builder.availability.value.upper()}")
            print(f"  Primary Stacks:         {', '.join(target_builder.primary_stacks)}")
            print(f"  Supported Backends:     {', '.join(target_builder.supported_backends)}")
            print(f"  Database & Auth:        {', '.join(target_builder.database_auth_support)}")
            print(f"  Deployment Options:     {', '.join(target_builder.deployment_options)}")
            print(f"  GitHub Integration:     {target_builder.github_integration}")
            print(f"  Source Code Export:     {target_builder.source_code_export}")
            print(f"  Key Capabilities:       {'; '.join(target_builder.key_capabilities)}")
            print(f"  Documented Limitations: {'; '.join(target_builder.documented_limitations)}")
            print(f"  Pricing Tier Summary:   {target_builder.pricing_tier_summary}")
            print(f"  Documentation URL:      {target_builder.source_url}")
            print(f"  Verification Date:      {target_builder.verification_date} (Audited: {target_builder.last_audit_date})")
            print("=" * 80)

            try:
                input(f"\n{colors.CYAN}Press [Enter] to return...{colors.RESET}")
            except (KeyboardInterrupt, EOFError):
                pass


# ===========================================================================
# Option 7: Text File Analysis
# ===========================================================================

def cli_file_analysis(colors: Colors) -> None:
    """Safely loads a local text file and offers security, comparison, or full workflow."""
    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}7. ANALYSE PROMPT FROM FILE{colors.RESET}")
    print("=" * 80)

    try:
        path_input = input(f"{colors.CYAN}Enter local path to text file (or 'c' to cancel):{colors.RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if path_input.lower() in {"c", "cancel", ""}:
        return

    file_path = Path(path_input).expanduser().resolve()

    # 1. Path existence and regular file check
    if not file_path.exists():
        print(f"{colors.RED}[!] Error: File does not exist: {file_path}{colors.RESET}")
        return
    if not file_path.is_file():
        print(f"{colors.RED}[!] Error: Path is not a regular file: {file_path}{colors.RESET}")
        return

    # 2. Readability check
    if not os.access(file_path, os.R_OK):
        print(f"{colors.RED}[!] Error: File is not readable (check permissions): {file_path}{colors.RESET}")
        return

    # 3. File size check (2 MB limit)
    MAX_FILE_BYTES = 2 * 1024 * 1024
    file_size = file_path.stat().st_size
    if file_size > MAX_FILE_BYTES:
        print(f"{colors.RED}[!] Error: File size ({file_size} bytes) exceeds maximum allowable limit (2 MB).{colors.RESET}")
        return

    # 4. UTF-8 Encoding check
    try:
        content = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"{colors.RED}[!] Error: File could not be decoded as UTF-8 text (binary or unsupported encoding).{colors.RESET}")
        return
    except Exception as e:
        print(f"{colors.RED}[!] Error reading file: {e}{colors.RESET}")
        return

    # 5. Empty file check
    if not content.strip():
        print(f"{colors.RED}[!] Error: File is empty or contains only whitespace: {file_path}{colors.RESET}")
        return

    # 6. Sensitive data pre-scan warning
    secret_findings_count = 0
    for pat in PATTERNS:
        matches = list(pat["regex"].finditer(content))
        secret_findings_count += len(matches)

    if secret_findings_count > 0:
        print(f"\n{colors.YELLOW}[!] CAUTION: File appears to contain detected credentials/secrets ({secret_findings_count} match(es)).{colors.RESET}")
        print("    PromptShield AI will mask secrets in reports, but confirm you want to proceed.")
        try:
            confirm = input(f"{colors.CYAN}Proceed with analysis of this file? (y/N):{colors.RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            return
        if confirm not in {"y", "yes"}:
            print(f"{colors.YELLOW}[i] Operation cancelled by user.{colors.RESET}")
            return

    # 7. Action Selection for Loaded Content
    print(f"\n{colors.GREEN}✓ File loaded successfully:{colors.RESET} {file_path.name}")
    print(f"  Length: {len(content)} chars | {len(content.split())} words | {len(content.splitlines())} lines")
    print("\nSelect action for loaded file content:")
    print("  [1] Run complete end-to-end workflow (Security + Recommendation + Optimization)")
    print("  [2] Standalone security analysis")
    print("  [3] Compare foundation models for this task")
    print("  [4] Compare IDE coding assistants for this task")
    print("  [5] Compare AI app builders for this task")
    print("  [0] Cancel and return to main menu")

    try:
        action = input(f"{colors.CYAN}Select action (0-5):{colors.RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if action == "1":
        cli_complete_end_to_end_workflow(colors, preloaded_prompt=content)
    elif action == "2":
        cli_prompt_security_analysis(colors, preloaded_prompt=content)
    elif action == "3":
        cli_compare_foundation_models(colors, preloaded_prompt=content)
    elif action == "4":
        cli_compare_ide_assistants(colors, preloaded_prompt=content)
    elif action == "5":
        cli_compare_app_builders(colors, preloaded_prompt=content)
    else:
        print(f"{colors.YELLOW}[i] Operation cancelled.{colors.RESET}")



# ===========================================================================
# Option 8: View Help and Limitations
# ===========================================================================

def cli_view_help_and_limitations(colors: Colors) -> None:
    """Displays platform guide, technical methodologies, and operational constraints."""
    print("\n" + "=" * 80)
    print(f"{colors.BOLD}{colors.CYAN}8. PROMPTSHIELD AI — HELP & ARCHITECTURAL LIMITATIONS{colors.RESET}")
    print("=" * 80)
    print(f"""
{colors.BOLD}PLATFORM ARCHITECTURE & WORKING RULES:{colors.RESET}
  1. 100% OFFLINE EXECUTION:
     PromptShield AI NEVER calls OpenAI, Google, Anthropic, xAI, or any external
     LLM generation APIs. No API keys are required or stored. Zero telemetry.

  2. SECURITY CLASSIFIERS & DETECTORS:
     • Prompt Security Model: Calibrated binary classifier trained on the MPDD dataset
       to detect adversarial malice, prompt injections, and jailbreaks.
     • Application Risk Model: Multi-label classifier evaluating 15 architectural
       attack surfaces (SQLi, Auth weakness, SSRF, IDOR, etc.) implied by features.
     • Security Controls Extractor: Recognizes declared security defenses (Argon2id,
       CSP, RBAC, etc.) and explicit negations (e.g. 'no database').
     • Sensitive Data Detector: Deterministic regex heuristics that detect API keys,
       passwords, and tokens, automatically masking them in displays.

  3. MULTI-MODEL COMPARISON (FOUNDATION MODELS):
     • Multi-criteria ranking via Weighted Sum Model (WSM) and TOPSIS.
     • Token counting: Exact via official local 'tiktoken' for OpenAI models;
       calibrated offline SentencePiece/BPE estimates for Gemini, Claude, Grok, DeepSeek.
     • Pricing & Missing Data Policy: Missing or unverified pricing receives maximum
       cost penalties and is NEVER assumed free or lowest cost.
     • Recommendation Score Disclaimer: Scores represent relative multi-criteria trade-offs
       [0.0, 1.0], NOT measured answer benchmark quality, latency, or model intelligence.

  4. PRODUCT CATEGORY ISOLATION:
     • Foundation Models, IDE Coding Assistants, and AI App Builders are evaluated
       in separate categories with domain-appropriate criteria.
     • IDEs and App Builders use subscription/credit pricing, NOT per-token rates.

  5. INTERACTIVE TERMINAL SHORTCUTS:
     • In multiline text entry, type 'END' on a line by itself to finish.
     • In any menu or prompt, type 'cancel' or 'c' to safely return.
     • Press Ctrl+C or Ctrl+D (EOF) at any time to abort without stack traces.
""")
    print("=" * 80)

    try:
        input(f"{colors.CYAN}Press [Enter] to return to main menu...{colors.RESET}")
    except (KeyboardInterrupt, EOFError):
        pass


# ===========================================================================
# Main Interactive Menu Loop
# ===========================================================================

def run_interactive_cli(colors: Colors) -> None:
    """
    Runs the main interactive workspace loop for PromptShield AI.
    The menu remains available after each completed action until option 0 is chosen.
    """
    print(get_banner(colors))

    while True:
        print("\n" + "=" * 80)
        print(f"{colors.BOLD}PROMPTSHIELD AI{colors.RESET}")
        print("Local Prompt Security & Model Recommendation Workspace")
        print("=" * 80)
        print("  1. Analyse, compare and optimize a prompt (Complete Workflow)")
        print("  2. Standalone security analysis")
        print("  3. Compare foundation models for a task")
        print("  4. Compare IDE coding assistants")
        print("  5. Compare AI app builders")
        print("  6. Inspect model/product catalogue")
        print("  7. Analyse a prompt from a file")
        print("  8. View help and limitations")
        print("  0. Exit")
        print("=" * 80)

        try:
            choice = input(f"{colors.CYAN}Select an option (0-8):{colors.RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{colors.CYAN}Exiting PromptShield AI. Goodbye!{colors.RESET}\n")
            sys.exit(0)

        if choice in {"1", "flow", "workflow", "optimize", "complete"}:
            cli_complete_end_to_end_workflow(colors)
        elif choice in {"2", "analyse", "security"}:
            cli_prompt_security_analysis(colors)
        elif choice in {"3", "compare", "models"}:
            cli_compare_foundation_models(colors)
        elif choice in {"4", "ide", "ides"}:
            cli_compare_ide_assistants(colors)
        elif choice in {"5", "app", "builder", "builders"}:
            cli_compare_app_builders(colors)
        elif choice in {"6", "inspect", "catalogue"}:
            cli_inspect_catalogue(colors)
        elif choice in {"7", "file"}:
            cli_file_analysis(colors)
        elif choice in {"8", "help"}:
            cli_view_help_and_limitations(colors)
        elif choice in {"0", "exit", "quit", "q"}:
            print(f"\n{colors.CYAN}Thank you for using PromptShield AI. Goodbye!{colors.RESET}\n")
            sys.exit(0)
        else:
            print(f"{colors.RED}[!] Invalid choice '{choice}'. Please select a number between 0 and 8.{colors.RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="PromptShield AI — Local Prompt Security & Model Recommendation Workspace."
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        default=None,
        help="Analyze a single prompt directly in non-interactive mode."
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        default=None,
        help="Path to a text file containing the prompt to analyze."
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color output."
    )

    args = parser.parse_args()
    colors = Colors(enabled=(not args.no_color and is_color_supported()))

    # Direct file input (non-interactive mode)
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"{colors.RED}Error: File not found: {file_path}{colors.RESET}", file=sys.stderr)
            sys.exit(1)
        prompt = file_path.read_text(encoding="utf-8").strip()
        if not prompt:
            print(f"{colors.RED}Error: File is empty: {file_path}{colors.RESET}", file=sys.stderr)
            sys.exit(1)

        print(get_banner(colors))
        print(f"Analyzing prompt from file: {file_path}...\n")
        result = analyze_prompt(prompt, analysis_mode="both")
        print(format_security_report(prompt, result, colors=colors))
        sys.exit(0)

    # Direct string input (non-interactive mode)
    if args.prompt is not None:
        prompt = args.prompt.strip()
        if not prompt:
            print(f"{colors.RED}Error: Provided prompt is empty or contains only whitespace.{colors.RESET}", file=sys.stderr)
            sys.exit(1)

        print(get_banner(colors))
        print("Analyzing provided prompt...\n")
        result = analyze_prompt(prompt, analysis_mode="both")
        print(format_security_report(prompt, result, colors=colors))
        sys.exit(0)

    # Interactive workspace mode
    run_interactive_cli(colors)


if __name__ == "__main__":
    main()
