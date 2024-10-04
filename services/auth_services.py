import datetime
from flask import Blueprint, request, jsonify,current_app
from models import db
import jwt

#created by Nicole Cabansag, this method is for generating ID (for PK)
def formatting_id(indicator, model_class, id_field):
    #get the current date in the format YYYYMMDD
    current_date_str = datetime.datetime.now().strftime('%Y%m%d')

    #query the last entry for the current date to get the latest ID
    last_entry = model_class.query.filter(getattr(model_class, id_field).like(f'{indicator}-{current_date_str}-%')) \
                                  .order_by(getattr(model_class, id_field).desc()) \
                                  .first()

    #determine the next sequence number (XXX)
    if last_entry:
        # Extract the last sequence number and increment it by 1
        last_sequence = int(getattr(last_entry, id_field).split('-')[-1])
        next_sequence = f"{last_sequence + 1:03d}"
    else:
        #if no previous entry exists for today, start with 001
        next_sequence = "001"

    #generate the new ID
    generated_id = f"{indicator}-{current_date_str}-{next_sequence}"

    return generated_id

#created by Nicole Cabansag, for audit logs
def log_audit_trail(user_id, table_name, record_id, operation, action_desc):
    from models.audit_trail import AuditTrail
    try:
        audit_id = formatting_id('AUD', AuditTrail, 'audit_id')

        #create the audit trail entry
        new_audit = AuditTrail(
            audit_id=audit_id,
            user_id=user_id,
            table_name=table_name,
            record_id=record_id,
            operation=operation,
            change_datetime=datetime.datetime.now(),
            action_desc=action_desc
        )

        #add and commit the new audit log
        db.session.add(new_audit)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Error logging audit trail: {e}")


def generate_token(user_id):
    """Generate a JWT token for the user with a 24-hour expiration."""
    # Define the token payload
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)  # Token expiry time
    }

    # Encode the token using the secret key
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token
