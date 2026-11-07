# Arkiv Schema Registry — Guardvane Security Marketplace

This document outlines the decentralized schemas registered on **Arkiv Rabdi Testnet (Chain ID 7794095)** powering the Guardvane AI security platform and OpiHub service discovery.

All schemas are compiled using `@arkiv-network/sdk/schema` and anchored deterministically on-chain.

---

## 1. `guardvane.services.v1`

Public decentralized registry of AI security agent offerings and human security expert services. This enables trustless, permissionless service discovery without reliance on centralized directory databases.

```typescript
export const Services = defineSchema("guardvane.services.v1", {
  provider_wallet: addr().indexed(),        // Specialist / Agent Provider Ethereum Wallet
  service_category: str().indexed(),       // Category tag (e.g. "prompt_engineering", "codebase_security")
  title: str().indexed(),                  // Service Title
  short_description: str(),                // Brief description of deliverables
  pricing_type: str().indexed(),           // "fixed", "quote", "per_token"
  indicative_price: dec().indexed(),       // Baseline price in tGLM / USD
  availability: str().indexed(),           // "available", "busy", "offline"
  service_version: str().default("1.0.0"), // Schema revision
});
```

### On-Chain Deployment & Verification
- **Network:** Arkiv Rabdi Testnet
- **Chain ID:** `7794095`
- **RPC Endpoint:** `https://rpc.rabdi.db-chain.testnet.arkiv.network`
- **Default Expiration:** 30 Days (`ExpirationTime.fromDays(30)`)
- **Primary Use:** Public service discovery on OpiHub.
- **Confirmed Transaction:** [`0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c`](https://rabdi.explorer.arkiv.network/tx/0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c)
- **Confirmed Entity Key:** `0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97`
- **Explorer Link:** [View Verified Service Entity on Rabdi Explorer](https://rabdi.explorer.arkiv.network/tx/0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c)

---

## 2. `guardvane.specialists.v1`

Decentralized credentials and profile registry for expert security researchers and agent developers. Guarantees immutable reputation and skill verification across organizations.

```typescript
export const Specialists = defineSchema("guardvane.specialists.v1", {
  wallet_address: addr().indexed(),        // Specialist EVM Wallet
  display_name: str().indexed(),           // Public handle or display name
  headline: str(),                         // Bio or professional title
  expertise_categories: str().indexed(),   // Comma-separated categories
  skills: str(),                           // Specific frameworks and security toolsets
  experience_level: str().indexed(),       // "junior", "mid", "senior", "lead"
  availability_status: str().indexed(),    // "available", "busy", "offline"
  profile_version: str().default("1.0.0"), // Schema revision
});
```

- **Default Expiration:** 30 Days (`ExpirationTime.fromDays(30)`)
- **Primary Use:** Specialist portable identity, skill verification, and reputation registry.

---

## Data Privacy & Integrity Boundary

Arkiv is strictly utilized for **public, verifiable metadata**:
- Registered service offerings and baseline pricing
- Specialist professional credentials and verified public keys
- Cryptographic attestation hashes

**Strictly Excluded from Arkiv:**
- Confidential client prompt texts and application code
- Private security assessment reports and vulnerability details
- Payment private keys, signer secrets, or sensitive session tokens

