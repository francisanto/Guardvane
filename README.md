# Guardvane + OpiHub

> **Autonomous AI-Agent Security Platform, Confidential 0G Reasoning, and Decentralized Specialist Marketplace on Arkiv Rabdi Testnet.**

---

## 🏗️ Project Architecture & Repository Layout

```text
ETH/
├── contracts/                           # Solidity Smart Contracts
│   └── GuardvaneEscrow.sol          # EVM escrow contract for specialist security reviews
├── data/                            # Datasets & Security benchmarks
├── integrations/                    # External Protocol Bridges
│   ├── arkiv/                       # Arkiv Rabdi Testnet client (Python bridge)
│   └── zero_g/                      # 0G Private Computer AI inference connectors
├── marketplace/                     # OpiHub Decentralized Marketplace Core
│   ├── catalogue.py                 # Service discovery registry
│   ├── db.py                        # Multi-database manager (PostgreSQL / SQLite)
│   ├── platform_agents.py           # 0G autonomous defense agents
│   ├── router.py                    # Marketplace API endpoints & escrow gates
│   ├── schemas.py                   # Pydantic request/response schemas
│   └── service.py                   # Business logic, state machines & verification
├── payments/                        # Escrow & Payment Infrastructures
│   ├── evm_escrow.py                # EVM Smart Escrow deposit/release verifier
│   └── gateway.py                   # Payment intent & escrow routing
├── scripts/                         # Deployment & Administrative Automation
│   ├── arkiv_cli.mjs                # Node.js Arkiv SDK entity inspector
│   ├── deploy_escrow.js             # Rabdi Testnet escrow deployment script
│   └── validate_zero_g.py           # 0G Private Computer verification script
├── static/                          # High-Performance Frontend Web SPA
│   ├── css/                         # Tailwind & custom design tokens
│   ├── js/                          # Client runtime (app.js + @arkiv-network/sdk)
│   └── index.html                   # Single Page Application entrypoint
├── main.py                          # FastAPI production server
├── requirements.txt                 # Pinned Python production dependencies
└── package.json                     # Node.js dependencies (@arkiv-network/sdk)
```

---

## 🏆 Core Tracks & Architecture

Guardvane + OpiHub integrates decentralized discovery, confidential AI reasoning, and autonomous smart escrow into a unified production architecture:

```text
                          ┌────────────────────────────────────────────────────────┐
                          │               GUARDVANE + OPIHUB UI                    │
                          │   (Tailwind CSS + Vanilla JS + Ethers / Arkiv SDK)     │
                          └───────────┬────────────────────────────────┬───────────┘
                                      │                                │
                       [Direct 0G AI Reasoning Route]      [Specialist Escrow Route]
                                      │                                │
                                      ▼                                ▼
                         ┌───────────────────────────┐   ┌───────────────────────────┐
                         │    0G Private Computer    │   │ MetaMask EVM Smart Escrow │
                         │ Confidential AI Reasoning │   │     (Rabdi Testnet)       │
                         │   and Threat Hardening    │   │ Direct Service Escrow     │
                         └─────────────┬─────────────┘   └─────────────┬─────────────┘
                                       │                               │
                                       └───────────────┬───────────────┘
                                                       │
                                      [Decentralized Arkiv Discovery]
                                                       │
                                                       ▼
                         ┌───────────────────────────────────────────────────────────┐
                         │             TRACK 1: ARKIV NETWORK (RABDI TESTNET)        │
                         │             Chain ID 7794095 • Native Currency: tGLM      │
                         │  Public Discovery & Registry: guardvane.services.v1       │
                         │  Live Verification via @arkiv-network/sdk client.getEntity│
                         └───────────────────────────────────────────────────────────┘
```

---

### Track 1: Arkiv Network — Decentralized Database & Discovery
- **Network:** Rabdi Testnet (Chain ID `7794095`, `0x76ee8f`)
- **RPC Endpoint:** `https://rpc.rabdi.db-chain.testnet.arkiv.network`
- **Block Explorer:** [https://rabdi.explorer.arkiv.network](https://rabdi.explorer.arkiv.network)
- **Active Schemas:** `guardvane.services.v1` and `guardvane.specialists.v1`
- **Client SDK:** `@arkiv-network/sdk` (`client.getEntity`, `defineSchema`)
- **Documentation:**
  - [`arkiv/schema.md`](arkiv/schema.md) — Schema definitions and live transaction details
  - [`arkiv/friction.md`](arkiv/friction.md) — Friction analysis & dual-layer query architecture
  - [`arkiv/reach.md`](arkiv/reach.md) — Ecosystem reach & autonomous agent discovery
  - [`arkiv/why-arkiv.md`](arkiv/why-arkiv.md) — Technical justifications vs IPFS / Ceramic
  - [`arkiv/how-you-use-arkiv.md`](arkiv/how-you-use-arkiv.md) — Code implementation walkthrough

#### Confirmed Live On-Chain Anchor
- **Transaction Hash:** [`0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c`](https://rabdi.explorer.arkiv.network/tx/0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c)
- **Entity Key:** `0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97`
- **Owner / Specialist:** Francis Anto (`0x6C566c890cBd6D77381805Cccc5EE19c7E016495`)
- **Service Title:** `auditing` (Prompt Engineering & Audit)
- **Indicative Price:** `3 tGLM`
- **Verification UI:** Accessible via the `Arkiv Verified (0x3b74...c97) ↗` badge on OpiHub or via `GET /marketplace/services/srv_0e5a964d/arkiv-verify`.

---

### Track 2: 0G (Zero Gravity) — Confidential AI Defense Reasoning
- **Inference Provider:** **0G Private Computer**
- **Confidential AI Defense:** Autonomous threat analysis and prompt hardening executed inside 0G confidential enclaves.
- **Direct AI Execution Architecture:** Customer submits prompt and requirements; FastAPI invokes 0G Private Computer directly; 0G processes reasoning; backend records findings and telemetry and immediately renders the verified security report.
- **Telemetry & Metadata:** Real token counts, processing latency, and execution telemetry are permanently recorded in generated security reports.

---

### Human Specialist Reviews: MetaMask EVM Smart Escrow
- **Network:** Arkiv Rabdi Testnet (Chain ID `7794095`)
- **Smart Contract:** `GuardvaneEscrow.sol` (`0x176B2d2eCE7a48d0B6780709B168aC06a5834501`)
- **Deposit & Release:** Customer deposits escrow in tGLM via MetaMask upon booking. Specialist submits audit deliverable; customer reviews and releases funds on Rabdi Testnet with real transaction verification on [https://rabdi.explorer.arkiv.network/tx/](https://rabdi.explorer.arkiv.network/tx/).

---

## 🔒 Off-Chain Confidentiality Architecture

Guardvane maintains strict security and privacy boundaries:
- **Public On-Chain (Arkiv):** Marketplace service discovery, public titles, categories, pricing, and specialist profiles.
- **Private Off-Chain:** Customer input prompts, proprietary LLM instructions, detailed vulnerability findings, and 0G inference computations remain strictly confidential and off-chain.

---

## 🛠️ Quickstart & Local Setup

### Prerequisites
- Node.js v18+ (tested with Node 20 / 24)
- Python 3.9+ or Python 3.11+
- MetaMask Wallet configured for **Arkiv Rabdi Testnet**

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/francisanto/ETH.git
cd ETH

# Install Node dependencies (Arkiv SDK)
npm install

# Setup Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Configuration (.env)
```env
# Arkiv Rabdi Testnet
ARKIV_CHAIN_ID=7794095
ARKIV_RPC_URL=https://rpc.rabdi.db-chain.testnet.arkiv.network

# 0G Private Computer
ZG_BASE_URL=https://router-api.0g.ai/v1
ZG_MODEL=glm-5.3
ZG_TRUST_MODE=verified
ZG_TIMEOUT=120
ZG_ENABLED=true

# Database (PostgreSQL with automatic SQLite fallback)
DATABASE_URL=postgresql://...
```

### 3. Run Application
```bash
source .venv/bin/activate
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Open [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard) in your browser.

---

## 🧪 Manual Verification Steps for Judges

### 1. Track 1: Arkiv Live Verification & Entity Inspection
1. Navigate to **OpiHub** (`http://127.0.0.1:8000/dashboard`).
2. On the **"auditing"** service card, click the green badge:  
   `Arkiv Verified (0x3b74...c97) ↗`.
3. The **Arkiv On-Chain Service Inspector** modal opens:
   - Verifies the entity live on Rabdi Testnet using `client.getEntity()`.
   - Shows entity key `0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97` with 1-click copy.
   - Click **View Transaction on Rabdi Explorer ↗** to inspect transaction `0xce3c...058c` on-chain.
   - Displays verified on-chain attributes (`auditing`, `0x6C56...6495`, `3 tGLM`, Block `298464`).
4. Click **Rabdi Testnet • Arkiv SDK Inspector** in the top bar to query any arbitrary entity key live.
5. Click an unanchored service (e.g. "Code base audits"):
   - Verify the honest error state: `❌ NOT VERIFIED ON ARKIV (Off-Chain Only)`. The UI never falsely claims verification based only on Supabase.

### 2. Track 2: Direct 0G AI Reasoning Execution
1. On OpiHub, click **Run 0G Defense** on "Prompt Security Analysis" or any 0G AI agent.
2. Enter your prompt or agent instructions under review.
3. Click **Execute 0G AI Defense ⚡**.
4. The backend immediately invokes 0G Private Computer AI reasoning directly, generates findings, hardens prompt boundaries, and opens the generated security report with latency and token telemetry.

### 3. Human Specialist Review & Smart Escrow Flow
1. Connect MetaMask to **Arkiv Rabdi Testnet**.
2. Order "Code base audits" ($4.00 USD) or "auditing" ($3.00 USD) from specialist Francis Anto.
3. Click **Deposit Escrow & Submit Request 🛡️**.
4. In **My Requests**, click **Deposit Escrow via MetaMask** to deposit funds into smart escrow on Rabdi Testnet.
5. Switch to the specialist wallet (`0x6c56...6495`) and open **Provider Workspace**:
   - The order appears in incoming / active requests.
   - Click **Submit Deliverable & Report**, fill out findings, and submit.
6. The client reviews the report under **My Requests** and clicks **Release Escrow** to disburse payment directly to the specialist.
