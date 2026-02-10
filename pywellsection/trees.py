from PySide6.QtWidgets import (
    QDockWidget, QTreeWidget,
    QTreeWidgetItem, )

from PySide6 import QtCore, QtWidgets, QtGui

from PySide6.QtCore import Qt

import logging

LOG = logging.getLogger(__name__)
LOG.setLevel("INFO")

class CheckableTree(QtWidgets.QTreeWidget):
    leafToggled = QtCore.Signal(str, bool)
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
    def build_tree(self, data, root_label=None):
        self.clear()

        if root_label is not None:
            root = self._make_item(str(root_label), parent=None)
            self.addTopLevelItem(root)
            self._add_children(root, data)
        else:
            if isinstance(data, dict):
                for k, v in data.items():
                    node = self._make_item(str(k), parent=None)
                    self.addTopLevelItem(node)
                    self._add_children(node, v)
            else:
                for elem in (data if isinstance(data, (list, tuple, set)) else [data]):
                    node = self._make_item(self._label(elem), parent=None)
                    self.addTopLevelItem(node)
                    self._add_children(node, elem)

        self.expandAll()

    def add_root(self, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add a new root (top-level) item.
        Returns the created root item.
        """
        root = self._make_item(text, parent=None)
        self.addTopLevelItem(root)

        # ensure consistent check state visuals
        try:
            self._updating = True
            root.setCheckState(0, QtCore.Qt.Unchecked)
        finally:
            self._updating = False

        return root

    def add_parent(self, parent_item, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add a new parent node under parent_item (or as top-level if parent_item is None).
        Returns the created item.
        """
        new_item = self._make_item(text, parent=None)

        if parent_item is None:
            self.addTopLevelItem(new_item)
        else:
            parent_item.addChild(new_item)
            parent_item.setExpanded(True)

        # keep parents consistent (tri-state display)
        self._refresh_upwards(new_item)
        return new_item

    def add_leaf(self, parent_item, text: str) -> QtWidgets.QTreeWidgetItem:
        """
        Add a new leaf node under parent_item (must not be None).
        The new leaf inherits parent's checked state if parent is Checked/Unchecked.
        Returns the created leaf item.
        """
        if parent_item is None:
            raise ValueError("add_leaf requires a non-None parent_item")

        leaf = self._make_item(text, parent=parent_item)

        # Inherit parent's check state if it's not partial
        pstate = parent_item.checkState(0)
        if pstate in (QtCore.Qt.Checked, QtCore.Qt.Unchecked):
            try:
                self._updating = True
                leaf.setCheckState(0, pstate)
            finally:
                self._updating = False

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

    def _add_children(self, parent_item, subtree):
        if isinstance(subtree, dict):
            for k, v in subtree.items():
                child = self._make_item(str(k), parent=parent_item)
                self._add_children(child, v)
            return
        if isinstance(subtree, (list, tuple, set)):
            for elem in subtree:
                child = self._make_item(self._label(elem), parent=parent_item)
                self._add_children(child, elem)
            return
        return

    def _label(self, x):
        if isinstance(x, tuple) and len(x) == 2 and isinstance(x[0], (str, int, float)):
            return str(x[0])
        return str(x)

    def _make_item(self, text: str, parent):
        item = QtWidgets.QTreeWidgetItem([text])
        item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEditable)
        item.setCheckState(0, QtCore.Qt.Unchecked)
        if parent is not None:
            parent.addChild(item)
        return item

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
                self.leafToggled.emit(self._item_path(leaf), checked)
            return

        self.leafToggled.emit(self._item_path(item), checked)
        try:
            self._updating = True
            self._update_parents(item)
        finally:
            self._updating = False

    def _set_subtree_checkstate(self, root, state):
        if state == QtCore.Qt.PartiallyChecked:
            return
        for i in range(root.childCount()):
            child = root.child(i)
            child.setCheckState(0, state)
            self._set_subtree_checkstate(child, state)

    def _update_parents(self, item):
        parent = item.parent()
        while parent is not None:
            parent.setCheckState(0, self._aggregate_state(parent))
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


def setup_checkable_tree(self, root_label=None):
    self.checkable_tree = CheckableTree(self)
    self.checkable_tree.setHeaderHidden(True)

    self.checkable_tree.parentToggled.connect(self.on_parent_toggled)
    self.checkable_tree.leafToggled.connect(self.on_leaf_toggled)

    self.checkable_tree.setContextMenuPolicy(Qt.CustomContextMenu)
    self.checkable_tree.customContextMenuRequested.connect(self._on_window_tree_context_menu)

    self.c_well_root_item = self.checkable_tree.add_root("Wells")

    self.c_well_tops_folder = self.checkable_tree.add_root("Tops")
    self.c_stratigraphy_root = self.checkable_tree.add_parent(self.c_well_tops_folder,"Stratigraphy")
    self.c_faults_root = self.checkable_tree.add_parent(self.c_well_tops_folder,"Faults")
    self.c_other_root = self.checkable_tree.add_parent(self.c_well_tops_folder,"Other")

    self.c_logs_folder = self.checkable_tree.add_root("Logs")

    self.c_tracks_folder = self.checkable_tree.add_root("Tracks")


    self.checkable_tree.set_accept_children_drop(self.c_well_root_item, False)
    self.checkable_tree.set_accept_children_drop(self.c_logs_folder, False)
    self.checkable_tree.set_accept_children_drop(self.c_tracks_folder, False)
    self.checkable_tree.set_accept_children_drop(self.c_stratigraphy_root, False)
    self.checkable_tree.set_accept_children_drop(self.c_faults_root, False)
    self.checkable_tree.set_accept_children_drop(self.c_other_root, False)

    #self.checkable_tree.setCurrentItem(c_wells_root)


    # Build from external demo data

    self.statusBar().showMessage("Toggle a checkbox...")
    #self.checkable_tree.build_tree(build_demo_data())

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
    self.well_root_item.setData(0, Qt.UserRole, "wells")
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
    self.well_tops_folder.setData(0, Qt.UserRole, "well_tops")
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
    self.stratigraphy_root.setData(0, Qt.UserRole, "strat_tops")
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

    self.faults_root.setData(0, Qt.UserRole, "faults_tops")
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
    self.other_root.setData(0, Qt.UserRole, "other_tops")
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
    self.well_logs_folder.setData(0, Qt.UserRole, "well_logs")
    self.well_tree.addTopLevelItem(self.well_logs_folder)

    self.continuous_logs_folder = QTreeWidgetItem(["continuous Logs"])
    self.continuous_logs_folder.setFlags(
        self.continuous_logs_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.continuous_logs_folder.setCheckState(0, Qt.Unchecked)
    self.continuous_logs_folder.setData(0, Qt.UserRole, "continuous_logs")
    self.well_logs_folder.addChild(self.continuous_logs_folder)

    self.discrete_logs_folder = QTreeWidgetItem(["Discrete Logs"])
    self.discrete_logs_folder.setFlags(
        self.discrete_logs_folder.flags()
        | Qt.ItemIsUserCheckable
        | Qt.ItemIsAutoTristate
        | Qt.ItemIsSelectable
        | Qt.ItemIsEnabled
    )
    self.discrete_logs_folder.setCheckState(0, Qt.Unchecked)
    self.discrete_logs_folder.setData(0, Qt.UserRole, "discrete_logs")
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
    self.bitmaps_folder.setData(0, Qt.UserRole, "bitmaps")
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
    self.track_root_item.setData(0, Qt.UserRole, "tracks")
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
    self.stratigraphy_root_item.setData(0, Qt.UserRole, "stratigraphy")
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


