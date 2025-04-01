import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from . import db_manager
import pandas as pd
import numpy as np
from database.institutional_performance_queries import get_data_for_modal_contents, get_data_for_text_displays
from urllib.parse import parse_qs
from components.DashboardHeader import DashboardHeader
from components.Tabs import Tabs
import pandas as pd
from dash.dcc import send_file
from components.KPI_Card import KPI_Card
from dashboards.usable_methods import default_if_empty, ensure_list, download_file
from charts.institutional_performance_charts import ResearchOutputPlot
from dash.exceptions import PreventUpdate
import json
from flask_jwt_extended import get_jwt_identity
from flask import session, current_app
from config import Config
from services.database_manager import DatabaseManager
import datetime
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session
from models import ResearchOutput, Status, Publication
from components.DashboardHeader import DashboardHeader
from datetime import datetime


class NumpyEncoder(json.JSONEncoder):
    """Special JSON encoder for numpy types"""
    def default(self, obj):
        import numpy as np
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                              np.int16, np.int32, np.int64, np.uint8,
                              np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
            return float(obj)
        elif isinstance(obj, (np.bool_)):
            return bool(obj)
        return json.JSONEncoder.default(self, obj)

class Institutional_Performance_Dash:
    def __init__(self, server):
        self.app = server
        self.dash_app = dash.Dash(
            __name__,
            server=server,
            routes_pathname_prefix='/institutional-performance/',
            external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
            requests_pathname_prefix="/institutional-performance/"
        )
        
        self.redis_client = self.app.redis_client
        
        self.plot_instance = ResearchOutputPlot()
        self.college = None
        self.program = None
        self.user_role = ""

        # Get default values from global db_manager for initial setup only
        self.palette_dict = db_manager.get_college_colors()
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_programs = []
        self.default_statuses = ["READY", "SUBMITTED", "ACCEPTED", "PUBLISHED", "PULLOUT"]
        self.default_terms = db_manager.get_unique_values('term')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]

        self.selected_colleges = []
        self.selected_programs = []
        
        # Add user database managers dictionary
        self.user_db_managers = {}
        
        self.setup_dashboard()
        self.set_callbacks()

    def setup_dashboard(self):
        """
        Create the layout of the dashboard.
        """

        college = html.Div(
            id="college-container",  # Add an ID for visibility control
            children=[
                dbc.Label("Select College/s:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        program = html.Div(
            id="program-container",  # Add an ID for visibility control
            children=[
                dbc.Label("Select Program:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="program",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values_by('program_id', 'college_id', self.college)],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        terms = sorted(db_manager.get_unique_values('term'))

        term = html.Div(
            [
                dbc.Label("Select Term/s:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="terms",
                    options=[{'label': value, 'value': value} for value in terms],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        # Define all statuses for data retrieval
        self.ALL_STATUSES = ["READY", "SUBMITTED", "ACCEPTED", "PUBLISHED", "PULLOUT"]
        self.default_statuses = self.ALL_STATUSES
        
        # For the status filter, only add options that should be visible initially
        # We'll update this dynamically later
        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLOUT']
        initial_visible_statuses = db_manager.get_unique_values('status')
        
        status = html.Div(
            [
                dbc.Label("Select Status:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="status",
                    options=[{'label': 'PULLOUT' if value == 'PULLOUT' else value, 'value': value} 
                            for value in status_order if value in initial_visible_statuses],
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

        controls = dbc.Col(
            dbc.Card(
                [
                    html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),  # Set the color to red
                    html.Div(
                        [college, program, status, term, slider, button], 
                        style={"font-size": "0.85rem", "padding": "5px"}  # Reduce font size and padding
                    ),
                ],
                body=True,
                style={
                    "background": "#d3d8db",
                    "height": "100vh",  # Full-height sidebar
                    "position": "sticky",  # Sticky position instead of fixed
                    "top": 0,
                    "padding": "10px",  # Reduce padding for a more compact layout
                    "border-radius": "0",  # Remove rounded corners
                },
            )
        )

        main_dash = dbc.Container([
            dbc.Row([  # Row for the line and pie charts
                dbc.Col(
                    dcc.Loading(
                        id="loading-college-line",
                        type="circle",
                        children=dcc.Graph(
                            id='college_line_plot',
                            config={"responsive": True},
                            style={"height": "400px"}  # Applied chart height from layout
                        )
                    ), 
                    width=8, 
                    style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}
                ),
                dbc.Col(
                    dcc.Loading(
                        id="loading-college-pie",
                        type="circle",
                        children=dcc.Graph(
                            id='college_pie_chart',
                            config={"responsive": True},
                            style={"height": "400px"}  # Applied chart height from layout
                        )
                    ), 
                    width=4, 
                    style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}
                )
            ], style={"margin": "10px"}),
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash1 = dbc.Container([
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        id="loading-research-status",
                        type="circle",
                        children=dcc.Graph(id='research_status_bar_plot'),
                    ), 
                    width=6, 
                    style={"height": "auto", "overflow": "hidden"}
                ),
                dbc.Col(
                    dcc.Loading(
                        id="loading-research-type",
                        type="circle",
                        children=dcc.Graph(id='research_type_bar_plot'),
                    ), 
                    width=6, 
                    style={"height": "auto", "overflow": "hidden"}
                )
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash2 = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Tabs(
                        id='nonscopus_scopus_tabs',
                        value='line',
                        children=[
                            dcc.Tab(label='Trends Over Time', value='line', style={"font-size": "12px"}),
                            dcc.Tab(label='Percentage Distribution', value='pie', style={"font-size": "12px"})
                        ],
                        style={"font-size": "14px"}  # Adjust overall font size of tabs
                    ),
                    dcc.Loading(
                        id="loading-nonscopus-scopus1",
                        type="circle",
                        children=dcc.Graph(
                            id='nonscopus_scopus_graph',
                            config={"responsive": True},
                            style={"height": "300px"}  # Applied chart height from layout
                        )
                    )
                ], width=6, style={"height": "auto", "overflow": "hidden"}),
                dbc.Col(
                    dcc.Loading(
                        id="loading-nonscopus-scopus2",
                        type="circle",
                        children=dcc.Graph(id='nonscopus_scopus_bar_plot')
                    ),
                    width=6,
                    style={"height": "auto", "overflow": "hidden"}
                )
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})


        sub_dash3 = dbc.Container([
            dbc.Row([
                dbc.Col(
                    dcc.Loading(
                        id="loading-sdg-bar",
                        type="circle",
                        children=dcc.Graph(id='sdg_bar_plot'),
                    ), 
                    width=12
                )
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})

        sub_dash4 = dbc.Container([
            dbc.Row([
                dbc.Col([
                dcc.Tabs(
                    id='proceeding_conference_tabs',
                    value='line',  # Default view is the line chart
                    children=[
                        dcc.Tab(label='Trends Over Time', value='line', style={"font-size": "12px"}),
                        dcc.Tab(label='Percentage Distribution', value='pie', style={"font-size": "12px"})
                    ],
                    style={"font-size": "14px"}  # Adjust overall font size of tabs
                ),
                dcc.Loading(
                    id="loading-proceeding-conference1",
                    type="circle",
                    children=dcc.Graph(
                        id='proceeding_conference_graph',
                        config={"responsive": True},
                        style={"height": "300px"}  # Applied chart height from layout
                    )
                )
            ], width=6, style={"height": "auto", "overflow": "hidden"}),
                dbc.Col(
                    dcc.Loading(
                        id="loading-proceeding-conference2",
                        type="circle",
                        children=dcc.Graph(id='proceeding_conference_bar_plot')
                    ),
                    width=6,
                    style={"height": "auto", "overflow": "hidden"}
                )
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})

        text_display = dbc.Container([
            dbc.Row(
                [
                    dbc.Col(KPI_Card("Research Output(s)", "0", id="open-total-modal", icon="fas fa-book-open", color="primary"), width="auto"),
                    dbc.Col(KPI_Card("Ready for Publication", "0", id="open-ready-modal", icon="fas fa-file-import", color="info"),width="auto"),
                    dbc.Col(KPI_Card("Submitted Paper(s)", "0", id="open-submitted-modal", icon="fas fa-file-export", color="warning"), width="auto"),
                    dbc.Col(KPI_Card("Accepted Paper(s)", "0", id="open-accepted-modal", icon="fas fa-check-circle", color="success"), width="auto"),
                    dbc.Col(KPI_Card("Published Paper(s)", "0", id="open-published-modal", icon="fas fa-file-alt", color="danger"), width="auto"),
                    dbc.Col(KPI_Card("Pulled-out Paper(s)", "0", id="open-pullout-modal", icon="fas fa-file-excel", color="secondary"), width="auto")
                ],
                className="g-2",  # Mas maliit na gap
                justify="center",
                style={"padding-top": "0", "padding-bottom": "0", "margin-top": "-10px"}  # Tinaas ang row
            ),
        ], className="p-0", style={"padding-top": "0", "padding-bottom": "0"})


        self.dash_app.layout = html.Div([
            dcc.Location(id='url', refresh=False),
            dcc.Store(id='session-store', storage_type='session'),
            dcc.Interval(id="data-refresh-interval", interval=30000, n_intervals=0),  # 30-second refresh interval
            dcc.Store(id="shared-data-store"),  # Shared data store to hold the updated dataset
            dcc.Download(id="total-download-link"), # For download feature (modal content)
            dcc.Download(id="ready-download-link"), # For download feature (modal content)
            dcc.Download(id="submitted-download-link"), # For download feature (modal content)
            dcc.Download(id="accepted-download-link"), # For download feature (modal content)
            dcc.Download(id="published-download-link"), # For download feature (modal content)
            dcc.Download(id="pullout-download-link"), # For download feature (modal content)
            dbc.Container([
                dbc.Row([
                    dbc.Col(
                        controls,
                        width={"size": 2, "order": 1},
                        style={"height": "100vh", "padding": "0", "overflow": "hidden"}
                    ),
                    dbc.Col(
                        html.Div([
                            html.Div(id="dynamic-header", style={"margin-bottom": "20px", "padding-top": "10px"}),
                            text_display,
                            html.Div(
                                id="dashboard-tabs",
                                children=Tabs(
                                    tabs_data=[
                                        ("Performance Overview", html.Div(main_dash, style={"height": "100%", "padding": "5px"})),
                                        ("Research Statuses and Types", html.Div(sub_dash1, style={"height": "100%", "padding": "5px"})),
                                        ("SDG Distribution", html.Div(sub_dash3, style={"height": "100%", "padding": "5px"})),
                                        ("Scopus and Non-Scopus", html.Div(sub_dash2, style={"height": "100%", "padding": "5px"})),                                        
                                        ("Publication Types", html.Div(sub_dash4, style={"height": "100%", "padding": "5px"}))
                                    ]
                                ),
                                style={"height": "calc(100vh - 50px)", "overflow": "hidden"}
                            ),
                            # Modals for each button
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Research Output(s)")),
                                dbc.ModalBody(id="total-modal-content"),
                                dbc.ModalFooter(
                                    dbc.ModalFooter([
                                        dbc.Button("Export", id="total-download-btn", color="success", className="mr-2", n_clicks=0),
                                        dbc.Col(dbc.Button("Close", id="close-total-modal", className="ms-auto", n_clicks=0))
                                    ])
                                ) 
                            ], id="total-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Ready for Publication")),
                                dbc.ModalBody(id="ready-modal-content"),
                                dbc.ModalFooter(
                                    dbc.ModalFooter([
                                        dbc.Button("Export", id="ready-download-btn", color="success", className="mr-2", n_clicks=0),
                                        dbc.Col(dbc.Button("Close", id="close-ready-modal", className="ms-auto", n_clicks=0))
                                    ])
                                ) 
                            ], id="ready-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Submitted Paper(s)")),
                                dbc.ModalBody(id="submitted-modal-content"),
                                dbc.ModalFooter(
                                    dbc.ModalFooter([
                                        dbc.Button("Export", id="submitted-download-btn", color="success", className="mr-2", n_clicks=0),
                                        dbc.Col(dbc.Button("Close", id="close-submitted-modal", className="ms-auto", n_clicks=0))
                                    ])
                                ) 
                            ], id="submitted-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Accepted Paper(s)")),
                                dbc.ModalBody(id="accepted-modal-content"),
                                dbc.ModalFooter(
                                    dbc.ModalFooter([
                                        dbc.Button("Export", id="accepted-download-btn", color="success", className="mr-2", n_clicks=0),
                                        dbc.Col(dbc.Button("Close", id="close-accepted-modal", className="ms-auto", n_clicks=0))
                                    ])
                                )  
                            ], id="accepted-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Published Paper(s)")),
                                dbc.ModalBody(id="published-modal-content"),
                                dbc.ModalFooter(
                                    dbc.ModalFooter([
                                        dbc.Button("Export", id="published-download-btn", color="success", className="mr-2", n_clicks=0),
                                        dbc.Col(dbc.Button("Close", id="close-published-modal", className="ms-auto", n_clicks=0))
                                    ])
                                )  
                            ], id="published-modal", scrollable=True, is_open=False, size="xl"),

                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Pulled-out Paper(s)")),
                                dbc.ModalBody(id="pullout-modal-content"),
                                dbc.ModalFooter(
                                    dbc.ModalFooter([
                                        dbc.Button("Export", id="pullout-download-btn", color="success", className="mr-2", n_clicks=0),
                                        dbc.Col(dbc.Button("Close", id="close-pullout-modal", className="ms-auto", n_clicks=0))
                                    ])
                                )     
                            ], id="pullout-modal", scrollable=True, is_open=False, size="xl"),
                        ], style={
                            "display": "flex",
                            "flex-direction": "column",
                            "height": "100vh",
                            "padding": "10px",
                            "overflow": "hidden"
                        }),
                        width={"size": 10, "order": 2},
                    ),
                ], style={"height": "100vh", "display": "flex", "flex-wrap": "nowrap"}),
            ], fluid=True, style={"height": "100vh", "margin": "0", "padding": "0", "overflow": "hidden"}),
        ], style={
            "height": "100vh",
            "margin": "0",
            "padding": "0",
            "overflow": "hidden",  # Prevent outer scrolling
        })
    
    # This helper function ensures numpy arrays are converted to lists before sending to SQL
    def convert_numpy_to_list(self, value):
        """Convert numpy arrays and values to Python native types for JSON serialization"""
        import numpy as np
        
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
    
    def set_callbacks(self):
        """
        Set up the interactive callbacks for the dashboard.
        """
        @self.dash_app.callback(
            [Output('url', 'pathname'),
             Output('session-store', 'data')],
            Input('url', 'search'),
            prevent_initial_call=True
        )
        def initialize_user_session(search):
            """Initialize user session from URL parameters"""
            # Parse URL query parameters
            parsed = parse_qs(search.lstrip('?'))
            user_role = parsed.get('user-role', ['01'])[0]  # Default role
            college_id = parsed.get('college', [None])[0]
            program_id = parsed.get('program', [None])[0]
            
            # Store these values in the class instance for this session
            self.user_role = user_role
            self.college = college_id
            self.program = program_id
            
            print(f"User Session Initialized - Role: {user_role}, College: {college_id}, Program: {program_id}")
            
            # For College Administrator (role 04), get all programs for this college
            if user_role == "04" and college_id:
                self.default_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
                self.selected_colleges = [college_id]
                print(f"College Administrator role detected - programs available: {self.default_programs}")
            # For Program Administrator (role 05), restrict to one program
            elif user_role == "05" and program_id:
                self.default_programs = [program_id]
                self.selected_programs = [program_id]
                print(f"Program Administrator role detected - program: {self.default_programs}")
            # For Directors and Head Executives (roles 02/03)
            else:
                if user_role in ["02", "03"]:
                    print(f"Director/Head Executive role detected")
            
            # Create session data to store
            session_data = {
                'user_role': user_role,
                'college_id': college_id,
                'program_id': program_id,
                'default_programs': self.default_programs if hasattr(self, 'default_programs') else []
            }
            
            # Return the current pathname and session data
            return dash.no_update, session_data
        
        # First callback that handles nonscopus_scopus tab changes and filter updates
        @self.dash_app.callback(
            Output('nonscopus_scopus_graph', 'figure'),
            [Input('nonscopus_scopus_tabs', 'value'),
            Input('college', 'value'),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value'),
            Input('reset_button', 'n_clicks')],
            [State('url', 'search')])
        def update_nonscopus_scopus_tab(nonscopus_scopus_tab, selected_colleges, selected_programs, 
                                    selected_status, selected_years, selected_terms, n_clicks, search):
            # Get user identity
            try:
                user_id = get_jwt_identity() or 'anonymous'
            except Exception as e:
                print(f"Error getting JWT identity: {e}")
                user_id = 'anonymous'
                
            # Parse URL parameters
            parsed = parse_qs(search.lstrip('?')) if search else {}
            user_role = parsed.get('user-role', ['01'])[0]
            college_id = parsed.get('college', [None])[0]
            program_id = parsed.get('program', [None])[0]
            
            # Check if reset button was clicked
            ctx = dash.callback_context
            if ctx.triggered and 'reset_button' in ctx.triggered[0]['prop_id']:
                selected_colleges = []
                selected_programs = []
                selected_status = self.default_statuses
                selected_years = self.default_years
                selected_terms = self.default_terms
            else:
                # Process selections and convert numpy arrays to lists
                selected_colleges = self.convert_numpy_to_list(ensure_list(selected_colleges) or [])
                selected_programs = self.convert_numpy_to_list(ensure_list(selected_programs) or [])
                selected_status = self.convert_numpy_to_list(ensure_list(selected_status) or self.default_statuses)
                selected_years = self.convert_numpy_to_list(ensure_list(selected_years) or self.default_years)
                selected_terms = self.convert_numpy_to_list(ensure_list(selected_terms) or self.default_terms)
            
            # Apply role-based filters
            if user_role in ["02", "03"]:  # Director/Head Executive
                if not selected_colleges:  # If no colleges selected, show all
                    selected_colleges = self.default_colleges
                selected_programs = []  # Always empty for Directors
            elif user_role == "04":  # College Administrator
                selected_colleges = [college_id]
                if not selected_programs:  # Show all programs from this college by default
                    selected_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
            elif user_role == "05":  # Program Administrator
                selected_colleges = []
                selected_programs = [program_id]
            
            # Return only the appropriate chart based on tab selection
            if nonscopus_scopus_tab == 'line':
                return self.plot_instance.scopus_line_graph(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms,
                    default_years=self.default_years
                )
            else:
                return self.plot_instance.scopus_pie_chart(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

        # Second callback that handles proceeding_conference tab changes and filter updates
        @self.dash_app.callback(
            Output('proceeding_conference_graph', 'figure'),
            [Input('proceeding_conference_tabs', 'value'),
            Input('college', 'value'),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value'),
            Input('reset_button', 'n_clicks')],
            [State('url', 'search')])
        def update_proceeding_conference_tab(proceeding_conference_tab, selected_colleges, selected_programs, 
                                        selected_status, selected_years, selected_terms, n_clicks, search):
            # Get user identity
            try:
                user_id = get_jwt_identity() or 'anonymous'
            except Exception as e:
                print(f"Error getting JWT identity: {e}")
                user_id = 'anonymous'
                
            # Parse URL parameters
            parsed = parse_qs(search.lstrip('?')) if search else {}
            user_role = parsed.get('user-role', ['01'])[0]
            college_id = parsed.get('college', [None])[0]
            program_id = parsed.get('program', [None])[0]
            
            # Check if reset button was clicked
            ctx = dash.callback_context
            if ctx.triggered and 'reset_button' in ctx.triggered[0]['prop_id']:
                selected_colleges = []
                selected_programs = []
                selected_status = self.default_statuses
                selected_years = self.default_years
                selected_terms = self.default_terms
            else:
                # Process selections and convert numpy arrays to lists
                selected_colleges = self.convert_numpy_to_list(ensure_list(selected_colleges) or [])
                selected_programs = self.convert_numpy_to_list(ensure_list(selected_programs) or [])
                selected_status = self.convert_numpy_to_list(ensure_list(selected_status) or self.default_statuses)
                selected_years = self.convert_numpy_to_list(ensure_list(selected_years) or self.default_years)
                selected_terms = self.convert_numpy_to_list(ensure_list(selected_terms) or self.default_terms)
            
            # Apply role-based filters
            if user_role in ["02", "03"]:  # Director/Head Executive
                if not selected_colleges:  # If no colleges selected, show all
                    selected_colleges = self.default_colleges
                selected_programs = []  # Always empty for Directors
            elif user_role == "04":  # College Administrator
                selected_colleges = [college_id]
                if not selected_programs:  # Show all programs from this college by default
                    selected_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
            elif user_role == "05":  # Program Administrator
                selected_colleges = []
                selected_programs = [program_id]
                
            # Return only the appropriate chart based on tab selection
            if proceeding_conference_tab == 'line':
                return self.plot_instance.publication_format_line_plot(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms,
                    default_years=self.default_years
                )
            else:
                return self.plot_instance.publication_format_pie_chart(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

        # Main callback for all other chart updates - removed the tab inputs
        @self.dash_app.callback(
            [Output('college_line_plot', 'figure'),
             Output('college_pie_chart', 'figure'),
             Output('research_status_bar_plot', 'figure'),
             Output('research_type_bar_plot', 'figure'),
             Output('nonscopus_scopus_bar_plot', 'figure'),
             Output('proceeding_conference_bar_plot', 'figure'),
             Output('sdg_bar_plot', 'figure')],
            [Input('data-refresh-interval', 'n_intervals'),  # Add the interval directly
             Input('url', 'search'),
             Input('college', 'value'),
             Input('program', 'value'),
             Input('status', 'value'),
             Input('years', 'value'),
             Input('terms', 'value'),
             Input('reset_button', 'n_clicks')])
        def update_dash_output(n_intervals, search, selected_colleges, selected_programs, selected_status, 
                            selected_years, selected_terms, n_clicks):
            # Get user identity
            try:
                user_id = get_jwt_identity() or 'anonymous'
            except Exception as e:
                print(f"Error getting JWT identity: {e}")
                user_id = 'anonymous'
                
            # Parse URL parameters
            parsed = parse_qs(search.lstrip('?')) if search else {}
            user_role = parsed.get('user-role', ['01'])[0]
            college_id = parsed.get('college', [None])[0]
            program_id = parsed.get('program', [None])[0]
            
            # Process selections and convert numpy arrays to lists
            selected_colleges = self.convert_numpy_to_list(ensure_list(selected_colleges) or [])
            selected_programs = self.convert_numpy_to_list(ensure_list(selected_programs) or [])
            selected_status = self.convert_numpy_to_list(ensure_list(selected_status) or self.default_statuses)
            selected_years = self.convert_numpy_to_list(ensure_list(selected_years) or self.default_years)
            selected_terms = self.convert_numpy_to_list(ensure_list(selected_terms) or self.default_terms)
            
            # Apply role-based filters
            if user_role in ["02", "03"]:  # Director/Head Executive
                if not selected_colleges:  # If no colleges selected, show all
                    selected_colleges = self.default_colleges
                selected_programs = []  # Always empty for Directors
            elif user_role == "04":  # College Administrator
                selected_colleges = [college_id]
                if not selected_programs:  # Show all programs from this college by default
                    selected_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
            elif user_role == "05":  # Program Administrator
                selected_colleges = []
                selected_programs = [program_id]
            print("Updating dash using status:",selected_status)
            # Get the trigger to see what caused this callback
            trigger = dash.callback_context.triggered[0]['prop_id'] if dash.callback_context.triggered else None
            
            # Log when interval triggers refresh for debugging
            if trigger == 'data-refresh-interval.n_intervals':
                print(f"Auto-refresh triggered at {datetime.now().strftime('%H:%M:%S')}")
            
            # Return all visualization components
            return [
                self.plot_instance.update_line_plot(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms,
                    default_years=self.default_years
                ),
                self.plot_instance.update_pie_chart(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                ),
                self.plot_instance.update_research_status_bar_plot(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                ),
                self.plot_instance.update_research_type_bar_plot(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                ),
                self.plot_instance.create_publication_bar_chart(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                ),
                self.plot_instance.update_publication_format_bar_plot(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                ),
                self.plot_instance.update_sdg_chart(
                    user_id=user_role,
                    college_colors=self.palette_dict,
                    selected_colleges=selected_colleges,
                    selected_programs=selected_programs,
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )
            ]
        
        @self.dash_app.callback(
            [
                Output('open-total-modal', 'children'),
                Output('open-ready-modal', 'children'),
                Output('open-submitted-modal', 'children'),
                Output('open-accepted-modal', 'children'),
                Output('open-published-modal', 'children'),
                Output('open-pullout-modal', 'children')
            ],
            [
                Input("data-refresh-interval", "n_intervals"),
                Input('session-store', 'data'),
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def refresh_text_buttons(n_intervals, session_data, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            # CRITICAL FIX: Get database values but ALWAYS include all KNOWN statuses
            db_statuses = db_manager.get_unique_values('status')
            all_known_statuses = ["READY", "SUBMITTED", "ACCEPTED", "PUBLISHED", "PULLOUT"]
            
            # Combine database values with known values to ensure we don't miss any
            self.default_statuses = np.unique(np.concatenate([db_statuses, all_known_statuses]))
            
            # Get user role from session store
            if not session_data:
                user_role = "01"  # Default if no session data
                college_id = None
                program_id = None
            else:
                user_role = session_data.get('user_role', '01')
                college_id = session_data.get('college_id')
                program_id = session_data.get('program_id')
            
            print(f"KPI Refresh - User Role: {user_role}, College: {college_id}, Program: {program_id}")
            
            # CRITICAL FIX: Always clear program selection for Directors
            if user_role in ["02", "03"]:
                selected_programs = []  # Force empty program selection for directors
                print(f"Director KPI Refresh: Forced program selection clear")
            
            # Apply role-based filters
            if user_role in ["02", "03"]:  # Director/Head Executive
                selected_colleges = selected_colleges or self.default_colleges
                selected_programs = []  # Always empty for directors
            elif user_role == "04":  # College Administrator
                selected_colleges = [college_id] if college_id else []
                if not selected_programs:  # Show all programs from this college by default
                    selected_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
            elif user_role == "05":  # Program Coordinator
                selected_colleges = []
                selected_programs = [program_id] if program_id else []
            
            # Apply default values if needed
            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)  # Already cleared for directors above
            
            # CRITICAL FIX: Always query for ALL known statuses for KPIs
            selected_status = all_known_statuses  # Force all statuses for KPI counts
            
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            
            # CRITICAL FIX: Convert numpy arrays to lists
            selected_colleges = self.convert_numpy_to_list(selected_colleges)
            selected_programs = self.convert_numpy_to_list(selected_programs)
            selected_status = self.convert_numpy_to_list(selected_status)
            selected_years = self.convert_numpy_to_list(selected_years)
            selected_terms = self.convert_numpy_to_list(selected_terms)
            
            print(f"KPI Final Filters - Role: {user_role}, Colleges: {selected_colleges}, Programs: {selected_programs}")
            
            # Apply filters with explicit user role consideration
            filter_kwargs = {
                "selected_status": selected_status,  # This now includes ALL statuses
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }
            
            # Based on role, determine whether to filter by college or program
            if user_role in ["02", "03"]:  # Directors, Head Execs
                filter_kwargs["selected_colleges"] = selected_colleges
                # Explicitly ensure no program filtering for directors
                filter_kwargs["selected_programs"] = []
            elif user_role == "04":  # College Admins
                if selected_programs:
                    filter_kwargs["selected_programs"] = selected_programs
                else:
                    filter_kwargs["selected_colleges"] = selected_colleges
            elif user_role == "05":  # Program Coordinators
                filter_kwargs["selected_programs"] = selected_programs
            
            # Get data specifically for this user's session - ALWAYS include ALL statuses
            filtered_data = get_data_for_text_displays(**filter_kwargs)
            
            # Process results consistently
            status_counts = {d["status"]: d["total_count"] for d in filtered_data}
            
            # Ensure all statuses are represented (even with zero count)
            for status in all_known_statuses:
                if status not in status_counts:
                    status_counts[status] = 0
            
            total_research_outputs = sum(status_counts.values())
            
            print(f'User Role: {user_role}, College: {college_id}, Program: {program_id}')
            print(f'Final selected_colleges: {selected_colleges}')
            print(f'Final selected_programs: {selected_programs}')
            
            return (
                [html.H3(f'{total_research_outputs}', className="mb-0")],
                [html.H3(f'{status_counts.get("READY", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("SUBMITTED", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("ACCEPTED", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("PUBLISHED", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("PULLOUT", 0)}', className="mb-0")]
            )

        # for total modal
        @self.dash_app.callback(
            [
                Output("total-modal", "is_open"),
                Output("total-modal-content", "children"),
                Output("total-download-link", "data"),
                Output("total-download-btn", "style")  # Control visibility
            ],
            [
                Input("open-total-modal", "n_clicks"),
                Input("close-total-modal", "n_clicks"),
                Input("total-download-btn", "n_clicks")
            ],
            [
                State("total-modal", "is_open"),
                State("college", "value"),
                State("program", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)

            # Apply filters properly
            filter_kwargs = {
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }

            if selected_programs and self.user_role not in ("02", "03"):
                filter_kwargs["selected_programs"] = selected_programs
            else:
                filter_kwargs["selected_colleges"] = selected_colleges  

            filtered_data = get_data_for_modal_contents(**filter_kwargs)
            df_filtered_data = pd.DataFrame(filtered_data) if filtered_data else pd.DataFrame()
            df_filtered_data = df_filtered_data.to_dict(orient="records") if not df_filtered_data.empty else []

            download_btn_style = {"display": "none"} if not df_filtered_data else {"display": "block"}

            if not df_filtered_data:
                if trigger_id == "close-total-modal":
                    return False, "", None, download_btn_style  
                return True, "No data records.", None, download_btn_style  

            selected_columns = {
                "sdg": "SDG",
                "title": "Research Title",
                "concatenated_authors": "Author(s)",
                "program_name": "Program",
                "concatenated_keywords": "Keywords",
                "research_type": "Research Type"
            }

            df_filtered_data = pd.DataFrame(df_filtered_data)[list(selected_columns.keys())] if df_filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))
            df_filtered_data = df_filtered_data.rename(columns=selected_columns)
            table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)

            if trigger_id == "open-total-modal":
                return True, table, None, download_btn_style  

            elif trigger_id == "close-total-modal":
                return False, "", None, download_btn_style  

            elif trigger_id == "total-download-btn":
                if df_filtered_data is not None and not df_filtered_data.empty:
                    download_data = download_file(df_filtered_data, "total_papers")
                    download_message = dbc.Alert(
                        "Your download should begin automatically.",
                        color="success",
                        dismissable=False
                    )
                    return is_open, download_message, download_data, {"display": "none"}

            return is_open, "", None, download_btn_style
        
        # for ready modal
        @self.dash_app.callback(
            [
                Output("ready-modal", "is_open"),
                Output("ready-modal-content", "children"),
                Output("ready-download-link", "data"),
                Output("ready-download-btn", "style")
            ],
            [
                Input("open-ready-modal", "n_clicks"),
                Input("close-ready-modal", "n_clicks"),
                Input("ready-download-btn", "n_clicks")
            ],
            [
                State("ready-modal", "is_open"),
                State("college", "value"),
                State("program", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)

            # Apply filters properly
            filter_kwargs = {
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }

            if selected_programs and self.user_role not in ("02", "03"):
                filter_kwargs["selected_programs"] = selected_programs
            else:
                filter_kwargs["selected_colleges"] = selected_colleges  

            filtered_data = get_data_for_modal_contents(**filter_kwargs)

            df_filtered_data = pd.DataFrame(filtered_data)
            df_filtered_data = df_filtered_data[df_filtered_data["status"] == "READY"] # Only get READY status data

            if df_filtered_data.empty:
                download_btn_style = {"display": "none"}
                if trigger_id == "close-ready-modal":
                    return False, "", None, download_btn_style
                return True, "No data records.", None, download_btn_style
            
            selected_columns = {
                "sdg": "SDG",
                "title": "Research Title",
                "concatenated_authors": "Author(s)",
                "program_name": "Program",
                "concatenated_keywords": "Keywords",
                "research_type": "Research Type"
            }

            # Apply renaming and select only the needed columns
            df_filtered_data = df_filtered_data.rename(columns=selected_columns)

            # Keep only the relevant columns in the correct order
            final_columns = ["SDG", "Research Title", "Author(s)", "Program", "Keywords", "Research Type"]
            df_filtered_data = df_filtered_data[final_columns]

            # Generate the table
            table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)
            download_btn_style = {"display": "block"}

            if trigger_id == "open-ready-modal":
                return True, table, None, download_btn_style

            elif trigger_id == "close-ready-modal":
                return False, "", None, download_btn_style

            elif trigger_id == "ready-download-btn":
                download_data = download_file(df_filtered_data, "ready_papers")
                download_message = dbc.Alert(
                    "Your download should begin automatically.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, download_data, {"display": "none"}

            return is_open, "", None, download_btn_style

        # for submitted modal
        @self.dash_app.callback(
            [
                Output("submitted-modal", "is_open"),
                Output("submitted-modal-content", "children"),
                Output("submitted-download-link", "data"),
                Output("submitted-download-btn", "style")
            ],
            [
                Input("open-submitted-modal", "n_clicks"),
                Input("close-submitted-modal", "n_clicks"),
                Input("submitted-download-btn", "n_clicks")
            ],
            [
                State("submitted-modal", "is_open"),
                State("college", "value"),
                State("program", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)

            # Apply filters properly
            filter_kwargs = {
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }

            if selected_programs and self.user_role not in ("02", "03"):
                filter_kwargs["selected_programs"] = selected_programs
            else:
                filter_kwargs["selected_colleges"] = selected_colleges  

            filtered_data = get_data_for_modal_contents(**filter_kwargs)

            df_filtered_data = pd.DataFrame(filtered_data)
            df_filtered_data = df_filtered_data[df_filtered_data["status"] == "SUBMITTED"] # Only get SUBMITTED status data

            if df_filtered_data.empty:
                download_btn_style = {"display": "none"}
                if trigger_id == "close-submitted-modal":
                    return False, "", None, download_btn_style
                return True, "No data records.", None, download_btn_style

            selected_columns = {
                "sdg": "SDG",
                "title": "Research Title",
                "concatenated_authors": "Author(s)",
                "program_name": "Program",
                "concatenated_keywords": "Keywords",
                "research_type": "Research Type"
            }

            # Apply renaming and select only the needed columns
            df_filtered_data = df_filtered_data.rename(columns=selected_columns)

            # Keep only the relevant columns in the correct order
            final_columns = ["SDG", "Research Title", "Author(s)", "Program", "Keywords", "Research Type"]
            df_filtered_data = df_filtered_data[final_columns]

            # Generate the table
            table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)
            download_btn_style = {"display": "block"}

            if trigger_id == "open-submitted-modal":
                return True, table, None, download_btn_style

            elif trigger_id == "close-submitted-modal":
                return False, "", None, download_btn_style

            elif trigger_id == "submitted-download-btn":
                download_data = download_file(df_filtered_data, "submitted_papers")
                download_message = dbc.Alert(
                    "Your download should begin automatically.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, download_data, {"display": "none"}

            return is_open, "", None, download_btn_style

        # for accepted modal
        @self.dash_app.callback(
            [
                Output("accepted-modal", "is_open"),
                Output("accepted-modal-content", "children"),
                Output("accepted-download-link", "data"),
                Output("accepted-download-btn", "style")
            ],
            [
                Input("open-accepted-modal", "n_clicks"),
                Input("close-accepted-modal", "n_clicks"),
                Input("accepted-download-btn", "n_clicks")
            ],
            [
                State("accepted-modal", "is_open"),
                State("college", "value"),
                State("program", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)

            # Apply filters properly
            filter_kwargs = {
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }

            if selected_programs and self.user_role not in ("02", "03"):
                filter_kwargs["selected_programs"] = selected_programs
            else:
                filter_kwargs["selected_colleges"] = selected_colleges  

            filtered_data = get_data_for_modal_contents(**filter_kwargs)

            df_filtered_data = pd.DataFrame(filtered_data)
            df_filtered_data = df_filtered_data[df_filtered_data["status"] == "ACCEPTED"] # Only get ACCEPTED status data

            if df_filtered_data.empty:
                download_btn_style = {"display": "none"}
                if trigger_id == "close-accepted-modal":
                    return False, "", None, download_btn_style
                return True, "No data records.", None, download_btn_style

            selected_columns = {
                "sdg": "SDG",
                "title": "Research Title",
                "concatenated_authors": "Author(s)",
                "program_name": "Program",
                "concatenated_keywords": "Keywords",
                "research_type": "Research Type"
            }

            # Apply renaming and select only the needed columns
            df_filtered_data = df_filtered_data.rename(columns=selected_columns)

            # Keep only the relevant columns in the correct order
            final_columns = ["SDG", "Research Title", "Author(s)", "Program", "Keywords", "Research Type"]
            df_filtered_data = df_filtered_data[final_columns]

            # Generate the table
            table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)
            download_btn_style = {"display": "block"}

            if trigger_id == "open-accepted-modal":
                return True, table, None, download_btn_style

            elif trigger_id == "close-accepted-modal":
                return False, "", None, download_btn_style

            elif trigger_id == "accepted-download-btn":
                download_data = download_file(df_filtered_data, "accepted_papers")
                download_message = dbc.Alert(
                    "Your download should begin automatically.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, download_data, {"display": "none"}

            return is_open, "", None, download_btn_style
        
        # for published modal
        @self.dash_app.callback(
            [
                Output("published-modal", "is_open"),
                Output("published-modal-content", "children"),
                Output("published-download-link", "data"),
                Output("published-download-btn", "style")
            ],
            [
                Input("open-published-modal", "n_clicks"),
                Input("close-published-modal", "n_clicks"),
                Input("published-download-btn", "n_clicks")
            ],
            [
                State("published-modal", "is_open"),
                State("college", "value"),
                State("program", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)

            # Apply filters properly
            filter_kwargs = {
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }

            if selected_programs and self.user_role not in ("02", "03"):
                filter_kwargs["selected_programs"] = selected_programs
            else:
                filter_kwargs["selected_colleges"] = selected_colleges  

            filtered_data = get_data_for_modal_contents(**filter_kwargs)

            df_filtered_data = pd.DataFrame(filtered_data)
            df_filtered_data = df_filtered_data[df_filtered_data["status"] == "PUBLISHED"] # Only get PUBLLISHED status data

            if df_filtered_data.empty:
                download_btn_style = {"display": "none"}
                if trigger_id == "close-published-modal":
                    return False, "", None, download_btn_style
                return True, "No data records.", None, download_btn_style

            selected_columns = {
                "sdg": "SDG",
                "title": "Research Title",
                "concatenated_authors": "Author(s)",
                "program_name": "Program",
                "concatenated_keywords": "Keywords",
                "research_type": "Research Type"
            }

            # Apply renaming and select only the needed columns
            df_filtered_data = df_filtered_data.rename(columns=selected_columns)

            # Keep only the relevant columns in the correct order
            final_columns = ["SDG", "Research Title", "Author(s)", "Program", "Keywords", "Research Type"]
            df_filtered_data = df_filtered_data[final_columns]

            # Generate the table
            table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)
            download_btn_style = {"display": "block"}

            if trigger_id == "open-published-modal":
                return True, table, None, download_btn_style

            elif trigger_id == "close-published-modal":
                return False, "", None, download_btn_style

            elif trigger_id == "published-download-btn":
                download_data = download_file(df_filtered_data, "published_papers")
                download_message = dbc.Alert(
                    "Your download should begin automatically.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, download_data, {"display": "none"}

            return is_open, "", None, download_btn_style
            
        # for pullout modal
        @self.dash_app.callback(
            [
                Output("pullout-modal", "is_open"),
                Output("pullout-modal-content", "children"),
                Output("pullout-download-link", "data"),
                Output("pullout-download-btn", "style")
            ],
            [
                Input("open-pullout-modal", "n_clicks"),
                Input("close-pullout-modal", "n_clicks"),
                Input("pullout-download-btn", "n_clicks")
            ],
            [
                State("pullout-modal", "is_open"),
                State("college", "value"),
                State("program", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)

            # Apply filters properly
            filter_kwargs = {
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }

            if selected_programs and self.user_role not in ("02", "03"):
                filter_kwargs["selected_programs"] = selected_programs
            else:
                filter_kwargs["selected_colleges"] = selected_colleges  

            filtered_data = get_data_for_modal_contents(**filter_kwargs)

            df_filtered_data = pd.DataFrame(filtered_data)
            df_filtered_data = df_filtered_data[df_filtered_data["status"] == "PULLOUT"] # Only get PULLOUT status data

            if df_filtered_data.empty:
                download_btn_style = {"display": "none"}
                if trigger_id == "close-pullout-modal":
                    return False, "", None, download_btn_style
                return True, "No data records.", None, download_btn_style

            selected_columns = {
                "sdg": "SDG",
                "title": "Research Title",
                "concatenated_authors": "Author(s)",
                "program_name": "Program",
                "concatenated_keywords": "Keywords",
                "research_type": "Research Type"
            }

            # Apply renaming and select only the needed columns
            df_filtered_data = df_filtered_data.rename(columns=selected_columns)

            # Keep only the relevant columns in the correct order
            final_columns = ["SDG", "Research Title", "Author(s)", "Program", "Keywords", "Research Type"]
            df_filtered_data = df_filtered_data[final_columns]

            # Generate the table
            table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)
            download_btn_style = {"display": "block"}

            if trigger_id == "open-pullout-modal":
                return True, table, None, download_btn_style

            elif trigger_id == "close-pullout-modal":
                return False, "", None, download_btn_style

            elif trigger_id == "pullout-download-btn":
                download_data = download_file(df_filtered_data, "pullout_papers")
                download_message = dbc.Alert(
                    "Your download should begin automatically.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, download_data, {"display": "none"}

            return is_open, "", None, download_btn_style

        @self.dash_app.callback(
            [Output('college-container', 'style'),
             Output('program-container', 'style'),
             Output('program', 'options'),
             Output('college', 'value'),
             Output('program', 'value')],
            [Input('url', 'search')]
        )
        def update_filter_visibility(search):
            if not search:
                raise PreventUpdate

            # Parse URL parameters
            parsed = parse_qs(search.lstrip('?'))
            user_role = parsed.get('user-role', ['01'])[0]
            college_id = parsed.get('college', [None])[0]
            program_id = parsed.get('program', [None])[0]

            print(f"User Role: {user_role}, College: {college_id}, Program: {program_id}")

            # Initialize default styles and values
            college_style = {'display': 'none'}  # Hidden by default
            program_style = {'display': 'none'}  # Hidden by default
            program_options = []
            college_value = []
            program_value = []

            if user_role in ["02", "03"]:  # Director and Head Executive
                # Show only college filter
                college_style = {'display': 'block'}
                program_style = {'display': 'none'}
                program_options = []
                college_value = []  # Don't preselect all colleges
                program_value = []
                
            elif user_role == "04":  # College Administrator
                # Show only program filter
                college_style = {'display': 'none'}
                program_style = {'display': 'block'}
                program_options = [
                    {'label': value, 'value': value} 
                    for value in db_manager.get_unique_values_by('program_id', 'college_id', college_id)
                ]
                college_value = [college_id] if college_id else []
                program_value = []
                
            elif user_role == "05":  # Program Administrator
                # Hide both filters
                college_style = {'display': 'none'}
                program_style = {'display': 'none'}
                program_options = []
                college_value = [college_id] if college_id else []
                program_value = [program_id] if program_id else []

            return college_style, program_style, program_options, college_value, program_value

        # Add this callback to reset filters without affecting visualizations
        @self.dash_app.callback(
            [Output('college', 'value', allow_duplicate=True),
             Output('program', 'value', allow_duplicate=True),
             Output('status', 'value', allow_duplicate=True), 
             Output('years', 'value', allow_duplicate=True),
             Output('terms', 'value', allow_duplicate=True)],
            [Input('reset_button', 'n_clicks')],
            [State('url', 'search')],
            prevent_initial_call=True
        )
        def reset_filters(n_clicks, search):
            if not n_clicks:
                raise PreventUpdate
        
            # Parse URL parameters to get role-specific defaults
            parsed = parse_qs(search.lstrip('?')) if search else {}
            user_role = parsed.get('user-role', ['01'])[0]
            college_id = parsed.get('college', [None])[0]
            program_id = parsed.get('program', [None])[0]
            
            print(f"Resetting filters for role: {user_role}")
            
            # Set default values based on user role
            if user_role in ["02", "03"]:  # Director and Head Executive
                college_value = []  # Empty - show all colleges
                program_value = []
            elif user_role == "04":  # College Administrator
                college_value = [college_id] if college_id else []  
                program_value = []  # Reset to no programs selected
            elif user_role == "05":  # Program Administrator
                college_value = [college_id] if college_id else []
                program_value = [program_id] if program_id else []
            else:
                college_value = []
                program_value = []
            
            # Clear all other filters (instead of setting to defaults)
            status_value = []  # Clear status selection
            years_value = self.default_years  # Keep years as default range
            terms_value = []  # Clear terms selection
            
            return college_value, program_value, status_value, years_value, terms_value

        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            [Input("data-refresh-interval", "n_intervals")],
            [State("college", "value"),
             State("program", "value"),
             State("status", "value"),
             State("years", "value"),
             State("terms", "value")]
        )
        def refresh_data(n_intervals, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            """Fetch fresh data at regular intervals and store in shared data store"""
            # Use the predefined list of all statuses
            print(f"Using predefined statuses: {self.default_statuses}")
            
            # Process filters as before
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            
            # If user has selected specific statuses, use those
            # Otherwise use ALL predefined statuses
            if selected_status and len(selected_status) > 0:
                selected_status = ensure_list(selected_status)
            else:
                selected_status = self.default_statuses
            
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            
            # Apply role-based restrictions
            if self.user_role in ["02", "03"]:
                selected_programs = []
            
            # Convert values to lists if they're not already
            selected_colleges = ensure_list(selected_colleges)
            selected_programs = ensure_list(selected_programs)
            selected_status = ensure_list(selected_status)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)
            
            # Apply filters properly
            filter_kwargs = {
                "selected_status": selected_status,
                "selected_years": selected_years,
                "selected_terms": selected_terms
            }

            if selected_programs and self.user_role not in ("02", "03"):
                filter_kwargs["selected_programs"] = selected_programs
            else:
                filter_kwargs["selected_colleges"] = selected_colleges  

            # Get fresh data
            fresh_data = get_data_for_modal_contents(**filter_kwargs)
            
            # Print a refresh notification for debugging
            print(f"Data refreshed at {datetime.now().strftime('%H:%M:%S')} with statuses: {selected_status}")
            
            return fresh_data
        @self.dash_app.callback(
            [Output("terms", "options"), 
             Output("years", "min"),
             Output("years", "max"),
             Output("years", "marks"),
             Output("status", "options")],
            [Input("data-refresh-interval", "n_intervals")],
            [State("college", "value"),
             State("program", "value")]
        )
        def update_filter_options(n_intervals, selected_colleges, selected_programs):
            """Update filter options without changing current selections"""
            # Create a session
            engine = db_manager.engine
            session = Session(engine)
            
            try:
                # Get terms with direct SQL query
                terms_query = session.query(distinct(ResearchOutput.term)).filter(ResearchOutput.term.isnot(None))
                all_terms = sorted([term[0] for term in terms_query.all() if term[0]])
                term_options = [{'label': value, 'value': value} for value in all_terms]
                
                # Get min and max years with direct SQL queries
                min_year_query = session.query(func.min(ResearchOutput.school_year)).filter(ResearchOutput.school_year.isnot(None))
                max_year_query = session.query(func.max(ResearchOutput.school_year)).filter(ResearchOutput.school_year.isnot(None))
                
                min_year = min_year_query.scalar() or 2010  # Default if no data
                max_year = max_year_query.scalar() or 2024  # Default if no data
                
                # Update default years and terms attributes
                self.default_years = [min_year, max_year]
                self.default_terms = all_terms
                
                # Create marks for the year slider
                marks = {
                    min_year: str(min_year),
                    max_year: str(max_year)
                }
                
                # Process college/program filters based on role
                selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
                selected_programs = default_if_empty(selected_programs, self.default_programs)
                
                # Apply role-based restrictions
                if self.user_role in ["02", "03"]:
                    selected_programs = []
                
                # Convert values to lists
                selected_colleges = ensure_list(selected_colleges)
                selected_programs = ensure_list(selected_programs)
                
                # Get status counts directly with SQL query
                status_counts_query = session.query(
                    Status.status, 
                    func.count(Status.status).label('count')
                ).join(
                    Publication, 
                    Status.publication_id == Publication.publication_id
                ).join(
                    ResearchOutput,
                    Publication.research_id == ResearchOutput.research_id
                )
                
                # Apply college/program filters if needed
                if selected_programs and self.user_role not in ("02", "03"):
                    status_counts_query = status_counts_query.filter(
                        ResearchOutput.program_id.in_(selected_programs)
                    )
                elif selected_colleges:
                    status_counts_query = status_counts_query.filter(
                        ResearchOutput.college_id.in_(selected_colleges)
                    )
                
                # Group by status and execute query
                status_counts_result = status_counts_query.group_by(Status.status).all()
                
                # Convert to dictionary
                status_counts = {status: count for status, count in status_counts_result}
                
                # Add READY status count from ResearchOutput table (papers with no Publication)
                ready_count_query = session.query(
                    func.count(ResearchOutput.research_id)
                ).outerjoin(
                    Publication, 
                    ResearchOutput.research_id == Publication.research_id
                ).filter(
                    Publication.research_id == None
                )
                
                # Apply the same filters
                if selected_programs and self.user_role not in ("02", "03"):
                    ready_count_query = ready_count_query.filter(
                        ResearchOutput.program_id.in_(selected_programs)
                    )
                elif selected_colleges:
                    ready_count_query = ready_count_query.filter(
                        ResearchOutput.college_id.in_(selected_colleges)
                    )
                
                ready_count = ready_count_query.scalar() or 0
                if ready_count > 0:
                    status_counts['READY'] = ready_count
                
                # Filter to only include statuses with at least one paper
                visible_statuses = [status for status in self.ALL_STATUSES if status_counts.get(status, 0) > 0]
                
                # Create status options list in the correct order
                status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLOUT']
                status_options = [{'label': 'PULLED-OUT' if value == 'PULLOUT' else value, 'value': value} 
                                 for value in status_order if value in visible_statuses]
                
                print(f"Updated terms filter: {all_terms}")
                print(f"Updated years range: {min_year} to {max_year}")
                print(f"Status counts: {status_counts}")
                print(f"Visible statuses in filter: {visible_statuses}")
                
                # Return all updated values EXCEPT the years.value
                return term_options, min_year, max_year, marks, status_options
            finally:
                session.close()

        # Add another callback that ONLY sets the initial default value of the year slider
        # This callback will NOT be triggered by the interval
        @self.dash_app.callback(
            Output("years", "value"),
            [Input("url", "pathname")],  # Only triggered when the page loads initially
            prevent_initial_call=False
        )
        def set_initial_year_range(pathname):
            """Set the initial default year range only when the page first loads"""
            engine = db_manager.engine
            session = Session(engine)
            
            try:
                # Get min and max years with direct SQL queries
                min_year_query = session.query(func.min(ResearchOutput.school_year)).filter(ResearchOutput.school_year.isnot(None))
                max_year_query = session.query(func.max(ResearchOutput.school_year)).filter(ResearchOutput.school_year.isnot(None))
                
                min_year = min_year_query.scalar() or 2010  # Default if no data
                max_year = max_year_query.scalar() or 2025  # Default if no data
                
                # Set the default years
                default_years = [min_year, max_year]
                
                print(f"Setting initial year range: {default_years}")
                return default_years
            finally:
                session.close()

        @self.dash_app.callback(
            Output("dynamic-header", "children"),
            Input("url", "search"),
            prevent_initial_call=True  
        )
        def update_header(search):
            if search:
                params = parse_qs(search.lstrip("?"))
                user_role = params.get("user-role", ["Guest"])[0]
                college = params.get("college", [""])[0]
                program = params.get("program", [""])[0]

            style = None

            if user_role in ["02", "03"]:
                style = {"display": "block"}
                college = ""
                program = ""
                header = DashboardHeader(left_text=f"{college}", title="INSTITUTIONAL PERFORMANCE DASHBOARD")
            elif user_role == "04":
                style = {"display": "none"}
                self.college = college
                self.program = program
                header = DashboardHeader(left_text=f"{college}", title="INSTITUTIONAL PERFORMANCE DASHBOARD")
            elif user_role == "05":
                style = {"display": "none"}
                self.college = college
                self.program = program
                header = DashboardHeader(left_text=f"{program}", title="INSTITUTIONAL PERFORMANCE DASHBOARD")
            else:
                # Default case for any other role
                header = DashboardHeader(title="INSTITUTIONAL PERFORMANCE DASHBOARD")

            return header

        @self.dash_app.callback(
            Output("timestamp", "children"),
            [Input("data-refresh-interval", "n_intervals")]
        )
        def update_timestamp(n):
            return html.P(f"as of {datetime.now():%B %d, %Y %I:%M %p}", 
                         style={
                             "color": "#6c757d",
                             "fontSize": "16px",
                             "fontWeight": "500",
                             "opacity": "0.8",
                             "whiteSpace": "nowrap",
                             "overflow": "hidden",
                             "textOverflow": "ellipsis"
                         })

    def get_user_specific_data(self, user_id, role_id, college_id=None, program_id=None):
        """
        Get or create user-specific data store in Redis
        """
        # Create a unique key for this user's data
        cache_key = f"inst_perf_dash:{user_id}"
        
        # Check if we already have cached data for this user
        cached_data = self.redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
            
        # Set up initial data object if no cached data exists
        user_data = {
            "user_id": user_id,
            "role_id": role_id,
            "college_id": college_id,
            "program_id": program_id,
            "selected_colleges": [college_id] if college_id else [],
            "selected_programs": [program_id] if program_id else [],
            "selected_status": self.convert_numpy_to_list(self.default_statuses),
            "selected_years": self.convert_numpy_to_list(self.default_years),
            "selected_terms": self.convert_numpy_to_list(self.default_terms)
        }
        
        # Cache the data with a reasonable expiration (e.g., 30 minutes)
        # Use a custom JSON encoder that can handle NumPy types
        try:
            json_data = json.dumps(user_data, cls=NumpyEncoder)
            self.redis_client.setex(cache_key, 1800, json_data)
        except Exception as e:
            print(f"Error serializing user data: {e}")
            # Fall back to basic types if JSON serialization fails
            simplified_data = {
                "user_id": str(user_id),
                "role_id": str(role_id),
                "college_id": str(college_id) if college_id else None,
                "program_id": str(program_id) if program_id else None,
                "selected_colleges": [str(c) for c in ([college_id] if college_id else [])],
                "selected_programs": [str(p) for p in ([program_id] if program_id else [])],
                "selected_status": [str(s) for s in self.default_statuses],
                "selected_years": [int(y) for y in self.default_years],
                "selected_terms": [str(t) for t in self.default_terms]
            }
            self.redis_client.setex(cache_key, 1800, json.dumps(simplified_data))
            return simplified_data
        
        return user_data

    def update_user_data(self, user_id, update_dict):
        """
        Update specific fields in the user's data store
        """
        cache_key = f"inst_perf_dash:{user_id}"
        cached_data = self.redis_client.get(cache_key)
        
        if cached_data:
            user_data = json.loads(cached_data)
            user_data.update(update_dict)
            self.redis_client.setex(cache_key, 1800, json.dumps(user_data))
            return user_data
        
        return None

    def modify_callbacks(self):
        """
        Modify existing callbacks to use user-specific data
        """
        # Add dcc.Store to layout for client-side session data
        if 'shared-data-store' not in [c.id for c in self.dash_app.layout.children if hasattr(c, 'id')]:
            self.dash_app.layout.children.append(dcc.Store(id='user-session-data'))

        # Here we would add/modify callbacks that need user-specific data
        # This would be integrated with your existing callbacks
        
        @self.dash_app.callback(
            Output('user-session-data', 'data'),
            Input('url', 'search'),
            prevent_initial_call=True
        )
        def initialize_user_session(self, search):
            # Parse URL query parameters
            parsed = parse_qs(search.lstrip('?'))
            user_role = parsed.get('user-role', ['02'])[0]  # Default to director
            college_id = parsed.get('college', [None])[0]
            program_id = parsed.get('program', [None])[0]
            
            # Store these values in the class instance
            self.user_role = user_role
            self.college = college_id
            self.program = program_id
            
            print(f"User ID: {getattr(self, 'user_id', 'anonymous')}, Role: {user_role}, College: {college_id}, Program: {program_id}")
            
            # For College Administrator (role 04), get all programs for this college
            if user_role == "04" and college_id:
                self.default_programs = db_manager.get_unique_values_by("program_id", "college_id", college_id)
                print(f"College Administrator role detected - showing programs: {self.default_programs}")
            # For Program Administrator (role 05), restrict to one program
            elif user_role == "05" and program_id:
                self.default_programs = [program_id]
                print(f"Program Administrator role detected - restricting to program: {self.default_programs}")
            # For Directors and Head Executives (roles 02/03), show all colleges
            else:
                self.default_programs = []
                if user_role in ["02", "03"]:
                    print(f"Director/Head Executive role detected - showing all colleges")
            
            # Return the user data for the dcc.Store
            return {
                "user_role": self.user_role,
                "college": self.college,
                "program": self.program,
                "default_programs": self.default_programs
            }