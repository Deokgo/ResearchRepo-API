from dash import Dash, html, dcc, dash_table
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from urllib.parse import parse_qs, urlparse
from . import db_manager
from database.institutional_performance_queries import get_data_for_performance_overview, get_data_for_research_type_bar_plot, get_data_for_research_status_bar_plot, get_data_for_scopus_section, get_data_for_jounal_section, get_data_for_sdg, get_data_for_modal_contents, get_data_for_text_displays
from components.DashboardHeader import DashboardHeader

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

def ensure_list(value):
    """
    Ensures that the given value is always returned as a list.
    - If it's a NumPy array, convert it to a list.
    - If it's a string, wrap it in a list.
    - If it's already a list, return as is.
    """
    if isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, str):
        return [value]
    return value  # Return as is if already a list or another type

class CollegeDashApp:
    def __init__(self, server, title=None, college=None, program=None, **kwargs):
        self.dash_app = Dash(__name__,
                             server=server,
                             url_base_pathname=kwargs.get('url_base_pathname', '/sample/'),
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.title = title
        self.college = college
        self.program = program

        self.palette_dict = db_manager.get_college_colors()
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_programs = []
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_terms = db_manager.get_unique_values('term')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]

        self.set_layout()
        self.add_callbacks()

        self.all_sdgs = [
            'SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 
            'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 
            'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17'
        ]

    def set_layout(self):
        """Common layout shared across all dashboards."""

        college = html.Div(
            [
                dbc.Label("Select College:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=self.college if self.college else [],  # Default to self.college or empty list
                    inline=True,
                ),
            ],
            className="mb-4",
            style={"display": "none", "opacity": "0.5"},  # Disable interaction and style for visual feedback
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
                            dcc.Tab(label='Line Chart', value='line', style={"font-size": "10px"}),
                            dcc.Tab(label='Pie Chart', value='pie', style={"font-size": "12px"})
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
                            dcc.Tab(label='Line Chart', value='line', style={"font-size": "10px"}),
                            dcc.Tab(label='Pie Chart', value='pie', style={"font-size": "12px"})
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

        self.dash_app.layout = html.Div([
            # URL tracking
            dcc.Location(id='url', refresh=False),
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),  # 1 second
            dcc.Store(id="shared-data-store"),  # Shared data store to hold the updated dataset
            dbc.Container([
                dbc.Row([
                    # Sidebar controls
                    dbc.Col(
                        controls,
                        width={"size": 2, "order": 1},  # Adjust width for sidebar
                        style={"height": "100%", "padding": "0", "overflow-y": "auto"}
                    ),
                    # Main dashboard content
                    dbc.Col(
                        html.Div([  # Wrapper div for horizontal scrolling
                            html.Div(id="dynamic-header"),
                            # Content of the Dash App
                            # Buttons in a single row
                            dbc.Row([
                                dbc.Col(dbc.Button("Research Output(s)", id="open-total-modal", color="primary", size="lg", n_clicks=0, style={
                                    "height": "100px", "width": "150px", "border-radius": "15px", "font-weight": "bold", "font-size": "14px",
                                    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)", "transition": "background-color 0.3s ease, transform 0.2s ease"
                                }), width="auto"),
                                dbc.Col(dbc.Button("Ready for Publication", id="open-ready-modal", color="info", size="lg", n_clicks=0, style={
                                    "height": "100px", "width": "150px", "border-radius": "15px", "font-weight": "bold", "font-size": "14px",
                                    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)", "transition": "background-color 0.3s ease, transform 0.2s ease"
                                }), width="auto"),
                                dbc.Col(dbc.Button("Submitted Paper(s)", id="open-submitted-modal", color="warning", size="lg", n_clicks=0, style={
                                    "height": "100px", "width": "150px", "border-radius": "15px", "font-weight": "bold", "font-size": "14px",
                                    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)", "transition": "background-color 0.3s ease, transform 0.2s ease"
                                }), width="auto"),
                                dbc.Col(dbc.Button("Accepted Paper(s)", id="open-accepted-modal", color="success", size="lg", n_clicks=0, style={
                                    "height": "100px", "width": "150px", "border-radius": "15px", "font-weight": "bold", "font-size": "14px",
                                    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)", "transition": "background-color 0.3s ease, transform 0.2s ease"
                                }), width="auto"),
                                dbc.Col(dbc.Button("Published Paper(s)", id="open-published-modal", color="danger", size="lg", n_clicks=0, style={
                                    "height": "100px", "width": "150px", "border-radius": "15px", "font-weight": "bold", "font-size": "14px",
                                    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)", "transition": "background-color 0.3s ease, transform 0.2s ease"
                                }), width="auto"),
                                dbc.Col(dbc.Button("Pulled-out Paper(s)", id="open-pullout-modal", color="secondary", size="lg", n_clicks=0, style={
                                    "height": "100px", "width": "150px", "border-radius": "15px", "font-weight": "bold", "font-size": "14px",
                                    "box-shadow": "0 4px 6px rgba(0, 0, 0, 0.1)", "transition": "background-color 0.3s ease, transform 0.2s ease"
                                }), width="auto"),
                            ], className="mb-2", justify="center"),  # Centering buttons in a single row
                            
                            # Modals for each button
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Research Output(s)")),
                                dbc.ModalBody(id="total-modal-content"),
                                dbc.ModalFooter(dbc.Button("Close", id="close-total-modal", className="ms-auto", n_clicks=0)),
                            ], id="total-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Ready for Publication")),
                                dbc.ModalBody(id="ready-modal-content"),
                                dbc.ModalFooter(dbc.Button("Close", id="close-ready-modal", className="ms-auto", n_clicks=0)),
                            ], id="ready-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Submitted Paper(s)")),
                                dbc.ModalBody(id="submitted-modal-content"),
                                dbc.ModalFooter(dbc.Button("Close", id="close-submitted-modal", className="ms-auto", n_clicks=0)),
                            ], id="submitted-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Accepted Paper(s)")),
                                dbc.ModalBody(id="accepted-modal-content"),
                                dbc.ModalFooter(dbc.Button("Close", id="close-accepted-modal", className="ms-auto", n_clicks=0)),
                            ], id="accepted-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Published Paper(s)")),
                                dbc.ModalBody(id="published-modal-content"),
                                dbc.ModalFooter(dbc.Button("Close", id="close-published-modal", className="ms-auto", n_clicks=0)),
                            ], id="published-modal", scrollable=True, is_open=False, size="xl"),
                            
                            dbc.Modal([
                                dbc.ModalHeader(dbc.ModalTitle("Pulled-out Paper(s)")),
                                dbc.ModalBody(id="pullout-modal-content"),
                                dbc.ModalFooter(dbc.Button("Close", id="close-pullout-modal", className="ms-auto", n_clicks=0)),
                            ], id="pullout-modal", scrollable=True, is_open=False, size="xl"),

                            # Tabs
                            dcc.Tabs(
                                id="dashboard-tabs",
                                value='main',
                                children=[
                                    dcc.Tab(
                                        label="Performance Overview",
                                        value="main",
                                        children=[
                                            html.Div(main_dash, style={'border': '2px solid #dcdcdc', 'padding': '5px'})
                                        ],
                                        style={"font-size": "14px"},
                                        selected_style={'backgroundColor': 'blue', 'color': 'white', "font-size": "14px"}
                                    ),
                                    dcc.Tab(
                                        label="Research Statuses and Types",
                                        value="sub1",
                                        children=[
                                            html.Div(sub_dash1, style={'border': '2px solid #dcdcdc', 'padding': '5px'})
                                        ],
                                        style={"font-size": "14px"},
                                        selected_style={'backgroundColor': 'blue', 'color': 'white', "font-size": "14px"}
                                    ),
                                    dcc.Tab(
                                        label="Scopus and Non-Scopus",
                                        value="sub2",
                                        children=[
                                            html.Div(sub_dash2, style={'border': '2px solid #dcdcdc', 'padding': '5px'})
                                        ],
                                        style={"font-size": "14px"},
                                        selected_style={'backgroundColor': 'blue', 'color': 'white', "font-size": "14px"}
                                    ),
                                    dcc.Tab(
                                        label="SDG Distribution",
                                        value="sub3",
                                        children=[
                                            html.Div(sub_dash3, style={'border': '2px solid #dcdcdc', 'padding': '5px'})
                                        ],
                                        style={"font-size": "14px"},
                                        selected_style={'backgroundColor': 'blue', 'color': 'white', "font-size": "14px"}
                                    ),
                                    dcc.Tab(
                                        label="Publication Types",
                                        value="sub4",
                                        children=[
                                            html.Div(sub_dash4, style={'border': '2px solid #dcdcdc', 'padding': '5px'})
                                        ],
                                        style={"font-size": "14px"},
                                        selected_style={'backgroundColor': 'blue', 'color': 'white', "font-size": "14px"}
                                    ),
                                ],
                                style={'width': '100%', 'display': 'flex', 'justify-content': 'center', 'fontSize': '12px'}
                            ),
                        ], style={
                            "height": "100%",
                            "display": "flex",
                            "flex-direction": "column",
                            "overflow-x": "hidden",  # Prevent horizontal overflow
                            "overflow-y": "auto",  # Enable vertical scrolling
                            "padding": "10px",
                        }),
                        width={"size": 10, "order": 2},  # Adjust main content width
                        style={
                            "height": "100%",
                            "display": "flex",
                            "flex-direction": "column"
                        }
                    ),
                ], style={
                    "height": "100vh",
                    "display": "flex",
                    "flex-wrap": "nowrap",  # Prevent wrapping to maintain layout
                }),
            ], fluid=True, style={
                "height": "100vh",
                "margin": "0",
                "padding": "0",
            }),
        ], style={
            "height": "100vh",
            "margin": "0",
            "padding": "0",
            "overflow": "hidden",  # Prevent outer scrolling
        })


    def create_display_card(self, title, value):
        """
        Create a responsive display card for showing metrics.
        """
        return html.Div([
            html.Div([
                html.H5(title, style={'textAlign': 'center', 'fontSize': '1rem'}),  # Smaller title
                html.H3(value, style={'textAlign': 'center', 'fontSize': '1.5rem'})  # Adjusted font size
            ], style={
                "border": "2px solid #0A438F",
                "borderRadius": "10px",
                "padding": "8px",
                "width": "140px",  # Smaller fixed size
                "height": "120px",
                "display": "flex",
                "flexDirection": "column",
                "justifyContent": "center",
                "alignItems": "center",
                "margin": "0",
                "minWidth": "120px",  # Ensures minimum size for responsiveness
                "maxWidth": "180px",  # Prevents excessive stretching
            })
        ])

    def get_program_colors(self, df):
        unique_programs = df['program_id'].unique()
        if not hasattr(self, "program_colors"):
            self.program_colors = {}  # Initialize if not exists

        available_colors = px.colors.qualitative.Set1  # Choose a color palette

        for i, program in enumerate(unique_programs):
            if program not in self.program_colors:
                self.program_colors[program] = available_colors[i % len(available_colors)]
                
    def update_line_plot(self, selected_program, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_program = ensure_list(selected_program)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_performance_overview
        filtered_data_with_term = get_data_for_performance_overview(None, selected_program, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        if len(selected_program) == 1:
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = f'Number of Research Outputs for {selected_program[0]}'
        else:
            df = df[df['program_id'].isin(selected_program)]
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = 'Number of Research Outputs per Program'
        
        # Generate a dynamic color mapping based on unique values in the color_column
        self.get_program_colors(df)
        color_discrete_map = self.program_colors
        
        # Generate the line plot
        fig_line = px.line(
            grouped_df,
            x='year',
            y='TitleCount',
            color=color_column,
            markers=True,
            color_discrete_map=color_discrete_map
        )
        
        # Update the layout for aesthetics and usability
        fig_line.update_layout(
            title=dict(text=title, font=dict(size=12)),  # Smaller title
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400
        )
        
        return fig_line

    def update_pie_chart(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_performance_overview
        filtered_data_with_term = get_data_for_performance_overview(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        if len(selected_programs) == 1:
            # Handle single program selection
            program_id = selected_programs[0]
            filtered_df = df[df['program_id'] == program_id]
            detail_counts = filtered_df.groupby('year').size().reset_index(name='count')  # Group by year and count
            title = f"Research Output Distribution for {program_id}"

            # Create the pie chart for yearly contribution
            fig_pie = px.pie(
                data_frame=detail_counts,
                names='year',
                values='count',
                color='year',
                labels={'year': 'Year', 'count': 'Number of Research Outputs'},
            )
        else:
            # Handle multiple programs
            detail_counts = df.groupby('program_id').size().reset_index(name='count')
            title = "Research Outputs per Program"

            # Generate a dynamic color mapping based on unique values in the `program_id`
            self.get_program_colors(df)
            color_discrete_map = self.program_colors

            # Create the pie chart
            fig_pie = px.pie(
                data_frame=detail_counts,
                names='program_id',
                values='count',
                color='program_id',
                color_discrete_map=color_discrete_map,
                labels={'program_id': 'Program', 'count': 'Number of Research Outputs'},
            )

        # Update layout
        fig_pie.update_layout(
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            title=dict(text=title, font=dict(size=12)),  # Smaller title
        )

        return fig_pie
    
    def update_research_type_bar_plot(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_research_type_bar_plot
        filtered_data_with_term = get_data_for_research_type_bar_plot(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        if df.empty:
            return px.bar(title="No data available")
        
        fig = go.Figure()

            #self.get_program_colors(df) 
        status_count = df.groupby(['research_type', 'program_id']).size().reset_index(name='Count')
        pivot_df = status_count.pivot(index='research_type', columns='program_id', values='Count').fillna(0)

        sorted_programs = sorted(pivot_df.columns)
        title = f"Comparison of Research Output Type Across Programs"

        self.get_program_colors(df)
        color_discrete_map = self.program_colors

        for program in sorted_programs:
            fig.add_trace(go.Bar(
                x=pivot_df.index,
                y=pivot_df[program],
                name=program,
                marker_color=color_discrete_map[program]
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title=dict(text='Research Type', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            title=dict(text=title, font=dict(size=12)),  # Smaller title
        )

        return fig
    
    def update_research_status_bar_plot(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_research_status_bar_plot
        filtered_data_with_term = get_data_for_research_status_bar_plot(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        if df.empty:
            return px.bar(title="No data available")
        
        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLOUT']

        fig = go.Figure()

        status_count = df.groupby(['status', 'program_id']).size().reset_index(name='Count')
        pivot_df = status_count.pivot(index='status', columns='program_id', values='Count').fillna(0)

        sorted_programs = sorted(pivot_df.columns)
        title = f"Comparison of Research Status Across Program/s"

        self.get_program_colors(df)
        color_discrete_map = self.program_colors

        for program in sorted_programs:
            fig.add_trace(go.Bar(
                x=pivot_df.index,
                y=pivot_df[program],
                name=program,
                marker_color=color_discrete_map[program]
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title=dict(text='Research Status', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            title=dict(text=title, font=dict(size=12)),  # Smaller title,
            xaxis=dict(
                tickvals=status_order,  # This should match the unique statuses in pivot_df index
                ticktext=status_order    # This ensures that the order of the statuses is displayed correctly
            )
        )

        # Ensure the x-axis is sorted in the defined order
        fig.update_xaxes(categoryorder='array', categoryarray=status_order)
        return fig
    
    def update_sdg_chart(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_sdg
        filtered_data_with_term = get_data_for_sdg(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        if df.empty:
            return px.scatter(title="No data available")

        df_copy = df.copy()

        df_copy = df_copy.set_index('program_id')['sdg'].str.split(';').apply(pd.Series).stack().reset_index(name='sdg')
        df_copy['sdg'] = df_copy['sdg'].str.strip()
        df_copy = df_copy.drop(columns=['level_1'])
        sdg_count = df_copy.groupby(['sdg', 'program_id']).size().reset_index(name='Count')
        title = f'Distribution of SDG-Targeted Research Across Programs'

        if sdg_count.empty:
            print("Pivot DataFrame is empty after processing")
            return px.scatter(title="No data available")

        fig = go.Figure()

        # Generate a dynamic color mapping based on unique values in the `program_id`
        self.get_program_colors(df)
        color_discrete_map = self.program_colors

        for program in sdg_count['program_id'].unique():
            program_data = sdg_count[sdg_count['program_id'] == program]
            fig.add_trace(go.Scatter(
                x=program_data['sdg'],
                y=program_data['program_id'],
                mode='markers',
                marker=dict(
                    size=program_data['Count'],
                    color=color_discrete_map.get(program, 'grey'),
                    sizemode='area',
                    sizeref=2. * max(sdg_count['Count']) / (100**2),  # Bubble size scaling
                    sizemin=4
                ),
                name=program
            ))

        fig.update_layout(
            xaxis_title='SDG Targeted',
            yaxis_title='Programs',
            title=title,
            xaxis=dict(
                tickvals=self.all_sdgs,
                ticktext=self.all_sdgs
            ),
            yaxis=dict(autorange="reversed"),
            showlegend=True
        )
        
        return fig


    def create_publication_bar_chart(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_scopus_section
        filtered_data_with_term = get_data_for_scopus_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        df = df[df['scopus'] != 'N/A']
        self.get_program_colors(df)
        grouped_df = df.groupby(['scopus', 'program_id']).size().reset_index(name='Count')
        x_axis = 'program_id'
        xaxis_title = 'Programs'
        title = f'Scopus vs. Non-Scopus per Program'
        
        fig_bar = px.bar(
            grouped_df,
            x=x_axis,
            y='Count',
            color='scopus',
            barmode='group',
            color_discrete_map=self.palette_dict,
            labels={'scopus': 'Scopus vs. Non-Scopus'}
        )
        
        fig_bar.update_layout(
            title=dict(text=title, font=dict(size=12)),  # Smaller title,
            xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=400
        )

        return fig_bar
    
    def update_publication_format_bar_plot(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_jounal_section
        filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

        grouped_df = df.groupby(['journal', 'program_id']).size().reset_index(name='Count')
        x_axis = 'program_id'
        xaxis_title = 'Programs'
        title = f'Publication Types per Program'

        fig_bar = px.bar(
            grouped_df,
            x=x_axis,
            y='Count',
            color='journal',
            barmode='group',
            color_discrete_map=self.palette_dict,
            labels={'journal': 'Publication Type'}
        )
        
        fig_bar.update_layout(
            title=dict(text=title, font=dict(size=12)),  # Smaller title,
            xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=400
        )

        return fig_bar
    
    def scopus_line_graph(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_scopus_section
        filtered_data_with_term = get_data_for_scopus_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        # Filter out rows where 'scopus' is 'N/A'
        df = df[df['scopus'] != 'N/A']

        # Group data by 'scopus' and 'year'
        grouped_df = df.groupby(['scopus', 'year']).size().reset_index(name='Count')

        # Ensure year and count are numeric
        grouped_df['year'] = grouped_df['year'].astype(int)
        grouped_df['Count'] = grouped_df['Count'].astype(int)

        # Create the line chart with markers
        fig_line = px.line(
            grouped_df,
            x='year',
            y='Count',
            color='scopus',
            color_discrete_map=self.palette_dict,
            labels={'scopus': 'Scopus vs. Non-Scopus'},
            markers=True  # Ensure points are visible even if no lines
        )

        # Update layout for smaller text and responsive UI
        fig_line.update_traces(
            line=dict(width=1.5),  # Thinner lines
            marker=dict(size=5)  # Smaller marker points
        )

        fig_line.update_layout(
            title=dict(text='Scopus vs. Non-Scopus Publications Over Time', font=dict(size=12)),  # Smaller title
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=300,  # Smaller chart height
            margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins for compact display
            xaxis=dict(
                type='linear',  
                tickangle=-45,  # Angled labels for better fit
                automargin=True,  # Prevent label overflow
                tickfont=dict(size=10)  # Smaller x-axis text
            ),
            yaxis=dict(
                automargin=True,  
                tickfont=dict(size=10)  # Smaller y-axis text
            ),
            legend=dict(font=dict(size=9)),  # Smaller legend text
        )

        return fig_line
    
    def scopus_pie_chart(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_scopus_section
        filtered_data_with_term = get_data_for_scopus_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        # Filter out rows where 'scopus' is 'N/A'
        df = df[df['scopus'] != 'N/A']

        # Group data by 'scopus' and sum the counts
        grouped_df = df.groupby(['scopus']).size().reset_index(name='Count')

        # Create the pie chart
        fig_pie = px.pie(
            grouped_df,
            names='scopus',
            values='Count',
            color='scopus',
            color_discrete_map=self.palette_dict,
            labels={'scopus': 'Scopus vs. Non-Scopus'}
        )

        # Update layout for a smaller and more responsive design
        fig_pie.update_traces(
            textfont=dict(size=9),  # Smaller text inside the pie
            insidetextfont=dict(size=9),  # Smaller text inside the pie
            marker=dict(line=dict(width=0.5))  # Thinner slice borders
        )

        fig_pie.update_layout(
            title=dict(text='Scopus vs. Non-Scopus Research Distribution', font=dict(size=12)),  # Smaller title
            template='plotly_white',
            height=300,  # Smaller chart height
            margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins
            legend=dict(font=dict(size=9)),  # Smaller legend text
        )

        return fig_pie


    def publication_format_line_plot(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_jounal_section
        filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        # Filter out rows with 'unpublished' journals and 'PULLOUT' status
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

        # Group data by 'journal' and 'year'
        grouped_df = df.groupby(['journal', 'year']).size().reset_index(name='Count')

        # Ensure year and count are numeric
        grouped_df['year'] = grouped_df['year'].astype(int)
        grouped_df['Count'] = grouped_df['Count'].astype(int)

        # Create the line chart with markers
        fig_line = px.line(
            grouped_df,
            x='year',
            y='Count',
            color='journal',
            color_discrete_map=self.palette_dict,
            labels={'journal': 'Publication Type'},
            markers=True  # Ensure points are visible even if no lines
        )

        # Update layout for smaller text and responsive UI
        fig_line.update_traces(
            line=dict(width=1.5),  # Thinner lines
            marker=dict(size=5)  # Smaller marker points
        )

        fig_line.update_layout(
            title=dict(text='Publication Types Over Time', font=dict(size=12)),  # Smaller title
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=300,  # Smaller chart height
            margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins for compact display
            xaxis=dict(
                type='linear',  
                tickangle=-45,  # Angled labels for better fit
                automargin=True,  # Prevent label overflow
                tickfont=dict(size=10)  # Smaller x-axis text
            ),
            yaxis=dict(
                automargin=True,  
                tickfont=dict(size=10)  # Smaller y-axis text
            ),
            legend=dict(font=dict(size=9)),  # Smaller legend text
        )

        return fig_line
    
    def publication_format_pie_chart(self, selected_programs, selected_status, selected_years, selected_terms):
        # Ensure selected_program is a standard Python list or array
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Fetch data using get_data_for_jounal_section
        filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)

        # Filter out rows with 'unpublished' journals and 'PULLOUT' status
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

        # Group data by 'journal' and sum the counts
        grouped_df = df.groupby(['journal']).size().reset_index(name='Count')

        # Create the pie chart
        fig_pie = px.pie(
            grouped_df,
            names='journal',
            values='Count',
            color='journal',
            color_discrete_map=self.palette_dict,
            labels={'journal': 'Publication Type'}
        )

        # Update layout for a smaller and more responsive design
        fig_pie.update_traces(
            textfont=dict(size=9),  # Smaller text inside the pie
            insidetextfont=dict(size=9),  # Smaller text inside the pie
            marker=dict(line=dict(width=0.5))  # Thinner slice borders
        )

        fig_pie.update_layout(
            title=dict(text='Publication Type Distribution', font=dict(size=12)),  # Smaller title
            template='plotly_white',
            height=300,  # Smaller chart height
            margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins
            legend=dict(font=dict(size=9)),  # Smaller legend text
        )

        return fig_pie

    def add_callbacks(self):
        @self.dash_app.callback(
        Output('college', 'value'),  # Update the checklist value
        Input('url', 'search'),  # Listen to URL changes
        prevent_initial_call=True   
        )
        def update_college_from_url(search):
            if not search:
                return self.default_colleges  # Default value if no parameters are provided

            # Parse the URL query parameters
            params = parse_qs(urlparse(search).query)

            # Extract the `college` parameter if it exists
            college_values = params.get('college', self.default_colleges)  # Returns a list or default
            self.college = college_values  # Dynamically update self.college

            return college_values

        @self.dash_app.callback(
            Output('college_line_plot', 'figure'),  # Update the line plot
            [
                Input('program', 'value'),  # Trigger when the college checklist changes
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_lineplot(selected_programs, selected_status, selected_years, selected_terms):
            # Fallback to defaults if inputs are not provided
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            # Update the line plot with filtered data
            return self.update_line_plot(selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('college_pie_chart', 'figure'),
            [Input('program', 'value'), Input('status', 'value'), Input('years', 'value'), Input('terms', 'value')]
        )
        def update_pie_chart_callback(selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_pie_chart(selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('research_type_bar_plot', 'figure'),
            [
                Input('program', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_research_type_bar_plot(selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_research_type_bar_plot(selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('research_status_bar_plot', 'figure'),
            [
                Input('program', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_research_status_bar_plot(selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_research_status_bar_plot(selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('sdg_bar_plot', 'figure'),
            [
                Input('program', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_sdg_chart(selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_sdg_chart(selected_programs, selected_status, selected_years, selected_terms)

        @self.dash_app.callback(
            Output('nonscopus_scopus_bar_plot', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('terms', 'value')]
        )
        def create_publication_bar_chart(selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.create_publication_bar_chart(selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('proceeding_conference_bar_plot', 'figure'),
            [
                Input('program', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_publication_format_bar_plot(selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_publication_format_bar_plot(selected_programs, selected_status, selected_years, selected_terms)

        @self.dash_app.callback(
        Output('program', 'options'),  # Update the program options based on the selected college
        Input('college', 'value')  # Trigger when the college checklist changes
        )
        def update_program_options(selected_colleges):
            # If no college is selected, return empty options
            if not selected_colleges:
                return []

            # Get the programs for the selected college
            program_options = db_manager.get_unique_values_by('program_id', 'college_id', selected_colleges[0])

            # Return the options for the program checklist
            return [{'label': program, 'value': program} for program in program_options]

        @self.dash_app.callback(
            [
                Output("program", "value"),
                Output("status", "value"),
                Output('terms', 'value'),
                Output("years", "value")
            ],
            Input("reset_button", "n_clicks"),
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        
        # Callback to update content based on the user role and other URL parameters
        @self.dash_app.callback(
            [
                Output("open-total-modal", "children"),
                Output("open-ready-modal", "children"),
                Output("open-submitted-modal", "children"),
                Output("open-accepted-modal", "children"),
                Output("open-published-modal", "children"),
                Output("open-pullout-modal", "children"),
                Output("dynamic-header", "children"),
            ],
            [
                Input("url", "search"),  # Capture query string from URL
                Input("data-refresh-interval", "n_intervals"),
                Input("program", "value"),
                Input("status", "value"),
                Input("years", "value"),
                Input("terms", "value"),
            ]
        )
        def update_dashboard(url_search, n_intervals, selected_programs, selected_status, selected_years, selected_terms):
            if not url_search:
                return (
                    html.H3("Welcome Guest! Please log in."),
                    html.H3("College: Unknown"),
                    "0 Research Output(s)",
                    "0 Ready for Publication",
                    "0 Submitted Paper(s)",
                    "0 Accepted Paper(s)",
                    "0 Published Paper(s)",
                    "0 Pulled-out Paper(s)",
                    DashboardHeader(left_text="", title="INSTITUTIONAL PERFORMANCE DASHBOARD", right_text="Unknown"),
                )

            params = dict(parse_qs(url_search.lstrip("?")))
            user_role = params.get("user-role", ["06"])[0]  # Default to '06' (guest)
            college = params.get("college", ["Unknown College"])[0]
            program = params.get("program", ["Unknown Program"])[0]
            
            # Set class-level variables
            self.college = college
            self.program = program
            self.default_programs = db_manager.get_unique_values_by("program_id", "college_id", self.college)

            # Apply default selections
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years or self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            selected_programs = ensure_list(selected_programs)
            selected_status = ensure_list(selected_status)
            selected_years = ensure_list(selected_years)
            selected_terms = ensure_list(selected_terms)

            # Get filtered data
            filtered_data = get_data_for_text_displays(
                None,
                selected_programs=selected_programs, 
                selected_status=selected_status,
                selected_years=selected_years,
                selected_terms=selected_terms
            )

            df_filtered_data = pd.DataFrame(filtered_data).to_dict(orient='records')
            status_counts = {d["status"]: d["total_count"] for d in df_filtered_data}
            total_research_outputs = sum(status_counts.values())
            
            # Set header based on user role
            if user_role == "02":
                view = "RPCO Director"
                college, program = "", ""
                style = {"display": "block"}
            elif user_role == "04":
                view = "College Dean"
                style = {"display": "none"}
            else:
                view = "Unknown"

            header = DashboardHeader(left_text=college, title="INSTITUTIONAL PERFORMANCE DASHBOARD", right_text=view)

            return (
                f"{total_research_outputs} Research Output(s)",
                f"{status_counts.get('READY', 0)} Ready for Publication",
                f"{status_counts.get('SUBMITTED', 0)} Submitted Paper(s)",
                f"{status_counts.get('ACCEPTED', 0)} Accepted Paper(s)",
                f"{status_counts.get('PUBLISHED', 0)} Published Paper(s)",
                f"{status_counts.get('PULLOUT', 0)} Pulled-out Paper(s)",
                header,
            )
        
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_shared_data_store(n_intervals):
            updated_data = db_manager.get_all_data()
            return updated_data.to_dict('records')
       
        @self.dash_app.callback(
            Output('nonscopus_scopus_graph', 'figure'),
            [
                Input('nonscopus_scopus_tabs', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_scopus_graph(tab, selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            if tab == 'line':
                return self.scopus_line_graph(selected_programs, selected_status, selected_years, selected_terms)
            else:
                return self.scopus_pie_chart(selected_programs, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('proceeding_conference_graph', 'figure'),
            [
                Input('proceeding_conference_tabs', 'value'),
                Input('program', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_proceeding_conference_graph(tab, selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            if tab == 'line':
                return self.publication_format_line_plot(selected_programs, selected_status, selected_years, selected_terms)
            else:
                return self.publication_format_pie_chart(selected_programs, selected_status, selected_years, selected_terms)
            
        # for total modal
        @self.dash_app.callback(
            Output("total-modal", "is_open"),
            Output("total-modal-content", "children"),
            Input("open-total-modal", "n_clicks"),
            Input("close-total-modal", "n_clicks"),
            State("total-modal", "is_open"),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value')
        )
        def toggle_modal(open_clicks, close_clicks, is_open, selected_programs, selected_status, selected_years, selected_terms):

            ctx = dash.callback_context
            if not ctx.triggered:
                return is_open, ""
            
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "open-total-modal":
                selected_programs = default_if_empty(selected_programs, self.default_programs)
                selected_status = default_if_empty(selected_status, self.default_statuses)
                selected_years = selected_years if selected_years else self.default_years
                selected_terms = default_if_empty(selected_terms, self.default_terms)

                selected_programs = ensure_list(selected_programs)
                selected_status = ensure_list(selected_status)
                selected_years = ensure_list(selected_years)
                selected_terms = ensure_list(selected_terms)

                # Apply filters
                filtered_data = get_data_for_modal_contents(
                    None,
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                df_filtered_data = pd.DataFrame(filtered_data)

                # Ensure df_filtered_data is a valid DataFrame or empty list
                if df_filtered_data is None or len(df_filtered_data) == 0:
                    return True, "No data records."
                elif isinstance(df_filtered_data, pd.DataFrame):
                    df_filtered_data = df_filtered_data.to_dict(orient="records")

                # Choose specific columns to display
                selected_columns = {
                    "research_id": "Research ID",
                    "title": "Research Title",
                    "concatenated_keywords": "Keywords",
                    "concatenated_authors": "Author(s)",
                    "sdg": "SDG",
                    "college_id": "College",
                    "program_name": "Program",
                    "research_type": "Research Type"
                }
                
                # Convert to DataFrame and filter selected columns
                if filtered_data:
                    filtered_df = pd.DataFrame(filtered_data)[list(selected_columns.keys())]
                    filtered_df = filtered_df.rename(columns=selected_columns)  # Rename columns
                else:
                    filtered_df = pd.DataFrame(columns=list(selected_columns.values()))  # Empty DataFrame with renamed columns

                # Convert DataFrame to dbc.Table
                table = dbc.Table.from_dataframe(filtered_df, striped=True, bordered=True, hover=True)

                return True, table
            elif trigger_id == "close-total-modal":
                return False, ""
            
            return is_open, ""
        
        # for ready modal
        @self.dash_app.callback(
            Output("ready-modal", "is_open"),
            Output("ready-modal-content", "children"),
            Input("open-ready-modal", "n_clicks"),
            Input("close-ready-modal", "n_clicks"),
            State("ready-modal", "is_open"),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value')
        )
        def toggle_modal(open_clicks, close_clicks, is_open, selected_programs, selected_status, selected_years, selected_terms):

            ctx = dash.callback_context
            if not ctx.triggered:
                return is_open, ""
            
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "open-ready-modal":
                selected_programs = default_if_empty(selected_programs, self.default_programs)
                selected_status = default_if_empty(selected_status, self.default_statuses)
                selected_years = selected_years if selected_years else self.default_years
                selected_terms = default_if_empty(selected_terms, self.default_terms)

                selected_programs = ensure_list(selected_programs)
                selected_status = ensure_list(selected_status)
                selected_years = ensure_list(selected_years)
                selected_terms = ensure_list(selected_terms)

                # Apply filters
                filtered_data = get_data_for_modal_contents(
                    None,
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                df_filtered_data = pd.DataFrame(filtered_data)

                # Ensure df_filtered_data is a list of dictionaries
                if df_filtered_data is None:
                    df_filtered_data = []
                elif isinstance(df_filtered_data, pd.DataFrame):  
                    df_filtered_data = df_filtered_data.to_dict(orient="records")

                # Filter only "ready" papers
                df_filtered_data = [d for d in df_filtered_data if d.get("status") == "READY"]
                if df_filtered_data == []:
                    return True, "No data records."
                
                # Choose specific columns to display
                selected_columns = {
                    "research_id": "Research ID",
                    "title": "Research Title",
                    "concatenated_keywords": "Keywords",
                    "concatenated_authors": "Author(s)",
                    "sdg": "SDG",
                    "college_id": "College",
                    "program_name": "Program",
                    "research_type": "Research Type"
                }
                
                df_filtered_data = pd.DataFrame(df_filtered_data)[list(selected_columns.keys())] if df_filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                df_filtered_data = df_filtered_data.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)

                return True, table
            elif trigger_id == "close-ready-modal":
                return False, ""
            
            return is_open, ""
        
        # for submitted modal
        @self.dash_app.callback(
            Output("submitted-modal", "is_open"),
            Output("submitted-modal-content", "children"),
            Input("open-submitted-modal", "n_clicks"),
            Input("close-submitted-modal", "n_clicks"),
            State("submitted-modal", "is_open"),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value')
        )
        def toggle_modal(open_clicks, close_clicks, is_open, selected_programs, selected_status, selected_years, selected_terms):

            ctx = dash.callback_context
            if not ctx.triggered:
                return is_open, ""
            
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "open-submitted-modal":
                selected_programs = default_if_empty(selected_programs, self.default_programs)
                selected_status = default_if_empty(selected_status, self.default_statuses)
                selected_years = selected_years if selected_years else self.default_years
                selected_terms = default_if_empty(selected_terms, self.default_terms)

                selected_programs = ensure_list(selected_programs)
                selected_status = ensure_list(selected_status)
                selected_years = ensure_list(selected_years)
                selected_terms = ensure_list(selected_terms)

                # Apply filters
                filtered_data = get_data_for_modal_contents(
                    None,
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                df_filtered_data = pd.DataFrame(filtered_data)

                # Ensure df_filtered_data is a list of dictionaries
                if df_filtered_data is None:
                    df_filtered_data = []
                elif isinstance(df_filtered_data, pd.DataFrame):  
                    df_filtered_data = df_filtered_data.to_dict(orient="records")

                # Filter only "SUBMITTED" papers
                df_filtered_data = [d for d in df_filtered_data if d.get("status") == "SUBMITTED"]
                if df_filtered_data == []:
                    return True, "No data records."
                
                # Choose specific columns to display
                selected_columns = {
                    "research_id": "Research ID",
                    "title": "Research Title",
                    "concatenated_keywords": "Keywords",
                    "concatenated_authors": "Author(s)",
                    "sdg": "SDG",
                    "college_id": "College",
                    "program_name": "Program",
                    "research_type": "Research Type"
                }
                
                df_filtered_data = pd.DataFrame(df_filtered_data)[list(selected_columns.keys())] if df_filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                df_filtered_data = df_filtered_data.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)

                return True, table
            elif trigger_id == "close-submitted-modal":
                return False, ""
            
            return is_open, ""
        
        # for accepted modal
        @self.dash_app.callback(
            Output("accepted-modal", "is_open"),
            Output("accepted-modal-content", "children"),
            Input("open-accepted-modal", "n_clicks"),
            Input("close-accepted-modal", "n_clicks"),
            State("accepted-modal", "is_open"),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value')
        )
        def toggle_modal(open_clicks, close_clicks, is_open, selected_programs, selected_status, selected_years, selected_terms):

            ctx = dash.callback_context
            if not ctx.triggered:
                return is_open, ""
            
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "open-accepted-modal":
                selected_programs = default_if_empty(selected_programs, self.default_programs)
                selected_status = default_if_empty(selected_status, self.default_statuses)
                selected_years = selected_years if selected_years else self.default_years
                selected_terms = default_if_empty(selected_terms, self.default_terms)

                selected_programs = ensure_list(selected_programs)
                selected_status = ensure_list(selected_status)
                selected_years = ensure_list(selected_years)
                selected_terms = ensure_list(selected_terms)

                # Apply filters
                filtered_data = get_data_for_modal_contents(
                    None,
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                df_filtered_data = pd.DataFrame(filtered_data)

                # Ensure df_filtered_data is a list of dictionaries
                if df_filtered_data is None:
                    df_filtered_data = []
                elif isinstance(df_filtered_data, pd.DataFrame):  
                    df_filtered_data = df_filtered_data.to_dict(orient="records")

                # Filter only "ACCEPTED" papers
                df_filtered_data = [d for d in df_filtered_data if d.get("status") == "ACCEPTED"]
                if df_filtered_data == []:
                    return True, "No data records."
                
                # Choose specific columns to display
                selected_columns = {
                    "research_id": "Research ID",
                    "title": "Research Title",
                    "concatenated_keywords": "Keywords",
                    "concatenated_authors": "Author(s)",
                    "sdg": "SDG",
                    "college_id": "College",
                    "program_name": "Program",
                    "research_type": "Research Type"
                }
                
                df_filtered_data = pd.DataFrame(df_filtered_data)[list(selected_columns.keys())] if df_filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                df_filtered_data = df_filtered_data.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)

                return True, table
            elif trigger_id == "close-accepted-modal":
                return False, ""
            
            return is_open, ""
        
        # for published modal
        @self.dash_app.callback(
            Output("published-modal", "is_open"),
            Output("published-modal-content", "children"),
            Input("open-published-modal", "n_clicks"),
            Input("close-published-modal", "n_clicks"),
            State("published-modal", "is_open"),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value')
        )
        def toggle_modal(open_clicks, close_clicks, is_open, selected_programs, selected_status, selected_years, selected_terms):

            ctx = dash.callback_context
            if not ctx.triggered:
                return is_open, ""
            
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "open-published-modal":
                selected_programs = default_if_empty(selected_programs, self.default_programs)
                selected_status = default_if_empty(selected_status, self.default_statuses)
                selected_years = selected_years if selected_years else self.default_years
                selected_terms = default_if_empty(selected_terms, self.default_terms)

                selected_programs = ensure_list(selected_programs)
                selected_status = ensure_list(selected_status)
                selected_years = ensure_list(selected_years)
                selected_terms = ensure_list(selected_terms)

                # Apply filters
                filtered_data = get_data_for_modal_contents(
                    None,
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                df_filtered_data = pd.DataFrame(filtered_data)

                # Ensure df_filtered_data is a list of dictionaries
                if df_filtered_data is None:
                    df_filtered_data = []
                elif isinstance(df_filtered_data, pd.DataFrame):  
                    df_filtered_data = df_filtered_data.to_dict(orient="records")

                # Filter only "PUBLISHED" papers
                df_filtered_data = [d for d in df_filtered_data if d.get("status") == "PUBLISHED"]
                if df_filtered_data == []:
                    return True, "No data records."
                
                # Choose specific columns to display
                selected_columns = {
                    "research_id": "Research ID",
                    "title": "Research Title",
                    "concatenated_keywords": "Keywords",
                    "concatenated_authors": "Author(s)",
                    "sdg": "SDG",
                    "college_id": "College",
                    "program_name": "Program",
                    "research_type": "Research Type"
                }
                
                df_filtered_data = pd.DataFrame(df_filtered_data)[list(selected_columns.keys())] if df_filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                df_filtered_data = df_filtered_data.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)

                return True, table
            elif trigger_id == "close-published-modal":
                return False, ""
            
            return is_open, ""
        
        # for pullout modal
        @self.dash_app.callback(
            Output("pullout-modal", "is_open"),
            Output("pullout-modal-content", "children"),
            Input("open-pullout-modal", "n_clicks"),
            Input("close-pullout-modal", "n_clicks"),
            State("pullout-modal", "is_open"),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value')
        )
        def toggle_modal(open_clicks, close_clicks, is_open, selected_programs, selected_status, selected_years, selected_terms):

            ctx = dash.callback_context
            if not ctx.triggered:
                return is_open, ""
            
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "open-pullout-modal":
                selected_programs = default_if_empty(selected_programs, self.default_programs)
                selected_status = default_if_empty(selected_status, self.default_statuses)
                selected_years = selected_years if selected_years else self.default_years
                selected_terms = default_if_empty(selected_terms, self.default_terms)

                selected_programs = ensure_list(selected_programs)
                selected_status = ensure_list(selected_status)
                selected_years = ensure_list(selected_years)
                selected_terms = ensure_list(selected_terms)

                # Apply filters
                filtered_data = get_data_for_modal_contents(
                    None,
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                df_filtered_data = pd.DataFrame(filtered_data)

                # Ensure df_filtered_data is a list of dictionaries
                if df_filtered_data is None:
                    df_filtered_data = []
                elif isinstance(df_filtered_data, pd.DataFrame):  
                    df_filtered_data = df_filtered_data.to_dict(orient="records")

                # Filter only "PULLOUT" papers
                df_filtered_data = [d for d in df_filtered_data if d.get("status") == "PULLOUT"]
                if df_filtered_data == []:
                    return True, "No data records."
                
                # Choose specific columns to display
                selected_columns = {
                    "research_id": "Research ID",
                    "title": "Research Title",
                    "concatenated_keywords": "Keywords",
                    "concatenated_authors": "Author(s)",
                    "sdg": "SDG",
                    "college_id": "College",
                    "program_name": "Program",
                    "research_type": "Research Type"
                }
                
                df_filtered_data = pd.DataFrame(df_filtered_data)[list(selected_columns.keys())] if df_filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                df_filtered_data = df_filtered_data.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(df_filtered_data, striped=True, bordered=True, hover=True)

                return True, table
            elif trigger_id == "close-pullout-modal":
                return False, ""
            
            return is_open, ""