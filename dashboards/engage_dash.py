# created by Jelly Mallari
# continued by Nicole Cabansag (for other charts and added reset_button function)

import dash
from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from datetime import datetime, timedelta
from . import view_manager
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

class Engage_Dash:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/engage/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP])

        self.palette_dict = {
            'CAS':'#141cff', 
            'CCIS':'#04a417', 
            'CHS':'#c2c2c2', 
            'MITL':'#bb0c0c',
            'ETYCB':'#e9e107'}
        
        # Get default values
        self.default_colleges = view_manager.get_unique_values('college_id')
        self.default_statuses = view_manager.get_unique_values('status')
        self.default_years = [view_manager.get_min_value('year'), view_manager.get_max_value('year')]
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
                dbc.Label("Select College:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in view_manager.get_unique_values('college_id')],
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
                        view_manager.get_unique_values('status'), key=lambda x: (x != 'READY', x != 'PULLOUT', x)
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
                    min=view_manager.get_min_value('year'), 
                    max=view_manager.get_max_value('year'), 
                    step=1, 
                    id="years",
                    marks=None,
                    tooltip={"placement": "bottom", "always_visible": True},
                    value=[view_manager.get_min_value('year'), view_manager.get_max_value('year')],
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
                    college,
                    status,
                    slider,
                    button,
                ],
                body=True,
                style={
                    "background": "#d3d8db",
                    "height": "100vh",  # Full-height sidebar
                    "position": "sticky",  # Sticky position instead of fixed
                    "top": 0,
                    "padding": "20px",
                    "border-radius": "0",  # Remove rounded corners
                },
            )
        )

        text_display = dbc.Container([
            dbc.Row([
                dbc.Container([
                    dbc.Row([
                        dbc.Col(
                        self.create_display_card("Total Research Papers", str(len(view_manager.get_all_data()))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Intended for Publication", str(len(view_manager.filter_data('status', 'READY', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Submitted Papers", str(len(view_manager.filter_data('status', 'SUBMITTED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Accepted Papers", str(len(view_manager.filter_data('status', 'ACCEPTED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Published Papers", str(len(view_manager.filter_data('status', 'PUBLISHED', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Pulled-out Papers", str(len(view_manager.filter_data('status', 'PULLOUT', invert=False)))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    )
                    ])
                ])
            ], style={"margin": "0", "display": "flex", "justify-content": "space-around", "align-items": "center"})
        ], style={"padding": "2rem"}, id="text-display-container")

        main_dash = dbc.Container([
                dbc.Row([  # Row for the line and pie charts
                    dbc.Col(dcc.Graph(id='college_line_plot'), width=11, style={"height": "auto", "overflow": "hidden", "paddingTop": "20px"}),
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash4 = dbc.Container([
                dbc.Row([
                    dbc.Col(dcc.Graph(id='college_pie_chart'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='nonscopus_scopus_line_graph'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed

        sub_dash2 = dbc.Container([ 
                dbc.Row([
                    dbc.Col(dcc.Graph(id='proceeding_conference_line_graph'), width=6, style={"height": "auto", "overflow": "hidden"}),
                    dbc.Col(dcc.Graph(id='proceeding_conference_bar_plot'), width=6, style={"height": "auto", "overflow": "hidden"})
                ], style={"margin": "10px"})
            ], fluid=True, style={"border": "2px solid #FFFFFF", "borderRadius": "5px","transform": "scale(1)", "transform-origin": "0 0"})  # Adjust the scale as needed
        
        self.dash_app.layout = html.Div([
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),  # 1 second
            dcc.Store(id="shared-data-store"),  # Shared data store to hold the updated dataset
            dbc.Container([
                dbc.Row([
                    dbc.Col(controls, width=2, style={"height": "100%"}),  # Controls on the side
                    dbc.Col(
                        html.Div([  # Wrapper div for horizontal scrolling
                            dbc.Label("Select Date Range:", style={"color": "#08397C"}),
                            dcc.Dropdown(
                                id='date-range-dropdown',
                                options=[
                                    {'label': 'Last 7 Days', 'value': '7D'},
                                    {'label': 'Last 2 Weeks', 'value': '14D'},
                                    {'label': 'Last Month', 'value': '1M'},
                                    {'label': 'Last 6 Months', 'value': '6M'}
                                ],
                                value='7D',
                                placeholder='Select a date range'
                            ),
                            dbc.Row(text_display, style={"flex": "1"}),  # Display `text_display` at the top
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
                                    children=sub_dash4
                                ), style={"flex": "1"}
                            ),  
                            dbc.Row(
                                dcc.Loading(
                                    id="loading-sub-dash2",
                                    type="circle",
                                    children=sub_dash2
                                ), style={"flex": "1"}
                            ), 
                        ], style={
                            "height": "90%",  # Reduced content area height
                            "display": "flex",
                            "flex-direction": "column",
                            "overflow-x": "auto",  # Allow horizontal scrolling for the entire content
                            "flex-grow": "1",  # Ensure content area grows to fill available space
                            "margin": "0",
                            "padding": "3px",
                        })
                    , style={
                        "height": "100%",  # Ensure wrapper takes full height
                        "display": "flex",
                        "flex-direction": "column"
                    }),
                ], style={"height": "100%", "display": "flex"}),
            ], fluid=True, className="dbc dbc-ag-grid", style={
                "height": "80vh",  # Reduced viewport height
                "margin": "0", 
                "padding": "0",
            })
        ], style={
            "height": "90vh",  # Reduced overall height
            "margin": "0",
            "padding": "0",
            "overflow-x": "hidden",  # No scrolling for outermost div
            "overflow-y": "hidden",  # No vertical scrolling for outermost div
        })


    def create_display_card(self, title, value):
        """
        Create a display card for showing metrics.
        """
        return html.Div([
            html.Div([
                html.H5(title, style={'textAlign': 'center', 'font-size': '14px' if len(title) > 20 else '16px'}),
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
    
    def update_line_plot(self, selected_colleges, selected_status, selected_years, start_date, end_date):
        # Get filtered data
        df = view_manager.get_filtered_data(selected_colleges, selected_status, selected_years)

        if df.empty:
            print("Debug: Filtered DataFrame is empty.")
            return go.Figure()

        # Convert 'date' column to datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if df['date'].isnull().any():
            print("Debug: Some dates could not be converted.")
        
        # Group by 'date' and calculate the sum
        df = df.groupby('date').agg({'total_views': 'sum',
                                    'total_unique_views': 'sum',
                                    'total_downloads': 'sum'}).reset_index()

        # Generate a full date range for reindexing
        full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df = df.set_index('date').reindex(full_date_range).reset_index()
        df.columns = ['date', 'total_views', 'total_unique_views', 'total_downloads']

        # Fill missing values with 0
        df = df.fillna(0)

        print("Debug: Data after reindexing and filling missing values:", df.head())

        # Transform data for Plotly
        df_melted = df.melt(id_vars=['date'], 
                            value_vars=['total_views', 'total_unique_views', 'total_downloads'], 
                            var_name='Metric', 
                            value_name='Count')

        # Create the line chart using Plotly
        fig = px.line(df_melted, 
                    x='date', 
                    y='Count', 
                    color='Metric', 
                    title='Views and Downloads Over Time',
                    labels={'date': 'Date', 'Count': 'Count', 'Metric': 'Metric'},
                    markers=True)

        return fig
    
    def top_10_research_ids(self, selected_colleges, selected_status, selected_years, start_date, end_date):
        # Get filtered data
        df = view_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:
            print("Debug: Filtered DataFrame is empty.")
            return go.Figure()
        
        # Convert 'date' column to datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        if df['date'].isnull().any():
            print("Debug: Some dates could not be converted.")
        
        # Filter date range
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        # Aggregate views by Research ID
        research_views = df.groupby('research_id')['total_unique_views'].sum().reset_index()
        
        # Get top 10 Research IDs by view count, sorting in descending order
        top_10_research_ids = research_views.sort_values(by='total_unique_views', ascending=True).head(10)
        
        print("Debug: Top 10 Research IDs by view count:", top_10_research_ids)
        
        # Create the vertical bar chart
        fig = px.bar(
            top_10_research_ids,
            x='total_unique_views',
            y='research_id',
            orientation='h',  # Horizontal orientation
            title='Top 10 Research Outputs (Unique Views)',
            hover_data={'research_id': True},  # Show Research ID on hover
            labels={'research_id': 'Research ID', 'total_unique_views': 'Total Views'},
            color='total_unique_views',
            color_continuous_scale='Viridis'
        )
        
        # Adjust layout
        fig.update_layout(
            title_font_size=20,
            title_x=0.5,
            yaxis_title='Research ID',
            xaxis_title='Total Views',
            showlegend=False
        )
        
        return fig
    
    def top_10_research_downloads(self, selected_colleges, selected_status, selected_years, start_date, end_date):
        # Get filtered data
        df = view_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:
            print("Debug: Filtered DataFrame is empty.")
            return go.Figure()
        
        # Convert 'date' column to datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        if df['date'].isnull().any():
            print("Debug: Some dates could not be converted.")
        
        # Filter date range
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        # Aggregate downloads by Research ID
        research_downloads = df.groupby('research_id')['total_downloads'].sum().reset_index()
        
        # Get top 10 Research IDs by download count, sorting in descending order
        top_10_research_downloads = research_downloads.sort_values(by='total_downloads', ascending=True).head(10)
        
        print("Debug: Top 10 Research IDs by download count:", top_10_research_downloads)
        
        # Create the vertical bar chart
        fig = px.bar(
            top_10_research_downloads,
            x='total_downloads',
            y='research_id',
            orientation='h',  # Horizontal orientation
            title='Top 10 Research Outputs (Downloads)',
            hover_data={'research_id': True},  # Show Research ID on hover
            labels={'research_id': 'Research ID', 'total_downloads': 'Total Downloads'},
            color='total_downloads',
            color_continuous_scale='Viridis'
        )
        
        # Adjust layout
        fig.update_layout(
            title_font_size=20,
            title_x=0.5,
            yaxis_title='Research ID',
            xaxis_title='Total Downloads',
            showlegend=False
        )
        
        return fig

    def create_heatmap(self, selected_colleges, selected_status, selected_years, start_date, end_date):
        # Get filtered data
        df = view_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        if df.empty:
            print("Debug: Filtered DataFrame is empty.")
            return go.Figure()
        
        # Convert 'date' column to datetime
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        if df['date'].isnull().any():
            print("Debug: Some dates could not be converted.")
        
        # Filter date range
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        
        # Extract day of week and time of day
        df['day_of_week'] = df['date'].dt.day_name()
        df['time_of_day'] = df['date'].dt.hour
        
        # Filter out invalid data
        df = df.dropna(subset=['day_of_week', 'time_of_day', 'total_views'])
        
        # Aggregate views by day and time
        heatmap_data = df.groupby(['day_of_week', 'time_of_day'])['total_views'].sum().reset_index()
        
        print("Debug: Heatmap data for visualization:", heatmap_data)
        
        # Create pivot table with proper keyword arguments
        pivot_table = heatmap_data.pivot(
            index='day_of_week',
            columns='time_of_day',
            values='total_views'
        )
        
        # Create the heatmap figure
        fig = px.imshow(
            pivot_table,
            aspect='auto',
            color_continuous_scale='Viridis',
            labels={'x': 'Time of Day', 'y': 'Day of Week', 'color': 'Total Views'},
            title='Most Active Days of the Week'
        )
        
        return fig
    
    def create_conversion_funnel(self, selected_colleges, selected_status, selected_years, start_date, end_date):
        # Get filtered data
        df = view_manager.get_filtered_data(selected_colleges, selected_status, selected_years)

        if df.empty:
            print("Debug: Filtered DataFrame is empty.")
            return go.Figure()

        # Convert 'date' column to datetime and filter by date range
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        if df['date'].isnull().any():
            print("Debug: Some dates could not be converted.")
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]

        # Aggregate the data
        funnel_data = df.agg({'total_views': 'sum', 
                            'total_unique_views': 'sum', 
                            'total_downloads': 'sum'}).reset_index()
        funnel_data.columns = ['Metric', 'Count']

        # Define the order of metrics for the funnel
        funnel_data['Metric'] = pd.Categorical(funnel_data['Metric'], 
                                            categories=['total_views', 'total_unique_views', 'total_downloads'], 
                                            ordered=True)
        funnel_data = funnel_data.sort_values('Metric')

        print("Debug: Funnel data for visualization:", funnel_data)

        # Create the horizontal funnel chart using Plotly
        fig = px.funnel(funnel_data, 
                        x='Count', 
                        y='Metric', 
                        orientation='h',  # Set the funnel to horizontal
                        title='Conversion Funnel: Views → Unique Views → Downloads',
                        labels={'Metric': 'Stage', 'Count': 'Count'})

        return fig

    def get_date_range(self,selected_range):
        end_date = datetime.now()
        if selected_range == '7D':
            start_date = end_date - timedelta(days=7)
        elif selected_range == '14D':
            start_date = end_date - timedelta(days=14)
        elif selected_range == '1M':
            start_date = end_date - timedelta(days=30)
        elif selected_range == '6M':
            start_date = end_date - timedelta(days=182)
        else:
            start_date = end_date - timedelta(days=7)

        return start_date,end_date


    def set_callbacks(self):
        """
        Set up the callback functions for the dashboard.
        """

        # Callback for reset button
        @self.dash_app.callback(
            [Output('college', 'value'),
            Output('status', 'value'),
            Output('years', 'value')],
            [Input('reset_button', 'n_clicks')],
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [view_manager.get_min_value('year'), view_manager.get_max_value('year')]


        @self.dash_app.callback(
            Output('college_line_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges, selected_status, selected_years,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
              # Default to last 7 days
            start,end = self.get_date_range(selected_range)
           
            return self.update_line_plot(selected_colleges, selected_status, selected_years,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

        @self.dash_app.callback(
            Output('college_pie_chart', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges, selected_status, selected_years,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
              # Default to last 7 days
            start,end = self.get_date_range(selected_range)
           
            return self.create_conversion_funnel(selected_colleges, selected_status, selected_years,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

        @self.dash_app.callback(
            Output('nonscopus_scopus_line_graph', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges, selected_status, selected_years,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
              # Default to last 7 days
            start,end = self.get_date_range(selected_range)
           
            return self.create_heatmap(selected_colleges, selected_status, selected_years,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

        @self.dash_app.callback(
            Output('proceeding_conference_line_graph', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges, selected_status, selected_years,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
              # Default to last 7 days
            start,end = self.get_date_range(selected_range)
           
            return self.top_10_research_ids(selected_colleges, selected_status, selected_years,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        @self.dash_app.callback(
            Output('proceeding_conference_bar_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('status', 'value'),
                Input('years', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges, selected_status, selected_years,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
              # Default to last 7 days
            start,end = self.get_date_range(selected_range)
           
            return self.top_10_research_downloads(selected_colleges, selected_status, selected_years,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))

        
        
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_shared_data_store(n_intervals):
            updated_data = view_manager.get_all_data()
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
                        self.create_display_card("Views", str(view_manager.get_sum_value('total_views'))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Unique Views", str(view_manager.get_sum_value('total_unique_views'))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Downloads", str(view_manager.get_sum_value('total_downloads'))),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Average Views per Research Output", f"{view_manager.get_average_views_per_research_id():.2f}%"),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    ),
                    dbc.Col(
                        self.create_display_card("Conversion Rate", f"{view_manager.get_conversion_rate():.2f}%"),
                        style={"display": "flex", "justify-content": "center", "align-items": "center", "padding": "0", "margin": "0"}
                    )
                    ])
                ])
        #"""

