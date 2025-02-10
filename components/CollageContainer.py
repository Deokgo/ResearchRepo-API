import dash_html_components as html
import dash_bootstrap_components as dbc

def CollageContainer(children, column_count=4, gap="5px"):
    """
    A dynamic Masonry (collage) container using CSS columns.

    :param children: List of elements to be arranged like a collage.
    :param column_count: Number of columns in the collage.
    :param gap: Space between elements.
    """
    return dbc.Container(
        html.Div(
            children,
            style={
                "columnCount": str(column_count),  # Controls number of masonry columns
                "columnGap": gap,  # Space between columns
                "width": "100%",
            }
        ),
        fluid=True
    )
