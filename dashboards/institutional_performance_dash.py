import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from . import db_manager
import pandas as pd
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

class Institutional_Performance_Dash:
    def __init__(self, flask_app, college=None, program=None):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/institutional-performance/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"])
        
        self.plot_instance = ResearchOutputPlot()
        self.college = college
        self.program = program
        self.user_role = ""

        # Get default values
        self.palette_dict = db_manager.get_college_colors()
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_programs = []
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_terms = db_manager.get_unique_values('term')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]

        self.selected_colleges = []
        self.selected_programs = []
        
        self.create_layout()
        self.set_callbacks()

    def create_layout(self):
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

        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLOUT']
        status = html.Div(
            [
                dbc.Label("Select Status:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="status",
                    options=[{'label': 'PULLED-OUT' if value == 'PULLOUT' else value, 'value': value} 
                            for value in status_order if value in db_manager.get_unique_values('status')],
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
                    dbc.Col(KPI_Card("Ready for Publication", "0", id="open-ready-modal", icon="fas fa-file-import", color="info"), width="auto"),
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
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),  # 1-second refresh interval
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
    
    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """
        # Reset status, years, and terms
        @self.dash_app.callback(
            [
                Output('status', 'value'),
                Output('years', 'value'),
                Output('terms', 'value')
            ],
            [Input('reset_button', 'n_clicks')],
            prevent_initial_call=True
        )
        def reset_status_years_terms(n_clicks):
            if not n_clicks:
                raise PreventUpdate
            print('RESET (status, years, terms)')
            return [], self.default_years, []
        
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

            return header
        
        @self.dash_app.callback(
            [
                Output('college', 'value'),
                Output('program', 'value'),
                Output('college-container', 'style'),
                Output('program-container', 'style'),
                Output('program', 'options')
            ],
            [
                Input("url", "search"),
                Input("reset_button", "n_clicks")
            ],
            prevent_initial_call=True
        )
        def set_college_and_program(search, reset_clicks):
            college_style = {"display": "block"}
            program_style = {"display": "block"}
            program_options = []
            
            ctx = dash.callback_context
            if not ctx.triggered:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

            trigger = ctx.triggered[0]["prop_id"].split(".")[0]

            if search:
                params = parse_qs(search.lstrip("?"))
                user_role = params.get("user-role", ["Guest"])[0]
                college = params.get("college", [""])[0]
                program = params.get("program", [""])[0]
            else:
                user_role = self.user_role  # Use previously stored value
                college = self.college
                program = self.program

            if trigger == "reset_button":
                if user_role in ["02", "03"]:
                    return [], [], {"display": "block"}, {"display": "none"}, []
                elif user_role == "04":
                    self.default_programs = db_manager.get_unique_values_by("program_id", "college_id", self.college)
                    program_options = [{'label': p, 'value': p} for p in self.default_programs]
                    return self.college, [], {"display": "none"}, {"display": "block"}, program_options
                elif user_role == "05":
                    self.default_programs = db_manager.get_unique_values_by("program_id", "college_id", self.college)
                    program_options = [{'label': p, 'value': p} for p in self.default_programs]
                    return [], self.program, {"display": "none"}, {"display": "none"}, program_options
                else:
                    return [], [], {"display": "block"}, {"display": "block"}, []

            self.college = college
            self.program = program
            self.user_role = user_role

            if user_role in ["02", "03"]:
                college = []  
                program = []  
                program_style = {"display": "none"}

            elif user_role == "04":
                college = self.college  
                program = []  
                self.default_programs = db_manager.get_unique_values_by("program_id", "college_id", self.college)
                program_options = [{'label': p, 'value': p} for p in self.default_programs]
                college_style = {"display": "none"}

            elif user_role == "05":
                college = []
                program = [self.program] if self.program else []
                college_style = {"display": "none"}
                program_style = {"display": "none"}

            return college, program, college_style, program_style, program_options

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
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def refresh_text_buttons(n_intervals, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            if self.user_role in ["02", "03"]:
                selected_programs = [] 

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

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

            filtered_data = get_data_for_text_displays(**filter_kwargs)

            df_filtered_data = pd.DataFrame(filtered_data).to_dict(orient='records')

            status_counts = {d["status"]: d["total_count"] for d in df_filtered_data}
            total_research_outputs = sum(status_counts.values())

            print(f'Final selected_colleges: {selected_colleges}')  # Debugging print
            print(f'Final selected_programs: {selected_programs}')  # Debugging print

            return (
                [html.H3(f'{total_research_outputs}', className="mb-0")],
                [html.H3(f'{status_counts.get("READY", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("SUBMITTED", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("ACCEPTED", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("PUBLISHED", 0)}', className="mb-0")],
                [html.H3(f'{status_counts.get("PULLOUT", 0)}', className="mb-0")]
            )

        @self.dash_app.callback(
            Output('college_line_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_lineplot(selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.plot_instance.update_line_plot(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, self.default_years)
        
        @self.dash_app.callback(
            Output('college_pie_chart', 'figure'),
            [
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_pie_chart(selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.plot_instance.update_pie_chart(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('research_type_bar_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_research_type_bar_plot(selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.plot_instance.update_research_type_bar_plot(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)

        @self.dash_app.callback(
            Output('research_status_bar_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_research_status_bar_plot(selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.plot_instance.update_research_status_bar_plot(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('nonscopus_scopus_bar_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def create_publication_bar_chart(selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.plot_instance.create_publication_bar_chart(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('proceeding_conference_bar_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_publication_format_bar_plot(selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.plot_instance.update_publication_format_bar_plot(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('sdg_bar_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_sdg_chart(selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.plot_instance.update_sdg_chart(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('nonscopus_scopus_graph', 'figure'),
            [
                Input('nonscopus_scopus_tabs', 'value'),
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_scopus_graph(tab, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            if tab == 'line':
                return self.plot_instance.scopus_line_graph(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, self.default_years)
            else:
                return self.plot_instance.scopus_pie_chart(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)
            
        @self.dash_app.callback(
            Output('proceeding_conference_graph', 'figure'),
            [
                Input('proceeding_conference_tabs', 'value'),
                Input('college', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_scopus_graph(tab, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            if tab == 'line':
                return self.plot_instance.publication_format_line_plot(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, self.default_years)
            else:
                return self.plot_instance.publication_format_pie_chart(self.user_role, self.palette_dict, selected_colleges, selected_programs, selected_status, selected_years, selected_terms)
            
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
                State("status", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

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
                    file_path = download_file(df_filtered_data, "total_papers")
                    download_message = dbc.Alert(
                        "The list of research outputs is downloaded. Check your Downloads folder.",
                        color="success",
                        dismissable=False
                    )
                    return is_open, download_message, send_file(file_path), {"display": "none"}  

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
                State("status", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

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
                file_path = download_file(df_filtered_data, "ready_papers")
                download_message = dbc.Alert(
                    "The list of research outputs is downloaded. Check your Downloads folder.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, send_file(file_path), {"display": "none"}

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
                State("status", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

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
                file_path = download_file(df_filtered_data, "submitted_papers")
                download_message = dbc.Alert(
                    "The list of research outputs is downloaded. Check your Downloads folder.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, send_file(file_path), {"display": "none"}

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
                State("status", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

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
                file_path = download_file(df_filtered_data, "accepted_papers")
                download_message = dbc.Alert(
                    "The list of research outputs is downloaded. Check your Downloads folder.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, send_file(file_path), {"display": "none"}

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
                State("status", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

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
                file_path = download_file(df_filtered_data, "published_papers")
                download_message = dbc.Alert(
                    "The list of research outputs is downloaded. Check your Downloads folder.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, send_file(file_path), {"display": "none"}

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
                State("status", "value"),
                State("years", "value"),
                State("terms", "value")
            ],
            prevent_initial_call=True
        )
        def toggle_modal(open_clicks, close_clicks, download_clicks, is_open, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
            ctx = dash.callback_context
            trigger_id = ctx.triggered_id

            if self.user_role in ["02", "03"]:
                selected_programs = []

            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

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
                file_path = download_file(df_filtered_data, "pullout_papers")
                download_message = dbc.Alert(
                    "The list of research outputs is downloaded. Check your Downloads folder.",
                    color="success",
                    dismissable=False
                )
                return is_open, download_message, send_file(file_path), {"display": "none"}

            return is_open, "", None, download_btn_style