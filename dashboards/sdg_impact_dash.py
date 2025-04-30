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
from services.sdg_colors import sdg_colors
from charts.sdg_charts import get_total_proceeding_count,create_sdg_plot, create_sdg_pie_chart,create_sdg_research_chart,create_geographical_heatmap,create_geographical_treemap,create_conference_participation_bar_chart,create_local_vs_foreign_donut_chart,get_word_cloud,generate_research_area_visualization,generate_sdg_bipartite_graph,visualize_sdg_impact

def default_if_empty(selected_values, default_values):
    return selected_values if selected_values else default_values


class SDG_Impact_Dash:
    def __init__(self, server, title=None, college=None, program=None, **kwargs):
        self.dash_app = Dash(
            __name__,
            server=server,
            url_base_pathname=kwargs.get('url_base_pathname', '/sdg-impact/'),
            external_stylesheets=[dbc.themes.BOOTSTRAP, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"]
        )
        self.title = title
        self.college = college
        self.program = program

        self.palette_dict = db_manager.get_college_colors()
        self.sdg_colors=sdg_colors
        self.all_sdgs = [f'SDG {i}' for i in range(1, 18)]
        # Get default values
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        self.default_pub_format = db_manager.get_unique_values('journal')[db_manager.get_unique_values('journal') != "unpublished"]
        

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

        pub_formats = sorted([value for value in db_manager.get_unique_values('journal') if value.lower() != 'unpublished'])
        pub_form = html.Div( [
            dbc.Label("Select Publication Type/s:", style={"color": "#08397C"}),
            dbc.Checklist(
                id='pub_form',
                options=[{'label': value, 'value': value} for value in pub_formats],
                value=[],
                inline=True,
            ),
        ], className="mb-4", )

        pub_form_container = html.Div(
            id="pub_form_container",
            children=[pub_form]
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
            status,
            pub_form_container,
            slider,
            button
        ], width=2, className="p-3", 
        style={"background": "#d3d8db", "height": "100vh", "position": "fixed", "left": 0, "top": 0, "zIndex": 1000})

        main_content = dbc.Col([
            dcc.Location(id="url", refresh=False),
            html.Div(id="dynamic-header"),
            
            html.Div(
                id="selected-filters-display",
                style={
                    "margin-top": "10px",
                    "margin-bottom": "10px",
                    "width": "100%"
                }
            ),
            
            html.Div(id="tabs-container", children=Tabs(
                tabs_data=[
                    ("Institutional SDG Impact", self.collage),
                    ("Global Research Proceedings", self.map),
                    ("Research Trends and Collaboration", self.trend)
                ],
                tabs_id="tabs"
            )),
            
        ], width=10, className="p-3", style={"marginLeft": "16.67%"})





        self.dash_app.layout = html.Div([
            dbc.Container([
                dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),
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
        @self.dash_app.callback(
            Output("pub_form_container", "style"),
            Input("tabs", "active_tab")  # This refers to the id of the Tabs component
        )
        def toggle_pub_form(active_tab):
            if active_tab == "tab-2":  # "tab-2" corresponds to the second tab
                return {"display": "none"}
            else:
                return {"display": "block"}
        @self.dash_app.callback(
            [Output('college', 'value'),
            Output('status', 'value'),
            Output('years', 'value'),
            Output('sdg-dropdown', 'value'),
            Output('pub_form', 'value')],
            [Input('reset_button', 'n_clicks')],
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')], "ALL",[]

        @self.dash_app.callback(
            Output("dynamic-header", "children"),
            Input("url", "search")  # Extracts the query string (e.g., "?user=John&role=Admin")
        )
        def update_header(search):
            if search:
                params = parse_qs(search.lstrip("?"))  # Parse query parameters
                user_role = params.get("user-role",["Guest"])[0]
                college = params.get("college", [""])[0]
                program = params.get("program", [""])[0]

            view=""

            if user_role == "02":
                view="RPCO Director"    
                college=""
                program=""
            elif user_role =="03":
                view="Head Executive"    
                college=""
                program=""
            else:
                view="Unknown"
            return DashboardHeader(left_text=college, title=f"SDG IMPACT DASHBOARD ")
        
                # --- Your callback ---
        @self.dash_app.callback(
            Output("selected-filters-display", "children"),
            [
                Input("college", "value"),
                Input("status", "value"),
                Input("pub_form", "value"),
                Input('sdg-dropdown', 'value'),
                Input("years", "value")
            ]
        )
        def update_selected_filters_display(colleges,statuses, pub_formats, sdg_dropdown,years):
            """
            Update the selected filters display in a single line format
            """
            print("Callback triggered:", colleges,  statuses, pub_formats,sdg_dropdown, years)

            if not any([colleges, statuses, pub_formats,sdg_dropdown, years]):
                return html.Div([
                    html.I(className="fas fa-info-circle me-2"),
                    html.Span("No specific filters selected. Displaying all data within the selected years."),
                ], style={
                    "padding": "10px",
                    "background-color": "#e9ecef",
                    "border-left": "4px solid #6c757d",
                    "border-radius": "4px",
                    "color": "#495057",
                    "font-style": "italic"
                })

            filter_tags = []

            colors = {
                "colleges": {"bg": "#cfe2ff", "border": "#0d6efd", "text": "#084298"},
                "programs": {"bg": "#d1e7dd", "border": "#198754", "text": "#0f5132"},
                "statuses": {"bg": "#fff3cd", "border": "#ffc107", "text": "#664d03"},
                "pub_formats": {"bg": "#f8d7da", "border": "#dc3545", "text": "#842029"},
                "sdg_dropdown": {"bg": "#e2e3e5", "border": "#6c757d", "text": "#41464b"},
                "years": {"bg": "#dff1fb", "border": "#0dcaf0", "text": "#055160"}
            }

            # Add SDG as tags
            if sdg_dropdown:
                if sdg_dropdown=="ALL":
                    sdg_dropdown="ALL SDG"
                filter_tags.append(html.Span([
                    html.I(className="fas fa-bullseye me-1", style={"font-size": "0.75rem"}),
                    sdg_dropdown
                ], style={
                    "background-color": colors["sdg_dropdown"]["bg"],
                    "border": f"1px solid {colors['sdg_dropdown']['border']}",
                    "color": colors["sdg_dropdown"]["text"],
                    "margin": "0 5px 0 0",
                    "padding": "3px 8px",
                    "border-radius": "16px",
                    "display": "inline-block",
                    "font-size": "0.75rem"
                }))


            # Colleges
            if colleges:
                for college in colleges:
                    filter_tags.append(html.Span([
                        html.I(className="fas fa-university me-1", style={"font-size": "0.75rem"}),
                        college
                    ], style={
                        "background-color": colors["colleges"]["bg"],
                        "border": f"1px solid {colors['colleges']['border']}",
                        "color": colors["colleges"]["text"],
                        "margin": "0 5px 0 0",
                        "padding": "3px 8px",
                        "border-radius": "16px",
                        "display": "inline-block",
                        "font-size": "0.75rem"
                    }))

          
            # Statuses
            if statuses:
                for status in statuses:
                    status_icon = {
                        "READY": "fas fa-file-import",
                        "SUBMITTED": "fas fa-file-export",
                        "ACCEPTED": "fas fa-check-circle",
                        "PUBLISHED": "fas fa-file-alt",
                        "PULLOUT": "fas fa-file-excel"
                    }.get(status, "fas fa-tag")

                    filter_tags.append(html.Span([
                        html.I(className=f"{status_icon} me-1", style={"font-size": "0.75rem"}),
                        status
                    ], style={
                        "background-color": colors["statuses"]["bg"],
                        "border": f"1px solid {colors['statuses']['border']}",
                        "color": colors["statuses"]["text"],
                        "margin": "0 5px 0 0",
                        "padding": "3px 8px",
                        "border-radius": "16px",
                        "display": "inline-block",
                        "font-size": "0.75rem"
                    }))

            # Publication formats
            if pub_formats:
                for pub_format in pub_formats:
                    filter_tags.append(html.Span([
                        html.I(className="fas fa-book me-1", style={"font-size": "0.75rem"}),
                        pub_format
                    ], style={
                        "background-color": colors["pub_formats"]["bg"],
                        "border": f"1px solid {colors['pub_formats']['border']}",
                        "color": colors["pub_formats"]["text"],
                        "margin": "0 5px 0 0",
                        "padding": "3px 8px",
                        "border-radius": "16px",
                        "display": "inline-block",
                        "font-size": "0.75rem"
                    }))

            # Years
            if years:
                filter_tags.append(html.Span([
                    html.I(className="fas fa-clock me-1", style={"font-size": "0.75rem"}),
                    f"{years[0]} - {years[1]}"
                ], style={
                    "background-color": colors["years"]["bg"],
                    "border": f"1px solid {colors['years']['border']}",
                    "color": colors["years"]["text"],
                    "margin": "0 5px 0 0",
                    "padding": "3px 8px",
                    "border-radius": "16px",
                    "display": "inline-block",
                    "font-size": "0.75rem"
                }))

            # Final display
            return html.Div([
                html.Span([
                    html.I(className="fas fa-filter me-2", style={"color": "#08397C"}),
                    "Active Filters: "
                ], style={"font-weight": "600", "color": "#08397C", "margin-right": "10px", "white-space": "nowrap"}),

                html.Div(filter_tags, style={
                    "display": "inline-flex",
                    "flex-wrap": "wrap",
                    "align-items": "center"
                })
            ], style={
                "display": "flex",
                "align-items": "center",
                "padding": "8px 15px",
                "background-color": "#f8f9fa",
                "border-radius": "8px",
                "border": "1px solid #dee2e6",
                "box-shadow": "0 1px 3px rgba(0,0,0,0.05)"
            })
    
        @self.dash_app.callback(
            Output('sdg-time-series', 'figure'),
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value'),
            Input('sdg-dropdown', 'value'),
            Input('pub_form', 'value')]
        )
        def update_all(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_pub_form = default_if_empty(selected_pub_form, self.default_pub_format)
            return create_sdg_plot(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form)


        @self.dash_app.callback(
            Output('sdg-pie', 'figure'),
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value'),
            Input('sdg-dropdown', 'value'),
            Input('pub_form', 'value')]
        )
        def update_all_pie(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_pub_form = default_if_empty(selected_pub_form, self.default_pub_format)
            return visualize_sdg_impact(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form)


        @self.dash_app.callback(
            Output('sdg-research-type', 'figure'),
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value'),
            Input('sdg-dropdown', 'value'),
            Input('pub_form', 'value')]  # <--- Added here
        )
        def update_fig1(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_pub_form = default_if_empty(selected_pub_form, self.default_pub_format)
            return create_sdg_research_chart(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form)

        @self.dash_app.callback(
            Output('sdg-map', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return create_geographical_heatmap(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('tree-map', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return create_geographical_treemap(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        @self.dash_app.callback(
            Output('participation-graph', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return create_conference_participation_bar_chart(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        @self.dash_app.callback(
            Output('local-vs-foreign', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return create_local_vs_foreign_donut_chart(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        @self.dash_app.callback(
            Output('word-cloud', 'figure'),
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value'),
            Input('sdg-dropdown', 'value'),
            Input('pub_form', 'value')]  # Added pub_form here
        )
        def update_fig(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_pub_form = default_if_empty(selected_pub_form, self.default_pub_format)
            return get_word_cloud(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form)


        @self.dash_app.callback(
            Output('research-areas', 'figure'),
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value'),
            Input('sdg-dropdown', 'value'),
            Input('pub_form', 'value')]  # Added pub_form here
        )
        def update_fig(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_pub_form = default_if_empty(selected_pub_form, self.default_pub_format)
            return generate_research_area_visualization(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form)


        @self.dash_app.callback(
            Output('sdg-graph', 'figure'),
            [Input('college', 'value'), 
            Input('status', 'value'), 
            Input('years', 'value'),
            Input('sdg-dropdown', 'value'),
            Input('pub_form', 'value')]  # Added pub_form here
        )
        def update_fig(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_pub_form = default_if_empty(selected_pub_form, self.default_pub_format)
            return generate_sdg_bipartite_graph(selected_colleges, selected_status, selected_years, sdg_dropdown_value, selected_pub_form)

        @self.dash_app.callback([
                Output("alert-message", "children"),
                Output("alert-message", "color")],  # ✅ Change color dynamically
                [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('sdg-dropdown', 'value')]
        )
        def update_alert_message(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years

            return get_total_proceeding_count(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        

