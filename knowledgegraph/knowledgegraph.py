import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict
from flask import Flask
from . import db_manager

def create_kg_sdg(flask_app):
    df = db_manager.get_all_data()

    G = nx.Graph()
    connected_nodes = defaultdict(list)

    for index, row in df.iterrows():
        study = row['title']
        sdg = row['sdg']

        G.add_node(study, type='study')

        sdg = sdg.strip()
        if not G.has_node(sdg):
            G.add_node(sdg, type='sdg')

        # Track which studies are connected to which sdg
        connected_nodes[sdg].append(study)
        G.add_edge(sdg, study)  

    sdg_nodes = [node for node in G.nodes() if G.nodes[node]['type'] == 'sdg']
    pos = nx.spring_layout(G.subgraph(sdg_nodes), k=1.0, weight='weight')

    # Node attributes (initially, only SDG nodes are shown)
    node_x = []
    node_y = []
    hover_text = []
    node_labels = []
    node_color = []
    node_size = []

    for node in sdg_nodes:
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        hover_text.append(f"{len(connected_nodes[node])} studies connected")
        node_color.append('green')
        node_size.append(20 + len(connected_nodes[node]))  
        node_labels.append(node)  

    edge_x = []
    edge_y = []

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
                'data': [node_trace],  
                'layout': go.Layout(
                    title='<br>Research Studies Knowledge Graph (sdg nodes)',
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

    @dash_app.callback(
        Output('network-graph', 'figure'),
        [Input('network-graph', 'hoverData'),
         Input('network-graph', 'clickData')]
    )
    def update_graph_on_hover_and_click(hoverData, clickData):
        hovered_node = None
        clicked_node = None

        if hoverData and 'points' in hoverData:
            hovered_node = hoverData['points'][0]['text']

        if clickData and 'points' in clickData:
            clicked_node = clickData['points'][0]['text']

        if clicked_node and clicked_node in G.nodes and G.nodes[clicked_node]['type'] == 'sdg':
            new_node_x = []
            new_node_y = []
            new_hover_text = []
            new_node_labels = []
            new_node_color = []
            new_node_size = []

            subgraph = G.subgraph([clicked_node] + connected_nodes[clicked_node])
            new_pos = nx.spring_layout(subgraph, k=1.0)

            for node in subgraph:
                x, y = new_pos[node]
                new_node_x.append(x)
                new_node_y.append(y)
                new_hover_text.append(node)
                if G.nodes[node].get('type') == 'sdg':
                    new_node_color.append('blue')  # Center SDG node
                    new_node_size.append(30)
                else:
                    new_node_color.append('red')
                    new_node_size.append(15)
                new_node_labels.append(node)

            new_edge_x = []
            new_edge_y = []
            for edge in subgraph.edges():
                x0, y0 = new_pos[edge[0]]
                x1, y1 = new_pos[edge[1]]
                new_edge_x.append(x0)
                new_edge_x.append(x1)
                new_edge_x.append(None)
                new_edge_y.append(y0)
                new_edge_y.append(y1)
                new_edge_y.append(None)

            # Create traces for edges and nodes after clicking
            clicked_edge_trace = go.Scatter(
                x=new_edge_x, y=new_edge_y,
                line=dict(width=0.5, color='#888'),
                hoverinfo='none',
                mode='lines'
            )

            clicked_node_trace = go.Scatter(
                x=new_node_x, y=new_node_y,
                mode='markers+text',
                text=new_node_labels,
                hovertext=new_hover_text,
                marker=dict(
                    color=new_node_color,
                    size=new_node_size,
                ),
                hoverinfo='text'
            )

            return {
                'data': [clicked_edge_trace, clicked_node_trace],
                'layout': go.Layout(
                    title=f"<br>Research Studies Knowledge Graph - {clicked_node}",
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

        return {
            'data': [node_trace],  
            'layout': go.Layout(
                title='<br>Research Studies Knowledge Graph (sdg nodes)',
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

    return dash_app
