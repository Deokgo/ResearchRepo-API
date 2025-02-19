from database.institutional_performance_queries import get_data_for_performance_overview, get_data_for_research_type_bar_plot, get_data_for_research_status_bar_plot, get_data_for_scopus_section, get_data_for_jounal_section, get_data_for_sdg, get_data_for_modal_contents, get_data_for_text_displays
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import pandas as pd
from dashboards.usable_methods import default_if_empty, ensure_list, download_file
import pandas as pd
import plotly.express as px
import random

class ResearchOutputPlot:
    def __init__(self):
        self.program_colors = {}
        self.all_sdgs = [f"SDG {i}" for i in range(1, 18)]  # Ensuring correct order
    
    def get_program_colors(self, df):
        unique_programs = df['program_id'].unique()
        available_colors = px.colors.qualitative.T10  # Colorblind-friendly palette
        used_colors = set(self.program_colors.values())  # Track assigned colors

        for program in unique_programs:
            if program not in self.program_colors:
                # Find an unused color from the palette
                unused_colors = [color for color in available_colors if color not in used_colors]

                if unused_colors:
                    chosen_color = unused_colors.pop(0)  # Take the first unused color
                else:
                    # Generate a random distinct color if all predefined colors are used
                    chosen_color = f"rgb({random.randint(0,255)},{random.randint(0,255)},{random.randint(0,255)})"

                self.program_colors[program] = chosen_color
                used_colors.add(chosen_color)  # Mark as used
    
    def update_line_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, default_years):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_performance_overview(selected_colleges, None, selected_status, selected_years, selected_terms)
            df = pd.DataFrame(filtered_data_with_term)
            
            if len(selected_colleges) == 1:
                label = {'program_id': 'Programs'}
                grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
                color_column = 'program_id'
                title = f'Number of Research Outputs for {selected_colleges[0]}'
                self.get_program_colors(grouped_df)
                color_discrete_map = self.program_colors if isinstance(self.program_colors, dict) else {}
            else:
                label = {'college_id': 'Colleges'}
                grouped_df = df.groupby(['college_id', 'year']).size().reset_index(name='TitleCount')
                color_column = 'college_id'
                title = 'Number of Research Outputs per College'
                color_discrete_map = college_colors if isinstance(college_colors, dict) else {}
        
        elif user_id in ["04", "05"]:
            filtered_data_with_term = get_data_for_performance_overview(None, selected_programs, selected_status, selected_years, selected_terms)
            df = pd.DataFrame(filtered_data_with_term)
            
            if len(selected_programs) == 1:
                label = {'program_id': 'Program(s)'}
                grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
                color_column = 'program_id'
                title = f'Number of Research Outputs for {selected_programs[0]}'
            else:
                label = {'program_id': 'Program(s)'}
                df = df[df['program_id'].isin(selected_programs)]
                grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
                color_column = 'program_id'
                title = 'Number of Research Outputs per Program'
            
            self.get_program_colors(df)
            color_discrete_map = self.program_colors if isinstance(self.program_colors, dict) else {}

        # Dynamically determine the first available year and add year[0] - 1 if applicable
        if not grouped_df.empty:
            first_year = default_years[0]

            if first_year in selected_years:
                previous_year = first_year - 1

                # Get unique categories (colleges/programs)
                categories = grouped_df[color_column].unique()

                # Create missing rows with count 0
                missing_rows = pd.DataFrame({color_column: categories, 'year': previous_year, 'TitleCount': 0})

                # Append to the dataframe
                grouped_df = pd.concat([missing_rows, grouped_df], ignore_index=True)

        fig_line = px.line(
            grouped_df,
            x='year',
            y='TitleCount',
            color=color_column,
            markers=True,
            color_discrete_map=color_discrete_map,
            labels=label
        )
        
        fig_line.update_layout(
            title=dict(text=title, font=dict(size=12)),
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400 if user_id != "05" else 300,
            showlegend=True
        )
        
        return fig_line

    def update_pie_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        
        # Determine the filtering parameters based on user_id
        colleges, programs = (selected_colleges, None) if user_id in ["02", "03"] else (None, selected_programs)
        
        # Fetch data
        filtered_data_with_term = get_data_for_performance_overview(colleges, programs, selected_status, selected_years, selected_terms)
        df = pd.DataFrame(filtered_data_with_term)
        
        if user_id in ["02", "03"] and len(selected_colleges) == 1:
            detail_counts = df[df['college_id'] == selected_colleges[0]].groupby('program_id').size()
            self.get_program_colors(df)
            title, color_map = f'Research Output Distribution for {selected_colleges[0]}', self.program_colors
        elif user_id in ["04", "05"] and len(selected_programs) == 1:
            detail_counts = df[df['program_id'] == selected_programs[0]].groupby('year').size().reset_index(name='count')
            title, color_map = f"Research Output Distribution for {selected_programs[0]}", None
        else:
            detail_counts = df.groupby('college_id' if user_id in ["02", "03"] else 'program_id').size().reset_index(name='count')
            title = 'Research Output Distribution by College' if user_id in ["02", "03"] else 'Research Outputs per Program'
            self.get_program_colors(df)
            color_map = self.program_colors if user_id not in ("02", "03") else college_colors
        
        # Create the pie chart
        fig_pie = px.pie(
            data_frame=detail_counts,
            names=detail_counts.index if isinstance(detail_counts, pd.Series) else detail_counts.columns[0],
            values=detail_counts if isinstance(detail_counts, pd.Series) else 'count',
            color=detail_counts.index if isinstance(detail_counts, pd.Series) else detail_counts.columns[0],
            color_discrete_map=color_map,
            labels={'names': 'Category', 'values': 'Number of Research Outputs'}
        )
        
        # Update layout
        fig_pie.update_layout(
            template='plotly_white',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400 if user_id != "05" else 300,
            title=dict(text=title, font=dict(size=12))
        )
        
        return fig_pie
    
    def update_research_type_bar_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        filter_college = selected_colleges if user_id in ["02", "03"] else None
        filter_program = selected_programs if user_id in ["04", "05"] else None
        
        df = pd.DataFrame(get_data_for_research_type_bar_plot(filter_college, filter_program, selected_status, selected_years, selected_terms))
        if df.empty:
            return px.bar(title="No data available")
        
        fig = go.Figure()
        group_col = 'college_id' if user_id in ["02", "03"] and len(selected_colleges) > 1 else 'program_id'
        
        if len(selected_programs) == 1:
            title = f"Comparison of Research Output Type in {selected_programs[0]}"
        elif len(selected_colleges) == 1:
            title = f"Comparison of Research Output Type Across Programs in {selected_colleges[0]}"
        else:
            title = "Comparison of Research Output Type Across " + ("Colleges" if group_col == 'college_id' else "Programs")

        status_count = df.groupby(['research_type', group_col]).size().reset_index(name='Count')
        pivot_df = status_count.pivot(index='research_type', columns=group_col, values='Count').fillna(0)
        
        if user_id in ["02", "03"] and len(selected_colleges) == 1:
            self.get_program_colors(df)
            color_map = self.program_colors
        elif user_id == "05":
            unique_values = status_count[group_col].unique()
            color_map = self.program_colors
        else:
            color_map = college_colors if group_col == 'college_id' else self.program_colors
        
        for group in sorted(pivot_df.columns):
            fig.add_trace(go.Bar(
                x=pivot_df.index,
                y=pivot_df[group],
                name=group,
                marker_color=color_map.get(group, 'grey')
            ))
        
        fig.update_layout(
            barmode='group',
            xaxis_title=dict(text='Research Type', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            title=dict(text=title, font=dict(size=12)),
            height=300 if user_id == "05" else None
        )
        
        return fig
    
    def update_research_status_bar_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        data_params = {
            "02": (selected_colleges, None),
            "03": (selected_colleges, None),
            "04": (None, selected_programs),
            "05": (None, selected_programs),
        }

        if user_id not in data_params:
            return px.bar(title="Invalid User ID")

        filtered_data_with_term = get_data_for_research_status_bar_plot(
            *data_params[user_id], selected_status, selected_years, selected_terms
        )

        df = pd.DataFrame(filtered_data_with_term)
        if df.empty:
            return px.bar(title="No data available")

        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLOUT']
        fig = go.Figure()

        group_by_col = 'college_id' if user_id in ["02", "03"] and len(selected_colleges) > 1 else 'program_id'
        
        if len(selected_programs) == 1:
            title_suffix = f'in {selected_programs[0]}'
        elif len(selected_colleges) == 1:
            title_suffix = f"Across Programs in {selected_colleges[0]}"
        else:
            title_suffix = "Across Colleges" if group_by_col == 'college_id' else "Across Programs"

        status_count = df.groupby(['status', group_by_col]).size().reset_index(name='Count')
        pivot_df = status_count.pivot(index='status', columns=group_by_col, values='Count').fillna(0)

        colors = (
            college_colors if group_by_col == 'college_id' else 
            self.program_colors if user_id in ["02", "04"] else 
            self.program_colors
        )

        for category in pivot_df.columns:
            fig.add_trace(go.Bar(
                x=pivot_df.index,
                y=pivot_df[category],
                name=category,
                marker_color=colors.get(category, 'grey')
            ))

        fig.update_layout(
            barmode='group',
            title=dict(text=f"Comparison of Research Status {title_suffix}", font=dict(size=12)),
            xaxis_title="Research Status",
            yaxis_title="Research Outputs",
            xaxis=dict(tickvals=status_order, ticktext=status_order, categoryorder='array', categoryarray=status_order),
            height=300 if user_id == "05" else None
        )

        return fig
    
    def create_publication_bar_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        
        data_func_args = (selected_colleges, None) if user_id in ["02", "03"] else (None, selected_programs)
        df = pd.DataFrame(get_data_for_scopus_section(*data_func_args, selected_status, selected_years, selected_terms))
        df = df[df['scopus'] != 'N/A']
        
        if df.empty:
            return px.bar(title="No data available")
        
        if user_id in ["02", "03"] and len(selected_colleges) == 1:
            x_axis, xaxis_title = 'program_id', 'Programs'
            title = f'Scopus vs. Non-Scopus per Program in {selected_colleges[0]}'
        else:
            x_axis, xaxis_title = ('college_id', 'Colleges') if user_id in ["02", "03"] else ('program_id', 'Programs')
            title = 'Scopus vs. Non-Scopus per College' if x_axis == 'college_id' else 'Scopus vs. Non-Scopus per Program'
        
        if user_id in ["04", "05"]:
            self.get_program_colors(df)
        
        grouped_df = df.groupby(['scopus', x_axis]).size().reset_index(name='Count')
        
        fig_bar = px.bar(
            grouped_df, x=x_axis, y='Count', color='scopus', barmode='group', 
            color_discrete_map=college_colors, labels={'scopus': 'Scopus vs. Non-Scopus'}
        )
        
        fig_bar.update_layout(
            title=dict(text=title, font=dict(size=12)),
            xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white', height=400 if user_id != "05" else 300
        )
        
        return fig_bar
    
    def update_publication_format_bar_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Determine filtering based on user_id
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms)
        else:
            filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms)
        
        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)
        df = df[(df['journal'] != 'unpublished') & (df['status'] != 'PULLOUT')]
        
        # Determine grouping
        if user_id in ["02", "03"] and len(selected_colleges) == 1:
            grouped_df = df.groupby(['journal', 'program_id']).size().reset_index(name='Count')
            x_axis, xaxis_title = 'program_id', 'Programs'
            title = f'Publication Types per Program in {selected_colleges[0]}'
        elif user_id in ["02", "03"]:
            grouped_df = df.groupby(['journal', 'college_id']).size().reset_index(name='Count')
            x_axis, xaxis_title = 'college_id', 'Colleges'
            title = 'Publication Types per College'
        else:
            grouped_df = df.groupby(['journal', 'program_id']).size().reset_index(name='Count')
            x_axis, xaxis_title, title = 'program_id', 'Programs', 'Publication Types per Program'
        
        # Create bar chart
        fig_bar = px.bar(
            grouped_df, x=x_axis, y='Count', color='journal', barmode='group',
            color_discrete_map=college_colors, labels={'journal': 'Publication Type'}
        )
        
        # Adjust layout
        fig_bar.update_layout(
            title=dict(text=title, font=dict(size=12)),
            xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=300 if user_id == "05" else 400
        )
        
        return fig_bar
    
    def update_sdg_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        
        user_filters = {
            "02": (selected_colleges, None),
            "03": (selected_colleges, None),
            "04": (None, selected_programs),
            "05": (None, selected_programs)
        }
        
        if user_id not in user_filters:
            return px.scatter(title="Invalid User ID")
        
        filtered_data = get_data_for_sdg(*user_filters[user_id], selected_status, selected_years, selected_terms)
        df = pd.DataFrame(filtered_data)
        
        if df.empty:
            return px.scatter(title="No data available")
        
        entity = 'program_id' if user_id not in ("02", "03") or len(selected_colleges) == 1 else 'college_id'
        title = (f'Distribution of SDG-Targeted Research in {selected_programs[0]}' 
                if len(selected_programs) == 1 
                else f'Distribution of SDG-Targeted Research Across Programs in {selected_colleges[0]}'
                if user_id in ["02", "03"] and len(selected_colleges) == 1
                else f'Distribution of SDG-Targeted Research Across Programs in {selected_colleges[0]}'
                if user_id not in ("02", "03") 
                else 'Distribution of SDG-Targeted Research Across Colleges')
                
        df_expanded = df.set_index(entity)['sdg'].str.split(';').apply(pd.Series).stack().reset_index(name='sdg')
        df_expanded['sdg'] = df_expanded['sdg'].str.strip()
        df_expanded.drop(columns=['level_1'], inplace=True)
        sdg_count = df_expanded.groupby(['sdg', entity]).size().reset_index(name='Count')
        
        if sdg_count.empty:
            return px.scatter(title="No data available")
        
        fig = go.Figure()
        self.get_program_colors(df)  # Ensuring color consistency
        color_map = self.program_colors if entity == 'program_id' else college_colors
        
        for value in sdg_count[entity].unique():
            entity_data = sdg_count[sdg_count[entity] == value]
            fig.add_trace(go.Scatter(
                x=[int(sdg.split(" ")[1]) for sdg in entity_data['sdg']],  # Ensure x values are numeric
                y=entity_data[entity],
                mode='markers',
                marker=dict(
                    size=entity_data['Count'],
                    color=color_map.get(value, 'grey'),
                    sizemode='area',
                    sizeref=2. * max(sdg_count['Count']) / (100**2),
                    sizemin=4
                ),
                name=value
            ))

        fig.update_layout(
            xaxis_title='SDG Targeted',
            yaxis_title='Programs' if entity == 'program_id' else 'Colleges',
            title=title,
            xaxis=dict(
                categoryorder="array",
                categoryarray=["SDG " + str(i) for i in range(1, 18)],  # Ensuring SDG 1 to 17 in order
                tickvals=list(range(1, 18)),
                ticktext=["SDG " + str(i) for i in range(1, 18)]
            ),
            yaxis=dict(autorange="reversed"),
            showlegend=True,
            legend=dict(
                itemsizing="constant",  # Ensures uniform marker sizes in the legend
            ),
            legend_tracegroupgap=5,
            height=300 if user_id == "05" else None
        )
        
        return fig

    def scopus_line_graph(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, default_years):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        
        # Determine filter parameters based on user_id
        college_filter = selected_colleges if user_id in ["02", "03"] else None
        program_filter = selected_programs if user_id in ["04", "05"] else None
        
        # Fetch data
        filtered_data = get_data_for_scopus_section(college_filter, program_filter, selected_status, selected_years, selected_terms)
        df = pd.DataFrame(filtered_data)
        df = df[df['scopus'] != 'N/A']  # Filter out 'N/A' values
        
        # Group and ensure numeric types
        grouped_df = df.groupby(['scopus', 'year']).size().reset_index(name='Count')
        grouped_df[['year', 'Count']] = grouped_df[['year', 'Count']].astype(int)

        # Ensure the first year - 1 exists with count 0 if the first year is in selected_years
        if not grouped_df.empty:
            first_year = default_years[0]
            
            if first_year in selected_years:
                previous_year = first_year - 1
                
                # Get unique scopus categories
                scopus_categories = grouped_df['scopus'].unique()
                
                # Create missing rows
                missing_rows = pd.DataFrame({'scopus': scopus_categories, 'year': previous_year, 'Count': 0})
                
                # Append to the dataframe
                grouped_df = pd.concat([missing_rows, grouped_df], ignore_index=True)

        # Create the line chart
        fig_line = px.line(
            grouped_df, x='year', y='Count', color='scopus',
            color_discrete_map=college_colors, labels={'scopus': 'Scopus vs. Non-Scopus'}, markers=True
        )
        
        # Update layout
        fig_line.update_traces(line=dict(width=1.5), marker=dict(size=5))
        fig_line.update_layout(
            title=dict(text='Scopus vs. Non-Scopus Publications Over Time', font=dict(size=12)),
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white', height=300 if user_id != "05" else 200,
            margin=dict(l=5, r=5, t=30, b=30),
            xaxis=dict(type='linear', tickangle=-45, automargin=True, tickfont=dict(size=10)),
            yaxis=dict(automargin=True, tickfont=dict(size=10)),
            legend=dict(font=dict(size=9))
        )
        
        return fig_line
    
    def scopus_pie_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Determine filtering criteria based on user_id
        colleges = selected_colleges if user_id in ["02", "03"] else None
        programs = selected_programs if user_id in ["04", "05"] else None
        
        # Fetch and process data
        filtered_data_with_term = get_data_for_scopus_section(colleges, programs, selected_status, selected_years, selected_terms)
        df = pd.DataFrame(filtered_data_with_term)
        df = df[df['scopus'] != 'N/A']  # Remove 'N/A' values
        grouped_df = df.groupby(['scopus']).size().reset_index(name='Count')

        # Create pie chart
        fig_pie = px.pie(
            grouped_df,
            names='scopus',
            values='Count',
            color='scopus',
            color_discrete_map=college_colors,
            labels={'scopus': 'Scopus vs. Non-Scopus'}
        )

        # Adjust layout and styling
        fig_pie.update_traces(
            textfont=dict(size=9),
            insidetextfont=dict(size=9),
            marker=dict(line=dict(width=0.5))
        )
        fig_pie.update_layout(
            title=dict(text='Scopus vs. Non-Scopus Research Distribution', font=dict(size=12)),
            template='plotly_white',
            height=200 if user_id == "05" else 300,  # Adjust height for user_id 05
            margin=dict(l=5, r=5, t=30, b=30),
            legend=dict(font=dict(size=9))
        )
        
        return fig_pie
    
    def publication_format_line_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, default_years):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Determine data filtering based on user_id
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms)
        else:  # Covers both user_id "04" and "05"
            filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame and apply filters
        df = pd.DataFrame(filtered_data_with_term)
        df = df[(df['journal'] != 'unpublished') & (df['status'] != 'PULLOUT')]
        
        # Group data by 'journal' and 'year'
        grouped_df = df.groupby(['journal', 'year']).size().reset_index(name='Count')
        grouped_df[['year', 'Count']] = grouped_df[['year', 'Count']].astype(int)

        # Ensure the first year - 1 exists with count 0 if the first year is in selected_years
        if not grouped_df.empty:
            first_year = default_years[0]
            
            if first_year in selected_years:
                previous_year = first_year - 1

                # Get unique journal categories
                journal_categories = grouped_df['journal'].unique()

                # Create missing rows
                missing_rows = pd.DataFrame({'journal': journal_categories, 'year': previous_year, 'Count': 0})

                # Append to the dataframe
                grouped_df = pd.concat([missing_rows, grouped_df], ignore_index=True)

        # Create the line chart with markers
        fig_line = px.line(
            grouped_df,
            x='year',
            y='Count',
            color='journal',
            color_discrete_map=college_colors,
            labels={'journal': 'Publication Type'},
            markers=True
        )

        # Update layout for smaller text and responsive UI
        fig_line.update_traces(line=dict(width=1.5), marker=dict(size=5))
        fig_line.update_layout(
            title=dict(text='Publication Types Over Time', font=dict(size=12)),
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=300 if user_id != "05" else 200,  # Adjust height for user_id "05"
            margin=dict(l=5, r=5, t=30, b=30),
            xaxis=dict(type='linear', tickangle=-45, automargin=True, tickfont=dict(size=10)),
            yaxis=dict(automargin=True, tickfont=dict(size=10)),
            legend=dict(font=dict(size=9))
        )

        return fig_line

    def publication_format_pie_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)

        # Determine the filtering parameters based on user_id
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms)
        else:  # For user_id "04" and "05"
            filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms)

        # Convert data to DataFrame and apply filters
        df = pd.DataFrame(filtered_data_with_term)
        df = df[(df['journal'] != 'unpublished') & (df['status'] != 'PULLOUT')]

        # Group data by 'journal' and sum the counts
        grouped_df = df.groupby(['journal']).size().reset_index(name='Count')

        # Create the pie chart
        fig_pie = px.pie(
            grouped_df,
            names='journal',
            values='Count',
            color='journal',
            color_discrete_map=college_colors,
            labels={'journal': 'Publication Type'}
        )

        # Update layout for a smaller and more responsive design
        fig_pie.update_traces(
            textfont=dict(size=9),
            insidetextfont=dict(size=9),
            marker=dict(line=dict(width=0.5))
        )

        fig_pie.update_layout(
            title=dict(text='Publication Type Distribution', font=dict(size=12)),
            template='plotly_white',
            height=200 if user_id == "05" else 300,  # Adjust height for user_id "05"
            margin=dict(l=5, r=5, t=30, b=30),
            legend=dict(font=dict(size=9))
        )

        return fig_pie