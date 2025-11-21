from PyQt5.QtWidgets import (
    QDockWidget, QTreeWidget,
    QTreeWidgetItem, )

from PyQt5.QtCore import Qt
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel("INFO")

def setup_well_widget_tree(self):
    ### --- Define the Input Tree ###
    self.well_tree = QTreeWidget(self)
    self.well_tree.setHeaderHidden(True)
    self.well_tree.itemChanged.connect(self._on_well_tree_item_changed)
    self.well_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.well_tree.customContextMenuRequested.connect(self._on_tree_context_menu)

    LOG.info("Setting up well tree")


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
    self.well_tree.addTopLevelItem(self.well_logs_folder)

    # --- Folder: Tracks (structure only, not necessarily checkable) ---
    self.track_root_item = QTreeWidgetItem(["Tracks"])
    # structure only -> no checkboxes needed, but selectable/enabled
    self.track_root_item.setFlags(
        self.track_root_item.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.track_root_item.setCheckState(0, Qt.Checked)
    self.well_tree.addTopLevelItem(self.track_root_item)

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
    self._populate_well_track_tree()


