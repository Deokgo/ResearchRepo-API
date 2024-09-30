from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate #install this module in your terminal
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from werkzeug.security import generate_password_hash, check_password_hash
from models import db
import datetime


app = Flask(__name__)
CORS(app)

#database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Papasa01!@localhost:5432/Research_Data_Integration_System'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
# Initialize the database
db.init_app(app)
migrate = Migrate(app, db)


# function that checks db if existing or not
def check_db(db_name, user, password, host='localhost', port='5432'):
    try:
        # Connect to the default 'postgres' database
        connection = psycopg2.connect(user=user, password=password, host=host, port=port, dbname='postgres')
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()

        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully.")
        else:
            print(f"Database '{db_name}' already exists.")
    except Exception as error:
        print(f"Error while creating database: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()

check_db('Research_Data_Integration_System', 'postgres', 'Papasa01!')

with app.app_context():
    db.create_all()
    print("Tables created successfully.")

#created by Nicole Cabansag, this method is for generating ID (for PK)
def formatting_id(indicator):
    #get the current date in the format YYYYMMDD
    current_date_str = datetime.datetime.now().strftime('%Y%m%d')

    #query the last audit entry for the current date to get the latest audit_id
    if indicator == 'AUD':
        last_audit = AuditTrail.query.filter(AuditTrail.audit_id.like(f'{indicator}-{current_date_str}-%')) \
                                        .order_by(AuditTrail.audit_id.desc()) \
                                        .first()
        
        #determine the next sequence number (XXX)
        if last_audit:
            #extract the last sequence number and increment it by 1
            last_sequence = int(last_audit.audit_id.split('-')[-1])
            next_sequence = f"{last_sequence + 1:03d}"
        else:
            #if no previous audit log exists for today, start with 001
            next_sequence = "001"

    #query the last user entry for the current date to get the latest user_id
    elif indicator == 'US':
        last_user = Account.query.filter(Account.user_id.like(f'{indicator}-{current_date_str}-%')) \
                                        .order_by(Account.user_id.desc()) \
                                        .first()
        #determine the next sequence number (XXX)
        if last_user:
            #extract the last sequence number and increment it by 1
            last_sequence = int(last_user.user_id.split('-')[-1])
            next_sequence = f"{last_sequence + 1:03d}"
        else:
            #if no previous user log exists for today, start with 001
            next_sequence = "001"
    
    
    generated_id = f"{indicator}-{current_date_str}-{next_sequence}"

    return generated_id

#created by Nicole Cabansag, for audit logs
def log_audit_trail(user_id, table_name, record_id, operation, action_desc):
    try:
        audit_id = formatting_id('AUD')

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


########################################################################### APIs FOR ACCOUNT MANAGEMENT MODULE ###########################################################################
from models import Account, Researcher, AuditTrail

#modified by Nicole Cabansag, added comparing hashed values for user_pw
@app.route('/login', methods=['POST']) 
def login():
    data = request.json
    if data:
        live_account = data.get('email')
        password = data.get('password')

        if not live_account or not password:
            return jsonify({"message": "Email and password are required"}), 400

        try:
            #retrieve user from the database
            user = Account.query.filter_by(live_account=live_account).one()

            #compare hashed password with the provided plain password
            if check_password_hash(user.user_pw, password):
                #if login successful...

                #log the successful login in the Audit_Trail
                log_audit_trail(user_id=user.user_id, table_name='Account', record_id=None,
                                operation='LOGIN', action_desc='User logged in')
                
                return jsonify({
                    "message": "Login successful",
                    "user_id": user.user_id,
                    "role": user.role.role_name
                }), 200
            else:
                return jsonify({"message": "Invalid password"}), 401

        except:
            return jsonify({"message": "User not found"}), 404

#created by Nicole Cabansag, for signup API
@app.route('/signup', methods=['POST']) 
def add_user():
    data = request.json

    #ensure all required fields are present
    required_fields = ['firstName', 'lastName', 'email', 'password', 'confirmPassword', 'department', 'program', 'role_id']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"message": f"{field} is required."}), 400
        
    #generate the new user_id with the incremented sequence number
    user_id = formatting_id('US')

    try:
        # Insert data into the Account table
        new_account = Account(
            user_id=user_id,  #assuming email is used as the user_id
            live_account=data['email'],  #mapúa MCL live account
            user_pw=generate_password_hash(data['password']),
            acc_status='ACTIVATED',  #assuming account is actived by default, change as needed
            role_id=data.get('role_id'),  
        )
        db.session.add(new_account)

        #insert data into the Researcher table
        new_researcher = Researcher(
            researcher_id=new_account.user_id,  #use the user_id from Account
            college_id=data['department'],  #department corresponds to college_id
            program_id=data['program'],  #program corresponds to program_id
            first_name=data['firstName'],
            middle_name=data.get('middleName'),  #allowing optional fields
            last_name=data['lastName'],
            suffix=data.get('suffix')  #allowing optional suffix
        )
        db.session.add(new_researcher)

        #commit both operations
        db.session.commit()

        #log the account creation in the Audit_Trail
        log_audit_trail(user_id=new_account.user_id, table_name='Account', record_id=None,
                        operation='CREATE', action_desc='New account created')
        return jsonify({
                    "message": "Signup successful",
                    "user_id": user_id
                }), 200

    except Exception as e:
        db.session.rollback()  #rollback in case of error
        return jsonify({"message": f"Failed to add user: {e}"}), 500

    finally:
        db.session.close()  #close the session


#created by Nicole Cabansag, for retrieving all users API
@app.route('/users', methods=['GET']) 
def get_all_users():
    try:
        researchers = Researcher.query.order_by(Researcher.researcher_id.asc()).all()

        researchers_list = []
        for researcher in researchers:
            researchers_list.append({
                "researcher_id": researcher.researcher_id,
                "college_id": researcher.college_id,
                "program_id": researcher.program_id,
                "first_name": researcher.first_name,
                "middle_name": researcher.middle_name,
                "last_name": researcher.last_name,
                "suffix": researcher.suffix
            })

        #return the list of researchers in JSON format
        return jsonify({"researchers": researchers_list}), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving all users: {str(e)}"}), 404

#created by Nicole Cabansag, for retrieving all user's acc and info by user_id API
@app.route('/users/<user_id>', methods=['GET']) 
def get_user_acc_by_id(user_id):
    try:
        user_acc = Account.query.filter_by(user_id=user_id).one()
        researcher_info = Researcher.query.filter_by(researcher_id=user_id).one()

        #construct the response in JSON format
        return jsonify({
            "account": {
                "user_id": user_acc.user_id,
                "live_account": user_acc.live_account,
                "user_pw": user_acc.user_pw,
                "acc_status": user_acc.acc_status,
                "role": user_acc.role.role_name  
            },
            "researcher": {
                "researcher_id": researcher_info.researcher_id,
                "college_id": researcher_info.college_id,
                "program_id": researcher_info.program_id,
                "first_name": researcher_info.first_name,
                "middle_name": researcher_info.middle_name,
                "last_name": researcher_info.last_name,
                "suffix": researcher_info.suffix
            }
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error retrieving user profile: {str(e)}"}), 404


if __name__ == "__main__":
    app.run(debug=True)
