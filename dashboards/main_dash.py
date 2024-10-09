from dash import Dash, html, dcc,dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px

class MainDashboard:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/overview/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.palette_dict = {
            'MITL': 'red',
            'ETYCB': 'yellow',
            'CCIS': 'green',
            'CAS': 'blue',
            'CHS': 'orange'
        }
        self.create_layout()
        self.set_callbacks()

    def create_layout(self):
        """
        Create the layout of the dashboard.
        """

        college = html.Div(
            [
                dbc.Label("Select College:"),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=db_manager.get_unique_values('college_id'),
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
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('status')],
                    value=db_manager.get_unique_values('status'),
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        slider = html.Div(
            [
                dbc.Label("Select Years"),
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
                html.H4("Filters", style={"margin": "10px 0px"}),
                college, status, slider, button
            ],
            body=True,
            style={"height": "95vh", "display": "flex", "flexDirection": "column"}
        )

        text_display = dbc.Container([
                dbc.Row([
                    dbc.Col(
                        self.create_display_card("Total Research Papers", str(len(db_manager.get_all_data()))),
                        width=3
                    ) for _ in range(4)  # Creates 4 identical columns for demonstration
                ])
            ],style={"transform": "scale(0.9)", "transform-origin": "0 0"})  # Adjust the scale as needed

        main_dash = dbc.Container([
                dbc.Row([  # Row for the line and pie charts
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(0.9)", "transform-origin": "0 0"})  # Adjust the scale as needed

        """sub_dash = dbc.Container([
                dbc.Row([
                dbc.Col(dcc.Graph(id='scopus_bar_plot', width=6, style={"height": "auto", "overflow": "hidden", "border": "1px solid #ddd"})),
                dbc.Col(dcc.Graph(id='publication_format_bar_plot', width=6, style={"height": "auto", "overflow": "hidden", "border": "1px solid #ddd"})),
            ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(0.9)", "transform-origin": "0 0"})  # Adjust the scale as needed"""
        
        self.dash_app.layout = html.Div([
                dbc.Container(
                    [
                        dbc.Row([
                            dbc.Col(controls, width=2),
                            dbc.Col([
                                text_display,
                                main_dash,
                                #sub_dash
                            ], width=10,style={"transform": "scale(0.9)", "transform-origin": "0 0"}),
                        ])
                    ],
                    fluid=True,
                    className="dbc dbc-ag-grid",
                    style={"overflow": "hidden"}
                ),
                dash_table.DataTable(
                    id='research-table',
                    columns=[],  # Columns will be populated by callback
                    data=[],  # Data will be populated by callback
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    page_size=30  # Set page size for better UX
                ),
                dcc.Interval(
                    id='interval-component',
                    interval=60 * 1000,  # Update every 1 minute (optional)
                    n_intervals=0
                )
            ], style={"padding": "20px"})


    def create_display_card(self, title, value):
        """
        Create a display card for showing metrics.
        """
        return html.Div([
            dbc.Col(html.Div([
                html.H5(title, style={'textAlign': 'center'}),
                html.H2(value, style={'textAlign': 'center'})
            ], style={
                            "border": "1px solid #007bff",  # Change color as needed
                            "borderRadius": "10px",          # Adjust the roundness
                            "padding": "10px",               # Add some padding inside the card
                            "margin": "5px"                  # Space between columns
                        }))
        ])
    
    def update_line_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if len(selected_colleges) == 1:
            grouped_df = df.groupby(['program_name', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_name'
            title = f'Number of Publications for {selected_colleges[0]}'
        else:
            grouped_df = df.groupby(['college_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'college_id'
            title = 'Number of Publications per College'

        fig_line = px.line(
            grouped_df, 
            x='year', 
            y='TitleCount', 
            color=color_column, 
            markers=True,
            color_discrete_map=self.palette_dict
        )
        
        fig_line.update_layout(
            title=title,
            xaxis_title='Academic Year',
            yaxis_title='Number of Publications',
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            showlegend=False  
        )

        return fig_line
    
    def update_pie_chart(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if len(selected_colleges) == 1:
            college_name = selected_colleges[0]
            filtered_df = df[df['college_id'] == college_name]
            detail_counts = filtered_df.groupby('program_name').size()
            title = f'Number of Publications for {college_name}'
        else:
            detail_counts = df.groupby('college_id').size()
            title = ''
        
        fig_pie = px.pie(
            names=detail_counts.index,
            values=detail_counts,
            color=detail_counts.index,
            color_discrete_map=self.palette_dict,
            labels={'names': 'Category', 'values': 'Number of Publications'},
        )

        fig_pie.update_layout(
            title=title,
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400
        )

        return fig_pie
    
    
    
    def update_table(n):
            # Fetch data from the database using DatabaseManager
            df = db_manager.get_all_data()

            # Format the data for the DataTable
            data = df.to_dict('records')  # Convert DataFrame to a list of dictionaries
            columns = [{'name': col, 'id': col} for col in df.columns]  # Columns format

            return data, columns

    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """
        @self.dash_app.callback(
            [Output('research-table', 'data'), Output('research-table', 'columns')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_table_callback(n):
            return self.update_table()
        
        @self.dash_app.callback(
            Output('college_line_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value')
            ]
        )
        def update_lineplot(selected_colleges, selected_status, selected_years):
            return self.update_line_plot(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('college_pie_chart', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value')
            ]
        )
        def update_piechart(selected_colleges, selected_status, selected_years):
            return self.update_pie_chart(selected_colleges, selected_status, selected_years)
        
