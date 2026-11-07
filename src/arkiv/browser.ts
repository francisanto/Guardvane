import { createPublicClient, createWalletClient, ExpirationTime } from "@arkiv-network/sdk";
import { rabdi } from "@arkiv-network/sdk/chains";
import { and, asc, desc, eq, gt, gte, lt, lte, or } from "@arkiv-network/sdk/query";
import { addr, bool, dec, defineSchema, key, str, u64 } from "@arkiv-network/sdk/schema";
import { custom, http } from "viem";

export const RABDI_CHAIN_ID = 7794095;
export const RABDI_CHAIN_ID_HEX = "0x76ee8f";
export const RABDI_RPC_URL = "https://rpc.rabdi.db-chain.testnet.arkiv.network";
export const RABDI_EXPLORER_URL = "https://rabdi.explorer.arkiv.network";

// ---------------------------------------------------------------------------
// 1. Schemas
// ---------------------------------------------------------------------------

export const SpecialistsSchema = defineSchema("guardvane.specialists.v1", {
  wallet_address: addr().indexed(),
  display_name: str().indexed(),
  headline: str(),
  expertise_categories: str().indexed(),
  skills: str(),
  experience_level: str().indexed(),
  availability_status: str().indexed(),
  profile_version: str().default("1.0.0"),
});

export const ServicesSchema = defineSchema("guardvane.services.v1", {
  provider_wallet: addr().indexed(),
  service_category: str().indexed(),
  title: str().indexed(),
  short_description: str(),
  pricing_type: str().indexed(),
  indicative_price: dec().indexed(),
  availability: str().indexed(),
  service_version: str().default("1.0.0"),
});

export const TasksSchema = defineSchema("guardvane.tasks.v1", {
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

export const BidsSchema = defineSchema("guardvane.bids.v1", {
  task_id: str().indexed(),
  specialist_wallet: addr().indexed(),
  proposed_price: dec().indexed(),
  estimated_duration: str(),
  proposal_summary: str(),
  status: str().indexed(),
  created_at: str(),
  bid_version: str().default("1.0.0"),
});

export const AwardsSchema = defineSchema("guardvane.awards.v1", {
  task_id: str().indexed(),
  accepted_bid_key: str().indexed(),
  customer_wallet: addr().indexed(),
  specialist_wallet: addr().indexed(),
  award_status: str().indexed(),
  created_at: str(),
});

// ---------------------------------------------------------------------------
// 2. Client Helpers
// ---------------------------------------------------------------------------

export function getPublicClient(accessKey = "") {
  const chain = rabdi({ accessKey });
  return createPublicClient({ chain, transport: http() });
}

export function getWalletClient(accountAddress, accessKey = "") {
  if (typeof window === "undefined" || !window.ethereum) {
    throw new Error("MetaMask (window.ethereum) is not available.");
  }
  const chain = rabdi({ accessKey });
  return createWalletClient({
    chain,
    transport: custom(window.ethereum),
    account: accountAddress,
  });
}

export async function switchOrAddRabdiNetwork() {
  if (typeof window === "undefined" || !window.ethereum) {
    throw new Error("MetaMask is not installed.");
  }

  try {
    await window.ethereum.request({
      method: "wallet_switchEthereumChain",
      params: [{ chainId: RABDI_CHAIN_ID_HEX }],
    });
    return true;
  } catch (switchError) {
    // Error 4902 indicates that the chain has not been added to MetaMask.
    if (switchError.code === 4902 || switchError.data?.originalError?.code === 4902) {
      await window.ethereum.request({
        method: "wallet_addEthereumChain",
        params: [
          {
            chainId: RABDI_CHAIN_ID_HEX,
            chainName: "Rabdi Testnet (Arkiv)",
            rpcUrls: [RABDI_RPC_URL],
            nativeCurrency: {
              name: "tGLM",
              symbol: "tGLM",
              decimals: 18,
            },
            blockExplorerUrls: [RABDI_EXPLORER_URL],
          },
        ],
      });
      return true;
    }
    throw switchError;
  }
}

// ---------------------------------------------------------------------------
// 3. Entity Creation via Browser Wallet (User-Owned Writes)
// ---------------------------------------------------------------------------

export async function publishSpecialistProfile(data, accountAddress, accessKey = "") {
  await switchOrAddRabdiNetwork();
  const wc = getWalletClient(accountAddress, accessKey);

  const payload = {
    wallet_address: addr(accountAddress),
    display_name: data.displayName || "Specialist",
    headline: data.headline || "",
    expertise_categories: data.categories || "ai_security",
    skills: data.skills || "",
    experience_level: data.experienceLevel || "senior",
    availability_status: data.availabilityStatus || "available",
    profile_version: "1.0.0",
  };

  const { entityKey, txHash } = await wc.createEntity(SpecialistsSchema, payload, {
    expiration: ExpirationTime.fromDays(30),
  });

  return { entityKey, txHash };
}

export async function publishServiceListing(data, accountAddress, accessKey = "") {
  await switchOrAddRabdiNetwork();
  const wc = getWalletClient(accountAddress, accessKey);

  const priceStr = (data.indicativePrice || "10.0").toString();
  const payload = {
    provider_wallet: addr(accountAddress),
    service_category: data.serviceCategory || "ai_security",
    title: data.title,
    short_description: data.shortDescription || "",
    pricing_type: data.pricingType || "fixed",
    indicative_price: dec(priceStr),
    availability: data.availability || "available",
    service_version: "1.0.0",
  };

  const { entityKey, txHash } = await wc.createEntity(ServicesSchema, payload, {
    expiration: ExpirationTime.fromDays(30),
  });

  return { entityKey, txHash };
}

export async function publishSecurityTask(data, accountAddress, accessKey = "") {
  await switchOrAddRabdiNetwork();
  const wc = getWalletClient(accountAddress, accessKey);

  const payload = {
    task_id: data.taskId,
    customer_wallet: addr(accountAddress),
    category: data.category || "application_security",
    title: data.title,
    public_description: data.publicDescription || "",
    required_skills: data.requiredSkills || "",
    budget_type: data.budgetType || "fixed",
    budget_range: data.budgetRange || "50-100 tGLM",
    status: "open",
    created_at: new Date().toISOString(),
    deadline: data.deadline || "",
    task_version: "1.0.0",
  };

  const { entityKey, txHash } = await wc.createEntity(TasksSchema, payload, {
    expiration: ExpirationTime.fromDays(7),
  });

  return { entityKey, txHash };
}

export async function submitSpecialistBid(data, accountAddress, accessKey = "") {
  await switchOrAddRabdiNetwork();
  const wc = getWalletClient(accountAddress, accessKey);

  const priceStr = (data.proposedPrice || "25.0").toString();
  const payload = {
    task_id: data.taskId,
    specialist_wallet: addr(accountAddress),
    proposed_price: dec(priceStr),
    estimated_duration: data.estimatedDuration || "3 days",
    proposal_summary: data.proposalSummary || "",
    status: "submitted",
    created_at: new Date().toISOString(),
    bid_version: "1.0.0",
  };

  const { entityKey, txHash } = await wc.createEntity(BidsSchema, payload, {
    expiration: ExpirationTime.fromHours(48),
  });

  return { entityKey, txHash };
}

export async function acceptBidAndCreateAward(data, accountAddress, accessKey = "") {
  await switchOrAddRabdiNetwork();
  const wc = getWalletClient(accountAddress, accessKey);

  const payload = {
    task_id: data.taskId,
    accepted_bid_key: data.acceptedBidKey,
    customer_wallet: addr(accountAddress),
    specialist_wallet: addr(data.specialistWallet),
    award_status: "awarded",
    created_at: new Date().toISOString(),
  };

  const { entityKey, txHash } = await wc.createEntity(AwardsSchema, payload, {
    expiration: ExpirationTime.fromDays(7),
  });

  return { entityKey, txHash };
}

// ---------------------------------------------------------------------------
// 4. Direct Public Client Queries (Public Discovery Layer)
// ---------------------------------------------------------------------------

function formatRow(row) {
  const item = {
    entity_key: row.$key,
    owner: row.$owner,
    creator: row.$creator,
    created_at_block: Number(row.$createdAt || 0n),
    expires_at: Number(row.$expiresAt || 0n),
  };
  for (const [k, v] of Object.entries(row)) {
    if (k.startsWith("$")) continue;
    item[k] = v && typeof v === "object" && "value" in v ? v.value : v;
  }
  return item;
}

export async function fetchSpecialists({ accessKey = "", availability = null, limit = 50, offset = 0 } = {}) {
  const client = getPublicClient(accessKey);
  let q = client.select().from(SpecialistsSchema);
  if (availability) {
    q = q.where(eq("availability_status", availability));
  }
  q = q.orderBy(desc("$key")).limit(limit).offset(offset);
  const res = await q.fetch();
  return res.entities.map(formatRow);
}

export async function fetchServices({ accessKey = "", category = null, limit = 50, offset = 0 } = {}) {
  const client = getPublicClient(accessKey);
  let q = client.select().from(ServicesSchema);
  if (category && category !== "all") {
    q = q.where(eq("service_category", category));
  }
  q = q.orderBy(desc("$key")).limit(limit).offset(offset);
  const res = await q.fetch();
  return res.entities.map(formatRow);
}

export async function fetchTasks({ accessKey = "", category = null, status = null, limit = 50, offset = 0 } = {}) {
  const client = getPublicClient(accessKey);
  let q = client.select().from(TasksSchema);
  if (status && status !== "all") {
    q = q.where(eq("status", status));
  }
  if (category && category !== "all") {
    q = q.where(eq("category", category));
  }
  q = q.orderBy(desc("$key")).limit(limit).offset(offset);
  const res = await q.fetch();
  return res.entities.map(formatRow);
}

export async function fetchBidsForTask(taskId, accessKey = "") {
  const client = getPublicClient(accessKey);
  const q = client.select().from(BidsSchema).where(eq("task_id", taskId)).orderBy(desc("$key")).limit(50);
  const res = await q.fetch();
  return res.entities.map(formatRow);
}

export async function fetchAwardsForTask(taskId, accessKey = "") {
  const client = getPublicClient(accessKey);
  const q = client.select().from(AwardsSchema).where(eq("task_id", taskId)).orderBy(desc("$key")).limit(10);
  const res = await q.fetch();
  return res.entities.map(formatRow);
}

// ---------------------------------------------------------------------------
// 5. Types and Operators Re-export
// ---------------------------------------------------------------------------

export {
  addr,
  bool,
  dec,
  key,
  str,
  u64,
  defineSchema,
  ExpirationTime,
  eq,
  and,
  or,
  asc,
  desc,
  gt,
  gte,
  lt,
  lte,
};
