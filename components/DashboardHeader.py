import dash_bootstrap_components as dbc
from dash import html
from datetime import datetime

def DashboardHeader(left_text=None, title=None):
    return dbc.Row([
        # Left Section
        dbc.Col(
            html.P(left_text if left_text else html.Span("\u00A0"), 
                   style={
                       "color": "#6c757d",  # Grayish text
                       "fontSize": "16px",
                       "fontWeight": "500",
                       "opacity": "0.8",  # Slight transparency for a subtle effect
                       "whiteSpace": "nowrap",
                       "overflow": "hidden",
                       "textOverflow": "ellipsis"
                   }),
            style={
                "background": "white",
                "textAlign": "left",
                "display": "flex",
                "alignItems": "center",
                "paddingLeft": "15px",
                "flex": "1"
            }
        ),  

        # Center Title Section
        dbc.Col(
            html.P(title if title else html.Span("\u00A0"), 
                   style={
                       "color": "#343a40",  # Darker for emphasis
                       "fontSize": "22px",  # Bigger to stand out
                       "fontWeight": "bold",
                       "letterSpacing": "0.5px",
                       "textTransform": "uppercase",
                       "whiteSpace": "nowrap",
                       "overflow": "hidden",
                       "textOverflow": "ellipsis"
                   }),
            style={
                "background": "white",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "flex": "2",  # Takes more space to stay centered
                "textAlign": "center"
            }
        ),  

        # Right Section
        dbc.Col(
            html.P(f"as of {datetime.now():%B %d, %Y %I:%M %p}", 
                   style={
                       "color": "#6c757d",
                       "fontSize": "16px",
                       "fontWeight": "500",
                       "opacity": "0.8",
                       "whiteSpace": "nowrap",
                       "overflow": "hidden",
                       "textOverflow": "ellipsis"
                   }),
            style={
                "background": "white",
                "display": "flex",
                "alignItems": "center",
                "paddingRight": "15px",
                "flex": "1",
                "justifyContent": "flex-end"
            }
        )  

    ], id="content-row", style={
        "height": "5vh",
        "display": "flex",
        "alignItems": "center",
        "width": "100%",
        "flexWrap": "nowrap",
        "borderBottom": "1px solid #dee2e6",  # Thin separator line for cleaner look
        "background": "#f8f9fa"  # Light gray background for slight contrast
    })
