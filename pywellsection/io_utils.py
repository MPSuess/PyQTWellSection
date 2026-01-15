
import json
from pathlib import Path
import re
import lasio
import numpy as np
import csv

from collections import defaultdict

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QComboBox, QLineEdit, QPushButton, QFileDialog,
    QDoubleSpinBox, QCheckBox, QDialogButtonBox, QMessageBox
)


def _file_load_tops_from_csv(self, path: str):
    """
    Load formation / fault tops from a CSV file with columns:
        Well_name, MD, Horizon, Name, Type

    and merge them into:
        - self.all_wells[*]["tops"]
        - self.stratigraphy (adds role if needed)

    Rules:
      - well must exist in self.all_wells (matched by well['name'])
      - top name is taken from:
          * if Type == 'Fault':  Name or Horizon
          * else:                Horizon or Name
      - role:
          * if Type == 'Fault'  -> 'fault'
          * else                -> 'stratigraphy'
      - depth is MD (float)
    """
    # ---- read CSV ----
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            rows = list(reader)
    except Exception as e:
        QMessageBox.critical(self, "Load tops CSV", f"Failed to read file:\n{e}")
        return

    if not rows:
        QMessageBox.information(self, "Load tops CSV", "No data rows found in CSV.")
        return

    # ---- index wells by name ----
    if not hasattr(self, "all_wells") or not self.all_wells:
        QMessageBox.warning(
            self,
            "Load tops CSV",
            "No wells in project. Please create/import wells before loading tops."
        )
        return

    wells_by_name = {}
    for w in self.all_wells:
        nm = w.get("name")
        if nm:
            wells_by_name[nm] = w

    # ---- ensure we have a stratigraphy dict ----
    strat = getattr(self, "stratigraphy", None)
    if strat is None or not isinstance(strat, dict):
        strat = OrderedDict()
    else:
        # preserve existing order
        strat = OrderedDict(strat)

    unknown_wells = set()
    skipped_rows = 0
    added_tops = 0
    updated_tops = 0

    for row in rows:
        well_name = (row.get("Well_name") or "").strip()
        md_str = (row.get("MD") or "").strip()
        horizon = (row.get("Horizon") or "").strip()
        name_col = (row.get("Name") or "").strip()
        type_col = (row.get("Type") or "").strip()

        if not well_name or not md_str:
            skipped_rows += 1
            continue

        # parse depth
        try:
            depth = float(md_str.replace(",", "."))  # comma or dot decimals
        except ValueError:
            skipped_rows += 1
            continue

        # find well
        well = wells_by_name.get(well_name)
        if well is None:
            unknown_wells.add(well_name)
            skipped_rows += 1
            continue

        # determine top name + role
        # For Faults -> name comes from Name or Horizon
        # For others -> name from Horizon or Name
        ttype = type_col.strip()
        if ttype == "Fault":
            top_name = name_col or horizon
            role = "fault"
        else:
            top_name = horizon or name_col
            role = "stratigraphy"

        if not top_name:
            # can't use an unnamed row
            skipped_rows += 1
            continue

        # ---- update stratigraphy meta ----
        meta = strat.get(top_name, {})
        if not isinstance(meta, dict):
            meta = {}

        # keep existing fields, just ensure role exists / updated
        meta.setdefault("level", "")  # you can refine this later
        meta.setdefault("color", "#000000")
        meta.setdefault("hatch", "-")
        # if no role defined yet, set it; if already set, we do NOT overwrite
        meta.setdefault("role", role)

        strat[top_name] = meta

        # ---- update well tops ----
        tops = well.setdefault("tops", {})
        old_val = tops.get(top_name)

        if isinstance(old_val, dict):
            old_val["depth"] = depth
            tops[top_name] = old_val
            updated_tops += 1
        elif old_val is not None:
            # old was a bare number
            tops[top_name] = {"depth": depth}
            updated_tops += 1
        else:
            tops[top_name] = {"depth": depth}
            added_tops += 1

    # store stratigraphy back
    self.stratigraphy = strat

    # ---- update panel ----
    if hasattr(self, "panel"):
        self.panel.wells = self.all_wells
        self.panel.stratigraphy = self.stratigraphy
        # keep zoom/flatten; if you want to reset, uncomment:
        # self.panel.current_depth_window = None
        # self.panel._flatten_depths = None
        self.panel.draw_panel()

    # ---- refresh trees ----
    if hasattr(self, "_populate_well_tree"):
        self._populate_well_tree()
    if hasattr(self, "_populate_top_tree"):
        self._populate_top_tree()

    # ---- summary message ----
    msg = [
        f"Added tops:   {added_tops}",
        f"Updated tops: {updated_tops}",
        f"Skipped rows: {skipped_rows}",
    ]
    if unknown_wells:
        msg.append(
            "\nUnknown wells encountered (not in project):\n  "
            + ", ".join(sorted(unknown_wells))
        )

    QMessageBox.information(self, "Load tops CSV", "\n".join(msg))


def _file_export_discrete_logs_csv(self):
    path, _ = QFileDialog.getSaveFileName(
        self,
        "Export Discrete Logs",
        "",
        "CSV files (*.csv);;All files (*.*)"
    )
    if not path:
        return

    # Call your actual export function
    export_discrete_logs_to_csv(self, path)

    self._file_load_tops_from_csv(path)


def _file_import_discrete_logs_csv(self):
    path, _ = QFileDialog.getOpenFileName(
        self,
        "Import discrete logs from CSV",
        "",
        "CSV files (*.csv);;All files (*.*)"
    )
    if not path:
        return

    import_discrete_logs_from_csv(self, path)


def load_project_from_json(path):
    path = Path(path)

    if path.suffix == ".pwj":
        #with path.open("r", encoding="utf-8") as f:
        data_cfg = _load_from_pwj(path)
        data_path = data_cfg["pwj_metadata"]["data_path"]
        data_path = Path(data_path)
    else:
        data_path = path

    # the output from _load_from_pws is a dict with a "data_path" key
    # data["_pws"] = {
    #     "path": pws_path,
    #     "project_name": shell.get("project_name"),
    #     "project_file_version": ver,
    #     "data_path": data_path,
    # }

    with data_path.open("r", encoding="utf-8") as f:
        data = json.load(f)


    wells = data.get("wells", [])
    tracks = data.get("tracks", [])
    stratigraphy = data.get("stratigraphy", [])
    window_dict = data.get("window_dict", {})
    metadata = data.get("metadata", {})
    ui_layout = data.get("ui_layout", {})

    return window_dict, wells, tracks, stratigraphy, ui_layout, metadata

def load_project_from_json_old(path):
    """Load a project from JSON file and return (wells, tracks, stratigraphy, metadata)."""
    path = Path(path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    wells = data.get("wells", [])
    tracks = data.get("tracks", [])
    stratigraphy = data.get("stratigraphy", [])
    window_dict = data.get("window_dict", {})
    metadata = data.get("metadata", {})
    ui_layout = data.get("ui_layout", {})

    return window_dict, wells, tracks, stratigraphy, ui_layout, metadata

def export_project_to_json(path, wells, tracks, stratigraphy=None, window_dict=None, ui_layout = None, extra_metadata=None):
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
    if window_dict:
        project["window_dict"] = window_dict
    if ui_layout is not None:
        project["ui_layout"] = ui_layout

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

def load_las_as_logs(path):
    """
    Read a LAS file and return:
      - well_info: dict with basic info (name, uwi, x, y, etc.)
      - logs: dict {mnemonic: {"depth": np.array, "data": np.array}}
    """
    las = lasio.read(path)

    # ---- depth vector ----
    # Prefer LAS index if it's depth, else look for DEPT/DEPTH
    if las.index is not None:
        depth = np.array(las.index, dtype=float)
    else:
        if "DEPT" in las.curves_dict:
            depth = np.array(las["DEPT"].data, dtype=float)
        elif "DEPTH" in las.curves_dict:
            depth = np.array(las["DEPTH"].data, dtype=float)
        else:
            raise ValueError("No DEPT/DEPTH curve found in LAS file.")

    # ---- basic well header info (best effort) ----
    well_section = las.well

    def wval(mnemonic, default=""):
        if mnemonic in well_section:
            v = well_section[mnemonic].value
            return str(v).strip() if v is not None else default
        return default

    name = wval("WELL", "")
    uwi = wval("UWI", "")
    x = wval("X", "")
    y = wval("Y", "")
    kb = wval("KB", "")

    try:
        x = float(x) if x not in ("", "None") else None
    except ValueError:
        x = None
    try:
        y = float(y) if y not in ("", "None") else None
    except ValueError:
        y = None

    # crude reference_depth and total_depth guess
    depth_min = float(np.nanmin(depth))
    depth_max = float(np.nanmax(depth))
    total_depth = depth_max - depth_min if depth_max > depth_min else 0.0
    reference_depth = depth_min

    well_info = {
        "name": name or uwi or "LAS_well",
        "uwi": uwi,
        "x": x,
        "y": y,
        "reference_type": kb or "KB",
        "reference_depth": reference_depth,
        "total_depth": total_depth,
    }

    # ---- collect logs (skip depth curves) ----
    logs = {}
    for curve in las.curves:
        mnem = curve.mnemonic.strip()
        umnem = mnem.upper()
        if umnem in ("DEPT", "DEPTH"):
            continue
        data = np.array(curve.data, dtype=float)
        logs[mnem] = {
            "depth": depth.copy(),
            "data": data,
        }

    if not logs:
        raise ValueError("No log curves found in LAS file (besides depth).")

    return well_info, logs

def export_discrete_logs_to_csv(self, path: str):
    """
    Export all discrete well logs (new format) to a CSV file.

    Input format per discrete log:
        {
            "depth":  [...],
            "values": [...],   # -999 = no value below that depth
        }

    Output columns:
        Well, Log, TopDepth, BottomDepth, Value
    """
    if not getattr(self, "all_wells", None):
        QMessageBox.information(self, "Export discrete logs", "No wells in project.")
        return

    rows = []
    MISSING = -999

    for well in self.all_wells:
        well_name = well.get("name", "UNKNOWN_WELL")
        disc_logs = well.get("discrete_logs", {}) or {}
        ref_depth = well.get("reference_depth", 0.0)
        well_td   = ref_depth + float(well.get("total_depth", 0.0))

        for log_name, disc_def in disc_logs.items():
            depths = np.array(disc_def.get("depth", []), dtype=float)
            values = np.array(disc_def.get("values", []), dtype=object)

            if depths.size == 0 or values.size == 0:
                continue

            # sort
            order = np.argsort(depths)
            depths = depths[order]
            values = values[order]

            # intervals between depth[i] and depth[i+1]
            for i in range(len(depths) - 1):
                top_d = float(depths[i])
                bot_d = float(depths[i + 1])
                val   = values[i]

                if val == MISSING:
                    continue

                rows.append({
                    "Well": well_name,
                    "Log": log_name,
                    "TopDepth": top_d,
                    "BottomDepth": bot_d,
                    "Value": val,
                })

            # last sample → extend to TD if not missing
            last_val = values[-1]
            if last_val != MISSING:
                top_d = float(depths[-1])
                bot_d = float(well_td)
                rows.append({
                    "Well": well_name,
                    "Log": log_name,
                    "TopDepth": top_d,
                    "BottomDepth": bot_d,
                    "Value": last_val,
                })

    if not rows:
        QMessageBox.information(
            self,
            "Export discrete logs",
            "No discrete logs found in the project."
        )
        return

    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["Well", "Log", "TopDepth", "BottomDepth", "Value"]
            )
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
    except Exception as e:
        QMessageBox.critical(
            self,
            "Export discrete logs",
            f"Failed to write CSV file:\n{e}"
        )
        return

    QMessageBox.information(
        self,
        "Export discrete logs",
        f"Exported {len(rows)} intervals to:\n{path}"
    )

def import_discrete_logs_from_csv(self, path: str):
    """
    Import discrete well logs from a CSV file in interval format:

        Well,Log,TopDepth,BottomDepth,Value

    and convert to internal format per (well, log):

        discrete_logs[log_name] = {
            "depth":  [top1, top2, ...],
            "values": [val1, val2, ...]   # string values; use '-999' as missing
        }

    Notes:
      - Requires wells with matching names already in self.all_wells.
      - For each (well, log), the imported data replaces any existing discrete log.
      - 'Value' is stored as string as-is; if you want a special missing code,
        use e.g. '-999' or an empty field in the CSV.
    """
    if not getattr(self, "all_wells", None):
        QMessageBox.information(self, "Import discrete logs", "No wells in project.")
        return

    # ---- read CSV ----
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        QMessageBox.critical(self, "Import discrete logs", f"Failed to read file:\n{e}")
        return

    if not rows:
        QMessageBox.information(self, "Import discrete logs", "No data rows found in CSV.")
        return

    # ---- group rows by (well_name, log_name) ----
    grouped = defaultdict(list)
    skipped = 0
    for r in rows:
        well_name = (r.get("Well") or "").strip()
        log_name  = (r.get("Log") or "").strip()
        top_s     = (r.get("TopDepth") or "").strip()
        val_raw   = r.get("Value", "")

        if not well_name or not log_name or not top_s:
            skipped += 1
            continue

        try:
            top_d = float(top_s.replace(",", "."))
        except ValueError:
            skipped += 1
            continue

        # Store value as string (we don’t force numeric)
        val = str(val_raw).strip()

        grouped[(well_name, log_name)].append((top_d, val))

    if not grouped:
        QMessageBox.information(
            self,
            "Import discrete logs",
            "No valid (Well, Log, TopDepth) rows found in CSV."
        )
        return

    # ---- map wells by name ----
    wells_by_name = {}
    for w in self.all_wells:
        nm = w.get("name")
        if nm:
            wells_by_name[nm] = w

    unknown_wells = set()
    imported_pairs = 0

    for (well_name, log_name), samples in grouped.items():
        well = wells_by_name.get(well_name)
        if well is None:
            unknown_wells.add(well_name)
            continue

        if not samples:
            continue

        # sort by depth
        samples.sort(key=lambda t: t[0])
        depths = [d for (d, v) in samples]
        values = [v for (d, v) in samples]

        disc_logs = well.setdefault("discrete_logs", {})
        disc_logs[log_name] = {
            "depth": depths,
            "values": values,
        }
        imported_pairs += 1

    # ---- update panel ----
    if hasattr(self, "panel"):
        self.panel.wells = self.all_wells
        # you can keep current zoom/flatten, or reset if you like:
        # self.panel._current_depth_window = None
        # self.panel._flatten_depths = None
        self.panel.draw_panel()

    # ---- refresh trees ----
    if hasattr(self, "_populate_log_tree"):
        self._populate_log_tree()
    if hasattr(self, "_populate_well_tree"):
        self._populate_well_tree()

    # ---- summary message ----
    msg_lines = [
        f"Imported discrete logs for {imported_pairs} (well, log) pairs.",
        f"Skipped rows: {skipped}",
    ]
    if unknown_wells:
        msg_lines.append(
            "\nUnknown wells (not found in project):\n  " +
            ", ".join(sorted(unknown_wells))
        )

    QMessageBox.information(
        self,
        "Import discrete logs",
        "\n".join(msg_lines)
    )

class LoadCoreBitmapDialog(QDialog):
    """
    Load an image (BMP/PNG/JPG) and assign it as a core bitmap to a well.

    Returns dict:
      {
        "well_name": str,
        "key": str,
        "path": str,
        "top_depth": float,
        "base_depth": float,
        "label": str,
        "flip_vertical": bool,
        "alpha": float,
        "interpolation": str,
        "cmap": str|None,
      }
    """

    def __init__(self, parent, well_names, default_well=None):
        super().__init__(parent)
        self.setWindowTitle("Load core bitmap")
        self.resize(520, 260)

        self._result = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # well selection
        self.cmb_well = QComboBox(self)
        self.cmb_well.addItems(list(well_names))
        if default_well and default_well in well_names:
            self.cmb_well.setCurrentText(default_well)
        form.addRow("Well:", self.cmb_well)

        # key/name
        self.ed_key = QLineEdit(self)
        self.ed_key.setText("core")
        form.addRow("Bitmap key:", self.ed_key)

        # file path + browse
        self.ed_path = QLineEdit(self)
        btn_browse = QPushButton("Browse…", self)
        row_path = QHBoxLayout()
        row_path.addWidget(self.ed_path)
        row_path.addWidget(btn_browse)
        form.addRow("Image file:", row_path)
        btn_browse.clicked.connect(self._browse)

        # depth interval
        self.spin_top = QDoubleSpinBox(self)
        self.spin_top.setRange(-1e9, 1e9)
        self.spin_top.setDecimals(3)
        self.spin_top.setSingleStep(1.0)
        form.addRow("Top depth:", self.spin_top)

        self.spin_base = QDoubleSpinBox(self)
        self.spin_base.setRange(-1e9, 1e9)
        self.spin_base.setDecimals(3)
        self.spin_base.setSingleStep(1.0)
        self.spin_base.setValue(1.0)
        form.addRow("Base depth:", self.spin_base)

        # label
        self.ed_label = QLineEdit(self)
        self.ed_label.setText("Core")
        form.addRow("Track label:", self.ed_label)

        # alpha
        self.spin_alpha = QDoubleSpinBox(self)
        self.spin_alpha.setRange(0.0, 1.0)
        self.spin_alpha.setDecimals(2)
        self.spin_alpha.setSingleStep(0.05)
        self.spin_alpha.setValue(1.0)
        form.addRow("Alpha:", self.spin_alpha)

        # interpolation
        self.cmb_interp = QComboBox(self)
        self.cmb_interp.addItems(["nearest", "bilinear", "bicubic"])
        self.cmb_interp.setCurrentText("nearest")
        form.addRow("Interpolation:", self.cmb_interp)

        # colormap (optional)
        self.cmb_cmap = QComboBox(self)
        self.cmb_cmap.addItems(["(none)", "gray"])
        self.cmb_cmap.setCurrentText("(none)")
        form.addRow("Colormap:", self.cmb_cmap)

        # flip
        self.chk_flip = QCheckBox("Flip vertically", self)
        self.chk_flip.setChecked(False)
        form.addRow("Orientation:", self.chk_flip)

        # OK/Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select image",
            "",
            "Images (*.bmp *.png *.jpg *.jpeg *.tif *.tiff);;All files (*.*)"
        )
        if path:
            self.ed_path.setText(path)

    def _on_accept(self):
        well_name = self.cmb_well.currentText().strip()
        key = self.ed_key.text().strip() or "core"
        path = self.ed_path.text().strip()

        if not well_name:
            QMessageBox.warning(self, "Load core bitmap", "Please choose a well.")
            return
        if not path:
            QMessageBox.warning(self, "Load core bitmap", "Please choose an image file.")
            return

        top_d = float(self.spin_top.value())
        base_d = float(self.spin_base.value())
        if abs(base_d - top_d) < 1e-9:
            QMessageBox.warning(self, "Load core bitmap", "Top and Base depth must differ.")
            return

        label = self.ed_label.text().strip() or "Core"
        alpha = float(self.spin_alpha.value())
        interpolation = self.cmb_interp.currentText().strip()
        cmap_txt = self.cmb_cmap.currentText().strip()
        cmap = None if cmap_txt == "(none)" else cmap_txt
        flip = bool(self.chk_flip.isChecked())

        self._result = {
            "well_name": well_name,
            "key": key,
            "path": path,
            "top_depth": top_d,
            "base_depth": base_d,
            "label": label,
            "alpha": alpha,
            "interpolation": interpolation,
            "cmap": cmap,
            "flip_vertical": flip,
        }
        self.accept()

    def result(self):
        return self._result


import os
import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox


SUPPORTED_PROJECT_FILE_VERSIONS = {1}


def load_project_from_json_new(self, path: str | None = None):
    """
    Load a project.

    Supported inputs:
      1) New format: <name>.pws (JSON shell) + <name>.data/data.json (project data)
      2) Legacy: a single JSON file containing {wells, tracks, stratigraphy, ...}

    After load:
      - updates self.all_wells / self.tracks / self.stratigraphy
      - rebuilds trees
      - refreshes all panels
    """
    if path is None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open project",
            "",
            "PyWellSection Project (*.pws);;Legacy JSON (*.json);;All files (*.*)"
        )
        if not path:
            return

    try:
        ext = os.path.splitext(path)[1].lower()

        if ext == ".pws":
            data = _load_from_pws(self, path)
        else:
            # legacy: direct json data
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

        # ---- normalize & compatibility ----
        wells = data.get("wells", []) or []
        tracks = data.get("tracks", []) or []
        stratigraphy = data.get("stratigraphy", {}) or {}

        _normalize_loaded_project(wells, tracks, stratigraphy)

        # ---- assign into app ----
        self.all_wells = wells
        self.tracks = tracks
        self.stratigraphy = stratigraphy

        # optional: restore dock layout if present
        ui_layout = data.get("ui_layout")
        if ui_layout and hasattr(self, "_dock_layout_restore"):
            # Ensure docks exist before restoring, if your workflow does that.
            # If you recreate docks dynamically, do it before calling restore.
            try:
                self._dock_layout_restore(ui_layout)
            except Exception:
                pass

        # ---- refresh UI ----
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()
        if hasattr(self, "_populate_track_tree"):
            self._populate_track_tree()
        if hasattr(self, "_populate_strat_tree"):
            self._populate_strat_tree()
        if hasattr(self, "_populate_window_tree"):
            self._populate_window_tree()

        if hasattr(self, "_refresh_all_panels"):
            self._refresh_all_panels()
        else:
            # minimal fallback
            if hasattr(self, "panel") and self.panel:
                self.panel.wells = self.all_wells
                self.panel.tracks = self.tracks
                self.panel.stratigraphy = self.stratigraphy
                self.panel.draw_panel()

        # remember last opened path
        self._last_project_path = path

    except UnicodeDecodeError:
        QMessageBox.critical(
            self, "Load error",
            "Failed to open file due to text encoding.\n"
            "If this is a legacy JSON, ensure it is UTF-8 encoded."
        )
    except Exception as e:
        QMessageBox.critical(self, "Load error", f"Failed to load project:\n{e}")


def _load_from_pwj(pwj_path = None):
    """
    Load project using the new .pws shell format.
    Returns the data dict loaded from data.json (plus any shell metadata you want to keep).
    """

    print (pwj_path)

    with open(pwj_path, "r", encoding="utf-8") as f:
        shell = json.load(f)

    ver = shell.get("project_file_version", None)
    if ver not in SUPPORTED_PROJECT_FILE_VERSIONS:
        raise ValueError(f"Unsupported project_file_version: {ver}")

    base_dir = os.path.dirname(os.path.abspath(pwj_path))
    data_info = shell.get("data", {}) or {}
    data_dir = data_info.get("directory")
    data_file = data_info.get("file", "data.json")

    if not data_dir:
        raise ValueError("Invalid .pws: missing data.directory")

    data_path = os.path.join(base_dir, data_dir, data_file)
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Project data file not found: {data_path}")

#    with open(data_path, "r", encoding="utf-8") as f:
#        data = json.load(f)

    data = {"pwj_metadata": {
        "path": pwj_path,
        "project_name": shell.get("project_name"),
        "project_file_version": ver,
        "data_path": data_path,
    }}

    # optionally keep shell metadata
    return data


def _normalize_loaded_project(wells: list, tracks: list, stratigraphy: dict):
    """
    Compatibility & safety normalization:
      - ensure dict structures exist
      - add missing top roles (default: stratigraphy)
      - ensure wells have expected keys
    """
    for w in wells:
        w.setdefault("logs", {})
        w.setdefault("discrete_logs", {})
        w.setdefault("bitmaps", {})
        w.setdefault("tops", {})

        # ensure core well keys exist (you added these earlier)
        w.setdefault("reference_depth", 0.0)
        w.setdefault("total_depth", 0.0)
        w.setdefault("x", None)
        w.setdefault("y", None)
        w.setdefault("reference_type", w.get("reference_type", "KB"))

        # normalize tops roles
        tops = w.get("tops") or {}
        for top_name, top_val in list(tops.items()):
            if isinstance(top_val, dict):
                # default role if missing
                top_val.setdefault("role", "stratigraphy")
                # standardize depth field if needed
                if "depth" not in top_val and "MD" in top_val:
                    top_val["depth"] = top_val["MD"]
            else:
                # legacy numeric depth -> convert to dict with role
                try:
                    tops[top_name] = {"depth": float(top_val), "role": "stratigraphy"}
                except Exception:
                    pass

    # Tracks: ensure each has a name and logs list
    for t in tracks:
        t.setdefault("name", "Track")
        t.setdefault("logs", [])

        # normalize bitmap track config
        if "bitmap" in t and isinstance(t["bitmap"], dict):
            t["bitmap"].setdefault("key", "core")
            t["bitmap"].setdefault("label", "Bitmap")
            t["bitmap"].setdefault("alpha", 1.0)
            t["bitmap"].setdefault("interpolation", "nearest")
            t["bitmap"].setdefault("cmap", None)
            t["bitmap"].setdefault("flip_vertical", False)

    # Stratigraphy is a dict (as you noted); no enforced schema here.
    if stratigraphy is None:
        stratigraphy = {}