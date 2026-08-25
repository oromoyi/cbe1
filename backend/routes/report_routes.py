import csv
import io
from datetime import datetime

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from models import db, ATM, NetworkInstallation, Computer, ITTicket, Technician, Branch
from utils import roles_required

bp = Blueprint("reports", __name__, url_prefix="/api/reports")


def _atm_report_data():
    total = ATM.query.count()
    online = ATM.query.filter_by(status="ONLINE").count()
    offline = ATM.query.filter_by(status="OFFLINE").count()
    error = ATM.query.filter_by(status="ERROR").count()
    maintenance = ATM.query.filter_by(status="MAINTENANCE").count()
    return {"Total ATMs": total, "Online": online, "Offline": offline, "Error": error, "Maintenance": maintenance}


def _network_report_data():
    installed = NetworkInstallation.query.filter_by(status="COMPLETED").count()
    pending = NetworkInstallation.query.filter(
        NetworkInstallation.status.in_(["PLANNED", "IN_PROGRESS", "TESTING"])
    ).count()
    failed = NetworkInstallation.query.filter_by(status="FAILED").count()
    return {
        "Installed Branches (Completed)": installed,
        "Pending Installations": pending,
        "Failed Installations": failed,
        "Completed Installations": installed,
    }


def _computer_report_data():
    return {
        "Working Computers": Computer.query.filter_by(status="WORKING").count(),
        "Error Computers": Computer.query.filter_by(status="ERROR").count(),
        "Offline Computers": Computer.query.filter_by(status="OFFLINE").count(),
        "Under Maintenance": Computer.query.filter_by(status="UNDER_MAINTENANCE").count(),
    }


def _ticket_report_data():
    return {
        "Open Tickets": ITTicket.query.filter_by(status="OPEN").count(),
        "Assigned Tickets": ITTicket.query.filter_by(status="ASSIGNED").count(),
        "In Progress Tickets": ITTicket.query.filter_by(status="IN_PROGRESS").count(),
        "Resolved Tickets": ITTicket.query.filter(ITTicket.status.in_(["RESOLVED", "CLOSED"])).count(),
        "Critical Tickets": ITTicket.query.filter_by(priority="CRITICAL").count(),
    }


def _technician_report_data():
    rows = []
    for t in Technician.query.all():
        assigned = ITTicket.query.filter_by(assigned_technician_id=t.id).count()
        completed = ITTicket.query.filter_by(assigned_technician_id=t.id).filter(
            ITTicket.status.in_(["RESOLVED", "CLOSED"])
        ).all()
        workload = ITTicket.query.filter_by(assigned_technician_id=t.id).filter(
            ITTicket.status.notin_(["RESOLVED", "CLOSED"])
        ).count()
        durations = []
        for tk in completed:
            if tk.created_at and tk.closed_at:
                durations.append((tk.closed_at - tk.created_at).total_seconds() / 3600.0)
        avg_hours = round(sum(durations) / len(durations), 1) if durations else 0
        rows.append({
            "Technician": t.full_name,
            "Assigned Tickets": assigned,
            "Completed Tickets": len(completed),
            "Avg Resolution (hrs)": avg_hours,
            "Current Workload": workload,
        })
    return rows


REPORT_BUILDERS = {
    "atm": _atm_report_data,
    "network": _network_report_data,
    "computer": _computer_report_data,
    "ticket": _ticket_report_data,
    "technician": _technician_report_data,
}


@bp.get("/<report_type>")
@jwt_required()
def get_report(report_type):
    builder = REPORT_BUILDERS.get(report_type)
    if not builder:
        return jsonify({"error": "Unknown report type"}), 404
    return jsonify({"report_type": report_type, "generated_at": datetime.utcnow().isoformat(), "data": builder()})


@bp.get("/<report_type>/export")
@jwt_required()
def export_report(report_type):
    fmt = request.args.get("format", "csv").lower()
    builder = REPORT_BUILDERS.get(report_type)
    if not builder:
        return jsonify({"error": "Unknown report type"}), 404
    data = builder()

    # Normalize data to list-of-rows
    if isinstance(data, dict):
        rows = [{"Metric": k, "Value": v} for k, v in data.items()]
    else:
        rows = data
    headers = list(rows[0].keys()) if rows else ["Metric", "Value"]

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        mem = io.BytesIO(buf.getvalue().encode("utf-8"))
        return send_file(
            mem, mimetype="text/csv", as_attachment=True,
            download_name=f"{report_type}_report.csv",
        )

    if fmt == "excel":
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = f"{report_type}_report"[:31]
        ws.append(headers)
        for r in rows:
            ws.append([r.get(h) for h in headers])
        for col in ws.columns:
            max_len = max((len(str(c.value)) for c in col if c.value is not None), default=10)
            ws.column_dimensions[col[0].column_letter].width = max(12, min(40, max_len + 2))
        mem = io.BytesIO()
        wb.save(mem)
        mem.seek(0)
        return send_file(
            mem, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True, download_name=f"{report_type}_report.xlsx",
        )

    if fmt == "pdf":
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm

        mem = io.BytesIO()
        doc = SimpleDocTemplate(mem, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
        styles = getSampleStyleSheet()
        elements = [
            Paragraph(f"CBE District IT — {report_type.title()} Report", styles["Title"]),
            Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
            Spacer(1, 0.5 * cm),
        ]
        table_data = [headers] + [[str(r.get(h, "")) for h in headers] for r in rows]
        table = Table(table_data, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A1D6E")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3F8")]),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)
        doc.build(elements)
        mem.seek(0)
        return send_file(
            mem, mimetype="application/pdf", as_attachment=True,
            download_name=f"{report_type}_report.pdf",
        )

    return jsonify({"error": "Unsupported format. Use csv, excel, or pdf."}), 400
