from PySide6.QtWidgets import (
    QDockWidget, QTreeWidget,
    QTreeWidgetItem)

from PySide6 import QtWidgets, QtCore, QtGui

from PySide6.QtCore import Qt

import logging

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

class CheckableTree(QtWidgets.QTreeWidget):
    """
    QTreeWidget with:
      - Arbitrary-depth build_tree()
      - Parent + leaf toggle signals
      - Leaf types:
          * ALWAYS-checkable leaf (checkbox)
          * NEVER-checkable leaf (no checkbox, ever)
      - Folder types:
          * Default folder (checkable)
          * Non-checkable folder (no checkbox, but can contain checkable descendants)
      - Context menu: check/uncheck, add/remove, remove children, move up/down, expand/collapse, add root, clear
      - Drag & drop internal move with:
          * Roots cannot be dragged
          * Items cannot become new roots (rollback)
          * can_drop predicate + per-item drop flags to block dropping ONTO some roots/folders
      - Safe clear_tree(), remove_all_children()
    """

    # Emitted for ALWAYS-checkable leaves: (path, checked_bool)
    itemToggled = QtCore.Signal(str, bool, object)

    # Emitted for checkable folders: (path, checked_bool)
    parentToggled = QtCore.Signal(str, bool, object)

    # Generic context action signal: (path, action_name)
    contextAction = QtCore.Signal(str, str)

    # Structural change signal: (moved_path_before, "moved", new_parent_path_or_empty_for_root)
    structureChanged = QtCore.Signal(str, str, str)

    # ---------- Checkability Policies (stored per item) ----------
    LEAF_ALWAYS_CHECKABLE = 1
    LEAF_NEVER_CHECKABLE = 2
    FOLDER_NEVER_CHECKABLE = 3
    _CHECK_POLICY_ROLE = QtCore.Qt.UserRole + 200
    # ---- Movability flag ----
    _MOVABLE_ROLE = QtCore.Qt.UserRole + 300  # bool

    # ---------- Drop flags (stored per item) ----------
    DROP_ACCEPT_CHILDREN = 0x01  # item can accept drops ONTO it (become parent)
    DROP_DEFAULT = DROP_ACCEPT_CHILDREN
    _DROP_ROLE = QtCore.Qt.UserRole + 101

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Item"])
        self.setUniformRowHeights(True)

        # guard to suppress itemChanged logic during programmatic updates
        self._updating = False

        # checkbox toggles
        self.itemChanged.connect(self._on_item_changed)

        # ---- Context menu wiring ----
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # ---- Drag & drop wiring ----
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)

    # ======================================================================
    # Public API: build / clear
    # ======================================================================

    def build_tree(self, data, root_label: str | None = None):
        """
        Build a tree from nested data with arbitrary depth.

        Supported structures:
          - dict: keys become nodes, values become children
          - list/tuple/set: each element becomes a node
          - scalar: becomes a leaf (DEFAULT: never-checkable leaf)

        Notes:
          - Leaves created by build_tree() default to LEAF_NEVER_CHECKABLE.
          - Folders created by build_tree() default to checkable folders.
        """
        self.clear_tree()

        def add_children(parent_item: QtWidgets.QTreeWidgetItem, subtree):
            if isinstance(subtree, dict):
                for k, v in subtree.items():
                    child = self._make_item(str(k), parent_item)
                    add_children(child, v)
                return

            if isinstance(subtree, (list, tuple, set)):
                for elem in subtree:
                    # If elem is a (label, children) tuple, support it:
                    if isinstance(elem, tuple) and len(elem) == 2 and isinstance(elem[0], (str, int, float)):
                        node = self._make_item(str(elem[0]), parent_item)
                        add_children(node, elem[1])
                    else:
                        leaf = self._make_item(str(elem), parent_item)
                        self.set_check_policy(leaf, self.LEAF_NEVER_CHECKABLE)
                        self._apply_check_policy(leaf)
                return

            # scalar child => leaf
            leaf = self._make_item(str(subtree), parent_item)
            self.set_check_policy(leaf, self.LEAF_NEVER_CHECKABLE)
            self._apply_check_policy(leaf)

        if root_label is not None:
            root = self.add_root(root_label)
            add_children(root, data)
        else:
            if isinstance(data, dict):
                for k, v in data.items():
                    root = self.add_root(str(k))
                    add_children(root, v)
            elif isinstance(data, (list, tuple, set)):
                for elem in data:
                    root = self.add_root(str(elem))
            else:
                self.add_root(str(data))

        # Apply policies across whole tree (ensures folders/leaf checkbox consistency)
        self._reapply_policies_entire_tree()
        self.expandAll()

    def clear_tree(self):
        """Clear the entire tree without firing toggle logic."""
        try:
            self._updating = True
            self.clear()
        finally:
            self._updating = False

    def to_dict(self) -> dict:
        """
        Serialize the entire tree into a nested dictionary.

        The result is safe JSON-serializable (only primitives).
        """

        def serialize_item(item: QtWidgets.QTreeWidgetItem) -> dict:
            # Determine node type
            is_folder = item.childCount() > 0

            # Check policy
            policy = self.check_policy(item)

            # Check state (only meaningful if item has checkbox)
            if self._has_checkbox(item):
                check_state = item.checkState(0)
            else:
                check_state = None

            # Movable flag
            movable = self.is_item_movable(item)

            # Drop flags
            drop_flags = self.drop_flags(item)

            # Expanded state (folders only)
            expanded = item.isExpanded() if is_folder else False

            node = {
                "text": item.text(0),
                "type": "folder" if is_folder else "leaf",
                "policy": policy,
                "check_state": check_state,
                "movable": movable,
                "drop_flags": drop_flags,
                "expanded": expanded,
                "children": [],
            }

            for i in range(item.childCount()):
                node["children"].append(serialize_item(item.child(i)))

            return node

        tree_data = {
            "roots": []
        }

        for i in range(self.topLevelItemCount()):
            tree_data["roots"].append(
                serialize_item(self.topLevelItem(i))
            )

        return tree_data

    def from_dict(self, data: dict):
        """
        Rebuild the entire tree from a dictionary produced by to_dict().

        Completely replaces current tree content.
        """

        if not isinstance(data, dict) or "roots" not in data:
            raise ValueError("Invalid tree dictionary format")

        self.clear_tree()

        def build_item(node_dict: dict, parent_item=None):
            text = node_dict.get("text", "")
            node_type = node_dict.get("type", "leaf")
            policy = node_dict.get("policy", None)
            check_state = node_dict.get("check_state", None)
            movable = node_dict.get("movable", True)
            drop_flags = node_dict.get("drop_flags", self.DROP_DEFAULT)
            expanded = node_dict.get("expanded", False)
            children = node_dict.get("children", [])

            # Create item (no checkbox yet; policy will apply it)
            item = self._make_item(text, parent_item)

            if parent_item is None:
                self.addTopLevelItem(item)

            # Restore policy
            if policy is not None:
                self.set_check_policy(item, policy)

            # Restore movable flag
            self.set_item_movable(item, movable)

            # Restore drop flags
            self.set_drop_flags(item, drop_flags)

            # Build children recursively
            for child_node in children:
                build_item(child_node, item)

            # Apply policy AFTER children exist (important for folder detection)
            self._apply_check_policy(item)

            # Restore check state if applicable
            if check_state is not None and self._has_checkbox(item):
                item.setCheckState(0, check_state)

            # Restore expanded state
            if node_type == "folder":
                item.setExpanded(bool(expanded))

            return item

        try:
            self._updating = True
            blocker = QtCore.QSignalBlocker(self)

            for root_node in data["roots"]:
                build_item(root_node, parent_item=None)

            # After full build, refresh aggregation top-down
            for i in range(self.topLevelItemCount()):
                self._refresh_upwards(self.topLevelItem(i))

        finally:
            del blocker
            self._updating = False
    # ======================================================================
    # Public API: add/remove/move items
    # ======================================================================

    def add_root(self, text: str, *, checkable_folder: bool = True) -> QtWidgets.QTreeWidgetItem:
        root = self._make_item(text, parent=None)
        self.addTopLevelItem(root)

        if not checkable_folder:
            self.set_check_policy(root, self.FOLDER_NEVER_CHECKABLE)

        self._apply_check_policy(root)
        return root

    def add_parent(self, parent_item: QtWidgets.QTreeWidgetItem | None, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add a checkable folder (default folder type) under parent_item, or as top-level if None.
        """
        item = self._make_item(text, parent=None)
        if parent_item is None:
            self.addTopLevelItem(item)
        else:
            parent_item.addChild(item)
            parent_item.setExpanded(True)

        # Folder default is checkable; ensure both parent and new item reflect structure/policy
        self._apply_check_policy(item)
        if parent_item is not None:
            self._apply_check_policy(parent_item)

        self._refresh_upwards(item)
        return item

    def add_noncheckable_folder(self, parent_item: QtWidgets.QTreeWidgetItem | None, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add a folder with NO checkbox (but can contain checkable descendants).
        """
        folder = self.add_parent(parent_item, text)
        self.set_check_policy(folder, self.FOLDER_NEVER_CHECKABLE)
        self._apply_check_policy(folder)
        self._refresh_upwards(folder)
        return folder

    def add_checkable_leaf(self, parent_item: QtWidgets.QTreeWidgetItem, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add an ALWAYS-checkable leaf (checkbox leaf).
        """
        if parent_item is None:
            raise ValueError("add_checkable_leaf requires a parent_item")
        leaf = self._make_item(text, parent_item)
        self.set_check_policy(leaf, self.LEAF_ALWAYS_CHECKABLE)
        self._apply_check_policy(leaf)

        parent_item.setExpanded(True)
        self._apply_check_policy(parent_item)  # ensure it's treated as folder
        self._refresh_upwards(leaf)
        return leaf

    def add_noncheckable_leaf(self, parent_item: QtWidgets.QTreeWidgetItem, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add a NEVER-checkable leaf (no checkbox).
        """
        if parent_item is None:
            raise ValueError("add_noncheckable_leaf requires a parent_item")
        leaf = self._make_item(text, parent_item)
        self.set_check_policy(leaf, self.LEAF_NEVER_CHECKABLE)
        self._apply_check_policy(leaf)

        parent_item.setExpanded(True)
        self._apply_check_policy(parent_item)
        self._refresh_upwards(leaf)
        return leaf

    def remove_item(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        """Remove an item (folder or leaf). Folder removal removes subtree."""
        if item is None:
            return False

        parent = item.parent()
        try:
            self._updating = True
            if parent is None:
                idx = self.indexOfTopLevelItem(item)
                if idx >= 0:
                    self.takeTopLevelItem(idx)
            else:
                parent.removeChild(item)
        finally:
            self._updating = False

        if parent is not None:
            self._apply_check_policy(parent)      # parent might become leaf
            self._refresh_upwards(parent)

        return True

    def remove_selected(self) -> bool:
        return self.remove_item(self.currentItem())

    def remove_all_children(self, parent_item: QtWidgets.QTreeWidgetItem) -> bool:
        """Remove all children of a folder, keep the folder itself."""
        if parent_item is None or parent_item.childCount() == 0:
            return False

        try:
            self._updating = True
            parent_item.takeChildren()
        finally:
            self._updating = False

        # Folder might become leaf => apply policy
        self._apply_check_policy(parent_item)
        self._refresh_upwards(parent_item)
        return True

    def move_item_up(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        """Move item one position up among siblings (roots included)."""
        if item is None:
            return False
        parent = item.parent()
        if parent is None:
            idx = self.indexOfTopLevelItem(item)
            if idx <= 0:
                return False
            self.takeTopLevelItem(idx)
            self.insertTopLevelItem(idx - 1, item)
        else:
            idx = parent.indexOfChild(item)
            if idx <= 0:
                return False
            parent.takeChild(idx)
            parent.insertChild(idx - 1, item)
        return True

    def move_item_down(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        """Move item one position down among siblings (roots included)."""
        if item is None:
            return False
        parent = item.parent()
        if parent is None:
            idx = self.indexOfTopLevelItem(item)
            if idx < 0 or idx >= self.topLevelItemCount() - 1:
                return False
            self.takeTopLevelItem(idx)
            self.insertTopLevelItem(idx + 1, item)
        else:
            idx = parent.indexOfChild(item)
            if idx < 0 or idx >= parent.childCount() - 1:
                return False
            parent.takeChild(idx)
            parent.insertChild(idx + 1, item)
        return True

    # ======================================================================
    # Drop policy + flags (used by can_drop)
    # ======================================================================

    def set_item_movable(self, item: QtWidgets.QTreeWidgetItem, movable: bool) -> None:
        """
        If movable=False, the item cannot be dragged/dropped (won't move at all).
        """
        if item is None:
            return
        item.setData(0, self._MOVABLE_ROLE, bool(movable))

    def is_item_movable(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        """
        Defaults to True if not set.
        """
        if item is None:
            return False
        v = item.data(0, self._MOVABLE_ROLE)
        return True if v is None else bool(v)

    def lock_leaf_movement(self, leaf_item: QtWidgets.QTreeWidgetItem) -> None:
        """
        Convenience: lock movement only if the item is a leaf.
        """
        if leaf_item is None:
            return
        if leaf_item.childCount() == 0:
            self.set_item_movable(leaf_item, False)

    def drop_flags(self, item: QtWidgets.QTreeWidgetItem) -> int:
        if item is None:
            return 0
        v = item.data(0, self._DROP_ROLE)
        return int(v) if v is not None else self.DROP_DEFAULT

    def set_drop_flags(self, item: QtWidgets.QTreeWidgetItem, flags: int) -> None:
        if item is None:
            return
        item.setData(0, self._DROP_ROLE, int(flags))

    def set_accept_children_drop(self, item: QtWidgets.QTreeWidgetItem, accept: bool) -> None:
        """
        If False: cannot drop ONTO this item (i.e., cannot become its child via OnItem).
        Useful to lock specific roots/folders from receiving new children via DnD.
        """
        flags = self.drop_flags(item)
        if accept:
            flags |= self.DROP_ACCEPT_CHILDREN
        else:
            flags &= ~self.DROP_ACCEPT_CHILDREN
        self.set_drop_flags(item, flags)

    def can_drop(
            self,
            dragged: QtWidgets.QTreeWidgetItem,
            intended_parent: QtWidgets.QTreeWidgetItem | None,
            drop_pos: QtWidgets.QAbstractItemView.DropIndicatorPosition,
    ) -> bool:
        """
        Disallow any drop that would make `intended_parent` receive a new child if it
        doesn't accept children drops.

        This blocks:
          - dropping ONTO a locked root/folder (OnItem)
          - dropping BETWEEN children inside a locked root/folder (AboveItem/BelowItem)
        """
        if dragged is None:
            return False

        # If the move would insert dragged as a child of intended_parent, enforce the flag.
        if intended_parent is not None:
            flags = self.drop_flags(intended_parent)
            if (flags & self.DROP_ACCEPT_CHILDREN) == 0:
                return False

        return True

    # ======================================================================
    # Drag & Drop overrides
    # ======================================================================

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item is None:
            return

        # existing rule: roots cannot be dragged
        if item.parent() is None:
            return

        # new rule: locked items cannot be dragged
        if not self.is_item_movable(item):
            return

        super().startDrag(supportedActions)

    def dropEvent(self, event: QtGui.QDropEvent):
        """
        Internal move with:
          - roots cannot be dragged
          - cannot create new roots (rollback)
          - cannot drop into own subtree
          - can_drop predicate based on flags/policies (e.g. locked roots)
        """
        dragged = self.currentItem()

        # Locked items cannot be moved at all (even if drag somehow started)
        if not self.is_item_movable(dragged):
            event.ignore()
            return

        if dragged is None:
            super().dropEvent(event)
            return

        # Roots cannot be moved at all
        if dragged.parent() is None:
            event.ignore()
            return

        old_parent = dragged.parent()
        old_index = old_parent.indexOfChild(dragged)

        target = self.itemAt(event.position().toPoint())
        drop_pos = self.dropIndicatorPosition()

        # Prevent dropping into own subtree
        if target is not None and self._is_descendant(dragged, target):
            event.ignore()
            return

        # Determine intended parent (who would receive dragged as a child)
        intended_parent = None
        if drop_pos == QtWidgets.QAbstractItemView.OnItem:
            intended_parent = target
        elif target is not None:
            intended_parent = target.parent()  # may be None for top-level target
        else:
            intended_parent = None

        # Apply predicate rule
        if not self.can_drop(dragged, intended_parent, drop_pos):
            event.ignore()
            return

        moved_path_before = self._item_path(dragged)

        # Let Qt perform the move
        try:
            self._updating = True
            super().dropEvent(event)
        finally:
            self._updating = False

        # Disallow becoming a new root (rollback)
        if dragged.parent() is None:
            try:
                self._updating = True
                top_idx = self.indexOfTopLevelItem(dragged)
                if top_idx >= 0:
                    self.takeTopLevelItem(top_idx)
                old_parent.insertChild(old_index, dragged)
            finally:
                self._updating = False

            self._apply_check_policy(old_parent)
            self._refresh_upwards(old_parent)
            event.ignore()
            return

        new_parent = dragged.parent()

        # Policies may change if something became leaf/folder due to move
        self._apply_check_policy(old_parent)
        self._apply_check_policy(new_parent)
        self._apply_check_policy(dragged)  # if subtree moved, keep its own policy consistent

        # Refresh check aggregation upwards for both old and new parents
        self._refresh_upwards(old_parent)
        self._refresh_upwards(new_parent)

        self.structureChanged.emit(moved_path_before, "moved", self._item_path(new_parent))

    # ======================================================================
    # Context menu
    # ======================================================================

    def _show_context_menu(self, pos: QtCore.QPoint):
        item = self.itemAt(pos)
        menu = QtWidgets.QMenu(self)

        # --- Empty space menu ---
        if item is None:
            act_add_root = menu.addAction("Add root (checkable)")
            act_add_root_nc = menu.addAction("Add root (non-checkable)")
            act_clear = menu.addAction("Clear tree")
            menu.addSeparator()
            act_expand_all = menu.addAction("Expand all")
            act_collapse_all = menu.addAction("Collapse all")

            chosen = menu.exec(self.viewport().mapToGlobal(pos))
            if chosen is None:
                return

            if chosen == act_add_root:
                r = self.add_root("New Root", checkable_folder=True)
                self.setCurrentItem(r)
                self.editItem(r, 0)
                self.contextAction.emit("", "add_root_checkable")
            elif chosen == act_add_root_nc:
                r = self.add_root("New Root", checkable_folder=False)
                self.setCurrentItem(r)
                self.editItem(r, 0)
                self.contextAction.emit("", "add_root_noncheckable")
            elif chosen == act_clear:
                self.clear_tree()
                self.contextAction.emit("", "clear_tree")
            elif chosen == act_expand_all:
                self.expandAll()
                self.contextAction.emit("", "expand_all")
            elif chosen == act_collapse_all:
                self.collapseAll()
                self.contextAction.emit("", "collapse_all")
            return

        path = self._item_path(item)
        is_folder = item.childCount() > 0
        self._apply_check_policy(item)
        has_checkbox = self._has_checkbox(item)

        # --- Check actions (only if item has a checkbox) ---
        act_check = act_uncheck = act_toggle = None
        if has_checkbox:
            act_check = menu.addAction("Check")
            act_uncheck = menu.addAction("Uncheck")
            act_toggle = menu.addAction("Toggle check")
            menu.addSeparator()

        # --- Add/remove actions ---
        act_add_folder = menu.addAction("Add folder (checkable) under this")
        act_add_folder_nc = menu.addAction("Add folder (non-checkable) under this")
        act_add_leaf_chk = menu.addAction("Add leaf (checkable) under this")
        act_add_leaf_nchk = menu.addAction("Add leaf (non-checkable) under this")
        act_remove_children = menu.addAction("Remove all children")
        act_remove = menu.addAction("Remove this")

        # Only folders can receive children (in this UI)
        if not is_folder:
            act_add_folder.setEnabled(False)
            act_add_folder_nc.setEnabled(False)
            act_add_leaf_chk.setEnabled(False)
            act_add_leaf_nchk.setEnabled(False)
            act_remove_children.setEnabled(False)

        menu.addSeparator()

        # --- Move actions ---
        act_move_up = menu.addAction("Move up")
        act_move_down = menu.addAction("Move down")

        # Disable move if not possible
        parent = item.parent()
        if parent is None:
            idx = self.indexOfTopLevelItem(item)
            act_move_up.setEnabled(idx > 0)
            act_move_down.setEnabled(idx < self.topLevelItemCount() - 1)
        else:
            idx = parent.indexOfChild(item)
            act_move_up.setEnabled(idx > 0)
            act_move_down.setEnabled(idx < parent.childCount() - 1)

        menu.addSeparator()

        # --- Expand/collapse / info ---
        act_expand = act_collapse = act_print = None
        if is_folder:
            act_expand = menu.addAction("Expand")
            act_collapse = menu.addAction("Collapse")
        else:
            act_print = menu.addAction("Print path")

        chosen = menu.exec(self.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        # Check actions
        if has_checkbox and chosen in (act_check, act_uncheck, act_toggle):
            if chosen == act_check:
                self._apply_check_from_menu(item, QtCore.Qt.Checked)
                self.contextAction.emit(path, "check")
            elif chosen == act_uncheck:
                self._apply_check_from_menu(item, QtCore.Qt.Unchecked)
                self.contextAction.emit(path, "uncheck")
            elif chosen == act_toggle:
                cur = item.checkState(0)
                new_state = QtCore.Qt.Unchecked if cur == QtCore.Qt.Checked else QtCore.Qt.Checked
                self._apply_check_from_menu(item, new_state)
                self.contextAction.emit(path, "toggle")
            return

        # Add/remove
        if chosen == act_add_folder:
            new_item = self.add_parent(item, "New Folder")
            self.setCurrentItem(new_item)
            self.editItem(new_item, 0)
            self.contextAction.emit(path, "add_folder_checkable")
            return

        if chosen == act_add_folder_nc:
            new_item = self.add_noncheckable_folder(item, "New Folder")
            self.setCurrentItem(new_item)
            self.editItem(new_item, 0)
            self.contextAction.emit(path, "add_folder_noncheckable")
            return

        if chosen == act_add_leaf_chk:
            new_item = self.add_checkable_leaf(item, "New Leaf")
            self.setCurrentItem(new_item)
            self.editItem(new_item, 0)
            self.contextAction.emit(path, "add_leaf_checkable")
            return

        if chosen == act_add_leaf_nchk:
            new_item = self.add_noncheckable_leaf(item, "New Leaf")
            self.setCurrentItem(new_item)
            self.editItem(new_item, 0)
            self.contextAction.emit(path, "add_leaf_noncheckable")
            return

        if chosen == act_remove_children:
            self.remove_all_children(item)
            self.contextAction.emit(path, "remove_all_children")
            return

        if chosen == act_remove:
            self.remove_item(item)
            self.contextAction.emit(path, "remove")
            return

        # Move
        if chosen == act_move_up:
            if self.move_item_up(item):
                self.setCurrentItem(item)
                self.contextAction.emit(path, "move_up")
            return

        if chosen == act_move_down:
            if self.move_item_down(item):
                self.setCurrentItem(item)
                self.contextAction.emit(path, "move_down")
            return

        # Expand/collapse/info
        if is_folder and chosen == act_expand:
            item.setExpanded(True)
            self.contextAction.emit(path, "expand")
            return

        if is_folder and chosen == act_collapse:
            item.setExpanded(False)
            self.contextAction.emit(path, "collapse")
            return

        if (not is_folder) and chosen == act_print:
            print(f"PATH: {path}")
            self.contextAction.emit(path, "print_path")
            return

    def _apply_check_from_menu(self, item: QtWidgets.QTreeWidgetItem, state: QtCore.Qt.CheckState):
        # Apply as if user toggled (but avoid intermediate signals)
        try:
            self._updating = True
            item.setCheckState(0, state)
        finally:
            self._updating = False
        self._handle_user_toggle(item)

    # ======================================================================
    # Check policy + checkbox enforcement
    # ======================================================================

    def set_check_policy(self, item: QtWidgets.QTreeWidgetItem, policy: int | None):
        item.setData(0, self._CHECK_POLICY_ROLE, policy)

    def check_policy(self, item: QtWidgets.QTreeWidgetItem) -> int | None:
        return item.data(0, self._CHECK_POLICY_ROLE)

    def _has_checkbox(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        return bool(item.flags() & QtCore.Qt.ItemIsUserCheckable)

    def _remove_checkbox(self, item: QtWidgets.QTreeWidgetItem):
        flags = item.flags() & ~QtCore.Qt.ItemIsUserCheckable
        item.setFlags(flags)
        # critical: remove CheckStateRole or Qt may still draw a checkbox
        item.setData(0, QtCore.Qt.CheckStateRole, None)

    def _ensure_checkbox(self, item: QtWidgets.QTreeWidgetItem):
        flags = item.flags() | QtCore.Qt.ItemIsUserCheckable
        item.setFlags(flags)
        if item.data(0, QtCore.Qt.CheckStateRole) is None:
            item.setCheckState(0, QtCore.Qt.Unchecked)

    def _apply_check_policy(self, item: QtWidgets.QTreeWidgetItem):
        if item is None:
            return

        policy = self.check_policy(item)
        is_folder = item.childCount() > 0

        # Explicit overrides first
        if policy == self.FOLDER_NEVER_CHECKABLE:
            self._remove_checkbox(item)
            return

        if policy == self.LEAF_NEVER_CHECKABLE:
            self._remove_checkbox(item)
            return

        if policy == self.LEAF_ALWAYS_CHECKABLE:
            self._ensure_checkbox(item)
            return

        # Defaults if no explicit policy:
        # folder => checkable
        # leaf   => non-checkable
        if is_folder:
            self._ensure_checkbox(item)
        else:
            self._remove_checkbox(item)

    def _reapply_policies_entire_tree(self):
        """Re-apply policies for all items (useful after bulk build)."""
        def walk(node: QtWidgets.QTreeWidgetItem):
            self._apply_check_policy(node)
            for i in range(node.childCount()):
                walk(node.child(i))

        for i in range(self.topLevelItemCount()):
            walk(self.topLevelItem(i))

        # Refresh parent aggregation for all roots
        for i in range(self.topLevelItemCount()):
            self._refresh_upwards(self.topLevelItem(i))

    # ======================================================================
    # Toggle logic + tri-state aggregation (including non-checkable folders)
    # ======================================================================

    def _on_item_changedo(self, item: QtWidgets.QTreeWidgetItem, column: int):
        if column != 0 or self._updating:
            return
        #self.blockSignals(True)
        self._handle_user_toggle(item)
        #self.blockSignals(False)
        #self.parentToggled.connect(self.on_parent_toggled)
        #self.leafToggled.connect(self.on_leaf_toggled)
        #self.contextAction.connect(self.on_context_action)

    def _on_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        if column != 0 or self._updating:
            return

        # Guard the whole user-toggle handling so any programmatic changes won't re-enter.
        self._updating = True
        try:
            self._handle_user_toggle(item)
        finally:
            self._updating = False


    def _handle_user_toggle(self, item: QtWidgets.QTreeWidgetItem):
        # Enforce policy and ignore non-checkable items
        self._apply_check_policy(item)
        if not self._has_checkbox(item):
            return

        state = item.checkState(0)
        #data = item.data[0]
        checked = (state == QtCore.Qt.Checked)

        if item.childCount() > 0:
            # folder toggled (only checkable folders can reach here)
            self.parentToggled.emit(self._item_path(item), checked, item)

            try:
                self._updating = True
                self._set_subtree_checkstate(item, state)
                self._update_parents(item)
            finally:
                self._updating = False
            return

        # checkable leaf toggled
        self.itemToggled.emit(self._item_path(item), checked, item)
        try:
            self._updating = True
            self._update_parents(item)
        finally:
            self._updating = False

    def _set_subtree_checkstate(self, root: QtWidgets.QTreeWidgetItem, state: QtCore.Qt.CheckState):
        """
        Apply state to all CHECKABLE descendants:
          - checkable folders: set state
          - checkable leaves:  set state
          - non-checkable folders: do not set state, but recurse through them
          - non-checkable leaves: ensure no checkbox/state role
        """
        if state == QtCore.Qt.PartiallyChecked:
            return

        for i in range(root.childCount()):
            child = root.child(i)

            # enforce policy before touching any check state (prevents "ghost" checkboxes)
            self._apply_check_policy(child)

            if self._has_checkbox(child):
                child.setCheckState(0, state)

            if child.childCount() > 0:
                self._set_subtree_checkstate(child, state)

    def _update_parents(self, item: QtWidgets.QTreeWidgetItem):
        parent = item.parent()
        while parent is not None:
            self._apply_check_policy(parent)
            agg = self._aggregate_state(parent)

            # Only checkable folders display tri-state
            if self._has_checkbox(parent):
                parent.setCheckState(0, agg)

            parent = parent.parent()

    def _effective_state(self, item: QtWidgets.QTreeWidgetItem) -> QtCore.Qt.CheckState | None:
        """
        Returns an "effective" state used for aggregation:
          - For checkable items: their checkState
          - For non-checkable folder: aggregated state of its descendants (may be None if nothing contributes)
          - For non-checkable leaf: None (ignored)
        """
        self._apply_check_policy(item)

        if self._has_checkbox(item):
            return item.checkState(0)

        if item.childCount() == 0:
            return None  # non-checkable leaf contributes nothing

        # non-checkable folder: aggregate children
        checked = unchecked = partial = considered = 0
        for i in range(item.childCount()):
            s = self._effective_state(item.child(i))
            if s is None:
                continue
            considered += 1
            if s == QtCore.Qt.Checked:
                checked += 1
            elif s == QtCore.Qt.Unchecked:
                unchecked += 1
            else:
                partial += 1

        if considered == 0:
            return None
        if partial > 0 or (checked > 0 and unchecked > 0):
            return QtCore.Qt.PartiallyChecked
        return QtCore.Qt.Checked if checked == considered else QtCore.Qt.Unchecked

    def _aggregate_state(self, parent: QtWidgets.QTreeWidgetItem) -> QtCore.Qt.CheckState:
        checked = unchecked = partial = considered = 0

        for i in range(parent.childCount()):
            s = self._effective_state(parent.child(i))
            if s is None:
                continue
            considered += 1
            if s == QtCore.Qt.Checked:
                checked += 1
            elif s == QtCore.Qt.Unchecked:
                unchecked += 1
            else:
                partial += 1

        if considered == 0:
            return QtCore.Qt.Unchecked
        if partial > 0 or (checked > 0 and unchecked > 0):
            return QtCore.Qt.PartiallyChecked
        return QtCore.Qt.Checked if checked == considered else QtCore.Qt.Unchecked

    def _refresh_upwards(self, item: QtWidgets.QTreeWidgetItem):
        """Recompute aggregation up the chain from item."""
        try:
            self._updating = True
            self._update_parents(item)
        finally:
            self._updating = False

    # ======================================================================
    # Item creation + utils
    # ======================================================================

    def _make_item(self, text: str, parent: QtWidgets.QTreeWidgetItem | None) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([text])
        item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        if parent is not None:
            parent.addChild(item)
        return item

    def _item_path(self, item: QtWidgets.QTreeWidgetItem | None) -> str:
        if item is None:
            return ""
        parts = []
        cur = item
        while cur is not None:
            parts.append(cur.text(0))
            cur = cur.parent()
        return " / ".join(reversed(parts))

    def _is_descendant(
        self, possible_ancestor: QtWidgets.QTreeWidgetItem, possible_descendant: QtWidgets.QTreeWidgetItem
    ) -> bool:
        cur = possible_descendant
        while cur is not None:
            if cur is possible_ancestor:
                return True
            cur = cur.parent()
        return False

    def get_items_in_folder(
            self,
            folder_item: QtWidgets.QTreeWidgetItem,
            *,
            recursive: bool = True,
            include_folders: bool = True,
            include_leaves: bool = True,
            only_checkable: bool = False,
    ) -> list[QtWidgets.QTreeWidgetItem]:
        """
        Return items inside a folder.

        Parameters
        ----------
        folder_item : QTreeWidgetItem
            The folder whose contents should be returned.

        recursive : bool
            If True, return all descendants.
            If False, return only direct children.

        include_folders : bool
            Include folder items in result.

        include_leaves : bool
            Include leaf items in result.

        only_checkable : bool
            If True, return only items that currently have a checkbox.

        Returns
        -------
        List[QTreeWidgetItem]
        """

        if folder_item is None:
            return []

        results = []

        def collect(item: QtWidgets.QTreeWidgetItem):
            is_folder = item.childCount() > 0
            has_checkbox = self._has_checkbox(item)

            if ((is_folder and include_folders) or
                    (not is_folder and include_leaves)):

                if not only_checkable or has_checkbox:
                    results.append(item)

            if recursive:
                for i in range(item.childCount()):
                    collect(item.child(i))

        for i in range(folder_item.childCount()):
            collect(folder_item.child(i))

        return results

def setup_input_tree(self, root_label=None):
    self.input_tree = CheckableTree(self)
    self.input_tree.setHeaderHidden(True)


    self.input_tree.parentToggled.connect(self.on_item_toggled)
    self.input_tree.itemToggled.connect(self.on_item_toggled)
    self.input_tree.contextAction.connect(self.on_context_action)
    #self.input_tree.structureChanged.connect(self.on_structure_changed)

    self.input_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.input_tree.customContextMenuRequested.connect(self._on_window_tree_context_menu)

    setup_well_tree(self)
    #self.input_tree.clear_tree()
    #setup_test_tree(self)

def setup_well_tree(self):

    #High Level Folder
    self.c_well_root_item = self.input_tree.add_root("Wells")
    self.c_well_tops_folder = self.input_tree.add_root("Wells Tops")
    self.c_well_logs_folder = self.input_tree.add_root("Logs")
    self.c_well_track_folder = self.input_tree.add_root("Tracks")


    # The Well Tops entries
    self.c_stratigraphy_root = self.input_tree.add_parent(self.c_well_tops_folder, "Stratigraphy")
    self.c_faults_root = self.input_tree.add_parent(self.c_well_tops_folder, "Faults")
    self.c_other_root = self.input_tree.add_parent(self.c_well_tops_folder, "Other")

    self.input_tree.set_accept_children_drop(self.c_well_tops_folder, False)
    self.input_tree.set_accept_children_drop(self.c_stratigraphy_root, False)
    self.input_tree.set_accept_children_drop(self.c_faults_root, False)
    self.input_tree.set_accept_children_drop(self.c_other_root, False)


    # it.setData(0, Qt.UserRole, well_name)
    # state = Qt.Checked if well_name in self.panel.visible_wells else Qt.Unchecked
    # it.setCheckState(0, state)
    # self.input_tree.set_accept_children_drop(it, False)

    # --- subfolders ---

    self.cont_folder = self.input_tree.add_noncheckable_folder(self.c_well_logs_folder, "continuous")
    self.disc_folder = self.input_tree.add_noncheckable_folder(self.c_well_logs_folder, "discrete")
    self.bmp_folder = self.input_tree.add_noncheckable_folder(self.c_well_logs_folder, "bitmap")

    self.input_tree.set_accept_children_drop(self.cont_folder, False)
    self.input_tree.set_accept_children_drop(self.disc_folder, False)
    self.input_tree.set_accept_children_drop(self.bmp_folder, False)


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
