import numpy as np
from PyQt5.QtWidgets import (

    QDoubleSpinBox, QPushButton,
    QDialog,  QLineEdit
)



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

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QComboBox, QDialogButtonBox
)

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

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox,
    QLineEdit, QDialogButtonBox
)

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


from collections import OrderedDict

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QPushButton,
    QDialogButtonBox, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt


class StratigraphyEditorDialog(QDialog):
    """
    Table dialog to edit/add stratigraphy for the project.

    Expects stratigraphy as an ordered dict-like:
        {
          "Formation_1": {"level": "formation", "color": "#ff0000", "hatch": ""},
          "Member_1":    {"level": "member",    "color": "#00ff00", "hatch": "//"},
          ...
        }
    The key order defines shallow -> deep.
    """
    COL_NAME = 0
    COL_LEVEL = 1
    COL_COLOR = 2
    COL_HATCH = 3

    def __init__(self, parent, stratigraphy: dict | None):
        super().__init__(parent)
        self.setWindowTitle("Edit Stratigraphy")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # Info label
        layout.addWidget(QLabel(
            "Edit stratigraphic units (top = shallowest, bottom = deepest).\n"
            "Name must be unique; level, color and hatch are optional metadata.",
            self
        ))

        # Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Level", "Color", "Hatch"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        # Fill from existing stratigraphy
        self._load_from_stratigraphy(stratigraphy or {})

        # Buttons: Add row / Delete row
        btn_row_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add row", self)
        self.btn_del = QPushButton("Delete selected row(s)", self)
        btn_row_layout.addWidget(self.btn_add)
        btn_row_layout.addWidget(self.btn_del)
        btn_row_layout.addStretch(1)
        layout.addLayout(btn_row_layout)

        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._delete_selected_rows)

        # OK / Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._accepted_strat = None  # will hold new strat on OK

    # ---------- populate / helpers ----------

    def _load_from_stratigraphy(self, stratigraphy: dict):
        """Fill table from ordered stratigraphy dict."""
        # preserve insertion order
        keys = list(stratigraphy.keys())
        self.table.setRowCount(len(keys))

        for row, name in enumerate(keys):
            meta = stratigraphy.get(name, {}) or {}
            level = meta.get("level", "")
            color = meta.get("color", "")
            hatch = meta.get("hatch", "")

            self.table.setItem(row, self.COL_NAME,  QTableWidgetItem(str(name)))
            self.table.setItem(row, self.COL_LEVEL, QTableWidgetItem(str(level)))
            self.table.setItem(row, self.COL_COLOR, QTableWidgetItem(str(color)))
            self.table.setItem(row, self.COL_HATCH, QTableWidgetItem(str(hatch)))

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        # new row starts empty; user fills it

    def _delete_selected_rows(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _on_accept(self):
        """Validate and build internal strat dict."""
        new_strat = OrderedDict()
        n_rows = self.table.rowCount()

        for row in range(n_rows):
            name_item = self.table.item(row, self.COL_NAME)
            if name_item is None:
                continue

            name = name_item.text().strip()
            if not name:
                # Completely empty row? Skip.
                level_item = self.table.item(row, self.COL_LEVEL)
                color_item = self.table.item(row, self.COL_COLOR)
                hatch_item = self.table.item(row, self.COL_HATCH)
                if not any(
                    it and it.text().strip()
                    for it in (level_item, color_item, hatch_item)
                ):
                    continue
                else:
                    QMessageBox.warning(
                        self,
                        "Stratigraphy",
                        f"Row {row+1} has metadata but no Name. Please fill Name or clear the row."
                    )
                    return

            if name in new_strat:
                QMessageBox.warning(
                    self,
                    "Stratigraphy",
                    f"Duplicate unit name '{name}' in row {row+1}. Names must be unique."
                )
                return

            level = ""
            color = ""
            hatch = ""

            level_item = self.table.item(row, self.COL_LEVEL)
            color_item = self.table.item(row, self.COL_COLOR)
            hatch_item = self.table.item(row, self.COL_HATCH)

            if level_item is not None:
                level = level_item.text().strip()
            if color_item is not None:
                color = color_item.text().strip()
            if hatch_item is not None:
                hatch = hatch_item.text().strip()

            new_strat[name] = {
                "level": level,
                "color": color,
                "hatch": hatch,
            }

        self._accepted_strat = new_strat
        self.accept()

    def result_stratigraphy(self):
        """Return OrderedDict of new stratigraphy or None if dialog cancelled."""
        return self._accepted_strat
    
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDoubleSpinBox,
    QDialogButtonBox
)

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
    
    
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox
)

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

from collections import OrderedDict

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QTableWidgetItem, QLineEdit,
    QDialogButtonBox, QLabel, QMessageBox, QPushButton, QComboBox
)
from PyQt5.QtCore import Qt


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

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QDialogButtonBox, QLabel, QMessageBox
)
from PyQt5.QtCore import Qt


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
