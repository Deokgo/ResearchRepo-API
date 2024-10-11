# created by Jelly Mallari

from dash import Dash, html, dcc,dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px

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
                dbc.Col(
                    dcc.Graph(id='conference_loc'),
                    width=9,
                    style={
                        "height": "auto", 
                        "border": "2px solid #007bff",  # Add a solid border
                        "borderRadius": "5px",           # Optional: Add rounded corners               # Optional: Add some padding
                    }
                )
            ], style={"margin": "10px"}),
            dbc.Row([  # Row for the world map chart
                dbc.Col(
                    dash_table.DataTable(
                    id='research-table',
                    columns=[],  # Columns will be populated by callback
                    data=[],  # Data will be populated by callback
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    page_size=6  # Set page size for better UX
                ),
                width=8
                
                )
            ], style={"margin": "10px"})
        ], fluid=True)


        """sub_dash = dbc.Container([
                dbc.Row([
                dbc.Col(dcc.Graph(id='scopus_bar_plot', width=6, style={"height": "auto", "overflow": "hidden", "border": "1px solid #ddd"})),
                dbc.Col(dcc.Graph(id='publication_format_bar_plot', width=6, style={"height": "auto", "overflow": "hidden", "border": "1px solid #ddd"})),
            ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(0.9)", "transform-origin": "0 0"})  # Adjust the scale as needed"""
        
        self.dash_app.layout = html.Div([
                dbc.Container(
                    [
                        dbc.Row([
                            dbc.Col(controls, width=2),
                            dbc.Col([
                                main_dash,
                                #sub_dash
                            ], width=10,style={"transform": "scale(0.9)", "transform-origin": "0 0"}),
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
        print(df.columns.tolist)
        thailand_data = df[df['country'] == 'Thailand'][['country', 'journal']]
        print(thailand_data)
        print(len(thailand_data))

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
    
    
    def get_conference_data(self):
        """
        Fetches the conference data and counts the number of journals and proceedings by country.
        Orders the result by the total count (journal count + proceeding count) in descending order.
        """
        # Fetch data from the database using DatabaseManager or the appropriate method
        df = db_manager.get_all_data()

        # Filter relevant columns and drop rows with null values in 'country' and 'date_published' columns
        conference_df = df[['country', 'journal', 'date_published']].dropna(subset=['country', 'date_published'])

        # Group by country and count journals and proceedings
        conference_counts = (
            conference_df.groupby('country', as_index=False)
            .agg(
                journal_count=('journal', lambda x: (x == 'journal').sum()),  # Count unique journals
                proceeding_count=('journal', lambda x: (x == 'proceeding').sum())  # Count occurrences of 'Proceedings'
            )
        )

        # Calculate total count as a new column
        conference_counts['Total Count'] = conference_counts['journal_count'] + conference_counts['proceeding_count']

        # Rename columns
        conference_counts.columns = ['Country', 'Journal Count', 'Proceeding Count', 'Total Count']

        # Order by total count in descending order
        conference_counts = conference_counts.sort_values(by='Total Count', ascending=False)

        return conference_counts

    
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
            [Input('interval-component', 'n_intervals')]
        )
        def update_research_table(n_intervals):
            # Get the grouped conference data
            conference_counts = self.get_conference_data()

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

        
