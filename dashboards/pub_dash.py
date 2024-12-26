# created by Jelly Mallari

from dash import Dash, html, dcc,dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from wordcloud import WordCloud

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

class PublicationDash:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/publication/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.palette_dict = {
            'MITL': 'red',
            'ETYCB': 'yellow',
            'CCIS': 'green',
            'CAS': 'blue',
            'CHS': 'orange'
        }
        # Get default values
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        self.create_layout()
        self.set_callbacks()

    def create_layout(self):
        """
        Create the layout of the dashboard.
        """

        college = html.Div(
            [
                dbc.Label("Select College:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        status = html.Div(
            [
                dbc.Label("Select Status:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="status",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('status')],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        slider = html.Div(
            [
                dbc.Label("Select Years:", style={"color": "#08397C"}),
                dcc.RangeSlider(
                    min=db_manager.get_min_value('year'), 
                    max=db_manager.get_max_value('year'), 
                    step=1, 
                    id="years",
                    marks=None,
                    tooltip={"placement": "bottom", "always_visible": True},
                    value=[db_manager.get_min_value('year'), db_manager.get_max_value('year')],
                    className="p-0",
                ),
            ],
            className="mb-4",
        )

        button = html.Div(
            [
                dbc.Button("Reset", color="primary", id="reset_button"),
            ],
            className="d-grid gap-2",
        )

        controls = dbc.Card(
            [
                html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),
                college, status, slider, button
            ],
            body=True,
            style={"border": "2px solid #0A438F", "display": "flex", "flexDirection": "column"}
        )

        all_sdgs = [f'SDG {i}' for i in range(1, 18)]

        # Sample DataFrame for testing
        df = db_manager.get_all_data()  # Fetch all data
        sdg_series = df['sdg'].str.split('; ').explode()

        # Step 2: Drop duplicates to get distinct SDG values
        distinct_sdg_df = pd.DataFrame(sdg_series.drop_duplicates().reset_index(drop=True), columns=['sdg'])
        distinct_sdg_values = distinct_sdg_df['sdg'].tolist()  # Convert distinct SDG column to list

        
        # Split 'concatenated_keywords' by semicolon and strip leading/trailing spaces
        keywords_series = df['concatenated_keywords'].str.split(';').explode().str.strip()

        # Get the count of each keyword after splitting and trimming
        keywords_count = keywords_series.value_counts().reset_index()

        # Rename the columns to 'Keyword' and 'Count'
        keywords_count.columns = ['Keyword', 'Count']

        sorted_keywords_count = keywords_count.sort_values(by='Count', ascending=False).reset_index(drop=True)





        # Insert into the main_dash layout
        main_dash = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H5("Choose SDG:", style={"color": "#08397C"}),
                        dcc.Dropdown(
                            id='sdg-dropdown',
                            options=[
                                {'label': sdg, 'value': sdg, 'disabled': sdg not in distinct_sdg_values}
                                for sdg in all_sdgs
                            ],
                            multi=True,
                            placeholder="Select SDGs",
                            value=distinct_sdg_values,
                            style={'width': '100%', "border": "1px solid #0A438F"}
                        )
                    ])])]),
            dbc.Row([
                dbc.Col([
                    dcc.Graph(id="keyword-wordcloud",style={"transform": "scale(1)", "transform-origin": "0 0"}),
                    html.H4("Research Conferences", style={'textAlign': 'left', 'margin-bottom': '10px'}),
                    dash_table.DataTable(
                        id='research-table',
                        columns=[],
                        data=[],
                        style_table={'overflowX': 'inherit'},
                        style_cell={'textAlign': 'left','whiteSpace': 'normal',    # Allows text to wrap naturally
                                    'wordWrap': 'break-word',  # Breaks long words and wraps them to the next line
                                    'wordBreak': 'break-word', # Forces a break in words if necessary
                                    'maxWidth': '200px',       # Optional: Sets the maximum width for the cell
                                    'overflow': 'hidden'},      
                        page_size=3
                    )
                ], width=8, style={"border": "2px solid #0A438F", "padding": "10px", "margin-bottom": "10px"}),
                dbc.Col([
                    dcc.Graph(id='author-sdg-graph'),
                    dcc.Graph(id='upload_publish_area_chart')
                ], width=4, style={"border": "2px solid #0A438F", "padding": "10px", "margin-bottom": "10px"})
            ], style={"margin": "10px"}),
        ], fluid=True)

        self.dash_app.layout = html.Div([
                dbc.Container(
                    [
                        dbc.Row([
                            dbc.Col([
                                main_dash
                            ], width=10,style={"transform": "scale(1)", "transform-origin": "0 0"}),
                            dbc.Col(controls, width=2),
                           
                        ]),
                        dcc.Interval(
                            id='interval-component',
                            interval=60 * 1000,  # Update every 1 minute (optional)
                            n_intervals=0
                        )
                    ],
                    fluid=True,
                    className="dbc dbc-ag-grid",
                    style={"overflow": "hidden"}
                )
            ], style={"padding": "20px"})


    def create_display_card(self, title, value):
        """
        Create a display card for showing metrics.
        """
        return html.Div([
            dbc.Col(html.Div([
                html.H5(title, style={'textAlign': 'center'}),
                html.H2(value, style={'textAlign': 'center'})
            ], style={
                            "border": "2px solid #0A438F",  # Change color as needed
                            "borderRadius": "10px",          # Adjust the roundness
                            "padding": "10px",               # Add some padding inside the card
                            "margin": "5px"                  # Space between columns
                        }))
        ])



    def get_conference_data(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Fetch filtered data from the database using DatabaseManager or the appropriate method
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)

        # Check if sdg_dropdown_value is provided for additional filtering
        if sdg_dropdown_value and len(sdg_dropdown_value) > 0:
            # If sdg_dropdown_value is not empty, filter the dataframe based on SDGs
            df = df[df['sdg'].apply(lambda x: any(sdg in x.split('; ') for sdg in sdg_dropdown_value))]
        else:
            # If sdg_dropdown_value is empty, skip the SDG filtering
            print("No SDGs selected, returning data filtered only by college, status, and years.")

        # Exclude rows where 'conference_title' is 'No conference title'
        df = df[df['conference_title'] != 'No Conference Title']

        # Aggregation of SDGs and counting the number of titles per conference
        result = df.groupby('conference_title').agg(
            aggregated_sdg=pd.NamedAgg(column='sdg', aggfunc=lambda x: ', '.join(set([sdg for sublist in x.str.split('; ') for sdg in sublist]))),
            number_of_titles=pd.NamedAgg(column='title', aggfunc='count')
        ).reset_index()

        # Sort by 'number_of_titles' in descending order (change to ascending=True if needed)
        result = result.sort_values(by='number_of_titles', ascending=False).reset_index(drop=True)

        # Rename columns for better readability
        result = result.rename(columns={
            'conference_title': 'Conference Title',
            'aggregated_sdg': 'SDGs Presented',
            'number_of_titles': 'Number of Published Papers'
        })

        return result



    def create_publication_bar_chart(self, selected_colleges, selected_status, selected_years,sdg_dropdown_value):  # Modified by Nicole Cabansag
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:  # Handle case where no data is returned
            return go.Figure()  # Return an empty figure
        
        # Check if sdg_dropdown_value is provided for additional filtering
        if sdg_dropdown_value and len(sdg_dropdown_value) > 0:
            # If sdg_dropdown_value is not empty, filter the dataframe based on SDGs
            df = df[df['sdg'].apply(lambda x: any(sdg in x.split('; ') for sdg in sdg_dropdown_value))]
        else:
            # If sdg_dropdown_value is empty, skip the SDG filtering
            print("No SDGs selected, returning data filtered only by college, status, and years.")

        # The dataframe `df` is now filtered by the selected colleges, status, years, and (if selected) SDGs

        # Group by College, Scopus, and Journal
        grouped_df = df.groupby([ 'scopus', 'journal']).size().reset_index(name='Count')
        # Concatenate Scopus and Journal values for display
        grouped_df['Scopus & Format'] = grouped_df['scopus'] + ' (' + grouped_df['journal'] + ')'

        # Create the bar chart
        fig_bar = px.bar(
            grouped_df,
            x='journal',
            y='Count',
            color='scopus',  # Color by Scopus and Format
            labels={'Count': 'Number of Research Papers'},
            barmode='group',
            title='Scopus vs. Non-Scopus'
        )

        fig_bar.update_layout(
            xaxis_title='College',
            yaxis_title='Number of Research Papers',
            xaxis_tickangle=0,  # Rotate x-axis labels for better readability
            template='plotly_white',  # Use a white background template
            margin=dict(l=0, r=0, t=30, b=0),  # Adjust margins
            height=350,  # Set the height of the figure
            showlegend=True,
            legend=dict(
            orientation="h",  # Horizontal orientation
            yanchor="top",  # Anchor to the bottom
            y=-0.2,           # Position below the plot area
            xanchor="center",  # Center anchor
            x=0.5              # Center position
            )
        )

        return fig_bar
    

    def get_uploaded_and_published_counts(self, selected_colleges, selected_status, selected_years,sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)

        # Check if sdg_dropdown_value is provided for additional filtering
        if sdg_dropdown_value and len(sdg_dropdown_value) > 0:
            # If sdg_dropdown_value is not empty, filter the dataframe based on SDGs
            df = df[df['sdg'].apply(lambda x: any(sdg in x.split('; ') for sdg in sdg_dropdown_value))]
        else:
            # If sdg_dropdown_value is empty, skip the SDG filtering
            print("No SDGs selected, returning data filtered only by college, status, and years.")

        # The dataframe `df` is now filtered by the selected colleges, status, years, and (if selected) SDGs
        # Count occurrences of each year and published_year
        year_counts = df['year'].value_counts().reset_index()
        year_counts.columns = ['year', 'year_count']  # Rename columns

        published_year_counts = df['published_year'].value_counts().reset_index()
        published_year_counts.columns = ['published_year', 'published_year_count']  # Rename columns

        # Merge the counts into a single DataFrame
        combined_counts = pd.merge(year_counts, published_year_counts, how='outer', left_on='year', right_on='published_year')

        # Fill NaN values with 0 for count columns
        combined_counts.fillna(0, inplace=True)

        
        return combined_counts


    def create_area_chart(self, selected_colleges, selected_status, selected_years,sdg_dropdown_value):
        """
        Creates a histogram for uploaded and published papers per year.
        """
        # Get the counts
        counts_df = self.get_uploaded_and_published_counts(selected_colleges, selected_status, selected_years,sdg_dropdown_value)

        # Create the histogram chart
        fig = go.Figure()

        # Add histogram for uploaded counts
        fig.add_trace(go.Bar(
            x=counts_df['year'],  # Year
            y=counts_df['year_count'],  # Uploaded count
            name='Uploaded Papers',
            opacity=0.6,  # Set transparency
            marker=dict(color='rgba(0, 100, 80, 0.6)'),  # Customize color
        ))

        # Add histogram for published counts
        fig.add_trace(go.Line(
            x=counts_df['year'],  # Year
            y=counts_df['published_year_count'],  # Published count
            name='Published Papers',
            opacity=0.6,  # Set transparency
            marker=dict(color='rgba(100, 0, 80, 0.6)'),  # Customize color
        ))

        # Update layout
        fig.update_layout(
            title='Published Papers Per Year',
            xaxis_title='Year',
            yaxis_title='Count of Papers',
            xaxis_tickangle=0,
            template='plotly_white',
            height=400,
            showlegend=True,
            legend=dict(
            orientation="h",  # Horizontal orientation
            yanchor="top",  # Anchor to the bottom
            y=-0.2,           # Position below the plot area
            xanchor="center",  # Center anchor
            x=0.5)  # Show the legend for better readability
        )

        return fig
    
    def update_bar_graph(self, selected_colleges, selected_status, selected_years,sdg_dropdown_value):  # Modified by Nicole Cabansag
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:  # Handle case where no data is returned
            return go.Figure()  # Return an empty figure
        
        # Check if sdg_dropdown_value is provided for additional filtering
        if sdg_dropdown_value and len(sdg_dropdown_value) > 0:
            # If sdg_dropdown_value is not empty, filter the dataframe based on SDGs
            df = df[df['sdg'].apply(lambda x: any(sdg in x.split('; ') for sdg in sdg_dropdown_value))]
        else:
            # If sdg_dropdown_value is empty, skip the SDG filtering
            print("No SDGs selected, returning data filtered only by college, status, and years.")

        # The dataframe `df` is now filtered by the selected colleges, status, years, and (if selected) SDGs
        
        df['author_count'] = df['concatenated_authors'].apply(lambda x: len(x.split(';')))
        
        # Step 2: Group by 'published_year' and sum the 'author_count'
        author_count_per_year = df.groupby('published_year')['author_count'].sum().reset_index()
        
        # Add a row for 2024 to the 'author_count_per_year' if it's missing
        if 2024 not in author_count_per_year['published_year'].values:
            author_count_per_year = pd.concat([
                author_count_per_year, 
                pd.DataFrame({'published_year': [2024], 'author_count': [0]})
            ], ignore_index=True)
        
        # Group by 'year' for uploaded data
        author_count_per_year1 = df.groupby('year')['author_count'].sum().reset_index()
    
        
        # Merge both dataframes so that we can overlay them on the same plot
        # We assume 'published_year' and 'year' are related but different contexts
        combined_df = pd.merge(author_count_per_year, author_count_per_year1, how='outer', left_on='published_year', right_on='year', suffixes=('_published', '_uploaded'))
        
        # Create the bar chart with overlay
        fig = go.Figure()

        # Add the "published_year" trace
        fig.add_trace(
            go.Line(
                x=combined_df['published_year'],
                y=combined_df['author_count_published'],
                name='Published Papers',
                marker_color='blue',  # Customize the color for published data
                opacity=0.6  # Make it slightly transparent to see overlapping bars
            )
        )
        
        # Add the "year" trace
        fig.add_trace(
            go.Bar(
                x=combined_df['published_year'],
                y=combined_df['author_count_uploaded'],
                name='Uploaded Papers',
                marker_color='orange',  # Customize the color for uploaded data
                opacity=0.6  # Make it slightly transparent
            )
        )
        
        # Update layout with better readability
        fig.update_layout(
            barmode='overlay',  # Overlay both bars on top of each other
            xaxis_title='Year',
            yaxis_title='Number of Authors',
            title='Contributors per Year ',
            xaxis_tickangle=0,  # Rotate x-axis labels for better readability
            template='plotly_white',  # Use a white background template
            margin=dict(l=0, r=0, t=30, b=0),  # Adjust margins
            height=350,  # Set the height of the figure
            showlegend=True,
            legend=dict(
                orientation="h",  # Horizontal orientation
                yanchor="top",  # Anchor to the bottom
                y=-0.2,  # Position below the plot area
                xanchor="center",  # Center anchor
                x=0.5  # Center position
            )
        )
        
        return fig
    
    def generate_wordcloud(self, selected_colleges, selected_status, selected_years,sdg_dropdown_value):
        # Fetch filtered data
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)


        # Check if sdg_dropdown_value is provided for additional filtering
        if sdg_dropdown_value and len(sdg_dropdown_value) > 0:
            # If sdg_dropdown_value is not empty, filter the dataframe based on SDGs
            df = df[df['sdg'].apply(lambda x: any(sdg in x.split('; ') for sdg in sdg_dropdown_value))]
        else:
            # If sdg_dropdown_value is empty, skip the SDG filtering
            print("No SDGs selected, returning data filtered only by college, status, and years.")

        # The dataframe `df` is now filtered by the selected colleges, status, years, and (if selected) SDGs

        df['concatenated_keywords'] = df['concatenated_keywords'].str.replace(' ', '_', regex=False)
        
        # Step 1: Split 'concatenated_keywords' by semicolon and strip leading/trailing spaces
        keywords_series = df['concatenated_keywords'].str.split(';').explode().str.strip()

        # Step 2: Get the count of each keyword after splitting and trimming
        keywords_count = keywords_series.value_counts().reset_index()

        # Step 3: Rename columns to 'Keyword' and 'Count'
        keywords_count.columns = ['Keyword', 'Count']

        # Step 4: Create a string of keywords for the word cloud
        keywords_string = ' '.join(keywords_count['Keyword'].values)
        
        # Step 5: Generate the word cloud
        wordcloud = WordCloud(
            background_color='white',
            width=1600,
            height=1000,
            max_words=200
        ).generate(keywords_string)

        # Step 6: Convert the word cloud image to a plotly figure
        fig = go.Figure()

        # Convert wordcloud to image array and plot it using plotly
        fig.add_trace(go.Image(z=wordcloud.to_array()))

        # Update layout
        fig.update_layout(
            title="Keywords Word Cloud",
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False)
        )

        return fig
    

    
    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """
        # Callback for reset button
        @self.dash_app.callback(
            [Output('college', 'value'),
            Output('status', 'value'),
            Output('years', 'value')],
            [Input('reset_button', 'n_clicks')],
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        
        @self.dash_app.callback(
            [Output('research-table', 'data'), Output('research-table', 'columns')],
            [Input('interval-component', 'n_intervals'),
            Input('college', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('sdg-dropdown', 'value')]
        )
        def update_research_table(n_intervals, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
            # Handle empty selections by using default values when inputs are empty
            if not selected_colleges:
                selected_colleges = db_manager.get_unique_values('college_id')
            if not selected_status:
                selected_status = db_manager.get_unique_values('status')
            if not selected_years or len(selected_years) != 2:
                selected_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
            if not sdg_dropdown_value:
                sdg_dropdown_value = None

            # Get the filtered conference data
            conference_counts = self.get_conference_data(selected_colleges, selected_status, selected_years, sdg_dropdown_value)

            # Format the data for the DataTable
            data = conference_counts.to_dict('records')  # Convert DataFrame to a list of dictionaries
            columns = [{'name': col, 'id': col} for col in conference_counts.columns]  # Columns format

            return data, columns
        
        @self.dash_app.callback(
            Output('publication_format_bar_plot', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_publication_bar_chart(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_publication_bar_chart(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('author-sdg-graph', 'figure'),
            [Input('college', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('sdg-dropdown', 'value')]  # Adjust these inputs based on the actual component IDs
        )
        def update_graph(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.update_bar_graph(selected_colleges, selected_status, selected_years,sdg_dropdown_value) 
        
        @self.dash_app.callback(
            Output('upload_publish_area_chart', 'figure'),  # Add an ID for your area chart
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value'),
            Input('sdg-dropdown', 'value')]
        )
        def update_upload_publish_area_chart(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_area_chart(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        
        # Callback for the Word Cloud
        @self.dash_app.callback(
            Output('keyword-wordcloud', 'figure'),
            [Input('college', 'value'),
             Input('status', 'value'),
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_wordcloud(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.generate_wordcloud(selected_colleges, selected_status, selected_years, sdg_dropdown_value)