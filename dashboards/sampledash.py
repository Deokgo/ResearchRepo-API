from dash import Dash, html, dcc
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


class DashApp:
    #user_college = ''
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
        self.user_college = ''
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]

        self.set_layout()
        self.add_callbacks()

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

        controls = dbc.Card(
            [
                html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),  # Set the color to red
                college,
                program,
                status,
                slider,
                button,
            ],
            body=True,
            style={"border": "2px solid #0A438F", "height": "95vh", "display": "flex", "flexDirection": "column"}
        )

        text_display = dbc.Container([
            dbc.Row([
                dbc.Col(
                    self.create_display_card("Total Research Papers", str(len(db_manager.filter_data('college_id', self.user_college)))),
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                ),
                dbc.Col(
                    self.create_display_card("Intended for Publication", str(len(db_manager.filter_data('status', 'READY', 'college_id', 'MITL')))),
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                ),
                dbc.Col(
                    self.create_display_card("Submitted Papers", str(len(db_manager.filter_data('status', 'SUBMITTED', 'college_id', 'MITL')))),
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                ),
                dbc.Col(
                    self.create_display_card("Accepted Papers", str(len(db_manager.filter_data('status', 'ACCEPTED', 'college_id', 'MITL')))),
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                ),
                dbc.Col(
                    self.create_display_card("Published Papers", str(len(db_manager.filter_data('status', 'PUBLISHED', 'college_id', 'MITL')))),
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                ),
                dbc.Col(
                    self.create_display_card("Pulled-out Papers", str(len(db_manager.filter_data('status', 'PULLOUT', 'college_id', 'MITL')))),
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                )
            ], style={"margin": "0", "display": "flex", "justify-content": "space-around", "align-items": "center"})
        ], style={"padding": "2rem"}, id="text-display-container")

        main_dash = dbc.Container([
                dbc.Row([  # Row for the line and pie charts
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}),
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #0A438F", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed




        self.dash_app.layout = html.Div([
            # URL tracking
            dcc.Location(id='url', refresh=False),
            dbc.Container([
                dbc.Row([
                    dbc.Col([
                        html.H1(self.title),
                        html.P(self.college),
                        html.P(self.program),
                        html.Button('Click Me', id='common-button'),
                        html.Div(id='output-container'),
                        # Placeholder for displaying user role, college, and program information
                        html.Div(id='user-role'),
                        html.Div(id='college-info'),
                        html.Div(id='program-info'),
                        dbc.Row(text_display),
                        dbc.Row(main_dash),
                    ], width=10, style={"transform": "scale(0.9)", "transform-origin": "0 0"}),
                    dbc.Col(controls, width=2)       # Controls on the side
                ])
            ], fluid=True, className="dbc dbc-ag-grid", style={"overflow": "hidden"})
        ])

    def create_display_card(self, title, value):
        """
        Create a display card for showing metrics.
        """
        return html.Div([
            html.Div([
                html.H5(title, style={'textAlign': 'center'}),
                html.H2(value, style={'textAlign': 'center'})
            ], style={
                "border": "2px solid #0A438F",    # Border color
                "borderRadius": "10px",           # Rounded corners
                "padding": "10px",                # Padding inside the card
                "width": "170px",                 # Fixed width
                "height": "150px",                # Fixed height
                "display": "flex",
                "flexDirection": "column",
                "justifyContent": "center",
                "alignItems": "center",
                "margin": "0"
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

    
    def update_line_plot(self, selected_program, selected_status, selected_years):
        # Fetch filtered data
        df = db_manager.get_filtered_data_bycollege(selected_program, selected_status, selected_years)

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
            yaxis_title='Number of Publications',
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400
        )
        
        return fig_line

    def update_pie_chart(self, selected_programs, selected_status, selected_years):
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)

        if len(selected_programs) == 1:
            # Handle single program selection
            program_id = selected_programs[0]
            filtered_df = df[df['program_id'] == program_id]
            detail_counts = filtered_df.groupby('year').size().reset_index(name='count')  # Group by year and count
            title = f"Research Outputs for Program {program_id}"

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
                Input('years', 'value')
            ]
        )
        def update_lineplot(selected_programs, selected_status, selected_years):
            # Fallback to defaults if inputs are not provided
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years

            # Update the line plot with filtered data
            return self.update_line_plot(selected_programs, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('college_pie_chart', 'figure'),
            [Input('program', 'value'), Input('status', 'value'), Input('years', 'value')]
        )
        def update_pie_chart_callback(selected_programs, selected_status, selected_years):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.update_pie_chart(selected_programs, selected_status, selected_years)

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
                Output("years", "value"),
            ],
            Input("reset_button", "n_clicks"),
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
            
        @self.dash_app.callback(
            Output('output-container', 'children'),
            Input('common-button', 'n_clicks')
        )
        def update_output(n_clicks):
            if n_clicks is None:
                return "Button not clicked yet"
            return f"Button clicked {n_clicks} times"
        
        # Callback to update content based on the user role and other URL parameters
        @self.dash_app.callback(
            [
                Output('user-role', 'children'),
                Output('college-info', 'children'),
                Output('program-info', 'children'),
                Output('text-display-container', 'children')
            ],
            Input('url', 'search')  # Capture the query string in the URL
        )
        def update_user_role_and_info(url_search):
            if url_search is None or url_search == '':
                return html.H3('Welcome Guest! Please log in.'), html.H3('College: Unknown'), html.H3('Program: Unknown')
            
            # Parse the URL parameters directly from the search
            params = dict((key, value) for key, value in (param.split('=') for param in url_search[1:].split('&')))
            
            user_role = params.get('user-role', '06')  # Default to 'guest' if no role is passed
            self.college = params.get('college', 'Unknown College')  # Default to 'Unknown College' if no college is passed
            self.program = params.get('program', 'Unknown Program')  # Default to 'Unknown Program' if no program is passed

            # Handle user role display
            if user_role == '04':
                user_role_message = html.H3('Welcome Admin! You have full control.')
            elif user_role == '02':
                user_role_message = html.H3('Welcome User! Your access is limited.')
            else:
                user_role_message = html.H3('Welcome Guest! Please log in.')
            
            self.default_programs = db_manager.get_unique_values_by('program_id','college_id',self.college)
            print(f'self.default_programs: {self.default_programs}\ncollege: {self.college}')

            DashApp.user_college = self.college
            print(f'self.user_college: {DashApp.user_college}')

            # Return the role, college, and program information
            return user_role_message, html.H3(f'College: {self.college}'), html.H3(f'Program: {self.program}'), dbc.Container([
                dbc.Row([
                    dbc.Col(self.create_display_card("Total Research Papers", str(len(db_manager.filter_data('college_id', self.college))))),
                    dbc.Col(
                        self.create_display_card("Intended for Publication", str(len(db_manager.filter_data('status', 'READY', 'college_id', self.college)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}),
                    dbc.Col(
                        self.create_display_card("Submitted Papers", str(len(db_manager.filter_data('status', 'SUBMITTED', 'college_id', self.college)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}),
                    dbc.Col(
                        self.create_display_card("Accepted Papers", str(len(db_manager.filter_data('status', 'ACCEPTED', 'college_id', self.college)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}),
                    dbc.Col(
                        self.create_display_card("Published Papers", str(len(db_manager.filter_data('status', 'PUBLISHED', 'college_id', self.college)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}),
                    dbc.Col(
                        self.create_display_card("Pulled-out Papers", str(len(db_manager.filter_data('status', 'PULLOUT', 'college_id', self.college)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"})
                    # Add other display cards similarly...
                ])
            ])
