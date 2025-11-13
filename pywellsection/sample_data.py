import numpy as np

def create_dummy_data_all():
    stratigraphy = {
        "Upper Formation A": {"level": "sequence", "color": "#ff0000"},
        "Formation A": {"level": "formation", "color": "#ffcc00"},
        "Sequence 1": {"level": "sequence"},
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
        "Shale": "#5c3d2e",      # dark brown
        "Limestone": "#a0c4ff",  # light blue
        "Dolomite": "#ffd6a5",   # beige
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
        "UWI": "56032002322",
        "x": 654321.0,
        "y": 5234567.0,
        "reference_type": "KB",
        "reference_depth": 0.0,   # KB / reference depth for this well
        "total_depth": 500.0,      # interval is 950–2450 m
        "logs": {
            "GR": {"depth": np.linspace(0, 500, 500), "data": np.random.normal(50, 13, 500)},
            "CAL": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(10, .2, 500)},
            "RT": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(10, 5, 500)},
            "RHOB": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(2.3, .13, 500)},
            "PHI": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(.25, .03, 500)},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": np.array([0, 50, 100, 150, 200, 250]),
                "bottom_depths": np.array([50, 100, 150, 200, 250, 300]),
                "values": np.array(["Sandstone", "Shale", "Limestone", "Shale", "Dolomite", "Shale"]),
            }
        },
        "tops": {
            "Formation A": {"depth": 200, "level": "formation", "color": "#ffcc00"},
            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        },
    }

    well2 = {
        "name": "Well B",
        "UWI": "5603200223",
        "x": 654700.0,
        "y": 5234600.0,
        "reference_type": "RL",
        "reference_depth": 0.0,  # different KB
        "total_depth": 1000.0,      # interval is 1010–2510 m
        "logs": {
            "GR": {"depth": np.linspace(500, 1000, 500), "data": np.random.normal(50, 13, 500)},
            "RT": {"depth": np.linspace(500, 1000, 500), "data": np.exp(np.random.normal(1, 5, 500))},
            "RHOB": {"depth": np.linspace(500, 1000, 500), "data": np.random.normal(2.3, .13, 500)},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": np.array([500, 550, 600, 650, 700, 750]),
                "bottom_depths": np.array([550, 600, 650, 700, 750, 800]),
                "values": np.array(["Sandstone", "Shale", "Limestone", "Shale", "Dolomite", "Shale"]),
            }
        },
        "tops": {
            "Formation A": {"depth": 900, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1600, "level": "sequence"},
        },
    }

    well3 = {
        "name": "Well C",
        "UWI": "5603200224",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "RL",
        "reference_depth": 0.0,
        "total_depth": 1500.0,  # interval is 950–1750 m
        "logs": {
            "GR": {"depth": np.linspace(1000, 1500, 500), "data": np.random.normal(50, 13, 500)},
            "RT": {"depth": np.linspace(1000, 1500, 500), "data": np.exp(np.random.normal(1, 5, 500))},
            "RHOB": {"depth": np.linspace(1000, 1500, 500), "data": np.random.normal(2.3, .13, 500)},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": np.array([1000, 1050, 1100, 1150, 1200, 1250]),
                "bottom_depths": np.array([1050, 1100, 1150, 1200, 1250, 1300]),
                "values": np.array(["Sandstone", "Shale", "Limestone", "Shale", "Dolomite", "Shale"]),
            }
        },
        "tops": {
            "Formation A": {"depth": 1300, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        },
    }

    tracks = [
        {
            "logs": [
                {
                    "log": "GR",
                    "label": "Gamma Ray (API)",
                    "color": "green",
                    "xlim": (0, 150),
                    "xscale": "linear",
                    "direction": "normal",
                },
                {
                    "log": "CAL",
                    "label": "Caliper (in)",
                    "color": "orange",
                    "xlim": (6, 16),
                    "xscale": "linear",
                    "direction": "reverse",
                },
            ],
        },
        {
            "logs": [
                {
                    "log": "RT",
                    "label": "Resistivity (Ω·m)",
                    "color": "red",
                    "xlim": (1, 100),
                    "xscale": "log",
                    "direction": "normal",
                },
            ],
        },
        {
            "logs": [
                {
                    "log": "RHOB",
                    "label": "Density (g/cc)",
                    "color": "blue",
                    "xlim": (1.9, 2.7),
                    "xscale": "linear",
                    "direction": "reverse",
                },
                {
                    "log": "PHI",
                    "label": "Porosity",
                    "color": "purple",
                    "xlim": (0, 0.5),
                    "xscale": "linear",
                    "direction": "normal",
                },
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

def create_dummy_data_rand():
    stratigraphy = {
        "Upper Formation A": {"level": "sequence", "color": "#ff0000"},
        "Formation A": {"level": "formation", "color": "#ffcc00"},
        "Sequence 1": {"level": "sequence"},
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
        "Shale": "#5c3d2e",      # dark brown
        "Limestone": "#a0c4ff",  # light blue
        "Dolomite": "#ffd6a5",   # beige
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
        "UWI": "5603200233",
        "x": 654321.0,
        "y": 5234567.0,
        "reference_type": "KB",
        "reference_depth": 0.0,   # KB / reference depth for this well
        "total_depth": 500.0,      # interval is 950–2450 m
        "logs": {
            "GR": {"depth": np.linspace(0, 500, 500), "data": np.random.normal(50, 13, 500)},
            "CAL": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(10, .2, 500)},
            "RT": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(10, 5, 500)},
            "RHOB": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(2.3, .13, 500)},
            "PHI": {"depth": np.linspace(000, 500, 500), "data": np.random.normal(.25, .03, 500)},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": np.array([0, 50, 100, 150, 200, 250]),
                "bottom_depths": np.array([50, 100, 150, 200, 250, 300]),
                "values": np.array(["Sandstone", "Shale", "Limestone", "Shale", "Dolomite", "Shale"]),
            }
        },
        "tops": {
            "Formation A": {"depth": 200, "level": "formation", "color": "#ffcc00"},
            "Sequence 1": {"depth": 400, "level": "sequence"},
            "Carboniferous": {"depth": 450, "level": "formation", "color": "#000000"},
        },
    }

    well2 = {
        "name": "Well B",
        "UWI": "5603200231",
        "x": 654700.0,
        "y": 5234600.0,
        "reference_type": "RL",
        "reference_depth": 0.0,  # different KB
        "total_depth": 1000.0,      # interval is 1010–2510 m
        "logs": {
            "GR": {"depth": np.linspace(500, 1000, 500), "data": np.random.normal(50, 13, 500)},
            "RT": {"depth": np.linspace(500, 1000, 500), "data": np.exp(np.random.normal(1, 5, 500))},
            "RHOB": {"depth": np.linspace(500, 1000, 500), "data": np.random.normal(2.3, .13, 500)},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": np.array([500, 550, 600, 650, 700, 750]),
                "bottom_depths": np.array([550, 600, 650, 700, 750, 800]),
                "values": np.array(["Sandstone", "Shale", "Limestone", "Shale", "Dolomite", "Shale"]),
            }
        },
        "tops": {
            "Formation A": {"depth": 600, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 850, "level": "member"},
            "Sequence 1": {"depth": 900, "level": "sequence"},
        },
    }

    well3 = {
        "name": "Well C",
        "UWI": "5603200234",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "RL",
        "reference_depth": 0.0,

        "total_depth": 1500.0,  # interval is 950–1750 m
        "logs": {
            "GR": {"depth": np.linspace(1000, 1500, 500), "data": np.random.normal(50, 13, 500)},
            "RT": {"depth": np.linspace(1000, 1500, 500), "data": np.exp(np.random.normal(1, 5, 500))},
            "RHOB": {"depth": np.linspace(1000, 1500, 500), "data": np.random.normal(2.3, .13, 500)},
        },
        "discrete_logs": {
            "FACIES": {
                "top_depths": np.array([1000, 1050, 1100, 1150, 1200, 1250]),
                "bottom_depths": np.array([1050, 1100, 1150, 1200, 1250, 1300]),
                "values": np.array(["Sandstone", "Shale", "Limestone", "Shale", "Dolomite", "Shale"]),
            }
        },
        "tops": {
            "Formation A": {"depth": 1300, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1450, "level": "formation", "color": "#000000"},
        },
    }

    tracks = [
        {
            "logs": [
                {
                    "log": "GR",
                    "label": "Gamma Ray (API)",
                    "color": "green",
                    "xlim": (0, 150),
                    "xscale": "linear",
                    "direction": "normal",
                },
                {
                    "log": "CAL",
                    "label": "Caliper (in)",
                    "color": "orange",
                    "xlim": (6, 16),
                    "xscale": "linear",
                    "direction": "reverse",
                },
            ],
        },
        {
            "logs": [
                {
                    "log": "RT",
                    "label": "Resistivity (Ω·m)",
                    "color": "red",
                    "xlim": (1, 100),
                    "xscale": "log",
                    "direction": "normal",
                },
            ],
        },
        {
            "logs": [
                {
                    "log": "RHOB",
                    "label": "Density (g/cc)",
                    "color": "blue",
                    "xlim": (1.9, 2.7),
                    "xscale": "linear",
                    "direction": "reverse",
                },
                {
                    "log": "PHI",
                    "label": "Porosity",
                    "color": "purple",
                    "xlim": (0, 0.5),
                    "xscale": "linear",
                    "direction": "normal",
                },
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
    stratigraphy = []
    return wells, tracks, stratigraphy

def create_top_only_Data ():

    stratigraphy = {
        "Formation A": {"level": "formation", "color": "#ffcc00"},
        "Sequence 1": { "level": "sequence"},
        "Member A1": {"level": "member"},
        "Carboniferous": {"level": "formation", "color": "#000000"},
    }


    well1 = {
        "name": "Well A",
        "UWI": "5603200234",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "RL",
        "reference_depth": 950.0,  # KB / reference depth for this well
        "total_depth": 800.0,  # so interval is 950–1750 m
        "tops": {
            "Formation A": {"depth": 1100, "level": "formation", "color": "#ffcc00"},

            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        }}

    well2 = {
        "name": "Well B",
        "UWI": "5603200231",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "KB",
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
        "UWI": "5603200234",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "GF",
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

def create_dummy_data_wells_only():
    well1 = {
        "name": "Well A",
        "UWI": "5603200234",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "RL",
        "reference_depth": 950.0,  # KB / reference depth for this well
        "total_depth": 800.0,  # so interval is 950–1750 m
        "tops": {
            "Formation A": {"depth": 1100, "level": "formation", "color": "#ffcc00"},

            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        }}

    well2 = {
        "name": "Well B",
        "UWI": "5603200231",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "KB",
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
        "UWI": "5603200234",
        "x": 658500.0,
        "y": 5236600.0,
        "reference_type": "GF",
        "reference_depth": 950.0,  # KB / reference depth for this well
        "total_depth": 800.0,  # so interval is 950–1750 m
        "tops": {
            "Formation A": {"depth": 1100, "level": "formation", "color": "#ffcc00"},
            "Member A1": {"depth": 1350, "level": "member"},
            "Sequence 1": {"depth": 1400, "level": "sequence"},
            "Carboniferous": {"depth": 1600, "level": "formation", "color": "#000000"},
        }}

    wells = [well1, well2, well3]
    tracks = []
    stratigraphy = []
    return wells, tracks, stratigraphy




def create_dummy_data():
    wells, tracks, stratigraphy = create_dummy_data_rand()
    return wells, tracks, stratigraphy