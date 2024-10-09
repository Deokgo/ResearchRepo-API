#Created by Jelly Mallari

from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from dash import dash_table 
from dash.dependencies import Input, Output
from . import db_manager

def create_main_dashboard(flask_app):
    """
    Function to create the main dashboard route at `/dashboard`.
    Adds the layout and callback logic for the dashboard.
    """
    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/main/', external_stylesheets=[dbc.themes.BOOTSTRAP])
    dash_app.layout = html.Div([
        html.H1("Research Outputs Data"),
        
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
    ])

    # Callback to fetch data from the database and update the table
    @dash_app.callback(
        [Output('research-table', 'data'), Output('research-table', 'columns')],
        [Input('interval-component', 'n_intervals')]
    )
    def update_table(n):
        # Fetch data from the database using DatabaseManager
        df = db_manager.get_all_data()

        # Format the data for the DataTable
        data = df.to_dict('records')  # Convert DataFrame to a list of dictionaries
        columns = [{'name': col, 'id': col} for col in df.columns]  # Columns format

        return data, columns
