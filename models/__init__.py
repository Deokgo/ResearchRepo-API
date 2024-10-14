from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from .account import Account
from .audit_trail import AuditTrail
from .college import College
from .conference import Conference
from .program import Program
from .publication import Publication
from .user_profile import UserProfile
from .research_outputs import ResearchOutput
from .research_output_author import ResearchOutputAuthor
from .roles import Role
from .status import Status
from .keywords import Keywords
from .panels import Panel
from .sdg import SDG