from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from urllib.parse import parse_qs, urlparse
from . import db_manager

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

class SDG_Map:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/sdg/map/', 
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

        
        sidebar_size = 2
        all_sdgs = [f'SDG {i}' for i in range(1, 18)]

        # Sample DataFrame for testing
        df = db_manager.get_all_data()  # Fetch all data
        sdg_series = df['sdg'].str.split('; ').explode()

        # Step 2: Drop duplicates to get distinct SDG values
        distinct_sdg_df = pd.DataFrame(sdg_series.drop_duplicates().reset_index(drop=True), columns=['sdg'])
        distinct_sdg_values = distinct_sdg_df['sdg'].tolist()  


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

        sdgs = html.Div(
            [
                dbc.Label("Select SDG:", style={"color": "#08397C"}),
                dcc.Dropdown(
                    id="sdg-dropdown",
                    options=[
                        # Add the "ALL" option at the top of the dropdown list
                        {"label": "ALL", "value": "ALL", "disabled": False},
                        *[
                            {
                                "label": sdg,
                                "value": sdg,
                                "disabled": sdg not in distinct_sdg_values,
                            }
                            for sdg in sorted(
                                all_sdgs,
                                key=lambda x: int(x.split()[1])  # Extract the numeric part and sort
                            )
                        ]
                    ],
                    multi=False,
                    placeholder="Select SDGs",
                    value="ALL",  # Default to "ALL"
                    style={
                        "width": "100%",
                        "border": "1px solid #0A438F",
                    },
                )
            ]
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

        sdg_container = html.Div(
            [
                html.Div(id="sdg-cards", style={"display": "flex", "flex-wrap": "wrap", "justify-content": "center", "gap": "10px"})
            ]
        )

        # Insert into main_dash layout
        main_dash = dbc.Container([
            dbc.Row([
                dbc.Col([dcc.Graph(id="sdg_college"), sdg_container], width=8, style={"gap": "10px", "display": "flex", "flex-wrap": "wrap"}),
                dbc.Col([dcc.Graph(id="sdg_donut"), dcc.Graph(id="sdg_box")], width=4, style={"gap": "10px", "display": "flex", "flexDirection": "column"}),
            ]),  # Add the research table here
        ], fluid=True)


        self.dash_app.layout = html.Div(
            [
                dbc.Container(
                    [
                        dbc.Row(
                            [
                                # Sidebar column
                                dbc.Col(
                                    [
                                        html.H2("sample",id="chosen-sdg"),
                                        html.H3("Sample Subtitle Here",id="chosen-sdg-label"),
                                        html.Div("This dashboard tracks key metrics like research output, regional performance, and emerging technologies to inform decision-making and accelerate progress towards a more sustainable and innovative future.", style={"color": "black"}),
                                        college,
                                        status,
                                        slider
                                    ],
                                    width=sidebar_size,
                                    style={
                                        "background": "#e8ceb0",
                                        "height": "100vh",  # Full-height sidebar
                                        "position": "fixed",  # Fix it on the left
                                        "top": 0,
                                        "left": 0,
                                        "padding": "20px",
                                    },
                                ),
                                # Main content column
                                dbc.Col(
                                    [
                                        sdgs,
                                        dcc.Graph(id="sdg_map"),
                                        dbc.Row([
                                            dbc.Col([
                                                dcc.Graph(id="sdg-trend"),
                                                dcc.Graph(id="sdg-per-college")
                                            ],width=6),
                                            dbc.Col(
                                                dcc.Graph(id="word-cloud"),
                                                width=6
                                            )
                                        ])
                                        
                                    ],
                                    width={"size": 10, "offset": sidebar_size},  # Offset for the sidebar
                                ),
                            ]
                        )
                    ],
                    fluid=True,
                    className="dbc dbc-ag-grid",
                    style={"overflow": "visible"},  # Ensure dropdown can expand
                )
            ],
            style={"padding": "20px"},
        )


    def create_sdg_map(self,selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()
        print(df_copy.columns)

        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_df = df_copy.explode('sdg')

        # Prepare the SDG map dataframe with 'SDG' and 'Conference Venue'
        sdg_map = sdg_df[['sdg', 'conference_venue']].dropna()

        # Extract country from 'Conference Venue' by splitting the string
        sdg_map['Country'] = sdg_map['conference_venue'].apply(
            lambda x: x.split(',')[-1].strip() if isinstance(x, str) else None
        )

        # Group the data by country and aggregate SDG into a list
        grouped = sdg_map.groupby('Country').agg({
            'sdg': lambda x: list(x),  # Convert SDG into a list
            'conference_venue': 'first'  # Keep the first conference venue (or apply other aggregation if needed)
        }).reset_index()
        if sdg_dropdown_value !="ALL":
            # Ensure that 'sdg' column contains individual SDG values after explode
            df_exploded = grouped.explode('sdg')
            filtered_df = df_exploded[df_exploded['sdg'].notna() & (df_exploded['sdg'] == sdg_dropdown_value)]  # Filter by SDG value

            # Count the number of occurrences per country
            country_counts = filtered_df['Country'].value_counts().reset_index()
            country_counts.columns = ['Country', 'Publication Count']

            # Merge the counts back to the filtered dataframe
            filtered_df = filtered_df.merge(country_counts, on='Country', how='left')

            # Create the choropleth map
            fig = px.choropleth(
                filtered_df,
                locations="Country",  # Column with country names
                locationmode="country names",  # Match with full country names
                title=f"Geochart of {sdg_dropdown_value} Publications by Country",
                color="sdg",  # Use SDG as the color indicator
                hover_data={  # Show SDG and publication count in hover
                    "Publication Count": True,
                    "sdg": True,  # Show SDG in hover
                    "Country": False,  # Country is already represented visually
                }
            )

            
        else:
            # Create a geochart without filtering by SDG
            fig = px.choropleth(
                grouped,
                locations="Country",  # Column with country names
                locationmode="country names",  # Match with full country names
                title="Geochart of Publication Classification by Country",
                hover_data={  # Show SDG in hover
                    "sdg": True,
                    "Country": False,  # Country is already represented visually
                }
            )

        # Update layout for better visualization
        fig.update_layout(
                geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
                coloraxis_showscale=False,  # Hide the color scale if not needed
                height=700,  # Adjust the height as needed (e.g., 800px)  # Adjust the width as needed (e.g., 1200px)
            )

        # Return the figure object
        return fig
    

    def create_sdg_trend(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()

        # Define the ordered list of SDGs (e.g., SDG 1, SDG 2, etc.)
        sdg_order = [f"SDG {i}" for i in range(1, 18)]  # Generates SDG 1 to SDG 17

        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_exploded = df_copy.explode('sdg')  # Explode rows for each SDG value

        # Strip whitespace from the SDG values and ensure correct ordering
        sdg_exploded['sdg'] = sdg_exploded['sdg'].str.strip()
        sdg_exploded['sdg'] = pd.Categorical(sdg_exploded['sdg'], categories=sdg_order, ordered=True)

        if sdg_dropdown_value !="ALL":
            # Filter data for the selected SDG
            sdg_filtered = sdg_exploded[sdg_exploded['sdg'] == sdg_dropdown_value]

            # Group data by year and count occurrences
            sdg_trend = sdg_filtered.groupby('year').size().reset_index(name='count')

            # Create a line chart using Plotly
            fig = px.line(
                sdg_trend,
                x='year',
                y='count',
                title=f'SDG {sdg_dropdown_value} Trend Over Time',
                labels={'year': 'Year', 'count': 'Frequency'},
                markers=True
            )
            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Frequency",
                title_x=0.5,
                template="plotly_white"
            )
        else:
            # Group the data by year and SDG, and calculate the count
            sdg_trends = sdg_exploded.groupby(['year', 'sdg']).size().reset_index(name='count')

            # Create a heatmap using Plotly
            fig = px.density_heatmap(
                sdg_trends,
                x='year',
                y='sdg',
                z='count',
                color_continuous_scale='Blues',
                title="SDG Trends Over Time",
                labels={'year': 'Year', 'sdg': 'SDG', 'count': 'Frequency'}
            )
            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Sustainable Development Goal",
                title_x=0.5,
                template="plotly_white"
            )

        return fig
    


    def create_sdg_bar(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()

        # Define the ordered list of SDGs (e.g., SDG 1, SDG 2, etc.)
        sdg_order = [f"SDG {i}" for i in range(1, 18)]  # Generates SDG 1 to SDG 17

        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_exploded = df_copy.explode('sdg')  # Explode rows for each SDG value

        # Strip whitespace from the SDG values and ensure correct ordering
        sdg_exploded['sdg'] = sdg_exploded['sdg'].str.strip()
        sdg_exploded['sdg'] = pd.Categorical(sdg_exploded['sdg'], categories=sdg_order, ordered=True)

        if sdg_dropdown_value !="ALL":
            # Filter the data for the selected SDG
            sdg_filtered = sdg_exploded[sdg_exploded['sdg'] == sdg_dropdown_value]

            # Group the data by year and research_type
            grouped_data = sdg_filtered.groupby(['year', 'research_type']).size().reset_index(name='count')

            # Create a line plot using Plotly
            fig = px.line(
                grouped_data,
                x='year',
                y='count',
                color='research_type',
                title=f"{sdg_dropdown_value} Trends Over Time by Research Type",
                labels={'year': 'Year', 'count': 'Frequency'},
                markers=True
            )

            # Customize the layout
            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Count",
                title_x=0.5,
                template="plotly_white",
                xaxis_tickangle=-45  # Rotate x-axis labels for better readability
            )
        else:
            # Group the data by SDG and research_type
            grouped_data = sdg_exploded.groupby(['sdg', 'research_type']).size().reset_index(name='count')

            # Create a bar chart using Plotly
            fig = px.bar(
                grouped_data,
                x='sdg',
                y='count',
                color='research_type',
                title="SDG and Research Type Distribution",
                labels={'sdg': 'Sustainable Development Goal', 'count': 'Frequency'},
                barmode='group'  # Group bars side by side
            )

            # Customize the layout
            fig.update_layout(
                xaxis_title="Sustainable Development Goal",
                yaxis_title="Count",
                title_x=0.5,
                template="plotly_white",
                xaxis={
                    'categoryorder': 'array', 
                    'categoryarray': sdg_order,
                    'tickangle': -45  # Rotate x-axis labels for better readability
                }
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
        
        # Callback to update the header based on selected SDG
        @self.dash_app.callback(
            [Output("chosen-sdg", "children"),
             Output("chosen-sdg-label", "children")],
            [Input("sdg-dropdown", "value")]
        )
        def update_header(selected_sdg):

            # If selected_sdg is a list, use the first item or handle as needed
            if isinstance(selected_sdg, list) and selected_sdg:
                selected_sdg = selected_sdg[0]  # Use the first selected SDG, or handle as needed

            label = {
                "SDG 1": "No Poverty",
                "SDG 2": "Zero Hunger",
                "SDG 3": "Good Health and Well-being",
                "SDG 4": "Quality Education",
                "SDG 5": "Gender Equality",
                "SDG 6": "Clean Water and Sanitation",
                "SDG 7": "Affordable and Clean Energy",
                "SDG 8": "Decent Work and Economic Growth",
                "SDG 9": "Industry, Innovation and Infrastructure",
                "SDG 10": "Reduced Inequality",
                "SDG 11": "Sustainable Cities and Communities",
                "SDG 12": "Responsible Consumption and Production",
                "SDG 13": "Climate Action",
                "SDG 14": "Life Below Water",
                "SDG 15": "Life on Land",
                "SDG 16": "Peace, Justice and Strong Institutions",
                "SDG 17": "Partnerships for the Goals"
            }
            title="Overall SDG" if selected_sdg=="ALL" else selected_sdg
                
            caption = label.get(selected_sdg, "") if selected_sdg else ""

            return title, caption
        
        @self.dash_app.callback(
            Output('sdg_map', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_sdg_map(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_map(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        

        @self.dash_app.callback(
            Output('sdg-per-college', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_sdg_trend(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_trend(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('sdg-trend', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_sdg_bar(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_bar(selected_colleges, selected_status, selected_years,sdg_dropdown_value)