# created by Jelly Mallari

from dash import Dash, html, dcc,dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

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
        self.create_layout()
        self.set_callbacks()

    def create_layout(self):
        """
        Create the layout of the dashboard.
        """

        college = html.Div(
            [
                dbc.Label("Select College:"),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=db_manager.get_unique_values('college_id'),
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        status = html.Div(
            [
                dbc.Label("Select Status:"),
                dbc.Checklist(
                    id="status",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('status')],
                    value=db_manager.get_unique_values('status'),
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        slider = html.Div(
            [
                dbc.Label("Select Years"),
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
                html.H4("Filters", style={"margin": "10px 0px"}),
                college, status, slider, button
            ],
            body=True,
            style={"height": "95vh", "display": "flex", "flexDirection": "column"}
        )


        main_dash = dbc.Container([     
            dbc.Row([  # Row for the world map chart
                dbc.Col([
                    dcc.Graph(
                        id='conference_loc',style={"transform": "scale(0.9)", "transform-origin": "0 0" }),
                    dash_table.DataTable(
                        id='research-table',
                        columns=[],  # Columns will be populated by callback
                        data=[],  # Data will be populated by callback
                        style_table={'overflowX': 'auto'},
                        style_cell={'textAlign': 'left'},
                        page_size=6  # Set page size for better UX
                )],
                    width=8,
                    style={
                        "height": "auto", 
                        "border": "2px solid #007bff",  # Add a solid border
                        "borderRadius": "5px"         # Optional: Add rounded corners               # Optional: Add some padding
                    }
                ),
                dbc.Col([
                    dcc.Graph(id='publication_format_bar_plot'),
                    dcc.Graph(id='upload_publish_area_chart')],
                    width=4,
                    style={
                        "height": "auto", 
                        "border": "2px solid #007bff",  # Add a solid border
                        "borderRadius": "5px",           # Optional: Add rounded corners               # Optional: Add some padding
                    }
                )
            ], style={"margin": "10px"}),
            dbc.Row([  # Row for the world map chart
                dbc.Col(
                    
                width=8)
            ], style={"margin": "10px"})
        ], fluid=True)

        self.dash_app.layout = html.Div([
                dbc.Container(
                    [
                        dbc.Row([
                            dbc.Col([
                                main_dash
                            ], width=10,style={"transform": "scale(0.9)", "transform-origin": "0 0"}),
                            dbc.Col(controls, width=2)
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
                            "border": "1px solid #007bff",  # Change color as needed
                            "borderRadius": "10px",          # Adjust the roundness
                            "padding": "10px",               # Add some padding inside the card
                            "margin": "5px"                  # Space between columns
                        }))
        ])
    
    def update_world_map(self, selected_colleges, selected_status, selected_years): # Added by Nicole Cabansag
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df = df.dropna()
        if 'country' not in df.columns or df['country'].isnull().all():
            return dcc.Graph()  

        country_counts = df.groupby('country').size().reset_index(name='Count')

        fig = px.choropleth(
            country_counts,
            locations='country',  
            locationmode='country names', 
            color='Count',  
            hover_name='country',  
            color_continuous_scale=px.colors.sequential.Plasma,  
            title="International Conference Distribution"
        )

        fig.update_layout(
            width=900,  # Adjust width
            height= 500,  # Adjust height
            geo=dict(showframe=False, showcoastlines=False),
            title_x=0.5
        )


        return fig
    
    
    def get_conference_data(self, selected_colleges, selected_status, selected_years):
        """
        Fetches the conference data and counts the number of journals and proceedings by country.
        Orders the result by the total count (journal count + proceeding count) in descending order.
        Includes SDG in the final output but does not include it in the journal and proceeding counts.
        """
        # Fetch data from the database using DatabaseManager or the appropriate method
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)

        # Filter relevant columns and drop rows with null values in 'country' and 'date_published' columns
        conference_df = df[['country', 'sdg', 'journal', 'date_published']].dropna(subset=['country', 'date_published'])

        # Group by country and aggregate data
        conference_counts = (
            conference_df.groupby('country', as_index=False)
            .agg(
                SDG_List=('sdg', lambda x: ', '.join(sorted(set(x)))),
                Journal_Count=('journal', lambda x: (x.str.lower() == 'journal').sum()),  # Count entries marked as 'journal'
                Proceeding_Count=('journal', lambda x: (x.str.lower() == 'proceeding').sum())  # Count entries marked as 'proceeding'
                  # List unique SDGs, sorted alphabetically
            )
        )

        # Calculate total count as a new column
        conference_counts['Total_Count'] = conference_counts['Journal_Count'] + conference_counts['Proceeding_Count']

        # Order by total count in descending order
        conference_counts = conference_counts.sort_values(by='Total_Count', ascending=False)

        # Return all columns except 'Total_Count'
        return conference_counts.drop(columns=['Total_Count'])



    

    def create_publication_bar_chart(self, selected_colleges, selected_status, selected_years):  # Modified by Nicole Cabansag
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:  # Handle case where no data is returned
            return go.Figure()  # Return an empty figure

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
    

    def get_uploaded_and_published_counts(self, selected_colleges, selected_status, selected_years):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        # Count occurrences of each year and published_year
        year_counts = df['year'].value_counts().reset_index()
        year_counts.columns = ['year', 'year_count']  # Rename columns

        published_year_counts = df['published_year'].value_counts().reset_index()
        published_year_counts.columns = ['published_year', 'published_year_count']  # Rename columns

        # Merge the counts into a single DataFrame
        combined_counts = pd.merge(year_counts, published_year_counts, how='outer', left_on='year', right_on='published_year')

        # Fill NaN values with 0 for count columns
        combined_counts.fillna(0, inplace=True)

        # Display the combined DataFrame
        print(combined_counts.columns.tolist)
        
        return combined_counts


    

    def create_area_chart(self, selected_colleges, selected_status, selected_years):
        """
        Creates a histogram for uploaded and published papers per year.
        """
        # Get the counts
        counts_df = self.get_uploaded_and_published_counts(selected_colleges, selected_status, selected_years)
        print(counts_df)

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


    
    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """
        @self.dash_app.callback(
        [Output('college', 'value'),
         Output('status', 'value'),
         Output('years', 'value')],
        [Input('reset_button', 'n_clicks')],
        prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return db_manager.get_unique_values('college_id'), db_manager.get_unique_values('status'), [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        
        @self.dash_app.callback(
            [Output('research-table', 'data'), Output('research-table', 'columns')],
            [Input('interval-component', 'n_intervals'),
             Input('college', 'value'),
            Input('status', 'value'),
            Input('years', 'value')]
        )
        def update_research_table(n_intervals,selected_colleges, selected_status, selected_years):
            # Get the grouped conference data
            conference_counts = self.get_conference_data(selected_colleges, selected_status, selected_years)

            # Format the data for the DataTable
            data = conference_counts.to_dict('records')  # Convert DataFrame to a list of dictionaries
            columns = [{'name': col, 'id': col} for col in conference_counts.columns]  # Columns format

            return data, columns
        
        @self.dash_app.callback(
            Output('conference_loc', 'figure'),  # Changed 'children' to 'figure'
            [Input('college', 'value'),
            Input('status', 'value'),
            Input('years', 'value')]
        )
        def update_map(selected_colleges, selected_status, selected_years):
            return self.update_world_map(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('publication_format_bar_plot', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value')]
        )
        def update_publication_bar_chart(selected_colleges, selected_status, selected_years):
            return self.create_publication_bar_chart(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('upload_publish_area_chart', 'figure'),  # Add an ID for your area chart
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value')]
        )
        def update_upload_publish_area_chart(selected_colleges, selected_status, selected_years):
            return self.create_area_chart(selected_colleges, selected_status, selected_years)


        
