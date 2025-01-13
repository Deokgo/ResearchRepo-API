import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict
from flask import Flask
from . import db_manager
import pandas as pd

def collection_kg(flask_app):
    df = db_manager.get_all_data()
    df['date_approved'] = pd.to_datetime(df['date_approved'], errors='coerce')
    G = nx.Graph()
    connected_nodes = defaultdict(list)

    # Define color palette for colleges
    palette_dict = {
        'MITL': 'red',
        'ETYCB': 'yellow',
        'CCIS': 'green',
        'CAS': 'blue',
        'CHS': 'orange'
    }

    # Build the graph
    for index, row in df.iterrows():
        research_id = row['research_id']
        study = row['title']
        sdg_list = row['concatenated_areas'].split(';')  # Split SDGs by ';' delimiter
        college_id = row['college_id']
        program_name = row['program_name']
        concatenated_authors = row['concatenated_authors']
        year = row['date_approved'].year

        # Add study node
        G.add_node(research_id, type='study', research=research_id, title=study,college=college_id, program=program_name,
                   authors=concatenated_authors, year=year)

        # Iterate over each SDG and add edges
        for sdg in sdg_list:
            sdg = sdg.strip()  # Remove any leading/trailing spaces
            if not G.has_node(sdg):
                G.add_node(sdg, type='sdg')

            connected_nodes[sdg].append(research_id)
            G.add_edge(sdg, research_id)

    pos = nx.kamada_kawai_layout(G)
    scaling_factor = 10  # Adjust as needed for more spacing
    fixed_pos = {node: (coords[0] * scaling_factor, coords[1] * scaling_factor) for node, coords in pos.items()}


    def build_traces(nodes_to_show, edges_to_show, filtered_nodes, show_labels=True):
        node_x = []
        node_y = []
        hover_text = []
        node_labels = []
        node_color = []
        node_size = []

        # Calculate the number of studies connected to each SDG
        sdg_connections = {
            node: len([study for study in connected_nodes[node] if study in filtered_nodes])
            for node in G.nodes() if G.nodes[node]['type'] == 'sdg'
        }

        # Get min and max connection counts for scaling
        if sdg_connections:
            max_connections = max(sdg_connections.values())
            min_connections = min(sdg_connections.values())

        for node in nodes_to_show:
            x, y = fixed_pos[node]
            node_x.append(x)
            node_y.append(y)

            if G.nodes[node]['type'] == 'sdg':
                filtered_count = len([study for study in connected_nodes[node] if study in filtered_nodes])
                hover_text.append(f"{filtered_count} studies connected")
                node_color.append('#0A438F')
                size = 30 + (filtered_count - min_connections) / (max_connections - min_connections) * (150 - 30) if max_connections > min_connections else 60
                node_size.append(size * 0.75)
                node_labels.append(node)
            else:
                hover_text.append(f"Title: {G.nodes[node]['title']}<br>"
                                f"College: {G.nodes[node]['college']}<br>"
                                f"Program: {G.nodes[node]['program']}<br>"
                                f"Authors: {G.nodes[node]['authors']}<br>"
                                f"Year: {G.nodes[node]['year']}")
                node_color.append(palette_dict.get(G.nodes[node]['college'], 'grey'))
                node_size.append(20)
                node_labels.append(node if show_labels else "")

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

        # Edge trace
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        # Shadow text trace
        shadow_trace = go.Scatter(
            x=[x + 0.05 for x in node_x],  # Offset for shadow
            y=[y + 0.05 for y in node_y],
            mode='text',
            text=node_labels,
            textfont=dict(color='white', size=8),  # Shadow style
            hoverinfo='none'
        )

        # Main text trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if any(G.nodes[node]['type'] == 'sdg' for node in nodes_to_show) else 'markers',
            text=node_labels,
            hovertext=hover_text,
            marker=dict(color=node_color, size=node_size),
            textfont=dict(color='black', size=9),  # Main text style
            hoverinfo='text'
        )

        return edge_trace, shadow_trace, node_trace



    initial_nodes = list(G.nodes())
    initial_edges = list(G.edges())
    edge_trace, shadow_trace, node_trace = build_traces(initial_nodes, initial_edges, initial_nodes, show_labels=False)
    # Initialize Dash app
    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/collectionkg/')

    # Layout for Dash app including filters for year and colleges
    dash_app.layout = html.Div(
        style={
            'width': '100vw',  # Use full viewport width
            'height': '100vh',  # Use full viewport height
            'margin': '0',  # Remove margins
            'padding': '0',  # Remove padding
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center',
            'overflow': 'hidden',  # Ensure no scrollbars
        },
        children=[
            dcc.Graph(
                id='knowledge-graph',
                figure={
                    'data': [edge_trace, shadow_trace, node_trace],
                    'layout': go.Layout(
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=0),  # Remove graph margins
                        autosize=True,  # Automatically size graph to container
                        xaxis=dict(
                            showgrid=False,
                            zeroline=False,
                            range=[-3, 3],  # Fixed x-axis range
                            fixedrange=True,  # Disable zoom on x-axis
                        ),
                        yaxis=dict(
                            showgrid=False,
                            zeroline=False,
                            range=[-3, 3],  # Fixed y-axis range
                            fixedrange=True,  # Disable zoom on y-axis
                        ),
                        transition=dict(duration=500),
                    ),
                },
                style={
                    'height': '100%',  # Fully occupy parent height
                    'width': '100%',  # Fully occupy parent width
                    'padding': '0',  # Remove padding
                    'margin': '0',  # Remove margins
                    'overflow': 'hidden',  # Prevent any overflow within graph
                },
                config={
                    'displayModeBar': False,  # Hide the mode bar
                    'staticPlot': True,  # Make the plot static
                },
            )
        ],
    )


    # Callback to handle initial graph display, filters, and node click events
    @dash_app.callback(
    Output('knowledge-graph', 'figure'),
    [Input('apply-filters', 'n_clicks'),
     Input('knowledge-graph', 'clickData')],
    [State('year-slider', 'value'),
     State('college-dropdown', 'value'),
     State('knowledge-graph', 'figure')]
)
    def update_graph(n_clicks, clickData, year_range, selected_colleges, current_figure):
        show_labels = False
        ctx = dash.callback_context
        triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]

        # Apply filters regardless of the triggered input
        filtered_nodes = [
            node for node in G.nodes()
            if (G.nodes[node]['type'] == 'sdg') or
            (G.nodes[node]['type'] == 'study' and
                (year_range[0] <= G.nodes[node]['year'] <= year_range[1]) and
                (not selected_colleges or G.nodes[node]['college'] in selected_colleges))
        ]
        edges_to_show = [
            edge for edge in G.edges()
            if edge[0] in filtered_nodes and edge[1] in filtered_nodes
        ]
        nodes_to_show = list(set([node for edge in edges_to_show for node in edge]))

        # Set default title
        new_title = '<br>Research Studies Knowledge Graph (Filtered)' if n_clicks > 0 else '<br>Research Studies Knowledge Graph (Overall View)'

        # Handle SDG node click events
        if (clickData and 'points' in clickData):
            clicked_node = clickData['points'][0]['text']
            if (current_figure['layout']['title']['text'] == f"<br>Research Studies Knowledge Graph - {clicked_node}") and (triggered_input != "apply-filters"):
                # If the same SDG is clicked again, return to the filtered or overall view
                nodes_to_show = filtered_nodes
                edges_to_show = [
                    edge for edge in G.edges()
                    if edge[0] in nodes_to_show and edge[1] in nodes_to_show
                ]
                new_title = '<br>Research Studies Knowledge Graph (Filtered)' if n_clicks > 0 else '<br>Research Studies Knowledge Graph (Overall View)'
                show_labels=False
            elif (G.nodes[clicked_node]['type'] == 'sdg') and (triggered_input != "apply-filters"):
                # Zoom in on the selected SDG node and show its connected studies, respecting current filters
                nodes_to_show = [clicked_node] + [
                    node for node in connected_nodes[clicked_node]
                    if node in filtered_nodes  # Respect current filters
                ]
                edges_to_show = [
                    edge for edge in G.edges(clicked_node)
                    if edge[1] in filtered_nodes  # Respect current filters
                ]
                show_labels = True

        edge_trace, shadow_trace, node_trace = build_traces(nodes_to_show, edges_to_show, filtered_nodes, show_labels=show_labels)
        new_figure = {
            'data': [edge_trace, shadow_trace, node_trace],
            'layout': go.Layout(
                title=new_title,
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=25),
                width=1300,  # Increased width
                height=1200,  # Increased height
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False),
                transition=dict(duration=500),  
            )
        }
        return new_figure


    return dash_app