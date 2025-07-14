import dash
from dash import Dash, dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import networkx as nx
from collections import defaultdict, Counter
import pandas as pd
import numpy as np
from database.knowledgegraph_queries import get_program_research_aggregation

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

    # Process data to collect usage per program information
    program_data = get_program_research_aggregation()

    # Calculate initial thresholds based on per-program usage
    keyword_program_usage = defaultdict(lambda: defaultdict(int))
    
    for _, row in program_data.iterrows():
        if pd.notnull(row['concatenated_keywords']):
            keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
            program = row['program_name']
            for keyword in keywords:
                keyword_program_usage[keyword][program] += 1

    # Find the highest number where any keyword has at least 2 programs using it that many times
    max_threshold = 1
    # Test each possible threshold from 1 up
    for test_threshold in range(1, 100):  # Set a reasonable upper limit
        found_valid_keyword = False
        # Check each keyword
        for keyword, program_counts in keyword_program_usage.items():
            # Count programs that used this keyword at least test_threshold times
            programs_meeting_threshold = sum(
                1 for count in program_counts.values() 
                if count >= test_threshold
            )
            # If at least 2 programs meet this threshold
            if programs_meeting_threshold >= 2:
                found_valid_keyword = True
                break
        
        if found_valid_keyword:
            max_threshold = test_threshold
        else:
            # If no keywords have 2+ programs meeting this threshold, we've found our max
            break

    min_usage_threshold = 1
    max_usage_threshold = max_threshold
    default_threshold = (min_usage_threshold + max_usage_threshold) // 2

    print(f"Initial thresholds - min: {min_usage_threshold}, max: {max_usage_threshold}, default: {default_threshold}")

    # Create marks for usage threshold
    if max_usage_threshold > 10:
        step = max(1, max_usage_threshold // 6)
        usage_marks = {
            i: f'≥{i} uses each by 2+ programs' for i in range(
                min_usage_threshold, 
                max_usage_threshold + 1, 
                step
            )
        }
        usage_marks[max_usage_threshold] = f'≥{max_usage_threshold} uses each by 2+ programs'
    else:
        usage_marks = {i: f'≥{i} uses each by 2+ programs' for i in range(min_usage_threshold, max_usage_threshold + 1)}

    # Define layout with single filter
    dash_app.layout = html.Div([
        dcc.Store(id='clicked-node', data=None),
        dcc.Interval(
            id='refresh-interval',
            interval=300000,  # 5 minutes in milliseconds
            n_intervals=0
        ),
        html.Div([
            html.Label('Filters', style=styles['main_label']),
            html.Div([
                html.Label('Select Year Range:', style=styles['label']),
                html.Div([
                    dcc.RangeSlider(
                        id='year-slider',
                        min=program_data['school_year'].min(),
                        max=program_data['school_year'].max(),
                        value=[program_data['school_year'].min(), program_data['school_year'].max()],
                        marks={year: str(year) for year in range(int(program_data['school_year'].min()), 
                                                               int(program_data['school_year'].max()) + 1, 2)},
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
                                for college in program_data['college_id'].unique()],
                        value=[],
                        multi=True,
                        placeholder='Select colleges...'
                    )
                ], style=styles['dropdown_container']),
            ]),

            # Single threshold slider for minimum uses per program
            html.Div([
                html.Label('Minimum Uses per Program:', style=styles['label']),
                html.Div([
                    dcc.Slider(
                        id='usage-threshold-slider',
                        min=min_usage_threshold,
                        max=max_usage_threshold,
                        value=default_threshold,  # Use the calculated default
                        marks=usage_marks,
                        step=1,
                        included=True
                    )
                ], style=styles['slider_container']),
            ]),

        ], style=styles['filter_container']),
        
        html.Div([
            dcc.Graph(
                id='research-network-graph',
                style={'height': 'calc(100vh - 40px)', 'width': '100%'},
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
    [Output('usage-threshold-slider', 'min'),
     Output('usage-threshold-slider', 'max'),
     Output('usage-threshold-slider', 'value'),
     Output('usage-threshold-slider', 'marks')],
    [Input('year-slider', 'value'),
     Input('college-dropdown', 'value'),
     Input('refresh-interval', 'n_intervals')]
)
    def update_usage_threshold_range(year_range, selected_colleges, n_intervals):
        print(f"Updating threshold range. Interval trigger: {n_intervals}")
        
        # Get filtered data
        filtered_data = get_program_research_aggregation(
            start_year=year_range[0] if year_range else None,
            end_year=year_range[1] if year_range else None,
            selected_colleges=selected_colleges if selected_colleges else None
        )

        # Calculate keyword usage per program
        keyword_program_usage = defaultdict(lambda: defaultdict(int))
        for _, row in filtered_data.iterrows():
            if pd.notnull(row['concatenated_keywords']):
                keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
                program = row['program_name']
                for keyword in keywords:
                    keyword_program_usage[keyword][program] += 1

        # Find the highest number where any keyword has at least 2 programs using it that many times
        max_threshold = 1
        # Test each possible threshold from 1 up
        for test_threshold in range(1, 100):  # Set a reasonable upper limit
            found_valid_keyword = False
            # Check each keyword
            for keyword, program_counts in keyword_program_usage.items():
                # Count programs that used this keyword at least test_threshold times
                programs_meeting_threshold = sum(
                    1 for count in program_counts.values() 
                    if count >= test_threshold
                )
                # If at least 2 programs meet this threshold
                if programs_meeting_threshold >= 2:
                    found_valid_keyword = True
                    break
            
            if found_valid_keyword:
                max_threshold = test_threshold
            else:
                # If no keywords have 2+ programs meeting this threshold, we've found our max
                break

        min_usage_threshold = 1
        max_usage_threshold = max_threshold
        default_threshold = (min_usage_threshold + max_usage_threshold) // 2

        print(f"Setting threshold range: min={min_usage_threshold}, max={max_usage_threshold}, default={default_threshold}")

        # Create marks for usage threshold
        if max_usage_threshold > 10:
            step = max(1, max_usage_threshold // 6)
            usage_marks = {
                i: f'≥{i} uses each by 2+ programs' for i in range(
                    min_usage_threshold, 
                    max_usage_threshold + 1, 
                    step
                )
            }
            usage_marks[max_usage_threshold] = f'≥{max_usage_threshold} uses each by 2+ programs'
        else:
            usage_marks = {i: f'≥{i} uses each by 2+ programs' for i in range(min_usage_threshold, max_usage_threshold + 1)}

        return min_usage_threshold, max_usage_threshold, default_threshold, usage_marks

    @dash_app.callback(
    [Output('research-network-graph', 'figure'),
     Output('clicked-node', 'data')],
    [Input('year-slider', 'value'),
     Input('college-dropdown', 'value'),
     Input('usage-threshold-slider', 'value'),
     Input('research-network-graph', 'clickData'),
     Input('refresh-interval', 'n_intervals')],
    [State('clicked-node', 'data')]
)
    def update_graph(year_range, selected_colleges, usage_threshold, clickData, n_intervals, previous_clicked):
        print(f"Updating graph. Interval trigger: {n_intervals}")
        
        # Get filtered data
        filtered_data = get_program_research_aggregation(
            start_year=year_range[0] if year_range else None,
            end_year=year_range[1] if year_range else None,
            selected_colleges=selected_colleges if selected_colleges else None
        )

        # Recalculate keyword usage based on filtered data
        keyword_program_usage = defaultdict(lambda: defaultdict(int))
        for _, row in filtered_data.iterrows():
            if pd.notnull(row['concatenated_keywords']):
                keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
                program = row['program_name']
                for keyword in keywords:
                    keyword_program_usage[keyword][program] += 1

        # Find the highest number where any keyword has at least 2 programs using it that many times
        max_threshold = 1
        # Get the absolute maximum any program used any keyword
        absolute_max = max(
            count 
            for program_counts in keyword_program_usage.values() 
            for count in program_counts.values()
        )
        
        # Test each possible threshold from 1 to absolute_max
        for test_threshold in range(1, absolute_max + 1):
            # Check each keyword
            for keyword, program_counts in keyword_program_usage.items():
                # Count programs that used this keyword at least test_threshold times
                programs_meeting_threshold = sum(
                    1 for count in program_counts.values() 
                    if count >= test_threshold
                )
                # If at least 2 programs meet this threshold
                if programs_meeting_threshold >= 2:
                    max_threshold = test_threshold
                    break  # Found a keyword with 2+ programs meeting this threshold
            else:
                # If we complete the keyword loop without finding any keywords
                # with 2+ programs meeting this threshold, we've found our max
                break

        # Ensure usage_threshold is within valid range
        if usage_threshold is None:
            usage_threshold = 1
        elif isinstance(usage_threshold, list):
            usage_threshold = min(usage_threshold[0], max_threshold)
        else:
            usage_threshold = min(int(usage_threshold), max_threshold)
        
        print(f"Using threshold: {usage_threshold} (max possible: {max_threshold})")  # Debug print

        # Get clicked node info
        clicked_keyword = None
        if clickData and clickData['points'][0]['text'] != previous_clicked:
            clicked_keyword = clickData['points'][0]['text']
            previous_clicked = clicked_keyword
        
        # Build network
        G = build_keyword_network(
            filtered_data,
            clicked_keyword=clicked_keyword,
            usage_threshold=usage_threshold
        )

        traces = build_network_traces(G, clicked_keyword)

        title = f'Research Synergy Knowledge Graph (Min. {usage_threshold} uses per program)'
        if selected_colleges or year_range != [filtered_data['school_year'].min(), filtered_data['school_year'].max()]:
            filter_desc = []
            if selected_colleges:
                filter_desc.append(f"Colleges: {', '.join(selected_colleges)}")
            if year_range != [filtered_data['school_year'].min(), filtered_data['school_year'].max()]:
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
        }, previous_clicked

    return dash_app


def build_keyword_network(df, clicked_keyword=None, usage_threshold=1):
    print(f"Building network with threshold: {usage_threshold}")  # Debug print
    G = nx.Graph()
    
    # Get aggregated program data
    program_data = get_program_research_aggregation()
    
    # Collect keyword statistics
    keyword_program_usage = defaultdict(lambda: defaultdict(int))
    program_colors = {}
    
    # Process the DataFrame rows to get keyword usage per program
    for _, row in program_data.iterrows():
        program = row['program_name']
        program_colors[program] = row['color_code']
        
        if pd.notnull(row['concatenated_keywords']):
            keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
            for keyword in keywords:
                keyword_program_usage[keyword][program] += 1
    
    # Filter keywords: must have at least 2 programs that EACH used it >= threshold times
    valid_keywords = set()
    for keyword, program_counts in keyword_program_usage.items():
        # Get programs that used it at least threshold times
        high_usage_programs = [prog for prog, count in program_counts.items() 
                             if count >= usage_threshold]
        if len(high_usage_programs) >= 2:  # At least 2 programs must meet threshold
            valid_keywords.add(keyword)
    
    print(f"Found {len(valid_keywords)} valid keywords")  # Debug print
    
    if clicked_keyword and clicked_keyword in valid_keywords:
        # Show clicked keyword and ONLY its connected programs that meet the threshold
        high_usage_programs = [prog for prog, count in keyword_program_usage[clicked_keyword].items() 
                             if count >= usage_threshold]
        
        G.add_node(clicked_keyword, 
                  type='keyword',
                  usage_count=sum(count for prog, count in keyword_program_usage[clicked_keyword].items()
                                if prog in high_usage_programs),
                  program_count=len(high_usage_programs))
        
        # Add ONLY programs that used it >= threshold times
        for program in high_usage_programs:
            count = keyword_program_usage[clicked_keyword][program]
            research_count = program_data[program_data['program_name'] == program]['research_count'].iloc[0]
            G.add_node(program, 
                      type='program',
                      usage_count=count,
                      research_count=research_count,
                      relative_size=1.0,
                      color_code=program_colors[program])
            G.add_edge(clicked_keyword, program)
    else:
        # Show all valid keywords
        for keyword in valid_keywords:
            high_usage_programs = [prog for prog, count in keyword_program_usage[keyword].items() 
                                 if count >= usage_threshold]
            G.add_node(keyword, 
                      type='keyword',
                      usage_count=sum(count for prog, count in keyword_program_usage[keyword].items()
                                    if prog in high_usage_programs),
                      program_count=len(high_usage_programs))
    
    return G

def build_network_traces(G, clicked_node):
    global global_pos

    # Use Kamada-Kawai layout when a node is clicked, spring layout otherwise
    if clicked_node:
        pos = nx.kamada_kawai_layout(G)
    else:
        # Check if global_pos has all current nodes, if not recalculate
        current_nodes = set(G.nodes())
        if global_pos and set(global_pos.keys()) == current_nodes:
            pos = global_pos
        else:
            pos = nx.spring_layout(G, k=1, iterations=50)
            global_pos = pos

    traces = []
    
    # Create keyword nodes trace
    keyword_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 'keyword']
    if keyword_nodes:
        keyword_hovertext = []
        for node in keyword_nodes:
            usage_count = G.nodes[node]['usage_count']
            high_usage_programs = G.nodes[node]['program_count']  # This is now correctly counted in build_keyword_network
            keyword_hovertext.append(f"{node}\nUsed {usage_count} times in {high_usage_programs} programs")

        # Filter nodes that have positions
        positioned_keyword_nodes = [node for node in keyword_nodes if node in pos]
        
        if positioned_keyword_nodes:
            traces.append(go.Scatter(
                x=[pos[node][0] for node in positioned_keyword_nodes],
                y=[pos[node][1] for node in positioned_keyword_nodes],
                mode='markers+text',
                text=[node for node in positioned_keyword_nodes],
                hovertext=[keyword_hovertext[keyword_nodes.index(node)] for node in positioned_keyword_nodes],
                textposition="bottom center",
                marker=dict(
                    size=[20 + (G.nodes[node]['program_count'] * 2) for node in positioned_keyword_nodes],
                    color=keyword_color,
                    symbol='diamond'
                ),
                name='Keywords',
                hoverinfo='text'
            ))

    # Create program nodes trace if a keyword is clicked
    program_nodes = [node for node, attr in G.nodes(data=True) if attr['type'] == 'program']
    if program_nodes:
        program_hovertext = []
        node_colors = []
        for node in program_nodes:
            usage_count = G.nodes[node]['usage_count']
            color_code = G.nodes[node]['color_code']
            program_hovertext.append(f"{node}\nUses keyword {usage_count} times")
            node_colors.append(color_code or '#0A438F')  # Default to '#0A438F' if color_code is None

        # Filter nodes that have positions
        positioned_program_nodes = [node for node in program_nodes if node in pos]
        
        if positioned_program_nodes:
            # Get corresponding colors and hover text for positioned nodes
            positioned_colors = [node_colors[program_nodes.index(node)] for node in positioned_program_nodes]
            positioned_hovertext = [program_hovertext[program_nodes.index(node)] for node in positioned_program_nodes]
            
            traces.append(go.Scatter(
                x=[pos[node][0] for node in positioned_program_nodes],
                y=[pos[node][1] for node in positioned_program_nodes],
                mode='markers+text',
                text=[node for node in positioned_program_nodes],
                hovertext=positioned_hovertext,
                textposition="top center",
                marker=dict(
                    size=[30 * G.nodes[node]['relative_size'] for node in positioned_program_nodes],
                    color=positioned_colors,
                    symbol='circle'
                ),
                name='Programs',
                hoverinfo='text'
            ))

    # Add edges if a keyword is clicked
    if clicked_node:
        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        traces.insert(0, go.Scatter(
            x=edge_x,
            y=edge_y,
            mode='lines',
            line=dict(width=0.5, color='#888'),
            hoverinfo='none'
        ))

    return traces

def build_research_aggregation_network(df, clicked_keyword=None, usage_threshold=(2, float('inf'))):
    G = nx.Graph()
    
    # Collect keyword statistics and research counts
    keyword_freq = Counter()
    keyword_programs = defaultdict(set)
    program_research = defaultdict(int)
    program_colors = {}
    
    # Process the data
    for _, row in df.iterrows():
        program = row['program_name']
        program_colors[program] = row['color_code']
        program_research[program] = row['research_count']
        
        if pd.notnull(row['concatenated_keywords']):
            keywords = [k.strip().lower() for k in row['concatenated_keywords'].split(';')]
            for keyword in keywords:
                keyword_freq[keyword] += 1
                keyword_programs[keyword].add(program)
    
    # Filter keywords based on threshold ranges
    valid_keywords = {
        k for k in keyword_freq 
        if (usage_threshold[0] <= keyword_freq[k] <= usage_threshold[1])
    }
    
    if clicked_keyword and clicked_keyword in valid_keywords:
        # Show clicked keyword and connected programs
        G.add_node(clicked_keyword,
                  type='keyword',
                  usage_count=keyword_freq[clicked_keyword],
                  program_count=len(keyword_programs[clicked_keyword]))
        
        # Add connected programs
        connected_programs = keyword_programs[clicked_keyword]
        if connected_programs:
            max_research = max(program_research[p] for p in connected_programs)
            
            for program in connected_programs:
                relative_size = 0.3 + (0.7 * program_research[program] / max_research) if max_research > 0 else 1.0
                G.add_node(program,
                          type='program',
                          research_count=program_research[program],
                          usage_count=1,
                          relative_size=relative_size,
                          color_code=program_colors[program])
                G.add_edge(clicked_keyword, program)
    else:
        # Show all valid keywords
        for keyword in valid_keywords:
            G.add_node(keyword,
                      type='keyword',
                      usage_count=keyword_freq[keyword],
                      program_count=len(keyword_programs[keyword]))
    
    return G
