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
    leafToggled = QtCore.Signal(str, bool)

    # Emitted for checkable folders: (path, checked_bool)
    parentToggled = QtCore.Signal(str, bool)

    # Generic context action signal: (path, action_name)
    contextAction = QtCore.Signal(str, str)

    # Structural change signal: (moved_path_before, "moved", new_parent_path_or_empty_for_root)
    structureChanged = QtCore.Signal(str, str, str)

    # ---------- Checkability Policies (stored per item) ----------
    LEAF_ALWAYS_CHECKABLE = 1
    LEAF_NEVER_CHECKABLE = 2
    FOLDER_NEVER_CHECKABLE = 3
    _CHECK_POLICY_ROLE = QtCore.Qt.UserRole + 200

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

    def add_noncheckable_folder(
        self, parent_item: QtWidgets.QTreeWidgetItem | None, text: str
    ) -> QtWidgets.QTreeWidgetItem:
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
        Predicate for whether a drop is allowed.

        Current rules:
          - If drop_pos == OnItem, intended_parent must accept child drops (DROP_ACCEPT_CHILDREN)
          - Above/Below is allowed (subject to other global restrictions enforced in dropEvent)
        """
        if dragged is None:
            return False

        if drop_pos == QtWidgets.QAbstractItemView.OnItem and intended_parent is not None:
            flags = self.drop_flags(intended_parent)
            if (flags & self.DROP_ACCEPT_CHILDREN) == 0:
                return False

        return True

    # ======================================================================
    # Drag & Drop overrides
    # ======================================================================

    def startDrag(self, supportedActions):
        """Prevent dragging of root items."""
        item = self.currentItem()
        if item is not None and item.parent() is None:
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
        if dragged is None:
            super().dropEvent(event)
            return

        # Roots cannot be moved at all
        if dragged.parent() is None:
            event.ignore()
            return

        old_parent = dragged.parent()
        old_index = old_parent.indexOfChild(dragged)

        target = self.itemAt(event.pos())
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

            chosen = menu.exec_(self.viewport().mapToGlobal(pos))
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

        chosen = menu.exec_(self.viewport().mapToGlobal(pos))
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

    def _on_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        if column != 0 or self._updating:
            return
        self._handle_user_toggle(item)

    def _handle_user_toggle(self, item: QtWidgets.QTreeWidgetItem):
        # Enforce policy and ignore non-checkable items
        self._apply_check_policy(item)
        if not self._has_checkbox(item):
            return

        state = item.checkState(0)
        checked = (state == QtCore.Qt.Checked)

        if item.childCount() > 0:
            # folder toggled (only checkable folders can reach here)
            self.parentToggled.emit(self._item_path(item), checked)

            try:
                self._updating = True
                self._set_subtree_checkstate(item, state)
                self._update_parents(item)
            finally:
                self._updating = False
            return

        # checkable leaf toggled
        self.leafToggled.emit(self._item_path(item), checked)
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



class ooCheckableTree(QtWidgets.QTreeWidget):
    leafToggled = QtCore.Signal(object, str, bool)
    parentToggled = QtCore.Signal(str, bool)
    contextAction = QtCore.Signal(str, str)  # (path, action_name)
    structureChanged = QtCore.Signal(str, str, str)  # (moved_path, action, new_parent_path)


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Item"])
        self.setUniformRowHeights(True)

        self._updating = False
        self.itemChanged.connect(self._on_item_changed)

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # ---- Drag & drop wiring ----
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)


    # ----------------------------
    # Public API: build / mutate
    # ----------------------------
    # def build_tree(self, data, root_label=None):
    #     self.clear()
    #
    #     if root_label is not None:
    #         root = self._make_item(str(root_label), parent=None, checkable=True)
    #         self.addTopLevelItem(root)
    #         self._add_children(root, data)
    #     else:
    #         if isinstance(data, dict):
    #             for k, v in data.items():
    #                 node = self._make_item(str(k), parent=None, checkable=True)
    #                 self.addTopLevelItem(node)
    #                 self._add_children(node, v)
    #         else:
    #             for elem in (data if isinstance(data, (list, tuple, set)) else [data]):
    #                 node = self._make_item(self._label(elem), parent=None, checkable=True)
    #                 self.addTopLevelItem(node)
    #                 self._add_children(node, elem)
    #
    #     self.expandAll()

    def clear_tree(self):
        """
        Clear the entire tree safely.

        This:
          - removes all items (roots + children)
          - suppresses itemChanged / checkbox logic
          - leaves the tree ready for rebuild
        """
        try:
            self._updating = True
            self.clear()
        finally:
            self._updating = False

    def add_root(self, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add a new root (top-level) item.
        Returns the created root item.
        """
        root = self._make_item(text, parent=None, checkable=False)
        self.addTopLevelItem(root)

        # ensure consistent check state visuals
        try:
            self._updating = True
            root.setCheckState(0, QtCore.Qt.Unchecked)
        finally:
            self._updating = False

        return root

    def add_parent(self, parent_item, text: str, checkable : bool) -> QtWidgets.QTreeWidgetItem:
        """
        Add a new parent node under parent_item (or as top-level if parent_item is None).
        Returns the created item.
        """

        print(f"ADD PARENT: {parent_item} {text}, {checkable}")

        new_item = self._make_item(text, parent=None, checkable=checkable)

        if parent_item is None:
            self.addTopLevelItem(new_item)
        else:
            parent_item.addChild(new_item)
            parent_item.setExpanded(False)

        # keep parents consistent (tri-state display)
        self._refresh_upwards(new_item)
        return new_item

    def add_leaf(
        self,
        parent_item: QtWidgets.QTreeWidgetItem,
        text: str,
        checkable : bool = True
    ) -> QtWidgets.QTreeWidgetItem:
        if parent_item is None:
            raise ValueError("add_leaf requires a parent item")

        leaf = self._make_item(text, parent=parent_item, checkable=False)

        parent_item.setExpanded(True)
        self._refresh_upwards(leaf)

        return leaf


    def remove_item(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        """
        Remove an item (parent or leaf). If it's a parent, removes the whole subtree.
        Returns True if removed, False if item was None.
        """
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

        # update check/partials up the chain
        if parent is not None:
            self._refresh_upwards(parent)

        return True

    def remove_selected(self) -> bool:
        """
        Convenience: remove the currently selected item.
        """
        return self.remove_item(self.currentItem())

    def move_item_up(self, item: QtWidgets.QTreeWidgetItem) -> bool:
        """
        Move item one position up among siblings.
        Returns True if moved, False if not possible.
        """
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
        """
        Move item one position down among siblings.
        Returns True if moved, False if not possible.
        """
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


    # ----------------------------
    # Context menu
    # ----------------------------
    def _show_context_menu(self, pos: QtCore.QPoint):
        item = self.itemAt(pos)
        menu = QtWidgets.QMenu(self)

        if item is None:
            act_add_root = menu.addAction("Add root")
            menu.addSeparator()
            act_expand_all = menu.addAction("Expand all")
            act_collapse_all = menu.addAction("Collapse all")


            chosen = menu.exec(self.viewport().mapToGlobal(pos))
            if chosen == act_add_root:
                root = self.add_root("New Root")
                self.setCurrentItem(root)
                self.editItem(root, 0)
                self.contextAction.emit("", "add_root")
            elif chosen == act_expand_all:
                self.expandAll()
                self.contextAction.emit("", "expand_all")
            elif chosen == act_collapse_all:
                self.collapseAll()
                self.contextAction.emit("", "collapse_all")
            return


        path = self._item_path(item)
        is_parent = item.childCount() > 0
        checked = (item.checkState(0) == QtCore.Qt.Checked)

        # Check actions
        act_check = menu.addAction("Check")
        act_uncheck = menu.addAction("Uncheck")
        act_toggle = menu.addAction("Toggle check")

        menu.addSeparator()

        # Add/remove actions
        act_add_parent = menu.addAction("Add parent under this")
        act_add_leaf = menu.addAction("Add leaf under this")
        act_remove = menu.addAction("Remove this")

        if not is_parent:
            act_add_leaf.setEnabled(False)  # leaf can't have children in our semantics
            act_add_parent.setEnabled(False)

        menu.addSeparator()

        act_move_up = menu.addAction("Move up")
        act_move_down = menu.addAction("Move down")

        # Disable when movement is impossible
        parent = item.parent()
        if parent is None:
            idx = self.indexOfTopLevelItem(item)
            act_move_up.setEnabled(idx > 0)
            act_move_down.setEnabled(idx < self.topLevelItemCount() - 1)
        else:
            idx = parent.indexOfChild(item)
            act_move_up.setEnabled(idx > 0)
            act_move_down.setEnabled(idx < parent.childCount() - 1)


        # Expand/collapse for parents
        if is_parent:
            act_expand = menu.addAction("Expand")
            act_collapse = menu.addAction("Collapse")
        else:
            act_print = menu.addAction("Print path")

        chosen = menu.exec_(self.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        if chosen == act_check:
            self._apply_check_from_menu(item, QtCore.Qt.Checked)
            self.contextAction.emit(path, "check")
        elif chosen == act_uncheck:
            self._apply_check_from_menu(item, QtCore.Qt.Unchecked)
            self.contextAction.emit(path, "uncheck")
        elif chosen == act_toggle:
            new_state = QtCore.Qt.Unchecked if checked else QtCore.Qt.Checked
            self._apply_check_from_menu(item, new_state)
            self.contextAction.emit(path, "toggle")
        elif chosen == act_add_parent:
            new_item = self.add_parent(item, "New Parent")
            self.setCurrentItem(new_item)
            self.editItem(new_item, 0)
            self.contextAction.emit(path, "add_parent")
        elif chosen == act_add_leaf:
            new_item = self.add_leaf(item, "New Leaf")
            self.setCurrentItem(new_item)
            self.editItem(new_item, 0)
            self.contextAction.emit(path, "add_leaf")
        elif chosen == act_remove:
            self.remove_item(item)
            self.contextAction.emit(path, "remove")
        elif is_parent and chosen == act_expand:
            item.setExpanded(True)
            self.contextAction.emit(path, "expand")
        elif is_parent and chosen == act_collapse:
            item.setExpanded(False)
            self.contextAction.emit(path, "collapse")
        elif (not is_parent) and chosen == act_print:
            print(f"PATH: {path}")
            self.contextAction.emit(path, "print_path")
        elif chosen == act_move_up:
            if self.move_item_up(item):
                self.setCurrentItem(item)
                self.contextAction.emit(path, "move_up")
        elif chosen == act_move_down:
            if self.move_item_down(item):
                self.setCurrentItem(item)
                self.contextAction.emit(path, "move_down")


    def _apply_check_from_menu(self, item: QtWidgets.QTreeWidgetItem, state: QtCore.Qt.CheckState):
        try:
            self._updating = True
            item.setCheckState(0, state)
        finally:
            self._updating = False
        self._handle_user_toggle(item)

    # ----------------------------
    # Build helpers
    # ----------------------------

    def set_check_policy(self, item: QtWidgets.QTreeWidgetItem, policy: int):
        """
        Store checkability policy on the item.
        """
        item.setData(0, self._CHECK_POLICY_ROLE, policy)

    def check_policy(self, item: QtWidgets.QTreeWidgetItem) -> int | None:
        return item.data(0, self._CHECK_POLICY_ROLE)


    def _ensure_folder_checkable(self, item: QtWidgets.QTreeWidgetItem):
        """
        If an item has children, it must be checkable.
        """
        if item.childCount() > 0:
            flags = item.flags()
            if not (flags & QtCore.Qt.ItemIsUserCheckable):
                flags |= QtCore.Qt.ItemIsUserCheckable
                item.setFlags(flags)
                item.setCheckState(0, QtCore.Qt.Unchecked)

    def _ensure_leaf_not_checkable(self, item: QtWidgets.QTreeWidgetItem):
        """
        If an item has no children, it must NOT be checkable.
        """
        if item.childCount() == 0:
            flags = item.flags()
            if flags & QtCore.Qt.ItemIsUserCheckable:
                flags &= ~QtCore.Qt.ItemIsUserCheckable
                item.setFlags(flags)

    # ---- Drop flags (bitmask stored on items) ----
    DROP_ACCEPT_CHILDREN = 0x01   # item can accept drops ONTO it (become parent)
    DROP_DEFAULT = DROP_ACCEPT_CHILDREN

    _DROP_ROLE = QtCore.Qt.UserRole + 101  # where we store the bitmask

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
        Convenience: allow/deny dropping ONTO this item (making it the new parent).
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
        target_item: QtWidgets.QTreeWidgetItem,
        drop_pos: QtWidgets.QAbstractItemView.DropIndicatorPosition,
    ) -> bool:
        """
        Predicate for whether a drop is allowed.

        Rules implemented:
          - Roots (top-level) are not draggable (handled in startDrag/dropEvent)
          - No drops that would create a new root (handled in dropEvent rollback)
          - If dropping ONTO an item (OnItem), it must have DROP_ACCEPT_CHILDREN
            (this is what you use to lock certain roots)
        """
        if dragged is None:
            return False

        # Example policy: only restrict drops ONTO items (reparenting)
        if drop_pos == QtWidgets.QAbstractItemView.OnItem and target_item is not None:
            flags = self.drop_flags(target_item)
            if (flags & self.DROP_ACCEPT_CHILDREN) == 0:
                return False

        return True

    def _is_descendant(self, possible_ancestor: QtWidgets.QTreeWidgetItem,
                       possible_descendant: QtWidgets.QTreeWidgetItem) -> bool:
        cur = possible_descendant
        while cur is not None:
            if cur is possible_ancestor:
                return True
            cur = cur.parent()
        return False

    def _root_of(self, item: QtWidgets.QTreeWidgetItem) -> QtWidgets.QTreeWidgetItem:
        cur = item
        while cur.parent() is not None:
            cur = cur.parent()
        return cur

    def dropEvento(self, event: QtGui.QDropEvent):
        """
        Enables drag+drop moving items within the tree (reorder + reparent).
        Prevents dropping an item into its own descendant.
        Refreshes parent partial-check states after the move.
        """
        # Track the dragged item and its original parent chain before Qt moves it.
        dragged = self.currentItem()
        if dragged is None:
            super().dropEvent(event)
            return

        old_parent = dragged.parent()  # None means top-level
        old_parent_for_refresh = old_parent if old_parent is not None else None

        # Determine target item under cursor
        target = self.itemAt(event.pos())

        # Prevent dropping into own subtree (e.g., dragging "Animals" onto "Birds")
        if target is not None and self._is_descendant(dragged, target):
            event.ignore()
            return

        moved_path_before = self._item_path(dragged)

        # Let Qt perform the internal move
        try:
            self._updating = True  # prevent checkbox handlers firing during structural move
            super().dropEvent(event)
        finally:
            self._updating = False

        # After move, refresh check states for both old and new parent chains
        new_parent = dragged.parent()
        if old_parent_for_refresh is not None:
            self._refresh_upwards(old_parent_for_refresh)
        if new_parent is not None:
            self._refresh_upwards(new_parent)

        # If it became a top-level item (new_parent is None), refresh its root chain
        # (No parent to update, but its former ancestors already handled above.)
        # Also refresh the root if you want to ensure top-level partial state correctness:
        # (This is optional; usually not necessary.)
        # self._refresh_upwards(dragged)

        # Emit optional structural change signal
        new_parent_path = self._item_path(new_parent) if new_parent is not None else ""
        self.structureChanged.emit(moved_path_before, "moved", new_parent_path)

    def startDrag(self, supportedActions):
        """
        Prevent dragging of root (top-level) items.
        """
        item = self.currentItem()
        if item is not None and item.parent() is None:
            return  # root folders are not draggable
        super().startDrag(supportedActions)

    def dropEvent(self, event: QtGui.QDropEvent):
        dragged = self.currentItem()
        if dragged is None:
            super().dropEvent(event)
            return

        # Root folders cannot be moved at all
        if dragged.parent() is None:
            event.ignore()
            return

        old_parent = dragged.parent()
        old_index = old_parent.indexOfChild(dragged)

        target = self.itemAt(event.pos())
        drop_pos = self.dropIndicatorPosition()

        # Prevent dropping into own subtree
        if target is not None and self._is_descendant(dragged, target):
            event.ignore()
            return

        # Determine the "intended parent" (who will receive dragged as a child)
        # OnItem => target becomes parent
        # Above/Below => target.parent() becomes parent (or None if target is root)
        intended_parent = None
        if drop_pos == QtWidgets.QAbstractItemView.OnItem:
            intended_parent = target
        elif target is not None:
            intended_parent = target.parent()

        # Apply predicate rule
        if not self.can_drop(dragged, intended_parent, drop_pos):
            event.ignore()
            return

        moved_path_before = self._item_path(dragged)

        try:
            self._updating = True
            super().dropEvent(event)
        finally:
            self._updating = False

        # Disallow creating new top-level items (rollback if happened)
        if dragged.parent() is None:
            try:
                self._updating = True
                top_idx = self.indexOfTopLevelItem(dragged)
                if top_idx >= 0:
                    self.takeTopLevelItem(top_idx)
                old_parent.insertChild(old_index, dragged)
            finally:
                self._updating = False

            self._refresh_upwards(old_parent)
            event.ignore()
            return

        # Refresh partial-check states
        self._refresh_upwards(old_parent)
        self._refresh_upwards(dragged.parent())

        # Optional structural signal, if you added it previously
        if hasattr(self, "structureChanged"):
            new_parent_path = self._item_path(dragged.parent()) if dragged.parent() else ""
            self.structureChanged.emit(moved_path_before, "moved", new_parent_path)

    def dropEvento(self, event: QtGui.QDropEvent):
        """
        Allow internal moves for non-root items, but:
          - prevent dragging root folders
          - prevent drops that would create new top-level items
        """
        dragged = self.currentItem()
        if dragged is None:
            super().dropEvent(event)
            return

        # 1) Root folders cannot be moved at all
        if dragged.parent() is None:
            event.ignore()
            return

        # Remember original position to allow rollback if needed
        old_parent = dragged.parent()
        old_index = old_parent.indexOfChild(dragged)

        # Disallow dropping into own subtree
        target = self.itemAt(event.pos())
        if target is not None and self._is_descendant(dragged, target):
            event.ignore()
            return

        moved_path_before = self._item_path(dragged)

        try:
            self._updating = True  # avoid triggering checkbox logic during the structural move
            super().dropEvent(event)
        finally:
            self._updating = False

        # 2) If the drop made it top-level (new root), rollback
        if dragged.parent() is None:
            try:
                self._updating = True
                top_idx = self.indexOfTopLevelItem(dragged)
                if top_idx >= 0:
                    self.takeTopLevelItem(top_idx)
                old_parent.insertChild(old_index, dragged)
            finally:
                self._updating = False

            # refresh check/partial state on the restored chain
            self._refresh_upwards(old_parent)
            event.ignore()
            return

        # Refresh partial-check states (old chain + new chain)
        self._refresh_upwards(old_parent)
        self._refresh_upwards(dragged.parent())

        # Optional structural signal (if you added it earlier)
        if hasattr(self, "structureChanged"):
            new_parent_path = self._item_path(dragged.parent()) if dragged.parent() else ""
            self.structureChanged.emit(moved_path_before, "moved", new_parent_path)

    # def _add_children(self, parent_item, subtree):
    #     if isinstance(subtree, dict):
    #         for k, v in subtree.items():
    #             child = self._make_item(str(k), parent=parent_item, checkable=True)
    #             self._add_children(child, v)
    #             self._add_children(child, v)
    #         return
    #     if isinstance(subtree, (list, tuple, set)):
    #         for elem in subtree:
    #             child = self._make_item(self._label(elem), parent=parent_item, checkable=True)
    #             self._add_children(child, elem)
    #         return
    #     return

    def remove_all_children(self, parent_item: QtWidgets.QTreeWidgetItem) -> bool:
        """
        Remove all children of the given parent item, but keep the parent itself.

        Returns True if children were removed,
        False if parent_item is None or has no children.
        """
        if parent_item is None or parent_item.childCount() == 0:
            return False

        try:
            self._updating = True
            parent_item.takeChildren()
        finally:
            self._updating = False

        # Recompute parent check / partial state upwards
        self._refresh_upwards(parent_item)

        return True

    def _label(self, x):
        if isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], (str, int, float)):
            return str(x[0])
        return str(x)

    def _make_itemo(
        self,
        text: str,
        parent: QtWidgets.QTreeWidgetItem | None,
        checkable: bool = True,
    ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([text])

        if not checkable:
            item.setFlags(
                item.flags()
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
            )
        else:
            item.setFlags(
                item.flags()
                | Qt.ItemIsSelectable
                | Qt.ItemIsEnabled
                | Qt.ItemIsUserCheckable
            )



        # item.setFlags(
        #     item.flags()
        #     | Qt.ItemIsEnabled
        # )
        #
#        print (f"this item: {item} is checkable: {checkable}")
#         flags = item.flags()
#         if checkable:
#             flags |= QtCore.Qt.ItemIsUserCheckable
#             item.setCheckState(0, QtCore.Qt.Unchecked)
        # #else:
        #     #flags &= ~QtCore.Qt.ItemIsUserCheckable
        #
        #
        # item.setFlags(flags | QtCore.Qt.ItemIsSelectable)

        if parent is not None:
            parent.addChild(item)

        return item

    def _make_item(
        self,
        text: str,
        parent: QtWidgets.QTreeWidgetItem | None,
        checkable: bool = True,
    ) -> QtWidgets.QTreeWidgetItem:
        item = QtWidgets.QTreeWidgetItem([text])

        flags = item.flags() | QtCore.Qt.ItemIsEditable

        if checkable:
            flags |= QtCore.Qt.ItemIsUserCheckable
            item.setCheckState(0, QtCore.Qt.Unchecked)
        else:
            flags &= ~QtCore.Qt.ItemIsUserCheckable

        item.setFlags(flags)

        if parent is not None:
            parent.addChild(item)

            # Parent is a folder → must be checkable
            self._ensure_folder_checkable(parent)

        return item


    def set_item_checkable(
        self,
        item: QtWidgets.QTreeWidgetItem,
        checkable: bool,
        recursive: bool = False,
        clear_state: bool = True,
    ) -> bool:
        """
        Enable or disable the checkbox for an item.

        Args:
            item: target item
            checkable: True = show checkbox, False = remove checkbox
            recursive: apply to all descendants
            clear_state: when disabling, force Unchecked state

        Returns:
            True if applied, False if item is None
        """
        if item is None:
            return False

        try:
            self._updating = True

            flags = item.flags()
            if checkable:
                flags |= QtCore.Qt.ItemIsUserCheckable
            else:
                flags &= ~QtCore.Qt.ItemIsUserCheckable

            item.setFlags(flags)

            if not checkable and clear_state:
                item.setCheckState(0, QtCore.Qt.Unchecked)

            if recursive:
                for i in range(item.childCount()):
                    self.set_item_checkable(
                        item.child(i),
                        checkable,
                        recursive=True,
                        clear_state=clear_state,
                    )

        finally:
            self._updating = False

        # Refresh parent partial state if needed
        self._refresh_upwards(item)

        return True

    # ----------------------------
    # Check logic + signals
    # ----------------------------
    def _on_item_changed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        if column != 0 or self._updating:
            return
        self._handle_user_toggle(item)

    def _handle_user_toggle(self, item: QtWidgets.QTreeWidgetItem):
        state = item.checkState(0)
        checked = (state == QtCore.Qt.Checked)

        if item.childCount() > 0:
            self.parentToggled.emit(self._item_path(item), checked)

            try:
                self._updating = True
                self._set_subtree_checkstate(item, state)
                self._update_parents(item)
            finally:
                self._updating = False

            for leaf in self._iter_leaves(item):
                self.leafToggled.emit(item,self._item_path(leaf), checked)
            return

        self.leafToggled.emit(item,self._item_path(item), checked)
        try:
            self._updating = True
            self._update_parents(item)
        finally:
            self._updating = False

    def _set_subtree_checkstate(self, root: QtWidgets.QTreeWidgetItem, state: QtCore.Qt.CheckState):
        """
        Apply check state only to folders (items with children).
        Leaves never get a check state.
        """
        if state == QtCore.Qt.PartiallyChecked:
            return

        for i in range(root.childCount()):
            child = root.child(i)

            if child.childCount() > 0:
                # child is a folder -> can be checked
                child.setCheckState(0, state)
                self._set_subtree_checkstate(child, state)
            else:
                # child is a leaf -> ensure no checkbox / state role exists
                self._ensure_leaf_not_checkable(child)

    def _set_subtree_checkstateo(self, root, state):
        if state == QtCore.Qt.PartiallyChecked:
            return
        for i in range(root.childCount()):
            child = root.child(i)
            child.setCheckState(0, state)
            self._set_subtree_checkstate(child, state)

    def _update_parents(self, item):
        parent = item.parent()
        while parent is not None:
            #parent.setCheckState(0, self._aggregate_state(parent))
            parent = parent.parent()

    def _aggregate_state(self, parent):
        checked = 0
        unchecked = 0
        partial = 0

        for i in range(parent.childCount()):
            s = parent.child(i).checkState(0)
            if s == QtCore.Qt.Checked:
                checked += 1
            elif s == QtCore.Qt.Unchecked:
                unchecked += 1
            else:
                partial += 1

        if partial > 0:
            return QtCore.Qt.PartiallyChecked
        if checked > 0 and unchecked > 0:
            return QtCore.Qt.PartiallyChecked
        if checked == parent.childCount() and parent.childCount() > 0:
            return QtCore.Qt.Checked
        return QtCore.Qt.Unchecked

    def _iter_leaves(self, item):
        queue = [item]
        while queue:
            node = queue.pop(0)
            if node.childCount() == 0:
                yield node
            else:
                for i in range(node.childCount()):
                    queue.append(node.child(i))

    def _item_path(self, item):
        parts = []
        cur = item
        while cur is not None:
            parts.append(cur.text(0))
            cur = cur.parent()
        return " / ".join(reversed(parts))

    def _refresh_upwards(self, item):
        """
        Recompute check/partial states upwards from item.parent().
        """
        try:
            self._updating = True
            self._update_parents(item)
        finally:
            self._updating = False

def setup_input_tree(self, root_label=None):
    self.input_tree = CheckableTree(self)
    self.input_tree.setHeaderHidden(True)


    self.input_tree.parentToggled.connect(self.on_parent_toggled)
    self.input_tree.leafToggled.connect(self.on_leaf_toggled)
    self.input_tree.contextAction.connect(self.on_context_action)
    #self.input_tree.structureChanged.connect(self.on_structure_changed)

    self.input_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.input_tree.customContextMenuRequested.connect(self._on_window_tree_context_menu)

    setup_test_tree(self)
    #self.input_tree.clear_tree()
    #setup_test_tree(self)

def setup_test_tree(self):

    self.input_tree.blockSignals(True)
    self.c_well_root_item = self.input_tree.add_root("Wells")

    self.c_well_tops_folder = self.input_tree.add_root("Tops")
    self.c_stratigraphy_root = self.input_tree.add_parent(self.c_well_tops_folder,"Stratigraphy")
    self.c_faults_root = self.input_tree.add_parent(self.c_well_tops_folder,"Faults")
    self.c_other_root = self.input_tree.add_parent(self.c_well_tops_folder,"Other")

    self.c_logs_folder = self.input_tree.add_root("Logs")

    self.c_tracks_folder = self.input_tree.add_root("Tracks")

    self.input_tree.set_accept_children_drop(self.c_well_root_item, False)
    self.input_tree.set_accept_children_drop(self.c_logs_folder, False)
    self.input_tree.set_accept_children_drop(self.c_tracks_folder, False)
    self.input_tree.set_accept_children_drop(self.c_stratigraphy_root, False)
    self.input_tree.set_accept_children_drop(self.c_faults_root, False)
    self.input_tree.set_accept_children_drop(self.c_other_root, False)

    #self.input_tree.setCurrentItem(c_wells_root)

    self.input_tree.blockSignals(False)
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
