import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict
from flask import Flask
from . import db_manager
import pandas as pd

def create_kg_sdg(flask_app):
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
    fixed_pos = {node: pos[node] for node in G.nodes()}

    # Function to create traces for the graph
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
                # Update hover text to reflect filtered connected nodes
                filtered_count = len([study for study in connected_nodes[node] if study in filtered_nodes])
                hover_text.append(f"{filtered_count} studies connected")
                node_color.append('#CA031B')

                # Scale the node size between 60 and 100 based on the number of connections
                if max_connections > min_connections:
                    size = 60 + (filtered_count - min_connections) / (max_connections - min_connections) * (100 - 60)
                else:
                    size = 60  # If all nodes have the same number of connections
                node_size.append(size * 0.75)
                node_labels.append(node)
            else:
                # Update hover text with college_id, program_name, concatenated_authors, and year
                hover_text.append(f"Title: {G.nodes[node]['title']}<br>"
                                f"College: {G.nodes[node]['college']}<br>"
                                f"Program: {G.nodes[node]['program']}<br>"
                                f"Authors: {G.nodes[node]['authors']}<br>"
                                f"Year: {G.nodes[node]['year']}")
                node_color.append(palette_dict.get(G.nodes[node]['college'], 'grey'))  # Default to grey if college is not found
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

        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if any(G.nodes[node]['type'] == 'sdg' for node in nodes_to_show) else 'markers',
            text=node_labels,
            hovertext=hover_text,
            marker=dict(
                color=node_color,
                size=node_size,
            ),
            hoverinfo='text'
        )

        return edge_trace, node_trace


    initial_nodes = list(G.nodes())
    initial_edges = list(G.edges())
    edge_trace, node_trace = build_traces(initial_nodes, initial_edges, initial_nodes, show_labels=False)
    # Initialize Dash app
    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/knowledgegraph/')

    # Layout for Dash app including filters for year and colleges
    dash_app.layout = html.Div([
        html.Div([
            html.Label('Select Year Range:'),
            dcc.RangeSlider(
                id='year-slider',
                min=df['date_approved'].dt.year.min(),  
                max=df['date_approved'].dt.year.max(), 
                value=[df['date_approved'].dt.year.min(), df['date_approved'].dt.year.max()],
                marks={year: str(year) for year in range(df['date_approved'].dt.year.min(), df['date_approved'].dt.year.max() + 1, 2)},
                step=1
            ),
            html.Label('Select Colleges:'),
            dcc.Dropdown(
                id='college-dropdown',
                options=[{'label': college, 'value': college} for college in df['college_id'].unique()],
                value=[],
                multi=True,
                placeholder='Select colleges...'
            ),
            html.Button('Apply Filters', id='apply-filters', n_clicks=0)
        ], style={'width': '20%', 'display': 'inline-block', 'padding': '20px', 'verticalAlign': 'top'}),

        html.Div([
            dcc.Graph(
                id='knowledge-graph',
                figure={
                    'data': [edge_trace, node_trace],  
                    'layout': go.Layout(
                        title='<br>Research Studies Knowledge Graph (Overall View)',
                        titlefont=dict(size=16),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=25),
                        width=1300,  # Increased width
                        height=1200,  # Increased height
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=False, zeroline=False),
                        transition=dict(duration=500),  # Add transition for animation
                    )
                }
            )
        ], style={'width': '75%', 'display': 'flex', 'justifyContent': 'center', 'flexDirection': 'column'})
    ])

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
                new_title = f'<br>Research Studies Knowledge Graph - {clicked_node}'
                show_labels = True

        edge_trace, node_trace = build_traces(nodes_to_show, edges_to_show, filtered_nodes, show_labels=show_labels)
        new_figure = {
            'data': [edge_trace, node_trace],
            'layout': go.Layout(
                title=new_title,
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=50),
                width=1300,  # Increased width
                height=1200,  # Increased height
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False),
                transition=dict(duration=500),  
            )
        }
        return new_figure


    return dash_app