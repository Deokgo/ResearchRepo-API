import dash_bootstrap_components as dbc
import dash_html_components as html

def Tabs(tabs_data, tabs_id="tabs"):
    """
    Creates a dynamic tab component.

    :param tabs_data: (list of tuples) Each tuple contains (tab_label, tab_content)
    :param tabs_id: (str) The id to assign to the dbc.Tabs component (default: 'tabs')
    :return: (html.Div) Tabs component
    """
    
    # Creating the list of tabs
    tab_elements = []
    
    # Dynamically adding other tabs based on input
    for index, (tab_label, tab_content) in enumerate(tabs_data, start=1):
        tab_elements.append(
            dbc.Tab(tab_content, label=tab_label, tab_id=f"tab-{index}")
        )
    
    return html.Div(
        [
            dbc.Tabs(
                tab_elements,
                id=tabs_id,  # Now we can pass the id here
                active_tab="tab-1",  # Default to first non-disabled tab
            ),
            html.Br(),
        ]
    )
