from dash import Dash, html, dcc, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from urllib.parse import parse_qs, urlparse
from . import db_manager
from nltk.corpus import stopwords
from wordcloud import WordCloud
from services.sdg_colors import sdg_colors

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values


class SDG_Map_College:
    def __init__(self, server, title=None, college=None, program=None, **kwargs):
        self.dash_app = Dash(__name__,
                             server=server,
                             url_base_pathname=kwargs.get('url_base_pathname', '/sdg/map/college/'),
                             external_stylesheets=[dbc.themes.BOOTSTRAP])
        self.title = title
        self.college = college
        self.program = program

        self.palette_dict = db_manager.get_college_colors()
        self.sdg_colors=sdg_colors
        self.all_sdgs = [f'SDG {i}' for i in range(1, 18)]
        self.default_colleges = db_manager.get_unique_values('college_id')
        self.default_programs = []
        self.default_statuses = db_manager.get_unique_values('status')
        self.default_years = [db_manager.get_min_value('year'), db_manager.get_max_value('year')]

        self.set_layout()
        self.add_callbacks()

        self.all_sdgs = [
            'SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 
            'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 
            'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17'
        ]

    def set_layout(self):
        """Common layout shared across all dashboards."""
        df = db_manager.get_all_data()
        sdg_series = df['sdg'].str.split('; ').explode()
        distinct_sdg_df = pd.DataFrame(sdg_series.drop_duplicates().reset_index(drop=True), columns=['sdg'])
        distinct_sdg_values = distinct_sdg_df['sdg'].tolist()  


        college = html.Div(
            [
                dbc.Label("Select College:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="college",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values('college_id')],
                    value=self.college if self.college else [],  # Default to self.college or empty list
                    inline=True,
                ),
            ],
            className="mb-4",
            style={"display": "none", "opacity": "0.5"},  # Disable interaction and style for visual feedback
        )

        program = html.Div(
            [
                dbc.Label("Select Program:", style={"color": "#08397C"}),
                dbc.Checklist(
                    id="program",
                    options=[{'label': value, 'value': value} for value in db_manager.get_unique_values_by('program_id','college_id',self.college)],
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
                    },
                )
            ],
             className="mb-4",
        )

        controls = dbc.Card(
            [
                html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),  # Set the color to red
                sdgs,
                college,
                program,
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
        tab1 = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart1",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-time-series")
                        ]
                    ),
                ],width=7),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart2",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-pie-distribution")
                        ]
                    ),
                ],width=5)
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart3",
                        type="circle",
                        children=[
                            dcc.Graph(id="sdg-research-type")
                        ]
                    ),
                ],width=6),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart4",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-status")
                        ]
                    ),
                ],width=6)
            ]),
            ]
        )

        tab2 = dbc.Container([
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart5",
                        type="circle",
                        children=[
                            dcc.Graph(id="sdg-conference")
                        ]
                    ),
                ],width=8),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart6",
                        type="circle",
                        children=[
                            dcc.Graph(id="sdg-publication-type")
                        ]
                    ),
                ],width=4)
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart7",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-map")
                        ]
                    ),
                ],width=12),
            ]),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart8",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-countries")
                        ]
                    ),
                ],width=8),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart9",
                        type="circle", 
                        children=[
                            dcc.Graph(id="sdg-local-foreign-pie")
                        ]
                    ),
                ],width=4)
            ]),

        ])

        tab3 = dbc.Container([
            dbc.Col(
                dcc.Loading(
                    id="loading-sdg-chart10",
                    type="circle",
                    children=[
                        dcc.Graph(id="keywords-cloud"),
                    ]
                ),
            ),
            
            dbc.Col(
                dcc.Loading(
                    id="loading-sdg-chart11",
                    type="circle",
                    children=[
                        dcc.Graph(id="research-area-cloud"),
                    ]
                ),
            ),
            dbc.Row([
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart12",
                        type="circle", 
                        children=[
                            dcc.Graph(id="top-research-area")
                        ]
                    ),
                ],width=6),
                dbc.Col([
                    dcc.Loading(
                        id="loading-sdg-chart13",
                        type="circle", 
                        children=[
                            dcc.Graph(id="top-authors")
                        ]
                    ),
                ],width=6)
            ]),
            ]
        )


        self.dash_app.layout = html.Div([
            # URL tracking
            dcc.Location(id='url', refresh=False),
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),  # 1 second
            dcc.Store(id="shared-data-store"),  # Shared data store to hold the updated dataset
            dbc.Container([
                dbc.Row([
                    dbc.Col(controls, width=2, style={"height": "100%"}),
                    dbc.Col([
                        dbc.Container([
                            html.Div(id='college-info'),
                            html.H4("sample",id="chosen-sdg"),
                            html.Div("This dashboard analyzes the institution’s research alignment with the global Sustainable Development Goals (SDGs), highlighting trends, strengths, and areas for improvement. It provides an overview of research performance across SDG categories, supporting data-driven decisions to enhance sustainable development efforts.")
                        ], style={"padding":"20px"}),
                        
                        dcc.Tabs(
                            id="sdg-tabs",
                            value="sdg-college-tab",  
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
                                            type="circle", 
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
                                        tab3
                                    ]
                                ),
                            ]
                        ),
                    ], style={
                        "height": "100%",
                        "display": "flex",
                        "flex-direction": "column",
                        "overflow-y": "auto",  
                        "overflow-x": "auto",  
                        "transform": "scale(0.98)",  
                        "transform-origin": "0 0",  
                        "margin": "0", 
                        "padding": "5px",
                        "flex-grow": "1",  
                    }),
                ], style={"height": "100%", "display": "flex"}),
            ], fluid=True, className="dbc dbc-ag-grid", style={
                "height": "90vh", 
                "margin": "0", 
                "padding": "0", 
                "overflow": "hidden"  # Prevent content from overflowing the container
            })
        ], style={"height": "90vh", "margin": "0", "padding": "0", "overflow": "hidden"})



    def get_program_colors(self, df, color_column='program_id'):
        """
        Generate a color mapping for the unique values in the specified column of the DataFrame.

        Args:
            df (pd.DataFrame): The DataFrame containing data.
            color_column (str): The column for which unique values will be colored (default is 'program_id').

        Updates:
            self.program_colors: A dictionary mapping unique values in the color_column to colors.
        """
        unique_values = df[color_column].unique()
        random_colors = px.colors.qualitative.Plotly[:len(unique_values)]
        self.program_colors = {value: random_colors[i % len(random_colors)] for i, value in enumerate(unique_values)}

    
    def create_sdg_plot(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
            # Get filtered data based on selected parameters
            df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
            df = df[df['journal'] != 'unpublished']
            df = df[df['status'] != 'PULLOUT']

            # Check if df is empty
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
                # Group by Year and College and count the number of research outputs
                sdg_college_distribution = df_temp.groupby(['year', 'program_id']).size().reset_index(name='Count')
                print(sdg_college_distribution)
                
                # Create the time-series plot grouped by college
                fig = px.line(
                    sdg_college_distribution,
                    x='year',
                    y='Count',
                    color='program_id',  # Group by College
                    title=f'Research Outputs Over Time by College (Filtered by SDG: {sdg_dropdown_value})',
                    labels={'year': 'Year', 'Count': 'Number of Research Outputs', 'program_id': 'College'},
                    template="plotly_white",
                    color_discrete_map=self.palette_dict,
                    markers=True
                )
            else:
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
                    labels={'year': 'Year', 'Count': 'Number of Research Outputs', 'sdg': 'SDG'},
                    color_discrete_map=sdg_colors,  # Apply SDG colors
                    category_orders={'sdg': self.all_sdgs}, 
                    markers=True
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
                legend=dict(title=dict(font=dict(size=14)), traceorder="normal", orientation="h", x=1, xanchor="right", y=-0.2),  # Position legend outside
            )

            return fig


    def create_sdg_pie_chart(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        # Get filtered data based on selected parameters

        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']

        
        # Create a temporary DataFrame by splitting the SDGs in the SDG column (by ';')
        df_temp = df.copy()
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces

        # If the SDG dropdown value is not "ALL", filter the data accordingly
        if sdg_dropdown_value != "ALL":
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]
            # Group by College to show the distribution of research outputs across colleges
            college_distribution = df_temp.groupby('program_id').size().reset_index(name='Count')
            college_distribution['Percentage'] = (college_distribution['Count'] / college_distribution['Count'].sum()) * 100
            print("COLLEge distribution:",college_distribution)
            # Create the pie chart to show the college distribution
            fig = px.pie(
                college_distribution,
                names='program_id',
                values='Percentage',
                title='Percentage of Research Outputs by College',
                color='program_id',
                labels={'program_id': 'College', 'Percentage': 'Percentage of Total Outputs'},
                color_discrete_map=self.palette_dict,
            )
        else:
            # Group by SDG and count the number of research outputs
            sdg_distribution = df_temp.groupby('sdg').size().reset_index(name='Count')

            # Calculate the percentage of total research outputs for each SDG
            total_count = sdg_distribution['Count'].sum()
            sdg_distribution['Percentage'] = (sdg_distribution['Count'] / total_count) * 100

            # Ensure all SDGs are included, even those with zero counts
            sdg_distribution = pd.DataFrame(self.all_sdgs, columns=['sdg']).merge(sdg_distribution, on='sdg', how='left').fillna(0)

            # Reorder the SDGs based on the predefined list (self.all_sdgs)
            sdg_distribution['sdg'] = pd.Categorical(sdg_distribution['sdg'], categories=self.all_sdgs, ordered=True)
            sdg_distribution = sdg_distribution.sort_values('sdg')

            # Create the pie chart to show the percentage distribution of research outputs by SDG
            fig = px.pie(
                sdg_distribution,
                names='sdg',
                values='Percentage',
                title='Percentage of Research Outputs by SDG',
                color='sdg',
                color_discrete_map=sdg_colors,  # Apply SDG colors
                labels={'sdg': 'SDG', 'Percentage': 'Percentage of Total Outputs'},
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
    
    def create_geographical_heatmap(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']
        
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
                title="Geographical Distribution of Research Outputs",
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
                title="Geographical Distribution of Research Outputs",
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

    def create_sdg_research_chart(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        types = db_manager.get_unique_values('research_type')
        print(types)
        # Fetch filtered data from the database
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)

        # Prepare the DataFrame
        df_temp = df.copy()
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces

        # If the SDG dropdown value is not "ALL", filter the data accordingly
        if sdg_dropdown_value != "ALL":
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]
            # Group by 'year' and 'research_type' for this case
            counts = df_temp.groupby(['year', 'research_type']).size().reset_index(name='Count')
            
            # Create a bar chart with 'year' on the x-axis and stacked bars for research types
            fig = px.line(
                counts,
                x='year',  # Set x to 'year'
                y='Count',
                color='research_type',
                orientation='v',  # Vertical bars
                title=f'Research Type Distribution for {sdg_dropdown_value} Over Years',
                labels={
                    'Count': 'Number of Research Outputs',
                    'year': 'Year',
                    'research_type': 'Type of Research Output',
                },
                color_discrete_sequence=px.colors.qualitative.Dark2,  # Use Dark2 color palette
            )
        else:
            # Ensure 'Research Type' is treated as a categorical column with all types
            df_temp['research_type'] = pd.Categorical(df_temp['research_type'], categories=types)

            # Ensure 'sdg' is treated as a categorical column with all SDGs
            df_temp['sdg'] = pd.Categorical(df_temp['sdg'], categories=self.all_sdgs)

            # Group by 'sdg' and 'Research Type', counting the number of occurrences
            counts = df_temp.groupby(['sdg', 'research_type']).size().reset_index(name='Count')

            # Create a stacked bar chart with Plotly
            fig = px.bar(
                counts,
                x='Count',
                y='sdg',
                color='research_type',
                orientation='h',
                title='Research Type Distribution by SDG',
                labels={
                    'Count': 'Number of Research Outputs',
                    'sdg': 'Sustainable Development Goals (SDGs)',
                    'research_type': 'Type of Research Output'
                },
                color_discrete_sequence=px.colors.qualitative.Dark2,  # Use Dark2 color palette
                category_orders={'sdg': self.all_sdgs}  # Correctly reverse SDGs
            )

        # Customize layout
        fig.update_layout(
            title_font_size=18,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            legend_title=dict(text='Research Types'),
            barmode='stack',  # Ensure bars are stacked
            template="plotly_white",
            legend=dict(
                title=dict(font=dict(size=14)),
                traceorder="normal",
                yanchor="top",
                y=1.02,
                xanchor="left",
                x=1.05
            ),
        )

        return fig
    
    def create_sdg_status_chart(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        # Fetch filtered data from the database
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        df = df[df['journal'] != 'unpublished']
        df = df[df['status'] != 'PULLOUT']
        
        # Step 1: Create a temporary DataFrame
        df_temp = df.copy()

        # Step 2: Split SDGs by ';' and explode into separate rows
        df_temp['sdg'] = df_temp['sdg'].str.split(';')  # Split SDGs by ';'
        df_temp = df_temp.explode('sdg')  # Explode into separate rows for each SDG
        df_temp['sdg'] = df_temp['sdg'].str.strip()  # Remove unnecessary spaces

        # Step 3: Ensure all SDGs are included
        all_sdgs = ['SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 'SDG 8', 'SDG 9', 'SDG 10',
                    'SDG 11', 'SDG 12', 'SDG 13', 'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17']
        df_temp['sdg'] = pd.Categorical(df_temp['sdg'], categories=all_sdgs, ordered=True)

        # Define the correct order for statuses
        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED']
        df_temp['status'] = pd.Categorical(df_temp['status'], categories=status_order, ordered=True)

        # Step 4: Handle filtering based on sdg_dropdown_value
        if sdg_dropdown_value != "ALL":
            # Filter the DataFrame for the selected SDG
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]
            
            # Group by year and status to calculate counts
            status_distribution = df_temp.groupby(['year', 'status']).size().reset_index(name='Count')

            # Step 5: Normalize counts to calculate percentages
            status_distribution['Percentage'] = status_distribution.groupby('year')['Count'].transform(lambda x: (x / x.sum()) * 100)

            # Step 6: Create a bar chart with years on the x-axis
            fig = px.bar(
                status_distribution,
                x='year',  # Set x to 'year'
                y='Percentage',
                color='status',
                orientation='v',  # Vertical bars
                title=f"Research Status Distribution for {sdg_dropdown_value} Over Years",
                labels={'year': 'Year', 'Percentage': 'Percentage of Outputs', 'status': 'Research Status'},
                color_discrete_sequence=px.colors.qualitative.Dark2,  # Use Dark2 color palette
                category_orders={'status': status_order}  # Enforce the correct order of statuses
            )
        else:
            # Group by SDG and status to calculate counts for all SDGs
            status_distribution = df_temp.groupby(['sdg', 'status']).size().reset_index(name='Count')

            # Step 5: Normalize counts to calculate percentages
            status_distribution['Percentage'] = status_distribution.groupby('sdg')['Count'].transform(lambda x: (x / x.sum()) * 100)

            # Step 6: Create a stacked bar chart with SDGs on the y-axis
            fig = px.bar(
                status_distribution,
                x='Percentage',
                y='sdg',  # Set y to 'sdg'
                color='status',
                orientation='h',  # Horizontal bars
                title="Percentage of Research Outputs by Status for Each SDG",
                labels={'sdg': 'Sustainable Development Goals (SDGs)', 'Percentage': 'Percentage of Outputs', 'status': 'Research Status'},
                category_orders={'sdg': all_sdgs, 'status': status_order}  # Enforce the correct order of statuses
            )

        # Step 7: Customize the layout
        fig.update_layout(
            title_font_size=18,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            legend_title_font_size=14,
            template="plotly_white",
            xaxis=dict(title='Percentage of Outputs', showgrid=True),
            yaxis=dict(showgrid=True),
        )

        return fig


    def create_sdg_country_distribution_chart(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        # Fetch filtered data from the database
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        # Check if df is empty
        if df.empty:
            # If no data, return an empty figure or a message
            return px.line(title="No data available for the selected parameters.")

        # Step 1: Split the SDGs and explode into separate rows
        df_temp = df.copy()
        df_temp['sdg'] = df_temp['sdg'].str.split(';')
        df_temp = df_temp.explode('sdg')
        df_temp['sdg'] = df_temp['sdg'].str.strip()
        df_temp = df_temp[df_temp['country'] != 'Unknown Country']

        # Step 2: Handle filtering based on sdg_dropdown_value
        if sdg_dropdown_value != "ALL":
            # Filter the DataFrame for the selected SDG
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]
            
            # Step 3: Group by year and country to calculate counts
            sdg_country_distribution = df_temp.groupby(['year', 'country']).size().reset_index(name='Count')

            # Step 4: Create a bar chart with years on the x-axis
            fig = px.bar(
                sdg_country_distribution,
                x='year',  # Set x to 'year'
                y='Count',
                color='country',
                title=f'Research Output Distribution for {sdg_dropdown_value} Over Years by Country',
                labels={'year': 'Year', 'Count': 'Number of Research Outputs', 'country': 'Country'},
                color_discrete_map=self.sdg_colors,  # Use SDG colors
                barmode='stack'
            )
        else:
            # Step 3: Get unique countries
            countries = df_temp['country'].unique()

            # Step 4: Create complete combinations with all SDGs and countries
            complete_combinations = pd.MultiIndex.from_product([self.all_sdgs, countries], names=['sdg', 'country'])
            sdg_country_distribution = pd.DataFrame(index=complete_combinations).reset_index()

            # Step 5: Merge with counts
            counts = df_temp.groupby(['sdg', 'country']).size().reset_index(name='Count')
            sdg_country_distribution = sdg_country_distribution.merge(
                counts,
                on=['sdg', 'country'],
                how='left'
            )

            # Fill missing values with 0
            sdg_country_distribution['Count'].fillna(0, inplace=True)

            # Step 6: Create the visualization with SDG on the x-axis and country distribution stacked
            fig = px.bar(
                sdg_country_distribution,
                x='sdg',  # Set x to 'sdg'
                y='Count',
                color='country',
                title='Research Output Distribution by SDG and Country',
                labels={'sdg': 'Sustainable Development Goals (SDGs)',
                        'Count': 'Number of Research Outputs',
                        'country': 'Country'},
                color_discrete_map=self.sdg_colors,
                barmode='stack',
                category_orders={'sdg': self.all_sdgs}  # Ensures SDGs are shown in order
            )

        # Step 7: Customize the layout
        fig.update_layout(
            title_font_size=18,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            legend_title_font_size=14,
            template="plotly_white",
            xaxis=dict(showgrid=True, tickangle=45),
            yaxis=dict(title='Number of Research Outputs', showgrid=True),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=1.02
            )
        )

        return fig

    


    
    def create_sdg_conference_chart(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        print("Fetching filtered data...")
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        print("Initial DataFrame:\n", df.head())

        # Create a copy of the DataFrame
        df_temp = df.copy()

        print("Processing SDG column...")
        if 'sdg' not in df_temp.columns:
            print("Error: 'sdg' column is missing.")
            return go.Figure()

        # Safely split and explode the SDG column
        df_temp['sdg'] = df_temp['sdg'].str.split(';')
        df_temp = df_temp.explode('sdg').reset_index(drop=True)
        df_temp['sdg'] = df_temp['sdg'].str.strip()
        print("Processed SDG DataFrame:\n", df_temp.head())

        # Drop rows without a conference title
        if 'conference_title' not in df_temp.columns:
            print("Error: 'conference_title' column is missing.")
            return go.Figure()
        df_temp = df_temp[df_temp['conference_title'].notna()].reset_index(drop=True)
        print("After dropping rows without conference titles:\n", df_temp.head())

        if sdg_dropdown_value != "ALL":
            print(f"Filtering by SDG: {sdg_dropdown_value}")
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]
            print("Filtered DataFrame:\n", df_temp.head())

            print("Grouping data by year and SDG...")
            sdg_conference_distribution = df_temp.groupby(['year', 'sdg']).size().reset_index(name='Count')
            print("SDG Conference Distribution:\n", sdg_conference_distribution)

            fig = px.line(
                sdg_conference_distribution,
                x='year',
                y='Count',
                color='sdg',
                title=f"SDG Distribution by Conference Participation for {sdg_dropdown_value}",
                labels={'year': 'Year', 'Count': 'Number of Presentations', 'sdg': 'Sustainable Development Goals (SDGs)'},
                color_discrete_map=self.sdg_colors,
                markers=True
            )
        else:
            print("Aggregating data for all SDGs...")
            sdg_conference_distribution = df_temp.groupby('sdg').size().reset_index(name='Count')
            print("SDG Conference Distribution:\n", sdg_conference_distribution)

            print("Merging with all SDGs...")
            all_sdgs_df = pd.DataFrame(self.all_sdgs, columns=['sdg'])
            sdg_conference_distribution = pd.merge(all_sdgs_df, sdg_conference_distribution, on='sdg', how='left').fillna(0)
            print("After merging with all SDGs:\n", sdg_conference_distribution)

            fig = px.bar(
                sdg_conference_distribution,
                x='sdg',
                y='Count',
                title="SDG Distribution by Conference Participation",
                labels={'sdg': 'Sustainable Development Goals (SDGs)', 'Count': 'Number of Presentations'},
                color='Count',
                color_continuous_scale='Viridis',
                category_orders={'sdg': self.all_sdgs}  # Ensure consistent SDG order
            )

        print("Customizing chart layout...")
        fig.update_layout(
            title_font_size=18,
            xaxis_title_font_size=14,
            yaxis_title_font_size=14,
            legend_title_font_size=14,
            template="plotly_white",
            xaxis=dict(showgrid=True, tickangle=45),
            yaxis=dict(title='Number of Presentations', showgrid=True),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.5,
                xanchor="center",
                x=0.5
            ) if sdg_dropdown_value != "ALL" else None
        )

        print("Chart successfully created.")
        return fig
        
    def create_publication_type_chart(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)

        if sdg_dropdown_value != "ALL":
            # Step 2: Split SDGs by ';' and explode into separate rows
            df['sdg'] = df['sdg'].str.split(';')  # Split SDGs by ';'
            df = df.explode('sdg')  # Explode into separate rows for each SDG
            df['sdg'] = df['sdg'].str.strip()  # Remove unnecessary spaces
            df = df[df['sdg'] == sdg_dropdown_value]
            df = df[df['journal'] != 'unpublished']
            df = df[df['status'] != 'PULLOUT']

        publication_counts = df.groupby('journal').size().reset_index(name='Count')

        # Step 2: Create the pie chart
        fig = px.pie(
            publication_counts,
            values='Count',
            names='journal',
            title=f"Publication Type Distribution ({sdg_dropdown_value})",
            color_discrete_sequence=px.colors.qualitative.Dark2
        )

        # Step 3: Customize the layout
        fig.update_layout(
            title_font_size=18,
            legend_title_font_size=14,
            template="plotly_white",
            legend=dict(
                orientation='h',  # Legend displayed horizontally
                x=0.5,            # Position the legend in the center horizontally
                xanchor='center', # Anchor the legend to the center
                y=-0.2            # Place the legend below the chart
            )
        )

        return fig
    
    def create_local_foreign_pie_chart(self, selected_programs, selected_status, selected_years,sdg_dropdown_value):
        # Fetch filtered data from the database
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        if sdg_dropdown_value != "ALL":
            # Step 2: Split SDGs by ';' and explode into separate rows
            df['sdg'] = df['sdg'].str.split(';')  # Split SDGs by ';'
            df = df.explode('sdg')  # Explode into separate rows for each SDG
            df['sdg'] = df['sdg'].str.strip()  # Remove unnecessary spaces
            df = df[df['sdg'] == sdg_dropdown_value]
    
        # Step 1: Categorize as 'Local' or 'Foreign'
        # Assuming 'local_countries' is a list of local country names
        local_countries = ['Philippines']  # Update with your actual local countries
        df['location'] = df['country'].apply(lambda x: 'Local' if x in local_countries else 'Foreign')

        # Step 2: Create a pie chart based on the 'location' column
        fig = px.pie(
            df,
            names='location',
            title=f'Local vs Foreign Venues ({sdg_dropdown_value})',
            color='location',
            color_discrete_map={'Local': 'blue', 'Foreign': 'green'},
            labels={'location': 'Research Location'}
        )

        # Customize layout
        fig.update_layout(
            title_font_size=18,
            template="plotly_white",
            showlegend=True,
            legend_title_font_size=14
        )

        return fig
    
    def get_word_cloud(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)

        if sdg_dropdown_value !="ALL":
            # If sdg contains strings like "SDG1; SDG2"
            df['sdg'] = df['sdg'].str.split('; ')  # Split by semicolon and space
            sdg_df = df.explode('sdg')

            # Filter the DataFrame for the single SDG value
            filtered_sdg_df = sdg_df[sdg_df['sdg'] == str(sdg_dropdown_value)]

            # Concatenate all nouns into a single string
            all_nouns = ' '.join(
                [' '.join(nouns) if isinstance(nouns, list) else '' for nouns in filtered_sdg_df['top_nouns']]
            )
        else:
            # Concatenate all nouns into a single string
            all_nouns = ' '.join([' '.join(nouns) if isinstance(nouns, list) else '' for nouns in df['top_nouns']])

        # Generate the word cloud with higher resolution
        wordcloud = WordCloud(
            background_color='white',
            width=1600,
            height=800,
            max_words=200,
            stopwords=set(stopwords.words('english')), # Increase scale for higher resolution
        ).generate(all_nouns)

        # Create a Plotly figure
        fig = go.Figure()

        # Add the word cloud image to the figure
        fig.add_trace(go.Image(z=wordcloud.to_array()))

        # Update layout
        fig.update_layout(
            title=f"Common Topics for {sdg_dropdown_value}" if sdg_dropdown_value != "ALL" else "Common Topics for All SDGs",
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            margin=dict(l=20, r=20, t=50, b=20)
        )

        return fig
    
    def get_area_word_cloud(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        # Fetch the filtered data from the db_manager
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        
        # If sdg_dropdown_value is not "ALL", filter the DataFrame by the selected SDG
        if sdg_dropdown_value != "ALL":
            df = df[df['sdg'].str.contains(sdg_dropdown_value, case=False, na=False)]  # Filter based on selected SDG
            df['sdg'] = df['sdg'].str.split(';')  # Split SDGs by ';'

        # Create a temporary DataFrame by copying the filtered data
        df_temp = df.copy()

        # Split concatenated_areas by ';'
        df_temp['concatenated_areas'] = df_temp['concatenated_areas'].str.split(';')  # Split concatenated_areas by ';'

        # Explode SDGs and concatenated_areas into separate rows
        df_temp = df_temp.explode('sdg')  # Explode SDGs
        df_temp = df_temp.explode('concatenated_areas')  # Explode concatenated_areas

        # Remove unnecessary spaces in SDGs and concatenated_areas
        df_temp['sdg'] = df_temp['sdg'].str.strip()
        df_temp['concatenated_areas'] = df_temp['concatenated_areas'].str.strip()

        # Remove rows where concatenated_areas are NaN or empty strings
        df_temp = df_temp[df_temp['concatenated_areas'].notna() & (df_temp['concatenated_areas'] != '')]

        # Combine all concatenated areas into a single string
        combined_keywords = ' '.join(df_temp['concatenated_areas'].values)

        # Generate the word cloud for all concatenated areas
        wordcloud = WordCloud(width=1600, height=800, background_color='white').generate(combined_keywords)

        # Create a Plotly figure
        fig = go.Figure()

        # Add the word cloud image to the figure
        fig.add_trace(go.Image(z=wordcloud.to_array()))

        # Update layout
        fig.update_layout(
            title=f"Common Topics for SDG: {sdg_dropdown_value}" if sdg_dropdown_value != "ALL" else "Common Topics for All SDGs",
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
            margin=dict(l=20, r=20, t=50, b=20)
        )

        return fig
    
    

    def get_top_research_areas_per_year(self, selected_programs, selected_status, selected_years, sdg_dropdown_value, top_n=10):
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        if df.empty:
        # If no data, return an empty figure or a message
            return px.line(title="No data available for the selected parameters.")
        df['sdg'] = df['sdg'].str.split(';')  
        df['sdg'] = df['sdg'].apply(lambda x: [i.strip() for i in x])  
        df = df.explode('sdg')
        df_temp = df.copy()
        df_temp['concatenated_areas'] = df_temp['concatenated_areas'].str.split(';')  

        df_temp = df_temp.explode('concatenated_areas')

        df_temp['concatenated_areas'] = df_temp['concatenated_areas'].str.strip()

        df_temp = df_temp[df_temp['concatenated_areas'].notna() & (df_temp['concatenated_areas'] != '')]

        x_axis = 'sdg'
        if sdg_dropdown_value != "ALL":
            df_temp = df_temp[df_temp['sdg'] == sdg_dropdown_value]  
            x_axis = 'year'  

        area_distribution = df_temp.groupby([x_axis, 'concatenated_areas']).size().reset_index(name='count')
        if x_axis == 'year':
            area_distribution = area_distribution.sort_values(by=['year', 'count'], ascending=[True, False])
        else:
            area_distribution = area_distribution.sort_values(by=['count'], ascending=False)
        fig = px.scatter(
            area_distribution,
            x=x_axis,  
            y='concatenated_areas', 
            size='count',  
            color='concatenated_areas',  
            hover_name='concatenated_areas',  
            title=f"Research Areas per {'Year' if x_axis == 'year' else 'SDG'}",
            labels={x_axis: 'Year' if x_axis == 'year' else 'Sustainable Development Goals (SDGs)',
                    'concatenated_areas': 'Research Areas'},
            template='plotly_white', 
            height=600,
            category_orders={'year': sorted(area_distribution['year'].unique())} if x_axis == 'year' else {'sdg': self.all_sdgs}
        )
        fig.update_layout(
            xaxis_title="Year" if x_axis == 'year' else "SDG",
            yaxis_title="Research Areas",
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=80)
        )

        return fig
        
    def get_top10(self, selected_programs, selected_status, selected_years, sdg_dropdown_value):
        df = db_manager.get_filtered_data_bycollege(selected_programs, selected_status, selected_years)
        if df.empty:
        # If no data, return an empty figure or a message
            return px.line(title="No data available for the selected parameters.")
        df['sdg'] = df['sdg'].str.split(';').apply(lambda x: [i.strip() for i in x]) 
        if sdg_dropdown_value != "ALL":
            df = df.explode('sdg')
            df = df[df['sdg'] == sdg_dropdown_value]
        df_temp = df.copy()
        df_temp['concatenated_areas'] = df_temp['concatenated_areas'].str.split(';')  
        df_temp = df_temp.explode('concatenated_areas')
        df_temp['concatenated_areas'] = df_temp['concatenated_areas'].str.strip()
        df_temp = df_temp[df_temp['concatenated_areas'].notna() & (df_temp['concatenated_areas'] != '')]
        top10_areas = df_temp['concatenated_areas'].value_counts().head(10)
        top10_df = top10_areas.reset_index()
        top10_df.columns = ['concatenated_areas', 'Count']
        top10_df = top10_df.sort_values(by='Count', ascending=True)
        fig = go.Figure(data=[go.Bar(
            y=top10_df['concatenated_areas'],
            x=top10_df['Count'], 
            orientation='h', 
            marker=dict(color='royalblue') 
        )])
        fig.update_layout(
            title="Top 10 Research Areas",
            xaxis_title="Count",
            yaxis_title="Research Areas",
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=80)
        )
        return fig
    
    def get_top10_authors(self, selected_colleges, selected_status, selected_years, sdg_dropdown_value):
        df = db_manager.get_filtered_data_bycollege(selected_colleges, selected_status, selected_years)
        
        if df.empty:
            # If no data, return an empty figure or a message
            return px.line(title="No data available for the selected parameters.")
        df['sdg'] = df['sdg'].str.split(';').apply(lambda x: [i.strip() for i in x]) 
        if sdg_dropdown_value != "ALL":
            df = df.explode('sdg')
            df = df[df['sdg'] == sdg_dropdown_value]
        df_temp = df.copy()
        df_temp['concatenated_authors'] = df_temp['concatenated_authors'].str.split(';')  
        df_temp = df_temp.explode('concatenated_authors')
        df_temp['concatenated_authors'] = df_temp['concatenated_authors'].str.strip()
        df_temp = df_temp[df_temp['concatenated_authors'].notna() & (df_temp['concatenated_authors'] != '')]
        top10_authors = df_temp['concatenated_authors'].value_counts().head(10)
        top10_df = top10_authors.reset_index()
        top10_df.columns = ['Author', 'Count']
        top10_df = top10_df.sort_values(by='Count', ascending=True)
        fig = go.Figure(data=[go.Bar(
            y=top10_df['Author'], 
            x=top10_df['Count'],  
            orientation='h',  
            marker=dict(color='royalblue')  
        )])

        fig.update_layout(
            title="Top 10 Authors",
            xaxis_title="Count",
            yaxis_title="Authors",
            template="plotly_white",
            margin=dict(l=20, r=20, t=40, b=80)
        )

        return fig

    def update_figures(self,selected_programs, selected_status, selected_years,sdg_dropdown_value):
        fig3 = self.create_sdg_plot(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        fig4 = self.create_sdg_pie_chart(selected_programs, selected_status, selected_years, sdg_dropdown_value)

        return fig3, fig4

    def add_callbacks(self):
        @self.dash_app.callback(
        Output('college', 'value'),  # Update the checklist value
        Input('url', 'search'),  # Listen to URL changes
        prevent_initial_call=True   
        )
        def update_college_from_url(search):
            if not search:
                return self.default_colleges  # Default value if no parameters are provided

            # Parse the URL query parameters
            params = parse_qs(urlparse(search).query)

            # Extract the `college` parameter if it exists
            college_values = params.get('college', self.default_colleges)  # Returns a list or default
            self.college = college_values  # Dynamically update self.college

            return college_values

        @self.dash_app.callback(
        Output('program', 'options'),  # Update the program options based on the selected college
        Input('college', 'value')  # Trigger when the college checklist changes
        )
        def update_program_options(selected_colleges):
            # If no college is selected, return empty options
            if not selected_colleges:
                return []

            # Get the programs for the selected college
            program_options = db_manager.get_unique_values_by('program_id', 'college_id', selected_colleges[0])

            # Return the options for the program checklist
            return [{'label': program, 'value': program} for program in program_options]

        @self.dash_app.callback(
            [
                Output("program", "value"),
                Output("status", "value"),
                Output("years", "value"),
            ],
            Input("reset_button", "n_clicks"),
            prevent_initial_call=True
        )
        def reset_filters(n_clicks):
            return [], [], [db_manager.get_min_value('year'), db_manager.get_max_value('year')]
        
        # Callback to update content based on the user role and other URL parameters
        @self.dash_app.callback(

            Output('college-info', 'children'),
            Input('url', 'search')  # Capture the query string in the URL
        )
        def update_user_role_and_info(url_search):
            if url_search is None or url_search == '':
                return html.H3('Welcome Guest! Please log in.'), html.H3('College: Unknown'), html.H3('Program: Unknown')
            
            # Parse the URL parameters directly from the search
            params = dict((key, value) for key, value in (param.split('=') for param in url_search[1:].split('&')))
            
            user_role = params.get('user-role', '06')  # Default to 'guest' if no role is passed
            self.college = params.get('college', 'Unknown College')  # Default to 'Unknown College' if no college is passed
            self.program = params.get('program', 'Unknown Program')  # Default to 'Unknown Program' if no program is passed

            self.default_programs = db_manager.get_unique_values_by('program_id','college_id',self.college)
            print(f'self.default_programs: {self.default_programs}\ncollege: {self.college}')

            # Return the role, college, and program information
            return html.H3(
                    f'College Department: {self.college}', 
                    style={
                        'textAlign': 'center',
                        'marginTop': '10px'
                    }
                )
        
        @self.dash_app.callback(
            Output("shared-data-store", "data"),
            Input("data-refresh-interval", "n_intervals")
        )
        def refresh_shared_data_store(n_intervals):
            updated_data = db_manager.get_all_data()
            return updated_data.to_dict('records')
        
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
            Output('sdg-time-series', 'figure'),
            Output('sdg-pie-distribution', 'figure'),
            ],
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_all(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.update_figures(selected_programs, selected_status, selected_years,sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('sdg-map', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_geographical_heatmap(selected_programs, selected_status, selected_years,sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('sdg-research-type', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig1(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_research_chart(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('sdg-status', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig2(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_status_chart(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('sdg-conference', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig3(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_conference_chart(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('sdg-publication-type', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig4(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_publication_type_chart(selected_programs, selected_status, selected_years, sdg_dropdown_value)

        @self.dash_app.callback(
            Output('sdg-countries', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig5(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_sdg_country_distribution_chart(selected_programs, selected_status, selected_years, sdg_dropdown_value)

        @self.dash_app.callback(
            Output('sdg-local-foreign-pie', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig6(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.create_local_foreign_pie_chart(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('keywords-cloud', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig7(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.get_word_cloud(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('research-area-cloud', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig8(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.get_top_research_areas_per_year(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('top-research-area', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig9(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.get_top10(selected_programs, selected_status, selected_years, sdg_dropdown_value)
        
        @self.dash_app.callback(
            Output('top-authors', 'figure'),
            [Input('program', 'value'), 
             Input('status', 'value'), 
             Input('years', 'value'),
             Input('sdg-dropdown', 'value')]
        )
        def update_fig8(selected_programs, selected_status, selected_years,sdg_dropdown_value):
            selected_programs = default_if_empty(selected_programs, self.default_programs)
            selected_status = default_if_empty(selected_status, self.default_statuses)
            selected_years = selected_years if selected_years else self.default_years
            return self.get_top10_authors(selected_programs, selected_status, selected_years, sdg_dropdown_value)