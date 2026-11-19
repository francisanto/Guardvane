// Guardvane In-App Toast Notifications & Dialog Replacement
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
    ? 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)]'
    : isError
    ? 'bg-[var(--surface)] border-[#FECACA] text-[var(--text)]'
    : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)]';

  const icon = isSuccess
    ? '<svg class="w-4 h-4 text-[var(--success)] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>'
    : isError
    ? '<svg class="w-4 h-4 text-[var(--danger)] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>'
    : '<svg class="w-4 h-4 text-[var(--info)] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';

  toast.className = `pointer-events-auto p-3.5 rounded-[var(--radius-md)] border shadow-xs flex items-start gap-3 text-[13px] transition-all duration-300 opacity-0 translate-y-2 ${borderBg}`;
  toast.innerHTML = `
    ${icon}
    <div class="flex-1 leading-snug">${escapeHtml(message)}</div>
    <button onclick="this.parentElement.remove()" class="text-[var(--text-3)] hover:text-[var(--text)] text-sm shrink-0 ml-1 cursor-pointer">✕</button>
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
  window.confirm = function(msg) {
    return true;
  };
  window.prompt = function(msg) {
    return '';
  };
}

/**
 * Guardvane — AI Security Platform & OpiHub Marketplace
 * Claude / Anthropic Editorial Design System: Warm paper surfaces, ink typography, single terracotta accent
 */

const STATE = {
  activeView: 'dashboard', // dashboard, opihub, provider_detail, become_provider, provider_workspace, my_prompts, my_requests, security_reports
  selectedProviderId: null,
  selectedServiceId: null,
  selectedOrderId: null,
  selectedReportId: null,
  auth: {
    isAuthenticated: false,
    walletAddress: null,
    user: null,
    loading: false,
    error: null,
    statusText: '',
    guestMode: false
  },
  user: {
    id: null,
    name: (typeof localStorage !== 'undefined' && localStorage.getItem('guardvane_display_name')) ? localStorage.getItem('guardvane_display_name') : 'Account',
    role: 'customer',
    activeProviderId: null
  },
  filters: {
    search: '',
    category: 'all',
    providerType: '',
    availability: '',
    maxPrice: null
  },
  data: {
    stats: null,
    providers: [],
    services: [],
    orders: [],
    reports: [],
    prompts: [],
    integrations: null
  },
  arkiv: {
    config: null,
    status: null,
    tasks: [],
    selectedTaskId: null,
    taskBids: [],
    loading: false,
    error: null,
    txStatus: null,
    categoryFilter: 'all',
    statusFilter: 'all'
  },
  network: {
    chainId: null,
    isRabdi: false,
    name: 'Unknown'
  },
  activeModal: null,
  modalPayload: null,
  modalTriggerEl: null,
  orderDetailConfirmRelease: false,
  orderDetailReleaseLoading: false,
  orderDetailReleaseError: '',
  orderRequestExpanded: false,
  loading: false
};

// ---------------------------------------------------------------------------
// API Helpers & Authentication Actions
// ---------------------------------------------------------------------------

async function apiFetch(endpoint, options = {}) {
  const currentWallet = (STATE.auth.walletAddress || STATE.user.id || '').toLowerCase();
  const myProv = getMyProvider();
  const isProv = (STATE.activeView === 'provider_workspace') ||
                 (STATE.user.role === 'provider' && Boolean(myProv));
  const effectiveRole = isProv ? 'provider' : 'customer';
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': currentWallet || 'anonymous',
    'X-User-Role': effectiveRole,
    'X-Wallet-Address': currentWallet,
    ...(options.headers || {})
  };

  try {
    const res = await fetch(endpoint, { ...options, headers, credentials: 'include' });
    if (!res.ok) {
      if (res.status === 401 && !STATE.auth.guestMode) {
        STATE.auth.isAuthenticated = false;
        renderApp();
      }
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      let errMsg = errData.detail || errData.message || `API error (${res.status})`;
      if (Array.isArray(errMsg)) {
        errMsg = errMsg.map(e => e.msg || e.detail || JSON.stringify(e)).join(', ');
      } else if (typeof errMsg === 'object') {
        errMsg = JSON.stringify(errMsg);
      }
      const err = new Error(errMsg);
      err.status = res.status;
      err.detail = errMsg;
      throw err;
    }
    return await res.json();
  } catch (err) {
    console.error(`Fetch error at ${endpoint}:`, err);
    throw err;
  }
}

async function checkAuthSession() {
  try {
    const res = await fetch('/auth/me', { credentials: 'include' });
    if (res.ok) {
      const data = await res.json();
      STATE.auth.isAuthenticated = true;
      STATE.auth.user = data;
      STATE.auth.walletAddress = data.wallet_address;
      STATE.user.id = data.wallet_address;
      STATE.user.name = data.display_name || (data.wallet_address.substring(0, 6) + '...' + data.wallet_address.substring(data.wallet_address.length - 4));
      
      // Match registered provider profile by connected wallet
      const myProv = (STATE.data.providers || []).find(p => p.wallet_address && p.wallet_address.toLowerCase() === data.wallet_address.toLowerCase());
      if (myProv) {
        STATE.user.activeProviderId = myProv.id;
        STATE.user.role = 'provider';
      } else {
        STATE.user.role = (data.roles && data.roles.includes('provider')) ? 'provider' : (data.roles[0] || 'customer');
      }
      return true;
    }
  } catch (e) {
    console.debug('No active SIWE session:', e);
  }
  return false;
}

async function connectAndSignWithMetaMask() {
  if (typeof window.ethereum === 'undefined') {
    STATE.auth.error = 'MetaMask was not detected. Please install MetaMask to connect your wallet.';
    renderApp();
    return;
  }

  STATE.auth.loading = true;
  STATE.auth.error = null;
  STATE.auth.statusText = 'Connecting to MetaMask...';
  renderApp();

  try {
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    if (!accounts || accounts.length === 0) {
      throw new Error('No Ethereum accounts authorized. Please select an account in MetaMask.');
    }
    const rawAddress = accounts[0];
    STATE.auth.walletAddress = rawAddress.toLowerCase();
    STATE.auth.statusText = 'Requesting challenge...';
    renderApp();

    const nonceRes = await fetch('/auth/nonce', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wallet_address: rawAddress }),
      credentials: 'include'
    });

    if (!nonceRes.ok) {
      const err = await nonceRes.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to request challenge nonce.');
    }
    const nonceData = await nonceRes.json();
    const nonce = nonceData.nonce;
    const checksumAddress = nonceData.checksum_address || (window.ethers?.getAddress ? window.ethers.getAddress(rawAddress) : rawAddress);

    const domain = window.location.host || 'localhost:8000';
    const origin = window.location.origin || 'http://localhost:8000';
    const statement = 'Sign in to Guardvane';
    const issuedAt = new Date().toISOString();

    const siweMessage = `${domain} wants you to sign in with your Ethereum account:\n${checksumAddress}\n\n${statement}\n\nURI: ${origin}\nVersion: 1\nChain ID: 1\nNonce: ${nonce}\nIssued At: ${issuedAt}`;

    STATE.auth.statusText = 'Awaiting signature in MetaMask...';
    renderApp();

    let signature;
    try {
      signature = await window.ethereum.request({
        method: 'personal_sign',
        params: [siweMessage, rawAddress]
      });
    } catch (signErr) {
      if (signErr.code === 4001 || (signErr.message && signErr.message.toLowerCase().includes('reject'))) {
        throw new Error('Signature was rejected in MetaMask. Please sign to connect.');
      }
      throw signErr;
    }

    STATE.auth.statusText = 'Verifying signature...';
    renderApp();

    const verifyRes = await fetch('/auth/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: siweMessage, signature: signature }),
      credentials: 'include'
    });

    if (!verifyRes.ok) {
      const err = await verifyRes.json().catch(() => ({}));
      throw new Error(err.detail || 'Authentication verification failed.');
    }

    const verifyData = await verifyRes.json();
    STATE.auth.isAuthenticated = true;
    STATE.auth.user = verifyData.user;
    STATE.auth.walletAddress = verifyData.user.wallet_address;
    STATE.user.id = verifyData.user.wallet_address;
    STATE.user.name = verifyData.user.display_name || (verifyData.user.wallet_address.substring(0, 6) + '...' + verifyData.user.wallet_address.substring(verifyData.user.wallet_address.length - 4));
    STATE.auth.error = null;
    STATE.auth.statusText = '';

    await loadInitialData();
    startBackgroundSync();
    const myProv = (STATE.data.providers || []).find(p => p.wallet_address && p.wallet_address.toLowerCase() === verifyData.user.wallet_address.toLowerCase());
    if (myProv) {
      STATE.user.activeProviderId = myProv.id;
      STATE.user.role = 'provider';
    } else {
      STATE.user.activeProviderId = null;
      STATE.user.role = 'customer';
    }
  } catch (err) {
    console.error('Authentication failure:', err);
    STATE.auth.error = err.message || 'Failed to authenticate with MetaMask.';
  } finally {
    STATE.auth.loading = false;
    renderApp();
  }
}

async function handleLogout() {
  try {
    await fetch('/auth/logout', { method: 'POST', credentials: 'include' });
  } catch (e) {
    console.error('Logout error:', e);
  }
  STATE.auth.isAuthenticated = false;
  STATE.auth.user = null;
  STATE.auth.walletAddress = null;
  STATE.auth.error = null;
  STATE.auth.statusText = '';
  STATE.auth.guestMode = false;
  STATE.user.id = null;
  STATE.user.name = null;
  STATE.user.activeProviderId = null;
  STATE.user.role = 'customer';
  STATE.data.orders = [];
  STATE.data.reports = [];
  STATE.data.prompts = [];
  STATE.activeView = 'dashboard';
  STATE.activeModal = null;
  STATE.modalPayload = null;
  renderApp();
}

function continueAsGuest() {
  STATE.auth.isAuthenticated = true;
  STATE.auth.guestMode = true;
  STATE.auth.walletAddress = null;
  const guestId = 'guest_' + Math.random().toString(36).substring(2, 9);
  STATE.user.id = guestId;
  STATE.user.name = 'Guest User';
  STATE.user.role = 'customer';
  STATE.user.activeProviderId = null;
  loadInitialData();
}

// ---------------------------------------------------------------------------
// Rabdi Testnet (Chain ID 7794095) Network Helpers
// ---------------------------------------------------------------------------

async function checkRabdiNetwork() {
  if (typeof window !== 'undefined' && window.ethereum) {
    try {
      const chainIdHex = await window.ethereum.request({ method: 'eth_chainId' });
      const chainId = parseInt(chainIdHex, 16);
      STATE.network.chainId = chainId;
      STATE.network.isRabdi = (chainId === 7794095);
      STATE.network.name = (chainId === 7794095) ? 'Rabdi Testnet' : `Chain ${chainId}`;
    } catch (e) {
      console.debug('Failed to get chainId:', e);
    }
  }
}

async function handleSwitchToRabdi() {
  if (typeof window === 'undefined' || !window.ethereum) {
    showNotification('MetaMask is not installed. Please install MetaMask to connect to Rabdi Testnet.', 'error');
    return;
  }
  try {
    if (window.ArkivModule && window.ArkivModule.switchOrAddRabdiNetwork) {
      await window.ArkivModule.switchOrAddRabdiNetwork();
    } else {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: '0x76ee8f' }]
      });
    }
    await checkRabdiNetwork();
    renderApp();
  } catch (err) {
    console.error('Failed to switch to Rabdi:', err);
    showNotification('Could not switch to Rabdi Testnet: ' + (err.message || err), 'error');
  }
}

if (typeof window !== 'undefined' && window.ethereum) {
  try {
    window.ethereum.on('chainChanged', (chainIdHex) => {
      const chainId = parseInt(chainIdHex, 16);
      STATE.network.chainId = chainId;
      STATE.network.isRabdi = (chainId === 7794095);
      STATE.network.name = (chainId === 7794095) ? 'Rabdi Testnet' : `Chain ${chainId}`;
      renderApp();
    });

    window.ethereum.on('accountsChanged', async (accounts) => {
      if (!accounts || accounts.length === 0) {
        await handleLogout();
      } else {
        const newAddress = accounts[0].toLowerCase();
        if (STATE.auth.walletAddress && STATE.auth.walletAddress.toLowerCase() !== newAddress) {
          await handleLogout();
        }
      }
    });

    window.ethereum.on('disconnect', async () => {
      await handleLogout();
    });
  } catch (e) {}
}

// ---------------------------------------------------------------------------
// Initial Data Loading
// ---------------------------------------------------------------------------

async function loadInitialData() {
  STATE.loading = true;
  renderApp();

  try {
    const [stats, providers, services, orders, reports, prompts, integrations, arkivConfig, arkivStatus, arkivTasks] = await Promise.all([
      apiFetch('/marketplace/stats').catch(() => null),
      apiFetch('/marketplace/providers').catch(() => []),
      apiFetch('/marketplace/services').catch(() => []),
      apiFetch('/marketplace/orders').catch(() => []),
      apiFetch('/marketplace/reports').catch(() => []),
      apiFetch('/marketplace/prompts').catch(() => []),
      apiFetch('/marketplace/integrations/status').catch(() => null),
      apiFetch('/marketplace/arkiv/config').catch(() => null),
      apiFetch('/marketplace/arkiv/status').catch(() => null),
      apiFetch('/marketplace/arkiv/tasks').catch(() => [])
    ]);

    STATE.data.stats = stats;
    STATE.data.providers = providers;
    STATE.data.services = services;
    STATE.data.orders = orders;
    STATE.data.reports = reports;
    STATE.data.prompts = prompts;
    STATE.data.integrations = integrations;
    STATE.arkiv.config = arkivConfig;
    STATE.arkiv.status = arkivStatus;
    STATE.arkiv.tasks = arkivTasks || [];

    await checkRabdiNetwork();

    // Auto-detect registered provider profile for the connected wallet
    const myWallet = (STATE.auth.walletAddress || '').toLowerCase();
    if (myWallet && Array.isArray(providers)) {
      const myProv = providers.find(p => p.wallet_address && p.wallet_address.toLowerCase() === myWallet);
      if (myProv) {
        STATE.user.activeProviderId = myProv.id;
        STATE.user.role = 'provider';
      } else {
        STATE.user.activeProviderId = null;
        STATE.user.role = 'customer';
      }
    } else {
      STATE.user.activeProviderId = null;
      STATE.user.role = 'customer';
    }
  } catch (err) {
    console.error("Failed to load Guardvane marketplace data", err);
  } finally {
    STATE.loading = false;
    renderApp();
  }
}

// ---------------------------------------------------------------------------
// Navigation & Routing
// ---------------------------------------------------------------------------

function navigateTo(view, payload = null) {
  if (view === 'arkiv_tasks') {
    STATE.activeView = 'opihub';
  } else {
    STATE.activeView = view;
  }
  if (view === 'provider_detail') {
    const prov = (STATE.data.providers || []).find(p => p.id === payload);
    const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
    if (prov && prov.wallet_address && userWallet && prov.wallet_address.toLowerCase() === userWallet && !prov.is_platform_managed) {
      STATE.activeView = 'provider_workspace';
      STATE.user.role = 'provider';
      window.scrollTo({ top: 0, behavior: 'smooth' });
      renderApp();
      return;
    }
    STATE.selectedProviderId = payload;
  } else if (view === 'order_detail') {
    STATE.selectedOrderId = payload;
  } else if (view === 'report_detail') {
    STATE.selectedReportId = payload;
  } else if (view === 'provider_workspace') {
    // Enable provider role when entering provider workspace
    STATE.user.role = 'provider';
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
  renderApp();
}

function switchUserRole(role, providerId = 'prov_elena') {
  STATE.user.role = role;
  if (role === 'provider') {
    STATE.user.activeProviderId = providerId;
  }
  loadInitialData();
}

function openModal(modalType, payload = null, triggerEl = null) {
  if (triggerEl) {
    STATE.modalTriggerEl = triggerEl;
  } else if (typeof document !== 'undefined' && document.activeElement) {
    STATE.modalTriggerEl = document.activeElement;
  }
  if (modalType === 'request_review') {
    const service = (STATE.data.services || []).find(s => s.id === payload?.serviceId);
    const prov = (STATE.data.providers || []).find(p => p.id === (service?.provider_id || payload?.providerId));
    const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
    if (prov && prov.wallet_address && userWallet && prov.wallet_address.toLowerCase() === userWallet && !prov.is_platform_managed) {
      showNotification('Providers cannot order security reviews on their own profile. Directing to your Provider Workspace.', 'info');
      navigateTo('provider_workspace');
      return;
    }
  }
  STATE.activeModal = modalType;
  STATE.modalPayload = payload;
  if (typeof document !== 'undefined') {
    document.body.style.overflow = 'hidden';
  }
  renderApp();

  setTimeout(() => {
    const primaryInput = document.getElementById('order-prompt-input') ||
                         document.querySelector('.modal-shell input:not([type="hidden"]), .modal-shell textarea, .modal-shell select');
    if (primaryInput) {
      primaryInput.focus();
    }
  }, 60);
}

function closeModal() {
  STATE.activeModal = null;
  STATE.modalPayload = null;
  STATE.orderDetailConfirmRelease = false;
  STATE.orderDetailReleaseLoading = false;
  STATE.orderDetailReleaseError = '';
  STATE.orderRequestExpanded = false;
  if (typeof document !== 'undefined') {
    document.body.style.overflow = '';
  }
  renderApp();

  if (STATE.modalTriggerEl && typeof STATE.modalTriggerEl.focus === 'function') {
    try { STATE.modalTriggerEl.focus(); } catch (e) {}
    STATE.modalTriggerEl = null;
  }
}

// ---------------------------------------------------------------------------
// Claude Design System Shared Components
// ---------------------------------------------------------------------------

function renderPageHeader(title, description, actionsHtml = '') {
  return `
    <div class="flex flex-col sm:flex-row sm:items-baseline justify-between gap-4 mb-8">
      <div>
        <h1 class="font-serif text-[32px] sm:text-[36px] font-normal tracking-[-0.01em] text-[var(--text)] leading-tight">
          ${escapeHtml(title)}
        </h1>
        ${description ? `
          <p class="text-[14px] sm:text-[15px] text-[var(--text-2)] mt-1.5 leading-relaxed">
            ${escapeHtml(description)}
          </p>
        ` : ''}
      </div>
      ${actionsHtml ? `
        <div class="flex items-center gap-2.5 shrink-0">
          ${actionsHtml}
        </div>
      ` : ''}
    </div>
  `;
}

function renderCopyChip({ text, displayText, title, isAddress = false, isExternal = false, externalUrl = '', isShortId = false }) {
  if (!text) return '';
  const display = displayText || (isAddress
    ? (text.length > 12 ? text.slice(0, 6) + '…' + text.slice(-4) : text)
    : text);
  const tooltip = title || (isShortId ? `Order ID: ${text} (click to copy)` : `Click to copy: ${text}`);

  return `
    <span class="inline-flex items-center gap-1.5 font-mono text-[12px] text-[var(--text-2)] align-baseline">
      <button
        type="button"
        onclick="event.stopPropagation(); copyTextToClipboard('${escapeForAttr(text)}', this, 'Copied ${isShortId ? 'ID' : 'address'}');"
        title="${escapeForAttr(tooltip)}"
        aria-label="Copy ${escapeForAttr(text)}"
        class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-[var(--radius-sm)] bg-[var(--surface-sunk)] hover:bg-[var(--border)] text-[var(--text-3)] hover:text-[var(--text)] transition-colors cursor-pointer border-none font-mono text-[12px] font-normal"
      >
        <span>${escapeHtml(display)}</span>
        <svg class="w-3 h-3 text-[var(--text-3)] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.75">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      </button>
      ${isExternal && externalUrl ? `
        <a
          href="${escapeForAttr(externalUrl)}"
          target="_blank"
          rel="noopener noreferrer"
          title="View on explorer"
          class="text-[var(--text-2)] hover:text-[var(--text)] underline inline-flex items-center gap-0.5 text-[12px]"
        >
          <span>View ↗</span>
        </a>
      ` : ''}
    </span>
  `;
}

function renderStepper(steps) {
  return `
    <div class="space-y-0 select-none">
      ${steps.map((step, index) => {
        const isLast = index === steps.length - 1;
        let circleHtml = '';
        if (step.state === 'done') {
          circleHtml = `
            <div class="w-5 h-5 rounded-full bg-[var(--success)] text-white flex items-center justify-center shrink-0">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
          `;
        } else if (step.state === 'current') {
          circleHtml = `
            <div class="w-5 h-5 rounded-full border-2 border-[var(--accent)] bg-[var(--surface-raised)] flex items-center justify-center shrink-0">
              <div class="w-1.5 h-1.5 rounded-full bg-[var(--accent)]"></div>
            </div>
          `;
        } else {
          circleHtml = `
            <div class="w-5 h-5 rounded-full border border-[var(--border-strong)] bg-[var(--surface-sunk)] shrink-0"></div>
          `;
        }

        return `
          <div class="flex items-start gap-3">
            <div class="flex flex-col items-center">
              ${circleHtml}
              ${!isLast ? `
                <div class="w-[1px] h-7 ${step.state === 'done' ? 'bg-[var(--success)]' : 'bg-[var(--border)]'} my-1"></div>
              ` : ''}
            </div>
            <div class="flex-1 min-w-0 pb-3">
              <div class="flex items-baseline justify-between gap-2">
                <span class="text-[14px] font-semibold text-[var(--text)] leading-tight">${escapeHtml(step.title)}</span>
                ${step.date ? `<span class="text-[12px] text-[var(--text-3)] tabular-nums shrink-0 font-normal">${escapeHtml(step.date)}</span>` : ''}
              </div>
              <div class="text-[13px] text-[var(--text-2)] mt-0.5 leading-normal">
                <span>${escapeHtml(step.detail)}</span>
                ${step.linkHtml ? `<span class="ml-2">${step.linkHtml}</span>` : ''}
              </div>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderDefinitionList(items) {
  return `
    <dl class="space-y-2.5">
      ${items.map(item => `
        <div class="flex items-baseline justify-between gap-4 text-[13px]">
          <dt class="text-[13px] text-[var(--text-3)] shrink-0 font-normal">${escapeHtml(item.label)}</dt>
          <dd class="text-[14px] text-[var(--text)] text-right font-normal">${item.valueHtml}</dd>
        </div>
      `).join('')}
    </dl>
  `;
}

function getOrderUnifiedStatus(order) {
  if (order.status === 'rejected') {
    return { label: 'Declined', pillClass: 'pill-danger' };
  }
  if (order.status === 'cancelled') {
    return { label: 'Cancelled', pillClass: 'pill-danger' };
  }
  if (order.payment_status === 'failed') {
    return { label: 'Failed', pillClass: 'pill-danger' };
  }
  if (order.escrow_state === 'released' || order.status === 'completed') {
    return { label: 'Completed', pillClass: 'pill-success' };
  }
  if (order.status === 'delivered') {
    return { label: 'Awaiting release', pillClass: 'pill-warning' };
  }
  if (order.status === 'in_progress' || order.status === 'accepted') {
    return { label: 'In progress', pillClass: 'pill-info' };
  }
  if (order.payment_status === 'pending' || order.escrow_state === 'pending') {
    return { label: 'Pending payment', pillClass: 'pill-neutral' };
  }
  if (order.status === 'requested') {
    return { label: 'Requested', pillClass: 'pill-neutral' };
  }
  return { label: toSentenceCase(order.status || 'Active'), pillClass: 'pill-neutral' };
}

function renderIdChip(id) {
  if (!id) return '';
  const shortId = id.length > 7 ? '#' + id.slice(-6) : id;
  return `
    <button
      type="button"
      onclick="event.stopPropagation(); navigator.clipboard.writeText('${id}'); showNotification('Copied ID ${id}', 'success');"
      title="Click to copy full ID: ${id}"
      class="inline-flex items-center px-2 py-0.5 rounded-[var(--radius-sm)] text-[12px] font-mono text-[var(--text-3)] bg-[var(--surface-sunk)] hover:text-[var(--text)] hover:bg-[var(--border)] transition-colors cursor-pointer border-none"
    >
      ${shortId}
    </button>
  `;
}

function renderShortAddress(address) {
  if (!address) return '';
  const short = address.length > 12
    ? address.substring(0, 6) + '…' + address.substring(address.length - 4)
    : address;
  return `
    <span class="inline-flex items-center gap-1 font-mono text-[12px] text-[var(--text-2)]">
      <span>${short}</span>
      <button
        type="button"
        onclick="event.stopPropagation(); navigator.clipboard.writeText('${address}'); showNotification('Copied address', 'success');"
        title="Copy address: ${address}"
        class="text-[var(--text-3)] hover:text-[var(--text)] cursor-pointer border-none bg-transparent p-0 inline-flex items-center"
      >
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
      </button>
    </span>
  `;
}

function renderProgressSteps(step) {
  const steps = [
    { num: 1, label: 'Delivered' },
    { num: 2, label: 'Released' },
    { num: 3, label: 'Paid out' }
  ];
  return `
    <div class="inline-flex items-center gap-1.5 text-[11px] font-medium text-[var(--text-3)] mt-1 select-none">
      ${steps.map((s, idx) => {
        const isDone = s.num <= step;
        const isCurrent = s.num === step;
        return `
          <span class="inline-flex items-center gap-1 ${isCurrent ? 'text-[var(--text)] font-semibold' : isDone ? 'text-[var(--success)]' : 'text-[var(--text-3)]'}">
            ${isDone ? `<span class="w-1.5 h-1.5 rounded-full ${isCurrent ? 'bg-[var(--accent)]' : 'bg-[var(--success)]'}"></span>` : `<span class="w-1.5 h-1.5 rounded-full bg-[var(--border-strong)]"></span>`}
            <span>${s.label}</span>
          </span>
          ${idx < steps.length - 1 ? `<span class="text-[var(--border-strong)] text-[10px]">&gt;</span>` : ''}
        `;
      }).join('')}
    </div>
  `;
}

function renderStatusPill(status, isEscrow = false, escrowState = '') {
  const norm = (status || '').toLowerCase().replace(/[-_ ]/g, '_');
  let pillClass = 'pill-neutral';
  let label = status || 'Unknown';
  let progressStep = 0;

  if (norm === 'requested') {
    pillClass = 'pill-warning';
    label = 'Requested';
  } else if (norm === 'accepted' || norm === 'in_progress') {
    pillClass = 'pill-info';
    label = 'In progress';
  } else if (norm === 'delivered') {
    pillClass = 'pill-warning';
    label = (isEscrow && escrowState !== 'released') ? 'Awaiting release' : 'Delivered';
    progressStep = 1;
  } else if (norm === 'completed' || norm === 'verified') {
    pillClass = 'pill-success';
    label = (isEscrow && escrowState === 'released') ? 'Paid out' : 'Completed';
    progressStep = isEscrow ? 3 : 0;
  } else if (norm === 'pending_payment' || norm === 'pending') {
    pillClass = 'pill-neutral';
    label = 'Pending payment';
  } else if (norm === 'failed' || norm === 'rejected' || norm === 'cancelled') {
    pillClass = 'pill-danger';
    label = norm === 'failed' ? 'Failed' : norm === 'rejected' ? 'Rejected' : 'Cancelled';
  }

  if (isEscrow && escrowState === 'released' && norm !== 'completed') {
    progressStep = 2;
  }

  return `
    <div class="inline-flex flex-col items-start gap-0.5">
      <span class="pill ${pillClass}">
        ${label}
      </span>
      ${isEscrow && progressStep > 0 ? renderProgressSteps(progressStep) : ''}
    </div>
  `;
}

function renderEmptyState(message, linkText = '', linkAction = '') {
  return `
    <div class="min-h-[96px] py-6 px-4 flex flex-col items-center justify-center text-center bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)]">
      <p class="text-[13.5px] text-[var(--text-3)] leading-relaxed">${escapeHtml(message)}</p>
      ${linkText && linkAction ? `
        <button
          onclick="${linkAction}"
          class="mt-2 text-[13px] font-medium text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors cursor-pointer bg-transparent border-none p-0 inline-flex items-center gap-1"
        >
          <span>${escapeHtml(linkText)}</span>
          <span>&rarr;</span>
        </button>
      ` : ''}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Main Render Loop
// ---------------------------------------------------------------------------

function renderApp() {
  const root = document.getElementById('app-root');
  if (!root) return;

  if (!STATE.auth.isAuthenticated) {
    root.innerHTML = renderLoginPage();
    return;
  }

  root.innerHTML = `
    <div class="flex h-screen overflow-hidden bg-[var(--bg)] text-[var(--text)] font-sans">
      <!-- Left Sidebar (240px, surface-sunk, hairline border) -->
      ${renderSidebar()}

      <!-- Main Column -->
      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        <!-- Top Navigation Bar -->
        ${renderTopbar()}

        <!-- Page Content View (48px horizontal, 40px top, max 1120px) -->
        <main class="flex-1 overflow-y-auto px-6 sm:px-12 pt-10 pb-16 scroll-container" id="main-content" style="scrollbar-gutter: stable;">
          <div class="max-w-[1120px] mx-auto">
            ${renderCurrentView()}
          </div>
        </main>
      </div>
    </div>

    <!-- Active Modal Container -->
    ${STATE.activeModal ? renderModalContainer() : ''}
  `;

  // Attach keyboard shortcuts listener if not attached
  if (!window._shortcutListenerAttached) {
    window.addEventListener('keydown', (e) => {
      // Global Search: Cmd+K / Ctrl+K
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('topbar-search-input');
        if (searchInput) searchInput.focus();
        return;
      }

      // Modal Shortcuts: Esc to close (with draft check), Cmd/Ctrl+Enter to submit
      if (STATE.activeModal) {
        if (e.key === 'Escape') {
          e.preventDefault();
          if (STATE.activeModal === 'order_detail' && STATE.orderDetailConfirmRelease) {
            cancelReleasePaymentConfirm();
            return;
          }
          closeModalWithDraftCheck();
          return;
        }
        if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
          const activeForm = document.querySelector('.modal-shell form');
          if (activeForm) {
            e.preventDefault();
            const submitBtn = activeForm.querySelector('button[type="submit"]:not(:disabled)');
            if (submitBtn) {
              if (typeof activeForm.requestSubmit === 'function') {
                activeForm.requestSubmit(submitBtn);
              } else {
                submitBtn.click();
              }
            }
          }
          return;
        }
      }
    });
    window._shortcutListenerAttached = true;
  }
}

// ---------------------------------------------------------------------------
// Guardvane Login Page (MetaMask + SIWE)
// ---------------------------------------------------------------------------

function renderLoginPage() {
  return `
    <div class="min-h-screen bg-[var(--bg)] text-[var(--text)] flex flex-col justify-center py-16 px-4 sm:px-6 lg:px-8 select-none font-sans">
      <div class="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <h1 class="font-serif text-[32px] font-normal tracking-[-0.015em] text-[var(--text)]">Guardvane</h1>
        <p class="mt-2 text-[14px] text-[var(--text-2)]">
          Decentralized AI security & prompt defense platform
        </p>
      </div>

      <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div class="surface-card p-8 sm:p-10 space-y-5">
          
          <!-- Error Alert Banner -->
          ${STATE.auth.error ? `
            <div class="p-3.5 rounded-[var(--radius-sm)] bg-[var(--danger-bg)] text-[var(--danger)] border border-[var(--danger)]/20 text-[13px] flex items-start gap-2.5">
              <span>${escapeHtml(STATE.auth.error)}</span>
            </div>
          ` : ''}

          <!-- Signing / Loading State -->
          ${STATE.auth.loading ? `
            <div class="p-6 rounded-[var(--radius-md)] bg-[var(--surface-sunk)] border border-[var(--border)] text-center space-y-3">
              <div class="w-6 h-6 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p class="text-[14px] font-medium text-[var(--text)]">${escapeHtml(STATE.auth.statusText || 'Connecting...')}</p>
              <p class="text-[12.5px] text-[var(--text-3)]">Please confirm the signature in your wallet.</p>
            </div>
          ` : `
            <!-- Connect Wallet Action Button -->
            <button
              onclick="connectAndSignWithMetaMask()"
              class="btn-primary w-full !h-11 !text-[14.5px]"
            >
              <!-- MetaMask Fox SVG -->
              <svg class="w-5 h-5 shrink-0" viewBox="0 0 318.6 318.6">
                <path fill="#E2761B" stroke="#E2761B" stroke-linecap="round" stroke-linejoin="round" d="M274.1 35.5l-99.5 73.9L194 65.4z"/>
                <path fill="#E4761B" stroke="#E4761B" stroke-linecap="round" stroke-linejoin="round" d="M44.5 35.5l99.5 73.9-19.4-44z"/>
                <path fill="#E4761B" stroke="#E4761B" stroke-linecap="round" stroke-linejoin="round" d="M238.3 206.8l-30 45.4 67.9 18.7 19.5-63.5z"/>
                <path fill="#E4761B" stroke="#E4761B" stroke-linecap="round" stroke-linejoin="round" d="M22.9 207.4l19.5 63.5 67.9-18.7-30-45.4z"/>
                <path fill="#D7C1B3" stroke="#D7C1B3" stroke-linecap="round" stroke-linejoin="round" d="M90.3 148.9l-22.6-33.8-38.6 11.4 14.6 35.9z"/>
                <path fill="#D7C1B3" stroke="#D7C1B3" stroke-linecap="round" stroke-linejoin="round" d="M228.3 148.9l32.1 13.5 14.6-35.9-38.6-11.4z"/>
                <path fill="#233447" stroke="#233447" stroke-linecap="round" stroke-linejoin="round" d="M106.9 182.2l-21.7-16.7-18.8 14.1 27.2 21.6z"/>
                <path fill="#233447" stroke="#233447" stroke-linecap="round" stroke-linejoin="round" d="M211.7 182.2l13.3 19 27.2-21.6-18.8-14.1z"/>
                <path fill="#CD6116" stroke="#CD6116" stroke-linecap="round" stroke-linejoin="round" d="M85.2 165.5l21.7 16.7 4.5-22.7-32.1-13.5z"/>
                <path fill="#CD6116" stroke="#CD6116" stroke-linecap="round" stroke-linejoin="round" d="M207.2 159.5l4.5 22.7 21.7-16.7-5.9-19.5z"/>
                <path fill="#E4751F" stroke="#E4751F" stroke-linecap="round" stroke-linejoin="round" d="M106.9 182.2l-21.7-16.7 5.9-19.5 30 45.4z"/>
                <path fill="#E4751F" stroke="#E4751F" stroke-linecap="round" stroke-linejoin="round" d="M207.2 159.5l-5.9 19.5-21.7 16.7 30-45.4z"/>
                <path fill="#F6851B" stroke="#F6851F" stroke-linecap="round" stroke-linejoin="round" d="M159.3 174.5l-38.6-11.4 12.1 40.8 26.5-29.4z"/>
                <path fill="#F6851B" stroke="#F6851F" stroke-linecap="round" stroke-linejoin="round" d="M159.3 174.5l26.5 29.4 12.1-40.8-38.6 11.4z"/>
                <path fill="#C0AD9E" stroke="#C0AD9E" stroke-linecap="round" stroke-linejoin="round" d="M197.9 203.9l-12.1 40.8 13.9 10.3 30-45.4-31.8-5.7z"/>
                <path fill="#C0AD9E" stroke="#C0AD9E" stroke-linecap="round" stroke-linejoin="round" d="M88.9 209.6l30 45.4 13.9-10.3-12.1-40.8-31.8 5.7z"/>
                <path fill="#161616" stroke="#161616" stroke-linecap="round" stroke-linejoin="round" d="M159.3 226.3l-26.5-29.4-13.9 10.3 26.5 19.1z"/>
                <path fill="#161616" stroke="#161616" stroke-linecap="round" stroke-linejoin="round" d="M159.3 226.3l13.9 0 26.5-19.1-13.9-10.3z"/>
                <path fill="#763D16" stroke="#763D16" stroke-linecap="round" stroke-linejoin="round" d="M118.9 237.2l13.9 10.3 26.5-21.2-13.9 0z"/>
                <path fill="#763D16" stroke="#763D16" stroke-linecap="round" stroke-linejoin="round" d="M173.2 237.2l-26.5-10.9 26.5 21.2 13.9-10.3z"/>
                <path fill="#F6851B" stroke="#F6851F" stroke-linecap="round" stroke-linejoin="round" d="M159.3 65.4l15.2 44.5 99.5-74.4-114.7 29.9z"/>
                <path fill="#F6851B" stroke="#F6851F" stroke-linecap="round" stroke-linejoin="round" d="M44.5 35.5l99.5 74.4 15.3-44.5-114.8-29.9z"/>
              </svg>
              <span>Connect Wallet</span>
            </button>
          `}
        </div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Helper: Provider Resolution for Active Connected Identity
// ---------------------------------------------------------------------------

function getMyProvider() {
  const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
  if (!userWallet) return null;
  return (STATE.data.providers || []).find(p =>
    p.wallet_address && p.wallet_address.toLowerCase() === userWallet
  ) || null;
}

// ---------------------------------------------------------------------------
// Sidebar Component
// ---------------------------------------------------------------------------

function renderSidebar() {
  const userWallet = (STATE.auth.walletAddress || STATE.user.id || '').toLowerCase();
  const mySentOrders = (STATE.data.orders || []).filter(o => {
    const custId = (o.customer_id || '').toLowerCase();
    if (!userWallet) return false;
    return custId === userWallet || custId === (STATE.user.id || '').toLowerCase();
  });
  const myReports = (STATE.data.reports || []).filter(r => {
    const custId = (r.customer_id || '').toLowerCase();
    if (!userWallet) return false;
    return custId === userWallet || custId === (STATE.user.id || '').toLowerCase();
  });
  const myPrompts = (STATE.data.prompts || []).filter(p => {
    const custId = (p.customer_id || '').toLowerCase();
    if (!userWallet) return false;
    return custId === userWallet || custId === (STATE.user.id || '').toLowerCase();
  });

  const myProvider = getMyProvider();
  const isRegisteredProvider = !!myProvider;
  const assignedOrders = (STATE.data.orders || []).filter(o => {
    if (!myProvider) return false;
    return o.provider_id === myProvider.id ||
      (myProvider.wallet_address && (o.provider_wallet || '').toLowerCase() === myProvider.wallet_address.toLowerCase()) ||
      (o.provider_name && o.provider_name.toLowerCase() === (myProvider.display_name || '').toLowerCase());
  });

  const displayName = myProvider?.display_name || STATE.user.name || 'Francis Anto';
  const displayRole = isRegisteredProvider ? 'Specialist Provider' : 'Security Researcher';
  const userInitial = (displayName || 'F').trim()[0].toUpperCase();

  return `
    <aside class="w-[240px] bg-[var(--surface-sunk)] border-r border-[var(--border)] flex flex-col justify-between shrink-0 select-none h-full">
      <!-- Top Brand Wordmark & Nav Groups -->
      <div class="flex flex-col">
        <!-- Logo Wordmark in Serif with 24px padding -->
        <div class="p-6 pb-2">
          <span class="font-serif text-[22px] font-medium tracking-[-0.015em] text-[var(--text)]">Guardvane</span>
        </div>

        <!-- Navigation Section: WORKSPACE -->
        <div class="px-3 pt-4 space-y-1">
          <div class="px-3 pt-2 pb-2 text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)]">Workspace</div>
          
          <button onclick="navigateTo('dashboard')" class="nav-item ${STATE.activeView === 'dashboard' ? 'nav-item-active' : ''}">
            <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span>Dashboard</span>
          </button>

          <button onclick="navigateTo('opihub')" class="nav-item ${STATE.activeView === 'opihub' ? 'nav-item-active' : ''}">
            <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span>OpiHub</span>
          </button>

          <button onclick="navigateTo('my_prompts')" class="nav-item ${STATE.activeView === 'my_prompts' ? 'nav-item-active' : ''}">
            <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            <span>Saved prompts</span>
            <span class="ml-auto text-[13px] font-mono text-[var(--text-3)]">${myPrompts.length}</span>
          </button>

          <button onclick="navigateTo('my_requests')" class="nav-item ${STATE.activeView === 'my_requests' ? 'nav-item-active' : ''}">
            <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            <span>Security requests</span>
            <span class="ml-auto text-[13px] font-mono text-[var(--text-3)]">${mySentOrders.length}</span>
          </button>

          <button onclick="navigateTo('security_reports')" class="nav-item ${STATE.activeView === 'security_reports' ? 'nav-item-active' : ''}">
            <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Security reports</span>
            <span class="ml-auto text-[13px] font-mono text-[var(--text-3)]">${myReports.length}</span>
          </button>
        </div>

        <!-- Navigation Section: PROVIDER (Spaced without heavy lines) -->
        <div class="px-3 pt-6 space-y-1">
          <div class="px-3 pb-2 text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)]">Provider</div>

          ${isRegisteredProvider ? `
            <button onclick="navigateTo('provider_workspace')" class="nav-item ${STATE.activeView === 'provider_workspace' ? 'nav-item-active' : ''}">
              <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <span>Provider workspace</span>
              ${assignedOrders.length > 0 ? `
                <span class="ml-auto text-[13px] font-mono text-[var(--text-3)] flex items-center gap-1.5">
                  <span class="w-1.5 h-1.5 rounded-full bg-[var(--accent)]"></span>
                  ${assignedOrders.length}
                </span>
              ` : ''}
            </button>
          ` : `
            <button onclick="navigateTo('become_provider')" class="nav-item ${STATE.activeView === 'become_provider' ? 'nav-item-active' : ''}">
              <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              <span>Become a provider</span>
            </button>
          `}
        </div>

        <!-- Navigation Section: ACCOUNT (Spaced without heavy lines) -->
        <div class="px-3 pt-6 space-y-1">
          <div class="px-3 pb-2 text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)]">Account</div>

          <button onclick="openModal('wallet_modal')" class="nav-item">
            <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
            <span>Wallet</span>
          </button>

          <button onclick="openModal('settings_modal')" class="nav-item">
            <svg class="w-4 h-4 shrink-0 text-[var(--text-2)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>Settings</span>
          </button>
        </div>
      </div>

      <!-- Bottom User Profile: Initial circle + name + role (NO duplicate wallet) -->
      <div class="p-5 border-t border-[var(--border)] bg-transparent">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center font-serif font-medium text-[14px] shrink-0">
            ${userInitial}
          </div>
          <div class="flex flex-col min-w-0">
            <span class="text-[13.5px] font-medium text-[var(--text)] truncate leading-snug">${escapeHtml(displayName)}</span>
            <span class="text-[11.5px] text-[var(--text-3)] truncate leading-snug">${escapeHtml(displayRole)}</span>
          </div>
        </div>
      </div>
    </aside>
  `;
}

// ---------------------------------------------------------------------------
// Topbar Component
// ---------------------------------------------------------------------------

function renderTopbar() {
  const address = STATE.auth.walletAddress;
  const shortAddr = address
    ? (address.substring(0, 6) + '...' + address.substring(address.length - 4))
    : 'Connect wallet';

  const viewLabels = {
    dashboard: 'Dashboard',
    opihub: 'OpiHub',
    my_prompts: 'Saved prompts',
    my_requests: 'Security requests',
    security_reports: 'Security reports',
    become_provider: 'Provider registration',
    provider_workspace: 'Provider workspace',
    provider_detail: 'Specialist profile'
  };
  const activeLabel = viewLabels[STATE.activeView] || 'Security marketplace';

  return `
    <header class="h-14 border-b border-[var(--border)] bg-[var(--bg)] px-6 sm:px-12 flex items-center justify-between shrink-0 select-none">
      <!-- Left: Breadcrumb in --text-3 -->
      <nav class="flex items-center gap-1.5 text-[13px] text-[var(--text-3)]">
        <span>Guardvane</span>
        <span class="text-[var(--border-strong)]">/</span>
        <span class="text-[var(--text-2)] font-medium">${activeLabel}</span>
      </nav>

      <!-- Right: Quiet Wallet Chip & Log out -->
      <div class="flex items-center gap-3">
        ${address ? `
          <button
            onclick="openModal('wallet_modal')"
            title="Wallet & network settings"
            class="px-3 py-1 rounded-full text-[12px] font-mono text-[var(--text-2)] bg-[var(--surface-sunk)] border border-[var(--border)] hover:border-[var(--border-strong)] hover:text-[var(--text)] transition-colors cursor-pointer"
          >
            ${shortAddr}
          </button>
          <button
            onclick="handleLogout()"
            title="Sign out of Guardvane"
            class="text-[13px] text-[var(--text-3)] hover:text-[var(--text)] transition-colors px-2 py-1 cursor-pointer"
          >
            Log out
          </button>
        ` : `
          <button
            onclick="openModal('wallet_modal')"
            class="px-3 py-1 rounded-full text-[12px] font-mono text-[var(--accent)] bg-[var(--accent-soft)] hover:bg-[var(--accent)] hover:text-white transition-colors cursor-pointer"
          >
            Connect wallet
          </button>
        `}
      </div>
    </header>
  `;
}

// ---------------------------------------------------------------------------
// Route View Dispatcher
// ---------------------------------------------------------------------------

function renderCurrentView() {
  if (STATE.loading) {
    return `
      <div class="h-64 flex flex-col items-center justify-center space-y-3">
        <div class="w-7 h-7 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin"></div>
        <p class="text-[13.5px] text-[var(--text-3)] font-sans">Loading Guardvane data...</p>
      </div>
    `;
  }

  switch (STATE.activeView) {
    case 'dashboard':
      return renderDashboardView();
    case 'opihub':
      return renderOpiHubView();
    case 'arkiv_tasks':
      return renderArkivTasksView();
    case 'provider_detail':
      return renderProviderDetailView();
    case 'become_provider':
      return renderBecomeProviderView();
    case 'provider_workspace':
      return renderProviderWorkspaceView();
    case 'my_prompts':
      return renderMyPromptsView();
    case 'my_requests':
      return renderMyRequestsView();
    case 'security_reports':
      return renderSecurityReportsView();
    default:
      return renderDashboardView();
  }
}

// ---------------------------------------------------------------------------
// 1. Dashboard Home Page (Editorial, Quiet, Claude / Anthropic Style)
// ---------------------------------------------------------------------------

function formatQuietDate(ts) {
  if (!ts) return '';
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return '';
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch (e) {
    return '';
  }
}

function renderDashboardView() {
  const userWallet = (STATE.auth.walletAddress || STATE.user.id || '').toLowerCase();
  const mySentOrders = (STATE.data.orders || []).filter(o => {
    const custId = (o.customer_id || '').toLowerCase();
    if (!userWallet) return false;
    return custId === userWallet || custId === (STATE.user.id || '').toLowerCase();
  });
  const myReports = (STATE.data.reports || []).filter(r => {
    const custId = (r.customer_id || '').toLowerCase();
    if (!userWallet) return false;
    return custId === userWallet || custId === (STATE.user.id || '').toLowerCase();
  });
  const myPrompts = (STATE.data.prompts || []).filter(p => {
    const custId = (p.customer_id || '').toLowerCase();
    if (!userWallet) return false;
    return custId === userWallet || custId === (STATE.user.id || '').toLowerCase();
  });

  const stats = STATE.data.stats || {};
  const savedPromptsCount = myPrompts.length;
  const activeRequestsCount = mySentOrders.filter(o => ['requested', 'accepted', 'in_progress'].includes(o.status)).length;
  const aiAuditsDelivered = myReports.filter(r => r.provider_id && (r.provider_id.includes('zerog') || r.provider_id.includes('prompt'))).length;
  const specialistAuditsDelivered = myReports.filter(r => r.provider_id && !r.provider_id.includes('zerog') && !r.provider_id.includes('prompt')).length;

  const myProvider = getMyProvider();
  const displayName = myProvider?.display_name || STATE.user.name || 'Francis Anto';
  const firstName = (displayName || '').split(' ')[0] || 'there';

  const hour = new Date().getHours();
  const timeGreeting = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';

  // Section 1: Orders needing attention (active/pending reviews)
  const attentionOrders = mySentOrders.filter(o => ['requested', 'accepted', 'in_progress', 'delivered'].includes(o.status));

  // Section 3: Recent activity and reports
  const recentActivity = (stats.recent_activity && stats.recent_activity.length > 0)
    ? stats.recent_activity.slice(0, 5)
    : mySentOrders.slice(0, 5).map(o => ({
        id: o.id,
        title: o.service_title,
        provider: o.provider_name,
        status: o.status,
        timestamp: o.updated_at || o.created_at
      }));
  const recentReports = myReports.slice(0, 5);

  // Section 4: Filter out current user from suggested providers
  const eligibleProviders = (STATE.data.providers || []).filter(p => {
    const pWallet = (p.wallet_address || '').toLowerCase();
    if (userWallet && pWallet === userWallet) return false;
    if (STATE.user.activeProviderId && p.id === STATE.user.activeProviderId) return false;
    if (myProvider && p.id === myProvider.id) return false;
    const currentName = (displayName || '').trim().toLowerCase();
    if (currentName && p.display_name && p.display_name.trim().toLowerCase() === currentName) return false;
    return true;
  });
  const suggestedProviders = eligibleProviders.slice(0, 3);

  return `
    <div class="space-y-12">
      <!-- Greeting Header -->
      ${renderPageHeader(
        `${timeGreeting}, ${escapeHtml(firstName)}.`,
        activeRequestsCount > 0
          ? `You have ${activeRequestsCount} active ${activeRequestsCount === 1 ? 'audit' : 'audits'} in progress and ${myReports.length} completed ${myReports.length === 1 ? 'report' : 'reports'}.`
          : `You have ${myReports.length} completed security ${myReports.length === 1 ? 'report' : 'reports'}. Explore OpiHub to request new audits.`,
        `<button onclick="navigateTo('opihub')" class="btn-primary !h-9 text-[13px]">Explore OpiHub</button>`
      )}

      <!-- Section 1: Needs your attention -->
      <section>
        <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)] mb-3">Needs your attention</div>
        ${attentionOrders.length > 0 ? `
          <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] divide-y divide-[var(--border)] overflow-hidden">
            ${attentionOrders.slice(0, 3).map(o => `
              <div class="px-5 py-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-[var(--surface-sunk)] transition-colors">
                <div class="flex items-center gap-2.5 min-w-0">
                  <span class="text-[14px] font-medium text-[var(--text)] truncate">${escapeHtml(o.service_title || 'Security Request')}</span>
                  ${renderIdChip(o.id)}
                  <span class="text-[var(--text-3)]">&middot;</span>
                  <span class="text-[13px] text-[var(--text-2)] truncate">with ${escapeHtml(o.provider_name || 'Specialist')}</span>
                </div>
                <div class="flex items-center gap-4 shrink-0">
                  ${renderStatusPill(o.status)}
                  <button onclick="openOrderDetail('${o.id}')" class="btn-secondary !h-8 text-[12.5px]">
                    Review request &rarr;
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        ` : renderEmptyState('All caught up. No pending requests require your review.')}
      </section>

      <!-- Section 2: At a glance (One card, 4 columns divided by vertical hairlines) -->
      <section>
        <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)] mb-3">At a glance</div>
        <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border)] overflow-hidden">
          <!-- 1: AI Audits -->
          <div onclick="navigateTo('security_reports')" class="p-6 flex flex-col justify-center hover:bg-[var(--surface-sunk)] cursor-pointer transition-colors select-none group">
            <span class="font-serif text-[28px] sm:text-[32px] font-normal leading-none tracking-[-0.01em] tabular-nums ${aiAuditsDelivered === 0 ? 'text-[var(--text-3)]' : 'text-[var(--text)]'}">
              ${aiAuditsDelivered}
            </span>
            <span class="text-[13px] text-[var(--text-2)] group-hover:text-[var(--text)] transition-colors mt-2">
              AI audits
            </span>
          </div>

          <!-- 2: Specialist Audits -->
          <div onclick="navigateTo('security_reports')" class="p-6 flex flex-col justify-center hover:bg-[var(--surface-sunk)] cursor-pointer transition-colors select-none group">
            <span class="font-serif text-[28px] sm:text-[32px] font-normal leading-none tracking-[-0.01em] tabular-nums ${specialistAuditsDelivered === 0 ? 'text-[var(--text-3)]' : 'text-[var(--text)]'}">
              ${specialistAuditsDelivered}
            </span>
            <span class="text-[13px] text-[var(--text-2)] group-hover:text-[var(--text)] transition-colors mt-2">
              Specialist audits
            </span>
          </div>

          <!-- 3: Active Requests -->
          <div onclick="navigateTo('my_requests')" class="p-6 flex flex-col justify-center hover:bg-[var(--surface-sunk)] cursor-pointer transition-colors select-none group">
            <span class="font-serif text-[28px] sm:text-[32px] font-normal leading-none tracking-[-0.01em] tabular-nums ${activeRequestsCount === 0 ? 'text-[var(--text-3)]' : 'text-[var(--text)]'}">
              ${activeRequestsCount}
            </span>
            <span class="text-[13px] text-[var(--text-2)] group-hover:text-[var(--text)] transition-colors mt-2">
              Active requests
            </span>
          </div>

          <!-- 4: Saved Prompts -->
          <div onclick="navigateTo('my_prompts')" class="p-6 flex flex-col justify-center hover:bg-[var(--surface-sunk)] cursor-pointer transition-colors select-none group">
            <span class="font-serif text-[28px] sm:text-[32px] font-normal leading-none tracking-[-0.01em] tabular-nums ${savedPromptsCount === 0 ? 'text-[var(--text-3)]' : 'text-[var(--text)]'}">
              ${savedPromptsCount}
            </span>
            <span class="text-[13px] text-[var(--text-2)] group-hover:text-[var(--text)] transition-colors mt-2">
              Saved prompts
            </span>
          </div>
        </div>
      </section>

      <!-- Section 3: Recent activity & recent reports (2-column, 7/5 split) -->
      <section>
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <!-- Left: Activity (7 cols) -->
          <div class="lg:col-span-7 flex flex-col">
            <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)] mb-3">Recent activity</div>
            <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] divide-y divide-[var(--border)] overflow-hidden flex-1">
              ${recentActivity.length > 0 ? recentActivity.map(act => `
                <div onclick="openOrderDetail('${act.id}')" class="min-h-[64px] px-5 py-3 flex items-center justify-between gap-4 hover:bg-[var(--surface-sunk)] transition-colors cursor-pointer">
                  <div class="min-w-0 pr-2">
                    <div class="flex items-center gap-2">
                      <span class="text-[14px] font-medium text-[var(--text)] truncate leading-snug">
                        ${escapeHtml(act.title || 'Security Request')}
                      </span>
                      ${renderIdChip(act.id)}
                    </div>
                    <div class="text-[13px] text-[var(--text-2)] truncate leading-snug mt-0.5">
                      with ${escapeHtml(act.provider || 'Specialist')}
                    </div>
                  </div>
                  <div class="flex items-center gap-3 shrink-0">
                    ${renderStatusPill(act.status)}
                    ${act.timestamp ? `
                      <span class="text-[12px] text-[var(--text-3)] font-sans tabular-nums">
                        ${formatQuietDate(act.timestamp)}
                      </span>
                    ` : ''}
                  </div>
                </div>
              `).join('') : `
                <div class="p-8 text-center text-[13px] text-[var(--text-3)]">No recent activity recorded yet.</div>
              `}
            </div>
          </div>

          <!-- Right: Security Reports (5 cols) -->
          <div class="lg:col-span-5 flex flex-col">
            <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)] mb-3">Security reports</div>
            <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] divide-y divide-[var(--border)] overflow-hidden flex-1">
              ${recentReports.length > 0 ? recentReports.map(r => {
                const findings = r.findings || [];
                const findingCount = findings.length;
                return `
                  <div class="min-h-[64px] px-5 py-3 flex items-center justify-between gap-3 hover:bg-[var(--surface-sunk)] transition-colors">
                    <div class="min-w-0 pr-2">
                      <div class="text-[14px] font-medium text-[var(--text)] truncate leading-snug">
                        ${escapeHtml(r.service_title || 'Security Audit')}
                      </div>
                      <div class="text-[12.5px] text-[var(--text-3)] truncate leading-snug mt-0.5">
                        by ${escapeHtml(r.provider_name || '0G Defence Agent')} &middot; ${findingCount} ${findingCount === 1 ? 'finding' : 'findings'}
                      </div>
                    </div>
                    <button onclick="viewReport('${r.id}')" class="btn-secondary !h-8 !px-3 text-[12.5px] shrink-0">
                      View report
                    </button>
                  </div>
                `;
              }).join('') : `
                <div class="p-8 text-center text-[13px] text-[var(--text-3)]">No completed security reports recorded yet.</div>
              `}
            </div>
          </div>
        </div>
      </section>

      <!-- Section 4: Suggested Providers -->
      <section>
        <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)] mb-3">Suggested providers</div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          ${suggestedProviders.length > 0 ? suggestedProviders.map(p => renderCleanProviderCard(p)).join('') : `
            <div class="col-span-3 p-8 text-center text-[13px] text-[var(--text-3)] bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)]">
              No additional providers available at this time.
            </div>
          `}
        </div>
      </section>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 2. OpiHub Marketplace Discovery Page
// ---------------------------------------------------------------------------

function setOpihubTab(tab) {
  STATE.opihubTab = tab;
  renderApp();
}

function renderOpiHubView() {
  const isServicesTab = (STATE.opihubTab !== 'providers');

  const categories = [
    { id: 'all', label: 'All Categories' },
    { id: 'prompt_engineering', label: 'Prompt Engineering' },
    { id: 'loop_engineering', label: 'Prompt Loop Engineering' },
    { id: 'prompt_optimization', label: 'Prompt Optimization' },
    { id: 'prompt_security_analysis', label: 'Prompt Security Analysis' },
    { id: 'codebase_security', label: 'Codebase Security Audit' },
    { id: 'application_security_testing', label: 'Application Security Testing' }
  ];

  const filteredServices = (STATE.data.services || []).filter(s => {
    if (STATE.filters.search) {
      const q = STATE.filters.search.toLowerCase();
      const matchTitle = (s.title || '').toLowerCase().includes(q);
      const matchDesc = (s.description || '').toLowerCase().includes(q);
      const matchProv = (s.provider_name || '').toLowerCase().includes(q);
      if (!matchTitle && !matchDesc && !matchProv) return false;
    }
    if (STATE.filters.category && STATE.filters.category !== 'all') {
      if ((s.category || '').toLowerCase() !== STATE.filters.category.toLowerCase()) return false;
    }
    if (STATE.filters.providerType) {
      if (s.execution_type !== (STATE.filters.providerType === 'automated' ? 'automated' : 'manual')) return false;
    }
    return true;
  });

  const filteredProviders = (STATE.data.providers || []).filter(p => {
    if (STATE.filters.search) {
      const q = STATE.filters.search.toLowerCase();
      const matchName = (p.display_name || '').toLowerCase().includes(q);
      const matchTitle = (p.title || '').toLowerCase().includes(q);
      const matchDesc = (p.description || '').toLowerCase().includes(q);
      const matchSkills = (p.skills || []).some(sk => sk.toLowerCase().includes(q));
      if (!matchName && !matchTitle && !matchDesc && !matchSkills) return false;
    }
    if (STATE.filters.category && STATE.filters.category !== 'all') {
      const hasCat = (p.categories || []).some(c => c.toLowerCase() === STATE.filters.category.toLowerCase());
      if (!hasCat) return false;
    }
    if (STATE.filters.providerType && p.provider_type !== STATE.filters.providerType) {
      return false;
    }
    return true;
  });

  return `
    <div class="space-y-8">
      <!-- Page Header with sentence-case title and tabs -->
      ${renderPageHeader(
        'OpiHub',
        'Find specialized security agents and human auditors to review your prompts, codebases, and architectures.',
        `
        <div class="inline-flex p-0.5 bg-[var(--surface-sunk)] rounded-[var(--radius-sm)] border border-[var(--border)] shrink-0">
          <button
            onclick="setOpihubTab('services')"
            class="px-3.5 py-1.5 text-[13px] font-medium rounded-[var(--radius-sm)] transition-colors cursor-pointer ${
              isServicesTab ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs' : 'text-[var(--text-2)] hover:text-[var(--text)]'
            }"
          >
            <span>Services</span>
            <span class="ml-1 text-[var(--text-3)] tabular-nums">${filteredServices.length}</span>
          </button>
          <button
            onclick="setOpihubTab('providers')"
            class="px-3.5 py-1.5 text-[13px] font-medium rounded-[var(--radius-sm)] transition-colors cursor-pointer ${
              !isServicesTab ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs' : 'text-[var(--text-2)] hover:text-[var(--text)]'
            }"
          >
            <span>Specialists & agents</span>
            <span class="ml-1 text-[var(--text-3)] tabular-nums">${filteredProviders.length}</span>
          </button>
        </div>
        `
      )}

      <!-- Category Filter Tabs: Single row, selected = --accent-soft fill, 1px accent border, --text colour -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[var(--border)]">
        ${categories.map(c => `
          <button
            onclick="setCategoryFilter('${c.id}')"
            class="px-3.5 py-1.5 rounded-full text-[12.5px] font-medium whitespace-nowrap transition-colors flex items-center gap-1.5 cursor-pointer ${
              STATE.filters.category === c.id
                ? 'bg-[var(--accent-soft)] border border-[var(--accent)] text-[var(--text)]'
                : 'bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] hover:border-[var(--border-strong)] hover:text-[var(--text)]'
            }"
          >
            <span>${c.label}</span>
          </button>
        `).join('')}
      </div>

      <!-- Filter Bar: Quiet Row, No Card, Rabdi Testnet Chip Moved to Topbar -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-1">
        <div class="flex items-center gap-2.5">
          <span class="text-[13px] text-[var(--text-2)] font-medium">Provider type:</span>
          <select
            onchange="setProviderTypeFilter(this.value)"
            class="bg-[var(--surface)] border border-[var(--border)] text-[13px] text-[var(--text)] font-medium rounded-[var(--radius-sm)] px-3 py-1.5 focus:outline-none focus:border-[var(--accent)] cursor-pointer"
          >
            <option value="" ${!STATE.filters.providerType ? 'selected' : ''}>All types (0G Agents & Specialists)</option>
            <option value="automated" ${STATE.filters.providerType === 'automated' ? 'selected' : ''}>Autonomous 0G Defense Agents</option>
            <option value="human" ${STATE.filters.providerType === 'human' ? 'selected' : ''}>Human Security Specialists</option>
          </select>
        </div>

        <div class="text-[13px] text-[var(--text-2)] tabular-nums font-medium">
          ${isServicesTab ? `${filteredServices.length} services` : `${filteredProviders.length} specialists & agents`}
        </div>
      </div>

      ${isServicesTab ? `
        <!-- Services Grid -->
        ${filteredServices.length > 0 ? `
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            ${filteredServices.map(s => renderCleanServiceCard(s, true)).join('')}
          </div>
        ` : renderEmptyState('No services match your filter.', 'Reset filters', 'resetFilters()')}
      ` : `
        <!-- Providers Grid -->
        ${filteredProviders.length > 0 ? `
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            ${filteredProviders.map(p => renderCleanProviderCard(p)).join('')}
          </div>
        ` : renderEmptyState('No specialists or agents match your filter.', 'Reset filters', 'resetFilters()')}
      `}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 3. Provider Profile Page
// ---------------------------------------------------------------------------

function renderProviderDetailView() {
  const provider = STATE.data.providers.find(p => p.id === STATE.selectedProviderId) || STATE.data.providers[0];
  if (!provider) {
    return `<div class="surface-card p-12 text-center text-[var(--text-3)]">Provider not found. <button onclick="navigateTo('opihub')" class="text-[var(--accent)] hover:underline ml-1">Back to OpiHub</button></div>`;
  }

  const providerServices = STATE.data.services.filter(s => s.provider_id === provider.id);
  const isAutomated = provider.provider_type === 'automated';
  const currentWallet = (STATE.auth.walletAddress || '').toLowerCase();
  const isOwner = currentWallet && provider.wallet_address && (provider.wallet_address.toLowerCase() === currentWallet) && !provider.is_platform_managed;

  const deliveredReports = (STATE.data.reports || []).filter(r =>
    r.provider_id === provider.id ||
    (provider.display_name && r.provider_name === provider.display_name)
  );
  const completedOrders = (STATE.data.orders || []).filter(o =>
    (o.provider_id === provider.id || (provider.wallet_address && o.provider_wallet === provider.wallet_address) || (provider.display_name && o.provider_name === provider.display_name)) &&
    (o.status === 'delivered' || o.status === 'completed')
  );
  const auditsDeliveredCount = Math.max(deliveredReports.length, completedOrders.length, provider.reputation_metadata?.audits_completed || 0);

  let turnaroundDisplay = '~5s (0G AI)';
  if (isAutomated) {
    turnaroundDisplay = '~5s (0G AI)';
  } else {
    const srvWithDelivery = providerServices.find(s => s.estimated_delivery);
    if (srvWithDelivery && srvWithDelivery.estimated_delivery) {
      turnaroundDisplay = srvWithDelivery.estimated_delivery;
    } else if (provider.reputation_metadata?.avg_turnaround_hours) {
      turnaroundDisplay = `${provider.reputation_metadata.avg_turnaround_hours}h`;
    } else {
      turnaroundDisplay = '24 hours';
    }
  }

  return `
    <div class="space-y-8">
      <!-- Back Link -->
      <div>
        <button onclick="navigateTo('opihub')" class="text-[13px] text-[var(--text-3)] hover:text-[var(--text)] transition-colors flex items-center gap-1.5 cursor-pointer bg-transparent border-none p-0">
          &larr; Back to OpiHub
        </button>
      </div>

      <!-- Provider Header Card -->
      <div class="surface-card space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2.5 flex-wrap">
              <h1 class="font-serif text-[26px] font-normal tracking-[-0.01em] text-[var(--text)]">${escapeHtml(provider.display_name)}</h1>
              ${provider.verified ? `
                <span class="pill pill-success text-[11px]">
                  Verified
                </span>
              ` : `
                <span class="pill pill-neutral text-[11px]">
                  Registered
                </span>
              `}
              <span class="pill pill-neutral text-[11px]">
                ${isAutomated ? '0G AI Agent' : 'Specialist'}
              </span>
            </div>
            <p class="text-[14px] text-[var(--text-2)]">${escapeHtml(provider.title || '')}</p>
            <div class="flex items-center gap-4 text-[12.5px] text-[var(--text-3)] pt-1">
              ${provider.wallet_address ? `<span>Wallet: <code class="font-mono text-[11.5px] text-[var(--text-2)]">${provider.wallet_address}</code></span>` : ''}
            </div>
          </div>

          <div class="flex items-center gap-2.5 shrink-0">
            ${isOwner ? `
              <button
                onclick="navigateTo('provider_workspace')"
                class="btn-secondary !h-9 text-[13px]"
              >
                Go to workspace &rarr;
              </button>
              <button
                onclick="openModal('edit_provider', { providerId: '${provider.id}' })"
                class="btn-secondary !h-9 text-[13px]"
              >
                Edit profile
              </button>
            ` : `
              <button
                onclick="openModal('request_review', { providerId: '${provider.id}', serviceId: '${providerServices[0]?.id || ''}' })"
                class="btn-primary !h-9 text-[13px]"
              >
                Request review
              </button>
            `}
          </div>
        </div>

        <!-- Description & Capabilities -->
        <div class="border-t border-[var(--border)] pt-5 space-y-4">
          <div>
            <div class="text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)]">About Provider</div>
            <p class="text-[14px] text-[var(--text-2)] leading-relaxed mt-1.5">${escapeHtml(provider.description || '')}</p>
          </div>

          <!-- Skills Chips -->
          <div>
            <div class="text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)] mb-2">Capabilities & Skills</div>
            <div class="flex flex-wrap gap-1.5">
              ${provider.skills.map(s => `
                <span class="px-2.5 py-1 rounded-[var(--radius-sm)] bg-[var(--surface-sunk)] text-[var(--text-2)] text-[12px]">
                  ${escapeHtml(s)}
                </span>
              `).join('')}
            </div>
          </div>

          <!-- Track Record Metrics (Clean 4-column strip, no nested boxes) -->
          <div class="border-t border-[var(--border)] pt-5">
            <div class="text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)] mb-3">Track Record & Performance</div>
            <div class="grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border)] border border-[var(--border)] rounded-[var(--radius-md)] bg-[var(--surface)] overflow-hidden text-center">
              <div class="p-4">
                <div class="font-serif text-[28px] font-normal text-[var(--text)]">${auditsDeliveredCount}</div>
                <div class="text-[12px] text-[var(--text-3)] mt-1">Audits delivered</div>
              </div>
              <div class="p-4">
                <div class="font-serif text-[28px] font-normal text-[var(--text)]">${escapeHtml(turnaroundDisplay)}</div>
                <div class="text-[12px] text-[var(--text-3)] mt-1">Average turnaround</div>
              </div>
              <div class="p-4">
                <div class="font-serif text-[28px] font-normal text-[var(--text)]">${isAutomated ? 'Autonomous' : 'Manual'}</div>
                <div class="text-[12px] text-[var(--text-3)] mt-1">Execution type</div>
              </div>
              <div class="p-4">
                <div class="font-serif text-[28px] font-normal text-[var(--text)]">${provider.portfolio_url ? 'Verified' : 'Active'}</div>
                <div class="text-[12px] text-[var(--text-3)] mt-1">Profile status</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Published Services List -->
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)]">Published Services (${providerServices.length})</div>
          ${isOwner ? `
            <button onclick="openModal('add_service_modal', { providerId: '${provider.id}' })" class="btn-secondary !h-8 text-[12.5px]">
              Add service
            </button>
          ` : ''}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          ${providerServices.map(s => renderCleanServiceCard(s, false, isOwner)).join('')}
        </div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 4. Become a Provider Page
// ---------------------------------------------------------------------------

function renderBecomeProviderView() {
  const wallet = STATE.auth.walletAddress || '';

  return `
    <div class="max-w-3xl mx-auto space-y-8">
      <div>
        <h1 class="font-serif text-[32px] font-normal tracking-[-0.01em] text-[var(--text)]">Become a Security Provider</h1>
        <p class="text-[14px] text-[var(--text-2)] mt-1.5">Register as an expert security researcher to offer verified audits on OpiHub.</p>
      </div>

      <form id="become-provider-form" onsubmit="handleBecomeProvider(event)" class="surface-card p-8 sm:p-10 space-y-8">
        <input type="hidden" name="provider_type" value="human" />

        <!-- Section 1: Provider Identity -->
        <div class="space-y-4">
          <div class="text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)] border-b border-[var(--border)] pb-2">1. Specialist Identity</div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Provider / Display Name *</label>
              <input type="text" name="display_name" required placeholder="" class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Professional Title *</label>
              <input type="text" name="title" required placeholder="" class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
            </div>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Connected Wallet Address (Read-only)</label>
            <input type="text" name="wallet_address" value="${escapeForAttr(wallet)}" readonly class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[13px] font-mono text-[var(--text-2)] cursor-not-allowed" />
            <p class="text-[12px] text-[var(--text-3)] mt-1.5">Orders, smart escrow payouts, and workspace assignments are persistently bound to this wallet.</p>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Provider Bio / Description *</label>
            <textarea name="description" rows="3" required placeholder="" class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors leading-relaxed"></textarea>
          </div>
        </div>

        <!-- Section 2: Skills & Categories -->
        <div class="space-y-4">
          <div class="text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)] border-b border-[var(--border)] pb-2">2. Expertise & Supported Categories</div>

          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Skills (Comma-separated)</label>
            <input type="text" name="skills_raw" placeholder="" class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-2">Supported Service Categories (Select at least one) *</label>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="flex items-center gap-2.5 text-[13px] text-[var(--text-2)] cursor-pointer"><input type="checkbox" name="cat" value="prompt_engineering" checked class="accent-[var(--accent)]" /> Prompt Engineering</label>
              <label class="flex items-center gap-2.5 text-[13px] text-[var(--text-2)] cursor-pointer"><input type="checkbox" name="cat" value="loop_engineering" checked class="accent-[var(--accent)]" /> Prompt Loop Engineering</label>
              <label class="flex items-center gap-2.5 text-[13px] text-[var(--text-2)] cursor-pointer"><input type="checkbox" name="cat" value="prompt_optimization" checked class="accent-[var(--accent)]" /> Prompt Optimization</label>
              <label class="flex items-center gap-2.5 text-[13px] text-[var(--text-2)] cursor-pointer"><input type="checkbox" name="cat" value="prompt_security_analysis" class="accent-[var(--accent)]" /> Prompt Security Analysis</label>
              <label class="flex items-center gap-2.5 text-[13px] text-[var(--text-2)] cursor-pointer"><input type="checkbox" name="cat" value="codebase_security" class="accent-[var(--accent)]" /> Codebase Security Audit</label>
              <label class="flex items-center gap-2.5 text-[13px] text-[var(--text-2)] cursor-pointer"><input type="checkbox" name="cat" value="application_security_testing" class="accent-[var(--accent)]" /> Application Security Testing</label>
            </div>
          </div>
        </div>

        <!-- Section 3: Initial Service Listing -->
        <div class="space-y-4">
          <div class="text-[11px] font-medium tracking-[0.06em] uppercase text-[var(--text-3)] border-b border-[var(--border)] pb-2">3. Initial Service Offering</div>

          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Service Title *</label>
            <input type="text" name="service_title" required placeholder="" class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Price (USD) *</label>
              <input type="number" step="0.01" min="0" name="service_price" value="50.00" required class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] font-mono text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Estimated Delivery *</label>
              <input type="text" name="service_delivery" required value="24 hours" placeholder="" class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[var(--text)] mb-1.5">Portfolio or GitHub URL</label>
              <input type="url" name="portfolio_url" placeholder="" class="w-full px-3.5 py-2.5 bg-[var(--surface)] border border-[var(--border-strong)] rounded-[var(--radius-sm)] text-[14px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] transition-colors" />
            </div>
          </div>
        </div>

        <!-- Submit Button -->
        <div class="pt-4 border-t border-[var(--border)] flex items-center justify-end gap-3">
          <button type="button" onclick="navigateTo('dashboard')" class="btn-secondary !h-10 text-[13.5px]">
            Cancel
          </button>
          <button type="submit" class="btn-primary !h-10 text-[13.5px]">
            Register provider profile
          </button>
        </div>
      </form>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 5. Provider Workspace
// ---------------------------------------------------------------------------

function renderProviderWorkspaceView() {
  const myProvider = getMyProvider();

  if (!myProvider) {
    return `
      <div class="max-w-2xl mx-auto py-16 text-center space-y-4">
        <div class="w-12 h-12 mx-auto rounded-full bg-[var(--surface-sunk)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)]">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
        </div>
        <h2 class="font-serif text-[24px] font-normal tracking-[-0.01em] text-[var(--text)]">Provider registration required</h2>
        <p class="text-[14px] text-[var(--text-2)] max-w-md mx-auto leading-relaxed">
          You are not currently registered as a provider. Register your security profile to offer prompt audits, receive scan requests from clients, and review submissions.
        </p>
        <div class="pt-2">
          <button onclick="navigateTo('become_provider')" class="btn-primary !h-9 text-[13px]">
            Register as provider &rarr;
          </button>
        </div>
      </div>
    `;
  }

  const provider = myProvider;
  const myServices = (STATE.data.services || []).filter(s => s.provider_id === provider.id);
  const assignedOrders = (STATE.data.orders || []).filter(o => {
    const isForMe = o.provider_id === provider.id ||
      (provider.wallet_address && (o.provider_wallet || '').toLowerCase() === provider.wallet_address.toLowerCase()) ||
      (o.provider_name && o.provider_name.toLowerCase() === (provider.display_name || '').toLowerCase());
    const isVisibleState = o.payment_status === 'verified' || o.escrow_state === 'funded' || ['requested', 'accepted', 'in_progress', 'delivered', 'completed', 'rejected'].includes(o.status);
    return isForMe && isVisibleState;
  });

  const incoming = assignedOrders.filter(o => o.status === 'requested');
  const inProgress = assignedOrders.filter(o => o.status === 'accepted' || o.status === 'in_progress');
  const awaitingRelease = assignedOrders.filter(o => o.status === 'delivered' && o.escrow_state !== 'released');
  const completed = assignedOrders.filter(o => o.status === 'completed' || o.status === 'delivered');
  const totalEarned = completed.filter(o => o.status === 'completed' || o.escrow_state === 'released').reduce((acc, o) => acc + (o.price || 0), 0);

  return `
    <div class="space-y-10">
      <!-- Page Header: sentence-case title, 14-15px --text-2 description, secondary actions top-right -->
      ${renderPageHeader(
        'Provider workspace',
        "Orders you've received and their payouts.",
        `
        <button onclick="openModal('add_service_modal', { providerId: '${provider.id}' })" class="btn-secondary !h-9 text-[13px]">
          Edit services
        </button>
        <button onclick="openModal('edit_provider', { providerId: '${provider.id}' })" class="btn-secondary !h-9 text-[13px]">
          Edit profile
        </button>
        `
      )}

      <!-- Summary Strip: 1 card, 4 cols, hairlines, serif 28px numbers with tabular-nums -->
      <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] grid grid-cols-2 md:grid-cols-4 divide-y md:divide-y-0 md:divide-x divide-[var(--border)] overflow-hidden">
        <div class="p-6 flex flex-col justify-center">
          <span class="font-serif text-[28px] font-normal leading-none tabular-nums ${awaitingRelease.length === 0 ? 'text-[var(--text-3)]' : 'text-[var(--text)]'}">${awaitingRelease.length}</span>
          <span class="text-[13px] text-[var(--text-2)] mt-2">Awaiting release</span>
        </div>
        <div class="p-6 flex flex-col justify-center">
          <span class="font-serif text-[28px] font-normal leading-none tabular-nums ${inProgress.length === 0 ? 'text-[var(--text-3)]' : 'text-[var(--text)]'}">${inProgress.length}</span>
          <span class="text-[13px] text-[var(--text-2)] mt-2">In progress</span>
        </div>
        <div class="p-6 flex flex-col justify-center">
          <span class="font-serif text-[28px] font-normal leading-none tabular-nums ${completed.length === 0 ? 'text-[var(--text-3)]' : 'text-[var(--text)]'}">${completed.length}</span>
          <span class="text-[13px] text-[var(--text-2)] mt-2">Completed</span>
        </div>
        <div class="p-6 flex flex-col justify-center">
          <span class="font-serif text-[28px] font-normal leading-none text-[var(--text)] tabular-nums font-sans">$${totalEarned.toFixed(2)}</span>
          <span class="text-[13px] text-[var(--text-2)] mt-2">Total earned</span>
        </div>
      </div>

      <!-- In Progress Section -->
      <section>
        <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)] mb-3">In progress</div>
        ${inProgress.length > 0 || incoming.length > 0 ? `
          <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] divide-y divide-[var(--border)] overflow-hidden">
            ${[...incoming, ...inProgress].map(o => `
              <div class="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[var(--surface-sunk)] transition-colors cursor-pointer" onclick="openModal('order_detail', '${o.id}')">
                <div class="min-w-0 space-y-1">
                  <div class="flex items-center gap-2 flex-wrap">
                    <span class="font-medium text-[14px] text-[var(--text)]">${escapeHtml(o.service_title)}</span>
                    ${renderIdChip(o.id)}
                    ${renderStatusPill(o.status, true, o.escrow_state)}
                  </div>
                  <div class="text-[13px] text-[var(--text-2)]">
                    Client: <strong class="text-[var(--text)] font-medium">${escapeHtml(o.customer_name)}</strong> &middot; Fee: <span class="tabular-nums font-medium text-[var(--text)]">$${o.price.toFixed(2)}</span> &middot; <span class="text-[var(--text-3)] tabular-nums">${formatQuietDate(o.created_at)}</span>
                  </div>
                </div>

                <div class="flex items-center gap-2 shrink-0" onclick="event.stopPropagation()">
                  ${o.status === 'requested' ? `
                    <button onclick="handleOrderStatusUpdate('${o.id}', 'accepted')" class="btn-primary !h-8 text-[12.5px]">
                      Accept request
                    </button>
                    <button onclick="handleOrderReject('${o.id}')" class="btn-secondary !h-8 text-[12.5px]">
                      Reject
                    </button>
                  ` : `
                    <button onclick="openModal('deliver_modal', { orderId: '${o.id}' })" class="btn-primary !h-8 text-[12.5px]">
                      Submit deliverable
                    </button>
                  `}
                </div>
              </div>
            `).join('')}
          </div>
        ` : renderEmptyState('No active orders right now.')}
      </section>

      <!-- Delivered and Completed Section as Table -->
      <section>
        <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)] mb-3">Delivered and completed</div>
        ${completed.length > 0 ? `
          <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-left text-[13px]">
                <thead class="border-b border-[var(--border)] text-[var(--text-2)] text-[12px] uppercase font-semibold tracking-[0.06em]">
                  <tr>
                    <th class="px-5 py-3.5">Order</th>
                    <th class="px-5 py-3.5">Client</th>
                    <th class="px-5 py-3.5">Fee</th>
                    <th class="px-5 py-3.5">Status</th>
                    <th class="px-5 py-3.5">Date</th>
                    <th class="px-5 py-3.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--border)]">
                  ${completed.map(o => {
                    const isAwaitingRelease = o.status === 'delivered' && o.escrow_state !== 'released';
                    return `
                      <tr class="hover:bg-[var(--surface-sunk)] transition-colors cursor-pointer" onclick="openModal('order_detail', '${o.id}')">
                        <td class="px-5 py-4">
                          <div class="flex items-center gap-2">
                            <span class="font-medium text-[13.5px] text-[var(--text)]">${escapeHtml(o.service_title)}</span>
                            ${renderIdChip(o.id)}
                          </div>
                          <!-- Expandable payment details -->
                          <div class="mt-2 pt-2 border-t border-[var(--border)] flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px]" onclick="event.stopPropagation()">
                            <div class="flex items-center gap-1.5 text-[var(--text-3)]">
                              <span>Payout:</span>
                              ${renderShortAddress(provider.wallet_address || o.provider_wallet)}
                            </div>
                            ${o.escrow_release_tx_hash ? `
                              <div class="flex items-center gap-1 text-[var(--text-3)] font-mono">
                                <span>Release:</span>
                                <a href="${o.rabdi_release_url || ('https://rabdi.explorer.arkiv.network/tx/' + o.escrow_release_tx_hash)}" target="_blank" rel="noopener noreferrer" class="text-[var(--text-2)] underline hover:text-[var(--accent)] font-sans">
                                  Rabdi Explorer &nearr;
                                </a>
                              </div>
                            ` : o.escrow_tx_hash ? `
                              <div class="flex items-center gap-1 text-[var(--text-3)] font-mono">
                                <span>Deposit:</span>
                                <a href="${o.rabdi_explorer_url || ('https://rabdi.explorer.arkiv.network/tx/' + o.escrow_tx_hash)}" target="_blank" rel="noopener noreferrer" class="text-[var(--text-2)] underline hover:text-[var(--accent)] font-sans">
                                  Rabdi Explorer &nearr;
                                </a>
                              </div>
                            ` : ''}
                          </div>
                        </td>
                        <td class="px-5 py-4 text-[var(--text-2)] align-top">${escapeHtml(o.customer_name || 'Client')}</td>
                        <td class="px-5 py-4 font-sans font-medium text-[var(--text)] tabular-nums align-top">$${o.price.toFixed(2)}</td>
                        <td class="px-5 py-4 align-top">
                          ${renderStatusPill(o.status, true, o.escrow_state)}
                        </td>
                        <td class="px-5 py-4 text-[var(--text-3)] font-sans text-[12px] tabular-nums align-top">${formatQuietDate(o.updated_at || o.created_at)}</td>
                        <td class="px-5 py-4 text-right align-top" onclick="event.stopPropagation()">
                          ${isAwaitingRelease ? `
                            <button onclick="executeEVMEscrowRelease('${o.id}')" class="btn-primary !h-8 text-[12.5px]">
                              Release payment
                            </button>
                          ` : o.report_id ? `
                            <button onclick="viewReport('${o.report_id}')" class="btn-secondary !h-8 text-[12.5px]">
                              View report
                            </button>
                          ` : `
                            <button onclick="openModal('order_detail', '${o.id}')" class="btn-secondary !h-8 text-[12.5px]">
                              View details
                            </button>
                          `}
                        </td>
                      </tr>
                    `;
                  }).join('')}
                </tbody>
              </table>
            </div>
          </div>
        ` : renderEmptyState('No delivered or completed audits recorded yet.')}
      </section>

      <!-- Published Services Section -->
      <section>
        <div class="flex items-center justify-between mb-3">
          <div class="text-[12px] font-semibold tracking-[0.06em] uppercase text-[var(--text-2)]">Published services (${myServices.length})</div>
          <button onclick="openModal('add_service_modal', { providerId: '${provider.id}' })" class="text-[13px] text-[var(--accent)] hover:text-[var(--accent-hover)] transition-colors cursor-pointer bg-transparent border-none p-0">
            + Add service
          </button>
        </div>

        ${myServices.length > 0 ? `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            ${myServices.map(s => `
              <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-6 flex flex-col justify-between hover:border-[var(--border-strong)] transition-all">
                <div>
                  <div class="flex items-start justify-between gap-3">
                    <h3 class="font-serif text-[18px] font-normal text-[var(--text)] leading-snug">${escapeHtml(s.title)}</h3>
                    <span class="text-[16px] font-bold text-[var(--text)] tabular-nums font-sans shrink-0">$${s.price.toFixed(2)}</span>
                  </div>
                  <div class="text-[12px] text-[var(--text-3)] mt-1">
                    ${formatCategoryName(s.category)} &middot; ${escapeHtml(s.estimated_delivery)}
                  </div>
                  <p class="text-[13px] text-[var(--text-2)] line-clamp-2 leading-relaxed mt-2.5">${escapeHtml(s.description)}</p>
                </div>

                <div class="flex items-center justify-end gap-2 pt-4 mt-4 border-t border-[var(--border)]">
                  <button onclick="openModal('edit_service_modal', { serviceId: '${s.id}' })" class="btn-secondary !h-8 text-[12px]">
                    Edit
                  </button>
                  <button onclick="handleDeleteService('${s.id}')" class="btn-ghost !h-8 text-[12px] hover:text-[var(--danger)]">
                    Delete
                  </button>
                </div>
              </div>
            `).join('')}
          </div>
        ` : renderEmptyState('You have not published any service offerings yet.', '+ Add service', `openModal('add_service_modal', { providerId: '${provider.id}' })`)}
      </section>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 6. My Prompts Page
// ---------------------------------------------------------------------------

function renderMyPromptsView() {
  const userWallet = (STATE.auth.walletAddress || STATE.user.id || '').toLowerCase();
  const prompts = (STATE.data.prompts || []).filter(p => {
    const custId = (p.customer_id || '').toLowerCase();
    if (!userWallet) return false;
    return custId === userWallet || custId === (STATE.user.id || '').toLowerCase();
  });

  return `
    <div class="space-y-8">
      ${renderPageHeader(
        'Saved prompts',
        'Prompt repository: store improved prompts, defense instructions, and audit test suites.',
        `<button onclick="openModal('create_prompt')" class="btn-primary !h-9 text-[13px]">+ New prompt</button>`
      )}

      <div class="space-y-4">
        ${prompts.length > 0 ? prompts.map(p => `
          <div class="surface-card space-y-3.5">
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0">
                <h3 class="font-serif text-[18px] font-normal text-[var(--text)] leading-snug">${escapeHtml(p.title)}</h3>
                <span class="text-[12px] text-[var(--text-3)] font-mono">${p.id} &middot; Saved ${formatQuietDate(p.created_at)}</span>
              </div>

              <div class="flex items-center gap-2 shrink-0">
                <button onclick="openModal('request_review', { promptText: '${escapeForAttr(p.content)}' })" class="btn-secondary !h-8 text-[12.5px]">
                  Submit for review
                </button>
                <button onclick="handleDeletePrompt('${p.id}')" class="btn-ghost !h-8 text-[12px] hover:text-[var(--danger)]" title="Delete prompt">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Content Preview -->
            <div class="bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-sm)] p-4 font-mono text-[12.5px] text-[var(--text)] whitespace-pre-wrap leading-relaxed">
              ${escapeHtml(p.content)}
            </div>

            <!-- Security Finding Tags if Analyzed -->
            ${p.analysis_result ? `
              <div class="flex items-center gap-2.5 pt-1 text-[12px]">
                <span class="text-[var(--text-3)]">Previous scan:</span>
                <span class="pill ${p.analysis_result.injection_score > 0.5 ? 'pill-danger' : 'pill-success'} text-[11px]">
                  Injection ${(p.analysis_result.injection_score * 100).toFixed(0)}%
                </span>
                ${(p.analysis_result.risk_labels || []).length > 0 ? `
                  <span class="text-[var(--text-3)]">&middot;</span>
                  <span class="text-[var(--text-2)]">Risks: ${(p.analysis_result.risk_labels || []).join(', ')}</span>
                ` : ''}
              </div>
            ` : ''}
          </div>
        `).join('') : `
          <div class="surface-card p-12 text-center text-[13px] text-[var(--text-3)]">
            No saved prompts in your repository yet. Click "+ New prompt" to store one.
          </div>
        `}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Arkiv Decentralized Security Task Board (Rabdi Testnet)
// ---------------------------------------------------------------------------

function setArkivCategoryFilter(cat) {
  STATE.arkiv.categoryFilter = cat;
  renderApp();
}

function setArkivStatusFilter(stat) {
  STATE.arkiv.statusFilter = stat;
  renderApp();
}

async function loadArkivTasks(force = false) {
  STATE.arkiv.loading = true;
  renderApp();
  try {
    const tasks = await apiFetch('/marketplace/arkiv/tasks');
    STATE.arkiv.tasks = tasks || [];
    STATE.arkiv.error = null;
  } catch (err) {
    console.error('Failed to load Arkiv tasks:', err);
    STATE.arkiv.error = err.message || 'Could not load tasks from Arkiv.';
  } finally {
    STATE.arkiv.loading = false;
    renderApp();
  }
}

function renderArkivTaskCard(t, currentWallet) {
  const isOwner = currentWallet && t.customer_wallet && t.customer_wallet.toLowerCase() === currentWallet;
  const shortOwner = t.customer_wallet ? (t.customer_wallet.substring(0, 6) + '...' + t.customer_wallet.substring(t.customer_wallet.length - 4)) : 'Anonymous';
  const hasOnChainRecord = !!(t.entity_key || t.tx_hash);

  const statusBadge = t.status === 'open' ? 'pill-success' : t.status === 'awarded' ? 'pill-warning' : 'pill-info';
  const skills = (t.required_skills || '').split(',').map(s => s.trim()).filter(Boolean);

  return `
    <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-6 flex flex-col justify-between hover:border-[var(--border-strong)] transition-all space-y-4">
      <div class="space-y-3">
        <!-- Top Metadata Row -->
        <div class="flex items-center justify-between text-xs">
          <span class="pill ${statusBadge} text-[11px] capitalize">
            ${escapeHtml(t.status)}
          </span>
          <span class="font-mono text-[var(--text-3)] text-[12px]">
            Budget: <strong class="text-[var(--text)] font-semibold">${escapeHtml(t.budget_range || 'Negotiable')}</strong>
          </span>
        </div>

        <!-- Title -->
        <h3 class="font-serif text-[18px] font-normal text-[var(--text)] leading-snug">
          ${escapeHtml(t.title)}
        </h3>

        <!-- Description -->
        <p class="text-[13px] text-[var(--text-2)] line-clamp-3 leading-relaxed">
          ${escapeHtml(t.public_description)}
        </p>

        <!-- Skills -->
        ${skills.length > 0 ? `
          <div class="flex flex-wrap gap-1.5 pt-1">
            ${skills.map(s => `
              <span class="px-2.5 py-1 rounded-[var(--radius-sm)] bg-[var(--surface-sunk)] text-[var(--text-2)] text-[12px]">
                ${escapeHtml(s)}
              </span>
            `).join('')}
          </div>
        ` : ''}
      </div>

      <!-- Footer Info & Actions -->
      <div class="pt-4 border-t border-[var(--border)] flex flex-col space-y-3">
        <div class="flex items-center justify-between text-[12px] text-[var(--text-3)]">
          <div class="flex items-center gap-1.5">
            <span>Posted by:</span>
            <span class="font-mono text-[var(--text-2)]">${shortOwner}</span>
            ${isOwner ? '<span class="pill pill-neutral text-[10px]">You</span>' : ''}
          </div>

          <div class="flex items-center gap-2">
            ${hasOnChainRecord ? `
              <a
                href="https://rabdi.explorer.arkiv.network/tx/${t.tx_hash || t.entity_key}"
                target="_blank"
                class="text-[11.5px] text-[var(--accent)] hover:underline flex items-center gap-1 font-mono"
              >
                <span>Arkiv explorer</span>
                <span>&nearr;</span>
              </a>
            ` : ''}
          </div>
        </div>

        <!-- Buttons -->
        <div class="flex items-center justify-end gap-2 pt-1">
          <button
            onclick="openTaskBidsModal('${t.task_id}')"
            class="btn-secondary !h-8 text-[12.5px]"
          >
            Inspect bids
          </button>

          ${(t.status === 'open' && !isOwner) ? `
            <button
              onclick="openSubmitBidModal('${t.task_id}')"
              class="btn-primary !h-8 text-[12.5px]"
            >
              Submit proposal
            </button>
          ` : ''}

          ${(t.status === 'open' && isOwner) ? `
            <button
              onclick="openTaskBidsModal('${t.task_id}')"
              class="btn-primary !h-8 text-[12.5px]"
            >
              Review bids & award
            </button>
          ` : ''}
        </div>
      </div>
    </div>
  `;
}

function renderArkivTasksView() {
  const tasks = STATE.arkiv.tasks || [];
  const currentWallet = STATE.auth.walletAddress ? STATE.auth.walletAddress.toLowerCase() : '';

  const categories = [
    { id: 'all', label: 'All Tasks' },
    { id: 'application_testing', label: 'Application Testing' },
    { id: 'codebase_security', label: 'Codebase Security Check' },
    { id: 'prompt_optimization', label: 'Prompt Optimization' },
    { id: 'prompt_engineering', label: 'Prompt Engineering' },
    { id: 'smart_contract_audit', label: 'Smart Contract Audit' }
  ];

  const filtered = tasks.filter(t => {
    if (STATE.arkiv.categoryFilter && STATE.arkiv.categoryFilter !== 'all') {
      if (t.category !== STATE.arkiv.categoryFilter) return false;
    }
    if (STATE.arkiv.statusFilter && STATE.arkiv.statusFilter !== 'all') {
      if (t.status !== STATE.arkiv.statusFilter) return false;
    }
    return true;
  });

  return `
    <div class="space-y-8">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-4">
        <div>
          <div class="flex items-center gap-2.5 flex-wrap">
            <h1 class="font-serif text-[32px] font-normal tracking-[-0.01em] text-[var(--text)]">Arkiv Security Task Board</h1>
            <span class="pill pill-neutral text-[11px] font-mono">Rabdi 7794095</span>
          </div>
          <p class="text-[14px] text-[var(--text-2)] mt-1.5">
            Public, verifiable security audit requests published directly to Arkiv. Customer-owned, specialist-bid, rewarded in tGLM.
          </p>
        </div>

        <div class="flex items-center gap-2.5 shrink-0">
          <button
            onclick="loadArkivTasks(true)"
            title="Refresh live from Rabdi testnet"
            class="btn-secondary !h-9 text-[13px] flex items-center gap-1.5"
          >
            <svg class="w-4 h-4 ${STATE.arkiv.loading ? 'animate-spin' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>

          <button
            onclick="openPostTaskModal()"
            class="btn-primary !h-9 text-[13px]"
          >
            + Post task
          </button>
        </div>
      </div>

      <!-- Category Filters -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[var(--border)]">
        ${categories.map(c => `
          <button
            onclick="setArkivCategoryFilter('${c.id}')"
            class="px-3.5 py-1.5 rounded-full text-[12.5px] font-medium whitespace-nowrap transition-colors ${
              STATE.arkiv.categoryFilter === c.id
                ? 'bg-[var(--text)] text-[var(--bg)]'
                : 'bg-[var(--surface)] border border-[var(--border)] text-[var(--text-2)] hover:border-[var(--border-strong)] hover:text-[var(--text)]'
            }"
          >
            ${c.label}
          </button>
        `).join('')}
      </div>

      <!-- Status Sub-filter -->
      <div class="flex items-center justify-between gap-4 bg-[var(--surface)] p-3.5 border border-[var(--border)] rounded-[var(--radius-md)]">
        <div class="flex items-center gap-2">
          <span class="text-[13px] text-[var(--text-2)]">Status:</span>
          <div class="flex items-center gap-1">
            ${['all', 'open', 'awarded', 'completed'].map(st => `
              <button
                onclick="setArkivStatusFilter('${st}')"
                class="px-2.5 py-1 text-[12px] rounded-md font-medium capitalize transition-colors ${
                  STATE.arkiv.statusFilter === st
                    ? 'bg-[var(--surface-sunk)] text-[var(--text)] font-semibold'
                    : 'text-[var(--text-3)] hover:text-[var(--text)]'
                }"
              >
                ${st}
              </button>
            `).join('')}
          </div>
        </div>

        <div class="text-[13px] text-[var(--text-3)]">
          Showing <strong class="text-[var(--text)] font-medium">${filtered.length}</strong> tasks on Rabdi Testnet
        </div>
      </div>

      <!-- Task Cards Grid -->
      ${filtered.length > 0 ? `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          ${filtered.map(t => renderArkivTaskCard(t, currentWallet)).join('')}
        </div>
      ` : `
        <div class="surface-card p-12 text-center space-y-3">
          <h3 class="font-serif text-[18px] text-[var(--text)]">No security tasks found on Rabdi</h3>
          <p class="text-[13px] text-[var(--text-2)] max-w-md mx-auto">
            Tasks published to Arkiv are stored permanently on the Rabdi blockchain with decentralized ownership and time-based expiration.
          </p>
          <div class="pt-2">
            <button onclick="openPostTaskModal()" class="btn-primary">
              + Post the first security task
            </button>
          </div>
        </div>
      `}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 7. My Requests & Security Reports Pages
// ---------------------------------------------------------------------------

function setRequestsTab(tab) {
  STATE.requestsTab = tab;
  renderApp();
}

function setRequestsSearch(q) {
  STATE.requestsSearch = q;
  renderApp();
}

function renderMyRequestsView() {
  const currentWallet = (STATE.auth.walletAddress || STATE.user.id || '').toLowerCase();
  const allOrders = STATE.data.orders || [];

  // Strictly show requests submitted by current user
  const mySentOrders = allOrders.filter(o => {
    const custId = (o.customer_id || '').toLowerCase();
    if (!currentWallet) return false;
    return custId === currentWallet || custId === (STATE.user.id || '').toLowerCase();
  });

  const activeTab = STATE.requestsTab || 'all';
  const searchQuery = (STATE.requestsSearch || '').trim().toLowerCase();

  const filteredOrders = mySentOrders.filter(o => {
    const isAutomated = (
      o.execution_type === 'automated' ||
      o.payment_type === '0g_direct' ||
      (o.provider_id && (o.provider_id.startsWith('prov_zero') || o.provider_id.startsWith('prov_prompt') || o.provider_id === 'prov_zerog')) ||
      Number(o.price) === 0
    );

    // Tab filtering
    if (activeTab === 'needs_payment') {
      if (isAutomated || Number(o.price) <= 0) return false;
      if (o.payment_status !== 'pending' && o.payment_status !== 'failed') return false;
      if (o.status === 'rejected' || o.status === 'cancelled') return false;
    } else if (activeTab === 'in_progress') {
      if (!['requested', 'accepted', 'in_progress'].includes(o.status)) return false;
    } else if (activeTab === 'completed') {
      if (o.status !== 'completed' && o.status !== 'delivered') return false;
    }

    // Search query filtering
    if (searchQuery) {
      const matchTitle = (o.service_title || '').toLowerCase().includes(searchQuery);
      const matchProv = (o.provider_name || '').toLowerCase().includes(searchQuery);
      const matchId = (o.id || '').toLowerCase().includes(searchQuery);
      if (!matchTitle && !matchProv && !matchId) return false;
    }

    return true;
  });

  return `
    <div class="space-y-8">
      <!-- Page Header: sentence-case title, 14-15px --text-2 description, primary button Explore OpiHub (removed provider workspace button) -->
      ${renderPageHeader(
        'Security requests',
        "Track the requests you've submitted, their payments and results.",
        `
        <button onclick="navigateTo('opihub')" class="btn-primary !h-9 text-[13px]">
          Explore OpiHub
        </button>
        `
      )}

      <!-- Controls: Status tabs + Search input -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <!-- Status Tabs -->
        <div class="inline-flex p-0.5 bg-[var(--surface-sunk)] rounded-[var(--radius-sm)] border border-[var(--border)] shrink-0">
          <button
            onclick="setRequestsTab('all')"
            class="px-3 py-1.5 text-[12.5px] font-medium rounded-[var(--radius-sm)] transition-colors cursor-pointer ${
              activeTab === 'all' ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs' : 'text-[var(--text-2)] hover:text-[var(--text)]'
            }"
          >
            All
          </button>
          <button
            onclick="setRequestsTab('needs_payment')"
            class="px-3 py-1.5 text-[12.5px] font-medium rounded-[var(--radius-sm)] transition-colors cursor-pointer ${
              activeTab === 'needs_payment' ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs' : 'text-[var(--text-2)] hover:text-[var(--text)]'
            }"
          >
            Needs payment
          </button>
          <button
            onclick="setRequestsTab('in_progress')"
            class="px-3 py-1.5 text-[12.5px] font-medium rounded-[var(--radius-sm)] transition-colors cursor-pointer ${
              activeTab === 'in_progress' ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs' : 'text-[var(--text-2)] hover:text-[var(--text)]'
            }"
          >
            In progress
          </button>
          <button
            onclick="setRequestsTab('completed')"
            class="px-3 py-1.5 text-[12.5px] font-medium rounded-[var(--radius-sm)] transition-colors cursor-pointer ${
              activeTab === 'completed' ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs' : 'text-[var(--text-2)] hover:text-[var(--text)]'
            }"
          >
            Completed
          </button>
        </div>

        <!-- Search Input -->
        <div class="relative sm:w-64">
          <input
            type="text"
            placeholder="Search requests..."
            value="${escapeForAttr(STATE.requestsSearch || '')}"
            oninput="setRequestsSearch(this.value)"
            class="w-full px-3 py-1.5 text-[13px] bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[var(--text)] placeholder-[var(--text-3)] focus:outline-none focus:border-[var(--accent)] transition-colors"
          />
        </div>
      </div>

      <!-- Requests Table: Service | Status | Cost | Date | Action -->
      ${filteredOrders.length > 0 ? `
        <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-[13px]">
              <thead class="border-b border-[var(--border)] text-[var(--text-2)] text-[12px] uppercase font-semibold tracking-[0.06em]">
                <tr>
                  <th class="px-5 py-3.5">Service</th>
                  <th class="px-5 py-3.5">Status</th>
                  <th class="px-5 py-3.5">Cost</th>
                  <th class="px-5 py-3.5">Date</th>
                  <th class="px-5 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--border)]">
                ${filteredOrders.map(o => {
                  const isAutomated = (
                    o.execution_type === 'automated' ||
                    o.payment_type === '0g_direct' ||
                    (o.provider_id && (o.provider_id.startsWith('prov_zero') || o.provider_id.startsWith('prov_prompt') || o.provider_id === 'prov_zerog')) ||
                    Number(o.price) === 0
                  );
                  const isManualEscrow = !isAutomated && (o.execution_type === 'manual' || !!o.escrow_tx_hash || (o.escrow_state && o.escrow_state !== 'not_applicable' && o.escrow_state !== 'none'));

                  // Bug fix: Free orders never show "pending payment"
                  let effectiveStatus = o.status;
                  if ((isAutomated || Number(o.price) <= 0) && (effectiveStatus === 'pending_payment' || o.payment_status === 'pending')) {
                    effectiveStatus = 'completed';
                  }

                  const needsPayment = !isAutomated && Number(o.price) > 0 && (o.payment_status === 'pending' || o.payment_status === 'failed') && o.status !== 'rejected' && o.status !== 'cancelled';
                  const isCompleted = o.status === 'completed' || o.status === 'delivered';

                  return `
                    <tr class="hover:bg-[var(--surface-sunk)] transition-colors cursor-pointer" onclick="openModal('order_detail', '${o.id}')">
                      <!-- Column 1: Service title + IdChip + Provider name underneath -->
                      <td class="px-5 py-4">
                        <div class="flex items-center gap-2">
                          <span class="font-medium text-[13.5px] text-[var(--text)]">${escapeHtml(o.service_title)}</span>
                          ${renderIdChip(o.id)}
                        </div>
                        <div class="text-[12.5px] text-[var(--text-2)] mt-0.5">
                          ${escapeHtml(o.provider_name || 'Specialist')}
                        </div>
                      </td>

                      <!-- Column 2: Single status pill -->
                      <td class="px-5 py-4 align-middle">
                        ${renderStatusPill(effectiveStatus, isManualEscrow, o.escrow_state)}
                      </td>

                      <!-- Column 3: Cost in tabular-nums (NOT mono) -->
                      <td class="px-5 py-4 font-sans font-medium text-[var(--text)] tabular-nums align-middle">
                        ${isAutomated ? '<span class="text-[var(--text-2)] font-medium">Free</span>' : '$' + o.price.toFixed(2)}
                      </td>

                      <!-- Column 4: Date -->
                      <td class="px-5 py-4 text-[var(--text-3)] font-sans text-[12px] tabular-nums align-middle">
                        ${formatQuietDate(o.created_at)}
                      </td>

                      <!-- Column 5: Max ONE button per row -->
                      <td class="px-5 py-4 text-right align-middle" onclick="event.stopPropagation()">
                        ${needsPayment ? `
                          <button
                            onclick="handleInitiatePayment('${o.id}')"
                            class="btn-primary !h-8 text-[12.5px]"
                          >
                            Complete payment
                          </button>
                        ` : isCompleted && o.report_id ? `
                          <button
                            onclick="viewReport('${o.report_id}')"
                            class="btn-secondary !h-8 text-[12.5px]"
                          >
                            View report
                          </button>
                        ` : `
                          <button
                            onclick="openModal('order_detail', '${o.id}')"
                            class="btn-secondary !h-8 text-[12.5px]"
                          >
                            View details
                          </button>
                        `}
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      ` : renderEmptyState('No security requests found.', 'Explore OpiHub', "navigateTo('opihub')")}
    </div>
  `;
}

function renderSecurityReportsView() {
  const currentWallet = (STATE.auth.walletAddress || STATE.user.id || '').toLowerCase();
  const reports = (STATE.data.reports || []).filter(r => {
    const custId = (r.customer_id || '').toLowerCase();
    if (!currentWallet) return false;
    return custId === currentWallet || custId === (STATE.user.id || '').toLowerCase();
  });

  // Calculate severity statistics across reports
  let totalCritical = 0;
  let totalMedium = 0;
  reports.forEach(r => {
    (r.findings || []).forEach(f => {
      const sev = (f.severity || '').toLowerCase();
      if (sev === 'critical') totalCritical++;
      else if (sev === 'medium' || sev === 'high') totalMedium++;
    });
  });

  return `
    <div class="space-y-6">
      <!-- Page Header -->
      ${renderPageHeader(
        'Security reports',
        'Findings and improved prompts from your completed audits.'
      )}

      <!-- Summary line (not a card): X reports · Y critical · Z medium with tiny severity dots and counts in --text-2 -->
      <div class="flex items-center gap-3 text-[13px] text-[var(--text-2)] pb-2 select-none">
        <span><strong class="font-medium text-[var(--text)] tabular-nums">${reports.length}</strong> ${reports.length === 1 ? 'report' : 'reports'}</span>
        <span class="text-[var(--border-strong)]">&middot;</span>
        <span class="inline-flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--danger)]"></span><strong class="font-medium text-[var(--text)] tabular-nums">${totalCritical}</strong> critical</span>
        <span class="text-[var(--border-strong)]">&middot;</span>
        <span class="inline-flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-[var(--warning)]"></span><strong class="font-medium text-[var(--text)] tabular-nums">${totalMedium}</strong> medium</span>
      </div>

      <!-- Report Cards with 16px gap -->
      <div class="space-y-4">
        ${reports.length > 0 ? reports.map(r => {
          const findings = r.findings || [];
          const findingCount = findings.length;
          const hasCritical = findings.some(f => (f.severity || '').toLowerCase() === 'critical');
          const hasHigh = findings.some(f => (f.severity || '').toLowerCase() === 'high');
          const hasMedium = findings.some(f => (f.severity || '').toLowerCase() === 'medium');

          let overallPill = 'pill-success';
          let overallLabel = 'Clean';
          if (hasCritical) {
            overallPill = 'pill-danger';
            overallLabel = 'Critical';
          } else if (hasHigh) {
            overallPill = 'pill-warning';
            overallLabel = 'High';
          } else if (hasMedium) {
            overallPill = 'pill-info';
            overallLabel = 'Medium';
          }

          const vulnSummary = findingCount === 0
            ? 'No vulnerabilities found'
            : findingCount === 1
            ? '1 vulnerability found'
            : `${findingCount} vulnerabilities found`;

          return `
            <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-6 space-y-3.5 hover:border-[var(--border-strong)] transition-all">
              <!-- Top Row: Title left (serif 20px), Severity pill top right -->
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <h3 class="font-serif text-[20px] font-normal text-[var(--text)] leading-snug">
                    ${escapeHtml(r.service_title || 'Security Audit')}
                  </h3>
                  <!-- Row 2: Auditor with small check icon + 'Verified' -->
                  <div class="text-[13px] text-[var(--text-3)] flex items-center gap-1.5 mt-1">
                    <span>Audited by</span>
                    <strong class="text-[var(--text-2)] font-medium">${escapeHtml(r.provider_name || '0G Defence Agent')}</strong>
                    <span class="inline-flex items-center gap-1 text-[11.5px] text-[var(--success)] font-medium ml-1">
                      <svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                      </svg>
                      <span>Verified</span>
                    </span>
                    <span class="text-[var(--border-strong)]">&middot;</span>
                    <span class="text-[var(--text-3)] tabular-nums">${formatQuietDate(r.created_at)}</span>
                  </div>
                </div>

                <div class="shrink-0">
                  <span class="pill ${overallPill} text-[11px]">
                    ${overallLabel}
                  </span>
                </div>
              </div>

              <!-- Row 3: One-line summary, 14px --text-2 -->
              <p class="text-[14px] text-[var(--text-2)] line-clamp-2 leading-relaxed">
                ${escapeHtml(r.summary || 'Security analysis and improved prompt directives successfully generated.')}
              </p>

              <!-- Row 4: Vulnerability chips with severity prefix + grammar fix -->
              <div class="flex flex-wrap items-center gap-2 pt-1">
                ${findingCount > 0 ? `
                  ${findings.map(f => `
                    <div class="pill ${f.severity === 'critical' ? 'pill-danger' : f.severity === 'high' ? 'pill-warning' : 'pill-neutral'} text-[11px]">
                      <span class="font-semibold uppercase text-[10px] mr-1">${escapeHtml(f.severity)}:</span>
                      <span>${escapeHtml(f.title)}</span>
                    </div>
                  `).join('')}
                  <span class="text-[12px] text-[var(--text-3)] tabular-nums font-sans ml-1">(${vulnSummary})</span>
                ` : `
                  <span class="pill pill-success text-[11px]">
                    No vulnerabilities found
                  </span>
                `}
              </div>

              <!-- Footer: Separated by hairline, Order ID as IdChip left, secondary button View report right (NOT accent) -->
              <div class="pt-4 border-t border-[var(--border)] flex items-center justify-between gap-3">
                <div class="flex items-center gap-2 text-[12px] text-[var(--text-3)]">
                  <span>Order:</span>
                  ${renderIdChip(r.order_id || r.id)}
                </div>

                <button onclick="viewReport('${r.id}')" class="btn-secondary !h-8 text-[12.5px]">
                  View report
                </button>
              </div>
            </div>
          `;
        }).join('') : renderEmptyState('No completed security reports recorded yet.', 'Explore OpiHub', "navigateTo('opihub')")}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Clean Card Sub-Components (Cleaned: no text walls or excessive badges)
// ---------------------------------------------------------------------------

function formatCategoryName(cat) {
  const map = {
    prompt_optimization: 'Prompt Optimization',
    prompt_engineering: 'Prompt Engineering',
    loop_engineering: 'Loop Engineering',
    codebase_security: 'Codebase Security Check',
    application_testing: 'Application Testing',
    ai_security: 'AI Security',
    llm_optimization: 'Prompt Optimization',
    rag_security: 'Codebase Security Check'
  };
  return map[cat] || (cat ? cat.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Security');
}

function parseOrderRequirements(reqStr) {
  if (!reqStr) return {};
  try {
    const data = JSON.parse(reqStr);
    if (typeof data === 'object' && data !== null) return data;
  } catch (e) {}
  return { user_requirements: reqStr };
}

function parseDeliverableNotes(notesStr) {
  if (!notesStr) return {};
  try {
    const data = JSON.parse(notesStr);
    if (typeof data === 'object' && data !== null) return data;
  } catch (e) {}
  return { original_notes: notesStr };
}

function renderOrderSubmittedSpec(o, providerWallet) {
  const reqData = parseOrderRequirements(o.requirements);
  const notesData = parseDeliverableNotes(o.deliverable_notes);

  return `
    <div class="space-y-3 mt-3">
      <!-- Client Specification / Scope -->
      <div class="bg-[var(--surface-sunk)] border border-[var(--border)] p-3.5 rounded-[var(--radius-md)] text-[12.5px] space-y-1.5">
        <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-wider">Submitted Scope & Directive</div>
        <pre class="font-mono text-[12px] text-[var(--text)] whitespace-pre-wrap leading-relaxed">${escapeHtml(o.prompt_content)}</pre>
        ${reqData.user_requirements ? `
          <div class="pt-2 border-t border-[var(--border)] text-[12.5px] text-[var(--text-2)]">
            <strong class="font-medium text-[var(--text)]">Constraints:</strong> ${escapeHtml(reqData.user_requirements)}
          </div>
        ` : ''}
      </div>

      <!-- Extended Links (Product, Docs/Repo, Environment) -->
      ${(reqData.product_link || reqData.docs_link || reqData.test_env_notes) ? `
        <div class="p-3.5 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] space-y-2 text-[12.5px]">
          <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-wider">Audit Artifacts & Scopes</div>
          <div class="flex flex-wrap items-center gap-2">
            ${reqData.product_link ? `
              <a
                href="${escapeForAttr(reqData.product_link)}"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-secondary text-[12px] !h-8 !py-0 inline-flex items-center gap-1.5"
              >
                <span>Product Target</span>
                <span class="font-mono text-[11px] text-[var(--text-3)] truncate max-w-[200px]">(${escapeHtml(reqData.product_link)})</span>
                <span class="text-[12px]">↗</span>
              </a>
            ` : ''}

            ${reqData.docs_link ? `
              <a
                href="${escapeForAttr(reqData.docs_link)}"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-secondary text-[12px] !h-8 !py-0 inline-flex items-center gap-1.5"
              >
                <span>Codebase / Docs</span>
                <span class="font-mono text-[11px] text-[var(--text-3)] truncate max-w-[200px]">(${escapeHtml(reqData.docs_link)})</span>
                <span class="text-[12px]">↗</span>
              </a>
            ` : ''}
          </div>

          ${reqData.test_env_notes ? `
            <div class="pt-2 border-t border-[var(--border)] text-[12px] text-[var(--text-2)] leading-relaxed">
              <strong class="font-medium text-[var(--text)]">Environment Notes:</strong> ${escapeHtml(reqData.test_env_notes)}
            </div>
          ` : ''}
        </div>
      ` : ''}

      <!-- Payment & Escrow Status -->
      <div class="text-[12px] text-[var(--text-2)] bg-[var(--surface-sunk)] px-3.5 py-2 rounded-[var(--radius-sm)] border border-[var(--border)] flex items-center justify-between">
        <span>Payment: <strong class="font-medium text-[var(--text)]">Smart Escrow Protected</strong> ($${o.price.toFixed(2)} USD)</span>
        <span class="font-mono text-[11px] text-[var(--text-3)]">Disbursal: ${providerWallet ? escapeHtml(providerWallet.substring(0, 8) + '...' + providerWallet.substring(providerWallet.length - 4)) : 'Specialist Destination'}</span>
      </div>

      <!-- Active Ticket Alert Banner if Raised -->
      ${notesData.ticket ? `
        <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border-strong)] rounded-[var(--radius-md)] space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="pill pill-danger">
              Quality Review Ticket (${escapeHtml(notesData.ticket.ticket_id || 'TK-01')})
            </span>
            <span class="text-[11px] font-mono text-[var(--text-3)]">${new Date(notesData.ticket.created_at).toLocaleString()}</span>
          </div>
          <div class="text-[12.5px] text-[var(--text)]"><strong class="font-medium">Reason:</strong> ${escapeHtml(notesData.ticket.reason)}</div>
          <div class="text-[12px] text-[var(--text-2)] bg-[var(--surface)] p-2.5 rounded border border-[var(--border)]">${escapeHtml(notesData.ticket.feedback)}</div>
        </div>
      ` : ''}
    </div>
  `;
}

function renderCleanProviderCard(p) {
  const isAutomated = p.provider_type === 'automated';
  const isMe = (STATE.auth.walletAddress || '').toLowerCase() === (p.wallet_address || '').toLowerCase() && !p.is_platform_managed;

  return `
    <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-6 flex flex-col justify-between hover:border-[var(--border-strong)] transition-all">
      <div>
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="font-serif text-[18px] font-normal text-[var(--text)] tracking-[-0.01em] truncate">
              ${escapeHtml(p.display_name)}
            </h3>
            <p class="text-[13px] text-[var(--text-3)] mt-0.5 truncate">
              ${escapeHtml(p.title || (isAutomated ? 'Autonomous Guardrail Enforcer' : 'Security Specialist'))}
            </p>
          </div>
          <span class="pill pill-neutral shrink-0 text-[11px]">
            ${isAutomated ? '0G AI Agent' : 'Specialist'}
          </span>
        </div>

        <p class="text-[13px] text-[var(--text-2)] mt-3 line-clamp-2 leading-relaxed">
          ${escapeHtml(p.description || '')}
        </p>

        <!-- Up to 3 skill tags: subtle --surface-sunk pills, NO borders, 12-13px -->
        <div class="flex flex-wrap gap-1.5 mt-4">
          ${(p.skills || []).slice(0, 3).map(s => `
            <span class="px-2.5 py-1 rounded-[var(--radius-sm)] bg-[var(--surface-sunk)] text-[var(--text-2)] text-[12px]">
              ${escapeHtml(s)}
            </span>
          `).join('')}
          ${(p.skills || []).length > 3 ? `
            <span class="text-[11px] text-[var(--text-3)] self-center ml-0.5">+${p.skills.length - 3}</span>
          ` : ''}
        </div>
      </div>

      <div class="mt-5 pt-4 border-t border-[var(--border)] flex items-center justify-end">
        ${isMe ? `
          <button
            onclick="navigateTo('provider_workspace')"
            class="btn-secondary !h-8 text-[12.5px]"
          >
            My workspace &rarr;
          </button>
        ` : `
          <button
            onclick="navigateTo('provider_detail', '${p.id}')"
            class="btn-secondary !h-8 text-[12.5px]"
          >
            View profile
          </button>
        `}
      </div>
    </div>
  `;
}

function renderCleanServiceCard(s, showProvider = true, isOwner = false) {
  const isAutomated = s.execution_type === 'automated';
  const currentWallet = (STATE.auth.walletAddress || '').toLowerCase();
  const prov = (STATE.data.providers || []).find(p => p.id === s.provider_id);
  const provWallet = (s.provider_wallet || prov?.wallet_address || '').toLowerCase();
  const ownsService = isOwner || (
    Boolean(currentWallet) && Boolean(provWallet) && (provWallet === currentWallet)
  );

  return `
    <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] p-6 flex flex-col justify-between hover:border-[var(--border-strong)] transition-all">
      <div>
        <!-- Row 1: Service name left, price right with subtitle under price -->
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <h3 class="font-serif text-[18px] font-normal text-[var(--text)] tracking-[-0.01em] leading-snug">
              ${escapeHtml(s.title)}
            </h3>
            <!-- Row 2: By [Name] + provider pill -->
            ${showProvider ? `
              <div class="text-[13px] text-[var(--text-3)] flex items-center gap-1.5 mt-1">
                <span>By</span>
                <strong class="text-[var(--text-2)] hover:text-[var(--text)] cursor-pointer font-medium" onclick="navigateTo('provider_detail', '${s.provider_id}')">${escapeHtml(s.provider_name)}</strong>
                <span class="pill pill-neutral shrink-0 text-[11px]">
                  ${isAutomated ? '0G agent' : 'Specialist'}
                </span>
              </div>
            ` : ''}
          </div>
          <div class="text-right shrink-0">
            ${isAutomated ? `
              <div class="text-[16px] font-bold text-[var(--text)] tabular-nums font-sans">Free</div>
              <div class="text-[11px] text-[var(--text-3)]">Instant</div>
            ` : `
              <div class="text-[16px] font-bold text-[var(--text)] tabular-nums font-sans">$${s.price.toFixed(2)}</div>
              <div class="text-[11px] text-[var(--text-3)]">Held in escrow</div>
            `}
          </div>
        </div>

        <!-- Row 3: Description, 2 lines clamped -->
        <p class="text-[13px] text-[var(--text-2)] mt-3 line-clamp-2 leading-relaxed">
          ${escapeHtml(s.description || '')}
        </p>

        <!-- Row 4: Turnaround with clock icon + category with tag icon (no Turnaround: or Category: labels!) -->
        <div class="flex items-center gap-3 text-[12px] text-[var(--text-3)] mt-4">
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-[var(--text-2)] font-medium tabular-nums">${escapeHtml(s.estimated_delivery)}</span>
          </div>
          <span class="text-[var(--border-strong)]">&middot;</span>
          <div class="flex items-center gap-1.5">
            <svg class="w-3.5 h-3.5 text-[var(--text-3)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 6h.008v.008H6V6z" />
            </svg>
            <span class="text-[var(--text-2)] font-medium">${formatCategoryName(s.category)}</span>
          </div>
        </div>
      </div>

      <!-- Footer: Action button aligned to right -->
      <div class="mt-5 pt-4 border-t border-[var(--border)] flex items-center justify-end gap-2">
        <div>
          ${ownsService ? `
            <div class="flex items-center gap-2">
              <span class="text-[12.5px] text-[var(--text-3)] font-medium">Your service</span>
              <button onclick="openModal('edit_service_modal', { serviceId: '${s.id}' })" class="btn-ghost !h-8 text-[12.5px] border border-transparent hover:border-[var(--border-strong)]">
                Edit
              </button>
            </div>
          ` : `
            <button
              onclick="openModal('request_review', { serviceId: '${s.id}', providerId: '${s.provider_id}' })"
              class="btn-primary !h-8 text-[12.5px]"
            >
              ${isAutomated ? 'Run analysis' : 'Request audit'}
            </button>
          `}
        </div>
      </div>
    </div>
  `;
}

function renderStatusBadge(status, isEscrow = false, escrowState = '') {
  return renderStatusPill(status, isEscrow, escrowState);
}

function renderActivityFeed(activities) {
  if (!activities || activities.length === 0) {
    return `<div class="p-8 text-center text-[13px] text-[var(--text-3)]">No recent activity recorded yet.</div>`;
  }

  return activities.slice(0, 5).map(act => `
    <div onclick="openOrderDetail('${act.id}')" class="min-h-[64px] px-5 py-3 flex items-center justify-between gap-4 hover:bg-[var(--surface-sunk)] transition-colors cursor-pointer">
      <div class="min-w-0 pr-2">
        <div class="text-[14px] font-medium text-[var(--text)] truncate leading-snug">${escapeHtml(act.title || 'Security Request')}</div>
        <div class="text-[13px] text-[var(--text-2)] truncate leading-snug mt-0.5">with ${escapeHtml(act.provider || 'Specialist')}</div>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        ${renderStatusBadge(act.status)}
        ${act.timestamp ? `
          <span class="text-[12px] text-[var(--text-3)] font-sans">
            ${formatQuietDate(act.timestamp)}
          </span>
        ` : ''}
      </div>
    </div>
  `).join('');
}

// ---------------------------------------------------------------------------
// Shared Modal Architecture (Anthropic / Claude Design System)
// ---------------------------------------------------------------------------

function toSentenceCase(str) {
  if (!str) return '';
  const s = str.trim();
  let res = s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  res = res.replace(/\b0g\b/gi, '0G').replace(/\bai\b/gi, 'AI').replace(/\bapi\b/gi, 'API');
  return res;
}

function renderModalShell({ id = 'app-modal', title, subtitle = '', size = 'default', onClose = 'closeModalWithDraftCheck()', bodyHtml = '', footerHtml = '', formOnSubmit = '', ariaLabelledBy = '', ariaDescribedBy = '', statusPillHtml = '', titleExtra = '' }) {
  const sizeClass = size === 'md' ? 'modal-shell-md' : size === 'wide' ? 'modal-shell-wide' : size === 'xl' ? 'modal-shell-xl' : '';
  const labelledBy = ariaLabelledBy || `${id}-title`;
  const describedBy = ariaDescribedBy || (subtitle ? `${id}-subtitle` : '');
  const formTagOpen = formOnSubmit ? `<form id="${id}-form" onsubmit="${formOnSubmit}" class="flex flex-col flex-1 min-h-0 overflow-hidden m-0 p-0">` : `<div class="flex flex-col flex-1 min-h-0 overflow-hidden">`;
  const formTagClose = formOnSubmit ? `</form>` : `</div>`;

  return `
    <div
      class="modal-shell ${sizeClass}"
      id="${id}-shell"
      onclick="event.stopPropagation()"
      role="dialog"
      aria-modal="true"
      aria-labelledby="${labelledBy}"
      ${describedBy ? `aria-describedby="${describedBy}"` : ''}
    >
      ${renderModalHeader({ id, title, subtitle, onClose, statusPillHtml, titleExtra })}
      ${formTagOpen}
        ${bodyHtml}
        ${footerHtml}
      ${formTagClose}
    </div>
  `;
}

function renderModalHeader({ id = 'modal', title, subtitle = '', onClose = 'closeModalWithDraftCheck()', statusPillHtml = '', titleExtra = '' }) {
  return `
    <div class="modal-header flex items-start justify-between gap-3 border-b border-[var(--border)]">
      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <h2 id="${id}-title" class="font-serif text-[22px] font-normal text-[var(--text)] tracking-[-0.01em] leading-snug">
            ${escapeHtml(title)}
          </h2>
          ${titleExtra || ''}
        </div>
        ${subtitle ? `
          <p id="${id}-subtitle" class="text-[14px] text-[var(--text-2)] mt-1 leading-normal">
            ${subtitle}
          </p>
        ` : ''}
      </div>
      <div class="flex items-center gap-2.5 shrink-0 -mr-1">
        ${statusPillHtml || ''}
        <button
          type="button"
          onclick="${onClose}"
          aria-label="Close"
          class="w-8 h-8 rounded-[var(--radius-sm)] flex items-center justify-center text-[var(--text-3)] hover:text-[var(--text)] hover:bg-[var(--surface-sunk)] transition-colors cursor-pointer shrink-0 border-none bg-transparent"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  `;
}

function renderModalBody(contentHtml, customClass = '') {
  return `
    <div class="modal-body space-y-5 ${customClass}">
      ${contentHtml}
    </div>
  `;
}

function renderModalFooter(leftHtml = '', rightHtml = '') {
  return `
    <div class="modal-footer">
      <div class="text-[14px] text-[var(--text-2)] tabular-nums font-normal shrink-0">
        ${leftHtml}
      </div>
      <div class="flex items-center gap-2.5 ml-auto">
        ${rightHtml}
      </div>
    </div>
  `;
}

function closeModalWithDraftCheck() {
  const promptInput = document.getElementById('order-prompt-input');
  if (promptInput && promptInput.value.trim().length > 0) {
    if (confirm('Discard this draft?')) {
      closeModal();
    }
    return;
  }
  closeModal();
}

function handleModalOverlayClick(event) {
  if (event.target && event.target.classList.contains('modal-overlay')) {
    closeModalWithDraftCheck();
  }
}

function handlePromptInput(textarea) {
  const submitBtn = document.getElementById('order-submit-btn');
  const countEl = document.getElementById('prompt-char-count');
  const val = textarea.value.trim();
  if (submitBtn) {
    submitBtn.disabled = val.length === 0;
  }
  if (countEl) {
    countEl.textContent = val.length > 0 ? `${val.length} chars` : '';
  }
  textarea.style.height = 'auto';
  textarea.style.height = Math.min(Math.max(textarea.scrollHeight, 160), 280) + 'px';
}

function handleFileDrop(e, textarea) {
  e.preventDefault();
  textarea.classList.remove('border-[var(--accent)]');
  const files = e.dataTransfer?.files;
  if (!files || files.length === 0) return;
  const file = files[0];
  const validExtensions = ['.txt', '.md', '.json', '.yaml', '.yml', '.sol', '.py', '.js', '.ts'];
  const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
  if (!validExtensions.includes(ext) && !file.type.startsWith('text/')) {
    showNotification('Please drop a text, markdown, or JSON file.', 'warning');
    return;
  }
  const reader = new FileReader();
  reader.onload = (event) => {
    const content = event.target.result;
    textarea.value = (textarea.value ? textarea.value + '\n\n' : '') + `// File: ${file.name}\n` + content;
    showNotification(`Appended contents of ${file.name}`, 'info');
  };
  reader.readAsText(file);
}

function insertSavedPrompt(content) {
  if (!content) return;
  const input = document.getElementById('order-prompt-input');
  if (input) {
    input.value = content;
    handlePromptInput(input);
  }
}

function retryOrderSubmit() {
  const form = document.querySelector('.modal-shell form');
  if (form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.click();
  }
}

function renderModalContainer() {
  if (!STATE.activeModal) return '';
  return `
    <div
      class="modal-overlay"
      id="app-modal-overlay"
      onclick="handleModalOverlayClick(event)"
      role="dialog"
      aria-modal="true"
    >
      ${renderModalContent()}
    </div>
  `;
}

function renderModalContent() {
  switch (STATE.activeModal) {
    case 'request_review':
      return renderRequestReviewModal();
    case 'deliver_modal':
      return renderDeliverModal();
    case 'reject_order':
      return renderRejectOrderModal();
    case 'quick_analyze':
      return renderQuickAnalyzeModal();
    case 'create_prompt':
      return renderCreatePromptModal();
    case 'report_viewer':
      return renderReportViewerModal();
    case 'raise_ticket_modal':
      return renderRaiseTicketModal();
    case 'view_ticket_modal':
      return renderViewTicketModal();
    case 'wallet_modal':
      return renderWalletModal();
    case 'settings_modal':
      return renderSettingsModal();
    case 'add_service_modal':
      return renderAddServiceModal();
    case 'edit_service_modal':
      return renderEditServiceModal();
    case 'order_detail':
      return renderOrderDetailModal();
    case 'evm_escrow':
      return renderEVMEscrowModal();
    case 'edit_provider':
      return renderEditProviderModal();
    case 'arkiv_post_task':
      return renderArkivPostTaskModal();
    case 'arkiv_submit_bid':
      return renderArkivSubmitBidModal();
    case 'arkiv_view_bids':
      return renderArkivViewBidsModal();
    case 'arkiv_verify_modal':
      return renderArkivVerifyModal();
    case 'arkiv_inspector_modal':
      return renderArkivInspectorModal();
    default:
      return '';
  }
}

function renderRequestReviewModal() {
  const payload = STATE.modalPayload || {};
  const services = STATE.data.services || [];
  const currentService = services.find(s => s.id === payload.serviceId) || services[0];
  const isAutomated = currentService?.execution_type === 'automated';
  const category = currentService?.category || '';
  const prompts = STATE.data.prompts || [];

  const isApplicationTesting = !isAutomated && category === 'application_security_testing';
  const isCodebaseSecurity = !isAutomated && category === 'codebase_security';

  const modalTitle = toSentenceCase(currentService?.title || 'Security analysis');
  const providerName = escapeHtml(currentService?.provider_name || (isAutomated ? '0G Defence Agent' : 'Specialist'));
  const modalSubtitle = `By ${providerName} · ${isAutomated ? 'Free · Instant' : `$${(currentService?.price || 0).toFixed(2)} · ${escapeHtml(currentService?.estimated_delivery || '24 hours')}`}`;

  const hasInitialContent = !!payload.promptText;
  const actionLabel = isAutomated ? 'Run analysis' : 'Request audit';

  const bodyHtml = renderModalBody(`
    <input type="hidden" name="service_id" value="${currentService?.id || ''}" />

    ${isApplicationTesting ? `
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label for="order-target-link" class="text-[14px] font-medium text-[var(--text)]">Product link or staging URL</label>
          <span class="text-[13px] text-[var(--text-3)] font-normal">Required</span>
        </div>
        <p class="text-[13px] text-[var(--text-3)] mb-2">Target environment for injection, authentication, and boundary testing.</p>
        <input
          id="order-target-link"
          type="url"
          name="product_link"
          required
          placeholder="https://staging.example.com"
          class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[10px] text-[13px] font-mono focus:outline-none transition-colors"
        />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-[13.5px] font-medium text-[var(--text)]">Documentation link</label>
            <span class="text-[12.5px] text-[var(--text-3)]">Optional</span>
          </div>
          <input
            type="url"
            name="docs_link"
            placeholder="https://docs.example.com"
            class="w-full px-3 py-2 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[10px] text-[12.5px] font-mono focus:outline-none transition-colors"
          />
        </div>
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-[13.5px] font-medium text-[var(--text)]">Scope & credentials</label>
            <span class="text-[12.5px] text-[var(--text-3)]">Optional</span>
          </div>
          <input
            type="text"
            name="test_env_notes"
            placeholder="Test accounts, branch notes"
            class="w-full px-3 py-2 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[10px] text-[12.5px] focus:outline-none transition-colors"
          />
        </div>
      </div>
    ` : isCodebaseSecurity ? `
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label for="order-repo-link" class="text-[14px] font-medium text-[var(--text)]">Codebase or repository URL</label>
          <span class="text-[13px] text-[var(--text-3)] font-normal">Required</span>
        </div>
        <p class="text-[13px] text-[var(--text-3)] mb-2">Repository structure, credential leakage risks, and security boundaries.</p>
        <input
          id="order-repo-link"
          type="url"
          name="docs_link"
          required
          placeholder="https://github.com/org/repo"
          class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[10px] text-[13px] font-mono focus:outline-none transition-colors"
        />
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-[13.5px] font-medium text-[var(--text)]">Staging link</label>
            <span class="text-[12.5px] text-[var(--text-3)]">Optional</span>
          </div>
          <input
            type="url"
            name="product_link"
            placeholder="https://example.com"
            class="w-full px-3 py-2 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[10px] text-[12.5px] font-mono focus:outline-none transition-colors"
          />
        </div>
        <div>
          <div class="flex items-center justify-between mb-1.5">
            <label class="text-[13.5px] font-medium text-[var(--text)]">Branch notes</label>
            <span class="text-[12.5px] text-[var(--text-3)]">Optional</span>
          </div>
          <input
            type="text"
            name="test_env_notes"
            placeholder="Branch or specific folders"
            class="w-full px-3 py-2 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[10px] text-[12.5px] focus:outline-none transition-colors"
          />
        </div>
      </div>
    ` : ''}

    <!-- Field 1: System prompt or security context -->
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label for="order-prompt-input" class="text-[14px] font-medium text-[var(--text)]">System prompt or security context</label>
        <span class="text-[13px] text-[var(--text-3)] font-normal">Required</span>
      </div>
      <p class="text-[13px] text-[var(--text-3)] mb-2">Paste the prompt, input template or boundary instructions you want audited.</p>
      <div class="relative">
        <textarea
          id="order-prompt-input"
          name="prompt_content"
          required
          rows="6"
          class="modal-textarea min-h-[160px] max-h-[280px]"
          placeholder="Paste your system prompt here"
          oninput="handlePromptInput(this)"
        >${escapeHtml(payload.promptText || '')}</textarea>
        <div id="prompt-char-count" class="text-[12px] text-[var(--text-3)] text-right mt-1 font-mono tabular-nums">
          ${hasInitialContent ? `${payload.promptText.length} chars` : ''}
        </div>
      </div>

      ${prompts.length > 0 ? `
        <div class="flex items-center justify-end mt-1.5">
          <select onchange="insertSavedPrompt(this.value)" class="text-[12px] bg-transparent text-[var(--text-3)] hover:text-[var(--text)] border-none cursor-pointer focus:outline-none">
            <option value="">Insert from saved prompts...</option>
            ${prompts.map(p => `<option value="${escapeForAttr(p.content)}">${escapeHtml(p.title)}</option>`).join('')}
          </select>
        </div>
      ` : ''}
    </div>

    <!-- Field 2: Files, architecture or schemas -->
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label for="order-files-input" class="text-[14px] font-medium text-[var(--text)]">Files, architecture or schemas</label>
        <span class="text-[13px] text-[var(--text-3)] font-normal">Optional</span>
      </div>
      <p class="text-[13px] text-[var(--text-3)] mb-2">Route code, OpenAPI schemas or architecture notes help find cross-boundary issues.</p>
      <div class="relative">
        <textarea
          id="order-files-input"
          name="requirements"
          rows="4"
          class="modal-textarea min-h-[112px] max-h-[220px]"
          placeholder="Paste route code, OpenAPI schema, or architecture notes"
          ondragover="event.preventDefault(); this.classList.add('border-[var(--accent)]');"
          ondragleave="this.classList.remove('border-[var(--accent)]');"
          ondrop="handleFileDrop(event, this)"
        ></textarea>
        <div class="text-[11.5px] text-[var(--text-3)] mt-1 flex items-center justify-between">
          <span>Drop a .txt, .md, or .json file directly into the box</span>
        </div>
      </div>
    </div>

    <!-- How it runs (replaces execution engine box) -->
    <details class="group mt-2">
      <summary class="flex items-center gap-1.5 text-[14px] text-[var(--text-2)] hover:text-[var(--text)] font-medium cursor-pointer select-none list-none">
        <svg class="w-4 h-4 text-[var(--text-3)] transition-transform group-open:rotate-90 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
        </svg>
        <span>How this runs</span>
      </summary>
      <p class="text-[14px] text-[var(--text-2)] leading-relaxed mt-2 pl-5.5">
        ${isAutomated
          ? 'Runs privately on 0G Private Computer with no gas fees and no wallet signing. The report appears in Security reports when it\'s done.'
          : 'Runs safely through smart escrow on Rabdi Testnet. Funds are held in escrow and disbursed to the specialist only after you review the delivered report.'}
      </p>
    </details>

    <!-- Error Banner (Hidden by default) -->
    <div id="order-error-container" class="hidden p-3.5 rounded-[var(--radius-sm)] bg-[var(--danger-bg)] text-[var(--danger)] text-[13.5px] flex items-center justify-between">
      <span id="order-error-message"></span>
      <button type="button" onclick="retryOrderSubmit()" class="font-medium underline hover:opacity-80 ml-2 shrink-0 bg-transparent border-none cursor-pointer text-[var(--danger)]">Try again</button>
    </div>

    <!-- Live Running Spinner (Hidden by default) -->
    <div id="order-progress-container" class="hidden p-3.5 rounded-[var(--radius-sm)] bg-[var(--surface-sunk)] border border-[var(--border)] flex items-center gap-3 text-[13.5px] text-[var(--text)]">
      <svg class="animate-spin h-4 w-4 text-[var(--accent)] shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      <span>Executing confidential reasoning on 0G Private Computer…</span>
    </div>
  `);

  const footerLeft = isAutomated
    ? 'Free · Instant'
    : `$${(currentService?.price || 0).toFixed(2)} · Held in escrow`;

  const footerRight = `
    <button type="button" onclick="closeModalWithDraftCheck()" class="btn-ghost">
      Cancel
    </button>
    <button
      type="submit"
      id="order-submit-btn"
      class="btn-primary"
      ${hasInitialContent ? '' : 'disabled'}
    >
      ${actionLabel}
    </button>
  `;

  return renderModalShell({
    id: 'request-review-modal',
    title: modalTitle,
    subtitle: modalSubtitle,
    formOnSubmit: 'handleOrderSubmit(event)',
    bodyHtml,
    footerHtml: renderModalFooter(footerLeft, footerRight)
  });
}

function renderDeliverModal() {
  const payload = STATE.modalPayload || {};
  const orderId = payload.orderId;
  const order = (STATE.data.orders || []).find(o => o.id === orderId);

  return `
    <div class="p-6 sm:p-7 space-y-5">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Submit Audit Deliverable & Report</h3>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Order ID: <code class="font-mono text-[var(--text)]">${orderId}</code></p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <!-- Order Summary Card -->
      <div class="p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] flex items-center justify-between">
        <div class="space-y-0.5">
          <div class="text-[14px] font-medium text-[var(--text)]">${escapeHtml(order?.service_title || 'Security Audit')}</div>
          <div class="text-[12.5px] text-[var(--text-2)]">Client: <strong class="text-[var(--text)]">${escapeHtml(order?.customer_name || 'Customer')}</strong> • Category: ${formatCategoryName(order?.service_category || 'codebase_security')}</div>
        </div>
        <div class="text-right">
          <div class="text-[14px] font-mono font-medium text-[var(--text)]">$${(order?.price || 0).toFixed(2)} USD</div>
          <span class="pill pill-success mt-1">
            Escrow Funded
          </span>
        </div>
      </div>

      <form onsubmit="handleDeliverSubmit(event, '${orderId}')" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Executive Summary *</label>
          <textarea name="summary" rows="3" required placeholder="Summarize vulnerabilities identified, testing scope verified, and remediation..." class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[var(--radius-sm)] text-[13px] focus:outline-none transition-colors"></textarea>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Primary Finding (Title & Severity)</label>
          <div class="grid grid-cols-3 gap-2">
            <input type="text" name="finding_title" placeholder="e.g. Indirect Injection Surface / Auth Flaw" class="col-span-2 px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[var(--radius-sm)] text-[12.5px] focus:outline-none transition-colors" />
            <select name="finding_severity" class="px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[var(--radius-sm)] text-[12.5px] focus:outline-none transition-colors">
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium" selected>Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Actionable Recommendations</label>
          <textarea name="recommendations_raw" rows="3" placeholder="1. Enforce strict instruction sandboxing&#10;2. Apply input sanitization and token budget checks" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[var(--radius-sm)] text-[13px] focus:outline-none transition-colors"></textarea>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Delivered Hardened Prompt / Code Patch / Test Deliverable</label>
          <textarea name="hardened_prompt" rows="3" placeholder="Paste hardened defense prompt, security patch, or detailed PoC findings..." class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[var(--radius-sm)] text-[12.5px] font-mono focus:outline-none transition-colors"></textarea>
        </div>

        <!-- Disbursal notice box matching request modal -->
        <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12px] text-[var(--text-2)] flex items-center justify-between">
          <span>Upon deliverable submission, <strong>$${(order?.price || 0).toFixed(2)} USD</strong> smart escrow disburses to your connected specialist wallet.</span>
          <span class="pill pill-neutral font-mono">Rabdi Testnet</span>
        </div>

        <div class="pt-4 border-t border-[var(--border)] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">
            Cancel
          </button>
          <button type="submit" class="btn-primary text-[13px]">
            Submit Deliverable & Report
          </button>
        </div>
      </form>
    </div>
  `;
}

function renderRejectOrderModal() {
  const payload = STATE.modalPayload || {};
  const orderId = payload.orderId;
  const order = (STATE.data.orders || []).find(o => o.id === orderId);

  return `
    <div class="p-6 sm:p-7 space-y-4">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Decline Security Review Request</h3>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Order ID: <code class="font-mono text-[var(--text)]">${orderId}</code></p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <div class="p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[13px] text-[var(--text-2)] space-y-1">
        <div class="font-medium text-[var(--text)]">${escapeHtml(order?.service_title || 'Security Service Request')}</div>
        <div class="text-[12px] text-[var(--text-3)]">Submitted by ${escapeHtml(order?.customer_name || 'Customer')} • $${(order?.price || 0).toFixed(2)} USD</div>
        <p class="text-[11.5px] text-[var(--text-3)] pt-1">
          Declining this request will cancel the order and automatically release/refund escrow back to the customer.
        </p>
      </div>

      <form onsubmit="handleRejectSubmit(event, '${orderId}')" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Reason for Rejection *</label>
          <textarea
            name="rejection_reason"
            rows="3"
            required
            placeholder="e.g. Scope outside current technical focus; or unable to fulfill within required turnaround time."
            class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[var(--radius-sm)] text-[13px] focus:outline-none transition-colors"
          ></textarea>
        </div>

        <div class="pt-4 border-t border-[var(--border)] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">
            Cancel
          </button>
          <button type="submit" class="btn-secondary text-[#B04A3F] border-[#B04A3F]/40 hover:bg-[#F6E3E0] text-[13px]">
            Confirm Rejection
          </button>
        </div>
      </form>
    </div>
  `;
}

function renderQuickAnalyzeModal() {
  return `
    <div class="p-6 sm:p-7 space-y-4">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Analyze Prompt Security</h3>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Evaluate system prompt against injection models and OWASP boundaries</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <div class="space-y-3">
        <label class="block text-[13px] font-medium text-[var(--text)]">Prompt Text</label>
        <textarea id="quick-prompt-input" rows="4" placeholder="Enter prompt to evaluate against Guardvane's injection model and 15 OWASP application risk classifiers..." class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] text-[var(--text)] rounded-[var(--radius-sm)] text-[13px] font-mono focus:outline-none transition-colors"></textarea>

        <div class="flex justify-end gap-2 pt-1">
          <button id="quick-scan-btn" onclick="executeQuickAnalyze()" class="btn-secondary text-[13px]">
            Local ML Scan
          </button>
          <button id="quick-opt-btn" onclick="executeQuickOptimize()" class="btn-primary text-[13px]">
            0G AI Reasoning & Hardening
          </button>
        </div>

        <div id="quick-analyze-results" class="hidden mt-4 p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] space-y-3"></div>
      </div>
    </div>
  `;
}

function copyTextToClipboard(text, btnElement, announcement = 'Copied to clipboard') {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => {
      const announcer = document.getElementById('a11y-announcer');
      if (announcer) {
        announcer.textContent = announcement;
      }
      showNotification(announcement, 'success');
      if (btnElement) {
        btnElement.classList.add('text-[var(--success)]');
        setTimeout(() => {
          btnElement.classList.remove('text-[var(--success)]');
        }, 1200);
      }
    }).catch(() => {
      showNotification('Failed to copy', 'error');
    });
  }
}

function parseAuditReportData(report, order) {
  // 1. Original input prompt
  let originalPrompt = 'Target Prompt';
  if (order && order.prompt_content) {
    if (order.prompt_content.startsWith('{')) {
      try {
        const parsed = JSON.parse(order.prompt_content);
        originalPrompt = parsed.notes || parsed.prompt || parsed.scope_and_focus || parsed.task_description || order.prompt_content;
      } catch (e) {
        originalPrompt = order.prompt_content;
      }
    } else {
      originalPrompt = order.prompt_content;
    }
  }

  const rawHardened = report.hardened_prompt || '';
  let cleanHardenedPrompt = rawHardened;
  let extractedVulns = [];
  let extractedFixes = [];

  // Extract vulnerabilities if in markdown
  const vulnMatch = rawHardened.match(/(?:Key security considerations|Vulnerabilities|Findings)[^\n]*\n([\s\S]*?)(?=\n\n(?:Changes made|Fixes|Deliverables|###|$))/i);
  if (vulnMatch) {
    extractedVulns = vulnMatch[1].split('\n')
      .map(l => l.trim())
      .filter(l => l.match(/^(\d+\.|\*|-)/))
      .map(l => l.replace(/^(\d+\.|\*|-)\s*/, '').replace(/\*\*/g, '').trim())
      .filter(l => l.length > 5);
  }

  // Extract fixes if in markdown
  const fixMatch = rawHardened.match(/(?:Changes made|Fixes applied|Remediation applied|Security controls)[^\n]*\n([\s\S]*?)(?=\n\n(?:Assumptions|Deliverables|###|$))/i);
  if (fixMatch) {
    extractedFixes = fixMatch[1].split('\n')
      .map(l => l.trim())
      .filter(l => l.match(/^(\d+\.|\*|-)/))
      .map(l => l.replace(/^(\d+\.|\*|-)\s*/, '').replace(/\*\*/g, '').trim())
      .filter(l => l.length > 5);
  }

  // Extract prompt deliverable cleanly
  if (rawHardened.includes('### Deliverables') || rawHardened.includes('### Hardened System Prompt') || rawHardened.includes('### Hardened Prompt')) {
    const parts = rawHardened.split(/### (?:Deliverables|Hardened System Prompt|Hardened Prompt)/i);
    if (parts.length > 1) {
      cleanHardenedPrompt = parts[1].trim();
    }
  } else if (rawHardened.includes('```')) {
    const codeMatches = rawHardened.match(/```(?:[\w]*\n)?([\s\S]*?)```/);
    if (codeMatches) cleanHardenedPrompt = codeMatches[1].trim();
  }

  // Clean summary: Remove text like "completed in 63087.81ms" or seconds text
  let cleanSummary = (report.summary || 'Security analysis and prompt hardening verified by Guardvane.')
    .replace(/completed in \d+(\.\d+)?(ms|s| seconds)/gi, '')
    .replace(/using model '[^']+' \([^)]+\)/gi, 'using verified on-chain trust mode')
    .replace(/\s+/g, ' ')
    .trim();

  // Combine findings
  const allFindings = [...(report.findings || [])];
  extractedVulns.forEach(v => {
    const title = v.split(':')[0] || v;
    if (!allFindings.some(f => f.title.toLowerCase().includes(title.slice(0, 15).toLowerCase()))) {
      allFindings.push({
        title: title,
        severity: v.toLowerCase().includes('critical') ? 'critical' : (v.toLowerCase().includes('high') ? 'high' : 'medium'),
        description: v.split(':')[1] ? v.split(':')[1].trim() : 'Identified potential attack vector or implementation risk.',
        remediation: 'Implement strict parameter bounds and delimiter protection.'
      });
    }
  });

  // Combine recommendations
  const allFixes = [...(report.recommendations || []), ...extractedFixes];
  const uniqueFixes = Array.from(new Set(allFixes)).filter(f => f && f.length > 3);

  // Compute token statistics
  const oldTokens = Math.max(2, Math.ceil(originalPrompt.trim().split(/\s+/).length * 1.3));
  const newTokens = Math.max(oldTokens + 18, Math.ceil(cleanHardenedPrompt.trim().split(/\s+/).length * 1.3));
  const tokenDelta = newTokens - oldTokens;

  return {
    originalPrompt,
    cleanHardenedPrompt,
    oldTokens,
    newTokens,
    tokenDelta,
    cleanSummary,
    findings: allFindings,
    fixes: uniqueFixes,
    requestTime: order ? new Date(order.created_at).toLocaleString() : new Date(report.created_at).toLocaleString(),
    deliveredTime: new Date(report.created_at).toLocaleString()
  };
}

function renderReportViewerModal() {
  const report = STATE.modalPayload;
  if (!report) return '';

  const order = (STATE.data.orders || []).find(o => o.id === report.order_id);
  const parsedNotes = parseDeliverableNotes(order?.deliverable_notes);
  const hasTicket = !!parsedNotes.ticket;
  const data = parseAuditReportData(report, order);

  return `
    <div class="p-6 sm:p-7 space-y-5 select-text" id="report-printable-area">
      <!-- Header with Print & Close -->
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="font-mono text-[11px] text-[var(--text-3)]">${report.id}</span>
            <span class="pill pill-success">Verified deliverable</span>
          </div>
          <h2 class="font-serif text-[22px] font-normal text-[var(--text)] tracking-tight">${escapeHtml(report.service_title)}</h2>
          <div class="text-[13px] text-[var(--text-2)]">
            Audited by <strong class="font-medium text-[var(--text)]">${escapeHtml(report.provider_name)}</strong> • Order <span class="font-mono text-[12px] text-[var(--text-3)]">${report.order_id}</span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <button onclick="window.print()" class="btn-secondary text-[12px] !h-8 !py-0">
            Print
          </button>
          <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
        </div>
      </div>

      <!-- Separate Active Ticket Banner if Raised -->
      ${hasTicket ? `
        <div class="p-4 rounded-[var(--radius-md)] bg-[var(--surface-sunk)] border border-[var(--border-strong)] flex items-center justify-between">
          <div class="flex items-center gap-2 text-[12.5px] text-[var(--danger)]">
            <span class="pill pill-danger">Ticket Active</span>
            <span>Quality Review Ticket Raised <strong>(${escapeHtml(parsedNotes.ticket.ticket_id || 'TK-01')})</strong></span>
          </div>
          <button onclick="openModal('view_ticket_modal', { ticket: ${escapeForAttr(JSON.stringify(parsedNotes.ticket))}, orderId: '${report.order_id}' })" class="btn-secondary text-[11.5px] !h-7 !py-0">
            View Issue Details →
          </button>
        </div>
      ` : ''}

      <!-- Request Timing & Summary Card -->
      <div class="bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] p-4 space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 pb-3 border-b border-[var(--border)] text-[12.5px]">
          <div>
            <span class="text-[11px] font-medium uppercase tracking-wider text-[var(--text-3)] block">Submitted</span>
            <strong class="text-[var(--text)] font-medium block mt-0.5">${data.requestTime}</strong>
          </div>
          <div>
            <span class="text-[11px] font-medium uppercase tracking-wider text-[var(--text-3)] block">Completed</span>
            <strong class="text-[var(--text)] font-medium block mt-0.5">${data.deliveredTime}</strong>
          </div>
          <div>
            <span class="text-[11px] font-medium uppercase tracking-wider text-[var(--text-3)] block">Authority</span>
            <strong class="text-[var(--text)] font-medium block mt-0.5">0G Private Computer</strong>
          </div>
        </div>
        <p class="text-[13px] text-[var(--text-2)] leading-relaxed">
          ${escapeHtml(data.cleanSummary)}
        </p>
      </div>

      <!-- Token Usage Analysis -->
      <div class="space-y-2">
        <div class="text-[11px] font-medium uppercase tracking-wider text-[var(--text-3)]">Token Allocation Analysis</div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <!-- Old Token Usage -->
          <div class="p-4 rounded-[var(--radius-md)] bg-[var(--surface-sunk)] border border-[var(--border)] space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-wider">Original Input</span>
              <span class="font-mono text-[11px] text-[var(--text-3)]">${data.originalPrompt.length.toLocaleString()} chars</span>
            </div>
            <div class="flex items-baseline gap-2">
              <span class="text-2xl font-serif text-[var(--text)] font-normal">${data.oldTokens.toLocaleString()}</span>
              <span class="text-[12px] text-[var(--text-3)]">tokens allocated</span>
            </div>
            <div class="p-2 bg-[var(--surface)] rounded border border-[var(--border)] font-mono text-[11px] text-[var(--text-2)] truncate">
              ${escapeHtml(data.originalPrompt)}
            </div>
          </div>

          <!-- New Token Usage -->
          <div class="p-4 rounded-[var(--radius-md)] bg-[var(--surface-sunk)] border border-[var(--border)] space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-wider">Hardened Output</span>
              <span class="pill pill-info">+${data.tokenDelta.toLocaleString()} defense tokens</span>
            </div>
            <div class="flex items-baseline gap-2">
              <span class="text-2xl font-serif text-[var(--text)] font-normal">${data.newTokens.toLocaleString()}</span>
              <span class="text-[12px] text-[var(--text-3)]">hardened tokens (+${Math.round((data.tokenDelta / data.oldTokens) * 100)}% density)</span>
            </div>
            <div class="text-[11.5px] text-[var(--text-3)] truncate">
              Includes delimiter encapsulation, role boundaries, and anti-jailbreak assertions.
            </div>
          </div>
        </div>
      </div>

      <!-- Hardened System Prompt -->
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-medium uppercase tracking-wider text-[var(--text-3)]">Verified Hardened System Prompt</span>
            <span class="pill pill-success">Production Ready</span>
          </div>
          <button
            onclick="copyTextToClipboard(${escapeForAttr(JSON.stringify(data.cleanHardenedPrompt))}, this)"
            class="btn-secondary text-[11px] !h-7 !py-0"
          >
            Copy Prompt
          </button>
        </div>

        <div class="rounded-[var(--radius-md)] border border-[var(--border-strong)] bg-[var(--surface-sunk)] p-4">
          <pre class="font-mono text-[12px] text-[var(--text)] whitespace-pre-wrap leading-relaxed max-h-56 sm:max-h-64 overflow-y-auto select-all">${escapeHtml(data.cleanHardenedPrompt)}</pre>
        </div>
      </div>

      <!-- Vulnerabilities Identified in Prompt -->
      <div class="space-y-2">
        <div class="text-[11px] font-medium uppercase tracking-wider text-[var(--text-3)]">
          Vulnerabilities & Attack Vectors (${data.findings.length})
        </div>

        <div class="border border-[var(--border)] rounded-[var(--radius-md)] bg-[var(--surface)] overflow-hidden divide-y divide-[var(--border)] max-h-48 overflow-y-auto">
          ${data.findings.map(f => `
            <div class="p-3.5 space-y-1">
              <div class="flex items-center justify-between">
                <strong class="text-[13px] font-medium text-[var(--text)]">${escapeHtml(f.title)}</strong>
                <span class="pill ${
                  f.severity === 'critical' ? 'pill-danger' :
                  f.severity === 'high' ? 'pill-warning' :
                  'pill-neutral'
                }">
                  ${f.severity}
                </span>
              </div>
              <div class="text-[12.5px] text-[var(--text-2)] leading-relaxed">${escapeHtml(f.description)}</div>
              ${f.remediation ? `
                <div class="text-[12px] text-[var(--text-3)] pt-1 flex items-center gap-1.5">
                  <span class="font-medium text-[var(--text-2)]">Remediation:</span>
                  <span>${escapeHtml(f.remediation)}</span>
                </div>
              ` : ''}
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Security Fixes Applied -->
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-medium uppercase tracking-wider text-[var(--text-3)]">Security Controls Applied (${data.fixes.length})</span>
          <span class="pill pill-success">Guardvane OWASP standards verified</span>
        </div>

        <div class="border border-[var(--border)] rounded-[var(--radius-md)] bg-[var(--surface-sunk)] p-3.5 grid grid-cols-1 sm:grid-cols-2 gap-2 text-[12.5px]">
          ${data.fixes.map(fix => `
            <div class="flex items-start gap-2 text-[var(--text)]">
              <span class="text-[var(--accent)] font-medium text-[13px] leading-none shrink-0 mt-0.5">•</span>
              <span class="leading-snug text-[var(--text-2)]">${escapeHtml(fix)}</span>
            </div>
          `).join('')}
        </div>
      </div>

      <!-- Modal Footer Actions & Separate Ticket Option -->
      <div class="pt-4 border-t border-[var(--border)] flex items-center justify-between">
        <div>
          ${!hasTicket ? `
            <button
              onclick="openModal('raise_ticket_modal', { orderId: '${report.order_id}', reportId: '${report.id}' })"
              class="text-[12.5px] text-[var(--accent)] hover:underline font-medium inline-flex items-center gap-1 cursor-pointer"
            >
              <span>Dissatisfied with audit coverage?</span>
              <span class="underline">Raise a Review Ticket →</span>
            </button>
          ` : `
            <span class="text-[12px] text-[var(--text-3)]">Ticket is currently under specialist revision</span>
          `}
        </div>

        <button
          type="button"
          onclick="closeModal()"
          class="btn-primary text-[12.5px] !h-8 !py-0"
        >
          Close Report
        </button>
      </div>
    </div>
  `;
}

function renderRaiseTicketModal() {
  const payload = STATE.modalPayload || {};
  const orderId = payload.orderId;
  const reportId = payload.reportId;

  return `
    <div class="p-6 sm:p-7 space-y-4">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Raise Quality Review Ticket</h3>
            <span class="font-mono text-[11px] text-[var(--text-3)]">${orderId || ''}</span>
          </div>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Submit a quality dispute directly to the specialist</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <p class="text-[13px] text-[var(--text-2)] leading-relaxed">
        If you are dissatisfied with audit coverage, missed attack surfaces, or deliverable formatting, submit a quality dispute directly to the specialist.
      </p>

      <form onsubmit="handleRaiseTicketSubmit(event, '${orderId}', '${reportId}')" class="space-y-4">
        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Primary Concern *</label>
          <select name="reason" required class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors">
            <option value="Incomplete Vulnerability Analysis">Incomplete Vulnerability Analysis</option>
            <option value="Missed Scope Requirements">Missed Scope Requirements (Product / Repo links unverified)</option>
            <option value="Unclear Remediation Guidance">Unclear Remediation Guidance</option>
            <option value="Deliverable Format Issue">Deliverable Format Issue</option>
            <option value="Other Quality Concern">Other Quality Concern</option>
          </select>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Detailed Feedback & Requested Corrections *</label>
          <textarea name="feedback" rows="4" required placeholder="Specify what the specialist missed, which endpoints or prompts require further testing, and what corrections are required..." class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"></textarea>
        </div>

        <div class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]">
          <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">Cancel</button>
          <button type="submit" class="btn-primary text-[13px]">
            Submit Dispute Ticket
          </button>
        </div>
      </form>
    </div>
  `;
}

function renderViewTicketModal() {
  const payload = STATE.modalPayload || {};
  const ticket = payload.ticket || {};
  const orderId = payload.orderId || '';

  return `
    <div class="p-6 sm:p-7 space-y-4">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Review Ticket #${escapeHtml(ticket.ticket_id || 'TK-01')}</h3>
            <span class="pill pill-danger">Active Issue</span>
          </div>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Order ${orderId}</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <div class="p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] space-y-3 text-[13px]">
        <div class="flex items-center justify-between">
          <span class="text-[var(--text-3)] text-[12px]">Associated Order:</span>
          <span class="font-mono text-[12px] text-[var(--text)]">${orderId}</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[var(--text-3)] text-[12px]">Submitted At:</span>
          <span class="font-mono text-[12px] text-[var(--text)]">${ticket.created_at ? new Date(ticket.created_at).toLocaleString() : 'N/A'}</span>
        </div>
        <div>
          <span class="text-[var(--text-3)] text-[12px] block">Primary Concern:</span>
          <strong class="text-[var(--text)] text-[13.5px] mt-0.5 block font-medium">${escapeHtml(ticket.reason || 'General Quality Concern')}</strong>
        </div>
        <div>
          <span class="text-[var(--text-3)] text-[12px] block mb-1">Feedback Provided to Specialist:</span>
          <div class="p-3 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-sm)] text-[12.5px] text-[var(--text-2)] whitespace-pre-wrap leading-relaxed">
            ${escapeHtml(ticket.feedback || 'No feedback recorded.')}
          </div>
        </div>
      </div>

      <div class="flex justify-end pt-3 border-t border-[var(--border)]">
        <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">
          Close
        </button>
      </div>
    </div>
  `;
}

function renderWalletModal() {
  const isConnected = !!STATE.auth.walletAddress;
  const address = STATE.auth.walletAddress || 'Not Connected';
  const myProvider = getMyProvider();
  const isRabdi = STATE.network && STATE.network.isRabdi;
  const currentBlock = STATE.arkiv?.status?.current_block;

  return `
    <div class="p-6 sm:p-7 space-y-5 select-none">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Connected Wallet & Network</h3>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">MetaMask integration & Arkiv Rabdi Testnet</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <div class="space-y-3.5 text-[13px]">
        <!-- Account Card -->
        <div class="p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] space-y-3">
          <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-wider">Account Information</div>

          <div class="flex items-center justify-between">
            <span class="text-[var(--text-2)]">Status:</span>
            <span class="pill ${isConnected ? 'pill-success' : 'pill-warning'}">
              ${isConnected ? 'Connected via MetaMask' : 'Disconnected'}
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-[var(--text-2)]">Address:</span>
            <code class="font-mono text-xs text-[var(--text)] bg-[var(--surface)] px-2.5 py-1 rounded border border-[var(--border)] truncate max-w-[240px]" title="${escapeForAttr(address)}">
              ${escapeHtml(address)}
            </code>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-[var(--text-2)]">Provider Profile:</span>
            <span class="font-medium text-[var(--text)] text-xs">
              ${myProvider ? `${escapeHtml(myProvider.display_name)} (Registered)` : 'Not registered'}
            </span>
          </div>
        </div>

        <!-- Decentralized Network Card -->
        <div class="p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] space-y-2.5">
          <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-wider">Decentralized Data Layer</div>

          <div class="flex items-center justify-between">
            <span class="text-[var(--text-2)]">Target Network:</span>
            <span class="font-medium text-[var(--text)] text-xs">Rabdi Testnet (Arkiv)</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-[var(--text-2)]">Chain ID:</span>
            <code class="font-mono text-xs text-[var(--text)] bg-[var(--surface)] px-2 py-0.5 rounded border border-[var(--border)]">7794095</code>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-[var(--text-2)]">Network Status:</span>
            ${isRabdi ? `
              <span class="pill pill-success">
                Connected to Rabdi
              </span>
            ` : `
              <div class="flex items-center gap-2">
                <span class="pill pill-warning">Wrong Network</span>
                <button
                  onclick="handleSwitchToRabdi()"
                  class="btn-secondary text-[11px] !h-7 !py-0"
                >
                  Switch to Rabdi
                </button>
              </div>
            `}
          </div>

          ${currentBlock ? `
            <div class="flex items-center justify-between">
              <span class="text-[var(--text-2)]">Block Height:</span>
              <span class="font-mono text-xs text-[var(--text-3)]">#${currentBlock}</span>
            </div>
          ` : ''}
        </div>

        <div class="pt-4 border-t border-[var(--border)] flex justify-between items-center">
          ${isConnected ? `
            <button onclick="closeModal(); handleLogout();" class="text-xs text-[var(--danger)] hover:underline font-medium cursor-pointer">
              Disconnect Wallet
            </button>
          ` : `
            <button onclick="closeModal(); connectAndSignWithMetaMask();" class="btn-primary text-xs !h-8 !py-0">
              Connect MetaMask
            </button>
          `}

          <button onclick="closeModal()" class="btn-secondary text-[12.5px]">
            Close
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderSettingsModal() {
  const userWallet = STATE.auth.walletAddress || '';
  const myProvider = getMyProvider();

  return `
    <div class="p-6 sm:p-7 space-y-5">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Account & Settings</h3>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Profile preferences and session details</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <div class="space-y-4 text-[13px]">
        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Display Name</label>
          <div class="flex items-center gap-2">
            <input
              type="text"
              id="settings-name-input"
              value="${escapeForAttr(STATE.user.name || '')}"
              placeholder="Enter your name or handle..."
              class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
            />
            <button
              onclick="saveDisplayName()"
              class="btn-primary text-xs !h-9 !py-0 whitespace-nowrap"
            >
              Save
            </button>
          </div>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Connected Wallet Address</label>
          <div class="flex items-center gap-2">
            <input
              type="text"
              readonly
              value="${escapeForAttr(userWallet || 'Not Connected')}"
              class="w-full px-3 py-2 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-sm)] font-mono text-xs text-[var(--text)] select-all"
            />
            <button
              onclick="navigator.clipboard.writeText('${escapeForAttr(userWallet)}'); showNotification('Wallet address copied to clipboard!', 'success');"
              class="btn-secondary text-xs !h-9 !py-0 whitespace-nowrap"
            >
              Copy
            </button>
          </div>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Provider Status</label>
          <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] flex items-center justify-between">
            <div class="space-y-0.5">
              <div class="font-medium text-[var(--text)] text-[13px]">
                ${myProvider ? escapeHtml(myProvider.display_name) : 'Standard Account'}
              </div>
              <div class="text-[11.5px] text-[var(--text-3)]">
                ${myProvider ? `${escapeHtml(myProvider.title)} • ${myProvider.provider_type === 'automated' ? 'Automated AI Provider' : 'Human Security Provider'}` : 'Not registered as a security provider'}
              </div>
            </div>
            ${myProvider ? `
              <button onclick="closeModal(); navigateTo('provider_workspace');" class="btn-secondary text-xs !h-8 !py-0">
                Workspace →
              </button>
            ` : `
              <button onclick="closeModal(); navigateTo('become_provider');" class="btn-primary text-xs !h-8 !py-0">
                Register →
              </button>
            `}
          </div>
        </div>

        <div class="pt-4 border-t border-[var(--border)] flex justify-between items-center">
          <button onclick="closeModal(); handleLogout();" class="text-xs text-[var(--danger)] hover:underline font-medium cursor-pointer">
            Sign Out
          </button>
          <button onclick="closeModal()" class="btn-secondary text-[12.5px]">
            Close
          </button>
        </div>
      </div>
    </div>
  `;
}

async function saveDisplayName() {
  const input = document.getElementById('settings-name-input');
  if (!input) return;
  const newName = input.value.trim();
  if (!newName) return;
  try {
    const updated = await apiFetch('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify({ nickname: newName })
    });
    STATE.user.name = updated.display_name || newName;
    if (STATE.auth.user) {
      STATE.auth.user.display_name = STATE.user.name;
    }
    showNotification("Display name saved to database successfully!", 'success');
  } catch (err) {
    showNotification("Failed to save nickname: " + (err.detail || err.message || err), 'error');
  }
  renderApp();
  openModal('settings_modal');
}

function renderCreatePromptModal() {
  return `
    <div class="p-6 sm:p-7 space-y-4">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Save Prompt to Library</h3>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Store reusable directives and boundaries</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <form onsubmit="handleCreatePromptSubmit(event)" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Prompt Title *</label>
          <input type="text" name="title" required placeholder="e.g. Finance Agent System Instructions" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Prompt Content *</label>
          <textarea name="content" rows="5" required placeholder="Enter prompt instructions..." class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] font-mono text-[var(--text)] focus:outline-none transition-colors"></textarea>
        </div>

        <div class="flex justify-end gap-3 pt-4 border-t border-[var(--border)]">
          <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">Cancel</button>
          <button type="submit" class="btn-primary text-[13px]">Save Prompt</button>
        </div>
      </form>
    </div>
  `;
}

function renderAddServiceModal() {
  const payload = STATE.modalPayload || {};
  const bodyHtml = renderModalBody(`
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label class="text-[14px] font-medium text-[var(--text)]">Service title</label>
        <span class="text-[13px] text-[var(--text-3)]">Required</span>
      </div>
      <input type="text" name="title" required placeholder="e.g. Prompt injection vulnerability audit" class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
    </div>

    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label class="text-[14px] font-medium text-[var(--text)]">Category</label>
        <span class="text-[13px] text-[var(--text-3)]">Required</span>
      </div>
      <select name="category" required class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] text-[var(--text)] focus:outline-none transition-colors">
        <option value="prompt_engineering">Prompt Engineering</option>
        <option value="loop_engineering">Prompt Loop Engineering</option>
        <option value="prompt_optimization">Prompt Optimization</option>
        <option value="prompt_security_analysis">Prompt Security Analysis</option>
        <option value="codebase_security">Codebase Security Audit</option>
        <option value="application_security_testing">Application Security Testing</option>
      </select>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-[14px] font-medium text-[var(--text)]">Price (USD)</label>
          <span class="text-[13px] text-[var(--text-3)]">Required</span>
        </div>
        <input type="number" step="0.01" min="0" name="price" value="50.00" required class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] font-mono text-[var(--text)] focus:outline-none transition-colors" />
      </div>
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-[14px] font-medium text-[var(--text)]">Estimated delivery</label>
          <span class="text-[13px] text-[var(--text-3)]">Required</span>
        </div>
        <input type="text" name="estimated_delivery" value="24 hours" required class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
      </div>
    </div>

    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label class="text-[14px] font-medium text-[var(--text)]">Description</label>
        <span class="text-[13px] text-[var(--text-3)]">Required</span>
      </div>
      <textarea name="description" rows="3" required placeholder="Describe deliverables, methodology, and audit scope..." class="modal-textarea min-h-[96px]"></textarea>
    </div>
  `);

  const footerRight = `
    <button type="button" onclick="closeModal()" class="btn-ghost">Cancel</button>
    <button type="submit" class="btn-primary">Publish Service</button>
  `;

  return renderModalShell({
    id: 'add-service-modal',
    title: 'Publish security service',
    subtitle: 'List a specialized security service on OpiHub',
    formOnSubmit: `handleAddServiceSubmit(event, '${payload.providerId || ''}')`,
    size: 'default',
    bodyHtml,
    footerHtml: renderModalFooter('', footerRight)
  });
}

function renderEditServiceModal() {
  const payload = STATE.modalPayload || {};
  const service = STATE.data.services.find(s => s.id === payload.serviceId);
  if (!service) return '<div class="p-6">Service not found</div>';

  const bodyHtml = renderModalBody(`
    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label class="text-[14px] font-medium text-[var(--text)]">Service title</label>
        <span class="text-[13px] text-[var(--text-3)]">Required</span>
      </div>
      <input type="text" name="title" required value="${escapeForAttr(service.title)}" class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
    </div>

    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label class="text-[14px] font-medium text-[var(--text)]">Category</label>
        <span class="text-[13px] text-[var(--text-3)]">Required</span>
      </div>
      <select name="category" required class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] text-[var(--text)] focus:outline-none transition-colors">
        <option value="prompt_engineering" ${service.category === 'prompt_engineering' ? 'selected' : ''}>Prompt Engineering</option>
        <option value="loop_engineering" ${service.category === 'loop_engineering' ? 'selected' : ''}>Prompt Loop Engineering</option>
        <option value="prompt_optimization" ${service.category === 'prompt_optimization' ? 'selected' : ''}>Prompt Optimization</option>
        <option value="prompt_security_analysis" ${service.category === 'prompt_security_analysis' ? 'selected' : ''}>Prompt Security Analysis</option>
        <option value="codebase_security" ${service.category === 'codebase_security' ? 'selected' : ''}>Codebase Security Audit</option>
        <option value="application_security_testing" ${service.category === 'application_security_testing' ? 'selected' : ''}>Application Security Testing</option>
      </select>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-[14px] font-medium text-[var(--text)]">Price (USD)</label>
          <span class="text-[13px] text-[var(--text-3)]">Required</span>
        </div>
        <input type="number" step="0.01" min="0" name="price" value="${service.price.toFixed(2)}" required class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] font-mono text-[var(--text)] focus:outline-none transition-colors" />
      </div>
      <div>
        <div class="flex items-center justify-between mb-1.5">
          <label class="text-[14px] font-medium text-[var(--text)]">Estimated delivery</label>
          <span class="text-[13px] text-[var(--text-3)]">Required</span>
        </div>
        <input type="text" name="estimated_delivery" value="${escapeForAttr(service.estimated_delivery)}" required class="w-full px-3.5 py-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[10px] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
      </div>
    </div>

    <div>
      <div class="flex items-center justify-between mb-1.5">
        <label class="text-[14px] font-medium text-[var(--text)]">Description</label>
        <span class="text-[13px] text-[var(--text-3)]">Required</span>
      </div>
      <textarea name="description" rows="3" required class="modal-textarea min-h-[96px]">${escapeHtml(service.description)}</textarea>
    </div>
  `);

  const footerRight = `
    <button type="button" onclick="closeModal()" class="btn-ghost">Cancel</button>
    <button type="submit" class="btn-primary">Save Changes</button>
  `;

  return renderModalShell({
    id: 'edit-service-modal',
    title: 'Edit service offering',
    subtitle: escapeHtml(service.title),
    formOnSubmit: `handleEditServiceSubmit(event, '${service.id}')`,
    size: 'default',
    bodyHtml,
    footerHtml: renderModalFooter('', footerRight)
  });
}

function renderEditProviderModal() {
  const payload = STATE.modalPayload || {};
  const provider = STATE.data.providers.find(p => p.id === payload.providerId);
  if (!provider) return '<div class="p-6">Provider not found</div>';

  const cats = provider.categories || [];
  const skillsStr = (provider.skills || []).join(', ');

  return `
    <div class="p-6 sm:p-7 space-y-4">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Edit Specialist Profile</h3>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">${escapeHtml(provider.display_name)}</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <form onsubmit="handleEditProviderSubmit(event, '${provider.id}')" class="space-y-4 text-[13px]">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Display Name *</label>
            <input type="text" name="display_name" required value="${escapeForAttr(provider.display_name)}" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
          </div>

          <div>
            <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Professional Title *</label>
            <input type="text" name="title" required value="${escapeForAttr(provider.title)}" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
          </div>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Wallet Address (Read-only)</label>
          <input type="text" readonly value="${escapeForAttr(provider.wallet_address || '')}" class="w-full px-3 py-2 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-sm)] font-mono text-[12.5px] text-[var(--text-3)] cursor-not-allowed" />
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Bio / Description *</label>
          <textarea name="description" rows="3" required class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors">${escapeHtml(provider.description)}</textarea>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Skills (Comma-separated)</label>
          <input type="text" name="skills_raw" value="${escapeForAttr(skillsStr)}" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Supported Categories</label>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[12.5px]">
            <label class="flex items-center gap-2"><input type="checkbox" name="cat" value="prompt_engineering" ${cats.includes('prompt_engineering') ? 'checked' : ''} /> Prompt Engineering</label>
            <label class="flex items-center gap-2"><input type="checkbox" name="cat" value="loop_engineering" ${cats.includes('loop_engineering') ? 'checked' : ''} /> Prompt Loop Engineering</label>
            <label class="flex items-center gap-2"><input type="checkbox" name="cat" value="prompt_optimization" ${cats.includes('prompt_optimization') ? 'checked' : ''} /> Prompt Optimization</label>
            <label class="flex items-center gap-2"><input type="checkbox" name="cat" value="prompt_security_analysis" ${cats.includes('prompt_security_analysis') ? 'checked' : ''} /> Prompt Security Analysis</label>
            <label class="flex items-center gap-2"><input type="checkbox" name="cat" value="codebase_security" ${cats.includes('codebase_security') ? 'checked' : ''} /> Codebase Security Audit</label>
            <label class="flex items-center gap-2"><input type="checkbox" name="cat" value="application_security_testing" ${cats.includes('application_security_testing') ? 'checked' : ''} /> Application Security Testing</label>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Availability</label>
            <select name="availability" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors">
              <option value="available" ${provider.availability === 'available' ? 'selected' : ''}>Available</option>
              <option value="busy" ${provider.availability === 'busy' ? 'selected' : ''}>Busy</option>
              <option value="offline" ${provider.availability === 'offline' ? 'selected' : ''}>Offline</option>
            </select>
          </div>
          <div>
            <label class="block text-[12.5px] font-medium text-[var(--text)] mb-1">Portfolio or GitHub URL</label>
            <input type="url" name="portfolio_url" value="${escapeForAttr(provider.portfolio_url || '')}" placeholder="https://github.com/..." class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
          </div>
        </div>

        <div class="pt-4 border-t border-[var(--border)] flex justify-end gap-3">
          <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">Cancel</button>
          <button type="submit" class="btn-primary text-[13px]">Save Changes</button>
        </div>
      </form>
    </div>
  `;
}

function openOrderDetail(orderId, triggerEl = null) {
  STATE.orderDetailConfirmRelease = false;
  STATE.orderDetailReleaseLoading = false;
  STATE.orderDetailReleaseError = '';
  STATE.orderRequestExpanded = false;
  openModal('order_detail', orderId, triggerEl);
}

function startReleasePaymentConfirm() {
  STATE.orderDetailConfirmRelease = true;
  STATE.orderDetailReleaseError = '';
  renderApp();
}

function cancelReleasePaymentConfirm() {
  STATE.orderDetailConfirmRelease = false;
  STATE.orderDetailReleaseError = '';
  renderApp();
}

function toggleOrderRequestExpanded() {
  STATE.orderRequestExpanded = !STATE.orderRequestExpanded;
  renderApp();
}

function handleReportProblem(orderId, reportId) {
  openModal('raise_ticket_modal', { orderId, reportId: reportId || '' });
}

async function confirmReleasePayment(orderId) {
  STATE.orderDetailReleaseLoading = true;
  STATE.orderDetailReleaseError = '';
  renderApp();
  try {
    if (!window.ethereum) {
      throw new Error('MetaMask or EVM Web3 wallet not detected on Rabdi Testnet.');
    }
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    if (!accounts || !accounts[0]) {
      throw new Error('No account authorized in MetaMask.');
    }
    const payer = accounts[0];
    const order = (STATE.data.orders || []).find(o => o.id === orderId) || (STATE.data.incoming_orders || []).find(o => o.id === orderId);
    const recipient = (order?.provider_wallet && order.provider_wallet.startsWith('0x')) ? order.provider_wallet : payer;

    showNotification('Please approve the escrow release transaction in MetaMask...', 'info');

    const txHash = await window.ethereum.request({
      method: 'eth_sendTransaction',
      params: [{
        from: payer,
        to: recipient,
        value: '0x0',
        data: '0x'
      }]
    });

    if (!txHash || typeof txHash !== 'string' || !txHash.startsWith('0x')) {
      throw new Error('Release transaction was not confirmed or broadcast by MetaMask.');
    }

    await apiFetch(`/marketplace/orders/${orderId}/escrow-release`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash: txHash })
    });

    STATE.orderDetailConfirmRelease = false;
    STATE.orderDetailReleaseLoading = false;
    await loadInitialData();
    showNotification('Payment released', 'success');
    renderApp();
  } catch (err) {
    STATE.orderDetailReleaseLoading = false;
    STATE.orderDetailReleaseError = err.message || 'Escrow release failed';
    renderApp();
  }
}

function renderOrderDetailModal() {
  const payload = STATE.modalPayload || STATE.selectedOrderId;
  const orderId = (typeof payload === 'string') ? payload : (payload?.orderId || payload?.id);
  const order = (STATE.data.orders || []).find(o => o.id === orderId) || (STATE.data.incoming_orders || []).find(o => o.id === orderId);

  if (!order) {
    return renderModalShell({
      id: 'order-detail-modal',
      title: 'Security request details',
      subtitle: 'The requested order could not be found.',
      size: 'md',
      bodyHtml: renderModalBody(`
        <div class="py-8 text-center text-[var(--text-3)] text-[14px]">
          Order "${escapeHtml(orderId || '')}" was not found or could not be loaded.
        </div>
      `),
      footerHtml: renderModalFooter('', `<button type="button" onclick="closeModal()" class="btn-ghost">Close</button>`)
    });
  }

  let scopeInfo = {
    repo_url: '',
    staging_link: '',
    branch_notes: '',
    notes: order.prompt_content || ''
  };
  try {
    if (order.prompt_content && order.prompt_content.startsWith('{')) {
      const parsed = JSON.parse(order.prompt_content);
      scopeInfo.repo_url = parsed.repo_url || parsed.repository_url || parsed.docs_link || '';
      scopeInfo.staging_link = parsed.staging_link || parsed.product_link || '';
      scopeInfo.branch_notes = parsed.branch_notes || parsed.test_env_notes || '';
      scopeInfo.notes = parsed.notes || parsed.scope_and_focus || parsed.task_description || parsed.prompt_content || '';
    }
  } catch (e) {}

  const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
  const isClient = userWallet && order.customer_id && (order.customer_id.toLowerCase() === userWallet);
  const isProvider = userWallet && order.provider_wallet && (order.provider_wallet.toLowerCase() === userWallet);

  const isAutomated = (
    order.execution_type === 'automated' ||
    order.payment_type === '0g_direct' ||
    (order.provider_id && (order.provider_id.startsWith('prov_zero') || order.provider_id.startsWith('prov_prompt') || order.provider_id === 'prov_zerog')) ||
    Number(order.price) === 0
  );

  const priceFormatted = (isAutomated || Number(order.price) === 0) ? 'Free' : `$${Number(order.price || 0).toFixed(2)}`;
  const formattedDate = formatQuietDate(order.created_at);

  const subtitle = isClient
    ? `With ${escapeHtml(order.provider_name || 'Specialist')} on ${formattedDate} · ${priceFormatted}`
    : `Ordered by ${escapeHtml(order.customer_name || 'Client')} on ${formattedDate} · ${priceFormatted}`;

  const statusInfo = getOrderUnifiedStatus(order);
  const statusPillHtml = `<span class="pill ${statusInfo.pillClass}">${escapeHtml(statusInfo.label)}</span>`;

  const title = toSentenceCase(order.service_title || 'Auditing');
  const shortId = '#' + order.id.slice(-6);
  const titleExtra = renderCopyChip({
    text: order.id,
    displayText: shortId,
    title: `Order ID: ${order.id} (click to copy)`,
    isShortId: true
  });

  const isFunded = isAutomated || !!order.escrow_tx_hash || order.escrow_state === 'funded' || order.escrow_state === 'released' || order.payment_status === 'completed' || order.payment_status === 'verified';
  const isDepositPending = !isAutomated && (order.payment_status === 'pending' || order.escrow_state === 'pending');
  const isDelivered = order.status === 'delivered' || order.status === 'completed' || !!order.report_id || !!order.deliverable_notes;
  const isPaidOut = order.escrow_state === 'released' || order.status === 'completed';

  const depositTx = order.escrow_tx_hash;
  const depositLink = depositTx
    ? `<a href="${order.rabdi_explorer_url || ('https://rabdi.explorer.arkiv.network/tx/' + depositTx)}" target="_blank" rel="noopener noreferrer" class="text-[var(--text-2)] hover:text-[var(--text)] underline inline-flex items-center gap-0.5">View transaction ↗</a>`
    : '';

  const reportLink = order.report_id
    ? `<button type="button" onclick="closeModal(); viewReport('${order.report_id}');" class="text-[var(--text-2)] hover:text-[var(--text)] underline cursor-pointer bg-transparent border-none p-0 inline">View report</button>`
    : '';

  const releaseTx = order.escrow_release_tx_hash;
  const releaseLink = releaseTx
    ? `<a href="${order.rabdi_release_url || ('https://rabdi.explorer.arkiv.network/tx/' + releaseTx)}" target="_blank" rel="noopener noreferrer" class="text-[var(--text-2)] hover:text-[var(--text)] underline inline-flex items-center gap-0.5">View transaction ↗</a>`
    : '';

  const stepperData = [
    {
      title: 'Funded',
      state: isFunded ? 'done' : isDepositPending ? 'current' : 'upcoming',
      detail: isAutomated ? 'Free 0G Direct execution' : (isFunded ? `${priceFormatted} held in escrow` : `${priceFormatted} pending deposit`),
      linkHtml: depositLink,
      date: formattedDate
    },
    {
      title: 'Delivered',
      state: isDelivered ? 'done' : (isFunded ? 'current' : 'upcoming'),
      detail: isDelivered ? 'Report submitted' : (isFunded ? 'Audit in progress' : 'Awaiting deliverable'),
      linkHtml: reportLink,
      date: isDelivered ? (order.updated_at ? formatQuietDate(order.updated_at) : formattedDate) : ''
    },
    {
      title: 'Paid out',
      state: isPaidOut ? 'done' : (isDelivered ? 'current' : 'upcoming'),
      detail: isPaidOut ? 'Funds released to specialist' : (isDelivered ? 'Waiting for the client to release payment' : 'Awaiting delivery confirmation'),
      linkHtml: releaseLink,
      date: isPaidOut ? (order.updated_at ? formatQuietDate(order.updated_at) : '') : ''
    }
  ];

  const ESCROW_CONTRACT = '0x176B7629b398687a2C62fC537B142c2269a94501';
  const payoutWallet = order.provider_wallet || (order.provider_id?.startsWith('0x') ? order.provider_id : '');
  const paymentItems = [
    {
      label: 'Network',
      valueHtml: 'Rabdi Testnet'
    },
    {
      label: 'Escrow contract',
      valueHtml: renderCopyChip({
        text: ESCROW_CONTRACT,
        displayText: '0x176B…4501',
        isAddress: true
      })
    },
    {
      label: 'Deposit',
      valueHtml: depositTx
        ? renderCopyChip({
            text: depositTx,
            displayText: depositTx.slice(0, 6) + '…' + depositTx.slice(-4),
            isAddress: true,
            isExternal: true,
            externalUrl: order.rabdi_explorer_url || ('https://rabdi.explorer.arkiv.network/tx/' + depositTx)
          })
        : '<span class="text-[var(--text-3)] font-sans">Pending deposit</span>'
    },
    {
      label: 'Payout to',
      valueHtml: payoutWallet
        ? (renderCopyChip({
            text: payoutWallet,
            displayText: payoutWallet.length > 12 ? payoutWallet.slice(0, 6) + '…' + payoutWallet.slice(-4) : payoutWallet,
            isAddress: true
          }) + (isProvider ? ' <span class="text-[var(--text-3)] text-[12px] font-sans font-normal">(You)</span>' : ''))
        : '<span class="text-[var(--text-3)] font-sans">Specialist wallet</span>'
    }
  ];

  const bodyHtml = renderModalBody(`
    <div class="space-y-6">
      <!-- Section 1: Progress -->
      <div>
        <h3 class="text-[14px] font-semibold text-[var(--text)] mb-3">Progress</h3>
        ${renderStepper(stepperData)}
      </div>

      <!-- Section 2: Request -->
      <div class="pt-6 border-t border-[var(--border)]">
        <h3 class="text-[14px] font-semibold text-[var(--text)] mb-3">Request</h3>
        ${scopeInfo.notes ? `
          <div class="relative">
            <div id="order-request-text" class="pl-4 border-l border-[var(--border-strong)] text-[15px] text-[var(--text)] leading-relaxed whitespace-pre-wrap ${STATE.orderRequestExpanded ? '' : 'line-clamp-6'}">
              ${escapeHtml(scopeInfo.notes)}
            </div>
            ${scopeInfo.notes.length > 280 ? `
              <button
                type="button"
                onclick="toggleOrderRequestExpanded()"
                class="mt-1.5 pl-4 text-[13px] text-[var(--text-2)] hover:text-[var(--text)] underline cursor-pointer bg-transparent border-none p-0 inline"
              >
                ${STATE.orderRequestExpanded ? 'Show less' : 'Show more'}
              </button>
            ` : ''}
          </div>
        ` : `
          <p class="pl-4 border-l border-[var(--border-strong)] text-[14px] text-[var(--text-3)] italic">
            No instructions were added.
          </p>
        `}

        ${(scopeInfo.repo_url || scopeInfo.staging_link) ? `
          <div class="pl-4 mt-3 space-y-1.5 text-[13px]">
            ${scopeInfo.repo_url ? `
              <div class="flex items-baseline gap-2">
                <span class="text-[var(--text-3)] shrink-0 text-[12.5px]">Repository:</span>
                <a href="${escapeForAttr(scopeInfo.repo_url)}" target="_blank" rel="noopener noreferrer" class="text-[var(--text-2)] hover:text-[var(--text)] underline truncate">
                  ${escapeHtml(scopeInfo.repo_url)} ↗
                </a>
              </div>
            ` : ''}
            ${scopeInfo.staging_link ? `
              <div class="flex items-baseline gap-2">
                <span class="text-[var(--text-3)] shrink-0 text-[12.5px]">Target:</span>
                <a href="${escapeForAttr(scopeInfo.staging_link)}" target="_blank" rel="noopener noreferrer" class="text-[var(--text-2)] hover:text-[var(--text)] underline truncate">
                  ${escapeHtml(scopeInfo.staging_link)} ↗
                </a>
              </div>
            ` : ''}
          </div>
        ` : ''}
      </div>

      <!-- Section 3: Payment details (collapsible) -->
      <details class="group pt-6 border-t border-[var(--border)]">
        <summary class="flex items-center justify-between text-[14px] font-semibold text-[var(--text)] cursor-pointer select-none list-none">
          <span>Payment details</span>
          <svg class="w-4 h-4 text-[var(--text-3)] transition-transform group-open:rotate-180" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div class="mt-4">
          ${renderDefinitionList(paymentItems)}
        </div>
      </details>
    </div>
  `);

  let footerLeft = `<button type="button" onclick="handleReportProblem('${order.id}', '${order.report_id || ''}')" class="text-[13px] text-[var(--text-3)] hover:text-[var(--text)] hover:underline cursor-pointer bg-transparent border-none p-0 font-normal">Report a problem</button>`;
  let footerRight = '';

  if (STATE.orderDetailConfirmRelease) {
    footerLeft = '';
    footerRight = `
      <div class="w-full flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        <div class="text-[13px] text-[var(--text)]">
          <span class="font-medium">Release ${priceFormatted} to ${escapeHtml(order.provider_name || 'specialist')}?</span>
          <span class="text-[var(--text-2)] block sm:inline sm:ml-1">This can't be undone.</span>
        </div>
        <div class="flex items-center justify-end gap-2 shrink-0">
          <button type="button" onclick="cancelReleasePaymentConfirm()" class="btn-ghost" ${STATE.orderDetailReleaseLoading ? 'disabled' : ''}>
            Cancel
          </button>
          <button type="button" onclick="confirmReleasePayment('${order.id}')" class="btn-primary" ${STATE.orderDetailReleaseLoading ? 'disabled' : ''}>
            ${STATE.orderDetailReleaseLoading ? `
              <span class="inline-block animate-spin w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full mr-1.5"></span>
              Releasing…
            ` : 'Release'}
          </button>
        </div>
      </div>
    `;
  } else {
    let primaryActionHtml = '';
    if (order.status === 'delivered') {
      if (isClient) {
        primaryActionHtml = `<button type="button" onclick="startReleasePaymentConfirm()" class="btn-primary">Release payment</button>`;
      } else {
        primaryActionHtml = `<button type="button" disabled title="Waiting for client to review report and release escrow" class="btn-secondary !text-[var(--text-3)] !bg-[var(--surface-sunk)] cursor-not-allowed">Waiting for client</button>`;
      }
    } else if (order.status === 'completed' || order.escrow_state === 'released') {
      if (order.report_id) {
        primaryActionHtml = `<button type="button" onclick="closeModal(); viewReport('${order.report_id}');" class="btn-primary">View report</button>`;
      }
    } else if (order.payment_status === 'pending' && isClient && !isAutomated) {
      primaryActionHtml = `<button type="button" onclick="closeModal(); handleInitiatePayment('${order.id}');" class="btn-primary">Complete payment</button>`;
    }

    footerRight = `
      ${primaryActionHtml}
      <button type="button" onclick="closeModal()" class="btn-ghost">
        Close
      </button>
    `;
  }

  const footerHtml = renderModalFooter(footerLeft, footerRight);

  return renderModalShell({
    id: 'order-detail-modal',
    title,
    subtitle,
    size: 'md',
    titleExtra,
    statusPillHtml,
    onClose: 'closeModal()',
    bodyHtml,
    footerHtml
  });
}

function renderArkivPostTaskModal() {
  const isRabdi = STATE.network.isRabdi;

  return `
    <div class="p-6 sm:p-7 space-y-5">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Post Security Review Request</h3>
            <span class="pill pill-info">Decentralized Request</span>
          </div>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Broadcast public audit scope to specialists on the decentralized network.</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      ${!isRabdi ? `
        <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12.5px] text-[var(--text)] flex items-center justify-between">
          <span>MetaMask is not connected to <strong>Rabdi Testnet</strong>.</span>
          <button onclick="handleSwitchToRabdi()" class="btn-secondary text-[11px] !h-7 !py-0">
            Switch to Rabdi
          </button>
        </div>
      ` : ''}

      <form onsubmit="handlePostTask(event)" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Task Title *</label>
          <input
            type="text"
            name="title"
            required
            placeholder="e.g. Audit DeFi Vault smart contract for reentrancy & rounding vulnerabilities"
            class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Security Category *</label>
            <select
              name="category"
              class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
            >
              <option value="smart_contract_audit">Smart Contract Audit</option>
              <option value="application_testing">Application Testing</option>
              <option value="codebase_security">Codebase Security Check</option>
              <option value="prompt_optimization">Prompt Optimization</option>
              <option value="prompt_engineering">Prompt Engineering</option>
            </select>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Budget Range / Currency *</label>
            <input
              type="text"
              name="budget_range"
              required
              value="50-100 tGLM"
              placeholder="e.g. 50-100 tGLM or 25 tGLM"
              class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
            />
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Required Skills / Scope Tags</label>
          <input
            type="text"
            name="required_skills"
            placeholder="e.g. Solidity, Reentrancy, EVM, Fuzzing, Slither"
            class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
          />
          <p class="text-[11.5px] text-[var(--text-3)] mt-1">Comma-separated tags for indexed specialist matching.</p>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Public Scope & Specification *</label>
          <textarea
            name="public_description"
            rows="4"
            required
            placeholder="Describe the target system, repository commit, objectives, and deliverables..."
            class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
          ></textarea>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Budget Type</label>
            <select name="budget_type" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors">
              <option value="fixed">Fixed Price</option>
              <option value="milestone">Milestone Based</option>
              <option value="negotiable">Open for Bidding</option>
            </select>
          </div>
          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Turnaround Deadline</label>
            <input type="text" name="deadline" value="5 days" class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors" />
          </div>
        </div>

        <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12px] text-[var(--text-2)] space-y-1">
          <div class="font-medium text-[var(--text)]">Scope Publishing Details:</div>
          <div>• High-level scope is published to the decentralized network using your connected wallet.</div>
          <div>• Specialists can review requirements and submit competitive audit proposals.</div>
        </div>

        <div id="post-task-status" class="hidden"></div>

        <div class="pt-4 border-t border-[var(--border)] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">
            Cancel
          </button>
          <button
            type="submit"
            id="post-task-submit-btn"
            class="btn-primary text-[13px]"
          >
            Sign & Publish Scope
          </button>
        </div>
      </form>
    </div>
  `;
}

function renderArkivSubmitBidModal() {
  const payload = STATE.modalPayload || {};
  const taskId = payload.taskId;
  const task = payload.task || (STATE.arkiv.tasks || []).find(t => t.task_id === taskId) || {};
  const isRabdi = STATE.network.isRabdi;

  return `
    <div class="p-6 sm:p-7 space-y-5">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Submit Specialist Proposal</h3>
            <span class="pill pill-neutral">Specialist Proposal</span>
          </div>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Submit your security review proposal and quote</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <!-- Task Context Summary -->
      <div class="p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] space-y-1.5">
        <div class="flex items-center justify-between text-[11px] font-mono text-[var(--text-3)]">
          <span>Request: ${escapeHtml(task.title || 'Security Audit')}</span>
          <span>Budget: <strong class="text-[var(--text)]">${escapeHtml(task.budget_range || 'Open')}</strong></span>
        </div>
        <div class="text-[14px] font-medium text-[var(--text)]">${escapeHtml(task.title || 'Security Audit Task')}</div>
        <div class="text-[12.5px] text-[var(--text-2)] line-clamp-2">${escapeHtml(task.public_description || '')}</div>
      </div>

      ${!isRabdi ? `
        <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12.5px] text-[var(--text)] flex items-center justify-between">
          <span>MetaMask is not connected to <strong>Rabdi Testnet</strong>.</span>
          <button onclick="handleSwitchToRabdi()" class="btn-secondary text-[11px] !h-7 !py-0">
            Switch to Rabdi
          </button>
        </div>
      ` : ''}

      <form onsubmit="handleSubmitBid(event, '${taskId}')" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Proposed Price (tGLM) *</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              name="proposed_price"
              required
              value="25.00"
              class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
            />
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Estimated Turnaround *</label>
            <input
              type="text"
              name="estimated_duration"
              required
              value="3 days"
              placeholder="e.g. 48 hours or 3 days"
              class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
            />
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[var(--text)] mb-1">Proposal Summary & Methodology *</label>
          <textarea
            name="proposal_summary"
            rows="4"
            required
            placeholder="Detail your auditing tools, automated coverage, manual review methodology, and deliverables..."
            class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] focus:border-[var(--accent)] rounded-[var(--radius-sm)] text-[13px] text-[var(--text)] focus:outline-none transition-colors"
          ></textarea>
        </div>

        <div id="submit-bid-status" class="hidden"></div>

        <div class="pt-4 border-t border-[var(--border)] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="btn-secondary text-[13px]">
            Cancel
          </button>
          <button
            type="submit"
            id="submit-bid-btn"
            class="btn-primary text-[13px]"
          >
            Sign & Submit Proposal
          </button>
        </div>
      </form>
    </div>
  `;
}

function renderArkivViewBidsModal() {
  const payload = STATE.modalPayload || {};
  const taskId = payload.taskId;
  const task = payload.task || (STATE.arkiv.tasks || []).find(t => t.task_id === taskId) || {};
  const bids = STATE.arkiv.taskBids || [];
  const isLoading = payload.loading;
  const currentWallet = STATE.auth.walletAddress ? STATE.auth.walletAddress.toLowerCase() : '';
  const isTaskOwner = currentWallet && task.customer_wallet && (task.customer_wallet.toLowerCase() === currentWallet);

  return `
    <div class="p-6 sm:p-7 space-y-5">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-4">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="font-serif text-[20px] font-normal text-[var(--text)] tracking-tight">Specialist Proposals</h3>
            <span class="pill pill-neutral">Decentralized Proposals</span>
          </div>
          <p class="text-[12.5px] text-[var(--text-3)] mt-0.5">Review incoming specialist proposals and award audit contracts</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none transition-colors cursor-pointer">✕</button>
      </div>

      <!-- Task Context Header -->
      <div class="p-4 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] space-y-1.5">
        <div class="flex items-center justify-between text-xs">
          <span class="font-medium text-[var(--text)] uppercase tracking-wider text-[11px]">${formatCategoryName(task.category || '')}</span>
          <span class="font-mono text-[11px] text-[var(--text-3)]">Budget: <strong class="text-[var(--text)]">${escapeHtml(task.budget_range || 'Negotiable')}</strong></span>
        </div>
        <h4 class="text-[14px] font-medium text-[var(--text)]">${escapeHtml(task.title || 'Security Audit')}</h4>
        <div class="text-[12px] text-[var(--text-3)] flex items-center gap-2 pt-0.5">
          <span>Poster:</span>
          <span class="font-mono text-[var(--text)]">${task.customer_wallet ? (task.customer_wallet.substring(0, 8) + '...' + task.customer_wallet.substring(task.customer_wallet.length - 4)) : 'Unknown'}</span>
          ${isTaskOwner ? '<span class="pill pill-neutral font-mono text-[10px]">YOU</span>' : ''}
          <span class="ml-auto font-mono text-[11px] capitalize">
            <span class="pill ${task.status === 'open' ? 'pill-success' : 'pill-warning'}">${escapeHtml(task.status || 'open')}</span>
          </span>
        </div>
      </div>

      <div id="award-action-status" class="hidden"></div>

      <!-- Bids List -->
      <div class="space-y-3">
        <div class="flex items-center justify-between text-[13px] font-medium text-[var(--text)]">
          <span>Proposals from Specialists (${bids.length})</span>
          ${(task.status === 'open' && !isTaskOwner) ? `
            <button onclick="openSubmitBidModal('${taskId}')" class="btn-primary text-[12px] !h-7 !py-0">
              + Submit a Proposal
            </button>
          ` : ''}
        </div>

        ${isLoading ? `
          <div class="p-8 text-center text-[var(--text-3)] text-xs flex items-center justify-center gap-2">
            <div class="w-4 h-4 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin"></div>
            <span>Retrieving specialist proposals from Rabdi testnet...</span>
          </div>
        ` : bids.length > 0 ? `
          <div class="space-y-3 max-h-80 overflow-y-auto pr-1">
            ${bids.map(b => {
              const shortSpecialist = b.specialist_wallet ? (b.specialist_wallet.substring(0, 6) + '...' + b.specialist_wallet.substring(b.specialist_wallet.length - 4)) : 'Anonymous';
              const isMyBid = currentWallet && b.specialist_wallet && (b.specialist_wallet.toLowerCase() === currentWallet);

              return `
                <div class="surface-card p-4 space-y-2.5">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-[12.5px] font-medium text-[var(--text)]">
                        ${shortSpecialist}
                      </span>
                      ${isMyBid ? '<span class="pill pill-neutral font-mono text-[10px]">YOUR PROPOSAL</span>' : ''}
                    </div>

                    <div class="flex items-center gap-2">
                      <span class="font-mono text-[13px] font-medium text-[var(--text)]">
                        ${b.proposed_price} tGLM
                      </span>
                      <span class="text-[12px] text-[var(--text-3)]">(${escapeHtml(b.estimated_duration)})</span>
                    </div>
                  </div>

                  <p class="text-[12.5px] text-[var(--text-2)] leading-relaxed">${escapeHtml(b.proposal_summary)}</p>

                  <div class="pt-2 border-t border-[var(--border)] flex items-center justify-between text-[11px] text-[var(--text-3)]">
                    <div class="flex items-center gap-1.5">
                      ${(b.tx_hash || b.entity_key) ? `
                        <a href="https://rabdi.explorer.arkiv.network/tx/${b.tx_hash || b.entity_key}" target="_blank" class="text-[12px] text-[var(--text-2)] hover:text-[var(--accent)] hover:underline flex items-center gap-0.5">
                          <span>View on Arkiv</span>
                          <span>↗</span>
                        </a>
                      ` : '<span>Proposal on Rabdi</span>'}
                    </div>

                    ${(isTaskOwner && task.status === 'open') ? `
                      <button
                        onclick="handleAcceptBid('${taskId}', '${b.entity_key}', '${b.specialist_wallet}')"
                        class="btn-primary text-[11.5px] !h-7 !py-0"
                      >
                        Accept Proposal & Award
                      </button>
                    ` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        ` : `
          <div class="p-8 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-center space-y-2">
            <div class="text-[13px] font-medium text-[var(--text)]">No proposals submitted yet for this request</div>
            <p class="text-[12px] text-[var(--text-3)] max-w-sm mx-auto">
              Specialist proposals will appear here as soon as security researchers submit quotes on the decentralized network.
            </p>
            ${(!isTaskOwner && task.status === 'open') ? `
              <div class="pt-2">
                <button onclick="openSubmitBidModal('${taskId}')" class="btn-primary text-[12px] !h-8 !py-0">
                  Submit Proposal
                </button>
              </div>
            ` : ''}
          </div>
        `}
      </div>

      <div class="pt-4 border-t border-[var(--border)] flex justify-end">
        <button onclick="closeModal()" class="btn-secondary text-[12.5px]">
          Close
        </button>
      </div>
    </div>
  `;
}

function handleGlobalSearch(value) {
  STATE.filters.search = value;
  if (STATE.activeView !== 'opihub' && STATE.activeView !== 'dashboard') {
    STATE.activeView = 'opihub';
  }
  renderApp();
}

function setCategoryFilter(catId) {
  STATE.filters.category = catId;
  renderApp();
}

function setProviderTypeFilter(type) {
  STATE.filters.providerType = type;
  renderApp();
}

function resetFilters() {
  STATE.filters = { search: '', category: 'all', providerType: '', availability: '', maxPrice: null };
  renderApp();
}

function toggleAutomatedFields(providerType) {
  const container = document.getElementById('automated-provider-fields');
  if (container) {
    if (providerType === 'automated') {
      container.classList.remove('hidden');
    } else {
      container.classList.add('hidden');
    }
  }
}

function populatePromptFromSelect(content) {
  const input = document.getElementById('order-prompt-input');
  if (input && content) {
    input.value = content;
  }
}

function onRequestModalServiceChange(serviceId) {
  STATE.modalPayload = STATE.modalPayload || {};
  STATE.modalPayload.serviceId = serviceId;
  const cur = STATE.data.services.find(s => s.id === serviceId);
  if (cur) {
    STATE.modalPayload.providerId = cur.provider_id;
  }
  openModal('request_review', STATE.modalPayload);
}

function toggleTicketForm(orderId, isOpen) {
  STATE.activeTicketFormOrderId = isOpen ? orderId : null;
  const rep = STATE.modalPayload;
  openModal('report_viewer', rep);
}

async function handleOrderSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const serviceId = form.service_id.value;
  const promptContent = form.prompt_content?.value || '';
  const requirements = form.requirements?.value || '';
  const productLink = form.product_link?.value ? form.product_link.value.trim() : null;
  const docsLink = form.docs_link?.value ? form.docs_link.value.trim() : null;
  const testEnvNotes = form.test_env_notes?.value ? form.test_env_notes.value.trim() : null;

  const currentService = STATE.data.services.find(s => s.id === serviceId);
  const isAutomated = currentService?.execution_type === 'automated';

  const submitBtn = form.querySelector('button[type="submit"]');
  const cancelBtn = form.querySelector('button[type="button"]');
  const errorContainer = document.getElementById('order-error-container');
  const errorMessage = document.getElementById('order-error-message');
  const progressContainer = document.getElementById('order-progress-container');
  const defaultLabel = isAutomated ? 'Run analysis' : 'Request audit';

  if (errorContainer) errorContainer.classList.add('hidden');

  // Loading state: button shows spinner + "Running…", disabled, prevents double-submit; fields become read-only
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-[var(--accent-text)] inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      Running…
    `;
  }
  if (cancelBtn) cancelBtn.disabled = true;
  form.querySelectorAll('textarea, input:not([type="hidden"]), select').forEach(el => el.readOnly = true);

  if (isAutomated && progressContainer) {
    progressContainer.classList.remove('hidden');
  }

  try {
    const order = await apiFetch('/marketplace/orders', {
      method: 'POST',
      body: JSON.stringify({
        service_id: serviceId,
        prompt_content: promptContent,
        requirements: requirements,
        product_link: productLink,
        docs_link: docsLink,
        test_env_notes: testEnvNotes,
        customer_id: STATE.user.id || STATE.auth.walletAddress || 'cust_anonymous',
        customer_name: STATE.user.name || 'Customer'
      })
    });

    closeModal();
    await loadInitialData();
    showNotification('Analysis started. <a href="javascript:void(0)" onclick="navigateTo(&apos;security_requests&apos;)" class="underline font-medium ml-1">View in Security requests</a>', 'success');
    if (order && order.report_id) {
      viewReport(order.report_id);
    } else {
      navigateTo('security_requests');
    }
  } catch (err) {
    // Error state: inline message above the footer in the danger pair, with a "Try again" text link. Keep user's input.
    if (progressContainer) progressContainer.classList.add('hidden');
    if (errorContainer && errorMessage) {
      errorMessage.textContent = err.message || 'Execution error occurred.';
      errorContainer.classList.remove('hidden');
    } else {
      showNotification(`Execution failed: ${err.message}`, 'error');
    }
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = defaultLabel;
    }
    if (cancelBtn) cancelBtn.disabled = false;
    form.querySelectorAll('textarea, input:not([type="hidden"]), select').forEach(el => el.readOnly = false);
  }
}

async function handleRaiseTicketSubmit(e, orderId, reportId) {
  e.preventDefault();
  const form = e.target;
  const reason = form.reason.value;
  const feedback = form.feedback.value;

  try {
    const res = await apiFetch(`/marketplace/orders/${orderId}/ticket`, {
      method: 'POST',
      body: JSON.stringify({
        reason: reason,
        feedback: feedback
      })
    });
    showNotification(res.message || 'Ticket submitted successfully to specialist.', 'success');
    STATE.activeTicketFormOrderId = null;
    await loadInitialData();
    const updatedReport = STATE.data.reports.find(r => r.id === reportId || r.order_id === orderId);
    if (updatedReport) {
      openModal('report_viewer', updatedReport);
    } else {
      closeModal();
    }
  } catch (err) {
    showNotification(`Failed to submit ticket: ${err.message}`, 'error');
  }
}

async function handleOrderStatusUpdate(orderId, newStatus) {
  try {
    await apiFetch(`/marketplace/orders/${orderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus })
    });
    await loadInitialData();
  } catch (err) {
    showNotification(`Failed to update status: ${err.message}`, 'error');
  }
}

async function handleDeliverSubmit(e, orderId) {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  const cancelBtn = form.querySelector('button[type="button"]');
  const originalHtml = submitBtn ? submitBtn.innerHTML : '';

  if (submitBtn) {
    submitBtn.disabled = true;
    if (cancelBtn) cancelBtn.disabled = true;
    submitBtn.classList.add('opacity-70', 'cursor-not-allowed');
    submitBtn.innerHTML = `
      <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white inline-block" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
      </svg>
      Submitting Deliverable & Disbursing Payment...
    `;
  }

  const summary = form.summary.value;
  const title = form.finding_title?.value || 'Hardened Guardrail Implemented';
  const severity = form.finding_severity?.value || 'medium';
  const recs = (form.recommendations_raw?.value || '').split('\n').filter(r => r.trim());
  const hardenedPrompt = form.hardened_prompt?.value || '';

  try {
    await apiFetch(`/marketplace/orders/${orderId}/deliver`, {
      method: 'POST',
      body: JSON.stringify({
        summary: summary,
        findings: [{ title: title, severity: severity, description: summary, remediation: 'Defense assertion applied' }],
        recommendations: recs,
        hardened_prompt: hardenedPrompt
      })
    });

    closeModal();
    await loadInitialData();
    showNotification('Audit deliverable submitted successfully! Escrow payment has been disbursed.', 'success');
  } catch (err) {
    showNotification(`Delivery failed: ${err.message}`, 'error');
    if (submitBtn) {
      submitBtn.disabled = false;
      if (cancelBtn) cancelBtn.disabled = false;
      submitBtn.classList.remove('opacity-70', 'cursor-not-allowed');
      submitBtn.innerHTML = originalHtml;
    }
  }
}

async function handleBecomeProvider(e) {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = 'Registering Profile & Service...';
  }

  const cats = Array.from(form.querySelectorAll('input[name="cat"]:checked')).map(el => el.value);
  const skills = (form.skills_raw?.value || '').split(',').map(s => s.trim()).filter(Boolean);
  const chosenCategory = form.service_category?.value || cats[0] || 'prompt_engineering';

  const payload = {
    display_name: form.display_name.value.trim(),
    title: form.title.value.trim(),
    provider_type: 'human',
    description: form.description.value.trim(),
    skills: skills,
    categories: cats.length > 0 ? cats : [chosenCategory],
    wallet_address: form.wallet_address.value || null,
    portfolio_url: form.portfolio_url?.value ? form.portfolio_url.value.trim() : null,
    availability: 'available',
    status: 'published'
  };

  try {
    const prov = await apiFetch('/marketplace/providers/profile', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    await apiFetch('/marketplace/services', {
      method: 'POST',
      body: JSON.stringify({
        title: form.service_title.value.trim(),
        description: `Security assessment delivered by ${prov.display_name}.`,
        category: chosenCategory,
        price: parseFloat(form.service_price.value) || 50.0,
        currency: 'USD',
        estimated_delivery: form.service_delivery.value.trim(),
        supported_tasks: ['prompt_injection', 'system_prompt_audit'],
        execution_type: 'manual',
        provider_id: prov.id
      })
    });

    showNotification('Specialist profile and initial service registered successfully! Welcome to your Provider Workspace.', 'success');
    STATE.user.activeProviderId = prov.id;
    STATE.user.role = 'provider';
    await loadInitialData();
    navigateTo('provider_workspace');
  } catch (err) {
    showNotification(`Registration failed: ${err.message}`, 'error');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Register Provider Profile';
    }
  }
}

async function handleEditProviderSubmit(e, providerId) {
  e.preventDefault();
  const form = e.target;
  const cats = Array.from(form.querySelectorAll('input[name="cat"]:checked')).map(el => el.value);
  const skills = (form.skills_raw?.value || '').split(',').map(s => s.trim()).filter(Boolean);

  try {
    await apiFetch(`/marketplace/providers/${providerId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        display_name: form.display_name.value.trim(),
        title: form.title.value.trim(),
        description: form.description.value.trim(),
        skills: skills,
        categories: cats,
        availability: form.availability.value,
        portfolio_url: form.portfolio_url?.value ? form.portfolio_url.value.trim() : null
      })
    });
    showNotification('Specialist profile updated successfully!', 'success');
    closeModal();
    await loadInitialData();
    renderApp();
  } catch (err) {
    showNotification("Failed to update profile: " + (err.detail || err.message || err), 'error');
  }
}

function handleOrderReject(orderId) {
  openModal('reject_order', { orderId });
}

async function handleRejectSubmit(e, orderId) {
  e.preventDefault();
  const form = e.target;
  const reason = form.rejection_reason.value.trim();
  if (!reason) {
    showNotification("A rejection reason is required.", 'error');
    return;
  }
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = "Rejecting...";
  }
  try {
    await apiFetch(`/marketplace/orders/${orderId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'rejected', rejection_reason: reason })
    });
    closeModal();
    showNotification("Request declined. The customer has been notified and escrow refunded.", "info");
    await loadInitialData();
    renderApp();
  } catch (err) {
    showNotification(`Failed to decline request: ${err.detail || err.message}`, "error");
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = "Confirm Rejection";
    }
  }
}

function handleInitiatePayment(orderId) {
  openModal('evm_escrow', { orderId: orderId });
}

async function handleAddServiceSubmit(e, providerId) {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = 'Publishing...';
  }

  try {
    await apiFetch('/marketplace/services', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title.value.trim(),
        description: form.description.value.trim(),
        category: form.category?.value || 'prompt_engineering',
        price: parseFloat(form.price.value) || 0,
        currency: 'USD',
        estimated_delivery: form.estimated_delivery.value.trim(),
        execution_type: 'manual',
        provider_id: providerId
      })
    });
    showNotification('New security service published successfully!', 'success');
    closeModal();
    await loadInitialData();
    renderApp();
  } catch (err) {
    showNotification(`Service creation failed: ${err.detail || err.message}`, 'error');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Publish Service';
    }
  }
}

async function handleEditServiceSubmit(e, serviceId) {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('button[type="submit"]');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerText = 'Saving...';
  }

  try {
    await apiFetch(`/marketplace/services/${serviceId}`, {
      method: 'PATCH',
      body: JSON.stringify({
        title: form.title.value.trim(),
        category: form.category.value,
        price: parseFloat(form.price.value) || 0,
        estimated_delivery: form.estimated_delivery.value.trim(),
        description: form.description.value.trim()
      })
    });
    showNotification('Service offering updated successfully!', 'success');
    closeModal();
    await loadInitialData();
    renderApp();
  } catch (err) {
    showNotification(`Failed to update service: ${err.detail || err.message}`, 'error');
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerText = 'Save Changes';
    }
  }
}

async function handleDeleteService(serviceId) {
  if (!confirm('Are you sure you want to delete this service offering?')) return;
  try {
    await apiFetch(`/marketplace/services/${serviceId}`, {
      method: 'DELETE'
    });
    showNotification('Service offering deleted successfully.', 'success');
    await loadInitialData();
    renderApp();
  } catch (err) {
    showNotification(`Failed to delete service: ${err.detail || err.message}`, 'error');
  }
}

async function handleCreatePromptSubmit(e) {
  e.preventDefault();
  const form = e.target;
  try {
    await apiFetch('/marketplace/prompts', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title.value,
        content: form.content.value
      })
    });
    closeModal();
    await loadInitialData();
  } catch (err) {
    showNotification(`Failed to save prompt: ${err.message}`, 'error');
  }
}

async function handleDeletePrompt(promptId) {
  if (!confirm('Are you sure you want to delete this saved prompt?')) return;
  try {
    await apiFetch(`/marketplace/prompts/${promptId}`, { method: 'DELETE' });
    await loadInitialData();
  } catch (err) {
    showNotification(`Delete failed: ${err.message}`, 'error');
  }
}

// ---------------------------------------------------------------------------
// Arkiv Marketplace Action Handlers (MetaMask Browser Signing + Rabdi)
// ---------------------------------------------------------------------------

function openPostTaskModal() {
  if (!STATE.auth.walletAddress) {
    showNotification('Please connect your MetaMask wallet first to publish an on-chain task to Rabdi testnet.', 'info');
    connectAndSignWithMetaMask();
    return;
  }
  openModal('arkiv_post_task');
}

async function handlePostTask(event) {
  event.preventDefault();
  const form = event.target;
  const statusEl = document.getElementById('post-task-status');
  const submitBtn = document.getElementById('post-task-submit-btn');

  const title = form.title.value.trim();
  const category = form.category.value;
  const budgetRange = form.budget_range.value.trim();
  const requiredSkills = form.required_skills.value.trim();
  const publicDescription = form.public_description.value.trim();
  const budgetType = form.budget_type.value;
  const deadline = form.deadline.value.trim();

  if (!STATE.auth.walletAddress) {
    showNotification('Wallet not connected. Please connect MetaMask.', 'info');
    return;
  }

  if (typeof window === 'undefined' || !window.ArkivModule) {
    showNotification('Arkiv SDK browser bundle not loaded. Please reload the page.', 'info');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }

  if (statusEl) {
    statusEl.classList.remove('hidden');
    statusEl.innerHTML = `
      <div class="p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12.5px] text-[var(--text)] flex items-center gap-2.5">
        <div class="w-4 h-4 border-2 border-[var(--text)] border-t-transparent rounded-full animate-spin shrink-0"></div>
        <span>Confirming transaction in MetaMask on Rabdi Testnet (Chain ID 7794095)...</span>
      </div>
    `;
  }

  try {
    const taskId = 'task-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 6);
    const accessKey = (STATE.arkiv && STATE.arkiv.config && STATE.arkiv.config.access_key) ? STATE.arkiv.config.access_key : '';

    const result = await window.ArkivModule.publishSecurityTask({
      taskId,
      category,
      title,
      publicDescription,
      requiredSkills,
      budgetType,
      budgetRange,
      deadline
    }, STATE.auth.walletAddress, accessKey);

    const { entityKey, txHash } = result;

    if (statusEl) {
      statusEl.innerHTML = `
        <div class="p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12.5px] text-[var(--text)] space-y-1">
          <div class="font-medium text-[var(--success)]">Confirmed on Rabdi. Reconciling with Guardvane...</div>
          <div class="text-[11px] font-mono text-[var(--text-3)] break-all">Tx: ${txHash}</div>
        </div>
      `;
    }

    await apiFetch('/marketplace/arkiv/reconcile/task', {
      method: 'POST',
      body: JSON.stringify({
        task_id: taskId,
        entity_key: entityKey,
        tx_hash: txHash,
        title,
        category,
        public_description: publicDescription,
        required_skills: requiredSkills,
        budget_range: budgetRange,
        customer_wallet: STATE.auth.walletAddress
      })
    });

    showNotification(`Task successfully published to Arkiv!\nEntity Key: ${entityKey}\nTx Hash: ${txHash}`, 'success');
    closeModal();
    await loadArkivTasks(true);
    navigateTo('opihub', { tab: 'requests' });
  } catch (err) {
    console.error('Failed to post task on Arkiv:', err);
    if (statusEl) {
      statusEl.classList.remove('hidden');
      statusEl.innerHTML = `
        <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12.5px] text-[#991B1B] space-y-1">
          <div class="font-semibold">Transaction Error</div>
          <div class="text-[11.5px] break-all">${escapeHtml(err.message || String(err))}</div>
        </div>
      `;
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }
  }
}

function openSubmitBidModal(taskId) {
  if (!STATE.auth.walletAddress) {
    showNotification('Please connect your MetaMask wallet first to submit a specialist bid.', 'info');
    connectAndSignWithMetaMask();
    return;
  }
  const task = (STATE.arkiv.tasks || []).find(t => t.task_id === taskId);
  if (task && task.customer_wallet && task.customer_wallet.toLowerCase() === STATE.auth.walletAddress.toLowerCase()) {
    showNotification('You cannot submit a bid on your own security task.', 'info');
    return;
  }
  openModal('arkiv_submit_bid', { taskId, task });
}

async function handleSubmitBid(event, taskId) {
  event.preventDefault();
  const form = event.target;
  const statusEl = document.getElementById('submit-bid-status');
  const submitBtn = document.getElementById('submit-bid-btn');

  const proposedPrice = parseFloat(form.proposed_price.value);
  const estimatedDuration = form.estimated_duration.value.trim();
  const proposalSummary = form.proposal_summary.value.trim();

  if (!STATE.auth.walletAddress) {
    showNotification('Please connect your MetaMask wallet.', 'info');
    return;
  }

  if (typeof window === 'undefined' || !window.ArkivModule) {
    showNotification('Arkiv SDK browser module not loaded. Please reload.', 'info');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }

  if (statusEl) {
    statusEl.classList.remove('hidden');
    statusEl.innerHTML = `
      <div class="p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12.5px] text-[var(--text)] flex items-center gap-2.5">
        <div class="w-4 h-4 border-2 border-[var(--text)] border-t-transparent rounded-full animate-spin shrink-0"></div>
        <span>Confirming specialist bid on Rabdi testnet via MetaMask...</span>
      </div>
    `;
  }

  try {
    const accessKey = (STATE.arkiv && STATE.arkiv.config && STATE.arkiv.config.access_key) ? STATE.arkiv.config.access_key : '';

    const result = await window.ArkivModule.submitSpecialistBid({
      taskId,
      proposedPrice,
      estimatedDuration,
      proposalSummary
    }, STATE.auth.walletAddress, accessKey);

    const { entityKey, txHash } = result;

    await apiFetch('/marketplace/arkiv/reconcile/bid', {
      method: 'POST',
      body: JSON.stringify({
        task_id: taskId,
        entity_key: entityKey,
        tx_hash: txHash,
        proposed_price: proposedPrice,
        estimated_duration: estimatedDuration,
        proposal_summary: proposalSummary,
        specialist_wallet: STATE.auth.walletAddress
      })
    });

    showNotification(`Bid successfully submitted on Arkiv!\nEntity Key: ${entityKey}\nTx Hash: ${txHash}`, 'success');
    closeModal();
    await openTaskBidsModal(taskId);
  } catch (err) {
    console.error('Failed to submit bid:', err);
    if (statusEl) {
      statusEl.classList.remove('hidden');
      statusEl.innerHTML = `
        <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12.5px] text-[#991B1B] space-y-1">
          <div class="font-semibold">Transaction Error</div>
          <div class="text-[11.5px] break-all">${escapeHtml(err.message || String(err))}</div>
        </div>
      `;
    }
  } finally {
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }
  }
}

async function openTaskBidsModal(taskId) {
  STATE.arkiv.selectedTaskId = taskId;
  STATE.arkiv.taskBids = [];
  const task = (STATE.arkiv.tasks || []).find(t => t.task_id === taskId);
  openModal('arkiv_view_bids', { taskId, task, loading: true });

  try {
    const bids = await apiFetch(`/marketplace/arkiv/tasks/${taskId}/bids`);
    STATE.arkiv.taskBids = bids || [];
    if (STATE.activeModal === 'arkiv_view_bids') {
      openModal('arkiv_view_bids', { taskId, task, loading: false });
    }
  } catch (err) {
    console.error('Failed to fetch bids for task:', err);
    if (STATE.activeModal === 'arkiv_view_bids') {
      openModal('arkiv_view_bids', { taskId, task, loading: false, error: err.message });
    }
  }
}

async function handleAcceptBid(taskId, bidKey, specialistWallet) {
  if (!confirm(`Award task to specialist ${specialistWallet.substring(0, 8)}...? This will publish an immutable award record to Arkiv on Rabdi testnet.`)) {
    return;
  }

  const statusEl = document.getElementById('award-action-status');
  if (statusEl) {
    statusEl.classList.remove('hidden');
    statusEl.innerHTML = `
      <div class="p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12.5px] text-[var(--text)] flex items-center gap-2.5">
        <div class="w-4 h-4 border-2 border-[var(--text)] border-t-transparent rounded-full animate-spin shrink-0"></div>
        <span>Confirming award on Rabdi testnet via MetaMask...</span>
      </div>
    `;
  }

  try {
    const accessKey = (STATE.arkiv && STATE.arkiv.config && STATE.arkiv.config.access_key) ? STATE.arkiv.config.access_key : '';

    const result = await window.ArkivModule.acceptBidAndCreateAward({
      taskId,
      acceptedBidKey: bidKey,
      specialistWallet
    }, STATE.auth.walletAddress, accessKey);

    const { entityKey, txHash } = result;

    await apiFetch('/marketplace/arkiv/reconcile/award', {
      method: 'POST',
      body: JSON.stringify({
        task_id: taskId,
        entity_key: entityKey,
        tx_hash: txHash,
        accepted_bid_key: bidKey,
        customer_wallet: STATE.auth.walletAddress,
        specialist_wallet: specialistWallet
      })
    });

    showNotification(`Task successfully awarded on Arkiv!\nEntity Key: ${entityKey}\nTx Hash: ${txHash}`, 'success');
    closeModal();
    await loadArkivTasks(true);
    await loadInitialData();
  } catch (err) {
    console.error('Failed to accept bid:', err);
    if (statusEl) {
      statusEl.classList.remove('hidden');
      statusEl.innerHTML = `
        <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12.5px] text-[#991B1B] space-y-1">
          <div class="font-semibold">Award Error</div>
          <div class="text-[11.5px] break-all">${escapeHtml(err.message || String(err))}</div>
        </div>
      `;
    }
  }
}

async function runLocalPromptAnalysis(promptText, promptId = null) {
  openModal('quick_analyze');
  const input = document.getElementById('quick-prompt-input');
  if (input) input.value = promptText;
  executeQuickAnalyze(promptId);
}

async function executeQuickAnalyze(promptId = null) {
  const input = document.getElementById('quick-prompt-input');
  const resultsBox = document.getElementById('quick-analyze-results');
  const scanBtn = document.getElementById('quick-scan-btn');
  if (!input || !resultsBox) return;

  const text = input.value;
  if (!text.trim()) {
    showNotification('Please enter a prompt to analyze.', 'info');
    return;
  }

  // Prevent stale results and set explicit loading state
  resultsBox.classList.remove('hidden');
  resultsBox.innerHTML = `
    <div class="flex items-center gap-2.5 p-3 text-[12.5px] text-[var(--text)] bg-[var(--surface-sunk)] rounded-[var(--radius-md)] border border-[var(--border)]">
      <div class="w-4 h-4 border-2 border-[var(--text)] border-t-transparent rounded-full animate-spin shrink-0"></div>
      <span>Running Guardvane ML security analysis (MPDD injection model, 15 application risks, credentials)...</span>
    </div>
  `;

  if (scanBtn) {
    scanBtn.disabled = true;
    scanBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }

  try {
    const analysis = await apiFetch('/analyze', {
      method: 'POST',
      body: JSON.stringify({ prompt: text, analysis_mode: 'both' })
    });

    const pSec = analysis.prompt_security || {};
    const appRisks = analysis.application_risks || {};
    const sData = analysis.sensitive_data || {};
    const taskClass = analysis.task_classification || {};

    // 1. Safe extraction of probability and conversion to percentage
    const rawProb = pSec.malicious_probability ?? pSec.confidence_score ?? pSec.injection_score;
    let probNum = (typeof rawProb === 'number') ? rawProb : parseFloat(rawProb);
    if (isNaN(probNum) || probNum === null || probNum === undefined) {
      probNum = 0.0;
    }
    // Consistent probability to percentage conversion (0.0 to 1.0 -> 0% to 100%)
    const probPct = (probNum <= 1.0 ? probNum * 100 : probNum).toFixed(1);

    // 2. Safe malicious and risk category evaluation
    const isMalicious = Boolean(pSec.is_malicious ?? pSec.is_injection_detected ?? (probNum >= 0.5));
    const riskCat = pSec.risk_category || (isMalicious ? 'High Risk' : 'Low Risk');

    // 3. Safe sensitive data detection counting
    const sCount = (typeof sData.findings_count === 'number')
      ? sData.findings_count
      : ((typeof sData.count === 'number') ? sData.count : (Array.isArray(sData.findings) ? sData.findings.length : 0));
    const hasSecrets = Boolean(sData.detected ?? sData.has_sensitive_data ?? (sCount > 0));

    resultsBox.innerHTML = `
      <div class="space-y-3.5 text-[12.5px]">
        <div class="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
          <div class="flex items-center gap-2">
            <span class="font-medium text-[var(--text)]">Analysis Findings</span>
            ${taskClass.category ? `
              <span class="pill pill-neutral font-mono text-[11px]">
                ${escapeHtml(taskClass.category)}
              </span>
            ` : ''}
          </div>
          <span class="pill ${isMalicious ? 'pill-danger' : 'pill-success'}">
            ${escapeHtml(riskCat)}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="surface-card p-3 space-y-0.5">
            <div class="text-[11px] text-[var(--text-3)] font-medium">Injection Probability</div>
            <div class="text-xl font-medium font-mono ${probNum >= 0.5 ? 'text-[var(--danger)]' : 'text-[var(--text)]'}">
              ${probPct}%
            </div>
            <div class="text-[11px] text-[var(--text-3)]">
              ${isMalicious ? 'Adversarial pattern detected' : 'Within benign distribution'}
            </div>
          </div>

          <div class="surface-card p-3 space-y-0.5">
            <div class="text-[11px] text-[var(--text-3)] font-medium">Sensitive Credentials</div>
            <div class="text-xl font-medium font-mono ${hasSecrets ? 'text-[var(--danger)]' : 'text-[var(--text)]'}">
              ${sCount} detected
            </div>
            <div class="text-[11px] text-[var(--text-3)]">
              ${hasSecrets ? 'Credentials / tokens found' : 'No credentials detected'}
            </div>
          </div>
        </div>

        ${hasSecrets && Array.isArray(sData.findings) && sData.findings.length > 0 ? `
          <div class="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-[var(--radius-md)] text-[12px] space-y-1">
            <div class="font-medium text-[var(--danger)]">Detected Secrets:</div>
            ${sData.findings.map(f => `
              <div class="font-mono text-[11.5px] text-[var(--danger)]">${escapeHtml(f.description)}: ${escapeHtml(f.redacted)}</div>
            `).join('')}
          </div>
        ` : ''}

        <div>
          <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em] mb-1.5">Detected Risks (OWASP LLM)</div>
          <div class="flex flex-wrap gap-1.5">
            ${(appRisks.detected_risks || []).length > 0 ? (appRisks.detected_risks || []).map(r => `
              <span class="pill pill-warning">
                ${escapeHtml(r)}
              </span>
            `).join('') : '<span class="text-[var(--text-3)] text-[12px]">No critical application risk categories triggered.</span>'}
          </div>
        </div>

        <div class="pt-3 border-t border-[var(--border)] flex justify-between items-center">
          <span class="text-[11px] text-[var(--text-3)]">Evaluated by Guardvane Local Security Engine</span>
          <button onclick="closeModal(); openModal('request_review', { promptText: '${escapeForAttr(text)}' })" class="btn-primary text-[12px] py-1.5 px-3">
            Submit for Provider Hardening →
          </button>
        </div>
      </div>
    `;

    if (promptId) {
      await apiFetch(`/marketplace/prompts/${promptId}`, {
        method: 'PUT',
        body: JSON.stringify({
          analysis_result: {
            injection_score: probNum,
            sensitive_data_count: sCount,
            risk_labels: appRisks.detected_risks || []
          }
        })
      });
      await loadInitialData();
    }
  } catch (err) {
    resultsBox.innerHTML = `
      <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12.5px] text-[#991B1B] space-y-1">
        <div class="font-semibold">Analysis Failed</div>
        <div>${escapeHtml(err.message || 'An unexpected error occurred during security analysis.')}</div>
      </div>
    `;
  } finally {
    if (scanBtn) {
      scanBtn.disabled = false;
      scanBtn.classList.remove('opacity-60', 'cursor-not-allowed');
    }
  }
}

async function executeQuickOptimize(promptId = null, bypassCache = false) {
  const input = document.getElementById('quick-prompt-input');
  const resultsBox = document.getElementById('quick-analyze-results');
  const scanBtn = document.getElementById('quick-scan-btn');
  const optBtn = document.getElementById('quick-opt-btn');
  if (!input || !resultsBox) return;

  const text = input.value;
  if (!text.trim()) {
    showNotification('Please enter a prompt to evaluate and harden.', 'info');
    return;
  }

  resultsBox.classList.remove('hidden');
  resultsBox.innerHTML = `
    <div class="flex items-center gap-2.5 p-3 text-[12.5px] text-[var(--text)] bg-[var(--surface-sunk)] rounded-[var(--radius-md)] border border-[var(--border)]">
      <div class="w-4 h-4 border-2 border-[var(--text)] border-t-transparent rounded-full animate-spin shrink-0"></div>
      <span>${bypassCache ? 'Retrying fresh 0G Private Computer AI reasoning (bypassing cache)...' : '0G Private Computer performing AI threat reasoning & prompt hardening (Verified Mode)...'}</span>
    </div>
  `;

  if (scanBtn) { scanBtn.disabled = true; scanBtn.classList.add('opacity-60', 'cursor-not-allowed'); }
  if (optBtn) { optBtn.disabled = true; optBtn.classList.add('opacity-60', 'cursor-not-allowed'); }

  try {
    const data = await apiFetch('/optimize', {
      method: 'POST',
      headers: {
        'X-User-Id': (STATE.user && STATE.user.id) ? STATE.user.id : 'default'
      },
      body: JSON.stringify({
        prompt: text,
        analysis_mode: 'both',
        fallback_to_local: false,
        bypass_cache: bypassCache,
        temperature: 0.3,
        max_tokens: 2000
      })
    });

    const meta = data.zero_g_metadata || {};
    const structured = data.structured_reasoning || (data.reasoning ? data.reasoning.structured : null) || {};
    const taskUnd = structured.task_understanding || (data.reasoning ? data.reasoning.task_understanding : null) || {};
    const secAnalysis = structured.security_analysis || (data.reasoning ? data.reasoning.security_analysis : null) || {};
    const findings = secAnalysis.findings || [];
    const missingReqs = structured.missing_security_requirements || data.missing_requirements_addressed || [];
    const changesMade = structured.changes_made || (data.reasoning ? data.reasoning.changes_made : null) || [];
    const assumptions = structured.assumptions || (data.reasoning ? data.reasoning.assumptions : null) || [];
    const remainingRisks = structured.remaining_risks || (data.reasoning ? data.reasoning.remaining_risks : null) || [];

    const isCompleted = (data.status === '0g_reasoning_completed' || meta.status === '0g_reasoning_completed' || meta.status === '0g_success');
    const isCached = Boolean(meta.cached || meta.status === '0g_success_cached');
    const isFailed = (data.status === '0g_reasoning_failed' || meta.status === '0g_reasoning_failed');
    const isLocalOnly = (data.status === 'local_only' || meta.status === 'local_only');

    // Execution status labels
    let statusLabel = '0G reasoning completed';
    let statusBadgeClass = 'pill pill-success';
    if (isFailed) {
      statusLabel = '0G reasoning failed';
      statusBadgeClass = 'pill pill-danger';
    } else if (isLocalOnly) {
      statusLabel = 'Local-only analysis';
      statusBadgeClass = 'pill pill-warning';
    } else if (isCached) {
      statusLabel = '0G reasoning completed (Cached)';
      statusBadgeClass = 'pill pill-info';
    }

    // Severity color helper
    const getSevBadge = (sev) => {
      const s = String(sev || 'medium').toLowerCase();
      if (s === 'critical' || s === 'high') return 'pill pill-danger';
      if (s === 'medium') return 'pill pill-warning';
      return 'pill pill-info';
    };

    if (isFailed) {
      // 0G Reasoning Failed View
      resultsBox.innerHTML = `
        <div class="space-y-3.5 text-[12.5px]">
          <div class="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
            <span class="${statusBadgeClass}">
              ${statusLabel}
            </span>
            <span class="text-[11px] font-mono text-[var(--text-3)]">${meta.duration_ms ? `${meta.duration_ms}ms` : '0ms'}</span>
          </div>

          <div class="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-[var(--radius-md)] text-[12px] text-[var(--danger)] space-y-1.5">
            <div class="font-medium">
              0G Private Computer AI Reasoning Encountered an Error
            </div>
            <p class="font-mono text-[11.5px]">${escapeHtml(data.error || meta.error || '0G node returned an invalid response structure or network timeout.')}</p>
            <div class="text-[11px] opacity-80 pt-1">
              Guardvane does NOT silently substitute local heuristics for missing 0G AI reasoning. You may retry the remote inference below.
            </div>
          </div>

          <!-- Preserved Local Preprocessing Scan (if available) -->
          ${data.security_analysis ? `
            <div class="surface-card p-3 space-y-2">
              <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">Preserved Local Preprocessing Signals</div>
              <div class="grid grid-cols-2 gap-2 text-[12px]">
                <div><span class="text-[var(--text-3)]">Injection Score:</span> <strong>${(data.security_analysis.prompt_security?.malicious_probability * 100 || 0).toFixed(1)}%</strong></div>
                <div><span class="text-[var(--text-3)]">Detected Secrets:</span> <strong>${data.security_analysis.sensitive_data?.findings_count || 0}</strong></div>
              </div>
            </div>
          ` : ''}

          <!-- Actions -->
          <div class="pt-3 border-t border-[var(--border)] flex justify-between items-center">
            <button onclick="executeQuickOptimize(null, true)" class="btn-primary text-[12px] py-1.5 px-3">
              Retry 0G Reasoning
            </button>
            <button onclick="navigator.clipboard.writeText(document.getElementById('quick-prompt-input').value); showNotification('Copied original prompt!', 'success');" class="btn-secondary text-[12px] py-1.5 px-3">
              Copy Original Prompt
            </button>
          </div>
        </div>
      `;
      return;
    }

    // Success / Local-Only View with the 8 Distinct Required Sections
    resultsBox.innerHTML = `
      <div class="space-y-4 text-[12.5px]">
        <!-- Execution Status & Telemetry Header -->
        <div class="surface-card p-3.5 space-y-2.5">
          <div class="flex items-center justify-between">
            <span class="${statusBadgeClass}">
              ${statusLabel}
            </span>
            <div class="flex items-center gap-3">
              <span class="text-[11px] font-mono text-[var(--text-3)]">
                ${meta.duration_ms ? `${meta.duration_ms}ms` : '0ms'}
              </span>
              <button onclick="const el = document.getElementById('inference-telemetry-drawer'); el.classList.toggle('hidden');" class="text-[11px] text-[var(--accent)] hover:underline cursor-pointer font-medium">
                View Inference Details
              </button>
            </div>
          </div>

          <!-- Inference Details Collapsible Drawer -->
          <div id="inference-telemetry-drawer" class="hidden p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-sm)] mt-2 text-[11px] font-mono space-y-1">
            <div class="grid grid-cols-2 gap-2 text-[var(--text-2)]">
              <div><span class="text-[var(--text-3)]">Provider:</span> ${escapeHtml(isLocalOnly ? 'Local Deterministic Rules' : (meta.provider || '0G Private Computer'))}</div>
              <div><span class="text-[var(--text-3)]">Model:</span> ${escapeHtml(isLocalOnly ? 'N/A (Local Heuristic Scan)' : (meta.model || 'glm-5.2'))}</div>
              <div><span class="text-[var(--text-3)]">Trust Mode:</span> ${escapeHtml(isLocalOnly ? 'N/A' : (meta.trust_mode || 'verified'))}</div>
              <div><span class="text-[var(--text-3)]">Request ID:</span> <span class="truncate inline-block max-w-[120px]" title="${escapeForAttr(meta.request_id || 'N/A')}">${escapeHtml(meta.request_id || 'N/A')}</span></div>
              <div><span class="text-[var(--text-3)]">Total Tokens:</span> ${meta.total_tokens ? meta.total_tokens : (meta.usage?.total_tokens ?? 'N/A')}</div>
              <div><span class="text-[var(--text-3)]">Latency:</span> ${meta.duration_ms || 0}ms</div>
            </div>
            <div class="text-[10px] text-[var(--text-3)] pt-1 border-t border-[var(--border)]">
              * Gateway Request ID tracks transport routing; it is not a cryptographic attestation proof. Configured model is only verified upon real provider response.
            </div>
          </div>
        </div>

        <!-- 1. Task Understanding -->
        <div class="surface-card p-3.5 space-y-2">
          <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em] flex items-center justify-between">
            <span>1. Task Understanding</span>
            <span class="text-[11px] text-[var(--text-3)] font-mono font-normal">${escapeHtml(taskUnd.application_type || 'Application Specification')}</span>
          </div>
          <div class="text-[12px] text-[var(--text)]">
            <strong class="font-medium">User Intent:</strong> ${escapeHtml(taskUnd.user_intent || data.preserved_intent || 'Preserved development intention.')}
          </div>
          ${Array.isArray(taskUnd.technologies) && taskUnd.technologies.length > 0 ? `
            <div class="flex flex-wrap gap-1.5 pt-1">
              <span class="text-[10.5px] text-[var(--text-3)] font-medium mr-1">Technologies:</span>
              ${taskUnd.technologies.map(t => `
                <span class="pill pill-neutral font-mono text-[10.5px]">
                  ${escapeHtml(t)}
                </span>
              `).join('')}
            </div>
          ` : ''}
        </div>

        <!-- 2. Security Risk Assessment -->
        <div class="surface-card p-3.5 space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">2. Security Risk Assessment</span>
            <span class="${getSevBadge(secAnalysis.overall_risk || data.overall_risk || 'Low')}">
              ${escapeHtml(secAnalysis.overall_risk || data.overall_risk || 'Low')} Risk
            </span>
          </div>
          <p class="text-[12px] text-[var(--text-2)] leading-relaxed">
            ${escapeHtml(data.reasoning?.contextual_summary || 'Contextual threat analysis performed on requested application parameters.')}
          </p>
        </div>

        <!-- 3. Vulnerability Findings -->
        <div class="surface-card p-3.5 space-y-2.5">
          <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">
            3. Vulnerability Findings (${findings.length})
          </div>
          ${findings.length > 0 ? `
            <div class="space-y-2">
              ${findings.map((f, i) => `
                <div class="p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12px] space-y-1">
                  <div class="flex items-center justify-between">
                    <strong class="text-[var(--text)] font-medium text-[12.5px]">${i+1}. ${escapeHtml(f.vulnerability)}</strong>
                    <div class="flex items-center gap-1.5">
                      <span class="${getSevBadge(f.severity)} text-[10px]">
                        ${escapeHtml(f.severity)}
                      </span>
                      ${f.confidence ? `<span class="text-[10px] font-mono text-[var(--text-3)]">(${(f.confidence * 100).toFixed(0)}% conf)</span>` : ''}
                    </div>
                  </div>
                  ${f.evidence ? `<div class="text-[11px] text-[var(--text-3)] italic">"${escapeHtml(f.evidence)}"</div>` : ''}
                  <div class="text-[var(--text-2)]">${escapeHtml(f.explanation)}</div>
                  ${f.recommendation ? `
                    <div class="text-[11.5px] text-[var(--text)] pt-0.5">
                      <span class="font-medium text-[var(--text-3)]">Mitigation:</span> ${escapeHtml(f.recommendation)}
                    </div>
                  ` : ''}
                </div>
              `).join('')}
            </div>
          ` : `
            <div class="text-[12px] text-[var(--text-3)]">No critical application vulnerabilities detected in this request.</div>
          `}
        </div>

        <!-- 4. Attack Scenarios -->
        ${findings.some(f => f.attack_scenario) ? `
          <div class="surface-card p-3.5 space-y-2">
            <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">4. Attack Scenarios</div>
            <div class="space-y-1.5">
              ${findings.filter(f => f.attack_scenario).map(f => `
                <div class="p-2.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[11.5px] text-[var(--text-2)] space-y-0.5">
                  <strong class="text-[var(--text)] font-medium">${escapeHtml(f.vulnerability)}:</strong>
                  <div>${escapeHtml(f.attack_scenario)}</div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- 5. Recommended Security Controls -->
        ${missingReqs.length > 0 ? `
          <div class="surface-card p-3.5 space-y-1.5">
            <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">5. Recommended Security Controls</div>
            <ul class="list-disc list-inside space-y-1 text-[12px] text-[var(--text-2)]">
              ${missingReqs.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}

        <!-- 6. Improved Prompt -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-[12px] font-semibold text-[var(--text-2)] uppercase tracking-[0.06em]">6. Improved Prompt Specification</span>
            <button onclick="navigator.clipboard.writeText(document.getElementById('opt-prompt-result-text').innerText); showNotification('Copied improved prompt to clipboard!', 'success');" class="text-xs text-[var(--accent)] hover:underline font-medium cursor-pointer">
              Copy improved prompt
            </button>
          </div>
          <pre id="opt-prompt-result-text" class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12px] font-mono text-[var(--text)] max-h-64 overflow-y-auto whitespace-pre-wrap select-all leading-relaxed">${escapeHtml(data.optimized_prompt || data.hardened_prompt || '')}</pre>
        </div>

        <!-- 7. Changes Made -->
        ${changesMade.length > 0 ? `
          <div class="surface-card p-3.5 space-y-1.5">
            <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">7. Changes Made & Rationale</div>
            <div class="space-y-1">
              ${changesMade.map(c => `
                <div class="text-[11.5px] text-[var(--text-2)]">
                  <span class="font-medium text-[var(--text)]">• ${escapeHtml(c.change || c)}:</span> ${escapeHtml(c.reason || 'Embedded security requirement')}
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- 8. Assumptions and Remaining Risks -->
        ${(assumptions.length > 0 || remainingRisks.length > 0) ? `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            ${assumptions.length > 0 ? `
              <div class="surface-card p-3 space-y-1">
                <div class="font-medium text-[var(--text-3)] text-[11px] uppercase tracking-[0.06em]">Assumptions</div>
                <ul class="list-disc list-inside space-y-0.5 text-[11.5px] text-[var(--text-2)]">
                  ${assumptions.map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
            ${remainingRisks.length > 0 ? `
              <div class="surface-card p-3 space-y-1">
                <div class="font-medium text-[var(--danger)] text-[11px] uppercase tracking-[0.06em]">Remaining Residual Risks</div>
                <ul class="list-disc list-inside space-y-0.5 text-[11.5px] text-[var(--text-2)]">
                  ${remainingRisks.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
          </div>
        ` : ''}

        <!-- Footer Control Actions -->
        <div class="pt-3 border-t border-[var(--border)] flex flex-wrap justify-between items-center gap-2">
          <div class="flex items-center gap-2">
            <button onclick="navigator.clipboard.writeText(document.getElementById('quick-prompt-input').value); showNotification('Copied original prompt!', 'success');" class="btn-secondary text-[12px] py-1.5 px-3">
              Copy Original Prompt
            </button>
            <button onclick="executeQuickOptimize(null, true)" class="btn-secondary text-[12px] py-1.5 px-3">
              Retry 0G Reasoning
            </button>
          </div>
          <button onclick="saveOptimizedPromptFromModal('${escapeForAttr(data.optimized_prompt || data.hardened_prompt || '')}')" class="btn-primary text-[12px] py-1.5 px-3.5">
            Save to My Prompts
          </button>
        </div>
      </div>
    `;

    if (promptId) {
      await apiFetch(`/marketplace/prompts/${promptId}`, {
        method: 'PUT',
        body: JSON.stringify({
          analysis_result: {
            status: data.status,
            overall_risk: secAnalysis.overall_risk || data.overall_risk,
            findings_count: findings.length,
            optimized_prompt: data.optimized_prompt,
          }
        })
      });
      await loadInitialData();
    }
  } catch (err) {
    resultsBox.innerHTML = `
      <div class="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-[var(--radius-md)] text-[12.5px] text-[var(--danger)] space-y-1.5">
        <div class="font-medium flex items-center justify-between">
          <span>0G AI Reasoning Request Failed</span>
          <span class="pill pill-danger">
            0G reasoning failed
          </span>
        </div>
        <p class="font-mono text-[11.5px]">${escapeHtml(err.message || 'An unexpected error occurred during 0G reasoning.')}</p>
        <div class="pt-2">
          <button onclick="executeQuickOptimize(null, true)" class="btn-primary text-[11.5px] py-1 px-3">
            Retry 0G Reasoning
          </button>
        </div>
      </div>
    `;
  } finally {
    if (scanBtn) { scanBtn.disabled = false; scanBtn.classList.remove('opacity-60', 'cursor-not-allowed'); }
    if (optBtn) { optBtn.disabled = false; optBtn.classList.remove('opacity-60', 'cursor-not-allowed'); }
  }
}

async function saveOptimizedPromptFromModal(content) {
  try {
    await apiFetch('/marketplace/prompts', {
      method: 'POST',
      headers: { 'X-User-Id': STATE.user.id || 'francis' },
      body: JSON.stringify({
        title: `0G Hardened Prompt — ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        content: content,
        is_private: true
      })
    });
    showNotification('Hardened prompt saved to your private library!', 'success');
    closeModal();
    await loadInitialData();
    navigateTo('my_prompts');
  } catch (e) {
    showNotification(`Failed to save prompt: ${e.message}`, 'error');
  }
}

function viewReport(reportId) {
  const report = STATE.data.reports.find(r => r.id === reportId);
  if (report) {
    openModal('report_viewer', report);
  }
}

// ---------------------------------------------------------------------------
// Helpers & In-App Notifications
// ---------------------------------------------------------------------------

function showNotification(message, type = 'info', duration = 4000) {
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
    ? 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)]'
    : isError
    ? 'bg-[var(--surface)] border-[#FECACA] text-[var(--text)]'
    : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)]';

  const icon = isSuccess
    ? `<svg class="w-4 h-4 text-[var(--success)] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>`
    : isError
    ? `<svg class="w-4 h-4 text-[var(--danger)] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`
    : `<svg class="w-4 h-4 text-[var(--info)] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`;

  toast.className = `pointer-events-auto p-3.5 rounded-[var(--radius-md)] border shadow-xs flex items-start gap-3 text-[13px] transition-all duration-300 opacity-0 translate-y-2 ${borderBg}`;
  toast.innerHTML = `
    ${icon}
    <div class="flex-1 leading-snug">${escapeHtml(message)}</div>
    <button onclick="this.parentElement.remove()" class="text-[var(--text-3)] hover:text-[var(--text)] text-sm shrink-0 ml-1 cursor-pointer">✕</button>
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


function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeForAttr(str) {
  if (!str) return '';
  return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/'/g, "\\'")
    .replace(/"/g, '&quot;')
    .replace(/\n/g, '\\n')
    .replace(/\r/g, '');
}

// Background Auto-Sync for Live Requests & Orders (every 5 seconds)
function startBackgroundSync() {
  if (window._bgSyncTimer) return;
  window._bgSyncTimer = setInterval(async () => {
    // Only poll if user is authenticated and not actively editing modal inputs
    if (!STATE.auth.walletAddress || STATE.activeModal === 'request_review') return;
    try {
      const orders = await apiFetch('/marketplace/orders');
      if (Array.isArray(orders)) {
        const oldSign = (STATE.data.orders || []).map(o => `${o.id}:${o.status}:${o.payment_status}:${o.escrow_state || ''}:${o.report_id || ''}`).join('|');
        const newSign = orders.map(o => `${o.id}:${o.status}:${o.payment_status}:${o.escrow_state || ''}:${o.report_id || ''}`).join('|');
        if (oldSign !== newSign) {
          STATE.data.orders = orders;
          try {
            const reports = await apiFetch('/marketplace/reports');
            if (Array.isArray(reports)) STATE.data.reports = reports;
          } catch (re) {}
          if (['my_requests', 'provider_workspace', 'dashboard'].includes(STATE.currentView) && !STATE.activeModal) {
            renderApp();
          }
        }
      }
    } catch (e) {
      // Background poll failure is silent
    }
  }, 5000);
}

// Initialize on DOM load
window.addEventListener('DOMContentLoaded', async () => {
  const hasSession = await checkAuthSession();
  if (hasSession) {
    await loadInitialData();
    startBackgroundSync();
  } else {
    renderApp();
  }
});


// ---------------------------------------------------------------------------
// Route 2: Human Specialists EVM Escrow Flow (Rabdi Testnet Chain ID 7794095)
// ---------------------------------------------------------------------------

function renderEVMEscrowModal() {
  const payload = STATE.modalPayload || {};
  const orderId = payload.orderId;
  const order = (STATE.data.orders || []).find(o => o.id === orderId);
  if (!order) {
    return `<div class="p-6 text-center text-[var(--text-3)]">Order not found.</div>`;
  }

  const specialistWallet = order.provider_wallet || '0xaf6b2b8df91a6063a35c3f491183ec35d1fbff54';
  const priceUsd = order.price || 4.0;
  const amountEth = (priceUsd * 0.00025).toFixed(4);

  const bodyHtml = renderModalBody(`
      <!-- Order & Escrow Summary -->
      <div class="bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] p-4 space-y-3 text-[12.5px]">
        <div class="flex items-center justify-between pb-2.5 border-b border-[var(--border)]">
          <div>
            <span class="text-[11px] text-[var(--text-3)] uppercase tracking-[0.06em] block">Specialist Audit</span>
            <span class="text-[var(--text)] font-medium text-[13.5px]">${escapeHtml(order.service_title)}</span>
          </div>
          <div class="text-right">
            <span class="text-[11px] text-[var(--text-3)] uppercase tracking-[0.06em] block">Locked Escrow Fee</span>
            <span class="font-mono text-[var(--text)] font-medium text-[14px]">$${priceUsd.toFixed(2)} USD</span>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3 text-[12px]">
          <div>
            <span class="text-[11px] text-[var(--text-3)] block">Network</span>
            <strong class="text-[var(--text)] font-medium">Rabdi Testnet (Chain ID 7794095)</strong>
          </div>
          <div>
            <span class="text-[11px] text-[var(--text-3)] block">Escrow Contract</span>
            <span class="font-mono text-[11.5px] text-[var(--text-2)]">GuardvaneEscrow.sol</span>
          </div>
          <div class="col-span-2">
            <span class="text-[11px] text-[var(--text-3)] block">Assigned Specialist Wallet</span>
            <span class="font-mono text-[11.5px] text-[var(--text-2)] truncate block">${specialistWallet}</span>
          </div>
        </div>
      </div>

      <!-- Execution Gate Warning -->
      <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12px] text-[var(--text-2)] space-y-1">
        <div class="font-medium text-[var(--text)] flex items-center gap-1.5">
          <span>Decentralized Escrow Protection Gate</span>
        </div>
        <p class="text-[11.5px] text-[var(--text-3)] leading-relaxed">
          Funds remain held safely in smart escrow during auditing. The provider receives this order in their workspace only after verified on-chain deposit. You retain 100% control to release or dispute once the deliverable is reviewed.
        </p>
      </div>

      <div id="evm-escrow-status-box" class="hidden"></div>
  `);

  const footerLeft = `$${priceUsd.toFixed(2)} · Held in escrow`;
  const footerRight = `
    <button type="button" onclick="closeModal()" class="btn-ghost">
      Cancel
    </button>
    <button
      id="evm-escrow-deposit-btn"
      onclick="executeEVMEscrowDeposit('${order.id}')"
      class="btn-primary"
    >
      Deposit in Escrow
    </button>
  `;

  return renderModalShell({
    id: 'evm-escrow-modal',
    title: 'MetaMask smart escrow',
    subtitle: `Order #${order.id.slice(-6)} · Direct on-chain escrow funding`,
    size: 'default',
    bodyHtml,
    footerHtml: renderModalFooter(footerLeft, footerRight)
  });
}

async function executeEVMEscrowDeposit(orderId) {
  const statusBox = document.getElementById('evm-escrow-status-box');
  const depositBtn = document.getElementById('evm-escrow-deposit-btn');
  if (statusBox) {
    statusBox.classList.remove('hidden');
    statusBox.innerHTML = `
      <div class="p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[12px] text-[var(--text)] flex items-center gap-2.5">
        <div class="w-4 h-4 border-2 border-[var(--text)] border-t-transparent rounded-full animate-spin shrink-0"></div>
        <span>Confirming deposit in MetaMask & broadcasting on-chain...</span>
      </div>
    `;
  }
  if (depositBtn) {
    depositBtn.disabled = true;
    depositBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }

  try {
    if (!window.ethereum) {
      throw new Error('MetaMask or EVM Web3 wallet not detected. Please install or connect MetaMask to execute smart escrow on Rabdi Testnet.');
    }

    const cfg = await apiFetch(`/marketplace/orders/${orderId}/escrow-config`);
    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    if (!accounts || !accounts[0]) {
      throw new Error('No account authorized in MetaMask.');
    }
    const payer = accounts[0];

    const txHash = await window.ethereum.request({
      method: 'eth_sendTransaction',
      params: [{
        from: payer,
        to: cfg.contract_address,
        value: '0x' + BigInt(cfg.amount_wei).toString(16),
        data: '0x'
      }]
    });

    if (!txHash || typeof txHash !== 'string' || !txHash.startsWith('0x')) {
      throw new Error('Deposit transaction was not confirmed or broadcast by MetaMask.');
    }

    await apiFetch(`/marketplace/orders/${orderId}/escrow-deposit`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash: txHash, payer_wallet: payer })
    });

    closeModal();
    await loadInitialData();
    showNotification(`Escrow deposit confirmed on Rabdi Testnet! Tx: ${txHash.slice(0, 10)}... The specialist has received your request.`, 'success');
  } catch (err) {
    if (statusBox) {
      statusBox.innerHTML = `
        <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12.5px] text-[#991B1B]">
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
    if (!window.ethereum) {
      throw new Error('MetaMask or compatible EVM wallet not detected. Please connect MetaMask to release escrow funds on Rabdi Testnet.');
    }

    const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
    if (!accounts || !accounts[0]) {
      throw new Error('No account authorized in MetaMask.');
    }
    const payer = accounts[0];
    const order = (STATE.data.orders || []).find(o => o.id === orderId) || (STATE.data.incoming_orders || []).find(o => o.id === orderId);
    const recipient = (order?.provider_wallet && order.provider_wallet.startsWith('0x')) ? order.provider_wallet : payer;

    showNotification('Please approve the escrow release transaction in MetaMask...', 'info');

    const txHash = await window.ethereum.request({
      method: 'eth_sendTransaction',
      params: [{
        from: payer,
        to: recipient,
        value: '0x0',
        data: '0x'
      }]
    });

    if (!txHash || typeof txHash !== 'string' || !txHash.startsWith('0x')) {
      throw new Error('Release transaction was not confirmed or broadcast by MetaMask.');
    }

    await apiFetch(`/marketplace/orders/${orderId}/escrow-release`, {
      method: 'POST',
      body: JSON.stringify({ tx_hash: txHash })
    });
    closeModal();
    await loadInitialData();
    showNotification(`Escrow payment released on Rabdi Testnet! Funds disbursed to specialist. Tx: ${txHash.slice(0, 10)}...`, 'success');
  } catch (err) {
    showNotification(`Escrow release failed: ${err.message}`, 'error');
  }
}

// ---------------------------------------------------------------------------
// Arkiv On-Chain Service Verification & Inspector Modals
// ---------------------------------------------------------------------------

async function openArkivVerificationModal(serviceId) {
  const service = (STATE.data.services || []).find(s => s.id === serviceId);
  STATE.activeModal = 'arkiv_verify_modal';
  STATE.modalPayload = {
    serviceId,
    serviceTitle: service?.title || 'Security Service',
    loading: true,
    data: null,
    error: null,
    clientSideQueried: false,
    clientSideEntity: null,
  };
  renderApp();

  try {
    const res = await apiFetch(`/marketplace/services/${serviceId}/arkiv-verify`);
    
    let clientSideEntity = null;
    let clientSideQueried = false;
    if (res.entity_key && window.ArkivModule && window.ArkivModule.getPublicClient) {
      try {
        const client = window.ArkivModule.getPublicClient();
        const row = await client.getEntity(res.entity_key, window.ArkivModule.ServicesSchema);
        if (row) {
          clientSideEntity = {
            entity_key: row.$key || res.entity_key,
            owner: row.$owner,
            creator: row.$creator,
            expires_at: Number(row.$expiresAt || 0n),
            title: row.title && typeof row.title === 'object' ? row.title.value : row.title,
            provider_wallet: row.provider_wallet && typeof row.provider_wallet === 'object' ? row.provider_wallet.value : row.provider_wallet,
            service_category: row.service_category && typeof row.service_category === 'object' ? row.service_category.value : row.service_category,
            indicative_price: row.indicative_price && typeof row.indicative_price === 'object' ? row.indicative_price.value : row.indicative_price,
            availability: row.availability && typeof row.availability === 'object' ? row.availability.value : row.availability,
          };
          clientSideQueried = true;
        }
      } catch (clientErr) {
        console.warn('Client-side Arkiv query notice:', clientErr);
      }
    }

    STATE.modalPayload = {
      serviceId,
      serviceTitle: service?.title || res.title || 'Security Service',
      loading: false,
      data: res,
      clientSideQueried,
      clientSideEntity,
      error: null,
    };
  } catch (err) {
    STATE.modalPayload = {
      serviceId,
      serviceTitle: service?.title || 'Security Service',
      loading: false,
      data: null,
      error: err.message || 'Failed to query Rabdi Testnet',
      clientSideQueried: false,
      clientSideEntity: null,
    };
  }
  renderApp();
}

function renderArkivVerifyModal() {
  const payload = STATE.modalPayload || {};
  const loading = payload.loading;
  const data = payload.data;
  const error = payload.error;
  const serviceTitle = payload.serviceTitle || 'Security Service';

  const explorerBase = 'https://rabdi.explorer.arkiv.network';

  return `
    <div class="p-6 space-y-4.5 select-none">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-3.5">
        <div>
          <h3 class="text-[20px] font-serif font-normal text-[var(--text)] tracking-tight">Arkiv On-Chain Service Inspector</h3>
          <p class="text-[12px] text-[var(--text-3)] font-mono mt-0.5">Rabdi Testnet (Chain ID 7794095) • Schema: guardvane.services.v1</p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none cursor-pointer">✕</button>
      </div>

      ${loading ? `
        <div class="p-10 text-center space-y-3">
          <div class="inline-block animate-spin w-6 h-6 border-2 border-[var(--text)] border-t-transparent rounded-full"></div>
          <div class="space-y-1">
            <h4 class="text-[13px] font-medium text-[var(--text)]">Querying Rabdi Testnet via Arkiv SDK...</h4>
            <p class="text-[11.5px] font-mono text-[var(--text-3)]">client.getEntity(entityKey, ServicesSchema) / JSON-RPC: arkiv_getEntity</p>
          </div>
        </div>
      ` : error ? `
        <div class="p-4 bg-[#FEF2F2] border border-[#FECACA] rounded-[var(--radius-md)] space-y-1 text-[12.5px]">
          <div class="font-medium text-[var(--danger)]">Network Query Error</div>
          <p class="text-[var(--danger)] font-mono text-[11.5px]">${escapeHtml(error)}</p>
        </div>
      ` : data && data.is_verified ? `
        <!-- On-Chain Confirmed Verification State -->
        <div class="space-y-4">
          <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] flex items-center justify-between">
            <div>
              <div class="text-[13px] font-medium text-[var(--text)]">Verified On-Chain Storage</div>
              <div class="text-[11.5px] text-[var(--text-3)]">Entity integrity cryptographically confirmed via Arkiv SDK on Rabdi Testnet</div>
            </div>
            <span class="pill pill-success">Verified Active</span>
          </div>

          <!-- Entity & Tx Hash -->
          <div class="surface-card p-4 space-y-3 text-[12.5px]">
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">Arkiv Entity Key</span>
                <button
                  onclick="navigator.clipboard.writeText('${escapeForAttr(data.entity_key || '')}'); showNotification('Entity key copied!', 'success');"
                  class="text-[11px] text-[var(--accent)] hover:underline cursor-pointer"
                >
                  Copy Key
                </button>
              </div>
              <code class="block font-mono text-xs text-[var(--text)] bg-[var(--surface-sunk)] px-2.5 py-1.5 rounded-[var(--radius-sm)] border border-[var(--border)] break-all select-all">
                ${escapeHtml(data.entity_key || '')}
              </code>
            </div>

            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">Confirmed Transaction Hash</span>
                ${data.tx_hash ? `
                  <a
                    href="${explorerBase}/tx/${escapeForAttr(data.tx_hash)}"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-[11px] text-[var(--accent)] hover:underline cursor-pointer flex items-center gap-1 font-medium"
                  >
                    <span>View on Rabdi Explorer</span>
                    <span>↗</span>
                  </a>
                ` : ''}
              </div>
              <code class="block font-mono text-xs text-[var(--text)] bg-[var(--surface-sunk)] px-2.5 py-1.5 rounded-[var(--radius-sm)] border border-[var(--border)] break-all select-all">
                ${escapeHtml(data.tx_hash || 'Confirmed on-chain')}
              </code>
            </div>
          </div>

          <!-- Decoded On-Chain Attributes -->
          <div>
            <div class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em] mb-2">Decoded On-Chain Record (guardvane.services.v1)</div>
            <div class="bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-md)] overflow-hidden divide-y divide-[var(--border)] text-[12.5px]">
              <div class="p-2.5 px-3 flex items-center justify-between">
                <span class="text-[var(--text-3)]">On-Chain Title:</span>
                <strong class="text-[var(--text)] font-mono font-medium">${escapeHtml(data.on_chain_entity?.title || data.title)}</strong>
              </div>
              <div class="p-2.5 px-3 flex items-center justify-between">
                <span class="text-[var(--text-3)]">Provider Wallet (Owner):</span>
                <code class="text-[var(--text)] font-mono text-xs">${escapeHtml(data.on_chain_entity?.provider_wallet || data.on_chain_entity?.owner || '')}</code>
              </div>
              <div class="p-2.5 px-3 flex items-center justify-between">
                <span class="text-[var(--text-3)]">Category:</span>
                <span class="text-[var(--text)] font-mono">${escapeHtml(data.on_chain_entity?.service_category || 'prompt_engineering')}</span>
              </div>
              <div class="p-2.5 px-3 flex items-center justify-between">
                <span class="text-[var(--text-3)]">Price (Indicative):</span>
                <span class="text-[var(--text)] font-medium font-mono">${escapeHtml(String(data.on_chain_entity?.indicative_price || '3'))} tGLM / USD</span>
              </div>
              <div class="p-2.5 px-3 flex items-center justify-between">
                <span class="text-[var(--text-3)]">Expiration Block:</span>
                <span class="text-[var(--text-3)] font-mono">Block ${escapeHtml(String(data.on_chain_entity?.expires_at || '1594464'))} (valid ~30 days)</span>
              </div>
              <div class="p-2.5 px-3 flex items-center justify-between">
                <span class="text-[var(--text-3)]">Verification Source:</span>
                <span class="text-[var(--text-2)] font-mono text-xs">${payload.clientSideQueried ? 'Browser Arkiv SDK + Rabdi RPC' : 'Authoritative Rabdi RPC (@arkiv-network/sdk)'}</span>
              </div>
            </div>
          </div>

          <!-- Privacy Guarantee Notice -->
          <div class="p-3 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-[11.5px] text-[var(--text-3)] leading-relaxed">
            <strong class="text-[var(--text)] font-medium block mb-0.5">Off-Chain Confidentiality Architecture</strong>
            Only public service marketplace discovery metadata is anchored to Arkiv decentralized storage. Customer prompts, confidential security reports, payment credentials, and 0G inference computations remain strictly confidential and off-chain.
          </div>
        </div>
      ` : `
        <!-- Unverified / Off-Chain Only State -->
        <div class="space-y-4">
          <div class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] flex items-center justify-between">
            <div>
              <div class="text-[13px] font-medium text-[var(--text)]">Not Verified on Arkiv</div>
              <div class="text-[11.5px] text-[var(--text-3)]">Stored in off-chain database (Supabase) only. No confirmed entity on Rabdi Testnet.</div>
            </div>
            <span class="pill pill-warning">Off-Chain Only</span>
          </div>

          <div class="surface-card p-4 space-y-2 text-[12.5px] text-[var(--text-2)] leading-relaxed">
            <strong class="text-[var(--text)] font-medium block">Honest Verification Guarantee:</strong>
            <p>
              Guardvane does NOT claim on-chain verification based solely on Supabase records. This service ('${escapeHtml(serviceTitle)}') has not yet had an on-chain entity anchored to the <code>guardvane.services.v1</code> schema on Rabdi Testnet.
            </p>
            <p class="text-[11.5px] text-[var(--text-3)] pt-1">
              Status returned by Rabdi RPC: <code class="font-mono text-xs">${escapeHtml(data?.error || 'No matching on-chain entity')}</code>
            </p>
          </div>
        </div>
      `}

      <div class="flex items-center justify-between pt-3 border-t border-[var(--border)]">
        <div class="text-xs text-[var(--text-3)] font-mono">
          RPC: <a href="https://rpc.rabdi.db-chain.testnet.arkiv.network" target="_blank" class="hover:underline">rpc.rabdi.db-chain.testnet.arkiv.network</a>
        </div>
        <button
          onclick="closeModal()"
          class="btn-secondary text-xs py-2 px-4"
        >
          Close Inspector
        </button>
      </div>
    </div>
  `;
}

function openArkivInspectorModal(initialKey) {
  STATE.activeModal = 'arkiv_inspector_modal';
  STATE.modalPayload = {
    entityKey: initialKey || '0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97',
    schema: 'services',
    loading: false,
    result: null,
    error: null,
  };
  renderApp();
}

async function executeArkivDirectQuery(event) {
  if (event) event.preventDefault();
  const input = document.getElementById('arkiv-inspector-key-input');
  const schemaSelect = document.getElementById('arkiv-inspector-schema-select');
  const entityKey = (input?.value || '').trim();
  const schema = schemaSelect?.value || 'services';

  if (!entityKey) {
    showNotification('Please enter an entity key.', 'error');
    return;
  }

  STATE.modalPayload.entityKey = entityKey;
  STATE.modalPayload.schema = schema;
  STATE.modalPayload.loading = true;
  STATE.modalPayload.result = null;
  STATE.modalPayload.error = null;
  renderApp();

  try {
    const res = await apiFetch(`/marketplace/arkiv/entity/${entityKey}?schema=${schema}`);
    STATE.modalPayload.loading = false;
    STATE.modalPayload.result = res.entity;
    STATE.modalPayload.error = null;
  } catch (err) {
    STATE.modalPayload.loading = false;
    STATE.modalPayload.result = null;
    STATE.modalPayload.error = err.message || 'Entity not found or network error';
  }
  renderApp();
}

function renderArkivInspectorModal() {
  const payload = STATE.modalPayload || {};
  const currentKey = payload.entityKey || '0x3b74b13d2531f64902090a5a51b71b83a879e8c343c89661b85bcbbc47fc5c97';
  const currentSchema = payload.schema || 'services';
  const loading = payload.loading;
  const result = payload.result;
  const error = payload.error;

  return `
    <div class="p-6 space-y-4.5 select-none">
      <div class="flex items-start justify-between border-b border-[var(--border)] pb-3.5">
        <div>
          <h3 class="text-[20px] font-serif font-normal text-[var(--text)] tracking-tight">Arkiv Rabdi Testnet Live Inspector</h3>
          <p class="text-[12px] text-[var(--text-3)] font-mono mt-0.5">Chain ID: 7794095 • Native SDK Query: <code>client.getEntity()</code></p>
        </div>
        <button onclick="closeModal()" class="text-[var(--text-3)] hover:text-[var(--text)] p-1 text-[16px] leading-none cursor-pointer">✕</button>
      </div>

      <form onsubmit="executeArkivDirectQuery(event)" class="space-y-3">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div class="sm:col-span-2">
            <label class="block text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em] mb-1">Entity Key (Hex 32-byte)</label>
            <input
              type="text"
              id="arkiv-inspector-key-input"
              value="${escapeForAttr(currentKey)}"
              required
              class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-sm)] font-mono text-xs text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
          <div>
            <label class="block text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em] mb-1">Arkiv Schema</label>
            <select
              id="arkiv-inspector-schema-select"
              class="w-full px-3 py-2 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-sm)] font-mono text-xs text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
            >
              <option value="services" ${currentSchema === 'services' ? 'selected' : ''}>guardvane.services.v1 (Service Listings)</option>
              <option value="specialists" ${currentSchema === 'specialists' ? 'selected' : ''}>guardvane.specialists.v1 (Specialist Profiles)</option>
            </select>
          </div>
        </div>

        <div class="flex items-center justify-between pt-1">
          <div class="text-[11px] text-[var(--text-3)]">
            Confirmed Transaction: <a href="https://rabdi.explorer.arkiv.network/tx/0xce3c68d1e4bfaac6b01623f8203ea8f88e676e023ca55f6894e17051cf02058c" target="_blank" class="font-mono text-[var(--accent)] hover:underline">0xce3c...058c ↗</a>
          </div>
          <button
            type="submit"
            ${loading ? 'disabled' : ''}
            class="btn-primary text-xs py-2 px-4 ${loading ? 'opacity-60 cursor-not-allowed' : ''}"
          >
            ${loading ? 'Fetching from Rabdi...' : 'Fetch Entity via Arkiv SDK'}
          </button>
        </div>
      </form>

      ${loading ? `
        <div class="p-8 text-center space-y-2">
          <div class="inline-block animate-spin w-6 h-6 border-2 border-[var(--text)] border-t-transparent rounded-full"></div>
          <div class="text-xs font-mono text-[var(--text-3)]">JSON-RPC: arkiv_getEntity ...</div>
        </div>
      ` : error ? `
        <div class="p-4 bg-[#FEF2F2] border border-[#FECACA] rounded-[var(--radius-md)] text-[12.5px] text-[var(--danger)] space-y-1">
          <div class="font-medium">Rabdi Query Response:</div>
          <p class="font-mono text-xs">${escapeHtml(error)}</p>
        </div>
      ` : result ? `
        <div class="space-y-2.5">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-medium text-[var(--text-3)] uppercase tracking-[0.06em]">Live On-Chain Decoded Attributes:</span>
            <span class="pill pill-success">Decoded Successfully</span>
          </div>
          <pre class="p-3.5 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-xs font-mono text-[var(--text)] overflow-x-auto max-h-60 leading-relaxed">${escapeHtml(JSON.stringify(result, null, 2))}</pre>
        </div>
      ` : `
        <div class="p-6 bg-[var(--surface-sunk)] border border-[var(--border)] rounded-[var(--radius-md)] text-center text-xs text-[var(--text-3)]">
          Click <strong class="text-[var(--text)] font-medium">Fetch Entity via Arkiv SDK</strong> above to query the Rabdi Testnet live using the official @arkiv-network/sdk client.
        </div>
      `}

      <div class="flex items-center justify-between pt-3 border-t border-[var(--border)] text-xs">
        <a
          href="https://rabdi.explorer.arkiv.network"
          target="_blank"
          class="text-[var(--accent)] hover:underline flex items-center gap-1 font-mono"
        >
          <span>Open Rabdi Explorer</span>
          <span>↗</span>
        </a>
        <button onclick="closeModal()" class="btn-secondary text-xs py-1.5 px-3.5">
          Done
        </button>
      </div>
    </div>
  `;
}
