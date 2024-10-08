# Created by Jelly Mallari
import dash
from dash import dcc, html
import plotly.graph_objs as go

def create_dash_app(flask_app):
    # Initialize Dash with the Flask server
    dash_app = dash.Dash(__name__, server=flask_app, url_base_pathname='/dashboard/')

    # Dash layout
    dash_app.layout = html.Div(children=[
        html.H1('Research Data Dashboard'),
        dcc.Graph(
            id='example-graph',
            figure={
                'data': [
                    go.Scatter(
                        x=[1, 2, 3, 4],
                        y=[10, 11, 12, 13],
                        mode='lines+markers',
                        name='Line Plot'
                    )
                ],
                'layout': go.Layout(
                    title='Simple Dash Graph',
                    xaxis={'title': 'X Axis'},
                    yaxis={'title': 'Y Axis'}
                )
            }
        )
    ])

    return dash_app
