from dash import Dash, html, dcc
import dash_bootstrap_components as dbc

def create_main_dashboard(server):
    # Create Dash app
    dash_app = Dash(__name__, server=server, url_base_pathname='/dashboard/')
    
    # Define layout for the main dashboard
    dash_app.layout = html.Div([
        html.H1("Main Dashboard"),
        dbc.NavLink('Go back to SDG Dashboard',external_link=True, href='/dashboard/sdg'),
        html.Br(),
        dbc.NavLink('Go to Analytics Dashboard',external_link=True, href='/dashboard/analytics')
    ])

    return dash_app
