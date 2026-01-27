from PySide6.QtWidgets import (
    QDockWidget, QTreeWidget,
    QTreeWidgetItem, )

from PySide6.QtCore import Qt
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
        | Qt.ItemIsAutoTristate
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
        | Qt.ItemIsAutoTristate
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
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )

    self.well_tops_folder.setCheckState(0, Qt.Unchecked)
    self.well_tree.addTopLevelItem(self.well_tops_folder)

    self.stratigraphy_root = QTreeWidgetItem(["Stratigraphy"])
    self.stratigraphy_root.setFlags(
        self.stratigraphy_root.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.stratigraphy_root.setCheckState(0, Qt.Unchecked)
    self.well_tops_folder.addChild(self.stratigraphy_root)

    self.faults_root = QTreeWidgetItem(["Faults"])
    self.faults_root.setFlags(
        self.faults_root.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.faults_root.setCheckState(0, Qt.Unchecked)
    self.well_tops_folder.addChild(self.faults_root)

    self.other_root = QTreeWidgetItem(["Other"])
    self.other_root.setFlags(
        self.other_root.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
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
        | Qt.ItemIsAutoTristate
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
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.continous_logs_folder.setCheckState(0, Qt.Unchecked)
    self.well_logs_folder.addChild(self.continous_logs_folder)

    self.discrete_logs_folder = QTreeWidgetItem(["Discrete Logs"])
    self.discrete_logs_folder.setFlags(
        self.discrete_logs_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.discrete_logs_folder.setCheckState(0, Qt.Unchecked)
    self.well_logs_folder.addChild(self.discrete_logs_folder)

    self.bitmaps_folder = QTreeWidgetItem(["Bitmaps"])
    self.bitmaps_folder.setFlags(
        self.bitmaps_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
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
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.track_root_item.setCheckState(0, Qt.Unchecked)
    self.well_tree.addTopLevelItem(self.track_root_item)

    # --- Folder: stratigraphy (structure only, not necessarily checkable) ---
    self.stratigraphy_root_item = QTreeWidgetItem(["Stratigraphic column"])
    # structure only -> no checkboxes needed, but selectable/enabled
    self.stratigraphy_root_item.setFlags(
        self.stratigraphy_root_item.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.stratigraphy_root_item.setCheckState(0, Qt.Unchecked)
    self.well_tree.addTopLevelItem(self.stratigraphy_root_item)



def build_stratigraphic_column_tree(tree_widget, strat_data):
    """
    Build a root item "Stratigraphic column" in a QTreeWidget and populate up to 7 levels.

    Parameters
    ----------
    tree_widget : QTreeWidget
        Your tree widget (e.g. self.tree_project or self.tree_wells).
    strat_data : dict or list
        Either:
          - a dict with key "stratigraphy": [root_nodes...]
          - OR directly the list [root_nodes...]
        Each node is like:
          {"acronym": "...", "name": "...", "level": <int>, "members": [ ... ]}

    Notes
    -----
    - Uses acronym as the visible text for leaves and intermediate nodes.
    - Stores the full node dict in item.data(0, Qt.UserRole) as ("strat_node", node_dict).
    - Only descends to max_depth=7 (requested).
    """
    # Remove any existing "Stratigraphic column" roots (optional safety)
    root = tree_widget.invisibleRootItem()
    for i in reversed(range(root.childCount())):
        if root.child(i).text(0) == "Stratigraphic column":
            root.removeChild(root.child(i))

    root_item = QTreeWidgetItem(["Stratigraphic column"])
    root_item.setFlags(
        root_item.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    root_item.setCheckState(0, Qt.Unchecked)
    tree_widget.addTopLevelItem(root_item)

    # Normalize input
    if isinstance(strat_data, dict):
        nodes = strat_data.get("stratigraphy", [])
    else:
        nodes = strat_data or []

    def node_label(node):
        acr = (node.get("acronym") or "").strip()
        # fallback if acronym missing
        if not acr:
            acr = (node.get("name") or "<?>").strip()
        return acr

    def node_tooltip(node):
        # show acronym + full name + age range if available
        acr = (node.get("acronym") or "").strip()
        nm = node.get("name")
        age = node.get("age_ma") or {}
        a_from = age.get("from")
        a_to = age.get("to")
        parts = []
        if acr:
            parts.append(acr)
        if nm:
            parts.append(str(nm))
        if a_from is not None or a_to is not None:
            parts.append(f"Age (Ma): {a_from} … {a_to}")
        return " | ".join(parts)

    def add_children(parent_item, node_list, depth, max_depth=7):
        if depth > max_depth:
            return
        for node in node_list:
            label = node_label(node)
            item = QTreeWidgetItem([label])
            #item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            #item.setCheckState(0, Qt.Checked)

            # store full record
            item.setData(0, Qt.UserRole, ("strat_node", node))

            # tooltip / secondary info
            item.setToolTip(0, node_tooltip(node))

            parent_item.addChild(item)

            members = node.get("members") or []
            if isinstance(members, list) and members and depth < max_depth:
                # make parents tristate for easy toggling
                item.setFlags(item.flags() | Qt.ItemIsAutoTristate)
                add_children(item, members, depth + 1, max_depth=max_depth)

    add_children(root_item, nodes, depth=1, max_depth=7)

    root_item.setExpanded(True)
    tree_widget.expandItem(root_item)

