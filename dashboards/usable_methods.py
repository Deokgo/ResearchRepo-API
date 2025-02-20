import os
import datetime
from pathlib import Path
import numpy as np

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
    """Handles saving the file and returns the file path."""
    downloads_folder = str(Path.home() / "Downloads")  # Works for Windows, Mac, Linux
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{file}_{timestamp}.xlsx"
    file_path = os.path.join(downloads_folder, file_name)

    # Save the file
    df.to_excel(file_path, index=False)

    return file_path

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
