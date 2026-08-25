/* Reusable UI helpers */

function toast(message, type = "info") {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}
function fmtDateTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
function timeAgo(iso) {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

const STATUS_COLOR_MAP = {
  ONLINE: "green", WORKING: "green", ACTIVE: "green", COMPLETED: "green", RESOLVED: "green",
  CLOSED: "grey", CONNECTED: "green", GREEN: "green", PASSED: "green", INSTALLED: "green",
  OFFLINE: "red", ERROR: "red", RED: "red", FAILED: "red", DISCONNECTED: "red", CRITICAL: "red",
  WARNING: "yellow", YELLOW: "yellow", MAINTENANCE: "yellow", UNDER_MAINTENANCE: "yellow",
  UNDER_REPAIR: "yellow", DEGRADED: "yellow", HIGH: "yellow", PENDING: "yellow", OUTDATED: "yellow",
  PLANNED: "blue", IN_PROGRESS: "blue", TESTING: "blue", ASSIGNED: "blue", OPEN: "blue",
  WAITING_FOR_USER: "blue", MEDIUM: "blue", SCHEDULED: "blue", LOW: "grey", UNKNOWN: "grey",
  CANCELLED: "grey", LOST: "grey", RETIRED: "grey", NOT_INSTALLED: "red",
};

function badge(status) {
  if (status === null || status === undefined || status === "") return `<span class="badge badge-grey">—</span>`;
  const color = STATUS_COLOR_MAP[status] || "grey";
  const label = String(status).replace(/_/g, " ");
  return `<span class="badge badge-${color}"><span class="badge-dotcolor" style="background:var(--${color === "grey" ? "text-faint" : color})"></span>${escapeHtml(label)}</span>`;
}

function statusDot(status) {
  const color = STATUS_COLOR_MAP[status] || "grey";
  return `<span class="status-dot" style="background:var(--${color === "grey" ? "text-faint" : color})"></span>`;
}

/* ---------------- Modal ---------------- */
function closeModal() {
  const root = document.getElementById("modal-root");
  root.classList.add("hidden");
  root.innerHTML = "";
}

function openModal({ title, bodyHtml, onMount, width }) {
  const root = document.getElementById("modal-root");
  root.innerHTML = `
    <div class="modal-card" style="${width ? `width:${width}` : ""}">
      <div class="modal-header">
        <div class="modal-title">${escapeHtml(title)}</div>
        <button class="modal-close" id="modal-close-btn">&times;</button>
      </div>
      <div id="modal-body">${bodyHtml}</div>
    </div>
  `;
  root.classList.remove("hidden");
  root.onclick = (e) => { if (e.target === root) closeModal(); };
  document.getElementById("modal-close-btn").onclick = closeModal;
  if (onMount) onMount(root);
}

/* ---------------- Form field builder ---------------- */
function field({ label, name, type = "text", value = "", required = false, options = null, full = false, placeholder = "", step }) {
  const req = required ? "required" : "";
  const cls = full ? "field full" : "field";
  if (type === "select") {
    const opts = (options || []).map(o => {
      const val = typeof o === "object" ? o.value : o;
      const lab = typeof o === "object" ? o.label : o;
      const sel = String(val) === String(value) ? "selected" : "";
      return `<option value="${escapeHtml(val)}" ${sel}>${escapeHtml(lab)}</option>`;
    }).join("");
    return `<label class="${cls}"><span>${escapeHtml(label)}</span>
      <select name="${name}" ${req}><option value="">Select…</option>${opts}</select></label>`;
  }
  if (type === "textarea") {
    return `<label class="${cls}"><span>${escapeHtml(label)}</span>
      <textarea name="${name}" rows="3" placeholder="${escapeHtml(placeholder)}" ${req}>${escapeHtml(value)}</textarea></label>`;
  }
  return `<label class="${cls}"><span>${escapeHtml(label)}</span>
    <input type="${type}" name="${name}" value="${escapeHtml(value)}" placeholder="${escapeHtml(placeholder)}" ${step ? `step="${step}"` : ""} ${req} /></label>`;
}

function formToObject(form) {
  const data = {};
  new FormData(form).forEach((v, k) => { data[k] = v === "" ? null : v; });
  return data;
}

/* ---------------- Table renderer ---------------- */
function renderTable({ columns, rows, onRowClick, emptyText = "No records found." }) {
  if (!rows || rows.length === 0) {
    return `<div class="table-empty">${escapeHtml(emptyText)}</div>`;
  }
  const thead = columns.map(c => `<th>${escapeHtml(c.label)}</th>`).join("");
  const tbody = rows.map((row, idx) => {
    const tds = columns.map(c => `<td>${c.render ? c.render(row) : escapeHtml(row[c.key] ?? "—")}</td>`).join("");
    return `<tr data-row-idx="${idx}">${tds}</tr>`;
  }).join("");
  return `<div class="table-scroll"><table class="data-table"><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody></table></div>`;
}

function attachRowClicks(container, rows, handler) {
  container.querySelectorAll("tbody tr").forEach(tr => {
    tr.addEventListener("click", () => handler(rows[Number(tr.dataset.rowIdx)]));
  });
}

function qs(params) {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  if (!entries.length) return "";
  return "?" + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");
}

function confirmAction(message) {
  return window.confirm(message);
}

function roleAllows(...roles) {
  const user = Session.user;
  return user && roles.includes(user.role);
}
