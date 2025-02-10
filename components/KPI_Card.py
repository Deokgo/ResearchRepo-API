import dash_bootstrap_components as dbc
import dash_html_components as html

def KPI_Card(title, value, id, icon=None, color="primary"):
    return dbc.Button(
        [
            html.I(className=icon, style={"fontSize": "20px"}) if icon else None,
            html.Div(
                [
                    html.Small(title, className="d-block text-muted"),
                    html.H5(value, className="mb-0", id=id),
                ]
            ),
        ],
        color=color,
        outline=True,
        className="d-flex align-items-center gap-2 p-3 text-start",
        style={"width": "200px", "height": "80px", "cursor": "pointer"},
        id=f"btn-{id}",  # Button ID
    )