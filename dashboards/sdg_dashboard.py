from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

def create_sdg_dashboard(flask_app):
    """
    Function to create the SDG dashboard route at `/dashboard/sdg`.
    Adds the layout and callback logic for the SDG dashboard.
    """
    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/sdg/', external_stylesheets=[dbc.themes.BOOTSTRAP])

    dash_app.layout = html.Div([
        html.H1("SDG Dashboard"),
        dcc.Graph(id='sdg-graph')
    ])

    # You can add any callbacks here

    return dash_app
