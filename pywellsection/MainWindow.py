from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QMessageBox, QDockWidget, QWidget, QVBoxLayout, QTreeWidget,
    QTreeWidgetItem, QPushButton, QHBoxLayout, QSizePolicy, QLineEdit, QTextEdit, QTableWidget,
    QTableWidgetItem,)
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from pywellsection.Qt_Well_Widget import WellPanelWidget
from pywellsection.sample_data import create_dummy_data
from pywellsection.io_utils import export_project_to_json, load_project_from_json, load_petrel_wellheads
from pywellsection.widgets import QTextEditLogger, QTextEditCommands
from pywellsection.console import QIPythonWidget

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

        self.panel = WellPanelWidget(wells, tracks, stratigraphy)
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

        ### --- Define the Input Tree ###
        self.well_tree = QTreeWidget(self)
        self.well_tree.setHeaderHidden(True)
        self.well_tree.itemChanged.connect(self._on_well_tree_item_changed)

        # 👇 create the folder item once
        self.well_root_item = QTreeWidgetItem(["Wells"])
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

        self.well_tops_folder = QTreeWidgetItem(["Tops"])
        # tristate so checking it checks/unchecks children
        self.well_tops_folder.setFlags(
            self.well_tops_folder.flags()
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsTristate
            | Qt.ItemIsSelectable
            | Qt.ItemIsEnabled
        )
        self.well_tops_folder.setCheckState(0, Qt.Checked)
        self.well_tree.addTopLevelItem(self.well_tops_folder)

        self.well_logs_folder = QTreeWidgetItem(["Logs"])
        # tristate so checking it checks/unchecks children
        self.well_logs_folder.setFlags(
            self.well_logs_folder.flags()
            | Qt.ItemIsUserCheckable
            | Qt.ItemIsTristate
            | Qt.ItemIsSelectable
            | Qt.ItemIsEnabled
        )
        self.well_logs_folder.setCheckState(0, Qt.Checked)
        #self.well_root_item.addChild(self.well_logs_folder)
        self.well_tree.addTopLevelItem(self.well_logs_folder)


        ### Setup the Dock

        self.well_dock = QDockWidget("Input Data", self)
        self.well_dock.setObjectName("Input")
        self.well_dock.setWidget(self.well_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.well_dock)


        self.splitDockWidget(self.well_dock, self.dock_panel, Qt.Horizontal)
        self.splitDockWidget(self.dock_panel, self.dock_console, Qt.Vertical)
        self.resizeDocks([self.dock_panel, self.dock_console], [4, 1], Qt.Vertical)

        self.tabifyDockWidget(self.dock_console, self.dock_commands)
        self.tabifyDockWidget(self.dock_commands, self.dock_logger)
        self.dock_console.raise_()



        # --- intial build of the well tree
        self._populate_well_tree()
        self._populate_well_tops_tree()
        self._populate_well_log_tree()
        # ---- build menu bar ----
        self._create_menubar()

    # ------------------------------------------------
    # MENU BAR SETUP
    # ------------------------------------------------
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

        # --- Help menu (unchanged) ---
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("About...", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)


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
            self.all_stratigraphy = []
            self.all_tracks = tracks

            self.all_wells = wells

            stratigraphy=self.all_stratigraphy

            for well in wells:
                tops = well.get("tops")
                if tops:
                    for top in tops:
                        if top in stratigraphy:
                            continue
                        else:
                            stratigraphy.append(top)
                else:
                    print("No tops found")

            self.all_stratigraphy = stratigraphy


            # populate well tree
            self._populate_well_tree()
            self._populate_well_tops_tree()
            self._populate_well_log_tree()

#            self._rebuild_visible_tops_from_tree()

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

        except Exception as e:
            QMessageBox.critical(self, "Import error", f"Failed to import:\n{e}")

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

        self._populate_well_tree()  # initial fill

        self.well_dock.setWidget(self.well_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.well_dock)

    def _populate_well_tree(self):
        """Rebuild the tree from self.all_wells, preserving selections if possible."""
        # Remember current selection by name
        prev_selected = set()
        root = self.well_root_item
        for i in range(root.childCount()):
            it = root.child(i)
            if it.checkState(0) == Qt.Checked:
                prev_selected.add(it.data(0, Qt.UserRole))

        self.well_tree.blockSignals(True)

        # remove all wells under the folder
        root.takeChildren()

        # add wells as children of "All wells"
        for w in self.all_wells:
            name = w.get("name") or "UNKNOWN"
            it = QTreeWidgetItem([name])
            it.setFlags(
                it.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
            )
            it.setData(0, Qt.UserRole, name)

            # default: keep previous selection; else checked
            if not prev_selected:
                state = Qt.Checked
            else:
                state = Qt.Checked if name in prev_selected else Qt.Unchecked
            it.setCheckState(0, state)

            root.addChild(it)

        self.well_tree.blockSignals(False)

        # Apply current selection to panel
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
                state = Qt.Checked if name in prev_selected else Qt.Unchecked
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
        for track in self.all_tracks:
            for log_cgf in track.get("logs",[]):
                name = log_cgf.get("log")
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


