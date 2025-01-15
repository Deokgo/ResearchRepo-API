import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict
from flask import Flask, redirect, url_for
from . import db_manager
import pandas as pd
import numpy as np

def create_kg_area(flask_app):
    df = db_manager.get_all_data()
    G = nx.Graph()
    connected_nodes = defaultdict(list)
    sdg_to_areas = defaultdict(set)
    area_to_studies = defaultdict(list)

    # Define color palette
    palette_dict = {
        'CAS':'#141cff', 
        'CCIS':'#04a417', 
        'CHS':'#c2c2c2', 
        'MITL':'#bb0c0c',
        'ETYCB':'#e9e107',
        'SDG': '#FF4500',  # Orange-red for SDG nodes
        'area': '#0A438F'  # Keep existing area color
    }

    # Build the graph
    for index, row in df.iterrows():
        research_id = row['research_id']
        study = row['title']
        area_list = row['concatenated_areas'].split(';') if pd.notnull(row['concatenated_areas']) else []
        sdg_list = row['sdg'].split(';') if pd.notnull(row['sdg']) else []
        college_id = row['college_id']
        program_name = row['program_name']
        concatenated_authors = row['concatenated_authors']
        year = row['year']

        # Add study node
        G.add_node(research_id, type='study', research=research_id, title=study,
                   college=college_id, program=program_name,
                   authors=concatenated_authors, year=year)

        # Process areas and SDGs
        for area in area_list:
            area = area.strip()
            if area:  # Skip empty areas
                if not G.has_node(area):
                    G.add_node(area, type='area')
                area_to_studies[area].append(research_id)
                G.add_edge(area, research_id)

        # Process SDGs and connect them to studies directly
        for sdg in sdg_list:
            sdg = sdg.strip()
            if sdg:  # Skip empty SDGs
                if not G.has_node(sdg):
                    G.add_node(sdg, type='sdg')
                connected_nodes[sdg].append(research_id)  # Connect SDG directly to study
                G.add_edge(sdg, research_id)  # Add direct edge between SDG and study

                # Connect SDG to areas of this study
                for area in area_list:
                    area = area.strip()
                    if area:
                        sdg_to_areas[sdg].add(area)
                        G.add_edge(sdg, area)

    def create_circular_layout(nodes, radius=1):
        """Create a circular layout for SDG nodes"""
        pos = {}
        # Calculate angle between each node
        angle = 2 * np.pi / len(nodes)
        
        # Create two circles: outer circle for isolated nodes
        # and inner circle for connected nodes
        connected_nodes = set()
        for edge in G.edges():
            n1, n2 = edge
            if G.nodes[n1]['type'] == 'sdg' and G.nodes[n2]['type'] == 'sdg':
                connected_nodes.add(n1)
                connected_nodes.add(n2)
        
        isolated_nodes = [n for n in nodes if n not in connected_nodes]
        connected_nodes = [n for n in nodes if n in connected_nodes]
        
        # Position connected nodes in inner circle
        if connected_nodes:
            inner_radius = radius * 0.6
            inner_angle = 2 * np.pi / len(connected_nodes)
            for i, node in enumerate(connected_nodes):
                theta = i * inner_angle
                x = inner_radius * np.cos(theta)
                y = inner_radius * np.sin(theta)
                pos[node] = np.array([x, y])
        
        # Position isolated nodes in outer circle
        if isolated_nodes:
            outer_angle = 2 * np.pi / len(isolated_nodes)
            for i, node in enumerate(isolated_nodes):
                theta = i * outer_angle
                x = radius * np.cos(theta)
                y = radius * np.sin(theta)
                pos[node] = np.array([x, y])
        
        return pos

    # Initial layout
    def get_initial_layout():
        sdg_nodes = [node for node in G.nodes() if G.nodes[node]['type'] == 'sdg']
        if len(sdg_nodes) > 0:
            # Use circular layout for SDG overview
            pos = create_circular_layout(sdg_nodes, radius=1.5)
            # Add positions for all other nodes using spring layout
            remaining_nodes = [node for node in G.nodes() if node not in pos]
            if remaining_nodes:
                other_pos = nx.spring_layout(G.subgraph(remaining_nodes), k=4.0, iterations=100, seed=42)
                pos.update(other_pos)
            return pos
        return nx.spring_layout(G, k=4.0, iterations=100, seed=42)

    pos = get_initial_layout()
    
    # Apply scaling
    scaling_factor = 25
    fixed_pos = {node: (coords[0] * scaling_factor, coords[1] * scaling_factor) 
                for node, coords in pos.items()}

    def build_traces(nodes_to_show, edges_to_show, filtered_nodes, show_labels=True, show_studies=False):
        # Calculate connections for both SDGs and areas
        node_connections = defaultdict(int)
        
        # Get the current SDG and area context
        current_sdg = None
        current_area = None
        for node in nodes_to_show:
            if G.nodes[node]['type'] == 'sdg':
                current_sdg = node
            elif G.nodes[node]['type'] == 'area':
                current_area = node

        for node in G.nodes():
            if G.nodes[node]['type'] == 'sdg':
                if current_area:
                    # When viewing specific area, count only studies connected to both
                    sdg_studies = set(n for n in G.neighbors(node) 
                                    if G.nodes[n]['type'] == 'study')
                    area_studies = set(n for n in G.neighbors(current_area) 
                                     if G.nodes[n]['type'] == 'study')
                    node_connections[node] = len(sdg_studies.intersection(area_studies))
                else:
                    # Normal SDG view - count all connected studies
                    node_connections[node] = len([n for n in G.neighbors(node) 
                                               if G.nodes[n]['type'] == 'study'])
            elif G.nodes[node]['type'] == 'area':
                if current_sdg:
                    # When in SDG view, count only studies connected to both
                    area_studies = set(n for n in G.neighbors(node) 
                                     if G.nodes[n]['type'] == 'study')
                    sdg_studies = set(n for n in G.neighbors(current_sdg) 
                                    if G.nodes[n]['type'] == 'study')
                    node_connections[node] = len(area_studies.intersection(sdg_studies))
                else:
                    # Normal area view - count all connected studies
                    node_connections[node] = len([n for n in G.neighbors(node) 
                                               if G.nodes[n]['type'] == 'study'])

        # Filter nodes based on type and whether to show studies
        nodes_to_show = [node for node in nodes_to_show 
                        if G.nodes[node]['type'] == 'sdg' or  # Always show SDG nodes
                        (G.nodes[node]['type'] == 'area' and show_studies) or  # Show areas only when studies are shown
                        (G.nodes[node]['type'] == 'study' and show_studies)]  # Show studies only when explicitly requested

        edges_to_show = [edge for edge in edges_to_show 
                        if edge[0] in nodes_to_show and edge[1] in nodes_to_show]

        node_x, node_y = [], []
        hover_text, node_labels = [], []
        node_color, node_size = [], []
        customdata = []

        # Adjust node sizes to prevent overlap
        sdg_size_range = (60, 150)  # Reduced from (80, 200)
        area_size_range = (30, 80)  # Reduced from (40, 100)
        study_size = 15  # Reduced from 20

        # Get connection counts for scaling
        sdg_counts = [count for node, count in node_connections.items() if count > 0]
        max_connections = max(sdg_counts) if sdg_counts else 1

        for node in nodes_to_show:
            x, y = fixed_pos[node]
            node_x.append(x)
            node_y.append(y)
            node_type = G.nodes[node]['type']

            if node_type == 'sdg':
                count = node_connections[node]
                size = sdg_size_range[0] + (count / max_connections) * (sdg_size_range[1] - sdg_size_range[0])
                node_size.append(max(size, sdg_size_range[0]))
                node_color.append(palette_dict['SDG'])
                hover_text.append(f"SDG: {node}<br>{count} studies")
                node_labels.append(node)
                customdata.append({'type': 'sdg', 'id': node})
            elif node_type == 'area':
                count = node_connections[node]  # This now reflects the correct count
                size = area_size_range[0] + (count / max_connections) * (area_size_range[1] - area_size_range[0])
                node_size.append(size)
                node_color.append(palette_dict['area'])
                hover_text.append(f"Research Area: {node}<br>{count} studies")
                node_labels.append(f"{node}" if show_labels else "")
                customdata.append({'type': 'area', 'id': node})
            else:  # Study nodes
                # Get connected SDGs
                connected_sdgs = [n for n in G.neighbors(node) 
                                if G.nodes[n]['type'] == 'sdg']
                # Get connected areas
                connected_areas = [n for n in G.neighbors(node) 
                                 if G.nodes[n]['type'] == 'area']
                
                hover_text.append(f"Title: {G.nodes[node]['title']}<br>"
                                f"College: {G.nodes[node]['college']}<br>"
                                f"Program: {G.nodes[node]['program']}<br>"
                                f"Authors: {G.nodes[node]['authors']}<br>"
                                f"Year: {G.nodes[node]['year']}<br>"
                                f"SDGs: {', '.join(connected_sdgs)}<br>"
                                f"Research Areas: {', '.join(connected_areas)}")
                node_color.append(palette_dict.get(G.nodes[node]['college'], 'grey'))
                node_size.append(study_size)
                node_labels.append("")
                customdata.append({'type': 'study', 'research_id': node})

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
            line=dict(width=0.3, color='#888'),  # Thinner lines
            hoverinfo='none',
            mode='lines'
        )

        # Create node trace with consistent labels
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_labels,
            textposition="middle center",
            hovertext=hover_text,
            hoverinfo='text',
            marker=dict(
                color=node_color,
                size=node_size,
                line=dict(width=2, color='white')
            ),
            customdata=customdata,
            textfont=dict(
                size=14,
                color='black',
                family='Arial'
            )
        )

        return edge_trace, node_trace



    initial_nodes = [node for node in G.nodes() if G.nodes[node]['type'] in ['sdg', 'area', 'study']]
    initial_edges = list(G.edges())
    edge_trace, node_trace = build_traces(initial_nodes, initial_edges, initial_nodes, show_labels=False)
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
        dcc.Store(id='click-store', storage_type='memory'),
        dcc.Store(id='parent-sdg-store', storage_type='memory'),
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
                    'data': [edge_trace, node_trace],
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
        [Output('knowledge-graph', 'figure'),
         Output('click-store', 'data'),
         Output('parent-sdg-store', 'data')],
        [Input('apply-filters', 'n_clicks'),
         Input('knowledge-graph', 'clickData')],
        [State('year-slider', 'value'),
         State('college-dropdown', 'value'),
         State('knowledge-graph', 'figure'),
         State('parent-sdg-store', 'data')]
    )
    def update_graph(n_clicks, clickData, year_range, selected_colleges, current_figure, parent_sdg):
        ctx = dash.callback_context
        triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]
        show_studies = False
        show_labels = True
        new_title = '<br>Research Studies Knowledge Graph (SDG View)'

        # Initialize filtered_nodes with all SDG nodes
        filtered_nodes = [
            node for node in G.nodes()
            if G.nodes[node]['type'] == 'sdg'  # Only include SDG nodes initially
        ]
        nodes_to_show = filtered_nodes
        edges_to_show = []  # No edges in the initial view

        if clickData and 'points' in clickData and clickData['points'][0].get('customdata'):
            point_data = clickData['points'][0]['customdata']
            clicked_type = point_data.get('type')
            clicked_id = point_data.get('id')
            current_title = current_figure.get('layout', {}).get('title', {}).get('text', '')

            if clicked_type == 'sdg':
                if 'Research Studies Knowledge Graph (SDG View)' not in current_title:
                    # Return to SDG overview
                    filtered_nodes = [
                        node for node in G.nodes()
                        if G.nodes[node]['type'] == 'sdg'
                    ]
                    nodes_to_show = filtered_nodes
                    edges_to_show = []
                    new_title = '<br>Research Studies Knowledge Graph (SDG View)'
                    show_studies = False
                    show_labels = True
                else:
                    # Show areas AND their connected studies for this SDG
                    nodes_to_show = {clicked_id}  # Start with the SDG node
                    
                    # Get studies directly connected to this SDG
                    sdg_studies = set(n for n in G.neighbors(clicked_id) 
                                    if G.nodes[n]['type'] == 'study')
                    
                    # Get areas connected to these studies
                    areas_with_studies = set()
                    for study in sdg_studies:
                        for neighbor in G.neighbors(study):
                            if G.nodes[neighbor]['type'] == 'area':
                                areas_with_studies.add(neighbor)
                    
                    nodes_to_show.update(areas_with_studies)
                    nodes_to_show.update(sdg_studies)
                    
                    edges_to_show = [e for e in G.edges() 
                                   if e[0] in nodes_to_show and e[1] in nodes_to_show]
                    
                    show_studies = True
                    new_title = f'<br>Research Areas and Studies for {clicked_id}'
                    filtered_nodes = list(nodes_to_show)

                # Build the figure
                edge_trace, node_trace = build_traces(
                    nodes_to_show, 
                    edges_to_show, 
                    filtered_nodes,
                    show_labels=show_labels,
                    show_studies=show_studies
                )

                new_figure = {
                    'data': [edge_trace, node_trace],
                    'layout': go.Layout(
                        title=new_title,
                        titlefont=dict(size=16),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=25),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        transition=dict(duration=500),
                        dragmode='pan'
                    )
                }

                if 'Research Studies Knowledge Graph (SDG View)' not in current_title:
                    return new_figure, None, None  # Reset parent SDG
                else:
                    return new_figure, None, clicked_id  # Store the current SDG

            elif clicked_type == 'area':
                if "Studies for Research Area:" in current_title and parent_sdg:
                    # We're in area view, return to the parent SDG view
                    nodes_to_show = {parent_sdg}
                    sdg_studies = set(n for n in G.neighbors(parent_sdg) 
                                    if G.nodes[n]['type'] == 'study')
                    
                    areas_with_studies = set()
                    for study in sdg_studies:
                        for neighbor in G.neighbors(study):
                            if G.nodes[neighbor]['type'] == 'area':
                                areas_with_studies.add(neighbor)
                    
                    nodes_to_show.update(areas_with_studies)
                    nodes_to_show.update(sdg_studies)
                    
                    edges_to_show = [e for e in G.edges() 
                                   if e[0] in nodes_to_show and e[1] in nodes_to_show]
                    
                    show_studies = True
                    new_title = f'<br>Research Areas and Studies for {parent_sdg}'
                    filtered_nodes = list(nodes_to_show)
                
                elif parent_sdg:  # We're in SDG view, zoom into area
                    # Show only studies connected to both this area AND the parent SDG
                    sdg_studies = set(n for n in G.neighbors(parent_sdg) 
                                    if G.nodes[n]['type'] == 'study')
                    area_studies = set(n for n in G.neighbors(clicked_id) 
                                     if G.nodes[n]['type'] == 'study')
                    common_studies = sdg_studies.intersection(area_studies)
                    
                    nodes_to_show = {clicked_id, parent_sdg}  # Include both area and SDG nodes
                    nodes_to_show.update(common_studies)
                    edges_to_show = [e for e in G.edges() 
                                   if e[0] in nodes_to_show and e[1] in nodes_to_show]
                    show_studies = True
                    new_title = f'<br>Studies for Research Area: {clicked_id} (SDG: {parent_sdg})'
                    filtered_nodes = list(nodes_to_show)

                # Build the figure
                edge_trace, node_trace = build_traces(
                    nodes_to_show, 
                    edges_to_show, 
                    filtered_nodes,
                    show_labels=show_labels,
                    show_studies=show_studies
                )

                new_figure = {
                    'data': [edge_trace, node_trace],
                    'layout': go.Layout(
                        title=new_title,
                        titlefont=dict(size=16),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=25),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        transition=dict(duration=500),
                        dragmode='pan'
                    )
                }

                return new_figure, None, parent_sdg

            elif clicked_type == 'study':
                research_id = point_data.get('research_id')
                return current_figure, {
                    'type': 'study_click',
                    'research_id': str(research_id),
                    'action': 'redirect'
                }, parent_sdg

        # Default return for no click event
        edge_trace, node_trace = build_traces(
            nodes_to_show, 
            edges_to_show, 
            filtered_nodes,
            show_labels=show_labels,
            show_studies=show_studies
        )

        new_figure = {
            'data': [edge_trace, node_trace],
            'layout': go.Layout(
                title=new_title,
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=25),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                transition=dict(duration=500),
                dragmode='pan'
            )
        }

        return new_figure, None, parent_sdg

    # Add clientside callback to handle redirects
    dash_app.clientside_callback(
        """
        function(clickStoreData) {
            if (clickStoreData && clickStoreData.type === 'study_click' && clickStoreData.action === 'redirect') {
                window.parent.postMessage({
                    type: 'study_click',
                    research_id: clickStoreData.research_id
                }, '*');
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('knowledge-graph', 'id'),  # Dummy output
        Input('click-store', 'data')
    )

    return dash_app