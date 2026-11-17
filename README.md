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
- **Documentation:**
  - [`arkiv/schema.md`](arkiv/schema.md) — Schema definitions and live transaction details
  - [`arkiv/friction.md`](arkiv/friction.md) — Friction analysis & dual-layer query architecture
  - [`arkiv/reach.md`](arkiv/reach.md) — Ecosystem reach & autonomous agent discovery
  - [`arkiv/why-arkiv.md`](arkiv/why-arkiv.md) — Technical justifications vs IPFS / Ceramic
  - [`arkiv/how-you-use-arkiv.md`](arkiv/how-you-use-arkiv.md) — Code implementation walkthrough



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

### 2. Environment Configuration (.env)
```env
# Arkiv Rabdi Testnet
ARKIV_CHAIN_ID=7794095
ARKIV_RPC_URL=https://rpc.rabdi.db-chain.testnet.arkiv.network
