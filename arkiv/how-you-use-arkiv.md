# How Guardvane Uses Arkiv

This guide provides an end-to-end breakdown of how Guardvane and OpiHub integrate the **Arkiv Rabdi Testnet** into production workflows.

---

## Architecture Overview

```mermaid
flowchart TD
    Provider["Specialist / Provider"] -->|Publishes Offering| Frontend["Guardvane Web SPA"]
    Frontend -->|POST /marketplace/services| Backend["Guardvane Fast-API Backend"]
    Backend -->|Dispatches Entity| ArkivBridge["Arkiv Publisher Bridge (Node/Python)"]
    ArkivBridge -->|Registers Transaction| Rabdi["Arkiv Rabdi Testnet (Chain ID 7794095)"]
    Rabdi -->|Emits Entity Key & Tx Hash| BlockExplorer["Rabdi Block Explorer"]
    
    Customer["Customer / Client"] -->|Browses OpiHub| Frontend
    Frontend -->|Trustless On-Chain Verify| SDK["@arkiv-network/sdk (Browser Direct)"]
    SDK -->|Query getEntity(entityKey)| Rabdi
    SDK -->|Displays Attestation| Modal["Interactive On-Chain Verification Modal"]
```

---

## 1. Schema Registration & Publishing

When a provider publishes a security service or when an autonomous agent is provisioned, the entity is defined and registered on Arkiv using `@arkiv-network/sdk`.

```javascript
// Excerpt from scripts/arkiv_publish_live.mjs
import { ArkivClient } from '@arkiv-network/sdk';
import { defineSchema, str, addr, dec } from '@arkiv-network/sdk/schema';

const client = new ArkivClient({
  rpcUrl: 'https://rpc.rabdi.db-chain.testnet.arkiv.network',
  chainId: 7794095
});

const serviceEntity = await client.createEntity({
  schema: 'guardvane.services.v1',
  payload: {
    provider_wallet: specialistWallet,
    service_category: 'codebase_security',
    title: 'Code base audits',
    short_description: 'Comprehensive static and dynamic codebase audit.',
    pricing_type: 'fixed',
    indicative_price: 4.00,
    availability: 'available',
    service_version: '1.0.0'
  }
});

console.log('Registered on Arkiv with Tx Hash:', serviceEntity.txHash);
console.log('Entity Key:', serviceEntity.entityKey);
```

### Confirmed Live Deployment Reference
- **Schema:** `guardvane.services.v1`
- **Transaction Hash:** `0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c`
- **Entity Key:** `0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97`
- **Explorer:** [View On-Chain Entity on Rabdi Explorer](https://rabdi.explorer.arkiv.network/tx/0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c)

---

## 2. Trustless Client-Side Verification in OpiHub

In `static/js/app.js`, every service card on OpiHub includes an interactive **"Verify on Arkiv"** inspector button.

When clicked:
1. The modal executes a direct query to Arkiv:
```javascript
// Client-side query directly via browser
const entity = await arkivSdkClient.getEntity(service.arkiv_entity_key);
```
2. The modal validates the entity integrity:
   - Matches the returned on-chain `indicative_price` and `title` against the current listing.
   - Verifies the owner wallet address.
   - Inspects the on-chain block timestamp and schema revision.
3. Renders a verification badge with an external link directly to the **Rabdi Block Explorer**.
4. If an entity cannot be found on-chain, the UI renders an honest `"Unverified / Off-Chain Entity"` status, preventing false claims.

---

## 3. Separation of Public vs Private Data

Guardvane strictly bounds what is sent to Arkiv:
- **Stored on Arkiv:** Public metadata (service titles, category tags, public provider wallets, pricing guidelines).
- **Off-Chain / Confidential:** User prompts, proprietary codebase links, API credentials, and generated security audit reports.

