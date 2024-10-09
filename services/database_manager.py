import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, desc
from models import College, Program, ResearchOutput, Publication, Status, Conference, ResearchOutputAuthor, Account, UserProfile, Keywords, db

class DatabaseManager:
    def __init__(self, database_uri):
        self.engine = create_engine(database_uri)
        self.Session = sessionmaker(bind=self.engine)

    def get_all_data(self):
        session = self.Session()
        try:
            # Subquery to get the latest status for each publication
            latest_status_subquery = session.query(
                Status.publication_id,
                Status.status,
                func.row_number().over(
                    partition_by=Status.publication_id,
                    order_by=desc(Status.timestamp)
                ).label('rn')
            ).subquery()

            # Subquery to concatenate authors
            authors_subquery = session.query(
                ResearchOutputAuthor.research_id,
                func.string_agg(
                    func.concat(
                        UserProfile.first_name, ' ',
                        func.coalesce(UserProfile.middle_name + ' ', ''),  # Handle middle name if present
                        UserProfile.last_name,
                        func.coalesce(' ' + UserProfile.suffix, '')  # Handle suffix if present
                    ), '; '
                ).label('concatenated_authors')
            ).join(Account, ResearchOutputAuthor.author_id == Account.user_id) \
            .join(UserProfile, Account.user_id == UserProfile.researcher_id) \
            .group_by(ResearchOutputAuthor.research_id).subquery()

            # Subquery to concatenate keywords
            keywords_subquery = session.query(
                Keywords.research_id,
                func.string_agg(Keywords.keyword, '; ').label('concatenated_keywords')
            ).group_by(Keywords.research_id).subquery()

            # Main query
            query = session.query(
                College.college_id,
                Program.program_name,
                ResearchOutput.sdg,
                ResearchOutput.title,
                ResearchOutput.date_approved,
                authors_subquery.c.concatenated_authors,
                keywords_subquery.c.concatenated_keywords,
                Publication.journal,
                Publication.date_published,
                Conference.conference_venue,
                Conference.conference_title,
                Conference.conference_date,
                latest_status_subquery.c.status
            ).join(College, ResearchOutput.college_id == College.college_id) \
            .join(Program, ResearchOutput.program_id == Program.program_id) \
            .outerjoin(Publication, ResearchOutput.research_id == Publication.research_id) \
            .outerjoin(Conference, Publication.conference_id == Conference.conference_id) \
            .outerjoin(latest_status_subquery, (Publication.publication_id == latest_status_subquery.c.publication_id) & (latest_status_subquery.c.rn == 1)) \
            .outerjoin(authors_subquery, ResearchOutput.research_id == authors_subquery.c.research_id) \
            .outerjoin(keywords_subquery, ResearchOutput.research_id == keywords_subquery.c.research_id) \
            .distinct()

            result = query.all()

            # Formatting results into a list of dictionaries
            data = [{
                'college_id': row.college_id,
                'program_name': row.program_name,
                'sdg': row.sdg,
                'title': row.title,
                'date_approved': row.date_approved,
                'concatenated_authors': row.concatenated_authors,
                'concatenated_keywords': row.concatenated_keywords,
                'journal': row.journal,
                'date_published': row.date_published,
                'conference_venue': row.conference_venue,
                'conference_title': row.conference_title,
                'conference_date': row.conference_date,
                'status': row.status
            } for row in result]

            # Convert the list of dictionaries to a DataFrame
            df = pd.DataFrame(data)

        finally:
            session.close()

        return df
