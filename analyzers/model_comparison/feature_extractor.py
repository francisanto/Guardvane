"""
PromptShield AI — Prompt Feature Extractor.
==========================================
Extracts quantitative and structural features from raw user prompts:
- Length attributes (chars, words, lines)
- Code proportion (heuristic syntax and block analysis)
- Structural complexity indicators
- Security sensitivity (detecting API keys, secrets, architectural vulnerabilities)
- Expected response length estimation (based on prompt intent and constraints)
"""

from dataclasses import dataclass
import re
from typing import Dict, List, Optional


@dataclass
class PromptFeatures:
    char_length: int
    word_count: int
    line_count: int
    code_proportion: float
    has_code_block: bool
    complexity_score: float
    technical_keyword_density: float
    security_sensitivity: float
    estimated_output_tokens: int
    detected_indicators: List[str]


class PromptFeatureExtractor:
    """Extracts structural and semantic attributes from prompt text."""

    CODE_SYNTAX_PATTERNS = [
        r"^\s*(def|class|function|var|let|const|package)\b",
        r"^\s*(import|from)\s+[a-zA-Z0-9_.]+(\s+import)?",
        r"^\s*(public|private|protected)\s+(static\s+)?(void|int|string|bool)",
        r"[a-zA-Z0-9_]+\s*\([^)]*\)\s*[{;:]",
        r"(==|!=|<=|>=|=>|->|\+\+|--|&&|\|\|)",
        r"(SELECT\s+[\s\S]*?\s+FROM\b|INSERT\s+INTO\b|UPDATE\s+[\s\S]*?\s+SET\b)",
        r"<\/?(div|span|script|template|button|input|form|table|a|p)\b",
        r"[{};]\s*$"
    ]

    COMPLEXITY_TRIGGERS = [
        r"\b(multi-step|architecture|distributed|asynchronous|concurrency|benchmark|tradeoffs?|optimize|scalab(le|ility)|caching|microservices|pipeline)\b",
        r"\b(edge cases?|fault tolerance|mathematical proof|formal verification|invariant|deadlock)\b",
        r"\b(compar(e|ison)|pros and cons|step[- ]by[- ]step|system design)\b"
    ]

    SECURITY_PATTERNS = [
        r"\b(sql injection|sqli|xss|csrf|ssrf|remote code execution|rce|buffer overflow)\b",
        r"\b(jwt|oauth|authentication|authorization|rbac|aes|rsa|encryption|decryption|hash|bcrypt)\b",
        r"\b(api[_-]?key|secret|credential|bearer\s+[a-zA-Z0-9_\-\.]{15,}|private key|password)\b",
        r"\b(vulnerability|exploit|penetration test|zero-day|cve-\d{4}-\d+|threat model)\b"
    ]

    TECHNICAL_PATTERNS = [
        r"\b(function|class|method|interface|struct|endpoint|schema|database|query|table|async|await)\b",
        r"\b(api|rest|graphql|docker|kubernetes|aws|azure|gcp|linux|git|json|yaml|xml)\b",
        r"\b(algorithm|array|hashmap|tree|graph|pointer|memory|thread|process|socket)\b"
    ]

    def extract_features(self, prompt: str) -> PromptFeatures:
        if not prompt or not prompt.strip():
            return PromptFeatures(
                char_length=0,
                word_count=0,
                line_count=0,
                code_proportion=0.0,
                has_code_block=False,
                complexity_score=0.0,
                technical_keyword_density=0.0,
                security_sensitivity=0.0,
                estimated_output_tokens=50,
                detected_indicators=[]
            )

        text = prompt.strip()
        char_len = len(text)
        words = text.split()
        word_count = len(words)
        lines = text.splitlines()
        line_count = len(lines)

        indicators = []

        # 1. Code proportion calculation
        fenced_blocks = re.findall(r"```[\s\S]*?```", text)
        has_fenced_block = bool(fenced_blocks)
        if has_fenced_block:
            indicators.append("contains_fenced_code_block")

        code_char_count = sum(len(b) for b in fenced_blocks)

        # Count lines with distinct programming syntax
        code_lines = 0
        for line in lines:
            line_str = line.strip()
            if any(re.search(pat, line_str, re.I) for pat in self.CODE_SYNTAX_PATTERNS):
                code_lines += 1

        if has_fenced_block:
            code_proportion = min(1.0, max(code_char_count / max(1, char_len), code_lines / max(1, line_count)))
        else:
            # If no fenced block, only treat as code-heavy if multiple code syntax lines exist
            if code_lines >= 2 or (line_count <= 2 and code_lines >= 1 and any(c in text for c in ["{", "}", ";", "=>", "()"])):
                code_proportion = min(0.90, (code_lines / max(1, line_count)) * 0.75)
            else:
                code_proportion = 0.0

        if code_proportion > 0.25:
            indicators.append("code_heavy")

        # 2. Technical keyword density
        tech_words = 0
        for pat in self.TECHNICAL_PATTERNS + self.SECURITY_PATTERNS:
            tech_words += len(re.findall(pat, text, re.I))
        technical_density = round(min(1.0, tech_words / max(1, word_count * 0.2)), 3)

        # 3. Complexity Score
        # Vocabulary richness (Type-Token Ratio)
        unique_words = len(set(w.lower() for w in words))
        ttr = unique_words / max(1, word_count)

        # Syntactic complexity: average sentence length and clause depth
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_len = word_count / max(1, len(sentences))

        # Complexity triggers
        complexity_hits = sum(len(re.findall(pat, text, re.I)) for pat in self.COMPLEXITY_TRIGGERS)
        complexity_factor = min(1.0, (complexity_hits * 0.18) + (technical_density * 0.32) + (avg_sentence_len / 40.0 * 0.25) + (min(word_count, 300) / 300.0 * 0.25))
        complexity_score = round(min(1.0, max(0.1, complexity_factor)), 3)
        if complexity_score > 0.6:
            indicators.append("high_structural_complexity")

        # 4. Security sensitivity
        sec_hits = 0
        for pat in self.SECURITY_PATTERNS:
            sec_hits += len(re.findall(pat, text, re.I))
        # High sensitivity if API keys or credentials pattern matches
        try:
            from analyzers.sensitive_data_detector import detect_sensitive_data
            sens_res = detect_sensitive_data(text)
            cred_match = sens_res.get("detected", False)
        except Exception:
            cred_match = False

        if not cred_match:
            cred_match = bool(re.search(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]", text))

        sec_score = min(1.0, (sec_hits * 0.2) + (0.5 if cred_match else 0.0))
        security_sensitivity = round(sec_score, 3)
        if cred_match:
            indicators.append("contains_sensitive_credentials")
        if security_sensitivity > 0.3:
            indicators.append("security_sensitive")

        # 5. Expected response length estimation
        # Heuristic based on prompt instructions
        is_concise = bool(re.search(r"\b(brief|concise|short|one-sentence|summary in 3 points|tldr)\b", text, re.I))
        is_extensive = bool(re.search(r"\b(comprehensive|complete implementation|full code|step-by-step|detailed architecture|entire)\b", text, re.I))

        if is_concise:
            base_tokens = 120
        elif is_extensive:
            base_tokens = 900
        elif code_proportion > 0.3:
            base_tokens = 550  # Code explanations / implementations typically generate 400-700 tokens
        else:
            base_tokens = 350

        # Adjust slightly for prompt length
        estimated_output_tokens = min(4096, max(80, int(base_tokens + (word_count * 0.5))))

        return PromptFeatures(
            char_length=char_len,
            word_count=word_count,
            line_count=line_count,
            code_proportion=round(code_proportion, 3),
            has_code_block=has_fenced_block,
            complexity_score=complexity_score,
            technical_keyword_density=technical_density,
            security_sensitivity=security_sensitivity,
            estimated_output_tokens=estimated_output_tokens,
            detected_indicators=indicators
        )


# Singleton instance
feature_extractor = PromptFeatureExtractor()
