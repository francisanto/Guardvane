#!/usr/bin/env node
/**
 * Arkiv Rabdi Integration CLI for Guardvane / PromptShield.
 * Uses official @arkiv-network/sdk to query schemas, inspect entities,
 * and verify ownership on Rabdi Testnet (Chain ID 7794095).
 */

import { createPublicClient, ExpirationTime } from "@arkiv-network/sdk";
import { rabdi } from "@arkiv-network/sdk/chains";
import { eq, and, desc, asc } from "@arkiv-network/sdk/query";
import { defineSchema, str, addr, dec } from "@arkiv-network/sdk/schema";
import { http } from "viem";

export const RABDI_CHAIN_ID = 7794095;
export const RABDI_RPC_URL = "https://rpc.rabdi.db-chain.testnet.arkiv.network";
export const RABDI_EXPLORER_URL = "https://rabdi.explorer.arkiv.network";

// ---------------------------------------------------------------------------
// 1. Official Arkiv Schema Definitions (Section 3 of Specification)
// ---------------------------------------------------------------------------

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

export const Tasks = defineSchema("guardvane.tasks.v1", {
  task_id: str().indexed(),
  customer_wallet: addr().indexed(),
  category: str().indexed(),
  title: str().indexed(),
  public_description: str(),
  required_skills: str(),
  budget_type: str().indexed(),
  budget_range: str(),
  status: str().indexed(),
  created_at: str(),
  deadline: str(),
  task_version: str().default("1.0.0"),
});

export const Bids = defineSchema("guardvane.bids.v1", {
  task_id: str().indexed(),
  specialist_wallet: addr().indexed(),
  proposed_price: dec().indexed(),
  estimated_duration: str(),
  proposal_summary: str(),
  status: str().indexed(),
  created_at: str(),
  bid_version: str().default("1.0.0"),
});

export const Awards = defineSchema("guardvane.awards.v1", {
  task_id: str().indexed(),
  accepted_bid_key: str().indexed(),
  customer_wallet: addr().indexed(),
  specialist_wallet: addr().indexed(),
  award_status: str().indexed(),
  created_at: str(),
});

export const SCHEMAS = {
  specialists: Specialists,
  services: Services,
  tasks: Tasks,
  bids: Bids,
  awards: Awards,
};

// ---------------------------------------------------------------------------
// 2. Client Construction
// ---------------------------------------------------------------------------

export function getPublicClient(accessKey = process.env.ARKIV_ACCESS_KEY || "") {
  const chain = rabdi({ accessKey });
  return createPublicClient({ chain, transport: http() });
}

// ---------------------------------------------------------------------------
// 3. Query Operations
// ---------------------------------------------------------------------------

export async function getStatus(accessKey) {
  try {
    const client = getPublicClient(accessKey);
    const blockNumber = await client.getBlockNumber();
    return {
      success: true,
      chain_id: RABDI_CHAIN_ID,
      network: "Rabdi Testnet",
      currency: "tGLM",
      rpc_url: RABDI_RPC_URL,
      explorer_url: RABDI_EXPLORER_URL,
      current_block: Number(blockNumber),
      is_connected: true,
    };
  } catch (err) {
    return {
      success: false,
      chain_id: RABDI_CHAIN_ID,
      network: "Rabdi Testnet",
      error: err.message,
      is_connected: false,
    };
  }
}

export async function queryEntities(schemaName, filters = {}, limit = 50, offset = 0, accessKey) {
  const schema = SCHEMAS[schemaName];
  if (!schema) {
    throw new Error(`Unknown schema '${schemaName}'. Supported: ${Object.keys(SCHEMAS).join(", ")}`);
  }

  const client = getPublicClient(accessKey);
  let query = client.select().from(schema);

  // Apply filters based on schema type
  if (schemaName === "tasks") {
    if (filters.status) {
      query = query.where(eq("status", filters.status));
    }
    if (filters.category) {
      query = query.where(eq("category", filters.category));
    }
    if (filters.customerWallet) {
      query = query.where(eq("customer_wallet", filters.customerWallet.toLowerCase()));
    }
    if (filters.taskId) {
      query = query.where(eq("task_id", filters.taskId));
    }
  } else if (schemaName === "bids") {
    if (filters.taskId) {
      query = query.where(eq("task_id", filters.taskId));
    }
    if (filters.specialistWallet) {
      query = query.where(eq("specialist_wallet", filters.specialistWallet.toLowerCase()));
    }
    if (filters.status) {
      query = query.where(eq("status", filters.status));
    }
  } else if (schemaName === "awards") {
    if (filters.taskId) {
      query = query.where(eq("task_id", filters.taskId));
    }
    if (filters.customerWallet) {
      query = query.where(eq("customer_wallet", filters.customerWallet.toLowerCase()));
    }
  } else if (schemaName === "specialists") {
    if (filters.availability) {
      query = query.where(eq("availability_status", filters.availability));
    }
    if (filters.wallet) {
      query = query.where(eq("wallet_address", filters.wallet.toLowerCase()));
    }
  } else if (schemaName === "services") {
    if (filters.category) {
      query = query.where(eq("service_category", filters.category));
    }
    if (filters.providerWallet) {
      query = query.where(eq("provider_wallet", filters.providerWallet.toLowerCase()));
    }
  }

  query = query.orderBy(desc("$key")).limit(Math.min(limit, 100)).offset(offset);

  const result = await query.fetch();
  const formatted = result.entities.map((row) => {
    const item = {
      entity_key: row.$key,
      owner: row.$owner,
      creator: row.$creator,
      created_at_block: Number(row.$createdAt || 0n),
      expires_at: Number(row.$expiresAt || 0n),
    };

    // Extract attributes
    for (const [k, v] of Object.entries(row)) {
      if (k.startsWith("$")) continue;
      item[k] = v && typeof v === "object" && "value" in v ? v.value : v;
    }
    return item;
  });

  return {
    success: true,
    schema: schemaName,
    count: formatted.length,
    skipped: result.skipped,
    entities: formatted,
  };
}

export async function getEntity(schemaName, entityKey, accessKey) {
  const schema = SCHEMAS[schemaName];
  if (!schema) {
    throw new Error(`Unknown schema '${schemaName}'`);
  }

  const client = getPublicClient(accessKey);
  const row = await client.getEntity(entityKey, schema);
  if (!row) return null;

  const item = {
    entity_key: row.$key || entityKey,
    owner: row.$owner,
    creator: row.$creator,
    expires_at: Number(row.$expiresAt || 0n),
  };

  for (const [k, v] of Object.entries(row)) {
    if (k.startsWith("$")) continue;
    item[k] = v && typeof v === "object" && "value" in v ? v.value : v;
  }
  return item;
}

// ---------------------------------------------------------------------------
// 4. Server-Side Entity Publishing (Section 3 of Specification)
// ---------------------------------------------------------------------------

export async function publishSpecialist(data, options = {}) {
  const isMock = Boolean(options.mock || process.env.ARKIV_TEST_MOCK === "1");
  if (isMock) {
    const mockHash = "0x" + Buffer.from(`mock_tx_specialist_${data.wallet_address || "addr"}_${Date.now()}`).toString("hex").padEnd(64, "0").slice(0, 64);
    const mockKey = "0x" + Buffer.from(`mock_key_specialist_${data.wallet_address || "addr"}`).toString("hex").padEnd(64, "0").slice(0, 64);
    return {
      success: true,
      mock: true,
      entityKey: mockKey,
      txHash: mockHash,
      expiresAt: Math.floor(Date.now() / 1000) + 30 * 86400,
    };
  }

  const privateKey = options.privateKey || process.env.ARKIV_SIGNER_PRIVATE_KEY || process.env.ARKIV_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error("Missing ARKIV_SIGNER_PRIVATE_KEY for backend write.");
  }

  const { createWalletClient, ExpirationTime } = await import("@arkiv-network/sdk");
  const { rabdi } = await import("@arkiv-network/sdk/chains");
  const { http } = await import("viem");
  const { privateKeyToAccount } = await import("viem/accounts");

  const formattedKey = privateKey.startsWith("0x") ? privateKey : `0x${privateKey}`;
  const account = privateKeyToAccount(formattedKey);
  const client = createWalletClient({
    account,
    chain: rabdi({ accessKey: options.accessKey || process.env.ARKIV_ACCESS_KEY || "" }),
    transport: http(),
  });

  const values = {
    wallet_address: addr(data.wallet_address),
    display_name: String(data.display_name || "Specialist"),
    headline: String(data.headline || data.title || ""),
    expertise_categories: String(Array.isArray(data.categories) ? data.categories.join(",") : (data.expertise_categories || data.category || "ai_security")),
    skills: String(Array.isArray(data.skills) ? data.skills.join(",") : (data.skills || "")),
    experience_level: String(data.experience_level || "senior"),
    availability_status: String(data.availability_status || data.availability || "available"),
    profile_version: String(data.profile_version || "1.0.0"),
  };

  const { entityKey, txHash, expiresAt } = await client.createEntity(
    Specialists,
    values,
    { expiration: ExpirationTime.fromDays(30) }
  );

  return {
    success: true,
    entityKey,
    txHash,
    expiresAt: Number(expiresAt || 0n),
  };
}

export async function publishService(data, options = {}) {
  const isMock = Boolean(options.mock || process.env.ARKIV_TEST_MOCK === "1");
  if (isMock) {
    const mockHash = "0x" + Buffer.from(`mock_tx_service_${data.provider_wallet || "prov"}_${Date.now()}`).toString("hex").padEnd(64, "0").slice(0, 64);
    const mockKey = "0x" + Buffer.from(`mock_key_service_${data.title || "service"}`).toString("hex").padEnd(64, "0").slice(0, 64);
    return {
      success: true,
      mock: true,
      entityKey: mockKey,
      txHash: mockHash,
      expiresAt: Math.floor(Date.now() / 1000) + 30 * 86400,
    };
  }

  const privateKey = options.privateKey || process.env.ARKIV_SIGNER_PRIVATE_KEY || process.env.ARKIV_PRIVATE_KEY;
  if (!privateKey) {
    throw new Error("Missing ARKIV_SIGNER_PRIVATE_KEY for backend write.");
  }

  const { createWalletClient, ExpirationTime } = await import("@arkiv-network/sdk");
  const { rabdi } = await import("@arkiv-network/sdk/chains");
  const { http } = await import("viem");
  const { privateKeyToAccount } = await import("viem/accounts");

  const formattedKey = privateKey.startsWith("0x") ? privateKey : `0x${privateKey}`;
  const account = privateKeyToAccount(formattedKey);
  const client = createWalletClient({
    account,
    chain: rabdi({ accessKey: options.accessKey || process.env.ARKIV_ACCESS_KEY || "" }),
    transport: http(),
  });

  const priceStr = (typeof data.indicative_price === "number")
    ? data.indicative_price.toFixed(2)
    : (typeof data.price === "number" ? data.price.toFixed(2) : String(data.price || data.indicative_price || "10.00"));

  const values = {
    provider_wallet: addr(data.provider_wallet || data.wallet_address),
    service_category: String(data.service_category || data.category || "ai_security"),
    title: String(data.title || "Security Service"),
    short_description: String((data.short_description || data.description || "").slice(0, 250)),
    pricing_type: String(data.pricing_type || "fixed"),
    indicative_price: dec(priceStr),
    availability: String(data.availability || "available"),
    service_version: String(data.service_version || "1.0.0"),
  };

  const { entityKey, txHash, expiresAt } = await client.createEntity(
    Services,
    values,
    { expiration: ExpirationTime.fromDays(30) }
  );

  return {
    success: true,
    entityKey,
    txHash,
    expiresAt: Number(expiresAt || 0n),
  };
}

// ---------------------------------------------------------------------------
// 5. CLI Entrypoint
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || "status";

  // Parse simple flags
  const flags = {};
  for (let i = 1; i < args.length; i++) {
    if (args[i].startsWith("--")) {
      const key = args[i].slice(2);
      const val = args[i + 1] && !args[i + 1].startsWith("--") ? args[++i] : true;
      flags[key] = val;
    }
  }

  const accessKey = flags.accessKey || process.env.ARKIV_ACCESS_KEY || "";

  try {
    if (command === "status") {
      const status = await getStatus(accessKey);
      console.log(JSON.stringify(status, null, 2));
    } else if (command === "query") {
      const schemaName = flags.schema || "tasks";
      const filters = {};
      if (flags.status) filters.status = flags.status;
      if (flags.category) filters.category = flags.category;
      if (flags.taskId) filters.taskId = flags.taskId;
      if (flags.wallet) filters.customerWallet = flags.wallet;
      if (flags.specialist) filters.specialistWallet = flags.specialist;

      const limit = Number(flags.limit || 50);
      const offset = Number(flags.offset || 0);

      const result = await queryEntities(schemaName, filters, limit, offset, accessKey);
      console.log(JSON.stringify(result, null, 2));
    } else if (command === "get") {
      const schemaName = flags.schema || "tasks";
      const entityKey = flags.entityKey;
      if (!entityKey) {
        throw new Error("Missing --entityKey flag");
      }
      const entity = await getEntity(schemaName, entityKey, accessKey);
      console.log(JSON.stringify({ success: true, entity }, null, 2));
    } else if (command === "publish-specialist") {
      const data = flags.data ? JSON.parse(flags.data) : {};
      const result = await publishSpecialist(data, {
        privateKey: flags.privateKey,
        accessKey,
        mock: Boolean(flags.mock),
      });
      console.log(JSON.stringify(result, null, 2));
    } else if (command === "publish-service") {
      const data = flags.data ? JSON.parse(flags.data) : {};
      const result = await publishService(data, {
        privateKey: flags.privateKey,
        accessKey,
        mock: Boolean(flags.mock),
      });
      console.log(JSON.stringify(result, null, 2));
    } else {
      console.error(`Unknown command: ${command}`);
      process.exit(1);
    }
  } catch (err) {
    console.error(JSON.stringify({ success: false, error: err.message }, null, 2));
    process.exit(1);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}
