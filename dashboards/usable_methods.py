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