# Guardvane — AI Security Platform & OpiHub Marketplace

> **ETHGlobal Mumbai — Official Submission**  
> Guardvane protects LLMs and autonomous AI agents against prompt injections, secret leakage, loop exploitation, and jailbreaks.  
> **OpiHub** is the decentralized security marketplace connecting customers with autonomous 0G AI defense agents and verified human security auditors.

---

## 📁 Project Architecture & Structure

```text
ETH/
├── alembic/                         # Database schema migrations
├── analyzers/                       # Security & Prompt Injection Analysis Engines
│   ├── prompt_security_analyzer.py  # Prompt injection and jailbreak detector
│   ├── sensitive_data_detector.py   # Secret, PII, and credential leakage scanner
│   ├── prompt_optimizer.py          # Hardened prompt synthesis
│   └── security_controls_extractor.py
├── arkiv/                           # Arkiv Track Submission Documentation
│   ├── schema.md                    # Exact schema definitions (guardvane.services.v1)
│   ├── friction.md                  # Developer friction points & engineering solutions
│   ├── reach.md                     # Ecosystem reach & multi-chain agent economy
│   ├── why-arkiv.md                 # Technical justifications & comparisons
│   └── how-you-use-arkiv.md         # Production implementation guide & SDK usage
├── auth/                            # Authentication & Session Management
│   ├── router.py                    # SIWE (Sign-In with Ethereum) & session tokens
│   ├── schemas.py
│   └── service.py
├── contracts/                       # Smart Contracts
│   └── GuardvaneEscrow.sol          # EVM escrow contract for specialist security reviews
├── data/                            # Datasets & Security benchmarks
├── integrations/                    # External Protocol Bridges
│   ├── arkiv/                       # Arkiv Rabdi Testnet client (Python bridge)
│   ├── hedera/                      # Hedera mirror node & account connectors
│   ├── swarm/                       # Decentralized content-addressed report storage
│   └── zero_g/                      # 0G Private Computer AI inference connectors
├── marketplace/                     # OpiHub Decentralized Marketplace Core
│   ├── catalogue.py                 # Service discovery registry
│   ├── db.py                        # Multi-database manager (PostgreSQL / SQLite)
│   ├── platform_agents.py           # 0G autonomous defense agents
│   ├── router.py                    # Marketplace API endpoints & escrow gates
│   ├── schemas.py                   # Pydantic request/response schemas
│   └── service.py                   # Business logic, state machines & verification
├── payments/                        # Multi-Chain Payment Infrastructures
│   ├── blocky402.py                 # Hedera x402 v2 exact micropayment facilitator
│   ├── evm_escrow.py                # EVM Smart Escrow deposit/release verifier
│   └── gateway.py                   # Payment intent routing
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
└── package.json                     # Node.js dependencies (@arkiv-network/sdk, @hashgraph/sdk)
```

---

## 🏆 ETHGlobal Mumbai Qualifying Tracks

Guardvane + OpiHub integrates three core sponsor tracks into a unified production architecture:

```text
                          ┌────────────────────────────────────────────────────────┐
                          │               GUARDVANE + OPIHUB UI                    │
                          │   (Tailwind CSS + Vanilla JS + Ethers / Arkiv SDK)     │
                          └───────────┬────────────────────────────────┬───────────┘
                                      │                                │
                       [TRACK 3: Hedera x402 Route]        [Specialist Escrow Route]
                                      │                                │
                                      ▼                                ▼
                         ┌───────────────────────────┐   ┌───────────────────────────┐
                         │   Hedera Testnet (x402)   │   │ MetaMask EVM Smart Escrow │
                         │ Native HBAR Micropayments │   │     (Rabdi Testnet)       │
                         │    via Blocky402 (v2)     │   │   Direct Service Escrow   │
                         └─────────────┬─────────────┘   └─────────────┬─────────────┘
                                       │                               │
                        [TRACK 2: 0G Inference Route]                  │
                                       │                               │
                                       ▼                               ▼
                         ┌───────────────────────────┐   ┌───────────────────────────┐
                         │    0G Private Computer    │   │  Verified Expert Auditors │
                         │ Confidential AI Reasoning │   │  Codebase & Architecture  │
                         │   and Threat Hardening    │   │   Security Assessments    │
                         └───────────────────────────┘   └───────────────────────────┘
                                       │                               │
                                       └───────────────┬───────────────┘
                                                       │
                                      [TRACK 1: Arkiv Discovery Route]
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
- **Block Explorer:** [https://explorer.rabdi.db-chain.testnet.arkiv.network](https://explorer.rabdi.db-chain.testnet.arkiv.network)
- **Active Schemas:** `guardvane.services.v1` and `guardvane.specialists.v1`
- **Client SDK:** `@arkiv-network/sdk` (`client.getEntity`, `defineSchema`)
- **Documentation:**
  - [`arkiv/schema.md`](arkiv/schema.md) — Schema definitions and live transaction details
  - [`arkiv/friction.md`](arkiv/friction.md) — Friction analysis & dual-layer query architecture
  - [`arkiv/reach.md`](arkiv/reach.md) — Ecosystem reach & autonomous agent discovery
  - [`arkiv/why-arkiv.md`](arkiv/why-arkiv.md) — Technical justifications vs IPFS / Ceramic
  - [`arkiv/how-you-use-arkiv.md`](arkiv/how-you-use-arkiv.md) — Code implementation walkthrough

#### Confirmed Live On-Chain Anchor
- **Transaction Hash:** [`0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c`](https://explorer.rabdi.db-chain.testnet.arkiv.network/tx/0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c)
- **Entity Key:** `0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97`
- **Owner / Specialist:** Francis Anto (`0x6C566c890cBd6D77381805Cccc5EE19c7E016495`)
- **Service Title:** `auditing` (Prompt Engineering & Audit)
- **Indicative Price:** `3 tGLM`
- **Verification UI:** Accessible via the `Arkiv Verified (0x3b74...c97) ↗` badge on OpiHub or via `GET /marketplace/services/srv_0e5a964d/arkiv-verify`.

---

### Track 2: 0G (Zero Gravity) — Confidential AI Defense Reasoning
- **Inference Provider:** **0G Private Computer**
- **Confidential AI Defense:** Autonomous threat analysis and prompt hardening executed inside 0G confidential enclaves.
- **Strict Payment Dependency:** All AI executions require confirmed payment. 0G inference executes **strictly after** Hedera x402 on-chain settlement is verified.
- **Telemetry & Metadata:** Real token counts, processing latency, and execution telemetry are permanently recorded in generated security reports.

---

### Track 3: Hedera — Native HBAR Micropayments via x402 Protocol
- **Network:** Hedera Testnet (`hedera:testnet`)
- **Asset ID:** `0.0.0` (Native HBAR)
- **Payment Standard:** x402 v2 exact payment scheme
- **Facilitator:** Blocky402 Hosted Testnet (`https://api.testnet.blocky402.com`)
- **Merchant Account ID:** `0.0.10946394`
- **Facilitator Fee Payer:** `0.0.7162784` (Zero gas for end users)
- **Dynamic Pricing:** Estimated usage-based quote ($0.03/1k tokens, minimum $0.015 USD), dynamically converted to HBAR via Hedera exchange rate.

---

## 🔒 Off-Chain Confidentiality Architecture

Guardvane maintains strict security and privacy boundaries:
- **Public On-Chain (Arkiv):** Marketplace service discovery, public titles, categories, pricing, and specialist profiles.
- **Private Off-Chain:** Customer input prompts, proprietary LLM instructions, detailed vulnerability findings, Hedera payment secrets, and 0G inference computations remain strictly confidential and off-chain.

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

# Install Node dependencies (Arkiv SDK & Hedera SDK)
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

# Hedera x402
X402_NETWORK=hedera:testnet
X402_ASSET_ID=0.0.0
X402_FACILITATOR_URL=https://api.testnet.blocky402.com
HEDERA_MERCHANT_ACCOUNT_ID=0.0.10946394
X402_PAYMENT_MODE=testnet

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

### 2. Track 2 & 3: Hedera x402 AI Payment & 0G Execution
1. On OpiHub, click **Run 0G Defense** on "Prompt Security Analysis".
2. Notice the live dynamic prompt quote updating as you type.
3. Submit with your Hedera Testnet account; payment settles via Blocky402, and 0G Private Computer AI reasoning runs only after confirmed payment.
4. Inspect the generated report with actual token usage and Hedera on-chain reference.

### 3. Human Specialist Review & Smart Escrow Flow
1. Connect MetaMask to **Arkiv Rabdi Testnet**.
2. Order "Code base audits" ($4.00 USD) or "auditing" ($3.00 USD) from specialist Francis Anto.
3. Click **Submit Review Request**.
4. In **My Requests**, click **Pay Escrow** to deposit funds into smart escrow.
5. Switch to the specialist wallet (`0x6c56...6495`) and open **Provider Workspace**:
   - The order appears in incoming / active requests.
   - Click **Submit Deliverable & Report**, fill out findings, and submit.
6. The client reviews the report under **My Requests** and clicks **Release Escrow** to disburse payment directly to the specialist.
