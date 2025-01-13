import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, desc
from models import College, Program, ResearchOutput, Publication, Status, Conference, ResearchOutputAuthor, Account, UserProfile, Keywords, SDG, ResearchArea, ResearchOutputArea, ResearchTypes, PublicationFormat, UserEngagement
from services.data_fetcher import ResearchDataFetcher
from collections import Counter
import re

class UserEngagementManager:
    def __init__(self, database_uri):
        self.engine = create_engine(database_uri)
        self.Session = sessionmaker(bind=self.engine)
        self.df = None

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
                ResearchOutputArea.research_id,
                func.string_agg(
                    func.concat(
                        ResearchArea.research_area_name), '; '
                ).label('concatenated_areas')
            ).join(ResearchArea, ResearchOutputArea.research_area_id == ResearchArea.research_area_id) \
            .group_by(ResearchOutputArea.research_id).subquery()

            agg_user_engage = session.query(
                UserEngagement.research_id,
                func.date(UserEngagement.timestamp).label('date'),  # Ensure 'date' is explicitly labeled
                func.sum(UserEngagement.view).label('total_views'),
                func.count(func.distinct(UserEngagement.user_id)).label('total_unique_views'),
                func.sum(UserEngagement.download).label('total_downloads')
            ).group_by(
                UserEngagement.research_id,
                func.date(UserEngagement.timestamp)
            ).subquery()


            # Main query
            query = session.query(
                agg_user_engage.c.research_id,
                agg_user_engage.c.date,  # Correctly accessing subquery columns
                agg_user_engage.c.total_views,
                agg_user_engage.c.total_unique_views,
                agg_user_engage.c.total_downloads,
                College.college_id,
                Program.program_id,
                Program.program_name,
                sdg_subquery.c.concatenated_sdg,
                ResearchOutput.title,
                ResearchOutput.school_year,
                ResearchOutput.term,
                ResearchTypes.research_type_name,
                authors_subquery.c.concatenated_authors,
                keywords_subquery.c.concatenated_keywords,
                Publication.publication_name,
                PublicationFormat.pub_format_name,
                Publication.date_published,
                latest_status_subquery.c.status,
                area_subquery.c.concatenated_areas,
            ).join(College, ResearchOutput.college_id == College.college_id) \
                .join(Program, ResearchOutput.program_id == Program.program_id) \
                .outerjoin(agg_user_engage, agg_user_engage.c.research_id == ResearchOutput.research_id) \
                .outerjoin(Publication, ResearchOutput.research_id == Publication.research_id) \
                .outerjoin(latest_status_subquery, (Publication.publication_id == latest_status_subquery.c.publication_id) & (latest_status_subquery.c.rn == 1)) \
                .outerjoin(authors_subquery, ResearchOutput.research_id == authors_subquery.c.research_id) \
                .outerjoin(keywords_subquery, ResearchOutput.research_id == keywords_subquery.c.research_id) \
                .outerjoin(sdg_subquery, ResearchOutput.research_id == sdg_subquery.c.research_id) \
                .outerjoin(area_subquery, ResearchOutput.research_id == area_subquery.c.research_id) \
                .outerjoin(ResearchTypes, ResearchOutput.research_type_id == ResearchTypes.research_type_id) \
                .outerjoin(PublicationFormat, Publication.pub_format_id == PublicationFormat.pub_format_id) \
                .distinct()

            result = query.all()

            # Formatting results into a list of dictionaries with safe handling for missing data
            data = [{
                'research_id': row.research_id if pd.notnull(row.research_id) else 'Unknown',
                'date': row.date if pd.notnull(row.date) else None,
                'total_views': row.total_views if pd.notnull(row.total_views) else 0,
                'total_unique_views': row.total_unique_views if pd.notnull(row.total_unique_views) else 0,
                'total_downloads': row.total_downloads if pd.notnull(row.total_downloads) else 0,
                'college_id': row.college_id if pd.notnull(row.college_id) else 'Unknown',
                'program_id': row.program_id if pd.notnull(row.program_id) else None,
                'program_name': row.program_name if pd.notnull(row.program_name) else 'N/A',
                'concatenated_sdg': row.concatenated_sdg if pd.notnull(row.concatenated_sdg) else 'Not Specified',
                'title': row.title if pd.notnull(row.title) else 'Untitled',
                'year': row.school_year if pd.notnull(row.school_year) else None,
                'term': row.term if pd.notnull(row.term) else None,
                'research_type_name': row.research_type_name if pd.notnull(row.research_type_name) else 'Unknown Type',
                'concatenated_authors': row.concatenated_authors if pd.notnull(row.concatenated_authors) else 'Unknown Authors',
                'concatenated_keywords': row.concatenated_keywords if pd.notnull(row.concatenated_keywords) else 'No Keywords',
                'publication_name': row.publication_name if pd.notnull(row.publication_name) else 'unpublished',
                'pub_format_name': row.pub_format_name if pd.notnull(row.pub_format_name) else 'unpublished',
                'date_published': row.date_published,
                'published_year': int(row.date_published.year) if pd.notnull(row.date_published) else None,
                'status': row.status if pd.notnull(row.status) else "READY",
                'concatenated_areas': row.concatenated_areas if pd.notnull(row.concatenated_areas) else 'No Research Areas',
            } for row in result]


            # Convert the list of dictionaries to a DataFrame
            self.df = pd.DataFrame(data)
            # Assuming self.df is your DataFrame
            self.df = self.df.dropna(subset=['research_id'])  # Drops rows where 'research_id' is NaN or None
            self.df = self.df[self.df['research_id'] != 'Unknown']  # Drops rows where 'research_id' is 'Unknown'

            # Optional: Reset index if needed
            self.df = self.df.reset_index(drop=True)
            print(self.df.columns)

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

    def get_sum_value(self, column_name):
        if self.df is not None:
            if column_name in self.df.columns:
                return self.df[column_name].sum()
            else:
                raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")
        else:
            raise ValueError("DataFrame is not initialized.")
        
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
        
    def get_conversion_rate(self):
        if self.df is not None:
            if 'total_downloads' in self.df.columns and 'total_unique_views' in self.df.columns:
                # Avoid division by zero
                if self.df['total_unique_views'].sum() > 0:
                    # Calculate conversion rate
                    conversion_rate = (self.df['total_downloads'].sum() / self.df['total_unique_views'].sum()) * 100
                    return conversion_rate
                else:
                    return 0.0  
        
    def get_average_views_per_research_id(self):
        if self.df is not None:
            if 'total_views' in self.df.columns and 'research_id' in self.df.columns:
                # Group by 'research_id' and calculate the total views for each ID
                grouped = self.df.groupby('research_id')['total_views'].sum()

                # Calculate the average views per research ID
                average_views = grouped.mean()
                return average_views
            else:
                raise ValueError("DataFrame must contain 'total_views' and 'research_id' columns.")
        else:
            raise ValueError("DataFrame is not initialized.")

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

        
