from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from urllib.parse import parse_qs, urlparse
from . import db_manager
from collections import Counter
import re
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from wordcloud import WordCloud
from services.sdg_colors import sdg_colors


def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

class SDG_Map:
    def __init__(self, flask_app):
        """
        Initialize the MainDashboard class and set up the Dash app.
        """
        self.dash_app = Dash(__name__, server=flask_app, url_base_pathname='/sdg/map/', 
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.palette_dict = {
            'MITL': 'red',
            'ETYCB': 'yellow',
            'CCIS': 'green',
            'CAS': 'blue',
            'CHS': 'orange'
        }
        self.sdg_colors=sdg_colors
        self.all_sdgs = [f'SDG {i}' for i in range(1, 18)]
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

        
        sidebar_size = 2
        

        # Sample DataFrame for testing
        df = db_manager.get_all_data()  # Fetch all data
        sdg_series = df['sdg'].str.split('; ').explode()

        # Step 2: Drop duplicates to get distinct SDG values
        distinct_sdg_df = pd.DataFrame(sdg_series.drop_duplicates().reset_index(drop=True), columns=['sdg'])
        distinct_sdg_values = distinct_sdg_df['sdg'].tolist()  


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

        sdgs = html.Div(
            [
                dbc.Label("Select SDG:", style={"color": "#08397C"}),
                dcc.Dropdown(
                    id="sdg-dropdown",
                    options=[
                        # Add the "ALL" option at the top of the dropdown list
                        {"label": "ALL", "value": "ALL", "disabled": False},
                        *[
                            {
                                "label": sdg,
                                "value": sdg,
                                "disabled": sdg not in distinct_sdg_values,
                            }
                            for sdg in sorted(
                                self.all_sdgs,
                                key=lambda x: int(x.split()[1])  # Extract the numeric part and sort
                            )
                        ]
                    ],
                    multi=False,
                    placeholder="Select SDGs",
                    value="ALL",  # Default to "ALL"
                    style={
                        "width": "100%",
                        "border": "1px solid #0A438F",
                    },
                )
            ]
        )
        tab1 = dbc.Container(
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart1",
                        type="circle",  # Type of spinner
                        children=[
                            dcc.Graph(id="sdg-time-series")
                        ]
                    ),
                ],width=7),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart2",
                        type="circle",  # Type of spinner
                        children=[
                            dcc.Graph(id="sdg-pie-distribution")
                        ]
                    ),
                ],width=5)
            ])
        )

        tab2 = dbc.Container(
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart3",
                        type="circle",  # Type of spinner
                        children=[
                            dcc.Graph(id="sdg-map")
                        ]
                    ),
                ],width=12),
            ])
        )


        self.dash_app.layout = html.Div([
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),  # 1 second
            dcc.Store(id="shared-data-store"),  # Shared data store to hold the updated dataset
            dbc.Container([
                dbc.Row([
                    dbc.Col(controls, width=2, style={"height": "100%"}),  # Controls on the side
                    dbc.Col([
                        sdgs,
                        dbc.Container([
                            html.H4("sample",id="chosen-sdg"),
                            html.Div("This dashboard analyzes the institution’s research alignment with the global Sustainable Development Goals (SDGs), highlighting trends, strengths, and areas for improvement. It provides an overview of research performance across SDG categories, supporting data-driven decisions to enhance sustainable development efforts.")
                        ], style={"padding":"20px"}),
                        
                        dcc.Tabs(
                            id="sdg-tabs",
                            value="sdg-college-tab",  # Default selected tab
                            children=[
                                dcc.Tab(
                                    label="Institutional SDG Impact",
                                    value="sdg-college-tab",
                                    children=[
                                        tab1,
                                        
                                    ]
                                ),
                                dcc.Tab(
                                    label="Global Research Publications",
                                    value="sdg-global-tab",
                                    children=[
                                        dcc.Loading(
                                            id="loading-sdg-map",
                                            type="circle",  # Type of spinner
                                            children=[
                                                tab2
                                            ]
                                        ),                                     
                                    ]
                                ),
                                dcc.Tab(
                                    label="Research Trends and Collaboration",
                                    value="sdg-trend-tab",
                                    children=[
                                        dcc.Loading(
                                        id="loading-word-cloud",
                                        type="circle",
                                        children=[
                                            dcc.Graph(id="word-cloud"),
                                            ]
                                        ),
                                    ]
                                ),
                            ]
                        ),
                        dbc.Row([
                            dbc.Col([
                                dcc.Loading(
                                    id="loading-sdg-per-college",
                                    type="circle",
                                    children=[
                                        dcc.Graph(id="sdg-per-college")
                                    ]
                                )
                            ], width=6),
                            dbc.Col(
                                [
                                    dcc.Loading(
                                        id="loading-sdg-trend",
                                        type="circle",
                                        children=[
                                            dcc.Graph(id="sdg-trend")
                                        ]
                                    )
                                ],
                                width=6
                            )
                        ])
                    ], style={
                        "height": "100%",
                        "display": "flex",
                        "flex-direction": "column",
                        "overflow-y": "auto",  # Add vertical scrolling
                        "overflow-x": "auto",  # Add vertical scrolling
                        "transform": "scale(0.98)",  # Reduce size to 90%
                        "transform-origin": "0 0",  # Ensure scaling starts from the top-left corner
                        "margin": "0", 
                        "padding": "5px",
                        "flex-grow": "1",  # Make the content area grow to occupy remaining space
                    }),
                ], style={"height": "100%", "display": "flex"}),
            ], fluid=True, className="dbc dbc-ag-grid", style={
                "height": "90vh", 
                "margin": "0", 
                "padding": "0", 
                "overflow": "hidden"  # Prevent content from overflowing the container
            })
        ], style={"height": "90vh", "margin": "0", "padding": "0", "overflow": "hidden"})

    def create_sdg_plot(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Get filtered data based on selected parameters
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        # Check if df is empty or not
        if df.empty:
            # If no data, return an empty figure or a message
            return px.line(title="No data available for the selected parameters.")
        
        # Create a temporary DataFrame by splitting the SDGs in the SDG column (by ';')
        df_temp = df.copy()
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces
        
        # If the SDG dropdown value is not "ALL", filter the data accordingly
        if sdg_dropdown_value != "ALL":
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]
        
        # Group by Year and SDG and count the number of research outputs
        sdg_year_distribution = df_temp.groupby(['year', 'sdg']).size().reset_index(name='Count')

        # Ensure that all SDGs are included, even those with zero counts
        # Create a DataFrame for all combinations of Year and SDG
        all_sdg_year_combinations = pd.MultiIndex.from_product([df['year'].unique(), self.all_sdgs], names=['year', 'sdg'])
        sdg_year_distribution = sdg_year_distribution.set_index(['year', 'sdg']).reindex(all_sdg_year_combinations, fill_value=0).reset_index()

        # Sort the data by Year to ensure chronological order
        sdg_year_distribution = sdg_year_distribution.sort_values(by='year')

        # Create the time-series plot to show SDG research outputs over time
        fig = px.line(
            sdg_year_distribution,
            x='year',
            y='Count',
            color='sdg',  # Group by SDG
            title='SDG Research Outputs Over Time',
            labels={'year': 'Year', 'Count': 'Number of Research Outputs', 'sdg': 'Sustainable Development Goals (SDGs)'},
            color_discrete_map=sdg_colors,  # Apply SDG colors
            category_orders={'sdg': self.all_sdgs},  # Ensure SDGs are in order
        )

        # Customize layout for better visualization
        fig.update_layout(
            title_font_size=18,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            legend_title_font_size=14,
            template="plotly_white",
            xaxis=dict(showgrid=True),  # Show grid on x-axis
            yaxis=dict(title='Number of Research Outputs', showgrid=True),  # Label y-axis clearly
            legend_title=dict(text='SDGs'),  # Rename legend title
            legend=dict(title=dict(font=dict(size=14)), traceorder="normal", orientation="h", x=1, xanchor="right", y=-0.2),  # Position legend outside
        )

        return fig


    def create_sdg_pie_chart(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Get filtered data based on selected parameters
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        # Create a temporary DataFrame by splitting the SDGs in the SDG column (by ';')
        df_temp = df.copy()
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces

        # Group by SDG and count the number of research outputs
        sdg_distribution = df_temp.groupby('sdg').size().reset_index(name='Count')

        # Calculate the percentage of total research outputs for each SDG
        total_count = sdg_distribution['Count'].sum()
        sdg_distribution['Percentage'] = (sdg_distribution['Count'] / total_count) * 100

        # Ensure all SDGs are included, even those with zero counts
        sdg_distribution = pd.DataFrame(self.all_sdgs, columns=['sdg']).merge(sdg_distribution, on='sdg', how='left').fillna(0)

        # Reorder the SDGs based on the predefined list (self.all_sdgs)
        sdg_distribution['SDG'] = pd.Categorical(sdg_distribution['sdg'], categories=self.all_sdgs, ordered=True)
        sdg_distribution = sdg_distribution.sort_values('sdg')

        # Create the pie chart to show the percentage distribution of research outputs by SDG
        fig = px.pie(
            sdg_distribution,
            names='sdg',
            values='Percentage',
            title='Percentage of Research Outputs by SDG',
            color='sdg',
            color_discrete_map=sdg_colors,  # Apply SDG colors
            labels={'sdg': 'Sustainable Development Goals (SDGs)', 'Percentage': 'Percentage of Total Outputs'},
            category_orders={'sdg': self.all_sdgs}  # Ensure SDG in legend is in order
        )

        # Customize layout for better visualization
        fig.update_layout(
            title_font_size=18,
            legend_title_font_size=14,
            template="plotly_white",
            legend=dict(
                title=dict(font=dict(size=14)),
                traceorder="normal",
                orientation="h",  # Horizontal legend
                x=0.5,  # Center the legend horizontally
                xanchor="center",  # Anchor the legend at the center
                y=-0.2,  # Position the legend below the chart
                yanchor="top",  # Anchor the legend at the top
            ),
        )

        return fig
    
    def create_geographical_heatmap(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Fetch filtered data from the database
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        
        # Step 2: Split SDGs by ';' and explode into separate rows
        df_temp = df.copy()
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces

        if sdg_dropdown_value != "ALL":
            # Step 3: Generate the pivot table of SDG-country distribution, including Year
            sdg_country_year_distribution = df_temp.groupby(['country', 'sdg', 'year']).size().reset_index(name='Count')

            # Filter according to the selected SDG value if not 'ALL'
            sdg_country_year_distribution = sdg_country_year_distribution[sdg_country_year_distribution['sdg'] == sdg_dropdown_value]

            # Step 4: Create a full list of all combinations of Country, SDG, and Year
            all_countries = df_temp['country'].unique()
            all_years = df_temp['year'].unique()

            # Create a multi-index of all combinations of Country, SDG, and Year
            all_combinations = pd.MultiIndex.from_product([all_countries, [sdg_dropdown_value], all_years], names=['country', 'sdg', 'year'])

            # Reindex the data to ensure all combinations are included
            sdg_country_year_distribution = sdg_country_year_distribution.set_index(['country', 'sdg', 'year']).reindex(all_combinations).reset_index()
            sdg_country_year_distribution['Count'] = sdg_country_year_distribution['Count'].fillna(0)

            # Remove countries with no data across all years and SDGs
            sdg_country_year_distribution.loc[sdg_country_year_distribution['Count'] == 0, 'Count'] = None

            # Step 5: Group data to list SDGs for each country and year
            sdg_summary = (
                sdg_country_year_distribution.groupby(['country', 'year', 'sdg'])
                .agg({'Count': 'sum'})
                .reset_index()
            )

            # Filter out SDGs with zero or null counts
            sdg_summary = sdg_summary[sdg_summary['Count'].notnull() & (sdg_summary['Count'] > 0)]

            # Sort SDGs according to the `all_sdgs` list
            sdg_summary['sdg'] = pd.Categorical(sdg_summary['sdg'], categories=self.all_sdgs, ordered=True)
            sdg_summary = sdg_summary.sort_values(['country', 'year', 'sdg'])

            # Convert sdg column back to string before concatenating
            sdg_summary['SDG Details'] = sdg_summary['sdg'].astype(str) + ": " + sdg_summary['Count'].astype(int).astype(str)

            # Aggregate SDG details for each country and year
            country_sdg_details = (
                sdg_summary.groupby(['country', 'year'])['SDG Details']
                .apply(lambda x: "<br>".join(x))  # Join SDG details for each year
                .reset_index(name='SDG Summary')
            )

            # Merge SDG summaries into the main dataset for hover info
            sdg_country_year_distribution = sdg_country_year_distribution.merge(
                country_sdg_details, on=['country', 'year'], how='left'
            )

            # Step 6: Calculate total count for each country and year
            country_year_total = (
                sdg_country_year_distribution.groupby(['country', 'year'])['Count']
                .sum()
                .reset_index(name='Total Count')
            )

            # Merge the total count into the main dataset
            sdg_country_year_distribution = sdg_country_year_distribution.merge(
                country_year_total, on=['country', 'year'], how='left'
            )

            # Step 7: Sort the DataFrame by Year to ensure proper ordering in the animation
            sdg_country_year_distribution = sdg_country_year_distribution.sort_values(by='year')

            # Step 8: Create a geographical heatmap using Plotly
            fig = px.choropleth(
                sdg_country_year_distribution,
                locations="country",
                locationmode="country names",  # Use country names for geographical locations
                color="Count",
                hover_name="country",
                hover_data={
                    "SDG Summary": True, 
                    "Count": False, 
                    "year": False,
                    "Total Count": True  # Include the total count in hover data
                },  # Show SDG summary and total count in hover
                color_continuous_scale="Viridis",  # Choose a color scale
                title="Geographical Distribution of Research Outputs by SDG and Year",
                labels={'Count': 'Number of Research Outputs'}
            )

        else:
            # If "ALL" is selected, summarize the data across all years
            sdg_country_year_distribution = df_temp.groupby(['country', 'sdg']).size().reset_index(name='Count')

            # Filter out SDGs with zero or null counts
            sdg_country_year_distribution = sdg_country_year_distribution[sdg_country_year_distribution['Count'] > 0]

            # Sort SDGs according to the `all_sdgs` list
            sdg_country_year_distribution['sdg'] = pd.Categorical(sdg_country_year_distribution['sdg'], categories=self.all_sdgs, ordered=True)
            sdg_country_year_distribution = sdg_country_year_distribution.sort_values(['country', 'sdg'])

            # Convert sdg column to string and concatenate with count for SDG Summary
            sdg_country_year_distribution['SDG Details'] = sdg_country_year_distribution['sdg'].astype(str) + ": " + sdg_country_year_distribution['Count'].astype(int).astype(str)
    
            # Aggregate SDG details for each country
            country_sdg_details = (
                sdg_country_year_distribution.groupby(['country'])['SDG Details']
                .apply(lambda x: "<br>".join(x))  # Join SDG details for each country, including counts
                .reset_index(name='SDG Summary')
            )

            # Merge SDG summaries into the main dataset for hover info
            sdg_country_year_distribution = sdg_country_year_distribution.merge(
                country_sdg_details, on=['country'], how='left'
            )

            # Step 6: Calculate total count for each country
            country_year_total = (
                sdg_country_year_distribution.groupby(['country'])['Count']
                .sum()
                .reset_index(name='Total Count')
            )

            # Merge the total count into the main dataset
            sdg_country_year_distribution = sdg_country_year_distribution.merge(
                country_year_total, on=['country'], how='left'
            )

            # Step 8: Create a geographical heatmap using Plotly
            fig = px.choropleth(
                sdg_country_year_distribution,
                locations="country",
                locationmode="country names",  # Use country names for geographical locations
                color="Count",
                hover_name="country",
                hover_data={
                    "SDG Summary": True,  # Show SDG details with counts in hover
                    "Count": False,  # Do not show SDG count, it's already in SDG Summary
                    "Total Count": False  # Include total count for the country in hover
                },  # Show SDG summary (with SDG counts) and total count in hover
                color_continuous_scale="Viridis",  # Choose a color scale
                title="Geographical Distribution of Research Outputs by SDG and Year",
                labels={'Count': 'Number of Research Outputs'}
            )


        

        # Step 9: Customize the layout
        fig.update_geos(showcoastlines=True, coastlinecolor="Black", projection_type="natural earth")
        fig.update_layout(
            geo=dict(showland=True, landcolor="lightgray", showocean=True, oceancolor="white"),
            title_font_size=18,
            geo_scope="world",  # Set the scope to 'world'
            template="plotly_white",
            height=600  # Adjust height as needed
        )

        return fig




    


    def create_sdg_trend(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()

        # Define the ordered list of SDGs (e.g., SDG 1, SDG 2, etc.)
        sdg_order = [f"SDG {i}" for i in range(1, 18)]  # Generates SDG 1 to SDG 17

        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_exploded = df_copy.explode('sdg')  # Explode rows for each SDG value

        # Strip whitespace from the SDG values and ensure correct ordering
        sdg_exploded['sdg'] = sdg_exploded['sdg'].str.strip()
        sdg_exploded['sdg'] = pd.Categorical(sdg_exploded['sdg'], categories=sdg_order, ordered=True)

        if sdg_dropdown_value !="ALL":
            # Filter data for the selected SDG
            sdg_filtered = sdg_exploded[sdg_exploded['sdg'] == sdg_dropdown_value]

            # Group data by year and count occurrences
            sdg_trend = sdg_filtered.groupby('year').size().reset_index(name='count')

            # Create a line chart using Plotly
            fig = px.line(
                sdg_trend,
                x='year',
                y='count',
                title=f'{sdg_dropdown_value} Trend Over Time',
                labels={'year': 'Year', 'count': 'Frequency'},
                markers=True
            )
            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Frequency",
                title_x=0.5,
                template="plotly_white"
            )
        else:
            # Group the data by year and SDG, and calculate the count
            sdg_trends = sdg_exploded.groupby(['year', 'sdg']).size().reset_index(name='count')

            # Create a heatmap using Plotly
            fig = px.density_heatmap(
                sdg_trends,
                x='year',
                y='sdg',
                z='count',
                color_continuous_scale='Blues',
                title="SDG Trends Over Time",
                labels={'year': 'Year', 'sdg': 'SDG','count':""}
            )
            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Sustainable Development Goal",
                title_x=0.5,
                template="plotly_white"
            )

        return fig
    


    def create_sdg_bar(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data(selected_colleges, selected_status, selected_years)
        df_copy = df.copy()

        # Define the ordered list of SDGs (e.g., SDG 1, SDG 2, etc.)
        sdg_order = [f"SDG {i}" for i in range(1, 18)]  # Generates SDG 1 to SDG 17

        # Split SDG values and explode into separate rows
        df_copy['sdg'] = df_copy['sdg'].str.split('; ')  # Split by semicolon and space
        sdg_exploded = df_copy.explode('sdg')  # Explode rows for each SDG value

        # Strip whitespace from the SDG values and ensure correct ordering
        sdg_exploded['sdg'] = sdg_exploded['sdg'].str.strip()
        sdg_exploded['sdg'] = pd.Categorical(sdg_exploded['sdg'], categories=sdg_order, ordered=True)

        if sdg_dropdown_value !="ALL":
            # Filter the data for the selected SDG
            sdg_filtered = sdg_exploded[sdg_exploded['sdg'] == sdg_dropdown_value]

            # Group the data by year and research_type
            grouped_data = sdg_filtered.groupby(['year', 'research_type']).size().reset_index(name='count')

            # Create a line plot using Plotly
            fig = px.line(
                grouped_data,
                x='year',
                y='count',
                color='research_type',
                title=f"{sdg_dropdown_value} Trends Over Time by Research Type",
                labels={'year': 'Year', 'count': 'Frequency'},
                markers=True
            )

            # Customize the layout
            fig.update_layout(
                xaxis_title="Year",
                yaxis_title="Count",
                title_x=0.5,
                template="plotly_white",
                xaxis_tickangle=-45  # Rotate x-axis labels for better readability
            )
        else:
            # Group the data by SDG and research_type
            grouped_data = sdg_exploded.groupby(['sdg', 'research_type']).size().reset_index(name='count')

            # Create a bar chart using Plotly
            fig = px.bar(
                grouped_data,
                x='sdg',
                y='count',
                color='research_type',
                title="SDG and Research Type Distribution",
                labels={'sdg': 'Sustainable Development Goal', 'count': 'Frequency'},
                barmode='group'  # Group bars side by side
            )

            # Customize the layout
            fig.update_layout(
                xaxis_title="Sustainable Development Goal",
                yaxis_title="Count",
                title_x=0.5,
                template="plotly_white",
                xaxis={
                    'categoryorder': 'array', 
                    'categoryarray': sdg_order,
                    'tickangle': -45  # Rotate x-axis labels for better readability
                }
            )

        return fig

    

    def update_figures(self,selected_colleges, selected_status, selected_years,sdg_dropdown_value):
        fig1 = self.create_sdg_trend(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        fig2 = self.create_sdg_bar(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        fig3 = self.create_sdg_plot(selected_colleges, selected_status, selected_years, sdg_dropdown_value)
        fig4 = self.create_sdg_pie_chart(selected_colleges, selected_status, selected_years, sdg_dropdown_value)

        return fig1,fig2, fig3, fig4

        
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
        
        # Callback to update the header based on selected SDG
        @self.dash_app.callback(
            Output("chosen-sdg", "children"),
            [Input("sdg-dropdown", "value")]
        )
        def update_header(selected_sdg):

            # If selected_sdg is a list, use the first item or handle as needed
            if isinstance(selected_sdg, list) and selected_sdg:
                selected_sdg = selected_sdg[0]  # Use the first selected SDG, or handle as needed

            label = {
                "SDG 1": "No Poverty",
                "SDG 2": "Zero Hunger",
                "SDG 3": "Good Health and Well-being",
                "SDG 4": "Quality Education",
                "SDG 5": "Gender Equality",
                "SDG 6": "Clean Water and Sanitation",
                "SDG 7": "Affordable and Clean Energy",
                "SDG 8": "Decent Work and Economic Growth",
                "SDG 9": "Industry, Innovation and Infrastructure",
                "SDG 10": "Reduced Inequality",
                "SDG 11": "Sustainable Cities and Communities",
                "SDG 12": "Responsible Consumption and Production",
                "SDG 13": "Climate Action",
                "SDG 14": "Life Below Water",
                "SDG 15": "Life on Land",
                "SDG 16": "Peace, Justice and Strong Institutions",
                "SDG 17": "Partnerships for the Goals"
            }
            title="Overall SDG" if selected_sdg=="ALL" else selected_sdg+":"
                
            caption = label.get(selected_sdg, "") if selected_sdg else ""

            return f"{title} {caption}"
        
        @self.dash_app.callback([
            Output('sdg-per-college', 'figure'),
            Output('sdg-trend', 'figure'),
            Output('sdg-time-series', 'figure'),
            Output('sdg-pie-distribution', 'figure'),
            ],
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_all(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.update_figures(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('sdg-map', 'figure'),
            [Input('college', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig(selected_colleges, selected_status, selected_years,sdg_dropdown_value):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_geographical_heatmap(selected_colleges, selected_status, selected_years,sdg_dropdown_value)
        
        
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_shared_data_store(n_intervals):
            updated_data = db_manager.get_all_data()
            return updated_data.to_dict('records')
        