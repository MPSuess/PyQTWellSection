
import json
import numpy as np
from pathlib import Path
import re


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

def load_petrel_wellheads(path):
    """
    Load a Petrel 'well head' file and return a list of well dictionaries
    compatible with WellPanelWidget (x, y, reference_type, reference_depth, total_depth, tops).
    Handles Petrel's typical Windows encodings and degree symbols.
    """
    path = Path(path)

    # ---------- robust text reading with encoding fallback ----------
    def _safe_read_lines(p: Path):
        last_err = None
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                with p.open("r", encoding=enc) as f:
                    text = f.read()
                # normalize weird degree symbol used in some Petrel exports
                text = text.replace("∞", "°")
                # keep only non-empty lines
                return [line.strip() for line in text.splitlines() if line.strip()]
            except UnicodeDecodeError as e:
                last_err = e
                continue
        if last_err is not None:
            raise last_err
        raise ValueError(f"Could not decode file {p}")

    lines = _safe_read_lines(path)

    # ---------- find header block safely ----------
    begin_idx = None
    end_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("BEGIN HEADER"):
            begin_idx = i
        elif ln.startswith("END HEADER"):
            end_idx = i
            break

    if begin_idx is None or end_idx is None:
        raise ValueError("BEGIN HEADER / END HEADER block not found in Petrel well head file")

    if end_idx <= begin_idx + 1:
        raise ValueError("Header block appears to be empty or malformed")

    header_lines = lines[begin_idx + 1:end_idx]
    headers = [h.strip() for h in header_lines if h.strip()]

    if not headers:
        raise ValueError("No header columns found between BEGIN HEADER and END HEADER")

    # data lines start after END HEADER
    data_lines = [
        ln for ln in lines[end_idx + 1:]
        if not ln.startswith("#") and ln.strip()
    ]
    if not data_lines:
        raise ValueError("No data lines found after END HEADER")

    # regex: quoted strings or non-space tokens
    pattern = re.compile(r'"[^"]*"|\S+')

    def to_float(val):
        if val is None:
            return None
        v = str(val).strip()
        if v in ("-999", "NULL", ""):
            return None
        try:
            return float(v)
        except ValueError:
            return None

    wells = []

    for line in data_lines:
        tokens = [t.strip('"') for t in pattern.findall(line)]

        if len(tokens) != len(headers):
            # instead of blowing up, just skip and optionally log
            # print(f"Skipping malformed line: got {len(tokens)} tokens, expected {len(headers)}\n{line}")
            continue

        row = dict(zip(headers, tokens))

        name = (row.get("Name") or "").strip()
        uwi = (row.get("UWI") or "").strip()

        surface_x = to_float(row.get("Surface X"))
        surface_y = to_float(row.get("Surface Y"))
        lat = row.get("Latitude", "")
        lon = row.get("Longitude", "")

        ref_name = (row.get("Well datum name") or "").strip()  # e.g. "KB"
        ref_value = to_float(row.get("Well datum value"))
        td_md = to_float(row.get("TD (MD)"))

        bh_x = to_float(row.get("Bottom hole X"))
        bh_y = to_float(row.get("Bottom hole Y"))

        # Fallbacks if some values are missing
        if ref_value is None:
            ref_value = 0.0
        if td_md is None:
            td_md = 0.0

        well = {
            "name": name or uwi or "UNKNOWN",
            #"uwi": uwi,
            "x": surface_x,
            "y": surface_y,
            #"latitude": lat,
            #"longitude": lon,
            "reference_type": ref_name or "KB",
            "reference_depth": ref_value,
            "total_depth": td_md,
            #"bottom_hole_x": bh_x,
            #"bottom_hole_y": bh_y,
            "tops": {},  # Petrel well head file doesn't include tops
            "logs": {}, # Petrel well head file doesn't include logs'
        }

        wells.append(well)

    if not wells:
        raise ValueError(
            "No valid wells parsed. "
            "Check that the file has data rows matching the header column count."
        )

    return wells

