from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QMessageBox, QDockWidget, QWidget, QVBoxLayout, QTreeWidget,
    QTreeWidgetItem, QPushButton, QHBoxLayout, QSizePolicy, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem,QDialog, QInputDialog, QMenu)
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QPoint

import numpy as np

from PyQt5.QtGui import QStandardItemModel, QStandardItem

from pywellsection.Qt_Well_Widget import WellPanelWidget
from pywellsection.sample_data import create_dummy_data
from pywellsection.io_utils import export_project_to_json, load_project_from_json, load_petrel_wellheads
from pywellsection.io_utils import load_las_as_logs
from pywellsection.widgets import QTextEditLogger, QTextEditCommands
from pywellsection.console import QIPythonWidget
from pywellsection.trees import setup_well_widget_tree
from pywellsection.dialogs import AssignLasToWellDialog, NewTrackDialog
from pywellsection.dialogs import AddLogToTrackDialog
from pywellsection.dialogs import StratigraphyEditorDialog
from pywellsection.dialogs import LayoutSettingsDialog
from pywellsection.dialogs import LogDisplaySettingsDialog

import logging
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQTWellSection")
        self.resize(1200, 1000)

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
                               "track_width": self.track_width}

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

        # 👇 NEW: Import Petrel well heads
        act_import_petrel = QAction("Import Petrel well heads...", self)
        act_import_petrel.triggered.connect(self._file_import_petrel)
        file_menu.addAction(act_import_petrel)

        act_import_las = QAction("Import LAS logs...", self)
        act_import_las.triggered.connect(self._file_import_las)
        file_menu.addAction(act_import_las)

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

        # --- Help menu (unchanged) ---
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("About...", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

            # (keep any existing View items like “Select all wells” etc.)

    def _show_about(self):
        QMessageBox.information(
            self,
            "About",
            "Well Panel Demo\n\n"
            "Includes well log visualization, top picking, and stratigraphic editing."
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
            wells, tracks, stratigraphy, _ = load_project_from_json(path)
            self.panel.wells = wells
            self.panel.tracks = tracks
            #self.all_stratigraphy = None
            self.all_logs = []
            self.all_tracks = tracks

            self.all_wells = wells

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

            #self.all_stratigraphy = stratigraphy


            # populate well tree
            self._populate_well_tree()
            self._populate_well_tops_tree()
            self._populate_well_log_tree()
            self._populate_well_track_tree()


            # ✅ Trigger full redraw
            self.panel.update_panel(tracks, wells, stratigraphy)
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

            # --- log leaves (informational, not checkable) ---
            logs_dict = w.get("logs", {}) or {}
            if logs_dict:
                # optionally add a small header item, or go straight to leaves
                # header = QTreeWidgetItem(["Logs"])
                # header.setFlags(header.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                # well_item.addChild(header)
                # parent_for_logs = header

                parent_for_logs = well_item  # direct children of the well

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

        self.well_tree.blockSignals(False)
        self._rebuild_panel_from_tree()

    def _populate_well_tops_tree(self):
        """Rebuild the tree from self.all_wells, preserving selections if possible."""
        # Remember current selection by name
        prev_selected = set()
        root = self.well_tops_folder
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))

        self.well_tree.blockSignals(True)

        # remove all wells under the folder
        root.takeChildren()

        # add wells as children of "All wells"

        strat_list = list (self.all_stratigraphy)

        for strat_name in strat_list:
            strat_it = QTreeWidgetItem([strat_name])
            strat_it.setFlags(
                strat_it.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
            )
            strat_it.setData(0, Qt.UserRole, strat_name)


            # default: keep previous selection; else checked
            if not prev_selected:
                state = Qt.Checked
            else:
                state = Qt.Checked if strat_name in prev_selected else Qt.Unchecked
            strat_it.setCheckState(0, state)

            root.addChild(strat_it)


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

        if item  is self.well_tops_folder:
            self._rebuild_visible_tops_from_tree()
            return

        # Logs
        if item is self.well_logs_folder or p is self.well_tops_folder:
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
        root = self.well_tops_folder
        visible = set()
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

    def _action_add_empty_track(self):
        # Suggest next unique name
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

        # --- case 2: log leaves under "Tracks" folder ---
        # tracks folder: track_root_item
        if parent is not None and parent.parent() is self.track_root_item:
            # parent is the track item, 'item' is the log name
            log_name = item.text(0)
            if not log_name:
                return

            menu = QMenu(self)
            act_edit = menu.addAction(f"Edit display settings for '{log_name}'...")
            chosen = menu.exec_(global_pos)
            if chosen == act_edit:
                self._edit_log_display_settings(log_name)
            return

        # other nodes (wells, tops folders, etc.) → no context menu for logs

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

        color = base_cfg.get("color", "black")
        xscale = base_cfg.get("xscale", "linear")
        direction = base_cfg.get("direction", "normal")
        xlim = base_cfg.get("xlim", None)

        # 2) Open dialog
        dlg = LogDisplaySettingsDialog(self, log_name, color, xscale, direction, xlim)
        if dlg.exec_() != QDialog.Accepted:
            return

        new_color, new_xscale, new_direction, new_xlim = dlg.values()

        # 3) Apply updated settings to ALL track configs with this log
        for track in self.all_tracks:
            for log_cfg in track.get("logs", []):
                if log_cfg.get("log") != log_name:
                    continue
                if new_color is not None:
                    log_cfg["color"] = new_color
                else:
                    log_cfg.pop("color", None)

                log_cfg["xscale"] = new_xscale or "linear"
                log_cfg["direction"] = new_direction or "normal"

                if new_xlim is not None:
                    log_cfg["xlim"] = new_xlim
                else:
                    log_cfg.pop("xlim", None)  # auto scale

        # 4) Sync with panel and redraw
        if hasattr(self, "panel"):
            self.panel.tracks = self.all_tracks
            self.panel.draw_panel()

        # 5) (Optional) refresh track/log trees for consistency
        #self._populate_well_track_tree()
        #self._populate_log_tree()