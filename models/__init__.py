from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from .account import Account
from .audit_trail import AuditTrail
from .college import College
from .conference import Conference
from .program import Program
from .publication import Publication
from .publisher import Publisher
from .researchers import Researcher
from .research_outputs import ResearchOutput
from .research_output_author import ResearchOutputAuthor
from .roles import Role
from .sdg import SDG