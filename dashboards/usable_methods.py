import os
import datetime
from pathlib import Path
import numpy as np
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from io import BytesIO
import base64

def default_if_empty(selected_values, default_values):
    """
    Returns default_values if selected_values is empty.
    """
    return selected_values if selected_values else default_values

def ensure_list(value):
    """
    Ensures that the given value is always returned as a list.
    - If it's a NumPy array, convert it to a list.
    - If it's a string, wrap it in a list.
    - If it's already a list, return as is.
    """
    if isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, str):
        return [value]
    return value  # Return as is if already a list or another type

def download_file(df, file):
    """Creates a downloadable file and returns it in a format Dash can use for client-side downloads."""
    # Create Excel file in memory
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    # Create a download dictionary that Dash can use
    content = output.getvalue()
    b64 = base64.b64encode(content).decode()
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{file}_{timestamp}.xlsx"
    
    return dict(
        content=b64,
        filename=filename,
        type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        base64=True
    )

def get_gradient_color(degree, min_degree, max_degree):
    if max_degree == min_degree:
        return "rgb(173, 216, 230)"  # Default to light blue-indigo if all nodes have the same degree

    # Normalize degree to range 0-1
    ratio = (degree - min_degree) / (max_degree - min_degree)

    # Transition from Light Blue-Indigo (173, 216, 230) to Deep Blue-Indigo (0, 0, 139)
    red = int(173 - (173 * ratio))   # Red decreases from 173 to 0
    green = int(216 - (216 * ratio)) # Green decreases from 216 to 0
    blue = int(230 - (91 * ratio))   # Blue decreases from 230 to 139

    return f"rgb({red}, {green}, {blue})"


def create_graph_card(graph_id, loading_id):
    return dbc.Card(
        dcc.Loading(
            id=loading_id,
            type='circle',
            children=dcc.Graph(id=graph_id, config={'responsive': True})
        ),
        body=True,
        className="flex-fill"
    )