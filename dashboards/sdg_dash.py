# created by Jelly Mallari

from dash import Dash, html, dcc,dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from . import db_manager
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from wordcloud import WordCloud
from dash.dash_table import DataTable
from scipy.stats import linregress

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

class SDG_Dash:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/sdg/overall/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.palette_dict = {
            'MITL': 'red',
            'ETYCB': 'yellow',
            'CCIS': 'green',
            'CAS': 'blue',
            'CHS': 'orange'
        }
        # Get default values
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        self.create_layout()
        self.set_callbacks()

    def create_layout(self):
        """
        Create the layout of the dashboard.
        """

        college = html.Div(
            [
                dbc.Label("Select College:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
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
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('status')],
                    value=[],
                    inline=True,
                ),
            ],
            className="mb-4",
        )

        slider = html.Div(
            [
                dbc.Label("Select Years:", style={"color": "#08397C"}),
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
                html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),
                college, status, slider, button
            ],
            body=True,
            style={"border": "2px solid #0A438F", "display": "flex", "flexDirection": "column"}
        )

        sdg_container = html.Div([

            html.Div(id="sdg-cards", style={"display": "flex", "flex-wrap": "wrap", "justify-content": "center"})
        ])

    

        # Insert into main_dash layout
        main_dash = dbc.Container([
            dbc.Row([
                dbc.Col([dcc.Graph(id="sdg_college"),sdg_container], width=8),
                dbc.Col([dcc.Graph(id="sdg_donut"), dcc.Graph(id="sdg_box")], width=4),
            ]), # Add the research table here
        ], fluid=True)

        self.dash_app.layout = html.Div([
                dbc.Container(
                    [
                        dbc.Row([
                            dbc.Col(controls, width=2),
                            dbc.Col([
                                main_dash
                            ], width=10,style={"transform": "scale(1)", "transform-origin": "0 0"}),                          
                        ]),
                        dcc.Interval(
                            id='interval-component',
                            interval=60 * 1000,  # Update every 1 minute (optional)
                            n_intervals=0
                        )
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
                            "border": "2px solid #0A438F",  # Change color as needed
                            "borderRadius": "10px",          # Adjust the roundness
                            "padding": "10px",               # Add some padding inside the card
                            "margin": "5px"                  # Space between columns
                        }))
        ])
    
    # Define colors and icons based on trend
    def get_arrow_style(self,trend):
        if trend == "increasing":
            return {"color": "green", "icon": "↑"}
        elif trend == "decreasing":
            return {"color": "red", "icon": "↓"}
        else:
            return {"color": "gray", "icon": "•••"}

    def create_sdg_college(self, selected_colleges, selected_status, selected_years):  
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()
        
        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_df = df_copy.explode('sdg')

        # Handle case where no data is returned
        if df.empty:  
            return go.Figure()  # Return an empty figure

        # Ensure all SDGs are included, even if they don't appear in the data
        all_sdgs = ['SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17']
        
        # Prepare data for the stacked bar chart
        stacked_data = sdg_df.groupby(["sdg", "college_id"]).size().unstack(fill_value=0)

        # Reindex to ensure all SDGs are included
        stacked_data = stacked_data.reindex(all_sdgs, axis=0, fill_value=0)

        # Create a Plotly bar chart
        fig_bar = go.Figure()

        for college in stacked_data.columns:
            color = self.palette_dict.get(college, 'gray')  # Default to gray if the college isn't in the palette
            fig_bar.add_trace(go.Bar(
                x=stacked_data.index,
                y=stacked_data[college],
                name=college,
                marker_color=color  # Set the color for the bars
            ))

        # Customize the chart
        fig_bar.update_layout(
            title="Colleges Targeting Each SDG",
            xaxis_title="SDG Targeted",
            yaxis_title="Count of Research Outputs",
            legend_title="College",
            xaxis=dict(
                tickmode='array',
                tickangle=45,  # Rotate labels by 45 degrees
                tickvals=stacked_data.index,  # Ensure all SDGs are displayed
                ticktext=stacked_data.index,  # Label text for each SDG
            ),
            margin=dict(l=50, r=50, t=50, b=150),  # Increase bottom margin to accommodate labels
            font=dict(size=10)  # Optional: Reduce font size for better readability
        )

        # Return the figure for Dash
        return fig_bar
    
    def create_sdg_donut(self, selected_colleges, selected_status, selected_years):  
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()
        
        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_df = df_copy.explode('sdg')

        # Handle case where no data is returned
        if df.empty:  
            return go.Figure()  # Return an empty figure

        # Ensure all SDGs are included, even if they don't appear in the data
        all_sdgs = ['SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17']
        
        # Count the occurrences of each SDG
        sdg_count = sdg_df['sdg'].value_counts().reindex(all_sdgs, fill_value=0)

        # Create the donut chart using Plotly
        fig = go.Figure(data=[go.Pie(
            labels=sdg_count.index,
            values=sdg_count.values,
            hole=0.4,  # Make it a donut chart
            hoverinfo="label+percent",  # Show label and percentage on hover
            textinfo="label+percent",   # Display label and percentage on the chart
        )])

        # Customize the layout
        fig.update_layout(
            title="Distribution of SDGs",
            showlegend=False,
            font=dict(size=12),
            margin=dict(t=50, b=50, l=50, r=50),  # Optional: Adjust the margins if needed
        )

        # Return the figure for Dash
        return fig


    def create_sdg_treemap(self, selected_colleges, selected_status, selected_years):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()

        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_df = df_copy.explode('sdg')

        # Handle case where no data is returned
        if df.empty:
            return go.Figure()  # Return an empty figure

        # Count the occurrences of each SDG
        sdg_count = sdg_df['sdg'].value_counts().reset_index()
        sdg_count.columns = ['SDG', 'Count']

        # Ensure all SDGs are included, even if they don't appear in the data
        all_sdgs = ['SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17']

        # Reindex to include all SDGs
        sdg_count = sdg_count.set_index('SDG').reindex(all_sdgs, fill_value=0).reset_index()
        sdg_count.columns = ['SDG', 'Count']

        # Create the tree map using Plotly Express
        fig = px.treemap(sdg_count,
                        path=['SDG'],  # Only SDG as the root, no parent
                        values='Count',
                        title="Distribution of SDGs",
                        color='Count',  # Color by the count # Color scale
                        hover_data=['Count'])  # Show count on hover

        # Customize the layout to remove borders and set background to white
        fig.update_layout(
            margin=dict(t=50, b=50, l=50, r=50),  # Optional: Adjust the margins
            paper_bgcolor='white',  # Set the overall background to white
            plot_bgcolor='white',  # Set the chart area background to white
            xaxis=dict(showline=False, zeroline=False),  # Remove x-axis lines
            yaxis=dict(showline=False, zeroline=False),  # Remove y-axis lines
            showlegend=True,  # Keep the legend visible
        )

        # Return the figure for Dash
        return fig
    
    def create_sdg_card(self,selected_colleges, selected_status, selected_years):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()

        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_df = df_copy.explode('sdg')
        print(sdg_df.columns)

        # Group by SDG and Year to calculate counts
        sdg_yearly_counts = sdg_df.groupby(['year', 'sdg']).size().unstack(fill_value=0)

        # Define the range of years for the analysis
        year_range = range(min(selected_years), max(selected_years) + 1)
        sdg_yearly_counts = sdg_yearly_counts.reindex(year_range, fill_value=0)

        # Ensure SDGs are sorted in order (e.g., SDG 1, SDG 2, ..., SDG 17)
        sorted_sdgs = sorted(sdg_yearly_counts.columns, key=lambda x: int(x.split(' ')[-1]) if x.startswith('SDG') else x)

        # Recalculate trends and percentage changes for all SDGs
        sdg_trends = []
        for sdg in sorted_sdgs:
            sdg_group = sdg_yearly_counts[sdg].reset_index()
            sdg_group.columns = ['Year', 'Count']

            if len(sdg_group) > 1:
                slope, _, _, _, _ = linregress(sdg_group["Year"], sdg_group["Count"])
                average_count = sdg_group["Count"].mean()
                trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stagnant"
                percent_change = (slope / average_count) * 100 if average_count != 0 else 0
            else:
                trend = "stagnant"
                percent_change = 0

            sdg_trends.append({
                "SDG": sdg,
                "Trend": trend,
                "PercentChange": abs(percent_change),
            })

        # Create the legend
        legend = html.Div([
            html.Div([
                html.Span(self.get_arrow_style("increasing")["icon"], style={"color": self.get_arrow_style("increasing")["color"], "font-size": "16px", "margin-right": "5px"}),
                html.Span("Increasing", style={"font-size": "14px"})
            ], style={"margin-right": "15px", "display": "inline-block"}),

            html.Div([
                html.Span(self.get_arrow_style("decreasing")["icon"], style={"color": self.get_arrow_style("decreasing")["color"], "font-size": "16px", "margin-right": "5px"}),
                html.Span("Decreasing", style={"font-size": "14px"})
            ], style={"margin-right": "15px", "display": "inline-block"}),

            html.Div([
                html.Span(self.get_arrow_style("stagnant")["icon"], style={"color": self.get_arrow_style("stagnant")["color"], "font-size": "16px", "margin-right": "5px"}),
                html.Span("Stagnant", style={"font-size": "14px"})
            ], style={"margin-right": "15px", "display": "inline-block"}),
        ], style={"padding": "10px", "border-bottom": "1px solid #ccc", "margin-bottom": "15px"})

        # Generate the SDG cards
        sdg_cards = [
            html.Div([
                html.P(sdg["SDG"], style={"font-weight": "bold"}),
                html.P(self.get_arrow_style(sdg["Trend"])["icon"], style={"color": self.get_arrow_style(sdg["Trend"])["color"], "font-size": "24px"}),
                html.P(f"{sdg['PercentChange']:.2f}%", style={"font-size": "12px"})
            ], style={
                "border": "1px solid #ccc",
                "border-radius": "5px",
                "padding": "10px",
                "text-align": "center",
                "width": "100px",
                "margin": "5px",
                "display": "inline-block"
            }) for sdg in sdg_trends
        ]

        # Combine legend and SDG cards
        return  sdg_cards + [legend]



    
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
            return [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        
        
        @self.dash_app.callback(
            Output('sdg_college', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value')]
        )
        def update_sdg_college(selected_colleges, selected_status, selected_years):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_college(selected_colleges, selected_status, selected_years)
        

        @self.dash_app.callback(
            Output('sdg_donut', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value')]
        )
        def update_sdg_donut(selected_colleges, selected_status, selected_years):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_donut(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output('sdg_box', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value')]
        )
        def update_sdg_box(selected_colleges, selected_status, selected_years):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_treemap(selected_colleges, selected_status, selected_years)
        
        @self.dash_app.callback(
            Output("sdg-cards", "children"),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value')]
        )
        def update_sdg_cards(selected_colleges, selected_status, selected_years):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_card(selected_colleges, selected_status, selected_years)
        