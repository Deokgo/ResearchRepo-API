from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from urllib.parse import parse_qs, urlparse
from . import db_manager
from services.sdg_colors import sdg_colors

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values


class SDG_Map_College:
    def __init__(self, server, title=None, college=None, program=None, **kwargs):
        self.dash_app = Dash(__name__,
                             server=server,
                             url_base_pathname=kwargs.get('url_base_pathname', '/sdg/map/college/'),
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.title = title
        self.college = college
        self.program = program
        self.sdg_colors=sdg_colors
        self.all_sdgs = [f'SDG {i}' for i in range(1, 18)]

        self.palette_dict = db_manager.get_college_colors()
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_programs = []
        self.default_statuses = db_manager.get_unique_values('status')
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
        df = db_manager.get_all_data()
        sdg_series = df['sdg'].str.split('; ').explode()
        distinct_sdg_df = pd.DataFrame(sdg_series.drop_duplicates().reset_index(drop=True), columns=['sdg'])
        distinct_sdg_values = distinct_sdg_df['sdg'].tolist() 

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
                sdgs,
                college,
                program,
                status,
                slider,
                button,
            ],
            body=True,
                style={
                    "background": "#d3d8db",
                    "height": "100vh",  # Full-height sidebar
                    "position": "sticky",  # Sticky position instead of fixed
                    "top": 0,
                    "padding": "20px",
                    "border-radius": "0",  # Remove rounded corners
                },
        )
        tab1 = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart1",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-time-series")
                        ]
                    ),
                ],width=7),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart2",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-pie-distribution")
                        ]
                    ),
                ],width=5)
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart3",
                        type="circle",
                        children=[
                            dcc.Graph(id="sdg-research-type")
                        ]
                    ),
                ],width=6),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart4",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-status")
                        ]
                    ),
                ],width=6)
            ]),
            ]
        )

        tab2 = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart5",
                        type="circle",
                        children=[
                            dcc.Graph(id="sdg-conference")
                        ]
                    ),
                ],width=8),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart6",
                        type="circle",
                        children=[
                            dcc.Graph(id="sdg-publication-type")
                        ]
                    ),
                ],width=4)
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart7",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-map")
                        ]
                    ),
                ],width=12),
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart8",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-countries")
                        ]
                    ),
                ],width=8),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart9",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-local-foreign-pie")
                        ]
                    ),
                ],width=4)
            ]),

        ])

        tab3 = dbc.Container([
            dbc.Col(
                dcc.Loading(
                    id="loading-sdg-chart10",
                    type="circle",
                    children=[
                        dcc.Graph(id="keywords-cloud"),
                    ]
                ),
            ),
            
            dbc.Col(
                dcc.Loading(
                    id="loading-sdg-chart11",
                    type="circle",
                    children=[
                        dcc.Graph(id="research-area-cloud"),
                    ]
                ),
            ),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart12",
                        type="circle", 
                        children=[
                            dcc.Graph(id="top-research-area")
                        ]
                    ),
                ],width=6),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart13",
                        type="circle", 
                        children=[
                            dcc.Graph(id="top-authors")
                        ]
                    ),
                ],width=6)
            ]),
            ]
        )

        main_dash = dbc.Container([
                dbc.Row([  # Row for the line and pie charts
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}),
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash1 = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='research_status_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='research_type_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash3 = dbc.Container([
            dbc.Row([
                dbc.Col(dcc.Graph(id='sdg_bar_plot'), width=12)  # Increase width to 12 to occupy the full space
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})

        sub_dash2 = dbc.Container([ 
                dbc.Row([
                    dbc.Col(dcc.Graph(id='proceeding_conference_line_graph'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='proceeding_conference_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed
        
        sub_dash4 = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='nonscopus_scopus_line_graph'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='nonscopus_scopus_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        layout = dbc.Container([
                                    dcc.Tabs(
                            id="sdg-tabs",
                            value="sdg-college-tab",  
                            children=[
                                dcc.Tab(
                                    label="Institutional SDG Impact",
                                    value="sdg-college-tab",
                                    children=[
                                        
                                        
                                    ]
                                ),
                                dcc.Tab(
                                    label="Global Research Publications",
                                    value="sdg-global-tab",
                                    children=[
                                        dcc.Loading(
                                            id="loading-sdg-map",
                                            type="circle", 
                                            children=[
                                                #tab2
                                            ]
                                        ),                                     
                                    ]
                                ),
                                dcc.Tab(
                                    label="Research Trends and Collaboration",
                                    value="sdg-trend-tab",
                                    children=[
                                        #tab3
                                    ]
                                ),
                            ]
                        ),            
        ],
        style={
            "height": "100%",
            "display": "flex",
            "flex-direction": "column",
            "overflow-y": "auto",  
            "overflow-x": "auto",  
            "transform": "scale(0.98)",  
            "transform-origin": "0 0",  
            "margin": "0", 
            "padding": "5px",
            "flex-grow": "1",  
        })
        
        self.dash_app.layout = html.Div([
            # URL tracking
            dcc.Location(id='url', refresh=False),
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),  # 1 second
            dcc.Store(id="shared-data-store"),  # Shared data store to hold the updated dataset
            dbc.Container([
                dbc.Row([
                    dbc.Col(controls, width=2, style={"height": "100%"}),
                    dbc.Col([
                        dbc.Container([
                            html.Div(id='college-info'),
                            html.H4("sample",id="chosen-sdg"),
                            html.Div("This dashboard analyzes the institution\’s research alignment with the global Sustainable Development Goals (SDGs), highlighting trends, strengths, and areas for improvement. It provides an overview of research performance across SDG categories, supporting data-driven decisions to enhance sustainable development efforts.")
                        ], style={"padding":"20px"}),
                        tab1,
                        dbc.Row(main_dash, style={"flex": "2"}),
                        dbc.Row(sub_dash1, style={"flex": "1"}),
                        dbc.Row(sub_dash3, style={"flex": "1"}),
                        dbc.Row(sub_dash2, style={"flex": "1"}),
                        dbc.Row(sub_dash4, style={"flex": "1"}),
                        ], style={
                        "height": "100%",
                        "display": "flex",
                        "flex-direction": "column",
                        "overflow-y": "auto",  # Allow vertical scrolling
                        "overflow-x": "auto",  # Allow horizontal scrolling
                        "flex-grow": "1",      # Ensure content area grows to fill available space
                        "margin": "0", 
                        "padding": "5px",
                    }),
                ], style={"height": "100%", "display": "flex"}),
            ], fluid=True, className="dbc dbc-ag-grid", style={
                "height": "90vh",  # Use full viewport height
                "margin": "0", 
                "padding": "0",
            })
        ], style={
            "height": "100vh",  # Use full viewport height
            "margin": "0",
            "padding": "0",
            "overflow-x": "hidden",  # Disable horizontal scrolling
            "overflow-y": "hidden",  # Disable vertical scrolling
        })


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

    
    def create_sdg_plot(self, selected_program, selected_status, selected_years,sdg_dropdown_value):
        # Fetch filtered data
        df = db_manager.get_filtered_data_bycollege(selected_program, selected_status, selected_years)

        df_temp = df.copy()
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces

        # If the SDG dropdown value is not "ALL", filter the data accordingly
        if sdg_dropdown_value != "ALL":
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]
            # Group by Year and Program and count the number of research outputs
            sdg_program_distribution = df_temp.groupby(['year', 'program_id']).size().reset_index(name='Count')
            
            # Create the time-series plot grouped by program
            fig = px.line(
                sdg_program_distribution,
                x='year',
                y='Count',
                color='program_id',  # Group by Program
                title=f'Research Outputs Over Time by Program (Filtered by SDG: {sdg_dropdown_value})',
                labels={'year': 'Year', 'Count': 'Number of Research Outputs', 'program_id': 'Program'},
                template="plotly_white",
                color_discrete_map=self.palette_dict,
            )
        else:
            # Group by Year and SDG and count the number of research outputs
            sdg_year_distribution = df_temp.groupby(['year', 'sdg']).size().reset_index(name='Count')

            # Ensure that all SDGs are included, even those with zero counts
            # Create a DataFrame for all combinations of Year and SDG
            all_sdg_year_combinations = pd.MultiIndex.from_product([df['year'].unique(), self.all_sdgs], names=['year', 'sdg'])
            sdg_year_distribution = sdg_year_distribution.set_index(['year', 'sdg']).reindex(all_sdg_year_combinations, fill_value=0).reset_index()

            # Sort the data by Year to ensure chronological order
            sdg_year_distribution = sdg_year_distribution.sort_values(by='year')

            # Create the time-series plot to show SDG research outputs over time
            fig = px.line(
                sdg_year_distribution,
                x='year',
                y='Count',
                color='sdg',  # Group by SDG
                title='SDG Research Outputs Over Time',
                labels={'year': 'Year', 'Count': 'Number of Research Outputs', 'sdg': 'SDG'},
                color_discrete_map=sdg_colors,  # Apply SDG colors
                category_orders={'sdg': self.all_sdgs},  # Ensure SDGs are in order
            )

        # Customize layout for better visualization
        fig.update_layout(
            title_font_size=18,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            legend_title_font_size=14,
            template="plotly_white",
            xaxis=dict(showgrid=True),  # Show grid on x-axis
            yaxis=dict(title='Number of Research Outputs', showgrid=True),  # Label y-axis clearly
            legend=dict(title=dict(font=dict(size=14)), traceorder="normal", orientation="h", x=1, xanchor="right", y=-0.2),  # Position legend outside
        )

        return fig
    
    def create_sdg_pie_chart(self, selected_program, selected_status, selected_years, sdg_dropdown_value):
        # Get filtered data based on selected parameters
        df = db_manager.get_filtered_data_bycollege(selected_program, selected_status, selected_years)

        if df.empty:
            return px.pie(title="No data available for the selected parameters.")

        df_temp = df.copy()
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces

        # Check unique SDGs to ensure the 'sdg' column is processed correctly
        print("I am here"+df_temp["sdg"].unique())

        # If the SDG dropdown value is not "ALL", filter the data accordingly
        if sdg_dropdown_value != "ALL":
            pass
        else:
            # Group by SDG and count the number of research outputs
            sdg_distribution = df_temp.groupby('sdg').size().reset_index(name='Count')
            print(sdg_distribution)
            # Calculate the percentage of total research outputs for each SDG
            total_count = sdg_distribution['Count'].sum()
            sdg_distribution['Percentage'] = (sdg_distribution['Count'] / total_count) * 100

            # Ensure all SDGs are included, even those with zero counts
            sdg_distribution = pd.DataFrame(self.all_sdgs, columns=['sdg']).merge(sdg_distribution, on='sdg', how='left').fillna(0)

            # Reorder the SDGs based on the predefined list (self.all_sdgs)
            sdg_distribution['sdg'] = pd.Categorical(sdg_distribution['sdg'], categories=self.all_sdgs, ordered=True)
            sdg_distribution = sdg_distribution.sort_values('sdg')

            # Create the pie chart to show the percentage distribution of research outputs by SDG
            fig = px.pie(
                sdg_distribution,
                names='sdg',
                values='Percentage',
                title='Percentage of Research Outputs by SDG',
                color='sdg',
                color_discrete_map=sdg_colors,  # Apply SDG colors
                labels={'sdg': 'SDG', 'Percentage': 'Percentage of Total Outputs'},
                category_orders={'sdg': self.all_sdgs}  # Ensure SDGs are in order
            )

        # Customize layout for better visualization
        fig.update_layout(
            title_font_size=18,
            legend_title_font_size=14,
            template="plotly_white",
            legend=dict(
                title=dict(font=dict(size=14)),
                traceorder="normal",
                orientation="h",  # Horizontal legend
                x=0.5,  # Center the legend horizontally
                xanchor="center",  # Anchor the legend at the center
                y=-0.2,  # Position the legend below the chart
                yanchor="top",  # Anchor the legend at the top
            ),
        )

        return fig
        
    def update_figures(self, selected_program, selected_status, selected_years, sdg_dropdown_value):
        #fig1 = self.create_sdg_pie_chart(selected_program, selected_status, selected_years, sdg_dropdown_value)
        fig2 = self.create_sdg_plot(selected_program, selected_status, selected_years, sdg_dropdown_value)

        return fig2


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
            Output('sdg-time-series', 'figure'),
              # Update the line plot
            [
                Input('program', 'value'),  # Trigger when the college checklist changes
                Input('status', 'value'),
                Input('years', 'value'),
                Input('sdg-dropdown', 'value')
            ]
        )
        def update_lineplot(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            # Fallback to defaults if inputs are not provided
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years

            # Update the line plot with filtered data
            return self.update_figures(selected_programs, selected_status, selected_years,sdg_dropdown_value)

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
        
        # Callback to update content based on the user role and other URL parameters
        @self.dash_app.callback(
            Output('college-info', 'children'),
            Input('url', 'search')  # Capture the query string in the URL
        )
        def update_user_role_and_info(url_search):
            if url_search is None or url_search == '':
                return html.H3('Welcome Guest! Please log in.'), html.H3('College: Unknown'), html.H3('Program: Unknown')
            
            # Parse the URL parameters directly from the search
            params = dict((key, value) for key, value in (param.split('=') for param in url_search[1:].split('&')))
            self.college = params.get('college', 'Unknown College')  # Default to 'Unknown College' if no college is passed
            self.program = params.get('program', 'Unknown Program')  # Default to 'Unknown Program' if no program is passed

            self.default_programs = db_manager.get_unique_values_by('program_id','college_id',self.college)
            print(f'self.default_programs: {self.default_programs}\ncollege: {self.college}')

            # Return the role, college, and program information
            return html.H3(
                    f'College Department: {self.college}', 
                    style={
                        'textAlign': 'center',
                        'marginTop': '10px'
                    }
            )
        
        
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_shared_data_store(n_intervals):
            updated_data = db_manager.get_all_data()
            return updated_data.to_dict('records')
        
                # Callback to update the header based on selected SDG
        @self.dash_app.callback(
            Output("chosen-sdg", "children"),
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
            title="Overall SDG" if selected_sdg=="ALL" else selected_sdg+":"
                
            caption = label.get(selected_sdg, "") if selected_sdg else ""

            return f"{title} {caption}"
        
        