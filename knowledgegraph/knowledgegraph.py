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

# Enable dragging feature
dragmode = 'pan'  # Allows users to move the graph freely
from services.sdg_colors import sdg_colors

def create_kg_area(flask_app):
    df = db_manager.get_all_data()
    G = nx.Graph()
    connected_nodes = defaultdict(list)
    sdg_to_areas = defaultdict(set)
    area_to_studies = defaultdict(list)

    # Define color palette
    palette_dict = {}

    # Build the graph
    for index, row in df.iterrows():
        research_id = row['research_id']
        study = row['title']
        area_list = row['concatenated_areas'].split(';') if pd.notnull(row['concatenated_areas']) else []
        sdg_list = row['sdg'].split(';') if pd.notnull(row['sdg']) else []
        college_id = row['college_id']
        color_code = row['color_code']
        program_name = row['program_name']
        concatenated_authors = row['concatenated_authors']
        year = row['year']

        if college_id not in palette_dict:
            palette_dict[college_id] = color_code

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
        """
        Creates an initial layout using a combination of circular layout for SDG nodes
        and Kamada-Kawai layout for other nodes.
        """
        # First identify SDG nodes
        sdg_nodes = [node for node in G.nodes() if G.nodes[node]['type'] == 'sdg']
        
        if len(sdg_nodes) > 0:
            # Initialize the position dictionary
            pos = {}
            
            # Use circular layout for SDG nodes
            sdg_pos = create_circular_layout(sdg_nodes, radius=1.5)

            """
            # Use Kamada-Kawai layout for remaining nodes
            other_pos = nx.kamada_kawai_layout(
                sdg_nodes,
                dist=None,
                weight=None,
                scale=3,
                pos={node: (np.random.rand() * 2 - 1, np.random.rand() * 2 - 1) 
                    for node in sdg_nodes}  # Random initial positions
            )
            pos.update(other_pos)
            """
            pos.update(sdg_pos)

            # Get remaining nodes
            remaining_nodes = [node for node in G.nodes() if node not in pos]
            
            if remaining_nodes:
                # Create a subgraph of remaining nodes
                remaining_subgraph = G.subgraph(remaining_nodes)
                
                # Use Kamada-Kawai layout for remaining nodes
                other_pos = nx.kamada_kawai_layout(
                    remaining_subgraph,
                    dist=None,
                    weight=None,
                    scale=1.5,
                    pos={node: (np.random.rand() * 2 - 1, np.random.rand() * 2 - 1) 
                        for node in remaining_nodes}  # Random initial positions
                )
                
                # Update positions
                pos.update(other_pos)
            
            return pos
        
        # If no SDG nodes, use Kamada-Kawai layout for the entire graph
        return nx.kamada_kawai_layout(
            G,
            dist=None,
            weight=None,
            scale=2.0
         )

    pos = get_initial_layout()
    
    # Apply scaling
    scaling_factor = 25
    fixed_pos = {node: (coords[0] * scaling_factor, coords[1] * scaling_factor) 
                for node, coords in pos.items()}

    
    def build_traces(nodes_to_show, edges_to_show, filtered_nodes, show_labels=True, show_studies=False, year_range=None, selected_colleges=None):
        # Calculate connections for both SDGs and areas
        node_connections = defaultdict(int)

        # Get the current SDG and area context
        # Check filtered_nodes first for SDG context, then nodes_to_show
        current_sdg = None
        current_area = None
        for node in filtered_nodes:
            if G.nodes[node]['type'] == 'sdg':
                current_sdg = node
                break
        
        for node in nodes_to_show:
            if G.nodes[node]['type'] == 'area':
                current_area = node

        # Helper function to check if a study matches filters
        def study_matches_filters(study_node):
            matches = True
            if year_range:
                matches = matches and (year_range[0] <= G.nodes[study_node]['year'] <= year_range[1])
            if selected_colleges:
                matches = matches and (G.nodes[study_node]['college'] in selected_colleges)
            return matches
        
        for node in G.nodes():
            if G.nodes[node]['type'] == 'sdg':
                if current_area:
                    # When viewing specific area, count only studies connected to both
                    sdg_studies = set(n for n in G.neighbors(node) 
                                    if G.nodes[n]['type'] == 'study' and study_matches_filters(n))
                    area_studies = set(n for n in G.neighbors(current_area) 
                                        if G.nodes[n]['type'] == 'study' and study_matches_filters(n))
                    node_connections[node] = len(sdg_studies.intersection(area_studies))
                else:
                    # Normal SDG view - count all connected studies that match filters
                    node_connections[node] = len([n for n in G.neighbors(node) 
                                                if G.nodes[n]['type'] == 'study' and study_matches_filters(n)])
            elif G.nodes[node]['type'] == 'area':
                # Always get intersection with current SDG since we can only reach area view through an SDG
                area_studies = set(n for n in G.neighbors(node) 
                                  if G.nodes[n]['type'] == 'study' and study_matches_filters(n))
                if current_sdg:
                    sdg_studies = set(n for n in G.neighbors(current_sdg) 
                                     if G.nodes[n]['type'] == 'study' and study_matches_filters(n))
                    node_connections[node] = len(area_studies.intersection(sdg_studies))
                else:
                    # This case should never happen in practice since we always have an SDG context
                    node_connections[node] = len(area_studies)

        # Filter nodes based on type and whether to show studies
        nodes_to_show = [node for node in nodes_to_show 
                        if G.nodes[node]['type'] == 'sdg' or  
                        (G.nodes[node]['type'] == 'area' and show_studies) or  
                        (G.nodes[node]['type'] == 'study' and show_studies and study_matches_filters(node))]

        edges_to_show = [edge for edge in edges_to_show 
                        if edge[0] in nodes_to_show and edge[1] in nodes_to_show]

        # Remove direct SDG-study edges when in SDG view
        current_sdg = next((node for node in filtered_nodes if G.nodes[node]['type'] == 'sdg'), None)
        if current_sdg and show_studies:  # If we're showing studies, we're in SDG view
            edges_to_show = [edge for edge in edges_to_show 
                            if not (
                                (edge[0] == current_sdg and G.nodes[edge[1]]['type'] == 'study') or
                                (edge[1] == current_sdg and G.nodes[edge[0]]['type'] == 'study')
                            )]

        node_x, node_y = [], []
        hover_text, node_labels = [], []
        node_color, node_size = [], []
        customdata = []

        # Adjust node sizes to prevent overlap
        sdg_size_range = (60, 150)
        area_size_range = (30, 80)
        study_size = 15

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
                # Format the node name to match sdg_colors dictionary keys
                sdg_key = f"SDG {node.split(' ')[1]}"  # Convert "SDG1" to "SDG 1"
                node_color.append(sdg_colors.get(sdg_key, '#FF4500'))  # Use color from sdg_colors
                hover_text.append(f"SDG: {node}<br>{count} studies")
                node_labels.append(node)
                customdata.append({'type': 'sdg', 'id': node})
            elif node_type == 'area':
                # Find the current SDG node (should be the only SDG in filtered_nodes)
                current_sdg = next((n for n in filtered_nodes if G.nodes[n]['type'] == 'sdg'), None)
                
                # Get studies connected to both this area and the current SDG
                area_studies = set(n for n in G.neighbors(node) if G.nodes[n]['type'] == 'study')
                sdg_studies = set(n for n in G.neighbors(current_sdg) if G.nodes[n]['type'] == 'study') if current_sdg else set()
                common_studies = area_studies.intersection(sdg_studies)
                
                # Apply additional filters
                filtered_studies = set()
                for study in common_studies:
                    if year_range and not (year_range[0] <= G.nodes[study]['year'] <= year_range[1]):
                        continue
                    if selected_colleges and G.nodes[study]['college'] not in selected_colleges:
                        continue
                    filtered_studies.add(study)
                
                count = len(filtered_studies)
                size = area_size_range[0] + (count / max_connections) * (area_size_range[1] - area_size_range[0])
                node_size.append(max(size, area_size_range[0]))
                node_color.append('#0A438F')
                hover_text.append(f"Research Area: {node}<br>Studies: {count}")
                node_labels.append(node if show_labels else '')
                customdata.append({'type': 'area', 'id': node})
            else:  # Study nodes
                connected_sdgs = [n for n in G.neighbors(node) if G.nodes[n]['type'] == 'sdg']
                connected_areas = [n for n in G.neighbors(node) if G.nodes[n]['type'] == 'area']
                
                hover_text.append(
                    f"<b>Title:</b> {G.nodes[node]['title']}<br>"
                    f"<b>College:</b> {G.nodes[node]['college']}<br>"
                    f"<b>Program:</b> {G.nodes[node]['program']}<br>"
                    f"<b>Authors:</b> {G.nodes[node]['authors']}<br>"
                    f"<b>Year:</b> {G.nodes[node]['year']}<br>"
                    f"<b>SDGs:</b> {', '.join(connected_sdgs)}<br>"
                    f"<b>Research Areas:</b> {', '.join(connected_areas)}"
                )
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
            line=dict(width=0.3, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

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
            'width': '25%',
            'height': '100%',
            'padding': '20px',
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
            'cursor': 'pointer',
            'borderRadius': '100px'
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
                    html.Label('Select College/s:', style=styles['label']),
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

                # Add threshold slider
                html.Div([
                    html.Label('Research Area Connection Threshold:', style=styles['label']),
                    html.Div([
                        dcc.Slider(
                            id='threshold-slider',
                            min=1,
                            max=5,
                            value=1,  # Default value
                            marks={i: f'{i} connections' for i in range(1, 6)},
                            step=1  # Force whole number intervals
                        )
                    ], style=styles['slider_container']),
                ], id='threshold-container', style={'display': 'none'}),  # Hidden by default

                #html.Button('Reset Filter',id='reset-filters',n_clicks=0,style=styles['filter_button'])
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
                        margin=dict(b=0, l=0, r=0, t=50),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        transition=dict(duration=500),
                        dragmode=dragmode
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

    @dash_app.callback(
    [Output('knowledge-graph', 'figure'),
     Output('click-store', 'data'),
     Output('parent-sdg-store', 'data')],
    [Input('year-slider', 'value'),
     Input('college-dropdown', 'value'),
     Input('threshold-slider', 'value'),
     Input('knowledge-graph', 'clickData')],  # Add Reset Button as Input
    [State('knowledge-graph', 'figure'),
     State('parent-sdg-store', 'data')]
)
    def update_graph(year_range, selected_colleges, threshold, clickData, current_figure, parent_sdg):
        ctx = dash.callback_context
        triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]

        if triggered_input == 'reset-filters':
            year_range = [df['year'].min(), df['year'].max()]  # Reset year range
            selected_colleges = []  # Reset college selection
            threshold = 1  # Reset threshold slider
        
        show_studies = False
        show_labels = True

        # Initialize with all SDG nodes for the overview
        filtered_nodes = [node for node in G.nodes() if G.nodes[node]['type'] == 'sdg']
        nodes_to_show = filtered_nodes
        edges_to_show = []
        new_title = '<br>Research Studies Knowledge Graph (SDG View)'

        # If we're in a specific SDG view and applying filters, maintain that view
        if triggered_input == 'apply-filters':
            if "Research Areas and Studies for SDG" in current_title:
                current_sdg = parent_sdg  # Get the current SDG from store
                if current_sdg:
                    # Show filtered areas and studies for this SDG
                    nodes_to_show = {current_sdg}
                    
                    # Get all studies connected to this SDG (before filtering)
                    sdg_studies = set(n for n in G.neighbors(current_sdg) 
                                    if G.nodes[n]['type'] == 'study')
                    
                    # Apply filters to studies
                    filtered_studies = set()
                    for study in sdg_studies:
                        if year_range and not (year_range[0] <= G.nodes[study]['year'] <= year_range[1]):
                            continue
                        if selected_colleges and G.nodes[study]['college'] not in selected_colleges:
                            continue
                        filtered_studies.add(study)
                    
                    # Get all areas connected to the filtered studies
                    area_connections = defaultdict(int)
                    areas_to_show = set()
                    
                    for study in filtered_studies:
                        for neighbor in G.neighbors(study):
                            if G.nodes[neighbor]['type'] == 'area':
                                area_connections[neighbor] += 1
                    
                    # Filter areas based on threshold but keep original connection counts
                    if area_connections:
                        min_connections = min(area_connections.values())
                        threshold_count = max(int(threshold * min_connections), min_connections)
                        areas_to_show = {
                            area for area, count in area_connections.items()
                            if count >= threshold_count
                        }
                    
                    # Only show studies connected to visible areas
                    studies_to_show = {
                        study for study in filtered_studies
                        if any(area in areas_to_show 
                              for area in G.neighbors(study) 
                              if G.nodes[area]['type'] == 'area')
                    }
                    
                    nodes_to_show.update(areas_to_show)
                    nodes_to_show.update(studies_to_show)
                    
                    # Get edges but exclude direct SDG-study connections
                    edges_to_show = [e for e in G.edges() 
                                   if e[0] in nodes_to_show and e[1] in nodes_to_show and
                                   not ((e[0] == current_sdg and G.nodes[e[1]]['type'] == 'study') or
                                        (e[1] == current_sdg and G.nodes[e[0]]['type'] == 'study'))]
                    
                    filtered_nodes = list(nodes_to_show)
                    show_studies = True
                    new_title = f'<br>Research Areas and Studies for {current_sdg}'
                    
                    if selected_colleges or year_range != [df['year'].min(), df['year'].max()]:
                        filter_desc = []
                        if selected_colleges:
                            filter_desc.append(f"Colleges: {', '.join(selected_colleges)}")
                        if year_range != [df['year'].min(), df['year'].max()]:
                            filter_desc.append(f"Years: {year_range[0]}-{year_range[1]}")
                        new_title += f" ({' | '.join(filter_desc)})"

            elif "Studies for Research Area:" in current_title and parent_sdg:
                # Maintain Research Area view when applying filters
                area_name = current_title.split("Studies for Research Area:")[1].split("(SDG:")[0].strip()
                nodes_to_show = {area_name}  # Only show the area node
                
                # Get studies connected to both area and SDG
                sdg_studies = set(n for n in G.neighbors(parent_sdg) 
                                 if G.nodes[n]['type'] == 'study')
                area_studies = set(n for n in G.neighbors(area_name) 
                                 if G.nodes[n]['type'] == 'study')
                
                common_studies = sdg_studies.intersection(area_studies)
                
                # Apply filters to studies
                if year_range:
                    common_studies = {
                        study for study in common_studies
                        if year_range[0] <= G.nodes[study]['year'] <= year_range[1]
                    }
                
                if selected_colleges:
                    common_studies = {
                        study for study in common_studies
                        if G.nodes[study]['college'] in selected_colleges
                    }
                
                nodes_to_show.update(common_studies)
                filtered_nodes = list(nodes_to_show)
                filtered_nodes.append(parent_sdg)  # Add SDG to filtered_nodes for context
                
                edges_to_show = [e for e in G.edges() 
                               if e[0] in nodes_to_show and e[1] in nodes_to_show]
                show_studies = True
                new_title = f'<br>Studies for Research Area: {area_name} (SDG: {parent_sdg})'

        # Handle click events
        elif triggered_input == 'knowledge-graph' and clickData:
            point_data = clickData['points'][0]['customdata']
            clicked_type = point_data.get('type')
            clicked_id = point_data.get('id')
            current_title = current_figure.get('layout', {}).get('title', {}).get('text', '')

            if clicked_type == 'sdg':
                if 'Research Studies Knowledge Graph (SDG View)' not in current_title:
                    # Return to SDG overview with applied filters
                    if selected_colleges or year_range != [df['year'].min(), df['year'].max()]:
                        # Apply filters to get relevant SDGs
                        if year_range:
                            year_filtered_studies = {
                                node for node in G.nodes()
                                if G.nodes[node]['type'] == 'study' and
                                year_range[0] <= G.nodes[node]['year'] <= year_range[1]
                            }
                        
                        if selected_colleges:
                            filtered_studies = {
                                node for node in year_filtered_studies
                                if G.nodes[node]['college'] in selected_colleges
                            }
                        else:
                            filtered_studies = year_filtered_studies
                        
                        filtered_sdgs = {
                            node for node in G.nodes()
                            if G.nodes[node]['type'] == 'sdg' and
                            any(neighbor in filtered_studies for neighbor in G.neighbors(node))
                        }
                        nodes_to_show = filtered_sdgs
                    else:
                        nodes_to_show = {node for node in G.nodes() if G.nodes[node]['type'] == 'sdg'}
                    
                    edges_to_show = []
                    new_title = '<br>Research Studies Knowledge Graph (SDG View)'
                    if selected_colleges or year_range != [df['year'].min(), df['year'].max()]:
                        filter_desc = []
                        if selected_colleges:
                            filter_desc.append(f"Colleges: {', '.join(selected_colleges)}")
                        if year_range != [df['year'].min(), df['year'].max()]:
                            filter_desc.append(f"Years: {year_range[0]}-{year_range[1]}")
                        new_title += f" ({' | '.join(filter_desc)})"
                    
                    show_studies = False
                    show_labels = True
                else:
                    # Show filtered areas and studies for this SDG
                    nodes_to_show = {clicked_id}
                    
                    # Get filtered studies directly connected to this SDG
                    sdg_studies = set(n for n in G.neighbors(clicked_id) 
                                    if G.nodes[n]['type'] == 'study')
                    
                    if year_range:
                        sdg_studies = {
                            study for study in sdg_studies
                            if year_range[0] <= G.nodes[study]['year'] <= year_range[1]
                        }
                    
                    if selected_colleges:
                        sdg_studies = {
                            study for study in sdg_studies
                            if G.nodes[study]['college'] in selected_colleges
                        }
                    
                    # Get areas connected to filtered studies with connection counts
                    area_connections = defaultdict(int)
                    
                    for study in sdg_studies:
                        for neighbor in G.neighbors(study):
                            if G.nodes[neighbor]['type'] == 'area':
                                area_connections[neighbor] += 1

                    # Calculate default threshold for initial view
                    if area_connections:
                        connection_counts = list(area_connections.values())
                        min_conn = min(connection_counts)
                        max_conn = min(max(connection_counts), 10)
                        default_threshold = min_conn + (max_conn - min_conn) // 2
                    else:
                        default_threshold = 1

                    # Apply threshold immediately
                    areas_with_studies = {
                        area for area, count in area_connections.items()
                        if count >= default_threshold
                    }
                    
                    nodes_to_show.update(areas_with_studies)
                    
                    # Only show studies connected to visible areas
                    filtered_studies = {
                        study for study in sdg_studies
                        if any(area in areas_with_studies 
                              for area in G.neighbors(study) 
                              if G.nodes[area]['type'] == 'area')
                    }
                    
                    nodes_to_show.update(filtered_studies)
                    
                    edges_to_show = [e for e in G.edges() 
                                   if e[0] in nodes_to_show and e[1] in nodes_to_show]
                    
                    show_studies = True
                    new_title = f'<br>Research Areas and Studies for {clicked_id}'

                filtered_nodes = list(nodes_to_show)

                # Update all build_traces calls to include the new parameters:
                edge_trace, node_trace = build_traces(
                    nodes_to_show, 
                    edges_to_show, 
                    filtered_nodes,
                    show_labels=show_labels,
                    show_studies=show_studies,
                    year_range=year_range,
                    selected_colleges=selected_colleges
                )

                new_figure = {
                    'data': [edge_trace, node_trace],
                    'layout': go.Layout(
                        title=new_title,
                        titlefont=dict(size=16),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=50),
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
                    
                    if year_range:
                        sdg_studies = {
                            study for study in sdg_studies
                            if year_range[0] <= G.nodes[study]['year'] <= year_range[1]
                        }
                        
                    if selected_colleges:
                        sdg_studies = {
                            study for study in sdg_studies
                            if G.nodes[study]['college'] in selected_colleges
                        }

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
                    # Store parent_sdg for context
                    context_sdg = parent_sdg
                    nodes_to_show = {clicked_id}  # Only show the area node
                    
                    # Get studies connected to both area and SDG
                    sdg_studies = set(n for n in G.neighbors(context_sdg) 
                                    if G.nodes[n]['type'] == 'study')
                    area_studies = set(n for n in G.neighbors(clicked_id) 
                                     if G.nodes[n]['type'] == 'study')
                    
                    common_studies = sdg_studies.intersection(area_studies)
                    
                    if year_range:
                        common_studies = {
                            study for study in common_studies
                            if year_range[0] <= G.nodes[study]['year'] <= year_range[1]
                        }
                    
                    if selected_colleges:
                        common_studies = {
                            study for study in common_studies
                            if G.nodes[study]['college'] in selected_colleges
                        }
                    
                    nodes_to_show.update(common_studies)  # Add studies to display
                    filtered_nodes = list(nodes_to_show)
                    filtered_nodes.append(context_sdg)  # Add SDG to filtered_nodes for context
                    
                    edges_to_show = [e for e in G.edges() 
                                   if e[0] in nodes_to_show and e[1] in nodes_to_show]
                    show_studies = True
                    new_title = f'<br>Studies for Research Area: {clicked_id} (SDG: {parent_sdg})'

                # Update all build_traces calls to include the new parameters:
                edge_trace, node_trace = build_traces(
                    nodes_to_show, 
                    edges_to_show, 
                    filtered_nodes,
                    show_labels=show_labels,
                    show_studies=show_studies,
                    year_range=year_range,
                    selected_colleges=selected_colleges
                )

                new_figure = {
                    'data': [edge_trace, node_trace],
                    'layout': go.Layout(
                        title=new_title,
                        titlefont=dict(size=16),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=50),
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

        # Build traces and return figure
        edge_trace, node_trace = build_traces(
            nodes_to_show, 
            edges_to_show, 
            filtered_nodes,
            show_labels=show_labels,
            show_studies=show_studies,
            year_range=year_range,
            selected_colleges=selected_colleges
        )

        return {
            'data': [edge_trace, node_trace],
            'layout': go.Layout(
                title=new_title,
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=50),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                transition=dict(duration=500),
                dragmode='pan'
            )
        }, None, parent_sdg

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

    @dash_app.callback(
        Output('threshold-container', 'style'),
        [Input('knowledge-graph', 'figure')]
    )
    def toggle_threshold_visibility(figure):
        # Show threshold slider only when in SDG view
        if figure and 'title' in figure['layout']:
            title = figure['layout']['title']['text']
            if "Research Areas and Studies for SDG" in title:
                return {'display': 'block'}
        return {'display': 'none'}

    # Update the callback that updates the threshold slider properties
    @dash_app.callback(
        [Output('threshold-slider', 'min'),
         Output('threshold-slider', 'max'),
         Output('threshold-slider', 'value'),
         Output('threshold-slider', 'marks')],
        [Input('knowledge-graph', 'clickData'),
         Input('knowledge-graph', 'figure'),
         Input('apply-filters', 'n_clicks')],
        [State('year-slider', 'value'),
         State('college-dropdown', 'value'),
         State('threshold-slider', 'value')]
    )
    def update_threshold_range(clickData, figure, n_clicks, year_range, selected_colleges, current_threshold):
        if not clickData:
            return 1, 5, 1, {i: f"{i} connections" for i in range(1, 6)}
        
        ctx = dash.callback_context
        triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]
        current_title = figure.get('layout', {}).get('title', {}).get('text', '')
        
        # Always maintain current threshold when applying filters
        if triggered_input == 'apply-filters':
            return dash.no_update, dash.no_update, current_threshold, dash.no_update
        
        # If this update wasn't triggered by a new click or new view, maintain current threshold
        if triggered_input != 'knowledge-graph':
            if current_threshold is not None:
                return dash.no_update, dash.no_update, current_threshold, dash.no_update
            return dash.no_update, dash.no_update, 1, dash.no_update
        
        clicked_node = clickData['points'][0]['customdata']['id']
        
        # Return default values if not in SDG view
        if G.nodes[clicked_node]['type'] != 'sdg':
            return 1, 5, 1, {i: f"{i} connections" for i in range(1, 6)}

        # Get studies for this SDG
        sdg_studies = set(n for n in G.neighbors(clicked_node) 
                         if G.nodes[n]['type'] == 'study')
        
        # Apply filters
        if year_range:
            sdg_studies = {
                study for study in sdg_studies
                if year_range[0] <= G.nodes[study]['year'] <= year_range[1]
            }
        
        if selected_colleges:
            sdg_studies = {
                study for study in sdg_studies
                if G.nodes[study]['college'] in selected_colleges
            }

        # Count area connections
        area_connections = defaultdict(int)
        for study in sdg_studies:
            for neighbor in G.neighbors(study):
                if G.nodes[neighbor]['type'] == 'area':
                    area_connections[neighbor] += 1

        if not area_connections:
            return 1, 5, 1, {i: f"{i} connections" for i in range(1, 6)}

        connection_counts = list(area_connections.values())
        min_conn = 1  # Always start at 1
        max_conn = min(max(connection_counts), 10)  # Cap at 10 for usability
        
        # Check if we're entering a new SDG view
        is_new_sdg_view = (
            triggered_input == 'knowledge-graph' and 
            "Research Areas and Studies for SDG" in current_title and
            not any(prev_title.strip().startswith("Research Areas and Studies for SDG") 
                   for prev_title in current_title.split('\n') if prev_title.strip())
        )
        
        if is_new_sdg_view:
            # Set default value to middle of range
            default_value = min_conn + (max_conn - min_conn) // 2
        else:
            # Maintain user's selected threshold
            default_value = current_threshold if current_threshold is not None else min_conn
        
        # Create marks with whole number intervals
        marks = {i: f"{i} connections" for i in range(min_conn, max_conn + 1)}
        
        return min_conn, max_conn, default_value, marks

    # Add a new callback to handle threshold changes
    @dash_app.callback(
        Output('threshold-slider', 'value', allow_duplicate=True),
        [Input('threshold-slider', 'value')],
        prevent_initial_call=True
    )
    def maintain_threshold_value(value):
        """Maintain the user's selected threshold value"""
        return value

    return dash_app