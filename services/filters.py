def get_filtered_data(self, selected_colleges, selected_status, selected_years):
        if self.df is not None:
            filtered_df = self.df[
                (self.df['college_id'].isin(selected_colleges)) & 
                (self.df['status'].isin(selected_status)) & 
                (self.df['year'].between(selected_years[0], selected_years[1]))
            ]
            return filtered_df

def filtered_data(df, selected_colleges, selected_status, selected_years):
      filtered_df = df[(df['college_id'].isin(selected_colleges)) & 
                (df['status'].isin(selected_status)) & 
                (df['year'].between(selected_years[0], selected_years[1])    
      )]
      return filtered_df
