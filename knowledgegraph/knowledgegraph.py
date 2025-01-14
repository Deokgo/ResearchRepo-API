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
        year = row['year']

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
        # Calculate the number of studies connected to each SDG
        sdg_connections = {
            node: len([study for study in connected_nodes[node] if study in filtered_nodes])
            for node in G.nodes() if G.nodes[node]['type'] == 'sdg'
        }

        # Remove SDG nodes with zero connections from nodes_to_show
        nodes_to_show = [node for node in nodes_to_show 
                        if G.nodes[node]['type'] != 'sdg' or sdg_connections.get(node, 0) > 0]
        
        # Update edges_to_show to remove edges connected to removed nodes
        edges_to_show = [edge for edge in edges_to_show 
                        if edge[0] in nodes_to_show and edge[1] in nodes_to_show]
        
        node_x = []
        node_y = []
        hover_text = []
        node_labels = []
        node_color = []
        node_size = []

        # Get min and max connection counts for scaling (only for nodes with connections)
        connected_sdg_counts = [count for count in sdg_connections.values() if count > 0]
        if connected_sdg_counts:
            max_connections = max(connected_sdg_counts)
            min_connections = min(connected_sdg_counts)
        else:
            max_connections = min_connections = 0

        for node in nodes_to_show:
            x, y = fixed_pos[node]
            node_x.append(x)
            node_y.append(y)

            if G.nodes[node]['type'] == 'sdg':
                filtered_count = sdg_connections[node]
                hover_text.append(f"{filtered_count} studies connected")
                node_color.append('#0A438F')
                size = 60 + (filtered_count - min_connections) / (max_connections - min_connections) * (150 - 60) if max_connections > min_connections else 60
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
            textfont=dict(color='white', size=12),  # Shadow style
            hoverinfo='none'
        )

        # Main text trace
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text' if any(G.nodes[node]['type'] == 'sdg' for node in nodes_to_show) else 'markers',
            text=node_labels,
            hovertext=hover_text,
            marker=dict(color=node_color, size=node_size),
            textfont=dict(color='black', size=12),  # Main text style
            hoverinfo='text'
        )

        return edge_trace, shadow_trace, node_trace



    initial_nodes = list(G.nodes())
    initial_edges = list(G.edges())
    edge_trace, shadow_trace, node_trace = build_traces(initial_nodes, initial_edges, initial_nodes, show_labels=False)
    # Initialize Dash app
    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/knowledgegraph/')

    # Define styles as Python dictionaries
    styles = {
        'filter_container': {
            'width': '30%',
            'padding': '25px',
            'border': "1px solid #0A438F",
            'borderRadius': '14px',
            'margin': '15px'
        },
        'graph_container': {
            'width': '100%',
        },
        'main_container': {
            'display': 'flex',
            'flexDirection': 'row',
            'width': '100%',
            'height': '100%',
            'fontFamily': 'Montserrat',
            'backgroundColor': 'white',
        },
        'slider_container': {
            'fontSize': '5px',
            'color': '#08397C',
            'marginTop': '20px',
            'marginBottom': '30px',
        },
        'dropdown_container': {
            'width': 'inherit',
            'fontSize' : '13px',
            'padding': '5px',
            'marginBottom': '20px'
        },
        'filter_button': {
            'width': '100%',
            'backgroundColor': '#08397C',
            'fontSize' : '15px',
            'color': 'white',
            'padding': '10px',
            'borderRadius': '4px',
            'border': 'none',
            'cursor': 'pointer'
        },
        'label': {
            'marginBottom': '10px',
            'fontSize' : '13px',
            'color': '#08397C',
            'fontFamily': 'Montserrat',
            'display': 'block'
        },
        'main_label': {
            'fontSize' : '20px',
            'color': '#F40824',
            'fontFamily': 'Montserrat',
            'fontWeight': 'bold',
            'marginBottom': '16px',
            'display': 'block'
        }
    }

    # Updated layout with inline styles
    dash_app.layout = html.Div([
        # Container for filters
        html.Div([
            html.Label('Filters', style=styles['main_label']),
            html.Div([
                html.Label('Select Year Range:', style=styles['label']),
                html.Div([
                    dcc.RangeSlider(
                        id='year-slider',
                        min=df['year'].min(),
                        max=df['year'].max(),
                        value=[df['year'].min(), df['year'].max()],
                        marks={year: str(year) for year in range(int(df['year'].min()), 
                                                               int(df['year'].max()) + 1, 2)},
                        step=1
                    )
                ], style=styles['slider_container']),
            ]),
            
            html.Div([
                html.Div([
                    html.Label('Select Colleges:', style=styles['label']),
                    html.Div([
                        dcc.Dropdown(
                            id='college-dropdown',
                            options=[{'label': college, 'value': college} for college in df['college_id'].unique()],
                            value=[],
                            multi=True,
                            placeholder='Select colleges...'
                        )
                    ], style=styles['dropdown_container']),
                ]),

                html.Button(
                    'Apply Filters',
                    id='apply-filters',
                    n_clicks=0,
                    style=styles['filter_button']
                )
            ])        
        ], style=styles['filter_container']),
        
        # Container for graph
        html.Div([
            dcc.Graph(
                id='knowledge-graph',
                figure={
                    'data': [edge_trace, shadow_trace, node_trace],
                    'layout': go.Layout(
                        title='<br>Research Studies Knowledge Graph (Overall View)',
                        titlefont=dict(size=16),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=25),
                        xaxis=dict(showgrid=False, zeroline=False),
                        yaxis=dict(showgrid=False, zeroline=False),
                        transition=dict(duration=500),
                    )
                },
                style={
                    'height': 'calc(100vh - 40px)',
                    'width': '100%'
                },
                config={
                    'responsive': True,
                    'scrollZoom': True,
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                }
            )
        ], style=styles['graph_container'])
    ], style=styles['main_container'])

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

        edge_trace, shadow_trace, node_trace = build_traces(nodes_to_show, edges_to_show, filtered_nodes, show_labels=show_labels)
        new_figure = {
            'data': [edge_trace, shadow_trace, node_trace],
            'layout': go.Layout(
                title=new_title,
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=25),
                xaxis=dict(showgrid=False, zeroline=False),
                yaxis=dict(showgrid=False, zeroline=False),
                transition=dict(duration=500),  
                
            )
        }
        return new_figure


    return dash_app