# created by Jelly Mallari (Oct 9)
# continued by Nicole Cabansag (UI, Oct 9)

from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash import dash_table 
from dash.dependencies import Input, Output
from . import db_manager
import dash_ag_grid as dag
import dash_table

class DashApp:
    def __init__(self, flask_app):
        self.flask_app = flask_app
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/main/', external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.PLOTLY_LOGO = "https://i.imghippo.com/files/8hU5H1724158029.png"
        self.df = db_manager.get_all_data()
        self.palette_dict = {
            'MITL': 'red',
            'ETYCB': 'yellow',
            'CCIS': 'green',
            'CAS': 'blue',
            'CHS': 'orange'
        }
        self.all_sdgs = [
            'SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 
            'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 
            'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17'
        ]

        """
        unique status for filter
        """

        #initialize layout
        self.set_layout()

        #register callbacks
        self.register_callbacks()

    def set_layout(self):

        """
        college = html.Div(
            [
                dbc.Label("Select College:"),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in self.df.get_unique_values('College')],
                    value=self.data_loader.get_unique_values('College'),
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
                    options=[{'label': value, 'value': value} for value in self.data_loader.get_unique_values('PUBLISHED')],
                    value=self.data_loader.get_unique_values('PUBLISHED'),
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        slider = html.Div(
            [
                dbc.Label("Select Years"),
                dcc.RangeSlider(
                    min=self.data_loader.get_min_value('Year'), 
                    max=self.data_loader.get_max_value('Year'), 
                    step=1, 
                    id="years",
                    marks=None,
                    tooltip={"placement": "bottom", "always_visible": True},
                    value=[self.data_loader.get_min_value('Year'), self.data_loader.get_max_value('Year')],
                    className="p-0",
                ),
            ],
            className="mb-4",
        )
        """

        
        upper_dash = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4("NUMBER OF RESEARCH PAPERS", style={'textAlign': 'center'}),
                        html.H2('sample', style={'textAlign': 'center', 'fontSize': '60px'}),
                    ], style={'border': '1px solid black', 'padding': '20px', 'height': '100%'})
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H4("NUMBER OF PUBLISHED PAPERS", style={'textAlign': 'center'}),
                        html.H2('sample', style={'textAlign': 'center', 'fontSize': '60px'}),
                    ], style={'border': '1px solid black', 'padding': '20px', 'height': '100%'})
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H4("NUMBER OF ON-GOING PAPERS", style={'textAlign': 'center'}),
                        html.H2('sample', style={'textAlign': 'center', 'fontSize': '60px'}),
                    ], style={'border': '1px solid black', 'padding': '20px', 'height': '100%'})
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H4("NUMBER OF NEWLY SUBMITTED PAPERS", style={'textAlign': 'center'}),
                        html.H2('sample', style={'textAlign': 'center', 'fontSize': '60px'}),
                    ], style={'border': '1px solid black', 'padding': '20px', 'height': '100%'})
                ], width=3)   
                ])
        ], style={'marginBottom': '20px'})

        main_dash = dbc.Container([
            dbc.Row([
                dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "400px", "overflow": "hidden"}),
                dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "400px", "overflow": "hidden"})
            ], style={"margin": "20px", "padding": "10px"}),

            dbc.Row([
                dbc.Col(dcc.Graph(id='proceeding_journal_bar_plot', style={"margin": "5px"}), width=6, style={"height": "450px", "overflow": "hidden", "border": "1px solid #ddd", "padding": "20px"}),
                dbc.Col(dcc.Graph(id='research_repos_status_bar_plot', style={"margin": "5px"}), width=6, style={"height": "450px", "overflow": "hidden", "border": "1px solid #ddd", "padding": "20px"}),
            ])
        ], fluid=True)

        tab2_content = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dbc.Row(
                        dbc.Col(
                            dcc.Graph(id='geo_chart_conference'),
                            width=12,
                            style={"height": "450px", "overflow": "hidden"}  
                        )
                    ),
                    dbc.Row(
                        dbc.Col(
                            dash_table.DataTable(
                                id='data_table',
                                data=self.update_table()[0],  
                                columns=self.update_table()[1], 
                                style_table={'height': '400px', 'overflowY': 'auto'},
                                style_cell={'textAlign': 'left', 'padding': '5px'},
                                style_header={
                                    'backgroundColor': 'rgb(230, 230, 230)',
                                    'fontWeight': 'bold'
                                },
                                tooltip_data=[{'value': 'Sample tooltip'}], 
                                tooltip_duration=None 
                            ),
                            width=12,
                            style={"height": "450px", "border": "1px solid #ddd", "padding": "20px"}
                        )
                    )
                ], width=8),  

                dbc.Col([
                    dbc.Row(
                        dbc.Col(
                            dcc.Graph(id='publication_line_plot'),
                            style={"height": "225px", "overflow": "hidden", "border": "1px solid #ddd"}  # Fixed height
                        )
                    ),
                    dbc.Row(
                        dbc.Col(
                            dcc.Graph(id='research_publication_status_bar_plot'),
                            style={"height": "225px", "overflow": "hidden", "border": "1px solid #ddd"}  # Fixed height
                        )
                    ),
                    dbc.Row(
                        dbc.Col(
                            dcc.Graph(id='scopus_bar_plot'),
                            style={"height": "auto", "overflow": "hidden", "border": "1px solid #ddd"}
                        )
                    )
                ], width=4)  
            ], style={"margin": "20px", "padding": "10px"}),
        ], fluid=True)

        tab1 = dbc.Tab(main_dash, label="RESEARCH PERFORMANCE OF INSTITUTION")
        tab2 = dbc.Tab(tab2_content, label="PUBLICATIONS OF INSTITUTION")
        tabs = dbc.Card(dbc.Tabs([tab1, tab2]))

        button = html.Div(
            [
                dbc.Button("Reset", color="primary", id="reset_button"),
            ],
            className="d-grid gap-2",
        )

        controls = dbc.Card(
            [
                html.H4("Filters", style={"margin": "20px 0px"}),
                button #college, status, slider, 
            ],
            body=True,
            style={"height": "120vh", "display": "flex", "flexDirection": "column"}
        )

        self.dash_app.layout = html.Div([
            dbc.Container(
                [
                    dbc.Row([
                        dbc.Col([upper_dash,tabs], width=10),
                        dbc.Col(controls, width=2),
                    ], style={"paddingTop": "60px"})
                ],
                fluid=True,
                className="dbc dbc-ag-grid",
                style={"margin": "20px", "overflow": "hidden", "backgroundColor": "#f8f9fa"}
            )
        ])

    def update_table(self):
        #fetch data from the database using DatabaseManager
        #format the data for the DataTable
        data = self.df.to_dict('records')  #convert DataFrame to a list of dictionaries
        columns = [{'name': col, 'id': col} for col in self.df.columns]  #columns format

        return data, columns

    def register_callbacks(self):
        #register callback to fetch data from the database and update the table
        @self.dash_app.callback(
            [Output('research-table', 'data'), Output('research-table', 'columns')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_table_callback(n):
            return self.update_table(n)


def create_main_dashboard(flask_app):
    dash_app = DashApp(flask_app)
    return dash_app
