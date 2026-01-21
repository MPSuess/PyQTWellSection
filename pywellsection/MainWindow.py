### PyQTWell ... an experimental well section viewer and editor ... .
### Provides basic functionality to load wells and compose well sections with a user-friendly interface
### You like to improve the code? just join the developers team :-).
### This program is licensed according to EUPL1.2
### M. Peter Süss, University of Tuebingen, Copyright 2025, 2026
### v 12.04
from os import removedirs

### TODO: reformulate the code to be more object oriented ... .
# Move all well functions into a separate class.
# Move all track functions into a separate class.
# Move all stratigraphy functions into a separate class.
# Move all log functions into a separate class. etc ... .

from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QMessageBox, QDockWidget, QWidget, QVBoxLayout, QTreeWidget,
    QTreeWidgetItem, QPushButton, QHBoxLayout, QSizePolicy, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem, QDialog, QInputDialog, QMenu)
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QPoint, QEvent, QByteArray

import base64
import numpy as np
import csv


import json
import shutil
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from pywellsection.sample_data import Wells # The new class for wells

from pywellsection.pws_project import PWSProject


from PyQt5.QtGui import QStandardItemModel, QStandardItem
from matplotlib.pyplot import vlines

from pywellsection.Qt_Well_Widget import WellPanelWidget, WellPanelDock
from pywellsection.Qt_Map_Widget import MapDockWindow, MapPanelWidget

from pywellsection.sample_data import create_dummy_data
from pywellsection.io_utils import export_project_to_json, load_project_from_json, load_petrel_wellheads
from pywellsection.io_utils import load_las_as_logs, export_discrete_logs_to_csv, import_discrete_logs_from_csv
from pywellsection.io_utils import import_schichtenverzeichnis

from pywellsection.widgets import QTextEditLogger, QTextEditCommands
from pywellsection.console import QIPythonWidget
from pywellsection.trees import setup_well_widget_tree, setup_window_tree
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
from pywellsection.dialogs import LoadBitmapForTrackDialog
from pywellsection.dialogs import BitmapPlacementDialog
from pywellsection.dialogs import TrackSettingsDialog
from pywellsection.dialogs import EditWellLogTableDialog
from pywellsection.dialogs import EditWellPanelOrderDialog
from pywellsection.dialogs import MapLimitsDialog

from pathlib import Path
from collections import OrderedDict

import logging
import os

# This file is part of the `pywellsection` project and licensed under
# EUPL 1.2
# M. Peter Süss 2025

logging.getLogger("ipykernel").setLevel("CRITICAL")
logging.getLogger("traitlets").setLevel("CRITICAL")
logging.getLogger("root").setLevel("CRITICAL")
logging.getLogger("parso").setLevel("CRITICAL")
logging.getLogger("parso.cache").setLevel("CRITICAL")

LOG = logging.getLogger(__name__)
LOG.setLevel("ERROR")

PROJECT_FILE_VERSION = 1.0  # bump when you change project schema

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.installEventFilter(self)
        self.setWindowTitle("PyQTWellSection")
        self.resize(1200, 1000)
        self.redraw_requested = False
        self.current_project_path = None

        self.project = PWSProject(name="My Project", crs="EPSG:32632", units={"xy": "m", "depth": "m"})

        # The Windows
        ### central widget ----
        wells, tracks, stratigraphy = create_dummy_data()

        wells.test_class()

        self.all_wells = wells
        self.all_stratigraphy = stratigraphy
        self.all_tracks = tracks

        self.all_logs = None
        self.all_discrete_logs = None
        self.all_bitmaps = None
        self.all_profiles = None

        self.well_gap_factor = 3.0
        self.track_gap_factor = 1.0
        self.track_width = 1.0
        self.vertical_scale = 2.0
        self.gap_proportional_to_distance = False
        self.gap_distance_mode="auto"
        self.gap_distance_ref_m = 1000.0
        self.gap_min_factor = 0.8
        self.gap_max_factor = 8.0


        # --- layout settings ---
        self.layout_settings = {
            "well_gap_factor": 3.0,  # legacy constant spacer width
            "track_width": 1.0,
            "track_gap_factor": 0.5,
        }



        window_name = "Well Section 1"

        self.panel_settings = {"well_gap_factor": self.well_gap_factor, "track_gap_factor": self.track_gap_factor,
                               "track_width": self.track_width, "redraw_requested": self.redraw_requested,
                               "vertical_scale": self.vertical_scale,
                               "gap_proportional_to_distance": self.gap_proportional_to_distance,
                               "gap_distance_mode": self.gap_distance_mode,
                               "gap_distance_ref_m": self.gap_distance_ref_m,
                               "gap_min_factor": self.gap_min_factor,
                               "gap_max_factor": self.gap_max_factor,  # clamp large gaps
                               }
        self.map_panel_settings = {"show_labels": True, "equal_aspect": True, "show_grid": True}

        self.dock = WellPanelDock(
            parent=self,
            wells=self.all_wells,
            tracks=self.all_tracks,
            stratigraphy=self.all_stratigraphy,
            panel_settings=self.panel_settings
        )
        self.dock.activated.connect(self._on_well_panel_activated)

        #self.tabifiedDockWidgetActivated.connect(self.window_activate)

        self.dock.well_panel.active_well_panel = True
        self.panel = self.dock.well_panel

        self.WindowList = []

        self.active_window = self.dock

        self.WindowList.append(self.active_window)

        # ipython console
        self.console = QIPythonWidget(self)
        self.dock_console = QDockWidget("Console", self)
        self.dock_console.setWidget(self.console)
        self.dock_console.setObjectName("Console")
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_console)

        # commands
        self.textedit_commands = QTextEditCommands(self)
        self.dock_commands = QDockWidget("Commands", self)
        self.dock_commands.setObjectName("Commands")
        self.dock_commands.setWidget(self.textedit_commands)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dock_commands)

        # log well_panel
        self.textbox_logger = QTextEditLogger(self)
        formatter = logging.Formatter("%(name)-20s - %(levelname)-8s - %(message)s")
        self.textbox_logger.setFormatter(formatter)
        logging.getLogger().addHandler(self.textbox_logger)
        logging.getLogger().setLevel("DEBUG")
        self.dock_logger = QDockWidget("Log", self)
        self.dock_logger.setObjectName("Log")
        self.dock_logger.setWidget(self.textbox_logger.widget)

        setup_well_widget_tree(self)
        setup_window_tree(self)

        ### Setup the Dock

        self.well_dock = QDockWidget("Input Data", self)
        self.well_dock.setObjectName("Input")
        self.well_dock.setWidget(self.well_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.well_dock)

        self.window_dock = QDockWidget("Windows", self)
        self.window_dock.setObjectName("Windows")
        self.window_dock.setWidget(self.window_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.window_dock)

        self.splitDockWidget(self.well_dock, self.dock, Qt.Horizontal)
        self.splitDockWidget(self.dock, self.dock_console, Qt.Vertical)
        self.resizeDocks([self.dock, self.dock_console], [4, 1], Qt.Vertical)

        self.tabifyDockWidget(self.dock_console, self.dock_commands)
        self.tabifyDockWidget(self.dock_commands, self.dock_logger)
        self.tabifyDockWidget(self.well_dock, self.window_dock)
        self.dock_console.raise_()
        self.well_dock.raise_()

        # --- intial build of the well tree
        self._populate_well_tree()
        self._populate_well_tops_tree()
        self._populate_well_log_tree()
        self._populate_well_track_tree()
        self._populate_window_tree()
        #self.redraw_requested = False

        self.redraw_requested = True

        #self.panel_settings = {"well_gap_factor": self.well_gap_factor, "track_gap_factor": self.track_gap_factor,
        #                       "track_width": self.track_width, "redraw_requested": self.redraw_requested,
        #                       "well_panel_title":self.dock.title}

        self.panel.set_visible_wells(None)
        #self.panel.update_well_panel(tracks, wells, stratigraphy, self.panel_settings)
        self.panel.draw_well_panel()

        # ---- build menu bar ----
        self._create_menubar()

    def _create_menubar(self):
        menubar = self.menuBar()

        # --- File menu ---
        file_menu = menubar.addMenu("&File")

        act_new = QAction("New project…", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(lambda: self._new_project(confirm=True))
        file_menu.addAction(act_new)

        act_open = QAction("Open project...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._project_file_open)
        file_menu.addAction(act_open)

        act_save_as = QAction("Save project as...", self)
        act_save_as.setShortcut("Ctrl+S")
        act_save_as.triggered.connect(self._project_file_save_as)
        file_menu.addAction(act_save_as)

        act_save = QAction("Save project...", self)
        act_save.setShortcut("Ctrl+Shift+S")
        act_save.triggered.connect(self._project_file_save)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        import_menu = file_menu.addMenu("&Import")

        act_import_tops = QAction("Import tops from CSV...", self)
        act_import_tops.triggered.connect(self._file_import_tops_csv)
        import_menu.addAction(act_import_tops)

        # 👇 NEW: Import Petrel well heads
        act_import_petrel = QAction("Import Petrel well heads...", self)
        act_import_petrel.triggered.connect(self._file_import_petrel)
        import_menu.addAction(act_import_petrel)

        act_import_las = QAction("Import LAS logs...", self)
        act_import_las.triggered.connect(self._file_import_las)
        import_menu.addAction(act_import_las)

        act_import_discrete = QAction("Discrete logs from CSV…", self)
        act_import_discrete.triggered.connect(self._file_import_discrete_logs_csv)
        import_menu.addAction(act_import_discrete)

        act_import_sv = QAction("Import BGR Schichtenverzeichnis", self)
        act_import_sv.triggered.connect(self._file_import_sv_tops)
        import_menu.addAction(act_import_sv)

        act_import_facies = QAction("Facies intervals from CSV…", self)
        act_import_facies.triggered.connect(self._file_import_facies_intervals_csv)
        import_menu.addAction(act_import_facies)

        act_import_bitmap = QAction("Import bitmaps...", self)
        act_import_bitmap.triggered.connect(self._action_load_core_bitmap_to_well)
        import_menu.addAction(act_import_bitmap)

        export_menu = file_menu.addMenu("&Export")
        act_export_discrete_logs = QAction("Export discrete logs as csv...", self)
        act_export_discrete_logs.triggered.connect(self._file_export_discrete_logs_csv)
        export_menu.addAction(act_export_discrete_logs)

        file_menu.addSeparator()

        act_exit = QAction("Exit", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # --- View menu: select/deselect all wells ---
        view_menu = menubar.addMenu("&View")
        # act_sel_all = QAction("Select all wells", self)
        # act_sel_all.triggered.connect(self._select_all_wells)
        # view_menu.addAction(act_sel_all)
        #
        # act_sel_none = QAction("Select no wells", self)
        # act_sel_none.triggered.connect(self._select_no_wells)
        # view_menu.addAction(act_sel_none)

        act_layout = QAction("Layout settings...", self)
        act_layout.triggered.connect(self._action_layout_settings)
        view_menu.addAction(act_layout)

        act_new_map = QAction("New Map window", self)
        act_new_map.triggered.connect(self._open_map_window)
        view_menu.addAction(act_new_map)


        # act_new_window = QAction("New Well Section Window ...", self)
        # act_new_window.triggered.connect(self._action_add_well_panel_dock)
        # view_menu.addAction(act_new_window)
        #
        # act_close_well_panel = QAction("Close active well well_panel", self)
        # act_close_well_panel.setShortcut("Ctrl+W")
        # act_close_well_panel.triggered.connect(self._remove_well_panel_dock)
        # view_menu.addAction(act_close_well_panel)

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
        act_help.triggered.connect(self._action_show_import_help)
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

    def _new_pws_project(self, confirm=False):
        if confirm:
            reply = QMessageBox.question(self, 'Message',
                                         "Are you sure you want to create a new project?", QMessageBox.Yes |
                                         QMessageBox.No, QMessageBox.No)
            # create
            self.project = PWSProject(name="My Project", crs="EPSG:32632", units={"xy": "m", "depth": "m"})

            # connect old references
            self.all_wells = self.project.all_wells
            self.tracks = self.project.all_tracks
            self.stratigraphy = self.project.all_stratigraphy

    def _save_pws_project(self, path):
            # save
            data = self.project.to_dict()


    def _load_pws_project(self, path):
            self.project = PWSProject.from_dict(json_data)

    def _redraw_all_panels(self):
        for win in self.WindowList:
            if win.type == "WellSection":
                win.well_panel.draw_well_panel()
            elif win.type == ("MapWindow"):
                win.draw_panel()

    def _project_file_open(self):

        #        BaseWindow = WindowList[0]
        #try

        """Load wells/tracks data from a JSON file (example)."""
        path, _ = QFileDialog.getOpenFileName(self, "Open project", "", "JSON Files and PyQtWS Projects (*.json *.pwj)")
        if not path:
            return
        try:
            window_dict, wells, tracks, raw_strat, ui_layout, _ = load_project_from_json(path)

            self.current_project_path = path
            self.project_name = Path(path).stem
            self.setWindowTitle(f"PyQtWellSection - {self.project_name}")

            # remove all existing windows
            self.panel = self.WindowList[0].well_panel
            for window in self.WindowList[1:]:
                LOG.debug(f"Removing window {window.title}")
                self._remove_well_panel_dock(window, confirm=False)
            self.WindowList = [self.WindowList[0]]
            #self.WindowList = []

            # self.all_stratigraphy = None
            self.all_logs = []
            self.all_bitmaps = []
            self.all_discrete_logs = []
            self.all_tracks = tracks
            self.all_wells = wells
            self.project.all_wells = wells

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

            if not self.all_stratigraphy:
                self.all_stratigraphy = stratigraphy
            else:
                self.all_stratigraphy.update(stratigraphy)

            self.project.all_stratigraphy = self.all_stratigraphy

            for well in wells:
                logs = well.get("logs")
                if logs:
                    for log in logs:
                        if not self.all_logs:
                            self.all_logs = logs.keys()
                        if log in self.all_logs:
                            continue
                        else:
                            # LOG.debug("appending log:" , log)
                            self.all_logs = self.all_logs | {log}
                    self.project.all_logs = self.all_logs
                else:
                    LOG.debug("No logs found")

            for well in wells:
                disc_logs = well.get("discrete_logs", {})
                self.all_discrete_logs=disc_logs

                for log_name, d in list(disc_logs.items()):
                    if "top_depths" in d and "bottom_depths" in d:
                        tops = np.array(d["top_depths"], dtype=float)
                        values = np.array(d["values"], dtype=object)
                        # convert to depth/value representation (top sample)
                        disc_logs[log_name] = {
                            "depth": tops.tolist(),
                            "values": values.tolist(),
                        }
                self.project.all_discrete_logs = self.all_discrete_logs

            for well in wells:
                bitmaps = well.get("bitmaps", None)
                # if bitmaps:
                #     for bitmap in bitmaps:
                #         if bitmap is not None:
                #             self.all_bitmaps.append(bitmap)

                if bitmaps:
                    for bitmap in bitmaps:
                        if bitmap is not None:
                            bitmap_cfg = bitmaps[bitmap]
                            bmp_full_path = bitmap_cfg.get("path", None)
                            if bmp_full_path:
                                fpath, fname = os.path.split(bmp_full_path)
                                p_path, pname = os.path.split(path)
                                rel_path = os.path.relpath(fpath, start=path)
                                bmp_project_path = str(os.path.join(p_path,f"{self.project_name}.pdj",fname))
                                bitmap_cfg["path"] = str(os.path.join(p_path,f"{self.project_name}.pdj",fname))
                                self.all_bitmaps.append(bitmap)
                                well[bitmap] = bitmap_cfg
                                print (bitmap_cfg)
                    self.project.all_bitmaps = self.all_bitmaps

            #self.panel.panel_settings = window_dict[0]["panel_settings"]
            self.panel.visible_tops = window_dict[0]["visible_tops"]
            self.panel.visible_logs = window_dict[0]["visible_logs"]
            self.panel.visible_tracks = window_dict[0]["visible_tracks"]
            self.panel.visible_wells = window_dict[0]["visible_wells"]
            self.WindowList[0].set_title(window_dict[0]["window_title"])
            self.panel.vertical_scale = window_dict[0].get("vertical_scale", 1.0)
            self.panel.gap_proportional_to_distance = window_dict[0].get("gap_proportional_to_distance", False)
            self.panel.gap_distance_mode = window_dict[0].get("gap_distance_mode", "auto")
            self.panel.gap_distance_ref_m = window_dict[0].get("gap_distance_ref_m", 1000)
            self.panel.gap_min_factor = window_dict[0].get("gap_min_factor", 0.8)
            self.panel.gap_max_factor = window_dict[0].get("gap_max_factor", 8.0)

            #add all remaining windows back in
            for window in window_dict[1:]:
                if (window["type"] == "WellSection"):
                    if window.get("panel_settings", None):
                        panel_setting = window["panel_settings"]
                    else:
                        panel_setting = window["well_panel_settings"]
                    dock = self._add_well_panel_dock(window["window_title"], window["visible_tops"],
                                                     window["visible_logs"], window["visible_tracks"],
                                                     window["visible_wells"], panel_setting)

                    dock.set_title(window["window_title"])
                    if window["visible"]:
                        dock.setVisible(True)
                    else:
                        dock.setVisible(False)

                elif (window["type"] == "MapWindow"):
                    layout_settings = {}
                    if window.get("layout_settings", None):
                        layout_setting = window["layout_settings"]
                    profiles = window["profiles"]
                    dock = MapDockWindow(parent=self,
                                         wells=self.all_wells,
                                         profiles=profiles,
                                         map_layout_settings=layout_settings,
                                         title=window["window_title"])
                    self.addDockWidget(Qt.RightDockWidgetArea, dock)
                    self.WindowList.append(dock)
                    if window["visible"]:
                        dock.setVisible(True)
                    else:
                        dock.setVisible(False)

            self.redraw_requested = False
            self.panel_settings["redraw_requested"] = False

            # populate well tree
            self._populate_well_tree()
            self._populate_well_tops_tree()
            #self._populate_well_log_tree()
            self._populate_well_track_tree()
            self._populate_window_tree()
            self._dock_layout_restore(ui_layout)

            #            self.panel.update_well_panel(tracks, wells, stratigraphy, self.panel_settings)

            self.panel.set_visible_tops(self.all_stratigraphy)

            self._refresh_all_well_panels()

            # ✅ Trigger full redraw
            #            self.redraw_requested = True
            self.panel_settings["redraw_requested"] = True
            #self.panel.draw_well_panel()
            self._redraw_all_panels()

        except Exception as e:
            QMessageBox.critical(self, "Open Error", str(e))

    def _project_file_save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save project as", "", "Well project (*.pwj);;All files (*.*)")
        if not path:
            return
        LOG.debug(f"Saving project as {path}")
        self._project_file_save(path)

    def _project_file_save(self, path = None):
        """
        Save project as:
          - <project_name>.pws              (JSON "project shell" with metadata)
          - <project_name>.data/data.json   (JSON with the actual project data)

        Example:
          MyProject.pws
          MyProject.data/
              data.json
        """

        old_path = None

        if self.current_project_path:
            old_path = self.current_project_path

        if not path and self.current_project_path:
            path = self.current_project_path

        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Save project",
                "",
                "PyWellSection Project (*.pwj);;All files (*.*)"
            )
            if not path:
                return

        # enforce .pws extension
        if path.lower().endswith(".json"):
            path = path[:-5] + ".pwj"
        if not path.lower().endswith(".pwj"):
            path = path + ".pwj"

        base_dir = os.path.dirname(os.path.abspath(path))
        project_stem = os.path.splitext(os.path.basename(path))[0]  # _project_name
        if project_stem.endswith(".json"):
            project_stem = project_stem[:-5]
        data_dir_name = f"{project_stem}.pdj"
        data_dir = os.path.join(base_dir, data_dir_name)
        data_json_path = os.path.join(data_dir, "Data.json")

        # build project data payload (your actual content)

        wells = getattr(self.panel, "wells", [])
        if len(wells) == 0:
            LOG.debug("Project was not saved: no wells to save")
            return
        LOG.debug(f"Saving {wells[0]}")

        for well in wells:
            LOG.debug(f"Saving {well["name"]}")

        tracks = getattr(self.panel, "tracks", [])
        stratigraphy = getattr(self.panel, "stratigraphy", None)
        extra_metadata = {
            "app": "pywellsection",
            "version": "0.1.0",
        }
        ui_layout = self._dock_layout_snapshot()

        window_list = self._get_window_list()


        # Write into a temp dir first (safer than half-written projects)
        tmp_dir = os.path.join(base_dir, f".{data_dir_name}.tmp")
        try:
            if os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir)
            os.makedirs(tmp_dir, exist_ok=True)

            # 1) write data.json inside tmp data dir
            tmp_data_json = os.path.join(tmp_dir, "data.json")

            export_project_to_json(tmp_data_json, wells, tracks, stratigraphy, window_list, ui_layout, extra_metadata)
            #
            # with open(tmp_data_json, "w", encoding="utf-8") as f:
            #     json.dump(project_data, f, indent=2)

            # 2) write the .pws "shell" file (metadata pointing to data.json)
            shell = {
                "project_file_version": PROJECT_FILE_VERSION,
                "project_name": project_stem,
                "created_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "data": {
                    "directory": data_dir_name,  # relative to .pws location
                    "file": "data.json",
                },
            }
            tmp_pws = os.path.join(base_dir, f".{project_stem}.pws.tmp")
            with open(tmp_pws, "w", encoding="utf-8") as f:
                json.dump(shell, f, indent=2)

            # 3) commit: replace existing data_dir atomically-ish
            #    - remove old dir
            if old_path == path: # if old equals new simple save ... .
            # just copy the new data.json into the existing data_dir
                shutil.copy2(tmp_data_json, data_dir)
                shutil.rmtree(tmp_dir)
            elif old_path != path: # .. an old name exist but it is not the same save existing project under new name ...
                    o_path, ofname = os.path.split(old_path)
                    oproject_stem = os.path.splitext(ofname)[0]
                    o_data_path = os.path.join(o_path, oproject_stem + ".pdj")
                    #os.makedirs(data_dir, exist_ok=True)
                    if os.path.exists(data_dir): # a previous project was saved under this name
                        shutil.rmtree(data_dir)
                    shutil.copytree(o_data_path, data_dir)
                    shutil.copy2(tmp_data_json, data_dir)
                    shutil.rmtree(tmp_dir)

            else: # a new project from scratch
                if os.path.exists(data_dir): # a previous project was saved under this name
                    shutil.rmtree(data_dir)
                os.rename(tmp_dir, data_dir)
            # 4) commit: replace .pws
            #    On Windows os.replace is safest; on macOS/Linux also fine.
            os.replace(tmp_pws, path)
            # keep last saved path if you want
            self._last_project_path = old_path
            self.current_project_path = path
            self.project_name = Path(path).stem
            self.setWindowTitle(f"PyQtWellSection - {self.project_name}")


        except Exception as e:
            # cleanup temp files
            try:
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
            except Exception:
                pass
            try:
                tmp_pws = os.path.join(base_dir, f".{project_stem}.pws.tmp")
                if os.path.exists(tmp_pws):
                    os.remove(tmp_pws)
            except Exception:
                pass

            QMessageBox.critical(self, "Save error", f"Failed to save project:\n{e}")
            return

        QMessageBox.information(self, "Project saved", f"Saved:\n{path}\n\nData:\n{data_json_path}")


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
                self.all_logs = self.all_logs | logs  # this operator merges the two dictionaries

        # Update well_panel + tree views
        self.panel.set_wells(self.all_wells)
        self.panel.draw_well_panel()

        # refresh tree sections
        self._populate_well_tree()
        #self._populate_well_log_tree()
        self._populate_well_track_tree()

        QMessageBox.information(self, "LAS import", "LAS logs imported successfully.")

    def _file_import_facies_intervals_csv(self):
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

            lithology, trend = self._parse_lithotrend(lt_txt, trd_txt)

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

    def _file_import_tops_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import tops from CSV",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not path:
            return

        self._file_load_tops_from_csv(path)

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

        # ---- update well_panel ----
        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            self.panel.stratigraphy = self.stratigraphy
            # keep zoom/flatten; if you want to reset, uncomment:
            # self.panel.current_depth_window = None
            # self.panel._flatten_depths = None
            self.panel.draw_well_panel()

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

    def _file_import_sv_tops(self):
        ### This import filter has been developed to load BGR Schichtenverzeichnis (SV) tops from a .xlsx file.
        path, _ = QFileDialog.getOpenFileName(
            self, "Import BGR Schichtenverzeichnis (XLSX)", "", "Excel (*.xlsx);;All files (*.*)"
        )
        if not path:
            return
        ok = import_schichtenverzeichnis(self, self.project, path)
        if ok:
            print (self.project.all_stratigraphy)
            self.all_stratigraphy = self.project.all_stratigraphy
            self.all_wells = self.project.all_wells
            self._populate_well_tops_tree()
            self._populate_well_tree()
#            self._refresh_all_panels()
#            self._populate_well_tree()

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
        self.well_root_item.setCheckState(0, Qt.Unchecked)

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

        self._populate_well_log_tree()

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
            #state = Qt.Checked if (not prev_selected or well_name in prev_selected) else Qt.Unchecked
            state = Qt.Checked if well_name in self.panel.visible_wells else Qt.Unchecked
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
            bmp_folder.setData(0, Qt.UserRole, ("folder", "bitmaps", well_name))

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
                    log_item.setData(0, Qt.UserRole, ("well_log",well_name , log_name))
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
                    blog_item = QTreeWidgetItem(bmp_folder, [blog_name])
                    blog_item.setData(0, Qt.UserRole, ("Bitmap", well_name, blog_name))

        self.well_tree.blockSignals(False)
        self._rebuild_well_panel_from_tree()

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

        strat_list = list(self.all_stratigraphy)

        for strat_name in strat_list:
            if self.all_stratigraphy[strat_name]['role'] == 'stratigraphy':
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
            elif self.all_stratigraphy[strat_name]['role'] == 'fault':
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
            elif self.all_stratigraphy[strat_name]['role'] == 'other':
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

        # Apply current selection to well_panel
        #self._rebuild_well_panel_from_tree()

    def _populate_well_log_tree(self):
        """Rebuild the tree from self.all_wells, preserving selections if possible."""
        ### add logs as children of "All logs"
        # delete all logs under the folder and rebuild from scratch
        ### Remember current selection by name
        ### First continous Logs

        print ("_populate_well_log_tree")

        self.well_tree.blockSignals(True)
        prev_selected = set()
        ### Start with populating the continous logs tree ###
        root = self.continous_logs_folder
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))
        # remove all wells under the folder
        root.takeChildren()

        log_names = set()
        if self.all_logs:
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

        ### Second discrete Logs ###
        prev_selected = set()
        root = self.discrete_logs_folder
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))
        root.takeChildren()

        dlog_names = set()
        if self.all_discrete_logs:
            for dlog in self.all_discrete_logs:
                name = dlog
                if dlog:
                    dlog_names.add(name)
            for name in sorted(dlog_names):
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

        ### Third bitmap Logs ###
        prev_selected = set()
        root = self.bitmaps_folder
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))
        root.takeChildren()
        bmp_names = set()
        if self.all_bitmaps:
            for bmp in self.all_bitmaps:
                name = bmp
                if bmp:
                    bmp_names.add(name)
            for name in sorted(bmp_names):
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
        self._rebuild_visible_bitmaps_from_tree()

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

    def _populate_window_tree(self):
        """Populate the tree of windows in the main window."""
        self.window_tree.blockSignals(True)
        #self.window_tree.clear()
        root = self.window_root

        prev_selected = set()
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))

        prevn = len(prev_selected)
        root.takeChildren()

        for win in self.WindowList:
            window_name = win.get_title()
            window_type = win.get_type()

            visible = win.get_visible()
            if not window_name:
                continue
            window_item = QTreeWidgetItem([window_name])
            # # make the track item checkable
            window_item.setFlags(
                window_item.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
                | Qt.ItemIsEditable
            )
            window_item.setData(0, Qt.UserRole, window_name)
            window_item.setData(1, Qt.UserRole, window_type)
            state = (
                Qt.Checked
                if (visible)
                else Qt.Unchecked
            )
            window_item.setCheckState(0, state)
            root.addChild(window_item)
        self.window_tree.blockSignals(False)

    def _on_well_tree_item_changed(self, item: QTreeWidgetItem, _col: int):
        """Recompute displayed wells whenever a checkbox changes."""

        #LOG.debug(f"on_tree_item_changed! {item.data(0, Qt.UserRole)} {item.checkState(0)}")
        #self.panel.set_draw_well_panel(False)

        if item.data(0, Qt.UserRole) is None:
            return 0

        p = item.parent()
        if item is self.well_root_item or p is self.well_root_item:
            self._rebuild_wells_from_tree()
            self._update_map_windows()

        if item is self.stratigraphy_root or p is self.stratigraphy_root:
            self._rebuild_visible_tops_from_tree()

        if item is self.faults_root or p is self.faults_root:
            self._rebuild_visible_tops_from_tree()

        if item is self.other_root or p is self.other_root:
            self._rebuild_visible_tops_from_tree()

        # Logs
        if item is self.continous_logs_folder or p is self.continous_logs_folder:
            #LOG.debug("LOGS FOLDER changed")
            self._rebuild_visible_logs_from_tree()
            self.panel.draw_well_panel()

        if item is self.discrete_logs_folder or p is self.discrete_logs_folder:
            LOG.debug("DISCRETE LOGS FOLDER changed")
            self._rebuild_visible_discrete_logs_from_tree()
            self.panel.draw_well_panel()

        if item is self.bitmaps_folder or p is self.bitmaps_folder:
            LOG.debug("BITMAPS FOLDER changed")
            self._rebuild_visible_bitmaps_from_tree()
            self.panel.draw_well_panel()

        # Tracks
        if item is self.track_root_item or p is self.track_root_item:
            self._rebuild_visible_tracks_from_tree()

        #self.panel.set_draw_well_panel(True)

    def _select_all_wells(self):
        self.well_tree.blockSignals(True)
        root = self.well_tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.Checked)
        self.well_tree.blockSignals(False)
        self._rebuild_well_panel_from_tree()

    def _select_no_wells(self):
        self.well_tree.blockSignals(True)
        root = self.well_tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setCheckState(0, Qt.Unchecked)
        self.well_tree.blockSignals(False)
        self._rebuild_well_panel_from_tree()

    def _set_tree_from_well_panel(self):

        #LOG.debug("Setting well tree ... .")
        self.well_tree.itemChanged.connect(self.do_nothing)

        wells = self.panel.get_visible_wells()

        if wells is not None:
            nb_wells = len(wells)
        checked_names = set()
        root = self.well_root_item

        self.panel.panel_settings["redraw_requested"] = False

        for i in range(root.childCount()):
            it = root.child(i)
            state = Qt.Unchecked
            if wells is not None:
                for well in wells:
                    if well == it.data(0, Qt.UserRole):
                        state = Qt.Checked
            it.setCheckState(0, state)

        tops = self.panel.get_visible_tops()
        #LOG.debug("visible tops:", tops)
        root = self.stratigraphy_root
        for i in range(root.childCount()):
            it = root.child(i)
            state = Qt.Unchecked
            if tops is not None:
                for top in tops:
                    if top == it.data(0, Qt.UserRole):
                        state = Qt.Checked
            it.setCheckState(0, state)

        tracks = self.panel.get_visible_tracks()
        #LOG.debug ("getting visible tracks", tracks)
        root = self.track_root_item
        for i in range(root.childCount()):
            it = root.child(i)
            state = Qt.Unchecked
            if tracks is not None:
                for track in tracks:
                    if track == it.data(0, Qt.UserRole):
                        #LOG.debug ("track is ",track)
                        state = Qt.Checked
            it.setCheckState(0, state)

        logs = self.panel.get_visible_logs()
        #LOG.debug("getting visible logs", logs)
        root = self.continous_logs_folder
        for i in range(root.childCount()):
            it = root.child(i)
            state = Qt.Unchecked
            if logs is not None:
                for log in logs:
                    if log == it.data(0, Qt.UserRole):
                        #LOG.debug("log is ", log)
                        state = Qt.Checked
            it.setCheckState(0, state)

        self.panel.panel_settings["redraw_requested"] = True
        self.well_tree.itemChanged.connect(self._on_well_tree_item_changed)
        self.panel.draw_well_panel()

    def do_nothing(self):
        return

    def _rebuild_well_panel_from_tree(self):
        """Collect checked wells (by name) and send to well_panel."""
        checked_names = set()

        #LOG.debug("rebuild_well_panel_from_tree")

        root = self.stratigraphy_root
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                checked_names.add(it.data(0, Qt.UserRole))
        selected = checked_names

        self.panel.set_visible_tops(selected)

        checked_names = set()

        root = self.track_root_item
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                checked_names.add(it.data(0, Qt.UserRole))
        selected = checked_names

        #LOG.debug (f"rebuild_well_panel tracks{selected}")

        self.panel.set_visible_tracks(selected)

        checked_names = set()

        root = self.well_root_item
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                checked_names.add(it.data(0, Qt.UserRole))

        # Map names → well dicts (keep original order)
        selected = [w for w in self.all_wells if (w.get("name") in checked_names)]
        # If none selected, you can either show none or all; here: show none
        #self.panel.set_wells(selected)

        self.panel.set_visible_wells(checked_names)

    def _rebuild_wells_from_tree(self):
        """Collect checked wells (by name) and send to well_panel."""
        checked_names = set()

        checked_names = set()
        root = self.well_root_item
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                checked_names.add(it.data(0, Qt.UserRole))

        # Map names → well dicts (keep original order)
        #selected = [w for w in self.all_wells if (w.get("name") in checked_names)]
        # If none selected, you can either show none or all; here: show none
        # self.panel.set_wells(selected)

        #LOG.debug(f"rebuild_wells_from_tree: {checked_names}")

        self.panel.set_visible_wells(checked_names)
        self.panel.draw_well_panel()

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

        #LOG.debug (f"_rebuild_visible_tops_from_tree visible:{visible}")

        self.panel.set_visible_tops(visible if visible else None)
        self.panel.draw_well_panel()

    def _rebuild_visible_logs_from_tree(self):
        """Collect checked logs and inform the well_panel."""
        root = self.continous_logs_folder
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
        #LOG.debug ("visible logs:", visible)
        self.panel.set_visible_logs(visible)

    def _rebuild_visible_discrete_logs_from_tree(self):
        root = self.discrete_logs_folder
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

        self.panel.set_visible_discrete_logs(visible_set)

    def _rebuild_visible_bitmaps_from_tree(self):
        root = self.bitmaps_folder
        visible = set()
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                nm = it.data(0, Qt.UserRole)
                if nm:
                    visible.add(nm)
        # If everything is checked, you can pass None to mean "no filter"
        if visible and len(visible) == root.childCount():
            visible_set = visible
        else:
            visible_set = visible if visible else set()

        self.panel.set_visible_bitmaps(visible_set)

    def _rebuild_visible_tracks_from_tree(self):
        """Collect checked tracks and inform the well_panel."""
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

        self.panel.set_visible_tracks(visible)

    def add_log_to_track(self, track_name: str, log_name: str,
                         label: str = None, color: str = "black",
                         xscale: str = "linear", direction: str = "normal",
                         xlim=None):
        """
        Add a new log config to a track by name and refresh well_panel & trees.

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

        # 5) propagate to well_panel & tree widgets
        #if self.panel.tracks is not None:
        #    self.panel.tracks = self.panel.tracks
        #    #LOG.debug(self.panel.tracks)# keep well_panel in sync
        #self.panel.draw_well_panel()

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
        else:
            existing_names = {t.get("name", "") for t in self.all_tracks}

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

        # Keep well_panel in sync
        #self.panel.tracks = self.tracks
        #self.panel.draw_well_panel()

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

        # keep well_panel in sync
        if hasattr(self, "well_panel"):
            self.panel.tracks = self.all_tracks

            # clean up visible_tracks if needed
            vt = getattr(self.panel, "visible_tracks", None)
            if vt is not None:
                vt = set(vt)
                if track_name in vt:
                    vt.remove(track_name)
                self.panel.visible_tracks = vt or None

            self.panel.draw_well_panel()

        # refresh tree sections
        self._populate_well_track_tree()  # tracks folder
        #self._populate_well_log_tree()  # logs folder still valid, but refresh for consistency

    def _action_show_import_help(self):
        dlg = HelpDialog(self, html=self.get_import_help_html(), title="Help - Import Formats")
        dlg.exec_()

    def get_import_help_html(self) -> str:

        with open('pywellsection/PyQtHelp.html', 'r') as file:
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

        # 2) push into well_panel
        if hasattr(self, "well_panel"):
            self.panel.stratigraphy = new_strat

            # flattening uses strat key order:
            # if you have any cached flatten state, you might want to reset:
            if hasattr(self.panel, "_flatten_depths"):
                self.panel._flatten_depths = None

            self.panel.draw_well_panel()

        # 3) refresh "Stratigraphic tops" folder in tree
        #        if hasattr(self, "_populate_top_tree"):
        self._populate_well_tops_tree()

    def _action_layout_settings(self):
        """Open dialog to adjust distance between wells and track width."""
        """ This only works if the current panel is a well_panel."""
        if not hasattr(self, "panel"):
            return

        if self.panel.type != "well_panel":
            return

        #
        # if self.panel.current_depth_window is None:
        #     depth_min = -9999
        #     depth_max = 9999
        # else:
        #     depth_min, depth_max = self.panel.current_depth_window

        depth_min, depth_max = self.panel.get_current_depth_window()

        dlg = LayoutSettingsDialog(
            self,
            well_gap_factor=self.panel.well_gap_factor,
            track_width=self.panel.track_width,
            vertical_scale = 1,
            depth_min = depth_min,
            depth_max = depth_max,
            track_gap_factor = self.track_gap_factor,
            gap_proportional_to_distance = self.gap_proportional_to_distance,
            gap_distance_ref_m = self.gap_distance_ref_m,
            gap_min_factor = self.gap_min_factor,
            gap_max_factor = self.gap_max_factor
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        gap, tw, vs, depth_min, depth_max, tgf, gptdi, gdrm, gmf, gxf= dlg.values()
        self.panel.set_current_depth_window(depth_min, depth_max)
        self.set_layout_params(gap, tw, vs, tgf, gptdi, gdrm, gmf, gxf)

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

        # --- redraw well_panel with updated tops ---
        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            self.panel.draw_well_panel()

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

        # Update well_panel wells (keep tracks & stratigraphy)
        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            # you might want to reset flattening or keep it; here we keep zoom/flatten
            self.panel.draw_well_panel()

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

        # push to well_panel
        if hasattr(self, "well_panel"):
            self.panel.tracks = self.tracks
            self.panel.draw_well_panel()

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

        # redraw well_panel
        if hasattr(self, "well_panel"):
            self.panel.tracks = self.all_tracks
            self.panel.draw_well_panel()

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

        # push into well_panel
        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            # optional: keep current zoom; if you want to reset, uncomment:
            # self.panel.current_depth_window = None
            # self.panel._flatten_depths = None
            self.panel.draw_well_panel()

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

        # update well_panel
        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            # optional: keep zoom/flatten; if you want to reset, uncomment:
            # self.panel.current_depth_window = None
            # self.panel._flatten_depths = None
            self.panel.draw_well_panel()

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

        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            self.panel.draw_well_panel()

        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()
        if hasattr(self, "_populate_top_tree"):
            self._populate_top_tree()

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

        # redraw well_panel so changes take effect
        if hasattr(self, "well_panel"):
            self.panel.tracks = self.all_tracks
            self.panel.draw_well_panel()

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

        # redraw well_panel
        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            self.panel.draw_well_panel()

        if unknown:
            QMessageBox.warning(
                self,
                "Lithofacies",
                "Some intervals refer to unknown wells:\n  "
                + ", ".join(sorted(set(unknown)))
            )

    def _action_change_window_title(self, title: str):
        """Change the title of the selected window."""
        for window in self.WindowList:
            if window.title == title:
                window.setWindowTitle(title)

                return window
        return None

    def _action_load_bitmap_into_bitmap_track(self, track_name: str):
        """
        Load an image and assign it to a selected well under the bitmap key
        of the selected bitmap track.
        """
        LOG.debug(f"Loading bitmap into track '{track_name}'...")

        if not getattr(self, "all_tracks", None):
            QMessageBox.information(self, "Load bitmap", "No tracks in project.")
            return
        if not getattr(self, "all_wells", None):
            QMessageBox.information(self, "Load bitmap", "No wells in project.")
            return

        # Find the track
        track = None
        for t in self.all_tracks:
            if t.get("name") == track_name:
                track = t
                break
        if track is None or "bitmaps" not in track:
            QMessageBox.warning(self, "Load bitmap", f"Track '{track_name}' is not a bitmap track.")
            return

        bmp_cfg = track.get("bitmap", {}) or {}
        key = bmp_cfg.get("key", None)
        if not key:
            QMessageBox.warning(self, "Load bitmap", "Bitmap track has no 'key' configured.")
            return

        well_names = [w.get("name") for w in self.all_wells if w.get("name")]
        if not well_names:
            QMessageBox.information(self, "Load bitmap", "No named wells available.")
            return

        dlg = LoadBitmapForTrackDialog(self, well_names, track_name, bmp_cfg)
        if dlg.exec_() != QDialog.Accepted:
            return

        res = dlg.result()
        if not res:
            return

        project_path = self.current_project_path

        base_dir = os.path.dirname(os.path.abspath(project_path))
        project_stem = os.path.splitext(os.path.basename(project_path))[0]  # _project_name
        if project_stem.endswith(".json"):
            project_stem = project_stem[:-5]
        data_dir_name = f"{project_stem}.pdj"
        data_dir = os.path.join(base_dir, data_dir_name)

        bitmap_name, bitmap_extention = os.path.splitext(res["bitmap_path"])

        new_bitmap_path = os.path.join(data_dir,f"{res['well_name']}_{key}.{bitmap_extention}" )

        bitmap_path = res["path"]
        bitmap_path = Path(bitmap_path)

        bitmap_copy = shutil.copy2(bitmap_path, data_dir)
        os.rename(bitmap_copy, new_bitmap_path)



        # Resolve well
        well = None
        for w in self.all_wells:
            if w.get("name") == res["well_name"]:
                well = w
                break
        if well is None:
            QMessageBox.warning(self, "Load bitmap", f"Well '{res['well_name']}' not found.")
            return

        # Store under this track key
        bitmaps = well.setdefault("bitmaps", {})
        bitmaps[key] = {
            "path": res["path"],
            "top_depth": res["top_depth"],
            "base_depth": res["base_depth"],
            "label": res["label"],
            "alpha": res["alpha"],
            "interpolation": res["interpolation"],
            "cmap": res["cmap"],
            "flip_vertical": res["flip_vertical"],
        }

        # Redraw
        if hasattr(self, "well_panel"):
            self.panel.wells = self.all_wells
            self.panel.tracks = self.tracks
            self.panel.draw_well_panel()

        # If you have multiple dock well_panels:
        if hasattr(self, "_refresh_all_well_panels"):
            self._refresh_all_well_panels()

        self._redraw_all_panels()

    def _action_load_core_bitmap_to_well(self, default_well_name=None):
        """
        Open dialog and attach core bitmap to selected well:
          well["bitmaps"][key] = {path, top_depth, base_depth, ...}
        """

        LOG.debug("Loading core bitmap to well...")

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

        project_path = self.current_project_path

        base_dir = os.path.dirname(os.path.abspath(project_path))
        project_stem = os.path.splitext(os.path.basename(project_path))[0]  # _project_name
        if project_stem.endswith(".json"):
            project_stem = project_stem[:-5]
        data_dir_name = f"{project_stem}.pdj"
        data_dir = os.path.join(base_dir, data_dir_name)

        bitmap_name, bitmap_extention = os.path.splitext(res["path"])

        new_bitmap_path = os.path.join(data_dir,f"{res['well_name']}_{res["key"]}{bitmap_extention}" )

        bitmap_path = res["path"]
        bitmap_path = Path(bitmap_path)

        bitmap_copy = shutil.copy2(bitmap_path, data_dir)
        os.rename(bitmap_copy, new_bitmap_path)


        # attach to well
        bitmaps = target.setdefault("bitmaps", {})
        bitmaps[res["key"]] = {
            "name": res["name"],
            "path": new_bitmap_path,
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

        # push into well_panel & redraw
        # if hasattr(self, "well_panel"):
        #     self.panel.wells = self.all_wells
        #     self.panel.tracks = self.tracks
        #     self.panel.draw_well_panel()

        # refresh tree (if you show bitmaps there)

        self.all_bitmaps.append(res["key"])

        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _action_add_well_panel_dock(self):
        dock = WellPanelDock(
            parent=self,
            wells=self.all_wells,
            tracks=self.all_tracks,
            stratigraphy=self.all_stratigraphy,
            panel_settings=self.panel_settings
        )

        dock.activated.connect(self._on_well_panel_activated)
        dock.well_panel.visible_tops = None
        dock.well_panel.visible_logs = None
        dock.well_panel.visible_tracks = None
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self._on_well_panel_activated(dock)
        self.WindowList.append(dock)
        self._populate_window_tree()
        nWindows = len(self.WindowList)

        item = self.window_root.child(nWindows - 1)
        item.setCheckState(0, Qt.Checked)

        def _remove_dock_safely(obj=None, dock_ref=dock):
            # Remove by identity if present; ignore if already removed
            try:
                # Fast path: membership check by identity
                for i, existing in enumerate(self.WindowList):
                    if existing is dock_ref:
                        del self.WindowList[i]
                        break
            except Exception:
                # Swallow any unexpected errors to avoid crashing during QObject teardown
                pass

        dock.destroyed.connect(_remove_dock_safely)

        dock.show()

    def _action_edit_bitmap_positions(self, track_name: str):
        track = next((t for t in self.all_tracks if t.get("name") == track_name), None)
        if track is None or "bitmap" not in track:
            QMessageBox.information(self, "Bitmap", "Selected track is not a bitmap track.")
            return

        # key = (track.get("bitmaps") or {}).get("key")
        # if not key:
        #     QMessageBox.warning(self, "Bitmap", "Bitmap track has no 'key'.")
        #     return

        key = "track"

        # Use the active well_panel (docked) if you implemented it; otherwise self.panel
        well_panel = getattr(self, "active_well_panel", None) or self.panel

        dlg = BitmapPlacementDialog(
            parent=self,
            wells=self.all_wells,
            track_name=track_name,
            bitmap_key=key,
            well_panel_widget=well_panel,
        )
        dlg.exec_()

    def _action_edit_panel_wells(self, dock):
        panel = dock.well_panel
        dlg = EditWellPanelOrderDialog(self, panel=panel, project_wells=self.all_wells)
        dlg.exec_()
        # after dialog, update map windows / refresh trees if needed
        if hasattr(self, "_update_map_windows"):
            self._update_map_windows()
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _action_edit_map_settings(self, map_dock):
        dlg = MapLimitsDialog(self, map_dock.panel)
        dlg.exec_()

    def _ensure_bitmap_track_exists(self):
        """
        Ensure there is at least one bitmap track in self.tracks.
        The bitmap track references a per-well bitmap by key.
        """
        if not hasattr(self, "tracks") or self.tracks is None:
            self.tracks = []

        for t in self.tracks:
            if "bitmap" in t:
                return t# already exists

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

        self.all_tracks = self.tracks

        return self.tracks[0]

    def _add_well_panel_dock(self, window_title=None, visible_tops=None, visible_logs=None, visible_tracks=None,
                             visible_wells=None, panel_settings=None):

        vertical_scale = panel_settings.get("vertical_scale", 1.0)
        panel_settings["vertical_scale"] = vertical_scale

        dock = WellPanelDock(
            parent=self,
            wells=self.all_wells,
            tracks=self.all_tracks,
            stratigraphy=self.all_stratigraphy,
            panel_settings=panel_settings
        )
        dock.activated.connect(self._on_well_panel_activated)

        dock.well_panel.visible_tops = visible_tops
        dock.well_panel.visible_logs = visible_logs
        dock.well_panel.visible_tracks = visible_tracks
        dock.well_panel.visible_wells = visible_wells
        dock.setWindowTitle(window_title)

        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        #self._on_well_panel_activated(dock)
        self.WindowList.append(dock)
        return dock

    def _remove_well_panel_dock(self, dock=None, confirm=True):
        """
        Remove a WellPanelDock from the main window.

        Parameters
        ----------
        dock : WellPanelDock | None
            If None, remove the currently active docked well_panel (if any).
        confirm : bool
            Ask user for confirmation.
        """
        # Resolve dock to remove
        if dock is False:
            dock = None
            for d in self.WindowList:
                if d and d.well_panel is getattr(self, "well_panel", None):
                    dock = d
                    break

        if dock is None:
            QMessageBox.information(self, "Remove well_panel", "No well well_panel selected.")
            return

        if confirm:
            res = QMessageBox.question(
                self,
                "Remove well well_panel",
                f"Close '{dock.title}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return

        # Detach widget safely
        self.removeDockWidget(dock)

        # Clean up tracking
        try:
            self.WindowList.remove(dock)
        except ValueError:
            pass

        # Clear active well_panel if needed
        if getattr(self, "active_well_panel", None) is dock.well_panel:
            self.active_window = self.panel  # fall back to central well_panel

        dock.deleteLater()

    def _on_well_panel_activated(self, dock: WellPanelDock):
        """
        Called whenever a docked well_panel is clicked/focused.
        Sets active well_panel and rebuilds tree (and anything else you want).
        """
        if dock is None or dock.well_panel is None:
            return

        self.panel = dock.well_panel

        #LOG.debug(f"Activated new window")

        self.panel.set_draw_well_panel(False)
        self._set_tree_from_well_panel()
        self.panel.set_draw_well_panel(True)
        #self.panel.draw_well_panel()

        # Optionally bring dock to front/tab
        dock.raise_()

        #LOG.debug ("Activated new window")

        # If you need the tree to reflect active_well_panel view filters, do that here.

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

    def set_layout_params(self, well_gap_factor: float, track_width: float,
                          vertical_scale: float, track_gap_factor: float,
                          gap_proportional_to_distance:bool, gap_distance_ref_m: float,
                          gap_min_factor: float, gap_max_factor: float):
        """Update well_panel layout (gap between wells and track width) and redraw."""
        self.well_gap_factor = max(0.1, float(well_gap_factor))
        self.track_width = max(0.1, float(track_width))
        self.vertical_scale = float(vertical_scale)
        self.gap_proportional_to_distance = bool(gap_proportional_to_distance)
        self.gap_distance_ref_m = float(gap_distance_ref_m)
        self.gap_min_factor = min(0.8,float(gap_min_factor))
        self.gap_max_factor = max(8.0,float(gap_max_factor))
        self.track_gap_factor = float(track_gap_factor)


        self.panel_settings = {"well_gap_factor": self.well_gap_factor, "track_gap_factor": self.track_gap_factor,
                               "track_width": self.track_width, "redraw_requested": self.redraw_requested,
                               "vertical_scale": self.vertical_scale,
                               "gap_proportional_to_distance": self.gap_proportional_to_distance,
                               "gap_distance_ref_m": self.gap_distance_ref_m,
                               "gap_min_factor": self.gap_min_factor,
                               "gap_max_factor": self.gap_max_factor,  # clamp large gaps
                               }
        self.panel.set_panel_settings(self.panel_settings)
        self.panel.draw_well_panel()

    def test_connect(self, pos):
        return True

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
                self.panel.draw_well_panel()

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
                    log_cfg = base_cfg

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
        # # 4) Sync with well_panel and redraw
        # if hasattr(self, "well_panel"):
        #     self.panel.tracks = self.all_tracks
        #     self.panel.draw_well_panel()

    def _move_well(self, well_name: str, direction: int):
        """
        Move a well left/right in well_panel order.

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
        self.panel.draw_well_panel()

    def _delete_well_from_project(self, well_name: str, confirm: bool = True):
        """
        Delete a well from the project by name.

        Removes:
          - the well entry in self.all_wells
        Keeps:
          - tracks (project-wide)
          - stratigraphy (project-wide)
        Then refreshes trees + all well_panels.

        Note: correlations/tops stored inside wells are deleted with the well.
        """
        if not well_name:
            return

        wells = getattr(self, "all_wells", None) or []
        idx = next((i for i, w in enumerate(wells) if w.get("name") == well_name), None)

        if idx is None:
            QMessageBox.information(self, "Delete well", f"Well '{well_name}' not found.")
            return

        if confirm:
            res = QMessageBox.question(
                self,
                "Delete well",
                f"Delete well '{well_name}' from the project?\n\n"
                "This removes the well including its logs, discrete logs, bitmaps and tops.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return

        # Remove well
        wells.pop(idx)

        # If you keep selected/active well name somewhere, clear it
        if getattr(self, "selected_well_name", None) == well_name:
            self.selected_well_name = None

        # If your well_panel keeps visibility filters, remove the deleted well from them
        for p in self._iter_all_well_panels():
            # visible_wells may be set/list/None
            vw = getattr(p, "visible_wells", None)
            if vw is not None:
                try:
                    if isinstance(vw, set):
                        vw.discard(well_name)
                    elif isinstance(vw, list):
                        while well_name in vw:
                            vw.remove(well_name)
                except Exception:
                    pass

            # flatten_depths must match number of wells -> easiest reset
            if hasattr(p, "flatten_depths") and getattr(p, "flatten_depths") is not None:
                # safest: unflatten after structural change
                p.flatten_depths = None

        # Rebuild trees and redraw all well_panels
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()
        if hasattr(self, "_populate_window_tree"):
            self._populate_window_tree()
        if hasattr(self, "_populate_track_tree"):
            self._populate_track_tree()

        if hasattr(self, "_refresh_all_well_panels"):
            self._refresh_all_well_panels()
        else:
            # fallback
            if hasattr(self, "well_panel"):
                self.panel.wells = self.all_wells
                self.panel.draw_well_panel()
        self._redraw_all_panels()

    def _iter_all_well_panels(self):
        """
        Yield central well_panel + dock well_panels (if available).
        """
        if hasattr(self, "well_panel") and self.panel is not None:
            yield self.panel
        for dock in getattr(self, "_well_panel_docks", []) or []:
            if dock and getattr(dock, "well_panel", None) is not None:
                yield dock.well_panel

    def _on_tree_context_menu(self, pos):
        """
        Show a context menu for logs in the tree:
          - logs under the 'Logs' folder
          - logs under each track in the 'Tracks' folder
        """
        item = self.well_tree.itemAt(pos)
        menu = QMenu(self)
        if item is None:
            return

        global_pos = self.well_tree.viewport().mapToGlobal(pos)
        parent = item.parent()
        data = item.data(0, Qt.UserRole)
        parent_data = parent.data(0, Qt.UserRole) if parent else None

        print (item, data)
        print (parent, parent_data)

        if item is self.well_root_item:
            #menu = QMenu(self)

            act_add_well = menu.addAction("Add new well...")
            act_edit_all_wells = menu.addAction("Edit all well settings ...")

            chosen = menu.exec_(global_pos)

            if chosen == act_add_well:
                self._action_add_new_well()
            elif chosen == act_edit_all_wells:
                self._action_edit_all_wells()
            return

        if parent is self.well_root_item:
            #menu = QMenu(self)

            well_name = item.text(0)
            act_edit_well = menu.addAction(f"Edit well '{well_name}'...")
            act_left = menu.addAction(f"Move well left '{well_name}'...")
            act_right = menu.addAction(f"Move well right '{well_name}'...")
            act_load_bitmap = menu.addAction(f"Load bitmap '{well_name}'...")
            act_delete_well = menu.addAction(f"Delete well '{well_name}'...")
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
                self._action_load_core_bitmap_to_well(default_well_name=well_name)
            if chosen == act_delete_well:
                self._delete_well_from_project(well_name, confirm = True)

        if isinstance(data, tuple) and len(data) == 3 and data[0] == "Bitmap":
            #menu = QMenu(self)
            _, well_name, bitmap_key = data
            act_del = menu.addAction(f"Delete bitmap from well {well_name}")
            chosen = menu.exec_(self.well_tree.viewport().mapToGlobal(pos))
            if chosen == act_del:
                if well_name and bitmap_key:
                    self._delete_bitmap_from_well(well_name, bitmap_key, confirm=True)
                elif not well_name:
                    for well in self.all_wells:
                        self._delete_bitmap_from_well(well.get("name"), bitmap_key, confirm=True)
            return

        if isinstance(data, tuple) and len(data) == 3 and data[0] == "well_log":
            _, well_name, log_name = data

            act_edit = menu.addAction("Edit log data (table)…")
            chosen = menu.exec_(self.well_tree.viewport().mapToGlobal(pos))
            if chosen == act_edit:
                self._edit_well_log_table(well_name, log_name)
            return


        # --- case 1: logs under "Logs" folder ---
        if parent is self.continous_logs_folder:
            log_name = item.data(0, Qt.UserRole) or item.text(0)
            if not log_name:
                return
            #menu = QMenu(self)
            act_edit = menu.addAction(f"Edit display settings for '{log_name}'...")
            chosen = menu.exec_(global_pos)
            if chosen == act_edit:
                self._edit_log_display_settings(log_name)
            return
        if parent is self.bitmaps_folder:
            bitmap_name = item.data(0, Qt.UserRole) or item.text(0)
            if not bitmap_name:
                return
            #menu = QMenu(self)
            act_edit = menu.addAction(f"Edit bitmap position'{bitmap_name}'...")
            act_del = menu.addAction("Delete bitmap…")

            chosen = menu.exec_(global_pos)
            if chosen == act_edit:
                self._action_edit_bitmap_positions(track_name=bitmap_name)
            if chosen == act_del:
                for well in self.all_wells:
                    self._delete_bitmap_from_well(well.get("name"), bitmap_name, confirm=True)

        if item is self.well_tops_folder:
            #menu = QMenu(self)

            act_edit_stratigraphy = menu.addAction("Edit well tops ...")
            chosen = menu.exec_(global_pos)

            if chosen == act_edit_stratigraphy:
                self._action_edit_stratigraphy()
            return

        if item is self.track_root_item:
            track_name = item.text(0)

            if not track_name:
                return

            #menu = QMenu(self)

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

            for track in self.all_tracks:
                if track.get("name") == track_name:
                    track_cfg = track
                    break

            #menu = QMenu(self)
            act_delete_track = menu.addAction(f"Delete Track '{track_name}'...")
            if track.get("type") == "discrete":
                #menu = QMenu(self)
                act_edit_disc_colors = menu.addAction(f"Edit discrete track colors '{track_name}'...")
                chosen = menu.exec_(global_pos)
                if chosen == act_edit_disc_colors:
                    self._action_edit_discrete_colors_for_track(track_name)
            elif track.get("type") == "bitmap":
                #menu = QMenu(self)
                act_add_core_bitmap = menu.addAction(f"Load core bitmap into '{track_name}'...")
                act_edit_bitmap_track = menu.addAction(f"Edit bitmap position'{track_name}'...")
                act_delete_all = menu.addAction("Delete all bitmaps for this track…")
                chosen = menu.exec_(global_pos)
                if chosen == act_add_core_bitmap:
                    self._action_load_bitmap_into_bitmap_track(track_name)
                elif chosen == act_edit_bitmap_track:
                    self._action_edit_bitmap_positions(track_name=track_name)
                elif chosen == act_delete_all:
                    self._delete_bitmaps_for_bitmap_track(track_name, confirm=True)
            elif track.get("type") == "continuous":
                #menu = QMenu(self)
                act_edit = menu.addAction(f"Edit display settings for '{track_name}'...")
                act_add_log = menu.addAction(f"Add new log to track ...")
                chosen = menu.exec_(global_pos)
                if chosen == act_edit:
                    #self._edit_log_display_settings(track_name)
                    self._action_edit_track_settings(track_name)
                    menu.close()
                elif chosen == act_add_log:
                    self._action_add_log_to_track()
            elif track.get("type") == "lithofacies":
                #menu = QMenu(self)
                act_edit_lithofacies_settings = menu.addAction("Edit lithofacies track settings ...")
                chosen = menu.exec_(global_pos)
                if chosen == act_edit_lithofacies_settings:
                    self._action_edit_lithofacies_settings_for_track(track_name)

            chosen = menu.exec_(global_pos)
            if chosen == act_delete_track:
                self._action_delete_track()

            return




        # other nodes (wells, tops folders, etc.) → no context menu for logs

    def _refresh_all_well_panels(self):
        # central well_panel
        if self.dock.type == "WellSection":
            self.panel.wells = self.all_wells
            self.panel.tracks = self.all_tracks
            self.panel.stratigraphy = self.all_stratigraphy
            self.panel.panel_settings = self.panel_settings
        #            self.panel.draw_well_panel()

        # docked well_panels
        for dock in list(self.WindowList):
            if dock.type=="WellSection":
                dock.well_panel.wells = self.all_wells
                dock.well_panel.tracks = self.all_tracks
                dock.well_panel.stratigraphy = self.all_stratigraphy
                dock.well_panel.panel_settings = self.panel_settings
                wlist = []
                for well in dock.well_panel.wells:
                    name = well.get("name")
                    wlist.append(name)
                visible_wells=[]
                vw = dock.well_panel.visible_wells
                for w in wlist:
                    for v in vw:
                        if v == w:
                            visible_wells.append(v)

                dock.well_panel.visible_wells=visible_wells

    def _on_window_item_changed(self, item, column):
        """Called when a window is checked/unchecked in the tree."""
        print(f"Window item changed: {item.text(0)}")

        win_name = item.data(0, Qt.UserRole)

        if win_name is None:
            return

        print (f"Window item changed: {win_name}")

        state = item.checkState(0)

        for win in self.WindowList:
            if win.title == win_name:
                if state == Qt.Checked:
                    win.setVisible(True)
                #            _on_well_panel_activated(self.WindowList[win_name])
                else:
                    win.setVisible(False)

        win_title = item.data(0, Qt.UserRole)
        new_title = item.text(0).strip()

        if win_title !=new_title:
            print(f"change the name of the window!:{win_title}, {new_title}")
            for win in self.WindowList:
                if win.title == win_title:
                    win.set_title(new_title)
            self._populate_window_tree()

    def _on_window_tree_context_menu(self, pos=None):
        """Show a context menu for the tree."""

        menu = QMenu(self)

        if pos is None:
            return

        item = self.window_tree.itemAt(pos)
        if item is None:
            return

        global_pos = self.window_tree.viewport().mapToGlobal(pos)

        if item == self.window_root:
            #menu = QMenu(self)
            act_add_window = menu.addAction("Add new well section window...")
            chosen = menu.exec_(global_pos)
            if chosen == act_add_window:
                #print("Add new window...")
                self._action_add_well_panel_dock()
        elif item.parent() == self.window_root:
            data = item.data(0, Qt.UserRole)
            type = item.data(1, Qt.UserRole)
            print (data)
            #menu = QMenu(self)
            window_name = item.text(0)
            act_delete_window = menu.addAction(f"Delete window '{window_name}'...")
            if type == "WellSection":
                act_edit_window = menu.addAction(f"Edit wells in section '{window_name}'...")

            if type == "MapWindow":
                act_edit_window = menu.addAction(f"Edit map settings for '{window_name}'...")

            chosen = menu.exec_(global_pos)
            if chosen == act_delete_window:
                #print("Delete window...")
                dock = self.get_dock_by_title(item.text(0))
                self._remove_well_panel_dock(dock)
                self._populate_window_tree()

            if type == "WellSection":
                if chosen == act_edit_window:
                    dock = self.get_dock_by_title(item.text(0))
                    self._action_edit_panel_wells(dock)
            elif type == "MapWindow":
                if chosen == act_edit_window:
                    dock = self.get_dock_by_title(item.text(0))
                    self._action_edit_map_settings(dock)


        parent = item.parent()
#        chosen = self.window_tree.contextMenuEvent(QContextMenuEvent(global_pos))

    def _dock_layout_snapshot(self) -> dict:
        """
        Serialize dock layout (positions + tabbing) into a JSON-friendly dict.
        Uses QMainWindow.saveState/saveGeometry (encoded as base64 strings).
        Also stores an explicit tab-group listing for transparency/debugging.

        Returns:
          {
            "geometry_b64": "...",
            "state_b64": "...",
            "tab_groups": [["DockA","DockB"], ["DockC","DockD","DockE"]],
          }
        """
        # Qt binary blobs
        geom: QByteArray = self.saveGeometry()
        state: QByteArray = self.saveState(version=1)

        geometry_b64 = base64.b64encode(bytes(geom)).decode("ascii")
        state_b64 = base64.b64encode(bytes(state)).decode("ascii")

        # Explicit tab groups (optional but useful)
        tab_groups = self._get_tabified_groups()

        return {
            "geometry_b64": geometry_b64,
            "state_b64": state_b64,
            "tab_groups": tab_groups,
        }

    def _get_tabified_groups(self) -> list[list[str]]:
        """
        Returns a list of tab groups. Each group is a list of dock objectNames
        that are tabified together.

        Qt itself already stores this in saveState(); this is extra metadata.
        """
        docks = self.findChildren(QDockWidget)
        visited = set()
        groups = []

        for d in docks:
            if d.objectName() in visited:
                continue

            # tabifiedDockWidgets() returns widgets tabbed with 'd'
            tabs = list(self.tabifiedDockWidgets(d))
            if not tabs:
                # single dock; still track it as visited
                visited.add(d.objectName())
                continue

            group = [d] + tabs
            names = []
            for g in group:
                nm = g.objectName()
                if nm:
                    names.append(nm)
                    visited.add(nm)

            # normalize order & dedupe
            names = list(dict.fromkeys(names))
            if len(names) >= 2:
                groups.append(names)

        # normalize groups (sorted by first name) for stable JSON diffs
        groups.sort(key=lambda x: x[0] if x else "")
        return groups

    def _dock_layout_restore(self, layout: dict) -> bool:
        """
        Restore dock layout from dict produced by _dock_layout_snapshot().

        IMPORTANT:
          - QDockWidgets must already exist with correct objectName().
          - Call after you have created your WellPanelDock widgets.

        Returns True if restore seems successful.
        """
        if not layout:
            return False

        geometry_b64 = layout.get("geometry_b64")
        state_b64 = layout.get("state_b64")
        if not geometry_b64 or not state_b64:
            return False

        try:
            geom = QByteArray(base64.b64decode(geometry_b64.encode("ascii")))
            state = QByteArray(base64.b64decode(state_b64.encode("ascii")))
        except Exception:
            return False

        ok_geom = self.restoreGeometry(geom)
        ok_state = self.restoreState(state, version=1)

        # Optional: if you also want to enforce tab groups explicitly,
        # you can apply them after restore (usually not needed).
        # self._apply_tab_groups(layout.get("tab_groups", []))

        return bool(ok_geom and ok_state)

    def get_dock_by_title(self, title: str):
        """Return a dock widget by title."""
        for window in self.WindowList:
            if window.title == title:
                return window
        return None

    def _get_window_list(self):
        window_list = []
        window_dict = {}

        for window in self.WindowList:
            panel = window.get_panel()
            panel_settings = getattr(panel, "panel_settings", None)
            # print(panel_settings)
            title = window.title
            visible = window.get_visible()
            floating = window.isFloating()

            # print(title)
            if window.type == "WellSection":
                visible_tops = getattr(window.well_panel, "visible_tops", None)
                visible_logs = getattr(window.well_panel, "visible_logs", None)
                visible_tracks = getattr(window.well_panel, "visible_tracks", None)
                visible_wells = getattr(window.well_panel, "visible_wells", None)
                window_dict = {"type": "WellSection", "visible": visible, "floating": floating,
                               "window_title": title, "visible_tops": visible_tops,
                               "visible_logs": visible_logs, "visible_tracks": visible_tracks,
                               "visible_wells": visible_wells, "panel_settings": panel_settings}
                # print(window_dict)
                window_list.append(window_dict)
            elif window.type == "MapWindow":
                profiles = window.panel.profiles
                wells = window.panel.wells
                window_dict = {"type": "MapWindow", "visible": visible, "floating": floating,
                               "window_title": title, "panel_settings": panel_settings, "profiles": profiles,
                               "wells": wells}
                window_list.append(window_dict)

        return window_list

    def _delete_bitmap_from_well(self, well_name: str, bitmap_key: str, confirm: bool = True):
        """
        Delete a bitmap with given key from a single well.
        """
        if not well_name or not bitmap_key:
            return

        well = next((w for w in getattr(self, "all_wells", []) if w.get("name") == well_name), None)
        if well is None:
            QMessageBox.information(self, "Delete bitmap", f"Well '{well_name}' not found.")
            return

        bm = (well.get("bitmaps") or {})
        if bitmap_key not in bm:
            QMessageBox.information(self, "Delete bitmap", f"No bitmap '{bitmap_key}' in well '{well_name}'.")
            return

        if confirm:
            res = QMessageBox.question(
                self,
                "Delete bitmap",
                f"Delete bitmap '{bitmap_key}' from well '{well_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return

        try:
            del bm[bitmap_key]
            # clean empty container
            if not bm:
                well.pop("bitmaps", None)
        except Exception as e:
            QMessageBox.critical(self, "Delete bitmap", f"Failed to delete bitmap:\n{e}")
            return

        if hasattr(self, "_refresh_all_well_panels"):
            self._refresh_all_well_panels()
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _delete_bitmap_key_from_all_wells(self, bitmap_key: str, confirm: bool = True):
        """
        Delete a bitmap key from ALL wells (useful for 'delete track images').
        """
        if not bitmap_key:
            return

        wells = getattr(self, "all_wells", []) or []
        hits = []
        for w in wells:
            bm = (w.get("bitmaps") or {})
            if bitmap_key in bm:
                hits.append(w.get("name", "<unnamed>"))

        if not hits:
            QMessageBox.information(self, "Delete bitmaps", f"No wells contain bitmap '{bitmap_key}'.")
            return

        if confirm:
            res = QMessageBox.question(
                self,
                "Delete bitmaps",
                f"Delete bitmap '{bitmap_key}' from {len(hits)} well(s)?\n\n"
                + "\n".join(hits[:15]) + ("\n…" if len(hits) > 15 else ""),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return

        for w in wells:
            bm = (w.get("bitmaps") or {})
            if bitmap_key in bm:
                del bm[bitmap_key]
                if not bm:
                    w.pop("bitmaps", None)

        if hasattr(self, "_refresh_all_well_panels"):
            self._refresh_all_well_panels()
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _delete_bitmaps_for_bitmap_track(self, track_name: str, confirm: bool = True):
        """
        Resolve bitmap key from bitmap track and delete it from all wells.
        """
        track = next((t for t in getattr(self, "tracks", []) if t.get("name") == track_name), None)
        if track is None or "bitmap" not in track:
            QMessageBox.information(self, "Delete bitmaps", "Selected track is not a bitmap track.")
            return

        key = (track.get("bitmap") or {}).get("key")
        if not key:
            QMessageBox.warning(self, "Delete bitmaps", "Bitmap track has no bitmap key.")
            return

        self._delete_bitmap_key_from_all_wells(key, confirm=confirm)

    def _available_log_names(self) -> list[str]:
        names = set()
        for w in getattr(self, "all_wells", []) or []:
            for ln in (w.get("logs", {}) or {}).keys():
                names.add(ln)
        return sorted(names)

    def _action_edit_track_settings(self, track_name: str):
        track = next((t for t in self.all_tracks if t.get("name") == track_name), None)
        if track is None:
            return

        dlg = TrackSettingsDialog(self, track, available_logs=self._available_log_names())
        if dlg.exec_() == QDialog.Accepted:
            self.panel_settings["redraw_requested"]=False
            # redraw / refresh
            if hasattr(self, "_refresh_all_well_panels"):
                self._refresh_all_well_panels()
            if hasattr(self, "_populate_well_track_tree"):
                self._populate_well_track_tree()
            self.panel_settings["redraw_requested"] = True
            self.panel.draw_well_panel()

    def _edit_well_log_table(self, well_name: str, log_name: str):
        wells = getattr(self, "all_wells", []) or []
        well = next((w for w in wells if w.get("name") == well_name), None)
        if well is None:
            QMessageBox.warning(self, "Edit log", f"Well '{well_name}' not found.")
            return

        logs = well.get("logs", {}) or {}
        log_def = logs.get(log_name)
        if log_def is None:
            QMessageBox.warning(self, "Edit log", f"Log '{log_name}' not found in well '{well_name}'.")
            return

        depth = log_def.get("depth", [])
        data = log_def.get("data", [])

        dlg = EditWellLogTableDialog(self, well_name, log_name, depth, data)
        if dlg.exec_() != QDialog.Accepted:
            return

        new_depth, new_data = dlg.result_arrays()
        if new_depth is None:
            return

        # Update model
        log_def["depth"] = new_depth
        log_def["data"] = new_data
        logs[log_name] = log_def
        well["logs"] = logs

        # Redraw + rebuild tree if you show log stats/availability
        if hasattr(self, "_refresh_all_well_panels"):
            self._refresh_all_well_panels()
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()

    def _new_project(self, confirm: bool = True):
        """
        Reset the application state for a new project:
          - clears all data (wells/tracks/stratigraphy)
          - closes/removes all extra well_panel docks
          - resets central well_panel state/filters
          - rebuilds trees and redraws

        Call this from File → New project...
        """
        if confirm:
            res = QMessageBox.question(
                self,
                "New project",
                "Start a new project?\n\n"
                "This will clear wells, logs, tops, tracks, bitmaps and close all well_panel windows.\n"
                "Unsaved changes will be lost.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if res != QMessageBox.Yes:
                return

        # ---- 1) clear core project data ----
        wells, tracks, stratigraphy = create_dummy_data()

        wells.test_class()

        self.all_wells = wells
        self.all_stratigraphy = stratigraphy
        self.all_tracks = tracks

        self.all_logs = None
        self.all_discrete_logs = None
        self.all_bitmaps = None

        self.well_gap_factor = 3.0
        self.track_gap_factor = 1.0
        self.track_width = 1.0
        self.vertical_scale = 2.0

        window_name = "Well Section 1"

        self.panel_settings = {"well_gap_factor": self.well_gap_factor, "track_gap_factor": self.track_gap_factor,
                               "track_width": self.track_width, "redraw_requested": self.redraw_requested,
                               "vertical_scale": self.vertical_scale
                               }

        # Optional: clear any additional project-level state
        for attr in (
            "_last_project_path",
            "_project_path",
            "_project_name",
        ):
            if hasattr(self, attr):
                setattr(self, attr, None)

        # ---- 2) close/remove all docked well_panels ----
        # Keep central well_panel; remove all dock well_panels
        for dock in list(getattr(self, "WindowList", []) or []):
            try:
                self.removeDockWidget(dock)
            except Exception:
                pass
            try:
                dock.setParent(None)
                dock.deleteLater()
            except Exception:
                pass

        self.WindowList = []

        self.dock = WellPanelDock(
            parent=self,
            wells=self.all_wells,
            tracks=self.all_tracks,
            stratigraphy=self.all_stratigraphy,
            panel_settings=self.panel_settings
        )
        self.dock.activated.connect(self._on_well_panel_activated)

        # self.tabifiedDockWidgetActivated.connect(self.window_activate)

        self.dock.well_panel.active_well_panel = True
        self.panel = self.dock.well_panel

        self.WindowList = []

        self.active_window = self.dock

        self.WindowList.append(self.active_window)



        # ---- 3) reset central well_panel view state/filters ----
        if hasattr(self, "well_panel") and self.panel is not None:
            p = self.panel
            p.wells = self.all_wells
            p.tracks = self.all_tracks
            p.stratigraphy = self.all_stratigraphy

            # clear common per-well_panel state
            for attr, default in (
                ("visible_wells", None),
                ("visible_tracks", None),
                ("visible_logs", None),
                ("visible_bitmaps", None),
                ("visible_discrete_logs", None),
                ("visible_tops", None),
                ("flatten_depths", None),
                ("depth_window", None),
                ("highlight_top", None),
                ("_active_pick_context", None),
                ("_bitmap_pick_ctx", None),
                ("_in_dialog_pick_mode", False),
            ):
                if hasattr(p, attr):
                    setattr(p, attr, default)

            # disconnect any lingering mpl event connections (optional safety)
            for cid_attr in ("_dialog_pick_cid", "_motion_pick_cid", "_bitmap_pick_cid", "_scroll_cid"):
                if hasattr(p, cid_attr):
                    cid = getattr(p, cid_attr)
                    if cid is not None and hasattr(p, "canvas"):
                        try:
                            p.canvas.mpl_disconnect(cid)
                        except Exception:
                            pass
                    setattr(p, cid_attr, None)

            # re-enable desired event handlers if you use them
            if hasattr(p, "enable_track_mouse_scrolling"):
                p.enable_track_mouse_scrolling()

            # redraw (empty)
            if hasattr(p, "draw_well_panel"):
                p.draw_well_panel()

        # ---- 4) rebuild UI trees ----
        if hasattr(self, "_populate_well_tree"):
            self._populate_well_tree()
        if hasattr(self, "_populate_well_track_tree"):
            self._populate_well_track_tree()
        if hasattr(self, "_populate_well_tops_tree"):
            self._populate_well_tops_tree()
        if hasattr(self, "_populate_window_tree"):
            self._populate_window_tree()
        if hasattr(self, "_populate_well_log_tree"):
            self._populate_well_log_tree()

        # ---- 5) refresh well_panels if you prefer centralized refresh ----
        if hasattr(self, "_refresh_all_well_panels"):
            self._refresh_all_well_panels()

        # Optional: update window title
        self.setWindowTitle("PyWellSection — New Project")

    def _get_visible_wells_for_well_panel(self, well_panel):
        """
        Return wells shown in that well_panel in display order (left->right).
        Adjust if you maintain a visible_wells filter.
        """
        wells = getattr(well_panel, "wells", []) or []

        # If you have a visibility filter:
        vw = getattr(well_panel, "visible_wells", None)
        if vw is not None:
            wells = [w for w in wells if w.get("name") in vw]

        return wells

    def _build_section_profiles(self):
        """
        Return list of profiles derived from each dock well_panel:
          [{"name": "<well_panel title>", "points": [(x,y), ...]}, ...]
        """
        profiles = []

        # include central well_panel too if desired
        candidates = []
        if hasattr(self, "panel") and self.panel is not None:
            candidates.append((self.dock.title, self.panel))

        for dock in self.WindowList:
            if dock.type == "WellSection":
                candidates.append((dock.title or "Panel", dock.well_panel))

        for name, well_panel in candidates:
            wells = self._get_visible_wells_for_well_panel(well_panel)
            pts = []
            for w in wells:
                x, y = w.get("x"), w.get("y")
                if x is None or y is None:
                    continue
                try:
                    pts.append((float(x), float(y)))
                except Exception:
                    pass
            if len(pts) >= 2:
                profiles.append({"name": name, "points": pts})

        return profiles

    def _open_map_window(self):
        self.all_profiles = self._build_section_profiles()
        dock = MapDockWindow(parent = self,
                             wells = self.all_wells,
                             profiles = self.all_profiles,
                             map_layout_settings =  self.map_panel_settings,
                             title=f"Map {len(self.WindowList) + 1}")

        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.WindowList.append(dock)
        self._update_map_windows()

        if hasattr(self, "_populate_window_tree"):
            self._populate_window_tree()

    def _update_map_windows(self):
        wells = getattr(self, "all_wells", []) or []
        self.all_profiles = self._build_section_profiles()

        for d in list(getattr(self, "WindowList", []) or []):
            try:
                if d.type == "MapWindow":
                    d.set_data(wells, self.all_profiles)
                    d.draw_map()
            except Exception:
                pass