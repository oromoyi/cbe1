/* View renderers for each module of the CBE District IT Console */
const Views = {};
let chartInstances = {};

function destroyCharts() {
  Object.values(chartInstances).forEach(c => c && c.destroy());
  chartInstances = {};
}

function pageHeader(title, sub, actionsHtml = "") {
  return `<div class="page-header">
    <div><div class="page-title">${escapeHtml(title)}</div>${sub ? `<div class="page-sub">${escapeHtml(sub)}</div>` : ""}</div>
    <div class="page-actions">${actionsHtml}</div>
  </div>`;
}

/* ============================= DASHBOARD ============================= */
Views.dashboard = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading district overview…</div>`;

  if (typeof Chart === "undefined") {
    root.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠</div>
        Chart.js failed to load. Refresh the page or restart the app to reload the dashboard assets.
      </div>
    `;
    return;
  }

  const [summary, charts] = await Promise.all([Api.dashboardSummary(), Api.dashboardCharts()]);
  destroyCharts();

  root.innerHTML = `
    ${pageHeader("District IT Overview", "Real-time (simulated) status across all CBE branches under this district office.")}
    <div class="kpi-grid">
      ${kpi("Branches", summary.total_branches, "accent")}
      ${kpi("Total ATMs", summary.total_atms, "accent")}
      ${kpi("Operational ATMs", summary.operational_atms, "green")}
      ${kpi("Offline ATMs", summary.offline_atms, "red")}
      ${kpi("Open ATM Errors", summary.atm_errors, "yellow")}
      ${kpi("Pending Tickets", summary.pending_tickets, "blue")}
      ${kpi("In-progress Tickets", summary.in_progress_tickets, "yellow")}
      ${kpi("Resolved Tickets", summary.resolved_tickets, "green")}
      ${kpi("Network Installations", summary.network_installations, "accent")}
      ${kpi("Completed Installs", summary.completed_installations, "green")}
      ${kpi("Pending Installs", summary.pending_installations, "blue")}
      ${kpi("Computers w/ Problems", summary.computers_with_problems, "red")}
      ${kpi("Active Technicians", summary.active_technicians, "accent")}
    </div>

    <div class="chart-grid">
      <div class="panel"><div class="panel-title">ATM Status Distribution</div><div class="chart-wrap"><canvas id="c-atm-status"></canvas></div></div>
      <div class="panel"><div class="panel-title">IT Incidents by Branch</div><div class="chart-wrap"><canvas id="c-incidents-branch"></canvas></div></div>
      <div class="panel"><div class="panel-title">ATM Error Types</div><div class="chart-wrap"><canvas id="c-error-types"></canvas></div></div>
      <div class="panel"><div class="panel-title">Monthly Support Requests</div><div class="chart-wrap"><canvas id="c-monthly"></canvas></div></div>
      <div class="panel"><div class="panel-title">Network Installation Progress</div><div class="chart-wrap"><canvas id="c-install-progress"></canvas></div></div>
      <div class="panel"><div class="panel-title">Resolved vs Unresolved Tickets</div><div class="chart-wrap"><canvas id="c-resolved"></canvas></div></div>
    </div>

    <div class="panel">
      <div class="panel-title">Branch Status Map</div>
      <div id="branch-tiles" class="branch-status-grid"></div>
    </div>
  `;

  const palette = ["#7C5CFF", "#4C9EFF", "#34D399", "#F5B93D", "#F0576B", "#E0A93A", "#6672A0"];
  const chartDefaults = {
    plugins: { legend: { labels: { color: "#9AA3C4", font: { size: 11 } } } },
    scales: { x: { ticks: { color: "#6672A0" }, grid: { color: "#1D253F" } }, y: { ticks: { color: "#6672A0" }, grid: { color: "#1D253F" } } },
  };

  chartInstances.atmStatus = new Chart(document.getElementById("c-atm-status"), {
    type: "doughnut",
    data: { labels: Object.keys(charts.atm_status), datasets: [{ data: Object.values(charts.atm_status), backgroundColor: palette }] },
    options: { plugins: chartDefaults.plugins, cutout: "62%" },
  });

  chartInstances.incidentsBranch = new Chart(document.getElementById("c-incidents-branch"), {
    type: "bar",
    data: { labels: Object.keys(charts.incidents_by_branch), datasets: [{ label: "Incidents", data: Object.values(charts.incidents_by_branch), backgroundColor: "#7C5CFF" }] },
    options: { ...chartDefaults, plugins: { legend: { display: false } } },
  });

  chartInstances.errorTypes = new Chart(document.getElementById("c-error-types"), {
    type: "pie",
    data: { labels: Object.keys(charts.error_types), datasets: [{ data: Object.values(charts.error_types), backgroundColor: palette }] },
    options: { plugins: chartDefaults.plugins },
  });

  chartInstances.monthly = new Chart(document.getElementById("c-monthly"), {
    type: "line",
    data: { labels: charts.monthly_support_requests.labels, datasets: [{ label: "Requests", data: charts.monthly_support_requests.values, borderColor: "#4C9EFF", backgroundColor: "#4C9EFF33", tension: .35, fill: true }] },
    options: { ...chartDefaults, plugins: { legend: { display: false } } },
  });

  chartInstances.installProgress = new Chart(document.getElementById("c-install-progress"), {
    type: "bar",
    data: { labels: Object.keys(charts.installation_progress), datasets: [{ label: "Projects", data: Object.values(charts.installation_progress), backgroundColor: "#E0A93A" }] },
    options: { ...chartDefaults, plugins: { legend: { display: false } }, indexAxis: "y" },
  });

  chartInstances.resolved = new Chart(document.getElementById("c-resolved"), {
    type: "doughnut",
    data: { labels: ["Resolved", "Unresolved"], datasets: [{ data: [charts.resolved_vs_unresolved.resolved, charts.resolved_vs_unresolved.unresolved], backgroundColor: ["#34D399", "#F0576B"] }] },
    options: { plugins: chartDefaults.plugins, cutout: "62%" },
  });

  const branches = await Api.listBranches();
  document.getElementById("branch-tiles").innerHTML = branches.map(b => `
    <div class="branch-tile" data-branch-id="${b.id}">
      <div class="branch-tile-name">${statusDot(b.overall_it_status)}${escapeHtml(b.name)}</div>
      <div class="branch-tile-meta">${escapeHtml(b.branch_code)} · ${b.atm_count ?? b.number_of_atms} ATMs · ${b.open_tickets ?? 0} open tickets</div>
    </div>
  `).join("");
  document.querySelectorAll(".branch-tile").forEach(t => t.addEventListener("click", () => navigate(`branch-detail/${t.dataset.branchId}`)));
};

function kpi(label, value, color) {
  return `<div class="kpi-card"><div class="kpi-label">${escapeHtml(label)}</div><div class="kpi-value kpi-${color}">${value ?? 0}</div></div>`;
}

/* ============================= BRANCHES ============================= */
Views.branches = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading branches…</div>`;
  const branches = await Api.listBranches();

  root.innerHTML = `
    ${pageHeader("Branches", "All CBE branches supported by this district IT office.", roleAllows("district_admin") ? `<button class="btn btn-primary" id="add-branch">+ Add Branch</button>` : "")}
    <div class="table-toolbar">
      <input type="text" id="branch-search" placeholder="Search branch name or code…" />
    </div>
    <div id="branch-table"></div>
  `;

  const cols = [
    { key: "branch_code", label: "Code", render: r => `<span class="mono">${escapeHtml(r.branch_code)}</span>` },
    { key: "name", label: "Branch" },
    { key: "location", label: "Location" },
    { key: "branch_manager_name", label: "Manager" },
    { key: "atm_count", label: "ATMs", render: r => r.atm_count ?? r.number_of_atms },
    { key: "computer_count", label: "Computers", render: r => r.computer_count ?? r.number_of_computers },
    { key: "network_status", label: "Network", render: r => badge(r.network_status) },
    { key: "overall_it_status", label: "IT Status", render: r => badge(r.overall_it_status) },
    { key: "open_tickets", label: "Open Tickets" },
  ];

  const draw = (list) => {
    const container = document.getElementById("branch-table");
    container.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No branches found." });
    attachRowClicks(container, list, (row) => navigate(`branch-detail/${row.id}`));
  };
  draw(branches);

  document.getElementById("branch-search").addEventListener("input", (e) => {
    const v = e.target.value.toLowerCase();
    draw(branches.filter(b => b.name.toLowerCase().includes(v) || b.branch_code.toLowerCase().includes(v)));
  });

  const addBtn = document.getElementById("add-branch");
  if (addBtn) addBtn.addEventListener("click", () => openBranchForm());
};

function openBranchForm(existing) {
  openModal({
    title: existing ? "Edit Branch" : "Add Branch",
    bodyHtml: `<form id="branch-form" class="form-grid">
      ${field({ label: "Branch Code", name: "branch_code", value: existing?.branch_code, required: true })}
      ${field({ label: "Branch Name", name: "name", value: existing?.name, required: true })}
      ${field({ label: "Location", name: "location", value: existing?.location, full: true })}
      ${field({ label: "Contact Number", name: "contact_number", value: existing?.contact_number })}
      ${field({ label: "Branch Manager", name: "branch_manager_name", value: existing?.branch_manager_name })}
      ${field({ label: "# Computers", name: "number_of_computers", type: "number", value: existing?.number_of_computers ?? 0 })}
      ${field({ label: "# ATMs", name: "number_of_atms", type: "number", value: existing?.number_of_atms ?? 0 })}
      ${field({ label: "Network Status", name: "network_status", type: "select", value: existing?.network_status || "CONNECTED", options: ["CONNECTED", "DEGRADED", "DISCONNECTED"] })}
      ${field({ label: "Overall IT Status", name: "overall_it_status", type: "select", value: existing?.overall_it_status || "GREEN", options: ["GREEN", "YELLOW", "RED"] })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">${existing ? "Save Changes" : "Create Branch"}</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("branch-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = formToObject(e.target);
        try {
          if (existing) await Api.updateBranch(existing.id, data);
          else await Api.createBranch(data);
          toast(existing ? "Branch updated." : "Branch created.", "success");
          closeModal();
          navigate("branches");
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

Views["branch-detail"] = async (root, id) => {
  root.innerHTML = `<div class="empty-state">Loading branch…</div>`;
  const b = await Api.getBranch(id);

  root.innerHTML = `
    ${pageHeader(b.name, `${b.branch_code} · ${b.location || ""}`, `
      <button class="btn btn-ghost" id="back-btn">← Back</button>
      ${roleAllows("district_admin") ? `<button class="btn btn-primary" id="edit-branch">Edit Branch</button>` : ""}
    `)}

    <div class="flow-chain panel" style="margin-bottom:20px;">
      ${flowStep("Branch Information", `${b.branch_manager_name || "—"} · ${b.contact_number || "—"}`)}
      ${flowStep("ATM Status", `${b.atms.length} ATM(s) — ${b.atms.filter(a=>a.status==='ONLINE').length} online`)}
      ${flowStep("Network Status", badge(b.network_status))}
      ${flowStep("Computer Status", `${b.computers.length} computer(s) — ${b.computers.filter(c=>c.status==='WORKING').length} working`)}
      ${flowStep("Open IT Problems", `${b.open_tickets_list.length} open ticket(s)`)}
      ${flowStep("Maintenance History", `${b.maintenance_history.length} record(s)`)}
      ${flowStep("Installation History", `${b.installation_history.length} project(s)`)}
    </div>

    <div class="tabs">
      <button class="tab-btn active" data-tab="atms">ATMs</button>
      <button class="tab-btn" data-tab="computers">Computers</button>
      <button class="tab-btn" data-tab="tickets">Open Tickets</button>
      <button class="tab-btn" data-tab="maintenance">Maintenance</button>
      <button class="tab-btn" data-tab="installs">Installations</button>
    </div>
    <div id="tab-content"></div>
  `;

  document.getElementById("back-btn").onclick = () => navigate("branches");
  const editBtn = document.getElementById("edit-branch");
  if (editBtn) editBtn.onclick = () => openBranchForm(b);

  const renderTab = (tab) => {
    const el = document.getElementById("tab-content");
    if (tab === "atms") {
      el.innerHTML = renderTable({
        columns: [
          { key: "atm_code", label: "ATM", render: r => `<span class="mono">${r.atm_code}</span>` },
          { key: "status", label: "Status", render: r => badge(r.status) },
          { key: "network_connection", label: "Network", render: r => badge(r.network_connection) },
          { key: "last_checked_at", label: "Last Checked", render: r => fmtDateTime(r.last_checked_at) },
        ], rows: b.atms, emptyText: "No ATMs at this branch.",
      });
      attachRowClicks(el, b.atms, (row) => navigate(`atm-detail/${row.id}`));
    } else if (tab === "computers") {
      el.innerHTML = renderTable({
        columns: [
          { key: "asset_number", label: "Asset #", render: r => `<span class="mono">${r.asset_number}</span>` },
          { key: "hostname", label: "Hostname" },
          { key: "employee_name", label: "User" },
          { key: "status", label: "Status", render: r => badge(r.status) },
        ], rows: b.computers, emptyText: "No computers registered.",
      });
    } else if (tab === "tickets") {
      el.innerHTML = renderTable({
        columns: [
          { key: "ticket_code", label: "Ticket", render: r => `<span class="mono">${r.ticket_code}</span>` },
          { key: "problem_category", label: "Category" },
          { key: "priority", label: "Priority", render: r => badge(r.priority) },
          { key: "status", label: "Status", render: r => badge(r.status) },
        ], rows: b.open_tickets_list, emptyText: "No open tickets.",
      });
      attachRowClicks(el, b.open_tickets_list, (row) => openTicketDetail(row.id));
    } else if (tab === "maintenance") {
      el.innerHTML = renderTable({
        columns: [
          { key: "maintenance_type", label: "Type", render: r => badge(r.maintenance_type) },
          { key: "scheduled_date", label: "Scheduled", render: r => fmtDate(r.scheduled_date) },
          { key: "result", label: "Result", render: r => badge(r.result) },
        ], rows: b.maintenance_history, emptyText: "No maintenance history.",
      });
    } else if (tab === "installs") {
      el.innerHTML = renderTable({
        columns: [
          { key: "installation_type", label: "Type" },
          { key: "status", label: "Status", render: r => badge(r.status) },
          { key: "start_date", label: "Start", render: r => fmtDate(r.start_date) },
        ], rows: b.installation_history, emptyText: "No installation projects.",
      });
      attachRowClicks(el, b.installation_history, (row) => navigate(`installation-detail/${row.id}`));
    }
  };
  renderTab("atms");
  document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b2 => b2.classList.remove("active"));
    btn.classList.add("active");
    renderTab(btn.dataset.tab);
  }));
};

function flowStep(title, value) {
  return `<div class="flow-step"><div class="detail-label">${escapeHtml(title)}</div><div class="detail-value">${value}</div></div>`;
}

/* ============================= ATMs ============================= */
Views.atms = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading ATMs…</div>`;
  const [atms, branches] = await Promise.all([Api.listAtms(), Api.listBranches()]);

  root.innerHTML = `
    ${pageHeader("ATM Monitoring", "Live (simulated) ATM status across all branches.", roleAllows("district_admin", "technician") ? `<button class="btn btn-primary" id="add-atm">+ Register ATM</button>` : "")}
    <div class="table-toolbar">
      <input type="text" id="atm-search" placeholder="Search ATM code / serial…" />
      <select id="atm-branch-filter"><option value="">All Branches</option>${branches.map(b => `<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("")}</select>
      <select id="atm-status-filter"><option value="">All Statuses</option>${["ONLINE","OFFLINE","WARNING","MAINTENANCE","ERROR","UNKNOWN"].map(s => `<option value="${s}">${s}</option>`).join("")}</select>
    </div>
    <div id="atm-table"></div>
  `;

  const cols = [
    { key: "atm_code", label: "ATM", render: r => `<span class="mono">${escapeHtml(r.atm_code)}</span>` },
    { key: "branch_name", label: "Branch" },
    { key: "status", label: "Status", render: r => badge(r.status) },
    { key: "network_connection", label: "Network", render: r => badge(r.network_connection) },
    { key: "ip_address", label: "IP", render: r => `<span class="mono">${escapeHtml(r.ip_address || "—")}</span>` },
    { key: "last_checked_at", label: "Last Checked", render: r => r.last_checked_at ? timeAgo(r.last_checked_at) : "Never" },
    { key: "actions", label: "", render: r => roleAllows("district_admin", "technician") ? `<button class="btn btn-sm btn-primary check-btn" data-id="${r.id}">Check ATM</button>` : "" },
  ];

  let currentList = atms;
  const draw = (list) => {
    currentList = list;
    const container = document.getElementById("atm-table");
    container.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No ATMs found." });
    attachRowClicks(container, list, (row) => navigate(`atm-detail/${row.id}`));
    container.querySelectorAll(".check-btn").forEach(btn => btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      btn.disabled = true; btn.textContent = "Checking…";
      try {
        const res = await Api.checkAtm(btn.dataset.id, {});
        toast(`${res.atm.atm_code}: ${res.atm.status} (${res.check.is_simulated ? "simulated check" : "monitoring API"})`, "success");
        Views.atms(root);
      } catch (err) { toast(err.message, "error"); btn.disabled = false; btn.textContent = "Check ATM"; }
    }));
  };
  draw(atms);

  const applyFilters = () => {
    const s = document.getElementById("atm-search").value.toLowerCase();
    const branch = document.getElementById("atm-branch-filter").value;
    const status = document.getElementById("atm-status-filter").value;
    draw(atms.filter(a =>
      (!s || a.atm_code.toLowerCase().includes(s) || (a.serial_number || "").toLowerCase().includes(s)) &&
      (!branch || String(a.branch_id) === branch) &&
      (!status || a.status === status)
    ));
  };
  ["atm-search", "atm-branch-filter", "atm-status-filter"].forEach(id => document.getElementById(id).addEventListener("input", applyFilters));

  const addBtn = document.getElementById("add-atm");
  if (addBtn) addBtn.addEventListener("click", () => openAtmForm(branches));
};

function openAtmForm(branches, existing) {
  openModal({
    title: existing ? "Edit ATM" : "Register ATM",
    bodyHtml: `<form id="atm-form" class="form-grid">
      ${field({ label: "ATM Code", name: "atm_code", value: existing?.atm_code, required: true, placeholder: "ATM-018" })}
      ${field({ label: "Serial Number", name: "serial_number", value: existing?.serial_number })}
      ${field({ label: "Branch", name: "branch_id", type: "select", value: existing?.branch_id, required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Model / Type", name: "model_type", value: existing?.model_type })}
      ${field({ label: "Location Description", name: "location_description", value: existing?.location_description })}
      ${field({ label: "IP Address", name: "ip_address", value: existing?.ip_address })}
      ${field({ label: "Installation Date", name: "installation_date", type: "date", value: existing?.installation_date })}
      ${field({ label: "Status", name: "status", type: "select", value: existing?.status || "UNKNOWN", options: ["ONLINE","OFFLINE","WARNING","MAINTENANCE","ERROR","UNKNOWN"] })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">${existing ? "Save Changes" : "Register ATM"}</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("atm-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = formToObject(e.target);
        try {
          if (existing) await Api.updateAtm(existing.id, data);
          else await Api.createAtm(data);
          toast(existing ? "ATM updated." : "ATM registered.", "success");
          closeModal();
          navigate("atms");
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

Views["atm-detail"] = async (root, id) => {
  root.innerHTML = `<div class="empty-state">Loading ATM…</div>`;
  const a = await Api.getAtm(id);

  root.innerHTML = `
    ${pageHeader(a.atm_code, `${a.branch_name} · ${a.model_type || "Unknown model"}`, `
      <button class="btn btn-ghost" id="back-btn">← Back</button>
      <button class="btn btn-primary" id="do-check">Check ATM</button>
      <button class="btn btn-danger" id="report-error">Report Error</button>
    `)}
    <div class="panel" style="margin-bottom:20px;">
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${badge(a.status)}</div></div>
        <div class="detail-item"><div class="detail-label">Network</div><div class="detail-value">${badge(a.network_connection)}</div></div>
        <div class="detail-item"><div class="detail-label">IP Address</div><div class="detail-value mono">${escapeHtml(a.ip_address || "—")}</div></div>
        <div class="detail-item"><div class="detail-label">Serial Number</div><div class="detail-value mono">${escapeHtml(a.serial_number || "—")}</div></div>
        <div class="detail-item"><div class="detail-label">Technician</div><div class="detail-value">${escapeHtml(a.technician_name || "Unassigned")}</div></div>
        <div class="detail-item"><div class="detail-label">Last Checked</div><div class="detail-value">${fmtDateTime(a.last_checked_at)}</div></div>
        <div class="detail-item"><div class="detail-label">Data Source</div><div class="detail-value">${a.is_simulated ? '<span class="badge badge-yellow">SIMULATED</span>' : '<span class="badge badge-green">LIVE MONITORING</span>'}</div></div>
        <div class="detail-item"><div class="detail-label">Error Status</div><div class="detail-value">${escapeHtml(a.error_status || "None")}</div></div>
      </div>
    </div>
    <div class="tabs">
      <button class="tab-btn active" data-tab="checks">Check History</button>
      <button class="tab-btn" data-tab="errors">Error Log</button>
    </div>
    <div id="tab-content"></div>
  `;

  document.getElementById("back-btn").onclick = () => navigate("atms");
  document.getElementById("do-check").onclick = async () => {
    try { await Api.checkAtm(a.id, {}); toast("ATM check completed.", "success"); Views["atm-detail"](root, id); }
    catch (err) { toast(err.message, "error"); }
  };
  document.getElementById("report-error").onclick = () => openAtmErrorForm(a);

  const renderTab = (tab) => {
    const el = document.getElementById("tab-content");
    if (tab === "checks") {
      el.innerHTML = renderTable({
        columns: [
          { key: "check_time", label: "Time", render: r => fmtDateTime(r.check_time) },
          { key: "availability_status", label: "Availability", render: r => badge(r.availability_status) },
          { key: "network_status", label: "Network", render: r => badge(r.network_status) },
          { key: "technician_name", label: "Technician" },
          { key: "is_simulated", label: "Source", render: r => r.is_simulated ? '<span class="badge badge-yellow">Simulated</span>' : '<span class="badge badge-green">Live</span>' },
          { key: "notes", label: "Notes" },
        ], rows: a.checks, emptyText: "No checks recorded yet.",
      });
    } else {
      el.innerHTML = renderTable({
        columns: [
          { key: "error_code", label: "Code", render: r => `<span class="mono">${r.error_code || "—"}</span>` },
          { key: "error_type", label: "Type" },
          { key: "error_group", label: "Group", render: r => badge(r.error_group) },
          { key: "severity", label: "Severity", render: r => badge(r.severity) },
          { key: "status", label: "Status", render: r => badge(r.status) },
          { key: "created_at", label: "Reported", render: r => fmtDate(r.created_at) },
        ], rows: a.errors, emptyText: "No errors recorded.",
      });
      attachRowClicks(el, a.errors, (row) => openAtmErrorDetail(row, a));
    }
  };
  renderTab("checks");
  document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b2 => b2.classList.remove("active"));
    btn.classList.add("active");
    renderTab(btn.dataset.tab);
  }));
};

async function openAtmErrorForm(atm) {
  const catalog = await Api.errorCatalog();
  const groupOptions = Object.keys(catalog);
  openModal({
    title: `Report ATM Error — ${atm.atm_code}`,
    bodyHtml: `<form id="err-form" class="form-grid">
      ${field({ label: "Error Group", name: "error_group", type: "select", value: "", required: true, options: groupOptions })}
      <label class="field"><span>Error Type</span><select name="error_type" id="error-type-select" required><option value="">Select group first…</option></select></label>
      ${field({ label: "Severity", name: "severity", type: "select", value: "MEDIUM", options: ["LOW", "MEDIUM", "HIGH", "CRITICAL"] })}
      ${field({ label: "Description", name: "description", type: "textarea", full: true, placeholder: "Technician-confirmed details of the issue" })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Record Error</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.querySelector('[name="error_group"]').addEventListener("change", (e) => {
        const sel = document.getElementById("error-type-select");
        const opts = catalog[e.target.value] || [];
        sel.innerHTML = `<option value="">Select…</option>` + opts.map(o => `<option value="${escapeHtml(o)}">${escapeHtml(o)}</option>`).join("");
      });
      document.getElementById("err-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = formToObject(e.target);
        data.atm_id = atm.id;
        try {
          await Api.createAtmError(data);
          toast("ATM error recorded.", "success");
          closeModal();
          navigate(`atm-detail/${atm.id}`);
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

function openAtmErrorDetail(err, atm) {
  openModal({
    title: `Error ${err.error_code || ""} — ${err.error_type}`,
    bodyHtml: `
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Group</div><div class="detail-value">${badge(err.error_group)}</div></div>
        <div class="detail-item"><div class="detail-label">Severity</div><div class="detail-value">${badge(err.severity)}</div></div>
        <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${badge(err.status)}</div></div>
        <div class="detail-item"><div class="detail-label">Reported</div><div class="detail-value">${fmtDate(err.created_at)}</div></div>
      </div>
      <p style="color:var(--text-muted);font-size:13px;">${escapeHtml(err.description || "No description provided.")}</p>
      ${roleAllows("district_admin", "technician") ? `
      <form id="resolve-form" class="form-grid">
        ${field({ label: "Status", name: "status", type: "select", value: err.status, options: ["OPEN", "IN_PROGRESS", "RESOLVED"] })}
        ${field({ label: "Resolution", name: "resolution", type: "textarea", value: err.resolution, full: true })}
        <div class="modal-footer full" style="grid-column:1/-1">
          <button type="submit" class="btn btn-primary">Update Error</button>
        </div>
      </form>` : ""}
    `,
    onMount: () => {
      const form = document.getElementById("resolve-form");
      if (form) form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          await Api.updateAtmError(err.id, formToObject(e.target));
          toast("Error record updated.", "success");
          closeModal();
          navigate(`atm-detail/${atm.id}`);
        } catch (er) { toast(er.message, "error"); }
      });
    },
  });
}

/* ============================= ATM ERRORS (global list) ============================= */
Views["atm-errors"] = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading ATM errors…</div>`;
  const errors = await Api.listAtmErrors();
  root.innerHTML = `
    ${pageHeader("ATM Error Management", "All recorded ATM errors across the district.")}
    <div class="table-toolbar">
      <select id="err-status-filter"><option value="">All Statuses</option>${["OPEN","IN_PROGRESS","RESOLVED"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
      <select id="err-severity-filter"><option value="">All Severities</option>${["LOW","MEDIUM","HIGH","CRITICAL"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
    </div>
    <div id="err-table"></div>
  `;
  const cols = [
    { key: "error_code", label: "Code", render: r => `<span class="mono">${r.error_code || "—"}</span>` },
    { key: "atm_code", label: "ATM" },
    { key: "branch_name", label: "Branch" },
    { key: "error_type", label: "Type" },
    { key: "error_group", label: "Group", render: r => badge(r.error_group) },
    { key: "severity", label: "Severity", render: r => badge(r.severity) },
    { key: "status", label: "Status", render: r => badge(r.status) },
    { key: "created_at", label: "Reported", render: r => fmtDate(r.created_at) },
  ];
  const draw = (list) => {
    const c = document.getElementById("err-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No ATM errors recorded." });
    attachRowClicks(c, list, (row) => openAtmErrorDetail(row, { id: row.atm_id }));
  };
  draw(errors);
  const applyFilters = () => {
    const status = document.getElementById("err-status-filter").value;
    const sev = document.getElementById("err-severity-filter").value;
    draw(errors.filter(e => (!status || e.status === status) && (!sev || e.severity === sev)));
  };
  ["err-status-filter", "err-severity-filter"].forEach(id => document.getElementById(id).addEventListener("change", applyFilters));
};

/* ============================= NETWORK INSTALLATIONS ============================= */
Views["network-installations"] = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading network installation projects…</div>`;
  const [installs, branches, technicians] = await Promise.all([Api.listInstallations(), Api.listBranches(), Api.listTechnicians()]);

  root.innerHTML = `
    ${pageHeader("Network Installation Management", "District network installation and upgrade projects.", roleAllows("district_admin", "technician") ? `<button class="btn btn-primary" id="add-install">+ New Project</button>` : "")}
    <div class="table-toolbar">
      <select id="inst-branch-filter"><option value="">All Branches</option>${branches.map(b => `<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("")}</select>
      <select id="inst-status-filter"><option value="">All Statuses</option>${["PLANNED","IN_PROGRESS","TESTING","COMPLETED","FAILED","CANCELLED"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
    </div>
    <div id="inst-table"></div>
  `;
  const cols = [
    { key: "branch_name", label: "Branch" },
    { key: "installation_type", label: "Type" },
    { key: "technician_name", label: "Technician" },
    { key: "status", label: "Status", render: r => badge(r.status) },
    { key: "start_date", label: "Start", render: r => fmtDate(r.start_date) },
    { key: "expected_completion", label: "Expected", render: r => fmtDate(r.expected_completion) },
  ];
  const draw = (list) => {
    const c = document.getElementById("inst-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No installation projects found." });
    attachRowClicks(c, list, (row) => navigate(`installation-detail/${row.id}`));
  };
  draw(installs);
  const applyFilters = () => {
    const branch = document.getElementById("inst-branch-filter").value;
    const status = document.getElementById("inst-status-filter").value;
    draw(installs.filter(i => (!branch || String(i.branch_id) === branch) && (!status || i.status === status)));
  };
  ["inst-branch-filter", "inst-status-filter"].forEach(id => document.getElementById(id).addEventListener("change", applyFilters));

  const addBtn = document.getElementById("add-install");
  if (addBtn) addBtn.addEventListener("click", () => openInstallForm(branches, technicians));
};

function openInstallForm(branches, technicians) {
  openModal({
    title: "New Network Installation Project",
    bodyHtml: `<form id="install-form" class="form-grid">
      ${field({ label: "Branch", name: "branch_id", type: "select", required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Installation Type", name: "installation_type", type: "select", options: ["New Branch Setup", "Network Upgrade", "ATM Network Expansion", "WiFi Rollout"] })}
      ${field({ label: "Technician", name: "technician_id", type: "select", options: technicians.map(t => ({ value: t.id, label: t.full_name })) })}
      ${field({ label: "Start Date", name: "start_date", type: "date" })}
      ${field({ label: "Expected Completion", name: "expected_completion", type: "date" })}
      ${field({ label: "Notes", name: "notes", type: "textarea", full: true })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Project</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("install-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const inst = await Api.createInstallation(formToObject(e.target));
          toast("Installation project created.", "success");
          closeModal();
          navigate(`installation-detail/${inst.id}`);
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

const CHECKLIST_LABELS = {
  router_installed: "Router installed",
  switch_installed: "Switch installed",
  cables_installed: "Network cables installed",
  ip_configuration_completed: "IP configuration completed",
  gateway_configured: "Gateway configured",
  dns_configured: "DNS configured",
  connectivity_tested: "Network connectivity tested",
  branch_computers_connected: "Branch computers connected",
  atm_network_checked: "ATM network connection checked",
  security_configuration_checked: "Network security configuration checked",
  documentation_completed: "Documentation completed",
};

Views["installation-detail"] = async (root, id) => {
  root.innerHTML = `<div class="empty-state">Loading project…</div>`;
  const inst = await Api.getInstallation(id);
  const canEdit = roleAllows("district_admin", "technician");

  root.innerHTML = `
    ${pageHeader(`Installation — ${inst.branch_name}`, inst.installation_type, `<button class="btn btn-ghost" id="back-btn">← Back</button>`)}
    <div class="panel" style="margin-bottom:20px;">
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${badge(inst.status)}</div></div>
        <div class="detail-item"><div class="detail-label">Technician</div><div class="detail-value">${escapeHtml(inst.technician_name || "Unassigned")}</div></div>
        <div class="detail-item"><div class="detail-label">Start Date</div><div class="detail-value">${fmtDate(inst.start_date)}</div></div>
        <div class="detail-item"><div class="detail-label">Expected Completion</div><div class="detail-value">${fmtDate(inst.expected_completion)}</div></div>
        <div class="detail-item"><div class="detail-label">Actual Completion</div><div class="detail-value">${fmtDate(inst.actual_completion)}</div></div>
      </div>
      ${canEdit ? `<form id="status-form" class="form-grid" style="margin-top:14px;">
        ${field({ label: "Update Status", name: "status", type: "select", value: inst.status, options: ["PLANNED","IN_PROGRESS","TESTING","COMPLETED","FAILED","CANCELLED"] })}
        ${field({ label: "Problems (if any)", name: "problems", value: inst.problems })}
        <div style="grid-column:1/-1"><button type="submit" class="btn btn-primary btn-sm">Update Project</button></div>
      </form>` : ""}
    </div>

    <div class="chart-grid" style="grid-template-columns:1fr 1fr;">
      <div class="panel">
        <div class="panel-title">Installation Checklist</div>
        <div id="checklist-container"></div>
      </div>
      <div class="panel">
        <div class="panel-title">Network Equipment</div>
        <div id="equipment-table"></div>
        ${canEdit ? `<button class="btn btn-sm btn-ghost" id="add-equip-btn" style="margin-top:12px;">+ Add Equipment</button>` : ""}
      </div>
    </div>
  `;

  document.getElementById("back-btn").onclick = () => navigate("network-installations");
  const statusForm = document.getElementById("status-form");
  if (statusForm) statusForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await Api.updateInstallation(inst.id, formToObject(e.target)); toast("Project updated.", "success"); navigate(`installation-detail/${id}`); }
    catch (err) { toast(err.message, "error"); }
  });

  const checklistEl = document.getElementById("checklist-container");
  checklistEl.innerHTML = Object.entries(inst.checklist).map(([key, val]) => `
    <label class="checklist-item">
      <input type="checkbox" data-key="${key}" ${val ? "checked" : ""} ${canEdit ? "" : "disabled"} />
      <span>${CHECKLIST_LABELS[key] || key}</span>
    </label>
  `).join("");
  if (canEdit) {
    checklistEl.querySelectorAll("input[type=checkbox]").forEach(cb => cb.addEventListener("change", async () => {
      try { await Api.updateChecklist(inst.id, { [cb.dataset.key]: cb.checked }); toast("Checklist updated.", "success"); }
      catch (err) { toast(err.message, "error"); cb.checked = !cb.checked; }
    }));
  }

  document.getElementById("equipment-table").innerHTML = renderTable({
    columns: [
      { key: "equipment_type", label: "Type" },
      { key: "model", label: "Model" },
      { key: "quantity", label: "Qty" },
      { key: "status", label: "Status", render: r => badge(r.status) },
    ], rows: inst.equipment, emptyText: "No equipment logged yet.",
  });

  const addEquipBtn = document.getElementById("add-equip-btn");
  if (addEquipBtn) addEquipBtn.addEventListener("click", () => openEquipmentForm(inst.id));
};

function openEquipmentForm(installId) {
  openModal({
    title: "Add Network Equipment",
    bodyHtml: `<form id="equip-form" class="form-grid">
      ${field({ label: "Equipment Type", name: "equipment_type", type: "select", options: ["Router","Switch","Access Point","Firewall","Network Cable","Patch Panel","Rack","UPS"], required: true })}
      ${field({ label: "Model", name: "model" })}
      ${field({ label: "Serial Number", name: "serial_number" })}
      ${field({ label: "Quantity", name: "quantity", type: "number", value: 1 })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Add Equipment</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("equip-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await Api.addEquipment(installId, formToObject(e.target)); toast("Equipment added.", "success"); closeModal(); navigate(`installation-detail/${installId}`); }
        catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

/* ============================= COMPUTERS ============================= */
Views.computers = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading computer inventory…</div>`;
  const [computers, branches] = await Promise.all([Api.listComputers(), Api.listBranches()]);

  root.innerHTML = `
    ${pageHeader("Computer Management", "Branch computer inventory and health status.", roleAllows("district_admin", "technician") ? `<button class="btn btn-primary" id="add-computer">+ Register Computer</button>` : "")}
    <div class="table-toolbar">
      <input type="text" id="comp-search" placeholder="Search asset # or hostname…" />
      <select id="comp-branch-filter"><option value="">All Branches</option>${branches.map(b => `<option value="${b.id}">${escapeHtml(b.name)}</option>`).join("")}</select>
      <select id="comp-status-filter"><option value="">All Statuses</option>${["WORKING","WARNING","ERROR","OFFLINE","UNDER_MAINTENANCE"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
    </div>
    <div id="comp-table"></div>
  `;
  const cols = [
    { key: "asset_number", label: "Asset #", render: r => `<span class="mono">${r.asset_number}</span>` },
    { key: "hostname", label: "Hostname" },
    { key: "branch_name", label: "Branch" },
    { key: "employee_name", label: "User" },
    { key: "operating_system", label: "OS" },
    { key: "antivirus_status", label: "Antivirus", render: r => badge(r.antivirus_status) },
    { key: "status", label: "Status", render: r => badge(r.status) },
  ];
  const draw = (list) => {
    const c = document.getElementById("comp-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No computers found." });
    attachRowClicks(c, list, (row) => openComputerDetail(row, branches));
  };
  draw(computers);
  const applyFilters = () => {
    const s = document.getElementById("comp-search").value.toLowerCase();
    const branch = document.getElementById("comp-branch-filter").value;
    const status = document.getElementById("comp-status-filter").value;
    draw(computers.filter(c =>
      (!s || c.asset_number.toLowerCase().includes(s) || (c.hostname||"").toLowerCase().includes(s)) &&
      (!branch || String(c.branch_id) === branch) && (!status || c.status === status)
    ));
  };
  ["comp-search","comp-branch-filter","comp-status-filter"].forEach(id => document.getElementById(id).addEventListener("input", applyFilters));

  const addBtn = document.getElementById("add-computer");
  if (addBtn) addBtn.addEventListener("click", () => openComputerForm(branches));
};

function openComputerForm(branches, existing) {
  openModal({
    title: existing ? "Edit Computer" : "Register Computer",
    bodyHtml: `<form id="comp-form" class="form-grid">
      ${field({ label: "Asset Number", name: "asset_number", value: existing?.asset_number, required: true })}
      ${field({ label: "Hostname", name: "hostname", value: existing?.hostname })}
      ${field({ label: "Branch", name: "branch_id", type: "select", value: existing?.branch_id, required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Department", name: "department", value: existing?.department })}
      ${field({ label: "Operating System", name: "operating_system", value: existing?.operating_system })}
      ${field({ label: "RAM", name: "ram", value: existing?.ram })}
      ${field({ label: "Storage", name: "storage", value: existing?.storage })}
      ${field({ label: "Processor", name: "processor", value: existing?.processor })}
      ${field({ label: "IP Address", name: "ip_address", value: existing?.ip_address })}
      ${field({ label: "MAC Address", name: "mac_address", value: existing?.mac_address })}
      ${field({ label: "Antivirus Status", name: "antivirus_status", type: "select", value: existing?.antivirus_status || "PROTECTED", options: ["PROTECTED","OUTDATED","NOT_INSTALLED"] })}
      ${field({ label: "Status", name: "status", type: "select", value: existing?.status || "WORKING", options: ["WORKING","WARNING","ERROR","OFFLINE","UNDER_MAINTENANCE"] })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">${existing ? "Save Changes" : "Register Computer"}</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("comp-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = formToObject(e.target);
        try {
          if (existing) await Api.updateComputer(existing.id, data); else await Api.createComputer(data);
          toast(existing ? "Computer updated." : "Computer registered.", "success");
          closeModal(); navigate("computers");
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

function openComputerDetail(c, branches) {
  openModal({
    title: c.asset_number,
    bodyHtml: `
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Hostname</div><div class="detail-value">${escapeHtml(c.hostname||"—")}</div></div>
        <div class="detail-item"><div class="detail-label">Branch</div><div class="detail-value">${escapeHtml(c.branch_name)}</div></div>
        <div class="detail-item"><div class="detail-label">OS</div><div class="detail-value">${escapeHtml(c.operating_system||"—")}</div></div>
        <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${badge(c.status)}</div></div>
        <div class="detail-item"><div class="detail-label">IP</div><div class="detail-value mono">${escapeHtml(c.ip_address||"—")}</div></div>
        <div class="detail-item"><div class="detail-label">MAC</div><div class="detail-value mono">${escapeHtml(c.mac_address||"—")}</div></div>
      </div>
      ${roleAllows("district_admin", "technician") ? `<button class="btn btn-primary btn-sm" id="edit-comp-btn">Edit Computer</button>` : ""}
    `,
    onMount: () => {
      const btn = document.getElementById("edit-comp-btn");
      if (btn) btn.onclick = () => { closeModal(); openComputerForm(branches, c); };
    },
  });
}

/* ============================= IT TICKETS ============================= */
Views.tickets = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading tickets…</div>`;
  const [tickets, branches, technicians, categories] = await Promise.all([
    Api.listTickets(), Api.listBranches(), Api.listTechnicians(), Api.ticketCategories(),
  ]);

  root.innerHTML = `
    ${pageHeader("IT Support Tickets", "Employee-reported computer & IT problems.", `<button class="btn btn-primary" id="add-ticket">+ Report Problem</button>`)}
    <div class="table-toolbar">
      <input type="text" id="tk-search" placeholder="Search ticket code or description…" />
      <select id="tk-status-filter"><option value="">All Statuses</option>${["OPEN","ASSIGNED","IN_PROGRESS","WAITING_FOR_USER","RESOLVED","CLOSED"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
      <select id="tk-priority-filter"><option value="">All Priorities</option>${["LOW","MEDIUM","HIGH","CRITICAL"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
    </div>
    <div id="tk-table"></div>
  `;
  const cols = [
    { key: "ticket_code", label: "Ticket", render: r => `<span class="mono">${r.ticket_code}</span>` },
    { key: "branch_name", label: "Branch" },
    { key: "problem_category", label: "Category" },
    { key: "priority", label: "Priority", render: r => badge(r.priority) },
    { key: "assigned_technician_name", label: "Technician", render: r => r.assigned_technician_name || "Unassigned" },
    { key: "status", label: "Status", render: r => badge(r.status) },
    { key: "created_at", label: "Created", render: r => fmtDate(r.created_at) },
  ];
  const draw = (list) => {
    const c = document.getElementById("tk-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No tickets found." });
    attachRowClicks(c, list, (row) => openTicketDetail(row.id, technicians));
  };
  draw(tickets);
  const applyFilters = () => {
    const s = document.getElementById("tk-search").value.toLowerCase();
    const status = document.getElementById("tk-status-filter").value;
    const priority = document.getElementById("tk-priority-filter").value;
    draw(tickets.filter(t =>
      (!s || t.ticket_code.toLowerCase().includes(s) || (t.description||"").toLowerCase().includes(s)) &&
      (!status || t.status === status) && (!priority || t.priority === priority)
    ));
  };
  ["tk-search","tk-status-filter","tk-priority-filter"].forEach(id => document.getElementById(id).addEventListener("input", applyFilters));

  document.getElementById("add-ticket").addEventListener("click", () => openTicketForm(branches, categories));
};

function openTicketForm(branches, categories) {
  openModal({
    title: "Report a Computer / IT Problem",
    bodyHtml: `<form id="ticket-form" class="form-grid">
      ${field({ label: "Branch", name: "branch_id", type: "select", required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Problem Category", name: "problem_category", type: "select", required: true, options: categories })}
      ${field({ label: "Priority", name: "priority", type: "select", value: "MEDIUM", options: ["LOW","MEDIUM","HIGH","CRITICAL"] })}
      ${field({ label: "Description", name: "description", type: "textarea", full: true, placeholder: "Describe the problem in detail…" })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Submit Ticket</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("ticket-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const t = await Api.createTicket(formToObject(e.target));
          toast(`Ticket ${t.ticket_code} submitted.`, "success");
          closeModal(); navigate("tickets");
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

async function openTicketDetail(ticketId, technicians) {
  const t = await Api.getTicket(ticketId);
  if (!technicians) technicians = await Api.listTechnicians();
  const canManage = roleAllows("district_admin", "technician");

  openModal({
    title: t.ticket_code,
    width: "620px",
    bodyHtml: `
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Branch</div><div class="detail-value">${escapeHtml(t.branch_name)}</div></div>
        <div class="detail-item"><div class="detail-label">Category</div><div class="detail-value">${escapeHtml(t.problem_category)}</div></div>
        <div class="detail-item"><div class="detail-label">Priority</div><div class="detail-value">${badge(t.priority)}</div></div>
        <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${badge(t.status)}</div></div>
        <div class="detail-item"><div class="detail-label">Created</div><div class="detail-value">${fmtDateTime(t.created_at)}</div></div>
        <div class="detail-item"><div class="detail-label">Technician</div><div class="detail-value">${escapeHtml(t.assigned_technician_name || "Unassigned")}</div></div>
      </div>
      <p style="color:var(--text-muted);font-size:13px;">${escapeHtml(t.description || "No description provided.")}</p>

      ${canManage ? `<form id="ticket-update-form" class="form-grid">
        ${field({ label: "Assign Technician", name: "assigned_technician_id", type: "select", value: t.assigned_technician_id, options: technicians.map(tc => ({ value: tc.id, label: tc.full_name })) })}
        ${field({ label: "Status", name: "status", type: "select", value: t.status, options: ["OPEN","ASSIGNED","IN_PROGRESS","WAITING_FOR_USER","RESOLVED","CLOSED"] })}
        ${field({ label: "Resolution", name: "resolution", type: "textarea", value: t.resolution, full: true })}
        <div style="grid-column:1/-1"><button type="submit" class="btn btn-primary btn-sm">Update Ticket</button></div>
      </form>` : ""}

      <div class="section-divider"></div>
      <div class="panel-title" style="font-size:12.5px;">Comments</div>
      <div id="ticket-comments" style="margin-bottom:12px;">
        ${(t.comments || []).map(c => `<div class="notif-item"><div class="notif-title">${escapeHtml(c.author_name)} <span style="color:var(--text-faint);font-weight:400;">(${escapeHtml(c.author_role)})</span></div><div class="notif-msg">${escapeHtml(c.message)}</div><div class="notif-time">${fmtDateTime(c.created_at)}</div></div>`).join("") || `<div class="table-empty">No comments yet.</div>`}
      </div>
      <form id="comment-form" style="display:flex;gap:8px;">
        <input type="text" name="message" placeholder="Add a comment…" style="flex:1;background:var(--bg-elevated);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);" required />
        <button type="submit" class="btn btn-sm btn-primary">Send</button>
      </form>
    `,
    onMount: () => {
      const uForm = document.getElementById("ticket-update-form");
      if (uForm) uForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await Api.updateTicket(t.id, formToObject(e.target)); toast("Ticket updated.", "success"); closeModal(); navigate("tickets"); }
        catch (err) { toast(err.message, "error"); }
      });
      document.getElementById("comment-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const msg = e.target.message.value;
        try { await Api.addTicketComment(t.id, msg); closeModal(); openTicketDetail(ticketId, technicians); }
        catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

/* ============================= INCIDENTS ============================= */
Views.incidents = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading incidents…</div>`;
  const [incidents, branches, technicians, types] = await Promise.all([
    Api.listIncidents(), Api.listBranches(), Api.listTechnicians(), Api.incidentTypes(),
  ]);

  root.innerHTML = `
    ${pageHeader("Incident Management", "District-wide IT incidents across ATM, network, computer, and infrastructure systems.", roleAllows("district_admin", "technician") ? `<button class="btn btn-primary" id="add-incident">+ Log Incident</button>` : "")}
    <div class="table-toolbar">
      <select id="inc-status-filter"><option value="">All Statuses</option>${["OPEN","IN_PROGRESS","RESOLVED"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
      <select id="inc-category-filter"><option value="">All Categories</option>${types.map(t=>`<option value="${t}">${t}</option>`).join("")}</select>
    </div>
    <div id="inc-table"></div>
  `;
  const cols = [
    { key: "incident_code", label: "Code", render: r => `<span class="mono">${r.incident_code}</span>` },
    { key: "branch_name", label: "Branch" },
    { key: "category", label: "Category" },
    { key: "severity", label: "Severity", render: r => badge(r.severity) },
    { key: "status", label: "Status", render: r => badge(r.status) },
    { key: "date_opened", label: "Opened", render: r => fmtDate(r.date_opened) },
  ];
  const draw = (list) => {
    const c = document.getElementById("inc-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No incidents found." });
    attachRowClicks(c, list, (row) => openIncidentDetail(row, technicians));
  };
  draw(incidents);
  const applyFilters = () => {
    const status = document.getElementById("inc-status-filter").value;
    const category = document.getElementById("inc-category-filter").value;
    draw(incidents.filter(i => (!status || i.status === status) && (!category || i.category === category)));
  };
  ["inc-status-filter","inc-category-filter"].forEach(id => document.getElementById(id).addEventListener("change", applyFilters));

  const addBtn = document.getElementById("add-incident");
  if (addBtn) addBtn.addEventListener("click", () => openIncidentForm(branches, technicians, types));
};

function openIncidentForm(branches, technicians, types) {
  openModal({
    title: "Log New Incident",
    bodyHtml: `<form id="inc-form" class="form-grid">
      ${field({ label: "Branch", name: "branch_id", type: "select", required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Category", name: "category", type: "select", required: true, options: types })}
      ${field({ label: "Severity", name: "severity", type: "select", value: "MEDIUM", options: ["LOW","MEDIUM","HIGH","CRITICAL"] })}
      ${field({ label: "Technician", name: "technician_id", type: "select", options: technicians.map(t => ({ value: t.id, label: t.full_name })) })}
      ${field({ label: "Description", name: "description", type: "textarea", full: true })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Log Incident</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("inc-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await Api.createIncident(formToObject(e.target)); toast("Incident logged.", "success"); closeModal(); navigate("incidents"); }
        catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

function openIncidentDetail(inc, technicians) {
  const canManage = roleAllows("district_admin", "technician");
  openModal({
    title: inc.incident_code,
    bodyHtml: `
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Branch</div><div class="detail-value">${escapeHtml(inc.branch_name)}</div></div>
        <div class="detail-item"><div class="detail-label">Category</div><div class="detail-value">${escapeHtml(inc.category)}</div></div>
        <div class="detail-item"><div class="detail-label">Severity</div><div class="detail-value">${badge(inc.severity)}</div></div>
        <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${badge(inc.status)}</div></div>
      </div>
      <p style="color:var(--text-muted);font-size:13px;">${escapeHtml(inc.description || "No description.")}</p>
      ${canManage ? `<form id="inc-update-form" class="form-grid">
        ${field({ label: "Status", name: "status", type: "select", value: inc.status, options: ["OPEN","IN_PROGRESS","RESOLVED"] })}
        ${field({ label: "Resolution", name: "resolution", type: "textarea", value: inc.resolution, full: true })}
        <div style="grid-column:1/-1"><button type="submit" class="btn btn-primary btn-sm">Update Incident</button></div>
      </form>` : ""}
    `,
    onMount: () => {
      const form = document.getElementById("inc-update-form");
      if (form) form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await Api.updateIncident(inc.id, formToObject(e.target)); toast("Incident updated.", "success"); closeModal(); navigate("incidents"); }
        catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

/* ============================= EQUIPMENT / ASSETS ============================= */
Views.equipment = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading equipment inventory…</div>`;
  const [assets, branches, types] = await Promise.all([Api.listAssets(), Api.listBranches(), Api.assetTypes()]);

  root.innerHTML = `
    ${pageHeader("Equipment Inventory", "IT asset management across all branches.", roleAllows("district_admin", "technician") ? `<button class="btn btn-primary" id="add-asset">+ Register Asset</button>` : "")}
    <div class="table-toolbar">
      <input type="text" id="ast-search" placeholder="Search asset code or serial…" />
      <select id="ast-type-filter"><option value="">All Types</option>${types.map(t=>`<option value="${t}">${t}</option>`).join("")}</select>
      <select id="ast-status-filter"><option value="">All Statuses</option>${["ACTIVE","RETIRED","UNDER_REPAIR","LOST"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
    </div>
    <div id="ast-table"></div>
  `;
  const cols = [
    { key: "asset_code", label: "Asset Code", render: r => `<span class="mono">${r.asset_code}</span>` },
    { key: "asset_type", label: "Type" },
    { key: "model", label: "Model" },
    { key: "branch_name", label: "Branch" },
    { key: "assigned_user", label: "Assigned To" },
    { key: "status", label: "Status", render: r => badge(r.status) },
  ];
  const draw = (list) => {
    const c = document.getElementById("ast-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No assets found." });
    attachRowClicks(c, list, (row) => openAssetForm(branches, types, row));
  };
  draw(assets);
  const applyFilters = () => {
    const s = document.getElementById("ast-search").value.toLowerCase();
    const type = document.getElementById("ast-type-filter").value;
    const status = document.getElementById("ast-status-filter").value;
    draw(assets.filter(a =>
      (!s || a.asset_code.toLowerCase().includes(s) || (a.serial_number||"").toLowerCase().includes(s)) &&
      (!type || a.asset_type === type) && (!status || a.status === status)
    ));
  };
  ["ast-search","ast-type-filter","ast-status-filter"].forEach(id => document.getElementById(id).addEventListener("input", applyFilters));

  const addBtn = document.getElementById("add-asset");
  if (addBtn) addBtn.addEventListener("click", () => openAssetForm(branches, types));
};

function openAssetForm(branches, types, existing) {
  openModal({
    title: existing ? "Edit Asset" : "Register Asset",
    bodyHtml: `<form id="asset-form" class="form-grid">
      ${field({ label: "Asset Code", name: "asset_code", value: existing?.asset_code, required: true })}
      ${field({ label: "Serial Number", name: "serial_number", value: existing?.serial_number })}
      ${field({ label: "Type", name: "asset_type", type: "select", value: existing?.asset_type, required: true, options: types })}
      ${field({ label: "Model", name: "model", value: existing?.model })}
      ${field({ label: "Branch", name: "branch_id", type: "select", value: existing?.branch_id, required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Assigned User/Location", name: "assigned_user", value: existing?.assigned_user })}
      ${field({ label: "Purchase Date", name: "purchase_date", type: "date", value: existing?.purchase_date })}
      ${field({ label: "Status", name: "status", type: "select", value: existing?.status || "ACTIVE", options: ["ACTIVE","RETIRED","UNDER_REPAIR","LOST"] })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">${existing ? "Save Changes" : "Register Asset"}</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("asset-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = formToObject(e.target);
        try {
          if (existing) await Api.updateAsset(existing.id, data); else await Api.createAsset(data);
          toast(existing ? "Asset updated." : "Asset registered.", "success");
          closeModal(); navigate("equipment");
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

/* ============================= MAINTENANCE ============================= */
Views.maintenance = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading maintenance records…</div>`;
  const [records, branches, technicians] = await Promise.all([Api.listMaintenance(), Api.listBranches(), Api.listTechnicians()]);

  root.innerHTML = `
    ${pageHeader("Maintenance Management", "Preventive and corrective maintenance activity log.", roleAllows("district_admin", "technician") ? `<button class="btn btn-primary" id="add-maint">+ Add Record</button>` : "")}
    <div class="table-toolbar">
      <select id="mt-type-filter"><option value="">All Types</option><option value="PREVENTIVE">Preventive</option><option value="CORRECTIVE">Corrective</option></select>
      <select id="mt-result-filter"><option value="">All Results</option>${["PENDING","PASSED","FAILED","COMPLETED"].map(s=>`<option value="${s}">${s}</option>`).join("")}</select>
    </div>
    <div id="mt-table"></div>
  `;
  const cols = [
    { key: "maintenance_type", label: "Type", render: r => badge(r.maintenance_type) },
    { key: "branch_name", label: "Branch" },
    { key: "technician_name", label: "Technician" },
    { key: "scheduled_date", label: "Scheduled", render: r => fmtDate(r.scheduled_date) },
    { key: "completion_date", label: "Completed", render: r => fmtDate(r.completion_date) },
    { key: "result", label: "Result", render: r => badge(r.result) },
  ];
  const draw = (list) => {
    const c = document.getElementById("mt-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No maintenance records found." });
  };
  draw(records);
  const applyFilters = () => {
    const type = document.getElementById("mt-type-filter").value;
    const result = document.getElementById("mt-result-filter").value;
    draw(records.filter(r => (!type || r.maintenance_type === type) && (!result || r.result === result)));
  };
  ["mt-type-filter","mt-result-filter"].forEach(id => document.getElementById(id).addEventListener("change", applyFilters));

  const addBtn = document.getElementById("add-maint");
  if (addBtn) addBtn.addEventListener("click", () => openMaintenanceForm(branches, technicians));
};

function openMaintenanceForm(branches, technicians) {
  openModal({
    title: "Add Maintenance Record",
    bodyHtml: `<form id="maint-form" class="form-grid">
      ${field({ label: "Type", name: "maintenance_type", type: "select", value: "PREVENTIVE", options: ["PREVENTIVE","CORRECTIVE"] })}
      ${field({ label: "Branch", name: "branch_id", type: "select", required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Technician", name: "technician_id", type: "select", options: technicians.map(t => ({ value: t.id, label: t.full_name })) })}
      ${field({ label: "Scheduled Date", name: "scheduled_date", type: "date" })}
      ${field({ label: "Completion Date", name: "completion_date", type: "date" })}
      ${field({ label: "Problem (corrective)", name: "problem", full: true })}
      ${field({ label: "Repair Action (corrective)", name: "repair_action", full: true })}
      ${field({ label: "Result", name: "result", type: "select", value: "PENDING", options: ["PENDING","PASSED","FAILED","COMPLETED"] })}
      ${field({ label: "Notes", name: "notes", type: "textarea", full: true })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Record</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("maint-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await Api.createMaintenance(formToObject(e.target)); toast("Maintenance record saved.", "success"); closeModal(); navigate("maintenance"); }
        catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

/* ============================= REMOTE SUPPORT ============================= */
Views["remote-support"] = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading remote support sessions…</div>`;
  const [sessions, branches, technicians] = await Promise.all([Api.listRemoteSupport(), Api.listBranches(), Api.listTechnicians()]);

  root.innerHTML = `
    ${pageHeader("Remote IT Support", "Scheduled and completed remote support sessions. All actual remote control is performed via an authorized enterprise remote-support tool; this module only records session activity.", roleAllows("district_admin", "technician") ? `<button class="btn btn-primary" id="add-session">+ Schedule Session</button>` : "")}
    <div id="rs-table"></div>
  `;
  const cols = [
    { key: "branch_name", label: "Branch" },
    { key: "technician_name", label: "Technician" },
    { key: "ticket_code", label: "Related Ticket", render: r => r.ticket_code || "—" },
    { key: "status", label: "Status", render: r => badge(r.status) },
    { key: "scheduled_time", label: "Scheduled", render: r => fmtDateTime(r.scheduled_time) },
    { key: "remote_tool_used", label: "Tool Used" },
  ];
  const draw = (list) => {
    const c = document.getElementById("rs-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No remote support sessions found." });
    attachRowClicks(c, list, (row) => openRemoteSessionDetail(row));
  };
  draw(sessions);

  const addBtn = document.getElementById("add-session");
  if (addBtn) addBtn.addEventListener("click", () => openRemoteSessionForm(branches, technicians));
};

function openRemoteSessionForm(branches, technicians) {
  openModal({
    title: "Schedule Remote Support Session",
    bodyHtml: `<form id="rs-form" class="form-grid">
      ${field({ label: "Branch", name: "branch_id", type: "select", required: true, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${field({ label: "Technician", name: "technician_id", type: "select", required: true, options: technicians.map(t => ({ value: t.id, label: t.full_name })) })}
      ${field({ label: "Scheduled Time", name: "scheduled_time", type: "datetime-local" })}
      ${field({ label: "Remote Tool Used", name: "remote_tool_used", value: "Authorized Enterprise Remote Support Tool", full: true })}
      <div class="modal-footer full" style="grid-column:1/-1">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Schedule Session</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("rs-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await Api.createRemoteSupport(formToObject(e.target)); toast("Session scheduled.", "success"); closeModal(); navigate("remote-support"); }
        catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

function openRemoteSessionDetail(s) {
  const canManage = roleAllows("district_admin", "technician");
  openModal({
    title: `Remote Session — ${s.branch_name}`,
    bodyHtml: `
      <div class="detail-grid">
        <div class="detail-item"><div class="detail-label">Technician</div><div class="detail-value">${escapeHtml(s.technician_name)}</div></div>
        <div class="detail-item"><div class="detail-label">Status</div><div class="detail-value">${badge(s.status)}</div></div>
        <div class="detail-item"><div class="detail-label">Scheduled</div><div class="detail-value">${fmtDateTime(s.scheduled_time)}</div></div>
        <div class="detail-item"><div class="detail-label">Remote Tool</div><div class="detail-value">${escapeHtml(s.remote_tool_used || "—")}</div></div>
      </div>
      ${canManage ? `<form id="rs-update-form" class="form-grid">
        ${field({ label: "Status", name: "status", type: "select", value: s.status, options: ["SCHEDULED","IN_PROGRESS","COMPLETED","CANCELLED"] })}
        ${field({ label: "Troubleshooting Steps", name: "troubleshooting_steps", type: "textarea", value: s.troubleshooting_steps, full: true })}
        ${field({ label: "Resolution", name: "resolution", type: "textarea", value: s.resolution, full: true })}
        <div style="grid-column:1/-1"><button type="submit" class="btn btn-primary btn-sm">Update Session</button></div>
      </form>` : ""}
    `,
    onMount: () => {
      const form = document.getElementById("rs-update-form");
      if (form) form.addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await Api.updateRemoteSupport(s.id, formToObject(e.target)); toast("Session updated.", "success"); closeModal(); navigate("remote-support"); }
        catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

/* ============================= KNOWLEDGE BASE ============================= */
Views["knowledge-base"] = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading knowledge base…</div>`;
  const kb = await Api.knowledgeBase();
  root.innerHTML = `
    ${pageHeader("Troubleshooting Knowledge Base", "Standard diagnostic guides for common IT problems.")}
    ${kb.map(item => `
      <div class="kb-card">
        <div class="kb-title">${escapeHtml(item.title)}</div>
        <div class="kb-cols">
          <div><h5>Possible Causes</h5><ul>${item.causes.map(c => `<li>${escapeHtml(c)}</li>`).join("")}</ul></div>
          <div><h5>Recommended Actions</h5><ul>${item.actions.map(a => `<li>${escapeHtml(a)}</li>`).join("")}</ul></div>
        </div>
      </div>
    `).join("")}
  `;
};

/* ============================= REPORTS ============================= */
const REPORT_DEFS = [
  { key: "atm", label: "ATM Report" },
  { key: "network", label: "Network Report" },
  { key: "computer", label: "Computer Report" },
  { key: "ticket", label: "Ticket Report" },
  { key: "technician", label: "Technician Report" },
];

Views.reports = async (root) => {
  root.innerHTML = `
    ${pageHeader("IT Reports", "Generate and export operational reports for district management.")}
    <div class="chart-grid" id="reports-grid"></div>
  `;
  const grid = document.getElementById("reports-grid");
  grid.innerHTML = REPORT_DEFS.map(r => `
    <div class="panel">
      <div class="panel-title">${r.label}</div>
      <div id="report-${r.key}"><div class="table-empty">Loading…</div></div>
      <div style="display:flex;gap:8px;margin-top:12px;">
        <a class="btn btn-sm btn-ghost" href="${Api.exportReportUrl(r.key, 'csv')}" target="_blank">Export CSV</a>
        <a class="btn btn-sm btn-ghost" href="${Api.exportReportUrl(r.key, 'excel')}" target="_blank">Export Excel</a>
        <a class="btn btn-sm btn-ghost" href="${Api.exportReportUrl(r.key, 'pdf')}" target="_blank">Export PDF</a>
      </div>
    </div>
  `).join("");

  for (const r of REPORT_DEFS) {
    try {
      const res = await Api.getReport(r.key);
      const rows = Array.isArray(res.data) ? res.data : Object.entries(res.data).map(([k, v]) => ({ Metric: k, Value: v }));
      const headers = Object.keys(rows[0] || { Metric: "", Value: "" });
      document.getElementById(`report-${r.key}`).innerHTML = renderTable({
        columns: headers.map(h => ({ key: h, label: h, render: row => escapeHtml(String(row[h] ?? "—")) })),
        rows,
      });
    } catch (err) {
      document.getElementById(`report-${r.key}`).innerHTML = `<div class="table-empty">Failed to load report.</div>`;
    }
  }

  // Note: export links require the auth token; append it as a query fallback isn't supported server-side,
  // so open in same-tab fetch-download flow instead of plain <a> when needed.
  grid.querySelectorAll("a.btn").forEach(a => {
    a.addEventListener("click", async (e) => {
      e.preventDefault();
      try {
        const res = await apiRequest("GET", a.getAttribute("href").replace(API_BASE, ""), null, { raw: true });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        const cd = res.headers.get("content-disposition") || "";
        const match = cd.match(/filename="?([^"]+)"?/);
        link.download = match ? match[1] : "report";
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
      } catch (err) { toast("Failed to export report.", "error"); }
    });
  });
};

/* ============================= NOTIFICATIONS ============================= */
Views.notifications = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading notifications…</div>`;
  const notifications = await Api.listNotifications();
  root.innerHTML = `
    ${pageHeader("Notifications", "Alerts for critical ATM errors, ticket activity, and installation events.", `<button class="btn btn-ghost" id="mark-all-read">Mark all as read</button>`)}
    <div class="panel">
      ${notifications.length ? notifications.map(n => `
        <div class="notif-item" style="${n.is_read ? "opacity:.55;" : ""}">
          <div class="notif-title">${badge(n.severity)} ${escapeHtml(n.title)}</div>
          <div class="notif-msg">${escapeHtml(n.message)}</div>
          <div class="notif-time">${fmtDateTime(n.created_at)}</div>
        </div>
      `).join("") : `<div class="table-empty">No notifications yet.</div>`}
    </div>
  `;
  document.getElementById("mark-all-read").addEventListener("click", async () => {
    await Api.markAllRead(); toast("All notifications marked as read.", "success"); Views.notifications(root); refreshNotifBadge();
  });
};

/* ============================= USERS ============================= */
Views.users = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading users…</div>`;
  const [users, branches] = await Promise.all([Api.listUsers(), Api.listBranches()]);
  root.innerHTML = `
    ${pageHeader("User Management", "District IT staff, technicians, branch managers, and employee accounts.", `<button class="btn btn-primary" id="add-user">+ Add User</button>`)}
    <div id="user-table"></div>
  `;
  const cols = [
    { key: "profile_photo", label: "Photo", render: r => r.profile_photo ? `<img src="${r.profile_photo}" alt="" style="width:32px;height:32px;border-radius:50%;object-fit:cover">` : `<span class="avatar">${escapeHtml(r.full_name.slice(0, 1))}</span>` },
    { key: "full_name", label: "Name" },
    { key: "username", label: "Username", render: r => `<span class="mono">${r.username}</span>` },
    { key: "email", label: "Email" },
    { key: "role", label: "Role", render: r => badge(r.role.toUpperCase()) },
    { key: "branch_name", label: "Branch", render: r => r.branch_name || "—" },
    { key: "is_active", label: "Active", render: r => r.is_active ? badge("ACTIVE") : badge("RETIRED") },
  ];
  const draw = (list) => {
    const c = document.getElementById("user-table");
    c.innerHTML = renderTable({ columns: cols, rows: list, emptyText: "No users found." });
    attachRowClicks(c, list, (row) => openUserForm(branches, row));
  };
  draw(users);
  document.getElementById("add-user").addEventListener("click", () => openUserForm(branches));
};

function openUserForm(branches, existing) {
  openModal({
    title: existing ? "Edit User" : "Add User",
    bodyHtml: `<form id="user-form" class="form-grid">
      ${field({ label: "Full Name", name: "full_name", value: existing?.full_name, required: true })}
      ${field({ label: "Username", name: "username", value: existing?.username, required: !existing })}
      ${field({ label: "Email", name: "email", type: "email", value: existing?.email, required: true })}
      ${field({ label: existing ? "New Password (optional)" : "Password", name: "password", type: "password", required: !existing })}
      ${existing ? `<div class="field"><label>Profile Photo</label><input id="profile-photo" type="file" accept="image/png,image/jpeg,image/gif,image/webp"></div>` : ""}
      ${field({ label: "Role", name: "role", type: "select", value: existing?.role, required: true, options: [
        { value: "district_admin", label: "District IT Administrator" },
        { value: "technician", label: "District IT Technician" },
        { value: "branch_employee", label: "Branch Employee" },
        { value: "branch_manager", label: "Branch Manager" },
      ] })}
      ${field({ label: "Branch", name: "branch_id", type: "select", value: existing?.branch_id, options: branches.map(b => ({ value: b.id, label: b.name })) })}
      ${existing ? field({ label: "Active", name: "is_active", type: "select", value: existing?.is_active ? "true" : "", options: [{value:"true",label:"Active"},{value:"",label:"Disabled"}] }) : ""}
      <div class="modal-footer full" style="grid-column:1/-1">
        ${existing ? `<button type="button" class="btn btn-ghost" id="reset-password-btn">Reset Password</button>` : ""}
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">${existing ? "Save Changes" : "Create User"}</button>
      </div>
    </form>`,
    onMount: () => {
      document.getElementById("cancel-btn").onclick = closeModal;
      document.getElementById("reset-password-btn")?.addEventListener("click", async () => {
        const password = window.prompt("Enter a new password (at least 6 characters):");
        if (!password) return;
        try { await Api.resetUserPassword(existing.id, password); toast("Password reset successfully.", "success"); }
        catch (err) { toast(err.message, "error"); }
      });
      document.getElementById("user-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = formToObject(e.target);
        if (existing) data.is_active = data.is_active === "true";
        if (!data.password) delete data.password;
        try {
          const saved = existing ? await Api.updateUser(existing.id, data) : await Api.createUser(data);
          const photo = document.getElementById("profile-photo")?.files[0];
          if (photo) { const upload = new FormData(); upload.append("file", photo); await Api.uploadUserPhoto(saved.id, upload); }
          toast(existing ? "User updated." : "User created.", "success");
          closeModal(); navigate("users");
        } catch (err) { toast(err.message, "error"); }
      });
    },
  });
}

Views.settings = async (root) => {
  const settings = await Api.getSettings();
  root.innerHTML = `${pageHeader("CBE Settings", "District identity, support contacts, and operational defaults.")}
    <div class="panel" style="max-width:900px"><form id="settings-form" class="form-grid">
      ${field({ label: "Organization Name", name: "organization_name", value: settings.organization_name, required: true })}
      ${field({ label: "District Name", name: "district_name", value: settings.district_name, required: true })}
      ${field({ label: "District Code", name: "district_code", value: settings.district_code })}
      ${field({ label: "Region", name: "region", value: settings.region })}
      ${field({ label: "Office Address", name: "office_address", value: settings.office_address })}
      ${field({ label: "Support Email", name: "support_email", value: settings.support_email, type: "email" })}
      ${field({ label: "Support Phone", name: "support_phone", value: settings.support_phone })}
      ${field({ label: "Timezone", name: "timezone", value: settings.timezone })}
      ${field({ label: "Currency", name: "currency", value: settings.currency })}
      ${field({ label: "Default Ticket Priority", name: "default_ticket_priority", type: "select", value: settings.default_ticket_priority, options: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].map(v => ({ value: v, label: v })) })}
      ${field({ label: "Maintenance Interval (days)", name: "maintenance_interval_days", type: "number", value: settings.maintenance_interval_days, min: 1 })}
      ${field({ label: "Simulation Mode", name: "simulation_mode", type: "select", value: settings.simulation_mode ? "true" : "false", options: [{ value: "true", label: "Enabled" }, { value: "false", label: "Disabled" }] })}
      <div class="modal-footer full"><button class="btn btn-primary" type="submit">Save CBE Settings</button></div>
    </form></div>`;
  document.getElementById("settings-form").onsubmit = async (e) => {
    e.preventDefault();
    const data = formToObject(e.target);
    data.maintenance_interval_days = Number(data.maintenance_interval_days);
    data.simulation_mode = data.simulation_mode === "true";
    try { await Api.updateSettings(data); toast("CBE settings saved.", "success"); }
    catch (err) { toast(err.message, "error"); }
  };
};

/* ============================= AUDIT LOGS ============================= */
Views["audit-logs"] = async (root) => {
  root.innerHTML = `<div class="empty-state">Loading audit logs…</div>`;
  const res = await Api.listAuditLogs();
  root.innerHTML = `
    ${pageHeader("Audit Logs", "System activity trail for compliance and accountability.")}
    <div id="audit-table"></div>
  `;
  document.getElementById("audit-table").innerHTML = renderTable({
    columns: [
      { key: "created_at", label: "Time", render: r => fmtDateTime(r.created_at) },
      { key: "user_name", label: "User" },
      { key: "action", label: "Action" },
      { key: "description", label: "Description" },
      { key: "ip_address", label: "IP", render: r => `<span class="mono">${r.ip_address || "—"}</span>` },
    ], rows: res.items, emptyText: "No audit log entries.",
  });
};
