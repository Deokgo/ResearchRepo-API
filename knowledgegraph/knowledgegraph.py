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

        connected_nodes[sdg].append(study)
        G.add_edge(sdg, study)  

    pos = nx.spring_layout(G, k=1.0, weight='weight')
    
    fixed_pos = {node: pos[node] for node in G.nodes()}

    def build_traces(nodes_to_show, edges_to_show):
        node_x = []
        node_y = []
        hover_text = []
        node_labels = []
        node_color = []
        node_size = []

        for node in nodes_to_show:
            x, y = fixed_pos[node]
            node_x.append(x)
            node_y.append(y)

            if G.nodes[node]['type'] == 'sdg':
                hover_text.append(f"{len(connected_nodes[node])} studies connected")
                node_color.append('green')
                node_size.append(20 + len(connected_nodes[node]))  
                node_labels.append(node)
            else:
                hover_text.append(node)  
                node_color.append('red')
                node_size.append(10)
                node_labels.append(node)

        edge_x = []
        edge_y = []
        for edge in edges_to_show:
            x0, y0 = fixed_pos[edge[0]]
            x1, y1 = fixed_pos[edge[1]]
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
            mode='lines'
        )

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

        return edge_trace, node_trace

    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/knowledgegraph/')

    sdg_nodes = [node for node in G.nodes() if G.nodes[node]['type'] == 'sdg']
    edge_trace, node_trace = build_traces(sdg_nodes, [])

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
            subgraph = G.subgraph([clicked_node] + connected_nodes[clicked_node])
            nodes_to_show = list(subgraph.nodes)
            edges_to_show = list(subgraph.edges)

            edge_trace, node_trace = build_traces(nodes_to_show, edges_to_show)

            return {
                'data': [edge_trace, node_trace],
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
