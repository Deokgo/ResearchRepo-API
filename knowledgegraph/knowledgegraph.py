import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State, ALL, MATCH
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict
from flask import Flask, redirect, url_for
import pandas as pd
import numpy as np
from database.knowledgegraph_queries import get_filtered_kgdata, get_filtered_sdg_counts, get_filtered_research_area_counts
from sqlalchemy import text
from sqlalchemy.orm import Session
from models import db  # Import db from models
from . import db_manager
from services.sdg_colors import sdg_colors
import json
from dash import clientside_callback

# Enable dragging featureF
dragmode = 'pan'  # Allows users to move the graph freely

# Global position variable
pos = {}

def create_kg_area(flask_app):
    # Get min and max years from the database manager
    sdg_counts_df = get_filtered_sdg_counts()
    min_year = db_manager.get_min_value('year')
    max_year = db_manager.get_max_value('year')

    # Get list of colleges from database manager
    colleges = db_manager.get_unique_values('college_id')


    def create_circular_layout(G, sdg_counts_df):
        """Create a circular layout for SDG nodes with radius based on study count"""
        pos = {}
        sdg_nodes = [node for node in G.nodes() if G.nodes[node]['type'] == 'sdg']
        
        if not sdg_nodes:
            return pos
        
        # Sort SDGs by study count in descending order
        sdg_counts_df = sdg_counts_df.sort_values('study_count', ascending=False)
        
        # Calculate angle between each node
        angle = 2 * np.pi / len(sdg_nodes)
        start_angle = 0  # Start from right (0 radians)
        
        # Get max study count for scaling
        max_count = max(sdg_counts_df['study_count']) if not sdg_counts_df.empty else 1
        min_radius = 1
        max_radius = 2
        
        # Assign positions based on sorted order (highest count gets rightmost position)
        for i, (_, row) in enumerate(sdg_counts_df.iterrows()):
            sdg = row['sdg']
            if sdg in G.nodes():
                count = row['study_count']
                # Calculate radius based on count
                radius = min_radius + (count / max_count) * (max_radius - min_radius)
                
                # Calculate angle - start from right (0) and move counterclockwise
                theta = start_angle + (i * angle)
                
                # Calculate coordinates
                x = radius * np.cos(theta)
                y = radius * np.sin(theta)
                pos[sdg] = np.array([x, y])
                
                # Store study count in node attributes for hover text
                G.nodes[sdg]['study_count'] = count
        
        return pos

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
            sdg_pos = create_circular_layout(G, sdg_counts_df)

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
                    pos={node: (np.random.rand() * 2 - 1, np.random.rand() * 2 - 1) 
                        for node in remaining_nodes}  # Random initial positions
                )
                
                # Update positions
                pos.update(other_pos)
            
            return pos

    def build_traces(G, edges, pos=None, show_labels=True):
        """Build traces for the graph visualization"""
        if pos is None:
            pos = nx.spring_layout(G)

        # Define min and max node sizes
        MIN_SIZE = 76
        MAX_SIZE = 130

        # Create edge trace
        edge_x = []
        edge_y = []
        for edge in edges:
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines'
        )

        # Create separate traces for SDG nodes and area nodes
        sdg_x, sdg_y = [], []
        sdg_hover_text = []
        sdg_images = []
        sdg_sizes = []
        sdg_data = []

        area_x, area_y = [], []
        area_text = []
        area_hover_text = []
        area_color = []
        area_size = []
        area_data = []

        # Get max study count for relative sizing
        max_study_count = max([G.nodes[node].get('study_count', 0) for node in G.nodes()], default=1)

        for node in G.nodes():
            x, y = pos[node]
            node_type = G.nodes[node].get('type', '')
            study_count = G.nodes[node].get('study_count', 0)

            if node_type == 'sdg':
                sdg_x.append(x)
                sdg_y.append(y)
                
                # Only show study count in overall view
                if len(G.edges()) == 0:  # In overall view (no edges)
                    hover_text = f"{node}<br>Research Count: {study_count}"
                else:  # In detail view
                    hover_text = f"{node}"
                sdg_hover_text.append(hover_text)
                
                # Calculate size based on study count
                if max_study_count > 0:
                    relative_size = MIN_SIZE + ((study_count / max_study_count) * (MAX_SIZE - MIN_SIZE))
                else:
                    relative_size = MIN_SIZE
                size = G.nodes[node].get('node_size', relative_size)
                sdg_sizes.append(size)
                
                sdg_data.append({
                    'id': node,
                    'type': node_type,
                    'study_count': study_count
                })

                # Add SDG image
                sdg_number = node.split()[-1].zfill(2)
                sdg_images.append(dict(
                    source=f"/static/assets/sdg_icons/E-WEB-Goal-{sdg_number}.png",
                    x=x,
                    y=y,
                    xref="x",
                    yref="y",
                    sizex=size/8,
                    sizey=size/8,
                    xanchor="center",
                    yanchor="middle",
                    layer="above",
                    sizing="contain"
                ))

            elif node_type == 'area':
                area_x.append(x)
                area_y.append(y)
                area_text.append(node)
                area_hover_text.append(f"{node}<br>Research Count: {study_count}")
                area_color.append('#9F7AEA')
                size = G.nodes[node].get('node_size', MIN_SIZE)
                area_size.append(size)
                area_data.append({
                    'id': node,
                    'type': node_type,
                    'study_count': study_count
                })

        # Create SDG nodes trace (using images directly)
        sdg_trace = go.Scatter(
            x=sdg_x,
            y=sdg_y,
            mode='markers',
            hoverinfo='text',
            hovertext=sdg_hover_text,
            marker=dict(
                size=[s*7 for s in sdg_sizes],  # Increased multiplier to match image size
                symbol='square',
                opacity=0.5,  # Make markers completely invisible
                sizemode='area'
            ),
            customdata=sdg_data,
            hoverlabel=dict(
                bgcolor='white',
                font_size=14,
                font_family='Arial'
            ),
            hovertemplate='%{hovertext}<extra></extra>'
        )

        # Create area nodes trace
        area_trace = go.Scatter(
            x=area_x,
            y=area_y,
            mode='markers+text' if show_labels else 'markers',
            text=area_text,
            textposition="middle center",
            hovertext=area_hover_text,
            marker=dict(
                color=area_color,
                size=area_size,
                line_width=2,
                line=dict(color='white'),
                opacity=1.0,
                symbol='circle',
                sizemode='diameter'
            ),
            customdata=area_data,
            hoverlabel=dict(
                bgcolor='white',
                font_size=14,
                font_family='Arial'
            ),
            hovertemplate='%{hovertext}<extra></extra>'
        )

        traces = []
        if edges:
            traces.append(edge_trace)
        if area_x:
            traces.append(area_trace)
        if sdg_x:
            traces.append(sdg_trace)

        return traces, sdg_images

    # Initial graph build with only SDG counts
    sdg_counts_df = get_filtered_sdg_counts()
    G = nx.Graph()
    
    # Add SDG nodes with their counts
    for _, row in sdg_counts_df.iterrows():
        G.add_node(row['sdg'], 
                  type='sdg',  # Make sure type is set
                  study_count=row['study_count'])

    # Create initial circular layout
    pos = create_circular_layout(G, sdg_counts_df)
    pos = {node: (coords[0] * 25, coords[1] * 25) 
           for node, coords in pos.items()}

    # Build initial traces
    edge_trace, sdg_images = build_traces(G, [], pos=pos, show_labels=True)

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
            'fontSize': '13px',
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
            'fontSize': '13px',
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
        },
        'side_panel': {
            'position': 'fixed',
            'top': '0',
            'right': '0',
            'width': '400px',
            'height': '100vh',
            'backgroundColor': 'white',
            'boxShadow': '-2px 0px 10px rgba(0, 0, 0, 0.1)',
            'padding': '20px',
            'overflowY': 'auto',
            'zIndex': '1000',
            'transition': 'transform 0.3s ease-in-out',
            'fontFamily': 'Montserrat'
        },
        'study_item': {
            'padding': '15px',
            'marginBottom': '10px',
            'border': '1px solid #ddd',
            'borderRadius': '5px',
            'backgroundColor': '#f9f9f9'
        },
        'study_title': {
            'fontSize': '16px',
            'fontWeight': 'bold',
            'color': '#08397C',
            'marginBottom': '8px'
        },
        'study_authors': {
            'fontSize': '14px',
            'color': '#666',
            'marginBottom': '5px'
        },
        'study_year': {
            'fontSize': '14px',
            'color': '#666'
        },
        'close_button': {
            'position': 'absolute',
            'right': '20px',
            'top': '20px',
            'cursor': 'pointer',
            'fontSize': '24px',
            'color': '#08397C'
        },
        'help_tooltip': {
            'position': 'absolute',
            'top': '10px',
            'right': '10px',
            'backgroundColor': '#08397C',
            'color': 'white',
            'borderRadius': '50%',
            'width': '24px',
            'height': '24px',
            'textAlign': 'center',
            'lineHeight': '24px',
            'cursor': 'help',
            'zIndex': '1000',
            'fontSize': '14px',
            'fontWeight': 'bold'
        },
        'tooltip_text': {
            'visibility': 'hidden',
            'backgroundColor': 'white',
            'color': '#08397C',
            'textAlign': 'left',
            'padding': '10px',
            'borderRadius': '6px',
            'position': 'absolute',
            'zIndex': '1001',
            'width': '250px',
            'right': '30px',
            'top': '0px',
            'border': '1px solid #08397C',
            'boxShadow': '0 2px 4px rgba(0,0,0,0.2)',
            'fontSize': '12px',
            'fontFamily': 'Montserrat'
        },
        'instructions_container': {
            'backgroundColor': 'white',
            'color': '#08397C',
            'padding': '15px',
            'borderRadius': '6px',
            'border': '1px solid #08397C',
            'marginTop': '20px',  # Add space between filters and instructions
            'fontSize': '12px',
            'fontFamily': 'Montserrat'
        },
        'instructions_title': {
            'fontWeight': 'bold',
            'marginBottom': '8px',
            'fontSize': '14px',
            'color': '#F40824'
        },
        'instructions_list': {
            'paddingLeft': '20px',
            'margin': '0'
        },
        'instructions_sublist': {
            'paddingLeft': '20px',
            'marginTop': '4px'
        }
    }

    # Updated layout with inline styles
    dash_app.layout = html.Div([
        dcc.Store(id='click-store', storage_type='memory'),
        dcc.Store(id='parent-sdg-store', storage_type='memory'),
        dcc.Store(id='side-panel-store', storage_type='memory'),
        dcc.Store(id='panel-visibility', data={'visible': True}),
        dcc.Store(id='threshold-store', storage_type='memory'),
        
        # Add interval component at the top
        dcc.Interval(
            id='refresh-interval',
            interval=5000,  # 5 second in milliseconds
            n_intervals=0
        ),
        
        html.Div([
            html.Label('Filters', style=styles['main_label']),
            
            # Year Range Filter
            html.Div([
                html.Label('Select Year Range:', style=styles['label']),
                html.Div([
                    dcc.RangeSlider(
                        id='year-slider',
                        min=min_year,
                        max=max_year,
                        value=[min_year, max_year],
                        marks={year: str(year) for year in range(min_year, max_year + 1, 2)},
                        step=1
                    )
                ], style=styles['slider_container']),
            ]),
            
            # College Dropdown
            html.Div([
                html.Label('Select College/s:', style=styles['label']),
                html.Div([
                    dcc.Dropdown(
                        id='college-dropdown',
                        options=[{'label': college, 'value': college} 
                                for college in colleges],
                        value=[],
                        multi=True,
                        placeholder='Select colleges...'
                    )
                ], style=styles['dropdown_container']),
            ]),
            
            # Threshold Slider
            html.Div([
                html.Label('Research Area Minimum Studies:', style=styles['label']),
                dcc.Slider(
                    id='threshold-slider',
                    min=1,
                    marks=None,
                    step=1
                ),
            ], id='threshold-container', style={'display': 'none'}),

            # Instructions below filters
            html.Div([
                html.P('💡 How to use the Knowledge Graph:', style=styles['instructions_title']),
                html.Ul([
                    html.Li('Click on any SDG icon to view its research areas'),
                    html.Li('In SDG detail view:'),
                    html.Ul([
                        html.Li('Pan by dragging the graph'),
                        html.Li('Zoom using mouse wheel or pinch gesture'),
                        html.Li('Click research areas to view related studies'),
                        html.Li('Click the same SDG again to return to overview')
                    ], style=styles['instructions_sublist'])
                ], style=styles['instructions_list'])
            ], style=styles['instructions_container']),
            
        ], style=styles['filter_container']),
        
        # Container for graph with updated config
        html.Div([
            dcc.Graph(
                id='knowledge-graph',
                figure={
                    'data': edge_trace,
                    'layout': go.Layout(
                        title=dict(text='<br>Research Studies Knowledge Graph', font=dict(size=16)),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=50),
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        dragmode='pan',
                        clickmode='event'
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
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                    'displaylogo': False
                }
            )
        ], style=styles['graph_container']),
        
        # Side Panel for Studies
        html.Div(id='side-panel', style={'display': 'none'}),
        
    ], style=styles['main_container'])

    # Add a simple callback to test clicks
    @dash_app.callback(
        Output('click-store', 'data'),
        [Input('knowledge-graph', 'clickData')]
    )
    def print_click_data(clickData):
        if clickData:
            print("Click detected!")
            print(f"Click data: {clickData}")
        return clickData

    # Update the click handler callback
    @dash_app.callback(
    Output('parent-sdg-store', 'data'),
    [Input('knowledge-graph', 'clickData')],
    [State('parent-sdg-store', 'data')]
)
    def handle_click(clickData, current_sdg):
        if clickData:
            try:
                point_data = clickData['points'][0]['customdata']
                print(f"Click detected on: {point_data}")

                if point_data['type'] == 'sdg':
                    if current_sdg == point_data['id']:
                        print("Same SDG clicked - returning to overall view")
                        return None
                    print(f"New SDG clicked - switching to {point_data['id']}")
                    return point_data['id']
                
                elif point_data['type'] == 'area':
                    print("Research Area clicked - **Maintaining threshold and SDG view**")
                    return dash.no_update  # Prevent SDG from resetting

            except Exception as e:
                print(f"Error in handle_click: {e}")
                import traceback
                print(traceback.format_exc())

        return dash.no_update




    # Main graph update callback
    @dash_app.callback(
        Output('knowledge-graph', 'figure'),
        [Input('year-slider', 'value'),
         Input('college-dropdown', 'value'),
         Input('threshold-slider', 'value'),
         Input('parent-sdg-store', 'data'),
         Input('refresh-interval', 'n_intervals')]
    )
    def update_graph_on_filter(year_range, selected_colleges, threshold, parent_sdg, n_intervals):
        try:
            if not selected_colleges:
                selected_colleges = colleges
            if not year_range:
                year_range = [min_year, max_year]
            if not threshold:
                threshold = 1

            print(f"Updating graph with parent_sdg: {parent_sdg}")

            # Always get fresh data for overall view when parent_sdg is None
            if parent_sdg is None:
                print("Creating overall SDG view")
                sdg_counts_df = get_filtered_sdg_counts(
                    start_year=year_range[0],
                    end_year=year_range[1],
                    selected_colleges=selected_colleges
                )
                
                # Create new graph with current data
                G = nx.Graph()
                
                # Add SDG nodes with their counts
                for _, row in sdg_counts_df.iterrows():
                    G.add_node(row['sdg'], 
                             type='sdg',
                             study_count=row['study_count'])

                # Create new layout based on current counts
                pos = create_circular_layout(G, sdg_counts_df)
                
                # Scale positions - reduced scaling factor for consistency
                pos = {node: (coords[0] * 25, coords[1] * 25) 
                      for node, coords in pos.items()}

                # Build traces with updated positions
                traces, sdg_images = build_traces(G, [], pos=pos, show_labels=True)
                
                title = '<br>Overall SDG View'

                # Create figure for overall view with fixed camera and disabled zoom
                fig = {
                    'data': traces,
                    'layout': go.Layout(
                        title=dict(text=title, font=dict(size=16)),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=50),
                        xaxis=dict(
                            showgrid=False, 
                            zeroline=False, 
                            showticklabels=False,
                            fixedrange=True,  # Disable x-axis zoom
                        ),
                        yaxis=dict(
                            showgrid=False, 
                            zeroline=False, 
                            showticklabels=False,
                            fixedrange=True,  # Disable y-axis zoom
                        ),
                        dragmode='pan',
                        clickmode='event',
                        uirevision=None,  # Reset the view when switching back
                        images=sdg_images,
                        transition={
                            'duration': 1000,
                            'easing': 'cubic-in-out'
                        }
                    )
                }
                return fig
            else:
                # SDG specific view code
                research_areas_df = get_filtered_research_area_counts(
                    selected_sdg=parent_sdg,
                    start_year=year_range[0],
                    end_year=year_range[1],
                    selected_colleges=selected_colleges
                )
                
                # Create new graph for SDG-specific view
                G = nx.Graph()
                
                # Define sizes for SDG detail view
                MIN_AREA_SIZE = 30
                MAX_AREA_SIZE = 60
                SDG_NODE_SIZE = 80
                MINIMUM_DISTANCE = 2
                
                # Add central SDG node with fixed size
                G.add_node(parent_sdg, type='sdg', node_size=SDG_NODE_SIZE)
                
                # Update the research area sizing logic
                if not research_areas_df.empty:
                    research_areas_df = research_areas_df.sort_values('study_count', ascending=False)
                    
                    # Use logarithmic scaling for node sizes to reduce the size disparity
                    max_study_count = research_areas_df['study_count'].max()
                    for _, row in enumerate(research_areas_df.itertuples()):
                        area_name = str(row.research_area_name)
                        study_count = int(row.study_count)
                        
                        if study_count >= threshold:
                            # Use log scaling to compress the size range
                            relative_size = MIN_AREA_SIZE + (
                                (np.log2(study_count + 1) / np.log2(max_study_count + 1)) 
                                * (MAX_AREA_SIZE - MIN_AREA_SIZE)
                            )
                            G.add_node(area_name, type='area', study_count=study_count, node_size=relative_size)
                            G.add_edge(parent_sdg, area_name)

                # Position nodes
                if len(G.nodes()) > 1:  # If we have research areas
                    # First position the SDG node at the center
                    pos = {parent_sdg: np.array([0, 0])}
                    
                    # Get all research area nodes
                    area_nodes = [node for node in G.nodes() if G.nodes[node]['type'] == 'area']
                    
                    if len(area_nodes) == 1:
                        # For single research area, place it to the right of the SDG node
                        area_node = area_nodes[0]
                        pos[area_node] = np.array([MINIMUM_DISTANCE, 0])
                    else:
                        # For multiple areas, use Kamada-Kawai layout
                        area_subgraph = G.subgraph(area_nodes)
                        area_pos = nx.kamada_kawai_layout(area_subgraph)
                        
                        # Ensure minimum distance from center
                        for node, coords in area_pos.items():
                            distance = np.linalg.norm(coords)
                            if distance < MINIMUM_DISTANCE:
                                # Scale up the position to meet minimum distance
                                scale_factor = MINIMUM_DISTANCE / distance
                                area_pos[node] = coords * scale_factor
                        
                        pos.update(area_pos)
                else:
                    pos = {parent_sdg: np.array([0, 0])}

                # Update the layout scaling
                pos = {node: (coords[0] * 10, coords[1] * 10)  # Reduced from 15 
                      for node, coords in pos.items()}

                # Build traces with updated positions
                traces, sdg_images = build_traces(G, G.edges(), pos=pos, show_labels=True)
                
                title = '<br>SDG Details View'

                # Create figure for SDG detail view with zoom enabled
                fig = {
                    'data': traces,
                    'layout': go.Layout(
                        title=dict(text=title, font=dict(size=16)),
                        showlegend=False,
                        hovermode='closest',
                        margin=dict(b=0, l=0, r=0, t=50),
                        xaxis=dict(
                            showgrid=False, 
                            zeroline=False, 
                            showticklabels=False,
                            fixedrange=False  # Enable x-axis zoom
                        ),
                        yaxis=dict(
                            showgrid=False, 
                            zeroline=False, 
                            showticklabels=False,
                            fixedrange=False  # Enable y-axis zoom
                        ),
                        dragmode='pan',
                        clickmode='event',
                        uirevision='constant',
                        images=sdg_images,
                        transition={
                            'duration': 1000,
                            'easing': 'cubic-in-out'
                        }
                    )
                }
                return fig

        except Exception as e:
            print(f"Error updating graph on filter: {e}")
            import traceback
            print(traceback.format_exc())
            return dash.no_update

    # Add callback to control threshold slider visibility
    @dash_app.callback(
        Output('threshold-container', 'style'),
        [Input('parent-sdg-store', 'data')]
    )
    def toggle_threshold_visibility(parent_sdg):
        if parent_sdg:  # If we're in a specific SDG view
            return {'display': 'block'}
        return {'display': 'none'}  # Hide in overall view

    # Modify the close button callback
    @dash_app.callback(
        [Output('side-panel', 'style'),
         Output('panel-visibility', 'data')],
        [Input('close-panel', 'n_clicks')],
        [State('panel-visibility', 'data')]
    )
    def handle_close_button(n_clicks, current_visibility):
        if n_clicks:
            print("Close button clicked!")
            return {'display': 'none'}, {'visible': False}
        raise dash.exceptions.PreventUpdate

    # Update the side panel callback
    @dash_app.callback(
        [Output('side-panel', 'children'),
         Output('side-panel', 'style', allow_duplicate=True)],
        [Input('knowledge-graph', 'clickData')],
        [State('parent-sdg-store', 'data'),
         State('year-slider', 'value'),
         State('college-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_side_panel(clickData, parent_sdg, year_range, selected_colleges):
        print("\n=== Side Panel Update ===")
        
        try:
            if not clickData:
                return None, {'display': 'none'}

            point_data = clickData['points'][0]['customdata']
            clicked_type = point_data.get('type')
            clicked_id = point_data.get('id')

            print(f"Clicked type: {clicked_type}, id: {clicked_id}")

            if clicked_type == 'area':
                df = get_filtered_kgdata(
                    selected_area=clicked_id,
                    selected_sdg=parent_sdg,
                    start_year=int(year_range[0]) if year_range else None,
                    end_year=int(year_range[1]) if year_range else None,
                    selected_colleges=selected_colleges if selected_colleges else None
                )
                
                if df is None or df.empty:
                    return None, {'display': 'none'}

                studies_list = []
                for _, row in df.iterrows():
                    study_item = html.Div([
                        html.Div(row['title'], style=styles['study_title']),
                        html.Div(f"Authors: {row['concatenated_authors']}", style=styles['study_authors']),
                        html.Div(f"Year: {row['school_year']}", style=styles['study_year']),
                        html.Button(
                            'View Details',
                            id={'type': 'study-button', 'index': row['research_id']},
                            n_clicks=0,
                            style={
                                'backgroundColor': '#08397C',
                                'color': '#FFF',
                                'border': 'none',
                                'borderRadius': '20px',
                                'padding': '5px 15px',
                                'marginTop': '10px',
                                'cursor': 'pointer',
                                'fontSize': '0.8rem',
                                'fontFamily': 'Montserrat, sans-serif'
                            }
                        ),
                        # Add a hidden div to store the research ID
                        html.Div(row['research_id'], id={'type': 'research-id', 'index': row['research_id']}, style={'display': 'none'})
                    ], style=styles['study_item'])
                    studies_list.append(study_item)

                panel_content = html.Div([
                    html.Button(
                        '×', 
                        id='close-panel',
                        n_clicks=0,
                        style=styles['close_button']
                    ),
                    html.H2(f"Studies in {clicked_id}", style={'marginBottom': '20px', 'color': '#08397C'}),
                    html.Div(studies_list)
                ])

                return panel_content, {**styles['side_panel'], 'display': 'block', 'transform': 'translateX(0)'}

            return None, {'display': 'none'}
            
        except Exception as e:
            print(f"Error in update_side_panel: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None, {'display': 'none'}

    # Update the threshold slider callback
    @dash_app.callback(
        [Output('threshold-slider', 'max'),
         Output('threshold-slider', 'value'),
         Output('threshold-slider', 'marks'),
         Output('threshold-store', 'data')],
        [Input('parent-sdg-store', 'data'),
         Input('year-slider', 'value'),
         Input('college-dropdown', 'value')]
    )
    def update_threshold_range(parent_sdg, year_range, selected_colleges):
        if parent_sdg:
            try:
                research_areas_df = get_filtered_research_area_counts(
                    selected_sdg=parent_sdg,
                    start_year=year_range[0] if year_range else None,
                    end_year=year_range[1] if year_range else None,
                    selected_colleges=selected_colleges if selected_colleges else None
                )

                if not research_areas_df.empty:
                    min_threshold = 1
                    max_threshold = int(research_areas_df['study_count'].max())
                    
                    # Set default value to 25th percentile instead of midpoint
                    default_value = max(
                        min_threshold,
                        int(research_areas_df['study_count'].quantile(0.25))
                    )

                    marks = {
                        min_threshold: {'label': str(min_threshold), 'style': {'color': '#08397C'}},
                        default_value: {'label': str(default_value), 'style': {'color': '#08397C'}},
                        max_threshold: {'label': str(max_threshold), 'style': {'color': '#08397C'}}
                    }

                    return max_threshold, default_value, marks, default_value

            except Exception as e:
                print(f"Error updating threshold: {e}")
                import traceback
                print(traceback.format_exc())

        return dash.no_update, 1, dash.no_update, 1
    
    dash_app.clientside_callback(
        """
        function(n_clicks, research_id) {
            if (n_clicks > 0) {
                console.log("Button clicked, research_id:", research_id);
                window.parent.postMessage({
                    type: 'study_click',
                    research_id: research_id
                }, '*');
                return 0;  // Reset n_clicks
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output({'type': 'study-button', 'index': MATCH}, 'n_clicks'),
        Input({'type': 'study-button', 'index': MATCH}, 'n_clicks'),
        State({'type': 'research-id', 'index': MATCH}, 'children'),
        prevent_initial_call=True
    )

    return dash_app