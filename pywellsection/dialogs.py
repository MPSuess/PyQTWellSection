import numpy as np

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout,
    QLineEdit, QComboBox, QDialogButtonBox, QLabel, QMessageBox,
    QDoubleSpinBox, QCheckBox, QColorDialog, QSpinBox, QCheckBox,
    QFileDialog, QTextBrowser, QTableWidget, QTableWidgetItem,
    QPushButton, QWidget, QListWidget, QGroupBox,
)
# from PyQt5.QtWidgets import (
#     QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
#     QPushButton, QDialogButtonBox, QMessageBox, QLabel, QLineEdit,
#     QPlainTextEdit, QCheckBox, QSpinBox, QGroupBox, QFormLayout
# )
import numpy as np

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from PyQt5.QtGui import QPixmap, QImage, QIcon

import matplotlib.cm as cm

from matplotlib import colormaps

from collections import OrderedDict

from PyQt5.QtGui import QColor

from PyQt5.QtCore import Qt

from PyQt5.QtCore import QUrl
from PyQt5.QtCore import QSize

import os

import pandas as pd




class HelpDialog(QDialog):
    def __init__(self, parent=None, html: str = "", title: str = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(820, 620)

        layout = QVBoxLayout(self)

        self.browser = QTextBrowser(self)
        self.browser.setStyleSheet("background-color: white; color: black;")
        self.browser.setOpenExternalLinks(True)   # open links in system browser
        self.browser.setHtml(html)
        layout.addWidget(self.browser)

        btns = QDialogButtonBox(QDialogButtonBox.Close, self)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        btns.button(QDialogButtonBox.Close).clicked.connect(self.close)
        layout.addWidget(btns)
#       alternative method calling load_html ...
#       self.load_html('pywellsection/PyQtHelp.html')

    def load_html(self, html_path: str):
        if not os.path.exists(html_path):
            self.browser.setPlainText(f"Help file not found:\n{html_path}")
            return

        # Use file URL so relative links (images, css) work
        url = QUrl.fromLocalFile(os.path.abspath(html_path))
        self.browser.setSource(url)

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

class OldNewTrackDialog(QDialog):
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

class NewTrackDialog(QDialog):
    """
    Create a new track of type:
      - continuous
      - discrete
      - facies
      - bitmap

    Returns a dict track configuration matching your draw function conventions.
    """

    def __init__(self, parent,
                 existing_track_names=None,
                 available_discrete_logs=None):
        super().__init__(parent)
        self.setWindowTitle("Add track")
        self.resize(520, 380)

        self._existing = set(existing_track_names or [])
        self._available_discrete_logs = sorted(set(available_discrete_logs or []))
        self._result = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Create a new track and select its type.\n"
            "Continuous: multiple continuous logs\n"
            "Discrete: interval fill log\n"
            "Facies: lithofacies intervals (color/hatch by environment)\n"
            "Bitmap: image/core track",
            self
        ))

        self.form = QFormLayout()
        form = self.form
        layout.addLayout(form)

        # Track name
        self.ed_name = QLineEdit(self)
        form.addRow("Track name:", self.ed_name)

        # Track type
        self.cmb_type = QComboBox(self)
        self.cmb_type.addItems(["continuous", "discrete", "facies", "bitmap"])
        form.addRow("Track type:", self.cmb_type)

        # -------------------------
        # Discrete options group
        # -------------------------
        self.disc_log = QComboBox(self)
        self.disc_log.setEditable(True)
        self.disc_log.addItems(self._available_discrete_logs)
        self.disc_label = QLineEdit(self)
        self.disc_label.setPlaceholderText("Label shown on track (optional)")
        self.disc_missing = QLineEdit(self)
        self.disc_missing.setText("-999")
        form.addRow("Discrete log:", self.disc_log)
        form.addRow("Discrete label:", self.disc_label)
        form.addRow("Missing code:", self.disc_missing)

        # -------------------------
        # Facies options group
        # -------------------------
        self.facies_label = QLineEdit(self)
        self.facies_label.setText("Facies")
        self.facies_color_by = QComboBox(self)
        self.facies_color_by.addItems(["environment", "lithology"])
        self.facies_default_color = QLineEdit(self)
        self.facies_default_color.setText("#cccccc")
        self.facies_default_hatch = QLineEdit(self)
        self.facies_default_hatch.setText("//")  # fallback hatch if env not mapped

        # “hardness / spline” defaults (since you added those settings)
        self.facies_hardness = QDoubleSpinBox(self)
        self.facies_hardness.setRange(0.0, 100.0)
        self.facies_hardness.setDecimals(3)
        self.facies_hardness.setValue(1.0)

        self.facies_smooth = QDoubleSpinBox(self)
        self.facies_smooth.setRange(0.0, 10.0)
        self.facies_smooth.setDecimals(3)
        self.facies_smooth.setValue(0.5)

        self.facies_samples = QDoubleSpinBox(self)
        self.facies_samples.setRange(10, 5000)
        self.facies_samples.setDecimals(0)
        self.facies_samples.setValue(200)

        form.addRow("Facies label:", self.facies_label)
        form.addRow("Color by:", self.facies_color_by)
        form.addRow("Default color:", self.facies_default_color)
        form.addRow("Default hatch:", self.facies_default_hatch)
        form.addRow("Hardness scale:", self.facies_hardness)
        form.addRow("Spline smooth:", self.facies_smooth)
        form.addRow("Spline samples:", self.facies_samples)

        # -------------------------
        # Bitmap options group
        # -------------------------
        self.bmp_label = QLineEdit(self)
        self.bmp_label.setText("Core")
        self.bmp_key = QLineEdit(self)
        self.bmp_key.setText("core")
        self.bmp_alpha = QDoubleSpinBox(self)
        self.bmp_alpha.setRange(0.0, 1.0)
        self.bmp_alpha.setDecimals(2)
        self.bmp_alpha.setValue(1.0)
        self.bmp_interp = QComboBox(self)
        self.bmp_interp.addItems(["nearest", "bilinear", "bicubic"])
        self.bmp_cmap = QComboBox(self)
        self.bmp_cmap.addItems(["(none)", "gray"])
        self.bmp_flip = QCheckBox("Flip vertically", self)

        form.addRow("Bitmap label:", self.bmp_label)
        form.addRow("Bitmap key:", self.bmp_key)
        form.addRow("Bitmap alpha:", self.bmp_alpha)
        form.addRow("Bitmap interpolation:", self.bmp_interp)
        form.addRow("Bitmap colormap:", self.bmp_cmap)
        form.addRow("Bitmap:", self.bmp_flip)

        # OK/Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # react to type changes
        self.cmb_type.currentTextChanged.connect(self._update_visibility)
#        self.cmb_type.currentTextChanged.connect(self._show_hide_form_row)
        self._update_visibility(self.cmb_type.currentText())

    def _show_hide_form_row(self, track_type: str):
        form_layout = self.form
        nrows = form_layout.rowCount()
        nindex = nrows*2

        t = (track_type or "").lower()
        # discrete visible?
        disc_vis = (t == "discrete")
        for idx in range(0, nindex):
            widgetItem = form_layout.itemAt(idx)
            print(widgetItem.widget)
            if widgetItem != None:
                widget = widgetItem.widget()
                print(widget.text())
                widget.hide()
                #widget.show()

            #
            #     if toggleBtn.isChecked():
            #         widget.show()
            #     else:
            #         widget.hide()



        #row.setVisible(show)

    def _update_visibility(self, track_type: str):
        """Show only relevant fields for chosen type."""
        t = (track_type or "").lower()

        # discrete visible?
        disc_vis = (t == "discrete")
        self.disc_log.setVisible(disc_vis)
        self.disc_label.setVisible(disc_vis)
        self.disc_missing.setVisible(disc_vis)

        # facies visible?
        fac_vis = (t == "facies")
        self.facies_label.setVisible(fac_vis)
        self.facies_color_by.setVisible(fac_vis)
        self.facies_default_color.setVisible(fac_vis)
        self.facies_default_hatch.setVisible(fac_vis)
        self.facies_hardness.setVisible(fac_vis)
        self.facies_smooth.setVisible(fac_vis)
        self.facies_samples.setVisible(fac_vis)

        # bitmap visible?
        bmp_vis = (t == "bitmap")
        self.bmp_label.setVisible(bmp_vis)
        self.bmp_key.setVisible(bmp_vis)
        self.bmp_alpha.setVisible(bmp_vis)
        self.bmp_interp.setVisible(bmp_vis)
        self.bmp_cmap.setVisible(bmp_vis)
        self.bmp_flip.setVisible(bmp_vis)

        # continuous has no extra widgets (kept simple)

    def _on_accept(self):
        name = self.ed_name.text().strip()
        if not name:
            QMessageBox.warning(self, "Add track", "Please provide a track name.")
            return
        if name in self._existing:
            QMessageBox.warning(self, "Add track", f"Track '{name}' already exists.")
            return

        track_type = self.cmb_type.currentText().strip().lower()

        # Base track skeleton
        track = {"name": name, "logs": [], "type": track_type}

        if track_type == "continuous":
            # nothing else needed
            pass

        elif track_type == "discrete":
            log_name = self.disc_log.currentText().strip()
            if not log_name:
                QMessageBox.warning(self, "Add track", "Please choose/enter a discrete log name.")
                return
            label = self.disc_label.text().strip() or log_name
            missing = (self.disc_missing.text().strip() or "-999")

            track["discrete"] = {
                "log": log_name,
                "label": label,
                "color_map": {},           # edit later in discrete color dialog
                "default_color": "#dddddd",
                "missing": missing,
            }

        elif track_type == "facies":
            label = self.facies_label.text().strip() or "Facies"
            color_by = self.facies_color_by.currentText().strip()
            default_color = self.facies_default_color.text().strip() or "#cccccc"
            default_hatch = self.facies_default_hatch.text().strip() or None

            track["facies"] = {
                "label": label,
                "color_by": color_by,
                "env_colors": {},          # user may fill later
                "env_hatches": {},         # user may fill later
                "lith_colors": {},         # optional if color_by=lithology
                "default_color": default_color,
                "default_hatch": default_hatch,
                "hardness_scale": float(self.facies_hardness.value()),
                "spline": {
                    "smooth": float(self.facies_smooth.value()),
                    "num_samples": int(self.facies_samples.value()),
                },
            }

        elif track_type == "bitmap":
            label = self.bmp_label.text().strip() or "Bitmap"
            key = self.bmp_key.text().strip() or "core"
            cmap_txt = self.bmp_cmap.currentText().strip()
            cmap = None if cmap_txt == "(none)" else cmap_txt

            track["bitmap"] = {
                "key": key,  # will resolve per well: well["bitmaps"][key]
                "label": label,
                "alpha": float(self.bmp_alpha.value()),
                "interpolation": self.bmp_interp.currentText().strip(),
                "cmap": cmap,
                "flip_vertical": bool(self.bmp_flip.isChecked()),
            }

        else:
            QMessageBox.warning(self, "Add track", f"Unknown track type: {track_type}")
            return

        self._result = track
        self.accept()

    def result_track(self):
        return self._result

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
    def __init__(self, parent, well_gap_factor: float, track_width: float, vertical_scale: float,
                 depth_min: float, depth_max:float):
        super().__init__(parent)
        self.setWindowTitle("Layout settings")
        self.resize(400, 150)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.spin_gap = QDoubleSpinBox(self)
        self.spin_gap.setFixedWidth(100)
        self.spin_gap.setRange(0.1, 20.0)
        self.spin_gap.setDecimals(2)
        self.spin_gap.setSingleStep(0.1)
        self.spin_gap.setValue(float(well_gap_factor))
        form.addRow("Gap between wells:", self.spin_gap)

        self.spin_track = QDoubleSpinBox(self)
        self.spin_track.setFixedWidth(100)
        self.spin_track.setRange(0.1, 10.0)
        self.spin_track.setDecimals(2)
        self.spin_track.setSingleStep(0.1)
        self.spin_track.setValue(float(track_width))
        form.addRow("Track width:", self.spin_track)

        self.spin_scale = QDoubleSpinBox(self)
        self.spin_scale.setFixedWidth(100)
        self.spin_scale.setRange(0.1, 1000.0)
        self.spin_scale.setDecimals(2)
        self.spin_scale.setSingleStep(0.1)
        self.spin_scale.setValue(float(vertical_scale))
        form.addRow("Vertical scale:", self.spin_scale)

        self.spin_min_depth = QDoubleSpinBox(self)
        self.spin_min_depth.setFixedWidth(100)
        self.spin_min_depth.setRange(-100000,100000)
        self.spin_min_depth.setDecimals(2)
        self.spin_min_depth.setSingleStep(10)
        self.spin_min_depth.setValue(float(depth_min))
        form.addRow("Section minimum depth:", self.spin_min_depth)

        self.spin_max_depth = QDoubleSpinBox(self)
        self.spin_max_depth.setFixedWidth(100)
        self.spin_max_depth.setRange(-100000,100000)
        self.spin_max_depth.setDecimals(2)
        self.spin_max_depth.setSingleStep(10)
        self.spin_max_depth.setValue(float(depth_max))
        form.addRow("Section maximum depth:", self.spin_max_depth)


        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def values(self):
        return (float(self.spin_gap.value()), float(self.spin_track.value()),
                float(self.spin_scale.value()), float(self.spin_min_depth.value()),
                float(self.spin_max_depth.value()))



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
        self.cmb_render.addItems(["line", "points", "color"])
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

        #--- Colormap selection - --

        # self.cmb_colorscale = QComboBox(self)
        # self.cmb_colorscale.addItem("")  # means no colormap
        # self.cmb_colorscale.addItems(list(colormaps))
        # self.cmb_colorscale.setCurrentText(self._cfg_in.get("colorscale", ""))

        #form.addRow("Color scale (optional):", self.cmb_colorscale)

        self.cmb_cmap = self.build_colormap_combo(self._cfg_in.get("colorscale", ""))
        form.addRow("Color scale:", self.cmb_cmap)

        # --- Range ---
        range_box = QHBoxLayout()
        self.spin_vmin = QDoubleSpinBox(self)
        self.spin_vmax = QDoubleSpinBox(self)
        self.spin_vmin.setDecimals(2)
        self.spin_vmax.setDecimals(2)
        self.spin_vmin.setRange(-1e6, 1e6)
        self.spin_vmax.setRange(-1e6, 1e6)
        vmin, vmax = (self._cfg_in.get("colorrange", [np.nan, np.nan]) if self._cfg_in.get("colorrange") else [np.nan, np.nan])
        if np.isfinite(vmin): self.spin_vmin.setValue(vmin)
        if np.isfinite(vmax): self.spin_vmax.setValue(vmax)
        range_box.addWidget(QLabel("Min:"))
        range_box.addWidget(self.spin_vmin)
        range_box.addWidget(QLabel("Max:"))
        range_box.addWidget(self.spin_vmax)

        form.addRow("Color range:", range_box)

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

        #cs = self.cmb_colorscale.currentText().strip()
        cs = self.cmb_cmap.currentText().strip()
        out["colorscale"] = cs
        out["colorrange"] = [self.spin_vmin.value(), self.spin_vmax.value()]

        self._result = out
        self.accept()

    def result_config(self) -> dict | None:
        return self._result

    def colormap_icon(self, cmap_name: str, width=120, height=18) -> QIcon:
        """
        Create a horizontal colorbar icon for a matplotlib colormap.
        """
        fig = Figure(figsize=(width / 100, height / 100), dpi=100)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()

        gradient = np.linspace(0, 1, 256).reshape(1, -1)
        ax.imshow(gradient, aspect="auto", cmap=cm.get_cmap(cmap_name))

        canvas.draw()
        buf = canvas.buffer_rgba()
        img = QImage(buf, buf.shape[1], buf.shape[0], QImage.Format_RGBA8888)
        pix = QPixmap.fromImage(img).scaled(width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        return QIcon(pix)

    def build_colormap_combo(self, current=None) -> QComboBox:
        cmb = QComboBox()
        cmb.setIconSize(QSize(120, 18))
        cmb.setMinimumWidth(160)

        # "None" option (classic single-color)
        cmb.addItem("None")
        cmb.setItemData(0, None)

        #cmaps = sorted(m for m in cm.cmap_d if not m.endswith("_r"))
        cmaps = list(colormaps)

        for name in cmaps:
            icon = self.colormap_icon(name)
            cmb.addItem(icon, name)
            cmb.setItemData(cmb.count() - 1, name)

        if current:
            idx = cmb.findText(current)
            if idx >= 0:
                cmb.setCurrentIndex(idx)

        return cmb

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

        # # key/name
        self.ed_key = QLineEdit(self)
        self.ed_key.setText("cp001")
        form.addRow("Bitmap Id:", self.ed_key)

        self.ed_name = QLineEdit(self)
        self.ed_name.setText("bitmap")
        form.addRow("Bitmap Name:", self.ed_name)

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
        form.addRow("Track name:", self.ed_label)

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
        name = self.ed_name.text().strip()

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

        label = self.ed_label.text().strip() or "core"
        # alpha = float(self.spin_alpha.value())
        # interpolation = self.cmb_interp.currentText().strip()
        # cmap_txt = self.cmb_cmap.currentText().strip()
        # cmap = None if cmap_txt == "(none)" else cmap_txt
        # flip = bool(self.chk_flip.isChecked())

        self._result = {
            "well_name": well_name,
            "name": name,
            "key": key,
            "path": path,
            "top_depth": top_d,
            "base_depth": base_d,
            "track": label,
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

class LoadBitmapForTrackDialog(QDialog):
    """
    Load an image and assign it to a well for a specific bitmap track key.
    Key comes from the track and is not editable.

    Returns:
      {
        "well_name": str,
        "path": str,
        "top_depth": float,
        "base_depth": float,
        "label": str,
        "alpha": float,
        "interpolation": str,
        "cmap": str|None,
        "flip_vertical": bool,
      }
    """

    def __init__(self, parent, well_names, track_name: str, bitmap_cfg: dict):
        super().__init__(parent)
        self.setWindowTitle(f"Load bitmap → Track: {track_name}")
        self.resize(560, 280)

        self._result = None
        self._well_names = list(well_names)
        self._bitmap_cfg = dict(bitmap_cfg or {})

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        # Well selection
        self.cmb_well = QComboBox(self)
        self.cmb_well.addItems(self._well_names)
        form.addRow("Well:", self.cmb_well)

        # Track key (locked)
        key = self._bitmap_cfg.get("key", "bitmap")
        self.lbl_key = QLabel(key, self)
        form.addRow("Bitmap key:", self.lbl_key)

        # File path + browse
        self.ed_path = QLineEdit(self)
        btn_browse = QPushButton("Browse…", self)
        row_path = QHBoxLayout()
        row_path.addWidget(self.ed_path)
        row_path.addWidget(btn_browse)
        form.addRow("Image file:", row_path)
        btn_browse.clicked.connect(self._browse)

        # Depth interval
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

        # Label defaults from track
        self.ed_label = QLineEdit(self)
        self.ed_label.setText(self._bitmap_cfg.get("label", "Bitmap"))
        form.addRow("Label:", self.ed_label)

        # Alpha defaults from track
        self.spin_alpha = QDoubleSpinBox(self)
        self.spin_alpha.setRange(0.0, 1.0)
        self.spin_alpha.setDecimals(2)
        self.spin_alpha.setSingleStep(0.05)
        self.spin_alpha.setValue(float(self._bitmap_cfg.get("alpha", 1.0)))
        form.addRow("Alpha:", self.spin_alpha)

        # Interpolation defaults from track
        self.cmb_interp = QComboBox(self)
        self.cmb_interp.addItems(["nearest", "bilinear", "bicubic"])
        self.cmb_interp.setCurrentText(self._bitmap_cfg.get("interpolation", "nearest"))
        form.addRow("Interpolation:", self.cmb_interp)

        # Cmap defaults from track
        self.cmb_cmap = QComboBox(self)
        self.cmb_cmap.addItems(["(none)", "gray"])
        cmap = self._bitmap_cfg.get("cmap", None)
        self.cmb_cmap.setCurrentText("gray" if cmap == "gray" else "(none)")
        form.addRow("Colormap:", self.cmb_cmap)

        # Flip defaults from track
        self.chk_flip = QCheckBox("Flip vertically", self)
        self.chk_flip.setChecked(bool(self._bitmap_cfg.get("flip_vertical", False)))
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
        path = self.ed_path.text().strip()

        if not well_name:
            QMessageBox.warning(self, "Load bitmap", "Please choose a well.")
            return
        if not path:
            QMessageBox.warning(self, "Load bitmap", "Please choose an image file.")
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Load bitmap", "Image file does not exist.")
            return

        top_d = float(self.spin_top.value())
        base_d = float(self.spin_base.value())
        if abs(base_d - top_d) < 1e-9:
            QMessageBox.warning(self, "Load bitmap", "Top and Base depth must differ.")
            return

        cmap_txt = self.cmb_cmap.currentText().strip()
        cmap = None if cmap_txt == "(none)" else cmap_txt

        self._result = {
            "well_name": well_name,
            "path": path,
            "top_depth": top_d,
            "base_depth": base_d,
            "label": self.ed_label.text().strip() or "Bitmap",
            "alpha": float(self.spin_alpha.value()),
            "interpolation": self.cmb_interp.currentText().strip(),
            "cmap": cmap,
            "flip_vertical": bool(self.chk_flip.isChecked()),
        }
        self.accept()

    def result(self):
        return self._result

class BitmapPlacementDialog(QDialog):
    """
    Interactive editor for bitmap positions (top/base depths) for a given bitmap track key.
    Uses TRUE depth coordinates; picking converts from flattened plot y to true depth.
    """

    COL_WELL = 0
    COL_TOP = 1
    COL_BASE = 2
    COL_LABEL = 3
    COL_ALPHA = 4
    COL_FLIP = 5
    COL_PATH = 6

    def __init__(self, parent, wells, track_name: str, bitmap_key: str, panel_widget):
        super().__init__(parent)
        self.setWindowTitle(f"Edit bitmap positions — Track: {track_name}")
        self.resize(300, 520)

        self.wells = wells
        self.track_name = track_name
        self.bitmap_key = "track"
        self.panel = panel_widget  # active WellPanelWidget (for picking + redraw)

        self._active_pick = None  # {"well_name":..., "which":"top"|"base"}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Bitmap track key:  {bitmap_key}\n"
            "Edit TRUE depths (MD). Use Pick Top/Base to click in the plot.",
            self
        ))

        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
#            ["Well", "Top depth", "Base depth", "Label", "Alpha", "Flip", "Path"]
            ["Well", "Top depth", "Base depth", "Label"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        row_btn = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh", self)
        self.btn_apply = QPushButton("Apply", self)
        self.btn_pick_top = QPushButton("Pick TOP on plot", self)
        self.btn_pick_base = QPushButton("Pick BASE on plot", self)
        row_btn.addWidget(self.btn_refresh)
        row_btn.addWidget(self.btn_apply)
        row_btn.addStretch(1)
        row_btn.addWidget(self.btn_pick_top)
        row_btn.addWidget(self.btn_pick_base)
        layout.addLayout(row_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Close, self)
        btns.rejected.connect(self.close)
        btns.accepted.connect(self.close)
        layout.addWidget(btns)

        self.btn_refresh.clicked.connect(self.populate)
        self.btn_apply.clicked.connect(self.apply_to_model)
        self.btn_pick_top.clicked.connect(lambda: self.arm_pick("top"))
        self.btn_pick_base.clicked.connect(lambda: self.arm_pick("base"))

        self.populate()

    # ----------------------------
    # Build table from model
    # ----------------------------
    def populate(self):
        rows = []
        for w in self.wells:
            wname = w.get("name", "")
            bmps = (w.get("bitmaps") or {}).keys()
            if not wname or bmps is None:
                continue
            else:
                for bmp in bmps:
                    bitmap=w.get("bitmaps", {}).get(bmp, {})
                    rows.append((wname, bitmap, bmp))

        self.table.setRowCount(len(rows))

        for r, (wname, bmp, bmp_name) in enumerate(rows):
            self._set_item(r, self.COL_WELL, wname, editable=False)

            self._set_item(r, self.COL_TOP,  str(float(bmp.get("top_depth", 0.0))), editable=True)
            self._set_item(r, self.COL_BASE, str(float(bmp.get("base_depth", 0.0))), editable=True)

            self._set_item(r, self.COL_LABEL, str(bmp_name), editable=False)
            #self._set_item(r, self.COL_ALPHA, str(float(bmp.get("alpha", 1.0))), editable=True)

            #self._set_item(r, self.COL_FLIP, "1" if bmp.get("flip_vertical", False) else "0", editable=True)
            #self._set_item(r, self.COL_PATH, str(bmp.get("path", "")), editable=False)

        self.table.resizeColumnsToContents()

    def _set_item(self, row, col, text, editable=True):
        it = QTableWidgetItem(text)
        if not editable:
            it.setFlags(it.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, col, it)

    # ----------------------------
    # Apply edits back to wells
    # ----------------------------
    def apply_to_model(self):

        rows = []
        bitmap_keys = set()
        try:
            for w in self.wells:
                wname = w.get("name", "")
                bitmaps_keys = w.get("bitmaps", {}).keys()
                bmp_cfg = w.get("bitmaps", {})
                for key in bitmaps_keys: # key is the bitmap track key in this well
                    new_cfg = w.get("bitmaps", {}).get(key, {})
                    path_txt = new_cfg.get("path", "")
                    #new_cfg = bmp_cfg
                    for r in range(self.table.rowCount()):
                        #if r == 0: continue
                        if self.table.item(r, self.COL_LABEL).text() == key and wname == self.table.item(r, self.COL_WELL).text():
                            top_txt = self.table.item(r, self.COL_TOP).text().strip()
                            base_txt = self.table.item(r, self.COL_BASE).text().strip()
                            label_txt = self.table.item(r, self.COL_LABEL).text().strip()
                            #alpha_txt = self.table.item(r, self.COL_ALPHA).text().strip()
                            #flip_txt = self.table.item(r, self.COL_FLIP).text().strip()
                            #path_txt = self.table.item(r, self.COL_PATH).text().strip()

                            top_d = float(top_txt.replace(",", "."))
                            base_d = float(base_txt.replace(",", "."))
                            #alpha = float(alpha_txt.replace(",", "."))
                            #flip = bool(int(flip_txt)) if flip_txt else False

                            bmp_cfg.update({key:{"path":path_txt,"top_depth": top_d, "base_depth": base_d,
                                            "track":self.track_name}})


            # redraw
            if self.panel is not None:
                self.panel.draw_panel()

        except Exception as e:
            QMessageBox.warning(self, "Apply bitmap edits", f"Failed to apply edits:\n{e}")

    # ----------------------------
    # Picking integration
    # ----------------------------
    def arm_pick(self, which: str):
        """
        Arm pick mode: user clicks in plot to set TOP or BASE for selected row.
        """
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Pick", "Select a row (well) first.")
            return

        wname = self.table.item(row, self.COL_WELL).text().strip()
        if not wname:
            return

        self._active_pick = {"well_name": wname, "which": which}

        # Call into panel to arm one-click pick
        if self.panel is None or not hasattr(self.panel, "arm_bitmap_pick"):
            QMessageBox.warning(
                self, "Pick",
                "Panel does not implement arm_bitmap_pick(). Add the helper below to WellPanelWidget."
            )
            return

        self.panel.arm_bitmap_pick(
            dialog=self,
            well_name=wname,
            bitmap_key=self.bitmap_key,
            which=which,
        )

    def set_picked_depth(self, depth_true: float):
        """
        Called by panel after click. Updates current row cell.
        """
        row = self.table.currentRow()
        if row < 0 or self._active_pick is None:
            return

        which = self._active_pick.get("which")
        if which == "top":
            self.table.item(row, self.COL_TOP).setText(f"{depth_true:.3f}")
        else:
            self.table.item(row, self.COL_BASE).setText(f"{depth_true:.3f}")

        # optionally apply immediately and redraw
        self.apply_to_model()
        self._active_pick = None


class FillEditDialog(QDialog):
    """
    Edit one fill rule dict.

    Supported types:
      - to_value:    log + value + where
      - to_minmax:   log + side(min/max)
      - between_logs:left/right + where
    """
    def __init__(self, parent, available_logs, fill_dict=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Fill")
        self.resize(420, 260)

        self.selected_color = "#cccccc"

        self.available_logs = list(available_logs)
        self._fill = dict(fill_dict or {})

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        self.cmb_type = QComboBox(self)
        self.cmb_type.addItems(["to_value", "to_minmax", "between_logs"])
        self.cmb_type.setCurrentText(self._fill.get("type", "to_value"))
        form.addRow("Type:", self.cmb_type)

        self.cmb_log = QComboBox(self)
        self.cmb_log.addItems(self.available_logs)
        self.cmb_log.setCurrentText(self._fill.get("log", self.available_logs[0] if self.available_logs else ""))
        form.addRow("Log:", self.cmb_log)

        self.spin_value = QDoubleSpinBox(self)
        self.spin_value.setDecimals(6)
        self.spin_value.setRange(-1e12, 1e12)
        self.spin_value.setValue(float(self._fill.get("value", 0.0)))
        form.addRow("Value:", self.spin_value)

        self.cmb_where_val = QComboBox(self)
        self.cmb_where_val.addItems(["greater", "less"])
        self.cmb_where_val.setCurrentText(self._fill.get("where", "greater"))
        form.addRow("Where (to_value):", self.cmb_where_val)

        self.cmb_side = QComboBox(self)
        self.cmb_side.addItems(["min", "max"])
        self.cmb_side.setCurrentText(self._fill.get("side", "min"))
        form.addRow("Side (to_minmax):", self.cmb_side)

        self.cmb_left = QComboBox(self)
        self.cmb_left.addItems(self.available_logs)
        self.cmb_left.setCurrentText(self._fill.get("log_left", self.available_logs[0] if self.available_logs else ""))
        form.addRow("Left log:", self.cmb_left)

        self.cmb_right = QComboBox(self)
        self.cmb_right.addItems(self.available_logs)
        self.cmb_right.setCurrentText(self._fill.get("log_right", self.available_logs[0] if self.available_logs else ""))
        form.addRow("Right log:", self.cmb_right)

        self.cmb_where_between = QComboBox(self)
        self.cmb_where_between.addItems(["all", "left_greater", "right_greater"])
        self.cmb_where_between.setCurrentText(self._fill.get("where", "all"))
        form.addRow("Where (between):", self.cmb_where_between)

        # Facecolor with picker + preview
        #self.ed_face = QLineEdit(self)
        #self.ed_face.setText(self._fill.get("facecolor", "#cccccc"))

        self.cmb_face = QComboBox(self)
        face_select = ["color"] + self.available_logs
        self.cmb_face.addItems(face_select)

        self.btn_pick_face = QPushButton("Pick…", self)

        self.lbl_swatch = QLabel(self)
        self.lbl_swatch.setFixedSize(26, 18)
        self.lbl_swatch.setStyleSheet("border: 1px solid #666;")
        self._update_swatch(self.selected_color)

        row_face = QHBoxLayout()
        row_face.addWidget(self.cmb_face)
        row_face.addWidget(self.btn_pick_face)
        row_face.addWidget(self.lbl_swatch)

        wrap = QWidget(self)
        wrap.setLayout(row_face)
        form.addRow("Facecolor:", wrap)

        self.btn_pick_face.clicked.connect(self._pick_facecolor)
        #self.ed_face.textChanged.connect(lambda _: self._update_swatch(self.ed_face.text().strip()))

        self.ed_hatch = QLineEdit(self)
        self.ed_hatch.setText("" if self._fill.get("hatch") is None else str(self._fill.get("hatch")))
        form.addRow("Hatch (optional):", self.ed_hatch)

        self.spin_alpha = QDoubleSpinBox(self)
        self.spin_alpha.setDecimals(2)
        self.spin_alpha.setRange(0.0, 1.0)
        self.spin_alpha.setValue(float(self._fill.get("alpha", 0.35)))
        form.addRow("Alpha:", self.spin_alpha)

        self.spin_z = QDoubleSpinBox(self)
        self.spin_z.setDecimals(2)
        self.spin_z.setRange(-10.0, 10.0)
        self.spin_z.setValue(float(self._fill.get("zorder", 0.6)))
        form.addRow("Z-order:", self.spin_z)

        self.lbl_hint = QLabel("", self)
        self.lbl_hint.setWordWrap(True)
        layout.addWidget(self.lbl_hint)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.cmb_type.currentTextChanged.connect(self._update_visibility)
        self._update_visibility(self.cmb_type.currentText())

    def _update_visibility(self, t):
        t = (t or "").strip().lower()
        is_to_value = (t == "to_value")
        is_to_minmax = (t == "to_minmax")
        is_between = (t == "between_logs")

        self.cmb_log.setEnabled(is_to_value or is_to_minmax)
        self.spin_value.setEnabled(is_to_value)
        self.cmb_where_val.setEnabled(is_to_value)
        self.cmb_side.setEnabled(is_to_minmax)

        self.cmb_left.setEnabled(is_between)
        self.cmb_right.setEnabled(is_between)
        self.cmb_where_between.setEnabled(is_between)

        if is_to_minmax:
            self.lbl_hint.setText("to_minmax fills between the curve and its displayed x-limit (min/max) for this track.")
        else:
            self.lbl_hint.setText("")

    def fill_dict(self) -> dict:
        t = self.cmb_type.currentText().strip()

        d = {
            "type": t,
            "facecolor": self.selected_color or "#cccccc",
            "facetype": self.cmb_face.currentText(),
            "alpha": float(self.spin_alpha.value()),
            "hatch": (self.ed_hatch.text().strip() or None),
            "zorder": float(self.spin_z.value()),
        }

        if t == "to_value":
            d.update({
                "log": self.cmb_log.currentText().strip(),
                "value": float(self.spin_value.value()),
                "where": self.cmb_where_val.currentText().strip(),
            })
        elif t == "to_minmax":
            d.update({
                "log": self.cmb_log.currentText().strip(),
                "side": self.cmb_side.currentText().strip(),  # min/max
            })
        else:  # between_logs
            d.update({
                "log_left": self.cmb_left.currentText().strip(),
                "log_right": self.cmb_right.currentText().strip(),
                "where": self.cmb_where_between.currentText().strip(),
            })

        return d

    def _pick_facecolor(self):
        #initial = QColor(self.ed_face.text().strip() or "#cccccc")
        initial = QColor(self.selected_color)
        col = QColorDialog.getColor(initial, self, "Select fill color")
        if not col.isValid():
            return
        #self.ed_face.setText(col.name())  # "#RRGGBB"
        self.selected_color = col.name()
        self._update_swatch(self.selected_color)

    def _update_swatch(self, color_text: str):
        c = QColor(color_text) if color_text else QColor("#cccccc")
        if not c.isValid():
            c = QColor("#cccccc")
        self.lbl_swatch.setStyleSheet(
            f"border: 1px solid #666; background-color: {c.name()};"
        )

class TrackSettingsDialog(QDialog):
    """
    Edit a single track dict including 'fills'.
    """
    def __init__(self, parent, track: dict, available_logs):
        super().__init__(parent)
        self.setWindowTitle("Track Settings")
        self.resize(640, 420)

        self.track = track
        self.available_logs = list(available_logs)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        layout.addLayout(form)

        self.ed_name = QLineEdit(self)
        self.ed_name.setText(track.get("name", "Track"))
        form.addRow("Track name:", self.ed_name)

        # --- fills list ---
        self.list_fills = QListWidget(self)
        layout.addWidget(self.list_fills)

        btn_row = QHBoxLayout()
        self.btn_add = QPushButton("Add…", self)
        self.btn_edit = QPushButton("Edit…", self)
        self.btn_del = QPushButton("Delete", self)
        self.btn_up = QPushButton("Up", self)
        self.btn_down = QPushButton("Down", self)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_edit)
        btn_row.addWidget(self.btn_del)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_up)
        btn_row.addWidget(self.btn_down)
        layout.addLayout(btn_row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(btns)

        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)

        self.btn_add.clicked.connect(self._add_fill)
        self.btn_edit.clicked.connect(self._edit_fill)
        self.btn_del.clicked.connect(self._delete_fill)
        self.btn_up.clicked.connect(lambda: self._move_fill(-1))
        self.btn_down.clicked.connect(lambda: self._move_fill(+1))

        self._refresh_fill_list()

    def _refresh_fill_list(self):
        self.list_fills.clear()
        fills = self.track.get("fills", []) or []
        for f in fills:
            self.list_fills.addItem(self._fill_to_text(f))

    def _fill_to_text(self, f: dict) -> str:
        t = (f.get("type") or "").lower()
        if t == "to_value":
            return f"to_value: {f.get('log')} vs {f.get('value')} ({f.get('where','greater')})"
        if t == "to_minmax":
            return f"to_minmax: {f.get('log')} → {f.get('side','min')}"
        if t == "between_logs":
            return f"between: {f.get('log_left')} ↔ {f.get('log_right')} ({f.get('where','all')})"
        return f"fill: {t}"

    def _add_fill(self):
        if not self.available_logs:
            QMessageBox.information(self, "Fills", "No logs available for fills.")
            return
        dlg = FillEditDialog(self, self.available_logs, fill_dict=None)
        if dlg.exec_() != QDialog.Accepted:
            return
        self.track.setdefault("fills", []).append(dlg.fill_dict())
        self._refresh_fill_list()

    def _edit_fill(self):
        row = self.list_fills.currentRow()
        if row < 0:
            return
        fills = self.track.get("fills", []) or []
        if row >= len(fills):
            return
        dlg = FillEditDialog(self, self.available_logs, fill_dict=fills[row])
        if dlg.exec_() != QDialog.Accepted:
            return
        fills[row] = dlg.fill_dict()
        self.track["fills"] = fills
        self._refresh_fill_list()
        self.list_fills.setCurrentRow(row)

    def _delete_fill(self):
        row = self.list_fills.currentRow()
        if row < 0:
            return
        fills = self.track.get("fills", []) or []
        if row >= len(fills):
            return
        del fills[row]
        self.track["fills"] = fills
        self._refresh_fill_list()

    def _move_fill(self, delta: int):
        row = self.list_fills.currentRow()
        if row < 0:
            return
        fills = self.track.get("fills", []) or []
        new_row = row + delta
        if new_row < 0 or new_row >= len(fills):
            return
        fills[row], fills[new_row] = fills[new_row], fills[row]
        self.track["fills"] = fills
        self._refresh_fill_list()
        self.list_fills.setCurrentRow(new_row)

    def _on_ok(self):
        name = self.ed_name.text().strip()
        if name:
            self.track["name"] = name
        self.accept()

import numpy as np
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QDialogButtonBox, QMessageBox, QLabel, QLineEdit
)
from PyQt5.QtCore import Qt


class EditWellLogTableDialog_old(QDialog):
    """
    Edit one continuous well log (depth, value) in a table.
    - two editable columns: Depth, Value
    - add/remove rows
    - sort by depth
    - filter (simple substring match on either column)
    """

    def __init__(self, parent, well_name: str, log_name: str, depth, data):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Log: {log_name} • {well_name}")
        self.resize(760, 560)

        self._well_name = well_name
        self._log_name = log_name

        depth = [] if depth is None else list(depth)
        data = [] if data is None else list(data)
        n = min(len(depth), len(data))

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit depth/value pairs. Use 'Sort by depth' before OK if you changed ordering.\n"
            "Rows with non-numeric values will be rejected on OK.",
            self
        ))

        # Filter row
        row_filter = QHBoxLayout()
        row_filter.addWidget(QLabel("Filter:", self))
        self.ed_filter = QLineEdit(self)
        self.ed_filter.setPlaceholderText("type to filter rows…")
        row_filter.addWidget(self.ed_filter, 1)

        self.btn_clear_filter = QPushButton("Clear", self)
        row_filter.addWidget(self.btn_clear_filter)
        layout.addLayout(row_filter)

        # Table
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Depth", "Value"])
        self.table.setRowCount(n)
        for i in range(n):
            self._set_cell(i, 0, depth[i])
            self._set_cell(i, 1, data[i])
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        # Buttons
        row_btns = QHBoxLayout()
        self.btn_add = QPushButton("Add row", self)
        self.btn_del = QPushButton("Delete selected", self)
        self.btn_sort = QPushButton("Sort by depth", self)
        row_btns.addWidget(self.btn_add)
        row_btns.addWidget(self.btn_del)
        row_btns.addStretch(1)
        row_btns.addWidget(self.btn_sort)
        layout.addLayout(row_btns)

        # OK/Cancel
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # connections
        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._delete_selected_rows)
        self.btn_sort.clicked.connect(self._sort_by_depth)
        self.ed_filter.textChanged.connect(self._apply_filter)
        self.btn_clear_filter.clicked.connect(lambda: self.ed_filter.setText(""))

        self._apply_filter()

        self._result_depth = None
        self._result_data = None

    def _set_cell(self, r: int, c: int, v):
        it = QTableWidgetItem("" if v is None else str(v))
        it.setFlags(it.flags() | Qt.ItemIsEditable)
        self.table.setItem(r, c, it)

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._set_cell(r, 0, "")
        self._set_cell(r, 1, "")
        self.table.setCurrentCell(r, 0)

    def _delete_selected_rows(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            self.table.removeRow(r)

    def _sort_by_depth(self):
        # Read all numeric rows
        rows = []
        for r in range(self.table.rowCount()):
            d_txt = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            v_txt = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()
            if not d_txt and not v_txt:
                continue
            try:
                d = float(d_txt.replace(",", "."))
                v = float(v_txt.replace(",", "."))
                rows.append((d, v))
            except Exception:
                # keep non-numeric rows at end unsorted
                rows.append((np.nan, np.nan))

        # Sort numeric first, preserve NaNs last
        rows_num = [(d, v) for d, v in rows if np.isfinite(d) and np.isfinite(v)]
        rows_nan = [(d, v) for d, v in rows if not (np.isfinite(d) and np.isfinite(v))]
        rows_num.sort(key=lambda t: t[0])
        rows_sorted = rows_num + rows_nan

        # Refill table
        self.table.setRowCount(len(rows_sorted))
        for i, (d, v) in enumerate(rows_sorted):
            self._set_cell(i, 0, "" if not np.isfinite(d) else d)
            self._set_cell(i, 1, "" if not np.isfinite(v) else v)

        self.table.resizeColumnsToContents()
        self._apply_filter()

    def _apply_filter(self):
        s = (self.ed_filter.text() or "").strip().lower()
        for r in range(self.table.rowCount()):
            if not s:
                self.table.setRowHidden(r, False)
                continue
            d = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").lower()
            v = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").lower()
            self.table.setRowHidden(r, (s not in d and s not in v))

    def _on_ok(self):
        depth = []
        data = []

        for r in range(self.table.rowCount()):
            # include hidden rows too: user can filter but still wants full dataset
            d_txt = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            v_txt = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()

            # allow skipping blank rows
            if not d_txt and not v_txt:
                continue

            try:
                d = float(d_txt.replace(",", "."))
                v = float(v_txt.replace(",", "."))
            except Exception:
                QMessageBox.warning(
                    self, "Invalid value",
                    f"Row {r+1} contains non-numeric Depth/Value:\n"
                    f"Depth='{d_txt}', Value='{v_txt}'"
                )
                return

            depth.append(d)
            data.append(v)

        if len(depth) == 0:
            res = QMessageBox.question(
                self, "Empty log",
                "This will result in an empty log. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if res != QMessageBox.Yes:
                return

        self._result_depth = depth
        self._result_data = data
        self.accept()

    def result_arrays(self):
        """Return (depth, data) as lists after OK, else (None, None)."""
        return self._result_depth, self._result_data




class EditWellLogTableDialog(QDialog):
    """
    Extended editor for one continuous well log (depth, value).

    Added features:
      - Basic stats (min/max/mean/count)
      - Replace blanks/NULLs with -999 (either depth, value, or both)
      - Replace a numeric value with another (e.g. -999 -> NaN like handling)
      - Paste from clipboard (2-column: depth,value) with delimiter auto-detect
      - Resample to uniform step (linear interpolation), optional depth range
    """

    COL_DEPTH = 0
    COL_VALUE = 1

    def __init__(self, parent, well_name: str, log_name: str, depth, data):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Log: {log_name} • {well_name}")
        self.resize(980, 680)

        self._well_name = well_name
        self._log_name = log_name

        depth = [] if depth is None else list(depth)
        data = [] if data is None else list(data)
        n = min(len(depth), len(data))

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Edit depth/value pairs. Hidden rows (filter) are still included on OK.\n"
            "Tips: Paste from clipboard, sort by depth, resample to step. Non-numeric rows are rejected on OK.",
            self
        ))

        # --- filter + stats row ---
        row_top = QHBoxLayout()
        row_top.addWidget(QLabel("Filter:", self))
        self.ed_filter = QLineEdit(self)
        self.ed_filter.setPlaceholderText("type to filter rows…")
        row_top.addWidget(self.ed_filter, 1)
        self.btn_clear_filter = QPushButton("Clear", self)
        row_top.addWidget(self.btn_clear_filter)

        self.lbl_stats = QLabel("", self)
        self.lbl_stats.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row_top.addWidget(self.lbl_stats, 0)

        layout.addLayout(row_top)

        # --- table ---
        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Depth", "Value"])
        self.table.setRowCount(n)
        for i in range(n):
            self._set_cell(i, self.COL_DEPTH, depth[i])
            self._set_cell(i, self.COL_VALUE, data[i])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        # --- action buttons row ---
        row_btns = QHBoxLayout()
        self.btn_add = QPushButton("Add row", self)
        self.btn_del = QPushButton("Delete selected", self)
        self.btn_sort = QPushButton("Sort by depth", self)
        self.btn_paste = QPushButton("Paste (Depth,Value)", self)

        row_btns.addWidget(self.btn_add)
        row_btns.addWidget(self.btn_del)
        row_btns.addWidget(self.btn_sort)
        row_btns.addWidget(self.btn_paste)
        row_btns.addStretch(1)
        layout.addLayout(row_btns)

        # --- tools area: Replace / Resample ---
        tools_row = QHBoxLayout()

        # Replace NULL/blanks
        grp_null = QGroupBox("NULL / blank handling", self)
        gnl = QVBoxLayout(grp_null)
        self.chk_blank_to_null = QCheckBox("Replace blanks/NULL with -999 (Value column)", self)
        self.chk_blank_to_null.setChecked(False)
        gnl.addWidget(self.chk_blank_to_null)

        self.chk_depth_blank_to_null = QCheckBox("Replace blanks/NULL with -999 (Depth column)", self)
        self.chk_depth_blank_to_null.setChecked(False)
        gnl.addWidget(self.chk_depth_blank_to_null)

        tools_row.addWidget(grp_null, 1)

        # Replace numeric
        grp_rep = QGroupBox("Replace numeric value", self)
        grl = QFormLayout(grp_rep)
        self.ed_rep_from = QLineEdit(self)
        self.ed_rep_from.setPlaceholderText("from (e.g. -999)")
        self.ed_rep_to = QLineEdit(self)
        self.ed_rep_to.setPlaceholderText("to (e.g. 0)")
        grl.addRow("Replace:", self.ed_rep_from)
        grl.addRow("With:", self.ed_rep_to)
        self.btn_apply_replace = QPushButton("Apply replace (Value)", self)
        grl.addRow(self.btn_apply_replace)
        tools_row.addWidget(grp_rep, 1)

        # Resample
        grp_rs = QGroupBox("Resample", self)
        rsl = QFormLayout(grp_rs)
        self.ed_step = QLineEdit(self)
        self.ed_step.setPlaceholderText("step (e.g. 0.1524)")
        self.ed_rs_top = QLineEdit(self)
        self.ed_rs_top.setPlaceholderText("optional top depth")
        self.ed_rs_base = QLineEdit(self)
        self.ed_rs_base.setPlaceholderText("optional base depth")
        rsl.addRow("Step:", self.ed_step)
        rsl.addRow("Top:", self.ed_rs_top)
        rsl.addRow("Base:", self.ed_rs_base)
        self.btn_resample = QPushButton("Resample (linear)", self)
        rsl.addRow(self.btn_resample)
        tools_row.addWidget(grp_rs, 1)

        layout.addLayout(tools_row)

        # --- OK/Cancel ---
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        # connections
        self.btn_add.clicked.connect(self._add_row)
        self.btn_del.clicked.connect(self._delete_selected_rows)
        self.btn_sort.clicked.connect(self._sort_by_depth)
        self.btn_paste.clicked.connect(self._paste_from_clipboard)

        self.ed_filter.textChanged.connect(self._apply_filter)
        self.btn_clear_filter.clicked.connect(lambda: self.ed_filter.setText(""))

        self.chk_blank_to_null.stateChanged.connect(self._apply_null_replacement_if_checked)
        self.chk_depth_blank_to_null.stateChanged.connect(self._apply_null_replacement_if_checked)

        self.btn_apply_replace.clicked.connect(self._apply_replace_value)
        self.btn_resample.clicked.connect(self._resample)

        self.table.itemChanged.connect(lambda *_: self._update_stats())

        self._result_depth = None
        self._result_data = None

        self._apply_filter()
        self._update_stats()

    # ---------------- table utils ----------------
    def _set_cell(self, r: int, c: int, v):
        it = QTableWidgetItem("" if v is None else str(v))
        it.setFlags(it.flags() | Qt.ItemIsEditable)
        self.table.setItem(r, c, it)

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._set_cell(r, self.COL_DEPTH, "")
        self._set_cell(r, self.COL_VALUE, "")
        self.table.setCurrentCell(r, 0)
        self._apply_filter()
        self._update_stats()

    def _delete_selected_rows(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            self.table.removeRow(r)
        self._apply_filter()
        self._update_stats()

    def _apply_filter(self):
        s = (self.ed_filter.text() or "").strip().lower()
        for r in range(self.table.rowCount()):
            if not s:
                self.table.setRowHidden(r, False)
                continue
            d = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").lower()
            v = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").lower()
            self.table.setRowHidden(r, (s not in d and s not in v))

    def _read_all_rows_numeric(self, allow_blank_rows=True):
        """
        Read all rows and return arrays (depth, value) as float, excluding fully blank rows.
        Raises ValueError for non-numeric content.
        """
        depth = []
        value = []
        for r in range(self.table.rowCount()):
            d_txt = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            v_txt = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()

            if allow_blank_rows and (not d_txt and not v_txt):
                continue

            d = float(d_txt.replace(",", "."))
            v = float(v_txt.replace(",", "."))
            depth.append(d)
            value.append(v)

        return np.asarray(depth, dtype=float), np.asarray(value, dtype=float)

    def _sort_by_depth(self):
        rows = []
        for r in range(self.table.rowCount()):
            d_txt = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            v_txt = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()
            if not d_txt and not v_txt:
                continue
            try:
                d = float(d_txt.replace(",", "."))
                v = float(v_txt.replace(",", "."))
                rows.append((d, v))
            except Exception:
                rows.append((np.nan, np.nan))

        rows_num = [(d, v) for d, v in rows if np.isfinite(d) and np.isfinite(v)]
        rows_nan = [(d, v) for d, v in rows if not (np.isfinite(d) and np.isfinite(v))]
        rows_num.sort(key=lambda t: t[0])
        rows_sorted = rows_num + rows_nan

        self.table.blockSignals(True)
        self.table.setRowCount(len(rows_sorted))
        for i, (d, v) in enumerate(rows_sorted):
            self._set_cell(i, 0, "" if not np.isfinite(d) else d)
            self._set_cell(i, 1, "" if not np.isfinite(v) else v)
        self.table.blockSignals(False)

        self.table.resizeColumnsToContents()
        self._apply_filter()
        self._update_stats()

    # ---------------- stats ----------------
    def _update_stats(self):
        # compute stats on numeric rows only
        vals = []
        depths = []
        for r in range(self.table.rowCount()):
            d_txt = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            v_txt = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()
            if not d_txt or not v_txt:
                continue
            try:
                d = float(d_txt.replace(",", "."))
                v = float(v_txt.replace(",", "."))
                depths.append(d)
                vals.append(v)
            except Exception:
                pass

        if not vals:
            self.lbl_stats.setText("count=0")
            return

        arr = np.asarray(vals, dtype=float)
        self.lbl_stats.setText(
            f"count={len(arr)}  min={np.nanmin(arr):.3g}  max={np.nanmax(arr):.3g}  mean={np.nanmean(arr):.3g}"
        )

    # ---------------- NULL replacement ----------------
    def _apply_null_replacement_if_checked(self):
        # apply to existing blanks/NULL tokens immediately
        null_tokens = {"null", "nan", "none", "nil", "na", "n/a", "-"}
        self.table.blockSignals(True)

        if self.chk_blank_to_null.isChecked():
            for r in range(self.table.rowCount()):
                it = self.table.item(r, self.COL_VALUE)
                txt = (it.text() if it else "").strip()
                if (not txt) or (txt.lower() in null_tokens):
                    self._set_cell(r, self.COL_VALUE, "-999")

        if self.chk_depth_blank_to_null.isChecked():
            for r in range(self.table.rowCount()):
                it = self.table.item(r, self.COL_DEPTH)
                txt = (it.text() if it else "").strip()
                if (not txt) or (txt.lower() in null_tokens):
                    self._set_cell(r, self.COL_DEPTH, "-999")

        self.table.blockSignals(False)
        self._update_stats()

    # ---------------- replace numeric ----------------
    def _apply_replace_value(self):
        frm = (self.ed_rep_from.text() or "").strip()
        to = (self.ed_rep_to.text() or "").strip()
        if not frm or not to:
            QMessageBox.information(self, "Replace", "Provide both 'from' and 'to' values.")
            return
        try:
            v_from = float(frm.replace(",", "."))
            v_to = float(to.replace(",", "."))
        except Exception:
            QMessageBox.warning(self, "Replace", "From/To must be numeric.")
            return

        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            it = self.table.item(r, self.COL_VALUE)
            if it is None:
                continue
            txt = it.text().strip()
            if not txt:
                continue
            try:
                v = float(txt.replace(",", "."))
            except Exception:
                continue
            if v == v_from:
                self._set_cell(r, self.COL_VALUE, str(v_to))
        self.table.blockSignals(False)
        self._update_stats()

    # ---------------- paste ----------------
    def _paste_from_clipboard(self):
        cb = self.parent().clipboard() if hasattr(self.parent(), "clipboard") else None
        if cb is None:
            from PyQt5.QtWidgets import QApplication
            cb = QApplication.clipboard()

        text = cb.text()
        if not text.strip():
            QMessageBox.information(self, "Paste", "Clipboard is empty.")
            return

        # Try to parse 2 columns with pandas, delimiter auto-detect
        try:
            # normalize decimal comma -> dot is ambiguous; keep as is for now, we convert later
            df = pd.read_csv(
                pd.compat.StringIO(text),
                sep=None,
                engine="python",
                header=None,
                comment="#"
            )
        except Exception:
            # fallback: whitespace split
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            rows = []
            for ln in lines:
                parts = ln.replace("\t", " ").split()
                if len(parts) >= 2:
                    rows.append(parts[:2])
            df = pd.DataFrame(rows)

        if df.shape[1] < 2:
            QMessageBox.warning(self, "Paste", "Need at least 2 columns: Depth and Value.")
            return

        depth_col = df.iloc[:, 0].astype(str).tolist()
        val_col = df.iloc[:, 1].astype(str).tolist()

        start_row = self.table.rowCount()
        self.table.blockSignals(True)
        self.table.setRowCount(start_row + len(depth_col))
        for i, (d, v) in enumerate(zip(depth_col, val_col)):
            self._set_cell(start_row + i, self.COL_DEPTH, d)
            self._set_cell(start_row + i, self.COL_VALUE, v)
        self.table.blockSignals(False)

        self._apply_filter()
        self._update_stats()

    # ---------------- resample ----------------
    def _resample(self):
        step_txt = (self.ed_step.text() or "").strip()
        if not step_txt:
            QMessageBox.information(self, "Resample", "Provide a step value.")
            return
        try:
            step = float(step_txt.replace(",", "."))
            if step <= 0:
                raise ValueError()
        except Exception:
            QMessageBox.warning(self, "Resample", "Step must be a positive number.")
            return

        # Read numeric arrays
        try:
            d, v = self._read_all_rows_numeric(allow_blank_rows=True)
        except Exception as e:
            QMessageBox.warning(self, "Resample", f"Cannot resample: non-numeric row exists.\n{e}")
            return

        if d.size < 2:
            QMessageBox.information(self, "Resample", "Need at least 2 samples to resample.")
            return

        # Sort by depth
        order = np.argsort(d)
        d = d[order]
        v = v[order]

        # Optional range
        top_txt = (self.ed_rs_top.text() or "").strip()
        base_txt = (self.ed_rs_base.text() or "").strip()
        top = d[0] if not top_txt else float(top_txt.replace(",", "."))
        base = d[-1] if not base_txt else float(base_txt.replace(",", "."))
        if base <= top:
            QMessageBox.warning(self, "Resample", "Base must be greater than Top.")
            return

        new_d = np.arange(top, base + 0.5 * step, step)
        new_v = np.interp(new_d, d, v)

        # Replace table content
        self.table.blockSignals(True)
        self.table.setRowCount(len(new_d))
        for i in range(len(new_d)):
            self._set_cell(i, self.COL_DEPTH, f"{new_d[i]:.6f}")
            self._set_cell(i, self.COL_VALUE, f"{new_v[i]:.6f}")
        self.table.blockSignals(False)

        self._apply_filter()
        self._update_stats()

    # ---------------- OK ----------------
    def _on_ok(self):
        # Apply blank->-999 if requested
        self._apply_null_replacement_if_checked()

        depth = []
        data = []

        for r in range(self.table.rowCount()):
            d_txt = (self.table.item(r, 0).text() if self.table.item(r, 0) else "").strip()
            v_txt = (self.table.item(r, 1).text() if self.table.item(r, 1) else "").strip()

            if not d_txt and not v_txt:
                continue

            try:
                d = float(d_txt.replace(",", "."))
                v = float(v_txt.replace(",", "."))
            except Exception:
                QMessageBox.warning(
                    self, "Invalid value",
                    f"Row {r+1} contains non-numeric Depth/Value:\n"
                    f"Depth='{d_txt}', Value='{v_txt}'"
                )
                return

            depth.append(d)
            data.append(v)

        if len(depth) == 0:
            res = QMessageBox.question(
                self, "Empty log",
                "This will result in an empty log. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if res != QMessageBox.Yes:
                return

        self._result_depth = depth
        self._result_data = data
        self.accept()

    def result_arrays(self):
        return self._result_depth, self._result_data