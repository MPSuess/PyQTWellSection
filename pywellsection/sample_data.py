import numpy as np

def create_dummy_data_all():
    stratigraphy = {
        "Upper Formation A": {"level": "sequence", "color": "#ff0000"},
        "Formation A": {"level": "formation", "color": "#ffcc00"},
        "Sequence 1": { "level": "sequence"},
        "Member A1": {"level": "member"},
        "Carboniferous": {"level": "formation", "color": "#000000"},
        "Lower Formation A": {"level": "sequence", "color": "#0000ff"},
    }

    # Define depth intervals and facies
    top_depths = np.array([1000, 1050, 1100, 1150, 1220, 1280])
    bottom_depths = np.array([1050, 1100, 1150, 1220, 1280, 1300])
    facies = np.array(["Sandstone", "Shale", "Limestone", "Shale", "Dolomite", "Shale"])

    # Define colors for facies (for discrete track)
    facies_colors = {
        "Sandstone": "#f5d76e",  # yellowish
        "Shale": "#5c3d2e",  # dark brown
        "Limestone": "#a0c4ff",  # light blue
        "Dolomite": "#ffd6a5",  # beige
    }

    # Example depth intervals (some logs shorter than the well)
    depth_gr = np.linspace(1050, 1900, 300)
    depth_cal = np.linspace(1100, 1800, 250)
    depth_rt = np.linspace(1200, 2000, 350)
    depth_rhob = np.linspace(1000, 2000, 400)
    depth_phi = np.linspace(1300, 1950, 200)

    # Synthetic data
    gamma_ray = 80 + 20 * np.sin(depth_gr / 100)
    caliper = 10 + 2 * np.cos(depth_cal / 150)
    resistivity = 10 * np.exp(-depth_rt / 500) + 2
    density = 2.3 + 0.1 * np.cos(depth_rhob / 200)
    porosity = 0.25 + 0.05 * np.sin(depth_phi / 120)

    well1 = {
        "name": "Well A",
        "reference_depth": 950.0,  # KB / reference depth for this well
        "total_depth": 800.0,  # so interval is 950–1750 m
        "logs": {
            "GR": {"depth": depth_gr, "data": gamma_ray},
            "CAL": {"depth": depth_cal, "data": caliper},
            "RT": {"depth": depth_rt, "data": resistivity},
            "RHOB": {"depth": depth_rhob, "data": density},
            "PHI": {"depth": depth_phi, "data": porosity},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": top_depths,
                "bottom_depths": bottom_depths,
                "values": facies,
            }
        },
        "tops": {
            "Formation A": {"depth": 1100, "level": "formation", "color": "#ffcc00"},

            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        }    }

    well2 = {
        "name": "Well B",
        "reference_depth": 1010.0,  # different KB
        "total_depth": 1000.0,  # different TD -> 1010–2010 m
        "logs": {
            "GR": {"depth": depth_gr, "data": gamma_ray},
            "RT": {"depth": depth_rt, "data": resistivity},
            "RHOB": {"depth": depth_rhob, "data": density},
        },
        "tops": {
            "Formation A": {"depth": 1300, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1600, "level": "sequence"},
        }

    }

    well3 = {
        "name": "Well A",
        "reference_depth": 950.0,  # KB / reference depth for this well
        "total_depth": 800.0,  # so interval is 950–1750 m
        "logs": {
            "GR": {"depth": depth_gr, "data": gamma_ray},
            "CAL": {"depth": depth_cal, "data": caliper},
            "RT": {"depth": depth_rt, "data": resistivity},
            "RHOB": {"depth": depth_rhob, "data": density},
            "PHI": {"depth": depth_phi, "data": porosity},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": top_depths,
                "bottom_depths": bottom_depths,
                "values": facies,
            }
        },
        "tops": {
            "Formation A": {"depth": 1100, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        }    }



    tracks = [
        {
            "logs": [
                {"log": "GR", "label": "Gamma Ray (API)", "color": "green",
                 "xlim": (0, 150), "xscale": "linear", "direction": "normal"},
                {"log": "CAL", "label": "Caliper (in)", "color": "orange",
                 "xlim": (6, 16), "xscale": "linear", "direction": "reverse"},
            ],
        },
        {
            "logs": [
                {"log": "RT", "label": "Resistivity (Ω·m)", "color": "red",
                 "xlim": (1, 100), "xscale": "log", "direction": "normal"},
            ],
        },
        {
            "logs": [
                {"log": "RHOB", "label": "Density (g/cc)", "color": "blue",
                 "xlim": (1.9, 2.7), "xscale": "linear", "direction": "reverse"},
                {"log": "PHI", "label": "Porosity", "color": "purple",
                 "xlim": (0, 0.5), "xscale": "linear", "direction": "normal"},
            ],
        },
    {
        "discrete": {
            "log": "FACIES",
            "label": "Facies",
            "color_map": facies_colors,
            "default_color": "#dddddd",
        }
    },
    ]






    wells = [well1, well2, well3]

    return wells, tracks, stratigraphy

def create_dummy_data_0():
    wells = []
    tracks = []
    return wells, tracks

def create_top_only_Data ():

    stratigraphy = {
        "Formation A": {"level": "formation", "color": "#ffcc00"},
        "Sequence 1": { "level": "sequence"},
        "Member A1": {"level": "member"},
        "Carboniferous": {"level": "formation", "color": "#000000"},
    }


    well1 = {
        "name": "Well A",
        "reference_depth": 950.0,  # KB / reference depth for this well
        "total_depth": 800.0,  # so interval is 950–1750 m
        "tops": {
            "Formation A": {"depth": 1100, "level": "formation", "color": "#ffcc00"},

            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        }}

    well2 = {
        "name": "Well B",
        "reference_depth": 1010.0,  # different KB
        "total_depth": 1000.0,  # different TD -> 1010–2010 m
        "tops": {
            "Formation A": {"depth": 1300, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1600, "level": "sequence"},
        }

    }

    well3 = {
        "name": "Well A",
        "reference_depth": 950.0,  # KB / reference depth for this well
        "total_depth": 800.0,  # so interval is 950–1750 m
        "tops": {
            "Formation A": {"depth": 1100, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        }}

    wells = [well1, well2, well3]
    tracks = [
        {
            "logs": [
                {"log": "Dummy", "label": "Empty", "color": "green",
                 "xlim": (0, 150), "xscale": "linear", "direction": "normal"},
            ],
        },
        ]
    return wells, tracks


def create_dummy_data():
    wells, tracks, stratigraphy = create_dummy_data_all()
    return wells, tracks, stratigraphy