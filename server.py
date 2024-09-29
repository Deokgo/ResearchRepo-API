from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate #install this module in your terminal
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from models import Account


app = Flask(__name__)
CORS(app)

#database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Papasa01!@localhost:5432/Research_Data_Integration_System'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

#created by Nicole Cabansag (Sept. 29, 2024)
#added table models to import db schema to the db through the following codes
#run this to your terminal before running the following codes
#export FLASK_APP=server.py
#flask db init
#flask db migrate -m "Initial migration."
#flask db upgrade
#if you want to delete all the migrations, use this: rm -rf migrations/

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

@app.route('/login', methods=['POST']) #created Nicole Cabansag (Sept. 29, 2024)
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

            #compare plain passwords
            if user.user_pw == password:
                #login successful
                return jsonify({
                    "message": "Login successful",
                    "user_id": user.user_id,
                    "role": user.role.role_name
                }), 200
            else:
                return jsonify({"message": "Invalid password"}), 401

        except:
            return jsonify({"message": "User not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
