from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from urllib.parse import parse_qs, urlparse
from . import db_manager
import dash

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values


class ProgDashApp:
    def __init__(self, server, title=None, college=None, program=None, **kwargs):
        self.dash_app = Dash(__name__,
                             server=server,
                             url_base_pathname=kwargs.get('url_base_pathname', '/progchairdash/'),
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
                    id="program",  # Updated ID
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values_by('program_id', 'college_id', self.college)],
                    value=self.program if self.program else [],
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
                        [program, status, term, slider, button], 
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
                        children=dcc.Graph(id='college_line_plot'),
                    ), 
                    width=8, 
                    style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}
                ),
                dbc.Col(
                    dcc.Loading(
                        id="loading-college-pie",
                        type="circle",
                        children=dcc.Graph(id='college_pie_chart'),
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
                            html.H1(self.title),
                            html.P(self.college),
                            html.P(self.program),
                            html.Div(id='output-container'),
                            html.Div(id='user-role'),
                            html.Div(id='college-info'),
                            html.Div(id='program-info'),
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
                            dcc.Tabs(id="dashboard-tabs", value='main', children=[
                                dcc.Tab(label="Performance Overview", value="main", children=[main_dash]),
                                dcc.Tab(label="Research Statuses and Types", value="sub1", children=[sub_dash1]),
                                dcc.Tab(label="Scopus & Non-Scopus", value="sub2", children=[sub_dash2]),
                                dcc.Tab(label="SDG Distribution", value="sub3", children=[sub_dash3]),
                                dcc.Tab(label="Publication Types", value="sub4", children=[sub_dash4]),
                            ]),
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

    def get_program_colors(self, df, color_column='program_id'):
        """
        Generate a color mapping for the unique values in the specified column of the DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame containing data.
            color_column (str): The column for which unique values will be colored (default is 'program_id').

        Updates:
            self.program_colors: A dictionary mapping unique values in the color_column to colors.
        """
        unique_values = df[color_column].unique()
        random_colors = px.colors.qualitative.Plotly[:len(unique_values)]
        self.program_colors = {value: random_colors[i % len(random_colors)] for i, value in enumerate(unique_values)}

    
    def update_line_plot(self, selected_program, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_bycollege_with_term(selected_program, selected_status, selected_years, selected_terms)

        if len(selected_program) == 1:
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = f'Number of Research Outputs for {selected_program[0]}'
        else:
            df = df[df['program_id'].isin(selected_program)]
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = 'Number of Research Outputs per College'
        
        # Generate a dynamic color mapping based on unique values in the color_column
        unique_values = grouped_df[color_column].unique()
        color_discrete_map = {value: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                            for i, value in enumerate(unique_values)}
        
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
            title=title,
            xaxis_title='Academic Year',
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400
        )
        
        return fig_line

    def update_pie_chart(self, selected_programs, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)

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
            unique_values = detail_counts['program_id'].unique()
            color_discrete_map = {value: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                                for i, value in enumerate(unique_values)}

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
            title=title
        )

        return fig_pie
    
    def update_research_type_bar_plot(self, selected_programs, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        if df.empty:
            return px.bar(title="No data available")
        
        fig = go.Figure()

            #self.get_program_colors(df) 
        status_count = df.groupby(['research_type', 'program_id']).size().reset_index(name='Count')
        pivot_df = status_count.pivot(index='research_type', columns='program_id', values='Count').fillna(0)

        sorted_programs = sorted(pivot_df.columns)
        title = f"Comparison of Research Output Type Across Programs"

        # Generate a dynamic color mapping based on unique values in the `program_id`
        unique_values = status_count['program_id'].unique()
        color_discrete_map = {value: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                            for i, value in enumerate(unique_values)}

        for program in sorted_programs:
            fig.add_trace(go.Bar(
                x=pivot_df.index,
                y=pivot_df[program],
                name=program,
                marker_color=color_discrete_map[program]
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title='Research Type',  
            yaxis_title='Number of Research Outputs',  
            title=title
        )

        return fig
    
    def update_research_status_bar_plot(self, selected_programs, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        """
        if df.empty:
            return px.bar(title="No data available")
        """
        
        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLOUT']

        fig = go.Figure()

        #self.get_program_colors(df) 
        status_count = df.groupby(['status', 'program_id']).size().reset_index(name='Count')
        pivot_df = status_count.pivot(index='status', columns='program_id', values='Count').fillna(0)

        sorted_programs = sorted(pivot_df.columns)
        title = f"Comparison of Research Status Across Program/s"

        # Generate a dynamic color mapping based on unique values in the `program_id`
        unique_values = status_count['program_id'].unique()
        color_discrete_map = {value: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                            for i, value in enumerate(unique_values)}

        for program in sorted_programs:
            fig.add_trace(go.Bar(
                x=pivot_df.index,
                y=pivot_df[program],
                name=program,
                marker_color=color_discrete_map[program]
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title='Research Status',  
            yaxis_title='Number of Research Outputs',  
            title=title,
            xaxis=dict(
                tickvals=status_order,  # This should match the unique statuses in pivot_df index
                ticktext=status_order    # This ensures that the order of the statuses is displayed correctly
            )
        )

        # Ensure the x-axis is sorted in the defined order
        fig.update_xaxes(categoryorder='array', categoryarray=status_order)
        return fig
    
    def update_sdg_chart(self, selected_programs, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        
        if df.empty:
            return px.scatter(title="No data available")

        df_copy = df.copy()

        #self.get_program_colors(df)
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
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        
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
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            height=400
        )

        return fig_bar
    
    def update_publication_format_bar_plot(self, selected_programs, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        
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
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            height=400
        )

        return fig_bar

    def scopus_line_graph(self, selected_programs, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        
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
            xaxis_title='Academic Year',
            yaxis_title='Number of Research Outputs',
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
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        
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
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        
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
            xaxis_title='Academic Year',
            yaxis_title='Number of Research Outputs',
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
        df = db_manager.get_filtered_data_bycollege_with_term(selected_programs, selected_status, selected_years, selected_terms)
        
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
                Output("status", "value"),
                Output('terms', 'value'),
                Output("years", "value"),
            ],
            Input("reset_button", "n_clicks"),
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        
        # Callback to update content based on the user role and other URL parameters
        @self.dash_app.callback(
            [
                Output('program-info', 'children'),
                Output('program', 'value'),  
            ],
            Input('url', 'search')  # Capture the query string in the URL
        )
        def update_user_role_and_info(url_search):
            if not url_search:
                return (
                    html.H3('Welcome Guest! Please log in.'),
                    [],
                )
            
            # Parse query parameters
            params = dict(param.split('=') for param in url_search.lstrip('?').split('&'))
            self.college = params.get('college', 'Unknown College')
            self.program = params.get('program', 'Unknown Program')

            # Fetch available programs
            self.default_programs = db_manager.get_unique_values_by('program_id', 'college_id', self.college)
            print(f"self.default_programs: {self.default_programs}")
            print(f"self.program: {self.program}")

            # Ensure the program is in the list of valid options
            value = [self.program] if self.program in self.default_programs else []
            print(f'VALUE: {value}')

            # Return updated components
            return html.H5(
                f'Program Department: {self.program}', 
                style={'textAlign': 'center', 'marginTop': '0px'}
            ), value

        
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_shared_data_store(n_intervals):
            updated_data = db_manager.get_all_data()
            return updated_data.to_dict('records')
        
        # for text button (dynamic)
        @self.dash_app.callback(
            Output('open-total-modal', 'children'),
            Output('open-ready-modal', 'children'),
            Output('open-submitted-modal', 'children'),
            Output('open-accepted-modal', 'children'),
            Output('open-published-modal', 'children'),
            Output('open-pullout-modal', 'children'),
            Input("data-refresh-interval", "n_intervals"),
            Input('program', 'value'),
            Input('status', 'value'),
            Input('years', 'value'),
            Input('terms', 'value')
        )
        def refresh_text_buttons(n_intervals, selected_programs, selected_status, selected_years, selected_terms):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            # Apply filters
            filtered_data = db_manager.get_filtered_data_bycollege_text_display(
                selected_programs=selected_programs, 
                selected_status=selected_status,
                selected_years=selected_years,
                selected_terms=selected_terms
            )

            # Convert DataFrame to list of dictionaries
            filtered_data = filtered_data.to_dict(orient='records')

            return f'{len(filtered_data)} Research Output(s)', \
                    f'{len([d for d in filtered_data if d["status"] == "READY"])} Ready for Publication', \
                    f'{len([d for d in filtered_data if d["status"] == "SUBMITTED"])} Submitted Paper(s)', \
                    f'{len([d for d in filtered_data if d["status"] == "ACCEPTED"])} Accepted Paper(s)', \
                    f'{len([d for d in filtered_data if d["status"] == "PUBLISHED"])} Published Paper(s)', \
                    f'{len([d for d in filtered_data if d["status"] == "PULLOUT"])} Pulled-out Paper(s)'
        
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

                # Apply filters
                filtered_data = db_manager.get_filtered_data_bycollege_text_display(
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                # Ensure filtered_data is a valid DataFrame or empty list
                if filtered_data is None or len(filtered_data) == 0:
                    return True, "No data records."
                elif isinstance(filtered_data, pd.DataFrame):
                    filtered_data = filtered_data.to_dict(orient="records")

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

                # Apply filters
                filtered_data = db_manager.get_filtered_data_bycollege_text_display(
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                # Ensure filtered_data is a list of dictionaries
                if filtered_data is None:
                    filtered_data = []
                elif isinstance(filtered_data, pd.DataFrame):  
                    filtered_data = filtered_data.to_dict(orient="records")

                # Filter only "ready" papers
                filtered_data = [d for d in filtered_data if d.get("status") == "READY"]
                if filtered_data == []:
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
                
                filtered_df = pd.DataFrame(filtered_data)[list(selected_columns.keys())] if filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                filtered_df = filtered_df.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(filtered_df, striped=True, bordered=True, hover=True)

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

                # Apply filters
                filtered_data = db_manager.get_filtered_data_bycollege_text_display(
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                # Ensure filtered_data is a list of dictionaries
                if filtered_data is None:
                    filtered_data = []
                elif isinstance(filtered_data, pd.DataFrame):  
                    filtered_data = filtered_data.to_dict(orient="records")

                # Filter only "submitted" papers
                filtered_data = [d for d in filtered_data if d.get("status") == "SUBMITTED"]
                if filtered_data == []:
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
                
                filtered_df = pd.DataFrame(filtered_data)[list(selected_columns.keys())] if filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                filtered_df = filtered_df.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(filtered_df, striped=True, bordered=True, hover=True)

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

                # Apply filters
                filtered_data = db_manager.get_filtered_data_bycollege_text_display(
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                # Ensure filtered_data is a list of dictionaries
                if filtered_data is None:
                    filtered_data = []
                elif isinstance(filtered_data, pd.DataFrame):  
                    filtered_data = filtered_data.to_dict(orient="records")

                # Filter only "accepted" papers
                filtered_data = [d for d in filtered_data if d.get("status") == "ACCEPTED"]
                if filtered_data == []:
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
                
                filtered_df = pd.DataFrame(filtered_data)[list(selected_columns.keys())] if filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                filtered_df = filtered_df.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(filtered_df, striped=True, bordered=True, hover=True)

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

                # Apply filters
                filtered_data = db_manager.get_filtered_data_bycollege_text_display(
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )

                # Ensure filtered_data is a list of dictionaries
                if filtered_data is None:
                    filtered_data = []
                elif isinstance(filtered_data, pd.DataFrame):  
                    filtered_data = filtered_data.to_dict(orient="records")

                # Filter only "PUBLISHED" papers
                filtered_data = [d for d in filtered_data if d.get("status") == "PUBLISHED"]
                if filtered_data == []:
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
                
                filtered_df = pd.DataFrame(filtered_data)[list(selected_columns.keys())] if filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                filtered_df = filtered_df.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(filtered_df, striped=True, bordered=True, hover=True)

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

                # Apply filters
                filtered_data = db_manager.get_filtered_data_bycollege_text_display(
                    selected_programs=selected_programs, 
                    selected_status=selected_status,
                    selected_years=selected_years,
                    selected_terms=selected_terms
                )
                print(f'filtered_data: {filtered_data}')
                # Ensure filtered_data is a list of dictionaries
                if filtered_data is None:
                    filtered_data = []
                elif isinstance(filtered_data, pd.DataFrame):  
                    filtered_data = filtered_data.to_dict(orient="records")

                # Filter only "PULLOUT" papers
                filtered_data = [d for d in filtered_data if d.get("status") == "PULLOUT"]
                if filtered_data == []:
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
                
                filtered_df = pd.DataFrame(filtered_data)[list(selected_columns.keys())] if filtered_data else pd.DataFrame(columns=list(selected_columns.keys()))

                # Rename columns
                filtered_df = filtered_df.rename(columns=selected_columns)

                # Convert to dbc.Table
                table = dbc.Table.from_dataframe(filtered_df, striped=True, bordered=True, hover=True)

                return True, table
            elif trigger_id == "close-pullout-modal":
                return False, ""
            
            return is_open, ""