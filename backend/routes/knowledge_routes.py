from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

bp = Blueprint("knowledge", __name__, url_prefix="/api/knowledge-base")

KB = [
    {
        "id": "computer-no-start",
        "title": "Computer Does Not Start",
        "causes": ["Power problem", "Power cable problem", "Hardware failure", "Operating system failure"],
        "actions": [
            "Check power", "Check cables", "Check hardware indicators",
            "Record diagnostic result", "Escalate if necessary",
        ],
    },
    {
        "id": "computer-no-internet",
        "title": "Computer Has No Internet",
        "causes": [
            "Cable disconnected", "Network adapter disabled", "IP configuration problem",
            "Switch problem", "Network outage",
        ],
        "actions": [
            "Check physical connection", "Check network adapter", "Check IP configuration",
            "Test connectivity", "Check switch connection", "Escalate to network technician",
        ],
    },
    {
        "id": "printer-not-working",
        "title": "Printer Not Working",
        "causes": [
            "Printer offline", "Driver problem", "Network connection",
            "Paper/toner problem", "Print spooler problem",
        ],
        "actions": [
            "Check printer power/network status", "Reinstall or update driver",
            "Verify network connectivity to printer", "Check paper and toner",
            "Restart print spooler service", "Record troubleshooting process and final solution",
        ],
    },
]


@bp.get("")
@jwt_required()
def list_kb():
    return jsonify(KB)
