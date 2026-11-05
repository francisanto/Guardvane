/**
 * PromptShield Marketplace — Professional AI Developer Console
 * Visual Inspiration: Claude Console (platform.claude.com/dashboard)
 * Green Palette: #176B45 (primary), #EAF5EE (surface/active), #F7F9F7 (background)
 */

const STATE = {
  activeView: 'dashboard',
  selectedProviderId: null,
  selectedServiceId: null,
  selectedOrderId: null,
  selectedReportId: null,
  user: {
    id: 'francis',
    name: 'Francis',
    org: "francis's Dev Org",
    role: 'customer', // 'customer' or 'provider'
    activeProviderId: 'prov_elena'
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
  activeModal: null,
  modalPayload: null,
  loading: false
};

// ---------------------------------------------------------------------------
// API Helpers
// ---------------------------------------------------------------------------

async function apiFetch(endpoint, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    'X-User-Id': STATE.user.role === 'provider' ? STATE.user.activeProviderId : STATE.user.id,
    'X-User-Role': STATE.user.role,
    ...(options.headers || {})
  };

  try {
    const res = await fetch(endpoint, { ...options, headers });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errData.detail || `API error (${res.status})`);
    }
    return await res.json();
  } catch (err) {
    console.error(`Fetch error at ${endpoint}:`, err);
    throw err;
  }
}

// ---------------------------------------------------------------------------
// Initial Data Loading
// ---------------------------------------------------------------------------

async function loadInitialData() {
  STATE.loading = true;
  renderApp();

  try {
    const [stats, providers, services, orders, reports, prompts, integrations] = await Promise.all([
      apiFetch('/marketplace/stats').catch(() => null),
      apiFetch('/marketplace/providers').catch(() => []),
      apiFetch('/marketplace/services').catch(() => []),
      apiFetch('/marketplace/orders').catch(() => []),
      apiFetch('/marketplace/reports').catch(() => []),
      apiFetch('/marketplace/prompts').catch(() => []),
      apiFetch('/marketplace/integrations/status').catch(() => null)
    ]);

    STATE.data.stats = stats;
    STATE.data.providers = providers;
    STATE.data.services = services;
    STATE.data.orders = orders;
    STATE.data.reports = reports;
    STATE.data.prompts = prompts;
    STATE.data.integrations = integrations;
  } catch (err) {
    console.error("Failed to load initial marketplace data", err);
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
// Sidebar Component
// ---------------------------------------------------------------------------

function renderSidebar() {
  const isSpecialist = STATE.user.role === 'provider';

  return `
    <aside class="w-64 bg-[#FAFBF9] border-r border-[#E2E9E3] flex flex-col justify-between shrink-0 select-none">
      <!-- Top Brand & Nav -->
      <div class="flex flex-col">
        <!-- Logo Header -->
        <div class="h-16 flex items-center px-6 border-b border-[#E2E9E3] gap-3">
          <div class="w-8 h-8 rounded-lg bg-[#176B45] text-white flex items-center justify-center font-bold shadow-sm">
            <svg class="w-5 h-5 text-emerald-200" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div class="flex flex-col">
            <span class="font-semibold text-[15px] tracking-tight text-[#176B45]">PromptShield</span>
            <span class="text-[11px] text-[#627566] tracking-wide font-medium">SECURITY CONSOLE</span>
          </div>
        </div>

        <!-- Navigation Section: Core -->
        <div class="px-3 py-4 space-y-1">
          <div class="px-3 pb-2 text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Marketplace</div>
          
          <button onclick="navigateTo('dashboard')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'dashboard' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            Dashboard
          </button>

          <button onclick="navigateTo('discover')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'discover' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Discover Specialists
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

        <!-- Navigation Section: Specialist Area -->
        <div class="px-3 py-2 space-y-1 border-t border-[#E2E9E3]/70">
          <div class="px-3 py-1.5 text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Specialist Program</div>

          <button onclick="navigateTo('become_specialist')" class="w-full flex items-center gap-3 px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'become_specialist' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <svg class="w-4 h-4 text-[#2FA36B]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Become a Specialist
          </button>

          <button onclick="navigateTo('workspace')" class="w-full flex items-center justify-between px-3 py-2 rounded-md text-[13.5px] font-medium transition-smooth ${STATE.activeView === 'workspace' ? 'nav-item-active' : 'text-[#445246] hover:bg-[#F0F5F1] hover:text-[#202820]'}">
            <div class="flex items-center gap-3">
              <svg class="w-4 h-4 text-[#627566]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
              <span>Workspace</span>
            </div>
            ${isSpecialist ? '<span class="text-[10px] bg-[#176B45] text-white px-1.5 py-0.5 rounded font-mono">ACTIVE</span>' : '<span class="text-[10px] text-[#8B9C8E]">Pro</span>'}
          </button>
        </div>
      </div>

      <!-- Bottom User Profile & Switcher -->
      <div class="p-4 border-t border-[#E2E9E3] bg-[#F7F9F7]/80">
        <!-- View Role Toggle -->
        <div class="mb-3 px-2 py-1.5 bg-[#EAF5EE] rounded-md flex items-center justify-between text-[11.5px]">
          <span class="text-[#176B45] font-semibold">Mode:</span>
          <div class="flex gap-1">
            <button onclick="switchUserRole('customer')" class="px-2 py-0.5 rounded transition-smooth ${STATE.user.role === 'customer' ? 'bg-[#176B45] text-white font-medium' : 'text-[#445246] hover:text-[#176B45]'}">
              Customer
            </button>
            <button onclick="switchUserRole('provider', 'prov_elena')" class="px-2 py-0.5 rounded transition-smooth ${STATE.user.role === 'provider' ? 'bg-[#176B45] text-white font-medium' : 'text-[#445246] hover:text-[#176B45]'}">
              Specialist
            </button>
          </div>
        </div>

        <!-- User Identity Row -->
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-[#E2E9E3] border border-[#CBD7CE] flex items-center justify-center font-semibold text-[#176B45] text-sm">
            F
          </div>
          <div class="flex flex-col min-w-0">
            <span class="text-[13px] font-semibold text-[#202820] truncate">${STATE.user.name}</span>
            <span class="text-[11px] text-[#627566] truncate">${STATE.user.role === 'provider' ? 'Specialist Workspace' : STATE.user.org}</span>
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
  const titles = {
    dashboard: 'Dashboard',
    discover: 'Discover Specialists',
    provider_detail: 'Specialist Profile',
    become_specialist: 'Become a Specialist',
    workspace: 'Specialist Workspace',
    my_prompts: 'My Prompts & Analyses',
    my_requests: 'My Requests & Orders',
    security_reports: 'Security Reports'
  };

  const currentTitle = titles[STATE.activeView] || 'Console';

  return `
    <header class="h-16 border-b border-[#E2E9E3] bg-[#FAFBF9] px-8 flex items-center justify-between shrink-0 select-none">
      <!-- Breadcrumb & Search -->
      <div class="flex items-center gap-6 min-w-0">
        <div class="flex items-center gap-2 text-[14px]">
          <span class="text-[#627566] font-medium hover:text-[#176B45] cursor-pointer" onclick="navigateTo('dashboard')">PromptShield</span>
          <span class="text-[#8B9C8E]">/</span>
          <span class="text-[#202820] font-semibold">${currentTitle}</span>
        </div>

        <!-- Search Bar with ⌘K -->
        <div class="relative w-80">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[#8B9C8E]">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            id="topbar-search-input"
            type="text"
            placeholder="Search specialists, audits, prompts..."
            value="${STATE.filters.search}"
            oninput="handleGlobalSearch(this.value)"
            class="w-full pl-9 pr-10 py-1.5 bg-[#FFFFFF] border border-[#E2E9E3] rounded-md text-[13px] text-[#202820] placeholder-[#8B9C8E] focus:outline-none focus:border-[#176B45] focus:ring-1 focus:ring-[#176B45] transition-smooth"
          />
          <div class="absolute inset-y-0 right-0 pr-2.5 flex items-center pointer-events-none">
            <kbd class="px-1.5 py-0.5 text-[10px] font-mono text-[#8B9C8E] bg-[#F7F9F7] border border-[#E2E9E3] rounded shadow-xs">⌘K</kbd>
          </div>
        </div>
      </div>

      <!-- Top Right Controls -->
      <div class="flex items-center gap-4">
        <!-- Integration Boundary Readiness Pill -->
        <button onclick="openModal('integrations_info')" class="flex items-center gap-2 px-3 py-1.5 rounded-md border border-[#E2E9E3] bg-[#FFFFFF] text-[12px] font-medium text-[#445246] hover:bg-[#F0F5F1] transition-smooth">
          <span class="w-2 h-2 rounded-full bg-[#2FA36B] animate-soft-pulse"></span>
          <span>Integrations: 4 Ready</span>
        </button>

        <!-- Hedera Wallet Status Placeholder -->
        <div class="flex items-center gap-2 px-3 py-1.5 bg-[#EAF5EE] border border-[#C4E4CE] rounded-md text-[12px] text-[#176B45] font-medium">
          <svg class="w-3.5 h-3.5 text-[#176B45]" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 14.5v-2.1c2.16-.36 3.5-1.78 3.5-3.65 0-2.02-1.52-3.35-4-3.55V5h-2v2.22c-2.31.38-3.7 1.83-3.7 3.69 0 2.05 1.55 3.32 4.2 3.54v2.35c-1.87-.27-2.9-1.25-3.05-2.55H6.4c.15 2.1 1.7 3.55 3.6 3.9V20h2v-2.05c2.37-.36 3.8-1.8 3.8-3.8 0-2.12-1.55-3.4-4.2-3.6v-2.3c1.7.25 2.65 1.15 2.8 2.3h1.55c-.15-1.95-1.5-3.35-3.35-3.7V5h-2v2.25c-2.2.35-3.5 1.7-3.5 3.5 0 1.95 1.45 3.15 4 3.4v2.4c-1.7-.25-2.7-1.15-2.85-2.3H6.4c.15 2 1.6 3.45 3.6 3.8V20h2v-2.05c2.3-.35 3.7-1.75 3.7-3.65 0-2.05-1.5-3.3-4.1-3.5z"/>
          </svg>
          <span class="font-mono">Hedera: 0.0.4829103</span>
        </div>

        <!-- Documentation Link -->
        <a href="/docs" target="_blank" class="text-[13px] font-medium text-[#445246] hover:text-[#176B45] flex items-center gap-1">
          Docs
          <svg class="w-3.5 h-3.5 text-[#8B9C8E]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>

        <!-- Notification Bell -->
        <button class="p-2 text-[#627566] hover:text-[#202820] hover:bg-[#F0F5F1] rounded-md transition-smooth relative">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-[#176B45] rounded-full"></span>
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
        <p class="text-[13px] text-[#627566]">Loading marketplace data...</p>
      </div>
    `;
  }

  switch (STATE.activeView) {
    case 'dashboard':
      return renderDashboardView();
    case 'discover':
      return renderDiscoverView();
    case 'provider_detail':
      return renderProviderDetailView();
    case 'become_specialist':
      return renderBecomeSpecialistView();
    case 'workspace':
      return renderWorkspaceView();
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
// 1. Dashboard Home Page (Claude Console Inspired)
// ---------------------------------------------------------------------------

function renderDashboardView() {
  const stats = STATE.data.stats || {
    registered_specialists_count: 5,
    available_services_count: 5,
    my_requests_count: 3,
    completed_reviews_count: 1,
    human_specialists_count: 3,
    automated_providers_count: 2,
    recent_activity: []
  };

  const featuredSpecialists = STATE.data.providers.slice(0, 3);
  const recommendedServices = STATE.data.services.slice(0, 4);

  return `
    <!-- Top Greeting Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">Good morning, ${STATE.user.name}</h1>
        <p class="text-[14px] text-[#627566] mt-0.5">Discover AI security specialists and manage your prompt reviews.</p>
      </div>
      <div class="flex items-center gap-3">
        <button onclick="openModal('quick_analyze')" class="px-4 py-2 bg-[#FFFFFF] border border-[#E2E9E3] hover:border-[#CBD7CE] text-[#202820] text-[13.5px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-2">
          <svg class="w-4 h-4 text-[#176B45]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Analyze a Prompt
        </button>
        <button onclick="navigateTo('discover')" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-2">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Request Security Review
        </button>
      </div>
    </div>

    <!-- Summary Metrics Cards (Matching Claude Console Metric Row) -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>Registered Specialists</span>
          <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-medium">Total</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${stats.registered_specialists_count}</span>
          <span class="text-[12px] text-[#627566]">(${stats.automated_providers_count} AI / ${stats.human_specialists_count} Human)</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('discover')">
          Browse directory →
        </div>
      </div>

      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>Available Services</span>
          <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-medium">Audits & Hardening</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${stats.available_services_count}</span>
          <span class="text-[12px] text-[#627566]">active offerings</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('discover')">
          View all services →
        </div>
      </div>

      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>My Requests</span>
          <span class="text-[11px] bg-[#FEF3C7] text-[#92400E] px-2 py-0.5 rounded font-medium">Orders</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${stats.my_requests_count}</span>
          <span class="text-[12px] text-[#627566]">orders in flight</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('my_requests')">
          Track lifecycle →
        </div>
      </div>

      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 flex flex-col justify-between shadow-xs">
        <div class="flex items-center justify-between text-[#627566] text-[13px] font-medium">
          <span>Completed Reviews</span>
          <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-medium">Reports</span>
        </div>
        <div class="mt-3 flex items-baseline gap-2">
          <span class="text-3xl font-semibold tracking-tight text-[#202820]">${stats.completed_reviews_count}</span>
          <span class="text-[12px] text-[#627566]">audited prompts</span>
        </div>
        <div class="mt-2 text-[12px] text-[#176B45] font-medium hover:underline cursor-pointer" onclick="navigateTo('security_reports')">
          Inspect reports →
        </div>
      </div>
    </div>

    <!-- Integration Architecture Readiness Banner -->
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-4 flex items-center justify-between shadow-xs">
      <div class="flex items-center gap-4">
        <div class="w-10 h-10 rounded-md bg-[#EAF5EE] text-[#176B45] flex items-center justify-center shrink-0">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <span class="text-[13.5px] font-semibold text-[#202820]">Decentralized Foundation Integration Architecture</span>
            <span class="text-[10px] bg-[#EAF5EE] text-[#176B45] font-mono px-2 py-0.5 rounded font-semibold">PHASE 1 READY</span>
          </div>
          <p class="text-[12.5px] text-[#627566] mt-0.5">
            Interfaces prepared for <strong class="text-[#202820]">0G Private Computer</strong> (AI reasoning), <strong class="text-[#202820]">Arkiv</strong> (registry), <strong class="text-[#202820]">Swarm</strong> (decentralized reports), and <strong class="text-[#202820]">Hedera x402</strong> (autonomous micropayments).
          </p>
        </div>
      </div>
      <button onclick="openModal('integrations_info')" class="px-3 py-1.5 text-[12.5px] font-medium text-[#176B45] hover:bg-[#EAF5EE] rounded-md transition-smooth">
        View Specs
      </button>
    </div>

    <!-- Featured Specialists Row -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-[16px] font-semibold tracking-tight text-[#202820]">Featured Security Specialists</h2>
        <button onclick="navigateTo('discover')" class="text-[13px] font-medium text-[#176B45] hover:underline">
          View all specialists (${STATE.data.providers.length}) →
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        ${featuredSpecialists.map(p => renderSpecialistCard(p)).join('')}
      </div>
    </div>

    <!-- Recommended Security Services -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-[16px] font-semibold tracking-tight text-[#202820]">Recommended Services</h2>
        <button onclick="navigateTo('discover')" class="text-[13px] font-medium text-[#176B45] hover:underline">
          Compare all offerings →
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        ${recommendedServices.map(s => renderServiceCard(s)).join('')}
      </div>
    </div>

    <!-- Recent Activity Feed -->
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-4">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[14px] font-semibold text-[#202820]">Recent Activity & Order Lifecycle</h3>
        <span class="text-[12px] text-[#627566]">Updated in real-time</span>
      </div>

      <div class="divide-y divide-[#E2E9E3]/70">
        ${renderActivityFeed(stats.recent_activity)}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 2. Discover Specialists Page
// ---------------------------------------------------------------------------

function renderDiscoverView() {
  const categories = [
    { id: 'all', label: 'All Specialists' },
    { id: 'ai_security', label: 'AI Security' },
    { id: 'prompt_engineering', label: 'Prompt Engineering' },
    { id: 'llm_optimization', label: 'LLM Optimization' },
    { id: 'ai_agents', label: 'AI Agents' },
    { id: 'rag_security', label: 'RAG Security' },
    { id: 'api_security', label: 'Application Security' }
  ];

  // Filter specialists
  const filtered = STATE.data.providers.filter(p => {
    // Search keyword
    if (STATE.filters.search) {
      const q = STATE.filters.search.toLowerCase();
      const matchName = p.display_name.toLowerCase().includes(q);
      const matchTitle = p.title.toLowerCase().includes(q);
      const matchDesc = p.description.toLowerCase().includes(q);
      const matchSkills = p.skills.some(s => s.toLowerCase().includes(q));
      if (!matchName && !matchTitle && !matchDesc && !matchSkills) return false;
    }

    // Category
    if (STATE.filters.category && STATE.filters.category !== 'all') {
      const hasCat = p.categories.some(c => c.toLowerCase() === STATE.filters.category.toLowerCase());
      if (!hasCat) return false;
    }

    // Provider Type
    if (STATE.filters.providerType && p.provider_type !== STATE.filters.providerType) {
      return false;
    }

    return true;
  });

  return `
    <!-- Header -->
    <div class="flex flex-col gap-1">
      <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">Discover AI Security Specialists</h1>
      <p class="text-[14px] text-[#627566]">Browse vetted human security auditors and automated AI defense agents.</p>
    </div>

    <!-- Category Filter Tabs (Pill Style) -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-[#E2E9E3]">
      ${categories.map(c => `
        <button
          onclick="setCategoryFilter('${c.id}')"
          class="px-3.5 py-1.5 rounded-full text-[13px] font-medium whitespace-nowrap transition-smooth ${
            STATE.filters.category === c.id
              ? 'bg-[#176B45] text-white shadow-xs'
              : 'bg-white border border-[#E2E9E3] text-[#445246] hover:bg-[#F0F5F1]'
          }"
        >
          ${c.label}
        </button>
      `).join('')}
    </div>

    <!-- Sub-Filters: Type, Price, Availability -->
    <div class="flex items-center justify-between gap-4 bg-white p-3 border border-[#E2E9E3] rounded-lg">
      <div class="flex items-center gap-3">
        <span class="text-[12.5px] font-medium text-[#627566]">Provider Type:</span>
        <select
          onchange="setProviderTypeFilter(this.value)"
          class="bg-[#F7F9F7] border border-[#E2E9E3] text-[13px] text-[#202820] rounded px-2.5 py-1 focus:outline-none focus:border-[#176B45]"
        >
          <option value="" ${!STATE.filters.providerType ? 'selected' : ''}>All Types</option>
          <option value="automated" ${STATE.filters.providerType === 'automated' ? 'selected' : ''}>Automated AI Provider</option>
          <option value="human" ${STATE.filters.providerType === 'human' ? 'selected' : ''}>Human Specialist</option>
        </select>
      </div>

      <div class="text-[13px] text-[#627566]">
        Showing <strong class="text-[#202820]">${filtered.length}</strong> of ${STATE.data.providers.length} registered specialists
      </div>
    </div>

    <!-- Specialists Grid -->
    ${filtered.length > 0 ? `
      <div class="grid grid-cols-1 md:grid-cols-3 gap-5">
        ${filtered.map(p => renderSpecialistCard(p)).join('')}
      </div>
    ` : `
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-12 text-center space-y-3">
        <div class="w-12 h-12 rounded-full bg-[#EAF5EE] text-[#176B45] flex items-center justify-center mx-auto">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 class="text-[15px] font-semibold text-[#202820]">No specialists matched your filter</h3>
        <p class="text-[13px] text-[#627566]">Try clearing your search query or selecting a different category.</p>
        <button onclick="resetFilters()" class="px-3.5 py-1.5 text-[13px] font-medium bg-[#176B45] text-white rounded-md">
          Reset Filters
        </button>
      </div>
    `}
  `;
}

// ---------------------------------------------------------------------------
// 3. Specialist Profile Page
// ---------------------------------------------------------------------------

function renderProviderDetailView() {
  const provider = STATE.data.providers.find(p => p.id === STATE.selectedProviderId) || STATE.data.providers[0];
  if (!provider) {
    return `<div class="p-8 text-center">Specialist not found. <button onclick="navigateTo('discover')" class="text-[#176B45] underline">Back to Directory</button></div>`;
  }

  const providerServices = STATE.data.services.filter(s => s.provider_id === provider.id);
  const isAutomated = provider.provider_type === 'automated';

  return `
    <!-- Back Link -->
    <div>
      <button onclick="navigateTo('discover')" class="text-[13px] text-[#176B45] font-medium hover:underline flex items-center gap-1.5">
        ← Back to Specialist Directory
      </button>
    </div>

    <!-- Provider Header Card -->
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-6 shadow-xs space-y-6">
      <div class="flex items-start justify-between">
        <div class="flex items-start gap-5">
          <img
            src="${provider.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}"
            alt="${provider.display_name}"
            class="w-20 h-20 rounded-lg object-cover border border-[#E2E9E3] shadow-xs shrink-0"
          />
          <div class="space-y-1.5">
            <div class="flex items-center gap-2.5">
              <h1 class="text-xl font-semibold text-[#202820] tracking-tight">${provider.display_name}</h1>
              ${provider.verified ? `
                <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#EAF5EE] text-[#176B45] border border-[#C4E4CE]">
                  <svg class="w-3 h-3 fill-current" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                  </svg>
                  Verified Specialist
                </span>
              ` : `
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F7F9F7] text-[#627566] border border-[#E2E9E3]">
                  Registered Provider
                </span>
              `}
              <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${isAutomated ? 'bg-[#E0E7FF] text-[#3730A3]' : 'bg-[#FEF3C7] text-[#92400E]'}">
                ${isAutomated ? 'Autonomous AI Provider' : 'Human Specialist'}
              </span>
            </div>
            <p class="text-[14px] text-[#445246] font-medium">${provider.title}</p>
            <div class="flex items-center gap-4 text-[12px] text-[#627566] pt-1">
              <span>Status: <strong class="text-[#176B45]">${provider.availability}</strong></span>
              ${provider.wallet_address ? `<span>Hedera Account: <code class="font-mono text-[#202820]">${provider.wallet_address}</code></span>` : ''}
              ${isAutomated && provider.x402_supported ? `<span class="text-[#176B45] font-semibold">x402 Protocol Enabled</span>` : ''}
            </div>
          </div>
        </div>

        <button
          onclick="openModal('request_review', { providerId: '${provider.id}', serviceId: '${providerServices[0]?.id || ''}' })"
          class="px-5 py-2.5 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth"
        >
          Request a Review
        </button>
      </div>

      <!-- Description & Genuine Reputation -->
      <div class="border-t border-[#E2E9E3] pt-5 space-y-4">
        <div>
          <h3 class="text-[13px] font-semibold text-[#8B9C8E] uppercase tracking-wider">About Specialist</h3>
          <p class="text-[14px] text-[#333E35] leading-relaxed mt-1.5">${provider.description}</p>
        </div>

        <!-- Skills Chips -->
        <div>
          <h3 class="text-[13px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Verified Skills & Tools</h3>
          <div class="flex flex-wrap gap-1.5 mt-2">
            ${provider.skills.map(s => `
              <span class="px-2.5 py-1 bg-[#F7F9F7] border border-[#E2E9E3] text-[#202820] text-[12px] font-medium rounded-md">
                ${s}
              </span>
            `).join('')}
          </div>
        </div>

        <!-- Genuine Verified Reputation (No Invented Stars) -->
        <div class="bg-[#FAFBF9] border border-[#E2E9E3] rounded-md p-4">
          <div class="text-[12px] font-semibold text-[#176B45] uppercase tracking-wider mb-2">Auditing Track Record & Performance</div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${provider.reputation_metadata.audits_completed || 0}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Audits Completed</div>
            </div>
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${provider.reputation_metadata.avg_turnaround_hours ? `${provider.reputation_metadata.avg_turnaround_hours}h` : (provider.reputation_metadata.avg_turnaround_sec ? `${provider.reputation_metadata.avg_turnaround_sec}s` : 'Instant')}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Avg Turnaround</div>
            </div>
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${isAutomated ? 'API / x402' : 'Manual'}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Execution Type</div>
            </div>
            <div class="bg-white p-3 rounded border border-[#E2E9E3]">
              <div class="text-xl font-bold text-[#202820]">${provider.portfolio_url ? 'Verified' : 'Active'}</div>
              <div class="text-[11px] text-[#627566] mt-0.5">Portfolio Check</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Published Services List -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-[16px] font-semibold tracking-tight text-[#202820]">Published Services (${providerServices.length})</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        ${providerServices.map(s => renderServiceCard(s, false)).join('')}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 4. Become a Specialist Page
// ---------------------------------------------------------------------------

function renderBecomeSpecialistView() {
  return `
    <div class="max-w-3xl mx-auto space-y-6">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">Become a PromptShield Specialist</h1>
        <p class="text-[14px] text-[#627566]">Register your human expertise or register an automated defense agent for discovery.</p>
      </div>

      <div class="bg-[#FAFBF9] border border-[#E2E9E3] rounded-lg p-4 text-[13px] text-[#445246] flex items-center gap-3">
        <svg class="w-5 h-5 text-[#176B45] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>
          Newly submitted profiles are published directly for testing with status <strong class="text-[#202820]">published</strong>. Verified badges require manual code and identity review.
        </span>
      </div>

      <form id="become-specialist-form" onsubmit="handleBecomeSpecialist(event)" class="bg-white border border-[#E2E9E3] rounded-lg p-7 shadow-xs space-y-6">
        <!-- Section 1: Provider Identity -->
        <div class="space-y-4">
          <h3 class="text-[14px] font-semibold text-[#176B45] border-b border-[#E2E9E3] pb-2">1. Specialist Identity & Type</h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Full Name / Agent Name *</label>
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
              <select name="provider_type" id="form-provider-type" onchange="toggleAutomatedFields(this.value)" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]">
                <option value="human">Human Specialist</option>
                <option value="automated">Automated AI Provider</option>
              </select>
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Wallet Address (Hedera or EVM)</label>
              <input type="text" name="wallet_address" placeholder="e.g. 0.0.7819234 or 0x..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] font-mono focus:outline-none focus:border-[#176B45]" />
            </div>
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Profile Bio / Description *</label>
            <textarea name="description" rows="3" required placeholder="Describe your security focus, background, attack surfaces tested, and tooling..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]"></textarea>
          </div>
        </div>

        <!-- Section 2: Automated Provider Configuration (Conditional) -->
        <div id="automated-provider-fields" class="space-y-4 hidden p-4 bg-[#F7F9F7] rounded-md border border-[#E2E9E3]">
          <h3 class="text-[13.5px] font-semibold text-[#176B45]">Automated Agent Configuration</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Provider API Endpoint</label>
              <input type="url" name="endpoint_url" placeholder="https://api.yourdomain.com/v1/scan" class="w-full px-3 py-2 bg-white border border-[#E2E9E3] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]" />
            </div>

            <div>
              <label class="block text-[12.5px] font-medium text-[#202820] mb-1">Input / Output Format</label>
              <input type="text" name="io_format" value="JSON / Prompt-in, Hardened-out" class="w-full px-3 py-2 bg-white border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]" />
            </div>
          </div>

          <div class="flex items-center gap-2">
            <input type="checkbox" name="x402_supported" id="cb-x402" class="rounded text-[#176B45] focus:ring-[#176B45]" />
            <label for="cb-x402" class="text-[13px] text-[#202820]">Enable Hedera x402 Autonomous Payment Protocol</label>
          </div>
        </div>

        <!-- Section 3: Skills & Categories -->
        <div class="space-y-4">
          <h3 class="text-[14px] font-semibold text-[#176B45] border-b border-[#E2E9E3] pb-2">2. Expertise & Categories</h3>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Skills (Comma-separated)</label>
            <input type="text" name="skills_raw" placeholder="Adversarial Prompting, OWASP LLM Top-10, Indirect Injection, Jailbreak Defense" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
          </div>

          <div>
            <label class="block text-[13px] font-medium text-[#202820] mb-1">Primary Categories</label>
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
          <h3 class="text-[14px] font-semibold text-[#176B45] border-b border-[#E2E9E3] pb-2">3. Primary Service Offering</h3>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Service Title *</label>
              <input type="text" name="service_title" required placeholder="e.g. Prompt Injection Vulnerability Audit" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13.5px] focus:outline-none focus:border-[#176B45]" />
            </div>

            <div>
              <label class="block text-[13px] font-medium text-[#202820] mb-1">Price (USD equivalent) *</label>
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

        <!-- Action Submit -->
        <div class="pt-4 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="navigateTo('dashboard')" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] hover:bg-[#F7F9F7] text-[13.5px] font-medium rounded-md transition-smooth">
            Cancel
          </button>
          <button type="submit" class="px-6 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth">
            Register Specialist Profile
          </button>
        </div>
      </form>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// 5. Specialist Workspace
// ---------------------------------------------------------------------------

function renderWorkspaceView() {
  // Find current specialist profile
  const provider = STATE.data.providers.find(p => p.id === STATE.user.activeProviderId) || STATE.data.providers[2];
  
  // Work assigned to this specialist
  const assignedOrders = STATE.data.orders.filter(o => o.provider_id === provider.id);
  const incoming = assignedOrders.filter(o => o.status === 'requested');
  const inProgress = assignedOrders.filter(o => o.status === 'accepted' || o.status === 'in_progress');
  const completed = assignedOrders.filter(o => o.status === 'completed' || o.status === 'delivered');

  return `
    <div class="space-y-6">
      <!-- Specialist Banner -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-6 shadow-xs flex items-center justify-between">
        <div class="flex items-center gap-4">
          <img src="${provider.avatar_url}" class="w-14 h-14 rounded-lg object-cover border border-[#E2E9E3]" />
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-xl font-semibold text-[#202820]">${provider.display_name}</h1>
              <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] font-semibold px-2 py-0.5 rounded">Active Workspace</span>
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

      <!-- Quick Stats -->
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
          <span class="text-[12px] text-[#627566] font-medium">Earnings Escrow Placeholder</span>
          <div class="text-2xl font-bold text-[#202820] mt-1 font-mono">$${(completed.length * 95).toFixed(2)}</div>
        </div>
      </div>

      <!-- Incoming Requests Section -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-4">
        <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
          <div class="flex items-center gap-2">
            <h2 class="text-[15px] font-semibold text-[#202820]">Incoming Service Requests</h2>
            <span class="text-[11px] bg-[#FEF3C7] text-[#92400E] font-medium px-2 py-0.5 rounded">${incoming.length} pending</span>
          </div>
          <span class="text-[12px] text-[#627566]">Specialist action required to accept or decline</span>
        </div>

        ${incoming.length > 0 ? `
          <div class="space-y-3">
            ${incoming.map(o => `
              <div class="p-4 rounded-md border border-[#E2E9E3] bg-[#FAFBF9] flex items-start justify-between gap-4">
                <div class="space-y-1.5 flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-[12px] text-[#627566]">${o.id}</span>
                    <strong class="text-[14px] text-[#202820]">${o.service_title}</strong>
                    <span class="text-[11px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-mono font-medium">$${o.price.toFixed(2)}</span>
                  </div>
                  <div class="text-[12.5px] text-[#445246]">
                    Submitted by: <strong>${o.customer_name}</strong> • ${new Date(o.created_at).toLocaleDateString()}
                  </div>
                  <div class="text-[12.5px] text-[#627566] bg-white p-2.5 rounded border border-[#E2E9E3] font-mono text-[11.5px] line-clamp-2">
                    ${escapeHtml(o.prompt_content)}
                  </div>
                </div>

                <div class="flex items-center gap-2 shrink-0">
                  <button onclick="handleOrderStatusUpdate('${o.id}', 'accepted')" class="px-3 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded transition-smooth">
                    Accept Order
                  </button>
                  <button onclick="handleOrderStatusUpdate('${o.id}', 'rejected')" class="px-3 py-1.5 border border-[#FECACA] bg-[#FEE2E2] text-[#991B1B] hover:bg-[#FCA5A5] text-[12.5px] font-medium rounded transition-smooth">
                    Reject
                  </button>
                </div>
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
            <h2 class="text-[15px] font-semibold text-[#202820]">Active Work In Progress</h2>
            <span class="text-[11px] bg-[#DBEAFE] text-[#1E40AF] font-medium px-2 py-0.5 rounded">${inProgress.length} active</span>
          </div>
          <span class="text-[12px] text-[#627566]">Prompts only shared with assigned specialist</span>
        </div>

        ${inProgress.length > 0 ? `
          <div class="space-y-4">
            ${inProgress.map(o => `
              <div class="p-5 rounded-md border border-[#E2E9E3] bg-[#FFFFFF] space-y-3">
                <div class="flex items-start justify-between">
                  <div>
                    <div class="flex items-center gap-2">
                      <span class="font-mono text-[12px] text-[#627566]">${o.id}</span>
                      <strong class="text-[14px] text-[#202820]">${o.service_title}</strong>
                      ${renderStatusBadge(o.status)}
                    </div>
                    <div class="text-[12px] text-[#627566] mt-0.5">
                      Client: <strong>${o.customer_name}</strong> • Price: <strong class="text-[#176B45] font-mono">$${o.price.toFixed(2)}</strong>
                    </div>
                  </div>

                  <div class="flex items-center gap-2">
                    ${o.status === 'accepted' ? `
                      <button onclick="handleOrderStatusUpdate('${o.id}', 'in_progress')" class="px-3 py-1.5 bg-[#1E40AF] text-white text-[12px] font-medium rounded hover:bg-[#1E3A8A]">
                        Mark In Progress
                      </button>
                    ` : ''}
                    <button onclick="openModal('deliver_modal', { orderId: '${o.id}', order: ${escapeForAttr(JSON.stringify(o))} })" class="px-3 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded shadow-xs">
                      Submit Deliverable & Report
                    </button>
                  </div>
                </div>

                <!-- Private Client Prompt Preview -->
                <div class="bg-[#FAFBF9] border border-[#E2E9E3] p-3 rounded-md text-[12.5px] space-y-1">
                  <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Submitted Prompt Under Review:</div>
                  <pre class="font-mono text-[12px] text-[#202820] whitespace-pre-wrap">${escapeHtml(o.prompt_content)}</pre>
                  ${o.requirements ? `
                    <div class="pt-2 border-t border-[#E2E9E3] text-[12px] text-[#445246]">
                      <strong class="text-[#202820]">Client Requirements:</strong> ${escapeHtml(o.requirements)}
                    </div>
                  ` : ''}
                </div>
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
          <p class="text-[14px] text-[#627566]">Private repository of prompts, security analyses, and hardened versions.</p>
        </div>
        <button onclick="openModal('create_prompt')" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13.5px] font-medium rounded-md shadow-xs transition-smooth flex items-center gap-1.5">
          + Add New Prompt
        </button>
      </div>

      <div class="bg-[#FAFBF9] border border-[#E2E9E3] rounded-lg p-3 text-[12.5px] text-[#445246] flex items-center gap-2">
        <svg class="w-4 h-4 text-[#176B45] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
        </svg>
        <span>Your prompts are stored privately on this node and are never broadcasted or shared with specialists until you submit a specific review order.</span>
      </div>

      <div class="grid grid-cols-1 gap-4">
        ${prompts.map(p => `
          <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs space-y-3 card-hover transition-smooth">
            <div class="flex items-start justify-between">
              <div>
                <h3 class="text-[15px] font-semibold text-[#202820]">${escapeHtml(p.title)}</h3>
                <span class="text-[11.5px] text-[#627566] font-mono">${p.id} • Saved ${new Date(p.created_at).toLocaleDateString()}</span>
              </div>

              <div class="flex items-center gap-2">
                <button onclick="runLocalPromptAnalysis('${escapeForAttr(p.content)}', '${p.id}')" class="px-3 py-1.5 bg-[#FAFBF9] border border-[#E2E9E3] hover:border-[#176B45] text-[#176B45] text-[12px] font-semibold rounded transition-smooth flex items-center gap-1.5">
                  <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Analyze with PromptShield
                </button>
                <button onclick="openModal('request_review', { promptText: '${escapeForAttr(p.content)}' })" class="px-3 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12px] font-medium rounded transition-smooth">
                  Submit to Specialist
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
// 7. My Requests & Security Reports Pages
// ---------------------------------------------------------------------------

function renderMyRequestsView() {
  const orders = STATE.data.orders;

  return `
    <div class="space-y-5">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-semibold tracking-tight text-[#202820]">My Requests & Orders</h1>
          <p class="text-[14px] text-[#627566]">Track the explicit lifecycle of your security audits and hardening requests.</p>
        </div>
        <button onclick="navigateTo('discover')" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs">
          + New Service Request
        </button>
      </div>

      <!-- Orders Table -->
      <div class="bg-white border border-[#E2E9E3] rounded-lg shadow-xs overflow-hidden">
        <table class="w-full text-left text-[13px]">
          <thead class="bg-[#FAFBF9] border-b border-[#E2E9E3] text-[#627566] text-[11.5px] uppercase font-semibold tracking-wider">
            <tr>
              <th class="px-5 py-3">Order ID</th>
              <th class="px-5 py-3">Service</th>
              <th class="px-5 py-3">Specialist / Provider</th>
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
                  ${o.report_id ? `
                    <button onclick="viewReport('${o.report_id}')" class="px-2.5 py-1 bg-[#EAF5EE] text-[#176B45] hover:bg-[#C4E4CE] font-medium text-[12px] rounded transition-smooth">
                      View Report
                    </button>
                  ` : `
                    <span class="text-[12px] text-[#8B9C8E]">In Progress</span>
                  `}
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
          <p class="text-[14px] text-[#627566]">Completed vulnerability audits, defense recommendations, and Swarm storage references.</p>
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
                <h3 class="text-[16px] font-semibold text-[#202820] mt-1">${escapeHtml(r.service_title)}</h3>
                <div class="text-[12.5px] text-[#627566]">
                  Audited by: <strong>${escapeHtml(r.provider_name)}</strong> • Order: <span class="font-mono">${r.order_id}</span>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <button onclick="viewReport('${r.id}')" class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded transition-smooth">
                  Inspect Findings & Hardened Prompt
                </button>
              </div>
            </div>

            <p class="text-[13.5px] text-[#445246]">${escapeHtml(r.summary)}</p>

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

            <!-- Swarm Reference Box -->
            ${r.swarm_reference ? `
              <div class="bg-[#FAFBF9] border border-[#E2E9E3] rounded px-3 py-2 flex items-center justify-between text-[11.5px]">
                <div class="flex items-center gap-2 font-mono text-[#445246] truncate">
                  <span class="text-[#176B45] font-semibold">Swarm Bzz Ref:</span>
                  <span class="truncate">${r.swarm_reference}</span>
                </div>
                <span class="text-[10px] text-[#8B9C8E] uppercase shrink-0 font-medium">Decentralized Storage Hash</span>
              </div>
            ` : ''}
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// Card & UI Sub-Components
// ---------------------------------------------------------------------------

function renderSpecialistCard(p) {
  const isAutomated = p.provider_type === 'automated';
  return `
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs flex flex-col justify-between card-hover transition-smooth space-y-4">
      <div class="space-y-3">
        <div class="flex items-start gap-3.5">
          <img src="${p.avatar_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150'}" class="w-12 h-12 rounded-lg object-cover border border-[#E2E9E3] shrink-0" />
          <div class="min-w-0">
            <div class="flex items-center gap-1.5">
              <h3 class="text-[14.5px] font-semibold text-[#202820] truncate">${escapeHtml(p.display_name)}</h3>
              ${p.verified ? `
                <svg class="w-3.5 h-3.5 text-[#176B45] shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              ` : ''}
            </div>
            <p class="text-[12px] text-[#627566] line-clamp-1">${escapeHtml(p.title)}</p>
            <div class="mt-1">
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded ${isAutomated ? 'bg-[#E0E7FF] text-[#3730A3]' : 'bg-[#FEF3C7] text-[#92400E]'}">
                ${isAutomated ? 'Autonomous AI' : 'Human Specialist'}
              </span>
            </div>
          </div>
        </div>

        <p class="text-[13px] text-[#445246] line-clamp-3 leading-relaxed">
          ${escapeHtml(p.description)}
        </p>

        <!-- Skills chips -->
        <div class="flex flex-wrap gap-1">
          ${(p.skills || []).slice(0, 3).map(s => `
            <span class="text-[11px] bg-[#FAFBF9] border border-[#E2E9E3] text-[#445246] px-2 py-0.5 rounded">
              ${escapeHtml(s)}
            </span>
          `).join('')}
          ${(p.skills || []).length > 3 ? `<span class="text-[10px] text-[#8B9C8E] self-center">+${p.skills.length - 3}</span>` : ''}
        </div>
      </div>

      <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-between">
        <div>
          <span class="text-[11px] text-[#627566] block">Availability</span>
          <span class="text-[12.5px] font-semibold text-[#176B45] capitalize">${p.availability}</span>
        </div>
        <button
          onclick="navigateTo('provider_detail', '${p.id}')"
          class="px-3 py-1.5 bg-[#FAFBF9] hover:bg-[#EAF5EE] border border-[#E2E9E3] text-[#176B45] text-[12.5px] font-medium rounded transition-smooth"
        >
          View Profile
        </button>
      </div>
    </div>
  `;
}

function renderServiceCard(s, showProvider = true) {
  return `
    <div class="bg-white border border-[#E2E9E3] rounded-lg p-5 shadow-xs flex flex-col justify-between card-hover transition-smooth space-y-3">
      <div class="space-y-2">
        <div class="flex items-start justify-between gap-2">
          <h3 class="text-[14.5px] font-semibold text-[#202820] tracking-tight leading-snug">${escapeHtml(s.title)}</h3>
          <span class="font-mono font-bold text-[14px] text-[#176B45] shrink-0">$${s.price.toFixed(2)}</span>
        </div>

        ${showProvider ? `
          <div class="text-[12px] text-[#627566] flex items-center gap-1.5">
            By <strong class="text-[#202820] cursor-pointer hover:underline" onclick="navigateTo('provider_detail', '${s.provider_id}')">${escapeHtml(s.provider_name)}</strong>
            <span class="text-[10px] px-1.5 py-0.2 rounded ${s.execution_type === 'automated' ? 'bg-[#E0E7FF] text-[#3730A3]' : 'bg-[#FEF3C7] text-[#92400E]'}">
              ${s.execution_type === 'automated' ? 'Instant AI' : 'Manual'}
            </span>
          </div>
        ` : ''}

        <p class="text-[13px] text-[#445246] line-clamp-2 leading-relaxed">
          ${escapeHtml(s.description)}
        </p>

        <div class="flex items-center gap-4 text-[11.5px] text-[#627566] pt-1">
          <span>Turnaround: <strong class="text-[#202820]">${s.estimated_delivery}</strong></span>
          <span>Category: <strong class="text-[#202820]">${s.category}</strong></span>
        </div>
      </div>

      <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-end">
        <button
          onclick="openModal('request_review', { serviceId: '${s.id}', providerId: '${s.provider_id}' })"
          class="px-3.5 py-1.5 bg-[#176B45] hover:bg-[#115638] text-white text-[12.5px] font-medium rounded transition-smooth"
        >
          Request Service
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

  return activities.map(act => `
    <div class="py-3 flex items-center justify-between text-[13px]">
      <div class="flex items-center gap-3">
        <div class="w-2 h-2 rounded-full bg-[#176B45]"></div>
        <div>
          <strong class="text-[#202820]">${escapeHtml(act.title)}</strong>
          <span class="text-[#627566]">with ${escapeHtml(act.provider)}</span>
        </div>
      </div>

      <div class="flex items-center gap-3">
        ${renderStatusBadge(act.status)}
        <span class="text-[12px] text-[#627566] font-mono">${new Date(act.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
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
    case 'integrations_info':
      return renderIntegrationsInfoModal();
    case 'add_service_modal':
      return renderAddServiceModal();
    default:
      return '';
  }
}

function renderRequestReviewModal() {
  const payload = STATE.modalPayload || {};
  const services = STATE.data.services;
  const initialService = services.find(s => s.id === payload.serviceId) || services[0];
  const prompts = STATE.data.prompts;

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[17px] font-semibold text-[#202820]">Request a Security Review</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <form onsubmit="handleOrderSubmit(event)" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Select Service Offering *</label>
          <select name="service_id" id="modal-service-select" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]">
            ${services.map(s => `
              <option value="${s.id}" ${s.id === initialService?.id ? 'selected' : ''}>
                ${escapeHtml(s.title)} — $${s.price.toFixed(2)} (${s.provider_name})
              </option>
            `).join('')}
          </select>
        </div>

        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="text-[13px] font-medium text-[#202820]">Prompt or System Instructions Under Review *</label>
            ${prompts.length > 0 ? `
              <select onchange="populatePromptFromSelect(this.value)" class="text-[12px] text-[#176B45] border border-[#E2E9E3] rounded px-2 py-0.5">
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
            placeholder="Paste your system prompt, customer agent instructions, or RAG directives here..."
            class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]"
          >${payload.promptText || ''}</textarea>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Customer Requirements & Known Attack Vectors</label>
          <textarea
            name="requirements"
            rows="2"
            placeholder="e.g. Audit against roleplay injection, SQL exfiltration, or vector similarity abuse..."
            class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"
          ></textarea>
        </div>

        <div class="bg-[#FAFBF9] border border-[#E2E9E3] p-3 rounded text-[12px] text-[#445246] space-y-1">
          <div class="font-medium text-[#202820]">Execution Notice:</div>
          <div>• Automated AI services execute immediately and generate verified security reports in seconds.</div>
          <div>• Human specialist orders are submitted to the specialist workspace for acceptance and manual adversarial probing.</div>
        </div>

        <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] text-[13px] font-medium rounded-md">
            Cancel
          </button>
          <button type="submit" class="px-5 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs">
            Confirm & Place Request
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
        <h3 class="text-[17px] font-semibold text-[#202820]">Deliver Security Audit & Report</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <form onsubmit="handleDeliverSubmit(event, '${orderId}')" class="space-y-4">
        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Executive Summary of Findings *</label>
          <textarea name="summary" rows="3" required placeholder="Summarize your audit findings, risk profile, and jailbreak resilience..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Vulnerability Findings (Title, Severity, Remediation)</label>
          <div class="space-y-2" id="findings-inputs">
            <div class="grid grid-cols-3 gap-2">
              <input type="text" name="finding_title" placeholder="e.g. Indirect Prompt Injection" class="col-span-2 px-2.5 py-1.5 border border-[#E2E9E3] rounded text-[12.5px]" />
              <select name="finding_severity" class="px-2 py-1.5 border border-[#E2E9E3] rounded text-[12.5px]">
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Actionable Recommendations (One per line)</label>
          <textarea name="recommendations_raw" rows="3" placeholder="1. Enforce XML delimiter encapsulation&#10;2. Apply input sanitization filter before LLM inference" class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div>
          <label class="block text-[13px] font-medium text-[#202820] mb-1">Hardened Prompt Deliverable</label>
          <textarea name="hardened_prompt" rows="4" placeholder="Paste the hardened defense version of the system prompt..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[12.5px] font-mono focus:outline-none focus:border-[#176B45]"></textarea>
        </div>

        <div class="pt-3 border-t border-[#E2E9E3] flex items-center justify-end gap-3">
          <button type="button" onclick="closeModal()" class="px-4 py-2 border border-[#E2E9E3] text-[#445246] text-[13px] font-medium rounded-md">Cancel</button>
          <button type="submit" class="px-5 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md shadow-xs">
            Complete Delivery & Upload to Swarm
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
        <h3 class="text-[17px] font-semibold text-[#202820]">Analyze Prompt Security</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <div class="space-y-3">
        <label class="block text-[13px] font-medium text-[#202820]">Enter Prompt Text</label>
        <textarea id="quick-prompt-input" rows="4" placeholder="Enter prompt to evaluate against PromptShield's injection model and 15 OWASP application risk classifiers..." class="w-full px-3 py-2 border border-[#E2E9E3] rounded-md text-[13px] font-mono focus:outline-none focus:border-[#176B45]"></textarea>

        <div class="flex justify-end gap-2">
          <button onclick="executeQuickAnalyze()" class="px-4 py-2 bg-[#176B45] hover:bg-[#115638] text-white text-[13px] font-medium rounded-md">
            Run ML Vulnerability Scan
          </button>
        </div>

        <!-- Result Box -->
        <div id="quick-analyze-results" class="hidden mt-4 p-4 bg-[#FAFBF9] border border-[#E2E9E3] rounded-md space-y-3"></div>
      </div>
    </div>
  `;
}

function renderReportViewerModal() {
  const report = STATE.modalPayload;
  if (!report) return '';

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <div>
          <span class="text-[11px] font-mono text-[#627566]">${report.id}</span>
          <h3 class="text-[17px] font-semibold text-[#202820]">${escapeHtml(report.service_title)}</h3>
        </div>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <div class="space-y-4 text-[13px]">
        <div>
          <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider">Executive Summary</div>
          <p class="text-[#333E35] mt-1 leading-relaxed">${escapeHtml(report.summary)}</p>
        </div>

        <div>
          <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider mb-2">Vulnerabilities & Findings</div>
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
            <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider mb-1">Delivered Hardened Prompt</div>
            <pre class="bg-[#FAFBF9] border border-[#E2E9E3] p-3 rounded font-mono text-[12px] text-[#202820] whitespace-pre-wrap">${escapeHtml(report.hardened_prompt)}</pre>
          </div>
        ` : ''}

        <div class="bg-[#FAFBF9] border border-[#E2E9E3] p-3 rounded font-mono text-[11px] text-[#627566] break-all">
          <strong class="text-[#176B45]">Swarm Content Hash:</strong> ${report.swarm_reference || 'Simulated Phase 1 Reference'}
        </div>
      </div>
    </div>
  `;
}

function renderIntegrationsInfoModal() {
  const ints = STATE.data.integrations || {};

  return `
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[17px] font-semibold text-[#202820]">Decentralized Integration Specifications</h3>
        <button onclick="closeModal()" class="text-[#8B9C8E] hover:text-[#202820]">✕</button>
      </div>

      <div class="space-y-4 text-[13px]">
        <div class="p-3 rounded border border-[#E2E9E3] bg-[#FAFBF9]">
          <div class="flex items-center justify-between">
            <strong class="text-[#176B45]">0G Private Computer (Zero-G)</strong>
            <span class="text-[10px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-mono font-semibold">INTERFACE READY</span>
          </div>
          <p class="text-[12px] text-[#445246] mt-1">Confidential AI reasoning for automated prompt hardening. Client handles sensitive data masking before inference with deterministic local fallback.</p>
        </div>

        <div class="p-3 rounded border border-[#E2E9E3] bg-[#FAFBF9]">
          <div class="flex items-center justify-between">
            <strong class="text-[#176B45]">Arkiv Registry</strong>
            <span class="text-[10px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-mono font-semibold">INTERFACE READY</span>
          </div>
          <p class="text-[12px] text-[#445246] mt-1">Decentralized provider discovery and immutable marketplace service publication records with cryptographic content verification.</p>
        </div>

        <div class="p-3 rounded border border-[#E2E9E3] bg-[#FAFBF9]">
          <div class="flex items-center justify-between">
            <strong class="text-[#176B45]">Ethereum Swarm</strong>
            <span class="text-[10px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-mono font-semibold">INTERFACE READY</span>
          </div>
          <p class="text-[12px] text-[#445246] mt-1">Content-addressable storage protocol for delivered security audit manifests and hardened prompt diffs using verifiable bzz:// references.</p>
        </div>

        <div class="p-3 rounded border border-[#E2E9E3] bg-[#FAFBF9]">
          <div class="flex items-center justify-between">
            <strong class="text-[#176B45]">Hedera x402 Micropayments</strong>
            <span class="text-[10px] bg-[#EAF5EE] text-[#176B45] px-2 py-0.5 rounded font-mono font-semibold">INTERFACE READY</span>
          </div>
          <p class="text-[12px] text-[#445246] mt-1">Autonomous machine-to-machine payment protocol for automated security agents using HTTP 402 challenge tokens and testnet account settlement.</p>
        </div>
      </div>
    </div>
  `;
}

function renderCreatePromptModal() {
  return `
    <div class="p-6 space-y-4">
      <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-3">
        <h3 class="text-[17px] font-semibold text-[#202820]">Save Prompt to Private Repository</h3>
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
        <h3 class="text-[17px] font-semibold text-[#202820]">Publish New Security Service</h3>
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

// ---------------------------------------------------------------------------
// Actions & Handlers
// ---------------------------------------------------------------------------

function handleGlobalSearch(value) {
  STATE.filters.search = value;
  // If not on discover, switch to discover to see full search
  if (STATE.activeView !== 'discover' && STATE.activeView !== 'dashboard') {
    STATE.activeView = 'discover';
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

async function handleOrderSubmit(e) {
  e.preventDefault();
  const form = e.target;
  const serviceId = form.service_id.value;
  const promptContent = form.prompt_content.value;
  const requirements = form.requirements.value;

  try {
    const order = await apiFetch('/marketplace/orders', {
      method: 'POST',
      body: JSON.stringify({
        service_id: serviceId,
        prompt_content: promptContent,
        requirements: requirements,
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

async function handleBecomeSpecialist(e) {
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
    x402_supported: Boolean(form.x402_supported?.checked),
    availability: 'available',
    status: 'published'
  };

  try {
    const prov = await apiFetch('/marketplace/providers/profile', {
      method: 'POST',
      body: JSON.stringify(payload)
    });

    // Create initial service
    await apiFetch('/marketplace/services', {
      method: 'POST',
      body: JSON.stringify({
        title: form.service_title.value,
        description: `Specialized security assessment provided by ${prov.display_name}.`,
        category: cats[0] || 'ai_security',
        price: parseFloat(form.service_price.value) || 50.0,
        currency: 'USD',
        estimated_delivery: form.service_delivery.value,
        supported_tasks: ['prompt_injection', 'system_prompt_audit'],
        execution_type: prov.provider_type === 'automated' ? 'automated' : 'manual',
        provider_id: prov.id
      })
    });

    alert('Specialist profile and initial service registered successfully!');
    STATE.user.activeProviderId = prov.id;
    STATE.user.role = 'provider';
    await loadInitialData();
    navigateTo('workspace');
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

async function runLocalPromptAnalysis(promptText, promptId = null) {
  openModal('quick_analyze');
  const input = document.getElementById('quick-prompt-input');
  if (input) input.value = promptText;
  executeQuickAnalyze(promptId);
}

async function executeQuickAnalyze(promptId = null) {
  const input = document.getElementById('quick-prompt-input');
  const resultsBox = document.getElementById('quick-analyze-results');
  if (!input || !resultsBox) return;

  const text = input.value;
  if (!text.trim()) {
    alert('Please enter a prompt to analyze.');
    return;
  }

  resultsBox.classList.remove('hidden');
  resultsBox.innerHTML = `<div class="text-[12px] text-[#627566] animate-pulse">Running PromptShield ML security analysis and OWASP risk detection...</div>`;

  try {
    const analysis = await apiFetch('/analyze', {
      method: 'POST',
      body: JSON.stringify({ prompt: text, analysis_mode: 'both' })
    });

    const pSec = analysis.prompt_security || {};
    const appRisks = analysis.application_risks || {};
    const sData = analysis.sensitive_data || {};

    resultsBox.innerHTML = `
      <div class="space-y-3 text-[12.5px]">
        <div class="flex items-center justify-between border-b border-[#E2E9E3] pb-2">
          <strong class="text-[#202820]">Analysis Findings</strong>
          <span class="text-[11px] px-2 py-0.5 rounded font-bold uppercase ${pSec.is_injection_detected ? 'bg-[#FEE2E2] text-[#991B1B]' : 'bg-[#EAF5EE] text-[#176B45]'}">
            ${pSec.risk_category || 'Evaluated'}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="bg-white p-2.5 rounded border border-[#E2E9E3]">
            <div class="text-[11px] text-[#627566]">Injection Probability</div>
            <div class="text-lg font-bold text-[#202820] mt-0.5">${(pSec.confidence_score * 100).toFixed(1)}%</div>
          </div>
          <div class="bg-white p-2.5 rounded border border-[#E2E9E3]">
            <div class="text-[11px] text-[#627566]">Sensitive Credentials</div>
            <div class="text-lg font-bold ${sData.has_sensitive_data ? 'text-[#991B1B]' : 'text-[#176B45]'} mt-0.5">
              ${sData.count || 0} detected
            </div>
          </div>
        </div>

        <div>
          <div class="text-[11px] font-semibold text-[#8B9C8E] uppercase tracking-wider mb-1">Detected Risks (OWASP LLM)</div>
          <div class="flex flex-wrap gap-1">
            ${(appRisks.detected_risks || []).length > 0 ? (appRisks.detected_risks || []).map(r => `
              <span class="px-2 py-0.5 bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] text-[11px] font-medium rounded">
                ${r}
              </span>
            `).join('') : '<span class="text-[#176B45]">No critical application risk categories triggered.</span>'}
          </div>
        </div>

        <div class="pt-2 border-t border-[#E2E9E3] flex justify-end">
          <button onclick="closeModal(); openModal('request_review', { promptText: '${escapeForAttr(text)}' })" class="px-3 py-1.5 bg-[#176B45] text-white text-[12px] font-medium rounded">
            Submit for Specialist Hardening →
          </button>
        </div>
      </div>
    `;

    // Optionally update prompt cached analysis if promptId is known
    if (promptId) {
      await apiFetch(`/marketplace/prompts/${promptId}`, {
        method: 'PUT',
        body: JSON.stringify({
          analysis_result: {
            injection_score: pSec.confidence_score,
            sensitive_data_count: sData.count || 0,
            risk_labels: appRisks.detected_risks || []
          }
        })
      });
      await loadInitialData();
    }
  } catch (err) {
    resultsBox.innerHTML = `<div class="text-[#991B1B] text-[12px]">Analysis error: ${err.message}</div>`;
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
window.addEventListener('DOMContentLoaded', () => {
  loadInitialData();
});

