import dash
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, html
from components.DashboardHeader import DashboardHeader
from components.Tabs import Tabs
from components.KPI_Card import KPI_Card
from components.CollageContainer import CollageContainer
from dash import dcc
from urllib.parse import parse_qs, urlparse
from . import db_manager
import dash_html_components as html
from services.sdg_colors import sdg_colors
from charts.sdg_college_charts import get_total_proceeding_count,generate_sdg_bipartite_graph,visualize_sdg_impact,create_sdg_plot, create_sdg_pie_chart,create_sdg_research_chart,create_geographical_heatmap,create_geographical_treemap,create_conference_participation_bar_chart,create_local_vs_foreign_donut_chart,get_word_cloud,generate_research_area_visualization
import json
import numpy as np
import datetime
from services.database_manager import DatabaseManager
import plotly.graph_objects as go
from dashboards.usable_methods import default_if_empty, ensure_list, download_file
from flask_jwt_extended import get_jwt_identity
from config import Config


def default_if_empty(value, default):
    """Return default if value is None or empty, otherwise return value."""
    if value is None or (isinstance(value, list) and len(value) == 0):
        return default
    return value

class SDG_Impact_College:
    def __init__(self, server, title=None, college=None, program=None, **kwargs):
        self.app = server
        self.dash_app = Dash(
            __name__,
            server=server,
            url_base_pathname=kwargs.get('url_base_pathname', '/sdg-impact/college/'),
            external_stylesheets=[dbc.themes.BOOTSTRAP, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"]
        )
        
        # Add Redis client from server
        self.redis_client = getattr(server, 'redis_client', None)
        self.redis_available = False
        
        # Test Redis connection if client exists
        if self.redis_client:
            try:
                self.redis_client.ping()
                self.redis_available = True
                print("Redis connection successful")
            except Exception as e:
                print(f"Redis connection failed: {e}")
                print("Falling back to in-memory session storage")
        
        # In-memory session storage as fallback
        self.user_sessions = {}
        
        self.title = title
        self.college = college
        self.program = program
        self.user_role = ""

        self.palette_dict = db_manager.get_college_colors()
        self.sdg_colors = sdg_colors
        self.all_sdgs = [f'SDG {i}' for i in range(1, 18)]
        
        # Get default values
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_programs = []
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        
        # Add user database managers dictionary
        self.user_db_managers = {}

        self.set_layout()
        self.add_callbacks()

    def set_layout(self):

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
            style={"display": "none", "opacity": "0.5"},
        )
        status = html.Div(
            [
                dbc.Label("Select Status:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="status",
                    options=[{'label': value, 'value': value} for value in sorted(
                        db_manager.get_unique_values('status'), key=lambda x: (x != 'READY', x != 'PULLOUT', x)
                    )],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )
        program = html.Div(
            [
                dbc.Label("Select Program:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="program",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values_by('program_id','college_id',self.college)],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )
        slider = html.Div(
            [
                dbc.Label("Select Years: ", style={"color": "#08397C"}),
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
                                "disabled": sdg not in self.all_sdgs,
                            }
                            for sdg in sorted(
                                self.all_sdgs,
                                key=lambda x: int(x.split()[1])  # Extract the numeric part and sort
                            )
                        ]
                    ],
                    multi=False,
                    placeholder="Select SDGs",
                    value="ALL",  # Default to "ALL"
                    style={
                        "width": "100%",
                    },
                )
            ],
             className="mb-4",
        )
        # Collage Section
        self.collage = dbc.Container([
            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dcc.Loading(
                            id='loading-sdg-time-series',
                            type='circle',  # Choose the type of spinner (e.g., 'circle', 'dot', 'default')
                            children=dcc.Graph(id='sdg-time-series')
                        ),
                        body=True,
                        style={"width": "auto", "height": "auto"}
                    ),
                    width="auto", className='p-0'
                ),
                dbc.Col(
                    dbc.Card(
                        dcc.Loading(
                            id='loading-sdg-pie',
                            type='circle', 
                            children=dcc.Graph(id='sdg-pie')
                        ),
                        body=True,
                        style={"width": "auto", "height": "auto"}
                    ),
                    width="auto", className='p-0'
                ),
            ], className='g-0 d-flex'),  # Margin-bottom for spacing

            dbc.Row([
                dbc.Col(
                    dbc.Card(
                        dcc.Loading(
                            id='loading-sdg-research-type',
                            type='circle',
                            children=dcc.Graph(id='sdg-research-type')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                    width="auto", className='p-0'
                ),
            ], className='g-0 d-flex')
        ], fluid=True)  # Set container to fluid for responsiveness


        # Map Section
        self.map = dbc.Container([
            dbc.Row([
                dbc.Alert("Initial alert message", id="alert-message", color="primary", is_open=True,style={"width": "100%", "padding": "2px", "fontSize": "14px"} ),
            ], className='g-0 d-flex'),  # Ensure no space around the alert

            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dcc.Loading(
                            id='loading-local-vs-foreign',
                            type='circle',
                            children=dcc.Graph(id='local-vs-foreign')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                    dbc.Card(
                        dcc.Loading(
                            id='loading-tree-map',
                            type='circle',
                            children=dcc.Graph(id='tree-map')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                ], width="auto", className='p-0'),
                dbc.Col([
                    dbc.Card(
                        dcc.Loading(
                            id='loading-sdg-map',
                            type='circle',
                            children=dcc.Graph(id='sdg-map')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                    dbc.Card(
                        dcc.Loading(
                            id='loading-participation-graph',
                            type='circle',
                            children=dcc.Graph(id='participation-graph')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                ], width="auto", className='p-0')
            ], className='g-0 d-flex')
        ])




        # Trend Section
        self.trend = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dbc.Card(
                        dcc.Loading(
                            id='loading-word-cloud',
                            type='circle',
                            children=dcc.Graph(id='word-cloud')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                    dbc.Card(
                        dcc.Loading(
                            id='loading-research-areas',
                            type='circle',
                            children=dcc.Graph(id='research-areas')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                ], width="auto", className='p-0'),
                dbc.Col(
                    dbc.Card(
                        dcc.Loading(
                            id='loading-sdg-graph',
                            type='circle',
                            children=dcc.Graph(id='sdg-graph')
                        ),
                        body=True,
                        style={"width": "100%", "height": "auto"}
                    ),
                    width="auto", className='p-0'
                )
            ])
        ])
        sidebar = dbc.Col([  # Added array brackets
            html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),
            sdgs,
            college,
            program,
            status,
            slider,
            button
        ], width=2, className="p-3", 
        style={"background": "#d3d8db", "height": "100vh", "position": "fixed", "left": 0, "top": 0, "zIndex": 1000})


        main_content = dbc.Col(
            [
                dcc.Location(id="url", refresh=False),  # Track URL changes
                html.Div(id="dynamic-header"),  # Placeholder for dynamic DashboardHeader
                html.Div(
                    id="tabs-container",
                    children=Tabs(  # Default Tabs
                        tabs_data=[
                            ("Institutional SDG Impact", self.collage),
                            ("Global Research Proceedings", self.map),
                            ("Research Trends and Collaboration",self.trend)
                        ]
                    )
                ),
            ],
            width=10,  # Takes remaining space
            className="p-3",
            style={"marginLeft": "16.67%"}  # Pushes main content to the right of sidebar
        )



        self.dash_app.layout = html.Div([
            dbc.Container([
                dcc.Interval(id="data-refresh-interval", interval=30000, n_intervals=0),
                dcc.Store(id='user-session-data'),  # Add user session storage
                dcc.Store(id='shared-data-store'),  # Add shared data store
                dcc.Location(id="url", refresh=False),  # Make sure URL is tracked
                dbc.Row(
                    [sidebar, main_content], 
                    className="g-0 flex-grow-1"
                )
            ], 
            fluid=True, 
            className="d-flex flex-column w-100 h-100"
            )
        ], 
        className="vh-100 vw-100 d-flex flex-column"
        )



    def add_callbacks(self):
        # Reset button callback
        @self.dash_app.callback(
            [Output('program', 'value'),
            Output('status', 'value'),
            Output('years', 'value'),
            Output('sdg-dropdown', 'value')],
            [Input('reset_button', 'n_clicks')],
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')], "ALL"

        # Update header based on URL parameters
        @self.dash_app.callback(
            [Output("dynamic-header", "children"),
            Output('college', 'value')],
            Input("url", "search")
        )
        def update_header(search):
            if search:
                params = parse_qs(search.lstrip("?"))  # Parse query parameters
                college = params.get("college", [""])[0]
                program = params.get("program", [""])[0]

            self.college = college
            self.program = program
            
            return DashboardHeader(left_text=f"{college}", title=f"SDG IMPACT DASHBOARD"), self.college
        
        # Update program options based on selected college
        @self.dash_app.callback(
        Output('program', 'options'),  # Update the program options based on the selected college
        Input('college', 'value')  # Trigger when the college checklist changes
        )
        def update_program_options(selected_college):
            # If no college is selected, return empty options
            if not selected_college:
                return []

            # Get the programs for the selected college
            program_options = db_manager.get_unique_values_by('program_id', 'college_id', selected_college)

            # Return the options for the program checklist
            return [{'label': program, 'value': program} for program in program_options]

        # Initialize user session data
        @self.dash_app.callback(
            Output('user-session-data', 'data'),
            Input('url', 'search'),
            prevent_initial_call=False
        )
        def initialize_user_session(search):
            # Get user identity from JWT
            try:
                user_id = get_jwt_identity() or 'anonymous'
            except Exception as e:
                print(f"Error getting JWT identity: {e}")
                user_id = 'anonymous'
            
            # Parse URL query parameters
            if search:
                parsed = parse_qs(search.lstrip('?'))
                college_id = parsed.get('college', [None])[0]
                program_id = parsed.get('program', [None])[0]
            else:
                college_id = self.college
                program_id = self.program
            
            # Always set role as college administrator (04)
            user_role = "04"
            
            # Store these values in the class instance
            self.user_role = user_role
            self.college = college_id
            self.program = program_id
            
            print(f"SDG Impact: Initializing session for User ID: {user_id}, College: {college_id}")
            
            # Get all programs for this college
            if college_id:
                self.default_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
                print(f"College programs for {college_id}: {self.default_programs}")
            
            # Get user-specific data
            user_data = self.get_user_specific_data(user_id, user_role, college_id, program_id)
            
            # Make sure college_id is included in the user data
            if "college_id" not in user_data or user_data["college_id"] != college_id:
                user_data["college_id"] = college_id
                user_data["selected_college"] = college_id
            
            print(f"Initialized session data: {user_id} at {college_id}")
            
            # Return the user data for the dcc.Store
            return user_data
        
        # Update shared data store based on user session
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            [Input("data-refresh-interval", "n_intervals"),
             Input("user-session-data", "data"),
             Input("college", "value"),
             Input("program", "value"),
             Input("status", "value"),
             Input("years", "value"),
             Input("sdg-dropdown", "value"),
             Input("reset_button", "n_clicks")],
            prevent_initial_call=False
        )
        def refresh_data(n_intervals, user_data, selected_college, selected_programs, 
                         selected_status, selected_years, sdg_value, reset_clicks):
            # Get current user ID
            try:
                from flask_jwt_extended import get_jwt_identity
                user_id = get_jwt_identity() or 'anonymous'
            except Exception as e:
                print(f"Error getting JWT identity in refresh_data: {e}")
                user_id = 'anonymous'
            
            if not user_data:
                # Create a basic user data structure if none exists
                print("Warning: No user data available")
                user_data = {
                    "user_id": user_id,
                    "role_id": "04",
                    "college_id": selected_college or self.college,
                    "selected_programs": [],
                    "selected_status": self.default_statuses,
                    "selected_years": self.default_years
                }
            
            # Check if reset button was clicked
            ctx = dash.callback_context
            if ctx.triggered and 'reset_button' in ctx.triggered[0]['prop_id']:
                selected_programs = []
                selected_status = self.default_statuses
                selected_years = self.default_years
                sdg_value = "ALL"
            
            # Extract college ID from user data - CRITICAL for user separation
            college_id = user_data.get('college_id')
            if not college_id and selected_college:
                college_id = selected_college
            elif not college_id:
                college_id = self.college
            
            print(f"Refresh data for user {user_id} using college_id: {college_id}")
            
            # Process selections and convert numpy arrays to lists
            selected_programs = self.convert_numpy_to_list(ensure_list(selected_programs) or [])
            selected_status = self.convert_numpy_to_list(ensure_list(selected_status) or self.default_statuses)
            selected_years = self.convert_numpy_to_list(ensure_list(selected_years) or self.default_years)
            
            # For college administrator, always use their college and let them select programs
            if not selected_programs:
                # If no programs explicitly selected, show all from this college
                selected_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
            
            # Log when interval triggers refresh for debugging
            if ctx.triggered and 'data-refresh-interval' in ctx.triggered[0]['prop_id']:
                print(f"Auto-refresh for user {user_id} at college {college_id} at {datetime.datetime.now().strftime('%H:%M:%S')}")
            
            # Update user data in cache
            if user_id != 'anonymous':
                try:
                    self.update_user_specific_data(user_id, college_id, {
                        "selected_college": college_id,
                        "selected_programs": selected_programs,
                        "selected_status": selected_status,
                        "selected_years": selected_years,
                        "sdg_value": sdg_value
                    })
                except Exception as e:
                    print(f"Error updating user data: {e}")
            
            # Build the shared data object with explicit college ID
            shared_data = {
                "selected_college": college_id,
                "selected_programs": selected_programs,
                "selected_status": selected_status,
                "selected_years": selected_years,
                "sdg_value": sdg_value,
                "timestamp": datetime.datetime.now().strftime('%H:%M:%S')
            }
            
            return shared_data
        
        # MAIN CALLBACK for all chart updates
        @self.dash_app.callback(
            [Output('sdg-time-series', 'figure'),
             Output('sdg-pie', 'figure'),
             Output('sdg-research-type', 'figure'),
             Output('sdg-map', 'figure'),
             Output('tree-map', 'figure'),
             Output('participation-graph', 'figure'),
             Output('local-vs-foreign', 'figure'),
             Output('word-cloud', 'figure'),
             Output('research-areas', 'figure'),
             Output('sdg-graph', 'figure')],
            [Input('shared-data-store', 'data')],
            prevent_initial_call=False
        )
        def update_all_charts(shared_data):
            if not shared_data:
                # Return empty figures if no data
                return [go.Figure() for _ in range(10)]
            
            # Extract data from shared store
            college = shared_data.get('selected_college')
            selected_programs = shared_data.get('selected_programs', [])
            selected_status = shared_data.get('selected_status', self.default_statuses)
            selected_years = shared_data.get('selected_years', self.default_years)
            sdg_dropdown_value = shared_data.get('sdg_value', 'ALL')
            
            # Ensure values are properly formatted
            selected_status = selected_status if selected_status else self.default_statuses
            selected_years = selected_years if selected_years else self.default_years
            
            # Generate all chart figures
            try:
                time_series = create_sdg_plot(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating time series: {e}")
                time_series = go.Figure()
                
            try:
                impact_chart = visualize_sdg_impact(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating impact chart: {e}")
                impact_chart = go.Figure()
                
            try:
                research_type = create_sdg_research_chart(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating research type chart: {e}")
                research_type = go.Figure()
                
            try:
                sdg_map = create_geographical_heatmap(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating heatmap: {e}")
                sdg_map = go.Figure()
                
            try:
                tree_map = create_geographical_treemap(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating treemap: {e}")
                tree_map = go.Figure()
                
            try:
                participation = create_conference_participation_bar_chart(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating participation chart: {e}")
                participation = go.Figure()
                
            try:
                local_vs_foreign = create_local_vs_foreign_donut_chart(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating local vs foreign chart: {e}")
                local_vs_foreign = go.Figure()
                
            try:
                word_cloud = get_word_cloud(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating word cloud: {e}")
                word_cloud = go.Figure()
                
            try:
                research_areas = generate_research_area_visualization(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating research areas: {e}")
                research_areas = go.Figure()
                
            try:
                sdg_graph = generate_sdg_bipartite_graph(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error generating SDG graph: {e}")
                sdg_graph = go.Figure()
            
            # Return all charts in a list
            return [
                time_series,
                impact_chart,
                research_type,
                sdg_map,
                tree_map,
                participation,
                local_vs_foreign,
                word_cloud,
                research_areas,
                sdg_graph
            ]
            
        # Alert message callback
        @self.dash_app.callback(
            [Output("alert-message", "children"),
             Output("alert-message", "color")],
            [Input('shared-data-store', 'data')],
            prevent_initial_call=False
        )
        def update_alert_message(shared_data):
            if not shared_data:
                return "No data available", "warning"
            
            # Extract data from shared store
            college = shared_data.get('selected_college')
            selected_programs = shared_data.get('selected_programs', [])
            selected_status = shared_data.get('selected_status', self.default_statuses)
            selected_years = shared_data.get('selected_years', self.default_years)
            sdg_dropdown_value = shared_data.get('sdg_value', 'ALL')
            
            # Ensure values are properly formatted
            selected_status = selected_status if selected_status else self.default_statuses
            selected_years = selected_years if selected_years else self.default_years
            
            try:
                return get_total_proceeding_count(
                    selected_programs, selected_status, selected_years, sdg_dropdown_value, college)
            except Exception as e:
                print(f"Error getting proceeding count: {e}")
                return f"Error retrieving data: {str(e)}", "danger"

    def convert_numpy_to_list(self, value):
        """Convert numpy arrays and values to Python native types for JSON serialization"""
        if isinstance(value, np.ndarray):
            return value.tolist()
        elif isinstance(value, np.integer):
            return int(value)
        elif isinstance(value, np.floating):
            return float(value)
        elif isinstance(value, np.bool_):
            return bool(value)
        elif isinstance(value, list):
            return [self.convert_numpy_to_list(item) for item in value]
        elif isinstance(value, dict):
            return {k: self.convert_numpy_to_list(v) for k, v in value.items()}
        else:
            return value
            
    def get_user_db_manager(self, user_id, role_id, college_id=None, program_id=None):
        """
        Get or create a database manager instance specific to this user.
        """
        # Check if we already have a manager for this user
        if user_id in self.user_db_managers:
            return self.user_db_managers[user_id]
        
        # Create a new manager for this user
        print(f"Creating new database manager for user {user_id} with role {role_id}")
        user_db = DatabaseManager(Config.SQLALCHEMY_DATABASE_URI)
        user_db.get_all_data()  # Load the data
        
        # Store it in our dictionary
        self.user_db_managers[user_id] = user_db
        
        return user_db
        
    def get_user_specific_data(self, user_id, role_id, college_id=None, program_id=None):
        """
        Get or create user-specific data store in Redis or memory
        """
        # Create a unique key that includes BOTH user ID AND college ID to ensure separation
        cache_key = f"sdg_impact_college:{user_id}:{college_id}"
        
        # Try Redis if available
        if self.redis_available and self.redis_client:
            try:
                # Check if we already have cached data for this user+college combination
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    print(f"Using cached data for user {user_id} at college {college_id}")
                    return json.loads(cached_data)
            except Exception as e:
                print(f"Redis error: {e}")
                print("Falling back to in-memory session storage")
                self.redis_available = False
        
        # Create a composite key for memory storage too
        memory_key = f"{user_id}:{college_id}"
        
        # Check in-memory cache if Redis failed or isn't available
        if memory_key in self.user_sessions:
            print(f"Using in-memory data for user {user_id} at college {college_id}")
            return self.user_sessions[memory_key]
        
        # Set up initial data object if no cached data exists
        # Always set role_id to "04" (College Administrator)
        user_data = {
            "user_id": user_id,
            "role_id": "04",  # Always college administrator
            "college_id": college_id,
            "program_id": program_id,
            "selected_college": college_id,  # Add this explicit field
            "selected_programs": db_manager.get_unique_values_by("program_id", "college_id", college_id) if college_id else [],
            "selected_status": self.convert_numpy_to_list(self.default_statuses),
            "selected_years": self.convert_numpy_to_list(self.default_years),
            "selected_terms": self.convert_numpy_to_list(self.default_terms) if hasattr(self, 'default_terms') else [],
            "timestamp": datetime.datetime.now().isoformat()  # Add timestamp for debugging
        }
        
        print(f"Creating new session for user {user_id} at college {college_id}")
        
        # Try to cache in Redis first
        if self.redis_available and self.redis_client:
            try:
                json_data = json.dumps(user_data)
                self.redis_client.setex(cache_key, 1800, json_data)
            except Exception as e:
                print(f"Error caching user data in Redis: {e}")
                self.redis_available = False
        
        # Store in memory as fallback
        self.user_sessions[memory_key] = user_data
        
        return user_data

    def update_user_specific_data(self, user_id, college_id, update_dict):
        """
        Update user-specific data in Redis or memory
        """
        # Create a unique key that includes BOTH user ID AND college ID
        cache_key = f"sdg_impact_college:{user_id}:{college_id}"
        memory_key = f"{user_id}:{college_id}"
        
        # Try Redis first if available
        if self.redis_available and self.redis_client:
            try:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    user_data = json.loads(cached_data)
                    user_data.update(update_dict)
                    user_data["timestamp"] = datetime.datetime.now().isoformat()  # Update timestamp
                    self.redis_client.setex(cache_key, 1800, json.dumps(user_data))
                    print(f"Updated Redis data for user {user_id} at college {college_id}")
                    return user_data
            except Exception as e:
                print(f"Redis error updating data: {e}")
                self.redis_available = False
        
        # Use in-memory storage as fallback
        if memory_key in self.user_sessions:
            self.user_sessions[memory_key].update(update_dict)
            self.user_sessions[memory_key]["timestamp"] = datetime.datetime.now().isoformat()
            print(f"Updated in-memory data for user {user_id} at college {college_id}")
            return self.user_sessions[memory_key]
        else:
            # Create new user session if it doesn't exist
            update_dict["timestamp"] = datetime.datetime.now().isoformat()
            self.user_sessions[memory_key] = update_dict
            print(f"Created new in-memory data for user {user_id} at college {college_id}")
            return update_dict