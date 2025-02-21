import dash_bootstrap_components as dbc
import dash_html_components as html

def KPI_Card(title, value, id, icon=None, color="primary"):
    return dbc.Button(
        [
            html.Div(
                [
                    # Icon (smaller size for responsiveness)
                    html.I(className=icon, style={"fontSize": "14px", "alignSelf": "start"}) if icon else None,
                    html.Div(
                        [
                            html.H3(value, className="mb-0 fw-bold", id=id),  # Smaller text
                            html.Small(title, style={"color": "inherit"}),  # Inherit color from H3
                        ],
                        className="text-center",
                    ),
                ],
                className="d-flex flex-column align-items-center justify-content-center position-relative w-100",
            )
        ],
        color=color,
        outline=True,
        className="p-2 text-start position-relative",  # Reduced padding
        style={
            "width": "100%",  # Full width by default
            "maxWidth": "180px",  # Restrict max width for large screens
            "height": "auto",  # Auto height for responsiveness
            "minHeight": "90px",  # Minimum height for consistency
            "cursor": "pointer",
        },
        id=f"btn-{id}",
    )
