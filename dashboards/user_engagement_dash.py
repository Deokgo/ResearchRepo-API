from dash import callback_context
import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, html
from components.DashboardHeader import DashboardHeader
from components.Tabs import Tabs
from components.KPI_Card import KPI_Card
from components.CollageContainer import CollageContainer
from dash import dcc
from urllib.parse import parse_qs, urlparse
from . import view_manager,db_manager
from datetime import datetime, timedelta
from database.engagement_queries import get_user_engagement_summary,get_top_10_users_by_unique_views,get_engagement_over_time,get_top_10_research_ids_by_downloads, get_research_funnel_data,get_top_10_research_ids_by_views, get_funnel_data, get_engagement_by_day_of_week, get_engagement_summary,get_user_funnel_data, get_top_10_users_by_engagement, get_top_10_users_by_downloads
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import dash



def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

class UserEngagementDash:
    def __init__(self, server, title=None, college=None, program=None, **kwargs):
        self.dash_app = Dash(
            __name__,
            server=server,
            url_base_pathname=kwargs.get('url_base_pathname', '/engage/'),
            external_stylesheets=[dbc.themes.BOOTSTRAP, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"]
        )
        self.title = title
        self.college = college
        self.program = program

        self.palette_dict = view_manager.get_college_colors()
        self.default_colleges = view_manager.get_unique_values('college_id')
        self.default_programs = []
        self.default_statuses = view_manager.get_unique_values('status')
        self.default_years = [view_manager.get_min_value('year'), view_manager.get_max_value('year')]

        self.all_sdgs = [
            'SDG 1', 'SDG 2', 'SDG 3', 'SDG 4', 'SDG 5', 'SDG 6', 'SDG 7', 
            'SDG 8', 'SDG 9', 'SDG 10', 'SDG 11', 'SDG 12', 'SDG 13', 
            'SDG 14', 'SDG 15', 'SDG 16', 'SDG 17'
        ]

        self.set_layout()
        self.add_callbacks()

    def set_layout(self):

        college = html.Div([  # Added array brackets
            dbc.Label("Select College:", style={"color": "#08397C"}),
            dbc.Checklist(
                id="college",
                options=[{'label': value, 'value': value} for value in view_manager.get_unique_values('college_id')],
                value=[],
                inline=True,
            ),
        ], className="mb-4",id="college-div", style={"display": "block"})

        date_range = html.Div([  # Added array brackets
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
        ], className="mb-4", style={"display": "block"})

        text_display = dbc.Container([
            # First row (2 KPI Cards)
            dbc.Row(
                [
                    dbc.Col(KPI_Card("Total Views", "0", id="kpi-total-views", icon="fas fa-eye", color="success"), width=2),
                    dbc.Col(KPI_Card("Unique Views", "0", id="kpi-unique-views", icon="fas fa-user-check", color="primary"), width=2),
                    dbc.Col(KPI_Card("Downloads", "0", id="kpi-downloads", icon="fas fa-download", color="info"), width=2),
                    dbc.Col(KPI_Card("Active Users", "0", id="kpi-avg-views", icon="fas fa-user-group", color="warning"), width=2),
                ],
                className="g-3",
                justify="center"
            )
        ], className="p-0")


        self.collage = html.Div([
            dbc.Container(
                children=[
                    # Upper row with the college line plot and KPI cards
                    dbc.Row(
                        [
                            # College Line Plot
                            dbc.Col(
                                dbc.Card(
                                    dcc.Graph(
                                        id='college_line_plot',
                                        config={'responsive': True},  # Ensure the graph is responsive
                                        style={
                                            "height": "90%",  # Apply scaling to height (scale = 0.9)
                                            "width": "90%",   # Apply scaling to width (scale = 0.9)
                                            "maxHeight": "350px",  # Optional: limit max height if needed
                                            "maxWidth": "100%"    # Optional: limit max width if needed
                                        }
                                    ),
                                    body=True
                                ),
                                width="auto",  # Adjust to 50% width to align with KPI cards
                                className='p-0'  # Remove padding
                            )
                        ],
                        className="g-0",  # Remove gutter space between columns
                        justify="center"
                    ),
                    # Lower row with the funnel-chart and active-days
                    dbc.Row(
                        [
                            dbc.Col(
                                dbc.Card(
                                    dbc.Tabs([
                                        dbc.Tab(
                                            dcc.Graph(id='user-funnel-chart'),
                                            label="User Funnel"
                                        ),
                                        dbc.Tab(
                                            dcc.Graph(id='research-funnel-chart'),
                                            label="Research Funnel"
                                        )
                                    ])
                                ),
                                width="auto",
                                className='p-2',
                                style={"margin-right": "5px"}
                            ),
                            dbc.Col(
                                dbc.Card(
                                    dcc.Graph(
                                        id='active-days'
                                    )
                                ),
                                width="auto",  # Automatically adjust width
                                className='p-2',  # Remove padding
                                style={"margin-left": "5px"}
                            )
                        ],
                        className="g-0",
                        justify="center"
                    )
                ],
                style={
                    "display": "flex",
                    "flex-direction": "column",  # Stack the rows vertically
                    "justify-content": "center",  # Center horizontally
                    "margin": "5px",
                    "width": "100%",
                    "height": "100%"  # Ensure it takes full height
                }
            )
        ])


        # Define the modal component
        # Modal Component (Content updates dynamically)
        modal = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(id="modal-title")),  # Dynamic Title
                dbc.ModalBody([
                    html.Div(id="modal-body"),  # Dynamic KPI Description
                    dcc.Graph(id="kpi-graph"),  # Dynamic Graph
                ]),
                dbc.ModalFooter(
                    dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)
                ),
            ],
            id="kpi-modal",
            is_open=False,  # Start closed
            size="xl",  # Large modal for better graph view
        )

        
        



        sidebar = dbc.Col([  # Added array brackets
            html.H4("Filters", style={"margin": "10px 0px", "color": "red"}),
            date_range,
            college
        ], width=2, className="p-3", 
        style={"background": "#d3d8db", "height": "100vh", "position": "fixed", "left": 0, "top": 0, "zIndex": 1000})

        main_content = dbc.Col([  # Added array brackets
            dcc.Location(id="url", refresh=False),
            html.Div(id="dynamic-header"),
            dbc.Row([text_display], style={"flex": "1"}),
            modal,
            self.collage
        ], width=10, className="p-3", style={"marginLeft": "16.67%"})

        self.dash_app.layout = dbc.Container([
            dcc.Interval(id="data-refresh-interval", interval=1000, n_intervals=0),
            dbc.Row([sidebar, 
                     main_content], className="g-0")
        ], fluid=True,style={
            "paddingBottom": "0px",
            "marginBottom": "0px",
            "overflow": "hidden",
            "height": "100vh",
            "width": "100vw",
            "display": "flex",
            "flexDirection": "column"})

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
    
    def update_line_plot(self, selected_colleges, start_date, end_date):
        # Ensure selected_colleges is a standard Python list or array
        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()  # Convert NumPy array to list
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]  # Ensure single college is in a list
        
        # Fetch data using get_engagement_over_time
        # Assuming get_engagement_over_time returns a list of tuples [(date, total_views, total_unique_views, total_downloads), ...]
        engagement_data = get_engagement_over_time(start_date, end_date, selected_colleges)

        if not engagement_data:
            print("Debug: Engagement data is empty.")
            return px.line(title='Views and Downloads Over Time').update_layout(
                annotations=[{
                    'text': "No data available to chart for the selected colleges and date range.",
                    'xref': 'paper', 'yref': 'paper',
                    'x': 0.5, 'y': 0.5,
                    'showarrow': False,
                    'font': {'size': 16, 'color': 'red'}
                }]
            )

        # Convert data to DataFrame
        df = pd.DataFrame(engagement_data, columns=['engagement_date', 'total_views', 'total_unique_views', 'total_downloads'])


        # Ensure 'engagement_date' is in datetime format
        df['engagement_date'] = pd.to_datetime(df['engagement_date'], errors='coerce')
        if df['engagement_date'].isnull().any():
            print("Debug: Some engagement dates could not be converted.")

        # Generate a full date range for reindexing
        full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        df = df.set_index('engagement_date').reindex(full_date_range).reset_index()
        df.columns = ['date', 'total_views', 'total_unique_views', 'total_downloads']

        # Fill missing values with 0
        df = df.fillna(0)

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
                    title='User Engagement Over Time (Views, Downloads, Unique Views)',
                    labels={'date': 'Date', 'Count': 'Count', 'Metric': 'Metric'})

        # Set the figure layout to be responsive to its container
        fig.update_layout(
            autosize=True,  # Allow the figure to automatically resize
            margin=dict(l=40, r=40, t=40, b=40),  # Adjust margins for better presentation
            height=230,  # Set a fixed height for the figure
            width=1200,  # Use a fixed pixel width (e.g., 800px)
            # Adjust legend position below the graph
            legend=dict(
                orientation='h',  # Vertical layout for legend
                y=-0.35,  # Position it at the bottom of the graph
                x=0,  # Position it at the left of the graph
                xanchor='left',  # Align the legend to the left of the x position
                yanchor='bottom',  # Align the legend to the bottom of the y position
            ),
        )
        

        return fig
    
    def create_conversion_funnel(self, selected_colleges, start_date, end_date):

        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()  # Convert NumPy array to list
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]  # Ensure single college is in a list

        # Get funnel data from the database
        funnel_data = get_funnel_data(start_date, end_date, college_ids=selected_colleges)

        if not funnel_data:
            print("Debug: Funnel data is empty or could not be fetched.")
            return go.Figure()

        # Convert funnel data to a DataFrame for processing
        df = pd.DataFrame(funnel_data)

        # Check if data is empty
        if df.empty:
            print("Debug: Filtered DataFrame is empty.")
            return go.Figure()

        # Check if necessary columns exist in the fetched data
        if not all(col in df.columns for col in ['stage', 'total_views']):
            print("Debug: Missing necessary columns in the data.")
            return go.Figure()

        # Aggregate the data to ensure one record per stage
        funnel_data = df.groupby('stage', as_index=False).agg({
            'total_views': 'sum'
        })

        # Rename stages to match the funnel steps
        stage_mapping = {
            'Total Views': 'total_views',
            'Total Unique Views': 'total_unique_views',
            'Total Downloads': 'total_downloads'
        }

        funnel_data['Metric'] = funnel_data['stage'].map(stage_mapping)

        # Filter out any unmapped stages
        funnel_data = funnel_data.dropna(subset=['Metric'])

        # Reorder the data
        funnel_data['Metric'] = pd.Categorical(funnel_data['Metric'], 
                                            categories=['total_views', 'total_unique_views', 'total_downloads'], 
                                            ordered=True)
        funnel_data = funnel_data.sort_values('Metric')

        # Create the horizontal funnel chart using Plotly
        fig = px.funnel(funnel_data, 
                        x='total_views', 
                        y='Metric', 
                        orientation='h',  # Set the funnel to horizontal
                        title='Engagement Funnel: Views, Unique Views, and Downloads',
                        labels={'Metric': 'Stage', 'total_views': 'Count'})
        
        # Update layout to make the funnel smaller
        fig.update_layout(
            height=200,  # Set a smaller height for the funnel chart
            width=600,   # Set a smaller width for the funnel chart
            title_x=0.5,  # Center the title
            title_y=0.95,  # Move title slightly up
            margin=dict(l=5, r=5, t=30, b=5),  # Adjust margins for a smaller layout
            showlegend=False  # Hide legend as it is unnecessary for funnel charts
        )


        return fig
    
    def create_user_funnel(self,selected_colleges, start_date, end_date):
        """Generates a user-focused engagement funnel visualization using Plotly."""
        
        # Ensure selected_colleges is a list
        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]

        # Fetch funnel data
        funnel_data = get_user_funnel_data(start_date, end_date, college_ids=selected_colleges)

        if not funnel_data:
            print("Debug: User funnel data is empty or could not be fetched.")
            return go.Figure()

        # Convert to DataFrame
        df = pd.DataFrame(funnel_data)

        # Check if necessary columns exist
        if not all(col in df.columns for col in ['stage', 'total']):
            print("Debug: Missing necessary columns in user funnel data.")
            return go.Figure()

        # Map stages to metric names
        stage_mapping = {
            'Total User Interactions': 'total_views',
            'Total Unique Users Viewed': 'total_unique_views',
            'Total Users Downloaded': 'total_downloads'
        }

        df['Metric'] = df['stage'].map(stage_mapping)
        df = df.dropna(subset=['Metric'])

        # Set correct order
        df['Metric'] = pd.Categorical(df['Metric'], 
                                    categories=['total_views', 'total_unique_views', 'total_downloads'], 
                                    ordered=True)
        df = df.sort_values('Metric')

        # Create funnel chart
        fig = px.funnel(df, 
                        x='total', 
                        y='Metric', 
                        orientation='h',  
                        title='User Engagement Funnel: Views, Unique Views, Downloads',
                        labels={'Metric': 'Stage', 'total': 'Count'})
        
        # Update layout
        fig.update_layout(
            height=200,
            width=600,
            title_x=0.5,
            title_y=0.95,
            margin=dict(l=5, r=5, t=30, b=5),
            showlegend=False
        )

        return fig

    
    def create_area_chart(self, selected_colleges, start_date, end_date):

        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()  # Convert NumPy array to list
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]  # Ensure single college is in a list

        # Get engagement data from the database
        engagement_data = get_engagement_by_day_of_week(start_date, end_date, selected_colleges)
        print(engagement_data)
        
        if not engagement_data:
            print("Debug: Engagement data is empty.")
            return go.Figure()
        
        # Convert to DataFrame
        df = pd.DataFrame(engagement_data)
        print("this is the df:", df)
        
        # Strip any leading or trailing spaces from 'day_of_week'
        df['day_of_week'] = df['day_of_week'].str.strip()

        # Ensure that 'day_of_week' is a categorical variable with the correct order
        day_of_week_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=day_of_week_order, ordered=True)

        # Sort the DataFrame by day of the week
        df = df.sort_values('day_of_week')
        print("this is after", df)
        
        # Create the bubble chart using Plotly Express
        fig = px.scatter(
            df,
            x='day_of_week',
            y='total_downloads',  # You can replace with another column if needed
            size='total_views',  # Bubble size based on total views
            title='Total Downloads by Day of the Week (Bubble Chart)',
            labels={'day_of_week': 'Day of Week', 'total_downloads': 'Total Downloads'},
            color='day_of_week',  # Optional: Color by day of the week
            hover_name='day_of_week',  # Hover over the day of the week
            hover_data=['total_views', 'total_downloads']  # Hover data with views and downloads
        )
        
        # Customize the layout to adjust bubble size
        fig.update_traces(
            marker=dict(
                sizemode='area', 
                opacity=0.6, 
                sizeref=0.1  # Adjust the sizeref value to scale the size of bubbles
            )
        )
        fig.update_layout(title='Most Active Days of the Week', template='plotly_white')
        # Update layout to make the funnel smaller
        fig.update_layout(
            height=230,  # Set a smaller height for the funnel chart
            width=600,   # Set a smaller width for the funnel chart
            title_x=0.5,  # Center the title
            title_y=0.95,  # Move title slightly up
            margin=dict(l=5, r=5, t=30, b=5),  # Adjust margins for a smaller layout
            showlegend=False  # Hide legend as it is unnecessary for funnel charts
        )

        return fig
    
    def top_10_research_views(self, selected_colleges, start_date, end_date, view_type='total_unique_views'):
        """Fetches the top 10 research outputs by views and creates a table."""

        # Ensure selected_colleges is a standard Python list or array
        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()  # Convert NumPy array to list
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]  # Ensure single college is in a list

        # Check if selected_colleges is empty
        if not selected_colleges:
            raise ValueError("No colleges selected.")
        
        # Call get_top_10_research_ids_by_views to get the top 10 research IDs by views
        top_views_data = get_top_10_research_ids_by_views(start_date, end_date, selected_colleges, view_type)
        
        # Check if the data is empty
        if not top_views_data:
            print("Debug: No data available to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Convert the result to a DataFrame
        df = pd.DataFrame(top_views_data)

        # Check if the DataFrame has the expected columns
        if 'research_id' not in df.columns or 'total_value' not in df.columns:
            raise ValueError("The data does not contain the expected columns: 'research_id' and 'total_value'.")

        # Ensure the DataFrame is not empty
        if df.empty:
            print("Debug: No valid data in the DataFrame to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Sort DataFrame by total views in descending order
        df = df.sort_values(by='total_value', ascending=False)

        # Assign ranks with ties having the same rank
        df['Rank'] = df['total_value'].rank(method='min', ascending=False).astype(int)

        # Create table
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=["Rank", "Research ID", "Total Views"],
                fill_color='lightgray',
                align='center'
            ),
            cells=dict(
                values=[df['Rank'], df['research_id'], df['total_value']],
                fill_color='white',
                align='center'
            )
        )])

        fig.update_layout(
            title=f"Top 10 Research Outputs by {view_type.replace('_', ' ').title()}",
            title_x=0.5
        )

        return fig
    
    def top_10_users_download(self, selected_colleges, start_date, end_date):
        """Generates a table visualization for the top 10 users by downloads."""
        
        # Ensure selected_colleges is a standard Python list or array
        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()  # Convert NumPy array to list
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]  # Ensure single college is in a list

        # Check if selected_colleges is empty
        if not selected_colleges:
            raise ValueError("No colleges selected.")

        # Call get_top_10_users_by_downloads to get the top 10 users by download
        top_users_data = get_top_10_users_by_downloads(start_date, end_date, selected_colleges)
        
        # Check if the data is empty
        if not top_users_data:
            print("Debug: No data available to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Convert the result to a DataFrame
        df = pd.DataFrame(top_users_data)

        # Check if the DataFrame has the expected columns
        if 'user_id' not in df.columns or 'total_downloads' not in df.columns:
            raise ValueError("The data does not contain the expected columns: 'user_id' and 'total_downloads'.")

        # Ensure the DataFrame is not empty
        if df.empty:
            print("Debug: No valid data in the DataFrame to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Create a table visualization of the data using Plotly
        fig = go.Figure(data=[go.Table(
            header=dict(values=["User ID", "Total Downloads"]),
            cells=dict(values=[df['user_id'], df['total_downloads']])
        )])

        fig.update_layout(
            title="Top 10 Active Users by Downloads",
            title_x=0.5
        )

        return fig
    
    def top_10_users_engagement(self, selected_colleges, start_date, end_date):
        # Ensure selected_colleges is a standard Python list or array
        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()  # Convert NumPy array to list
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]  # Ensure single college is in a list

        # Check if selected_colleges is empty
        if not selected_colleges:
            raise ValueError("No colleges selected.")

        # Call get_top_10_users_by_engagement to get the top 10 users by engagement
        top_users_data = get_top_10_users_by_engagement(start_date, end_date, selected_colleges)
        
        # Check if the data is empty
        if not top_users_data:
            print("Debug: No data available to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Convert the result to a DataFrame
        df = pd.DataFrame(top_users_data)

        # Check if the DataFrame has the expected columns
        if 'user_id' not in df.columns or 'total_views' not in df.columns:
            raise ValueError("The data does not contain the expected columns: 'user_id' and 'total_views'.")

        # Ensure the DataFrame is not empty
        if df.empty:
            print("Debug: No valid data in the DataFrame to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Create a table visualization of the data using Plotly
        fig = go.Figure(data=[go.Table(
            header=dict(values=["User ID", "Total Views"]),
            cells=dict(values=[df['user_id'], df['total_views']])
        )])

        fig.update_layout(
            title="Top 10 Active Users by Engagement",
            title_x=0.5
        )

        return fig
    
    def top_10_research_downloads(self, selected_colleges, start_date, end_date):
        # Ensure selected_colleges is a standard Python list or array
        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()  # Convert NumPy array to list
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]  # Ensure single college is in a list

        # Check if selected_colleges is empty
        if not selected_colleges:
            raise ValueError("No colleges selected.")

        # Call get_top_10_research_ids_by_downloads to get the top 10 research IDs by downloads
        top_downloads_data = get_top_10_research_ids_by_downloads(start_date, end_date, selected_colleges)
        
        # Check if the data is empty
        if not top_downloads_data:
            print("Debug: No data available to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Convert the result to a DataFrame
        df = pd.DataFrame(top_downloads_data)

        # Check if the DataFrame has the expected columns
        if 'research_id' not in df.columns or 'total_downloads' not in df.columns or 'previous_total_downloads' not in df.columns or 'trend' not in df.columns:
            raise ValueError("The data does not contain the expected columns: 'research_id', 'total_downloads', 'previous_total_downloads', and 'trend'.")

        # Ensure the DataFrame is not empty
        if df.empty:
            print("Debug: No valid data in the DataFrame to display.")
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Sort DataFrame by total downloads in descending order
        df = df.sort_values(by='total_downloads', ascending=False)
        print(df)
        
        # Assign ranks with ties having the same rank
        df['Rank'] = df['total_downloads'].rank(method='min', ascending=False).astype(int)

        # Create table
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=["Rank", "Research ID", "Total Downloads"],
                fill_color='lightgray',
                align='center'
            ),
            cells=dict(
                values=[df['Rank'], df['research_id'], df['total_downloads']],
                fill_color='white',
                align='center'
            )
        )])

        fig.update_layout(
            title="Top 10 Research Outputs by Downloads",
            title_x=0.5
        )

        return fig
    
    def create_research_funnel(self,selected_colleges, start_date, end_date):
        """Generates a research-focused engagement funnel visualization using Plotly."""
        
        # Ensure selected_colleges is a list
        if isinstance(selected_colleges, np.ndarray):
            selected_colleges = selected_colleges.tolist()
        elif isinstance(selected_colleges, str):
            selected_colleges = [selected_colleges]

        # Fetch funnel data
        funnel_data = get_research_funnel_data(start_date, end_date, college_ids=selected_colleges)

        if not funnel_data:
            print("Debug: Research funnel data is empty or could not be fetched.")
            return go.Figure()

        # Convert to DataFrame
        df = pd.DataFrame(funnel_data)

        # Check if necessary columns exist
        if not all(col in df.columns for col in ['stage', 'total']):
            print("Debug: Missing necessary columns in research funnel data.")
            return go.Figure()

        # Map stages to metric names
        stage_mapping = {
            'Total Research Papers Viewed': 'total_views',
            'Total Unique Research Papers Viewed': 'total_unique_views',
            'Total Research Papers Downloaded': 'total_downloads'
        }

        df['Metric'] = df['stage'].map(stage_mapping)
        df = df.dropna(subset=['Metric'])

        # Set correct order
        df['Metric'] = pd.Categorical(df['Metric'], 
                                    categories=['total_views', 'total_unique_views', 'total_downloads'], 
                                    ordered=True)
        df = df.sort_values('Metric')

        # Create funnel chart
        fig = px.funnel(df, 
                        x='total', 
                        y='Metric', 
                        orientation='h',  
                        title='Research Engagement Funnel: Views, Unique Views, Downloads',
                        labels={'Metric': 'Stage', 'total': 'Count'})
        
        # Update layout
        fig.update_layout(
            height=200,
            width=600,
            title_x=0.5,
            title_y=0.95,
            margin=dict(l=5, r=5, t=30, b=5),
            showlegend=False
        )

        return fig
    
    def create_top_10_users_by_unique_views_chart(self, start_date, end_date, college_ids=None):
        """Fetches the top 10 users by distinct research views and creates a table."""

        # Get top 10 users by distinct research views using the previously created function
        top_users_data = get_top_10_users_by_unique_views(start_date, end_date, college_ids)

        # Check if the data is empty
        if not top_users_data:
            fig = go.Figure()
            fig.add_annotation(
                text="No data available for the selected colleges and date range.",
                xref='paper', yref='paper',
                x=0.5, y=0.5,
                showarrow=False,
                font={'size': 12, 'color': 'red'}
            )
            return fig

        # Convert the list of dictionaries to a pandas DataFrame for easier manipulation
        df = pd.DataFrame(top_users_data)

        # Check if the DataFrame contains the expected columns
        if 'user_id' not in df.columns or 'distinct_research_count' not in df.columns:
            raise ValueError("The data does not contain the expected columns: 'user_id' and 'distinct_research_count'.")

        # Create a table visualization
        fig = go.Figure(data=[go.Table(
            header=dict(values=["User ID", "Distinct Research Views"]),
            cells=dict(values=[df['user_id'], df['distinct_research_count']])
        )])

        fig.update_layout(
            title="Top 10 Users by Distinct Research Views",
            title_x=0.5
        )

        return fig

    def add_callbacks(self):
        # Callback for reset button

        
        @self.dash_app.callback(
            [Output("dynamic-header", "children"),
             Output('college', 'value'),
            Output('college-div', 'style')  ],
            Input("url", "search"),  # Extracts the query string (e.g., "?user=John&role=Admin")
            prevent_initial_call=True  
        )
        def update_header(search):
            if search:
                params = parse_qs(search.lstrip("?"))  # Parse query parameters
                user_role = params.get("user-role",["Guest"])[0]
                college = params.get("college", [""])[0]
                program = params.get("program", [""])[0]

            view=""
            style=None

            if user_role == "02":
                view="RPCO Director"
                style = {"display": "block"}
                college = ""
                program = ""
            elif user_role =="04":
                view="College Dean"
                style ={"display": "none"}
                self.college = college
                self.program = program
            else:
                view="Unknown"
            return DashboardHeader(left_text=f"{college}", title=f"USER ENGAGEMENT DASHBOARD", right_text=view), college, style

        @self.dash_app.callback(
            [
                Output("kpi-total-views", "children"),
                Output("kpi-unique-views", "children"),
                Output("kpi-downloads", "children"),
                Output("kpi-avg-views", "children")
            ],
            [
                Input("data-refresh-interval", "n_intervals"),
                Input("college", "value"),
                Input("date-range-dropdown", "value"),
                Input('url', 'search')
            ]
        )
        def refresh_text_display(n_intervals, selected_colleges, selected_range, search):
            if search:
                params = parse_qs(search.lstrip("?"))  # Parse query parameters
                user_role = params.get("user-role",["Guest"])[0]
                college = params.get("college", [""])[0]
                program = params.get("program", [""])[0]
                self.college = college
                self.program = program
            print(f"🔄 Refresh triggered! Interval: {n_intervals}")
            print(f"📌 Colleges selected: {selected_colleges}")
            print(f"📌 Date Range selected: {selected_range}")

            if user_role =="04":
                selected_colleges = [college]
            else:
                selected_colleges = list(default_if_empty(selected_colleges, self.default_colleges))
            
            # Get the start and end date from the selected range
            start, end = self.get_date_range(selected_range)
            print(f"📅 Date range applied: {start} to {end}")

            # Fetch engagement data
            engagement_data = get_engagement_summary(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), selected_colleges)
            users_data = get_user_engagement_summary(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), selected_colleges)
            if not users_data:
                active_users=0
            else:
                active_users = len(set(item["user_id"] for item in users_data))  

            # If no data is returned, set default values
            if not engagement_data:
                total_views = total_unique_views = total_downloads = 0
            else:
                total_views = sum(item["total_views"] for item in engagement_data)
                total_unique_views = sum(item["total_unique_views"] for item in engagement_data)
                total_downloads = sum(item["total_downloads"] for item in engagement_data)
                


            print(f"📊 Total Views: {total_views}, Unique Views: {total_unique_views}, Downloads: {total_downloads}")

            # Return updated KPI values
            return (
                [ html.H5(f"{total_views}", className="mb-0")],
                [ html.H5(f"{total_unique_views}", className="mb-0")],
                [ html.H5(f"{total_downloads}", className="mb-0")],
                [ html.H5(f"{active_users}", className="mb-0")]
            )
        @self.dash_app.callback(
            Output('college_line_plot', 'figure'),
            [
                Input('college', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
              # Default to last 7 days
            start,end = self.get_date_range(selected_range)
           
            return self.update_line_plot(selected_colleges,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        @self.dash_app.callback(
            Output('user-funnel-chart', 'figure'),
            [
                Input('college', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            start,end = self.get_date_range(selected_range)
            return self.create_user_funnel(selected_colleges, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        @self.dash_app.callback(
            Output('research-funnel-chart', 'figure'),
            [
                Input('college', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges,selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            start,end = self.get_date_range(selected_range)
            return self.create_research_funnel(selected_colleges, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        @self.dash_app.callback(
            Output('active-days', 'figure'),
            [
                Input('college', 'value'),
                Input('date-range-dropdown', 'value')
            ]
        )
        def update_linechart(selected_colleges, selected_range):
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            start,end = self.get_date_range(selected_range)
           
            return self.create_area_chart(selected_colleges,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        
        @self.dash_app.callback(
            [Output("kpi-modal", "is_open"), 
            Output("modal-title", "children"), 
            Output("modal-body", "children"),
            Output("kpi-graph", "figure")],  # Graph update
            [Input("btn-kpi-total-views", "n_clicks"),
            Input("btn-kpi-unique-views", "n_clicks"),
            Input("btn-kpi-downloads", "n_clicks"),
            Input("btn-kpi-avg-views", "n_clicks"),
            Input("close-modal", "n_clicks")],  # Close button
            [State('college', 'value'), 
            State('date-range-dropdown', 'value')],  # Additional filter parameters
            prevent_initial_call=True
        )
        def toggle_modal(*args):
            ctx = dash.callback_context
            if not ctx.triggered:
                return False, "", "", go.Figure()

            button_id = ctx.triggered[0]["prop_id"].split(".")[0]

            # If close button is clicked, close the modal
            if button_id == "close-modal":
                return False, "", "", go.Figure()

            # Extract filter parameters
            selected_colleges, selected_range = args[-2:]
            selected_colleges = default_if_empty(selected_colleges, self.default_colleges)
            start,end = self.get_date_range(selected_range)

            # Determine which function to use for the figure
            title, body, fig = "", "", go.Figure()
            
            if button_id == "btn-kpi-total-views":
                fig1 = self.top_10_research_views(selected_colleges,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'),view_type='total_views')
                body = dbc.Row([ # First column for KPI Description
                        dbc.Col(dcc.Graph(figure=fig1, id="kpi-graph1"), width="auto" ),  # Second column for the Graph
                    ],justify="center")
                title = "Top 10 Research Outputs (Overall Views)"
               

            elif button_id == "btn-kpi-downloads":
                fig1 = self.top_10_users_download(selected_colleges,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
                fig2 = self.top_10_research_downloads(selected_colleges,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
                body = dbc.Row([
                        dbc.Col(dcc.Graph(figure=fig2, id="kpi-graph2"), width=6),  # First column for KPI Description
                        dbc.Col(dcc.Graph(figure=fig1, id="kpi-graph3"), width=6),  # Second column for the Graph
                    ],justify="center")
                title = "Top 10 Research Outputs (Downloads)"

            elif button_id == "btn-kpi-unique-views":
                fig2 = self.top_10_research_views(selected_colleges,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'),view_type='total_unique_views')
                fig1 = self.create_top_10_users_by_unique_views_chart(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'),selected_colleges)
                body = dbc.Row([
                        dbc.Col(dcc.Graph(figure=fig2, id="kpi-graph2"), width=6),  # First column for KPI Description
                        dbc.Col(dcc.Graph(figure=fig1, id="kpi-graph3"), width=6),  # Second column for the Graph
                    ],justify="center")
                title = "Top 10 Research Outputs (Unique Views)"
                
            elif button_id == "btn-kpi-avg-views":
                title = "Top 10 Users"
                fig = self.top_10_users_engagement(selected_colleges,start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
            else:
                title = "Unknown KPI"
                body = "No details available for this metric."
            
            return True, title, body, fig