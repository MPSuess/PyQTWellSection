from PySide6.QtWidgets import (
    QDockWidget, QTreeWidget,
    QTreeWidgetItem)

from PySide6 import QtWidgets, QtCore, QtGui

from PySide6.QtCore import Qt

import logging

from shiboken6 import isValid

LOG = logging.getLogger(__name__)
LOG.setLevel("INFO")

# ---- Checkability policy ----
LEAF_ALWAYS_CHECKABLE = 1
LEAF_NEVER_CHECKABLE = 2

_CHECK_POLICY_ROLE = QtCore.Qt.UserRole + 200

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
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.window_root.setCheckState(0, Qt.Unchecked)
    self.window_tree.addTopLevelItem(self.window_root)

def setup_input_tree(self, root_label=None):
    self.input_tree = CheckableTree(self)
    self.input_tree.setHeaderHidden(True)
    setup_well_tree(self)
    connect_input_tree(self)


def connect_input_tree(self):
    self.input_tree.parentToggled.connect(self.on_parent_toggled)
    #self.input_tree.itemToggled.connect(self.on_item_toggled)
    self.input_tree.itemToggled.connect(self.on_leaf_toggled)
    self.input_tree.contextAction.connect(self.on_context_action)
    # self.input_tree.structureChanged.connect(self.on_structure_changed)
    self.input_tree.contextMenuEvent.connect(self.on_input_tree_context_menu)
    self.input_tree.itemDoubleClicked.connect(self.on_double_click)

    self.input_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.input_tree.customContextMenuRequested.connect(self._on_window_tree_context_menu)
    on_tree_loaded(self)

def on_tree_loaded(self):
    descendents = self.input_tree.get_items_in_folder(self.input_tree.invisibleRootItem(), recursive=True)
    for d in descendents:
        data = d.data(0, Qt.UserRole)
        if data and len(data) > 2:
            if data[2] == "Folder":
                if data[0]=="Wells":
                    self.c_well_folder = d
                if data[0]=="Tops":
                    self.c_well_tops_folder = d
                if data[0]=="Logs":
                    self.c_well_logs_folder = d
                if data[0]=="Tracks":
                    self.c_well_track_folder = d


    descendents = self.input_tree.get_items_in_folder(self.c_well_tops_folder, recursive=False)
    if len(descendents) > 0:
        for d in descendents:
            data = d.data(0, Qt.UserRole)
            if len(data) > 2:
                if data[2] == "Subfolder":
                    if data[1]=="Faults":
                        self.c_faults_root = d
                    if data[1]=="Stratigraphy":
                        self.c_stratigraphy_root = d
                    if data[1]=="Other":
                        self.c_other_root = d

    descendents = self.input_tree.get_items_in_folder(self.c_well_logs_folder, recursive=False)
    if len(descendents) > 0:
        for d in descendents:
            data = d.data(0, Qt.UserRole)
            if len(data) > 2:
                if data[2] == "Subfolder":
                    if data[1]=="continuous":
                        self.cont_folder = d
                    if data[1]=="discrete":
                        self.disc_folder = d
                    if data[1]=="bitmap":
                        self.bmp_folder = d
    return



def setup_well_tree(self):

    #High Level Folder
    self.c_well_folder = self.input_tree.add_root("Wells")
    self.c_well_tops_folder = self.input_tree.add_root("Wells Tops")
    self.c_well_logs_folder = self.input_tree.add_root("Logs")
    self.c_well_track_folder = self.input_tree.add_root("Tracks")

    # Subfolders
    # The Well Tops entries
    self.c_stratigraphy_root = self.input_tree.add_parent(self.c_well_tops_folder, "Stratigraphy")
    self.c_faults_root = self.input_tree.add_parent(self.c_well_tops_folder, "Faults")
    self.c_other_root = self.input_tree.add_parent(self.c_well_tops_folder, "Other")
    # The Well Logs entries
    self.cont_folder = self.input_tree.add_noncheckable_folder(self.c_well_logs_folder, "continuous")
    self.disc_folder = self.input_tree.add_noncheckable_folder(self.c_well_logs_folder, "discrete")
    self.bmp_folder = self.input_tree.add_noncheckable_folder(self.c_well_logs_folder, "bitmap")

    # Set Data for identification
    self.c_well_folder.setData(0, Qt.UserRole, ("Wells", "Root", "Folder"))
    self.c_well_tops_folder.setData(0,Qt.UserRole, ("Tops", "Root", "Folder"))
    self.c_well_logs_folder.setData(0,Qt.UserRole, ("Logs", "Root", "Folder"))
    self.c_well_track_folder.setData(0,Qt.UserRole, ("Tracks", "Root", "Folder"))
    # --- subfolders ---
    self.c_faults_root.setData(0, Qt.UserRole, ("Well Tops", "Faults", "Subfolder"))
    self.c_stratigraphy_root.setData(0, Qt.UserRole, ("Well Tops", "Stratigraphy", "Subfolder"))
    self.c_other_root.setData(0, Qt.UserRole, ("Well Tops", "Other", "Subfolder"))

    self.cont_folder.setData(0, Qt.UserRole, ("Well Logs", "continuous", "Subfolder"))
    self.disc_folder.setData(0, Qt.UserRole, ("Well Logs", "discrete", "Subfolder"))
    self.bmp_folder.setData(0, Qt.UserRole, ("Well Logs", "bitmap", "Subfolder"))

    # self.input_tree.set_accept_children_drop(self.cont_folder, False)
    # self.input_tree.set_accept_children_drop(self.disc_folder, False)
    # self.input_tree.set_accept_children_drop(self.bmp_folder, False)
    # self.input_tree.set_accept_children_drop(self.c_well_tops_folder, False)
    # self.input_tree.set_accept_children_drop(self.c_stratigraphy_root, False)
    # self.input_tree.set_accept_children_drop(self.c_faults_root, False)
    # self.input_tree.set_accept_children_drop(self.c_other_root, False)



    #self.input_tree.setCurrentItem(c_wells_root)

    # Build from external demo data

    self.statusBar().showMessage("Toggle a checkbox...")
    #self.input_tree.build_tree(build_demo_data())

def build_demo_data():
    """
    Returns nested data of arbitrary depth.

    Supported node types in build_tree():
      - dict: keys become nodes, values become children
      - list/tuple/set: each element becomes a child node
      - everything else: treated as a leaf label (stringified)
    """
    return {
        "Animals": {
            "Mammals": ["Dog", "Cat", "Horse"],
            "Birds": ["Eagle", "Parrot"],
            "Reptiles": {
                "Lizards": ["Gecko", "Iguana"],
                "Snakes": ["Python", "Cobra"],
            },
        },
        "Plants": {
            "Trees": ["Oak", "Pine"],
            "Flowers": ["Rose", "Tulip", "Daisy"],
        },
        "Settings": {
            "Audio": {"Output": ["Speakers", "Headphones"], "Input": ["Mic 1", "Mic 2"]},
            "Video": {"Resolution": ["1080p", "4K"], "HDR": ["On", "Off"]},
        },
    }
