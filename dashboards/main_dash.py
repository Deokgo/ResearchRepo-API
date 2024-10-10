# created by Jelly Mallari
# continued by Nicole Cabansag

import dash
from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px

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
                    self.create_display_card("Published Papers", str(len(db_manager.filter_data_by_list('status', ['PUBLISHED', 'INDEXED'], invert=False)))),
                    width=3
                ),
                dbc.Col(
                    self.create_display_card("Ongoing Papers", str(len(db_manager.filter_data_by_list('status', ['PUBLISHED', 'INDEXED', 'UPLOADED'], invert=True)))),
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
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=8, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=4, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #007bff", "borderRadius": "5px","transform": "scale(0.9)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='publication_format_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='research_status_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
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
                ),
                dash_table.DataTable(
                    id='research-table',
                    columns=[],  # Columns will be populated by callback
                    data=[],  # Data will be populated by callback
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left'},
                    page_size=30  # Set page size for better UX
                ),
                dcc.Interval(
                    id='interval-component',
                    interval=60 * 1000,  # Update every 1 minute (optional)
                    n_intervals=0
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
    
    def update_line_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if len(selected_colleges) == 1:
            grouped_df = df.groupby(['program_name', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_name'
            title = f'Number of Publications for {selected_colleges[0]}'
        else:
            grouped_df = df.groupby(['college_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'college_id'
            title = 'Number of Publications per College'

        fig_line = px.line(
            grouped_df, 
            x='year', 
            y='TitleCount', 
            color=color_column, 
            markers=True,
            color_discrete_map=self.palette_dict
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
            detail_counts = filtered_df.groupby('program_name').size()
            title = f'Number of Publications for {college_name}'
        else:
            detail_counts = df.groupby('college_id').size()
            title = ''
        
        fig_pie = px.pie(
            names=detail_counts.index,
            values=detail_counts,
            color=detail_counts.index,
            color_discrete_map=self.palette_dict,
            labels={'names': 'Category', 'values': 'Number of Publications'},
        )

        fig_pie.update_layout(
            title=title,
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400
        )

        return fig_pie
    
    def update_table(n):
        df = db_manager.get_all_data()

        data = df.to_dict('records')  
        columns = [{'name': col, 'id': col} for col in df.columns]  

        return data, columns
    
    def update_publication_format_bar_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        grouped_df = df.groupby(['journal', 'college_id']).size().reset_index(name='Count')
        
        fig_bar = px.bar(
            grouped_df,
            x='college_id',
            y='Count',
            color='journal',
            barmode='group',
            color_discrete_map=self.palette_dict
        )
        
        fig_bar.update_layout(
            title="Publication Formats per College",
            xaxis_title='College',
            yaxis_title='Number of Publications',
            template='plotly_white',
            height=400
        )

        return fig_bar
    
    def update_research_status_bar_plot(self, selected_colleges, selected_status, selected_years):
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:
            return px.bar(title="No data available")

        status_mapping = {
            'PUBLISHED': 'PUBLISHED',
            'SUBMITTED': 'SUBMITTED',
            'UPLOADED': 'UPLOADED'
        }

        df['grouped_status'] = df['status'].apply(lambda x: status_mapping.get(x, 'ON-GOING'))

        status_count = df.groupby(['grouped_status', 'college_id']).size().reset_index(name='Count')

        pivot_df = status_count.pivot(index='grouped_status', columns='college_id', values='Count').fillna(0)

        desired_statuses = ['PUBLISHED', 'ON-GOING', 'SUBMITTED', 'UPLOADED']
        pivot_df = pivot_df.reindex(desired_statuses).fillna(0)

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
            xaxis_title='Number of Research Outputs',
            yaxis_title='Research Status',
            title='Colleges Research Status',
            yaxis=dict(
                autorange='reversed',  
                tickvals=desired_statuses,  
                ticktext=desired_statuses  
            )
        )
        
        return fig

    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """

        #reset filters when the reset button is clicked
        @self.dash_app.callback(
            [
                Output('college', 'value'),
                Output('status', 'value'),
                Output('years', 'value')
            ],
            [Input('reset_button', 'n_clicks')],
            [
                State('college', 'options'),
                State('status', 'options'),
                State('years', 'min'),
                State('years', 'max')
            ]
        )
        def reset_filters(n_clicks, college_options, status_options, years_min, years_max):
            if n_clicks:
                #reset the values of all filters
                all_colleges = [option['value'] for option in college_options]
                all_statuses = [option['value'] for option in status_options]
                return all_colleges, all_statuses, [years_min, years_max]
            #default return when the page first loads
            return dash.no_update, dash.no_update, dash.no_update

        @self.dash_app.callback(
            [Output('research-table', 'data'), Output('research-table', 'columns')],
            [Input('interval-component', 'n_intervals')]
        )
        def update_table_callback(n):
            return self.update_table()

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
            Output('publication_format_bar_plot', 'figure'),
            [
                Input('college', 'value'), 
                Input('status', 'value'), 
                Input('years', 'value')
            ]
        )
        def update_publication_format_bar_plot(selected_colleges, selected_status, selected_years):
            return self.update_publication_format_bar_plot(selected_colleges, selected_status, selected_years)
        
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