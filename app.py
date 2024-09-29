from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db  # Import the db object from the models
from routes import api  # Import the blueprint for routes

app = Flask(__name__)
CORS(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Papasa01!@localhost:5432/Research_Data_Integration_System'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Register the blueprint for routes
app.register_blueprint(api)

if __name__ == "__main__":
    app.run(debug=True)
