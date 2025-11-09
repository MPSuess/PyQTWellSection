import numpy as np
from multi_wells_panel import draw_multi_wells_panel_on_figure

# --- DEMO WELL: no continuous log data ---

demo_well = {
    "name": "Well_A",
    "reference_depth": 1000,   # depth of KB or datum
    "total_depth": 300,        # total measured depth from reference
    "logs": {},                # no continuous logs

    "discrete_logs": {},       # no discrete logs yet

    # define a few formation tops (depths relative to reference)
    "tops": {

    },
}

demo_well_B = {
    "name": "Well_B",
    "reference_depth": 1020,
    "total_depth": 320,
    "logs": {},
    "discrete_logs": {},
    "tops": {
    },
}

tracks = [
    {"logs": []},  # empty track
]


import matplotlib.pyplot as plt

fig = plt.figure(figsize=(10, 6))

axes, well_main_axes = draw_multi_wells_panel_on_figure(
    fig,
    wells=[demo_well, demo_well_B],
    tracks=tracks,
    suptitle="Demo Wells Without Logs",
)

plt.show()