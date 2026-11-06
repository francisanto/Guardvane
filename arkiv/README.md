# Arkiv Decentralized Database Integration — Guardvane + OpiHub

> **ETHGlobal Mumbai — Arkiv Qualification & Judging Documentation**  
> **Network:** Rabdi Testnet (Arkiv DB-Chain)  
> **Chain ID:** `7794095` (`0x76ee8f`)  
> **RPC URL:** `https://rpc.rabdi.db-chain.testnet.arkiv.network`  
> **Explorer:** [https://explorer.rabdi.db-chain.testnet.arkiv.network](https://explorer.rabdi.db-chain.testnet.arkiv.network)  
> **Currency:** `tGLM`

---

## 1. Confirmed Live On-Chain Transaction & Entity

Our on-chain security service listing has been confirmed and anchored to Rabdi Testnet using the official `@arkiv-network/sdk`.

- **Transaction Hash:**  
  [`0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c`](https://explorer.rabdi.db-chain.testnet.arkiv.network/tx/0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c)
- **Active Schema:**  
  `guardvane.services.v1`
- **Entity Key:**  
  `0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97`
- **Owner / Creator / Provider Wallet:**  
  `0x6C566c890cBd6D77381805Cccc5EE19c7E016495`
- **Block Anchor:**  
  Block `298464`
- **Expiration Block:**  
  Block `1594464` (valid for 30 days)

### Decoded On-Chain Attributes (Retrieved Live via `client.getEntity()`)

```json
{
  "entity_key": "0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97",
  "owner": "0x6C566c890cBd6D77381805Cccc5EE19c7E016495",
  "creator": "0x6C566c890cBd6D77381805Cccc5EE19c7E016495",
  "provider_wallet": "0x6C566c890cBd6D77381805Cccc5EE19c7E016495",
  "title": "auditing",
  "service_category": "prompt_engineering",
  "short_description": "audting based on the code",
  "pricing_type": "fixed",
  "indicative_price": "3",
  "availability": "available",
  "service_version": "1.0.0",
  "created_at_block": 298464,
  "expires_at": 1594464
}
```

---

## 2. Arkiv SDK Integration Architecture

Guardvane utilizes the official `@arkiv-network/sdk` in a dual configuration:
1. **Frontend Discovery & Live Verification (`static/js/arkiv-browser.js` & `static/js/app.js`):**
   - Connects directly to Rabdi Testnet using `createPublicClient({ chain: rabdi(), transport: http() })`.
   - Executes live entity queries using `client.getEntity(entityKey, ServicesSchema)`.
   - Provides user-facing on-chain verification badges and inspector modals.
2. **Backend Node.js CLI Bridge (`scripts/arkiv_cli.mjs` & `integrations/arkiv/`):**
   - Headless CLI runner executing standard Arkiv SDK commands:
     - `node scripts/arkiv_cli.mjs get --schema services --entityKey <key>`
     - `node scripts/arkiv_cli.mjs query --schema services --category <cat>`
     - `node scripts/arkiv_cli.mjs status`
   - Wrapped by FastAPI endpoints:
     - `GET /marketplace/services/{service_id}/arkiv-verify`
     - `GET /marketplace/arkiv/entity/{entity_key}`
     - `GET /marketplace/arkiv/status`

---

## 3. Official Arkiv Schema Definitions

Defined using `defineSchema` from `@arkiv-network/sdk/schema`:

### 1. `guardvane.services.v1` (Service Listings)
```typescript
export const Services = defineSchema("guardvane.services.v1", {
  provider_wallet: addr().indexed(),
  service_category: str().indexed(),
  title: str().indexed(),
  short_description: str(),
  pricing_type: str().indexed(),
  indicative_price: dec().indexed(),
  availability: str().indexed(),
  service_version: str().default("1.0.0"),
});
```

### 2. `guardvane.specialists.v1` (Specialist Profiles)
```typescript
export const Specialists = defineSchema("guardvane.specialists.v1", {
  wallet_address: addr().indexed(),
  display_name: str().indexed(),
  headline: str(),
  expertise_categories: str().indexed(),
  skills: str(),
  experience_level: str().indexed(),
  availability_status: str().indexed(),
  profile_version: str().default("1.0.0"),
});
```

---

## 4. Query Implementation Details

### Retrieving a Specific Entity
```typescript
import { createPublicClient } from "@arkiv-network/sdk";
import { rabdi } from "@arkiv-network/sdk/chains";

const client = createPublicClient({ chain: rabdi(), transport: http() });
const entity = await client.getEntity(
  "0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97",
  Services
);
```

### Filtering Services by Category
```typescript
import { eq, desc } from "@arkiv-network/sdk/query";

const res = await client
  .select()
  .from(Services)
  .where(eq("service_category", "prompt_engineering"))
  .orderBy(desc("$key"))
  .limit(10)
  .fetch();
```

---

## 5. Architectural Privacy & Data Integrity Guarantees

Guardvane maintains a strict separation of concerns between public decentralized discovery and confidential execution:

| Data Type | Storage Location | Public on Arkiv? | Reason |
|:---|:---|:---:|:---|
| Service Title & Category | Arkiv (`guardvane.services.v1`) | **Yes** | Decentralized marketplace discovery |
| Indicative Price & Provider Wallet | Arkiv (`guardvane.services.v1`) | **Yes** | Unstoppable, censorship-resistant public pricing |
| Specialist Profiles | Arkiv (`guardvane.specialists.v1`) | **Yes** | Portable reputation and skills catalog |
| Customer Prompt & System Instructions | Local Confidential Memory / 0G Private Computer | **NO** | Proprietary customer IP and sensitive security vectors |
| Vulnerability Findings & Reports | Encrypted Supabase / Customer Session | **NO** | Confidential security scan deliverables |
| Hedera x402 Payment Secrets / Nonces | Client Local Browser Storage | **NO** | Cryptographic security |

### Honest Verification Principle
The Guardvane UI **never** reports a service as on-chain verified based only on a local database record. A green verified badge is rendered if and only if:
1. The service holds an on-chain `entity_key`.
2. The entity is retrieved live from the Rabdi RPC node using `client.getEntity()`.
3. The on-chain entity owner matches the registered provider wallet.

Unpublished services explicitly display an amber/red `Off-Chain (Supabase Only)` badge.

---

## 6. How to Verify in the Running Application

1. Open the Guardvane dashboard at `http://127.0.0.1:8000/dashboard` and navigate to **OpiHub**.
2. Locate the service titled **"auditing"** by Francis Anto.
3. Observe the green badge: `Arkiv Verified (0x3b74...c97) ↗`.
4. Click the badge to open the **Arkiv On-Chain Service Inspector**.
5. Inspect the live decoded on-chain data, entity key copy action, and direct link to Rabdi Explorer.
6. Click **Rabdi Testnet • Arkiv SDK Inspector** in the top bar to query any arbitrary entity key live.
7. Click any unanchored service (e.g., "Code base audits") to verify the honest unverified state.
