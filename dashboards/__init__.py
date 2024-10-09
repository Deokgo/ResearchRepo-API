from services.database_manager import DatabaseManager  
from config import Config

# Initialize the database manager
db_manager = DatabaseManager(Config.SQLALCHEMY_DATABASE_URI)