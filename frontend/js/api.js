/* API client for the CBE District IT Management System */
const API_BASE = "/api";

const Session = {
  get token() { return localStorage.getItem("cbe_token"); },
  set token(v) { v ? localStorage.setItem("cbe_token", v) : localStorage.removeItem("cbe_token"); },
  get user() { try { return JSON.parse(localStorage.getItem("cbe_user")); } catch { return null; } },
  set user(v) { v ? localStorage.setItem("cbe_user", JSON.stringify(v)) : localStorage.removeItem("cbe_user"); },
  clear() { this.token = null; this.user = null; },
};

async function apiRequest(method, path, body, opts = {}) {
  const headers = {};
  if (!(body instanceof FormData)) headers["Content-Type"] = "application/json";
  if (Session.token) headers["Authorization"] = `Bearer ${Session.token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? (body instanceof FormData ? body : JSON.stringify(body)) : undefined,
  });

  if (res.status === 401 && !opts.silent401) {
    Session.clear();
    window.location.reload();
    throw new Error("Unauthorized");
  }

  if (opts.raw) return res;

  const contentType = res.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    const message = (data && data.error) ? data.error : `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

const Api = {
  // Auth
  login: (username, password) => apiRequest("POST", "/auth/login", { username, password }, { silent401: true }),
  me: () => apiRequest("GET", "/auth/me"),
  changePassword: (old_password, new_password) => apiRequest("POST", "/auth/change-password", { old_password, new_password }),

  // Dashboard
  dashboardSummary: () => apiRequest("GET", "/dashboard/summary"),
  dashboardCharts: () => apiRequest("GET", "/dashboard/charts"),

  // Branches
  listBranches: (params = "") => apiRequest("GET", `/branches${params}`),
  getBranch: (id) => apiRequest("GET", `/branches/${id}`),
  createBranch: (data) => apiRequest("POST", "/branches", data),
  updateBranch: (id, data) => apiRequest("PUT", `/branches/${id}`, data),
  deleteBranch: (id) => apiRequest("DELETE", `/branches/${id}`),

  // ATMs
  listAtms: (params = "") => apiRequest("GET", `/atms${params}`),
  getAtm: (id) => apiRequest("GET", `/atms/${id}`),
  createAtm: (data) => apiRequest("POST", "/atms", data),
  updateAtm: (id, data) => apiRequest("PUT", `/atms/${id}`, data),
  deleteAtm: (id) => apiRequest("DELETE", `/atms/${id}`),
  checkAtm: (id, data = {}) => apiRequest("POST", `/atms/${id}/check`, data),
  errorCatalog: () => apiRequest("GET", "/atms/error-catalog"),
  listAtmErrors: (params = "") => apiRequest("GET", `/atms/errors/list${params}`),
  createAtmError: (data) => apiRequest("POST", "/atms/errors", data),
  updateAtmError: (id, data) => apiRequest("PUT", `/atms/errors/${id}`, data),

  // Network installations
  listInstallations: (params = "") => apiRequest("GET", `/network-installations${params}`),
  getInstallation: (id) => apiRequest("GET", `/network-installations/${id}`),
  createInstallation: (data) => apiRequest("POST", "/network-installations", data),
  updateInstallation: (id, data) => apiRequest("PUT", `/network-installations/${id}`, data),
  updateChecklist: (id, data) => apiRequest("PUT", `/network-installations/${id}/checklist`, data),
  addEquipment: (id, data) => apiRequest("POST", `/network-installations/${id}/equipment`, data),
  deleteInstallation: (id) => apiRequest("DELETE", `/network-installations/${id}`),
  checklistItems: () => apiRequest("GET", "/network-installations/checklist-items"),

  // Computers
  listComputers: (params = "") => apiRequest("GET", `/computers${params}`),
  getComputer: (id) => apiRequest("GET", `/computers/${id}`),
  createComputer: (data) => apiRequest("POST", "/computers", data),
  updateComputer: (id, data) => apiRequest("PUT", `/computers/${id}`, data),
  deleteComputer: (id) => apiRequest("DELETE", `/computers/${id}`),

  // Tickets
  listTickets: (params = "") => apiRequest("GET", `/tickets${params}`),
  getTicket: (id) => apiRequest("GET", `/tickets/${id}`),
  createTicket: (data) => apiRequest("POST", "/tickets", data),
  updateTicket: (id, data) => apiRequest("PUT", `/tickets/${id}`, data),
  addTicketComment: (id, message) => apiRequest("POST", `/tickets/${id}/comments`, { message }),
  ticketCategories: () => apiRequest("GET", "/tickets/categories"),

  // Incidents
  listIncidents: (params = "") => apiRequest("GET", `/incidents${params}`),
  createIncident: (data) => apiRequest("POST", "/incidents", data),
  updateIncident: (id, data) => apiRequest("PUT", `/incidents/${id}`, data),
  incidentTypes: () => apiRequest("GET", "/incidents/types"),

  // Assets
  listAssets: (params = "") => apiRequest("GET", `/assets${params}`),
  getAsset: (id) => apiRequest("GET", `/assets/${id}`),
  createAsset: (data) => apiRequest("POST", "/assets", data),
  updateAsset: (id, data) => apiRequest("PUT", `/assets/${id}`, data),
  deleteAsset: (id) => apiRequest("DELETE", `/assets/${id}`),
  assetTypes: () => apiRequest("GET", "/assets/types"),

  // Maintenance
  listMaintenance: (params = "") => apiRequest("GET", `/maintenance${params}`),
  createMaintenance: (data) => apiRequest("POST", "/maintenance", data),
  updateMaintenance: (id, data) => apiRequest("PUT", `/maintenance/${id}`, data),
  deleteMaintenance: (id) => apiRequest("DELETE", `/maintenance/${id}`),

  // Remote support
  listRemoteSupport: (params = "") => apiRequest("GET", `/remote-support${params}`),
  createRemoteSupport: (data) => apiRequest("POST", "/remote-support", data),
  updateRemoteSupport: (id, data) => apiRequest("PUT", `/remote-support/${id}`, data),

  // Knowledge base
  knowledgeBase: () => apiRequest("GET", "/knowledge-base"),

  // Users / Technicians / Employees
  listUsers: (params = "") => apiRequest("GET", `/users${params}`),
  createUser: (data) => apiRequest("POST", "/users", data),
  updateUser: (id, data) => apiRequest("PUT", `/users/${id}`, data),
  resetUserPassword: (id, password) => apiRequest("POST", `/users/${id}/reset-password`, { password }),
  uploadUserPhoto: (id, formData) => apiRequest("POST", `/users/${id}/photo`, formData),
  deleteUser: (id) => apiRequest("DELETE", `/users/${id}`),
  listTechnicians: (params = "") => apiRequest("GET", `/technicians${params}`),
  updateTechnician: (id, data) => apiRequest("PUT", `/technicians/${id}`, data),
  listEmployees: (params = "") => apiRequest("GET", `/employees${params}`),
  createEmployee: (data) => apiRequest("POST", "/employees", data),
  getSettings: () => apiRequest("GET", "/settings"),
  updateSettings: (data) => apiRequest("PUT", "/settings", data),

  // Notifications
  listNotifications: (params = "") => apiRequest("GET", `/notifications${params}`),
  unreadCount: () => apiRequest("GET", "/notifications/unread-count"),
  markRead: (id) => apiRequest("PUT", `/notifications/${id}/read`),
  markAllRead: () => apiRequest("PUT", "/notifications/mark-all-read"),

  // Audit logs
  listAuditLogs: (params = "") => apiRequest("GET", `/audit-logs${params}`),

  // Search
  search: (q) => apiRequest("GET", `/search?q=${encodeURIComponent(q)}`),

  // Reports
  getReport: (type) => apiRequest("GET", `/reports/${type}`),
  exportReportUrl: (type, format) => `${API_BASE}/reports/${type}/export?format=${format}`,

  // Uploads
  uploadFile: (formData) => apiRequest("POST", "/uploads", formData),
};
