from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

def create_sdg_dashboard(server):
    # Create Dash app
    dash_app = Dash(__name__, server=server, url_base_pathname='/dashboard/sdg/')
    
    # Define layout for the SDG dashboard
    dash_app.layout = html.Div([
        html.H1("SDG Dashboard"),
        dbc.NavLink('Go back to Main Dashboard',external_link=True, href='/dashboard'),
        html.Br(),
        dbc.NavLink('Go to Analytics Dashboard', href='/dashboard/analytics')
    ])

    return dash_app
