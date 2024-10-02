from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db  # Import the db object from the models
from routes import api  # Import the blueprint for routes
import os

app = Flask(__name__)
CORS(app)

# Database Configuration
app.config['SECRET_KEY']=os.environ.get('SECRET_KEY', "b'\x06F\x83X\xe1\x94\xd6\x1f\x89bU\xf5\xbfd\xa4\xda\xb2T\xf7\x0b{\xc0\xaf\xc2'")
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Papasa01!@localhost:5432/Research_Data_Integration_System'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Register the blueprint for routes
app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
