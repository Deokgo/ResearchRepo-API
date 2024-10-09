import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import networkx as nx
import numpy as np
from collections import defaultdict
from flask import Flask
from . import db_manager

def create_kg_sdg(flask_app):
    df = db_manager.get_all_data()
    G = nx.Graph()
    connected_nodes = defaultdict(list)


    for index, row in df.iterrows():
        study = row['title']  
        authors = row['concatenated_authors']  
        sdgs = row['sdg']
        
        G.add_node(study, label=authors, title=row['title'], type='study', year=row['date_published'])
        
        for sdg in sdgs:
            sdg = sdg.strip()
            if not G.has_node(sdg):
                G.add_node(sdg, type='sdg')
            connected_nodes[sdg].append(study)
            G.add_edge(study, sdg, weight=2 if len(sdgs) > 1 else 1)

    pos = nx.spring_layout(G, k=1.0, weight='weight', iterations=100)

    node_x = []
    node_y = []
    hover_text = []
    node_labels = []
    node_color = []
    node_size = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        hover_text.append(G.nodes[node].get('title', node))
        
        if G.nodes[node]['type'] == 'sdg':
            node_color.append('green')
            node_size.append(20)
            node_labels.append(G.nodes[node].get('label', node))
        else:
            node_color.append('red')
            node_size.append(10)
            node_labels.append(f"{G.nodes[node].get('label')} ({G.nodes[node].get('year')})")

    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_labels,
        hovertext=hover_text,
        marker=dict(
            color=node_color,
            size=node_size,
        ),
        hoverinfo='text'
    )

    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/knowledgegraph/')

    # Layout for Dash app
    dash_app.layout = html.Div([
        dcc.Graph(
            id='network-graph',
            figure={
                'data': [edge_trace, node_trace],
                'layout': go.Layout(
                    title='<br>Research Studies Knowledge Graph',
                    titlefont=dict(size=16),
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0, l=0, r=0, t=50),
                    width=1200,
                    height=800,
                    xaxis=dict(showgrid=False, zeroline=False),
                    yaxis=dict(showgrid=False, zeroline=False)
                )
            }
        )
    ])

    # Callback for hover interaction
    @dash_app.callback(
        Output('network-graph', 'figure'),
        [Input('network-graph', 'hoverData')]
    )
    def update_nodes_on_hover(hoverData):
        if hoverData is None:
            return {
                'data': [edge_trace, node_trace],
                'layout': go.Layout(
                    title='<br>Research Studies Knowledge Graph',
                    titlefont=dict(size=16),
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0, l=0, r=0, t=50),
                    width=1200,
                    height=800,
                    xaxis=dict(showgrid=False, zeroline=False),
                    yaxis=dict(showgrid=False, zeroline=False)
                )
            }
        
        hovered_node = hoverData['points'][0]['text']
        new_node_color = []
        new_node_size = []
        
        for node in G.nodes():
            if node == hovered_node or node in connected_nodes.get(hovered_node, []):
                new_node_color.append('blue')  
                new_node_size.append(15)
            else:
                new_node_color.append('red' if G.nodes[node]['type'] == 'study' else 'green')
                new_node_size.append(10 if G.nodes[node]['type'] == 'study' else 20)
        
        updated_node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_labels,
            hovertext=hover_text,
            marker=dict(
                color=new_node_color,
                size=new_node_size,
            ),
            hoverinfo='text'
        )
        
        return {
            'data': [edge_trace, updated_node_trace],
            'layout': go.Layout(
                title='<br>Research Studies Knowledge Graph',
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=50),
                width=1200,
                height=800,
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False)
            )
        }

