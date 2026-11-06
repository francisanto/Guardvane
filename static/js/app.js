/**
 * Guardvane — AI Security Platform & OpiHub Marketplace
 * Developer Console Layout & Green Palette: #176B45 (primary), #EAF5EE (surface/active), #F7F9F7 (background)
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
  loading: false
};

// ---------------------------------------------------------------------------
// API Helpers & Authentication Actions
// ---------------------------------------------------------------------------

async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': STATE.user.id || STATE.auth.walletAddress || 'guest',
    'X-User-Role': STATE.user.role || 'customer',
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
      throw new Error(errData.detail || `API error (${res.status})`);
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
      const savedDisplayName = (typeof localStorage !== 'undefined') ? localStorage.getItem('guardvane_display_name') : null;
      STATE.user.name = savedDisplayName || data.display_name || (data.wallet_address.substring(0, 6) + '...' + data.wallet_address.substring(data.wallet_address.length - 4));
      STATE.user.role = (data.roles && data.roles.includes('provider')) ? 'provider' : (data.roles[0] || 'customer');
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
    STATE.user.role = verifyData.user.roles?.[0] || 'customer';
    STATE.auth.error = null;
    STATE.auth.statusText = '';

    await loadInitialData();
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
  renderApp();
}

function continueAsGuest() {
  STATE.auth.isAuthenticated = true;
  STATE.auth.guestMode = true;
  STATE.auth.walletAddress = '0xfrancis...dev';
  STATE.user.id = 'francis';
  STATE.user.name = 'Francis (Guest)';
  STATE.user.role = 'customer';
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
    alert('MetaMask is not installed. Please install MetaMask to connect to Rabdi Testnet.');
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
    alert('Could not switch to Rabdi Testnet: ' + (err.message || err));
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
    if (STATE.auth.walletAddress && Array.isArray(providers)) {
      const myProv = providers.find(p => p.wallet_address && p.wallet_address.toLowerCase() === STATE.auth.walletAddress.toLowerCase());
      if (myProv) {
        STATE.user.activeProviderId = myProv.id;
        STATE.user.role = 'provider';
      }
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
  STATE.activeView = view;
  if (view === 'provider_detail') {
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

function openModal(modalType, payload = null) {
  STATE.activeModal = modalType;
  STATE.modalPayload = payload;
  renderApp();
}

function closeModal() {
  STATE.activeModal = null;
  STATE.modalPayload = null;
  renderApp();
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
    <div class="flex h-screen overflow-hidden bg-[#F7F9F7] text-[#202820]">
      <!-- Left Sidebar -->
      ${renderSidebar()}

      <!-- Main Column -->
      <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
        <!-- Top Navigation Bar -->
        ${renderTopbar()}

        <!-- Page Content View -->
        <main class="flex-1 overflow-y-auto px-8 py-7" id="main-content">
          <div class="max-w-7xl mx-auto space-y-6">
            ${renderCurrentView()}
          </div>
        </main>
      </div>
    </div>

    <!-- Active Modal Container -->
    ${STATE.activeModal ? renderModalContainer() : ''}
  `;

  // Attach search shortcut listener if not attached
  if (!window._shortcutListenerAttached) {
    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('topbar-search-input');
        if (searchInput) searchInput.focus();
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
    <div class="min-h-screen bg-[#F7F9F7] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 select-none">
      <div class="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <!-- Shield Brand Icon -->
        <div class="mx-auto w-14 h-14 rounded-2xl bg-[#176B45] text-white flex items-center justify-center shadow-md">
          <svg class="w-8 h-8 text-emerald-100" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <h1 class="mt-4 text-2xl font-bold tracking-tight text-[#202820]">Guardvane</h1>
        <p class="mt-1.5 text-[13.5px] text-[#627566] max-w-sm mx-auto">
          AI Security Platform
        </p>
      </div>

      <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div class="bg-white py-8 px-6 shadow-sm border border-[#E2E9E3] rounded-2xl sm:px-10 space-y-5">
          
          <!-- Error Alert Banner -->
          ${STATE.auth.error ? `
            <div class="p-3.5 rounded-lg bg-[#FDF2F2] border border-[#F8B4B4] text-[13px] text-[#9B1C1C] flex items-start gap-2.5">
              <svg class="w-5 h-5 shrink-0 text-[#E02424] mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>${escapeHtml(STATE.auth.error)}</span>
            </div>
          ` : ''}

          <!-- Signing / Loading State -->
          ${STATE.auth.loading ? `
            <div class="p-5 rounded-xl bg-[#EAF5EE] border border-[#CDE5D5] text-center space-y-2.5">
              <div class="w-7 h-7 border-3 border-[#176B45] border-t-transparent rounded-full animate-spin mx-auto"></div>
              <p class="text-[13.5px] font-semibold text-[#176B45]">${escapeHtml(STATE.auth.statusText || 'Connecting...')}</p>
              <p class="text-[11.5px] text-[#627566]">Please confirm the signature in your wallet.</p>
            </div>
          ` : `
            <!-- Connect Wallet Action Button -->
            <button
              onclick="connectAndSignWithMetaMask()"
              class="w-full flex items-center justify-center gap-3 px-4 py-3.5 bg-[#176B45] hover:bg-[#115638] text-white text-[14px] font-semibold rounded-xl shadow-xs transition-smooth cursor-pointer"
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
// Sidebar Component
// ---------------------------------------------------------------------------

function renderSidebar() {
  const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
  const myProvider = STATE.data.providers.find(p =>
    (p.wallet_address && p.wallet_address.toLowerCase() === userWallet) ||
    p.id === STATE.user.activeProviderId
  );
  const isRegisteredProvider = !!myProvider;
  const shortAddr = STATE.user.name
    ? STATE.user.name
    : (STATE.auth.walletAddress
        ? (STATE.auth.walletAddress.substring(0, 6) + '...' + STATE.auth.walletAddress.substring(STATE.auth.walletAddress.length - 4))
        : 'Account');

  return `
    <aside class="w-64 bg-[#FAFBF9] border-r border-[#E2E9E3] flex flex-col justify-between shrink-0 select-none">
      <!-- Top Brand & Nav -->
      <div class="flex flex-col">
        <!-- Navigation Section: WORKSPACE -->
        <div class="px-3 py-4 space-y-1">
          <div class="px-3 pb-1.5 text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Workspace</div>
          
          <button onclick="navigateTo('dashboard')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'dashboard' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            Dashboard
          </button>

          <button onclick="navigateTo('opihub')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'opihub' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            OpiHub
          </button>

          <button onclick="navigateTo('arkiv_tasks')" class="w-full flex items-center justify-between px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'arkiv_tasks' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <div class="flex items-center gap-3">
              <svg class="w-4 h-4 text-[#176B45]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              <span>Arkiv Task Board</span>
            </div>
            <span class="text-[10px] bg-[#EAF5EE] text-[#176B45] font-mono font-semibold px-2 py-0.5 rounded">RABDI</span>
          </button>

          <button onclick="navigateTo('my_prompts')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'my_prompts' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
            My Prompts
            <span class="ml-auto text-[11px] bg-[#EAF5EE] text-[#176B45] font-semibold px-2 py-0.5 rounded-full">${STATE.data.prompts.length}</span>
          </button>

          <button onclick="navigateTo('my_requests')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'my_requests' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
            My Requests
            <span class="ml-auto text-[11px] bg-[#E2E9E3] text-[#445246] font-semibold px-2 py-0.5 rounded-full">${STATE.data.orders.length}</span>
          </button>

          <button onclick="navigateTo('security_reports')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'security_reports' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Security Reports
            <span class="ml-auto text-[11px] bg-[#EAF5EE] text-[#176B45] font-semibold px-2 py-0.5 rounded-full">${STATE.data.reports.length}</span>
          </button>
        </div>

        <!-- Navigation Section: PROVIDER -->
        <div class="px-3 py-3 space-y-1 border-t border-[#E2E9E3]/70">
          <div class="px-3 py-1.5 text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Provider</div>

          <button onclick="navigateTo('become_provider')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'become_provider' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#2FA36B]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Become a Provider
          </button>

          <button onclick="navigateTo('provider_workspace')" class="w-full flex items-center justify-between px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'provider_workspace' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <div class="flex items-center gap-3">
              <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <span>Provider Workspace</span>
            </div>
            ${isRegisteredProvider ? '<span class="text-[10px] bg-[#EAF5EE] text-[#176B45] font-semibold px-2 py-0.5 rounded font-mono">PROVIDER</span>' : ''}
          </button>
        </div>

        <!-- Navigation Section: ACCOUNT -->
        <div class="px-3 py-3 space-y-1 border-t border-[#E2E9E3]/70">
          <div class="px-3 py-1.5 text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Account</div>

          <button onclick="openModal('wallet_modal')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820] transition-smooth">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
            Wallet
          </button>

          <button onclick="openModal('settings_modal')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820] transition-smooth">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings
          </button>
        </div>
      </div>

      <!-- Bottom User Profile -->
      <div class="p-4 border-t border-[#E2E9E3] bg-[#F7F9F7]/80">
        <!-- User Identity Row -->
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-[#EAF5EE] border border-[#CDE5D5] flex items-center justify-center text-[#176B45] shrink-0">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div class="flex flex-col min-w-0">
            <span class="text-[13px] font-mono font-medium text-[#202820] truncate">${shortAddr}</span>
            <span class="text-[11px] text-[#627566] truncate">${isRegisteredProvider ? 'Registered Provider' : 'Connected Wallet'}</span>
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
  const isRabdi = STATE.network && STATE.network.isRabdi;
  const chainId = STATE.network && STATE.network.chainId;

  return `
    <header class="h-16 border-b border-[#E2E9E3] bg-[#FAFBF9] px-8 flex items-center justify-between shrink-0 select-none">
      <!-- Left: Rabdi Network Status Pill -->
      <div class="flex items-center gap-3">
        ${isRabdi ? `
          <div class="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-[#EAF5EE] text-[#176B45] border border-[#CDE5D5]">
            <span class="w-2 h-2 rounded-full bg-[#2FA36B] animate-pulse"></span>
            <span>Rabdi Testnet (7794095)</span>
            ${(STATE.arkiv && STATE.arkiv.status && STATE.arkiv.status.current_block) ? `
              <span class="text-[11px] text-[#627566] pl-1 border-l border-[#CDE5D5]">#${STATE.arkiv.status.current_block}</span>
            ` : ''}
          </div>
        ` : `
          <button
            onclick="handleSwitchToRabdi()"
            title="Click to switch MetaMask to Rabdi Testnet"
            class="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] hover:bg-[#FDE68A] transition-smooth cursor-pointer"
          >
            <span class="w-2 h-2 rounded-full bg-[#D97706] animate-ping"></span>
            <span>${chainId ? `Chain ${chainId}: Switch to Rabdi (7794095)` : 'Switch to Rabdi Testnet'}</span>
          </button>
        `}
      </div>

      <!-- Top Right Controls -->
      <div class="flex items-center gap-3">
        <!-- Wallet Badge -->
        ${STATE.auth.walletAddress ? `
          <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium bg-[#EAF5EE] text-[#176B45] border border-[#CDE5D5]">
            <span class="w-2 h-2 rounded-full bg-[#2FA36B] animate-pulse"></span>
            <span>${STATE.auth.walletAddress.substring(0, 6)}...${STATE.auth.walletAddress.substring(STATE.auth.walletAddress.length - 4)}</span>
          </div>
        ` : ''}

        <!-- Logout Button -->
        <button
          onclick="handleLogout()"
          title="Sign out of Guardvane"
          class="px-2.5 py-1 text-xs text-[#627566] hover:text-[#C53030] hover:bg-[#FDE8E8] rounded-md transition-smooth font-medium cursor-pointer"
        >
          Logout
        </button>
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
        <div class="w-8 h-8 border-3 border-[#176B45] border-t-transparent rounded-full animate-spin"></div>
        <p class="text-[13px] text-[#627566]">Loading Guardvane data...</p>
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
// 1. Dashboard Home Page (Cleaned & Simplified)
// ---------------------------------------------------------------------------

function renderDashboardView() {
  const stats = STATE.data.stats || {};
  const savedPromptsCount = stats.saved_prompts_count ?? STATE.data.prompts.length;
  const activeRequestsCount = stats.active_requests_count ?? STATE.data.orders.filter(o => ['requested', 'accepted', 'in_progress'].includes(o.status)).length;
  const completedAuditsCount = stats.completed_audits_count ?? stats.completed_reviews_count ?? STATE.data.reports.length;
  const availableProvidersCount = stats.available_providers_count ?? STATE.data.providers.length;

  const recommendedProviders = STATE.data.providers.slice(0, 3);
  const recentReports = STATE.data.reports.slice(0, 3);
  const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
  const myProvider = STATE.data.providers.find(p =>
    (p.wallet_address && p.wallet_address.toLowerCase() === userWallet) ||
    p.id === STATE.user.activeProviderId
  );
  const displayName = myProvider?.display_name || STATE.user.name || 'Developer';

  return `
    <!-- Top Greeting Header -->
    <!-- Dashboard Top Bar / Actions -->
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">Dashboard</h1>
      <div class="flex items-center gap-3">
        <button onclick="openModal('quick_analyze')" class="px-4 py-2 bg-[#FFFFFF] border border-[#E2E9E3] hover:border-[#CBD7CE] text-[#202820] text-[13.5px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-2">
          <svg class="w-4 h-4 text-[#176B45]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Analyze a Prompt
        </button>
        <button onclick="navigateTo('opihub')" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          Explore OpiHub
        </button>
      </div>
    </div>

    <!-- 4 Clean Metric Cards (Matching Claude Console developer style) -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>Saved Prompts</span>
          <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-medium">Private</span>
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
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>Active Requests</span>
          <span class="text-[11px] bg-[#FEF3C7] text-[#92400E] px-2 py-0.5 rounded font-medium">In Flight</span>
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
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>Completed Audits</span>
          <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-medium">Reports</span>
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
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>Available Providers</span>
          <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-medium">OpiHub</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${availableProvidersCount}</span>
          <span class="text-[12px] text-[#627566]">human & automated</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('opihub')">
          Explore on OpiHub →
        </div>
      </div>
    </div>

    <!-- Recommended Providers Row (Cleaned & Concise) -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-[15px] font-semibold tracking-tight text-[#202820]">Recommended Providers</h2>
        <button onclick="navigateTo('opihub')" class="text-[13px] font-medium text-[#176B45] hover:underline">
          Explore all on OpiHub (${STATE.data.providers.length}) →
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        ${recommendedProviders.map(p => renderCleanProviderCard(p)).join('')}
      </div>
    </div>

    <!-- Two Column: Recent Activity & Recent Reports -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <!-- Recent Activity Feed -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-4">
        <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
          <h3 class="text-[14px] font-semibold text-[#202820]">Recent Activity</h3>
          <span class="text-[12px] text-[#627566] hover:text-[#176B45] cursor-pointer" onclick="navigateTo('my_requests')">View all orders →</span>
        </div>
        <div class="divide-y divide-[#E2E9E3]/70">
          ${renderActivityFeed(stats.recent_activity || [])}
        </div>
      </div>

      <!-- Recent Reports -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-4">
        <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
          <h3 class="text-[14px] font-semibold text-[#202820]">Recent Reports</h3>
          <span class="text-[12px] text-[#627566] hover:text-[#176B45] cursor-pointer" onclick="navigateTo('security_reports')">View all reports →</span>
        </div>
        <div class="space-y-3">
          ${recentReports.length > 0 ? recentReports.map(r => `
            <div class="p-3 rounded border border-[#E2E9E3] bg-[#FAFBF9] flex items-center justify-between">
              <div class="min-w-0 pr-3">
                <div class="font-medium text-[13px] text-[#202820] truncate">${escapeHtml(r.service_title)}</div>
                <div class="text-[11.5px] text-[#627566]">By ${escapeHtml(r.provider_name)} • ${(r.findings || []).length} findings</div>
              </div>
              <button onclick="viewReport('${r.id}')" class="px-2.5 py-1 text-[12px] font-medium bg-white border border-[#E2E9E3] hover:border-[#176B45] text-[#176B45] rounded shrink-0 transition-smooth">
                Inspect Findings
              </button>
            </div>
          `).join('') : `
            <div class="py-6 text-center text-[#627566] text-[13px]">No completed audit reports recorded yet.</div>
          `}
        </div>
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 2. OpiHub Marketplace Discovery Page
// ---------------------------------------------------------------------------

function renderOpiHubView() {
  const categories = [
    { id: 'all', label: 'All Services & Specialists' },
    { id: 'prompt_optimization', label: 'Prompt Optimization' },
    { id: 'prompt_engineering', label: 'Prompt Engineering' },
    { id: 'loop_engineering', label: 'Loop Engineering' },
    { id: 'codebase_security', label: 'Codebase Security Check' },
    { id: 'application_testing', label: 'Application Testing' }
  ];

  const filtered = STATE.data.providers.filter(p => {
    if (STATE.filters.search) {
      const q = STATE.filters.search.toLowerCase();
      const matchName = p.display_name.toLowerCase().includes(q);
      const matchTitle = p.title.toLowerCase().includes(q);
      const matchDesc = p.description.toLowerCase().includes(q);
      const matchSkills = (p.skills || []).some(s => s.toLowerCase().includes(q));
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

  const matchingServices = STATE.data.services.filter(s => {
    if (STATE.filters.category && STATE.filters.category !== 'all') {
      return s.category === STATE.filters.category;
    }
    return true;
  });

  return `
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">OpiHub</h1>
      </div>
    </div>

    <!-- Category Filter Tabs with Authority Indicators -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[#E2E9E3]">
      ${categories.map(c => `
        <button
          onclick="setCategoryFilter('${c.id}')"
          class="px-3.5 py-1.5 rounded-full text-[13px] font-medium whitespace-nowrap transition-smooth flex items-center gap-1.5 ${
            STATE.filters.category === c.id
              ? 'bg-[#176B45] text-white shadow-xs'
              : 'bg-white border border-[#E2E9E3] text-[#445246] hover:bg-[#F0F5F1]'
          }"
        >
          <span>${c.label}</span>
          ${(c.id === 'codebase_security' || c.id === 'application_testing') ? `
            <span class="text-[10px] font-mono px-1.5 py-0.2 rounded ${STATE.filters.category === c.id ? 'bg-white/20 text-white' : 'bg-[#FEF3C7] text-[#92400E]'}">Specialists</span>
          ` : ''}
        </button>
      `).join('')}
    </div>

    <!-- Sub-Filters: Type, Availability, Count -->
    <div class="flex items-center justify-between gap-4 bg-white p-3.5 border border-[#E2E9E3] rounded-lg shadow-xs">
      <div class="flex items-center gap-3">
        <span class="text-[13px] font-medium text-[#445246]">Provider Type:</span>
        <select
          onchange="setProviderTypeFilter(this.value)"
          class="bg-white border border-[#CBD7CE] text-[13.5px] text-[#202820] font-medium rounded-md px-3.5 py-2 min-w-[220px] focus:outline-none focus:border-[#176B45] focus:ring-1 focus:ring-[#176B45] shadow-2xs transition-smooth cursor-pointer"
        >
          <option value="" ${!STATE.filters.providerType ? 'selected' : ''}>All Types (Automated & Specialists)</option>
          <option value="automated" ${STATE.filters.providerType === 'automated' ? 'selected' : ''}>Automated 0G Defense Agent</option>
          <option value="human" ${STATE.filters.providerType === 'human' ? 'selected' : ''}>Human Security Specialists</option>
        </select>
      </div>

      <div class="text-[13px] text-[#627566]">
        Showing <strong class="text-[#202820]">${filtered.length}</strong> providers • <strong class="text-[#202820]">${matchingServices.length}</strong> active offerings
      </div>
    </div>

    <!-- Providers Grid -->
    ${filtered.length > 0 ? `
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        ${filtered.map(p => renderCleanProviderCard(p)).join('')}
      </div>
    ` : `
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-12 text-center space-y-3">
        <div class="w-12 h-12 rounded-full bg-[#EAF5EE] text-[#176B45] flex items-center justify-center mx-auto">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 class="text-[15px] font-semibold text-[#202820]">No providers matched your filter</h3>
        <p class="text-[13px] text-[#627566]">Try clearing your search query or selecting a different category.</p>
        <button onclick="resetFilters()" class="px-3.5 py-1.5 text-[13px] font-medium bg-[#176B45] text-white rounded-md">
          Reset Filters
        </button>
      </div>
    `}
  `;
}

// ---------------------------------------------------------------------------
// 3. Provider Profile Page
// ---------------------------------------------------------------------------

function renderProviderDetailView() {
  const provider = STATE.data.providers.find(p => p.id === STATE.selectedProviderId) || STATE.data.providers[0];
  if (!provider) {
    return `<div class="p-8 text-center">Provider not found. <button onclick="navigateTo('opihub')" class="text-[#176B45] underline">Back to OpiHub</button></div>`;
  }

  const providerServices = STATE.data.services.filter(s => s.provider_id === provider.id);
  const isAutomated = provider.provider_type === 'automated';

  return `
    <!-- Back Link -->
    <div>
      <button onclick="navigateTo('opihub')" class="text-[13px] text-[#176B45] font-medium hover:underline flex items-center gap-1.5">
        ← Back to OpiHub
      </button>
    </div>

    <!-- Provider Header Card -->
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-6 shadow-xs space-y-6">
      <div class="flex items-start justify-between">
        <div class="flex items-start gap-5">
          <img
            src="${provider.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}"
            alt="${provider.display_name}"
            class="w-16 h-16 rounded-lg object-cover border border-[#E2E9E3] shadow-xs shrink-0"
          />
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <h1 class="text-xl font-semibold text-[#202820] tracking-tight">${provider.display_name}</h1>
              ${provider.verified ? `
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#EAF5EE] text-[#176B45] border border-[#C4E4CE]">
                  <svg class="w-3 h-3 fill-current" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  Verified Provider
                </span>
              ` : `
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F7F9F7] text-[#627566] border border-[#E2E9E3]">
                  Registered
                </span>
              `}
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${isAutomated ? 'bg-[#E0E7FF] text-[#3730A3]' : 'bg-[#FEF3C7] text-[#92400E]'}">
                ${isAutomated ? 'Automated AI Security Provider' : 'Human Security Provider'}
              </span>
            </div>
            <p class="text-[13.5px] text-[#445246] font-medium">${provider.title}</p>
            <div class="flex items-center gap-4 text-[12px] text-[#627566] pt-0.5">
              <span>Status: <strong class="text-[#176B45] capitalize">${provider.availability}</strong></span>
              ${provider.wallet_address ? `<span>Wallet: <code class="font-mono text-[#202820]">${provider.wallet_address}</code></span>` : ''}
            </div>
          </div>
        </div>

        <button
          onclick="openModal('request_review', { providerId: '${provider.id}', serviceId: '${providerServices[0]?.id || ''}' })"
          class="px-5 py-2.5 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth"
        >
          Request Review
        </button>
      </div>

      <!-- Description & Genuine Track Record -->
      <div class="border-t border-[#E2E9E3] pt-5 space-y-4">
        <div>
          <h3 class="text-[12.5px] font-semibold text-[#8B9C8E] uppercase tracking-wider">About Provider</h3>
          <p class="text-[13.5px] text-[#333E35] leading-relaxed mt-1.5">${provider.description}</p>
        </div>

        <!-- Skills Chips -->
        <div>
          <h3 class="text-[12.5px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Capabilities & Skills</h3>
          <div class="flex flex-wrap gap-1.5 mt-2">
            ${provider.skills.map(s => `
              <span class="px-2.5 py-1 bg-[#F7F9F7] border border-[#E2E9E3] text-[#202820] text-[12px] font-medium rounded-md">
                ${s}
              </span>
            `).join('')}
          </div>
        </div>

        <!-- Real Track Record Metrics -->
        <div class="bg-[#FAFBF9] border border-[#E2E9E3] rounded-md p-4">
          <div class="text-[11.5px] font-semibold text-[#176B45] uppercase tracking-wider mb-2">Track Record & Performance</div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${provider.reputation_metadata.audits_completed || 0}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Audits Delivered</div>
            </div>
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${provider.reputation_metadata.avg_turnaround_hours ? `${provider.reputation_metadata.avg_turnaround_hours}h` : (provider.reputation_metadata.avg_turnaround_sec ? `${provider.reputation_metadata.avg_turnaround_sec}s` : 'Instant')}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Turnaround Time</div>
            </div>
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${isAutomated ? 'Autonomous' : 'Manual'}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Execution Type</div>
            </div>
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${provider.portfolio_url ? 'Verified' : 'Active'}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Profile Status</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Published Services List -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-[15px] font-semibold tracking-tight text-[#202820]">Published Services (${providerServices.length})</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        ${providerServices.map(s => renderCleanServiceCard(s, false)).join('')}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 4. Become a Provider Page
// ---------------------------------------------------------------------------

function renderBecomeProviderView() {
  return `
    <div class="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">Become a Provider</h1>
      </div>

      <form id="become-provider-form" onsubmit="handleBecomeProvider(event)" class="bg-white border border-[#E2E9E3] rounded-lg p-7 shadow-xs space-y-6">
        <!-- Section 1: Provider Identity -->
        <div class="space-y-4">
          <h3 class="text-[13.5px] font-semibold text-[#176B45] border-b border-[#E2E9E3] pb-2">1. Provider Identity</h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Provider Name *</label>
              <input type="text" name="display_name" required placeholder="e.g. Dr. Maya Patel or GuardAgent-X" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Professional Title *</label>
              <input type="text" name="title" required placeholder="e.g. Senior LLM Red Teamer & Jailbreak Analyst" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Provider Type *</label>
              <select name="provider_type" id="form-provider-type" onchange="toggleAutomatedFields(this.value)" class="w-full px-3.5 py-2.5 bg-white border border-[#CBD7CE] rounded-md text-[13.5px] font-medium text-[#202820] focus:outline-none focus:border-[#176B45] focus:ring-1 focus:ring-[#176B45] shadow-2xs transition-smooth cursor-pointer">
                <option value="human">Human Security Provider</option>
                <option value="automated">Automated AI Security Provider</option>
              </select>
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Wallet Address</label>
              <input type="text" name="wallet_address" value="${escapeForAttr(STATE.auth.walletAddress || '')}" placeholder="0x..." class="w-full px-3 py-2 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md text-[13.5px] font-mono focus:outline-none focus:border-[#176B45]" />
              <p class="text-[11px] text-[#627566] mt-1">Audit requests and review orders from clients will be linked to this wallet.</p>
            </div>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Provider Bio / Description *</label>
            <textarea name="description" rows="3" required placeholder="Describe your security focus, background, attack surfaces tested, and tooling..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]"></textarea>
          </div>
        </div>

        <!-- Section 2: Automated Provider Configuration (Conditional) -->
        <div id="automated-provider-fields" class="space-y-4 hidden p-4 bg-[#F7F9F7] rounded-md border border-[#E2E9E3]">
          <h3 class="text-[13px] font-semibold text-[#176B45]">Automated Agent Configuration</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[12.5px] font-medium text-[#202820] mb-1">API Endpoint</label>
              <input type="url" name="endpoint_url" placeholder="https://api.yourdomain.com/v1/scan" class="w-full px-3 py-2 bg-white border border-[#E2E9E3] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]" />
            </div>

            <div>
              <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Input / Output Format</label>
              <input type="text" name="io_format" value="JSON / Prompt-in, Hardened-out" class="w-full px-3 py-2 bg-white border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]" />
            </div>
          </div>
        </div>

        <!-- Section 3: Skills & Categories -->
        <div class="space-y-4">
          <h3 class="text-[13.5px] font-semibold text-[#176B45] border-b border-[#E2E9E3] pb-2">2. Expertise & Categories</h3>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Skills (Comma-separated)</label>
            <input type="text" name="skills_raw" placeholder="Adversarial Prompting, OWASP LLM Top-10, Indirect Injection, Jailbreak Defense" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Categories</label>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
              <label class="flex items-center gap-2 text-[13px] text-[#445246]"><input type="checkbox" name="cat" value="ai_security" checked /> AI Security</label>
              <label class="flex items-center gap-2 text-[13px] text-[#445246]"><input type="checkbox" name="cat" value="prompt_engineering" checked /> Prompt Engineering</label>
              <label class="flex items-center gap-2 text-[13px] text-[#445246]"><input type="checkbox" name="cat" value="llm_optimization" /> LLM Optimization</label>
              <label class="flex items-center gap-2 text-[13px] text-[#445246]"><input type="checkbox" name="cat" value="rag_security" /> RAG Security</label>
              <label class="flex items-center gap-2 text-[13px] text-[#445246]"><input type="checkbox" name="cat" value="ai_agents" /> AI Agents</label>
              <label class="flex items-center gap-2 text-[13px] text-[#445246]"><input type="checkbox" name="cat" value="api_security" /> Application Security</label>
            </div>
          </div>
        </div>

        <!-- Section 4: Initial Service Listing -->
        <div class="space-y-4">
          <h3 class="text-[13.5px] font-semibold text-[#176B45] border-b border-[#E2E9E3] pb-2">3. Initial Service Offering</h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Service Title *</label>
              <input type="text" name="service_title" required placeholder="e.g. Prompt Injection Vulnerability Audit" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Price (USD) *</label>
              <input type="number" step="0.01" min="0" name="service_price" value="50.00" required class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Estimated Delivery Time *</label>
              <input type="text" name="service_delivery" required value="24 hours" placeholder="e.g. 24 hours, Instant (< 10s)" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Portfolio or GitHub URL</label>
              <input type="url" name="portfolio_url" placeholder="https://github.com/your-username" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
            </div>
          </div>
        </div>

        <!-- Submit Button -->
        <div class="pt-4 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="navigateTo('dashboard')" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] hover:bg-[#F7F9F7] text-[13.5px] font-medium rounded-md transition-smooth">
            Cancel
          </button>
          <button type="submit" class="px-6 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth">
            Register Provider Profile
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
  const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
  const myProvider = STATE.data.providers.find(p =>
    (p.wallet_address && p.wallet_address.toLowerCase() === userWallet) ||
    p.id === STATE.user.activeProviderId
  );

  if (!myProvider) {
    return `
      <div class="max-w-2xl mx-auto py-16 text-center space-y-4">
        <div class="w-14 h-14 mx-auto rounded-2xl bg-[#EAF5EE] border border-[#CDE5D5] flex items-center justify-center text-[#176B45]">
          <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-[#202820]">Provider Registration Required</h2>
        <p class="text-[14px] text-[#627566] max-w-md mx-auto leading-relaxed">
          You are not currently registered as a provider. Register your security profile to offer prompt audits, receive scan requests from clients, and review submissions.
        </p>
        <div class="pt-2">
          <button onclick="navigateTo('become_provider')" class="px-5 py-2.5 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth inline-flex items-center gap-2">
            Register as Provider →
          </button>
        </div>
      </div>
    `;
  }

  const provider = myProvider;
  const assignedOrders = STATE.data.orders.filter(o => o.provider_id === provider.id || (provider.wallet_address && o.provider_wallet === provider.wallet_address));
  const incoming = assignedOrders.filter(o => o.status === 'requested');
  const inProgress = assignedOrders.filter(o => o.status === 'accepted' || o.status === 'in_progress');
  const completed = assignedOrders.filter(o => o.status === 'completed' || o.status === 'delivered');

  return `
    <div class="space-y-6">
      <!-- Provider Workspace Banner -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-6 shadow-xs flex items-center justify-between">
        <div class="flex items-center gap-4">
          <img src="${provider.avatar_url}" class="w-14 h-14 rounded-lg object-cover border border-[#E2E9E3]" />
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-xl font-semibold text-[#202820]">${provider.display_name}</h1>
              <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] font-semibold px-2 py-0.5 rounded">Provider Workspace</span>
            </div>
            <p class="text-[13px] text-[#627566]">${provider.title}</p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button onclick="openModal('add_service_modal', { providerId: '${provider.id}' })" class="px-3.5 py-2 bg-[#FFFFFF] border border-[#E2E9E3] hover:border-[#CBD7CE] text-[#202820] text-[13px] font-medium rounded-md shadow-xs transition-smooth">
            + Publish New Service
          </button>
          <button onclick="navigateTo('provider_detail', '${provider.id}')" class="px-3.5 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth">
            View Public Profile
          </button>
        </div>
      </div>

      <!-- Quick Metrics -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-white p-4 rounded-lg border border-[#E2E9E3]">
          <span class="text-[12px] text-[#627566] font-medium">Incoming Requests</span>
          <div class="text-2xl font-bold text-[#202820] mt-1">${incoming.length}</div>
        </div>
        <div class="bg-white p-4 rounded-lg border border-[#E2E9E3]">
          <span class="text-[12px] text-[#627566] font-medium">In Progress</span>
          <div class="text-2xl font-bold text-[#1E40AF] mt-1">${inProgress.length}</div>
        </div>
        <div class="bg-white p-4 rounded-lg border border-[#E2E9E3]">
          <span class="text-[12px] text-[#627566] font-medium">Delivered / Completed</span>
          <div class="text-2xl font-bold text-[#176B45] mt-1">${completed.length}</div>
        </div>
        <div class="bg-white p-4 rounded-lg border border-[#E2E9E3]">
          <span class="text-[12px] text-[#627566] font-medium">Completed Value</span>
          <div class="text-2xl font-bold text-[#202820] mt-1 font-mono">$${(completed.length * 95).toFixed(2)}</div>
        </div>
      </div>

      <!-- Incoming Requests Section -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-4">
        <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
          <div class="flex items-center gap-2">
            <h2 class="text-[14.5px] font-semibold text-[#202820]">Incoming Service Requests</h2>
            <span class="text-[11px] bg-[#FEF3C7] text-[#92400E] font-medium px-2 py-0.5 rounded">${incoming.length} pending</span>
          </div>
          <span class="text-[12px] text-[#627566]">Inspect submitted links and scope before accepting</span>
        </div>

        ${incoming.length > 0 ? `
          <div class="space-y-4">
            ${incoming.map(o => `
              <div class="p-4 rounded-lg border border-[#E2E9E3] bg-[#FAFBF9] space-y-3">
                <div class="flex items-start justify-between gap-4">
                  <div class="space-y-1 flex-1 min-w-0">
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-[12px] text-[#627566]">${o.id}</span>
                      <strong class="text-[13.5px] text-[#202820]">${escapeHtml(o.service_title)}</strong>
                      <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-mono font-medium">$${o.price.toFixed(2)}</span>
                    </div>
                    <div class="text-[12.5px] text-[#445246]">
                      Submitted by: <strong>${escapeHtml(o.customer_name)}</strong> • ${new Date(o.created_at).toLocaleDateString()}
                    </div>
                  </div>

                  <div class="flex items-center gap-2 shrink-0">
                    <button onclick="handleOrderStatusUpdate('${o.id}', 'accepted')" class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded transition-smooth cursor-pointer">
                      Accept Order
                    </button>
                    <button onclick="handleOrderStatusUpdate('${o.id}', 'rejected')" class="px-3 py-1.5 border border-[#FECACA] bg-[#FEE2E2] text-[#991B1B] hover:bg-[#FCA5A5] text-[12px] font-medium rounded transition-smooth cursor-pointer">
                      Reject
                    </button>
                  </div>
                </div>

                ${renderOrderSubmittedSpec(o, provider.wallet_address)}
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="p-6 text-center text-[#627566] text-[13px]">
            No incoming pending requests at this time.
          </div>
        `}
      </div>

      <!-- Work In Progress Section -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-4">
        <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
          <div class="flex items-center gap-2">
            <h2 class="text-[14.5px] font-semibold text-[#202820]">Active Work In Progress</h2>
            <span class="text-[11px] bg-[#DBEAFE] text-[#1E40AF] font-medium px-2 py-0.5 rounded">${inProgress.length} active</span>
          </div>
          <span class="text-[12px] text-[#627566]">Audit scopes, product links, and repositories</span>
        </div>

        ${inProgress.length > 0 ? `
          <div class="space-y-4">
            ${inProgress.map(o => `
              <div class="p-5 rounded-lg border border-[#E2E9E3] bg-[#FFFFFF] space-y-3 shadow-2xs">
                <div class="flex items-start justify-between">
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-[12px] text-[#627566]">${o.id}</span>
                      <strong class="text-[13.5px] text-[#202820]">${escapeHtml(o.service_title)}</strong>
                      ${renderStatusBadge(o.status)}
                    </div>
                    <div class="text-[12px] text-[#627566] mt-0.5">
                      Client: <strong>${escapeHtml(o.customer_name)}</strong> • Escrow Value: <strong class="text-[#176B45] font-mono">$${o.price.toFixed(2)}</strong>
                    </div>
                  </div>

                  <div class="flex items-center gap-2">
                    ${o.status === 'accepted' ? `
                      <button onclick="handleOrderStatusUpdate('${o.id}', 'in_progress')" class="px-3 py-1.5 bg-[#1E40AF] text-white text-[12px] font-medium rounded hover:bg-[#1E3A8A] transition-smooth cursor-pointer">
                        Mark In Progress
                      </button>
                    ` : ''}
                    <button onclick="openModal('deliver_modal', { orderId: '${o.id}', order: ${escapeForAttr(JSON.stringify(o))} })" class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded shadow-xs transition-smooth cursor-pointer">
                      Submit Deliverable & Report
                    </button>
                  </div>
                </div>

                ${renderOrderSubmittedSpec(o, provider.wallet_address)}
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="p-6 text-center text-[#627566] text-[13px]">
            No orders currently in progress.
          </div>
        `}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 6. My Prompts Page
// ---------------------------------------------------------------------------

function renderMyPromptsView() {
  const prompts = STATE.data.prompts;

  return `
    <div class="space-y-5">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">My Prompts</h1>
        </div>
        <button onclick="openModal('create_prompt')" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-1.5">
          + Add New Prompt
        </button>
      </div>

      <div class="grid grid-cols-1 gap-4">
        ${prompts.map(p => `
          <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-3 card-hover transition-smooth">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="text-[14.5px] font-semibold text-[#202820]">${escapeHtml(p.title)}</h3>
                <span class="text-[11.5px] text-[#627566] font-mono">${p.id} • Saved ${new Date(p.created_at).toLocaleDateString()}</span>
              </div>

              <div class="flex items-center gap-2">
                <button onclick="runLocalPromptAnalysis('${escapeForAttr(p.content)}', '${p.id}')" class="px-3 py-1.5 bg-[#FAFBF9] border border-[#E2E9E3] hover:border-[#176B45] text-[#176B45] text-[12px] font-semibold rounded transition-smooth flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Analyze with Guardvane
                </button>
                <button onclick="openModal('request_review', { promptText: '${escapeForAttr(p.content)}' })" class="px-3 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded transition-smooth">
                  Submit to Provider
                </button>
                <button onclick="handleDeletePrompt('${p.id}')" class="p-1.5 text-[#8B9C8E] hover:text-[#991B1B] rounded transition-smooth">
                  <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Content Preview -->
            <div class="bg-[#FAFBF9] border border-[#E2E9E3] rounded p-3 font-mono text-[12px] text-[#333E35] whitespace-pre-wrap">
              ${escapeHtml(p.content)}
            </div>

            <!-- Security Finding Tags if Analyzed -->
            ${p.analysis_result ? `
              <div class="flex items-center gap-3 pt-1 text-[11.5px]">
                <span class="text-[#627566]">Previous Scan:</span>
                <span class="font-medium ${p.analysis_result.injection_score > 0.5 ? 'text-[#991B1B]' : 'text-[#176B45]'}">
                  Injection: ${(p.analysis_result.injection_score * 100).toFixed(0)}%
                </span>
                <span class="text-[#627566]">•</span>
                <span class="text-[#445246]">Detected Risks: ${(p.analysis_result.risk_labels || []).join(', ') || 'None'}</span>
              </div>
            ` : ''}
          </div>
        `).join('')}
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
  const shortKey = t.entity_key ? (t.entity_key.substring(0, 10) + '...' + t.entity_key.substring(t.entity_key.length - 6)) : 'Pending';

  const statusColors = {
    open: 'bg-[#EAF5EE] text-[#176B45] border-[#CDE5D5]',
    awarded: 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]',
    completed: 'bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]'
  };
  const statusBadge = statusColors[t.status] || 'bg-gray-100 text-gray-800 border-gray-200';
  const skills = (t.required_skills || '').split(',').map(s => s.trim()).filter(Boolean);

  return `
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs hover:shadow-md transition-smooth flex flex-col justify-between space-y-4">
      <div class="space-y-3">
        <!-- Top Metadata Row -->
        <div class="flex items-center justify-between text-xs">
          <span class="px-2.5 py-0.5 rounded-full font-medium capitalize text-[11px] border ${statusBadge}">
            ${escapeHtml(t.status)}
          </span>
          <span class="font-mono text-[#627566] text-[11px]">
            Budget: <strong class="text-[#202820] font-semibold">${escapeHtml(t.budget_range || 'Negotiable')}</strong>
          </span>
        </div>

        <!-- Title -->
        <h3 class="text-[16px] font-semibold text-[#202820] leading-snug">
          ${escapeHtml(t.title)}
        </h3>

        <!-- Description -->
        <p class="text-[13px] text-[#445246] line-clamp-3 leading-relaxed">
          ${escapeHtml(t.public_description)}
        </p>

        <!-- Skills -->
        ${skills.length > 0 ? `
          <div class="flex flex-wrap gap-1.5 pt-1">
            ${skills.map(s => `
              <span class="px-2 py-0.5 rounded text-[11px] font-mono bg-[#F0F5F1] text-[#445246] border border-[#E2E9E3]">
                ${escapeHtml(s)}
              </span>
            `).join('')}
          </div>
        ` : ''}
      </div>

      <!-- Footer Info & Actions -->
      <div class="pt-3 border-t border-[#E2E9E3] flex flex-col space-y-3">
        <div class="flex items-center justify-between text-[11.5px] text-[#627566]">
          <div class="flex items-center gap-1.5">
            <span>Posted by:</span>
            <a
              href="https://explorer.rabdi.db-chain.testnet.arkiv.network/address/${t.customer_wallet}"
              target="_blank"
              class="font-mono text-[#176B45] hover:underline"
            >
              ${shortOwner}
            </a>
            ${isOwner ? '<span class="text-[9.5px] px-1 rounded bg-[#EAF5EE] text-[#176B45] font-semibold font-mono">YOU</span>' : ''}
          </div>

          <div class="font-mono text-[10.5px] text-[#8B9C8E]" title="Entity Key: ${t.entity_key}">
            Key: ${shortKey}
          </div>
        </div>

        <!-- Buttons -->
        <div class="flex items-center justify-end gap-2 pt-1">
          <button
            onclick="openTaskBidsModal('${t.task_id}')"
            class="px-3 py-1.5 bg-white border border-[#E2E9E3] hover:border-[#176B45] text-[#202820] text-[12.5px] font-medium rounded-md transition-smooth cursor-pointer"
          >
            Inspect Bids
          </button>

          ${(t.status === 'open' && !isOwner) ? `
            <button
              onclick="openSubmitBidModal('${t.task_id}')"
              class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded-md shadow-xs transition-smooth cursor-pointer"
            >
              Submit Bid
            </button>
          ` : ''}

          ${(t.status === 'open' && isOwner) ? `
            <button
              onclick="openTaskBidsModal('${t.task_id}')"
              class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded-md shadow-xs transition-smooth cursor-pointer"
            >
              Review Bids & Award
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
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">Arkiv Security Task Board</h1>
            <span class="px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-[#EAF5EE] text-[#176B45] border border-[#CDE5D5]">Rabdi 7794095</span>
          </div>
          <p class="text-[13px] text-[#627566] mt-0.5">
            Public, verifiable security audit requests published directly to Arkiv. Customer-owned, specialist-bid, rewarded in tGLM.
          </p>
        </div>

        <div class="flex items-center gap-2.5">
          <button
            onclick="loadArkivTasks(true)"
            title="Refresh live from Rabdi testnet"
            class="px-3 py-2 bg-white border border-[#E2E9E3] hover:border-[#176B45] text-[#202820] text-[13px] font-medium rounded-md shadow-2xs transition-smooth flex items-center gap-1.5 cursor-pointer"
          >
            <svg class="w-4 h-4 text-[#627566] ${STATE.arkiv.loading ? 'animate-spin' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>

          <button
            onclick="openPostTaskModal()"
            class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-2 cursor-pointer"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            <span>Post Security Task</span>
          </button>
        </div>
      </div>

      <!-- Category Filters -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[#E2E9E3]">
        ${categories.map(c => `
          <button
            onclick="setArkivCategoryFilter('${c.id}')"
            class="px-3.5 py-1.5 rounded-full text-[13px] font-medium whitespace-nowrap transition-smooth ${
              STATE.arkiv.categoryFilter === c.id
                ? 'bg-[#176B45] text-white shadow-xs'
                : 'bg-white border border-[#E2E9E3] text-[#445246] hover:bg-[#F0F5F1]'
            }"
          >
            ${c.label}
          </button>
        `).join('')}
      </div>

      <!-- Status Sub-filter -->
      <div class="flex items-center justify-between gap-4 bg-white p-3.5 border border-[#E2E9E3] rounded-lg shadow-xs">
        <div class="flex items-center gap-2">
          <span class="text-[13px] font-medium text-[#445246]">Status:</span>
          <div class="flex items-center gap-1">
            ${['all', 'open', 'awarded', 'completed'].map(st => `
              <button
                onclick="setArkivStatusFilter('${st}')"
                class="px-2.5 py-1 text-[12px] rounded-md font-medium capitalize transition-smooth ${
                  STATE.arkiv.statusFilter === st
                    ? 'bg-[#EAF5EE] text-[#176B45] font-semibold border border-[#CDE5D5]'
                    : 'text-[#627566] hover:text-[#202820]'
                }"
              >
                ${st}
              </button>
            `).join('')}
          </div>
        </div>

        <div class="text-[13px] text-[#627566]">
          Showing <strong class="text-[#202820]">${filtered.length}</strong> tasks on Rabdi Testnet
        </div>
      </div>

      <!-- Task Cards Grid -->
      ${filtered.length > 0 ? `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
          ${filtered.map(t => renderArkivTaskCard(t, currentWallet)).join('')}
        </div>
      ` : `
        <div class="bg-white border border-[#E2E9E3] rounded-lg p-12 text-center space-y-3">
          <div class="w-12 h-12 rounded-full bg-[#EAF5EE] text-[#176B45] flex items-center justify-center mx-auto">
            <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 class="text-[15px] font-semibold text-[#202820]">No security tasks found on Rabdi</h3>
          <p class="text-[13px] text-[#627566] max-w-md mx-auto">
            Tasks published to Arkiv are stored permanently on the Rabdi blockchain with decentralized ownership and time-based expiration.
          </p>
          <button onclick="openPostTaskModal()" class="px-4 py-2 bg-[#176B45] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth cursor-pointer">
            + Post the First Security Task
          </button>
        </div>
      `}
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 7. My Requests & Security Reports Pages
// ---------------------------------------------------------------------------

function renderMyRequestsView() {
  const orders = STATE.data.orders;

  return `
    <div class="space-y-5">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">My Requests</h1>
        </div>
        <button onclick="navigateTo('opihub')" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs">
          + Explore OpiHub
        </button>
      </div>

      <!-- Orders Table -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg shadow-xs overflow-hidden">
        <table class="w-full text-left text-[13px]">
          <thead class="bg-[#FAFBF9] border-b border-[#E2E9E3] text-[#627566] text-[11.5px] uppercase font-semibold tracking-wider">
            <tr>
              <th class="px-5 py-3">Order ID</th>
              <th class="px-5 py-3">Service</th>
              <th class="px-5 py-3">Provider</th>
              <th class="px-5 py-3">Status</th>
              <th class="px-5 py-3">Price</th>
              <th class="px-5 py-3">Date</th>
              <th class="px-5 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[#E2E9E3]">
            ${orders.map(o => `
              <tr class="hover:bg-[#FAFBF9]/80 transition-smooth">
                <td class="px-5 py-3.5 font-mono text-[12px] text-[#627566]">${o.id}</td>
                <td class="px-5 py-3.5 font-medium text-[#202820]">
                  ${escapeHtml(o.service_title)}
                  <div class="text-[11px] text-[#627566] font-normal">${o.execution_type === 'automated' ? 'Automated Execution' : 'Human Review'}</div>
                </td>
                <td class="px-5 py-3.5 text-[#445246]">${escapeHtml(o.provider_name)}</td>
                <td class="px-5 py-3.5">${renderStatusBadge(o.status)}</td>
                <td class="px-5 py-3.5 font-mono font-medium text-[#202820]">$${o.price.toFixed(2)}</td>
                <td class="px-5 py-3.5 text-[#627566]">${new Date(o.created_at).toLocaleDateString()}</td>
                <td class="px-5 py-3.5 text-right">
                  <div class="flex items-center justify-end gap-2">
                    ${(() => {
                      const notes = parseDeliverableNotes(o.deliverable_notes);
                      if (notes.ticket) {
                        return `<span class="px-2 py-0.5 rounded text-[10.5px] font-mono font-semibold bg-[#FEF2F2] text-[#991B1B] border border-[#FECACA]">Ticket Open</span>`;
                      }
                      return '';
                    })()}
                    ${o.report_id ? `
                      <button onclick="viewReport('${o.report_id}')" class="px-2.5 py-1 bg-[#EAF5EE] text-[#176B45] hover:bg-[#C4E4CE] font-medium text-[12px] rounded transition-smooth cursor-pointer">
                        View Report
                      </button>
                    ` : `
                      <span class="text-[12px] text-[#8B9C8E]">In Progress</span>
                    `}
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderSecurityReportsView() {
  const reports = STATE.data.reports;

  return `
    <div class="space-y-5">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">Security Reports</h1>
        </div>
      </div>

      <div class="grid grid-cols-1 gap-4">
        ${reports.map(r => `
          <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-4">
            <div class="flex items-start justify-between">
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-mono text-[12px] text-[#627566]">${r.id}</span>
                  <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] font-semibold px-2 py-0.5 rounded">Verified Audit</span>
                </div>
                <h3 class="text-[15.5px] font-semibold text-[#202820] mt-1">${escapeHtml(r.service_title)}</h3>
                <div class="text-[12px] text-[#627566]">
                  Audited by: <strong>${escapeHtml(r.provider_name)}</strong> • Order: <span class="font-mono">${r.order_id}</span>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <button onclick="viewReport('${r.id}')" class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded transition-smooth">
                  Inspect Findings & Hardened Prompt
                </button>
              </div>
            </div>

            <p class="text-[13px] text-[#445246]">${escapeHtml(r.summary)}</p>

            <!-- Findings Summary Chips -->
            <div class="flex flex-wrap gap-2 pt-1 border-t border-[#E2E9E3]">
              ${(r.findings || []).map(f => `
                <div class="px-2.5 py-1 rounded text-[11.5px] font-medium border flex items-center gap-1.5 ${
                  f.severity === 'critical' ? 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]' :
                  f.severity === 'high' ? 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]' :
                  'bg-[#EAF5EE] text-[#176B45] border-[#C4E4CE]'
                }">
                  <span class="uppercase text-[10px] font-bold">${f.severity}:</span>
                  <span>${escapeHtml(f.title)}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `).join('')}
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
    <div class="space-y-2 mt-2">
      <!-- Client Specification / Prompt -->
      <div class="bg-[#FAFBF9] border border-[#E2E9E3] p-3 rounded-md text-[12.5px] space-y-1">
        <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Submitted Specification / Scope:</div>
        <pre class="font-mono text-[12px] text-[#202820] whitespace-pre-wrap">${escapeHtml(o.prompt_content)}</pre>
        ${reqData.user_requirements ? `
          <div class="pt-2 border-t border-[#E2E9E3] text-[12px] text-[#445246]">
            <strong class="text-[#202820]">Client Constraints:</strong> ${escapeHtml(reqData.user_requirements)}
          </div>
        ` : ''}
      </div>

      <!-- Extended Links (Product, Docs/Repo, Environment) -->
      ${(reqData.product_link || reqData.docs_link || reqData.test_env_notes) ? `
        <div class="p-3 bg-white border border-[#E2E9E3] rounded-md space-y-2 text-[12px]">
          <div class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider">Audit Artifacts & Scopes</div>
          <div class="flex flex-wrap items-center gap-2">
            ${reqData.product_link ? `
              <a
                href="${escapeForAttr(reqData.product_link)}"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#EAF5EE] text-[#176B45] hover:bg-[#D5EBDC] font-medium border border-[#CDE5D5] transition-smooth cursor-pointer"
              >
                <span>🔗 Launch Product URL</span>
                <span class="font-mono text-[11px] text-[#2FA36B] truncate max-w-[200px]">(${escapeHtml(reqData.product_link)})</span>
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            ` : ''}

            ${reqData.docs_link ? `
              <a
                href="${escapeForAttr(reqData.docs_link)}"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#FAFBF9] text-[#202820] hover:bg-[#F0F5F1] font-medium border border-[#CBD7CE] transition-smooth cursor-pointer"
              >
                <span>📄 View Docs / Codebase</span>
                <span class="font-mono text-[11px] text-[#627566] truncate max-w-[200px]">(${escapeHtml(reqData.docs_link)})</span>
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
              </a>
            ` : ''}
          </div>

          ${reqData.test_env_notes ? `
            <div class="pt-1.5 border-t border-[#E2E9E3] text-[#445246] leading-relaxed">
              <strong class="text-[#202820]">Environment & Credentials Notes:</strong> ${escapeHtml(reqData.test_env_notes)}
            </div>
          ` : ''}
        </div>
      ` : ''}

      <!-- Payment & Escrow Status -->
      <div class="text-[11.5px] text-[#627566] bg-[#FAFBF9] px-3 py-1.5 rounded border border-[#E2E9E3] flex items-center justify-between">
        <span>Payment: <strong class="text-[#176B45]">Hedera x402 Autonomous Escrow</strong> ($${o.price.toFixed(2)} USD)</span>
        <span class="font-mono text-[11px] text-[#202820]">Disburses to: ${providerWallet ? escapeHtml(providerWallet.substring(0, 8) + '...' + providerWallet.substring(providerWallet.length - 4)) : 'Provider Wallet'}</span>
      </div>

      <!-- Active Ticket Alert Banner if Raised -->
      ${notesData.ticket ? `
        <div class="p-3 bg-[#FEF2F2] border border-[#FECACA] rounded-md space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-[12.5px] font-semibold text-[#991B1B] flex items-center gap-1.5">
              🚨 Quality Review Ticket Raised (${escapeHtml(notesData.ticket.ticket_id || 'TK-01')})
            </span>
            <span class="text-[11px] font-mono text-[#B91C1C]">${new Date(notesData.ticket.created_at).toLocaleString()}</span>
          </div>
          <div class="text-[12px] text-[#7F1D1D]"><strong class="font-semibold text-[#991B1B]">Reason:</strong> ${escapeHtml(notesData.ticket.reason)}</div>
          <div class="text-[12px] text-[#7F1D1D] bg-white/80 p-2 rounded border border-[#FCA5A5] italic">${escapeHtml(notesData.ticket.feedback)}</div>
        </div>
      ` : ''}
    </div>
  `;
}

function renderCleanProviderCard(p) {
  const isAutomated = p.provider_type === 'automated';
  const shortDesc = p.description.length > 130 ? p.description.slice(0, 130) + '...' : p.description;

  return `
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs flex flex-col justify-between card-hover transition-smooth space-y-3">
      <div class="space-y-2.5">
        <div class="flex items-start gap-3">
          <img src="${p.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-11 h-11 rounded-lg object-cover border border-[#E2E9E3] shrink-0" />
          <div class="min-w-0">
            <div class="flex items-center gap-1.5">
              <h3 class="text-[14px] font-semibold text-[#202820] truncate">${escapeHtml(p.display_name)}</h3>
              ${p.verified ? `
                <svg class="w-3.5 h-3.5 text-[#176B45] shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              ` : ''}
            </div>
            <p class="text-[11.5px] text-[#627566] line-clamp-1">${escapeHtml(p.title)}</p>
            <div class="mt-1">
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded font-mono ${isAutomated ? 'bg-[#E0E7FF] text-[#3730A3]' : 'bg-[#FEF3C7] text-[#92400E]'}">
                ${isAutomated ? '0G AI Defense Agent' : 'Human Security Specialist'}
              </span>
            </div>
          </div>
        </div>

        <p class="text-[12.5px] text-[#445246] line-clamp-2 leading-relaxed">
          ${escapeHtml(shortDesc)}
        </p>

        <!-- Concise Skills chips -->
        <div class="flex flex-wrap gap-1">
          ${(p.skills || []).slice(0, 3).map(s => `
            <span class="text-[10.5px] bg-[#FAFBF9] border border-[#E2E9E3] text-[#445246] px-2 py-0.5 rounded">
              ${escapeHtml(s)}
            </span>
          `).join('')}
          ${(p.skills || []).length > 3 ? `<span class="text-[10px] text-[#8B9C8E] self-center">+${p.skills.length - 3}</span>` : ''}
        </div>
      </div>

      <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-between">
        <div>
          <span class="text-[11px] text-[#627566] block">Availability</span>
          <span class="text-[12px] font-semibold text-[#176B45] capitalize">${p.availability}</span>
        </div>
        <button
          onclick="navigateTo('provider_detail', '${p.id}')"
          class="px-3 py-1.5 bg-[#FAFBF9] hover:bg-[#EAF5EE] border border-[#E2E9E3] text-[#176B45] text-[12px] font-medium rounded transition-smooth cursor-pointer"
        >
          View Profile
        </button>
      </div>
    </div>
  `;
}

function renderCleanServiceCard(s, showProvider = true) {
  const isAutomated = s.execution_type === 'automated';

  return `
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs flex flex-col justify-between card-hover transition-smooth space-y-3">
      <div class="space-y-2">
        <div class="flex items-start justify-between gap-2">
          <h3 class="text-[14px] font-semibold text-[#202820] tracking-tight leading-snug">${escapeHtml(s.title)}</h3>
          <div class="text-right shrink-0">
            <span class="font-mono font-bold text-[13.5px] text-[#176B45]">$${s.price.toFixed(2)}</span>
            ${isAutomated ? '<div class="text-[10px] font-mono text-[#2FA36B]">Free with 0G Credits</div>' : ''}
          </div>
        </div>

        ${showProvider ? `
          <div class="text-[12px] text-[#627566] flex items-center gap-1.5">
            By <strong class="text-[#202820] cursor-pointer hover:underline" onclick="navigateTo('provider_detail', '${s.provider_id}')">${escapeHtml(s.provider_name)}</strong>
            <span class="text-[10px] px-1.5 py-0.2 rounded font-mono font-medium ${isAutomated ? 'bg-[#E0E7FF] text-[#3730A3]' : 'bg-[#FEF3C7] text-[#92400E]'}">
              ${isAutomated ? '0G Autonomous AI' : 'Specialist Review'}
            </span>
          </div>
        ` : ''}

        <p class="text-[12.5px] text-[#445246] line-clamp-2 leading-relaxed">
          ${escapeHtml(s.description)}
        </p>

        <div class="flex items-center gap-4 text-[11.5px] text-[#627566] pt-1">
          <span>Turnaround: <strong class="text-[#202820]">${s.estimated_delivery}</strong></span>
          <span>Category: <strong class="text-[#202820]">${formatCategoryName(s.category)}</strong></span>
        </div>
      </div>

      <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-between">
        <div class="text-[11px] text-[#627566]">
          ${isAutomated ? '⚡ Instant On-Chain Inference' : '🔒 Hedera x402 Escrow Protected'}
        </div>
        <button
          onclick="openModal('request_review', { serviceId: '${s.id}', providerId: '${s.provider_id}' })"
          class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded transition-smooth cursor-pointer shadow-xs"
        >
          ${isAutomated ? 'Run 0G Defense' : 'Request Review'}
        </button>
      </div>
    </div>
  `;
}

function renderStatusBadge(status) {
  const map = {
    requested: 'badge-status-requested',
    accepted: 'badge-status-accepted',
    in_progress: 'badge-status-in_progress',
    delivered: 'badge-status-delivered',
    completed: 'badge-status-completed',
    rejected: 'badge-status-rejected',
    cancelled: 'badge-status-cancelled'
  };
  const cls = map[status] || 'bg-gray-100 text-gray-800';
  return `<span class="px-2.5 py-0.5 rounded-full text-[11px] font-semibold capitalize font-mono ${cls}">${status.replace('_', ' ')}</span>`;
}

function renderActivityFeed(activities) {
  if (!activities || activities.length === 0) {
    return `<div class="py-4 text-center text-[#627566] text-[13px]">No recent orders or reports recorded yet.</div>`;
  }

  return activities.slice(0, 4).map(act => `
    <div class="py-3 flex items-center justify-between text-[13px]">
      <div class="flex items-center gap-2.5 min-w-0 pr-3">
        <div class="w-2 h-2 rounded-full bg-[#176B45] shrink-0"></div>
        <div class="truncate">
          <strong class="text-[#202820]">${escapeHtml(act.title)}</strong>
          <span class="text-[#627566]">with ${escapeHtml(act.provider)}</span>
        </div>
      </div>

      <div class="flex items-center gap-2.5 shrink-0">
        ${renderStatusBadge(act.status)}
      </div>
    </div>
  `).join('');
}

// ---------------------------------------------------------------------------
// Modals Container & Dialogs
// ---------------------------------------------------------------------------

function renderModalContainer() {
  return `
    <div class="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
      <div class="bg-white rounded-lg shadow-xl border border-[#E2E9E3] max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        ${renderModalContent()}
      </div>
    </div>
  `;
}

function renderModalContent() {
  switch (STATE.activeModal) {
    case 'request_review':
      return renderRequestReviewModal();
    case 'deliver_modal':
      return renderDeliverModal();
    case 'quick_analyze':
      return renderQuickAnalyzeModal();
    case 'create_prompt':
      return renderCreatePromptModal();
    case 'report_viewer':
      return renderReportViewerModal();
    case 'wallet_modal':
      return renderWalletModal();
    case 'settings_modal':
      return renderSettingsModal();
    case 'add_service_modal':
      return renderAddServiceModal();
    case 'arkiv_post_task':
      return renderArkivPostTaskModal();
    case 'arkiv_submit_bid':
      return renderArkivSubmitBidModal();
    case 'arkiv_view_bids':
      return renderArkivViewBidsModal();
    default:
      return '';
  }
}

function renderRequestReviewModal() {
  const payload = STATE.modalPayload || {};
  const services = STATE.data.services;
  const currentService = services.find(s => s.id === payload.serviceId) || services[0];
  const isAutomated = currentService?.execution_type === 'automated';
  const category = currentService?.category || '';
  const prompts = STATE.data.prompts;
  const isApplicationTesting = category === 'application_testing';
  const isCodebaseSecurity = category === 'codebase_security';

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <div>
          <h3 class="text-[16px] font-semibold text-[#202820]">
            ${isAutomated ? 'Execute Autonomous 0G Defense' : 'Request Specialist Security Review'}
          </h3>
          <p class="text-[12px] text-[#627566] mt-0.5">${formatCategoryName(category)} • ${escapeHtml(currentService?.provider_name || '')}</p>
        </div>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <form onsubmit="handleOrderSubmit(event)" class="space-y-4">
        <!-- Service Selector -->
        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Select Service Offering *</label>
          <select
            name="service_id"
            id="modal-service-select"
            onchange="onRequestModalServiceChange(this.value)"
            class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] font-medium text-[#202820] focus:outline-none focus:border-[#176B45]"
          >
            ${services.map(s => `
              <option value="${s.id}" ${s.id === currentService?.id ? 'selected' : ''}>
                ${escapeHtml(s.title)} — $${s.price.toFixed(2)} (${escapeHtml(s.provider_name)}${s.execution_type === 'automated' ? ' • Automated 0G' : ' • Specialist'})
              </option>
            `).join('')}
          </select>
        </div>

        <!-- Dynamic Category-Specific Form Fields -->
        ${isApplicationTesting ? `
          <!-- Application Testing Specific Inputs -->
          <div class="space-y-3.5 p-3.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-xl">
            <div class="text-[11.5px] font-semibold text-[#176B45] uppercase tracking-wider">Application Target Details</div>
            
            <div>
              <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Product Link / Staging URL *</label>
              <input
                type="url"
                name="product_link"
                required
                placeholder="https://app.example.com or https://staging.example.com"
                class="w-full px-3 py-2 bg-white border border-[#CBD7CE] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]"
              />
              <p class="text-[11px] text-[#627566] mt-1">Specialist will test this target environment directly for injection, authentication, and SSRF flaws.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Documentation / API Spec Link</label>
                <input
                  type="url"
                  name="docs_link"
                  placeholder="https://docs.example.com or Swagger URL"
                  class="w-full px-3 py-2 bg-white border border-[#CBD7CE] rounded-md text-[12.5px] font-mono focus:outline-none focus:border-[#176B45]"
                />
              </div>
              <div>
                <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Staging Credentials & Scope Notes</label>
                <input
                  type="text"
                  name="test_env_notes"
                  placeholder="Test account logins, staging endpoints, focus pages..."
                  class="w-full px-3 py-2 bg-white border border-[#CBD7CE] rounded-md text-[12.5px] focus:outline-none focus:border-[#176B45]"
                />
              </div>
            </div>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Testing Scope & Attack Vectors to Probe *</label>
            <textarea
              name="prompt_content"
              rows="4"
              required
              placeholder="Describe user roles, sensitive business logic, connected LLM APIs, and priority attack vectors (e.g. prompt injection, unauthorized data exfiltration, privilege escalation)..."
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"
            >${payload.promptText || ''}</textarea>
          </div>
        ` : (isCodebaseSecurity ? `
          <!-- Codebase Security Specific Inputs -->
          <div class="space-y-3.5 p-3.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-xl">
            <div class="text-[11.5px] font-semibold text-[#176B45] uppercase tracking-wider">Repository & Architecture Scope</div>

            <div>
              <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Codebase / Repository URL *</label>
              <input
                type="url"
                name="docs_link"
                required
                placeholder="https://github.com/organization/repo (or private repo invite link)"
                class="w-full px-3 py-2 bg-white border border-[#CBD7CE] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]"
              />
              <p class="text-[11px] text-[#627566] mt-1">Specialist Marcus Chen will review Python/TypeScript agent frameworks and tool invocation boundaries.</p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Live Application / Staging Link (Optional)</label>
                <input
                  type="url"
                  name="product_link"
                  placeholder="https://app.example.com"
                  class="w-full px-3 py-2 bg-white border border-[#CBD7CE] rounded-md text-[12.5px] font-mono focus:outline-none focus:border-[#176B45]"
                />
              </div>
              <div>
                <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Branch / Sensitive Modules Notes</label>
                <input
                  type="text"
                  name="test_env_notes"
                  placeholder="e.g. main branch, langchain_agents/, secrets.py"
                  class="w-full px-3 py-2 bg-white border border-[#CBD7CE] rounded-md text-[12.5px] focus:outline-none focus:border-[#176B45]"
                />
              </div>
            </div>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Codebase Security Audit Scope & Focus *</label>
            <textarea
              name="prompt_content"
              rows="4"
              required
              placeholder="Specify sensitive modules, credential access patterns, agent memory persistence, or tool execution privileges to evaluate..."
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"
            >${payload.promptText || ''}</textarea>
          </div>
        ` : `
          <!-- Prompt / Loop Engineering Inputs -->
          <div>
            <div class="flex items-center justify-between mb-1">
              <label class="text-[13px] font-medium text-[#202820]">Prompt or Agent Instructions Under Review *</label>
              ${prompts.length > 0 ? `
                <select onchange="populatePromptFromSelect(this.value)" class="text-[12px] text-[#176B45] border border-[#CBD7CE] rounded px-2 py-0.5">
                  <option value="">Insert from Saved Prompts...</option>
                  ${prompts.map(p => `<option value="${escapeForAttr(p.content)}">${escapeHtml(p.title)}</option>`).join('')}
                </select>
              ` : ''}
            </div>
            <textarea
              id="order-prompt-input"
              name="prompt_content"
              rows="5"
              required
              placeholder="Paste system instructions, agent cyclic graph, or prompt here..."
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]"
            >${payload.promptText || ''}</textarea>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Specific Hardening Constraints & Target LLM</label>
            <textarea
              name="requirements"
              rows="2"
              placeholder="e.g. Target model (GPT-4o / Claude 3.5), tone constraints, defense against roleplay escapes..."
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"
            ></textarea>
          </div>
        `)}

        <!-- Payment & Authority Architecture Section -->
        ${isAutomated ? `
          <div class="p-3.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-xl space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="text-[11.5px] font-semibold text-[#176B45] uppercase tracking-wider">Payment & Execution Authority</span>
              <span class="text-[11px] bg-[#E0E7FF] text-[#3730A3] font-semibold px-2 py-0.5 rounded font-mono">0G Private Computer</span>
            </div>
            <div class="space-y-2 text-[12.5px]">
              <label class="flex items-start gap-3 p-3 rounded-lg border border-[#CDE5D5] bg-[#EAF5EE] cursor-pointer transition-smooth">
                <input type="radio" name="wallet_payment_mode" value="0g" checked onchange="toggleZeroGMode(true)" class="mt-0.5 text-[#176B45] focus:ring-[#176B45]" />
                <div>
                  <span class="font-semibold text-[#176B45] flex items-center gap-1.5">
                    ✨ 0G-Registered Wallet (0G Compute Credits)
                  </span>
                  <p class="text-[11.5px] text-[#445246] mt-0.5 leading-relaxed">
                    Covered under 0G Compute Allocation Credits — <strong class="text-[#176B45] font-mono">$0.00 USD (Zero Gas)</strong>.
                  </p>
                </div>
              </label>
              <label class="flex items-start gap-3 p-3 rounded-lg border border-[#E2E9E3] bg-white cursor-pointer transition-smooth">
                <input type="radio" name="wallet_payment_mode" value="x402" onchange="toggleZeroGMode(false)" class="mt-0.5 text-[#176B45] focus:ring-[#176B45]" />
                <div>
                  <span class="font-semibold text-[#202820]">
                    ⚡ Standard Web3 Wallet (Hedera x402 Micropayment)
                  </span>
                  <p class="text-[11.5px] text-[#627566] mt-0.5 leading-relaxed">
                    Autonomous micro-payment settled via Hedera x402 protocol — <strong class="text-[#202820] font-mono">$${currentService.price.toFixed(2)} USD</strong>.
                  </p>
                </div>
              </label>
              <input type="hidden" name="is_zero_g_wallet" id="is_zero_g_wallet_hidden" value="true" />
            </div>
          </div>
        ` : `
          <div class="p-3.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-xl space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-[11.5px] font-semibold text-[#176B45] uppercase tracking-wider">Payment & Escrow Protection</span>
              <span class="text-[11px] bg-[#FEF3C7] text-[#92400E] font-semibold px-2 py-0.5 rounded font-mono">Hedera x402 Smart Escrow</span>
            </div>
            <div class="p-3 rounded-lg border border-[#E2E9E3] bg-white text-[12.5px] space-y-1.5">
              <div class="flex items-center justify-between">
                <span class="text-[#445246] font-medium">Specialist Audit Fee:</span>
                <span class="font-mono font-bold text-[#202820] text-[14px]">$${currentService.price.toFixed(2)} USD</span>
              </div>
              <p class="text-[11.5px] text-[#627566] leading-relaxed">
                Payment is locked in autonomous smart escrow and automatically disburses directly to the specialist's wallet upon verified delivery of your audit deliverable.
              </p>
            </div>
            <input type="hidden" name="is_zero_g_wallet" value="false" />
          </div>
        `}

        <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] text-[13px] font-medium rounded-md hover:bg-[#F0F5F1] transition-smooth cursor-pointer">
            Cancel
          </button>
          <button type="submit" class="px-5 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth cursor-pointer">
            ${isAutomated ? 'Execute 0G Defense' : 'Submit Review Request'}
          </button>
        </div>
      </form>
    </div>
  `;
}

function renderDeliverModal() {
  const payload = STATE.modalPayload || {};
  const orderId = payload.orderId;

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[16px] font-semibold text-[#202820]">Submit Audit Deliverable & Report</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <form onsubmit="handleDeliverSubmit(event, '${orderId}')" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Executive Summary *</label>
          <textarea name="summary" rows="3" required placeholder="Summarize vulnerabilities identified, testing scope verified, and remediation..." class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Primary Finding (Title & Severity)</label>
          <div class="grid grid-cols-3 gap-2">
            <input type="text" name="finding_title" placeholder="e.g. Indirect Injection Surface" class="col-span-2 px-2.5 py-1.5 border border-[#CBD7CE] rounded text-[12.5px]" />
            <select name="finding_severity" class="px-2 py-1.5 border border-[#CBD7CE] rounded text-[12.5px]">
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Actionable Recommendations</label>
          <textarea name="recommendations_raw" rows="3" placeholder="1. Enforce XML delimiter encapsulation&#10;2. Apply input sanitization" class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Delivered Hardened Prompt / Code Patch / Test Deliverable</label>
          <textarea name="hardened_prompt" rows="3" placeholder="Paste hardened defense prompt, security patch, or detailed PoC findings..." class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[12.5px] font-mono focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] text-[13px] font-medium rounded-md">Cancel</button>
          <button type="submit" class="px-5 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth cursor-pointer">
            Deliver Audit & Disburse Payment
          </button>
        </div>
      </form>
    </div>
  `;
}

function renderQuickAnalyzeModal() {
  return `
    <div class="p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[16px] font-semibold text-[#202820]">Analyze Prompt Security</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <div class="space-y-3">
        <label class="block text-[13px] font-medium text-[#202820]">Prompt Text</label>
        <textarea id="quick-prompt-input" rows="4" placeholder="Enter prompt to evaluate against Guardvane's injection model and 15 OWASP application risk classifiers..." class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]"></textarea>

        <div class="flex justify-end gap-2">
          <button id="quick-scan-btn" onclick="executeQuickAnalyze()" class="px-3.5 py-2 bg-white border border-[#CBD7CE] hover:border-[#176B45] text-[#202820] text-[13px] font-medium rounded-md shadow-xs transition-smooth inline-flex items-center gap-1.5 cursor-pointer">
            <svg class="w-4 h-4 text-[#176B45]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            Local ML Scan
          </button>
          <button id="quick-opt-btn" onclick="executeQuickOptimize()" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth inline-flex items-center gap-1.5 cursor-pointer">
            <span class="w-2 h-2 rounded-full bg-emerald-300 animate-pulse"></span>
            0G AI Reasoning & Hardening
          </button>
        </div>

        <div id="quick-analyze-results" class="hidden mt-4 p-4 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md space-y-3"></div>
      </div>
    </div>
  `;
}

function renderReportViewerModal() {
  const report = STATE.modalPayload;
  if (!report) return '';

  const order = STATE.data.orders.find(o => o.id === report.order_id);
  const parsedNotes = parseDeliverableNotes(order?.deliverable_notes);
  const hasTicket = !!parsedNotes.ticket;
  const isTicketFormOpen = STATE.activeTicketFormOrderId === report.order_id;

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <div>
          <span class="text-[11px] font-mono text-[#627566]">${report.id}</span>
          <h3 class="text-[16px] font-semibold text-[#202820]">${escapeHtml(report.service_title)}</h3>
        </div>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <!-- Ticket Alert Banner if Ticket Exists -->
      ${hasTicket ? `
        <div class="p-4 rounded-xl bg-[#FEF2F2] border border-[#FECACA] space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[13px] font-semibold text-[#991B1B] flex items-center gap-2">
              🚨 Quality Review Ticket Raised (${escapeHtml(parsedNotes.ticket.ticket_id || 'TK-01')})
            </span>
            <span class="text-[11px] font-mono text-[#B91C1C]">${new Date(parsedNotes.ticket.created_at).toLocaleString()}</span>
          </div>
          <div class="text-[12.5px] text-[#7F1D1D]"><strong class="font-medium text-[#991B1B]">Reason:</strong> ${escapeHtml(parsedNotes.ticket.reason)}</div>
          <div class="text-[12px] text-[#7F1D1D] bg-white/80 p-2.5 rounded border border-[#FCA5A5] italic">${escapeHtml(parsedNotes.ticket.feedback)}</div>
          <div class="text-[11.5px] text-[#991B1B] font-medium">Status: Under Specialist Revision</div>
        </div>
      ` : ''}

      <div class="space-y-4 text-[13px]">
        <div>
          <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Executive Summary</div>
          <p class="text-[#333E35] mt-1 leading-relaxed">${escapeHtml(report.summary)}</p>
        </div>

        <div>
          <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider mb-2">Findings</div>
          <div class="space-y-2">
            ${(report.findings || []).map(f => `
              <div class="p-3 rounded border border-[#E2E9E3] bg-[#FAFBF9] space-y-1">
                <div class="flex items-center justify-between">
                  <strong class="text-[13px] text-[#202820]">${escapeHtml(f.title)}</strong>
                  <span class="uppercase text-[10px] font-bold px-2 py-0.5 rounded ${f.severity === 'critical' ? 'bg-[#FEE2E2] text-[#991B1B]' : 'bg-[#FEF3C7] text-[#92400E]'}">
                    ${f.severity}
                  </span>
                </div>
                <div class="text-[12px] text-[#445246]">${escapeHtml(f.description)}</div>
                ${f.remediation ? `<div class="text-[12px] text-[#176B45]"><strong>Remediation:</strong> ${escapeHtml(f.remediation)}</div>` : ''}
              </div>
            `).join('')}
          </div>
        </div>

        ${report.hardened_prompt ? `
          <div>
            <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider mb-1">Delivered Security Output & Defense Assertions</div>
            <pre class="bg-[#FAFBF9] border border-[#E2E9E3] p-3 rounded font-mono text-[12px] text-[#202820] whitespace-pre-wrap">${escapeHtml(report.hardened_prompt)}</pre>
          </div>
        ` : ''}

        <!-- Raise a Ticket Option for Dissatisfied Performance -->
        ${!hasTicket && order ? `
          <div class="pt-4 border-t border-[#E2E9E3]">
            ${!isTicketFormOpen ? `
              <div class="flex items-center justify-between p-3.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-xl">
                <div>
                  <h4 class="text-[13px] font-medium text-[#202820]">Dissatisfied with audit findings or performance?</h4>
                  <p class="text-[11.5px] text-[#627566]">Raise a quality review ticket directly to the specialist to request revisions or dispute deliverable coverage.</p>
                </div>
                <button
                  onclick="toggleTicketForm('${report.order_id}', true)"
                  class="px-3.5 py-1.5 bg-white border border-[#FECACA] hover:bg-[#FEE2E2] text-[#991B1B] text-[12px] font-semibold rounded-md transition-smooth shrink-0 cursor-pointer shadow-2xs"
                >
                  Raise a Ticket
                </button>
              </div>
            ` : `
              <div class="p-4 bg-[#FEF2F2]/60 border border-[#FECACA] rounded-xl space-y-3">
                <div class="flex items-center justify-between">
                  <h4 class="text-[13.5px] font-semibold text-[#991B1B] flex items-center gap-1.5">
                    🚨 Raise a Quality Ticket / Dispute Deliverable
                  </h4>
                  <button onclick="toggleTicketForm('${report.order_id}', false)" class="text-[#991B1B] hover:text-[#7F1D1D] text-xs">Cancel</button>
                </div>
                <form onsubmit="handleRaiseTicketSubmit(event, '${report.order_id}', '${report.id}')" class="space-y-3">
                  <div>
                    <label class="block text-[12px] font-medium text-[#7F1D1D] mb-1">Primary Concern *</label>
                    <select name="reason" required class="w-full px-3 py-2 bg-white border border-[#FECACA] rounded-md text-[12.5px] text-[#202820] focus:outline-none focus:border-[#991B1B]">
                      <option value="Incomplete Vulnerability Analysis">Incomplete Vulnerability Analysis</option>
                      <option value="Missed Scope Requirements">Missed Scope Requirements (Product / Repo links unverified)</option>
                      <option value="Unclear Remediation Guidance">Unclear Remediation Guidance</option>
                      <option value="Deliverable Format Issue">Deliverable Format Issue</option>
                      <option value="Other Quality Concern">Other Quality Concern</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-[12px] font-medium text-[#7F1D1D] mb-1">Detailed Feedback & Requested Changes *</label>
                    <textarea name="feedback" rows="3" required placeholder="Specify what the specialist missed, which endpoints or prompts require further testing, and what corrections are required..." class="w-full px-3 py-2 bg-white border border-[#FECACA] rounded-md text-[12.5px] text-[#202820] focus:outline-none focus:border-[#991B1B]"></textarea>
                  </div>
                  <div class="flex justify-end gap-2 pt-1">
                    <button type="button" onclick="toggleTicketForm('${report.order_id}', false)" class="px-3 py-1.5 bg-white border border-[#E2E9E3] text-[#445246] text-xs rounded-md">Cancel</button>
                    <button type="submit" class="px-4 py-1.5 bg-[#991B1B] hover:bg-[#7F1D1D] text-white text-xs font-semibold rounded-md shadow-xs transition-smooth cursor-pointer">
                      Submit Ticket to Specialist
                    </button>
                  </div>
                </form>
              </div>
            `}
          </div>
        ` : ''}
      </div>
    </div>
  `;
}

function renderWalletModal() {
  const isConnected = !!STATE.auth.walletAddress;
  const address = STATE.auth.walletAddress || 'Not Connected';
  const userWallet = (STATE.auth.walletAddress || '').toLowerCase();
  const myProvider = STATE.data.providers.find(p =>
    (p.wallet_address && p.wallet_address.toLowerCase() === userWallet) ||
    p.id === STATE.user.activeProviderId
  );

  return `
    <div class="p-6 space-y-4 select-none">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[16px] font-semibold text-[#202820]">Connected Wallet</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <div class="space-y-4 text-[13px]">
        <div class="p-4 bg-[#FAFBF9] border border-[#E2E9E3] rounded-xl space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-[#627566]">Status:</span>
            <span class="flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-semibold ${isConnected ? 'bg-[#EAF5EE] text-[#176B45]' : 'bg-[#FEF3C7] text-[#92400E]'}">
              <span class="w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-[#176B45]' : 'bg-[#D97706]'}"></span>
              ${isConnected ? 'Connected via MetaMask' : 'Disconnected'}
            </span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-[#627566]">Address:</span>
            <code class="font-mono text-xs text-[#202820] bg-white px-2 py-1 rounded border border-[#E2E9E3] truncate max-w-[240px]" title="${escapeForAttr(address)}">
              ${escapeHtml(address)}
            </code>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-[#627566]">Provider Profile:</span>
            <span class="font-medium text-[#202820] text-xs">
              ${myProvider ? `${escapeHtml(myProvider.display_name)} (Registered)` : 'Not registered'}
            </span>
          </div>
        </div>

        <div class="pt-3 border-t border-[#E2E9E3] flex justify-between items-center">
          ${isConnected ? `
            <button onclick="closeModal(); handleLogout();" class="px-3 py-1.5 text-xs text-[#991B1B] hover:bg-[#FEE2E2] rounded-md font-medium transition-smooth">
              Disconnect Wallet
            </button>
          ` : `
            <button onclick="closeModal(); connectAndSignWithMetaMask();" class="px-3 py-1.5 bg-[#176B45] text-white text-xs rounded-md font-medium">
              Connect MetaMask
            </button>
          `}

          <button onclick="closeModal()" class="px-4 py-2 bg-[#202820] text-white text-[12.5px] font-medium rounded-md hover:bg-black transition-smooth">
            Close
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderSettingsModal() {
  const userWallet = STATE.auth.walletAddress || '';
  const myProvider = STATE.data.providers.find(p =>
    (p.wallet_address && userWallet && p.wallet_address.toLowerCase() === userWallet.toLowerCase()) ||
    p.id === STATE.user.activeProviderId
  );

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[16px] font-semibold text-[#202820]">Account & Settings</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <div class="space-y-4 text-[13px]">
        <div>
          <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Display Name</label>
          <div class="flex items-center gap-2">
            <input
              type="text"
              id="settings-name-input"
              value="${escapeForAttr(STATE.user.name || '')}"
              placeholder="Enter your name or handle..."
              class="w-full px-3 py-2 bg-white border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
            />
            <button
              onclick="saveDisplayName()"
              class="px-3.5 py-2 bg-[#176B45] text-white hover:bg-[#115638] text-xs font-medium rounded-md whitespace-nowrap transition-smooth shadow-xs cursor-pointer"
            >
              Save
            </button>
          </div>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Connected Wallet Address</label>
          <div class="flex items-center gap-2">
            <input
              type="text"
              readonly
              value="${escapeForAttr(userWallet || 'Not Connected')}"
              class="w-full px-3 py-2 bg-[#F7F9F7] border border-[#E2E9E3] rounded-md font-mono text-xs text-[#202820] select-all"
            />
            <button
              onclick="navigator.clipboard.writeText('${escapeForAttr(userWallet)}'); alert('Wallet address copied to clipboard!');"
              class="px-3 py-2 bg-[#FFFFFF] border border-[#E2E9E3] hover:border-[#CBD7CE] text-[#202820] text-xs font-medium rounded-md whitespace-nowrap transition-smooth shadow-xs"
            >
              Copy
            </button>
          </div>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Provider Status</label>
          <div class="p-3 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md flex items-center justify-between">
            <div class="space-y-0.5">
              <div class="font-medium text-[#202820] text-[13px]">
                ${myProvider ? escapeHtml(myProvider.display_name) : 'Standard Account'}
              </div>
              <div class="text-[11.5px] text-[#627566]">
                ${myProvider ? `${escapeHtml(myProvider.title)} • ${myProvider.provider_type === 'automated' ? 'Automated AI Provider' : 'Human Security Provider'}` : 'Not registered as a security provider'}
              </div>
            </div>
            ${myProvider ? `
              <button onclick="closeModal(); navigateTo('provider_workspace');" class="px-3 py-1.5 bg-[#EAF5EE] text-[#176B45] hover:bg-[#D7EFE0] rounded text-xs font-semibold transition-smooth">
                Workspace →
              </button>
            ` : `
              <button onclick="closeModal(); navigateTo('become_provider');" class="px-3 py-1.5 bg-[#176B45] text-white hover:bg-[#115638] rounded text-xs font-medium transition-smooth">
                Register →
              </button>
            `}
          </div>
        </div>

        <div>
          <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Session Security</label>
          <div class="p-3 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md space-y-1 text-[12px] text-[#627566]">
            <div class="flex items-center justify-between text-[#202820]">
              <span>Authentication Standard</span>
              <span class="font-mono text-[11px] bg-white px-2 py-0.5 rounded border border-[#E2E9E3]">EIP-4361 (SIWE)</span>
            </div>
            <div class="flex items-center justify-between text-[#202820] pt-1">
              <span>Session Storage</span>
              <span class="font-mono text-[11px] bg-white px-2 py-0.5 rounded border border-[#E2E9E3]">Secure HttpOnly Cookie</span>
            </div>
          </div>
        </div>

        <div class="pt-3 border-t border-[#E2E9E3] flex justify-between items-center">
          <button onclick="closeModal(); handleLogout();" class="text-xs text-[#991B1B] hover:underline font-medium">
            Sign Out
          </button>
          <button onclick="closeModal()" class="px-4 py-2 bg-[#202820] text-white text-[12.5px] font-medium rounded-md hover:bg-black transition-smooth">
            Close
          </button>
        </div>
      </div>
    </div>
  `;
}

function saveDisplayName() {
  const input = document.getElementById('settings-name-input');
  if (!input) return;
  const newName = input.value.trim();
  if (newName) {
    STATE.user.name = newName;
    localStorage.setItem('guardvane_display_name', newName);
  } else {
    STATE.user.name = null;
    localStorage.removeItem('guardvane_display_name');
  }
  renderApp();
  openModal('settings_modal');
}

function renderCreatePromptModal() {
  return `
    <div class="p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[16px] font-semibold text-[#202820]">Save Prompt to Library</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <form onsubmit="handleCreatePromptSubmit(event)" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Prompt Title *</label>
          <input type="text" name="title" required placeholder="e.g. Finance Agent System Instructions" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]" />
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Prompt Content *</label>
          <textarea name="content" rows="5" required placeholder="Enter prompt instructions..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-[#E2E9E3]">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[13px] rounded-md">Cancel</button>
          <button type="submit" class="px-5 py-2 bg-[#176B45] text-white text-[13px] font-medium rounded-md">Save Prompt</button>
        </div>
      </form>
    </div>
  `;
}

function renderAddServiceModal() {
  const payload = STATE.modalPayload || {};
  return `
    <div class="p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[16px] font-semibold text-[#202820]">Publish New Security Service</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <form onsubmit="handleAddServiceSubmit(event, '${payload.providerId}')" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Service Title *</label>
          <input type="text" name="title" required placeholder="e.g. Autonomous Token Defense Audit" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]" />
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Description *</label>
          <textarea name="description" rows="3" required placeholder="Describe deliverables, methodology, and scope..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Price (USD) *</label>
            <input type="number" step="0.01" min="0" name="price" value="75.00" required class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px]" />
          </div>
          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Turnaround Estimate *</label>
            <input type="text" name="estimated_delivery" value="24 hours" required class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px]" />
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Execution Type</label>
          <select name="execution_type" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px]">
            <option value="manual">Manual Specialist Delivery</option>
            <option value="automated">Automated AI Service</option>
          </select>
        </div>

        <div class="flex justify-end gap-2 pt-3 border-t border-[#E2E9E3]">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[13px] rounded-md">Cancel</button>
          <button type="submit" class="px-5 py-2 bg-[#176B45] text-white text-[13px] font-medium rounded-md">Publish Service</button>
        </div>
      </form>
    </div>
  `;
}

function renderArkivPostTaskModal() {
  const isRabdi = STATE.network.isRabdi;

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="text-[16px] font-semibold text-[#202820]">Post Security Task to Arkiv</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#EAF5EE] text-[#176B45] border border-[#CDE5D5]">Rabdi 7794095</span>
          </div>
          <p class="text-[12px] text-[#627566] mt-0.5">Published directly to Rabdi blockchain with a 7-day expiration lease. Verified decentralized discovery.</p>
        </div>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      ${!isRabdi ? `
        <div class="p-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-md text-[12.5px] text-[#92400E] flex items-center justify-between">
          <span>MetaMask is not on <strong>Rabdi Testnet (Chain ID 7794095)</strong>.</span>
          <button onclick="handleSwitchToRabdi()" class="px-2.5 py-1 bg-[#D97706] hover:bg-[#B45309] text-white text-[11px] font-semibold rounded cursor-pointer">
            Switch to Rabdi
          </button>
        </div>
      ` : ''}

      <form onsubmit="handlePostTask(event)" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Task Title *</label>
          <input
            type="text"
            name="title"
            required
            placeholder="e.g. Audit DeFi Vault smart contract for reentrancy & rounding vulnerabilities"
            class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Security Category *</label>
            <select
              name="category"
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
            >
              <option value="smart_contract_audit">Smart Contract Audit</option>
              <option value="application_testing">Application Testing</option>
              <option value="codebase_security">Codebase Security Check</option>
              <option value="prompt_optimization">Prompt Optimization</option>
              <option value="prompt_engineering">Prompt Engineering</option>
            </select>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Budget Range / Currency *</label>
            <input
              type="text"
              name="budget_range"
              required
              value="50-100 tGLM"
              placeholder="e.g. 50-100 tGLM or 25 tGLM"
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
            />
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Required Skills / Scope Tags</label>
          <input
            type="text"
            name="required_skills"
            placeholder="e.g. Solidity, Reentrancy, EVM, Fuzzing, Slither"
            class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
          />
          <p class="text-[11px] text-[#8B9C8E] mt-0.5">Comma-separated tags for indexed specialist matching.</p>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Public Scope & Specification *</label>
          <textarea
            name="public_description"
            rows="4"
            required
            placeholder="Describe the target system, repository commit, objectives, and deliverables. Note: This content will be published directly to the Rabdi blockchain."
            class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
          ></textarea>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Budget Type</label>
            <select name="budget_type" class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px]">
              <option value="fixed">Fixed Price</option>
              <option value="milestone">Milestone Based</option>
              <option value="negotiable">Open for Bidding</option>
            </select>
          </div>
          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Turnaround Deadline</label>
            <input type="text" name="deadline" value="5 days" class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px]" />
          </div>
        </div>

        <div class="p-3 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md text-[11.5px] text-[#627566] space-y-1">
          <div class="font-semibold text-[#202820] flex items-center gap-1.5">
            <svg class="w-4 h-4 text-[#176B45]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            On-Chain Publishing Details:
          </div>
          <div>• Posting creates an entity on the <code>guardvane.tasks.v1</code> schema using your connected wallet.</div>
          <div>• Requires a signature in MetaMask (Rabdi testnet). Expiration is set to 7 days.</div>
        </div>

        <div id="post-task-status" class="hidden"></div>

        <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] text-[13px] font-medium rounded-md hover:bg-[#F0F5F1] transition-smooth cursor-pointer">
            Cancel
          </button>
          <button
            type="submit"
            id="post-task-submit-btn"
            class="px-5 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-2 cursor-pointer"
          >
            <span>Sign & Publish to Rabdi</span>
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
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
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="text-[16px] font-semibold text-[#202820]">Submit Specialist Bid</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#EAF5EE] text-[#176B45] border border-[#CDE5D5]">Arkiv bids.v1</span>
          </div>
          <p class="text-[12px] text-[#627566] mt-0.5">Bid record expires automatically after 48 hours on Rabdi testnet.</p>
        </div>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <!-- Task Context Summary -->
      <div class="p-3.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-lg space-y-1.5">
        <div class="flex items-center justify-between text-[11px] font-mono text-[#627566]">
          <span>Task: ${escapeHtml(task.task_id || taskId)}</span>
          <span>Budget: <strong class="text-[#202820]">${escapeHtml(task.budget_range || 'Open')}</strong></span>
        </div>
        <div class="text-[14px] font-semibold text-[#202820]">${escapeHtml(task.title || 'Security Audit Task')}</div>
        <div class="text-[12px] text-[#445246] line-clamp-2">${escapeHtml(task.public_description || '')}</div>
      </div>

      ${!isRabdi ? `
        <div class="p-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-md text-[12.5px] text-[#92400E] flex items-center justify-between">
          <span>MetaMask is not on <strong>Rabdi Testnet (Chain ID 7794095)</strong>.</span>
          <button onclick="handleSwitchToRabdi()" class="px-2.5 py-1 bg-[#D97706] hover:bg-[#B45309] text-white text-[11px] font-semibold rounded cursor-pointer">
            Switch to Rabdi
          </button>
        </div>
      ` : ''}

      <form onsubmit="handleSubmitBid(event, '${taskId}')" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Proposed Price (tGLM) *</label>
            <input
              type="number"
              step="0.01"
              min="0.01"
              name="proposed_price"
              required
              value="25.00"
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
            />
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Estimated Turnaround *</label>
            <input
              type="text"
              name="estimated_duration"
              required
              value="3 days"
              placeholder="e.g. 48 hours or 3 days"
              class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
            />
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Proposal Summary & Methodology *</label>
          <textarea
            name="proposal_summary"
            rows="4"
            required
            placeholder="Detail your auditing tools, automated coverage, manual review methodology, and deliverables..."
            class="w-full px-3 py-2 border border-[#CBD7CE] rounded-md text-[13px] text-[#202820] focus:outline-none focus:border-[#176B45]"
          ></textarea>
        </div>

        <div id="submit-bid-status" class="hidden"></div>

        <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] text-[13px] font-medium rounded-md hover:bg-[#F0F5F1] transition-smooth cursor-pointer">
            Cancel
          </button>
          <button
            type="submit"
            id="submit-bid-btn"
            class="px-5 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-2 cursor-pointer"
          >
            <span>Sign & Submit Bid</span>
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
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
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <div>
          <div class="flex items-center gap-2">
            <h3 class="text-[16px] font-semibold text-[#202820]">Specialist Bids & Awards</h3>
            <span class="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#EAF5EE] text-[#176B45] border border-[#CDE5D5]">Arkiv Rabdi</span>
          </div>
          <p class="text-[12px] text-[#627566] mt-0.5">Task ID: <code class="font-mono text-[#202820]">${escapeHtml(taskId)}</code></p>
        </div>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <!-- Task Context Header -->
      <div class="p-3.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-lg space-y-1">
        <div class="flex items-center justify-between text-xs">
          <span class="font-medium text-[#176B45] uppercase tracking-wider text-[11px]">${formatCategoryName(task.category || '')}</span>
          <span class="font-mono text-[11px] text-[#627566]">Budget: <strong class="text-[#202820]">${escapeHtml(task.budget_range || 'Negotiable')}</strong></span>
        </div>
        <h4 class="text-[14px] font-semibold text-[#202820]">${escapeHtml(task.title || 'Security Audit')}</h4>
        <div class="text-[11.5px] text-[#627566] flex items-center gap-2 pt-0.5">
          <span>Poster:</span>
          <a href="https://explorer.rabdi.db-chain.testnet.arkiv.network/address/${task.customer_wallet}" target="_blank" class="font-mono text-[#176B45] hover:underline">
            ${task.customer_wallet ? (task.customer_wallet.substring(0, 8) + '...' + task.customer_wallet.substring(task.customer_wallet.length - 4)) : 'Unknown'}
          </a>
          ${isTaskOwner ? '<span class="px-1.5 py-0.2 rounded bg-[#EAF5EE] text-[#176B45] font-semibold text-[10px] font-mono">TASK OWNER</span>' : ''}
          <span class="ml-auto font-mono text-[11px] capitalize px-2 py-0.5 rounded border ${task.status === 'open' ? 'bg-[#EAF5EE] text-[#176B45] border-[#CDE5D5]' : 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]'}">
            ${escapeHtml(task.status || 'open')}
          </span>
        </div>
      </div>

      <div id="award-action-status" class="hidden"></div>

      <!-- Bids List -->
      <div class="space-y-3">
        <div class="flex items-center justify-between text-[13px] font-medium text-[#202820]">
          <span>Proposals from Specialists (${bids.length})</span>
          ${(task.status === 'open' && !isTaskOwner) ? `
            <button onclick="openSubmitBidModal('${taskId}')" class="px-3 py-1 bg-[#176B45] hover:bg-[#115638] text-white text-[11.5px] font-medium rounded transition-smooth cursor-pointer">
              + Submit a Bid
            </button>
          ` : ''}
        </div>

        ${isLoading ? `
          <div class="p-8 text-center text-[#627566] text-xs flex items-center justify-center gap-2">
            <div class="w-4 h-4 border-2 border-[#176B45] border-t-transparent rounded-full animate-spin"></div>
            <span>Querying Arkiv (guardvane.bids.v1) on Rabdi testnet...</span>
          </div>
        ` : bids.length > 0 ? `
          <div class="space-y-3 max-h-80 overflow-y-auto pr-1">
            ${bids.map(b => {
              const shortSpecialist = b.specialist_wallet ? (b.specialist_wallet.substring(0, 6) + '...' + b.specialist_wallet.substring(b.specialist_wallet.length - 4)) : 'Anonymous';
              const shortBidKey = b.entity_key ? (b.entity_key.substring(0, 10) + '...' + b.entity_key.substring(b.entity_key.length - 6)) : '';
              const isMyBid = currentWallet && b.specialist_wallet && (b.specialist_wallet.toLowerCase() === currentWallet);

              return `
                <div class="p-4 bg-white border border-[#E2E9E3] rounded-lg shadow-2xs hover:border-[#176B45] transition-smooth space-y-2.5">
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                      <a href="https://explorer.rabdi.db-chain.testnet.arkiv.network/address/${b.specialist_wallet}" target="_blank" class="font-mono text-[12px] font-semibold text-[#176B45] hover:underline">
                        ${shortSpecialist}
                      </a>
                      ${isMyBid ? '<span class="px-1.5 py-0.2 rounded bg-[#EFF6FF] text-[#1E40AF] text-[9.5px] font-semibold font-mono">YOUR BID</span>' : ''}
                    </div>

                    <div class="flex items-center gap-2">
                      <span class="px-2 py-0.5 rounded text-[11.5px] font-bold font-mono bg-[#EAF5EE] text-[#176B45]">
                        ${b.proposed_price} tGLM
                      </span>
                      <span class="text-[11.5px] text-[#627566]">(${escapeHtml(b.estimated_duration)})</span>
                    </div>
                  </div>

                  <p class="text-[12.5px] text-[#445246] leading-relaxed">${escapeHtml(b.proposal_summary)}</p>

                  <div class="pt-2 border-t border-[#E2E9E3] flex items-center justify-between text-[11px] text-[#8B9C8E]">
                    <span title="Bid Entity Key: ${b.entity_key}">Key: <code class="font-mono text-[#627566]">${shortBidKey || 'N/A'}</code></span>

                    ${(isTaskOwner && task.status === 'open') ? `
                      <button
                        onclick="handleAcceptBid('${taskId}', '${b.entity_key}', '${b.specialist_wallet}')"
                        class="px-3 py-1 bg-[#176B45] hover:bg-[#115638] text-white text-[11.5px] font-medium rounded shadow-2xs transition-smooth cursor-pointer"
                      >
                        Accept & Award Task 🎯
                      </button>
                    ` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        ` : `
          <div class="p-8 bg-[#FAFBF9] border border-[#E2E9E3] rounded-lg text-center space-y-2">
            <div class="text-[13px] font-medium text-[#202820]">No bids submitted yet for this task</div>
            <p class="text-[12px] text-[#627566] max-w-sm mx-auto">
              Specialist proposals will appear here as soon as security researchers inspect the task on Rabdi.
            </p>
            ${(!isTaskOwner && task.status === 'open') ? `
              <div class="pt-2">
                <button onclick="openSubmitBidModal('${taskId}')" class="px-3.5 py-1.5 bg-[#176B45] text-white text-[12px] font-medium rounded cursor-pointer">
                  Submit the First Bid
                </button>
              </div>
            ` : ''}
          </div>
        `}
      </div>

      <div class="pt-3 border-t border-[#E2E9E3] flex justify-end">
        <button onclick="closeModal()" class="px-4 py-2 bg-[#202820] text-white text-[12.5px] font-medium rounded-md hover:bg-black transition-smooth">
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

function toggleZeroGMode(isZeroG) {
  const hiddenInput = document.getElementById('is_zero_g_wallet_hidden');
  if (hiddenInput) {
    hiddenInput.value = isZeroG ? 'true' : 'false';
  }
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
  const isZeroGWallet = (form.is_zero_g_wallet?.value === 'true') || !!form.is_zero_g_wallet?.checked;

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
        is_zero_g_wallet: isZeroGWallet,
        customer_id: STATE.user.id,
        customer_name: STATE.user.name
      })
    });

    closeModal();
    await loadInitialData();
    navigateTo('my_requests');
  } catch (err) {
    alert(`Order submission error: ${err.message}`);
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
    alert(res.message || 'Ticket submitted successfully to specialist.');
    STATE.activeTicketFormOrderId = null;
    await loadInitialData();
    const updatedReport = STATE.data.reports.find(r => r.id === reportId || r.order_id === orderId);
    if (updatedReport) {
      openModal('report_viewer', updatedReport);
    } else {
      closeModal();
    }
  } catch (err) {
    alert(`Failed to submit ticket: ${err.message}`);
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
    alert(`Failed to update status: ${err.message}`);
  }
}

async function handleDeliverSubmit(e, orderId) {
  e.preventDefault();
  const form = e.target;
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
  } catch (err) {
    alert(`Delivery failed: ${err.message}`);
  }
}

async function handleBecomeProvider(e) {
  e.preventDefault();
  const form = e.target;
  const cats = Array.from(form.querySelectorAll('input[name="cat"]:checked')).map(el => el.value);
  const skills = form.skills_raw.value.split(',').map(s => s.trim()).filter(Boolean);

  const payload = {
    display_name: form.display_name.value,
    title: form.title.value,
    provider_type: form.provider_type.value,
    description: form.description.value,
    skills: skills,
    categories: cats,
    wallet_address: form.wallet_address.value || null,
    portfolio_url: form.portfolio_url.value || null,
    endpoint_url: form.endpoint_url?.value || null,
    io_format: form.io_format?.value || 'JSON / Prompt-in, Hardened-out',
    x402_supported: form.provider_type.value === 'automated',
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
        title: form.service_title.value,
        description: `Security assessment delivered by ${prov.display_name}.`,
        category: cats[0] || 'ai_security',
        price: parseFloat(form.service_price.value) || 50.0,
        currency: 'USD',
        estimated_delivery: form.service_delivery.value,
        supported_tasks: ['prompt_injection', 'system_prompt_audit'],
        execution_type: prov.provider_type === 'automated' ? 'automated' : 'manual',
        provider_id: prov.id
      })
    });

    alert('Provider profile and initial service registered successfully!');
    STATE.user.activeProviderId = prov.id;
    STATE.user.role = 'provider';
    await loadInitialData();
    navigateTo('provider_workspace');
  } catch (err) {
    alert(`Registration failed: ${err.message}`);
  }
}

async function handleAddServiceSubmit(e, providerId) {
  e.preventDefault();
  const form = e.target;
  try {
    await apiFetch('/marketplace/services', {
      method: 'POST',
      body: JSON.stringify({
        title: form.title.value,
        description: form.description.value,
        category: 'ai_security',
        price: parseFloat(form.price.value),
        currency: 'USD',
        estimated_delivery: form.estimated_delivery.value,
        execution_type: form.execution_type.value,
        provider_id: providerId
      })
    });
    closeModal();
    await loadInitialData();
  } catch (err) {
    alert(`Service creation failed: ${err.message}`);
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
    alert(`Failed to save prompt: ${err.message}`);
  }
}

async function handleDeletePrompt(promptId) {
  if (!confirm('Are you sure you want to delete this saved prompt?')) return;
  try {
    await apiFetch(`/marketplace/prompts/${promptId}`, { method: 'DELETE' });
    await loadInitialData();
  } catch (err) {
    alert(`Delete failed: ${err.message}`);
  }
}

// ---------------------------------------------------------------------------
// Arkiv Marketplace Action Handlers (MetaMask Browser Signing + Rabdi)
// ---------------------------------------------------------------------------

function openPostTaskModal() {
  if (!STATE.auth.walletAddress) {
    alert('Please connect your MetaMask wallet first to publish an on-chain task to Rabdi testnet.');
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
    alert('Wallet not connected. Please connect MetaMask.');
    return;
  }

  if (typeof window === 'undefined' || !window.ArkivModule) {
    alert('Arkiv SDK browser bundle not loaded. Please reload the page.');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }

  if (statusEl) {
    statusEl.classList.remove('hidden');
    statusEl.innerHTML = `
      <div class="p-3 bg-[#EAF5EE] border border-[#CDE5D5] rounded-md text-[12.5px] text-[#176B45] flex items-center gap-2">
        <div class="w-4 h-4 border-2 border-[#176B45] border-t-transparent rounded-full animate-spin shrink-0"></div>
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
        <div class="p-3 bg-[#EAF5EE] border border-[#CDE5D5] rounded-md text-[12.5px] text-[#176B45] space-y-1">
          <div class="font-semibold">✓ Confirmed on Rabdi! Reconciling with Guardvane...</div>
          <div class="text-[11px] font-mono break-all">Tx: ${txHash}</div>
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

    alert(`Task successfully published to Arkiv!\nEntity Key: ${entityKey}\nTx Hash: ${txHash}`);
    closeModal();
    await loadArkivTasks(true);
    navigateTo('arkiv_tasks');
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
    alert('Please connect your MetaMask wallet first to submit a specialist bid.');
    connectAndSignWithMetaMask();
    return;
  }
  const task = (STATE.arkiv.tasks || []).find(t => t.task_id === taskId);
  if (task && task.customer_wallet && task.customer_wallet.toLowerCase() === STATE.auth.walletAddress.toLowerCase()) {
    alert('You cannot submit a bid on your own security task.');
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
    alert('Please connect your MetaMask wallet.');
    return;
  }

  if (typeof window === 'undefined' || !window.ArkivModule) {
    alert('Arkiv SDK browser module not loaded. Please reload.');
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-60', 'cursor-not-allowed');
  }

  if (statusEl) {
    statusEl.classList.remove('hidden');
    statusEl.innerHTML = `
      <div class="p-3 bg-[#EAF5EE] border border-[#CDE5D5] rounded-md text-[12.5px] text-[#176B45] flex items-center gap-2">
        <div class="w-4 h-4 border-2 border-[#176B45] border-t-transparent rounded-full animate-spin shrink-0"></div>
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

    alert(`Bid successfully submitted on Arkiv!\nEntity Key: ${entityKey}\nTx Hash: ${txHash}`);
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
      <div class="p-3 bg-[#EAF5EE] border border-[#CDE5D5] rounded-md text-[12.5px] text-[#176B45] flex items-center gap-2">
        <div class="w-4 h-4 border-2 border-[#176B45] border-t-transparent rounded-full animate-spin shrink-0"></div>
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

    alert(`Task successfully awarded on Arkiv!\nEntity Key: ${entityKey}\nTx Hash: ${txHash}`);
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
    alert('Please enter a prompt to analyze.');
    return;
  }

  // Prevent stale results and set explicit loading state
  resultsBox.classList.remove('hidden');
  resultsBox.innerHTML = `
    <div class="flex items-center gap-2.5 p-3 text-[12.5px] text-[#176B45] font-medium bg-[#EAF5EE] rounded border border-[#CDE5D5]">
      <div class="w-4 h-4 border-2 border-[#176B45] border-t-transparent rounded-full animate-spin shrink-0"></div>
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
        <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-2">
          <div class="flex items-center gap-2">
            <strong class="text-[#202820]">Analysis Findings</strong>
            ${taskClass.category ? `
              <span class="px-2 py-0.5 bg-[#FAFBF9] text-[#627566] border border-[#E2E9E3] text-[11px] font-mono rounded">
                task: ${escapeHtml(taskClass.category)}
              </span>
            ` : ''}
          </div>
          <span class="text-[11px] px-2.5 py-0.5 rounded font-bold uppercase tracking-wider ${isMalicious ? 'bg-[#FEE2E2] text-[#991B1B] border border-[#FECACA]' : 'bg-[#EAF5EE] text-[#176B45] border border-[#CDE5D5]'}">
            ${escapeHtml(riskCat)}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="bg-white p-3 rounded-lg border border-[#E2E9E3]">
            <div class="text-[11px] font-medium text-[#627566]">Injection Probability</div>
            <div class="text-xl font-bold font-mono ${probNum >= 0.5 ? 'text-[#991B1B]' : 'text-[#202820]'} mt-0.5">
              ${probPct}%
            </div>
            <div class="text-[10.5px] text-[#8B9C8E] mt-0.5">
              ${isMalicious ? 'Adversarial pattern detected' : 'Within benign distribution'}
            </div>
          </div>

          <div class="bg-white p-3 rounded-lg border border-[#E2E9E3]">
            <div class="text-[11px] font-medium text-[#627566]">Sensitive Credentials</div>
            <div class="text-xl font-bold font-mono ${hasSecrets ? 'text-[#991B1B]' : 'text-[#176B45]'} mt-0.5">
              ${sCount} detected
            </div>
            <div class="text-[10.5px] text-[#8B9C8E] mt-0.5">
              ${hasSecrets ? 'API keys / secrets found' : 'No credentials detected'}
            </div>
          </div>
        </div>

        ${hasSecrets && Array.isArray(sData.findings) && sData.findings.length > 0 ? `
          <div class="p-2.5 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[11.5px] space-y-1">
            <div class="font-semibold text-[#991B1B]">Detected Secrets:</div>
            ${sData.findings.map(f => `
              <div class="font-mono text-[#7F1D1D]">${escapeHtml(f.description)}: ${escapeHtml(f.redacted)}</div>
            `).join('')}
          </div>
        ` : ''}

        <div>
          <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider mb-1.5">Detected Risks (OWASP LLM)</div>
          <div class="flex flex-wrap gap-1.5">
            ${(appRisks.detected_risks || []).length > 0 ? (appRisks.detected_risks || []).map(r => `
              <span class="px-2 py-0.5 bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] text-[11px] font-medium rounded">
                ${escapeHtml(r)}
              </span>
            `).join('') : '<span class="text-[#176B45] font-medium">No critical application risk categories triggered.</span>'}
          </div>
        </div>

        <div class="pt-2 border-t border-[#E2E9E3] flex justify-between items-center">
          <span class="text-[11px] text-[#8B9C8E]">Evaluated by Guardvane Local Security Engine</span>
          <button onclick="closeModal(); openModal('request_review', { promptText: '${escapeForAttr(text)}' })" class="px-3 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded transition-smooth">
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
    alert('Please enter a prompt to evaluate and harden.');
    return;
  }

  resultsBox.classList.remove('hidden');
  resultsBox.innerHTML = `
    <div class="flex items-center gap-2.5 p-3 text-[12.5px] text-[#176B45] font-medium bg-[#EAF5EE] rounded border border-[#CDE5D5]">
      <div class="w-4 h-4 border-2 border-[#176B45] border-t-transparent rounded-full animate-spin shrink-0"></div>
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
    let statusBadgeClass = 'bg-[#EAF5EE] text-[#176B45] border-[#CDE5D5]';
    if (isFailed) {
      statusLabel = '0G reasoning failed';
      statusBadgeClass = 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
    } else if (isLocalOnly) {
      statusLabel = 'Local-only analysis';
      statusBadgeClass = 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]';
    } else if (isCached) {
      statusLabel = '0G reasoning completed (Cached • 0 Credits)';
      statusBadgeClass = 'bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]';
    }

    // Severity color helper
    const getSevBadge = (sev) => {
      const s = String(sev || 'medium').toLowerCase();
      if (s === 'critical') return 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
      if (s === 'high') return 'bg-[#FFEDD5] text-[#C2410C] border-[#FED7AA]';
      if (s === 'medium') return 'bg-[#FEF3C7] text-[#92400E] border-[#FDE68A]';
      return 'bg-[#EFF6FF] text-[#1E40AF] border-[#BFDBFE]';
    };

    if (isFailed) {
      // 0G Reasoning Failed View
      resultsBox.innerHTML = `
        <div class="space-y-3.5 text-[12.5px]">
          <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-2">
            <span class="px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border ${statusBadgeClass}">
              ${statusLabel}
            </span>
            <span class="text-[11px] font-mono text-[#627566]">${meta.duration_ms ? `${meta.duration_ms}ms` : '0ms'}</span>
          </div>

          <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12px] text-[#991B1B] space-y-1.5">
            <div class="font-semibold flex items-center gap-1.5">
              <span>⚠️ 0G Private Computer AI Reasoning Encountered an Error</span>
            </div>
            <p class="font-mono text-[11.5px]">${escapeHtml(data.error || meta.error || '0G node returned an invalid response structure or network timeout.')}</p>
            <div class="text-[11px] text-[#7F1D1D] pt-1">
              Guardvane does NOT silently substitute local heuristics for missing 0G AI reasoning. You may retry the remote inference below.
            </div>
          </div>

          <!-- Preserved Local Preprocessing Scan (if available) -->
          ${data.security_analysis ? `
            <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-2">
              <div class="text-[11px] font-semibold text-[#627566] uppercase tracking-wider">Preserved Local Preprocessing Signals</div>
              <div class="grid grid-cols-2 gap-2 text-[12px]">
                <div><span class="text-[#8B9C8E]">Injection Score:</span> <strong>${(data.security_analysis.prompt_security?.malicious_probability * 100 || 0).toFixed(1)}%</strong></div>
                <div><span class="text-[#8B9C8E]">Detected Secrets:</span> <strong>${data.security_analysis.sensitive_data?.findings_count || 0}</strong></div>
              </div>
            </div>
          ` : ''}

          <!-- Actions -->
          <div class="pt-2 border-t border-[#E2E9E3] flex justify-between items-center">
            <button onclick="executeQuickOptimize(null, true)" class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded transition-smooth inline-flex items-center gap-1.5 cursor-pointer">
              <span>🔄</span> Retry 0G Reasoning
            </button>
            <button onclick="navigator.clipboard.writeText(document.getElementById('quick-prompt-input').value); alert('Copied original prompt!');" class="text-xs text-[#627566] hover:underline font-medium cursor-pointer">
              Copy Original Prompt 📋
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
        <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-2">
          <div class="flex items-center justify-between">
            <span class="px-2.5 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border ${statusBadgeClass}">
              ${statusLabel}
            </span>
            <div class="flex items-center gap-3">
              <span class="text-[11px] font-mono text-[#627566]">
                ${meta.duration_ms ? `${meta.duration_ms}ms` : '0ms'}
              </span>
              <button onclick="const el = document.getElementById('inference-telemetry-drawer'); el.classList.toggle('hidden');" class="text-[11px] text-[#176B45] hover:underline cursor-pointer font-medium">
                View Inference Details ℹ️
              </button>
            </div>
          </div>

          <!-- Inference Details Collapsible Drawer -->
          <div id="inference-telemetry-drawer" class="hidden p-2.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded mt-2 text-[11px] font-mono space-y-1">
            <div class="grid grid-cols-2 gap-2 text-[#445246]">
              <div><span class="text-[#8B9C8E]">Provider:</span> ${escapeHtml(isLocalOnly ? 'Local Deterministic Rules' : (meta.provider || '0G Private Computer'))}</div>
              <div><span class="text-[#8B9C8E]">Model:</span> ${escapeHtml(isLocalOnly ? 'N/A (Local Heuristic Scan)' : (meta.model || 'glm-5.2'))}</div>
              <div><span class="text-[#8B9C8E]">Trust Mode:</span> ${escapeHtml(isLocalOnly ? 'N/A' : (meta.trust_mode || 'verified'))}</div>
              <div><span class="text-[#8B9C8E]">Request ID:</span> <span class="truncate inline-block max-w-[120px]" title="${escapeForAttr(meta.request_id || 'N/A')}">${escapeHtml(meta.request_id || 'N/A')}</span></div>
              <div><span class="text-[#8B9C8E]">Total Tokens:</span> ${meta.total_tokens ? meta.total_tokens : (meta.usage?.total_tokens ?? 'N/A')}</div>
              <div><span class="text-[#8B9C8E]">Latency:</span> ${meta.duration_ms || 0}ms</div>
            </div>
            <div class="text-[10px] text-[#8B9C8E] pt-1 border-t border-[#E2E9E3]">
              * Gateway Request ID tracks transport routing; it is not a cryptographic attestation proof. Configured model is only verified upon real provider response.
            </div>
          </div>
        </div>

        <!-- 1. Task Understanding -->
        <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-2">
          <div class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider flex items-center justify-between">
            <span>1. Task Understanding</span>
            <span class="text-[11px] text-[#627566] font-mono font-normal">${escapeHtml(taskUnd.application_type || 'Application Specification')}</span>
          </div>
          <div class="text-[12px] text-[#202820]">
            <strong>User Intent:</strong> ${escapeHtml(taskUnd.user_intent || data.preserved_intent || 'Preserved development intention.')}
          </div>
          ${Array.isArray(taskUnd.technologies) && taskUnd.technologies.length > 0 ? `
            <div class="flex flex-wrap gap-1 pt-1">
              <span class="text-[10.5px] text-[#8B9C8E] font-medium mr-1">Technologies:</span>
              ${taskUnd.technologies.map(t => `
                <span class="px-2 py-0.5 bg-[#FAFBF9] border border-[#CBD7CE] text-[#374151] rounded text-[10.5px] font-mono">
                  ${escapeHtml(t)}
                </span>
              `).join('')}
            </div>
          ` : ''}
        </div>

        <!-- 2. Security Risk Assessment -->
        <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider">2. Security Risk Assessment</span>
            <span class="px-2 py-0.5 rounded text-[11px] font-bold uppercase tracking-wider border ${getSevBadge(secAnalysis.overall_risk || data.overall_risk || 'Low')}">
              ${escapeHtml(secAnalysis.overall_risk || data.overall_risk || 'Low')} Risk
            </span>
          </div>
          <p class="text-[12px] text-[#445246]">
            ${escapeHtml(data.reasoning?.contextual_summary || 'Contextual threat analysis performed on requested application parameters.')}
          </p>
        </div>

        <!-- 3. Vulnerability Findings -->
        <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-2.5">
          <div class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider">
            3. Vulnerability Findings (${findings.length})
          </div>
          ${findings.length > 0 ? `
            <div class="space-y-2">
              ${findings.map((f, i) => `
                <div class="p-2.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md text-[11.5px] space-y-1">
                  <div class="flex items-center justify-between">
                    <strong class="text-[#202820] text-[12px]">${i+1}. ${escapeHtml(f.vulnerability)}</strong>
                    <div class="flex items-center gap-1.5">
                      <span class="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${getSevBadge(f.severity)}">
                        ${escapeHtml(f.severity)}
                      </span>
                      ${f.confidence ? `<span class="text-[10px] font-mono text-[#8B9C8E]">(${(f.confidence * 100).toFixed(0)}% conf)</span>` : ''}
                    </div>
                  </div>
                  ${f.evidence ? `<div class="text-[11px] text-[#627566] italic">"${escapeHtml(f.evidence)}"</div>` : ''}
                  <div class="text-[#445246]">${escapeHtml(f.explanation)}</div>
                  ${f.recommendation ? `
                    <div class="text-[11px] text-[#176B45] pt-0.5">
                      <strong>Mitigation:</strong> ${escapeHtml(f.recommendation)}
                    </div>
                  ` : ''}
                </div>
              `).join('')}
            </div>
          ` : `
            <div class="text-[12px] text-[#176B45] font-medium">No critical application vulnerabilities detected in this request.</div>
          `}
        </div>

        <!-- 4. Attack Scenarios -->
        ${findings.some(f => f.attack_scenario) ? `
          <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-2">
            <div class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider">4. Attack Scenarios</div>
            <div class="space-y-1.5">
              ${findings.filter(f => f.attack_scenario).map(f => `
                <div class="p-2 bg-[#FFFBEB] border border-[#FDE68A] rounded text-[11.5px] text-[#92400E] space-y-0.5">
                  <strong>${escapeHtml(f.vulnerability)}:</strong>
                  <div>${escapeHtml(f.attack_scenario)}</div>
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- 5. Recommended Security Controls -->
        ${missingReqs.length > 0 ? `
          <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-1.5">
            <div class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider">5. Recommended Security Controls</div>
            <ul class="list-disc list-inside space-y-1 text-[12px] text-[#445246]">
              ${missingReqs.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}

        <!-- 6. Hardened Prompt -->
        <div class="space-y-1.5">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider">6. Hardened Prompt Specification</span>
            <div class="flex items-center gap-2">
              <button onclick="navigator.clipboard.writeText(document.getElementById('opt-prompt-result-text').innerText); alert('Copied hardened prompt to clipboard!');" class="text-xs text-[#176B45] hover:underline font-medium cursor-pointer">
                Copy Hardened Prompt 📋
              </button>
            </div>
          </div>
          <pre id="opt-prompt-result-text" class="p-3 bg-white border border-[#CBD7CE] rounded-lg text-[12px] font-mono text-[#202820] max-h-64 overflow-y-auto whitespace-pre-wrap select-all">${escapeHtml(data.optimized_prompt || data.hardened_prompt || '')}</pre>
        </div>

        <!-- 7. Changes Made -->
        ${changesMade.length > 0 ? `
          <div class="p-3 bg-white border border-[#E2E9E3] rounded-lg space-y-1.5">
            <div class="text-[11px] font-semibold text-[#176B45] uppercase tracking-wider">7. Changes Made & Rationale</div>
            <div class="space-y-1">
              ${changesMade.map(c => `
                <div class="text-[11.5px] text-[#445246]">
                  <span class="font-semibold text-[#202820]">• ${escapeHtml(c.change || c)}:</span> ${escapeHtml(c.reason || 'Embedded security requirement')}
                </div>
              `).join('')}
            </div>
          </div>
        ` : ''}

        <!-- 8. Assumptions and Remaining Risks -->
        ${(assumptions.length > 0 || remainingRisks.length > 0) ? `
          <div class="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            ${assumptions.length > 0 ? `
              <div class="p-2.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md text-[11.5px] space-y-1">
                <div class="font-semibold text-[#627566] text-[11px] uppercase tracking-wider">Assumptions</div>
                <ul class="list-disc list-inside space-y-0.5 text-[#445246]">
                  ${assumptions.map(a => `<li>${escapeHtml(a)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
            ${remainingRisks.length > 0 ? `
              <div class="p-2.5 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md text-[11.5px] space-y-1">
                <div class="font-semibold text-[#991B1B] text-[11px] uppercase tracking-wider">Remaining Residual Risks</div>
                <ul class="list-disc list-inside space-y-0.5 text-[#7F1D1D]">
                  ${remainingRisks.map(r => `<li>${escapeHtml(r)}</li>`).join('')}
                </ul>
              </div>
            ` : ''}
          </div>
        ` : ''}

        <!-- Footer Control Actions -->
        <div class="pt-2 border-t border-[#E2E9E3] flex flex-wrap justify-between items-center gap-2">
          <div class="flex items-center gap-2">
            <button onclick="navigator.clipboard.writeText(document.getElementById('quick-prompt-input').value); alert('Copied original prompt!');" class="px-2.5 py-1.5 bg-white border border-[#CBD7CE] hover:border-[#176B45] text-[#202820] text-[11.5px] font-medium rounded transition-smooth cursor-pointer">
              Copy Original Prompt 📋
            </button>
            <button onclick="executeQuickOptimize(null, true)" class="px-2.5 py-1.5 bg-white border border-[#CBD7CE] hover:border-[#176B45] text-[#202820] text-[11.5px] font-medium rounded transition-smooth cursor-pointer">
              Retry 0G Reasoning 🔄
            </button>
          </div>
          <button onclick="saveOptimizedPromptFromModal('${escapeForAttr(data.optimized_prompt || data.hardened_prompt || '')}')" class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded transition-smooth cursor-pointer">
            Save to My Prompts 💾
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
      <div class="p-3 bg-[#FEF2F2] border border-[#FCA5A5] rounded-md text-[12.5px] text-[#991B1B] space-y-1.5">
        <div class="font-semibold flex items-center justify-between">
          <span>0G AI Reasoning Request Failed</span>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase border bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]">
            0G reasoning failed
          </span>
        </div>
        <p class="font-mono text-[11.5px]">${escapeHtml(err.message || 'An unexpected error occurred during 0G reasoning.')}</p>
        <div class="pt-2">
          <button onclick="executeQuickOptimize(null, true)" class="px-3 py-1 bg-[#991B1B] hover:bg-[#7F1D1D] text-white text-[11px] font-medium rounded cursor-pointer">
            Retry 0G Reasoning 🔄
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
    alert('Hardened prompt saved to your private library!');
    closeModal();
    await loadInitialData();
    navigateTo('my_prompts');
  } catch (e) {
    alert(`Failed to save prompt: ${e.message}`);
  }
}

function viewReport(reportId) {
  const report = STATE.data.reports.find(r => r.id === reportId);
  if (report) {
    openModal('report_viewer', report);
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

// Initialize on DOM load
window.addEventListener('DOMContentLoaded', async () => {
  const hasSession = await checkAuthSession();
  if (hasSession) {
    await loadInitialData();
  } else {
    renderApp();
  }
});
