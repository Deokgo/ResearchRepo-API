from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_migrate import Migrate #install this module in your terminal

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

#college Table
class College(db.Model):
    __tablename__ = 'college'
    college_id = db.Column(db.String(6), primary_key=True)
    college_name = db.Column(db.String(50))

#program Table
class Program(db.Model):
    __tablename__ = 'program'
    program_id = db.Column(db.String(5), primary_key=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_name = db.Column(db.String(50))
    college = db.relationship('College', backref=db.backref('programs', lazy=True))

#roles Table
class Role(db.Model):
    __tablename__ = 'roles'
    role_id = db.Column(db.String(2), primary_key=True)
    role_name = db.Column(db.String(50))

#SDG Table
class SDG(db.Model):
    __tablename__ = 'sdg'
    sdg_id = db.Column(db.String(6), primary_key=True)
    sdg_desc = db.Column(db.String(50))

#account table
class Account(db.Model):
    __tablename__ = 'account'
    user_id = db.Column(db.String(15), primary_key=True)
    live_account = db.Column(db.String(80))
    user_pw = db.Column(db.String(64))  #store the hashed password
    acc_status = db.Column(db.String(20), server_default=text("'ACTIVATED'"))  #default value in the database
    role_id = db.Column(db.String(2), db.ForeignKey('roles.role_id'))
    role = db.relationship('Role', backref=db.backref('accounts', lazy=True))


#researchers Table
class Researcher(db.Model):
    __tablename__ = 'researchers'
    researcher_id = db.Column(db.String(15), db.ForeignKey('account.user_id'), primary_key=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_id = db.Column(db.String(5), db.ForeignKey('program.program_id'))
    first_name = db.Column(db.String(30))
    middle_name = db.Column(db.String(2))
    last_name = db.Column(db.String(30))
    suffix = db.Column(db.String(10))

#research Outputs Table
class ResearchOutput(db.Model):
    __tablename__ = 'research_outputs'
    research_id = db.Column(db.String(15), primary_key=True)
    college_id = db.Column(db.String(6), db.ForeignKey('college.college_id'))
    program_id = db.Column(db.String(5), db.ForeignKey('program.program_id'))
    title = db.Column(db.String(100))
    abstract = db.Column(db.String(1000))
    sdg_id = db.Column(db.String(6), db.ForeignKey('sdg.sdg_id'))
    keywords = db.Column(db.String(50))
    pdf = db.Column(db.String(100))
    date_submitted = db.Column(db.TIMESTAMP)
    date_modified = db.Column(db.TIMESTAMP)
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))

#research Output Authors Table
class ResearchOutputAuthor(db.Model):
    __tablename__ = 'research_output_authors'
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'), primary_key=True)
    author_id = db.Column(db.String(15), db.ForeignKey('account.user_id'), primary_key=True)
    author_order = db.Column(db.Integer)

#audit Trail Table
class AuditTrail(db.Model):
    __tablename__ = 'audit_trail'
    audit_id = db.Column(db.String(16), primary_key=True)
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))
    table_name = db.Column(db.String(50))
    record_id = db.Column(db.String(16))
    operation = db.Column(db.String(50))
    change_datetime = db.Column(db.TIMESTAMP)
    action_desc = db.Column(db.String(100))

#publisher Table
class Publisher(db.Model):
    __tablename__ = 'publisher'
    publisher_id = db.Column(db.String(16), primary_key=True)
    publisher_name = db.Column(db.String(70))

#conference Table
class Conference(db.Model):
    __tablename__ = 'conference'
    conference_id = db.Column(db.String(15), primary_key=True)
    conference_title = db.Column(db.String(100))
    location = db.Column(db.String(100))
    country = db.Column(db.String(30))
    conference_date = db.Column(db.Date)
    date_added = db.Column(db.TIMESTAMP)
    date_modified = db.Column(db.TIMESTAMP)

#publication Table
class Publication(db.Model):
    __tablename__ = 'publications'
    publication_id = db.Column(db.String(16), primary_key=True)
    research_id = db.Column(db.String(15), db.ForeignKey('research_outputs.research_id'))
    publication_format = db.Column(db.String(20))
    conference_id = db.Column(db.String(15), db.ForeignKey('conference.conference_id'))
    publisher_id = db.Column(db.String(16), db.ForeignKey('publisher.publisher_id'))
    publication_name = db.Column(db.String(100))
    status = db.Column(db.String(20))
    date_submitted = db.Column(db.TIMESTAMP)
    date_modified = db.Column(db.TIMESTAMP)
    user_id = db.Column(db.String(15), db.ForeignKey('account.user_id'))

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
