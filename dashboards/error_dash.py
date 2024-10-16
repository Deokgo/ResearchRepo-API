# created by Jelly Mallari

from dash import Dash, html, dcc,dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

class ErrorPageApp:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/error/', 
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

    def setup_layout(self):
        # Layout of the Error Page
        self.app.layout = html.Div([
            html.H1("Oops! Something went wrong.", style={'color': 'red'}),
            html.P("We're sorry, but the page you requested could not be found."),
            html.A("Go back to the homepage", href='/'),
            dcc.Location(id='url', refresh=False)  # Tracks the current URL
        ])

    def run(self):
        # Run the app
        self.app.run_server(debug=True)

        
