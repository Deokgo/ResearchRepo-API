import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, desc
from models import College, Program, ResearchOutput, Publication, Status, Conference, ResearchOutputAuthor, Account, UserProfile, Keywords, SDG, Category, ResearchCategory
from services.data_fetcher import ResearchDataFetcher
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk import pos_tag

class DatabaseManager:
    def __init__(self, database_uri):
        self.engine = create_engine(database_uri)
        self.Session = sessionmaker(bind=self.engine)
        self.df = None
        self.stop_words = set(stopwords.words('english'))

        self.get_all_data()

    def get_data_from_model(self,model):
        fetcher = ResearchDataFetcher(model)
        data = fetcher.get_data_from_model()
        return data

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
                        UserProfile.last_name, ', ',  # Surname first
                        func.substring(UserProfile.first_name, 1, 1), '. ',  # First name initial
                        func.coalesce(func.substring(UserProfile.middle_name, 1, 1) + '.', '') 
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

            # Subquery to concatenate SDG
            sdg_subquery = session.query(
                SDG.research_id,
                func.string_agg(SDG.sdg, '; ').label('concatenated_sdg')
            ).group_by(SDG.research_id).subquery()

            # Subquery to get the research areas for each publication
            area_subquery = session.query(
                ResearchCategory.research_id,
                func.string_agg(
                    func.concat(
                        Category.category_name), '; '
                ).label('concatenated_areas')
            ).join(Category, ResearchCategory.category_id == Category.category_id) \
            .group_by(ResearchCategory.research_id).subquery()

            # Main query
            query = session.query(
                College.college_id,
                Program.program_id,
                Program.program_name,
                sdg_subquery.c.concatenated_sdg,
                ResearchOutput.research_id,
                ResearchOutput.title,
                ResearchOutput.date_approved,
                ResearchOutput.research_type,
                authors_subquery.c.concatenated_authors,
                keywords_subquery.c.concatenated_keywords,
                Publication.publication_name,
                Publication.journal,
                Publication.scopus,
                Publication.date_published,
                Conference.conference_venue,
                Conference.conference_title,
                Conference.conference_date,
                latest_status_subquery.c.status,
                area_subquery.c.concatenated_areas,
                ResearchOutput.abstract
            ).join(College, ResearchOutput.college_id == College.college_id) \
            .join(Program, ResearchOutput.program_id == Program.program_id) \
            .outerjoin(Publication, ResearchOutput.research_id == Publication.research_id) \
            .outerjoin(Conference, Publication.conference_id == Conference.conference_id) \
            .outerjoin(latest_status_subquery, (Publication.publication_id == latest_status_subquery.c.publication_id) & (latest_status_subquery.c.rn == 1)) \
            .outerjoin(authors_subquery, ResearchOutput.research_id == authors_subquery.c.research_id) \
            .outerjoin(keywords_subquery, ResearchOutput.research_id == keywords_subquery.c.research_id) \
            .outerjoin(sdg_subquery, ResearchOutput.research_id ==  sdg_subquery.c.research_id) \
            .outerjoin(area_subquery, ResearchOutput.research_id ==  area_subquery.c.research_id) \
            .distinct()

            result = query.all()

            # Formatting results into a list of dictionaries with safe handling for missing data
            data = [{
                'research_id': row.research_id if pd.notnull(row.research_id) else 'Unknown',
                'college_id': row.college_id if pd.notnull(row.college_id) else 'Unknown',
                'program_name': row.program_name if pd.notnull(row.program_name) else 'N/A',
                'program_id': row.program_id if pd.notnull(row.program_id) else None,
                'title': row.title if pd.notnull(row.title) else 'Untitled',
                'year': row.date_approved.year if pd.notnull(row.date_approved) else None,
                'date_approved': row.date_approved,
                'concatenated_authors': row.concatenated_authors if pd.notnull(row.concatenated_authors) else 'Unknown Authors',
                'concatenated_keywords': row.concatenated_keywords if pd.notnull(row.concatenated_keywords) else 'No Keywords',
                'sdg': row.concatenated_sdg if pd.notnull(row.concatenated_sdg) else 'Not Specified',
                'research_type': row.research_type if pd.notnull(row.research_type) else 'Unknown Type',
                'journal': row.journal if pd.notnull(row.journal) else 'unpublished',
                'scopus': row.scopus if pd.notnull(row.scopus) else 'N/A',
                'date_published': row.date_published,
                'published_year': int(row.date_published.year) if pd.notnull(row.date_published) else None,
                'conference_venue': row.conference_venue if pd.notnull(row.conference_venue) else 'Unknown Venue',
                'conference_title': row.conference_title if pd.notnull(row.conference_title) else 'No Conference Title',
                'conference_date': row.conference_date,
                'status': row.status if pd.notnull(row.status) else "READY",
                'country': row.conference_venue.split(",")[-1].strip() if pd.notnull(row.conference_venue) else 'Unknown Country',
                'abstract': row.abstract if pd.notnull(row.abstract) else '',
                'concatenated_areas': row.concatenated_areas if pd.notnull(row.concatenated_areas) else 'No Research Areas',
            } for row in result]

            # Convert the list of dictionaries to a DataFrame
            self.df = pd.DataFrame(data)
            # Combine the title and concatenated_keywords columns
            self.df['combined'] = self.df['title'].astype(str) + ' ' + self.df['concatenated_keywords'].astype(str) + ' ' + self.df['abstract'].astype(str)

            # Apply the function to extract top nouns
            self.df['top_nouns'] = self.df['combined'].apply(lambda x: self.top_nouns(x, 10))

        finally:
            session.close()

        return self.df
    
    def get_college_colors(self):
        session = self.Session()
        
        query = session.query(College.college_id, College.color_code)
        colleges = query.all()

        # Convert the list of tuples into a dictionary
        college_colors = {college_id: color_code for college_id, color_code in colleges}
    
        return college_colors

    def get_unique_values(self, column_name):
        if self.df is not None and column_name in self.df.columns:
            unique_values = self.df[column_name].dropna().unique()
            if len(unique_values) == 0:
                print(f"Warning: Column '{column_name}' exists but contains no values.")
            return unique_values
        else:
            return []  # Return an empty list if the column doesn't exist or has no values

    def get_unique_values_by(self, column_name, condition_column=None, condition_value=None):
        if self.df is not None and column_name in self.df.columns:
            if condition_column and condition_column in self.df.columns:
                # Apply the condition
                filtered_df = self.df[self.df[condition_column] == condition_value]
                
                # Debug: print filtered dataframe
                print(f"Filtered DataFrame for {condition_column} == {condition_value}:\n")
                
                # Get unique values from the filtered data
                unique_values = filtered_df[column_name].dropna().unique()
                print(f'unique values: {unique_values}')
            else:
                # No condition, get all unique values
                unique_values = self.df[column_name].dropna().unique()

            if len(unique_values) == 0:
                print(f"Warning: Column '{column_name}' contains no unique values.")
            
            return unique_values
        else:
            print(f"Error: Column '{column_name}' does not exist in the DataFrame.")
            return []


    def get_columns(self):
        return self.df.columns.tolist() if self.df is not None else []

    def filter_data(self, column_name1, value1, column_name2=None, value2=None, invert=False):
        if self.df is not None:
            if column_name1 in self.df.columns and (column_name2 is None or column_name2 in self.df.columns):
                if column_name2 is None:
                    # Single column filter
                    if invert:
                        return self.df[self.df[column_name1] != value1]
                    else:
                        return self.df[self.df[column_name1] == value1]
                else:
                    # Two-column filter
                    if invert:
                        return self.df[(self.df[column_name1] != value1) | (self.df[column_name2] != value2)]
                    else:
                        return self.df[(self.df[column_name1] == value1) & (self.df[column_name2] == value2)]
            else:
                missing_column = column_name1 if column_name1 not in self.df.columns else column_name2
                raise ValueError(f"Column '{missing_column}' does not exist in the DataFrame.")
        else:
            raise ValueError("Data not loaded. Please call 'get_all_data()' first.")

    def filter_data_by_list(self, column_name, values, invert=False):
        if self.df is not None:
            if column_name in self.df.columns:
                if invert:
                    return self.df[~self.df[column_name].isin(values)]
                else:
                    return self.df[self.df[column_name].isin(values)]
            else:
                raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")
        else:
            raise ValueError("Data not loaded. Please call 'get_all_data()' first.")

    def get_min_value(self, column_name):
        if self.df is not None and column_name in self.df.columns:
            return self.df[column_name].min()
        else:
            raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")

    def get_max_value(self, column_name):
        if self.df is not None and column_name in self.df.columns:
            return self.df[column_name].max()
        else:
            raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")

    def get_filtered_data(self, selected_colleges, selected_status, selected_years):
        if self.df is not None:
            filtered_df = self.df[
                (self.df['college_id'].isin(selected_colleges)) & 
                (self.df['status'].isin(selected_status)) & 
                (self.df['year'].between(selected_years[0], selected_years[1]))
            ]
            return filtered_df
        else:
            raise ValueError("Data not loaded. Please call 'get_all_data()' first.")
    
    def get_filtered_data_bycollege(self, selected_program, selected_status, selected_years):
        if self.df is not None:
            filtered_df = self.df[
                (self.df['program_id'].isin(selected_program)) & 
                (self.df['status'].isin(selected_status)) & 
                (self.df['year'].between(selected_years[0], selected_years[1]))
            ]
            return filtered_df
        else:
            raise ValueError("Data not loaded. Please call 'get_all_data()' first.")
        
    def top_nouns(self,text, top_n=10):
        # Remove punctuation using regex
        text = re.sub(r'[^\w\s]', '', text)  # This removes punctuation (e.g. % / \ < > etc.)

        # Tokenize the text
        words = word_tokenize(text.lower())  # Tokenize and convert to lowercase

        # Remove stopwords and words with less than 3 letters
        words = [word for word in words if word not in self.stop_words and len(word) >= 3]

        # Get part-of-speech tags for the words
        pos_tags = pos_tag(words)

        # Filter for nouns (NN, NNS, NNP, NNPS)
        nouns = [word for word, tag in pos_tags if tag in ['NN', 'NNS', 'NNP', 'NNPS']]

        # Count the occurrences of the nouns
        word_counts = Counter(nouns)
        top_n_words = word_counts.most_common(top_n)

        # Convert the top_n_words to a nested list format [noun, count]
        top_n_words_nested = [word for word, _ in top_n_words]

        return top_n_words_nested # Return the top n most common nouns as a nested list
    

    def get_words(self,selected_colleges, selected_status, selected_years):
        if self.df is not None:
            df_copy = self.df.copy()

            
            filtered_df = df_copy[
                (df_copy['college_id'].isin(selected_colleges)) & 
                (df_copy['status'].isin(selected_status)) & 
                (df_copy['year'].between(selected_years[0], selected_years[1]))
            ]
            return filtered_df
        else:
            raise ValueError("Data not loaded. Please call 'get_all_data()' first.")

        
