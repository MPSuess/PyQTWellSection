
import json
from pathlib import Path
import re
import lasio
import numpy as np
import csv

from collections import defaultdict

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QComboBox, QLineEdit, QPushButton, QFileDialog,
    QDoubleSpinBox, QCheckBox, QDialogButtonBox, QMessageBox, QLabel
)

from typing import Dict, Any, List, Tuple, Optional

import openpyxl

from pywellsection.dialogs import ImportTopsAssignWellDialog


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
from PySide6.QtWidgets import QFileDialog, QMessageBox


SUPPORTED_PROJECT_FILE_VERSIONS = {1,2}


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

# ============================================================
# 1) Role inference from Hauptformation (full) and abbreviation
# ============================================================

def infer_role_from_hauptformation(full_name: str, abbr: str) -> str:
    """
    Rules requested:
      - "Lücke" or "L*"  => role="other"
      - "Störung" or "*ST" => role="fault"
      - "Transgression" or "*TRSGR" => role="other"
      - otherwise => role="stratigraphy"
    """
    fn = (full_name or "").strip().lower()
    ab = (abbr or "").strip().upper()

    # Missing section
    if "lücke" in fn:
        return "other"
    if ab.startswith("L*") or ab.startswith("*L") or re.match(r"^\*?L\*$", ab):
        return "other"

    # Fault
    if "störung" in fn:
        return "fault"
    if ab.startswith("*ST") or re.match(r"^\*?ST\b", ab):
        return "fault"

    # Transgression
    if "transgression" in fn:
        return "other"
    if ab.startswith("*TRSGR") or "TRSGR" in ab:
        return "other"

    return "stratigraphy"

def default_level_for_role(role: str) -> str:
    if role == "fault":
        return "fault"
    if role == "other":
        return "other"
    return "formation"

# ============================================================
# 2) XLSX parser (UPDATED)
#    - Reads from sheet with the header (RWE_Dea-DEA-WinDEA)
#    - Uses Column E (2nd "Hauptformation") as top KEY
#    - Adds stratigraphy updates with "Full Name"
# ============================================================

def parse_geolprofile_xlsx_to_tops_v2(
    xlsx_path: str,
    sheet_name: str,
) -> Tuple[List[Dict[str, Any]], float, Dict[str, Dict[str, Any]]]:
    """
    Returns:
      tops_list: [
          {"key": <abbr>, "full_name": <full>, "depth": <top_depth>, "role": <role>}, ...
      ]
      td: float
      strat_updates: { <abbr>: {"Full Name": <full>, "role": <role>, "level": <level>} , ... }

    Notes:
      - KEY is Column E (2nd 'Hauptformation', abbreviation).
      - If abbreviation is blank, falls back to a generated key:
          fault -> "*ST_<depth>"
          other -> "*OTHER_<depth>"
          else -> "<full>_<depth>"
      - "Endteufe" row is treated as TD only (not a top).
      - Top depth uses Toptiefe if present, else previous row base depth.
    """
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)

    ws = None

    if sheet_name not in wb.sheetnames:
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook")
    if sheet_name:
        ws = wb[sheet_name]
    else:
        # Pick the first non-empty sheet that contains "Profil_ID" header
        #ws = None
        for name in wb.sheetnames:
            cand = wb[name]
            first = next(cand.iter_rows(values_only=True), None)
            if first and "Profil_ID" in list(first):
                ws = cand
                break
    if ws is None:
        raise ValueError("No sheet with 'Profil_ID' header found.")

    rows = [r for r in ws.iter_rows(values_only=True)]
    if not rows or len(rows) < 2:
        return [], 0.0, {}

    header = list(rows[0])

    # indices
    idx_top = header.index("Toptiefe") if "Toptiefe" in header else 1
    idx_base = header.index("Basistiefe") if "Basistiefe" in header else 2

    hf_idxs = [i for i, h in enumerate(header) if h == "Hauptformation"]
    # Column D = first Hauptformation (full name)
    # Column E = second Hauptformation (abbrev) (requested)
    idx_full = hf_idxs[0] if len(hf_idxs) >= 1 else 3
    idx_abbr = hf_idxs[1] if len(hf_idxs) >= 2 else 4

    tops: List[Dict[str, Any]] = []
    strat_updates: Dict[str, Dict[str, Any]] = {}

    prev_base = 0.0
    td = 0.0

    for r in rows[1:]:
        if r is None:
            continue

        base_v = r[idx_base] if idx_base < len(r) else None
        if base_v is None or base_v == "":
            continue
        try:
            base_d = float(base_v)
        except Exception:
            continue

        td = max(td, base_d)

        top_v = r[idx_top] if idx_top < len(r) else None
        if top_v is None or top_v == "":
            top_d = prev_base
        else:
            try:
                top_d = float(top_v)
            except Exception:
                top_d = prev_base

        full = r[idx_full] if idx_full < len(r) else ""
        abbr = r[idx_abbr] if idx_abbr < len(r) else ""

        full_name = (str(full).strip() if full not in (None, "") else "")
        abbr_key = (str(abbr).strip() if abbr not in (None, "") else "")

        # "Endteufe" row: TD only
        if full_name.lower() == "endteufe":
            prev_base = base_d
            continue

        role = infer_role_from_hauptformation(full_name, abbr_key)
        level = default_level_for_role(role)

        # Required: Use abbreviation as top key
        key = abbr_key

        # If abbreviation is missing: generate deterministic key
        if not key:
            if role == "fault":
                key = f"*ST_{top_d:.2f}"
            elif role == "other":
                key = f"*OTHER_{top_d:.2f}"
            else:
                # keep a readable fallback
                fn = full_name if full_name else "TOP"
                key = f"{fn}_{top_d:.2f}"

        # Track stratigraphy update:
        # - store "Full Name" (requested exact field)
        # - store role/level
        if key not in strat_updates:
            strat_updates[key] = {"Full Name": full_name, "role": role, "level": level, "color": random_strat_color(),
                                  "hatch": "-"}
        else:
            # keep first full name if already set; but fill if missing
            if not strat_updates[key].get("Full Name"):
                strat_updates[key]["Full Name"] = full_name
            strat_updates[key].setdefault("role", role)
            strat_updates[key].setdefault("level", level)
            strat_updates[key].setdefault("color", random_strat_color())
            strat_updates[key].setdefault("hatch", "-")

        tops.append({"key": key, "full_name": full_name, "depth": top_d, "role": role, "color": random_strat_color(),
                     "hatch": "-"})

        prev_base = base_d

    # Deduplicate tops by key: keep shallowest occurrence
    dedup: Dict[str, Dict[str, Any]] = {}
    for t in tops:
        k = t["key"]
        if k not in dedup or float(t["depth"]) < float(dedup[k]["depth"]):
            dedup[k] = t
    tops = list(dedup.values())
    tops.sort(key=lambda x: float(x["depth"]))

    return tops, float(td), strat_updates

import random

def random_strat_color(seed=None):
    """
    Generate a random, visually pleasant color for stratigraphic units.

    Parameters
    ----------
    seed : Optional[int]
        If provided, color generation becomes reproducible.

    Returns
    -------
    str
        Hex color string, e.g. '#7fbf7f'
    """
    if seed is not None:
        random.seed(seed)

    # avoid extremes (too dark / too bright)
    r = random.randint(60, 220)
    g = random.randint(60, 220)
    b = random.randint(60, 220)

    return f"#{r:02x}{g:02x}{b:02x}"
# ============================================================
# 4) Import routine (UPDATED)
#    - applies tops using abbreviation keys
#    - updates project.stratigraphy with "Full Name" field
# ============================================================

def import_schichtenverzeichnisv1(parent,project, xlsx_path: str,): # PWSProject or app container with .all_wells/.all_stratigraphy
    if not os.path.exists(xlsx_path):
        QMessageBox.warning(parent, "Import", f"File not found:\n{xlsx_path}")
        return False

    try:
        parsed_tops, td, strat_updates = parse_geolprofile_xlsx_to_tops_v2(xlsx_path)
    except Exception as e:
        QMessageBox.critical(parent, "Import", f"Failed to parse file:\n{e}")
        return False

    if not parsed_tops:
        QMessageBox.information(parent, "Import", "No tops found in this file.")
        return False

    wells = getattr(project, "all_wells", None)
    if wells is None:
        wells = getattr(project, "wells", []) or []

    existing_names = [w.get("name", "") for w in wells if w.get("name")]
    default_new_name = os.path.splitext(os.path.basename(xlsx_path))[0]

    dlg = ImportTopsAssignWellDialog(
        parent,
        existing_well_names=existing_names,
        default_new_name=default_new_name,
        td=td,
        n_tops=len(parsed_tops),
    )
    if dlg.exec_() != QDialog.Accepted:
        return False

    sel = dlg.result_selection()

    # Resolve target well
    target_well = None
    if sel["create_new"]:
        new_name = sel["new_name"]
        if not new_name:
            QMessageBox.warning(parent, "Import", "Please provide a name for the new well.")
            return False

        target_well = {
            "name": new_name,
            "UWI": "",
            "x": None,
            "y": None,
            "reference_type": "KB",
            "reference_depth": 0.0,
            "total_depth": float(sel["td"]) if sel["set_td"] else 0.0,
            "logs": {},
            "discrete_logs": {},
            "tops": {},
            "facies_intervals": [],
            "bitmaps": {},
        }
        wells.append(target_well)
    else:
        nm = sel["existing_name"]
        for w in wells:
            if w.get("name") == nm:
                target_well = w
                break
        if target_well is None:
            QMessageBox.warning(parent, "Import", "Selected well not found.")
            return False

        if sel["set_td"]:
            ref = float(target_well.get("reference_depth", 0.0) or 0.0)
            target_well["total_depth"] = max(float(target_well.get("total_depth", 0.0) or 0.0), float(td - ref))

    # Update project stratigraphy with "Full Name" and roles
    strat = getattr(project, "all_stratigraphy", None)
    if strat is None:
        strat = getattr(project, "stratigraphy", None)
        if strat is None:
            strat = {}
            # attach if possible
            if hasattr(project, "all_stratigraphy"):
                project.all_stratigraphy = strat
            elif hasattr(project, "stratigraphy"):
                project.stratigraphy = strat

    # strat is expected to be dict
    if not isinstance(strat, dict):
        strat = {}

    # merge updates (do not overwrite existing styling)
    for key, upd in strat_updates.items():
        if key not in strat:
            strat[key] = dict(upd)
        else:
            # ensure Full Name exists (requested)
            if "Full Name" not in strat[key] or not strat[key].get("Full Name"):
                strat[key]["Full Name"] = upd.get("Full Name", "")
            strat[key].setdefault("role", upd.get("role", "stratigraphy"))
            strat[key].setdefault("level", upd.get("level", "formation"))

    # Apply tops to the well using abbreviation keys
    tops_dict = target_well.setdefault("tops", {})

    added = 0
    updated = 0
    for t in parsed_tops:
        key = t["key"]
        depth = float(t["depth"])

        meta = strat.get(key, {}) if isinstance(strat, dict) else {}
        role = meta.get("role", t.get("role", "stratigraphy"))
        level = meta.get("level", default_level_for_role(role))

        if key in tops_dict and isinstance(tops_dict[key], dict):
            tops_dict[key]["depth"] = depth
            tops_dict[key].setdefault("role", role)
            tops_dict[key].setdefault("level", level)
            updated += 1
        else:
            tops_dict[key] = {"depth": depth, "role": role, "level": level}
            # if you keep color/hatch in stratigraphy, you can copy defaults once:
            if isinstance(meta, dict):
                if "color" in meta:
                    tops_dict[key].setdefault("color", meta["color"])
                if "hatch" in meta:
                    tops_dict[key].setdefault("hatch", meta["hatch"])
            added += 1

    QMessageBox.information(
        parent,
        "Import",
        f"Imported tops into '{target_well.get('name','')}'.\n\nAdded: {added}\nUpdated: {updated}\n"
        f"Stratigraphy updated/extended: {len(strat_updates)} keys\n\n"
        "Note: Top keys use the abbreviation (2nd Hauptformation / Column E)."
    )
    return True

def import_schichtenverzeichnis(parent, project, xlsx_path):
    if not os.path.exists(xlsx_path):
        QMessageBox.warning(parent, "Import", f"File not found:\n{xlsx_path}")
        return False

    # --- Load workbook first ---
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    sheet_names = wb.sheetnames

    if not sheet_names:
        QMessageBox.warning(parent, "Import", "No worksheets found in file.")
        return False

    wells = project.all_wells
    existing_names = [w["name"] for w in wells if w.get("name")]

    dlg = ImportTopsAssignWellDialog(
        parent,
        sheet_names=sheet_names,
        existing_well_names=existing_names,
        default_new_name=os.path.splitext(os.path.basename(xlsx_path))[0],
    )

    # --- Live preview update when sheet changes ---
    def update_preview():
        try:
            tops, td, _ = parse_geolprofile_xlsx_to_tops_v2(
                xlsx_path,
                dlg.selected_sheet(),
            )
            dlg.set_preview(len(tops), td)
        except Exception as e:
            dlg.lbl_preview.setText(f"Preview error: {e}")

    dlg.cmb_sheet.currentIndexChanged.connect(update_preview)
    update_preview()

    if dlg.exec_() != QDialog.Accepted:
        return False

    sel = dlg.result_selection()

    # --- Parse selected sheet ---
    tops, td, strat_updates = parse_geolprofile_xlsx_to_tops_v2(
        xlsx_path,
        sel["sheet"],
    )

    if not tops:
        QMessageBox.information(parent, "Import", "No tops found in selected sheet.")
        return False

    # --- Resolve well (unchanged logic) ---
    if sel["create_new"]:
        target_well = {
            "name": sel["new_name"],
            "reference_type": "KB",
            "reference_depth": 0.0,
            "total_depth": td if sel["set_td"] else 0.0,
            "logs": {},
            "discrete_logs": {},
            "tops": {},
            "facies_intervals": [],
            "bitmaps": {},
        }
        wells.append(target_well)
    else:
        target_well = next(
            (w for w in wells if w.get("name") == sel["existing_name"]), None
        )
        if target_well is None:
            QMessageBox.warning(parent, "Import", "Selected well not found.")
            return False

        if sel["set_td"]:
            ref = float(target_well.get("reference_depth", 0.0))
            target_well["total_depth"] = max(
                float(target_well.get("total_depth", 0.0)),
                td - ref,
            )

    # --- Apply stratigraphy + tops (unchanged) ---
    strat = project.all_stratigraphy
    for key, meta in strat_updates.items():
        strat.setdefault(key, {}).update(meta)

    tops_dict = target_well.setdefault("tops", {})
    for t in tops:
        tops_dict[t["key"]] = {
            "depth": t["depth"],
            "role": t["role"],
            "level": strat.get(t["key"], {}).get("level", "formation"),
        }

    QMessageBox.information(
        parent,
        "Import",
        f"Imported {len(tops)} tops from sheet '{sel['sheet']}' into '{target_well['name']}'."
    )

    return True

def read_sv_tops_file(path: str) -> List[Dict[str, Any]]:
    """
    Returns list of records:
      {"well": str, "md": float, "name": str, "type": str}
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    # sniff delimiter
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        reader = csv.DictReader(f, dialect=dialect)

        out = []
        for row in reader:
            # normalize keys
            keys = {k.strip(): k for k in row.keys() if k}

            def g(*cands):
                for c in cands:
                    for kk, orig in keys.items():
                        if kk.lower() == c.lower():
                            return row.get(orig)
                return None

            well = (g("Well_name", "Well", "WELL") or "").strip()
            name = (g("Horizon", "Name", "Unit", "Strat", "STRAT") or "").strip()
            typ = (g("Type", "TYPE") or "").strip()
            md_s = g("MD", "Depth", "DEPTH", "TVD")  # treat as MD-like number for now

            try:
                md = float(md_s) if md_s not in (None, "") else None
            except Exception:
                md = None

            if not name:
                continue

            out.append({"well": well, "md": md, "name": name, "type": typ})

    return out



def import_sv_tops_using_beee(
    parent,
    project,
    sv_path: str,
    beee_strat_roots: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Workflow:
      - parse sv_tops (Base picks)
      - map base -> top using BEEE hierarchy
      - show dialog for unresolved
      - return list of TOP picks:
          {"well":..., "md":..., "name":..., "role":..., "type":"Top"}
    """
    sv_rows = read_sv_tops_file(sv_path)
    idx = flatten_strat_tree(beee_strat_roots)

    mapped, unresolved = map_sv_bases_to_tops(sv_rows, idx, only_base_rows=True)

    # resolve unresolved
    if unresolved:
        dlg = ResolveUnmatchedBasesDialog(parent, unresolved, idx)
        if dlg.exec_() != QDialog.Accepted:
            return []

        manual = dlg.results()
        for m in manual:
            # If user picked a BEEE base unit, convert via hierarchy
            if m["chosen_beee_base_key"]:
                eq_top = equivalent_top_for_base(idx, m["chosen_beee_base_key"])
                if eq_top:
                    mapped.append({
                        "well": m["well"],
                        "md": m["md"],
                        "sv_name": m["sv_name"],
                        "beee_base_key": m["chosen_beee_base_key"],
                        "mapped_top": eq_top,
                        "role": "stratigraphy",
                        "type": "Top",
                    })
                    continue

            # Otherwise use custom top name, with chosen role
            if m["custom_top"]:
                mapped.append({
                    "well": m["well"],
                    "md": m["md"],
                    "sv_name": m["sv_name"],
                    "beee_base_key": None,
                    "mapped_top": m["custom_top"],
                    "role": m["role"] or "other",
                    "type": "Top",
                })

    # Ensure project stratigraphy contains custom tops (role != stratigraphy)
    strat = getattr(project, "all_stratigraphy", None)
    if strat is None:
        strat = {}
        project.all_stratigraphy = strat

    added_strat = 0
    for r in mapped:
        nm = r["mapped_top"]
        role = r.get("role", "stratigraphy")
        if nm and nm not in strat:
            # Only auto-create for non-stratigraphy custom entries OR unknown names
            # (BEEE names likely already exist elsewhere, but harmless if added)
            strat[nm] = {
                "level": "fault" if role == "fault" else ("other" if role == "other" else "formation"),
                "role": role,
                "color": None,
                "hatch": None,
            }
            added_strat += 1

    # Final TOP picks list (name replaced)
    out = []
    for r in mapped:
        out.append({
            "well": r.get("well",""),
            "md": r.get("md", None),
            "name": r.get("mapped_top",""),
            "role": r.get("role","stratigraphy"),
            "type": "Top",
            "source": "sv_tops(Base→Top via BEEE)",
            "sv_base_name": r.get("sv_name",""),
        })

    QMessageBox.information(
        parent,
        "SV tops import",
        f"Imported {len(out)} TOP picks from sv_tops.\n"
        f"Unmatched base rows resolved: {len(unresolved)}\n"
        f"Stratigraphy entries added: {added_strat}"
    )
    return out