"""
Database models for the CBE District IT Management and Remote Support System.

Tables (per project spec section 25):
users, branches, employees, technicians, atms, atm_checks, atm_errors,
network_installations, network_equipment, computers, it_tickets, incidents,
assets, maintenance_records, remote_support_sessions, notifications, audit_logs
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def now():
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# USERS / AUTH
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # district_admin | technician | branch_employee | branch_manager
    role = db.Column(db.String(30), nullable=False, default="branch_employee")
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=now)
    last_login = db.Column(db.DateTime, nullable=True)
    profile_photo = db.Column(db.String(255), nullable=True)

    branch = db.relationship("Branch", back_populates="users", foreign_keys=[branch_id])
    technician_profile = db.relationship("Technician", back_populates="user", uselist=False)
    employee_profile = db.relationship("Employee", back_populates="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "profile_photo": self.profile_photo,
        }


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)


# ---------------------------------------------------------------------------
# BRANCHES
# ---------------------------------------------------------------------------
class Branch(db.Model):
    __tablename__ = "branches"

    id = db.Column(db.Integer, primary_key=True)
    branch_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    location = db.Column(db.String(200))
    contact_number = db.Column(db.String(40))
    branch_manager_name = db.Column(db.String(120))
    number_of_computers = db.Column(db.Integer, default=0)
    number_of_atms = db.Column(db.Integer, default=0)
    # network_status: CONNECTED | DEGRADED | DISCONNECTED
    network_status = db.Column(db.String(20), default="CONNECTED")
    # overall_it_status: GREEN | YELLOW | RED
    overall_it_status = db.Column(db.String(10), default="GREEN")
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    users = db.relationship("User", back_populates="branch", foreign_keys=[User.branch_id])
    atms = db.relationship("ATM", back_populates="branch", cascade="all,delete-orphan")
    computers = db.relationship("Computer", back_populates="branch", cascade="all,delete-orphan")
    employees = db.relationship("Employee", back_populates="branch", cascade="all,delete-orphan")
    technicians = db.relationship("Technician", back_populates="branch")
    installations = db.relationship("NetworkInstallation", back_populates="branch", cascade="all,delete-orphan")
    tickets = db.relationship("ITTicket", back_populates="branch", cascade="all,delete-orphan")
    incidents = db.relationship("Incident", back_populates="branch", cascade="all,delete-orphan")
    assets = db.relationship("Asset", back_populates="branch", cascade="all,delete-orphan")

    def to_dict(self, detailed=False):
        d = {
            "id": self.id,
            "branch_code": self.branch_code,
            "name": self.name,
            "location": self.location,
            "contact_number": self.contact_number,
            "branch_manager_name": self.branch_manager_name,
            "number_of_computers": self.number_of_computers,
            "number_of_atms": self.number_of_atms,
            "network_status": self.network_status,
            "overall_it_status": self.overall_it_status,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }
        if detailed:
            d["open_tickets"] = len([t for t in self.tickets if t.status not in ("RESOLVED", "CLOSED")])
            d["atm_count"] = len(self.atms)
            d["computer_count"] = len(self.computers)
        return d


# ---------------------------------------------------------------------------
# EMPLOYEES / TECHNICIANS
# ---------------------------------------------------------------------------
class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    employee_id_code = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    department = db.Column(db.String(80))
    phone = db.Column(db.String(40))
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    branch = db.relationship("Branch", back_populates="employees")
    user = db.relationship("User", back_populates="employee_profile")

    def to_dict(self):
        return {
            "id": self.id,
            "employee_id_code": self.employee_id_code,
            "full_name": self.full_name,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "department": self.department,
            "phone": self.phone,
        }


class Technician(db.Model):
    __tablename__ = "technicians"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    specialty = db.Column(db.String(80))  # ATM | Network | Computer | General
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=True)  # primary assigned branch
    phone = db.Column(db.String(40))
    is_active = db.Column(db.Boolean, default=True)

    user = db.relationship("User", back_populates="technician_profile")
    branch = db.relationship("Branch", back_populates="technicians")

    def to_dict(self):
        open_tickets = ITTicket.query.filter_by(assigned_technician_id=self.id).filter(
            ITTicket.status.notin_(["RESOLVED", "CLOSED"])
        ).count()
        resolved_tickets = ITTicket.query.filter_by(assigned_technician_id=self.id).filter(
            ITTicket.status.in_(["RESOLVED", "CLOSED"])
        ).count()
        return {
            "id": self.id,
            "user_id": self.user_id,
            "full_name": self.full_name,
            "specialty": self.specialty,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "phone": self.phone,
            "is_active": self.is_active,
            "open_tickets": open_tickets,
            "resolved_tickets": resolved_tickets,
        }


# ---------------------------------------------------------------------------
# ATMs
# ---------------------------------------------------------------------------
class ATM(db.Model):
    __tablename__ = "atms"

    id = db.Column(db.Integer, primary_key=True)
    atm_code = db.Column(db.String(30), unique=True, nullable=False)  # e.g. ATM-001
    serial_number = db.Column(db.String(80))
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    location_description = db.Column(db.String(200))
    ip_address = db.Column(db.String(45))
    network_connection = db.Column(db.String(20), default="CONNECTED")  # CONNECTED | DISCONNECTED
    model_type = db.Column(db.String(80))
    installation_date = db.Column(db.Date, nullable=True)
    last_maintenance_date = db.Column(db.Date, nullable=True)
    # ONLINE | OFFLINE | WARNING | MAINTENANCE | ERROR | UNKNOWN
    status = db.Column(db.String(20), default="UNKNOWN")
    error_status = db.Column(db.String(120), nullable=True)
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=True)
    last_checked_at = db.Column(db.DateTime, nullable=True)
    is_simulated = db.Column(db.Boolean, default=True)  # True unless real monitoring integration is used
    created_at = db.Column(db.DateTime, default=now)

    branch = db.relationship("Branch", back_populates="atms")
    technician = db.relationship("Technician")
    checks = db.relationship("ATMCheck", back_populates="atm", cascade="all,delete-orphan")
    errors = db.relationship("ATMError", back_populates="atm", cascade="all,delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "atm_code": self.atm_code,
            "serial_number": self.serial_number,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "location_description": self.location_description,
            "ip_address": self.ip_address,
            "network_connection": self.network_connection,
            "model_type": self.model_type,
            "installation_date": self.installation_date.isoformat() if self.installation_date else None,
            "last_maintenance_date": self.last_maintenance_date.isoformat() if self.last_maintenance_date else None,
            "status": self.status,
            "error_status": self.error_status,
            "technician_id": self.technician_id,
            "technician_name": self.technician.full_name if self.technician else None,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "is_simulated": self.is_simulated,
        }


class ATMCheck(db.Model):
    __tablename__ = "atm_checks"

    id = db.Column(db.Integer, primary_key=True)
    atm_id = db.Column(db.Integer, db.ForeignKey("atms.id"), nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    check_time = db.Column(db.DateTime, default=now)
    network_status = db.Column(db.String(20))
    availability_status = db.Column(db.String(20))
    error = db.Column(db.String(200), nullable=True)
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_simulated = db.Column(db.Boolean, default=True)

    atm = db.relationship("ATM", back_populates="checks")
    technician = db.relationship("Technician")

    def to_dict(self):
        return {
            "id": self.id,
            "atm_id": self.atm_id,
            "atm_code": self.atm.atm_code if self.atm else None,
            "branch_id": self.branch_id,
            "check_time": self.check_time.isoformat() if self.check_time else None,
            "network_status": self.network_status,
            "availability_status": self.availability_status,
            "error": self.error,
            "technician_id": self.technician_id,
            "technician_name": self.technician.full_name if self.technician else None,
            "notes": self.notes,
            "is_simulated": self.is_simulated,
        }


class ATMError(db.Model):
    __tablename__ = "atm_errors"

    id = db.Column(db.Integer, primary_key=True)
    error_code = db.Column(db.String(30))
    error_type = db.Column(db.String(60), nullable=False)  # category, e.g. "Network disconnected"
    error_group = db.Column(db.String(30))  # Network | Hardware | Software | Security | Other
    description = db.Column(db.Text)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    atm_id = db.Column(db.Integer, db.ForeignKey("atms.id"), nullable=False)
    severity = db.Column(db.String(20), default="MEDIUM")  # LOW | MEDIUM | HIGH | CRITICAL
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=True)
    resolution = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="OPEN")  # OPEN | IN_PROGRESS | RESOLVED
    created_at = db.Column(db.DateTime, default=now)
    resolved_at = db.Column(db.DateTime, nullable=True)

    atm = db.relationship("ATM", back_populates="errors")
    branch = db.relationship("Branch")
    technician = db.relationship("Technician")

    def to_dict(self):
        return {
            "id": self.id,
            "error_code": self.error_code,
            "error_type": self.error_type,
            "error_group": self.error_group,
            "description": self.description,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "atm_id": self.atm_id,
            "atm_code": self.atm.atm_code if self.atm else None,
            "severity": self.severity,
            "technician_id": self.technician_id,
            "technician_name": self.technician.full_name if self.technician else None,
            "resolution": self.resolution,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


# ---------------------------------------------------------------------------
# NETWORK INSTALLATION
# ---------------------------------------------------------------------------
class NetworkInstallation(db.Model):
    __tablename__ = "network_installations"

    id = db.Column(db.Integer, primary_key=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    installation_type = db.Column(db.String(80))  # New Branch Setup | Upgrade | Expansion...
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    expected_completion = db.Column(db.Date, nullable=True)
    actual_completion = db.Column(db.Date, nullable=True)
    # PLANNED | IN_PROGRESS | TESTING | COMPLETED | FAILED | CANCELLED
    status = db.Column(db.String(20), default="PLANNED")
    problems = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    checklist = db.Column(db.JSON, default=dict)  # {"router_installed": true, ...}
    created_at = db.Column(db.DateTime, default=now)

    branch = db.relationship("Branch", back_populates="installations")
    technician = db.relationship("Technician")
    equipment = db.relationship("NetworkEquipment", back_populates="installation", cascade="all,delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "installation_type": self.installation_type,
            "technician_id": self.technician_id,
            "technician_name": self.technician.full_name if self.technician else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "expected_completion": self.expected_completion.isoformat() if self.expected_completion else None,
            "actual_completion": self.actual_completion.isoformat() if self.actual_completion else None,
            "status": self.status,
            "problems": self.problems,
            "notes": self.notes,
            "checklist": self.checklist or {},
            "equipment": [e.to_dict() for e in self.equipment],
        }


CHECKLIST_ITEMS = [
    "router_installed",
    "switch_installed",
    "cables_installed",
    "ip_configuration_completed",
    "gateway_configured",
    "dns_configured",
    "connectivity_tested",
    "branch_computers_connected",
    "atm_network_checked",
    "security_configuration_checked",
    "documentation_completed",
]


class NetworkEquipment(db.Model):
    __tablename__ = "network_equipment"

    id = db.Column(db.Integer, primary_key=True)
    installation_id = db.Column(db.Integer, db.ForeignKey("network_installations.id"), nullable=False)
    equipment_type = db.Column(db.String(60))  # Router | Switch | Access Point | Firewall | Cable | Patch Panel | Rack | UPS
    model = db.Column(db.String(120))
    serial_number = db.Column(db.String(80))
    quantity = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default="INSTALLED")

    installation = db.relationship("NetworkInstallation", back_populates="equipment")

    def to_dict(self):
        return {
            "id": self.id,
            "installation_id": self.installation_id,
            "equipment_type": self.equipment_type,
            "model": self.model,
            "serial_number": self.serial_number,
            "quantity": self.quantity,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# COMPUTERS
# ---------------------------------------------------------------------------
class Computer(db.Model):
    __tablename__ = "computers"

    id = db.Column(db.Integer, primary_key=True)
    asset_number = db.Column(db.String(40), unique=True, nullable=False)
    hostname = db.Column(db.String(80))
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    department = db.Column(db.String(80))
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    operating_system = db.Column(db.String(60))
    ram = db.Column(db.String(20))
    storage = db.Column(db.String(30))
    processor = db.Column(db.String(80))
    ip_address = db.Column(db.String(45))
    mac_address = db.Column(db.String(45))
    antivirus_status = db.Column(db.String(20), default="PROTECTED")  # PROTECTED | OUTDATED | NOT_INSTALLED
    # WORKING | WARNING | ERROR | OFFLINE | UNDER_MAINTENANCE
    status = db.Column(db.String(20), default="WORKING")
    last_maintenance_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    branch = db.relationship("Branch", back_populates="computers")
    employee = db.relationship("Employee")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_number": self.asset_number,
            "hostname": self.hostname,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "department": self.department,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "operating_system": self.operating_system,
            "ram": self.ram,
            "storage": self.storage,
            "processor": self.processor,
            "ip_address": self.ip_address,
            "mac_address": self.mac_address,
            "antivirus_status": self.antivirus_status,
            "status": self.status,
            "last_maintenance_date": self.last_maintenance_date.isoformat() if self.last_maintenance_date else None,
        }


# ---------------------------------------------------------------------------
# IT TICKETS
# ---------------------------------------------------------------------------
class ITTicket(db.Model):
    __tablename__ = "it_tickets"

    id = db.Column(db.Integer, primary_key=True)
    ticket_code = db.Column(db.String(30), unique=True, nullable=False)  # IT-1024
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True)
    problem_category = db.Column(db.String(60))
    description = db.Column(db.Text)
    attachment_path = db.Column(db.String(255), nullable=True)
    priority = db.Column(db.String(20), default="MEDIUM")  # LOW | MEDIUM | HIGH | CRITICAL
    assigned_technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=True)
    # OPEN | ASSIGNED | IN_PROGRESS | WAITING_FOR_USER | RESOLVED | CLOSED
    status = db.Column(db.String(30), default="OPEN")
    resolution = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)
    closed_at = db.Column(db.DateTime, nullable=True)

    branch = db.relationship("Branch", back_populates="tickets")
    employee = db.relationship("Employee")
    computer = db.relationship("Computer")
    technician = db.relationship("Technician")
    comments = db.relationship("TicketComment", back_populates="ticket", cascade="all,delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_code": self.ticket_code,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "computer_id": self.computer_id,
            "computer_asset_number": self.computer.asset_number if self.computer else None,
            "problem_category": self.problem_category,
            "description": self.description,
            "attachment_path": self.attachment_path,
            "priority": self.priority,
            "assigned_technician_id": self.assigned_technician_id,
            "assigned_technician_name": self.technician.full_name if self.technician else None,
            "status": self.status,
            "resolution": self.resolution,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "comments": [c.to_dict() for c in self.comments],
        }


class TicketComment(db.Model):
    __tablename__ = "ticket_comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("it_tickets.id"), nullable=False)
    author_name = db.Column(db.String(120))
    author_role = db.Column(db.String(30))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=now)

    ticket = db.relationship("ITTicket", back_populates="comments")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "author_name": self.author_name,
            "author_role": self.author_role,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# INCIDENTS
# ---------------------------------------------------------------------------
class Incident(db.Model):
    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    incident_code = db.Column(db.String(30), unique=True, nullable=False)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    category = db.Column(db.String(40))  # ATM | Network | Computer | Printer | Server | Software | Security | Power
    description = db.Column(db.Text)
    severity = db.Column(db.String(20), default="MEDIUM")
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=True)
    status = db.Column(db.String(20), default="OPEN")  # OPEN | IN_PROGRESS | RESOLVED
    resolution = db.Column(db.Text, nullable=True)
    date_opened = db.Column(db.DateTime, default=now)
    date_resolved = db.Column(db.DateTime, nullable=True)

    branch = db.relationship("Branch", back_populates="incidents")
    technician = db.relationship("Technician")

    def to_dict(self):
        return {
            "id": self.id,
            "incident_code": self.incident_code,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "technician_id": self.technician_id,
            "technician_name": self.technician.full_name if self.technician else None,
            "status": self.status,
            "resolution": self.resolution,
            "date_opened": self.date_opened.isoformat() if self.date_opened else None,
            "date_resolved": self.date_resolved.isoformat() if self.date_resolved else None,
        }


# ---------------------------------------------------------------------------
# ASSETS (equipment inventory)
# ---------------------------------------------------------------------------
class Asset(db.Model):
    __tablename__ = "assets"

    id = db.Column(db.Integer, primary_key=True)
    asset_code = db.Column(db.String(40), unique=True, nullable=False)
    serial_number = db.Column(db.String(80))
    asset_type = db.Column(db.String(40))  # Computer|Printer|Scanner|Router|Switch|AP|UPS|Server|ATM|Other
    model = db.Column(db.String(120))
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    assigned_user = db.Column(db.String(120), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    installation_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="ACTIVE")  # ACTIVE | RETIRED | UNDER_REPAIR | LOST
    created_at = db.Column(db.DateTime, default=now)

    branch = db.relationship("Branch", back_populates="assets")
    maintenance_records = db.relationship("MaintenanceRecord", back_populates="asset", cascade="all,delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "asset_code": self.asset_code,
            "serial_number": self.serial_number,
            "asset_type": self.asset_type,
            "model": self.model,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "assigned_user": self.assigned_user,
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "installation_date": self.installation_date.isoformat() if self.installation_date else None,
            "status": self.status,
        }


# ---------------------------------------------------------------------------
# MAINTENANCE
# ---------------------------------------------------------------------------
class MaintenanceRecord(db.Model):
    __tablename__ = "maintenance_records"

    id = db.Column(db.Integer, primary_key=True)
    maintenance_type = db.Column(db.String(20), default="PREVENTIVE")  # PREVENTIVE | CORRECTIVE
    asset_id = db.Column(db.Integer, db.ForeignKey("assets.id"), nullable=True)
    atm_id = db.Column(db.Integer, db.ForeignKey("atms.id"), nullable=True)
    computer_id = db.Column(db.Integer, db.ForeignKey("computers.id"), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=True)
    scheduled_date = db.Column(db.Date, nullable=True)
    completion_date = db.Column(db.Date, nullable=True)
    problem = db.Column(db.Text, nullable=True)  # for corrective
    checklist = db.Column(db.JSON, default=dict)  # for preventive
    repair_action = db.Column(db.Text, nullable=True)
    result = db.Column(db.String(20), default="PENDING")  # PENDING | PASSED | FAILED | COMPLETED
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    asset = db.relationship("Asset", back_populates="maintenance_records")
    branch = db.relationship("Branch")
    technician = db.relationship("Technician")
    atm = db.relationship("ATM")
    computer = db.relationship("Computer")

    def to_dict(self):
        return {
            "id": self.id,
            "maintenance_type": self.maintenance_type,
            "asset_id": self.asset_id,
            "asset_code": self.asset.asset_code if self.asset else None,
            "atm_id": self.atm_id,
            "atm_code": self.atm.atm_code if self.atm else None,
            "computer_id": self.computer_id,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "technician_id": self.technician_id,
            "technician_name": self.technician.full_name if self.technician else None,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
            "problem": self.problem,
            "checklist": self.checklist or {},
            "repair_action": self.repair_action,
            "result": self.result,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# REMOTE SUPPORT
# ---------------------------------------------------------------------------
class RemoteSupportSession(db.Model):
    __tablename__ = "remote_support_sessions"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("it_tickets.id"), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branches.id"), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey("technicians.id"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=True)
    scheduled_time = db.Column(db.DateTime, nullable=True)
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    # SCHEDULED | IN_PROGRESS | COMPLETED | CANCELLED
    status = db.Column(db.String(20), default="SCHEDULED")
    troubleshooting_steps = db.Column(db.Text, nullable=True)
    resolution = db.Column(db.Text, nullable=True)
    # Notes that this used an authorized enterprise remote-support tool
    remote_tool_used = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    ticket = db.relationship("ITTicket")
    branch = db.relationship("Branch")
    technician = db.relationship("Technician")
    employee = db.relationship("Employee")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "ticket_code": self.ticket.ticket_code if self.ticket else None,
            "branch_id": self.branch_id,
            "branch_name": self.branch.name if self.branch else None,
            "technician_id": self.technician_id,
            "technician_name": self.technician.full_name if self.technician else None,
            "employee_id": self.employee_id,
            "employee_name": self.employee.full_name if self.employee else None,
            "scheduled_time": self.scheduled_time.isoformat() if self.scheduled_time else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "troubleshooting_steps": self.troubleshooting_steps,
            "resolution": self.resolution,
            "remote_tool_used": self.remote_tool_used,
        }


# ---------------------------------------------------------------------------
# NOTIFICATIONS
# ---------------------------------------------------------------------------
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # null = broadcast to admins
    type = db.Column(db.String(40))  # e.g. ATM_CRITICAL, ATM_OFFLINE, TICKET_NEW, ...
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    severity = db.Column(db.String(20), default="INFO")  # INFO | WARNING | CRITICAL
    related_entity = db.Column(db.String(40), nullable=True)  # e.g. "atm", "ticket"
    related_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "severity": self.severity,
            "related_entity": self.related_entity,
            "related_id": self.related_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# AUDIT LOG
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user_name = db.Column(db.String(120), nullable=True)
    action = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=now)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "action": self.action,
            "description": self.description,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


DASHBOARD_METRIC_FIELDS = [
    "total_branches", "total_atms", "operational_atms", "offline_atms",
    "atm_errors", "pending_tickets", "in_progress_tickets", "resolved_tickets",
    "network_installations", "completed_installations", "pending_installations",
    "computers_with_problems", "active_technicians",
]


class DailyMetricSnapshot(db.Model):
    """One row per calendar day holding the dashboard KPI values for that
    day. Powers real (non-fabricated) trend arrows / sparklines on the
    dashboard. A row is upserted every time /api/dashboard/summary is
    requested, so it always reflects the latest known value for 'today'."""
    __tablename__ = "daily_metric_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    snapshot_date = db.Column(db.Date, nullable=False, unique=True, index=True)

    total_branches = db.Column(db.Integer, default=0)
    total_atms = db.Column(db.Integer, default=0)
    operational_atms = db.Column(db.Integer, default=0)
    offline_atms = db.Column(db.Integer, default=0)
    atm_errors = db.Column(db.Integer, default=0)
    pending_tickets = db.Column(db.Integer, default=0)
    in_progress_tickets = db.Column(db.Integer, default=0)
    resolved_tickets = db.Column(db.Integer, default=0)
    network_installations = db.Column(db.Integer, default=0)
    completed_installations = db.Column(db.Integer, default=0)
    pending_installations = db.Column(db.Integer, default=0)
    computers_with_problems = db.Column(db.Integer, default=0)
    active_technicians = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    def to_dict(self):
        d = {"date": self.snapshot_date.isoformat()}
        for f in DASHBOARD_METRIC_FIELDS:
            d[f] = getattr(self, f)
        return d


def log_action(user, action, description="", ip_address=None):
    entry = AuditLog(
        user_id=user.id if user else None,
        user_name=user.full_name if user else "System",
        action=action,
        description=description,
        ip_address=ip_address,
    )
    db.session.add(entry)
    db.session.commit()
    return entry
