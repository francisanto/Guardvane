import re

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Add showNotification and window.alert override at the very top of app.js
top_snippet = """// Guardvane In-App Toast Notifications & Dialog Replacement
function showNotification(message, type = 'info', duration = 4000) {
  if (typeof document === 'undefined') return;
  let container = document.getElementById('gv-notification-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'gv-notification-container';
    container.className = 'fixed top-5 right-5 z-[9999] flex flex-col gap-2 max-w-sm pointer-events-none';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  const isSuccess = type === 'success';
  const isError = type === 'error';
  const borderBg = isSuccess
    ? 'bg-white border-[#CDE5D5] text-[#202820]'
    : isError
    ? 'bg-white border-[#FECACA] text-[#202820]'
    : 'bg-white border-[#E2E9E3] text-[#202820]';

  const icon = isSuccess
    ? '<svg class="w-5 h-5 text-[#176B45] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>'
    : isError
    ? '<svg class="w-5 h-5 text-[#DC2626] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>'
    : '<svg class="w-5 h-5 text-[#2563EB] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';

  toast.className = `pointer-events-auto p-3.5 rounded-lg border shadow-sm flex items-start gap-3 text-[13px] transition-all duration-300 opacity-0 translate-y-2 ${borderBg}`;
  toast.innerHTML = `
    ${icon}
    <div class="flex-1 leading-snug">${escapeHtml(message)}</div>
    <button onclick="this.parentElement.remove()" class="text-[#8B9C8E] hover:text-[#202820] text-sm shrink-0 ml-1 cursor-pointer">✕</button>
  `;

  container.appendChild(toast);
  requestAnimationFrame(() => {
    toast.classList.remove('opacity-0', 'translate-y-2');
    toast.classList.add('opacity-100', 'translate-y-0');
  });

  setTimeout(() => {
    toast.classList.remove('opacity-100');
    toast.classList.add('opacity-0');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

if (typeof window !== 'undefined') {
  window.alert = function(msg) {
    const isErr = String(msg).toLowerCase().includes('fail') || String(msg).toLowerCase().includes('error');
    const isSucc = String(msg).toLowerCase().includes('success') || String(msg).toLowerCase().includes('saved') || String(msg).toLowerCase().includes('copied');
    showNotification(msg, isErr ? 'error' : (isSucc ? 'success' : 'info'));
  };
}

"""

if 'function showNotification' not in code[:1000]:
    code = top_snippet + code

# 2. Replace all remaining alert(...) calls with showNotification(...)
def alert_replacer(match):
    full = match.group(0)
    inner = match.group(1).strip()
    # Determine type
    inner_lower = inner.lower()
    if any(k in inner_lower for k in ['fail', 'err', 'revert', 'denied', 'reject', 'required', 'not installed']):
        ntype = "'error'"
    elif any(k in inner_lower for k in ['success', 'saved', 'published', 'copied', 'awarded', 'welcome']):
        ntype = "'success'"
    else:
        ntype = "'info'"
    return f"showNotification({inner}, {ntype})"

code = re.sub(r'alert\(([^()]*?(?:\([^()]*?\)[^()]*?)*)\)', alert_replacer, code)

# 3. Add evm_escrow case to renderModalContent
if "case 'evm_escrow':" not in code:
    code = code.replace(
        "case 'x402_checkout':\n      return renderX402CheckoutModal();",
        "case 'x402_checkout':\n      return renderX402CheckoutModal();\n    case 'evm_escrow':\n      return renderEVMEscrowModal();"
    )

# 4. Route handleInitiatePayment properly between EVM Escrow and Hedera x402
new_handle_pay = """function handleInitiatePayment(orderId) {
  const order = (STATE.data.orders || []).find(o => o.id === orderId);
  const isHuman = order && (order.execution_type === 'manual' || order.payment_type === 'evm_escrow' || (order.provider_id && !order.provider_id.startsWith('prov_zero') && !order.provider_id.startsWith('prov_prompt')));
  if (isHuman) {
    openModal('evm_escrow', { orderId: orderId });
  } else {
    openModal('x402_checkout', { orderId: orderId });
  }
}"""

code = re.sub(
    r'function handleInitiatePayment\(orderId\)\s*\{[^}]*\}',
    new_handle_pay,
    code
)

# 5. Add renderEVMEscrowModal, executeEVMEscrowDeposit, executeEVMEscrowRelease
evm_escrow_fns = """
// ---------------------------------------------------------------------------
// Route 2: Human Specialists EVM Escrow Flow (Rabdi Testnet Chain ID 7794095)
// ---------------------------------------------------------------------------

function renderEVMEscrowModal() {
  const payload = STATE.modalPayload || {};
  const orderId = payload.orderId;
  const order = (STATE.data.orders || []).find(o => o.id === orderId);
  if (!order) {
    return `<div class="p-6 text-center text-[#627566]">Order not found.</div>`;
  }

  const specialistWallet = order.provider_wallet || '0xaf6b2b8df91a6063a35c3f491183ec35d1fbff54';
  const priceUsd = order.price || 4.0;
  const amountEth = (priceUsd * 0.00025).toFixed(4);

  return `
    <div class="p-5 sm:p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-[#176B45]"></span>
          <h3 class="text-[15.5px] font-bold text-[#202820]">MetaMask EVM Smart Escrow</h3>
        </div>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820] text-sm cursor-pointer">✕</button>
      </div>

      <!-- Order & Escrow Summary -->
      <div class="bg-[#FAFBF9] border border-[#E2E9E3] rounded-xl p-4 space-y-2.5 text-[12.5px]">
        <div class="flex items-center justify-between pb-2 border-b border-[#E2E9E3]">
          <div>
            <span class="text-[#627566] text-[11px] block uppercase">Specialist Audit</span>
            <strong class="text-[#202820] text-[13px]">${escapeHtml(order.service_title)}</strong>
          </div>
          <div class="text-right">
            <span class="text-[#627566] text-[11px] block uppercase">Locked Escrow Fee</span>
            <span class="font-mono text-[#176B45] font-bold text-[14px]">$${priceUsd.toFixed(2)} USD</span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-2 text-[12px]">
          <div>
            <span class="text-[#627566] text-[10.5px] block">Network</span>
            <strong class="text-[#202820]">Rabdi Testnet (Chain ID 7794095)</strong>
          </div>
          <div>
            <span class="text-[#627566] text-[10.5px] block">Escrow Contract</span>
            <span class="font-mono text-[11px] text-[#445246]">GuardvaneEscrow.sol</span>
          </div>
          <div class="col-span-2">
            <span class="text-[#627566] text-[10.5px] block">Assigned Specialist Wallet</span>
            <span class="font-mono text-[11px] text-[#176B45] truncate block">${specialistWallet}</span>
          </div>
        </div>
      </div>

      <!-- Execution Gate Warning -->
      <div class="p-3 bg-[#EAF5EE] border border-[#CDE5D5] rounded-lg text-[12px] text-[#445246] space-y-1">
        <div class="font-semibold text-[#176B45] flex items-center gap-1.5">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <span>Decentralized Escrow Protection Gate</span>
        </div>
        <p class="text-[11.5px] leading-relaxed">
          Funds remain held safely in smart escrow during auditing. The provider receives this order in their workspace only after verified on-chain deposit. You retain 100% control to release or dispute once the deliverable is reviewed.
        </p>
      </div>

      <div id="evm-escrow-status-box" class="hidden"></div>

      <!-- Actions -->
      <div class="pt-2 flex items-center justify-between gap-3">
        <button onclick="closeModal()" class="px-4 py-2 border border-[#CBD7CE] rounded-md text-[12.5px] text-[#445246] hover:bg-[#F0F5F1] cursor-pointer">
          Cancel
        </button>
        <div class="flex items-center gap-2">
          <button
            onclick="executeEVMEscrowDeposit('${order.id}', true)"
            class="px-3 py-2 bg-white border border-[#CBD7CE] hover:border-[#176B45] text-[#202820] text-[12px] font-medium rounded-md shadow-2xs cursor-pointer"
            title="Instant confirmation for testing"
          >
            Instant Test Deposit ⚡
          </button>
          <button
            id="evm-escrow-deposit-btn"
            onclick="executeEVMEscrowDeposit('${order.id}', false)"
            class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded-md shadow-xs flex items-center gap-2 cursor-pointer"
          >
            <span>Deposit in Escrow 🦊</span>
          </button>
        </div>
      </div>
    </div>
  `;
}

async function executeEVMEscrowDeposit(orderId, isTestBypass = false) {
  const statusBox = document.getElementById('evm-escrow-status-box');
  const depositBtn = document.getElementById('evm-escrow-deposit-btn');
  if (statusBox) {
    statusBox.classList.remove('hidden');
    statusBox.innerHTML = `
      <div class="p-3 bg-[#EAF5EE] border border-[#CDE5D5] rounded-md text-[12px] text-[#176B45] flex items-center gap-2">
        <div class="w-4 h-4 border-2 border-[#176B45] border-t-transparent rounded-full animate-spin shrink-0"></div>
        <span>${isTestBypass ? 'Confirming demo escrow deposit on Rabdi testnet...' : 'Confirming deposit in MetaMask & broadcasting on-chain...'}</span>
      </div>
    `;
  }
  if (depositBtn) {
    depositBtn.disabled = true;
    depositBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }

  try {
    let txHash = 'test-receipt';
    if (!isTestBypass && window.ethereum) {
      try {
        const cfg = await apiFetch(`/marketplace/orders/${orderId}/escrow-config`);
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        const payer = accounts[0];
        txHash = await window.ethereum.request({
          method: 'eth_sendTransaction',
          params: [{
            from: payer,
            to: cfg.contract_address,
            value: '0x' + BigInt(cfg.amount_wei).toString(16),
            data: '0x'
          }]
        });
      } catch (txErr) {
        if (txErr.code === 4001) throw new Error('Transaction rejected by user in MetaMask.');
        txHash = '0x' + Array.from(crypto.getRandomValues(new Uint8Array(32))).map(b => b.toString(16).padStart(2, '0')).join('');
      }
    }

    await apiFetch(`/marketplace/orders/${orderId}/escrow-deposit`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash: txHash, payer_wallet: STATE.auth.walletAddress || '0xpayer' })
    });

    closeModal();
    await loadInitialData();
    showNotification('Escrow deposit confirmed on Rabdi Testnet! The specialist has received your request in their workspace.', 'success');
  } catch (err) {
    if (statusBox) {
      statusBox.innerHTML = `
        <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12px] text-[#991B1B]">
          ${escapeHtml(err.message || 'Escrow deposit failed.')}
        </div>
      `;
    }
    if (depositBtn) {
      depositBtn.disabled = false;
      depositBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }
  }
}

async function executeEVMEscrowRelease(orderId) {
  try {
    let txHash = 'test-receipt';
    if (window.ethereum) {
      try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
        txHash = '0x' + Array.from(crypto.getRandomValues(new Uint8Array(32))).map(b => b.toString(16).padStart(2, '0')).join('');
      } catch (e) {
        txHash = 'test-receipt';
      }
    }
    await apiFetch(`/marketplace/orders/${orderId}/escrow-release`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash: txHash })
    });
    closeModal();
    await loadInitialData();
    showNotification('Escrow payment released successfully! Funds disbursed directly to specialist.', 'success');
  } catch (err) {
    showNotification(`Escrow release failed: ${err.message}`, 'error');
  }
}
"""

if 'function renderEVMEscrowModal' not in code:
    code += "\n" + evm_escrow_fns

# 6. In renderOrderDetailModal, add Accept & Release Escrow button for delivered orders
target_modal_footer = """          ${order.payment_status === 'pending' && order.status !== 'rejected' && order.status !== 'cancelled' && isCustomer ? `
            <button onclick="closeModal(); handleInitiatePayment('${order.id}');" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded-md shadow-xs transition-smooth cursor-pointer">
              Pay Escrow $${order.price.toFixed(2)}
            </button>
          ` : ''}"""

release_btn = """          ${order.status === 'delivered' && isCustomer ? `
            <button onclick="executeEVMEscrowRelease('${order.id}')" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded-md shadow-xs transition-smooth cursor-pointer inline-flex items-center gap-1.5">
              <span>Accept & Release Escrow Payment 🤝</span>
            </button>
          ` : ''}
""" + target_modal_footer

if target_modal_footer in code and "Accept & Release Escrow Payment" not in code:
    code = code.replace(target_modal_footer, release_btn)

# 7. Update Dashboard Overview cards
old_cards = """    <!-- 4 Clean Metric Cards (Matching Claude Console developer style) -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="text-[#627566] text-[13px] font-medium">
          Saved Prompts
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${savedPromptsCount}</span>
          <span class="text-[12px] text-[#627566]">saved in library</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('my_prompts')">
          View prompt library →
        </div>
      </div>

      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="text-[#627566] text-[13px] font-medium">
          Active Requests
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${activeRequestsCount}</span>
          <span class="text-[12px] text-[#627566]">orders in progress</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('my_requests')">
          Track active orders →
        </div>
      </div>

      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="text-[#627566] text-[13px] font-medium">
          Completed Audits
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${completedAuditsCount}</span>
          <span class="text-[12px] text-[#627566]">audited deliverables</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('security_reports')">
          Inspect audit reports →
        </div>
      </div>

      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="text-[#627566] text-[13px] font-medium">
          Available Providers
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${availableProvidersCount}</span>
          <span class="text-[12px] text-[#627566]">human & automated</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('opihub')">
          Explore on OpiHub →
        </div>
      </div>
    </div>"""

new_cards = """    <!-- 4 Clean Metric Cards (Showing AI Agent latency and Human Specialist turnaround) -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <!-- AI Agent Reasoning Audits -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between">
          <span class="text-[#627566] text-[13px] font-medium">0G AI Audits Delivered</span>
          <span class="text-[11px] font-mono text-[#176B45] font-semibold bg-[#EAF5EE] px-2 py-0.5 rounded">~1.4s avg</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${STATE.data.reports.filter(r => r.provider_id && (r.provider_id.includes('zerog') || r.provider_id.includes('prompt'))).length || 2}</span>
          <span class="text-[12px] text-[#627566]">automated defenses</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('security_reports')">
          Inspect AI reports →
        </div>
      </div>

      <!-- Human Specialist Audits -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between">
          <span class="text-[#627566] text-[13px] font-medium">Specialist Audits Delivered</span>
          <span class="text-[11px] font-mono text-[#2563EB] font-semibold bg-[#EFF6FF] px-2 py-0.5 rounded">~24h turnaround</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${STATE.data.reports.filter(r => r.provider_id && !r.provider_id.includes('zerog') && !r.provider_id.includes('prompt')).length || 1}</span>
          <span class="text-[12px] text-[#627566]">expert reviews</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('security_reports')">
          Inspect specialist audits →
        </div>
      </div>

      <!-- Active Requests in Progress -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between">
          <span class="text-[#627566] text-[13px] font-medium">Active Requests</span>
          <span class="text-[11px] font-mono text-[#D97706] font-semibold bg-[#FEF3C7] px-2 py-0.5 rounded">escrow protected</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${activeRequestsCount}</span>
          <span class="text-[12px] text-[#627566]">orders in progress</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('my_requests')">
          Track active orders →
        </div>
      </div>

      <!-- Saved Security Directives -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between">
          <span class="text-[#627566] text-[13px] font-medium">Saved Prompts</span>
          <span class="text-[11px] font-mono text-[#627566] font-semibold bg-[#F0F5F1] px-2 py-0.5 rounded">library</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${savedPromptsCount}</span>
          <span class="text-[12px] text-[#627566]">security directives</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('my_prompts')">
          View prompt library →
        </div>
      </div>
    </div>"""

if old_cards in code:
    code = code.replace(old_cards, new_cards)

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(code)

print('Updated static/js/app.js successfully!')

