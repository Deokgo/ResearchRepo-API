from services.database_manager import DatabaseManager  
from services.user_engagement import UserEngagementManager
from config import Config

# Initialize the database manager
db_manager = DatabaseManager(Config.SQLALCHEMY_DATABASE_URI)
view_manager = UserEngagementManager(Config.SQLALCHEMY_DATABASE_URI)