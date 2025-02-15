from database.institutional_performance_queries import get_data_for_performance_overview, get_data_for_research_type_bar_plot, get_data_for_research_status_bar_plot, get_data_for_scopus_section, get_data_for_jounal_section, get_data_for_sdg, get_data_for_modal_contents, get_data_for_text_displays
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import pandas as pd
from dashboards.usable_methods import default_if_empty, ensure_list, download_file

def update_line_plot(self, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_programs = ensure_list(selected_programs)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    if selected_programs == None:
        # Fetch data using get_data_for_performance_overview
        filtered_data_with_term = get_data_for_performance_overview(selected_colleges, None, selected_status, selected_years, selected_terms)

        df = pd.DataFrame(filtered_data_with_term) # Convert data to DataFrame
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
            color_discrete_map=self.program_colors if len(selected_colleges) == 1 else self.palette_dict
        )
        
        fig_line.update_layout(
            title=dict(text=title, font=dict(size=12)),  # Smaller title
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            showlegend=True  
        )
    elif len(selected_programs) > 1:
        # Fetch data using get_data_for_performance_overview
        filtered_data_with_term = get_data_for_performance_overview(None, selected_programs, selected_status, selected_years, selected_terms)

        df = pd.DataFrame(filtered_data_with_term) # Convert data to DataFrame
        if len(selected_programs) == 1:
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = f'Number of Research Outputs for {selected_programs[0]}'
        else:
            df = df[df['program_id'].isin(selected_programs)]
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = 'Number of Research Outputs per Program'
        
        # Generate a dynamic color mapping based on unique values in the color_column
        self.get_program_colors(df)
        color_discrete_map = self.program_colors
        
        # Generate the line plot
        fig_line = px.line(
            grouped_df,
            x='year',
            y='TitleCount',
            color=color_column,
            markers=True,
            color_discrete_map=color_discrete_map
        )
        
        # Update the layout for aesthetics and usability
        fig_line.update_layout(
            title=dict(text=title, font=dict(size=12)),  # Smaller title
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400
        )
    elif len(selected_programs) == 1:
        # Fetch data using get_data_for_performance_overview
        filtered_data_with_term = get_data_for_performance_overview(None, selected_programs, selected_status, selected_years, selected_terms)

        df = pd.DataFrame(filtered_data_with_term) # Convert data to DataFrame
        if len(selected_programs) == 1:
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = f'Number of Research Outputs for {selected_programs[0]}'
        else:
            df = df[df['program_id'].isin(selected_programs)]
            grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
            color_column = 'program_id'
            title = 'Number of Research Outputs per College'
        
        # Generate a dynamic color mapping based on unique values in the color_column
        unique_values = grouped_df[color_column].unique()
        color_discrete_map = {value: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] 
                            for i, value in enumerate(unique_values)}
        
        # Generate the line plot
        fig_line = px.line(
            grouped_df,
            x='year',
            y='TitleCount',
            color=color_column,
            markers=True,
            color_discrete_map=color_discrete_map
        )
        
        # Update the layout for aesthetics and usability
        fig_line.update_layout(
            title=dict(text=title, font=dict(size=12)),  # Smaller title
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=300
        ) 
    return fig_line

"""
def update_pie_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_performance_overview
    filtered_data_with_term = get_data_for_performance_overview(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)

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
        color_discrete_map=self.program_colors if len(selected_colleges) == 1 else self.palette_dict,
        labels={'names': 'Category', 'values': 'Number of Research Outputs'},
    )

    fig_pie.update_layout(
        template='plotly_white',
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        title=dict(text=title, font=dict(size=12)),  # Smaller title
    )

    return fig_pie

def update_research_type_bar_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_research_type_bar_plot
    filtered_data_with_term = get_data_for_research_type_bar_plot(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)

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
        xaxis_title=dict(text='Research Type', font=dict(size=12)),
        yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
        title=dict(text=title, font=dict(size=12)),  # Smaller title
    )

    return fig

def update_research_status_bar_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_filtered_data_with_term
    filtered_data_with_term = get_data_for_research_status_bar_plot(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)

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
        xaxis_title=dict(text='Research Status', font=dict(size=12)),
        yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
        title=dict(text=title, font=dict(size=12)),  # Smaller title,
        xaxis=dict(
            tickvals=status_order,  # This should match the unique statuses in pivot_df index
            ticktext=status_order    # This ensures that the order of the statuses is displayed correctly
        )
    )

    # Ensure the x-axis is sorted in the defined order
    fig.update_xaxes(categoryorder='array', categoryarray=status_order)

    return fig

def create_publication_bar_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_scopus_section
    filtered_data_with_term = get_data_for_scopus_section(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)

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
        title=dict(text=title, font=dict(size=12)),  # Smaller title,
        xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
        yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
        template='plotly_white',
        height=400
    )

    return fig_bar

def update_publication_format_bar_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_jounal_section
    filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)

    df = df[df['journal'] != 'unpublished']
    df = df[df['status'] != 'PULLOUT']

    if len(selected_colleges) == 1:
        grouped_df = df.groupby(['journal', 'program_id']).size().reset_index(name='Count')
        x_axis = 'program_id'
        xaxis_title = 'Programs'
        title = f'Publication Types per Program in {selected_colleges[0]}'
    else:
        grouped_df = df.groupby(['journal', 'college_id']).size().reset_index(name='Count')
        x_axis = 'college_id'
        xaxis_title = 'Colleges'
        title = 'Publication Types per College'

    fig_bar = px.bar(
        grouped_df,
        x=x_axis,
        y='Count',
        color='journal',
        barmode='group',
        color_discrete_map=self.palette_dict,
        labels={'journal': 'Publication Type'}
    )
    
    fig_bar.update_layout(
        title=dict(text=title, font=dict(size=12)),  # Smaller title,
        xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
        yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
        template='plotly_white',
        height=400
    )

    return fig_bar


def update_sdg_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_sdg
    filtered_data_with_term = get_data_for_sdg(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)

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
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_scopus_section
    filtered_data_with_term = get_data_for_scopus_section(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)

    # Filter out rows where 'scopus' is 'N/A'
    df = df[df['scopus'] != 'N/A']

    # Group data by 'scopus' and 'year'
    grouped_df = df.groupby(['scopus', 'year']).size().reset_index(name='Count')

    # Ensure year and count are numeric
    grouped_df['year'] = grouped_df['year'].astype(int)
    grouped_df['Count'] = grouped_df['Count'].astype(int)

    # Create the line chart with markers
    fig_line = px.line(
        grouped_df,
        x='year',
        y='Count',
        color='scopus',
        color_discrete_map=self.palette_dict,
        labels={'scopus': 'Scopus vs. Non-Scopus'},
        markers=True
    )

    # Update layout for smaller text and responsive UI
    fig_line.update_traces(
        line=dict(width=1.5),  # Thinner lines
        marker=dict(size=5)  # Smaller marker points
    )

    fig_line.update_layout(
        title=dict(text='Scopus vs. Non-Scopus Publications Over Time', font=dict(size=12)),  # Smaller title
        xaxis_title=dict(text='Academic Year', font=dict(size=12)),
        yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
        template='plotly_white',
        height=300,  # Smaller chart height
        margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins for compact display
        xaxis=dict(
            type='linear',  
            tickangle=-45,  # Angled labels for better fit
            automargin=True,  # Prevent label overflow
            tickfont=dict(size=10)  # Smaller x-axis text
        ),
        yaxis=dict(
            automargin=True,  
            tickfont=dict(size=10)  # Smaller y-axis text
        ),
        legend=dict(font=dict(size=9)),  # Smaller legend text
    )

    return fig_line

def scopus_pie_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_scopus_section
    filtered_data_with_term = get_data_for_scopus_section(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)
    
    # Filter out rows where 'scopus' is 'N/A'
    df = df[df['scopus'] != 'N/A']

    # Group data by 'scopus' and sum the counts
    grouped_df = df.groupby(['scopus']).size().reset_index(name='Count')

    # Create the pie chart
    fig_pie = px.pie(
        grouped_df,
        names='scopus',
        values='Count',
        color='scopus',
        color_discrete_map=self.palette_dict,
        labels={'scopus': 'Scopus vs. Non-Scopus'}
    )

    # Update layout for a smaller and more responsive design
    fig_pie.update_traces(
        textfont=dict(size=9),  # Smaller text inside the pie
        insidetextfont=dict(size=9),  # Smaller text inside the pie
        marker=dict(line=dict(width=0.5))  # Thinner slice borders
    )

    fig_pie.update_layout(
        title=dict(text='Scopus vs. Non-Scopus Research Distribution', font=dict(size=12)),  # Smaller title
        template='plotly_white',
        height=300,  # Smaller chart height
        margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins
        legend=dict(font=dict(size=9)),  # Smaller legend text
    )

    return fig_pie

def publication_format_line_plot(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_jounal_section
    filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)
    
    # Filter out rows with 'unpublished' journals and 'PULLOUT' status
    df = df[df['journal'] != 'unpublished']
    df = df[df['status'] != 'PULLOUT']

    # Group data by 'journal' and 'year'
    grouped_df = df.groupby(['journal', 'year']).size().reset_index(name='Count')

    # Ensure year and count are numeric
    grouped_df['year'] = grouped_df['year'].astype(int)
    grouped_df['Count'] = grouped_df['Count'].astype(int)

    # Create the line chart with markers
    fig_line = px.line(
        grouped_df,
        x='year',
        y='Count',
        color='journal',
        color_discrete_map=self.palette_dict,
        labels={'journal': 'Publication Type'},
        markers=True
    )

    # Update layout for smaller text and responsive UI
    fig_line.update_traces(
        line=dict(width=1.5),  # Thinner lines
        marker=dict(size=5)  # Smaller marker points
    )

    fig_line.update_layout(
        title=dict(text='Publication Types Over Time', font=dict(size=12)),  # Smaller title
        xaxis_title=dict(text='Academic Year', font=dict(size=12)),
        yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
        template='plotly_white',
        height=300,  # Smaller chart height
        margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins for compact display
        xaxis=dict(
            type='linear',  
            tickangle=-45,  # Angled labels for better fit
            automargin=True,  # Prevent label overflow
            tickfont=dict(size=10)  # Smaller x-axis text
        ),
        yaxis=dict(
            automargin=True,  
            tickfont=dict(size=10)  # Smaller y-axis text
        ),
        legend=dict(font=dict(size=9)),  # Smaller legend text
    )

    return fig_line

def publication_format_pie_chart(self, selected_colleges, selected_status, selected_years, selected_terms):
    # Ensure selected_colleges is a standard Python list or array
    selected_colleges = ensure_list(selected_colleges)
    selected_status = ensure_list(selected_status)
    selected_years = ensure_list(selected_years)
    selected_terms = ensure_list(selected_terms)

    # Fetch data using get_data_for_jounal_section
    filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms)

    # Convert data to DataFrame
    df = pd.DataFrame(filtered_data_with_term)
    
    # Filter out rows with 'unpublished' journals and 'PULLOUT' status
    df = df[df['journal'] != 'unpublished']
    df = df[df['status'] != 'PULLOUT']

    # Group data by 'journal' and sum the counts
    grouped_df = df.groupby(['journal']).size().reset_index(name='Count')

    # Create the pie chart
    fig_pie = px.pie(
        grouped_df,
        names='journal',
        values='Count',
        color='journal',
        color_discrete_map=self.palette_dict,
        labels={'journal': 'Publication Type'}
    )

    # Update layout for a smaller and more responsive design
    fig_pie.update_traces(
        textfont=dict(size=9),  # Smaller text inside the pie
        insidetextfont=dict(size=9),  # Smaller text inside the pie
        marker=dict(line=dict(width=0.5))  # Thinner slice borders
    )

    fig_pie.update_layout(
        title=dict(text='Publication Type Distribution', font=dict(size=12)),  # Smaller title
        template='plotly_white',
        height=300,  # Smaller chart height
        margin=dict(l=5, r=5, t=30, b=30),  # Minimal margins
        legend=dict(font=dict(size=9)),  # Smaller legend text
    )

    return fig_pie
"""