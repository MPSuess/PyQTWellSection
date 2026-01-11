from PyQt5.QtWidgets import (
    QDockWidget, QTreeWidget,
    QTreeWidgetItem, )

from PyQt5.QtCore import Qt
import logging

LOG = logging.getLogger(__name__)
LOG.setLevel("INFO")

def setup_window_tree(self):
    self.window_tree = QTreeWidget(self)
    self.window_tree.setHeaderHidden(True)
    self.window_tree.itemChanged.connect(self._on_window_item_changed)
    self.window_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.window_tree.customContextMenuRequested.connect(self._on_window_tree_context_menu)

    # 👇 create the folder item once
    self.window_root = QTreeWidgetItem(["Windows"])
    # tristate so checking it checks/unchecks children
    self.window_root.setFlags(
        self.window_root.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.window_root.setCheckState(0, Qt.Unchecked)
    self.window_tree.addTopLevelItem(self.window_root)


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

    self.well_root_item.setCheckState(0, Qt.Unchecked)
    self.well_tree.addTopLevelItem(self.well_root_item)

    self.well_tops_folder = QTreeWidgetItem(["Well Tops"])
    # tristate so checking it checks/unchecks children
    self.well_tops_folder.setFlags(
        self.well_tops_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )

    self.well_tops_folder.setCheckState(0, Qt.Unchecked)
    self.well_tree.addTopLevelItem(self.well_tops_folder)

    self.stratigraphy_root = QTreeWidgetItem(["Stratigraphy"])
    self.stratigraphy_root.setFlags(
        self.stratigraphy_root.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.stratigraphy_root.setCheckState(0, Qt.Unchecked)
    self.well_tops_folder.addChild(self.stratigraphy_root)

    self.faults_root = QTreeWidgetItem(["Faults"])
    self.faults_root.setFlags(
        self.faults_root.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.faults_root.setCheckState(0, Qt.Unchecked)
    self.well_tops_folder.addChild(self.faults_root)

    self.other_root = QTreeWidgetItem(["Other"])
    self.other_root.setFlags(
        self.other_root.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.other_root.setCheckState(0, Qt.Unchecked)
    self.well_tops_folder.addChild(self.other_root)

    self.well_logs_folder = QTreeWidgetItem(["Logs"])
    # tristate so checking it checks/unchecks children
    self.well_logs_folder.setFlags(
        self.well_logs_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )

    self.well_logs_folder.setCheckState(0, Qt.Unchecked)
#    self.well_root_item.addChild(self.well_logs_folder)
    self.well_tree.addTopLevelItem(self.well_logs_folder)

    self.continous_logs_folder = QTreeWidgetItem(["Continous Logs"])
    self.continous_logs_folder.setFlags(
        self.continous_logs_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.continous_logs_folder.setCheckState(0, Qt.Unchecked)
    self.well_logs_folder.addChild(self.continous_logs_folder)

    self.discrete_logs_folder = QTreeWidgetItem(["Discrete Logs"])
    self.discrete_logs_folder.setFlags(
        self.discrete_logs_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.discrete_logs_folder.setCheckState(0, Qt.Unchecked)
    self.well_logs_folder.addChild(self.discrete_logs_folder)

    self.bitmaps_folder = QTreeWidgetItem(["Bitmaps"])
    self.bitmaps_folder.setFlags(
        self.bitmaps_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.bitmaps_folder.setCheckState(0, Qt.Unchecked)
    self.well_logs_folder.addChild(self.bitmaps_folder)



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
    self.track_root_item.setCheckState(0, Qt.Unchecked)
    self.well_tree.addTopLevelItem(self.track_root_item)




