import numpy as np
from PyQt5.QtWidgets import (
    QDoubleSpinBox, QPushButton,
    QDialog, QLineEdit, QDialogButtonBox,
    QDialog, QVBoxLayout, QFormLayout,
    QComboBox, QDialogButtonBox,
    QTableWidget, QTableWidgetItem,
    QLabel, QMessageBox, QHBoxLayout,
)
from collections import OrderedDict

from PyQt5.QtCore import Qt

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

class LogDisplaySettingsDialog(QDialog):
    """
    Dialog to edit display settings for a log mnemonic:
      - color
      - xscale: linear/log
      - direction: normal/reverse
      - xlim: min/max or blank for auto
    """
    def __init__(self, parent, log_name: str,
                 color: str, xscale: str, direction: str, xlim):
        super().__init__(parent)
        self.setWindowTitle(f"Display settings – {log_name}")
        self.resize(320, 200)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.ed_color = QLineEdit(color or "", self)
        form.addRow("Color:", self.ed_color)

        self.cmb_xscale = QComboBox(self)
        self.cmb_xscale.addItems(["linear", "log"])
        idx = self.cmb_xscale.findText(xscale or "linear")
        if idx < 0:
            idx = 0
        self.cmb_xscale.setCurrentIndex(idx)
        form.addRow("X scale:", self.cmb_xscale)

        self.cmb_dir = QComboBox(self)
        self.cmb_dir.addItems(["normal", "reverse"])
        idx = self.cmb_dir.findText(direction or "normal")
        if idx < 0:
            idx = 0
        self.cmb_dir.setCurrentIndex(idx)
        form.addRow("Direction:", self.cmb_dir)

        # xlim: two line edits, blank = auto
        xmin_txt = ""
        xmax_txt = ""
        if xlim is not None and len(xlim) == 2:
            try:
                xmin_txt = str(xlim[0])
                xmax_txt = str(xlim[1])
            except Exception:
                pass

        self.ed_xmin = QLineEdit(xmin_txt, self)
        self.ed_xmax = QLineEdit(xmax_txt, self)
        form.addRow("X min (blank = auto):", self.ed_xmin)
        form.addRow("X max (blank = auto):", self.ed_xmax)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def values(self):
        color = self.ed_color.text().strip() or None
        xscale = self.cmb_xscale.currentText()
        direction = self.cmb_dir.currentText()

        xmin_txt = self.ed_xmin.text().strip()
        xmax_txt = self.ed_xmax.text().strip()

        if xmin_txt and xmax_txt:
            try:
                xlim = (float(xmin_txt), float(xmax_txt))
            except ValueError:
                xlim = None
        else:
            xlim = None

        return color, xscale, direction, xlim

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