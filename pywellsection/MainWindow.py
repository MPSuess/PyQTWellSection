from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QMessageBox, QDockWidget, QWidget, QVBoxLayout, QTreeWidget,
    QTreeWidgetItem, QPushButton, QHBoxLayout, QSizePolicy, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem,QDialog, QInputDialog, QMenu)
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QPoint

import numpy as np
import csv

from PyQt5.QtGui import QStandardItemModel, QStandardItem

from pywellsection.Qt_Well_Widget import WellPanelWidget
from pywellsection.sample_data import create_dummy_data
from pywellsection.io_utils import export_project_to_json, load_project_from_json, load_petrel_wellheads
from pywellsection.io_utils import load_las_as_logs, export_discrete_logs_to_csv, import_discrete_logs_from_csv


from pywellsection.widgets import QTextEditLogger, QTextEditCommands
from pywellsection.console import QIPythonWidget
from pywellsection.trees import setup_well_widget_tree
from pywellsection.dialogs import AssignLasToWellDialog, NewTrackDialog
from pywellsection.dialogs import AddLogToTrackDialog
from pywellsection.dialogs import StratigraphyEditorDialog
from pywellsection.dialogs import LayoutSettingsDialog
from pywellsection.dialogs import LogDisplaySettingsDialog
from pywellsection.dialogs import AllTopsTableDialog
from pywellsection.dialogs import NewWellDialog
from pywellsection.dialogs import AllWellsSettingsDialog
from pywellsection.dialogs import SingleWellSettingsDialog
from pywellsection.dialogs import NewDiscreteTrackDialog
from pywellsection.dialogs import DiscreteColorEditorDialog
from pywellsection.dialogs import ImportFaciesIntervalsDialog
from pywellsection.dialogs import LithofaciesDisplaySettingsDialog
from pywellsection.dialogs import LithofaciesTableDialog
from pywellsection.dialogs import LoadCoreBitmapDialog
from pywellsection.dialogs import HelpDialog

from pathlib import Path
from collections import OrderedDict


import logging

# This file is part of the `pywellsection` project and licensed under
# EUPL 1.2
# M. Peter Süss 2025

logging.getLogger("ipykernel").setLevel("CRITICAL")
logging.getLogger("traitlets").setLevel("CRITICAL")
logging.getLogger("root").setLevel("CRITICAL")
logging.getLogger("parso").setLevel("CRITICAL")
logging.getLogger("parso.cache").setLevel("CRITICAL")

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQTWellSection")
        self.resize(1200, 1000)
        self.redraw_requested = False

        # The Windows
        ### central widget ----
        wells, tracks, stratigraphy = create_dummy_data()

        self.all_wells = wells
        self.all_stratigraphy = stratigraphy
        self.all_logs = None
        self.all_tracks = tracks

        self.well_gap_factor = 3.0
        self.track_gap_factor = 1.0
        self.track_width = 1.0


        self.panel_settings = {"well_gap_factor": self.well_gap_factor, "track_gap_factor": self.track_gap_factor,
                               "track_width": self.track_width, "redraw_requested": self.redraw_requested}

        self.panel = WellPanelWidget(wells, tracks, stratigraphy, self.panel_settings)
        self.dock_panel = QDockWidget("Well Panel", self)
        self.dock_panel.setWidget(self.panel)
        self.addDockWidget(Qt.TopDockWidgetArea, self.dock_panel)


        # ipython console
        self.console = QIPythonWidget(self)
        self.dock_console = QDockWidget("Console", self)
        self.dock_console.setWidget(self.console)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_console)

        # commands
        self.textedit_commands = QTextEditCommands(self)
        self.dock_commands = QDockWidget("Commands", self)
        self.dock_commands.setWidget(self.textedit_commands)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_commands)

        # log panel
        self.textbox_logger = QTextEditLogger(self)
        formatter = logging.Formatter("%(name)-20s - %(levelname)-8s - %(message)s")
        self.textbox_logger.setFormatter(formatter)
        logging.getLogger().addHandler(self.textbox_logger)
        logging.getLogger().setLevel("DEBUG")
        self.dock_logger = QDockWidget("Log", self)
        self.dock_logger.setWidget(self.textbox_logger.widget)

        setup_well_widget_tree(self)

        self.redraw_requested=True

        self.panel_settings = {"well_gap_factor": self.well_gap_factor, "track_gap_factor": self.track_gap_factor,
                               "track_width": self.track_width, "redraw_requested": self.redraw_requested}

        self.panel.update_panel(tracks, wells, stratigraphy, self.panel_settings)
        self.panel.draw_panel()

        # ---- build menu bar ----
        self._create_menubar()

    def _create_menubar(self):
        menubar = self.menuBar()

        # --- File menu ---
        file_menu = menubar.addMenu("&File")

        act_open = QAction("Open project...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._project_file_open)
        file_menu.addAction(act_open)

        act_save = QAction("Save project...", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._project_file_save)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        import_menu = file_menu.addMenu("&Import")

        act_import_tops = QAction("Import tops from CSV...", self)
        act_import_tops.triggered.connect(self._action_import_tops_csv)
        import_menu.addAction(act_import_tops)

        # 👇 NEW: Import Petrel well heads
        act_import_petrel = QAction("Import Petrel well heads...", self)
        act_import_petrel.triggered.connect(self._file_import_petrel)
        import_menu.addAction(act_import_petrel)

        act_import_las = QAction("Import LAS logs...", self)
        act_import_las.triggered.connect(self._file_import_las)
        import_menu.addAction(act_import_las)

        act_import_discrete = QAction("Discrete logs from CSV…", self)
        act_import_discrete.triggered.connect(self._action_import_discrete_logs_csv)
        import_menu.addAction(act_import_discrete)

        act_import_facies = QAction("Facies intervals from CSV…", self)
        act_import_facies.triggered.connect(self._action_import_facies_intervals_csv)
        import_menu.addAction(act_import_facies)


        export_menu = file_menu.addMenu("&Export")
        act_export_discrete_logs = QAction("Export discrete logs as csv...", self)
        act_export_discrete_logs.triggered.connect(self._action_export_discrete_logs_csv)
        export_menu.addAction(act_export_discrete_logs)

        file_menu.addSeparator()

        act_exit = QAction("Exit", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # --- View menu: select/deselect all wells ---
        view_menu = menubar.addMenu("&View")
        act_sel_all = QAction("Select all wells", self)
        act_sel_all.triggered.connect(self._select_all_wells)
        view_menu.addAction(act_sel_all)

        act_sel_none = QAction("Select no wells", self)
        act_sel_none.triggered.connect(self._select_no_wells)
        view_menu.addAction(act_sel_none)

        act_layout = QAction("Layout settings...", self)
        act_layout.triggered.connect(self._action_layout_settings)
        view_menu.addAction(act_layout)

        tools_menu = menubar.addMenu("&Tools")

        act_add_log_to_track = QAction("Add log to track...", self)
        act_add_log_to_track.triggered.connect(self._action_add_log_to_track)
        tools_menu.addAction(act_add_log_to_track)

        act_add_track = QAction("Add empty track...", self)
        act_add_track.triggered.connect(self._action_add_empty_track)
        tools_menu.addAction(act_add_track)

        act_delete_track = QAction("Delete track...", self)
        act_delete_track.triggered.connect(self._action_delete_track)
        tools_menu.addAction(act_delete_track)

        act_edit_strat = QAction("Edit stratigraphy...", self)
        act_edit_strat.triggered.connect(self._action_edit_stratigraphy)
        tools_menu.addAction(act_edit_strat)

        act_edit_all_tops = QAction("Edit all tops in table...", self)
        act_edit_all_tops.triggered.connect(self._action_edit_all_tops)
        tools_menu.addAction(act_edit_all_tops)

        act_edit_litho = QAction("Edit lithofacies table...", self)
        act_edit_litho.triggered.connect(self._action_edit_lithofacies_table)
        tools_menu.addAction(act_edit_litho)


        # --- Help menu (unchanged) ---
        help_menu = menubar.addMenu("&Help")

        act_help = QAction("Import formats…", self)
        act_help.triggered.connect(self._action_show_help)
        help_menu.addAction(act_help)

        help_menu.addSeparator()

        act_about = QAction("About…", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

            # (keep any existing View items like “Select all wells” etc.)

    def _show_about(self):
        QMessageBox.information(
            self,
            "About",
            (
                "Well Section & Log Panel Viewer\n"
                "Author: M. Peter Süss\n\n"
                "This software provides tools for visualizing and editing well correlations, "
                "well tops, logs, and related geological data.\n\n"
                "\n\n"
                "Licensed under the European Union Public Licence (EUPL) v1.2.\n"
                "See: https://joinup.ec.europa.eu/collection/eupl/eupl-text-12\n\n"
                "© M. Peter Süss"
            )
        )

    # ------------------------------------------------
    # FILE HANDLERS (placeholders for now)
    # ------------------------------------------------

    def _project_file_open(self):
        """Load wells/tracks data from a JSON file (example)."""
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            wells, tracks, raw_strat, _ = load_project_from_json(path)
            self.panel.wells = wells
            self.panel.tracks = tracks
            #self.all_stratigraphy = None
            self.all_logs = []
            self.all_tracks = tracks
            self.all_wells = wells

            # ---- normalize stratigraphy ----
            # Ensure it's an ordered mapping of name -> dict(meta)
            if isinstance(raw_strat, dict):
                strat_items = raw_strat.items()
            elif isinstance(raw_strat, list):
                # in case older format is a list of (name, meta) pairs
                strat_items = raw_strat
            else:
                strat_items = []

            stratigraphy = OrderedDict()
            for name, meta in strat_items:
                if meta is None or not isinstance(meta, dict):
                    meta = {}

                # keep existing fields
                level = meta.get("level", "")
                color = meta.get("color", "#000fff")
                hatch = meta.get("hatch", "-")
                role = meta.get("role", "stratigraphy")  # 👈 default if missing

                stratigraphy[name] = {
                    "level": level,
                    "color": color,
                    "hatch": hatch,
                    "role": role,
                }

#            self.stratigraphy = stratigraphy

            #stratigraphy=self.all_stratigraphy

            if not self.all_stratigraphy:
                self.all_stratigraphy = stratigraphy
            else:
                self.all_stratigraphy.update(stratigraphy)

            for well in wells:
                logs = well.get("logs")
                if logs:
                    for log in logs:
                        if not self.all_logs:
                            self.all_logs = logs.keys()
                        if log in self.all_logs:
                            continue
                        else:
                            print("appending log:" , log)
                            self.all_logs = self.all_logs|{log}
                else:
                    print("No logs found")

            for well in wells:
                disc_logs = well.get("discrete_logs", {})
                for log_name, d in list(disc_logs.items()):
                    if "top_depths" in d and "bottom_depths" in d:
                        tops = np.array(d["top_depths"], dtype=float)
                        values = np.array(d["values"], dtype=object)
                        # convert to depth/value representation (top sample)
                        disc_logs[log_name] = {
                            "depth": tops.tolist(),
                            "values": values.tolist(),
                        }

            #self.all_stratigraphy = stratigraphy

            self.redraw_requested = False
            self.panel_settings["redraw_requested"] = False
            self.panel.update_panel(tracks, wells, stratigraphy, self.panel_settings)

            # populate well tree
            self._populate_well_tree()
            self._populate_well_tops_tree()
            self._populate_well_log_tree()
            self._populate_well_track_tree()


            # ✅ Trigger full redraw
            self.redraw_requested = True
            self.panel_settings["redraw_requested"] = True
            self.panel.update_panel(tracks, wells, stratigraphy, self.panel_settings)
            self.panel.draw_panel()

        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))

    def _project_file_save(self):
        """Save wells/tracks data to a JSON file (example)."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save project",
            "",
            "Well project (*.json);;All files (*.*)"
        )
        if not path:
            return

        path = Path(path)

        try:
            wells = getattr(self.panel, "wells", [])
            #print ("Saving",wells[0])

            for well in wells:
                print("Saving",well["name"], "")

            tracks = getattr(self.panel, "tracks", [])
            stratigraphy = getattr(self.panel, "stratigraphy", None)
            extra_metadata = {
                "app": "pywellsection",
                "version": "0.1.0",
            }

            project = export_project_to_json(path, wells, tracks, stratigraphy, extra_metadata)



            print("Saving",project["wells"][0]["name"], "done")



        except Exception as e:
            QMessageBox.critical(self, "Save error", f"Failed to save project:\n{e}")

    def _file_import_petrel(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Petrel well heads",
            "",
            "Petrel well head (*.txt *.dat *.whd);;All files (*.*)"
        )
        if not path:
            return
        try:
            wells = load_petrel_wellheads(path)
            self.all_wells = wells  # master list
            # Panel will show whatever is checked (defaults to all)
            self._populate_well_tree()
            self._populate_well_tops_tree()
            self._populate_well_log_tree()
            self._populate_well_track_tree()

        except Exception as e:
            QMessageBox.critical(self, "Import error", f"Failed to import:\n{e}")

    def _file_import_las(self):
        """Import LAS file and assign logs to an existing or new well."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import LAS file",
            "",
            "LAS files (*.las);;All files (*.*)"
        )
        if not path:
            return

        try:
            las_well_info, logs = load_las_as_logs(path)
        except Exception as e:
            QMessageBox.critical(self, "LAS import error", f"Failed to read LAS:\n{e}")
            return

        # Dialog to choose target well or create new one
        dlg = AssignLasToWellDialog(self, self.all_wells, las_well_info)
        if dlg.exec_() != QDialog.Accepted:
            return

        mode, idx, new_name, new_uwi = dlg.result_assignment()

        if mode == "existing":
            # Attach logs to existing well
            if idx < 0 or idx >= len(self.all_wells):
                QMessageBox.critical(self, "LAS import", "Invalid well index selected.")
                return

            target_well = self.all_wells[idx]
            if "logs" not in target_well:
                target_well["logs"] = {}
            # merge/override logs
            for mnem, log_def in logs.items():
                target_well["logs"][mnem] = log_def

        else:
            # Create new well from LAS info
            wi = las_well_info.copy()
            if new_name:
                wi["name"] = new_name
            if new_uwi:
                wi["uwi"] = new_uwi

            # ensure required keys
            wi.setdefault("x", None)
            wi.setdefault("y", None)
            wi.setdefault("reference_type", "KB")
            wi.setdefault("reference_depth", 0.0)
            wi.setdefault("total_depth", max(
                (float(np.nanmax(v["depth"])) for v in logs.values()),
                default=0.0,
            ))
            wi.setdefault("tops", {})
            wi["logs"] = logs

            self.all_wells.append(wi)

            if self.all_logs is None:
                 self.all_logs = logs
            else:
                 self.all_logs = self.all_logs|logs # this operator merges the two dictionaries


        # Update panel + tree views
        self.panel.set_wells(self.all_wells)

        # refresh tree sections
        self._populate_well_tree()
        self._populate_well_log_tree()
        self._populate_well_track_tree()

        QMessageBox.information(self, "LAS import", "LAS logs imported successfully.")

    def _build_well_tree_dock(self):
        """Left dock: tree with checkboxes to toggle wells."""
        self.well_dock = QDockWidget("Wells", self)
        self.well_dock.setObjectName("WellDock")
        self.well_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        self.well_tree = QTreeWidget(self.well_dock)
        self.well_tree.setHeaderHidden(True)
        self.well_tree.itemChanged.connect(self._on_well_tree_item_changed)

         # 👇 create the folder item once
        self.well_root_item = QTreeWidgetItem(["All wells"])
        # tristate so checking it checks/unchecks children
        self.well_root_item.setFlags(
            self.well_root_item.flags()
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsTristate
            | Qt.ItemIsSelectable
            | Qt.ItemIsEnabled
        )
        self.well_root_item.setCheckState(0, Qt.Checked)

        self.well_tree.addTopLevelItem(self.well_root_item)

        # Context menu
        #self.well_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        #self.well_tree.customContextMenuRequested.connect(self._on_tree_context_menu)
        #self.well_tree.customContextMenuRequested.connect(self.test_connect)

        self._populate_well_tree()  # initial fill

        self.well_dock.setWidget(self.well_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.well_dock)

    def _populate_well_tree(self):
        """Rebuild wells subtree from self.all_wells, with log leaves under each well."""
        prev_selected = set()
        root = self.well_root_item
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))

        self.well_tree.blockSignals(True)
        root.takeChildren()

        for w in self.all_wells:
            well_name = w.get("name") or "UNKNOWN"

            # --- well item (checkable) ---
            well_item = QTreeWidgetItem([well_name])
            well_item.setFlags(
                well_item.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
            )
            well_item.setData(0, Qt.UserRole, well_name)
            state = Qt.Checked if (not prev_selected or well_name in prev_selected) else Qt.Unchecked
            well_item.setCheckState(0, state)
            root.addChild(well_item)

            # --- subfolders ---
            cont_folder = QTreeWidgetItem(well_item, ["continuous"])
            #lith_folder = QTreeWidgetItem(well_item, ["lithofacies"])
            disc_folder = QTreeWidgetItem(well_item, ["discrete"])

            bmp_folder = QTreeWidgetItem(well_item, ["bitmap"])

            cont_folder.setExpanded(True)
            #lith_folder.setExpanded(True)
            disc_folder.setExpanded(True)
            bmp_folder.setExpanded(False)

            cont_folder.setData(0, Qt.UserRole, ("folder", "continuous", well_name))
            #lith_folder.setData(0, Qt.UserRole, ("folder", "lithofacies", well_name))
            disc_folder.setData(0, Qt.UserRole, ("folder", "discrete", well_name))
            bmp_folder.setData(0, Qt.UserRole,("folder","bitmaps", well_name))


            # --- log leaves (informational, not checkable) ---
            logs_dict = w.get("logs", {}) or {}
            if logs_dict:
                # optionally add a small header item, or go straight to leaves
                # header = QTreeWidgetItem(["Logs"])
                # header.setFlags(header.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                # well_item.addChild(header)
                # parent_for_logs = header

                parent_for_logs = cont_folder  # direct children of the well

                for log_name in sorted(logs_dict.keys()):
                    log_item = QTreeWidgetItem([log_name])
                    # selectable but not user-checkable
                    log_item.setFlags(
                        log_item.flags()
                        | Qt.ItemIsSelectable
                        | Qt.ItemIsEnabled
                    )
                    # store mnemonic for possible future actions
                    log_item.setData(0, Qt.UserRole, log_name)
                    parent_for_logs.addChild(log_item)

            # --- lithofacies ---
            # We store as a single dataset item (you can expand this later if you want per-interval children)
            facies_intervals = w.get("facies_intervals", []) or []
            if facies_intervals:
                txt = f"Lithofacies (n={len(facies_intervals)})"
            else:
                txt = "intervals (n=0)"
            lith_item = QTreeWidgetItem(disc_folder, [txt])
            lith_item.setData(0, Qt.UserRole, ("Lithofacies", well_name, "intervals"))

            # --- discrete logs ---
            dlogs = (w.get("discrete_logs") or {})
            for dlog_name in sorted(dlogs.keys(), key=str):
                dlog_item = QTreeWidgetItem(disc_folder, [dlog_name])
                dlog_item.setData(0, Qt.UserRole, ("Discrete", well_name, dlog_name))

            # --- bitmaps ---
            blogs = (w.get("bitmaps", None) or {})
            if blogs is not None:
                for blog_name in sorted(blogs.keys(), key=str):
                    blog_item = QTreeWidgetItem(bmp_folder,[blog_name])
                    blog_item.setData(0, Qt.UserRole,("Bitmap",well_name,blog_name))

        self.well_tree.blockSignals(False)
        self._rebuild_panel_from_tree()

    def _populate_well_tops_tree(self):
        """Rebuild the tree from self.all_wells, preserving selections if possible."""
        # Remember current selection by name
        strat_prev_selected = set()
        strat_root = self.stratigraphy_root
        for i in range(strat_root.childCount()):
            it = strat_root.child(i)
            if it.checkState(0) == Qt.Checked:
                strat_prev_selected.add(it.data(0, Qt.UserRole))
        self.well_tree.blockSignals(True)

        # remove all children under the folder
        strat_root.takeChildren()

        faults_prev_selected = set()
        faults_root = self.faults_root
        for i in range(faults_root.childCount()):
            it = faults_root.child(i)
            if it.checkState(0) == Qt.Checked:
                faults_prev_selected.add(it.data(0, Qt.UserRole))
        self.well_tree.blockSignals(True)

        # remove all children under the folder
        faults_root.takeChildren()

        other_prev_selected = set()
        other_root = self.faults_root
        for i in range(other_root.childCount()):
            it = other_root.child(i)
            if it.checkState(0) == Qt.Checked:
                other_prev_selected.add(it.data(0, Qt.UserRole))
        self.well_tree.blockSignals(True)

        # remove all children under the folder
        faults_root.takeChildren()


        # add wells as children of "All wells"

        strat_list = list (self.all_stratigraphy)

        for strat_name in strat_list:
            if self.all_stratigraphy[strat_name]['role']=='stratigraphy':
                strat_it = QTreeWidgetItem([strat_name])
                strat_it.setFlags(
                    strat_it.flags()
                    | Qt.ItemIsUserCheckable
                    | Qt.ItemIsSelectable
                    | Qt.ItemIsEnabled
                )
                strat_it.setData(0, Qt.UserRole, strat_name)

                # default: keep previous selection; else checked
                if not strat_prev_selected:
                    state = Qt.Checked
                else:
                    state = Qt.Checked if strat_name in strat_prev_selected else Qt.Unchecked
                strat_it.setCheckState(0, state)
                strat_root.addChild(strat_it)
            elif self.all_stratigraphy[strat_name]['role']=='fault':
                fault_it = QTreeWidgetItem([strat_name])
                fault_it.setFlags(
                    fault_it.flags()
                    | Qt.ItemIsUserCheckable
                    | Qt.ItemIsSelectable
                    | Qt.ItemIsEnabled
                )
                fault_it.setData(0, Qt.UserRole, strat_name)

                if not faults_prev_selected:
                    state = Qt.Checked
                else:
                    state = Qt.Checked if strat_name in faults_prev_selected else Qt.Unchecked
                fault_it.setCheckState(0, state)
                faults_root.addChild(fault_it)
            elif self.all_stratigraphy[strat_name]['role']=='other':
                other_it = QTreeWidgetItem([strat_name])
                other_it.setFlags(
                    other_it.flags()
                    | Qt.ItemIsUserCheckable
                    | Qt.ItemIsSelectable
                    | Qt.ItemIsEnabled
                )
                other_it.setData(0, Qt.UserRole, strat_name)

                if not other_prev_selected:
                    state = Qt.Checked
                else:
                    state = Qt.Checked if strat_name in other_prev_selected else Qt.Unchecked
                other_it.setCheckState(0, state)
                other_root.addChild(other_it)


        self.well_tree.blockSignals(False)

        # Apply current selection to panel
        #self._rebuild_panel_from_tree()

    def _populate_well_log_tree(self):
        """Rebuild the tree from self.all_wells, preserving selections if possible."""
        # Remember current selection by name
        prev_selected = set()
        root = self.well_logs_folder
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))

        self.well_tree.blockSignals(True)

        # remove all wells under the folder
        root.takeChildren()

        # add wells as children of "All wells"

        log_names = set()
        # for track in self.all_tracks:
        #     for log_cgf in track.get("logs",[]):
        #         name = log_cgf.get("log")
        #         if name:
        #             log_names.add(name)

        if self.all_logs is None:
            return

        for log in self.all_logs:
            name = log
            if name:
                log_names.add(name)

        for name in sorted(log_names):
            it = QTreeWidgetItem([name])
            it.setFlags(
                it.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
            )
            it.setData(0, Qt.UserRole, name)

            state = Qt.Checked if (not prev_selected or name in prev_selected) else Qt.Unchecked
            it.setCheckState(0, state)
            root.addChild(it)
        self.well_tree.blockSignals(False)
        self._rebuild_visible_logs_from_tree()

    def _populate_well_track_tree(self):
        """Rebuild tracks subtree from self.tracks, showing track→log assignment."""
        if self.all_tracks is None:
            return
        else:
            tracks = self.all_tracks

        root = self.track_root_item

        # remember previous checked tracks

        prev_selected = set()
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))

        self.well_tree.blockSignals(True)
        root.takeChildren()

        for track in self.all_tracks:
            track_name = track.get("name") or "Track"
            track_item = QTreeWidgetItem([track_name])
            # make the track item checkable
            track_item.setFlags(
                track_item.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
            )
            track_item.setData(0, Qt.UserRole, track_name)

            state = (
                Qt.Checked
                if (not prev_selected or track_name in prev_selected)
                else Qt.Unchecked
            )
            track_item.setCheckState(0, state)

            # add logs as children (structural only)
            for log_cfg in track.get("logs", []):
                log_name = log_cfg.get("log")
                if not log_name:
                    continue
                log_item = QTreeWidgetItem([log_name])
                log_item.setFlags(
                    log_item.flags()
                    | Qt.ItemIsSelectable
                    | Qt.ItemIsEnabled
                )
                track_item.addChild(log_item)

            root.addChild(track_item)

        self.well_tree.blockSignals(False)
        self._rebuild_visible_tracks_from_tree()

    def _on_well_tree_item_changed(self, item: QTreeWidgetItem, _col: int):
        """Recompute displayed wells whenever a checkbox changes."""

        p = item.parent()
        if item  is self.well_root_item or p is self.well_root_item:
            self._rebuild_panel_from_tree()
            return

        if item  is self.stratigraphy_root or p is self.stratigraphy_root:
            self._rebuild_visible_tops_from_tree()
            return

        if item  is self.faults_root or p is self.faults_root:
            self._rebuild_visible_tops_from_tree()
            return

        if item  is self.other_root or p is self.other_root:
            self._rebuild_visible_tops_from_tree()
            return

        # Logs
        if item is self.well_logs_folder:
            self._rebuild_visible_logs_from_tree()
            return

        # Tracks
        if item is self.track_root_item or p is self.track_root_item:
            self._rebuild_visible_tracks_from_tree()
            return

    def _select_all_wells(self):
        self.well_tree.blockSignals(True)
        root = self.well_tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.Checked)
        self.well_tree.blockSignals(False)
        self._rebuild_panel_from_tree()

    def _select_no_wells(self):
        self.well_tree.blockSignals(True)
        root = self.well_tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.Unchecked)
        self.well_tree.blockSignals(False)
        self._rebuild_panel_from_tree()

    def _rebuild_panel_from_tree(self):
        """Collect checked wells (by name) and send to panel."""
        checked_names = set()
        root = self.well_root_item
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                checked_names.add(it.data(0, Qt.UserRole))

        # Map names → well dicts (keep original order)
        selected = [w for w in self.all_wells if (w.get("name") in checked_names)]
        # If none selected, you can either show none or all; here: show none
        self.panel.set_wells(selected)

    def _rebuild_visible_tops_from_tree(self):
        root = self.stratigraphy_root
        visible = set()
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                nm = it.data(0, Qt.UserRole)
                if nm:
                    visible.add(nm)
        root = self.faults_root
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                nm = it.data(0, Qt.UserRole)
                if nm:
                    visible.add(nm)

        root = self.other_root
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                nm = it.data(0, Qt.UserRole)
                if nm:
                    visible.add(nm)

        self.panel.set_visible_tops(visible if visible else None)
        self.panel.set_visible_tops(visible)

    def _rebuild_visible_logs_from_tree(self):
        """Collect checked logs and inform the panel."""
        root = self.well_logs_folder
        visible = set()
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                nm = it.data(0, Qt.UserRole)
                if nm:
                    visible.add(nm)

        # If everything is checked, you can pass None to mean "no filter"
        if visible and len(visible) == root.childCount():
            visible_set = None
        else:
            visible_set = visible if visible else set()

        self.panel.set_visible_logs(visible_set)

    def _rebuild_visible_tracks_from_tree(self):
        """Collect checked tracks and inform the panel."""
        root = self.track_root_item
        visible = set()
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                nm = it.data(0, Qt.UserRole)
                if nm:
                    visible.add(nm)

        # If all tracks are checked, we can pass None (= no filter)
        if visible and len(visible) == root.childCount():
            visible_set = None
        else:
            visible_set = visible if visible else None

        self.panel.set_visible_tracks(visible_set)

    def add_log_to_track(self, track_name: str, log_name: str,
                         label: str = None, color: str = "black",
                         xscale: str = "linear", direction: str = "normal",
                         xlim=None):
        """
        Add a new log config to a track by name and refresh panel & trees.

        - track_name: name of the track (track['name'])
        - log_name:   log mnemonic as used in well['logs'][log_name]
        - label:      label shown on top (defaults to log_name)
        - color:      matplotlib color string
        - xscale:     'linear' or 'log'
        - direction:  'normal' or 'reverse' (reverse = flip x-axis)
        - xlim:       optional (min, max) tuple for x-axis
        """
        if label is None:
            label = log_name

        # 1) find the track
        track = None
        for t in self.all_tracks:
            if t.get("name") == track_name:
                track = t
                break

        if track is None:
            raise ValueError(f"Track '{track_name}' not found.")

        # 2) ensure 'logs' list exists
        if "logs" not in track or track["logs"] is None:
            track["logs"] = []

        # 3) build log config
        log_cfg = {
            "log": log_name,
            "label": label,
            "color": color,
            "xscale": xscale,
            "direction": direction,
        }
        if xlim is not None:
            log_cfg["xlim"] = tuple(xlim)

        # 4) append to track
        track["logs"].append(log_cfg)

        # 5) propagate to panel & tree widgets
        #if self.panel.tracks is not None:
        #    self.panel.tracks = self.panel.tracks
        #    print(self.panel.tracks)# keep panel in sync
        #self.panel.draw_panel()

        # refresh log+track trees so the new log shows up
        self._populate_well_log_tree()
        self._populate_well_track_tree()

    def _action_add_log_to_track(self):
        """Show dialog to add a log to a track, then apply."""
        dlg = AddLogToTrackDialog(self, self.all_tracks, self.all_wells)
        if dlg.exec_() != QDialog.Accepted:
            return

        track_name, log_name, label, color = dlg.get_values()
        try:
            self.add_log_to_track(
                track_name=track_name,
                log_name=log_name,
                label=label,
                color=color,
            )
        except Exception as e:
            QMessageBox.critical(self, "Add log to track", f"Failed:\n{e}")

    def add_empty_track(self, track_name: str | None = None):
        """
        Add a new empty track (no logs, no discrete track) to the project and refresh UI.

        If track_name is None, generate a unique name like 'Track 1', 'Track 2', ...
        """
        # Ensure we have a list of existing names

        if not hasattr(self, "all_tracks") or self.all_tracks is None:
            if self.tracks is None:
                existing_names = set()
            else:
    #            existing_names = {t.get("name", "") for t in self.tracks}
                existing_names = {t.get("name", "") for t in getattr(self, "tracks", [])}
        else: existing_names = {t.get("name", "") for t in self.all_tracks}

        if not track_name:
            # Generate "Track N" that isn't used yet
            base = "Track"
            i = 1
            while f"{base} {i}" in existing_names:
                i += 1
            track_name = f"{base} {i}"

        # Build the empty track definition
        new_track = {
            "name": track_name,
            "logs": [],  # no continuous logs yet
            "discrete": None,  # no discrete track yet
        }

        # Append to tracks
        if not hasattr(self, "all_tracks") or self.all_tracks is None:
            self.all_tracks = []
        self.all_tracks.append(new_track)
        #self.all_tracks.append(new_track)


        # Keep panel in sync
        #self.panel.tracks = self.tracks
        #self.panel.draw_panel()

        # Refresh tree sections that depend on tracks
        self._populate_well_track_tree()
        self._populate_well_log_tree()  # stays the same; just ensures consistency

    def delete_track(self, track_name: str):
        """
        Delete a track (by its name) from the project and refresh UI.
        Does NOT delete any log data from wells, only the track definition.
        """
        if not hasattr(self, "all_tracks") or self.all_tracks is None:
            raise ValueError("No tracks defined in the project.")

        # find track index
        idx = None
        for i, t in enumerate(self.all_tracks):
            if t.get("name") == track_name:
                idx = i
                break

        if idx is None:
            raise ValueError(f"Track '{track_name}' not found.")

        # remove from tracks list
        del self.all_tracks[idx]

        # keep panel in sync
        if hasattr(self, "panel"):
            self.panel.tracks = self.all_tracks

            # clean up visible_tracks if needed
            vt = getattr(self.panel, "visible_tracks", None)
            if vt is not None:
                vt = set(vt)
                if track_name in vt:
                    vt.remove(track_name)
                self.panel.visible_tracks = vt or None

            self.panel.draw_panel()

        # refresh tree sections
        self._populate_well_track_tree()  # tracks folder
        #self._populate_well_log_tree()  # logs folder still valid, but refresh for consistency

    def _action_show_help(self):
        dlg = HelpDialog(self, html=self.get_import_help_html())
        dlg.exec_()

    def get_import_help_html(self) -> str:

        with open('pywellsection/PyQtHelp.html','r') as file:
            data = file.read()
        return data





    def _action_add_empty_track(self):
        if not hasattr(self, "all_tracks") or self.all_tracks is None:
            self.all_tracks = []

        existing_names = [t.get("name", "") for t in self.all_tracks]

        # collect discrete log names from wells (optional quality-of-life)
        disc_names = set()
        if getattr(self, "all_wells", None):
            for w in self.all_wells:
                for nm in (w.get("discrete_logs") or {}).keys():
                    disc_names.add(nm)

        dlg = NewTrackDialog(
            self,
            existing_track_names=existing_names,
            available_discrete_logs=disc_names,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        new_track = dlg.result_track()
        if not new_track:
            return

        self.all_tracks.append(new_track)

        self._populate_well_track_tree()

    def _action_add_empty_track_old(self):
        # Suggest next unique name

        suggested = ""

        existing_names = {t.get("name", "") for t in getattr(self, "tracks", [])}
        base = "Track"
        i = 1
        while f"{base} {i}" in existing_names:
            i += 1
        suggested = f"{base} {i}"

        dlg = NewTrackDialog(self, suggested_name=suggested)
        if dlg.exec_() != QDialog.Accepted:
            return

        name = dlg.track_name() or suggested
        try:
            self.add_empty_track(name)
        except Exception as e:
            QMessageBox.critical(self, "Add empty track", f"Failed to add track:\n{e}")

    def _action_delete_track(self):
        """Ask user which track to delete, then call delete_track."""
        if not getattr(self, "all_tracks", None):
            QMessageBox.information(self, "Delete track", "There are no tracks to delete.")
            return

        track_names = [t.get("name", f"Track {i + 1}") for i, t in enumerate(self.all_tracks)]

        name, ok = QInputDialog.getItem(
            self,
            "Delete track",
            "Select track to delete:",
            track_names,
            0,
            False,
        )
        if not ok or not name:
            return

        try:
            self.delete_track(name)
        except Exception as e:
            QMessageBox.critical(self, "Delete track", f"Failed to delete track:\n{e}")

    def _action_edit_stratigraphy(self):
        """Open table dialog to edit/add stratigraphy for the project."""
        # Make sure we have a stratigraphy dict
        strat = getattr(self, "all_stratigraphy", None)
        if strat is None:
            strat = {}

        dlg = StratigraphyEditorDialog(self, strat)
        if dlg.exec_() != QDialog.Accepted:
            return

        new_strat = dlg.result_stratigraphy()
        if new_strat is None:
            return

        # 1) update project-level stratigraphy
        self.stratigraphy = new_strat
        self.all_stratigraphy = new_strat

        # 2) push into panel
        if hasattr(self, "panel"):
            self.panel.stratigraphy = new_strat

            # flattening uses strat key order:
            # if you have any cached flatten state, you might want to reset:
            if hasattr(self.panel, "_flatten_depths"):
                self.panel._flatten_depths = None

            self.panel.draw_panel()

        # 3) refresh "Stratigraphic tops" folder in tree
#        if hasattr(self, "_populate_top_tree"):
        self._populate_well_tops_tree()

    def _action_layout_settings(self):
        """Open dialog to adjust distance between wells and track width."""
        if not hasattr(self, "panel"):
            return

        dlg = LayoutSettingsDialog(
            self,
            well_gap_factor=self.panel.well_gap_factor,
            track_width=self.panel.track_width,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        gap, tw = dlg.values()
        self.set_layout_params(gap, tw)

    def _action_edit_all_tops(self):
        """Open table dialog to edit/add/delete tops of all wells."""
        if not getattr(self, "all_wells", None):
            QMessageBox.information(self, "Edit tops", "No wells in project.")
            return

        strat = getattr(self, "stratigraphy", None)

        dlg = AllTopsTableDialog(self, self.all_wells, stratigraphy=strat)
        if dlg.exec_() != QDialog.Accepted:
            return

        result = dlg.result_changes()
        if not result:
            return

        updates = result["updates"]  # (well_name, top_name) -> depth
        additions = result["additions"]  # (well_name, top_name) -> depth
        deletions = result["deletions"]  # set of (well_name, top_name)

        # Map well_name -> well dict (assuming names are unique)
        wells_by_name = {}
        for w in self.all_wells:
            nm = w.get("name")
            if nm:
                wells_by_name[nm] = w

        # --- apply deletions ---
        for (well_name, top_name) in deletions:
            well = wells_by_name.get(well_name)
            if not well:
                continue
            tops = well.get("tops", {})
            if top_name in tops:
                del tops[top_name]

        # --- apply updates (depth changes for existing tops) ---
        for (well_name, top_name), depth in updates.items():
            well = wells_by_name.get(well_name)
            if not well:
                QMessageBox.warning(
                    self,
                    "Edit tops",
                    f"Well '{well_name}' not found in project. Skipping update for top '{top_name}'."
                )
                continue

            tops = well.setdefault("tops", {})
            old_val = tops.get(top_name)
            if isinstance(old_val, dict):
                new_val = dict(old_val)
                new_val["depth"] = depth
                tops[top_name] = new_val
            else:
                tops[top_name] = depth

        # --- apply additions (new tops) ---
        for (well_name, top_name), depth in additions.items():
            well = wells_by_name.get(well_name)
            if not well:
                QMessageBox.warning(
                    self,
                    "Edit tops",
                    f"Well '{well_name}' not found in project. Cannot add top '{top_name}'."
                )
                continue

            tops = well.setdefault("tops", {})
            if top_name in tops:
                # Should not happen if dialog prevented duplicates, but guard anyway
                QMessageBox.warning(
                    self,
                    "Edit tops",
                    f"Top '{top_name}' already exists in well '{well_name}'. Skipping addition."
                )
                continue

            # store as simple depth; if you use richer top dicts, adapt this
            tops[top_name] = depth

        # --- redraw panel with updated tops ---
        if hasattr(self, "panel"):
            self.panel.wells = self.all_wells
            self.panel.draw_panel()

        # --- refresh tops tree ---
        if hasattr(self, "_populate_top_tree"):
            self._populate_top_tree()

    def _action_add_new_well(self):
        """Open dialog to add a new well to the project."""
        existing_names = [w.get("name", "") for w in getattr(self, "all_wells", [])]

        dlg = NewWellDialog(self, existing_names=existing_names)
        if dlg.exec_() != QDialog.Accepted:
            return

        new_well = dlg.result_well()
        if new_well is None:
            return

        # Append to project well list
        if not hasattr(self, "all_wells") or self.all_wells is None:
            self.all_wells = []
        self.all_wells.append(new_well)

        # Update panel wells (keep tracks & stratigraphy)
        if hasattr(self, "panel"):
            self.panel.wells = self.all_wells
            # you might want to reset flattening or keep it; here we keep zoom/flatten
            self.panel.draw_panel()

        # Refresh wells tree (and maybe other trees)
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _action_add_discrete_track(self):
        """Create a new discrete track and append it to the project."""
        if not hasattr(self, "tracks") or self.tracks is None:
            self.tracks = []

        # collect all discrete log names currently present in wells
        available_disc_logs = set()
        if getattr(self, "all_wells", None):
            for w in self.all_wells:
                dlogs = w.get("discrete_logs", {}) or {}
                for lname in dlogs.keys():
                    available_disc_logs.add(lname)

        existing_track_names = [t.get("name", "") for t in self.tracks]

        dlg = NewDiscreteTrackDialog(
            self,
            available_discrete_logs=available_disc_logs,
            existing_track_names=existing_track_names,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        new_track = dlg.result_track()
        if not new_track:
            return

        # append track
        self.tracks.append(new_track)

        # push to panel
        if hasattr(self, "panel"):
            self.panel.tracks = self.tracks
            self.panel.draw_panel()

        # refresh track tree
        if hasattr(self, "_populate_track_tree"):
            self._populate_track_tree()

    def _action_edit_discrete_colors_for_track(self, track_name: str):
        """
        Edit the color_map and default_color for a discrete track
        identified by its track name.
        """
        if not hasattr(self, "all_tracks") or not self.all_tracks:
            QMessageBox.information(self, "Discrete colors", "No tracks in project.")
            return

        # find track
        track = None
        for t in self.all_tracks:
            if t.get("name") == track_name:
                track = t
                break

        if track is None:
            QMessageBox.warning(
                self,
                "Discrete colors",
                f"Track '{track_name}' not found."
            )
            return

        disc_cfg = track.get("discrete")
        if not disc_cfg:
            QMessageBox.information(
                self,
                "Discrete colors",
                f"Track '{track_name}' is not a discrete track."
            )
            return

        log_name = disc_cfg.get("log")
        color_map = disc_cfg.get("color_map", {}) or {}
        default_color = disc_cfg.get("default_color", "#dddddd")
        missing_code = disc_cfg.get("missing", "-999")

        # collect values from wells for this discrete log
        available_values = set()
        if getattr(self, "all_wells", None):
            for w in self.all_wells:
                disc_logs = w.get("discrete_logs", {}) or {}
                dlog = disc_logs.get(log_name)
                if not dlog:
                    continue
                vals = dlog.get("values", []) or []
                for v in vals:
                    sv = str(v).strip()
                    if sv == str(missing_code):
                        continue
                    if sv == "":
                        continue
                    available_values.add(sv)

        dlg = DiscreteColorEditorDialog(
            self,
            log_name=log_name,
            color_map=color_map,
            default_color=default_color,
            available_values=available_values,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        new_map, new_default = dlg.result_colors()
        if new_map is None:
            return

        disc_cfg["color_map"] = new_map
        disc_cfg["default_color"] = new_default

        # redraw panel
        if hasattr(self, "panel"):
            self.panel.tracks = self.all_tracks
            self.panel.draw_panel()

    def _action_edit_all_wells(self):
        """Open dialog to edit all well header settings."""
        if not getattr(self, "all_wells", None):
            QMessageBox.information(self, "Well settings", "No wells in project.")
            return

        dlg = AllWellsSettingsDialog(self, self.all_wells)
        if dlg.exec_() != QDialog.Accepted:
            return

        headers = dlg.result_headers()
        if not headers:
            return

        # Apply back to self.all_wells, preserving tops/logs/discrete_logs
        for i, hdr in enumerate(headers):
            if i >= len(self.all_wells):
                break
            w = self.all_wells[i]
            w["name"] = hdr["name"]
            w["uwi"] = hdr["uwi"]
            w["x"] = hdr["x"]
            w["y"] = hdr["y"]
            w["reference_type"] = hdr["reference_type"]
            w["reference_depth"] = hdr["reference_depth"]
            w["total_depth"] = hdr["total_depth"]

        # push into panel
        if hasattr(self, "panel"):
            self.panel.wells = self.all_wells
            # optional: keep current zoom; if you want to reset, uncomment:
            # self.panel._current_depth_window = None
            # self.panel._flatten_depths = None
            self.panel.draw_panel()

        # refresh tree views that show wells
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _action_edit_single_well_by_index(self, well_index: int):
        """Open dialog to edit a single well's settings."""
        if not getattr(self, "all_wells", None):
            QMessageBox.information(self, "Well settings", "No wells in project.")
            return

        if well_index < 0 or well_index >= len(self.all_wells):
            QMessageBox.warning(self, "Well settings", "Invalid well index.")
            return

        well = self.all_wells[well_index]
        existing_names = [w.get("name", "") for w in self.all_wells]

        dlg = SingleWellSettingsDialog(self, well, existing_names=existing_names)
        if dlg.exec_() != QDialog.Accepted:
            return

        hdr = dlg.result_header()
        if not hdr:
            return

        # apply header changes
        well["name"] = hdr["name"]
        well["uwi"] = hdr["uwi"]
        well["x"] = hdr["x"]
        well["y"] = hdr["y"]
        well["reference_type"] = hdr["reference_type"]
        well["reference_depth"] = hdr["reference_depth"]
        well["total_depth"] = hdr["total_depth"]

        # update panel
        if hasattr(self, "panel"):
            self.panel.wells = self.all_wells
            # optional: keep zoom/flatten; if you want to reset, uncomment:
            # self.panel._current_depth_window = None
            # self.panel._flatten_depths = None
            self.panel.draw_panel()

        # refresh trees (names may have changed)
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()
        if hasattr(self, "_populate_top_tree"):
            self._populate_top_tree() or parent is self.well_root_item

    def _action_edit_single_well_by_name(self, well_name: str):
        """Edit a single well, identified by its name from the tree item."""
        if not getattr(self, "all_wells", None):
            QMessageBox.information(self, "Well settings", "No wells in project.")
            return

        # find index by name
        well_index = None
        for i, w in enumerate(self.all_wells):
            if w.get("name") == well_name:
                well_index = i
                break

        if well_index is None:
            QMessageBox.warning(
                self,
                "Well settings",
                f"Well '{well_name}' not found in project."
            )
            return

        well = self.all_wells[well_index]
        existing_names = [w.get("name", "") for w in self.all_wells]

        dlg = SingleWellSettingsDialog(self, well, existing_names=existing_names)
        if dlg.exec_() != QDialog.Accepted:
            return

        hdr = dlg.result_header()
        if not hdr:
            return

        well["name"] = hdr["name"]
        well["uwi"] = hdr["uwi"]
        well["x"] = hdr["x"]
        well["y"] = hdr["y"]
        well["reference_type"] = hdr["reference_type"]
        well["reference_depth"] = hdr["reference_depth"]
        well["total_depth"] = hdr["total_depth"]

        if hasattr(self, "panel"):
            self.panel.wells = self.all_wells
            self.panel.draw_panel()

        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()
        if hasattr(self, "_populate_top_tree"):
            self._populate_top_tree()

    def _action_export_discrete_logs_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Discrete Logs",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )
        if not path:
            return

        # Call your actual export function
        export_discrete_logs_to_csv(self,path)

    def _action_import_discrete_logs_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import discrete logs from CSV",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )
        if not path:
            return

        import_discrete_logs_from_csv(self,path)

    def _action_edit_lithofacies_settings_for_track(self, track_name: str):
        """
        Open dialog to edit lithofacies display parameters for a track
        identified by its track name (track['name']).
        """
        if not hasattr(self, "all_tracks") or not self.all_tracks:
            QMessageBox.information(self, "Lithofacies settings", "No tracks in project.")
            return

        # find track by name
        track = None
        for t in self.all_tracks:
            if t.get("name") == track_name:
                track = t
                break

        if track is None:
            QMessageBox.warning(
                self,
                "Lithofacies settings",
                f"Track '{track_name}' not found."
            )
            return

        facies_cfg = track.get("config")
        if facies_cfg is None:
            QMessageBox.information(
                self,
                "Lithofacies settings",
                f"Track '{track_name}' has no facies configuration."
            )
            return

        # current parameters or defaults
        hardness_scale = facies_cfg.get("hardness_scale", 1.0)
        spline_cfg = facies_cfg.get("spline", {}) or {}
        spline_smooth = spline_cfg.get("smooth", 0.5)
        spline_samples = spline_cfg.get("num_samples", 200)

        dlg = LithofaciesDisplaySettingsDialog(
            self,
            hardness_scale=hardness_scale,
            spline_smooth=spline_smooth,
            spline_num_samples=spline_samples,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        params = dlg.result_params()
        if not params:
            return

        # store back into track config
        facies_cfg["hardness_scale"] = params["hardness_scale"]
        facies_cfg["spline"] = params["spline"]

        # redraw panel so changes take effect
        if hasattr(self, "panel"):
            self.panel.tracks = self.all_tracks
            self.panel.draw_panel()

    def _action_edit_lithofacies_table(self):
        """Open table dialog to edit lithofacies intervals for all wells."""
        if not getattr(self, "all_wells", None):
            QMessageBox.information(self, "Lithofacies", "No wells in project.")
            return

        dlg = LithofaciesTableDialog(self, self.all_wells)
        if dlg.exec_() != QDialog.Accepted:
            return

        by_well = dlg.result_by_well()
        if not by_well:
            return

        # map wells by name
        wells_by_name = {w.get("name"): w for w in self.all_wells if w.get("name")}
        unknown = []

        # clear existing facies_intervals
        for w in self.all_wells:
            w["facies_intervals"] = []

        for wname, intervals in by_well.items():
            well = wells_by_name.get(wname)
            if well is None:
                unknown.append(wname)
                continue
            well["facies_intervals"] = list(intervals)

        # redraw panel
        if hasattr(self, "panel"):
            self.panel.wells = self.all_wells
            self.panel.draw_panel()

        if unknown:
            QMessageBox.warning(
                self,
                "Lithofacies",
                "Some intervals refer to unknown wells:\n  "
                + ", ".join(sorted(set(unknown)))
            )

    from PyQt5.QtWidgets import QMessageBox
    import os

    def _ensure_bitmap_track_exists(self):
        """
        Ensure there is at least one bitmap track in self.tracks.
        The bitmap track references a per-well bitmap by key.
        """
        if not hasattr(self, "tracks") or self.tracks is None:
            self.tracks = []

        for t in self.tracks:
            if "bitmap" in t:
                return  # already exists

        # Create a default bitmap track
        self.tracks.append({
            "name": "Core",
            "type": "bitmap",
            "bitmap": {
                "key": "core",  # per-well bitmap key
                "label": "Core",
                "alpha": 1.0,
                "cmap": None,
                "interpolation": "nearest",
                "flip_vertical": False,
            }
        })

    def _action_load_core_bitmap_to_well(self, default_well_name=None):
        """
        Open dialog and attach core bitmap to selected well:
          well["bitmaps"][key] = {path, top_depth, base_depth, ...}
        """

        import os

        if not getattr(self, "all_wells", None):
            QMessageBox.information(self, "Load core bitmap", "No wells in project.")
            return

        well_names = [w.get("name") for w in self.all_wells if w.get("name")]
        if not well_names:
            QMessageBox.information(self, "Load core bitmap", "No named wells available.")
            return

        dlg = LoadCoreBitmapDialog(self, well_names, default_well=default_well_name)
        if dlg.exec_() != QDialog.Accepted:
            return

        res = dlg.result()
        if not res:
            return

        # find well
        target = None
        for w in self.all_wells:
            if w.get("name") == res["well_name"]:
                target = w
                break
        if target is None:
            QMessageBox.warning(self, "Load core bitmap", f"Well '{res['well_name']}' not found.")
            return

        if not os.path.exists(res["path"]):
            QMessageBox.warning(self, "Load core bitmap", "Image file does not exist.")
            return

        # attach to well
        bitmaps = target.setdefault("bitmaps", {})
        bitmaps[res["key"]] = {
            "path": res["path"],
            "top_depth": res["top_depth"],
            "base_depth": res["base_depth"],
            "track": res["track"],
            # "alpha": res["alpha"],
            # "cmap": res["cmap"],
            # "interpolation": res["interpolation"],
            # "flip_vertical": res["flip_vertical"],
        }

        # ensure we have a bitmap track to display it
#        self._ensure_bitmap_track_exists()

        # push into panel & redraw
        # if hasattr(self, "panel"):
        #     self.panel.wells = self.all_wells
        #     self.panel.tracks = self.tracks
        #     self.panel.draw_panel()

        # refresh tree (if you show bitmaps there)
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _parse_lithotrend(self, litho_str: str, trend_str: str):
        """
        Parse 'LithoTrend' field like:
          'SS, cu'  -> lithology='SS', trend='cu'
          'M, fu'   -> lithology='M',  trend='fu'
          'SS'      -> lithology='SS', trend='constant'
        """

        lithology = litho_str if litho_str else ""
        trend_raw = trend_str if len(trend_str) > 1 else ""

        tr = trend_raw.lower()
        if tr == "cu":
            trend = "cu"  # coarsening upward
        elif tr == "fu":
            trend = "fu"  # fining upward
        else:
            trend = "constant"
        return lithology, trend

    def _action_import_facies_intervals_csv(self):
        """
        Open a CSV with columns:
            Well, ID, LithoTrend, Environment, Rel_Top, Rel_Base

        Parse LithoTrend into (Lithology, Trend) and attach intervals
        to each well as well['facies_intervals'] = [ ... ].
        """
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import facies intervals from CSV",
            "",
            "CSV files (*.csv);;All files (*.*)"
        )
        if not path:
            return

        # --- read CSV ---
        try:
            with open(path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            QMessageBox.critical(self, "Import facies intervals", f"Failed to read file:\n{e}")
            return

        if not rows:
            QMessageBox.information(self, "Import facies intervals", "No data rows found in CSV.")
            return

        required_cols = {"Well", "ID", "Litho", "Trend", "Environment", "Rel_Top", "Rel_Base"}
        missing = required_cols - set(rows[0].keys())
        if missing:
            QMessageBox.warning(
                self,
                "Import facies intervals",
                "Missing required columns in CSV:\n  " + ", ".join(sorted(missing))
            )
            return

        # --- parse rows ---
        intervals = []
        skipped = 0
        for r in rows:
            well_name = (r.get("Well") or "").strip()
            id_txt = (r.get("ID") or "").strip()
            lt_txt = (r.get("Litho") or "").strip()
            trd_txt = (r.get("Trend") or "").strip()
            env_txt = (r.get("Environment") or "").strip()
            top_txt = (r.get("Rel_Top") or "").strip()
            base_txt = (r.get("Rel_Base") or "").strip()

            if not well_name or not id_txt:
                skipped += 1
                continue

            try:
                _id = int(id_txt)
            except ValueError:
                skipped += 1
                continue

            try:
                rel_top = float(top_txt.replace(",", ".")) if top_txt else None
                rel_base = float(base_txt.replace(",", ".")) if base_txt else None
            except ValueError:
                skipped += 1
                continue

            lithology, trend = self._parse_lithotrend(lt_txt,trd_txt)

            intervals.append({
                "well": well_name,
                "id": _id,
                "litho_trend": lt_txt,
                "lithology": lithology,
                "trend": trend,  # "cu", "fu", or "constant"
                "environment": env_txt,
                "rel_top": rel_top,
                "rel_base": rel_base,
            })

        if not intervals:
            QMessageBox.information(
                self,
                "Import facies intervals",
                f"No valid rows found. Skipped: {skipped}"
            )
            return

        # --- preview dialog ---
        dlg = ImportFaciesIntervalsDialog(self, intervals)
        if dlg.exec_() != QDialog.Accepted:
            return

        imported = dlg.result_intervals()
        if not imported:
            return

        # --- attach intervals to wells by name ---
        if not getattr(self, "all_wells", None):
            QMessageBox.warning(
                self,
                "Import facies intervals",
                "No wells in project; cannot attach facies intervals."
            )
            return

        wells_by_name = {w.get("name"): w for w in self.all_wells if w.get("name")}
        unknown_wells = set()

        # clear or merge? here: replace per well
        for w in self.all_wells:
            w.setdefault("facies_intervals", [])

        # group by well
        by_well = {}
        for iv in imported:
            wnm = iv["well"]
            by_well.setdefault(wnm, []).append(iv)

        for wname, intervals_for_well in by_well.items():
            well = wells_by_name.get(wname)
            if well is None:
                unknown_wells.add(wname)
                continue
            # sort by rel_top descending if they are relative from top=1->0,
            # or ascending depending on your convention – here we just keep input order
            well["facies_intervals"] = list(intervals_for_well)

        msg_lines = [
            f"Imported {len(imported)} facies intervals.",
            f"Skipped rows: {skipped}",
        ]
        if unknown_wells:
            msg_lines.append(
                "\nUnknown wells (not found in project):\n  "
                + ", ".join(sorted(unknown_wells))
            )

        QMessageBox.information(
            self,
            "Import facies intervals",
            "\n".join(msg_lines)
        )

    def set_layout_params(self, well_gap_factor: float, track_width: float):
        """Update panel layout (gap between wells and track width) and redraw."""
        self.well_gap_factor = max(0.1, float(well_gap_factor))
        self.track_width = max(0.1, float(track_width))
        self.panel_settings = {"well_gap_factor": self.well_gap_factor, "track_gap_factor": self.track_gap_factor,
                               "track_width": self.track_width}
        self.panel.set_panel_settings(self.panel_settings)
        self.panel.draw_panel()

    def test_connect(self, pos):
        return True

    from PyQt5.QtWidgets import QMessageBox

    def _edit_log_display_settings(self, log_name: str):
        """
        Open dialog to edit display settings for log 'log_name' and apply
        to all track configs that use this log.
        """
        # 1) Find existing settings from the first matching track/log
        base_cfg = None
        for track in self.all_tracks:
            for log_cfg in track.get("logs", []):
                if log_cfg.get("log") == log_name:
                    base_cfg = log_cfg
                    break
            if base_cfg is not None:
                break

        if base_cfg is None:
            QMessageBox.information(
                self,
                "Log display",
                f"No track display settings found for log '{log_name}'."
            )
            return

        dlg = LogDisplaySettingsDialog(self, log_name, base_cfg)
        if dlg.exec_() == QDialog.Accepted:
            new_cfg = dlg.result_config()
            if new_cfg:
                # store back into the track configuration
                base_cfg.update(new_cfg)

                # redraw
                self.panel.draw_panel()


        # color = base_cfg.get("color", "black")
        # xscale = base_cfg.get("xscale", "linear")
        # direction = base_cfg.get("direction", "normal")
        # xlim = base_cfg.get("xlim", None)
        #
        # # 2) Open dialog
        # dlg = LogDisplaySettingsDialog(self, log_name, color, xscale, direction, xlim)
        # if dlg.exec_() != QDialog.Accepted:
        #     return
        #
        # new_color, new_xscale, new_direction, new_xlim = dlg.values()
        #
        # 3) Apply updated settings to ALL track configs with this log
        for track in self.all_tracks:
            for log_cfg in track.get("logs", []):
                if log_cfg.get("log") != log_name:
                    continue
                else:
                    log_cfg=base_cfg

        #         if new_color is not None:
        #             log_cfg["color"] = new_color
        #         else:
        #             log_cfg.pop("color", None)
        #
        #         log_cfg["xscale"] = new_xscale or "linear"
        #         log_cfg["direction"] = new_direction or "normal"
        #
        #         if new_xlim is not None:
        #             log_cfg["xlim"] = new_xlim
        #         else:
        #             log_cfg.pop("xlim", None)  # auto scale
        #
        # # 4) Sync with panel and redraw
        # if hasattr(self, "panel"):
        #     self.panel.tracks = self.all_tracks
        #     self.panel.draw_panel()



    def _load_tops_from_csv(self, path: str):
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
            # self.panel._current_depth_window = None
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

    def _action_import_tops_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import tops from CSV",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not path:
            return

        self._load_tops_from_csv(path)

    def _move_well(self, well_name: str, direction: int):
        """
        Move a well left/right in panel order.

        direction:
            -1 → move left
            +1 → move right
        """
        wells = self.all_wells
        names = [w.get("name") for w in wells]

        if well_name not in names:
            return

        idx = names.index(well_name)
        new_idx = idx + direction

        if new_idx < 0 or new_idx >= len(wells):
            return  # cannot move further

        wells[idx], wells[new_idx] = wells[new_idx], wells[idx]

        # redraw + rebuild tree so order stays in sync
        self._populate_well_tree()
        self.panel.draw_panel()

    def _on_tree_context_menu(self, pos):
        """
        Show a context menu for logs in the tree:
          - logs under the 'Logs' folder
          - logs under each track in the 'Tracks' folder
        """
        item = self.well_tree.itemAt(pos)
        if item is None:
            return

        global_pos = self.well_tree.viewport().mapToGlobal(pos)
        parent = item.parent()

        # --- Wells folder or well items: show "Add new well..." ---
        if item is self.well_root_item:
            menu = QMenu(self)

            act_add_well = menu.addAction("Add new well...")
            act_edit_all_wells = menu.addAction("Edit all well settings ...")

            chosen = menu.exec_(global_pos)

            if chosen == act_add_well:
                self._action_add_new_well()
            elif chosen == act_edit_all_wells:
                self._action_edit_all_wells()
            return


        if parent is self.well_root_item:
            menu = QMenu(self)

            well_name = item.text(0)
            act_edit_well = menu.addAction(f"Edit well '{well_name}'...")
            act_left = menu.addAction(f"Move well left '{well_name}'...")
            act_right = menu.addAction(f"Move well right '{well_name}'...")
            act_load_bitmap = menu.addAction(f"Load bitmap '{well_name}'...")
            chosen = menu.exec_(global_pos)
            well_index = item.data(0, Qt.UserRole)
            if well_index is None:
                return
            if chosen == act_edit_well:
                self._action_edit_single_well_by_name(well_name)
            elif chosen == act_left:
                self._move_well(well_name, -1)
            elif chosen == act_right:
                self._move_well(well_name, +1)
            if chosen == act_load_bitmap:
                self._action_load_core_bitmap_to_well(default_well_name = well_name)

        # --- case 1: logs under "Logs" folder ---
        if parent is self.well_logs_folder:
            log_name = item.data(0, Qt.UserRole) or item.text(0)
            if not log_name:
                return

            menu = QMenu(self)
            act_edit = menu.addAction(f"Edit display settings for '{log_name}'...")
            chosen = menu.exec_(global_pos)
            if chosen == act_edit:
                self._edit_log_display_settings(log_name)
            return

        if item is self.well_tops_folder:
            menu = QMenu(self)

            act_edit_stratigraphy = menu.addAction("Edit well tops ...")
            chosen = menu.exec_(global_pos)

            if chosen == act_edit_stratigraphy:
                self._action_edit_stratigraphy()
            return


        if item is self.track_root_item:
            track_name = item.text(0)

            if not track_name:
                return

            menu = QMenu(self)

            act_add_track = menu.addAction("Add new track...")
            act_add_disc_track = menu.addAction("Add new discrete track...")
            chosen = menu.exec_(global_pos)

            if chosen == act_add_track:
                self._action_add_empty_track()
            elif chosen == act_add_disc_track:
                self._action_add_discrete_track()
            return


        # --- case 2: log leaves under "Tracks" folder ---
        # tracks folder: track_root_item
        if parent is self.track_root_item:
            # parent is the track item, 'item' is the log name
            track_name = item.text(0)
            if not track_name:
                return

            menu = QMenu(self)
            act_edit = menu.addAction(f"Edit display settings for '{track_name}'...")
            act_add_log = menu.addAction(f"Add new log to track ...")
            act_delete_track = menu.addAction(f"Delete Track '{track_name}'...")
            act_edit_disc_colors = menu.addAction(f"Edit discrete track colors '{track_name}'...")
            act_edit_lithofacies_settings = menu.addAction("Edit lithofacies track settings ...")
            chosen = menu.exec_(global_pos)
            if chosen == act_edit:
                self._edit_log_display_settings(track_name)
            elif chosen == act_add_log:
                self._action_add_log_to_track()
            elif chosen == act_delete_track:
                self._action_delete_track()
            elif chosen == act_edit_disc_colors:
                self._action_edit_discrete_colors_for_track(track_name)
            elif chosen == act_edit_lithofacies_settings:
                self._action_edit_lithofacies_settings_for_track(track_name)
            return

        # other nodes (wells, tops folders, etc.) → no context menu for logs
