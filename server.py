from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate #install this module in your terminal
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


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

from models import Account, Researcher

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

    #ensure data contains both researcher and account information
    data1 = data.get('researcher')
    data2 = data.get('account')

    if not data1 or not data2:
        return jsonify({"message": "Both researcher and account data are required."}), 400

    try:
        #insert data into the Account table
        new_account = Account(
            user_id = data2['user_id'],
            live_account=data2['live_account'],
            user_pw=generate_password_hash(data2['user_pw']),
            acc_status=data2['acc_status'],
            role_id=data2['role_id'],
        )
        db.session.add(new_account)

        #insert data into the Researcher table
        new_researcher = Researcher(
            researcher_id=new_account.user_id,
            college_id=data1['college_id'],
            program_id=data1['program_id'],
            first_name=data1['first_name'],
            middle_name=data1.get('middle_name'),  #used .get() to allow optional fields
            last_name=data1['last_name'],
            suffix=data1.get('suffix')
        )
        db.session.add(new_researcher)


        #commit both operations
        db.session.commit()
        return jsonify({"message": "User added successfully."}), 201

    except Exception as e:
        db.session.rollback()  #rollback in case of error
        return jsonify({"message": f"Failed to add user: {e}"}), 500

    finally:
        db.session.close()  #close the session

if __name__ == "__main__":
    app.run(debug=True)
