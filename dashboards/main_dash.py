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

        self.all_sdgs = [
            'SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 
            'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 
            'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17'
        ]

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
                    options=[{'label': value, 'value': value} for value in sorted(
                        db_manager.get_unique_values('status'), key=lambda x: (x != 'READY', x != 'PULLOUT', x)
                    )],
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
                    self.create_display_card("Research Papers", str(len(db_manager.get_all_data()))),
                    width=2,
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "height": "150px"}
                ),
                dbc.Col(
                    self.create_display_card("For Publication", str(len(db_manager.filter_data('status', 'READY', invert=False)))),
                    width=2,
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "height": "150px"}
                ),
                dbc.Col(
                    self.create_display_card("Submitted Papers", str(len(db_manager.filter_data('status', 'SUBMITTED', invert=False)))),
                    width=2,
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "height": "150px"}
                ),
                dbc.Col(
                    self.create_display_card("Accepted Papers", str(len(db_manager.filter_data('status', 'ACCEPTED', invert=False)))),
                    width=2,
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "height": "150px"}
                ),
                dbc.Col(
                    self.create_display_card("Published Papers", str(len(db_manager.filter_data('status', 'PUBLISHED', invert=False)))),
                    width=2,
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "height": "150px"}
                ),
                dbc.Col(
                    self.create_display_card("Pullout Papers", str(len(db_manager.filter_data('status', 'PULLOUT', invert=False)))),
                    width=2,
                    style={"display": "flex", "justify-content": "center", "align-items": "center", "height": "150px"}
                ) 
            ], justify="center")
        ], style={"transform": "scale(1)", "transform-origin": "0 0"})

        main_dash = dbc.Container([
                dbc.Row([  # Row for the line and pie charts
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}),
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash1 = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='research_status_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='research_type_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash2 = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='nonscopus_scopus_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='proceeding_conference_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash3 = dbc.Container([
            dbc.Row([
                dbc.Col(dcc.Graph(id='sdg_bar_plot'), width=12)  # Increase width to 12 to occupy the full space
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})

        """
        # Add the DataTable
        data_table_section = dbc.Container([
            dbc.Row([
                dbc.Col(
                    dash_table.DataTable(
                        id='data_table',
                        columns=[{"name": col, "id": col} for col in db_manager.get_all_data().columns],
                        data=db_manager.get_all_data().to_dict('records'),
                        style_table={'height': '400px', 'overflowY': 'auto'},
                        style_cell={'textAlign': 'left'},
                        page_size=10,
                    ),
                    width=12
                )
            ], style={"margin": "10px"})
        ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px", "transform": "scale(1)", "transform-origin": "0 0"})
        """

        self.dash_app.layout = html.Div([
                dbc.Container(
                    [
                        dbc.Row([
                            dbc.Col([
                                text_display,
                                main_dash,
                                sub_dash1,
                                sub_dash3,
                                sub_dash2
                                #data_table_section  # Add the table section below the sub_dash sections
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
    
    def create_publication_bar_chart(self, selected_colleges, selected_status, selected_years):  # Modified by Nicole Cabansag
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        df = df[df['scopus'] != 'N/A']

        if len(selected_colleges) == 1:
            grouped_df = df.groupby(['scopus', 'program_id']).size().reset_index(name='Count')
            x_axis = 'program_id'
            xaxis_title = 'Programs'
            title = f'Scopus vs. Non-Scopus per Programs in {selected_colleges[0]}'
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
            yaxis_title='Number of Publications',
            template='plotly_white',
            height=400
        )

        return fig_bar
    
    def update_publication_format_bar_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

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
            color_discrete_map=self.palette_dict,
            labels={'journal': 'Publication Format'}
        )
        
        fig_bar.update_layout(
            title=title,
            xaxis_title=xaxis_title,
            yaxis_title='Number of Publications',
            template='plotly_white',
            height=400
        )

        return fig_bar


    def update_sdg_chart(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:
            return px.bar(title="No data available")

        df_copy = df.copy()

        if len(selected_colleges) == 1:
            self.get_program_colors(df)
            df_copy = df_copy.set_index('program_id')['sdg'].str.split(';').apply(pd.Series).stack().reset_index(name='sdg')
            df_copy['sdg'] = df_copy['sdg'].str.strip()
            df_copy = df_copy.drop(columns=['level_1'])
            sdg_count = df_copy.groupby(['sdg', 'program_id']).size().reset_index(name='Count')
            pivot_df = sdg_count.pivot(index='sdg', columns='program_id', values='Count').reindex(self.all_sdgs).fillna(0)
            pivot_df['Total'] = pivot_df.sum(axis=1)
            pivot_df = pivot_df.sort_values(by='Total', ascending=False).drop(columns='Total')
            pivot_df = pivot_df.reindex(self.all_sdgs)

            sorted_programs = sorted(pivot_df.columns)  # Sort programs alphabetically
            pivot_df = pivot_df[sorted_programs]  # Reorder the columns in pivot_df by the sorted program list
            title = f'Programs in {selected_colleges} Targeting Each SDG'

            if pivot_df.empty:
                print("Pivot DataFrame is empty after processing")
                return px.bar(title="No data available")

            fig = go.Figure()

            for program in sorted_programs:
                fig.add_trace(go.Bar(
                    y=pivot_df.index,
                    x=pivot_df[program],
                    name=program,
                    orientation='h',
                    marker_color=self.program_colors[program]
                ))
        else:
            df_copy = df_copy.set_index('college_id')['sdg'].str.split(';').apply(pd.Series).stack().reset_index(name='sdg')
            df_copy['sdg'] = df_copy['sdg'].str.strip()
            df_copy = df_copy.drop(columns=['level_1'])
            sdg_count = df_copy.groupby(['sdg', 'college_id']).size().reset_index(name='Count')
            pivot_df = sdg_count.pivot(index='sdg', columns='college_id', values='Count').reindex(self.all_sdgs).fillna(0)
            pivot_df['Total'] = pivot_df.sum(axis=1)
            pivot_df = pivot_df.sort_values(by='Total', ascending=False).drop(columns='Total')
            pivot_df = pivot_df.reindex(self.all_sdgs)

            title = 'Colleges Targeting Each SDG'

            if pivot_df.empty:
                print("Pivot DataFrame is empty after processing")
                return px.bar(title="No data available")

            fig = go.Figure()

            for college in pivot_df.columns:
                fig.add_trace(go.Bar(
                    y=pivot_df.index,
                    x=pivot_df[college],
                    name=college,
                    orientation='h',
                    marker_color=self.palette_dict.get(college, 'grey')
                ))

        fig.update_layout(
            barmode='stack',
            xaxis_title='Count',
            yaxis_title='SDG Targeted',
            title=title,
            yaxis=dict(
                autorange='reversed',
                tickvals=self.all_sdgs,
                ticktext=self.all_sdgs
            )
        )
        
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
        
        @self.dash_app.callback(
            Output('nonscopus_scopus_bar_plot', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value')]
        )
        def create_publication_bar_chart(selected_colleges, selected_status, selected_years):
            return self.create_publication_bar_chart(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('proceeding_conference_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value')
            ]
        )
        def update_publication_format_bar_plot(selected_colleges, selected_status, selected_years):
            return self.update_publication_format_bar_plot(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('sdg_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value')
            ]
        )
        def update_sdg_chart(selected_colleges, selected_status, selected_years):
            return self.update_sdg_chart(selected_colleges, selected_status, selected_years)