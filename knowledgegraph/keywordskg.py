import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict, Counter
import pandas as pd
from . import db_manager

# Define color palette for colleges
palette_dict = {
    'CAS': '#141cff',   # Blue
    'CCIS': '#04a417',  # Green
    'CHS': '#c2c2c2',   # Grey
    'MITL': '#bb0c0c',  # Red
    'ETYCB': '#e9e107'  # Yellow
}

# Global variable to store node positions
global_pos = {}

def create_research_network(flask_app):
    global global_pos  # Use the global cache

    # Initialize Dash app
    dash_app = Dash(__name__, server=flask_app, url_base_pathname='/knowledgegraph/research-network/')

    # Process data to collect department information
    df = db_manager.get_all_data()
    dept_metadata = defaultdict(lambda: {
        'papers': set(),
        'keywords': Counter(),
        'college': None
    })

    for _, row in df.iterrows():
        program = row['program_name']
        college = row['college_id']
        research_id = row['research_id']
        
        if not program or pd.isna(row['concatenated_keywords']):
            continue

        dept_metadata[program]['papers'].add(research_id)
        dept_metadata[program]['college'] = college

        # Process keywords
        if pd.notnull(row['concatenated_keywords']):
            keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
            dept_metadata[program]['keywords'].update(keywords)

    # **Create the network graph once**
    G = build_keyword_network(dept_metadata)

    # **Generate static positions once and store them**
    if not global_pos:
        global_pos = nx.spring_layout(G, k=1, iterations=50)

    # Define layout
    dash_app.layout = html.Div([
        dcc.Graph(
            id='research-network-graph',
            style={'height': 'calc(100vh - 40px)', 'width': '100%'},
            config={'scrollZoom': True}
        )
    ])

    @dash_app.callback(
        Output('research-network-graph', 'figure'),
        [Input('research-network-graph', 'hoverData')]
    )
    def update_graph(hover_data):
        traces = build_network_traces(G, hover_data)

        return {
            'data': traces,
            'layout': go.Layout(
                title='Program-Keyword Knowledge Graph',
                showlegend=False,
                hovermode='closest',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                dragmode='pan',
                paper_bgcolor='white',
                plot_bgcolor='white'
            )
        }

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
        
        # Connect keywords to programs
        for program, data in dept_metadata.items():
            if keyword in data['keywords']:
                G.add_edge(program, keyword, 
                          weight=data['keywords'][keyword])
    
    return G

def build_network_traces(G, hover_data):
    global global_pos  # Use cached positions

    hovered_node = None
    if hover_data and 'points' in hover_data:
        hovered_node = hover_data['points'][0]['text']

    # **Keep node positions constant**
    pos = global_pos

    # **Highlight hovered node and neighbors**
    highlighted_nodes = set()
    highlighted_edges = []

    if hovered_node and hovered_node in G:
        highlighted_nodes.add(hovered_node)
        for neighbor in G.neighbors(hovered_node):
            highlighted_nodes.add(neighbor)
            highlighted_edges.append((hovered_node, neighbor))

    # **Create edge traces (normal and highlighted)**
    edge_x, edge_y, edge_highlight_x, edge_highlight_y = [], [], [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]

        if edge in highlighted_edges or (edge[1], edge[0]) in highlighted_edges:
            edge_highlight_x.extend([x0, x1, None])
            edge_highlight_y.extend([y0, y1, None])
        else:
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    normal_edges_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=1, color='#888'), mode='lines', hoverinfo='none')
    highlighted_edges_trace = go.Scatter(x=edge_highlight_x, y=edge_highlight_y, line=dict(width=2, color='#FF5733'), mode='lines', hoverinfo='none')

    # **Create node traces**
    node_x, node_y, node_size, node_color, node_text = [], [], [], [], []
    for node in G.nodes():
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        node_size.append(25 if node in highlighted_nodes else 15)
        node_color.append('#FFD700' if node in highlighted_nodes else '#04a417')
        node_text.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text', text=node_text, textposition="bottom center",
        marker=dict(size=node_size, color=node_color, line=dict(width=2, color='black')),
        hoverinfo='text'
    )

    return [normal_edges_trace, highlighted_edges_trace, node_trace]

