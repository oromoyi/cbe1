/* App bootstrap: auth flow, sidebar nav, routing */

const NAV_ITEMS = [
  { key: "dashboard", label: "Dashboard", icon: "◆", roles: null },
  { key: "branches", label: "Branches", icon: "🏢", roles: null },
  { key: "atms", label: "ATMs", icon: "🏧", roles: null },
  { key: "atm-errors", label: "ATM Errors", icon: "⚠", roles: null },
  { key: "network-installations", label: "Network Installation", icon: "🌐", roles: null },
  { key: "computers", label: "Computers", icon: "💻", roles: null },
  { key: "tickets", label: "IT Tickets", icon: "🎫", roles: null },
  { key: "incidents", label: "Incidents", icon: "🚨", roles: null },
  { key: "equipment", label: "Equipment", icon: "📦", roles: null },
  { key: "maintenance", label: "Maintenance", icon: "🛠", roles: null },
  { key: "remote-support", label: "Remote Support", icon: "🖥", roles: null },
  { key: "knowledge-base", label: "Knowledge Base", icon: "📘", roles: null },
  { key: "reports", label: "Reports", icon: "📊", roles: null },
  { key: "notifications", label: "Notifications", icon: "🔔", roles: null },
  { key: "users", label: "Users", icon: "👥", roles: ["district_admin"] },
  { key: "settings", label: "CBE Settings", icon: "⚙", roles: ["district_admin"] },
  { key: "audit-logs", label: "Audit Logs", icon: "📜", roles: ["district_admin"] },
];

function buildSidebar() {
  const user = Session.user;
  const nav = document.getElementById("sidebar-nav");
  nav.innerHTML = NAV_ITEMS
    .filter(item => !item.roles || item.roles.includes(user.role))
    .map(item => `<div class="nav-item" data-route="${item.key}"><span class="icon">${item.icon}</span><span>${item.label}</span></div>`)
    .join("");
  nav.querySelectorAll(".nav-item").forEach(el => {
    el.addEventListener("click", () => {
      navigate(el.dataset.route);
      document.getElementById("sidebar").classList.remove("open");
    });
  });
}

function setActiveNav(route) {
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.dataset.route === route.split("/")[0]);
  });
}

async function navigate(route) {
  window.location.hash = route;
}

async function handleRoute() {
  const hash = window.location.hash.replace(/^#\/?/, "") || "dashboard";
  const [view, ...rest] = hash.split("/");
  const param = rest.join("/");
  setActiveNav(hash);

  const content = document.getElementById("content");
  const renderer = Views[view];
  if (!renderer) {
    content.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔍</div>Page not found.</div>`;
    return;
  }
  try {
    await renderer(content, param);
  } catch (err) {
    console.error(err);
    content.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠</div>${escapeHtml(err.message || "Failed to load this view.")}</div>`;
  }
}

/* ---------------- Global search ---------------- */
let searchDebounce;
function initSearch() {
  const input = document.getElementById("global-search");
  const results = document.getElementById("search-results");
  input.addEventListener("input", () => {
    clearTimeout(searchDebounce);
    const q = input.value.trim();
    if (q.length < 2) { results.classList.add("hidden"); return; }
    searchDebounce = setTimeout(async () => {
      try {
        const data = await Api.search(q);
        renderSearchResults(data, results);
      } catch (e) { /* ignore */ }
    }, 250);
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".topbar-search")) results.classList.add("hidden");
  });
}

function renderSearchResults(data, container) {
  const groups = [
    { key: "branches", label: "Branches", route: "branch-detail", name: r => r.name, sub: r => r.branch_code },
    { key: "atms", label: "ATMs", route: "atm-detail", name: r => r.atm_code, sub: r => r.branch_name },
    { key: "computers", label: "Computers", route: null, name: r => r.asset_number, sub: r => r.hostname },
    { key: "employees", label: "Employees", route: null, name: r => r.full_name, sub: r => r.employee_id_code },
    { key: "tickets", label: "Tickets", route: null, name: r => r.ticket_code, sub: r => r.problem_category },
    { key: "incidents", label: "Incidents", route: null, name: r => r.incident_code, sub: r => r.category },
    { key: "assets", label: "Assets", route: null, name: r => r.asset_code, sub: r => r.asset_type },
    { key: "technicians", label: "Technicians", route: null, name: r => r.full_name, sub: r => r.specialty },
  ];
  let html = "";
  let hasAny = false;
  groups.forEach(g => {
    const items = data[g.key] || [];
    if (!items.length) return;
    hasAny = true;
    html += `<div class="search-group-title">${g.label}</div>`;
    items.forEach((item, idx) => {
      html += `<div class="search-item" data-group="${g.key}" data-idx="${idx}"><span>${escapeHtml(g.name(item))}</span><span style="color:var(--text-faint)">${escapeHtml(g.sub(item) || "")}</span></div>`;
    });
  });
  container.innerHTML = hasAny ? html : `<div class="search-item" style="color:var(--text-faint)">No matches found.</div>`;
  container.classList.remove("hidden");
  container.querySelectorAll(".search-item[data-group]").forEach(el => {
    el.addEventListener("click", () => {
      const g = groups.find(gr => gr.key === el.dataset.group);
      const item = data[g.key][Number(el.dataset.idx)];
      container.classList.add("hidden");
      document.getElementById("global-search").value = "";
      if (g.route) navigate(`${g.route}/${item.id}`);
      else if (g.key === "tickets") openTicketDetail(item.id);
      else toast(`${g.label.slice(0, -1)}: ${g.name(item)}`, "info");
    });
  });
}

/* ---------------- Notifications badge ---------------- */
async function refreshNotifBadge() {
  try {
    const { unread_count } = await Api.unreadCount();
    const el = document.getElementById("notif-count");
    if (unread_count > 0) { el.textContent = unread_count > 99 ? "99+" : unread_count; el.classList.remove("hidden"); }
    else el.classList.add("hidden");
  } catch (e) { /* ignore */ }
}

function initNotifPanel() {
  const btn = document.getElementById("notif-btn");
  const panel = document.getElementById("notif-panel");
  btn.addEventListener("click", async (e) => {
    e.stopPropagation();
    if (!panel.classList.contains("hidden")) { panel.classList.add("hidden"); return; }
    const items = await Api.listNotifications("?unread_only=false");
    panel.innerHTML = items.slice(0, 10).map(n => `
      <div class="notif-item">
        <div class="notif-title">${badge(n.severity)} ${escapeHtml(n.title)}</div>
        <div class="notif-msg">${escapeHtml(n.message)}</div>
        <div class="notif-time">${timeAgo(n.created_at)}</div>
      </div>
    `).join("") || `<div class="notif-item">No notifications yet.</div>`;
    panel.classList.remove("hidden");
  });
  document.addEventListener("click", (e) => {
    if (!e.target.closest("#notif-panel") && !e.target.closest("#notif-btn")) panel.classList.add("hidden");
  });
}

/* ---------------- Auth flow ---------------- */
function showLogin() {
  document.getElementById("login-screen").classList.remove("hidden");
  document.getElementById("app-shell").classList.add("hidden");
}

function showApp() {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app-shell").classList.remove("hidden");
  const user = Session.user;
  document.getElementById("user-name").textContent = user.full_name;
  document.getElementById("user-role").textContent = user.role.replace(/_/g, " ");
  document.getElementById("user-avatar").textContent = user.full_name.split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
  buildSidebar();
  handleRoute();
  refreshNotifBadge();
  setInterval(refreshNotifBadge, 30000);
}

document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("login-username").value.trim();
  const password = document.getElementById("login-password").value;
  const errorEl = document.getElementById("login-error");
  errorEl.classList.add("hidden");
  const btn = e.target.querySelector("button[type=submit]");
  btn.disabled = true; btn.textContent = "Signing in…";
  try {
    const res = await Api.login(username, password);
    Session.token = res.access_token;
    Session.user = res.user;
    showApp();
  } catch (err) {
    errorEl.textContent = err.message || "Login failed.";
    errorEl.classList.remove("hidden");
  } finally {
    btn.disabled = false; btn.textContent = "Sign in";
  }
});

document.getElementById("logout-btn").addEventListener("click", () => {
  Session.clear();
  destroyCharts();
  window.location.hash = "";
  showLogin();
});

document.getElementById("menu-toggle").addEventListener("click", () => {
  document.getElementById("sidebar").classList.toggle("open");
});

window.addEventListener("hashchange", handleRoute);

/* ---------------- Boot ---------------- */
(async function boot() {
  initSearch();
  initNotifPanel();
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
