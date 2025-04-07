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
        self.scopus_colors = {}
        self.pub_format_colors = {}
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
    
    def assign_colors(self, df, column_name):
        unique_values = df[column_name].unique()
        available_colors = px.colors.qualitative.T10  # Colorblind-friendly palette

        # Determine which dictionary to update
        if column_name == 'scopus':
            target_dict = self.scopus_colors
        elif column_name == 'journal':
            target_dict = self.pub_format_colors
        else:
            target_dict = self.program_colors

        used_colors = set(target_dict.values())  # Track assigned colors

        for value in unique_values:
            if value not in target_dict:
                # Find an unused color from the palette
                unused_colors = [color for color in available_colors if color not in used_colors]

                if unused_colors:
                    chosen_color = unused_colors.pop(0)  # Take the first unused color
                else:
                    # Generate a random distinct color if all predefined colors are used
                    chosen_color = f"rgb({random.randint(0,255)},{random.randint(0,255)},{random.randint(0,255)})"

                target_dict[value] = chosen_color
                used_colors.add(chosen_color)
    
    def update_line_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, default_years, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)
        
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_performance_overview(selected_colleges, None, selected_status, selected_years, selected_terms, selected_pub_format)
            df = pd.DataFrame(filtered_data_with_term)
            if df.empty:
                return px.bar(title="No data available")
            
            if len(selected_colleges) == 1:
                label = {'program_id': 'Programs'}
                grouped_df = df.groupby(['program_id', 'year']).size().reset_index(name='TitleCount')
                color_column = 'program_id'
                title = f'Number of Research Outputs for {selected_colleges[0]}'
                self.assign_colors(grouped_df, 'program_id')
                color_discrete_map = self.program_colors if isinstance(self.program_colors, dict) else {}
            else:
                label = {'college_id': 'Colleges'}
                grouped_df = df.groupby(['college_id', 'year']).size().reset_index(name='TitleCount')
                color_column = 'college_id'
                title = 'Number of Research Outputs per College'
                color_discrete_map = college_colors if isinstance(college_colors, dict) else {}
        
        elif user_id in ["04", "05"]:
            filtered_data_with_term = get_data_for_performance_overview(None, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format)
            df = pd.DataFrame(filtered_data_with_term)
            if df.empty:
                return px.bar(title="No data available")
            
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
            
            self.assign_colors(df, 'program_id')
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
        else:
            return px.line(title="No data available")

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

        fig_line.update_traces(
            hovertemplate="Year: %{x}<br>"
                        "Number of Research Outputs: %{y}<extra></extra>"
        )

        
        return fig_line

    def update_pie_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)
        
        # Determine the filtering parameters based on user_id
        colleges, programs = (selected_colleges, None) if user_id in ["02", "03"] else (None, selected_programs)
        
        # Fetch data
        filtered_data_with_term = get_data_for_performance_overview(colleges, programs, selected_status, selected_years, selected_terms, selected_pub_format)
        df = pd.DataFrame(filtered_data_with_term)

        if df.empty:
            return px.pie(title="No Data Available", template='plotly_white')
        
        if user_id in ["02", "03"] and len(selected_colleges) == 1:
            detail_counts = df[df['college_id'] == selected_colleges[0]].groupby('program_id').size()
            self.assign_colors(df, 'program_id')
            title, color_map = f'Research Output Distribution for {selected_colleges[0]}', self.program_colors
        elif user_id in ["04", "05"] and len(selected_programs) == 1:
            detail_counts = df[df['program_id'] == selected_programs[0]].groupby('year').size().reset_index(name='count')
            title, color_map = f"Research Output Distribution for {selected_programs[0]}", None
        else:
            detail_counts = df.groupby('college_id' if user_id in ["02", "03"] else 'program_id').size().reset_index(name='count')
            title = 'Research Output Distribution by College' if user_id in ["02", "03"] else 'Research Outputs per Program'
            self.assign_colors(df, 'program_id')
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

        fig_pie.update_traces(
            hovertemplate="%{label}<br>"
                        "Number of Research Outputs: %{value}<extra></extra>"
        )
        
        return fig_pie
    
    def update_research_type_bar_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)

        filter_college = selected_colleges if user_id in ["02", "03"] else None
        filter_program = selected_programs if user_id in ["04", "05"] else None
        
        df = pd.DataFrame(get_data_for_research_type_bar_plot(filter_college, filter_program, selected_status, selected_years, selected_terms, selected_pub_format))
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
            self.assign_colors(df, 'program_id')
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
                marker_color=color_map.get(group, 'grey'),
                hovertemplate="%{customdata}<br>"
                            "Research Type: %{x}<br>"
                            "Number of Research Outputs: %{y}<extra></extra>",
                customdata=[group] * len(pivot_df)  # Pass the group name dynamically
            ))

        fig.update_layout(
            barmode='group',
            xaxis_title=dict(text='Research Type', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            title=dict(text=title, font=dict(size=12)),
            height=None
        )
        
        return fig
    
    def update_research_status_bar_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)

        data_params = {
            "02": (selected_colleges, None),
            "03": (selected_colleges, None),
            "04": (None, selected_programs),
            "05": (None, selected_programs),
        }

        if user_id not in data_params:
            return px.bar(title="Invalid User ID")

        filtered_data_with_term = get_data_for_research_status_bar_plot(
            *data_params[user_id], selected_status, selected_years, selected_terms, selected_pub_format
        )

        df = pd.DataFrame(filtered_data_with_term)
        if df.empty:
            return px.bar(title="No data available")
        df['status'] = df['status'].replace({'PULLOUT': 'PULLED-OUT'})
        status_order = ['READY', 'SUBMITTED', 'ACCEPTED', 'PUBLISHED', 'PULLED-OUT']
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
                marker_color=colors.get(category, 'grey'),
                hovertemplate="%{customdata}<br>"
                            "Research Status: %{x}<br>"
                            "Number of Research Outputs: %{y}<extra></extra>",
                customdata=[category] * len(pivot_df)  # Pass the college/program name dynamically
            ))

        fig.update_layout(
            barmode='group',
            title=dict(text=f"Comparison of Research Status {title_suffix}", font=dict(size=12)),
            xaxis_title="Research Status",
            yaxis_title="Research Outputs",
            xaxis=dict(tickvals=status_order, ticktext=status_order, categoryorder='array', categoryarray=status_order),
            height=None
        )

        return fig
    
    def create_publication_bar_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)
        
        data_func_args = (selected_colleges, None) if user_id in ["02", "03"] else (None, selected_programs)
        df = pd.DataFrame(get_data_for_scopus_section(*data_func_args, selected_status, selected_years, selected_terms, selected_pub_format))
        if 'scopus' in df.columns:
            df = df[df['scopus'] != 'N/A']  # Remove 'N/A' values
        
        # Assign colors for scopus column
        self.assign_colors(df, 'scopus')
        
        if df.empty:
            return px.bar(title="No data available")
        
        if user_id in ["02", "03"] and len(selected_colleges) == 1:
            x_axis, xaxis_title = 'program_id', 'Programs'
            title = f'Scopus vs. Non-Scopus per Program in {selected_colleges[0]}'
        else:
            x_axis, xaxis_title = ('college_id', 'Colleges') if user_id in ["02", "03"] else ('program_id', 'Programs')
            title = 'Scopus vs. Non-Scopus per College' if x_axis == 'college_id' else 'Scopus vs. Non-Scopus per Program'
        
        if user_id in ["04", "05"]:
            self.assign_colors(df, 'program_id')
        
        grouped_df = df.groupby(['scopus', x_axis]).size().reset_index(name='Count')
        
        fig_bar = px.bar(
            grouped_df, x=x_axis, y='Count', color='scopus', barmode='group', 
            color_discrete_map=self.scopus_colors, labels={'scopus': 'Scopus vs. Non-Scopus'}
        )
        
        fig_bar.update_layout(
            title=dict(text=title, font=dict(size=12)),
            xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white', height=None
        )

        fig_bar.update_traces(
            hovertemplate="%{x}<br>"
                        "Number of Research Outputs: %{y}<extra></extra>"
        )

        
        return fig_bar
    
    def update_publication_format_bar_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)

        # Determine filtering based on user_id
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms, selected_pub_format)
        else:
            filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format)
        
        # Convert data to DataFrame
        df = pd.DataFrame(filtered_data_with_term)
        if 'journal' in df.columns:
            df = df[(df['journal'] != 'unpublished') & (df['status'] != 'PULLOUT')]
        
        # Assign colors for scopus column
        self.assign_colors(df, 'journal')

        if df.empty:
            return px.bar(title="No Data Available")
        
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
            color_discrete_map=self.pub_format_colors, labels={'journal': 'Publication Type'}
        )
        
        # Adjust layout
        fig_bar.update_layout(
            title=dict(text=title, font=dict(size=12)),
            xaxis_title=dict(text=xaxis_title, font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=None
        )

        fig_bar.update_traces(
            hovertemplate="%{x}<br>"
                        "Number of Research Outputs: %{y}<extra></extra>"
        )

        
        return fig_bar
    
    def update_sdg_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)
        
        user_filters = {
            "02": (selected_colleges, None),
            "03": (selected_colleges, None),
            "04": (None, selected_programs),
            "05": (None, selected_programs)
        }
        
        if user_id not in user_filters:
            return px.scatter(title="Invalid User ID")
        
        filtered_data = get_data_for_sdg(*user_filters[user_id], selected_status, selected_years, selected_terms, selected_pub_format)
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
        
        # Check if 'sdg' column exists in the dataframe
        if 'sdg' not in df.columns:
            return px.scatter(title="No SDG data available")
        
        # Safely expand SDG data
        try:
            df_expanded = df.set_index(entity)['sdg'].str.split(';').apply(pd.Series).stack().reset_index(name='sdg')
            df_expanded['sdg'] = df_expanded['sdg'].str.strip()
            df_expanded = df_expanded[df_expanded['sdg'] != 'Not Specified']
            if 'level_1' in df_expanded.columns:
                df_expanded.drop(columns=['level_1'], inplace=True)
                
            # Check if df_expanded is empty after processing
            if df_expanded.empty:
                return px.scatter(title="No SDG data available")
            
            sdg_count = df_expanded.groupby(['sdg', entity]).size().reset_index(name='Count')
        except Exception as e:
            print(f"Error in SDG data expansion: {e}")
            return px.scatter(title=f"Error processing SDG data: {e}")

        # Ensure all SDGs (1-17) are present
        all_sdgs = pd.DataFrame({'sdg': ["SDG " + str(i) for i in range(1, 18)]})
        
        # Create a cross product of all SDGs with all entities to ensure all combinations exist
        entities = df[entity].unique()  # Use original dataframe for entities
        all_combinations = []
        for sdg in all_sdgs['sdg']:
            for ent in entities:
                all_combinations.append({'sdg': sdg, entity: ent})
        
        all_combinations_df = pd.DataFrame(all_combinations)
        
        # Add debug prints
        print(f"all_combinations_df columns: {all_combinations_df.columns}")
        print(f"sdg_count columns: {sdg_count.columns}")
        
        # Ensure column names match before merging
        if 'sdg' in all_combinations_df.columns and 'sdg' in sdg_count.columns and entity in all_combinations_df.columns and entity in sdg_count.columns:
            # Merge with actual counts
            result = pd.merge(all_combinations_df, sdg_count, on=['sdg', entity], how='left')
            result['Count'] = result['Count'].fillna(0)  # Fill missing combinations with zero count
        else:
            print("Column mismatch during merge operation")
            missing_in_combinations = set(['sdg', entity]) - set(all_combinations_df.columns)
            missing_in_sdg_count = set(['sdg', entity]) - set(sdg_count.columns)
            print(f"Missing in all_combinations_df: {missing_in_combinations}")
            print(f"Missing in sdg_count: {missing_in_sdg_count}")
            return px.scatter(title="Data structure error - missing required columns")
        
        if result.empty:
            return px.scatter(title="No data available after merging")
        
        fig = go.Figure()
        self.assign_colors(df, 'program_id')  # Ensuring color consistency
        color_map = self.program_colors if entity == 'program_id' else college_colors
        
        # Extract SDG numbers for consistent ordering
        result['sdg_num'] = result['sdg'].str.extract(r'SDG (\d+)').astype(int)
        
        for value in result[entity].unique():
            entity_data = result[result[entity] == value]
            fig.add_trace(go.Scatter(
                x=entity_data['sdg_num'],  # Use the extracted numeric values
                y=[value] * len(entity_data),
                mode='markers',
                marker=dict(
                    size=entity_data['Count'],
                    color=color_map.get(value, 'grey'),
                    sizemode='area',
                    sizeref=2. * max(result['Count']) / (100**2),
                    sizemin=4
                ),
                name=value,
                hovertemplate="College/Program: %{y}<br>"
                            "SDG: %{customdata}<br>"
                            "Number of Research Outputs: %{marker.size}<extra></extra>",
                customdata=entity_data['sdg'].tolist()  # Pass the full SDG label for hover text
            ))

        fig.update_layout(
            xaxis_title='SDG Targeted',
            yaxis_title='Programs' if entity == 'program_id' else 'Colleges',
            title=title,
            xaxis=dict(
                tickvals=list(range(1, 18)),  # Tick marks at each SDG number
                ticktext=["SDG " + str(i) for i in range(1, 18)],  # Labels for each tick
                range=[0.5, 17.5]  # Ensure full range is visible
            ),
            yaxis=dict(autorange="reversed"),
            showlegend=True,
            legend=dict(
                itemsizing="constant",  # Ensures uniform marker sizes in the legend
            ),
            legend_tracegroupgap=5,
            height=None
        )
        
        return fig

    def scopus_line_graph(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, default_years, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)

        college_filter = selected_colleges if user_id in ["02", "03"] else None
        program_filter = selected_programs if user_id in ["04", "05"] else None

        filtered_data = get_data_for_scopus_section(college_filter, program_filter, selected_status, selected_years, selected_terms, selected_pub_format)
        df = pd.DataFrame(filtered_data)
        
        if 'scopus' in df.columns:
            df = df[df['scopus'] != 'N/A']

        if df.empty:
            return px.line(title="No data available")

        # Assign colors for scopus column
        self.assign_colors(df, 'scopus')

        grouped_df = df.groupby(['scopus', 'year']).size().reset_index(name='Count')
        grouped_df[['year', 'Count']] = grouped_df[['year', 'Count']].astype(int)

        if not grouped_df.empty:
            first_year = default_years[0]
            if first_year in selected_years:
                previous_year = first_year - 1
                scopus_categories = grouped_df['scopus'].unique()
                missing_rows = pd.DataFrame({'scopus': scopus_categories, 'year': previous_year, 'Count': 0})
                grouped_df = pd.concat([missing_rows, grouped_df], ignore_index=True)

        fig_line = px.line(
            grouped_df, x='year', y='Count', color='scopus',
            color_discrete_map=self.scopus_colors,
            labels={'scopus': 'Scopus vs. Non-Scopus'}, markers=True
        )

        fig_line.update_traces(
            line=dict(width=1.5),
            marker=dict(size=5),
            hovertemplate="Year: %{x}<br>Publications: %{y}<extra></extra>"
        )

        fig_line.update_layout(
            title=dict(text='Scopus vs. Non-Scopus Publications Over Time', font=dict(size=12)),
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white', height=None,
            margin=dict(l=5, r=5, t=30, b=30),
            xaxis=dict(type='linear', tickangle=-45, automargin=True, tickfont=dict(size=10)),
            yaxis=dict(automargin=True, tickfont=dict(size=10)),
            legend=dict(font=dict(size=9))
        )

        return fig_line


    def scopus_pie_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)

        colleges = selected_colleges if user_id in ["02", "03"] else None
        programs = selected_programs if user_id in ["04", "05"] else None

        filtered_data_with_term = get_data_for_scopus_section(colleges, programs, selected_status, selected_years, selected_terms, selected_pub_format)
        df = pd.DataFrame(filtered_data_with_term)

        if 'scopus' in df.columns:
            df = df[df['scopus'] != 'N/A']

        if df.empty:
            return px.pie(title="No Data Available", template='plotly_white')

        # Assign colors for scopus column
        self.assign_colors(df, 'scopus')

        grouped_df = df.groupby(['scopus']).size().reset_index(name='Count')

        fig_pie = px.pie(
            grouped_df,
            names='scopus',
            values='Count',
            color='scopus',
            color_discrete_map=self.scopus_colors,
            labels={'scopus': 'Scopus vs. Non-Scopus'}
        )

        fig_pie.update_traces(
            textfont=dict(size=9),
            insidetextfont=dict(size=9),
            marker=dict(line=dict(width=0.5)),
            hovertemplate="%{label}<br>Number of Publications: %{value}<br>"
        )

        fig_pie.update_layout(
            title=dict(text='Scopus vs. Non-Scopus Research Distribution', font=dict(size=12)),
            template='plotly_white',
            height=None,
            margin=dict(l=5, r=5, t=30, b=30),
            legend=dict(font=dict(size=9))
        )

        return fig_pie
    
    def publication_format_line_plot(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, default_years, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)

        # Determine data filtering based on user_id
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms, selected_pub_format)
        else:  # Covers both user_id "04" and "05"
            filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format)

        # Convert data to DataFrame and apply filters
        df = pd.DataFrame(filtered_data_with_term)
        if 'journal' in df.columns:
            df = df[(df['journal'] != 'unpublished') & (df['status'] != 'PULLOUT')]

        # Assign colors to journals before plotting
        self.assign_colors(df, 'journal')

        # Handle empty DataFrame case
        if df.empty:
            return px.line(title="No data available")
        
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
            color_discrete_map=self.pub_format_colors,
            labels={'journal': 'Publication Type'},
            markers=True
        )

        # Update layout for smaller text and responsive UI
        fig_line.update_traces(
            line=dict(width=1.5),
            marker=dict(size=5),
            hovertemplate="Year: %{x}<br>"
                        "Publications: %{y}<extra></extra>"
        )
        fig_line.update_layout(
            title=dict(text='Publication Types Over Time', font=dict(size=12)),
            xaxis_title=dict(text='Academic Year', font=dict(size=12)),
            yaxis_title=dict(text='Research Outputs', font=dict(size=12)),
            template='plotly_white',
            height=None,
            margin=dict(l=5, r=5, t=30, b=30),
            xaxis=dict(type='linear', tickangle=-45, automargin=True, tickfont=dict(size=10)),
            yaxis=dict(automargin=True, tickfont=dict(size=10)),
            legend=dict(font=dict(size=9))
        )

        return fig_line

    def publication_format_pie_chart(self, user_id, college_colors, selected_colleges, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format):
        selected_colleges = ensure_list(selected_colleges)
        selected_programs = ensure_list(selected_programs)
        selected_status = ensure_list(selected_status)
        selected_years = ensure_list(selected_years)
        selected_terms = ensure_list(selected_terms)
        selected_pub_format = ensure_list(selected_pub_format)

        # Determine the filtering parameters based on user_id
        if user_id in ["02", "03"]:
            filtered_data_with_term = get_data_for_jounal_section(selected_colleges, None, selected_status, selected_years, selected_terms, selected_pub_format)
        else:  # For user_id "04" and "05"
            filtered_data_with_term = get_data_for_jounal_section(None, selected_programs, selected_status, selected_years, selected_terms, selected_pub_format)

        # Convert data to DataFrame and apply filters
        df = pd.DataFrame(filtered_data_with_term)
        if 'journal' in df.columns:
            df = df[(df['journal'] != 'unpublished') & (df['status'] != 'PULLOUT')]

        # Assign colors to journals before plotting
        self.assign_colors(df, 'journal')

        # Handle empty DataFrame case
        if df.empty:
            return px.pie(title="No Data Available", template='plotly_white')

        # Group data by 'journal' and sum the counts
        grouped_df = df.groupby(['journal']).size().reset_index(name='Count')

        # Create the pie chart
        fig_pie = px.pie(
            grouped_df,
            names='journal',
            values='Count',
            color='journal',
            color_discrete_map=self.pub_format_colors,
            labels={'journal': 'Publication Type'}
        )

        fig_pie.update_traces(
            textfont=dict(size=9),
            insidetextfont=dict(size=9),
            marker=dict(line=dict(width=0.5)),
            hovertemplate="Publication Type: %{label}<br>"
                        "Number of Publications:</b> %{value}<br>"
        )

        # Add total count to title
        total_count = grouped_df['Count'].sum()
        fig_pie.update_layout(
            title=dict(text=f'Publication Type Distribution', font=dict(size=12)),
            template='plotly_white',
            height=None,
            margin=dict(l=5, r=5, t=30, b=30),
            legend=dict(font=dict(size=9))
        )

        return fig_pie