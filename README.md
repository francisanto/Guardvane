# backendprompt

# PromptShield AI
## Intelligent Prompt Analysis, Security Assessment and Multi-Model Optimization Platform

PromptShield AI is a security-focused platform designed to analyze prompts used with AI coding agents and generative AI systems.

The system is designed to identify security risks arising from:

1. The prompt itself
2. The application or system that the prompt asks an AI coding agent to build
3. Sensitive information contained in the prompt

The platform will eventually provide:

- Security risk analysis
- Prompt security analysis
- Sensitive-data detection
- Security recommendations
- Prompt optimization
- Token analysis
- Cost estimation
- Multi-model comparison
- Model ranking
- Multi-model optimization

---

# Current Project Stage

## 🔄 CURRENT STAGE: Prompt Security Model + Application Risk Baseline

The project currently has a baseline **Application Risk Prediction Model** and is now implementing a separate **Prompt Security Model** using the MPDD malicious-prompt dataset.

---

# Current Progress

| Component | Status |
|---|---|
| FastAPI backend | ✅ Complete |
| `/analyze` API | ✅ Complete |
| Unified Terminal CLI (`cli.py`) | ✅ Complete |
| Basic prompt analyzer orchestrator | ✅ Complete |
| Initial Application Risk dataset | ✅ Complete |
| Application Risk dataset validation | ✅ Complete |
| Application Risk baseline model | ✅ Complete |
| TF-IDF for Application Risk | ✅ Complete |
| Multi-label Logistic Regression | ✅ Complete |
| Application Risk prediction script | ✅ Complete |
| Application Risk error analysis | ✅ Complete |
| MPDD dataset acquisition | ✅ Complete |
| MPDD dataset inspection | ✅ Complete |
| MPDD preprocessing pipeline | ✅ Complete |
| MPDD cleaned dataset | ✅ Complete |
| Prompt Security Model | ✅ Complete |
| Prompt Security model training | ✅ Complete |
| Prompt Security evaluation | ✅ Complete |
| Prompt Security testing | ✅ Complete |
| Sensitive Data Detector | ✅ Complete |
| Security recommendations engine | ✅ Complete |
| Probability calibration | ⬜ |
| Context extraction | ⬜ |
| Improved Application Risk Engine | ⬜ |
| 30-risk Application Risk taxonomy | 🔄 Planned |
| Risk aggregation | ⬜ |
| Security explanations | ⬜ |
| Prompt Optimizer | ⬜ Planned |
| Token analysis | ✅ Complete (Exact tiktoken + Calibrated Gemini/Claude) |
| Cost estimation | ✅ Complete (Separated input & estimated output) |
| Model registry & lifecycle | ✅ Complete (Active, Deprecated, Retired, Preview) |
| Multi-model comparison | ✅ Complete (`/compare-models`) |
| Model ranking (WSM & TOPSIS) | ✅ Complete (Balanced, Cost, Quality, Long-Context) |
| Frontend integration | ⬜ Planned |

---

# 🚀 Terminal CLI Usage

PromptShield AI provides an interactive, unified Terminal Workspace suitable for local development, security audits, and live demonstrations (e.g., college project expos).

### Launching the Workspace

You can launch the CLI using any of the following commands:

```bash
# 1. Recommended launcher script (checks virtualenv and dependencies):
./run_cli.sh

# 2. As a Python module:
.venv/bin/python -m promptshield

# 3. Direct script execution:
.venv/bin/python cli.py
```

### Main Menu Options

When launched, the workspace presents an interactive main menu that persists across actions:

```text
================================================================================
PROMPTSHIELD AI
Local Prompt Security & Model Recommendation Workspace
================================================================================
  1. Analyse a prompt for security vulnerabilities
  2. Compare foundation models for a task
  3. Compare IDE coding assistants
  4. Compare AI app builders
  5. Inspect model/product catalogue
  6. Analyse a prompt from a file
  7. View help and limitations
  0. Exit
================================================================================
```

1. **Option 1 — Prompt Security Analysis**:
   - Evaluates adversarial malice, prompt injections, and jailbreaks (MPDD classifier).
   - Predicts 15 architectural attack surfaces (SQLi, Auth weakness, SSRF, IDOR, etc.).
   - Extracts explicitly stated security controls (Argon2id, CSP, RBAC, etc.) and negations.
   - Detects and automatically redacts exposed credentials and API keys.
   - Delivers actionable security remediation recommendations.
2. **Option 2 — Offline Foundation Model Comparison**:
   - 100% offline multi-model comparison using Weighted Sum Model (WSM) or TOPSIS.
   - Infers task categories locally (`task_classifier.py`).
   - Token counting: Exact via `tiktoken` for OpenAI, calibrated offline estimates for Gemini/Claude/Grok/DeepSeek.
   - Explains excluded models (preview, unverified, legacy) and penalizes missing pricing.
3. **Option 3 — IDE Coding Assistant Comparison**:
   - Compares verified IDE assistants (Cursor, Windsurf, GitHub Copilot, Google Antigravity).
   - Scored on multi-file agents, repo indexing, terminal execution, and privacy.
   - Uses subscription plans, NOT per-token foundation pricing.
4. **Option 4 — AI App Builder Comparison**:
   - Compares verified platforms (Vercel v0, Bolt.new, Lovable, Replit).
   - Scored on full-stack backend, database/auth support, UI quality, and code export.
   - Uses credit/subscription tiers, NOT per-token foundation pricing.
5. **Option 5 — Inspect Model/Product Catalogue**:
   - Displays exact verified IDs, context windows, pricing per 1M tokens, tokenizer types, and audit dates.
   - Lists unverified future releases (`gemini-2.5-pro`, `gemini-2.5-flash`) and previews (`grok-3`, `grok-3-mini`).
6. **Option 6 — Analyse a Prompt from a File**:
   - Safely ingests UTF-8 text files up to 2 MB (no execution, no file mutation).
   - Pre-scans for sensitive secrets and prompts for confirmation if keys are found.
   - Dispatches to security analysis or multi-model comparison.
7. **Option 7 — View Help and Limitations**:
   - Complete technical guide to classifiers, tokenizers, ranking formulas, and offline operation.
8. **Option 0 — Exit**:
   - Clean shutdown without tracebacks.

### Non-Interactive / Scripting Mode

You can also run single-shot evaluations using command-line arguments:

```bash
# Analyze a direct prompt string
.venv/bin/python cli.py --prompt "Build a web app with user login, password reset, and SQL database."

# Analyze a prompt from a file
.venv/bin/python cli.py --file path/to/prompt.txt

# Disable ANSI colors (useful for pipelines or plain log files)
.venv/bin/python cli.py --prompt "Build an API" --no-color
```

---

# Current ML Architecture

PromptShield uses two separate security prediction problems evaluated in parallel:

```text
                                  USER PROMPT
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
Prompt Security Model        Application Risk Model        Sensitive Data Detector
        │                              │                              │
        ▼                              ▼                              ▼
 "Is the prompt                "What risks could the         "Does the prompt contain
  malicious / jailbreak?"       requested application         hardcoded API keys,
                                potentially introduce?"       tokens, or passwords?"
        │                              │                              │
        ▼                              ▼                              ▼
  MPDD Dataset                  Contextual Dataset           Regex Pattern Heuristics
        │                              │                              │
        ▼                              ▼                              ▼
Binary Classification         Multi-Label Classification     Automated Secret Redaction
(Benign vs. Malicious)         (15 Risk Categories)           (Masked Output)
        │                              │                              │
        └──────────────────────────────┬──────────────────────────────┘
                                       │
                                       ▼
                       Unified Security Report & Recommendations
```

---

# 🧠 Local Model Comparison & Multi-Criteria Ranking Engine

PromptShield AI includes a **100% offline, local foundation model comparison and ranking engine** that evaluates prompts across leading LLMs (OpenAI GPT, Google Gemini, and Anthropic Claude) without requiring external provider generation API calls or API keys.

```text
                             USER PROMPT
                                  │
                                  ▼
               ┌─────────────────────────────────────┐
               │    FastAPI Validation & Router      │
               └──────────────────┬──────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │                                                 │
         ▼                                                 ▼
┌──────────────────────────────┐          ┌──────────────────────────────┐
│  Prompt Feature Extraction   │          │   Local Task Classifier      │
│  - Length (chars/words)      │          │   - TF-IDF + Multinomial NB  │
│  - Code proportion           │          │   - 6 domain categories      │
│  - Structural complexity     │          │   - Confidence scores        │
│  - Security sensitivity      │          │   - Uncertainty indicators   │
│  - Expected response length  │          │                              │
└──────────────┬───────────────┘          └──────────────┬───────────────┘
               │                                         │
               └──────────────────┬──────────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │     Model Registry Snapshot     │
                 │     - Active vs. Deprecated     │
                 │     - Verified 2025 Pricing     │
                 │     - Context limits (128k - 2M)│
                 └────────────────┬────────────────┘
                                  │
       ┌──────────────────────────┼──────────────────────────┐
       │                          │                          │
       ▼                          ▼                          ▼
┌──────────────┐           ┌──────────────┐           ┌──────────────┐
│ OpenAI BPE   │           │ Google 256k  │           │ Claude BPE   │
│ Exact Token  │           │ Calibrated   │           │ Calibrated   │
│ Count        │           │ Estimate     │           │ Estimate     │
└──────┬───────┘           └──────┬───────┘           └──────┬───────┘
       │                          │                          │
       └──────────────────────────┼──────────────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │     Cost Breakdown Calculator   │
                 │     - Separated input cost      │
                 │     - Estimated output cost     │
                 │     - Total estimated cost      │
                 └────────────────┬────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │   Architectural Suitability     │
                 │   - Task alignment              │
                 │   - Engineering/code aptitude   │
                 │   - Complexity tier fit         │
                 │   - Context headroom            │
                 └────────────────┬────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │ Multi-Criteria Ranking Engine   │
                 │ - Weighted Sum Model (WSM)      │
                 │ - TOPSIS Euclidean Distance     │
                 │ - Presets (Balanced, Cost,      │
                 │   Quality, Long-Context)        │
                 └────────────────┬────────────────┘
                                  │
                                  ▼
                 ┌─────────────────────────────────┐
                 │ Transparent Response & Rationale│
                 │ - Evidenced explanations        │
                 │ - Clear provenance declarations │
                 │ - No fabricated metrics         │
                 └─────────────────────────────────┘
```

### 1. Token Counting & Provenance Disclosures

| Provider | Adapter Engine | Accuracy | Provenance Disclosure |
|---|---|---|---|
| **OpenAI** (GPT-4o, GPT-4o-mini, GPT-4-turbo) | `tiktoken` (`o200k_base`, `cl100k_base`) | **100% Exact** | Exact local BPE count for prompt text. |
| **Google** (Gemini 1.5 Pro, 1.5 Flash, 2.0 Flash) | Calibrated SentencePiece heuristic | **Estimated** | Explicitly declared as calibrated estimate; official exact counts require remote Google API. |
| **Anthropic** (Claude 3.5 Sonnet, 3.5 Haiku, 3 Opus) | Calibrated BPE heuristic | **Estimated** | Explicitly declared as calibrated estimate; Anthropic provides no local open-source tokenizer. |

> **Production API Billing Note:** Raw prompt token counts do not reflect exact provider API billing. Final billing includes system instructions, tool declarations, chat framing formatting wrappers, and provider caching policies.

### 2. Model Registry & Verified Lifecycle Tracking

### 2. Multi-Category AI Catalogue & Verified Lifecycle Policy

PromptShield AI organizes AI systems into three distinct categories with strict category isolation:

#### Category A: Foundation Models (`foundation_model`)
Centralized in `analyzers/model_comparison/registry.py` with verified provider documentation (audited 2026-10-28):

- **Active Generally Available Models (Default recommendation pool of 21 verified models):**
  - **OpenAI (7 models):**
    - `gpt-5.5` (1.05M context, $5.00/$30.00 per M) — [OpenAI GPT-5.5](https://platform.openai.com/docs/models#gpt-5-5)
    - `gpt-5.5-pro` (1.05M context, $30.00/$180.00 per M) — [OpenAI GPT-5.5 Pro](https://platform.openai.com/docs/models#gpt-5-5-pro)
    - `gpt-5` (400k context, $1.25/$10.00 per M) — [OpenAI GPT-5](https://platform.openai.com/docs/models#gpt-5)
    - `gpt-5-mini` (400k context, $0.25/$2.00 per M) — [OpenAI GPT-5 Mini](https://platform.openai.com/docs/models#gpt-5-mini)
    - `gpt-6-astra` (1.05M context, $10.00/$50.00 per M) — [OpenAI GPT-6 Astra](https://developers.openai.com/api/docs/models#gpt-6-astra)
    - `gpt-6-sol` (1.05M context, $2.00/$10.00 per M) — [OpenAI GPT-6 Sol](https://developers.openai.com/api/docs/models#gpt-6-sol)
    - `gpt-6-luna` (1.05M context, $0.10/$0.50 per M) — [OpenAI GPT-6 Luna](https://developers.openai.com/api/docs/models#gpt-6-luna)
  - **Google (6 models):**
    - `gemini-4-argon` (1.0M context, $2.00/$10.00 per M) — [Google Gemini 4 Argon](https://ai.google.dev/gemini-api/docs/models#gemini-4-argon)
    - `gemini-3.8-flash` (1.0M context, $0.75/$3.75 per M) — [Google Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models#gemini-3.8-flash)
    - `gemini-3.7-flash` (1.0M context, $0.75/$3.75 per M) — [Google Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models#gemini-3.7-flash)
    - `gemini-3.6-flash` (1.0M context, $0.75/$3.75 per M) — [Google Gemini 3.6 Flash](https://ai.google.dev/gemini-api/docs/models#gemini-3.6-flash)
    - `gemini-3.5-flash` (1.0M context, $1.50/$9.00 per M) — [Google Gemini 3.5 Flash](https://ai.google.dev/gemini-api/docs/models#gemini-3.5-flash)
    - `gemini-3.5-flash-lite` (1.0M context, $0.30/$2.50 per M) — [Google Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models#gemini-3.5-flash-lite)
  - **Anthropic (4 models):**
    - `claude-fable-5-1` (1.0M context, $10.00/$50.00 per M) — [Anthropic Claude Fable 5.1](https://docs.anthropic.com/en/docs/about-claude/models#claude-fable-5-1)
    - `claude-opus-5-5` (1.0M context, $4.00/$20.00 per M) — [Anthropic Claude Opus 5.5](https://docs.anthropic.com/en/docs/about-claude/models#claude-opus-5-5)
    - `claude-sonnet-5-5` (1.0M context, $2.00/$10.00 per M) — [Anthropic Claude Sonnet 5.5](https://docs.anthropic.com/en/docs/about-claude/models#claude-sonnet-5-5)
    - `claude-haiku-5-5` (1.0M context, $0.10/$0.50 per M) — [Anthropic Claude Haiku 5.5](https://docs.anthropic.com/en/docs/about-claude/models#claude-haiku-5-5)
  - **xAI (2 models):**
    - `grok-4.7` (500k context, $2.00/$6.00 per M) — [xAI Grok 4.7](https://docs.x.ai/docs/models#grok-4.7)
    - `grok-4.3` (1.0M context, $1.25/$2.50 per M) — [xAI Grok 4.3](https://docs.x.ai/docs/models#grok-4.3)
  - **DeepSeek (2 models):**
    - `deepseek-v4-pro` (1.0M context, $0.66/$1.98 per M) — [DeepSeek-V4-Pro](https://api-docs.deepseek.com/quick_start/pricing)
    - `deepseek-flash` (1.0M context, $0.15/$0.60 per M) — [DeepSeek-Flash](https://api-docs.deepseek.com/quick_start/pricing)

- **Preview & Unverified Models (Opt-in required via `include_preview=True` or CLI `'p'`):**
  - `gemini-3.1-pro-preview` (1.0M context, $2.00/$12.00 per M) — [Google Gemini 3.1 Pro](https://ai.google.dev/gemini-api/docs/models#gemini-3.1-pro)
  - `gemini-2.5-pro` & `gemini-2.5-flash` (Unverified candidates; missing public API pricing)
  - `grok-3` & `grok-3-mini` (Preview tier; unverified public token API endpoints)

- **Deprecated / Retired Historical Models (20 models; strictly excluded by default; accessible via `include_deprecated=True`):**
  - `deepseek-chat` (Retired Jul 24, 2026; replaced by DeepSeek-Flash) — [DeepSeek Deprecations](https://api-docs.deepseek.com/quick_start/pricing)
  - `deepseek-reasoner` (Retired Jul 24, 2026; replaced by DeepSeek-V4-Pro) — [DeepSeek Deprecations](https://api-docs.deepseek.com/quick_start/pricing)
  - `gemini-1.0-pro`, `gemini-1.5-pro`, `gemini-1.5-flash` (Shut down and retired Google Gemini 1.x models)
  - `gemini-2.0-flash` & `gemini-2.0-flash-lite` (Retired Jun 2026; replaced by Gemini 3.8 Flash series)
  - `gpt-4o` & `gpt-4o-mini` (Retired Oct 1, 2026; replaced by GPT-6 Sol and GPT-6 Luna)
  - `o1` & `o1-mini` & `o3-mini` (Retired OpenAI reasoning series; replaced by GPT-6 Astra and GPT-6 Sol)
  - `gpt-4-turbo` & `gpt-3.5-turbo` (Retired legacy OpenAI generation)
  - `claude-3-7-sonnet` (Retired Feb 19, 2026; replaced by Claude Sonnet 5.5)
  - `claude-3-5-sonnet` & `claude-3-5-haiku` & `claude-3-opus` (Retired Claude 3 series)
  - `grok-2` & `grok-2-vision` (Retired xAI models; replaced by Grok 4.7)

#### Category B: IDEs & Coding Assistants (`ide_assistant`)
Evaluated on developer environment workflows, multi-file agent autonomy, and repository understanding:
- **`cursor`** (Anysphere) — VS Code fork featuring Composer, local vector indexing, and Claude Sonnet 5.5 / GPT-6 Sol selection. ($0 / $20/mo / $40/mo).
- **`windsurf`** (Codeium) — Continuous flow IDE with Cascade Fast Context routing, multi-file inline edits, and terminal execution. ($0 / $20/mo / $40/mo).
- **`github-copilot`** (GitHub / Microsoft) — Deepest editor ecosystem (VS Code, JetBrains, Visual Studio, Xcode), Copilot Workspace, PR review. ($0 / $10/mo / $19/mo / $39/mo).
- **`google-antigravity`** (Google) — Agent-first platform with autonomous multi-surface agents, asynchronous agent manager, verifiable artifacts, and browser subagents.

#### Category C: AI App Builders (`app_builder`)
Evaluated on full-stack scaffolding, UI generation, database/auth support, and code ownership:
- **`v0-dev`** (Vercel) — UI component generator outputting production-grade React, Next.js, and shadcn/ui. Frontend-focused ($0 / $20/mo).
- **`bolt-new`** (StackBlitz) — In-browser full-stack prototyping running Node.js in WebContainers with interactive Plan & Build modes ($0 / $20/mo).
- **`lovable-dev`** (Lovable) — Full-stack web MVP builder tightly integrated with Supabase PostgreSQL, Auth, and two-way GitHub sync ($0 / $20/mo / $50/mo).
- **`replit-agent`** (Replit) — Autonomous cloud development platform with full Linux backend execution, multi-language support (Python, Node, Go), and Postgres ($0 / $20/mo / $95/mo).

### 3. Multi-Criteria Ranking Algorithms

The platform implements two decision-making algorithms:

1. **Weighted Sum Model (WSM):**
   $$S_i = \sum_{j} w_j \cdot \bar{x}_{ij}$$
   - Normalized logarithmically across multi-order-of-magnitude foundation model pricing ($0.075/M to $75/M).
   - Evaluates category-specific benefit and cost criteria.

2. **TOPSIS (Similarity to Ideal Solution):**
   $$C_i = \frac{D_i^-}{D_i^+ + D_i^-}$$
   - Measures Euclidean distance to positive ideal solution ($D_i^+$) and negative ideal solution ($D_i^-$).
   - Handles degenerate zero-range and single-candidate cases cleanly.

#### Presets & Weight Allocations by Category

**Category A: Foundation Models**
| Preset | Suitability | Cost | Context Headroom | Objective Focus |
|---|---|---|---|---|
| **`balanced`** | 0.45 | 0.35 | 0.20 | Balanced compromise between cost, quality, and context. |
| **`cost_optimized`** | 0.20 | 0.70 | 0.10 | Prioritizes economical models (e.g. Gemini 2.0 Flash, GPT-4o-mini). |
| **`quality_optimized`** | 0.80 | 0.05 | 0.15 | Prioritizes frontier capability tiers (Claude 3.7 Sonnet, o1, o3-mini, GPT-4o). |
| **`long_context`** | 0.25 | 0.25 | 0.50 | Prioritizes massive context capacity (Gemini 2.5 Pro 2M window). |

**Category B: IDE Assistants**
| Preset | Multi-File Agent | Repo Indexing | Terminal Exec | Model Flex | Ecosystem | Privacy | Affordability |
|---|---|---|---|---|---|---|---|
| **`balanced`** | 0.20 | 0.15 | 0.15 | 0.15 | 0.15 | 0.10 | 0.10 |
| **`agentic_power`** | 0.35 | 0.20 | 0.25 | 0.10 | 0.05 | 0.02 | 0.03 |
| **`ecosystem_integration`** | 0.10 | 0.10 | 0.03 | 0.25 | 0.35 | 0.02 | 0.15 |
| **`privacy_enterprise`** | 0.10 | 0.20 | 0.05 | 0.05 | 0.15 | 0.40 | 0.05 |

**Category C: AI App Builders**
| Preset | Full-Stack Backend | Frontend UI Quality | Deployment/Hosting | Code Export/GitHub | Autonomous Iteration | Pricing Accessibility |
|---|---|---|---|---|---|---|
| **`balanced`** | 0.20 | 0.20 | 0.15 | 0.20 | 0.15 | 0.10 |
| **`full_stack`** | 0.40 | 0.05 | 0.15 | 0.15 | 0.20 | 0.05 |
| **`frontend_ui`** | 0.05 | 0.45 | 0.20 | 0.05 | 0.10 | 0.15 |
| **`code_ownership`** | 0.20 | 0.05 | 0.10 | 0.45 | 0.15 | 0.05 |

### 4. What is NOT Measured in Offline Mode

PromptShield AI strictly enforces transparent provenance:
- **No Live Latency:** Network latency, time-to-first-token (TTFT), and token generation throughput are marked `unavailable` offline.
- **No Fabricated Benchmarks:** The platform does not invent or claim to measure third-party MMLU, SWE-bench, or HumanEval scores offline.
- **Relative Recommendation Scores:** The final ranking score is explicitly a multi-criteria decision trade-off index, not a probability of answer correctness.
- **No Product Token Costs:** IDEs and App Builders disclose their real subscription and credit structures ($0 free, $10-$20/mo pro) rather than fabricated token costs.

---

# 🧪 Running Tests & API Server

### Running the FastAPI Backend

```bash
.venv/bin/uvicorn main:app --reload --port 8000
```

- Swagger UI Documentation: `http://localhost:8000/docs`
- Healthcheck: `GET http://localhost:8000/`
- List Eligible Models: `GET http://localhost:8000/models`
- List IDE Assistants: `GET http://localhost:8000/models?category=ide_assistant`
- List App Builders: `GET http://localhost:8000/models?category=app_builder`
- Multi-Category Comparison: `POST http://localhost:8000/compare-models`

### Running the Pytest Suite

```bash
# Run all tests (unit, integration, benchmark, and model comparison)
.venv/bin/pytest -v

# Run only model comparison tests
.venv/bin/pytest tests/test_model_comparison.py -v
```

