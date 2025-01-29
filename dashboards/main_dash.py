# created by Jelly Mallari
# continued by Nicole Cabansag (for other charts and added reset_button function)

import dash
from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

class MainDashboard:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/overview/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP])

        self.palette_dict = db_manager.get_college_colors()
        
        # Get default values
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_terms = db_manager.get_unique_values('term')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        self.create_layout()
        self.set_callbacks()

        self.all_sdgs = [
            'SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 
            'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 
            'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17'
        ]

    def create_layout(self):
        """
        Create the layout of the dashboard.
        """

        section = html.Div(
            [
                dcc.Dropdown(
                    id="term",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('term')],
                    value=None,  # Ensure the placeholder appears
                    placeholder="Select a section...",
                    style={"width": "100%"},
                ),
            ],
            className="mb-4",
        )

        college = html.Div(
            [
                dbc.Label("Select College/s:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        terms = sorted(db_manager.get_unique_values('term'))

        term = html.Div(
            [
                dbc.Label("Select Term/s:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="terms",
                    options=[{'label': value, 'value': value} for value in terms],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        status = html.Div(
            [
                dbc.Label("Select Status:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="status",
                    options=[{'label': value, 'value': value} for value in sorted(
                        db_manager.get_unique_values('status'), key=lambda x: (x != 'READY', x != 'PULLOUT', x)
                    )],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        slider = html.Div(
            [
                dbc.Label("Select Years: ", style={"color": "#08397C"}),
                dcc.RangeSlider(
                    min=db_manager.get_min_value('year'), 
                    max=db_manager.get_max_value('year'), 
                    step=1, 
                    id="years",
                    marks=None,
                    tooltip={"placement": "bottom", "always_visible": True},
                    value=[db_manager.get_min_value('year'), db_manager.get_max_value('year')],
                    className="p-0",
                ),
            ],
            className="mb-4",
        )

        button = html.Div(
            [
                dbc.Button("Reset", color="primary", id="reset_button"),
            ],
            className="d-grid gap-2",
        )

        controls = dbc.Col(
            dbc.Card(
                [
                    html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),  # Set the color to red
                    html.Div(
                        [section, college, status, term, slider, button], 
                        style={"font-size": "0.85rem", "padding": "5px"}  # Reduce font size and padding
                    ),
                ],
                body=True,
                style={
                    "background": "#d3d8db",
                    "height": "100vh",  # Full-height sidebar
                    "position": "sticky",  # Sticky position instead of fixed
                    "top": 0,
                    "padding": "10px",  # Reduce padding for a more compact layout
                    "border-radius": "0",  # Remove rounded corners
                },
            )
        )

        text_display = dbc.Container([
            dbc.Row([
                dbc.Container([
                    dbc.Row([
                        dbc.Col(
                        self.create_display_card("Total Research Papers", str(len(db_manager.get_all_data()))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Intended for Publication", str(len(db_manager.filter_data('status', 'READY', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Submitted Papers", str(len(db_manager.filter_data('status', 'SUBMITTED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Accepted Papers", str(len(db_manager.filter_data('status', 'ACCEPTED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Published Papers", str(len(db_manager.filter_data('status', 'PUBLISHED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Pulled-out Papers", str(len(db_manager.filter_data('status', 'PULLOUT', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    )
                    ])
                ])
            ], style={"margin": "0", "display": "flex", "justify-content": "space-around", "align-items": "center"})
        ], style={"padding": "2rem"}, id="text-display-container")

        main_dash = dbc.Container([
                dbc.Row([  # Row for the line and pie charts
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}),
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash1 = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='research_status_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='research_type_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash2 = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Tabs(
                        id='nonscopus_scopus_tabs', 
                        value='line', 
                        children=[
                            dcc.Tab(label='Scopus and Non-Scopus Over Time', value='line', style={"font-size": "12px"}),
                            dcc.Tab(label='Scopus vs. Non-Scopus', value='pie', style={"font-size": "12px"})
                        ], 
                        style={"font-size": "14px"}  # Adjust overall font size of tabs
                    ),
                    dcc.Loading(
                        id="loading-nonscopus-scopus",
                        type="circle",
                        children=dcc.Graph(id='nonscopus_scopus_graph')
                    )
                ], width=6, style={"height": "auto", "overflow": "hidden"}),

                dbc.Col([
                    dcc.Tabs(
                        id='proceeding_conference_tabs',
                        value='line',  # Default view is the line chart
                        children=[
                            dcc.Tab(label='Journal and Proceeding Over Time', value='line', style={"font-size": "12px"}),
                            dcc.Tab(label='Journal vs. Proceeding', value='pie', style={"font-size": "12px"})
                        ],
                        style={"font-size": "14px"}  # Adjust overall font size of tabs
                    ),
                    dcc.Loading(
                        id="loading-proceeding-conference",
                        type="circle",
                        children=dcc.Graph(id='proceeding_conference_graph')
                    )
                ], width=6, style={"height": "auto", "overflow": "hidden"})
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})


        sub_dash3 = dbc.Container([
            dbc.Row([
                dbc.Col(dcc.Graph(id='sdg_bar_plot'), width=12)  # Increase width to 12 to occupy the full space
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})

        sub_dash4 = dbc.Container([
            dbc.Row([
                dbc.Col(dcc.Graph(id='nonscopus_scopus_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"}),
                dbc.Col(dcc.Graph(id='proceeding_conference_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})
        
        sub_dash5 = dbc.Container([
            dbc.Row([
                dbc.Col(dcc.Graph(id='term_college_bar_plot'), width=12)  # Increase width to 12 to occupy the full space
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})


        self.dash_app.layout = html.Div([
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),  # 1-second refresh interval
            dcc.Store(id="shared-data-store"),  # Shared data store to hold the updated dataset
            dbc.Container([
                dbc.Row([
                    # Sidebar controls
                    dbc.Col(
                        controls,
                        width={"size": 2, "order": 1},  # Adjust width for sidebar
                        style={"height": "100%", "padding": "0", "overflow-y": "auto"}
                    ),
                    # Main dashboard content
                    dbc.Col(
                        html.Div([
                            dbc.Row(text_display, style={"flex": "1"}),  # Display text_display at the top
                            dbc.Row(
                                dcc.Loading(
                                    id="loading-main-dash",
                                    type="circle",
                                    children=main_dash
                                ), style={"flex": "2"}
                            ),
                            dbc.Row(
                                dcc.Loading(
                                    id="loading-sub-dash5",
                                    type="circle",
                                    children=sub_dash5
                                ), style={"flex": "1"}
                            ),
                            dbc.Row(
                                dcc.Loading(
                                    id="loading-sub-dash1",
                                    type="circle",
                                    children=sub_dash1
                                ), style={"flex": "1"}
                            ),
                            dbc.Row(
                                dcc.Loading(
                                    id="loading-sub-dash3",
                                    type="circle",
                                    children=sub_dash3
                                ), style={"flex": "1"}
                            ),
                            dbc.Row(
                                children=sub_dash2,
                                style={"flex": "1"}
                            ),
                            dbc.Row(
                                dcc.Loading(
                                    id="loading-sub-dash4",
                                    type="circle",
                                    children=sub_dash4
                                ), style={"flex": "1"}
                            ),
                        ], style={
                            "height": "100%",
                            "display": "flex",
                            "flex-direction": "column",
                            "overflow-x": "hidden",  # Prevent horizontal overflow
                            "overflow-y": "auto",  # Enable vertical scrolling
                            "padding": "10px",
                        }),
                        width={"size": 10, "order": 2},  # Adjust main content width
                        style={
                            "height": "100%",
                            "display": "flex",
                            "flex-direction": "column"
                        }
                    ),
                ], style={
                    "height": "100vh",
                    "display": "flex",
                    "flex-wrap": "nowrap",  # Prevent wrapping to maintain layout
                }),
            ], fluid=True, style={
                "height": "100vh",
                "margin": "0",
                "padding": "0",
            }),
        ], style={
            "height": "100vh",
            "margin": "0",
            "padding": "0",
            "overflow": "hidden",  # Prevent outer scrolling
        })

    def create_display_card(self, title, value):
        """
        Create a display card for showing metrics.
        """
        return html.Div([
            html.Div([
                html.H5(title, style={'textAlign': 'center'}),
                html.H2(value, style={'textAlign': 'center'})
            ], style={
                "border": "2px solid #0A438F",    # Border color
                "borderRadius": "10px",           # Rounded corners
                "padding": "10px",                # Padding inside the card
                "width": "170px",                 # Fixed width
                "height": "150px",                # Fixed height
                "display": "flex",
                "flexDirection": "column",
                "justifyContent": "center",
                "alignItems": "center",
                "margin": "0"
            })
        ])
    
    def get_program_colors(self, df):
        unique_programs = df['program_id'].unique()
        random_colors = px.colors.qualitative.Plotly[:len(unique_programs)]
        self.program_colors = {program: random_colors[i % len(random_colors)] for i, program in enumerate(unique_programs)}
    
    def update_line_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        if len(selected_colleges) == 1:
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = f'Number of Research Outputs for {selected_colleges[0]}'
            self.get_program_colors(grouped_df) 
        else:
            grouped_df = df.groupby(['college_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'college_id'
            title = 'Number of Research Outputs per College'

        fig_line = px.line(
            grouped_df, 
            x='year', 
            y='TitleCount', 
            color=color_column, 
            markers=True,
            color_discrete_map=self.palette_dict if len(selected_colleges) > 1 else self.program_colors
        )
        
        fig_line.update_layout(
            title=title,
            xaxis_title='Academic Year',
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            showlegend=False  
        )

        return fig_line
    
    def update_pie_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        if len(selected_colleges) == 1:
            college_name = selected_colleges[0]
            filtered_df = df[df['college_id'] == college_name]
            detail_counts = filtered_df.groupby('program_id').size()
            self.get_program_colors(filtered_df) 
            title = f'Research Output Distribution for {selected_colleges[0]}'
        else:
            detail_counts = df.groupby('college_id').size()
            title = 'Research Output Distribution by College'
        
        fig_pie = px.pie(
            names=detail_counts.index,
            values=detail_counts,
            color=detail_counts.index,
            color_discrete_map=self.palette_dict if len(selected_colleges) > 1 else self.program_colors,
            labels={'names': 'Category', 'values': 'Number of Research Outputs'},
        )

        fig_pie.update_layout(
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            title=title
        )

        return fig_pie
    
    def update_research_type_bar_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        if df.empty:
            return px.bar(title="No data available")
        
        fig = go.Figure()

        if len(selected_colleges) == 1:
            self.get_program_colors(df) 
            status_count = df.groupby(['research_type', 'program_id']).size().reset_index(name='Count')
            pivot_df = status_count.pivot(index='research_type', columns='program_id', values='Count').fillna(0)

            sorted_programs = sorted(pivot_df.columns)
            title = f"Comparison of Research Output Type Across Programs"

            for program in sorted_programs:
                fig.add_trace(go.Bar(
                    x=pivot_df.index,
                    y=pivot_df[program],
                    name=program,
                    marker_color=self.program_colors[program]
                ))
        else:
            status_count = df.groupby(['research_type', 'college_id']).size().reset_index(name='Count')
            pivot_df = status_count.pivot(index='research_type', columns='college_id', values='Count').fillna(0)
            title = 'Comparison of Research Output Type Across Colleges'
            
            for college in pivot_df.columns:
                fig.add_trace(go.Bar(
                    x=pivot_df.index,
                    y=pivot_df[college],
                    name=college,
                    marker_color=self.palette_dict.get(college, 'grey')
                ))

        fig.update_layout(
            barmode='group',
            xaxis_title='Research Type',  
            yaxis_title='Number of Research Outputs',  
            title=title
        )

        return fig

    def update_research_status_bar_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)

        if df.empty:
            return px.bar(title="No data available")

        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLOUT']

        fig = go.Figure()

        if len(selected_colleges) == 1:
            self.get_program_colors(df) 
            status_count = df.groupby(['status', 'program_id']).size().reset_index(name='Count')
            pivot_df = status_count.pivot(index='status', columns='program_id', values='Count').fillna(0)

            sorted_programs = sorted(pivot_df.columns)
            title = f"Comparison of Research Status Across Programs"

            for program in sorted_programs:
                fig.add_trace(go.Bar(
                    x=pivot_df.index,
                    y=pivot_df[program],
                    name=program,
                    marker_color=self.program_colors[program]
                ))
        else:
            status_count = df.groupby(['status', 'college_id']).size().reset_index(name='Count')
            pivot_df = status_count.pivot(index='status', columns='college_id', values='Count').fillna(0)
            title = 'Comparison of Research Output Status Across Colleges'
            
            for college in pivot_df.columns:
                fig.add_trace(go.Bar(
                    x=pivot_df.index,
                    y=pivot_df[college],
                    name=college,
                    marker_color=self.palette_dict.get(college, 'grey')
                ))

        fig.update_layout(
            barmode='group',
            xaxis_title='Research Status',  
            yaxis_title='Number of Research Outputs',  
            title=title,
            xaxis=dict(
                tickvals=status_order,  # This should match the unique statuses in pivot_df index
                ticktext=status_order    # This ensures that the order of the statuses is displayed correctly
            )
        )

        # Ensure the x-axis is sorted in the defined order
        fig.update_xaxes(categoryorder='array', categoryarray=status_order)

        return fig
    
    def create_publication_bar_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        df = df[df['scopus'] != 'N/A']

        if len(selected_colleges) == 1:
            grouped_df = df.groupby(['scopus', 'program_id']).size().reset_index(name='Count')
            x_axis = 'program_id'
            xaxis_title = 'Programs'
            title = f'Scopus vs. Non-Scopus per Program in {selected_colleges[0]}'
        else:
            grouped_df = df.groupby(['scopus', 'college_id']).size().reset_index(name='Count')
            x_axis = 'college_id'
            xaxis_title = 'Colleges'
            title = 'Scopus vs. Non-Scopus per College'
        
        fig_bar = px.bar(
            grouped_df,
            x=x_axis,
            y='Count',
            color='scopus',
            barmode='group',
            color_discrete_map=self.palette_dict,
            labels={'scopus': 'Scopus vs. Non-Scopus'}
        )
        
        fig_bar.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            height=400
        )

        return fig_bar
    
    def update_publication_format_bar_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

        if len(selected_colleges) == 1:
            grouped_df = df.groupby(['journal', 'program_id']).size().reset_index(name='Count')
            x_axis = 'program_id'
            xaxis_title = 'Programs'
            title = f'Publication Formats per Program in {selected_colleges[0]}'
        else:
            grouped_df = df.groupby(['journal', 'college_id']).size().reset_index(name='Count')
            x_axis = 'college_id'
            xaxis_title = 'Colleges'
            title = 'Publication Formats per College'

        fig_bar = px.bar(
            grouped_df,
            x=x_axis,
            y='Count',
            color='journal',
            barmode='group',
            color_discrete_map=self.palette_dict,
            labels={'journal': 'Publication Format'}
        )
        
        fig_bar.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            height=400
        )

        return fig_bar


    def update_sdg_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)

        if df.empty:
            return px.scatter(title="No data available")

        df_copy = df.copy()

        if len(selected_colleges) == 1:
            self.get_program_colors(df)
            df_copy = df_copy.set_index('program_id')['sdg'].str.split(';').apply(pd.Series).stack().reset_index(name='sdg')
            df_copy['sdg'] = df_copy['sdg'].str.strip()
            df_copy = df_copy.drop(columns=['level_1'])
            sdg_count = df_copy.groupby(['sdg', 'program_id']).size().reset_index(name='Count')
            title = f'Distribution of SDG-Targeted Research Across Programs in {selected_colleges[0]}'

            if sdg_count.empty:
                print("Data is empty after processing")
                return px.scatter(title="No data available")

            fig = go.Figure()

            for program in sdg_count['program_id'].unique():
                program_data = sdg_count[sdg_count['program_id'] == program]
                fig.add_trace(go.Scatter(
                    x=program_data['sdg'],
                    y=program_data['program_id'],
                    mode='markers',
                    marker=dict(
                        size=program_data['Count'],
                        color=self.program_colors.get(program, 'grey'),
                        sizemode='area',
                        sizeref=2. * max(sdg_count['Count']) / (100**2),  # Bubble size scaling
                        sizemin=4
                    ),
                    name=program
                ))
        else:
            df_copy = df_copy.set_index('college_id')['sdg'].str.split(';').apply(pd.Series).stack().reset_index(name='sdg')
            df_copy['sdg'] = df_copy['sdg'].str.strip()
            df_copy = df_copy.drop(columns=['level_1'])
            sdg_count = df_copy.groupby(['sdg', 'college_id']).size().reset_index(name='Count')
            title = 'Distribution of SDG-Targeted Research Across Colleges'

            if sdg_count.empty:
                print("Data is empty after processing")
                return px.scatter(title="No data available")

            fig = go.Figure()

            for college in sdg_count['college_id'].unique():
                college_data = sdg_count[sdg_count['college_id'] == college]
                fig.add_trace(go.Scatter(
                    x=college_data['sdg'],
                    y=college_data['college_id'],
                    mode='markers',
                    marker=dict(
                        size=college_data['Count'],
                        color=self.palette_dict.get(college, 'grey'),
                        sizemode='area',
                        sizeref=2. * max(sdg_count['Count']) / (100**2),  # Bubble size scaling
                        sizemin=4
                    ),
                    name=college
                ))

        fig.update_layout(
            xaxis_title='SDG Targeted',
            yaxis_title='Programs or Colleges',
            title=title,
            xaxis=dict(
                tickvals=self.all_sdgs,
                ticktext=self.all_sdgs
            ),
            yaxis=dict(autorange="reversed"),
            showlegend=True
        )

        return fig
    
    def scopus_line_graph(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        # Filter out rows where 'scopus' is 'N/A'
        df = df[df['scopus'] != 'N/A']

        # Group data by 'scopus' and 'year'
        grouped_df = df.groupby(['scopus', 'year']).size().reset_index(name='Count')

        # Ensure year and count are numeric
        grouped_df['year'] = grouped_df['year'].astype(int)
        grouped_df['Count'] = grouped_df['Count'].astype(int)

        # Debug: Print the grouped data
        print(grouped_df)

        # Create the line chart with markers
        fig_line = px.line(
            grouped_df,
            x='year',
            y='Count',
            color='scopus',
            color_discrete_map=self.palette_dict,
            labels={'scopus': 'Scopus vs. Non-Scopus'},
            markers=True  # Ensure points are visible even if no lines
        )

        # Update layout for the figure
        fig_line.update_layout(
            title='Scopus vs. Non-Scopus Publications Over Time',
            xaxis_title='Academic Year',
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            height=400,
            xaxis=dict(
                type='linear',  # Treat x-axis as continuous
                tickformat="%d",  # Display years as integers
                tickangle=-45  # Make labels diagonal
            )
        )

        return fig_line
    
    def scopus_pie_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        # Filter out rows where 'scopus' is 'N/A'
        df = df[df['scopus'] != 'N/A']

        # Group data by 'scopus' and sum the counts
        grouped_df = df.groupby(['scopus']).size().reset_index(name='Count')

        # Debug: Print the grouped data
        print(grouped_df)

        # Create the pie chart
        fig_pie = px.pie(
            grouped_df,
            names='scopus',
            values='Count',
            color='scopus',
            color_discrete_map=self.palette_dict,
            labels={'scopus': 'Scopus vs. Non-Scopus'}
        )

        # Update layout for the figure
        fig_pie.update_layout(
            title='Scopus vs. Non-Scopus Research Distribution',
            template='plotly_white',
            height=400
        )

        return fig_pie



    def publication_format_line_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        # Filter out rows with 'unpublished' journals and 'PULLOUT' status
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

        # Group data by 'journal' and 'year'
        grouped_df = df.groupby(['journal', 'year']).size().reset_index(name='Count')

        # Ensure year and count are numeric
        grouped_df['year'] = grouped_df['year'].astype(int)
        grouped_df['Count'] = grouped_df['Count'].astype(int)

        # Debug: Print the grouped data
        print(grouped_df)

        # Create the line chart with markers
        fig_line = px.line(
            grouped_df,
            x='year',
            y='Count',
            color='journal',
            color_discrete_map=self.palette_dict,
            labels={'journal': 'Publication Format'},
            markers=True  # Ensure points are visible even if no lines
        )

        # Update layout for the figure
        fig_line.update_layout(
            title='Publication Formats Over Time',
            xaxis_title='Academic Year',
            yaxis_title='Number of Research Outputs',
            template='plotly_white',
            height=400,
            xaxis=dict(
                type='linear',  # Treat x-axis as continuous
                tickformat="%d",  # Display years as integers
                tickangle=-45  # Make labels diagonal
            )
        )

        return fig_line
    
    def publication_format_pie_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)
        
        # Filter out rows with 'unpublished' journals and 'PULLOUT' status
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

        # Group data by 'journal' and sum the counts
        grouped_df = df.groupby(['journal']).size().reset_index(name='Count')

        # Debug: Print the grouped data
        print(grouped_df)

        # Create the pie chart
        fig_pie = px.pie(
            grouped_df,
            names='journal',
            values='Count',
            color='journal',
            color_discrete_map=self.palette_dict,
            labels={'journal': 'Publication Format'}
        )

        # Update layout for the figure
        fig_pie.update_layout(
            title='Publication Format Distribution',
            template='plotly_white',
            height=400
        )

        return fig_pie

    def update_research_outputs_by_year_and_term(self, selected_colleges, selected_status, selected_years, selected_terms):
            
        df = db_manager.get_filtered_data_with_term(selected_colleges, selected_status, selected_years, selected_terms)

        if df.empty:
            return px.bar(title="No data available")

        if len(selected_colleges) == 1:
            # Group by year, program_id, and term for a single college
            self.get_program_colors(df) 
            grouped_df = df.groupby(['year', 'program_id', 'term']).size().reset_index(name='Count')
            x_axis = 'year'
            color_axis = 'program_id'
            xaxis_title = 'Year'
            yaxis_title = 'Number of Research Outputs'
            title = f'Number of Research Outputs by Programs in {selected_colleges[0]} and Year for Each Academic Term' 
            color_label = 'Program'
        else:
            # Group by year, college_id, and term for multiple colleges
            grouped_df = df.groupby(['year', 'college_id', 'term']).size().reset_index(name='Count')
            x_axis = 'year'
            color_axis = 'college_id'
            xaxis_title = 'Year'
            yaxis_title = 'Number of Research Outputs'
            title = 'Number of Research Outputs by College and Year for Each Academic Term'
            color_label = 'College'

        # Create the bar chart with stacking enabled and facets for each term
        fig_bar = px.bar(
            grouped_df,
            x=x_axis,
            y='Count',
            color=color_axis,
            barmode='stack',  # Stack bars for the same year
            color_discrete_map=self.palette_dict if len(selected_colleges) > 1 else self.program_colors,
            facet_col='term',  # Facet by term (1, 2, 3)
            labels={x_axis: xaxis_title, 'Count': yaxis_title, color_axis: color_label}
        )

        # Update the layout of the chart
        fig_bar.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title=yaxis_title,
            template='plotly_white',
            height=400,
            xaxis=dict(
                type='linear',  # Treat x-axis as continuous
                tickformat="%d"  # Display years as integers
            )
        )

        return fig_bar


    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """

        # Callback for reset button
        @self.dash_app.callback(
            [Output('college', 'value'),
            Output('status', 'value'),
            Output('terms', 'value'),
            Output('years', 'value')],
            [Input('reset_button', 'n_clicks')],
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')]

        @self.dash_app.callback(
            Output('college_line_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_lineplot(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_line_plot(selected_colleges, selected_status, selected_years, selected_terms)

        @self.dash_app.callback(
            Output('college_pie_chart', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_piechart(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_pie_chart(selected_colleges, selected_status, selected_years, selected_terms)

        @self.dash_app.callback(
            Output('research_type_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_research_type_bar_plot(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_research_type_bar_plot(selected_colleges, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('research_status_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_research_status_bar_plot(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_research_status_bar_plot(selected_colleges, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('nonscopus_scopus_bar_plot', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('terms', 'value')]
        )
        def create_publication_bar_chart(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.create_publication_bar_chart(selected_colleges, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('proceeding_conference_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_publication_format_bar_plot(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_publication_format_bar_plot(selected_colleges, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('sdg_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_sdg_chart(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_sdg_chart(selected_colleges, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_shared_data_store(n_intervals):
            updated_data = db_manager.get_all_data()
            return updated_data.to_dict('records')
        
        #"""
        @self.dash_app.callback(
            Output('text-display-container', 'children'),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_text_display(n_intervals):
            return dbc.Container([
                    dbc.Row([
                        dbc.Col(
                        self.create_display_card("Total Research Papers", str(len(db_manager.get_all_data()))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Ready for Publication", str(len(db_manager.filter_data('status', 'READY', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Submitted Papers", str(len(db_manager.filter_data('status', 'SUBMITTED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Accepted Papers", str(len(db_manager.filter_data('status', 'ACCEPTED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Published Papers", str(len(db_manager.filter_data('status', 'PUBLISHED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Pulled-out Papers", str(len(db_manager.filter_data('status', 'PULLOUT', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    )
                    ])
                ])
        #"""

        """
        @self.dash_app.callback(
            Output('nonscopus_scopus_line_graph', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def scopus_line_graph(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.scopus_line_graph(selected_colleges, selected_status, selected_years, selected_terms)
        """
        
        @self.dash_app.callback(
            Output('nonscopus_scopus_graph', 'figure'),
            [
                Input('nonscopus_scopus_tabs', 'value'),
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_scopus_graph(tab, selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            if tab == 'line':
                return self.scopus_line_graph(selected_colleges, selected_status, selected_years, selected_terms)
            else:
                return self.scopus_pie_chart(selected_colleges, selected_status, selected_years, selected_terms)

        """
        @self.dash_app.callback(
            Output('proceeding_conference_line_graph', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def publication_format_line_plot(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.publication_format_line_plot(selected_colleges, selected_status, selected_years, selected_terms)
        """
        
        @self.dash_app.callback(
            Output('proceeding_conference_graph', 'figure'),
            [
                Input('proceeding_conference_tabs', 'value'),
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_proceeding_conference_graph(tab, selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)

            if tab == 'line':
                return self.publication_format_line_plot(selected_colleges, selected_status, selected_years, selected_terms)
            else:
                return self.publication_format_pie_chart(selected_colleges, selected_status, selected_years, selected_terms)
        
        @self.dash_app.callback(
            Output('term_college_bar_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('terms', 'value')
            ]
        )
        def update_research_outputs_by_year_and_term(selected_colleges, selected_status, selected_years, selected_terms):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            selected_terms = default_if_empty(selected_terms, self.default_terms)
            return self.update_research_outputs_by_year_and_term(selected_colleges, selected_status, selected_years, selected_terms)