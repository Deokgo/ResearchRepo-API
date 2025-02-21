import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict, Counter
import pandas as pd
from . import db_manager
import numpy as np

# Define color for keywords (Distinct Purple)
keyword_color = '#8A2BE2'

# Global variable to store node positions
global_pos = {}

def create_research_network(flask_app):
    global global_pos

    # Initialize Dash app
    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/knowledgegraph/research-network/')

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
        },
        'threshold_container': {
            'fontSize': '5px',
            'color': '#08397C',
            'marginTop': '20px',
            'marginBottom': '30px',
        }
    }

    # Process data to collect department information
    df = db_manager.get_all_data()

    # Define color palette from database (make it global)
    global palette_dict
    palette_dict = {}
    for _, row in df.iterrows():
        college_id = row['college_id']
        color_code = row['color_code']
        if college_id and color_code:
            palette_dict[college_id] = color_code

    # Calculate initial threshold range from complete dataset
    initial_keyword_counts = defaultdict(int)
    for _, row in df.iterrows():
        if pd.notnull(row['concatenated_keywords']):
            keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
            for keyword in keywords:  # Update counts one keyword at a time
                initial_keyword_counts[keyword] += 1

    min_threshold = 2
    max_threshold = max(initial_keyword_counts.values())
    
    # Create initial marks
    if max_threshold > 10:
        step = max(1, max_threshold // 8)
        initial_marks = {i: f'{i} uses' for i in range(min_threshold, max_threshold + 1, step)}
        initial_marks[max_threshold] = f'{max_threshold} uses'
    else:
        initial_marks = {i: f'{i} uses' for i in range(min_threshold, max_threshold + 1)}

    # Define layout with filters
    dash_app.layout = html.Div([
        dcc.Store(id='clicked-node', data=None),
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
                html.Label('Select College/s:', style=styles['label']),
                html.Div([
                    dcc.Dropdown(
                        id='college-dropdown',
                        options=[{'label': college, 'value': college} 
                                for college in df['college_id'].unique()],
                        value=[],
                        multi=True,
                        placeholder='Select colleges...'
                    )
                ], style=styles['dropdown_container']),
            ]),

            # Add threshold slider
            html.Div([
                html.Label('Keyword Usage Threshold:', style=styles['label']),
                html.Div([
                    dcc.Slider(
                        id='threshold-slider',
                        min=min_threshold,
                        max=max_threshold,
                        value=min_threshold,
                        marks=initial_marks,
                        step=None
                    )
                ], style=styles['threshold_container']),
            ]),

        ], style=styles['filter_container']),
        
        html.Div([
            dcc.Graph(
                id='research-network-graph',
                style={
                    'height': 'calc(100vh - 40px)',
                    'width': '100%'
                },
                config={
                    'responsive': True,
                    'scrollZoom': True,
                    'displayModeBar': True,
                    'modeBarButtonsToRemove': ['lasso2d', 'select2d']
                },
            )
        ], style=styles['graph_container'])
    ], style=styles['main_container'])

    @dash_app.callback(
    [Output('threshold-slider', 'min'),
     Output('threshold-slider', 'max'),
     Output('threshold-slider', 'value'),
     Output('threshold-slider', 'marks')],
    [Input('year-slider', 'value'),
     Input('college-dropdown', 'value')]
)
    def update_threshold_range(year_range, selected_colleges):
        filtered_df = df.copy()

        if year_range:
            filtered_df = filtered_df[(filtered_df['year'] >= year_range[0]) & 
                                    (filtered_df['year'] <= year_range[1])]

        if selected_colleges:
            filtered_df = filtered_df[filtered_df['college_id'].isin(selected_colleges)]

        keyword_counts = defaultdict(int)
        for _, row in filtered_df.iterrows():
            if pd.notnull(row['concatenated_keywords']):
                keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
                for keyword in keywords:
                    keyword_counts[keyword] += 1

        if not keyword_counts:
            return 2, 5, 2, {i: f'{i} uses' for i in range(2, 6)}

        min_threshold = 2
        max_threshold = max(keyword_counts.values())
        avg_count = int(np.ceil(np.mean(list(keyword_counts.values()))))
        default_value = max(min_threshold, avg_count)

        if max_threshold > 10:
            step = max(1, max_threshold // 8)
            marks = {i: f'{i} uses' for i in range(min_threshold, max_threshold + 1, step)}
            marks[max_threshold] = f'{max_threshold} uses'
        else:
            marks = {i: f'{i} uses' for i in range(min_threshold, max_threshold + 1)}

        return min_threshold, max_threshold, default_value, marks


    @dash_app.callback(
    [Output('research-network-graph', 'figure'),
     Output('clicked-node', 'data')],
    [Input('year-slider', 'value'),
     Input('college-dropdown', 'value'),
     Input('threshold-slider', 'value'),
     Input('research-network-graph', 'clickData')],
    [State('clicked-node', 'data')]
)
    def update_graph(year_range, selected_colleges, threshold, clickData, previous_clicked):
        threshold = max(2, threshold if threshold is not None else 2)

        global palette_dict
        ctx = dash.callback_context
        triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]

        # Handle click events
        clicked_node = None
        if triggered_input == 'research-network-graph' and clickData:
            current_clicked = clickData['points'][0]['text']
            clicked_node = None if current_clicked == previous_clicked else current_clicked

        # Filter and process data
        filtered_df = df.copy()
        
        if year_range:
            filtered_df = filtered_df[(filtered_df['year'] >= year_range[0]) & 
                                    (filtered_df['year'] <= year_range[1])]
        
        if selected_colleges:
            filtered_df = filtered_df[filtered_df['college_id'].isin(selected_colleges)]

        # Process data based on threshold
        dept_metadata = defaultdict(lambda: {'papers': set(), 'keywords': Counter(), 'college': None})
        keyword_usage = Counter()

        for _, row in filtered_df.iterrows():
            if pd.notnull(row['concatenated_keywords']):
                keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
                keyword_usage.update(keywords)

        valid_keywords = {k for k, count in keyword_usage.items() if count >= threshold}

        for _, row in filtered_df.iterrows():
            program = row['program_name']
            college = row['college_id']
            research_id = row['research_id']
            
            if not program or pd.isna(row['concatenated_keywords']):
                continue

            dept_metadata[program]['papers'].add(research_id)
            dept_metadata[program]['college'] = college

            if pd.notnull(row['concatenated_keywords']):
                keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
                filtered_keywords = [k for k in keywords if k in valid_keywords]
                dept_metadata[program]['keywords'].update(filtered_keywords)

        G = build_keyword_network(dept_metadata)
        
        global global_pos
        if not global_pos or len(global_pos) != len(G.nodes()):
            global_pos = nx.spring_layout(G, k=1, iterations=50)

        traces = build_network_traces(G, clicked_node)

        title = '<br>Program-Keyword Knowledge Graph'
        if selected_colleges or year_range != [df['year'].min(), df['year'].max()]:
            filter_desc = []
            if selected_colleges:
                filter_desc.append(f"Colleges: {', '.join(selected_colleges)}")
            if year_range != [df['year'].min(), df['year'].max()]:
                filter_desc.append(f"Years: {year_range[0]}-{year_range[1]}")
            title += f" ({' | '.join(filter_desc)})"

        return {
            'data': traces,
            'layout': go.Layout(
                title=title,
                titlefont=dict(size=16),
                showlegend=False,
                hovermode='closest',
                margin=dict(b=0, l=0, r=0, t=50),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                transition=dict(duration=500),
                dragmode='pan',
                paper_bgcolor='white',
                plot_bgcolor='white'
            )
        }, clicked_node

    return dash_app


def build_keyword_network(dept_metadata):
    G = nx.Graph()
    
    # Add program nodes
    for program, data in dept_metadata.items():
        G.add_node(program, 
                  type='program',
                  college=data['college'])
    
    # Add keyword nodes for top keywords
    keyword_freq = Counter()
    for data in dept_metadata.values():
        keyword_freq.update(data['keywords'])
    
    top_keywords = [k for k, _ in keyword_freq.most_common(20)]  # Top 20 keywords
    
    for keyword in top_keywords:
        G.add_node(keyword, type='keyword')
        
        # Connect keywords to programs and store usage count
        for program, data in dept_metadata.items():
            if keyword in data['keywords']:
                G.add_edge(program, keyword, weight=data['keywords'][keyword])
    
    return G

def build_network_traces(G, clicked_node):
    global global_pos, palette_dict

    # Get positions and setup highlighted nodes/edges
    pos = global_pos
    highlighted_nodes = set()
    highlighted_edges = []
    
    # Determine if we're in highlight mode
    highlight_mode = clicked_node and clicked_node in G
    
    if highlight_mode:
        highlighted_nodes.add(clicked_node)
        for neighbor in G.neighbors(clicked_node):
            highlighted_nodes.add(neighbor)
            highlighted_edges.append((clicked_node, neighbor))

    # Separate nodes by type
    keyword_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 'keyword']
    program_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 'program']

    # Filter nodes based on highlight mode
    if highlight_mode:
        keyword_nodes = [n for n in keyword_nodes if n in highlighted_nodes]
        program_nodes = [n for n in program_nodes if n in highlighted_nodes]

    # Create edge traces
    edge_x, edge_y = [], []
    
    # Only show highlighted edges in highlight mode
    edges_to_show = highlighted_edges if highlight_mode else G.edges()
    
    for edge in edges_to_show:
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    # Create program node hovertext with connected keyword counts
    program_hovertext = []
    program_display = []  # New list for display text
    for node in program_nodes:
        connected_keywords = len([n for n in G.neighbors(node) if G.nodes[n]['type'] == 'keyword'])
        if clicked_node and clicked_node in keyword_nodes and G.has_edge(node, clicked_node):
            count = G[node][clicked_node]['weight']
            program_hovertext.append(f"{node}\n(connected to {connected_keywords} keywords)\n(used '{clicked_node}' {count} times)")
        else:
            program_hovertext.append(f"{node}\n(connected to {connected_keywords} keywords)")
        program_display.append(node)  # Only show the name

    # Create keyword node hovertext with connected program counts
    keyword_hovertext = []
    keyword_display = []  # New list for display text
    for node in keyword_nodes:
        connected_programs = len([n for n in G.neighbors(node) if G.nodes[n]['type'] == 'program'])
        if clicked_node and clicked_node in program_nodes and G.has_edge(clicked_node, node):
            count = G[clicked_node][node]['weight']
            keyword_hovertext.append(f"{node}\n(used in {connected_programs} programs)\n(used {count} times in '{clicked_node}')")
        else:
            keyword_hovertext.append(f"{node}\n(used in {connected_programs} programs)")
        keyword_display.append(node)  # Only show the name

    # Define size ranges for nodes
    keyword_size_range = (20, 30)  # Min and max sizes for keywords
    program_size = 20  # Fixed size for programs

    # Get connection counts for scaling
    keyword_counts = [len([n for n in G.neighbors(node) if G.nodes[n]['type'] == 'program']) 
                     for node in keyword_nodes]
    max_connections = max(keyword_counts) if keyword_counts else 1

    # Create traces
    traces = [
        go.Scatter(
            x=edge_x, 
            y=edge_y, 
            line=dict(width=1, color='rgba(200, 200, 200, 0.3)' if not highlight_mode else 'rgba(255, 87, 51, 0.6)'), 
            mode='lines', 
            hoverinfo='none'
        ),
        go.Scatter(
            x=[pos[node][0] for node in program_nodes],
            y=[pos[node][1] for node in program_nodes],
            mode='markers+text',
            text=program_display,
            hovertext=program_hovertext,
            textposition="bottom center",
            marker=dict(
                size=program_size,
                color=[palette_dict.get(G.nodes[node]['college'], '#000000') for node in program_nodes],
                symbol='circle'
            ),
            name='Programs',
            hoverinfo='text'
        ),
        go.Scatter(
            x=[pos[node][0] for node in keyword_nodes],
            y=[pos[node][1] for node in keyword_nodes],
            mode='markers+text',
            text=keyword_display,
            hovertext=keyword_hovertext,
            textposition="bottom center",
            marker=dict(
                # Scale node size based on number of connections
                size=[
                    keyword_size_range[0] + 
                    (len([n for n in G.neighbors(node) if G.nodes[n]['type'] == 'program']) / max_connections) 
                    * (keyword_size_range[1] - keyword_size_range[0])
                    for node in keyword_nodes
                ],
                color=keyword_color,
                symbol='diamond'
            ),
            name='Keywords',
            hoverinfo='text'
        )
    ]

    return traces
