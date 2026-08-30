/* ============================================================
   CBE District IT Management System — App Bootstrap
   © 2025 Deressa Fufa
   ============================================================ */

const NAV_ITEMS = [
  // Overview
  { key: 'dashboard',             label: 'Dashboard',           icon: '◆', roles: null,                section: 'Overview' },
  // Infrastructure
  { key: 'branches',              label: 'Branches',            icon: '🏢', roles: null,                section: 'Infrastructure' },
  { key: 'atms',                  label: 'ATMs',                icon: '🏧', roles: null,                section: null },
  { key: 'atm-errors',            label: 'ATM Errors',          icon: '⚠', roles: null,                section: null },
  { key: 'network-installations', label: 'Network Installations',icon: '🌐', roles: null,               section: null },
  { key: 'computers',             label: 'Computers',           icon: '💻', roles: null,                section: null },
  // Support
  { key: 'tickets',               label: 'IT Tickets',          icon: '🎫', roles: null,                section: 'Support' },
  { key: 'incidents',             label: 'Incidents',           icon: '🚨', roles: null,                section: null },
  { key: 'remote-support',        label: 'Remote Support',      icon: '🖥', roles: null,                section: null },
  // Assets
  { key: 'equipment',             label: 'Equipment',           icon: '📦', roles: null,                section: 'Assets & Ops' },
  { key: 'maintenance',           label: 'Maintenance',         icon: '🛠', roles: null,                section: null },
  { key: 'knowledge-base',        label: 'Knowledge Base',      icon: '📘', roles: null,                section: null },
  // Reports & Admin
  { key: 'reports',               label: 'Reports',             icon: '📊', roles: null,                section: 'Reports & Admin' },
  { key: 'notifications',         label: 'Notifications',       icon: '🔔', roles: null,                section: null },
  { key: 'users',                 label: 'Users',               icon: '👥', roles: ['district_admin'],  section: null },
  { key: 'settings',              label: 'CBE Settings',        icon: '⚙', roles: ['district_admin'],  section: null },
  { key: 'audit-logs',            label: 'Audit Logs',          icon: '📜', roles: ['district_admin'],  section: null },
];

/* ── Sidebar builder with section labels ── */
function buildSidebar() {
  const user = Session.user;
  const nav = document.getElementById('sidebar-nav');
  let lastSection = null;
  let html = '';
  NAV_ITEMS
    .filter(item => !item.roles || item.roles.includes(user.role))
    .forEach(item => {
      if (item.section && item.section !== lastSection) {
        html += `<div class="nav-section-label">${escapeHtml(item.section)}</div>`;
        lastSection = item.section;
      }
      html += `<div class="nav-item" data-route="${item.key}">
        <span class="icon">${item.icon}</span>
        <span>${escapeHtml(item.label)}</span>
      </div>`;
    });
  nav.innerHTML = html;
  nav.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => {
      navigate(el.dataset.route);
      document.getElementById('sidebar').classList.remove('open');
    });
  });
}

function setActiveNav(route) {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.route === route.split('/')[0]);
  });
}

/* ── Progress bar ── */
function progressStart() {
  const bar = document.getElementById('page-progress-bar');
  bar.style.width = '40%';
  bar.style.transition = 'width .4s ease';
}
function progressDone() {
  const bar = document.getElementById('page-progress-bar');
  bar.style.width = '100%';
  bar.style.transition = 'width .2s ease';
  setTimeout(() => { bar.style.width = '0'; bar.style.transition = 'none'; }, 400);
}

/* ── Router ── */
async function navigate(route) {
  window.location.hash = route;
}

async function handleRoute() {
  const hash = window.location.hash.replace(/^#\/?/, '') || 'dashboard';
  const [view, ...rest] = hash.split('/');
  const param = rest.join('/');
  setActiveNav(hash);

  const content = document.getElementById('content');
  const renderer = Views[view];
  if (!renderer) {
    content.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔍</div>Page not found.</div>`;
    return;
  }
  progressStart();
  try {
    await renderer(content, param);
  } catch (err) {
    console.error(err);
    content.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div>${escapeHtml(err.message || 'Failed to load this view.')}</div>`;
  } finally {
    progressDone();
  }
}

/* ── Live Clock ── */
function startClock() {
  const timeEl = document.getElementById('clock-time');
  const dateEl = document.getElementById('clock-date');
  function tick() {
    const now = new Date();
    timeEl.textContent = now.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    dateEl.textContent = now.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  }
  tick();
  setInterval(tick, 1000);
}

/* ── Global search ── */
let searchDebounce;
function initSearch() {
  const input = document.getElementById('global-search');
  const results = document.getElementById('search-results');

  // '/' key focuses search
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && document.activeElement !== input) {
      e.preventDefault();
      input.focus();
    }
    if (e.key === 'Escape') {
      results.classList.add('hidden');
      input.blur();
    }
  });

  input.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    const q = input.value.trim();
    if (q.length < 2) { results.classList.add('hidden'); return; }
    searchDebounce = setTimeout(async () => {
      try {
        const data = await Api.search(q);
        renderSearchResults(data, results);
      } catch (e) { /* ignore */ }
    }, 250);
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.topbar-search')) results.classList.add('hidden');
  });
}

function renderSearchResults(data, container) {
  const groups = [
    { key: 'branches',    label: 'Branches',    route: 'branch-detail', name: r => r.name,          sub: r => r.branch_code },
    { key: 'atms',        label: 'ATMs',         route: 'atm-detail',    name: r => r.atm_code,      sub: r => r.branch_name },
    { key: 'computers',   label: 'Computers',    route: null,            name: r => r.asset_number,  sub: r => r.hostname },
    { key: 'employees',   label: 'Employees',    route: null,            name: r => r.full_name,     sub: r => r.employee_id_code },
    { key: 'tickets',     label: 'Tickets',      route: null,            name: r => r.ticket_code,   sub: r => r.problem_category },
    { key: 'incidents',   label: 'Incidents',    route: null,            name: r => r.incident_code, sub: r => r.category },
    { key: 'assets',      label: 'Assets',       route: null,            name: r => r.asset_code,    sub: r => r.asset_type },
    { key: 'technicians', label: 'Technicians',  route: null,            name: r => r.full_name,     sub: r => r.specialty },
  ];
  let html = '';
  let hasAny = false;
  groups.forEach(g => {
    const items = data[g.key] || [];
    if (!items.length) return;
    hasAny = true;
    html += `<div class="search-group-title">${g.label}</div>`;
    items.forEach((item, idx) => {
      html += `<div class="search-item" data-group="${g.key}" data-idx="${idx}">
        <span>${escapeHtml(g.name(item))}</span>
        <span style="color:var(--text-faint)">${escapeHtml(g.sub(item) || '')}</span>
      </div>`;
    });
  });
  container.innerHTML = hasAny ? html : `<div class="search-item" style="color:var(--text-faint)">No matches found.</div>`;
  container.classList.remove('hidden');
  container.querySelectorAll('.search-item[data-group]').forEach(el => {
    el.addEventListener('click', () => {
      const g = groups.find(gr => gr.key === el.dataset.group);
      const item = data[g.key][Number(el.dataset.idx)];
      container.classList.add('hidden');
      document.getElementById('global-search').value = '';
      if (g.route) navigate(`${g.route}/${item.id}`);
      else if (g.key === 'tickets') openTicketDetail(item.id);
      else toast(`${g.label.slice(0, -1)}: ${g.name(item)}`, 'info');
    });
  });
}

/* ── Notifications ── */
async function refreshNotifBadge() {
  try {
    const { unread_count } = await Api.unreadCount();
    const el = document.getElementById('notif-count');
    if (unread_count > 0) {
      el.textContent = unread_count > 99 ? '99+' : unread_count;
      el.classList.remove('hidden');
    } else {
      el.classList.add('hidden');
    }
  } catch (e) { /* ignore */ }
}

function initNotifPanel() {
  const btn = document.getElementById('notif-btn');
  const panel = document.getElementById('notif-panel');
  btn.addEventListener('click', async (e) => {
    e.stopPropagation();
    if (!panel.classList.contains('hidden')) { panel.classList.add('hidden'); return; }
    panel.innerHTML = `<div class="notif-panel-header">🔔 Notifications</div><div class="notif-item" style="color:var(--text-faint);font-size:12px">Loading…</div>`;
    panel.classList.remove('hidden');
    try {
      const items = await Api.listNotifications('?unread_only=false');
      panel.innerHTML = `<div class="notif-panel-header">🔔 Notifications</div>` +
        (items.slice(0, 12).map(n => `
          <div class="notif-item">
            <div class="notif-title">${badge(n.severity)} ${escapeHtml(n.title)}</div>
            <div class="notif-msg">${escapeHtml(n.message)}</div>
            <div class="notif-time">${timeAgo(n.created_at)}</div>
          </div>
        `).join('') || `<div class="notif-item">No notifications yet.</div>`);
    } catch {
      panel.innerHTML = `<div class="notif-item" style="color:var(--text-faint)">Failed to load.</div>`;
    }
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#notif-panel') && !e.target.closest('#notif-btn')) panel.classList.add('hidden');
  });
}

/* ── User Dropdown ── */
function initUserDropdown() {
  const chip = document.getElementById('user-chip');
  const dropdown = document.getElementById('user-dropdown');
  chip.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('hidden');
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('#user-chip') && !e.target.closest('#user-dropdown')) {
      dropdown.classList.add('hidden');
    }
  });
}

/* ── Auth flow ── */
function showLogin() {
  document.getElementById('login-screen').classList.remove('hidden');
  document.getElementById('app-shell').classList.add('hidden');
}

function showApp() {
  document.getElementById('login-screen').classList.add('hidden');
  document.getElementById('app-shell').classList.remove('hidden');
  const user = Session.user;
  const initials = user.full_name.split(' ').map(p => p[0]).slice(0, 2).join('').toUpperCase();
  const roleLabel = user.role.replace(/_/g, ' ');

  // Topbar
  document.getElementById('user-name').textContent = user.full_name;
  document.getElementById('user-role').textContent = roleLabel;
  document.getElementById('user-avatar').textContent = initials;

  // Dropdown
  document.getElementById('user-dropdown-avatar').textContent = initials;
  document.getElementById('user-dropdown-name').textContent = user.full_name;
  document.getElementById('user-dropdown-role').textContent = roleLabel;

  // Sidebar footer
  document.getElementById('sidebar-user-avatar').textContent = initials;
  document.getElementById('sidebar-user-name').textContent = user.full_name;
  document.getElementById('sidebar-user-role').textContent = roleLabel;

  // Last login timestamp, as recorded by the backend at auth time.
  const lastLoginEl = document.getElementById('sidebar-last-login');
  lastLoginEl.textContent = user.last_login ? `🕒 Last login: ${fmtDateTime(user.last_login)}` : '';

  buildSidebar();
  startClock();
  handleRoute();
  refreshNotifBadge();
  setInterval(refreshNotifBadge, 30000);
}

/* ── Login form ── */
document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errorEl = document.getElementById('login-error');
  errorEl.classList.add('hidden');
  const btn = document.getElementById('login-btn');
  const btnText = btn.querySelector('.btn-text');
  const btnSpinner = btn.querySelector('.btn-spinner');
  btn.disabled = true;
  btnText.textContent = 'Signing in…';
  btnSpinner.classList.remove('hidden');
  try {
    const res = await Api.login(username, password);
    Session.token = res.access_token;
    Session.user = res.user;
    toast(`Welcome back, ${res.user.full_name}! 👋`, 'success');
    showApp();
  } catch (err) {
    errorEl.textContent = '⚠ ' + (err.message || 'Invalid credentials. Please try again.');
    errorEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btnText.textContent = 'Sign In';
    btnSpinner.classList.add('hidden');
  }
});

/* ── Logout ── */
document.getElementById('logout-btn').addEventListener('click', async () => {
  const ok = await confirmAction('You will be signed out of the system.', {
    title: 'Sign Out',
    icon: '🚪',
    okLabel: 'Sign Out',
    danger: true,
  });
  if (!ok) return;
  Session.clear();
  destroyCharts();
  window.location.hash = '';
  document.getElementById('user-dropdown').classList.add('hidden');
  showLogin();
  toast('You have been signed out.', 'info');
});

/* ── Mobile sidebar ── */
document.getElementById('menu-toggle').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('open');
});

window.addEventListener('hashchange', handleRoute);

/* ── Boot ── */
(async function boot() {
  initSearch();
  initNotifPanel();
  initUserDropdown();
  if (Session.token && Session.user) {
    try {
      const user = await Api.me();
      Session.user = user;
      showApp();
    } catch (e) {
      Session.clear();
      showLogin();
    }
  } else {
    showLogin();
  }
})();
