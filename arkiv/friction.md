# Developer Friction Points & Arkiv Solutions

During the engineering of Guardvane + OpiHub, integrating a decentralized database at scale revealed several real-world friction points compared to traditional Web2 databases (PostgreSQL/Supabase). This document details those friction points and how the Guardvane architecture overcame them.

---

## 1. RPC Latency & Asynchronous State Propagation

### The Friction
Traditional relational databases return immediate synchronous confirmations upon write (`INSERT INTO ...`). In decentralized databases like Arkiv, entity writes undergo transaction broadcast, mempool inclusion, block creation, and state indexing on the Rabdi Testnet. While Arkiv's block times are fast (~1-2 seconds), frontend user interfaces cannot stall indefinitely waiting for deep block finality during live interaction.

### The Guardvane Solution
We designed an **optimistic dual-layer architecture**:
- **Immediate Local State:** When a specialist publishes a new security offering or edits their profile, the operation updates the active session and application cache immediately.
- **Asynchronous Anchoring:** An asynchronous publishing bridge (`scripts/arkiv_publish_live.mjs` and `integrations/arkiv/client.py`) registers the entity on the Rabdi Testnet and secures the on-chain transaction receipt.
- **Cryptographic Verification Badge:** Once confirmed, the service displays a live "Verified on Arkiv" badge. Users can inspect the exact transaction hash (`0xce3c...058c`) and raw entity payload (`0x3b74...c5c97`) on Rabdi Explorer without latency degrading UX.

---

## 2. Deterministic Entity Key Derivation vs Mutable Updates

### The Friction
In decentralized registries, entity identity can easily fragment if updates create new entity hashes instead of updating existing entity records. If a security auditor updates their hourly rate or skill tags, clients querying historical records must not be misled by duplicate or orphaned entities.

### The Guardvane Solution
We implemented a **deterministic key derivation model**:
- Every service offering derives its Arkiv entity key deterministically from the provider's wallet address and canonical service slug using UUIDv5 / keccak256 hashing.
- When an update occurs, the transaction targets the deterministic entity key, preserving historical provenance while updating the indexed attributes (`indicative_price`, `availability`, `service_version`).

---

## 3. Client-Side Browser Querying vs Node Rate Limits

### The Friction
Querying Arkiv directly from the end-user's browser using `@arkiv-network/sdk` requires RPC connectivity. In high-traffic environments or strict browser sandbox environments (CORS / content security policies), direct browser calls can experience connection drops or rate-limiting.

### The Guardvane Solution
We built an **autonomous fallback query pipeline**:
1. **Primary Route (Trustless Client-Side):** The browser loads `@arkiv-network/sdk` and queries the Rabdi RPC node directly via `client.getEntity(entityKey)` for maximum trust minimization.
2. **Secondary Route (Resilient Gateway Bridge):** If the user's browser is behind an aggressive corporate firewall or ad-blocker, the client seamlessly falls back to Guardvane's backend verification endpoint (`GET /marketplace/services/{service_id}/arkiv-verify`), which queries the node server-side and returns the verified cryptographic attestation.

---

## 4. Sensitive Data Sandboxing & Confidentiality

### The Friction
Many Web3 projects inadvertently leak sensitive user data onto public ledgers by persisting full payload strings to on-chain storage. In cybersecurity auditing, prompts, proprietary code, and vulnerability findings are strictly confidential.

### The Guardvane Solution
- **Strict Separation of Concerns:**
  - **Public State on Arkiv:** Public catalog discovery, verified auditor identity, pricing parameters, and attestation hashes.
  - **Private Execution off Arkiv:** Client prompts and vulnerability reports remain end-to-end encrypted and held in off-chain secure memory or decentralized content-addressed encrypted storage (Swarm / local encrypted state).

