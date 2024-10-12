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

class MainDashboard:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/dashboard/overview/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.palette_dict = {
            'MITL': 'red',
            'ETYCB': 'yellow',
            'CCIS': 'green',
            'CAS': 'blue',
            'CHS': 'orange'
        }
        self.create_layout()
        self.set_callbacks()

    def create_layout(self):
        """
        Create the layout of the dashboard.
        """

        college = html.Div(
            [
                dbc.Label("Select College:"),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=db_manager.get_unique_values('college_id'),
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        status = html.Div(
            [
                dbc.Label("Select Status:"),
                dbc.Checklist(
                    id="status",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('status')],
                    value=db_manager.get_unique_values('status'),
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        slider = html.Div(
            [
                dbc.Label("Select Years"),
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

        controls = dbc.Card(
            [
                html.H4("Filters", style={"margin": "10px 0px"}),
                college, status, slider, button
            ],
            body=True,
            style={"height": "95vh", "display": "flex", "flexDirection": "column"}
        )

        text_display = dbc.Container([
            dbc.Row([
                dbc.Col(
                    self.create_display_card("Total Research Papers", str(len(db_manager.get_all_data()))),
                    width=3
                ),
                dbc.Col(
                    self.create_display_card("Published Papers", str(len(db_manager.filter_data('status', 'PUBLISHED', invert=False)))),
                    width=3
                ),
                dbc.Col(
                    self.create_display_card("Accepted Papers", str(len(db_manager.filter_data('status', 'ACCEPTED', invert=False)))),
                    width=3
                ),
                dbc.Col(
                    self.create_display_card("Newly Submitted Papers", str(len(db_manager.filter_data('status', 'SUBMITTED', invert=False)))),
                    width=3
                )
            ])
        ], style={"transform": "scale(0.9)", "transform-origin": "0 0"})

        main_dash = dbc.Container([
                dbc.Row([  # Row for the line and pie charts
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}),
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(0.9)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='research_status_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='research_type_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(0.9)", "transform-origin": "0 0"})  # Adjust the scale as needed

        self.dash_app.layout = html.Div([
                dbc.Container(
                    [
                        dbc.Row([
                            dbc.Col([
                                text_display,
                                main_dash,
                                sub_dash
                            ], width=10,style={"transform": "scale(0.9)", "transform-origin": "0 0"}),
                            dbc.Col(controls, width=2)
                        ])
                    ],
                    fluid=True,
                    className="dbc dbc-ag-grid",
                    style={"overflow": "hidden"}
                )
            ], style={"padding": "20px"})

    def create_display_card(self, title, value):
        """
        Create a display card for showing metrics.
        """
        return html.Div([
            dbc.Col(html.Div([
                html.H5(title, style={'textAlign': 'center'}),
                html.H2(value, style={'textAlign': 'center'})
            ], style={
                            "border": "1px solid #007bff",  # Change color as needed
                            "borderRadius": "10px",          # Adjust the roundness
                            "padding": "10px",               # Add some padding inside the card
                            "margin": "5px"                  # Space between columns
                        }))
        ])
    
    def get_program_colors(self, df):
        unique_programs = df['program_id'].unique()
        random_colors = px.colors.qualitative.Plotly[:len(unique_programs)]
        self.program_colors = {program: random_colors[i % len(random_colors)] for i, program in enumerate(unique_programs)}
    
    def update_line_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
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
            yaxis_title='Number of Publications',
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            showlegend=False  
        )

        return fig_line
    
    def update_pie_chart(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if len(selected_colleges) == 1:
            college_name = selected_colleges[0]
            filtered_df = df[df['college_id'] == college_name]
            detail_counts = filtered_df.groupby('program_id').size()
            self.get_program_colors(filtered_df) 
        else:
            detail_counts = df.groupby('college_id').size()
        
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
            height=400
        )

        return fig_pie
    
    """
    def update_publication_format_bar_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if len(selected_colleges) == 1:
            grouped_df = df.groupby(['journal', 'program_id']).size().reset_index(name='Count')
            x_axis = 'program_id'
            xaxis_title = 'Programs'
            title = f'Publication Formats per Programs in {selected_colleges[0]}'
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
            color_discrete_map=self.palette_dict
        )
        
        fig_bar.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='Number of Publications',
            template='plotly_white',
            height=400
        )

        return fig_bar
    """
    
    def update_research_type_bar_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
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

    def update_research_status_bar_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)

        if df.empty:
            return px.bar(title="No data available")

        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED']

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


    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """
        
        @self.dash_app.callback(
        [Output('college', 'value'),
         Output('status', 'value'),
         Output('years', 'value')],
        [Input('reset_button', 'n_clicks')],
        prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return db_manager.get_unique_values('college_id'), db_manager.get_unique_values('status'), [db_manager.get_min_value('year'), db_manager.get_max_value('year')]

        @self.dash_app.callback(
            Output('college_line_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value')
            ]
        )
        def update_lineplot(selected_colleges, selected_status, selected_years):
            return self.update_line_plot(selected_colleges, selected_status, selected_years)

        @self.dash_app.callback(
            Output('college_pie_chart', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value')
            ]
        )
        def update_piechart(selected_colleges, selected_status, selected_years):
            return self.update_pie_chart(selected_colleges, selected_status, selected_years)

        @self.dash_app.callback(
            Output('research_type_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value')
            ]
        )
        def update_research_type_bar_plot(selected_colleges, selected_status, selected_years):
            return self.update_research_type_bar_plot(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('research_status_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value')
            ]
        )
        def update_research_status_bar_plot(selected_colleges, selected_status, selected_years):
            return self.update_research_status_bar_plot(selected_colleges, selected_status, selected_years)