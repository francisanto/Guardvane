# Why Arkiv: Technical Justification

When architecting Guardvane's decentralized metadata and discovery layer, we evaluated several decentralized storage and database solutions:

| Feature / Requirement | Centralized SQL | IPFS / Arweave | Ceramic Network | **Arkiv (Rabdi Testnet)** |
| :--- | :---: | :---: | :---: | :---: |
| **Protocol-Level Schema Enforcement** | ❌ (app-level) | ❌ (none) | ⚠️ (data streams) | ✅ **Native Typed Schemas** |
| **Real-Time On-Chain Queryability** | ✅ | ❌ (needs indexer) | ⚠️ (high latency) | ✅ **Sub-Second RPC Queries** |
| **EVM Native Compatibility** | ❌ | ❌ | ❌ | ✅ **EVM & Web3 Tooling** |
| **Censorship-Resistant Discovery** | ❌ | ✅ | ✅ | ✅ **Deterministic Entities** |
| **Built-in Time-to-Live / Expiration** | ❌ (manual cron) | ❌ (permanent) | ❌ | ✅ **Native Expiration Bounds** |

---

## Key Advantages for Guardvane

### 1. Protocol-Enforced Typed Schemas
Unlike raw decentralized blob storage (IPFS / Arweave), where corrupted or malformed payloads can break consumer clients, Arkiv enforces strict typing at the protocol layer. The `guardvane.services.v1` schema guarantees that every registered service contains valid fields (`title`, `service_category`, `pricing_type`, `indicative_price`) before the transaction is accepted into a block.

### 2. High-Throughput EVM Compatibility
Arkiv's Rabdi Testnet operates as an EVM-compatible chain. This eliminates the need for foreign cryptographic signing libraries or separate browser wallet extensions:
- Users connect via MetaMask.
- Transactions are signed using standard Ethereum wallet primitives.
- Smart contracts can read entity existence proofs and state directly.

### 3. Native Expiration and Hygiene
Security services and pricing change frequently; stale listings can clutter market discovery. Arkiv's native `ExpirationTime` mechanics (e.g. 30-day lease with automatic renewal upon update) ensure the registry remains active, pruning abandoned listings without expensive smart contract cleanup transactions.

### 4. Direct Client Verification
Arkiv enables direct, client-side browser verification without an intermediary server. A user inspecting a security offering on OpiHub can fetch the on-chain entity directly from the Rabdi RPC node using `@arkiv-network/sdk`, guaranteeing that the pricing and scope shown in the UI have not been spoofed by an intermediary backend.

