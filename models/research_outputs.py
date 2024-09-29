from . import db

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
