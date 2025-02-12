# created by Nicole Cabansag

from flask import Blueprint, jsonify
from sqlalchemy import func, desc, nulls_last, extract
import pandas as pd
from models import  Account, AuditTrail, Role, db
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity
from pytz import timezone

auditlogs = Blueprint('auditlogs', __name__)

# For fetching the overall audit logs
@auditlogs.route('/fetch_logs', methods=['GET'])
@auditlogs.route('/fetch_logs/<int:hours>', methods=['GET'])
@jwt_required()
def fetch_logs(hours=None):
    # Perform the SQLAlchemy query
    query = (
        db.session.query(AuditTrail)
        .order_by(desc(AuditTrail.change_datetime))
    )

    if hours:
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(AuditTrail.change_datetime >= time_threshold)

    # Fetch the results
    results = query.all()

    # Convert the results into a JSON-friendly format
    logs = []
    for audit_trail in results:
        logs.append({
            "audit_log": audit_trail.audit_id,
            "email": audit_trail.email,  # Now directly from audit_trail
            "operation": audit_trail.operation,
            "table_name": audit_trail.table_name,
            "record_id": audit_trail.record_id if audit_trail.record_id is not None else 'N/A',
            "changed_datetime": audit_trail.change_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            "action_desc": audit_trail.action_desc,
            "role": audit_trail.role  # Now directly from audit_trail
        })

    return jsonify({"logs": logs})

# For filtering purposes (operations)
@auditlogs.route('/fetch_operations', methods=['GET'])
@jwt_required()
def fetch_operations():
    # Perform the SQLAlchemy query to get distinct operations
    distinct_operations = (
        db.session.query(AuditTrail.operation)
        .distinct()
        .all()
    )

    operations = [op[0] for op in distinct_operations]
    return jsonify({"operations": operations})

# For filtering purposes (operations)
@auditlogs.route('/fetch_roles', methods=['GET'])
@jwt_required()
def fetch_roles():
    # Get distinct roles directly from audit_trail
    distinct_roles = (
        db.session.query(AuditTrail.role)
        .distinct()
        .all()
    )

    roles = [role[0] for role in distinct_roles]
    return jsonify({"roles": roles})

@auditlogs.route('/fetch_date_range', methods=['GET'])
@jwt_required()
def fetch_date_range():
    result = db.session.query(
        func.min(extract('year', AuditTrail.change_datetime)).label('min_year'),
        func.max(extract('year', AuditTrail.change_datetime)).label('max_year')
    ).one()

    # Prepare the result as a JSON object
    response = {
        "min_year": int(result.min_year) if result.min_year else None,  # Convert to int if not None
        "max_year": int(result.max_year) if result.max_year else None   # Convert to int if not None
    }

    # Return as a JSON response
    return jsonify({"date_range": response})