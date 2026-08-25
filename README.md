ZCCCX# CBE District IT Management and Remote Support System

A full-stack **IT support and infrastructure management system** for a Commercial
Bank of Ethiopia (CBE) district office IT team. It lets district IT staff monitor
ATM status, manage network installation projects, track branch computers, receive
and resolve IT support tickets, log incidents, manage equipment and maintenance,
record remote-support sessions, and generate reports — across all branches the
district office supports.

> **This is an educational/IT-management simulation.** It is not connected to, and
> must never be connected to, real CBE ATM systems, banking systems, core banking
> networks, credentials, or production infrastructure. See **Simulation Mode**
> below.

---

## 1. Tech Stack

| Layer     | Technology |
|-----------|------------|
| Frontend  | Vanilla JavaScript (SPA, hash-router), HTML5, CSS3, [Chart.js](https://www.chartjs.org/) (via CDN) — no build step required |
| Backend   | Python 3, Flask, Flask-SQLAlchemy, Flask-JWT-Extended, Flask-CORS |
| Database  | SQLite (default, zero-config) — swappable for MySQL/PostgreSQL via `DATABASE_URL` |
| Reports   | CSV (built-in), Excel (`openpyxl`), PDF (`reportlab`) |
| Auth      | JWT access tokens, password hashing via Werkzeug, role-based authorization |

The frontend is served directly by the Flask backend (no separate frontend
server/build step needed) — just run the Flask app and open your browser.

---

## 2. Project Structure

```
cbe-district-it/
├── backend/
│   ├── app.py                 # Flask app factory, blueprint registration, static serving
│   ├── config.py               # Configuration (env vars, simulation mode, uploads)
│   ├── models.py               # SQLAlchemy models for all 17 database tables
│   ├── utils.py                 # Auth decorators, audit logging, notifications, helpers
│   ├── seed.py                  # Seeds the database with realistic simulated demo data
│   ├── test_app.py              # Pytest smoke tests
│   ├── requirements.txt
│   └── routes/                  # One blueprint per module (branches, atms, tickets, ...)
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── api.js               # API client wrapper
│       ├── ui.js                 # Reusable UI helpers (toasts, modals, tables, badges)
│       ├── views.js               # Per-module view renderers
│       └── app.js                  # Router, auth flow, sidebar navigation
└── README.md
```

---

## 3. Getting Started

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Seed the database with demo data

```bash
python seed.py
```

This creates `cbe_it.db` (SQLite) with 8 simulated branches, ATMs, computers,
tickets, incidents, assets, maintenance records, and the following **demo login
accounts**:

| Role                        | Username      | Password      |
|------------------------------|---------------|---------------|
| District IT Administrator    | `admin`       | `Admin@123`   |
| District IT Technician       | `tech1`       | `Tech@123`    |
| Branch Manager               | `mgr.add001`  | `Manager@123` |
| Branch Employee              | `employee`    | `Employee@123`|

(All data is simulated / fictitious and safe to reset at any time.)

### Run the application

```bash
python app.py
```

Then open **http://localhost:5000** in your browser. The Flask app serves both
the REST API (`/api/...`) and the frontend SPA (`/`).

### Run tests

```bash
pytest test_app.py -v
```

---

## 4. Roles & Permissions

| Role | Capabilities |
|---|---|
| **District IT Administrator** | Full access: manage users, branches, technicians, view all data, assign technicians, manage settings, view audit logs |
| **District IT Technician** | View assigned branches, monitor/check ATMs, record ATM errors, manage network installations, troubleshoot tickets, record maintenance |
| **Branch Employee** | Report computer/IT problems, view own submitted tickets, comment on tickets |
| **Branch Manager** | View branch IT status, incidents, maintenance reports, and installation progress for their branch |

Role is enforced both in the UI (hiding actions not permitted) and in the API
(`@roles_required(...)` decorators) — the API is the source of truth.

---

## 5. Simulation Mode (Important)

Per the project's real-world requirements, this system **never claims an ATM is
online just because the web server is running**. All ATM/network "checks" are
clearly labeled:

- `is_simulated: true` on every `ATMCheck` / `ATM` record unless a real,
  authorized monitoring integration is configured.
- To connect a **real, authorized** monitoring API, set the
  `AUTHORIZED_MONITORING_API_URL` environment variable and implement the
  integration call in `backend/routes/atm_routes.py` (`check_atm`). Until then,
  the system performs clearly-labeled simulated checks for demonstration only.
- Remote support sessions are **records only** — this system does not implement
  remote desktop control, credential capture, or hidden surveillance. Any actual
  remote-control activity must go through a separate, authorized enterprise
  remote-support tool (name recorded in `remote_tool_used`).

---

## 6. Database Tables

`users`, `branches`, `employees`, `technicians`, `atms`, `atm_checks`,
`atm_errors`, `network_installations`, `network_equipment`, `computers`,
`it_tickets`, `ticket_comments`, `incidents`, `assets`, `maintenance_records`,
`remote_support_sessions`, `notifications`, `audit_logs`.

All tables use proper primary/foreign keys, and cascading deletes are configured
where appropriate (e.g. deleting a branch removes its ATMs, computers, tickets).

---

## 7. Security Notes

- Passwords are hashed with Werkzeug's `generate_password_hash` (never stored
  in plain text).
- All API endpoints (except `/api/auth/login` and `/api/health`) require a
  valid JWT access token.
- Role-based authorization is enforced server-side on every mutating endpoint.
- File uploads are restricted by extension and size, and stored outside the
  webroot with randomized filenames.
- CORS is restricted via `CORS_ORIGINS` (defaults to `*` for local dev — set
  an explicit origin in production).
- Secrets (`SECRET_KEY`, `JWT_SECRET_KEY`) are read from environment variables;
  replace the development defaults before any real deployment.
- All significant actions (logins, creates, updates, deletes, ATM checks,
  ticket assignments) are recorded in `audit_logs`.

**This system must not be connected to real banking infrastructure, real ATM
networks, or real customer/employee credentials.** It is designed and intended
purely as an educational IT-operations management simulation.

---

## 8. Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `dev-secret-key-change-me` | Flask secret key |
| `JWT_SECRET_KEY` | `dev-jwt-secret-change-me` | JWT signing key |
| `DATABASE_URL` | `sqlite:///cbe_it.db` | SQLAlchemy database URL (swap for MySQL/Postgres) |
| `SIMULATION_MODE` | `true` | Master simulation-mode flag |
| `AUTHORIZED_MONITORING_API_URL` | *(empty)* | Set to enable real ATM monitoring integration |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `PORT` | `5000` | Server port |

---

## 9. API Overview

All endpoints are under `/api`. Highlights:

- `POST /api/auth/login`, `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/branches`
- `GET/POST/PUT/DELETE /api/atms`, `POST /api/atms/<id>/check`, `/api/atms/errors`
- `GET/POST/PUT /api/network-installations`, `/{id}/checklist`, `/{id}/equipment`
- `GET/POST/PUT/DELETE /api/computers`
- `GET/POST/PUT /api/tickets`, `/{id}/comments`
- `GET/POST/PUT /api/incidents`
- `GET/POST/PUT/DELETE /api/assets`
- `GET/POST/PUT/DELETE /api/maintenance`
- `GET/POST/PUT /api/remote-support`
- `GET /api/knowledge-base`
- `GET/POST/PUT/DELETE /api/users`, `/api/technicians`, `/api/employees`
- `GET /api/notifications`, `/api/notifications/unread-count`
- `GET /api/audit-logs`
- `GET /api/search?q=...`
- `GET /api/reports/<type>`, `GET /api/reports/<type>/export?format=csv|excel|pdf`
- `GET /api/dashboard/summary`, `GET /api/dashboard/charts`

---

## 10. Notes on Real-World Deployment

If this project were ever adapted beyond an educational simulation:

1. Replace SQLite with a managed MySQL/PostgreSQL instance.
2. Put the app behind a production WSGI server (gunicorn/uwsgi) and HTTPS.
3. Integrate ATM/network monitoring only through CBE's own authorized,
   approved infrastructure APIs — never scrape or spoof status.
4. Route all "remote support" through CBE's approved enterprise remote-support
   tooling; this codebase intentionally does not implement remote control.
5. Conduct a full security review (secrets management, rate limiting, WAF,
   dependency scanning) before any production use.

# cbe1
