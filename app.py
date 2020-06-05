# Imports
import plotly.express as px
import plotly.graph_objects as go
from jupyter_dash import JupyterDash
from dash import callback_context
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import pandas
import os, ntpath


## Helpers
#

def options_factory(iterable, label_accessor=lambda x: x, value_accessor=lambda x: x):
    """
    Factory function for creating a dash dropdown menu's 'options' attribute.

    Positional arguments:
    iterable -- any iterable data structure.

    Keyword arguments (optional):
    label_accessor -- function to retrieve the label from a single data point in iterable.
    value_accessor -- function to retrieve the value from a single data point in iterable.

    Returns a list of dictionaries with keys 'label' and 'value'.
    """
    return [
        { 'label': label_accessor(d), 'value': value_accessor(d) }
        for d in iterable
    ]


def read_ensemble_data_from_results_folder(folder):
    """
    Read GillesPy2 ensemble simulation results into a list of pandas data frames.
    
    Positional arguments:
    folder -- folder on disk containing csv files with one trajectory result per file.
    
    Returns:
    List of pandas data frames where the indices represent trajectory numbers and 
    values represent 2-dimensional arrays where columns are species and rows are 
    result values for each species at some time step.
    """
    files = sorted([ os.path.join(results_dir, f) for f in os.listdir(results_dir) ])
    dfs = [ pandas.read_csv(f_path) for f_path in files ]
    return dfs


def defaultLocalStore(trajectories):
	"""
	Initial client-side JSON storage for callbacks to refernece.
	"""
	group_assigns = [None] * len(trajectories)
	return {
		'group_assigns': group_assigns
	}


# Extra styling for dropdowns
dropdown_styles = {}

# Default trajectory selector ('dropdown' or 'slider')
default_trajectory_selector = 'slider'

# Setup dropdown options
trajectory_options = options_factory(range(len(dfs)), label_accessor=lambda x: str(x+1))
species_options = options_factory([ c for c in dfs[0].columns if c != 'time' ])
group_options = range(1, 5)

# Read the data files into pandas dataframes
results_dir = './results_csv_06042020_150109/'
dfs = read_ensemble_data_from_results_folder(results_dir)

# Make the initial store
store = defaultLocalStore()


## App
#

app = JupyterDash(__name__)

## Fragments

# Trajectory selector (dropdown)
trajectory_selector_dropdown = html.Label([
    dcc.Dropdown(style=dropdown_styles,
        id='trajectory-selector', clearable=False,
        options=trajectory_options, value=0)
])

# Trajectory selector (slider)
trajectory_selector_slider = html.Div([
    dcc.Slider(
        id='trajectory-selector',
        min=0,
        max=len(trajectory_options)-1,
        step=1,
        value=0,
        marks = { i:str(i+1) for i in range(0, len(trajectory_options)) }
    ),
    html.Div(id='slider-output-container')
])

# Get default trajectory selector (slider or dropdown, determined from config above)
default_trajectory_selector = trajectory_selector_dropdown if default_trajectory_selector == 'dropdown' else trajectory_selector_slider


## Components

# Interface for assigning  trajectories to groups
group_assigner_layout = html.Div([
    html.H4(children="Assign Trajectories to Groups"),
    
    html.Div([
        html.Label("Select Trajectory"),
        html.Div(children=default_trajectory_selector, id='trajectory-selector-container'),
        html.Button('Dropdown', id='select-trajectory-dropdown-btn', n_clicks=0),
        html.Button('Slider', id='select-trajectory-slider-btn', n_clicks=0)
    ],
    id='trajectory-selector-wrapper',
    style={'padding-bottom': '1em'}),
    
    html.Label([
    "Show Species",
    dcc.Dropdown(style=dropdown_styles,
        id='species-dropdown-trajectory', clearable=False,
        value=dfs[0].columns[1], options=species_options)
    ]),
    html.Label([
    "Set Group",
    dcc.Dropdown(id='group-dropdown-trajectory', clearable=True, style=dropdown_styles, options=group_options, value=0)
    ]),
    dcc.Graph(id='graph')
    # Color scale dropdown menu
])

group_inspector_layout = html.Div([
    html.H4(children="Inspect Groups"),
    
    html.Label("Select Group"),
    
    html.Label([
    "Show Species",
    dcc.Dropdown(style=dropdown_styles,
        id='species-dropdown-group', clearable=False,
        value=1, options=group_options)
    ]),
    html.Label([
    "Select Group",
    dcc.Dropdown(id='group-inspector-select-group-dropdown', clearable=True, style=dropdown_styles, options=group_options, value=0)
    ]),
    dcc.Graph(id='graph')
    # Color scale dropdown menu
])

app.layout = html.Div([
    dcc.Store(id='memory', data=store),
    group_assigner_layout,
    group_inspector_layout
])

@app.callback(
    Output('trajectory-selector-container', 'children'),
    [Input('select-trajectory-dropdown-btn', 'n_clicks'),
     Input('select-trajectory-slider-btn', 'n_clicks')],
    [State('trajectory-selector-container', 'children')]
)
def update_trajectory_selector_dropdown(dropdown_n_clicks, slider_n_clicks, current):
    changed_id = [p['prop_id'] for p in callback_context.triggered][0]
    if 'select-trajectory-dropdown-btn' in changed_id and dropdown_n_clicks:
        return trajectory_selector_dropdown
    if 'select-trajectory-slider-btn' in changed_id and slider_n_clicks:
        return trajectory_selector_slider
    return current


# Define callback to update graph
@app.callback(
    Output('graph', 'figure'),
    [Input('species-dropdown-trajectory', 'value'),
     Input('trajectory-selector', 'value')]
)
def update_figure(species, trajectory):
    
    if species == 'ALL':
        species = y_column_names

    return px.line(
        dfs[trajectory], x="time", y=species,
        render_mode="webgl", title="Trajectory {}".format(trajectory+1)
    )


# Update the group dropdown when selected trajectory changes
@app.callback(
    Output('group-dropdown-trajectory', 'value'),
    [Input('memory', 'modified_timestamp'),
     Input('trajectory-selector', 'value')],
    [State('memory', 'data')]
)
def update_group_dropdown(timestamp, trajectory, memory):
    return memory['group_assigns'][trajectory]


# Store the trajectory's group when the user selects from the group dropdown
@app.callback(
    Output('memory', 'data'),
    [Input('group-dropdown-trajectory', 'value')],
    [State('trajectory-selector', 'value'),
     State('memory', 'data')]
     )
def set_trajectory_group(group, trajectory, memory):
    memory['group_assigns'][trajectory] = group
    return memory


# Run app and display result inline in the notebook
app.run_server(debug=True)
