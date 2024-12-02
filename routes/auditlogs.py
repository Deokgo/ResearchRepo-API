# created by Nicole Cabansag

from flask import Blueprint, jsonify
from sqlalchemy import func, desc, nulls_last, extract
import pandas as pd
from models import  Account, AuditTrail, Role, db
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity

auditlogs = Blueprint('auditlogs', __name__)

# For fetching the overall audit logs
@auditlogs.route('/fetch_logs', methods=['GET'])
@auditlogs.route('/fetch_logs/<int:hours>', methods=['GET'])
@jwt_required()
def fetch_logs(hours=None):
    # Perform the SQLAlchemy query
    query = (
        db.session.query(Account, AuditTrail, Role)
        .join(AuditTrail, Account.user_id == AuditTrail.user_id)
        .join(Role, Account.role_id == Role.role_id)
        .order_by(desc(AuditTrail.change_datetime))
    )

    if hours:
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(AuditTrail.change_datetime >= time_threshold)

    # Fetch the results
    results = query.all()

    # Convert the results into a JSON-friendly format
    logs = []
    for account, audit_trail, role in results:
        logs.append({
            "audit_log": audit_trail.audit_id,
            "email": account.email,
            "operation": audit_trail.operation,
            "table_name": audit_trail.table_name,
            "record_id": audit_trail.record_id if audit_trail.record_id is not None else 'N/A',
            "changed_datetime": audit_trail.change_datetime,
            "action_desc": audit_trail.action_desc,
            "role_name": role.role_name
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

    # Convert the result into a list of operations
    operations = [op[0] for op in distinct_operations]  # Extract the first element of each tuple

    return jsonify({"operations": operations})

# For filtering purposes (operations)
@auditlogs.route('/fetch_roles', methods=['GET'])
@jwt_required()
def fetch_roles():
    # Perform the SQLAlchemy query to get distinct operations
    distinct_operations = (
        db.session.query(Role.role_name)
        .distinct()
        .all()
    )

    # Convert the result into a list of operations
    operations = [op[0] for op in distinct_operations]  # Extract the first element of each tuple

    return jsonify({"roles": operations})

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