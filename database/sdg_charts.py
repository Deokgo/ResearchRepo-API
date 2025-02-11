from database.sdg_queries import get_research_count, get_research_percentage, get_research_type_distribution, get_geographical_distribution,get_conference_participation,get_local_vs_foreign_participation,get_research_with_keywords,get_research_area_data
import pandas as pd
import plotly.express as px
from services.sdg_colors import sdg_colors
from dashboards import db_manager
from models import ResearchTypes
import numpy as np
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
import base64
from io import BytesIO
import dash_html_components as html
import plotly.graph_objects as go

# Download necessary NLTK datasets
nltk.download("stopwords")
nltk.download("punkt")
nltk.download("wordnet")

# Initialize stopwords and lemmatizer
stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

def create_sdg_plot(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    all_sdgs = [f'SDG {i}' for i in range(1, 18)]
    
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()

    # Fetch data from database using get_research_count
    research_data = get_research_count(
        start_year=min(selected_years),
        end_year=max(selected_years),
        sdg_filter=[sdg_dropdown_value] if sdg_dropdown_value != "ALL" else None,
        status_filter=selected_status,
        college_filter=selected_colleges
    )
    
    # Convert to DataFrame
    df = pd.DataFrame(research_data)
    
    # Check if df is empty
    if df.empty:
        return px.imshow([[0]], labels={'x': "Year", 'y': "SDG", 'color': "Count"}, title="No data available for the selected parameters.")
    
    # Rename columns if necessary
    df.rename(columns={'research_count': 'Count', 'sdg': 'sdg', 'school_year': 'school_year', 'college_id': 'College'}, inplace=True)
    
    # Sort by year (school_year) and SDG based on all_sdgs order
    df['school_year'] = df['school_year'].astype(int)  # Ensure school_year is treated as an integer
    df = df.sort_values(by=['school_year', 'sdg'], key=lambda col: col.map({sdg: i for i, sdg in enumerate(all_sdgs)}))
    
    # If sdg_dropdown_value is not "ALL", create a line graph for the selected SDG
    if sdg_dropdown_value != "ALL":
        # Filter data for the selected SDG
        df = df[df['sdg'] == sdg_dropdown_value]
        
        # Sort the DataFrame by year for line graph
        df = df.sort_values(by='school_year')  # Ensures the data is ordered by year
        
        # Create line plot for the selected SDG over time
        fig = px.line(
            df,
            x='school_year',
            y='Count',
            title=f"Research Outputs Over Time for {sdg_dropdown_value}",
            labels={'school_year': 'Year', 'Count': 'Research Output Count'},
            template="plotly_white",
            markers=True
        )
        
        fig.update_layout(
            title_font_size=14,
            width=670,
            height=350,
            margin=dict(l=10, r=10, t=30, b=10)
        )
    
    else:
        # Sort the DataFrame by year for heatmap
        df = df.sort_values(by='school_year')  # Ensures the data is ordered by year
        
        # Create heatmap for all SDGs
        fig = px.imshow(
            df.pivot(index='sdg', columns='school_year', values='Count').fillna(0).reindex(index=all_sdgs),
            labels={'x': "Year", 'y': "SDG", 'color': "Count"},
            title='Research Outputs Over Time by SDG',
            color_continuous_scale='Viridis'
        )
        
        fig.update_layout(
            title_font_size=14,
            template="plotly_white",
            width=670,
            height=350,
            margin=dict(l=10, r=10, t=30, b=10)
        )
    
    return fig


def create_sdg_pie_chart(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    """
    Creates a pie chart showing the percentage distribution of research outputs by SDG or College.

    :param selected_colleges: List of selected colleges
    :param selected_status: List of selected statuses
    :param selected_years: List of selected school years
    :param sdg_dropdown_value: Selected SDG filter
    :return: Plotly pie chart figure
    """
    all_sdgs = [f'SDG {i}' for i in range(1, 18)]

    # Convert arrays to lists if needed
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()
    
    # Fetch data based on filter
    research_data = get_research_percentage(
        start_year=min(selected_years), 
        end_year=max(selected_years),
        sdg_filter=None if sdg_dropdown_value == "ALL" else [sdg_dropdown_value],
        status_filter=selected_status,
        college_filter=selected_colleges
    )
    df = pd.DataFrame(research_data)

    if sdg_dropdown_value == "ALL":
        # Group by SDG if SDG filter is "ALL"
        df['sdg'] = pd.Categorical(df['sdg'], categories=all_sdgs, ordered=True)
        df = df.sort_values('sdg')

        fig = px.pie(
            df,
            names='sdg',
            values='percentage',
            title='Percentage of Research Outputs by SDG',
            labels={'sdg': 'SDG', 'percentage': 'Percentage of Total Outputs'},
            category_orders={"sdg": all_sdgs}  # Ensure legend follows all_sdgs order
        )
    else:
        # Group by College for distribution if SDG filter is not "ALL"
        college_distribution = df.groupby('college_id').sum().reset_index()
        college_distribution['Percentage'] = (college_distribution['research_count'] / college_distribution['research_count'].sum()) * 100
        
        fig = px.pie(
            college_distribution,
            names='college_id',
            values='Percentage',
            title='Percentage of Research Outputs by College',
            labels={'college_id': 'College', 'Percentage': 'Percentage of Total Outputs'}
        )

    fig.update_layout(
        title_font_size=14,  
        legend_title_font_size=12,  
        template="plotly_white",
        width=600,  
        height=350,  
        margin=dict(l=10, r=10, t=30, b=10),  
        uniformtext_minsize=10,  
        uniformtext_mode='hide',
        legend=dict(
            orientation="v",  # Vertical legend
            x=1.02,  # Position the legend outside on the right
            y=1,  # Align legend to the top
            yanchor="top",
            xanchor="left",
            traceorder="normal",
            itemsizing="constant",
            title_font_size=12,
            font=dict(size=10)
        ))

    return fig



def create_sdg_research_chart(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    """
    Generates a bar chart or line chart showing research type distribution by SDG.

    :param selected_colleges: List of selected colleges
    :param selected_status: List of selected statuses
    :param selected_years: List of selected school years
    :param sdg_dropdown_value: Selected SDG filter
    :return: Plotly figure (stacked bar chart or line chart)
    """
    # Fetch unique research types
    all_sdgs = [f'SDG {i}' for i in range(1, 18)]

    # Convert arrays to lists if needed
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()
    types = [rt.research_type_name for rt in ResearchTypes.query_all()]
    
    # Fetch research type distribution from the database
    research_data = get_research_type_distribution(
        start_year=min(selected_years),
        end_year=max(selected_years),
        sdg_filter=None if sdg_dropdown_value == "ALL" else [sdg_dropdown_value],
        status_filter=selected_status,
        college_filter=selected_colleges
    )

    # Convert to DataFrame
    df = pd.DataFrame(research_data)

    # Ensure SDG and Research Type are categorical (for ordering)
    df['research_type_name'] = pd.Categorical(df['research_type_name'], categories=types, ordered=True)
    df['sdg'] = pd.Categorical(df['sdg'], categories=all_sdgs, ordered=True)

    # If sdg_dropdown_value is not "ALL", create a bar chart
    if sdg_dropdown_value != "ALL":
        # Create bar chart for the selected SDG and research type
        fig = px.bar(
            df,
            x="research_type_name",
            y="research_count",
            color="research_type_name",
            title=f"Research Type Distribution for {sdg_dropdown_value}",
            labels={"research_type_name": "Research Type", "research_count": "Research Count"},
            template="plotly_white",
            color_discrete_sequence=px.colors.qualitative.Set2,
            barmode="stack"  # To stack the bars
        )

        # Customize layout to ensure all types are displayed and the bar size is appropriate
        fig.update_layout(
            title_font_size=14,
            width=1200,
            height=250,
            margin=dict(l=10, r=10, t=30, b=80),
            xaxis_title="Research Type",
            yaxis_title="Research Count",
            xaxis=dict(tickangle=0),  # Rotate labels for better readability
            showlegend=True
        )

    else:
        # Pivot the data to a format suitable for a heatmap
        heatmap_data = df.pivot(index='research_type_name', columns='sdg', values='research_count')

        # Ensure all research types appear and replace NaN with 0
        heatmap_data = heatmap_data.reindex(index=types, columns=all_sdgs, fill_value=0).fillna(0)

        # Create heatmap with a visually appealing color scale
        fig = px.imshow(
            heatmap_data,
            labels=dict(x="Sustainable Development Goals (SDGs)", y="Research Type", color="Research Count"),
            color_continuous_scale="Plasma",  # Alternative: "Viridis", "Turbo", "Sunsetdark"
            aspect="auto"
        )

        # Customize layout for heatmap
        fig.update_layout(
            title="Research Type Distribution by SDG",
            title_font_size=14,
            width=1200,
            height=250,
            margin=dict(l=10, r=10, t=30, b=10),
            xaxis_title="Sustainable Development Goals (SDGs)",
            yaxis_title="Research Type",
            coloraxis_colorbar=dict(title="Research Count"),
            xaxis=dict(tickangle=-45)  # Rotate SDG labels for better readability
        )

    return fig



def create_geographical_heatmap(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    """
    Generates a choropleth heatmap for the geographical distribution of research outputs.

    :param start_year: Start school year (integer)
    :param end_year: End school year (integer)
    :param sdg_filter: List of SDG filters (list of strings, optional)
    :param status_filter: List of status filters (list of strings, optional)
    :param college_filter: List of college filters (list of strings, optional)
    :param program_filter: List of program filters (list of strings, optional)
    :return: Plotly figure object
    """
        # Convert arrays to lists if needed
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()
    df = get_geographical_distribution(
        start_year=min(selected_years),
        end_year=max(selected_years),
        sdg_filter=None if sdg_dropdown_value == "ALL" else [sdg_dropdown_value],
        status_filter=selected_status,
        college_filter=selected_colleges)

    # Ensure df is a DataFrame
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    if df.empty:
        return None  # No data available

    # Aggregate by country
    df_country = df.groupby('country', as_index=False)['research_count'].sum()
    fig = px.choropleth(
        df_country,
        locations="country",
        locationmode="country names",
        color="research_count",
        hover_name="country",
        hover_data={"research_count": True},
        color_continuous_scale="Viridis",
        title="Geographical Distribution of Research Outputs",
        labels={'research_count': 'Count'}
    )

    # Customize layout
    fig.update_geos(
        showcoastlines=True, coastlinecolor="Black",
        showland=True, landcolor="lightgray",
        showocean=True, oceancolor="white",
        projection_type="natural earth"
    )

    fig.update_layout(
        title_font_size=14,
        geo_scope="world",
        template="plotly_white",
        width=900,
        height=400,
        margin=dict(l=0, r=0, t=23, b=0)  # Reduce unnecessary spacing
    )


    return fig

def create_geographical_treemap(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    """
    Generates a treemap for the geographical distribution of research outputs,
    with countries as the main category and cities as the subcategory.

    :param selected_colleges: List of selected colleges (list of strings)
    :param selected_status: List of selected research statuses (list of strings)
    :param selected_years: List of selected years (list of integers)
    :param sdg_dropdown_value: Selected SDG goal (string)
    :return: Plotly figure object
    """
    # Convert arrays to lists if needed
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()

    # Fetch data
    df = get_geographical_distribution(
        start_year=min(selected_years),
        end_year=max(selected_years),
        sdg_filter=None if sdg_dropdown_value == "ALL" else [sdg_dropdown_value],
        status_filter=selected_status,
        college_filter=selected_colleges
    )

    # Ensure df is a DataFrame
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    if df.empty:
        return None  # No data available

    # Aggregate research count by country and city
    df_grouped = df.groupby(['country', 'city'], as_index=False)['research_count'].sum()

    # Create treemap with country as the main category and city as subcategory
    fig = px.treemap(
        df_grouped,
        path=['country', 'city'],  # Main category: country, Sub-category: city
        values='research_count',
        color='research_count',
        color_continuous_scale='Viridis',
        title="Conference Venue Treemap",
        labels={'research_count': 'Count'}
    )

    fig.update_layout(
        title_font_size=14,
        template="plotly_white",
        width=400,
        height=400,
        margin=dict(l=0, r=0, t=25, b=0)  # Reduce margins to remove extra spacing
    )

    return fig


def create_conference_participation_bar_chart(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    """
    Generates a bar chart showing the number of conference participations per year.

    :param selected_colleges: List of selected colleges (list of strings)
    :param selected_status: List of selected research statuses (list of strings)
    :param selected_years: List of selected years (list of integers)
    :param sdg_dropdown_value: Selected SDG goal (string)
    :return: Plotly figure object
    """
    # Convert arrays to lists if needed
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()

    # Fetch data
    df = get_conference_participation(
        start_year=min(selected_years),
        end_year=max(selected_years),
        sdg_filter=None if sdg_dropdown_value == "ALL" else [sdg_dropdown_value],
        status_filter=selected_status,
        college_filter=selected_colleges
    )

    # Ensure df is a DataFrame
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df)

    if df.empty:
        return None  # No data available

    # Aggregate participation count per year
    df_grouped = df.groupby(['school_year'], as_index=False)['participation_count'].sum()

    # Create a bar chart
    fig = px.bar(
        df_grouped,
        x='school_year',
        y='participation_count',
        labels={'school_year': 'School Year', 'participation_count': 'Participation Count'},
        title="Conference Participation Per Year",
        color='participation_count',
        color_continuous_scale='Viridis'
    )

    fig.update_traces(textposition='outside')

    fig.update_layout(
        title_font_size=14,
        template="plotly_white",
        width=900,
        height=200,
        margin=dict(l=0, r=0, t=25, b=0),
        xaxis=dict(type='category',tickangle=0),  # Ensure school years appear as categorical
        yaxis_title="Participation Count"
    )

    return fig


def create_local_vs_foreign_donut_chart(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    """
    Generates a donut chart comparing local vs. foreign conference participation.

    :param selected_colleges: List of selected colleges (list of strings)
    :param selected_status: List of selected research statuses (list of strings)
    :param selected_years: List of selected years (list of integers)
    :param sdg_dropdown_value: Selected SDG goal (string)
    :param country_name: Name of the country considered as 'Local' (string)
    :return: Plotly figure object
    """

    # Convert arrays to lists if needed
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()

    # Fetch data using the function that categorizes local vs. foreign
    df = get_local_vs_foreign_participation(
        start_year=min(selected_years),
        end_year=max(selected_years),
        country_name="Philippines",
        sdg_filter=None if sdg_dropdown_value == "ALL" else [sdg_dropdown_value],
        status_filter=selected_status,
        college_filter=selected_colleges
    )

    # Ensure df is a DataFrame
    if not isinstance(df, pd.DataFrame):
        df = pd.DataFrame(df, columns=['location_category', 'research_count'])

    if df.empty:
        return None  # No data available

    # Create a donut chart
    fig = px.pie(
        df,
        names='location_category',
        values='research_count',
        hole=0.4,  # Creates the donut effect
        title="Local vs. Foreign",
        color='location_category',
        color_discrete_map={"Local": "blue", "Foreign": "red"}  # Custom colors
    )

    fig.update_traces(textinfo='percent+label', pull=[0.05, 0])  # Slightly separate one slice for effect

    fig.update_layout(
        title_font_size=14,
        template="plotly_white",
        height=200,
        width=400,
        margin=dict(l=0, r=0, t=25, b=0) 
    )

    return fig



# Download necessary NLTK datasets
nltk.download("stopwords")
nltk.download("punkt")
nltk.download("wordnet")

# Initialize stopwords and lemmatizer
stop_words = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()

def preprocess_text_nltk(text):
    """
    Cleans and preprocesses text using NLTK.
    - Tokenizes text
    - Removes stopwords
    - Lemmatizes words
    """
    words = word_tokenize(text.lower())  # Tokenize and lowercase
    processed_words = [
        lemmatizer.lemmatize(word) for word in words
        if word.isalpha() and word not in stop_words  # Keep only words (no numbers/punctuation)
    ]
    return " ".join(processed_words)


def get_word_cloud(selected_colleges, selected_status, selected_years, sdg_dropdown_value):
    """
    Generates a word cloud from research titles, abstracts, and keywords and returns it as a Plotly Figure.
    """
    # Convert arrays to lists if needed
    if isinstance(selected_colleges, np.ndarray):
        selected_colleges = selected_colleges.tolist()
    if isinstance(selected_status, np.ndarray):
        selected_status = selected_status.tolist()
    
    # Fetch data using get_research_with_keywords
    data = get_research_with_keywords(
        start_year=min(selected_years),
        end_year=max(selected_years),
        sdg_filter=None if sdg_dropdown_value == "ALL" else [sdg_dropdown_value],
        status_filter=selected_status,
        college_filter=selected_colleges
    )

    # Convert to DataFrame if it's a list
    df = pd.DataFrame(data) if isinstance(data, list) else data

    # Check if DataFrame is empty
    if df.empty:
        return go.Figure().update_layout(title="No Data Available")

    # Ensure necessary columns exist
    required_columns = ["title", "abstract", "keywords"]
    if not all(col in df.columns for col in required_columns):
        return go.Figure().update_layout(title="Missing Necessary Columns in Dataset")

    # Combine text fields
    df["combined_text"] = df[["title", "abstract", "keywords"]].astype(str).agg(" ".join, axis=1)

    # Concatenate all research text
    all_text = " ".join(df["combined_text"])

    # Tokenize, remove stopwords, and clean text
    stop_words = set(stopwords.words("english"))
    words = [word.lower() for word in all_text.split() if word.isalpha() and word.lower() not in stop_words]

    # If no valid words, return an empty figure
    if not words:
        return go.Figure().update_layout(title="No Meaningful Words Available")

    # Generate word cloud
    wordcloud = WordCloud(
        background_color="white",
        width=800,
        height=400,
        max_words=200
    ).generate(" ".join(words))

    # Convert word cloud to an image buffer
    img_buffer = BytesIO()
    wordcloud.to_image().save(img_buffer, format="PNG")
    img_buffer.seek(0)

    # Encode image to base64
    encoded_img = base64.b64encode(img_buffer.getvalue()).decode("utf-8")
    img_src = f"data:image/png;base64,{encoded_img}"

    # Create a Plotly figure
    fig = go.Figure()

    fig.add_layout_image(
        dict(
            source=img_src,
            xref="paper",
            yref="paper",
            x=0,
            y=1,
            sizex=1,
            sizey=1,
            xanchor="left",
            yanchor="top",
            layer="below"
        )
    )

    # Ensure the figure scales properly with the image
    fig.update_xaxes(visible=False, range=[0, 1], domain=[0, 1])
    fig.update_yaxes(visible=False, range=[0, 1], scaleanchor="x", domain=[0, 1])

    # Remove margins to fit the image exactly
    fig.update_layout(
        title=f"Common Topics for {sdg_dropdown_value}" if sdg_dropdown_value != "ALL" else "Common Topics for All SDGs",
        margin=dict(l=0, r=0, t=40, b=0),
        width=720,  # Match word cloud size
        height=400  # Match word cloud size
    )

    return fig


def generate_research_area_visualization(selected_colleges, selected_status, selected_years, sdg_dropdown_value="ALL"):
    """
    Generates an interactive bubble chart of research areas per SDG or year using Plotly.
    """

    # Convert arrays to lists if needed
    def convert_to_python_list(value):
        return value.tolist() if isinstance(value, np.ndarray) else value

    selected_colleges = convert_to_python_list(selected_colleges)
    selected_status = convert_to_python_list(selected_status)
    selected_years = convert_to_python_list(selected_years)

    # Ensure years are integers
    if isinstance(selected_years, list) and len(selected_years) > 0:
        selected_years = [int(year) for year in selected_years]  # Convert all elements to int
    elif isinstance(selected_years, np.ndarray) and selected_years.size == 1:
        selected_years = int(selected_years.item())  # Extract scalar if it's a single-value array

    # Fetch data
    df = get_research_area_data(
        start_year=selected_years[0] if isinstance(selected_years, list) and len(selected_years) > 0 else None,
        end_year=selected_years[-1] if isinstance(selected_years, list) and len(selected_years) > 0 else None,
        sdg_filter=[sdg_dropdown_value] if sdg_dropdown_value != "ALL" else None,
        status_filter=selected_status,
        college_filter=selected_colleges
    )

    if df.empty:
        print("No data available for the selected filters.")
        return None

    # Convert research count to integer
    df["research_count"] = df["research_count"].astype(int)

    # Determine X-axis
    x_axis = "sdg"
    if sdg_dropdown_value != "ALL":
        df = df[df["sdg"] == sdg_dropdown_value]
        x_axis = "year"  # Show distribution across years when filtering by SDG

    # Aggregate research areas
    df_grouped = df.groupby([x_axis, "research_area_name"])["research_count"].sum().reset_index()

    # Sort and get top N research areas
    if x_axis == "year":
        df_grouped = df_grouped.sort_values(by=["year", "research_count"], ascending=[True, False])
    else:
        df_grouped = df_grouped.sort_values(by=["research_count"], ascending=False)

    # Define SDG ordering if needed
    all_sdgs = [f'SDG {i}' for i in range(1, 18)]  # SDG 1 to SDG 17

    # Create bubble chart
    fig = px.scatter(
        df_grouped,
        x="research_area_name", 
        y= x_axis,
        size="research_count",  
        color="research_area_name",  
        hover_name="research_area_name",  
        title=f"Research Areas per {'Year' if x_axis == 'year' else 'SDG'}",
        labels={x_axis: 'Year' if x_axis == 'year' else 'Sustainable Development Goals (SDGs)',
                "research_area_name": "Research Areas"},
        template="plotly_white",  
        height=400,
        width=600,
        category_orders={"sdg": all_sdgs} if x_axis == "sdg" else None  # Ensure SDG order
    )

    # Update layout to hide Y-axis label
    fig.update_layout(
        yaxis_title="Year" if x_axis == "year" else "SDG",
        xaxis_title="",  # Hide the Y-axis label
        showlegend=False,
        xaxis=dict(tickvals=[]),  # Remove the Y-axis ticks (research area names)
        margin=dict(l=0, r=0, t=30, b=0),
        yaxis=dict(
            tickangle=0  # Set tick labels to be horizontal
        ),
    )

    return fig