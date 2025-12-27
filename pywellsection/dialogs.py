import numpy as np
from PyQt5.QtWidgets import (
    QDoubleSpinBox, QPushButton,
    QDialog, QLineEdit, QDialogButtonBox,
    QDialog, QVBoxLayout, QFormLayout,
    QComboBox, QDialogButtonBox,
    QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QHBoxLayout,
    QColorDialog, QSpinBox, QCheckBox,
    QFileDialog
)
from collections import OrderedDict

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

import os


class EditFormationTopDialog(QDialog):
    def __init__(self, parent, well_name, formation_name,
                 current_depth, min_bound, max_bound):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Top: {formation_name} • {well_name}")
        self.resize(380, 160)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        def fmt(v):
            return "-∞" if not np.isfinite(v) else f"{v:.3f}"
        self.bounds = (min_bound, max_bound)
        self.lbl_bounds = QLabel(f"Bounds: {fmt(min_bound)} … {fmt(max_bound)}")
        form.addRow("Limits:", self.lbl_bounds)

        self.spin = QDoubleSpinBox(self)
        mn = min_bound if np.isfinite(min_bound) else -1e9
        mx = max_bound if np.isfinite(max_bound) else 1e9
        self.spin.setRange(mn, mx)
        self.spin.setDecimals(3)
        self.spin.setSingleStep(0.1)
        self.spin.setValue(float(current_depth))
        form.addRow("Depth:", self.spin)

        self.btn_pick = QPushButton("Pick on plot", self)
        layout.addWidget(self.btn_pick)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)   # important
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def set_depth(self, d: float):
        mn, mx = self.bounds
        if np.isfinite(mn):
            d = max(d, mn + 1e-6)
        if np.isfinite(mx):
            d = min(d, mx - 1e-6)
        self.spin.setValue(float(d))

    def value(self) -> float:
        return float(self.spin.value())

    def _dialog_accepted(self):
        """OK clicked on dialog: update top and redraw."""
        if self._active_top_dialog is None:
            print ("no more top dialog?")
            return

        tops = self.well["tops"]

        new_depth = self._active_top_dialog.value()
        self.top_depth = new_depth
        nearest_name=self._picked_formation

        old_val = tops[nearest_name]
        if isinstance(old_val, dict):
            updated_val = dict(old_val)
            updated_val["depth"] = new_depth
            self._active_top_dialog = None
        else:
            updated_val = new_depth

        tops[nearest_name] = updated_val

        self.top_depth = new_depth
        self._active_top_dialog = None
        self._active_pick_context = None
        self._clear_pick_line()
        self.draw_panel()

    def _dialog_rejected(self):
        """Cancel clicked: just clean up."""
        self._active_top_dialog = None
        self._active_pick_context = None
        self._clear_pick_line()
        # no change to self.top_depth


    def _get_stratigraphic_bounds(self, top_name: str):
        """
        Return (min_bound, max_bound) depth for a top so that moving it
        cannot violate the stratigraphic order defined in self.stratigraphy.

        - depths increase with depth (e.g. 1000 m -> 2000 m)
        - self.stratigraphy is ordered shallow -> deep
        """

        well = self.well
        tops = well["tops"]

        if top_name not in tops:
            return

        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        # Default: whole well interval
        min_bound = ref_depth
        max_bound = well_td

        strat = getattr(self, "stratigraphy", None)
        if not strat or top_name not in strat:
            return min_bound, max_bound

        tops = well.get("tops", {})
        idx_map = {key: i for i, key in enumerate(strat)}
        idx = idx_map.get(top_name)

        #idx = strat.index(top_name)

        # Find shallower neighbor (earlier in strat list that exists in this well)
        shallower_depth = None
        for j in range(idx - 1, -1, -1):
            name_j = list(idx_map)[j]
            if name_j in tops:
                val = tops[name_j]
                shallower_depth = float(val["depth"] if isinstance(val, dict) else val)
                break

        # Find deeper neighbor (later in strat list that exists in this well)
        deeper_depth = None
        for j in range(idx + 1, len(strat)):
            name_j = list(idx_map)[j]
            if name_j in tops:
                val = tops[name_j]
                deeper_depth = float(val["depth"] if isinstance(val, dict) else val)
                break

        eps = 1e-3  # small margin to avoid exact crossing

        # If we have a shallower neighbor, this sets the upper bound (shallower depth)
        if shallower_depth is not None:
            min_bound = max(min_bound, shallower_depth + eps)

        # If we have a deeper neighbor, this sets the lower bound (deeper depth)
        if deeper_depth is not None:
            max_bound = min(max_bound, deeper_depth - eps)

        # Ensure min_bound < max_bound (if strat is strange, just fall back)
        if not (min_bound < max_bound):
            min_bound, max_bound = ref_depth, well_td

        return min_bound, max_bound

class AddFormationTopDialog(QDialog):
    """
    Dialog to add a new formation top at a picked depth.
    Shows the depth and a drop-down of stratigraphic candidates.
    """
    def __init__(self, parent, well_name: str, depth: float, candidates: list[str]):
        super().__init__(parent)
        self.setWindowTitle(f"Add formation top • {well_name}")
        self.resize(380, 160)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # Depth label
        lbl_depth = QLabel(f"{depth:.3f}")
        form.addRow("Depth:", lbl_depth)

        # Drop-down with candidate units
        self.combo = QComboBox(self)
        self.combo.addItems(candidates)
        form.addRow("Unit:", self.combo)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def selected_unit(self) -> str:
        return self.combo.currentText()

class AddLogToTrackDialog(QDialog):
    """
    Simple dialog to choose a track and log mnemonic and optional label/color.
    """
    def __init__(self, parent, tracks, all_wells):
        super().__init__(parent)
        self.setWindowTitle("Add log to track")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # track combo
        self.cmb_track = QComboBox(self)
        for t in tracks:
            self.cmb_track.addItem(t.get("name", "Track"), userData=t)
        form.addRow("Track:", self.cmb_track)

        # collect all log mnemonics from wells
        log_names = set()
        for w in all_wells:
            for m in w.get("logs", {}).keys():
                log_names.add(m)
        self.cmb_log = QComboBox(self)
        for m in sorted(log_names):
            self.cmb_log.addItem(m)
        form.addRow("Log:", self.cmb_log)

        # optional label & color
        self.ed_label = QLineEdit(self)
        self.ed_color = QLineEdit("black", self)

        form.addRow("Label (optional):", self.ed_label)
        form.addRow("Color:", self.ed_color)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_values(self):
        track_name = self.cmb_track.currentText()
        log_name = self.cmb_log.currentText()
        label = self.ed_label.text().strip() or None
        color = self.ed_color.text().strip() or "black"
        return track_name, log_name, label, color

class AssignLasToWellDialog(QDialog):
    """
    Dialog to assign LAS logs to an existing well or create a new well.
    - wells: list of existing well dicts
    - las_well_info: dict from load_las_as_logs (name, uwi, etc.)
    """
    def __init__(self, parent, wells, las_well_info):
        super().__init__(parent)
        self.setWindowTitle("Assign LAS logs to well")

        self._wells = wells
        self._las_well_info = las_well_info

        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        # Combo: existing wells + "Create new well..."
        self.cmb_target = QComboBox(self)
        self.cmb_target.addItem("Create new well…", userData=None)
        for i, w in enumerate(wells):
            self.cmb_target.addItem(w.get("name", f"Well {i+1}"), userData=i)
        form.addRow("Assign to:", self.cmb_target)

        # LAS-derived defaults
        default_name = las_well_info.get("name", "")
        default_uwi = las_well_info.get("uwi", "")

        self.ed_name = QLineEdit(default_name, self)
        self.ed_uwi = QLineEdit(default_uwi, self)

        form.addRow("New well name:", self.ed_name)
        form.addRow("New well UWI:", self.ed_uwi)

        # Info label
        info_txt = (
            f"LAS well: {default_name or 'N/A'}  "
            f"(UWI: {default_uwi or 'N/A'})"
        )
        layout.addWidget(QLabel(info_txt, self))

        # Enable/disable name/uwi fields depending on selection
        self.cmb_target.currentIndexChanged.connect(self._update_fields_enabled)
        self._update_fields_enabled()

        # OK/Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _update_fields_enabled(self):
        """Enable ed_name/ed_uwi only when 'Create new well' is selected."""
        idx = self.cmb_target.currentIndex()
        is_new = (idx == 0)
        self.ed_name.setEnabled(is_new)
        self.ed_uwi.setEnabled(is_new)

    def result_assignment(self):
        """
        Returns (mode, index_or_None, new_well_name, new_well_uwi)

        mode: "existing" or "new"
        - if mode == "existing": index_or_None is well index in the wells list
        - if mode == "new":      index_or_None is None, and name/uwi are used
        """
        idx = self.cmb_target.currentIndex()
        user_data = self.cmb_target.itemData(idx)
        if user_data is None:
            # create new
            return (
                "new",
                None,
                self.ed_name.text().strip(),
                self.ed_uwi.text().strip(),
            )
        else:
            return (
                "existing",
                int(user_data),
                self.ed_name.text().strip(),
                self.ed_uwi.text().strip(),
            )

class NewTrackDialog(QDialog):
    def __init__(self, parent, suggested_name="Track"):
        super().__init__(parent)
        self.setWindowTitle("Add empty track")

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.ed_name = QLineEdit(suggested_name, self)
        form.addRow("Track name:", self.ed_name)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def track_name(self) -> str:
        return self.ed_name.text().strip()

class StratigraphyEditorDialog(QDialog):
    """
    Table dialog to edit/add stratigraphy for the project.

    Stratigraphy dict structure:
        {
          "Unit_A": {
              "level": "formation",
              "role":  "stratigraphy",   # NEW
              "color": "#ff0000",
              "hatch": "",
          },
          "Fault_1": {
              "level": "fault",
              "role":  "fault",
              "color": "#0000ff",
              "hatch": "//",
          },
          ...
        }
    """

    COL_NAME  = 0
    COL_LEVEL = 1
    COL_ROLE  = 2
    COL_COLOR = 3
    COL_HATCH = 4

    def __init__(self, parent, stratigraphy: dict | None):
        super().__init__(parent)
        self.setWindowTitle("Edit Stratigraphy")
        self.resize(700, 400)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit stratigraphic units (top = shallowest, bottom = deepest).\n"
            "Columns:\n"
            "  • Level – e.g. formation/member/fault/etc.\n"
            "  • Role  – e.g. stratigraphy/fault/other, used to distinguish surfaces.",
            self
        ))

        # Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Level", "Role", "Color", "Hatch"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Buttons: Add / Delete row
        btn_row_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add row", self)
        self.btn_del = QPushButton("Delete selected row(s)", self)
        btn_row_layout.addWidget(self.btn_add)
        btn_row_layout.addWidget(self.btn_del)
        btn_row_layout.addStretch(1)
        layout.addLayout(btn_row_layout)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._delete_selected_rows)

        # OK/Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._accepted_strat = None
        self._load_from_stratigraphy(stratigraphy or {})

    # ---------- populate / helpers ----------

    def _load_from_stratigraphy(self, stratigraphy: dict):
        """
        Fill table from existing stratigraphy dict, preserving order.
        """
        keys = list(stratigraphy.keys())
        self.table.setRowCount(len(keys))

        for row, name in enumerate(keys):
            meta  = stratigraphy.get(name, {}) or {}
            level = meta.get("level", "")
            role  = meta.get("role", "stratigraphy")  # default role
            color = meta.get("color", "")
            hatch = meta.get("hatch", "")

            self.table.setItem(row, self.COL_NAME,
                               QTableWidgetItem(str(name)))
            self.table.setItem(row, self.COL_LEVEL,
                               QTableWidgetItem(str(level)))
            self.table.setItem(row, self.COL_ROLE,
                               QTableWidgetItem(str(role)))
            self.table.setItem(row, self.COL_COLOR,
                               QTableWidgetItem(str(color)))
            self.table.setItem(row, self.COL_HATCH,
                               QTableWidgetItem(str(hatch)))

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # Everything starts blank; user fills Name, Level, Role, Color, Hatch

    def _delete_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _on_accept(self):
        """
        Validate and build new stratigraphy OrderedDict.
        Enforces:
          - Name not empty
          - Name unique
        """
        new_strat = OrderedDict()
        n_rows = self.table.rowCount()

        for row in range(n_rows):
            name_item = self.table.item(row, self.COL_NAME)
            if name_item is None:
                continue

            name = name_item.text().strip()
            if not name:
                # Check if the rest of row is empty; if not, complain
                row_items = [
                    self.table.item(row, c)
                    for c in (self.COL_LEVEL, self.COL_ROLE,
                              self.COL_COLOR, self.COL_HATCH)
                ]
                if not any(it and it.text().strip() for it in row_items):
                    # fully empty row => skip
                    continue
                else:
                    QMessageBox.warning(
                        self,
                        "Stratigraphy",
                        f"Row {row+1} has metadata but no Name. "
                        "Please fill Name or clear the row."
                    )
                    return

            if name in new_strat:
                QMessageBox.warning(
                    self,
                    "Stratigraphy",
                    f"Duplicate unit name '{name}' in row {row+1}. "
                    "Names must be unique."
                )
                return

            def _get(col):
                it = self.table.item(row, col)
                return it.text().strip() if it is not None else ""

            level = _get(self.COL_LEVEL)
            role  = _get(self.COL_ROLE) or "stratigraphy"  # default
            color = _get(self.COL_COLOR)
            hatch = _get(self.COL_HATCH)

            new_strat[name] = {
                "level": level,
                "role":  role,
                "color": color,
                "hatch": hatch,
            }

        self._accepted_strat = new_strat
        self.accept()

    def result_stratigraphy(self):
        """Return OrderedDict or None."""
        return self._accepted_strat

class LayoutSettingsDialog(QDialog):
    def __init__(self, parent, well_gap_factor: float, track_width: float):
        super().__init__(parent)
        self.setWindowTitle("Layout settings")
        self.resize(300, 150)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.spin_gap = QDoubleSpinBox(self)
        self.spin_gap.setRange(0.1, 20.0)
        self.spin_gap.setDecimals(2)
        self.spin_gap.setSingleStep(0.1)
        self.spin_gap.setValue(float(well_gap_factor))
        form.addRow("Gap between wells:", self.spin_gap)

        self.spin_track = QDoubleSpinBox(self)
        self.spin_track.setRange(0.1, 10.0)
        self.spin_track.setDecimals(2)
        self.spin_track.setSingleStep(0.1)
        self.spin_track.setValue(float(track_width))
        form.addRow("Track width:", self.spin_track)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def values(self):
        return float(self.spin_gap.value()), float(self.spin_track.value())

# class LogDisplaySettingsDialog(QDialog):
#     """
#     Dialog to edit display settings for a log mnemonic:
#       - color
#       - xscale: linear/log
#       - direction: normal/reverse
#       - xlim: min/max or blank for auto
#     """
#     def __init__(self, parent, log_name: str,
#                  color: str, xscale: str, direction: str, xlim):
#         super().__init__(parent)
#         self.setWindowTitle(f"Display settings – {log_name}")
#         self.resize(320, 200)
#
#         layout = QVBoxLayout(self)
#         form = QFormLayout()
#         layout.addLayout(form)
#
#         self.ed_color = QLineEdit(color or "", self)
#         form.addRow("Color:", self.ed_color)
#
#         self.cmb_xscale = QComboBox(self)
#         self.cmb_xscale.addItems(["linear", "log"])
#         idx = self.cmb_xscale.findText(xscale or "linear")
#         if idx < 0:
#             idx = 0
#         self.cmb_xscale.setCurrentIndex(idx)
#         form.addRow("X scale:", self.cmb_xscale)
#
#         self.cmb_dir = QComboBox(self)
#         self.cmb_dir.addItems(["normal", "reverse"])
#         idx = self.cmb_dir.findText(direction or "normal")
#         if idx < 0:
#             idx = 0
#         self.cmb_dir.setCurrentIndex(idx)
#         form.addRow("Direction:", self.cmb_dir)
#
#         # xlim: two line edits, blank = auto
#         xmin_txt = ""
#         xmax_txt = ""
#         if xlim is not None and len(xlim) == 2:
#             try:
#                 xmin_txt = str(xlim[0])
#                 xmax_txt = str(xlim[1])
#             except Exception:
#                 pass
#
#         self.ed_xmin = QLineEdit(xmin_txt, self)
#         self.ed_xmax = QLineEdit(xmax_txt, self)
#         form.addRow("X min (blank = auto):", self.ed_xmin)
#         form.addRow("X max (blank = auto):", self.ed_xmax)
#
#         btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
#         btns.accepted.connect(self.accept)
#         btns.rejected.connect(self.reject)
#         layout.addWidget(btns)
#
#     def values(self):
#         color = self.ed_color.text().strip() or None
#         xscale = self.cmb_xscale.currentText()
#         direction = self.cmb_dir.currentText()
#
#         xmin_txt = self.ed_xmin.text().strip()
#         xmax_txt = self.ed_xmax.text().strip()
#
#         if xmin_txt and xmax_txt:
#             try:
#                 xlim = (float(xmin_txt), float(xmax_txt))
#             except ValueError:
#                 xlim = None
#         else:
#             xlim = None
#
#         return color, xscale, direction, xlim

class LogDisplaySettingsDialog(QDialog):
    """
    Edit display settings for one continuous log in one track.

    Existing settings (kept):
      - color, xscale, direction, xlim

    Added settings:
      - render (line/points), linewidth, linestyle
      - marker, markersize
      - alpha
      - decimate
      - clip, mask_nan
      - zorder
    """

    def __init__(self, parent, log_name: str, cfg: dict):
        super().__init__(parent)
        self.setWindowTitle(f"Log display: {log_name}")
        self.resize(420, 520)

        self._log_name = log_name
        self._cfg_in = dict(cfg or {})
        self._result = None

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # ---- Color (with picker) ----
        self.ed_color = QLineEdit(self)
        self.ed_color.setText(str(self._cfg_in.get("color", "black")))
        btn_pick = QPushButton("Pick…", self)
        row = QHBoxLayout()
        row.addWidget(self.ed_color)
        row.addWidget(btn_pick)
        form.addRow("Color:", row)
        btn_pick.clicked.connect(self._pick_color)

        # ---- X scale ----
        self.cmb_xscale = QComboBox(self)
        self.cmb_xscale.addItems(["linear", "log"])
        self.cmb_xscale.setCurrentText(self._cfg_in.get("xscale", "linear"))
        form.addRow("X scale:", self.cmb_xscale)

        # ---- Direction ----
        self.cmb_dir = QComboBox(self)
        self.cmb_dir.addItems(["normal", "reverse"])
        self.cmb_dir.setCurrentText(self._cfg_in.get("direction", "normal"))
        form.addRow("Direction:", self.cmb_dir)

        # ---- X limits ----
        xlim = self._cfg_in.get("xlim", None)
        xmn = xlim[0] if isinstance(xlim, (list, tuple)) and len(xlim) == 2 else None
        xmx = xlim[1] if isinstance(xlim, (list, tuple)) and len(xlim) == 2 else None

        self.chk_xlim = QCheckBox("Use x-limits", self)
        self.chk_xlim.setChecked(xmn is not None and xmx is not None)

        self.spin_xmin = QDoubleSpinBox(self)
        self.spin_xmin.setRange(-1e12, 1e12)
        self.spin_xmin.setDecimals(6)
        self.spin_xmin.setValue(float(xmn) if xmn is not None else 0.0)

        self.spin_xmax = QDoubleSpinBox(self)
        self.spin_xmax.setRange(-1e12, 1e12)
        self.spin_xmax.setDecimals(6)
        self.spin_xmax.setValue(float(xmx) if xmx is not None else 1.0)

        xlim_row = QHBoxLayout()
        xlim_row.addWidget(self.chk_xlim)
        xlim_row.addWidget(QLabel("min:", self))
        xlim_row.addWidget(self.spin_xmin)
        xlim_row.addWidget(QLabel("max:", self))
        xlim_row.addWidget(self.spin_xmax)
        form.addRow("X limits:", xlim_row)

        # ---- Render mode (NEW) ----
        self.cmb_render = QComboBox(self)
        self.cmb_render.addItems(["line", "points"])
        self.cmb_render.setCurrentText(self._cfg_in.get("render", "line"))
        form.addRow("Render:", self.cmb_render)

        # ---- Line settings (NEW) ----
        self.spin_lw = QDoubleSpinBox(self)
        self.spin_lw.setRange(0.1, 20.0)
        self.spin_lw.setDecimals(2)
        self.spin_lw.setSingleStep(0.1)
        self.spin_lw.setValue(float(self._cfg_in.get("linewidth", 1.0)))
        form.addRow("Line width:", self.spin_lw)

        self.cmb_ls = QComboBox(self)
        self.cmb_ls.addItems(["-", "--", "-.", ":", "None"])
        self.cmb_ls.setCurrentText(str(self._cfg_in.get("style", "-")))
        form.addRow("Line style:", self.cmb_ls)

        # ---- Point settings (NEW) ----
        self.ed_marker = QLineEdit(self)
        self.ed_marker.setText(str(self._cfg_in.get("marker", ".")))
        form.addRow("Marker:", self.ed_marker)

        self.spin_ms = QDoubleSpinBox(self)
        self.spin_ms.setRange(0.1, 50.0)
        self.spin_ms.setDecimals(2)
        self.spin_ms.setSingleStep(0.2)
        self.spin_ms.setValue(float(self._cfg_in.get("markersize", 2.0)))
        form.addRow("Marker size:", self.spin_ms)

        # ---- Alpha (NEW) ----
        self.spin_alpha = QDoubleSpinBox(self)
        self.spin_alpha.setRange(0.0, 1.0)
        self.spin_alpha.setDecimals(2)
        self.spin_alpha.setSingleStep(0.05)
        self.spin_alpha.setValue(float(self._cfg_in.get("alpha", 1.0)))
        form.addRow("Alpha:", self.spin_alpha)

        # ---- Decimate (NEW) ----
        self.spin_dec = QSpinBox(self)
        self.spin_dec.setRange(1, 1000)
        self.spin_dec.setValue(int(self._cfg_in.get("decimate", 1)))
        form.addRow("Decimate (every N):", self.spin_dec)

        # ---- Clip / mask (NEW) ----
        self.chk_clip = QCheckBox("Clip to x-limits (if set)", self)
        self.chk_clip.setChecked(bool(self._cfg_in.get("clip", True)))
        form.addRow("Clipping:", self.chk_clip)

        self.chk_mask = QCheckBox("Mask NaN/Inf", self)
        self.chk_mask.setChecked(bool(self._cfg_in.get("mask_nan", True)))
        form.addRow("Masking:", self.chk_mask)

        # ---- Z-order (NEW) ----
        self.spin_z = QSpinBox(self)
        self.spin_z.setRange(-100, 100)
        self.spin_z.setValue(int(self._cfg_in.get("zorder", 2)))
        form.addRow("Z-order:", self.spin_z)

        # OK/Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # wiring to enable/disable based on render mode
        self.cmb_render.currentTextChanged.connect(self._update_enable_states)
        self.chk_xlim.toggled.connect(self._update_enable_states)
        self._update_enable_states()

    def _pick_color(self):
        current = self.ed_color.text().strip() or "#000000"
        qcol = QColor(current) if QColor(current).isValid() else QColor("#000000")
        col = QColorDialog.getColor(qcol, self, "Pick log color")
        if col.isValid():
            self.ed_color.setText(col.name())

    def _update_enable_states(self):
        render = self.cmb_render.currentText().strip().lower()

        # xlim enable
        use_xlim = self.chk_xlim.isChecked()
        self.spin_xmin.setEnabled(use_xlim)
        self.spin_xmax.setEnabled(use_xlim)
        self.chk_clip.setEnabled(use_xlim)

        # line controls only if line
        is_line = (render == "line")
        self.spin_lw.setEnabled(is_line)
        self.cmb_ls.setEnabled(is_line)

        # marker controls only if points
        is_pts = (render == "points")
        self.ed_marker.setEnabled(is_pts)
        self.spin_ms.setEnabled(is_pts)

    def _on_accept(self):
        # validate xlim
        xlim = None
        if self.chk_xlim.isChecked():
            xmin = float(self.spin_xmin.value())
            xmax = float(self.spin_xmax.value())
            if np.isclose(xmin, xmax):
                QMessageBox.warning(self, "Log settings", "x-limits min and max must differ.")
                return
            xlim = [xmin, xmax]

        render = self.cmb_render.currentText().strip().lower()
        style = self.cmb_ls.currentText().strip()
        if style == "None":
            style = "None"

        out = dict(self._cfg_in)  # keep any unknown keys too

        out["color"] = self.ed_color.text().strip() or "black"
        out["xscale"] = self.cmb_xscale.currentText().strip()
        out["direction"] = self.cmb_dir.currentText().strip()

        if xlim is not None:
            out["xlim"] = xlim
        else:
            out.pop("xlim", None)

        # NEW fields
        out["render"] = render
        out["alpha"] = float(self.spin_alpha.value())
        out["decimate"] = int(self.spin_dec.value())
        out["clip"] = bool(self.chk_clip.isChecked())
        out["mask_nan"] = bool(self.chk_mask.isChecked())
        out["zorder"] = int(self.spin_z.value())

        # line / points specific
        if render == "line":
            out["linewidth"] = float(self.spin_lw.value())
            out["style"] = style if style != "None" else "None"
        else:
            out["marker"] = (self.ed_marker.text().strip() or ".")
            out["markersize"] = float(self.spin_ms.value())

        self._result = out
        self.accept()

    def result_config(self) -> dict | None:
        return self._result


class AllTopsTableDialog(QDialog):
    """
    Edit/add/delete formation tops of all wells in a single table.

    Columns: Well, Top, Level, Depth
    - Existing rows: Well, Top via comboboxes (disabled), Depth editable.
    - New rows: Well, Top via comboboxes (enabled), Depth editable.
      Top choices come from stratigraphy + any extra tops found in wells.
    Filter box: filters by substring in Well/Top/Level columns.
    """

    COL_WELL = 0
    COL_TOP = 1
    COL_LEVEL = 2
    COL_DEPTH = 3

    def __init__(self, parent, wells, stratigraphy=None):
        super().__init__(parent)
        self.setWindowTitle("Edit all formation tops")
        self.resize(800, 500)

        self._wells = wells
        self._strat = stratigraphy or {}

        # existing (well_name, top_name) pairs from incoming data
        self._existing_pairs = set()
        for wi, well in enumerate(self._wells):
            well_name = well.get("name", f"Well {wi+1}")
            tops = well.get("tops", {}) or {}
            for top_name in tops.keys():
                self._existing_pairs.add((well_name, top_name))

        # sets for easy combo population
        self._well_names = sorted({
            w.get("name", f"Well {i+1}") for i, w in enumerate(self._wells)
        })

        # all top names: first strat order, then any extra from wells
        strat_names = list(self._strat.keys())
        extra_names = set()
        for well in self._wells:
            for tname in (well.get("tops", {}) or {}).keys():
                if tname not in strat_names:
                    extra_names.add(tname)
        self._top_names = strat_names + sorted(extra_names)

        # records deletions of existing tops
        self._deleted_pairs = set()

        # result structure on accept
        self._result = None  # {"updates": {...}, "additions": {...}, "deletions": set(...)}

        # ---------- layout ----------
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit depths of formation tops for all wells.\n"
            "Use the filter to search by well name or top name.\n"
            "You can also add new tops (choose Well + Top + Depth) or delete rows.",
            self
        ))

        # filter box
        flayout = QFormLayout()
        self.ed_filter = QLineEdit(self)
        self.ed_filter.setPlaceholderText("Filter by well / top / level...")
        self.ed_filter.textChanged.connect(self._apply_filter)
        flayout.addRow("Filter:", self.ed_filter)
        layout.addLayout(flayout)

        # table
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Well", "Top", "Level", "Depth"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # add/delete row buttons
        row_btn_layout = QHBoxLayout()
        self.btn_add_row = QPushButton("Add row", self)
        self.btn_del_row = QPushButton("Delete selected row(s)", self)
        row_btn_layout.addWidget(self.btn_add_row)
        row_btn_layout.addWidget(self.btn_del_row)
        row_btn_layout.addStretch(1)
        layout.addLayout(row_btn_layout)

        self.btn_add_row.clicked.connect(self._add_row)
        self.btn_del_row.clicked.connect(self._delete_selected_rows)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # fill data
        self._populate_table()

    # ---------------- combobox helpers ----------------

    def _create_well_combo(self, selected_name: str = "", enabled: bool = True) -> QComboBox:
        cb = QComboBox(self.table)
        cb.addItems(self._well_names)
        if selected_name and selected_name in self._well_names:
            cb.setCurrentText(selected_name)
        if not enabled:
            cb.setEnabled(False)
        return cb

    def _create_top_combo(self, selected_name: str = "", enabled: bool = True) -> QComboBox:
        cb = QComboBox(self.table)
        cb.addItems(self._top_names)
        if selected_name and selected_name in self._top_names:
            cb.setCurrentText(selected_name)
        if not enabled:
            cb.setEnabled(False)
        # when top changes, update Level column if we have stratigraphy
        cb.currentTextChanged.connect(self._update_level_for_row_from_top)
        return cb

    def _update_level_for_row_from_top(self, top_name: str):
        """
        When top combo changes on any row, update the Level column using stratigraphy.
        """
        if not self._strat:
            return

        # find which combobox emitted the signal
        cb = self.sender()
        if cb is None:
            return

        # locate row of this combobox
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, self.COL_TOP) is cb:
                level = ""
                meta = self._strat.get(top_name, {}) or {}
                level = meta.get("level", "")
                it_level = self.table.item(row, self.COL_LEVEL)
                if it_level is None:
                    it_level = QTableWidgetItem(level)
                    it_level.setFlags(it_level.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row, self.COL_LEVEL, it_level)
                else:
                    it_level.setText(level)
                break

    # ---------------- populate / helpers ----------------

    def _populate_table(self):
        """
        Fill table with rows for every (well, top).
        Order: by stratigraphy (if provided), then any remaining tops.
        """
        rows = []

        for wi, well in enumerate(self._wells):
            well_name = well.get("name", f"Well {wi+1}")
            tops = well.get("tops", {}) or {}
            if not tops:
                continue

            ordered_names = list(self._strat.keys()) if self._strat else []
            used = set()

            # first by strat column order
            for name in ordered_names:
                if name in tops:
                    rows.append((well_name, name))
                    used.add(name)

            # add any remaining tops not in stratigraphy
            for name in tops.keys():
                if name not in used:
                    rows.append((well_name, name))

        self.table.setRowCount(len(rows))

        for row, (well_name, top_name) in enumerate(rows):
            # find depth
            depth = 0.0
            for well in self._wells:
                if well.get("name", "") == well_name:
                    tops = well.get("tops", {}) or {}
                    val = tops.get(top_name)
                    if isinstance(val, dict):
                        depth = float(val.get("depth", 0.0))
                    else:
                        depth = float(val)
                    break

            level = ""
            if self._strat:
                meta = self._strat.get(top_name, {}) or {}
                level = meta.get("level", "")

            # Well combobox (existing row, disabled)
            cb_well = self._create_well_combo(well_name, enabled=False)
            self.table.setCellWidget(row, self.COL_WELL, cb_well)

            # Top combobox (existing row, disabled)
            cb_top = self._create_top_combo(top_name, enabled=False)
            self.table.setCellWidget(row, self.COL_TOP, cb_top)

            # Level (read-only)
            it_level = QTableWidgetItem(level)
            it_level.setFlags(it_level.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, self.COL_LEVEL, it_level)

            # Depth (editable)
            it_depth = QTableWidgetItem(f"{depth:.3f}")
            it_depth.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_DEPTH, it_depth)

    def _add_row(self):
        """
        Add a new row: Well & Top via combos (enabled), Depth editable.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)

        cb_well = self._create_well_combo("", enabled=True)
        self.table.setCellWidget(row, self.COL_WELL, cb_well)

        cb_top = self._create_top_combo("", enabled=True)
        self.table.setCellWidget(row, self.COL_TOP, cb_top)

        # Level auto-filled when top changes (handled by signal)
        it_level = QTableWidgetItem("")
        it_level.setFlags(it_level.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, self.COL_LEVEL, it_level)

        it_depth = QTableWidgetItem("")
        it_depth.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, self.COL_DEPTH, it_depth)

    def _delete_selected_rows(self):
        """
        Delete selected rows. If a row corresponds to an existing (well,top),
        record it in _deleted_pairs so caller can remove that top from wells.
        """
        sel_rows = sorted(
            {idx.row() for idx in self.table.selectedIndexes()},
            reverse=True
        )
        for row in sel_rows:
            cb_well = self.table.cellWidget(row, self.COL_WELL)
            cb_top = self.table.cellWidget(row, self.COL_TOP)

            well_name = cb_well.currentText().strip() if cb_well else ""
            top_name = cb_top.currentText().strip() if cb_top else ""

            pair = (well_name, top_name)
            if pair in self._existing_pairs:
                self._deleted_pairs.add(pair)

            self.table.removeRow(row)

    def _apply_filter(self, text: str):
        """Hide rows that don't match the filter text."""
        txt = text.strip().lower()
        n_rows = self.table.rowCount()
        if not txt:
            for row in range(n_rows):
                self.table.setRowHidden(row, False)
            return

        for row in range(n_rows):
            show = False

            # Well & Top from combobox
            cb_well = self.table.cellWidget(row, self.COL_WELL)
            cb_top = self.table.cellWidget(row, self.COL_TOP)
            well_txt = cb_well.currentText().lower() if cb_well else ""
            top_txt = cb_top.currentText().lower() if cb_top else ""

            if txt in well_txt or txt in top_txt:
                show = True
            else:
                # Level from item
                item = self.table.item(row, self.COL_LEVEL)
                if item and txt in item.text().lower():
                    show = True

            self.table.setRowHidden(row, not show)

    def _on_accept(self):
        """
        Validate depths and build:
          - updates:   (well_name, top_name) -> depth
          - additions: (well_name, top_name) -> depth
          - deletions: set of (well_name, top_name)
        """
        updates = {}
        additions = {}
        seen_pairs = set()

        n_rows = self.table.rowCount()

        for row in range(n_rows):
            cb_well = self.table.cellWidget(row, self.COL_WELL)
            cb_top = self.table.cellWidget(row, self.COL_TOP)
            item_depth = self.table.item(row, self.COL_DEPTH)

            well_name = cb_well.currentText().strip() if cb_well else ""
            top_name = cb_top.currentText().strip() if cb_top else ""
            depth_txt = item_depth.text().strip() if item_depth else ""

            # skip completely empty rows (shouldn't really happen with combos, but just in case)
            if not well_name and not top_name and not depth_txt:
                continue

            if not well_name or not top_name or not depth_txt:
                QMessageBox.warning(
                    self,
                    "Edit tops",
                    f"Row {row+1} is incomplete. Please select Well, Top, and Depth or delete the row."
                )
                return

            # depth numeric?
            try:
                depth = float(depth_txt)
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Edit tops",
                    f"Invalid depth '{depth_txt}' in row {row+1}. Please enter a number."
                )
                return

            pair = (well_name, top_name)
            if pair in seen_pairs:
                QMessageBox.warning(
                    self,
                    "Edit tops",
                    f"Duplicate (Well, Top) pair '{well_name}', '{top_name}' in the table.\n"
                    "Each top may only appear once."
                )
                return
            seen_pairs.add(pair)

            if pair in self._existing_pairs:
                updates[pair] = depth
            else:
                additions[pair] = depth

        self._result = {
            "updates": updates,
            "additions": additions,
            "deletions": set(self._deleted_pairs),
        }
        self.accept()

    def result_changes(self):
        """
        Return dict:
          {
            "updates":   { (well_name, top_name): depth, ... },
            "additions": { (well_name, top_name): depth, ... },
            "deletions": set( (well_name, top_name), ... ),
          }
        or None if dialog was cancelled.
        """
        return self._result

class NewWellDialog(QDialog):
    """
    Dialog to create a new well with basic settings.
    Produces a dict you can append to self.all_wells.
    """

    def __init__(self, parent, existing_names=None):
        super().__init__(parent)
        self.setWindowTitle("Add new well")
        self.resize(400, 300)

        self._existing_names = set(existing_names or [])

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Enter well header information.\n"
            "Name should be unique in the project.", self
        ))

        form = QFormLayout()
        layout.addLayout(form)

        # Name
        self.ed_name = QLineEdit(self)
        form.addRow("Name:", self.ed_name)

        # UWI
        self.ed_uwi = QLineEdit(self)
        form.addRow("UWI:", self.ed_uwi)

        # X, Y
        self.spin_x = QDoubleSpinBox(self)
        self.spin_x.setRange(-1e9, 1e9)
        self.spin_x.setDecimals(3)
        self.spin_x.setSpecialValueText("NaN")
        self.spin_x.setValue(0.0)
        form.addRow("Surface X (m):", self.spin_x)

        self.spin_y = QDoubleSpinBox(self)
        self.spin_y.setRange(-1e9, 1e9)
        self.spin_y.setDecimals(3)
        self.spin_y.setSpecialValueText("NaN")
        self.spin_y.setValue(0.0)
        form.addRow("Surface Y (m):", self.spin_y)

        # Reference type (KB, RL, RT, DF, etc.)
        self.cmb_ref_type = QComboBox(self)
        self.cmb_ref_type.addItems(["KB", "RL", "RT", "DF"])
        form.addRow("Reference type:", self.cmb_ref_type)

        # Reference depth (e.g. KB elevation)
        self.spin_ref_depth = QDoubleSpinBox(self)
        self.spin_ref_depth.setRange(-1e5, 1e5)
        self.spin_ref_depth.setDecimals(3)
        self.spin_ref_depth.setValue(0.0)
        form.addRow("Reference depth (m):", self.spin_ref_depth)

        # Total depth (MD measured from reference)
        self.spin_td = QDoubleSpinBox(self)
        self.spin_td.setRange(0.0, 1e5)
        self.spin_td.setDecimals(3)
        self.spin_td.setValue(1000.0)
        form.addRow("Total depth (m):", self.spin_td)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._result = None

    def _on_accept(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "New well", "Please enter a well name.")
            return
        if name in self._existing_names:
            QMessageBox.warning(
                self, "New well",
                f"A well named '{name}' already exists in the project. "
                "Please choose another name."
            )
            return

        uwi = self.ed_uwi.text().strip()
        x = float(self.spin_x.value())
        y = float(self.spin_y.value())
        ref_type = self.cmb_ref_type.currentText()
        ref_depth = float(self.spin_ref_depth.value())
        total_depth = float(self.spin_td.value())

        new_well = {
            "name": name,
            "uwi": uwi,
            "x": x,
            "y": y,
            "reference_type": ref_type,
            "reference_depth": ref_depth,
            "total_depth": total_depth,
            "tops": {},
            "logs": {},
            "discrete_logs": {},
        }

        self._result = new_well
        self.accept()

    def result_well(self):
        """Return well dict or None if cancelled."""
        return self._result

class AllWellsSettingsDialog(QDialog):
    """
    Edit basic settings of all wells in a single table.

    Columns:
      0: Name
      1: UWI
      2: X
      3: Y
      4: Reference type (KB/RL/RT/DF/other)
      5: Reference depth
      6: Total depth

    Does NOT add or delete wells – just edits existing headers.
    """

    COL_NAME  = 0
    COL_UWI   = 1
    COL_X     = 2
    COL_Y     = 3
    COL_REFT  = 4
    COL_REFZ  = 5
    COL_TD    = 6

    def __init__(self, parent, wells):
        super().__init__(parent)
        self.setWindowTitle("Edit well settings")
        self.resize(900, 400)

        self._wells = wells
        self._result = None  # list of header dicts, parallel to wells

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit well header parameters.\n"
            "Name must be unique. X/Y, reference depth, and total depth must be numeric.",
            self
        ))

        # table
        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Name", "UWI", "X", "Y", "Ref. type", "Ref. depth", "Total depth"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # optional future buttons (add/delete wells) – for now we just leave empty row
        btn_row_layout = QHBoxLayout()
        btn_row_layout.addStretch(1)
        layout.addLayout(btn_row_layout)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._populate_table()

    # ---------- populate ----------

    def _populate_table(self):
        n = len(self._wells)
        self.table.setRowCount(n)

        for row, w in enumerate(self._wells):
            name = w.get("name", f"Well {row+1}")
            uwi  = w.get("uwi", "")

            x = w.get("x", 0.0)
            y = w.get("y", 0.0)

            ref_type   = w.get("reference_type", "KB")
            ref_depth  = w.get("reference_depth", 0.0)
            total_depth = w.get("total_depth", 0.0)

            # Name
            it_name = QTableWidgetItem(str(name))
            self.table.setItem(row, self.COL_NAME, it_name)

            # UWI
            it_uwi = QTableWidgetItem(str(uwi))
            self.table.setItem(row, self.COL_UWI, it_uwi)

            # X, Y
            it_x = QTableWidgetItem(f"{x:.3f}")
            it_x.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_X, it_x)

            it_y = QTableWidgetItem(f"{y:.3f}")
            it_y.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_Y, it_y)

            # Reference type as combobox
            cb_ref = QComboBox(self.table)
            cb_ref.addItems(["KB", "RL", "RT", "DF", "Other"])
            # if custom value, add it
            if ref_type not in [cb_ref.itemText(i) for i in range(cb_ref.count())]:
                cb_ref.addItem(ref_type)
            cb_ref.setCurrentText(ref_type)
            self.table.setCellWidget(row, self.COL_REFT, cb_ref)

            # Reference depth
            it_refz = QTableWidgetItem(f"{ref_depth:.3f}")
            it_refz.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_REFZ, it_refz)

            # Total depth
            it_td = QTableWidgetItem(f"{total_depth:.3f}")
            it_td.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_TD, it_td)

    # ---------- accept / validate ----------

    def _on_accept(self):
        n_rows = self.table.rowCount()

        # collect/validate
        names = []
        headers = []

        for row in range(n_rows):
            it_name = self.table.item(row, self.COL_NAME)
            it_uwi  = self.table.item(row, self.COL_UWI)
            it_x    = self.table.item(row, self.COL_X)
            it_y    = self.table.item(row, self.COL_Y)
            it_refz = self.table.item(row, self.COL_REFZ)
            it_td   = self.table.item(row, self.COL_TD)
            cb_ref  = self.table.cellWidget(row, self.COL_REFT)

            name = it_name.text().strip() if it_name else ""
            if not name:
                QMessageBox.warning(
                    self,
                    "Well settings",
                    f"Row {row+1}: Name is empty. Please fill a well name."
                )
                return

            names.append(name)

            uwi = it_uwi.text().strip() if it_uwi else ""

            def _parse_float(item, row_label):
                if item is None:
                    return 0.0
                txt = item.text().strip()
                if not txt:
                    return 0.0
                try:
                    return float(txt.replace(",", "."))
                except ValueError:
                    raise ValueError(f"Row {row+1}: invalid {row_label} '{txt}'.")

            try:
                x = _parse_float(it_x, "X")
                y = _parse_float(it_y, "Y")
                ref_depth = _parse_float(it_refz, "reference depth")
                total_depth = _parse_float(it_td, "total depth")
            except ValueError as e:
                QMessageBox.warning(self, "Well settings", str(e))
                return

            ref_type = cb_ref.currentText().strip() if cb_ref else "KB"
            if not ref_type:
                ref_type = "KB"

            headers.append({
                "name": name,
                "uwi": uwi,
                "x": x,
                "y": y,
                "reference_type": ref_type,
                "reference_depth": ref_depth,
                "total_depth": total_depth,
            })

        # name uniqueness
        if len(set(names)) != len(names):
            QMessageBox.warning(
                self,
                "Well settings",
                "Well names must be unique. Please adjust duplicates."
            )
            return

        self._result = headers
        self.accept()

    def result_headers(self):
        """
        Returns list of dicts, one per row/well:
          [{
             "name": ...,
             "uwi": ...,
             "x": ...,
             "y": ...,
             "reference_type": ...,
             "reference_depth": ...,
             "total_depth": ...,
          }, ...]
        or None if cancelled.
        """
        return self._result

class SingleWellSettingsDialog(QDialog):
    """
    Edit header settings for a single well:
      - name, UWI, X, Y
      - reference type, reference depth, total depth
    """

    def __init__(self, parent, well: dict, existing_names=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit well: {well.get('name', '')}")
        self.resize(400, 300)

        self._orig_name = well.get("name", "")
        self._existing_names = set(existing_names or []) - {self._orig_name}
        self._result = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit well header parameters.\n"
            "Name must be unique. X/Y, reference depth, and total depth must be numeric.",
            self
        ))

        form = QFormLayout()
        layout.addLayout(form)

        # Name
        self.ed_name = QLineEdit(self)
        self.ed_name.setText(well.get("name", ""))
        form.addRow("Name:", self.ed_name)

        # UWI
        self.ed_uwi = QLineEdit(self)
        self.ed_uwi.setText(well.get("uwi", ""))
        form.addRow("UWI:", self.ed_uwi)

        # X, Y
        self.spin_x = QDoubleSpinBox(self)
        self.spin_x.setRange(-1e9, 1e9)
        self.spin_x.setDecimals(3)
        self.spin_x.setValue(float(well.get("x", 0.0)))
        form.addRow("Surface X (m):", self.spin_x)

        self.spin_y = QDoubleSpinBox(self)
        self.spin_y.setRange(-1e9, 1e9)
        self.spin_y.setDecimals(3)
        self.spin_y.setValue(float(well.get("y", 0.0)))
        form.addRow("Surface Y (m):", self.spin_y)

        # Reference type
        self.cmb_ref_type = QComboBox(self)
        self.cmb_ref_type.addItems(["KB", "RL", "RT", "DF", "Other"])
        ref_type = well.get("reference_type", "KB")
        if ref_type not in [self.cmb_ref_type.itemText(i) for i in range(self.cmb_ref_type.count())]:
            self.cmb_ref_type.addItem(ref_type)
        self.cmb_ref_type.setCurrentText(ref_type)
        form.addRow("Reference type:", self.cmb_ref_type)

        # Reference depth
        self.spin_ref_depth = QDoubleSpinBox(self)
        self.spin_ref_depth.setRange(-1e5, 1e5)
        self.spin_ref_depth.setDecimals(3)
        self.spin_ref_depth.setValue(float(well.get("reference_depth", 0.0)))
        form.addRow("Reference depth (m):", self.spin_ref_depth)

        # Total depth
        self.spin_td = QDoubleSpinBox(self)
        self.spin_td.setRange(0.0, 1e6)
        self.spin_td.setDecimals(3)
        self.spin_td.setValue(float(well.get("total_depth", 0.0)))
        form.addRow("Total depth (m):", self.spin_td)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Well settings", "Please enter a well name.")
            return
        if name in self._existing_names:
            QMessageBox.warning(
                self,
                "Well settings",
                f"A well named '{name}' already exists.\n"
                "Please choose another name."
            )
            return

        uwi = self.ed_uwi.text().strip()
        x = float(self.spin_x.value())
        y = float(self.spin_y.value())
        ref_type = self.cmb_ref_type.currentText().strip() or "KB"
        ref_depth = float(self.spin_ref_depth.value())
        total_depth = float(self.spin_td.value())

        self._result = {
            "name": name,
            "uwi": uwi,
            "x": x,
            "y": y,
            "reference_type": ref_type,
            "reference_depth": ref_depth,
            "total_depth": total_depth,
        }
        self.accept()

    def result_header(self):
        """Return dict with updated header fields, or None."""
        return self._result

class NewDiscreteTrackDialog(QDialog):
    """
    Dialog to define a new discrete track.

    Produces a track config like:
      {
        "name": "<track name>",
        "logs": [],
        "discrete": {
            "log": "<discrete log name>",
            "label": "<axis label>",
            "color_map": {},
            "default_color": "#dddddd",
            "missing": -999,
        },
      }
    """

    def __init__(self, parent, available_discrete_logs=None, existing_track_names=None):
        super().__init__(parent)
        self.setWindowTitle("Add discrete track")
        self.resize(400, 220)

        self._available_discrete_logs = sorted(set(available_discrete_logs or []))
        self._existing_track_names = set(existing_track_names or [])
        self._result = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Define a new discrete track.\n"
            "Choose a track name and a discrete log to display.",
            self
        ))

        form = QFormLayout()
        layout.addLayout(form)

        # Track name
        self.ed_track_name = QLineEdit(self)
        form.addRow("Track name:", self.ed_track_name)

        # Discrete log name (combo)
        self.cmb_log = QComboBox(self)
        self.cmb_log.setEditable(True)  # allow typing a new name if needed
        self.cmb_log.addItems(self._available_discrete_logs)
        form.addRow("Discrete log:", self.cmb_log)

        # Label (optional; default to discrete log name)
        self.ed_label = QLineEdit(self)
        form.addRow("Label (optional):", self.ed_label)

        # Missing code (string, default "-999")
        self.ed_missing = QLineEdit(self)
        self.ed_missing.setText("-999")
        form.addRow("Missing code:", self.ed_missing)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        track_name = self.ed_track_name.text().strip()
        if not track_name:
            QMessageBox.warning(self, "Discrete track", "Please enter a track name.")
            return
        if track_name in self._existing_track_names:
            QMessageBox.warning(
                self,
                "Discrete track",
                f"A track named '{track_name}' already exists.\n"
                "Please choose another name."
            )
            return

        log_name = self.cmb_log.currentText().strip()
        if not log_name:
            QMessageBox.warning(self, "Discrete track", "Please select or enter a discrete log name.")
            return

        label = self.ed_label.text().strip() or log_name

        missing_txt = self.ed_missing.text().strip()
        # store missing code as string; your plotting/export treats it symbolically
        if not missing_txt:
            missing_txt = "-999"

        self._result = {
            "name": track_name,
            "logs": [],  # no continuous logs in this track by default
            "discrete": {
                "log": log_name,
                "label": label,
                "color_map": {},           # user can edit later via log-display dialog
                "default_color": "#dddddd",
                "missing": missing_txt,
            },
        }
        self.accept()

    def result_track(self):
        """Return the new track dict or None."""
        return self._result

class DiscreteColorEditorDialog(QDialog):
    """
    Edit color map for a discrete track.

    Parameters
    ----------
    log_name : str
        Name of the discrete log (for display).
    color_map : dict
        Existing mapping value -> color string (e.g. "#ff0000").
    default_color : str
        Default color used when no mapping exists.
    available_values : iterable (optional)
        Values encountered in wells for this discrete log; used to
        prepopulate rows if not present in color_map.
    """

    COL_VALUE = 0
    COL_COLOR = 1

    def __init__(self, parent, log_name, color_map=None,
                 default_color="#dddddd", available_values=None):
        super().__init__(parent)
        self.setWindowTitle(f"Discrete colors: {log_name}")
        self.resize(500, 400)

        self._log_name = log_name
        self._color_map_in = dict(color_map or {})
        self._default_color_in = default_color
        self._available_values = set(str(v) for v in (available_values or []))

        self._result_color_map = None
        self._result_default_color = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit colors for discrete values.\n"
            "Double-click the Color cell or use the 'Pick color' button "
            "to choose a color.",
            self
        ))

        # --- table of value -> color ---
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Value", "Color"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Buttons to add/remove rows
        btn_row_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add row", self)
        self.btn_del = QPushButton("Delete selected", self)
        btn_row_layout.addWidget(self.btn_add)
        btn_row_layout.addWidget(self.btn_del)
        btn_row_layout.addStretch(1)
        layout.addLayout(btn_row_layout)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._delete_selected_rows)

        # Default color row
        def_layout = QHBoxLayout()
        def_layout.addWidget(QLabel("Default color:", self))
        self.ed_default = QLineEdit(self)
        self.ed_default.setText(self._default_color_in)
        self.btn_pick_default = QPushButton("Pick...", self)
        def_layout.addWidget(self.ed_default)
        def_layout.addWidget(self.btn_pick_default)
        def_layout.addStretch(1)
        layout.addLayout(def_layout)

        self.btn_pick_default.clicked.connect(self._pick_default_color)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # signals for color picking in table
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        # populate table
        self._populate_table()

    # ---------- populate ----------

    def _populate_table(self):
        """
        Fill table with union of color_map keys and available_values.
        """
        # union of values in color_map and encountered values
        all_values = set(self._color_map_in.keys()) | self._available_values
        all_values = sorted(all_values, key=str)

        self.table.setRowCount(len(all_values))

        for row, val in enumerate(all_values):
            # value
            it_val = QTableWidgetItem(str(val))
            self.table.setItem(row, self.COL_VALUE, it_val)

            # color
            col_str = self._color_map_in.get(val, "")
            it_col = QTableWidgetItem(col_str)
            self.table.setItem(row, self.COL_COLOR, it_col)

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # empty value/color
        self.table.setItem(row, self.COL_VALUE, QTableWidgetItem(""))
        self.table.setItem(row, self.COL_COLOR, QTableWidgetItem(""))

    def _delete_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()},
                      reverse=True)
        for r in rows:
            self.table.removeRow(r)

    # ---------- color picking ----------

    def _on_cell_double_clicked(self, row, col):
        if col != self.COL_COLOR:
            return
        item = self.table.item(row, col)
        current = item.text().strip() if item else ""
        initial = QColor(current) if current else QColor("#ffffff")
        color = QColorDialog.getColor(initial, self, "Pick color")
        if color.isValid():
            if item is None:
                item = QTableWidgetItem()
                self.table.setItem(row, col, item)
            item.setText(color.name())

    def _pick_default_color(self):
        current = self.ed_default.text().strip()
        initial = QColor(current) if current else QColor("#dddddd")
        color = QColorDialog.getColor(initial, self, "Pick default color")
        if color.isValid():
            self.ed_default.setText(color.name())

    # ---------- accept / result ----------

    def _on_accept(self):
        color_map = {}
        n_rows = self.table.rowCount()

        for row in range(n_rows):
            it_val = self.table.item(row, self.COL_VALUE)
            it_col = self.table.item(row, self.COL_COLOR)
            val = it_val.text().strip() if it_val else ""
            col = it_col.text().strip() if it_col else ""

            if not val:
                if col:
                    QMessageBox.warning(
                        self,
                        "Discrete colors",
                        f"Row {row+1}: color set but value empty.\n"
                        "Either fill a value or clear the row."
                    )
                    return
                # completely empty row -> skip
                continue

            if not col:
                # no color -> skip this mapping (will use default)
                continue

            color_map[val] = col

        default_color = self.ed_default.text().strip() or "#dddddd"

        self._result_color_map = color_map
        self._result_default_color = default_color
        self.accept()

    def result_colors(self):
        """
        Returns (color_map, default_color) or (None, None) if canceled.
        """
        return self._result_color_map, self._result_default_color

class ImportFaciesIntervalsDialog(QDialog):
    """
    Preview dialog for facies / lithology intervals.

    Expects a list of dicts with keys:
      well, id, litho_trend, lithology, trend,
      environment, rel_top, rel_base
    """

    def __init__(self, parent, intervals):
        super().__init__(parent)
        self.setWindowTitle("Import facies intervals")
        self.resize(800, 400)

        self._intervals = intervals
        self._accepted_data = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Preview of imported facies intervals.\n"
            "LithoTrend has been split into Lithology and Trend.",
            self
        ))

        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["Well", "ID", "LithoTrend", "Lithology", "Trend",
             "Environment", "Rel_Top", "Rel_Base"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self._populate_table()

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _populate_table(self):
        self.table.setRowCount(len(self._intervals))
        for row, iv in enumerate(self._intervals):
            def set_item(col, text, align_right=False):
                it = QTableWidgetItem(str(text))
                if align_right:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, col, it)

            set_item(0, iv.get("well", ""))
            set_item(1, iv.get("id", ""))
            set_item(2, iv.get("litho_trend", ""))
            set_item(3, iv.get("lithology", ""))
            set_item(4, iv.get("trend", ""))
            set_item(5, iv.get("environment", ""))
            rt = iv.get("rel_top", None)
            rb = iv.get("rel_base", None)
            set_item(6, f"{rt:.3f}" if rt is not None else "", True)
            set_item(7, f"{rb:.3f}" if rb is not None else "", True)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

    def _on_accept(self):
        self._accepted_data = list(self._intervals)
        self.accept()

    def result_intervals(self):
        return self._accepted_data

class LithofaciesDisplaySettingsDialog(QDialog):
    """
    Dialog to edit display parameters of a lithofacies track:

      - hardness_scale: controls how strongly hardness is visualized
      - spline.smooth:  smoothing factor / tension
      - spline.num_samples: sampling resolution for curves

    You can adapt names/semantics as needed in your drawing code.
    """

    def __init__(self, parent,
                 hardness_scale: float = 1.0,
                 spline_smooth: float = 0.5,
                 spline_num_samples: int = 200):
        super().__init__(parent)
        self.setWindowTitle("Lithofacies display settings")
        self.resize(400, 240)

        self._result = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Adjust display parameters of the lithofacies track.\n"
            "Hardness scale controls intensity; spline controls smoothing / resolution.",
            self
        ))

        form = QFormLayout()
        layout.addLayout(form)

        # Hardness scale
        self.spin_hardness = QDoubleSpinBox(self)
        self.spin_hardness.setRange(0.0, 100.0)
        self.spin_hardness.setDecimals(3)
        self.spin_hardness.setSingleStep(0.1)
        self.spin_hardness.setValue(float(hardness_scale))
        form.addRow("Hardness scale:", self.spin_hardness)

        # Spline smoothing
        self.spin_smooth = QDoubleSpinBox(self)
        self.spin_smooth.setRange(0.0, 10.0)
        self.spin_smooth.setDecimals(3)
        self.spin_smooth.setSingleStep(0.1)
        self.spin_smooth.setValue(float(spline_smooth))
        form.addRow("Spline smooth:", self.spin_smooth)

        # Spline resolution (number of samples)
        self.spin_samples = QSpinBox(self)
        self.spin_samples.setRange(10, 5000)
        self.spin_samples.setSingleStep(10)
        self.spin_samples.setValue(int(spline_num_samples))
        form.addRow("Spline samples:", self.spin_samples)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_accept(self):
        hardness = float(self.spin_hardness.value())
        smooth   = float(self.spin_smooth.value())
        samples  = int(self.spin_samples.value())

        self._result = {
            "hardness_scale": hardness,
            "spline": {
                "smooth": smooth,
                "num_samples": samples,
            },
        }
        self.accept()

    def result_params(self):
        """
        Returns:
            {
              "hardness_scale": float,
              "spline": {
                 "smooth": float,
                 "num_samples": int,
              }
            }
        or None if cancelled.
        """
        return self._result

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialogButtonBox, QLabel, QMessageBox, QComboBox
)
from PyQt5.QtCore import Qt


class LithofaciesTableDialog(QDialog):
    """
    Edit lithofacies intervals for all wells in a table.

    Expects wells to be a list of dicts, each possibly having:
        well["name"]
        well["facies_intervals"] = [
            {
                "well": well_name,
                "id": int,
                "litho_trend": str,
                "lithology": str,
                "trend": "cu"|"fu"|"constant",
                "environment": str,
                "rel_top": float,
                "rel_base": float,
            }, ...
        ]
    """

    COL_WELL   = 0
    COL_ID     = 1
    COL_LITH   = 2
    COL_TREND  = 3
    COL_ENV    = 4
    COL_TOP    = 5
    COL_BASE   = 6

    def __init__(self, parent, wells):
        super().__init__(parent)
        self.setWindowTitle("Edit lithofacies intervals")
        self.resize(900, 500)

        self._wells = wells
        self._well_names = [w.get("name", f"Well {i+1}") for i, w in enumerate(wells)]
        self._accepted_intervals = None  # will become {well_name: [intervals...]}

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit lithofacies intervals for all wells.\n"
            "Trend: 'cu' (coarsening upward), 'fu' (fining upward), "
            "or 'constant'. Relative depths 0–1.",
            self
        ))

        # table
        self.table = QTableWidget(self)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Well", "ID", "Lithology", "Trend", "Environment", "Rel_Top", "Rel_Base"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # buttons row (add/delete)
        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add row", self)
        self.btn_del = QPushButton("Delete selected", self)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_del)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._delete_selected_rows)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._populate_table()

    # ------------------------------------------------------------------
    # Populate table from wells
    # ------------------------------------------------------------------
    def _populate_table(self):
        rows_data = []

        for w in self._wells:
            wname = w.get("name", "")
            facies_list = w.get("facies_intervals", []) or []
            for iv in facies_list:
                rows_data.append({
                    "well": wname,
                    "id": iv.get("id", ""),
                    "lithology": iv.get("lithology", ""),
                    "trend": iv.get("trend", "constant"),
                    "environment": iv.get("environment", ""),
                    "rel_top": iv.get("rel_top", None),
                    "rel_base": iv.get("rel_base", None),
                })

        self.table.setRowCount(len(rows_data))

        for row, iv in enumerate(rows_data):
            # Well (combobox)
            cmb = QComboBox(self.table)
            cmb.addItems(self._well_names)
            if iv["well"] in self._well_names:
                cmb.setCurrentText(iv["well"])
            self.table.setCellWidget(row, self.COL_WELL, cmb)

            # ID
            it_id = QTableWidgetItem(str(iv["id"]))
            it_id.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_ID, it_id)

            # Lithology
            it_lith = QTableWidgetItem(iv["lithology"])
            self.table.setItem(row, self.COL_LITH, it_lith)

            # Trend (combo)
            cmb_trend = QComboBox(self.table)
            cmb_trend.addItems(["constant", "cu", "fu"])
            t = (iv["trend"] or "constant").lower()
            if t not in ["constant", "cu", "fu"]:
                t = "constant"
            cmb_trend.setCurrentText(t)
            self.table.setCellWidget(row, self.COL_TREND, cmb_trend)

            # Environment
            it_env = QTableWidgetItem(iv["environment"])
            self.table.setItem(row, self.COL_ENV, it_env)

            # Rel_Top
            rt = iv["rel_top"]
            txt_rt = "" if rt is None else f"{rt:.4f}"
            it_rt = QTableWidgetItem(txt_rt)
            it_rt.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_TOP, it_rt)

            # Rel_Base
            rb = iv["rel_base"]
            txt_rb = "" if rb is None else f"{rb:.4f}"
            it_rb = QTableWidgetItem(txt_rb)
            it_rb.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, self.COL_BASE, it_rb)

    # ------------------------------------------------------------------
    # Row operations
    # ------------------------------------------------------------------
    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # default well = first in list
        cmb = QComboBox(self.table)
        cmb.addItems(self._well_names)
        self.table.setCellWidget(row, self.COL_WELL, cmb)

        # ID default empty
        self.table.setItem(row, self.COL_ID, QTableWidgetItem(""))

        # Lithology
        self.table.setItem(row, self.COL_LITH, QTableWidgetItem(""))

        # Trend combo
        cmb_trend = QComboBox(self.table)
        cmb_trend.addItems(["constant", "cu", "fu"])
        cmb_trend.setCurrentText("constant")
        self.table.setCellWidget(row, self.COL_TREND, cmb_trend)

        # Environment
        self.table.setItem(row, self.COL_ENV, QTableWidgetItem(""))

        # Rel_Top / Rel_Base
        self.table.setItem(row, self.COL_TOP, QTableWidgetItem(""))
        self.table.setItem(row, self.COL_BASE, QTableWidgetItem(""))

    def _delete_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    # ------------------------------------------------------------------
    # Accept: validate & build per-well facies_intervals
    # ------------------------------------------------------------------
    def _on_accept(self):
        n_rows = self.table.rowCount()
        by_well = {}

        for row in range(n_rows):
            cmb_well = self.table.cellWidget(row, self.COL_WELL)
            if cmb_well is None:
                continue
            well_name = cmb_well.currentText().strip()
            if not well_name:
                QMessageBox.warning(
                    self,
                    "Lithofacies",
                    f"Row {row+1}: Well name is empty."
                )
                return

            it_id   = self.table.item(row, self.COL_ID)
            it_lith = self.table.item(row, self.COL_LITH)
            cmb_tr  = self.table.cellWidget(row, self.COL_TREND)
            it_env  = self.table.item(row, self.COL_ENV)
            it_rt   = self.table.item(row, self.COL_TOP)
            it_rb   = self.table.item(row, self.COL_BASE)

            id_txt = it_id.text().strip() if it_id else ""
            if not id_txt:
                QMessageBox.warning(
                    self,
                    "Lithofacies",
                    f"Row {row+1}: ID is empty."
                )
                return

            try:
                _id = int(id_txt)
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Lithofacies",
                    f"Row {row+1}: ID '{id_txt}' is not an integer."
                )
                return

            lithology = it_lith.text().strip() if it_lith else ""
            env_txt   = it_env.text().strip() if it_env else ""
            trend_txt = cmb_tr.currentText().strip().lower() if cmb_tr else "constant"
            if trend_txt not in ("constant", "cu", "fu"):
                trend_txt = "constant"

            def _parse_rel(item, label):
                if item is None:
                    return None
                txt = item.text().strip()
                if not txt:
                    return None
                try:
                    return float(txt.replace(",", "."))
                except ValueError:
                    raise ValueError(f"Row {row+1}: invalid {label} '{txt}'")

            try:
                rel_top  = _parse_rel(it_rt, "Rel_Top")
                rel_base = _parse_rel(it_rb, "Rel_Base")
            except ValueError as e:
                QMessageBox.warning(self, "Lithofacies", str(e))
                return

            # reconstruct LithoTrend string: "Lithology, cu/fu" or just Lithology
            if trend_txt in ("cu", "fu"):
                lithotrend = f"{lithology}, {trend_txt}"
            else:
                lithotrend = lithology

            iv = {
                "well": well_name,
                "id": _id,
                "litho_trend": lithotrend,
                "lithology": lithology,
                "trend": trend_txt,
                "environment": env_txt,
                "rel_top": rel_top,
                "rel_base": rel_base,
            }

            by_well.setdefault(well_name, []).append(iv)

        # keep them in the order entered; optionally sort by rel_top etc.
        self._accepted_intervals = by_well
        self.accept()

    def result_by_well(self):
        """
        Returns dict:
           { well_name: [intervals...] }
        or None if cancelled.
        """
        return self._accepted_intervals

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

        # # alpha
        # self.spin_alpha = QDoubleSpinBox(self)
        # self.spin_alpha.setRange(0.0, 1.0)
        # self.spin_alpha.setDecimals(2)
        # self.spin_alpha.setSingleStep(0.05)
        # self.spin_alpha.setValue(1.0)
        # form.addRow("Alpha:", self.spin_alpha)

        # # interpolation
        # self.cmb_interp = QComboBox(self)
        # self.cmb_interp.addItems(["nearest", "bilinear", "bicubic"])
        # self.cmb_interp.setCurrentText("nearest")
        # form.addRow("Interpolation:", self.cmb_interp)
        #
        # # colormap (optional)
        # self.cmb_cmap = QComboBox(self)
        # self.cmb_cmap.addItems(["(none)", "gray"])
        # self.cmb_cmap.setCurrentText("(none)")
        # form.addRow("Colormap:", self.cmb_cmap)
        #
        # # flip
        # self.chk_flip = QCheckBox("Flip vertically", self)
        # self.chk_flip.setChecked(False)
        # form.addRow("Orientation:", self.chk_flip)

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
        # alpha = float(self.spin_alpha.value())
        # interpolation = self.cmb_interp.currentText().strip()
        # cmap_txt = self.cmb_cmap.currentText().strip()
        # cmap = None if cmap_txt == "(none)" else cmap_txt
        # flip = bool(self.chk_flip.isChecked())

        self._result = {
            "well_name": well_name,
            "key": key,
            "path": path,
            "top_depth": top_d,
            "base_depth": base_d,
            "label": label,
            # "alpha": alpha,
            # "interpolation": interpolation,
            # "cmap": cmap,
            # "flip_vertical": flip,
        }
        self.accept()

    def result(self):
        return self._result

class MoveWellDialog(QDialog):
    def __init__(self, parent, well_name, max_pos, current_pos):
        super().__init__(parent)
        self.setWindowTitle(f"Move well: {well_name}")
        self.resize(300, 120)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        self.spin = QSpinBox(self)
        self.spin.setRange(1, max_pos)
        self.spin.setValue(current_pos + 1)
        form.addRow("New position:", self.spin)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def position(self):
        return self.spin.value() - 1