"""
Security Controls and Negation Extractor for PromptShield AI.
Extracts explicitly declared security controls, architectural defenses,
and feature negations from software specification prompts.
"""

import re
from typing import Any, Dict, List


CONTROL_PATTERNS: List[Dict[str, Any]] = [
    {
        "id": "password_hashing",
        "name": "Password Hashing & Key Derivation",
        "category": "Authentication",
        "associated_risks": ["auth_weakness"],
        "regex": re.compile(
            r"\b(argon2(?:id)?|bcrypt|pbkdf2|scrypt|salted password|password[- ]hashing)\b",
            re.IGNORECASE
        ),
        "description": "Cryptographically secure password hashing (Argon2id, bcrypt, PBKDF2, scrypt)."
    },
    {
        "id": "mfa",
        "name": "Multi-Factor Authentication (MFA)",
        "category": "Authentication",
        "associated_risks": ["auth_weakness"],
        "regex": re.compile(
            r"\b(mfa|2fa|two[- ]factor|multi[- ]factor|totp|authenticator app|sms otp)\b",
            re.IGNORECASE
        ),
        "description": "Secondary authentication factor required for account access."
    },
    {
        "id": "rate_limiting",
        "name": "Rate Limiting & Anti-Brute-Force",
        "category": "Abuse Prevention",
        "associated_risks": ["auth_weakness", "model_extraction"],
        "regex": re.compile(
            r"\b(rate[- ]limit(?:ing)?|throttl(?:ing|e)|request throttling|account lockout|brute[- ]force protection)\b",
            re.IGNORECASE
        ),
        "description": "Request throttling or lockout mechanisms to prevent brute-forcing and systematic scraping."
    },
    {
        "id": "secure_sessions",
        "name": "Secure Session & Token Management",
        "category": "Session Management",
        "associated_risks": ["auth_weakness", "csrf"],
        "regex": re.compile(
            r"\b(secure session(?:s)?|httponly|samesite|session rotation|session invalidation|jwt verification|token expiration)\b",
            re.IGNORECASE
        ),
        "description": "Hardened session flags (HttpOnly, SameSite) and cryptographically verified tokens."
    },
    {
        "id": "authorization_checks",
        "name": "Granular Authorization & RBAC",
        "category": "Access Control",
        "associated_risks": ["authz_weakness", "idor"],
        "regex": re.compile(
            r"\b(role[- ]based access control|rbac|abac|authorization checks?|permission checks?|least privilege|access control list|acl)\b",
            re.IGNORECASE
        ),
        "description": "Centralized access control enforcing permissions on every protected resource."
    },
    {
        "id": "parameterized_queries",
        "name": "Parameterized Queries & Prepared Statements",
        "category": "Database Security",
        "associated_risks": ["sqli"],
        "regex": re.compile(
            r"\b(parameterized quer(?:y|ies)|prepared statements?|sqlalchemy|orm|query parameterization|parameter binding|avoid sql concatenation)\b",
            re.IGNORECASE
        ),
        "description": "Separation of SQL query structure from dynamic user inputs."
    },
    {
        "id": "output_encoding",
        "name": "Contextual Output Encoding & CSP",
        "category": "Web Security",
        "associated_risks": ["xss"],
        "regex": re.compile(
            r"\b(content security policy|csp|output (?:encoding|escaping)|html (?:encoding|escaping)|input sanitization|dompurify|xss filter)\b",
            re.IGNORECASE
        ),
        "description": "Context-aware HTML escaping and Content Security Policy headers to stop client-side execution."
    },
    {
        "id": "anti_csrf",
        "name": "Anti-CSRF Tokens",
        "category": "Web Security",
        "associated_risks": ["csrf"],
        "regex": re.compile(
            r"\b(anti[- ]csrf|csrf token(?:s)?|csrf protection|synchronizer token)\b",
            re.IGNORECASE
        ),
        "description": "Cryptographic tokens verifying that requests originate from legitimate application sessions."
    },
    {
        "id": "file_validation",
        "name": "Strict File Upload Validation & Isolated Storage",
        "category": "Storage Security",
        "associated_risks": ["file_upload", "path_traversal"],
        "regex": re.compile(
            r"\b(magic bytes|mime[- ]type validation|file size limit(?:s)?|restrict file size|outside (?:the )?web root|isolated (?:s3|storage|bucket)|randomize(?:d)? filenames?)\b",
            re.IGNORECASE
        ),
        "description": "Validation of binary signatures (magic bytes), size restrictions, and non-executable storage."
    },
    {
        "id": "network_egress_control",
        "name": "Outbound URL / Egress Validation",
        "category": "Network Security",
        "associated_risks": ["ssrf"],
        "regex": re.compile(
            r"\b(egress (?:allowlist|whitelist)|url (?:allowlist|whitelist)|destination whitelist|block internal ip(?:s)?|block private network(?:s)?)\b",
            re.IGNORECASE
        ),
        "description": "Restricting outbound network destinations and blocking requests to private RFC1918 subnets."
    },
    {
        "id": "data_encryption",
        "name": "Data Encryption at Rest & in Transit",
        "category": "Cryptography",
        "associated_risks": ["sensitive_data"],
        "regex": re.compile(
            r"\b(aes[- ]256|tls 1\.[23]|encrypt(?:ed|ion) at rest|encrypt(?:ed|ion) in transit|kms|secret manager)\b",
            re.IGNORECASE
        ),
        "description": "End-to-end cryptographic protection for sensitive records and tokens."
    }
]


NEGATION_TARGETS: List[Dict[str, Any]] = [
    {
        "feature": "login",
        "associated_risks": ["auth_weakness", "authz_weakness"],
        "regex": re.compile(r"\b(login|auth|authentication|session|sessions|account|user registration)\b", re.IGNORECASE),
        "description": "User authentication or login functionality is explicitly negated."
    },
    {
        "feature": "database",
        "associated_risks": ["sqli", "sensitive_data"],
        "regex": re.compile(r"\b(database|db|sql|postgresql|mysql|mongodb|storage|datastore)\b", re.IGNORECASE),
        "description": "Database or persistent data storage is explicitly negated."
    },
    {
        "feature": "file_upload",
        "associated_risks": ["file_upload", "path_traversal"],
        "regex": re.compile(r"\b(file\s*uploads?|uploading|attachments?|images?|file storage)\b", re.IGNORECASE),
        "description": "User file upload or attachment functionality is explicitly negated."
    },
    {
        "feature": "server_side_processing",
        "associated_risks": ["command_injection", "ssrf", "csrf", "sensitive_data"],
        "regex": re.compile(r"\b(server[- ]side(?: processing)?|backend|dynamic server|api processing)\b", re.IGNORECASE),
        "description": "Server-side computation or backend processing is explicitly negated."
    }
]

NEGATION_CLAUSE_REGEX = re.compile(
    r"\b(?:no|not need|does not need|without|does not require|neither|never need|free of)\s+([^.]+)",
    re.IGNORECASE
)


def extract_security_controls(prompt: str) -> List[Dict[str, Any]]:
    """
    Scans a prompt for explicitly declared security controls and defensive measures.
    Returns structured control objects.
    """
    if not prompt or not isinstance(prompt, str):
        return []

    found_controls: List[Dict[str, Any]] = []
    seen_ids = set()

    for ctrl in CONTROL_PATTERNS:
        match = ctrl["regex"].search(prompt)
        if match and ctrl["id"] not in seen_ids:
            seen_ids.add(ctrl["id"])
            found_controls.append({
                "id": ctrl["id"],
                "name": ctrl["name"],
                "category": ctrl["category"],
                "matched_text": match.group(0),
                "description": ctrl["description"],
                "mitigates_risks": ctrl["associated_risks"]
            })

    return found_controls


def extract_declared_negations(prompt: str) -> List[Dict[str, Any]]:
    """
    Identifies features explicitly negated in the prompt, including coordinate lists
    (e.g., 'does not need login, a database, file uploads, or server-side processing').
    Returns a list of negated feature objects and their associated risks to suppress.
    """
    if not prompt or not isinstance(prompt, str):
        return []

    negations: List[Dict[str, Any]] = []
    seen_features = set()

    # Find all negated clauses (e.g. 'does not need A, B, or C')
    matches = NEGATION_CLAUSE_REGEX.finditer(prompt)
    for clause_match in matches:
        clause_text = clause_match.group(1).lower()
        for target in NEGATION_TARGETS:
            if target["feature"] not in seen_features and target["regex"].search(clause_text):
                seen_features.add(target["feature"])
                negations.append({
                    "feature": target["feature"],
                    "matched_text": clause_match.group(0).strip(),
                    "description": target["description"],
                    "suppressed_risks": target["associated_risks"]
                })

    return negations


# Canonical aliases
extract_declared_security_controls = extract_security_controls
extract_feature_negations = extract_declared_negations


def filter_negated_risks(
    predicted_risks: List[str],
    negations: List[Dict[str, Any]]
) -> tuple:
    """
    Filters out predicted risks that are explicitly negated by user specifications.
    Returns (active_risks, suppressed_risks).
    """
    suppressed_set = set()
    for neg in negations:
        for r in neg.get("suppressed_risks", []):
            suppressed_set.add(r)

    active = [r for r in predicted_risks if r not in suppressed_set]
    suppressed = [r for r in predicted_risks if r in suppressed_set]
    return active, suppressed

