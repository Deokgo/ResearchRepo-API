import dash_bootstrap_components as dbc
import dash_html_components as html

def KPI_Card(title, value, id, icon=None, color="primary"):
    return dbc.Button(
        [
            html.Div(
                [
                    # Icon (mas maliit)
                    html.I(className=icon, style={"fontSize": "14px", "alignSelf": "start"}) if icon else None,
                    html.Div(
                        [
                            html.H3(value, className="mb-0 fw-bold", id=id),  # Mas maliit na text
                            html.Small(title, className="text-muted"),  # Title lagi visible
                        ],
                        className="text-center",
                    ),
                ],
                className="d-flex flex-column align-items-center justify-content-center position-relative w-100",
            )
        ],
        color=color,
        outline=True,
        className="p-2 text-start position-relative",  # Binawasan ang padding
        style={"width": "150px", "height": "90px", "cursor": "pointer"},  # Mas maliit na width at height
        id=f"btn-{id}",
    )
