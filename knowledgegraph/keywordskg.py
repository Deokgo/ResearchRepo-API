import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict, Counter
import pandas as pd
from . import db_manager

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
            'fontSize': '13px',
            'padding': '5px',
            'marginBottom': '20px'
        },
        'filter_button': {
            'width': '100%',
            'backgroundColor': '#08397C',
            'fontSize': '15px',
            'color': 'white',
            'padding': '10px',
            'borderRadius': '4px',
            'border': 'none',
            'cursor': 'pointer'
        },
        'label': {
            'marginBottom': '10px',
            'fontSize': '13px',
            'color': '#08397C',
            'fontFamily': 'Montserrat',
            'display': 'block'
        },
        'main_label': {
            'fontSize': '20px',
            'color': '#F40824',
            'fontFamily': 'Montserrat',
            'fontWeight': 'bold',
            'marginBottom': '16px',
            'display': 'block'
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

            html.Button(
                'Apply Filters',
                id='apply-filters',
                n_clicks=0,
                style=styles['filter_button']
            )
        ], style=styles['filter_container']),
        
        html.Div([
            dcc.Graph(
                id='research-network-graph',
                style={'height': 'calc(100vh - 40px)', 'width': '100%'},
                config={'scrollZoom': True}
            )
        ], style=styles['graph_container'])
    ], style=styles['main_container'])

    @dash_app.callback(
        [Output('research-network-graph', 'figure'),
         Output('clicked-node', 'data')],
        [Input('apply-filters', 'n_clicks'),
         Input('research-network-graph', 'clickData')],
        [State('year-slider', 'value'),
         State('college-dropdown', 'value')]
    )
    def update_graph(n_clicks, clickData, year_range, selected_colleges):
        global palette_dict
        ctx = dash.callback_context
        triggered_input = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Handle click events
        clicked_node = None
        if triggered_input == 'research-network-graph' and clickData:
            clicked_node = clickData['points'][0]['text']

        # Filter data based on year range and selected colleges
        filtered_df = df.copy()
        
        if year_range:
            filtered_df = filtered_df[
                (filtered_df['year'] >= year_range[0]) & 
                (filtered_df['year'] <= year_range[1])
            ]
        
        if selected_colleges:
            filtered_df = filtered_df[filtered_df['college_id'].isin(selected_colleges)]

        # Process filtered data
        dept_metadata = defaultdict(lambda: {
            'papers': set(),
            'keywords': Counter(),
            'college': None
        })

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
                dept_metadata[program]['keywords'].update(keywords)

        # Build network with filtered data
        G = build_keyword_network(dept_metadata)
        
        # Update global positions if needed
        global global_pos
        if not global_pos or len(global_pos) != len(G.nodes()):
            global_pos = nx.spring_layout(G, k=1, iterations=50)

        # Build traces
        traces = build_network_traces(G, clicked_node)

        # Create title with filter information
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
                showlegend=False,
                hovermode='closest',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
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

    if clicked_node and clicked_node in G:
        highlighted_nodes.add(clicked_node)
        for neighbor in G.neighbors(clicked_node):
            highlighted_nodes.add(neighbor)
            highlighted_edges.append((clicked_node, neighbor))

    # Separate nodes by type
    keyword_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 'keyword']
    program_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 'program']

    # Create edge traces
    edge_x, edge_y = [], []
    edge_highlight_x, edge_highlight_y = [], []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        if edge in highlighted_edges or (edge[1], edge[0]) in highlighted_edges:
            edge_highlight_x.extend([x0, x1, None])
            edge_highlight_y.extend([y0, y1, None])
        else:
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    # Create program node hovertext with keyword counts
    program_hovertext = []
    for node in program_nodes:
        if clicked_node and clicked_node in keyword_nodes and G.has_edge(node, clicked_node):
            count = G[node][clicked_node]['weight']
            program_hovertext.append(f"{node} (used {count} times)")
        else:
            program_hovertext.append(node)

    # Create keyword node hovertext with usage counts in programs
    keyword_hovertext = []
    for node in keyword_nodes:
        if clicked_node and clicked_node in program_nodes and G.has_edge(clicked_node, node):
            count = G[clicked_node][node]['weight']
            keyword_hovertext.append(f"{node} (used {count} times)")
        else:
            keyword_hovertext.append(node)

    # Create traces
    traces = [
        go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none'),
        go.Scatter(x=edge_highlight_x, y=edge_highlight_y, line=dict(width=2, color='#FF5733'), mode='lines', hoverinfo='none'),
        go.Scatter(
            x=[pos[node][0] for node in program_nodes],
            y=[pos[node][1] for node in program_nodes],
            mode='markers+text',
            text=program_hovertext,
            textposition="bottom center",
            marker=dict(size=15, color=[palette_dict.get(G.nodes[node]['college'], '#000000') for node in program_nodes], symbol='circle'),
            name='Programs',
            hoverinfo='text'
        ),
        go.Scatter(
            x=[pos[node][0] for node in keyword_nodes],
            y=[pos[node][1] for node in keyword_nodes],
            mode='markers+text',
            text=keyword_hovertext,
            textposition="bottom center",
            marker=dict(size=15, color=keyword_color, symbol='diamond'),
            name='Keywords',
            hoverinfo='text'
        )
    ]

    return traces
