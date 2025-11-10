
import json
import numpy as np
from pathlib import Path
import re
import pandas as pd

def load_project_from_json(path):
    """Load a project from JSON file and return (wells, tracks, stratigraphy, metadata)."""
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    wells = data.get("wells", [])
    tracks = data.get("tracks", [])
    stratigraphy = data.get("stratigraphy", [])
    metadata = data.get("metadata", {})

    return wells, tracks, stratigraphy, metadata


def export_project_to_json(path, wells, tracks, stratigraphy=None, extra_metadata=None):
    """
    Export the current project to a JSON file (NumPy-safe).

    Parameters
    ----------
    path : str or Path
        Target filename (.json).
    wells : list
        List of well dictionaries.
    tracks : list
        List of track dictionaries.
    stratigraphy : list, optional
        Stratigraphic column (shallow -> deep).
    extra_metadata : dict, optional
        Any additional project metadata.
    """
    path = Path(path)

    project = {
        "wells": wells,
        "tracks": tracks,
    }
    if stratigraphy is not None:
        project["stratigraphy"] = stratigraphy
    if extra_metadata:
        project["metadata"] = extra_metadata

    with path.open("w", encoding="utf-8") as f:
        json.dump(project, f, indent=2, default=_json_serializer)

    return project


def _json_serializer(obj):
    """Handle non-JSON-serializable objects (e.g. NumPy types)."""
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (set, tuple)):
        return list(obj)
    # fallback to string
    return str(obj)



def _gather_project_state(self):
    """Collect data + settings to be exported as a JSON 'project' file."""
    state = {}

    # Core data
    for name in ["formation_tops", "wells"]:
        if hasattr(self, name):
            state[name] = self._to_json(getattr(self, name))

        # Logs (numeric curves) and their visibility
        if hasattr(self, "logs"):
            state["logs"] = self._to_json(getattr(self, "logs"))
        if hasattr(self, "visible_logs"):
            state["visible_logs"] = self._to_json(getattr(self, "visible_logs"))

    return state

def _to_json_scalar(self, obj):
    import numpy as _np
    try:
        if isinstance(obj, (_np.integer, _np.int_, _np.int32, _np.int64)):
            return int(obj)
        if isinstance(obj, (_np.floating, _np.float_, _np.float32, _np.float64)):
            return float(obj)
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
    except Exception:
        pass
    return str(obj)

def _to_json(self, obj):
    """Best-effort conversion of numpy arrays and common domain objects to JSON-serializable types."""
    import numpy as _np

    # numpy arrays -> list
    if isinstance(obj, _np.ndarray):
        return obj.tolist()

    # numpy scalar
    try:
        if isinstance(obj, (_np.generic,)):
            return self._to_json_scalar(obj.item())
    except Exception:
        pass

    # dict
    if isinstance(obj, dict):
        return {str(self._to_json(k)): self._to_json(v) for k, v in obj.items()}

    # list / tuple / set
    if isinstance(obj, (list, tuple, set)):
        return [self._to_json(v) for v in obj]

    # welly.Well minimal serialization (if present)
    try:
        import welly
        if isinstance(obj, welly.Well):
            data = {
                "name": getattr(obj, "name", None),
                "location": self._to_json(getattr(obj, "location", None)),
                "params": self._to_json(getattr(obj, "params", {})),
                "curves": {},
            }
            for c in getattr(obj, "curves", []):
                try:
                    mn = getattr(c, "mnemonic", getattr(c, "name", "UNK"))
                    vals = getattr(c, "values", getattr(c, "data", []))
                    data["curves"][str(mn)] = self._to_json(vals)
                except Exception:
                    continue
            return data
    except Exception:
        pass

    # fallback
    return self._to_json_scalar(obj)

def parse_petrel_wellhead_file(path):
    """Parse a Petrel Well Head file and return a DataFrame."""
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    # Find header block
    begin = lines.index("BEGIN HEADER")
    end = lines.index("END HEADER")
    header_lines = lines[begin + 1:end]
    headers = [h.strip() for h in header_lines]

    # Data starts after END HEADER
    data_lines = lines[end + 1:]

    # Petrel data lines: quoted strings + numbers separated by spaces
    # Split on spaces but preserve quoted substrings
    pattern = re.compile(r'"[^"]*"|\S+')

    records = []
    for line in data_lines:
        tokens = [t.strip('"') for t in pattern.findall(line)]
        if len(tokens) != len(headers):
            print(f"⚠️  Warning: skipping malformed line ({len(tokens)} vs {len(headers)}): {line}")
            continue
        records.append(tokens)

    df = pd.DataFrame(records, columns=headers)

    # Convert numeric fields (where possible)
    numeric_cols = [
        "Surface X", "Surface Y", "Well datum value", "TD (MD)",
        "Bottom hole X", "Bottom hole Y"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Replace Petrel nulls
    df.replace({"NULL": None, "-999": None}, inplace=True)

    return df
