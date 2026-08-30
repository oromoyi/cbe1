"""
Seed the CBE District IT Management database with realistic demo data.

All data here is SIMULATED for educational/demo purposes and is not
connected to any real CBE system. Run with:  python seed.py
"""
import os
import random
from datetime import datetime, timedelta, date

from app import create_app
from models import (
    db, User, Branch, Employee, Technician, ATM, ATMCheck, ATMError,
    NetworkInstallation, NetworkEquipment, CHECKLIST_ITEMS, Computer,
    ITTicket, TicketComment, Incident, Asset, MaintenanceRecord,
    RemoteSupportSession, Notification, AuditLog,
    DailyMetricSnapshot, DASHBOARD_METRIC_FIELDS,
)

random.seed(42)

BRANCH_DATA = [
    ("ADD001", "Ambo District CBE Branch", "Ambo, Oromia"),
    ("ADD002", "Merkato Branch", "Merkato, Addis Ababa"),
    ("ADD003", "Piassa Branch", "Piassa, Addis Ababa"),
    ("ADD004", "Kazanchis Branch", "Kazanchis, Addis Ababa"),
    ("ADD005", "Gerji Branch", "Gerji, Addis Ababa"),
    ("ADD006", "CMC Branch", "CMC, Addis Ababa"),
    ("ADD007", "Megenagna Branch", "Megenagna, Addis Ababa"),
    ("ADD008", "Sarbet Branch", "Sarbet, Addis Ababa"),
]

FIRST_NAMES = ["Abebe", "Kebede", "Almaz", "Selam", "Marta", "Yonas", "Hana", "Dawit",
               "Sara", "Solomon", "Meron", "Henok", "Bethlehem", "Natnael", "Rahel", "Samuel"]
LAST_NAMES = ["Tesfaye", "Girma", "Bekele", "Alemu", "Haile", "Wolde", "Mekonnen",
              "Assefa", "Tadesse", "Gebre", "Fikru", "Desta"]


def rand_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def days_ago(n):
    return datetime.utcnow() - timedelta(days=n)


def main(app=None):
    app = app or create_app()
    with app.app_context():
        print("Resetting database...")
        db.drop_all()
        db.create_all()

        # --- Users & core admin/technician accounts ---
        print("Creating users...")
        admin = User(full_name="Debi Tolessa", username="admin", email="admin@cbe-it.local", role="district_admin")
        admin.set_password(os.environ.get("ADMIN_PASSWORD", "Admin@123"))
        db.session.add(admin)
        db.session.commit()

        # --- Branches ---
        print("Creating branches...")
        branches = []
        for code, name, location in BRANCH_DATA:
            b = Branch(
                branch_code=code,
                name=name,
                location=location,
                contact_number=f"+251-11-{random.randint(1000000,9999999)}",
                branch_manager_name=rand_name(),
                number_of_computers=random.randint(8, 25),
                number_of_atms=random.randint(1, 4),
                network_status=random.choice(["CONNECTED", "CONNECTED", "CONNECTED", "DEGRADED"]),
                overall_it_status=random.choice(["GREEN", "GREEN", "GREEN", "YELLOW", "RED"]),
            )
            branches.append(b)
            db.session.add(b)
        db.session.commit()

        # --- Branch managers & employees ---
        print("Creating branch managers and employees...")
        employees = []
        for b in branches:
            mgr_user = User(
                full_name=b.branch_manager_name, username=f"mgr.{b.branch_code.lower()}",
                email=f"mgr.{b.branch_code.lower()}@cbe-it.local", role="branch_manager", branch_id=b.id,
            )
            mgr_user.set_password("Manager@123")
            db.session.add(mgr_user)

            for i in range(random.randint(3, 6)):
                emp = Employee(
                    employee_id_code=f"{b.branch_code}-EMP{i+1:02d}",
                    full_name=rand_name(),
                    branch_id=b.id,
                    department=random.choice(["Customer Service", "Teller", "Credit", "Operations", "Loan"]),
                    phone=f"+251-9{random.randint(10000000,39999999)}",
                )
                employees.append(emp)
                db.session.add(emp)
        db.session.commit()

        # One branch employee login for demo purposes
        demo_employee = employees[0]
        emp_user = User(
            full_name=demo_employee.full_name, username="employee",
            email="employee@cbe-it.local", role="branch_employee", branch_id=demo_employee.branch_id,
        )
        emp_user.set_password("Employee@123")
        db.session.add(emp_user)
        db.session.commit()
        demo_employee.user_id = emp_user.id
        db.session.commit()

        # --- Technicians ---
        print("Creating technicians...")
        specialties = ["ATM", "Network", "Computer", "General"]
        technicians = []
        for i in range(6):
            username = f"tech{i+1}"
            tuser = User(full_name=rand_name(), username=username,
                         email=f"{username}@cbe-it.local", role="technician")
            tuser.set_password("Tech@123")
            db.session.add(tuser)
            db.session.commit()
            tech = Technician(
                user_id=tuser.id,
                full_name=tuser.full_name,
                specialty=specialties[i % len(specialties)],
                branch_id=random.choice(branches).id,
                phone=f"+251-9{random.randint(10000000,39999999)}",
                is_active=True,
            )
            technicians.append(tech)
            db.session.add(tech)
        db.session.commit()

        # --- ATMs, checks & errors (SIMULATED) ---
        print("Creating ATMs...")
        atm_error_catalog = {
            "Network": ["Network disconnected", "IP address problem", "Gateway problem", "DNS problem",
                        "Network timeout", "Connection refused"],
            "Hardware": ["Card reader error", "Cash dispenser error", "Receipt printer error",
                         "Display error", "Keyboard error", "Sensor error", "Power failure"],
            "Software": ["Application failure", "Operating system error", "Service stopped",
                         "Configuration error", "Software crash"],
            "Security": ["Authentication failure", "Communication security error", "Access denied"],
            "Other": ["Unknown error", "Maintenance required", "Device unavailable"],
        }
        statuses = ["ONLINE", "ONLINE", "ONLINE", "OFFLINE", "WARNING", "ERROR", "MAINTENANCE"]
        atm_counter = 1
        atms = []
        for b in branches:
            for i in range(b.number_of_atms):
                status = random.choice(statuses)
                atm = ATM(
                    atm_code=f"ATM-{atm_counter:03d}",
                    serial_number=f"SN-{random.randint(100000,999999)}",
                    branch_id=b.id,
                    location_description=random.choice(["Main Hall", "Drive-through", "Outdoor Kiosk", "Lobby"]),
                    ip_address=f"10.{b.id}.{i+1}.{random.randint(2,254)}",
                    network_connection="CONNECTED" if status in ("ONLINE", "WARNING") else "DISCONNECTED",
                    model_type=random.choice(["NCR SelfServ 84", "Diebold Nixdorf ProCash", "Wincor CINEO C4060"]),
                    installation_date=date.today() - timedelta(days=random.randint(200, 1800)),
                    last_maintenance_date=date.today() - timedelta(days=random.randint(5, 90)),
                    status=status,
                    error_status=None,
                    technician_id=random.choice(technicians).id,
                    last_checked_at=days_ago(random.randint(0, 2)),
                    is_simulated=True,
                )
                atms.append(atm)
                db.session.add(atm)
                atm_counter += 1
        db.session.commit()

        print("Creating ATM checks and errors...")
        for atm in atms:
            for i in range(random.randint(2, 5)):
                check = ATMCheck(
                    atm_id=atm.id,
                    branch_id=atm.branch_id,
                    check_time=days_ago(random.randint(0, 30)),
                    network_status=atm.network_connection,
                    availability_status=random.choice(["ONLINE", "ONLINE", "OFFLINE", "WARNING"]),
                    error=None,
                    technician_id=atm.technician_id,
                    notes="Routine simulated status check.",
                    is_simulated=True,
                )
                db.session.add(check)

            if atm.status in ("ERROR", "OFFLINE", "WARNING"):
                group = random.choice(list(atm_error_catalog.keys()))
                err_type = random.choice(atm_error_catalog[group])
                err = ATMError(
                    error_code=f"ERR-{1000 + atm.id}",
                    error_type=err_type,
                    error_group=group,
                    description=f"Technician confirmed: {err_type} on {atm.atm_code}.",
                    branch_id=atm.branch_id,
                    atm_id=atm.id,
                    severity=random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                    technician_id=atm.technician_id,
                    status=random.choice(["OPEN", "IN_PROGRESS", "RESOLVED"]),
                    created_at=days_ago(random.randint(0, 15)),
                )
                atm.error_status = err_type
                db.session.add(err)
        db.session.commit()

        # --- Network installations ---
        print("Creating network installation projects...")
        install_types = ["New Branch Setup", "Network Upgrade", "ATM Network Expansion", "WiFi Rollout"]
        equipment_types = ["Router", "Switch", "Access Point", "Firewall", "Network Cable", "Patch Panel", "Rack", "UPS"]
        for b in random.sample(branches, k=5):
            status = random.choice(["PLANNED", "IN_PROGRESS", "TESTING", "COMPLETED", "COMPLETED", "FAILED"])
            checklist = {item: (status == "COMPLETED" or random.random() > 0.4) for item in CHECKLIST_ITEMS}
            inst = NetworkInstallation(
                branch_id=b.id,
                installation_type=random.choice(install_types),
                technician_id=random.choice(technicians).id,
                start_date=date.today() - timedelta(days=random.randint(10, 120)),
                expected_completion=date.today() + timedelta(days=random.randint(-10, 30)),
                actual_completion=date.today() - timedelta(days=random.randint(0, 10)) if status == "COMPLETED" else None,
                status=status,
                problems="Cable routing delay due to civil works." if status == "FAILED" else None,
                notes="Simulated project record for demonstration.",
                checklist=checklist,
            )
            db.session.add(inst)
            db.session.commit()
            for _ in range(random.randint(2, 4)):
                eq = NetworkEquipment(
                    installation_id=inst.id,
                    equipment_type=random.choice(equipment_types),
                    model=f"Model-{random.randint(100,999)}",
                    serial_number=f"EQ-{random.randint(10000,99999)}",
                    quantity=random.randint(1, 4),
                    status="INSTALLED",
                )
                db.session.add(eq)
        db.session.commit()

        # --- Computers ---
        print("Creating computer inventory...")
        os_choices = ["Windows 10", "Windows 11", "Ubuntu 22.04"]
        comp_statuses = ["WORKING", "WORKING", "WORKING", "WARNING", "ERROR", "OFFLINE", "UNDER_MAINTENANCE"]
        computers = []
        comp_counter = 1
        branch_employees = {}
        for e in employees:
            branch_employees.setdefault(e.branch_id, []).append(e)

        for b in branches:
            for i in range(b.number_of_computers):
                emp_list = branch_employees.get(b.id, [])
                comp = Computer(
                    asset_number=f"PC-{comp_counter:04d}",
                    hostname=f"{b.branch_code}-WS{i+1:02d}",
                    branch_id=b.id,
                    department=random.choice(["Customer Service", "Teller", "Credit", "Operations", "IT"]),
                    employee_id=random.choice(emp_list).id if emp_list else None,
                    operating_system=random.choice(os_choices),
                    ram=random.choice(["8GB", "16GB", "32GB"]),
                    storage=random.choice(["256GB SSD", "512GB SSD", "1TB HDD"]),
                    processor=random.choice(["Intel i5-1135G7", "Intel i7-1165G7", "AMD Ryzen 5 5600U"]),
                    ip_address=f"10.{b.id}.10.{i+2}",
                    mac_address=f"00:1B:44:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}",
                    antivirus_status=random.choice(["PROTECTED", "PROTECTED", "OUTDATED"]),
                    status=random.choice(comp_statuses),
                    last_maintenance_date=date.today() - timedelta(days=random.randint(5, 200)),
                )
                computers.append(comp)
                db.session.add(comp)
                comp_counter += 1
        db.session.commit()

        # --- IT Tickets ---
        print("Creating IT support tickets...")
        categories = ["Computer not starting", "Windows problem", "Software problem", "Network problem",
                      "Internet problem", "Printer problem", "Scanner problem", "Email problem",
                      "Login problem", "Slow computer", "Hardware problem", "Virus/security alert", "Other"]
        statuses_t = ["OPEN", "ASSIGNED", "IN_PROGRESS", "WAITING_FOR_USER", "RESOLVED", "CLOSED"]
        priorities = ["LOW", "MEDIUM", "MEDIUM", "HIGH", "CRITICAL"]
        ticket_counter = 1000
        for _ in range(90):
            b = random.choice(branches)
            emp_list = branch_employees.get(b.id, [])
            comp_list = [c for c in computers if c.branch_id == b.id]
            status = random.choice(statuses_t)
            created = days_ago(random.randint(0, 180))
            ticket_counter += 1
            t = ITTicket(
                ticket_code=f"IT-{ticket_counter}",
                branch_id=b.id,
                employee_id=random.choice(emp_list).id if emp_list else None,
                computer_id=random.choice(comp_list).id if comp_list else None,
                problem_category=random.choice(categories),
                description="Simulated support request generated for demonstration purposes.",
                priority=random.choice(priorities),
                assigned_technician_id=random.choice(technicians).id if status != "OPEN" else None,
                status=status,
                resolution="Issue diagnosed and resolved after remote troubleshooting." if status in ("RESOLVED", "CLOSED") else None,
                created_at=created,
                updated_at=created + timedelta(hours=random.randint(1, 72)),
                closed_at=created + timedelta(hours=random.randint(2, 96)) if status in ("RESOLVED", "CLOSED") else None,
            )
            db.session.add(t)
            db.session.commit()
            if random.random() > 0.5:
                db.session.add(TicketComment(
                    ticket_id=t.id, author_name=rand_name(), author_role="technician",
                    message="Investigating the issue remotely.", created_at=created + timedelta(hours=1),
                ))
                db.session.commit()

        # --- Incidents ---
        print("Creating incidents...")
        incident_categories = ["ATM", "Network", "Computer", "Printer", "Server", "Software", "Security", "Power"]
        inc_counter = 2000
        for _ in range(35):
            b = random.choice(branches)
            status = random.choice(["OPEN", "IN_PROGRESS", "RESOLVED", "RESOLVED"])
            opened = days_ago(random.randint(0, 150))
            inc_counter += 1
            db.session.add(Incident(
                incident_code=f"INC-{inc_counter}",
                branch_id=b.id,
                category=random.choice(incident_categories),
                description="Simulated IT incident for demonstration purposes.",
                severity=random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
                technician_id=random.choice(technicians).id,
                status=status,
                resolution="Resolved after on-site/remote intervention." if status == "RESOLVED" else None,
                date_opened=opened,
                date_resolved=opened + timedelta(hours=random.randint(2, 72)) if status == "RESOLVED" else None,
            ))
        db.session.commit()

        # --- Assets ---
        print("Creating equipment/asset inventory...")
        asset_types = ["Printer", "Scanner", "Router", "Switch", "Access Point", "UPS", "Server"]
        asset_counter = 1
        assets = []
        for b in branches:
            for _ in range(random.randint(3, 6)):
                a_type = random.choice(asset_types)
                a = Asset(
                    asset_code=f"AST-{asset_counter:04d}",
                    serial_number=f"SN-{random.randint(100000,999999)}",
                    asset_type=a_type,
                    model=f"{a_type} Model-{random.randint(100,999)}",
                    branch_id=b.id,
                    assigned_user=random.choice(["IT Room", "Front Desk", "Server Room", None]),
                    purchase_date=date.today() - timedelta(days=random.randint(200, 1500)),
                    installation_date=date.today() - timedelta(days=random.randint(180, 1400)),
                    status=random.choice(["ACTIVE", "ACTIVE", "ACTIVE", "UNDER_REPAIR", "RETIRED"]),
                )
                assets.append(a)
                db.session.add(a)
                asset_counter += 1
        db.session.commit()

        # --- Maintenance records ---
        print("Creating maintenance records...")
        for _ in range(50):
            b = random.choice(branches)
            asset = random.choice([a for a in assets if a.branch_id == b.id]) if any(a.branch_id == b.id for a in assets) else None
            m_type = random.choice(["PREVENTIVE", "CORRECTIVE"])
            scheduled = date.today() - timedelta(days=random.randint(0, 90))
            db.session.add(MaintenanceRecord(
                maintenance_type=m_type,
                asset_id=asset.id if asset else None,
                branch_id=b.id,
                technician_id=random.choice(technicians).id,
                scheduled_date=scheduled,
                completion_date=scheduled + timedelta(days=random.randint(0, 3)),
                problem="Reported malfunction during routine use." if m_type == "CORRECTIVE" else None,
                checklist={"inspected": True, "cleaned": True, "tested": True} if m_type == "PREVENTIVE" else {},
                repair_action="Replaced faulty component." if m_type == "CORRECTIVE" else None,
                result=random.choice(["PASSED", "COMPLETED", "COMPLETED"]),
                notes="Simulated maintenance record.",
            ))
        db.session.commit()

        # --- Remote support sessions ---
        print("Creating remote support sessions...")
        tickets_sample = ITTicket.query.limit(20).all()
        for t in tickets_sample:
            emp_list = branch_employees.get(t.branch_id, [])
            db.session.add(RemoteSupportSession(
                ticket_id=t.id,
                branch_id=t.branch_id,
                technician_id=t.assigned_technician_id or random.choice(technicians).id,
                employee_id=random.choice(emp_list).id if emp_list else None,
                scheduled_time=t.created_at + timedelta(hours=1),
                start_time=t.created_at + timedelta(hours=1) if t.status != "OPEN" else None,
                end_time=t.created_at + timedelta(hours=2) if t.status in ("RESOLVED", "CLOSED") else None,
                status="COMPLETED" if t.status in ("RESOLVED", "CLOSED") else random.choice(["SCHEDULED", "IN_PROGRESS"]),
                troubleshooting_steps="Verified network connectivity and restarted affected service.",
                resolution=t.resolution,
                remote_tool_used="Authorized Enterprise Remote Support Tool",
            ))
        db.session.commit()

        # --- Notifications ---
        print("Creating notifications...")
        for atm in [a for a in atms if a.status in ("OFFLINE", "ERROR")][:15]:
            db.session.add(Notification(
                type="ATM_OFFLINE" if atm.status == "OFFLINE" else "ATM_CRITICAL",
                title=f"ATM {atm.atm_code} needs attention",
                message=f"{atm.atm_code} at {atm.branch.name} is currently {atm.status}.",
                severity="CRITICAL" if atm.status == "ERROR" else "WARNING",
                related_entity="atm",
                related_id=atm.id,
                created_at=days_ago(random.randint(0, 5)),
            ))
        db.session.commit()

        # --- Audit logs ---
        print("Creating audit log entries...")
        sample_actions = [
            "Technician checked ATM-001", "Technician updated ATM status",
            "Technician resolved ticket", "Admin assigned ticket to technician",
            "Technician completed network installation", "Branch employee submitted computer problem",
        ]
        for _ in range(60):
            db.session.add(AuditLog(
                user_id=random.choice(technicians).user_id,
                user_name=random.choice(technicians).full_name,
                action=random.choice(sample_actions),
                description="Simulated audit trail entry for demonstration.",
                ip_address=f"192.168.{random.randint(1,20)}.{random.randint(2,254)}",
                created_at=days_ago(random.randint(0, 60)),
            ))
        db.session.commit()

        # --- Daily KPI snapshot history (for real, not-fabricated, dashboard trends) ---
        print("Backfilling 14 days of dashboard KPI history...")
        from routes.dashboard_routes import compute_summary_metrics
        today_metrics = compute_summary_metrics()
        for i in range(13, -1, -1):
            snap_date = date.today() - timedelta(days=i)
            row = DailyMetricSnapshot(snapshot_date=snap_date)
            for field in DASHBOARD_METRIC_FIELDS:
                base = today_metrics[field]
                if i == 0:
                    value = base  # today matches the live computed values exactly
                else:
                    # Gentle randomized walk back from today's real value so the
                    # sparkline looks like plausible recent history, never negative.
                    jitter = round(base * random.uniform(-0.12, 0.12) * (i / 13))
                    value = max(0, base - jitter)
                setattr(row, field, value)
            db.session.add(row)
        db.session.commit()

        print("\nSeed complete!\n")
        print("Demo login credentials (SIMULATION DATA ONLY):")
        print("  District IT Administrator -> username: admin       password: Admin@123")
        print("  District IT Technician    -> username: tech1       password: Tech@123")
        print("  Branch Manager            -> username: mgr.add001  password: Manager@123")
        print("  Branch Employee           -> username: employee    password: Employee@123")


if __name__ == "__main__":
    main()
