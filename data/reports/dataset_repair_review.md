# PromptShield AI — Dataset Repair & Validation Review Report

**Generated:** 2026-10-25T11:10:25.288746+00:00  
**Platform:** PromptShield AI (Intelligent Prompt Analysis, Security Assessment & Multi-Model Optimization)  
**Stage:** Controlled Dataset Repair & Validation (Pre-Merge Stage)  
**Status:** Proposals Generated — Original Datasets Preserved  

---

## Executive Summary

Following the baseline dataset quality audit, controlled repair proposals have been formulated across all three project datasets. In strict accordance with project safety rules, **no original dataset files, trained model artifacts, or training scripts have been altered or overwritten**. All proposed additions and corrections are isolated in `data/proposed/` for formal review prior to any merge.

### Key Repair Deliverables
1. **`data/proposed/path_traversal_examples.csv`**: 25 realistic, diverse application requirement prompts addressing the 0-positive unlearnable label defect.
2. **`data/proposed/mpdd_label_corrections.csv`**: 3,283 candidate label corrections for `mpdd_clean.csv`, distinguishing benign news/code from a genuine adversarial jailbreak (Row 10632).
3. **`data/proposed/web_payload_corrections.md`**: Investigation and exact fix for the missing payload in row 238 (`csrf-039`), severity conflict resolution, and duplicate payload taxonomy.

---

## 1. Application-Risk Dataset: Path Traversal Remediation

### Problem Summary
The application security risk dataset (`data/security_risk_dataset.csv`, 296 records) contained **0 positive training examples** for `path_traversal`. As a result, the `OneVsRestClassifier` pipeline in `ml/train_security_model.py` issued warnings during training and defaulted to predicting 0 for all future prompts, rendering PromptShield AI completely incapable of assessing directory traversal attack surfaces.

### Proposed Additions Overview
- **File Created:** `data/proposed/path_traversal_examples.csv`
- **Total Proposed Records:** 25
- **Vulnerable Scenarios (`path_traversal = 1`):** 15 records
- **Secured / Safe Scenarios (`path_traversal = 0`):** 10 records
- **Schema Conformance:** Exact 23-column match with `data/security_risk_dataset.csv`.

### Representation of Vulnerable Scenarios (`path_traversal = 1`)
Covers diverse, realistic enterprise requirements with unvalidated user-controlled paths:
1. **Direct file download query parameters** (e.g., `?filename=report.pdf`, `?log_path=server.log`).
2. **Dynamic template and view inclusion** (e.g., `?template_file=dashboard.html`).
3. **Zip Slip archive extraction** (unzipping archives directly without checking target path traversal).
4. **AI Agent local file reading** (AI assistant reading arbitrary file paths provided by users).
5. **Static asset and audio streaming** (parameterized track and documentation loading).

### Representation of Secured Scenarios (`path_traversal = 0`)
Covers application requirements involving file handling that are explicitly secured:
1. **UUID/Database object mapping** (files stored in private S3/GCS buckets retrieved strictly by UUID with no filesystem path access).
2. **Strict whitelist dictionaries** (templates selected from hardcoded dictionary lookups).
3. **Path canonicalization and sandboxing** (verifying that resolved paths stay strictly within an ephemeral temp folder or public web root).
4. **In-memory generation** (generating PDFs and reports in memory without disk writes).

### Impact on Class Balance
| Risk Label | Current Positives ($N=296$) | Proposed Additions | Projected Positives ($N=321$) | Projected Positive Ratio |
| :--- | :---: | :---: | :---: | :---: |
| `path_traversal` | **0** (0.00%) | +15 | **15** | **4.67%** |
| `sensitive_data` | 35 (11.82%) | +14 | 49 | 15.26% |
| `idor` | 28 (9.46%) | +7 | 35 | 10.90% |
| `file_upload` | 30 (10.14%) | +4 | 34 | 10.59% |
| `authz_weakness` | 33 (11.15%) | +3 | 36 | 11.21% |

- **Diversity Verification:** Maximum Jaccard similarity between any proposed prompt and the 296 existing prompts is **0.300** (zero near-duplicates, zero exact duplicates).

---

## 2. Prompt-Security Dataset: Controlled Label Noise Remediation

### Problem Summary
In `data/processed/mpdd_clean.csv` (39,116 records), **3,284 records** in class `1` (Malicious) are non-malicious tasks: 3,060 AG News categorization articles and 224 ordinary StackOverflow programming questions. The existing training pipeline in `ml/train_prompt_security_model.py` intercepted these on-the-fly using regex to flip them in memory, leaving the on-disk file corrupted.

### Critical Finding: The Neuromancer Jailbreak (Row 10632)
> **CRITICAL SAFETY FINDING:** Deep inspection of the candidate rows revealed that **Row 10632** is an actual adversarial jailbreak attack prompt! It employs roleplay persona framing (`{{Neuromancer☠}}`), mentions illicit chemical synthesis, and contains weaponized XSS/trojan JavaScript code. Because this weaponized payload contained `function(` and `console.log('YOU HAVE BEEN TROJANED!!!')`, the naive training script regex blindly relabeled Row 10632 to Benign (`0`).

- **Proposed Action:** Row 10632 is explicitly preserved as **`isMalicious = 1`** (`proposed_isMalicious = 1`) in `data/proposed/mpdd_label_corrections.csv` with category `adversarial_jailbreak_misclassified_as_so_code` and `confidence = high`.

### Summary of Proposed Label Corrections
- **Total Candidates Processed:** 3283
- **Proposed to Flip to Benign (`0`):** 3282
- **Proposed to Retain as Malicious (`1`):** 1 (Row 10632)

### Category Breakdown
- **`ag_news_standard`:** 2,896 records
- **`stackoverflow_frontend_code`:** 223 records
- **`ag_news_security_topic`:** 163 records
- **`adversarial_jailbreak_misclassified_as_so_code`:** 1 records

### Confidence Breakdown
- **`high`:** 3,120 records
- **`medium`:** 163 records

### Ambiguous / Security-Adjacent Cases for Manual Review (163 Records)
163 AG News categorization tasks report on real-world security events (e.g. Sasser worm, Bali bombings, Microsoft JPEG exploits). These prompts have been flagged with **`confidence = medium`** so human reviewers can verify that the surrounding text does not contain covert adversarial prompts.

---

## 3. Web Security Payloads: Ingestion Bug & Severity Alignment

### Row 238 (`csrf-039`) Ingestion Fix
- **Problem:** Null payload in CSV due to omitted `payload` key in source JSON `data/raw/web_security_payloads_clean.json`.
- **Resolution:** Extract payload string from contaminated description field:
  - `description`: `CSRF using script with async/await fetch`
  - `payload`: `<script>(async()=>{await fetch('https://target.com/api/async',{method:'POST',credentials:'include',body:'action=async'});})();</script>`

### Conflicting Severity Resolutions
1. **`; echo injected` (Command Injection):**
   - Rows: `cmdinj-014` (`medium`), `cmdinj-024` (`medium`), `cmdinj-092` (`high`).
   - Proposed resolution: Align `cmdinj-092` to `medium` because plain echo injection is a non-destructive POC command.
2. **SVG CSRF Script targeting `/api/delete`:**
   - Rows: `csrf-009` (`high`), `csrf-025` (`critical`).
   - Proposed resolution: Align both to `high` based on standard CVSS scoring for authenticated state deletion.

---

## 4. Remaining Uncertainties & Expected Impact

### Expected Model Impact Upon Merge
1. **Application Risk Model:**
   - Once the 25 path traversal examples are merged, `OneVsRestClassifier` will successfully train a decision boundary for `path_traversal` without warnings.
   - Path traversal precision and recall will become measurable on held-out test splits.
2. **Prompt Security Model:**
   - Relabeling the 3,282 benign news and coding examples will eliminate false-positive training signal for standard text classification and UI code.
   - Removing the training script's in-memory regex will prevent dangerous misclassification of sophisticated jailbreaks like Row 10632.

### Manual Decisions Required Prior to Merge
1. **Review and approve the 163 security-adjacent AG News prompts** in `data/proposed/mpdd_label_corrections.csv`.
2. **Approve the proposed 25 path traversal examples** in `data/proposed/path_traversal_examples.csv`.
3. **Decide on web payload deduplication strategy**: whether to prune the 45 redundant payloads or retain them for regression test suites.
