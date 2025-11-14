from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure

import sys

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QScrollArea, QDialog, QMenu, QVBoxLayout, QMessageBox
)

from .multi_wells_panel import draw_multi_wells_panel_on_figure
from .multi_wells_panel import add_tops_and_correlations
from .sample_data import create_dummy_data
from .dialogs import EditFormationTopDialog
from .dialogs import AddFormationTopDialog


import numpy as np


class WellPanelWidget(QWidget):
    def __init__(self, wells, tracks, stratigraphy, parent=None):
        super().__init__(parent)
        self.wells = wells
        self.well = None
        self.tracks = tracks
        self.all_tracks = tracks
        self.n_tracks = len(tracks)
        self.stratigraphy = stratigraphy
        self.logs = None

        self.highlight_top = None
        self.visible_tops = None
        self.visible_logs = None
        self.visible_discrete_logs = None
        self.visible_tracks = tracks
        #self._temp_highlight_top = None

        self.fig = Figure(figsize=(12, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFixedSize(1200, 800)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.canvas)
        self.scroll_area.setWidgetResizable(False)

        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)

        self._syncing_ylim = False
        self._ylim_cids = []
        self._corr_artists = []


        # ... your figure / canvas / toolbar / layout setup ...

        self.axis_index = {}          # axis -> (well_index, track_index)
        self._pick_cid = None         # global click handler id
        self._dialog_pick_cid = None  # one-shot pick-on-plot handler id
        self._motion_pick_cid = None
        self._in_dialog_pick_mode = False
        self._active_top_dialog = None
        self._active_pick_context = None  # {'wi': int, 'formation_name': str}
        self.ax = None

        # temporary highlight of a selected top (optional)
        self._temp_highlight_artists = []

        # hatched moving line during 'pick on plot'
        self._pick_line_artists = []

        self._picked_depth = None
        self._picked_formation = None

        self._flatten_top_name = None
        self._flatten_depths = []

        self.draw_panel()
        self.enable_top_picking()

    def draw_panel(self):
        if len(self.wells) != 0:
            self.fig.clear()
            self._corr_artists = []
            flatten_depths = self._flatten_depths
            visible_tops = self.visible_tops
            visible_logs = self.visible_logs
            visible_discrete_logs = self.visible_discrete_logs
            visible_tracks = self.visible_tracks



            self.axes, self.well_main_axes = draw_multi_wells_panel_on_figure(
                self.fig,
                self.wells,
                self.tracks,
                suptitle="Well Log Panel",
                corr_artists=self._corr_artists,
                highlight_top=self.highlight_top,
                flatten_depths=flatten_depths,
                visible_tops = visible_tops,
                visible_logs = visible_logs,
                visible_discrete_logs=visible_discrete_logs,
                visible_tracks = visible_tracks,
            )
            self._connect_ylim_sync()
            self._build_axis_index()

            #draw_multi_wells_panel_on_figure(self.fig,self.wells,self.tracks)
            self.canvas.draw()

    def update_panel(self,tracks, wells, stratigraphy):
        self.tracks = tracks
        self.n_tracks = len(tracks)
        self.wells = wells
        self.stratigraphy = stratigraphy
        self.draw_panel()

    def enable_top_picking(self):
        """
        Connect a mouse-click handler so the user can pick & edit formation tops.
        """
        if self._pick_cid is None:
            self._pick_cid = self.canvas.mpl_connect(
                "button_press_event", self._on_top_click
            )

        #--- Helpers

    def _dialog_accepted(self):
        """OK clicked on dialog: update top and redraw."""
        if self._active_top_dialog is None:
            print ("no more top dialog?")
            return

        wi = self._active_pick_context["wi"]
        well = self.wells[wi]
        tops = well["tops"]

        new_depth = self._active_top_dialog.value()
        self.top_depth = new_depth
        nearest_name=self._picked_formation

        old_val = tops[nearest_name]
        if isinstance(old_val, dict):
            updated_val = dict(old_val)
            updated_val["depth"] = new_depth
            self._active_top_dialog = None
        else:
            updated_val = new_depth

        tops[nearest_name] = updated_val

        self.top_depth = new_depth
        self._active_top_dialog = None
        self._active_pick_context = None
        self._clear_pick_line()
        self.draw_panel()

    def _dialog_rejected(self):
        """Cancel clicked: just clean up."""
        self._active_top_dialog = None
        self._active_pick_context = None
        self._clear_pick_line()
        # no change to self.top_depth

    # ---------- PICK MODE ----------
    def _arm_pick_for_dialog(self):
        """Hide dialog and start pick-on-plot mode."""
        if self._active_top_dialog is None or self._active_pick_context is None:
            return

        self._active_top_dialog.hide()
        self._in_dialog_pick_mode = True

        # disconnect previous pick handlers
        if self._dialog_pick_cid is not None:
            self.canvas.mpl_disconnect(self._dialog_pick_cid)
            self._dialog_pick_cid = None
        if self._motion_pick_cid is not None:
            self.canvas.mpl_disconnect(self._motion_pick_cid)
            self._motion_pick_cid = None

        # connect handlers
        self._dialog_pick_cid = self.canvas.mpl_connect(
            "button_press_event", self._handle_dialog_pick_click
        )
        self._motion_pick_cid = self.canvas.mpl_connect(
            "motion_notify_event", self._handle_dialog_pick_move
        )

    def _clear_pick_line(self):
        for art in self._pick_line_artists:
            try:
                art.remove()
            except Exception:
                pass
        self._pick_line_artists = []
        self.canvas.draw_idle()

    def _handle_dialog_pick_click(self, event):
        """Click once to set depth and return to dialog."""
        if not self._in_dialog_pick_mode:
            return
        if self._active_pick_context is None:
            return

        wi = self._active_pick_context["wi"]

        if self._flatten_depths is not None:
        #if len(self._flatten_depths) > 0:
            flatten_depth = self._flatten_depths[wi]
        else:
            flatten_depth = 0
        print("dialog pick event received")

        ctx = self._active_pick_context
        depth = None
        if event.ydata is not None:
            depth = float(event.ydata)
            ctx["last_depth"] = depth
        else:
            depth = ctx.get("last_depth")

        depth = depth + flatten_depth

        formation_name = self._active_pick_context["formation_name"]

        min, max = self._get_stratigraphic_bounds(formation_name)

        if depth < min:
            depth = min
        if depth > max:
            depth = max

        if depth is not None and self._active_top_dialog is not None:
            self._active_top_dialog.set_depth(depth)

        # exit pick mode and remove band
        if self._dialog_pick_cid is not None:
            self.canvas.mpl_disconnect(self._dialog_pick_cid)
            self._dialog_pick_cid = None
        if self._motion_pick_cid is not None:
            self.canvas.mpl_disconnect(self._motion_pick_cid)
            self._motion_pick_cid = None

        self._in_dialog_pick_mode = False
        self._clear_pick_line()

        # show dialog again so user can OK/Cancel
        if self._active_top_dialog is not None:
            self._active_top_dialog.show()
            self._active_top_dialog.raise_()
            self._active_top_dialog.activateWindow()

    def _on_top_click(self, event):
        if self._in_dialog_pick_mode:
            return
        if event.button != 1:
            return

        mapped = self._map_event_to_well_axes(event)
        if mapped is None:
            return
        wi, ti, ax, depth_plot, depth_true = mapped

        well = self.wells[wi]
        if "tops" not in well or not well["tops"]:
            return

        # --- find nearest top in TRUE depth space ---
        tops = well["tops"]
        nearest_name = None
        nearest_depth = None
        min_dist = None

        for name, val in tops.items():
            d = float(val["depth"] if isinstance(val, dict) else val)
            dist = abs(d - depth_true)
            if min_dist is None or dist < min_dist:
                min_dist = dist
                nearest_name = name
                nearest_depth = d

        if nearest_name is None:
            return

        self._picked_depth = nearest_depth
        self._picked_formation = nearest_name

        # distance threshold based on TRUE depth range
        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]
        depth_range = abs(well_td - ref_depth) or 1.0
        max_pick_distance = depth_range * 0.02
        if min_dist > max_pick_distance:
            return

        # highlight top (your existing helper should already respect flattening
        # via add_tops_and_correlations if you pass flatten_depths there)
        self._clear_temp_highlight()
        self._draw_temp_highlight(wi, nearest_name)

        # --- context menu ---
        menu = QMenu(self)
        act_edit = menu.addAction(f"Edit top '{nearest_name}'…")
        act_delete = menu.addAction(f"Delete top '{nearest_name}'")
        act_add = menu.addAction(f"Add top at {depth_true:.2f} m…")
        act_flatten = menu.addAction(f"Flatten on '{nearest_name}'")

        if hasattr(event, "guiEvent") and event.guiEvent is not None:
            global_pos = event.guiEvent.globalPos()
        else:
            global_pos = QCursor.pos()

        chosen = menu.exec_(global_pos)
        if chosen is None:
            return

        if chosen == act_edit:
            self._edit_formation_top(
                well_index=wi,
                top_name=nearest_name,
                initial_depth=nearest_depth,  # TRUE depth
            )
            return

        if chosen == act_delete:
            self._delete_formation_top(well_index=wi, top_name=nearest_name)
            return

        if chosen == act_add:
            # pass TRUE depth into "add top" logic
            self._add_formation_top_at_depth(well_index=wi, depth=depth_true)
            return

        if chosen == act_flatten:
            self._flatten_on_formation_top(nearest_name)
            return

    def _build_axis_index(self):
        """
        Map each base track axis to its (well_index, track_index).
        Spacer axes are ignored.
        """
        self.axis_index.clear()
        n_wells = len(self.wells)
        #n_tracks = len(self.tracks)

        if self.visible_tracks is None:
            filtered_tracks = self.tracks[:]
        else:
            filtered_tracks = [t for t in self.tracks if t.get("name") in self.visible_tracks]

        if not filtered_tracks:
            n_tracks = 1
        else:
            n_tracks = len(filtered_tracks)


        # layout is [W0T0, W0T1, ..., spacer, W1T0, W1T1, ..., spacer, ...]
        for wi in range(n_wells):
            first_track_idx = wi * (n_tracks + 1)
            for ti in range(n_tracks):
                ax = self.axes[first_track_idx + ti]
                self.axis_index[ax] = (wi, ti)

    def _connect_ylim_sync(self):
        # disconnect old if any
        for ax, cid in getattr(self, "_ylim_cids", []):
            ax.callbacks.disconnect(cid)
        self._ylim_cids = []

        for ax in self.axes:
            cid = ax.callbacks.connect("ylim_changed", self._on_ylim_changed)
            self._ylim_cids.append((ax, cid))

    def _on_ylim_changed(self, changed_ax):
        if self._syncing_ylim:
            return

        self._syncing_ylim = True
        try:
            new_ylim = changed_ax.get_ylim()

            # sync all base axes
            for ax, cid in self._ylim_cids:
                if ax is changed_ax:
                    continue
                ax.set_ylim(new_ylim)

            # remove old correlation artists
            for art in self._corr_artists:
                art.remove()
            self._corr_artists.clear()

            # recompute correlations with current zoom
            add_tops_and_correlations(
                self.fig,
                self.axes,
                self.wells,
                self.well_main_axes,
                len(self.tracks),
                correlations_only=True,
                corr_artists=self._corr_artists,
                flatten_depths=self._flatten_depths
            )

            self.canvas.draw_idle()
        finally:
            self._syncing_ylim = False

    def _handle_dialog_pick_move(self, event):
        """
        While in dialog 'Pick on plot' mode, show a moving horizontal
        hatched band at the mouse depth for the selected well.
        """
        if self._active_top_dialog is None:
            print("dialog is None")

        if not self._in_dialog_pick_mode:
            return
        if self._active_pick_context is None:
            return
        if event.ydata is None:
            return

        wi_target = self._active_pick_context["wi"]
        depth = float(event.ydata)
        if self._flatten_depths is not None:
        #if len(self._flatten_depths) > 0:
            flatten_depth = self._flatten_depths[wi_target]
        else:
            flatten_depth = 0

        depth = depth - flatten_depth


        formation_name = self._active_pick_context["formation_name"]

        if formation_name is not None:
            min,max = self._get_stratigraphic_bounds(formation_name)

            if depth < min-flatten_depth:
                depth = min-flatten_depth
            if depth > max:
                depth = max-flatten_depth

        print("move", event.ydata, min, max, depth)




        # draw a thin hatched band across ALL tracks of the selected well
        self._clear_pick_line()
        first_track_idx = wi_target * (self.n_tracks + 1)

        for ti in range(self.n_tracks):
            base_ax = self.axes[first_track_idx + ti]

            # choose a small thickness relative to the depth range
            y0, y1 = base_ax.get_ylim()


            band = base_ax.axhline(depth+flatten_depth, color="tab:red", lw=1.2, ls="--", zorder=10)

            self._pick_line_artists.append(band)

        self.canvas.draw_idle()
    ###----
    # def _handle_dialog_pick_click(self, event):
    #     """
    #     One-click depth pick for the dialog:
    #       - use event.ydata if available; otherwise use last_depth from context
    #       - update dialog spinbox
    #       - ALWAYS exit pick mode, remove band, and show dialog again
    #     """
    #     print("click", event.ydata)
    #
    #     if not self._in_dialog_pick_mode:
    #         return
    #     if self._active_pick_context is None:
    #          return
    #
    #     ctx = self._active_pick_context
    #
    #     # Prefer depth from this click, but fall back to last valid depth
    #     depth = None
    #     if event.ydata is not None:
    #         depth = float(event.ydata)
    #         ctx["last_depth"] = depth
    #     else:
    #         depth = ctx.get("last_depth")
    #
    #     # If we have any valid depth, update the dialog spinbox
    #     if depth is not None:
    #         self._active_top_dialog.set_depth(depth)
    #
    #     # --- Exit pick mode no matter what ---
    #
    #     if self._dialog_pick_cid is not None:
    #         self.canvas.mpl_disconnect(self._dialog_pick_cid)
    #         self._dialog_pick_cid = None
    #     if self._motion_pick_cid is not None:
    #         self.canvas.mpl_disconnect(self._motion_pick_cid)
    #         self._motion_pick_cid = None
    #
    #     self._in_dialog_pick_mode = False
    #
    #     # Remove moving band
    #     self._clear_pick_line()
    #
    #     # Show dialog again so user can confirm / adjust / OK / Cancel
    #     self._active_top_dialog.show()
    #     self._active_top_dialog.raise_()
    #     self._active_top_dialog.activateWindow()
    #
    #     return depth
    #
    #
    # def _handle_dialog_pick(self, event):
    #     """
    #     Handle a single click while in dialog 'Pick on plot' mode:
    #       - take the ydata as depth
    #       - update the dialog's spinbox
    #       - exit pick mode
    #     """
    #     # only care about clicks inside an axis
    #     if event.inaxes is not None and event.ydata is not None and self._active_top_dialog is not None:
    #         depth = float(event.ydata)
    #         self._active_top_dialog.set_depth(depth)
    #
    #     # exit pick mode and disconnect handler
    #     if self._dialog_pick_cid is not None:
    #         self.canvas.mpl_disconnect(self._dialog_pick_cid)
    #         self._dialog_pick_cid = None
    #
    #     self._in_dialog_pick_mode = False
    #
    #     # prevent this click from also triggering _on_top_click afterwards
    #     # (we already consumed it)
    #
    #
    def _clear_temp_highlight(self):
        """Remove any temporary highlight artists (selected top)."""
        for art in self._temp_highlight_artists:
            try:
                art.remove()
            except Exception:
                pass
        self._temp_highlight_artists = []
        self.canvas.draw_idle()

    def _draw_temp_highlight(self, wi: int, top_name: str):
        """Highlight a top in a given well (used when top is first clicked)."""
        well = self.wells[wi]
        tops = well.get("tops", {})
        if top_name not in tops:
            return

        #if len(self._flatten_depths) > 0:
        if self._flatten_depths is not None:
            flatten_depth = self._flatten_depths[wi]
        else:
            flatten_depth = 0

        val = tops[top_name]
        if isinstance(val, dict):
            depth = float(val["depth"])
            color = val.get("color", "red")
        else:
            depth = float(val)
            color = "red"

        artists = []

        # bold line across all tracks of this well
        first_track_idx = wi * (self.n_tracks + 1)
        for ti in range(self.n_tracks):
            base_ax = self.axes[first_track_idx + ti]
            line = base_ax.axhline(
                depth-flatten_depth,
                xmin=0.0,
                xmax=1.0,
                color=color,
                linewidth=2.0,
                linestyle="-",
                zorder=3,
            )
            artists.append(line)

        # marker and label on main axis
        main_ax = self.well_main_axes[wi]
        x_min, x_max = main_ax.get_xlim()
        x_label_pos = x_min + 0.02 * (x_max - x_min)

        txt = main_ax.text(
            x_label_pos,
            depth- flatten_depth,
            top_name,
            va="center",
            ha="left",
            fontsize=9,
            color=color,
            bbox=dict(facecolor="yellow", alpha=0.8, edgecolor="black", pad=0.5),
            zorder=4,
        )
        artists.append(txt)

        marker = main_ax.plot(
            [x_min + 0.01 * (x_max - x_min)],
            [depth-flatten_depth],
            marker="o",
            markersize=6,
            markeredgecolor="black",
            markerfacecolor="yellow",
            zorder=4,
        )[0]
        artists.append(marker)

        self._temp_highlight_artists = artists
        self.canvas.draw_idle()

    def _edit_formation_top(self, well_index: int, top_name: str, initial_depth: float):
        """
        Open the edit dialog for a specific top of a specific well.
        Keeps all dialog + pick-on-plot behaviour in one place.
        """
        from PyQt5.QtWidgets import QDialog

        well = self.wells[well_index]
        tops = well["tops"]

        if top_name not in tops:
            return

        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        min_bound = ref_depth
        max_bound = well_td

        # store context for 'pick on plot'
        self._active_pick_context = {
            "wi": well_index,
            "formation_name": top_name,
            "last_depth": initial_depth,
        }

        dlg = EditFormationTopDialog(
            self,
            well_name=well.get("name", f"Well {well_index + 1}"),
            formation_name=top_name,
            current_depth=initial_depth,
            min_bound=min_bound,
            max_bound=max_bound,
        )
        self._active_top_dialog = dlg
        dlg.btn_pick.clicked.connect(self._arm_pick_for_dialog)

        # # wire up actions
        dlg.accepted.connect(self._dialog_accepted)
        dlg.rejected.connect(self._dialog_rejected)
        #
        print ("Starting Dialog")
        dlg.show()

    def _delete_formation_top(self, well_index: int, top_name: str):
        """
        Delete a formation top from a given well, after user confirmation.
        Redraws the panel and clears any highlight.
        """
        well = self.wells[well_index]
        tops = well.get("tops", {})

        if top_name not in tops:
            return

        # Optional confirmation dialog
        reply = QMessageBox.question(
            self,
            "Delete top",
            f"Delete top '{top_name}' in well '{well.get('name', well_index + 1)}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            # keep highlight or clear it, your choice:
            # self._clear_temp_highlight()
            return

        # Actually remove the top
        del tops[top_name]

        # Clear highlight and redraw correlations & fills
        self._clear_temp_highlight()
        self.draw_panel()

    def _get_stratigraphic_bounds(self, top_name: str):
        """
        Return (min_bound, max_bound) depth for a top so that moving it
        cannot violate the stratigraphic order defined in self.stratigraphy.

        - depths increase with depth (e.g. 1000 m -> 2000 m)
        - self.stratigraphy is ordered shallow -> deep
        """
        wi = self._active_pick_context["wi"]
        well = self.wells[wi]
        #well = self.well
        tops = well["tops"]

        if top_name not in tops:
            return

        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        # Default: whole well interval
        min_bound = ref_depth
        max_bound = well_td

        strat = getattr(self, "stratigraphy", None)
        if not strat or top_name not in strat:
            return min_bound, max_bound

        tops = well.get("tops", {})
        idx_map = {key: i for i, key in enumerate(tops)}
        idx = idx_map.get(top_name)

        idx_l=list(idx_map)

        if idx is None:
            return min_bound, max_bound
        else:
            if idx==0:
                return min_bound,tops[idx_l[idx+1]]["depth"]
            elif idx==len(idx_l)-1:
                print()
                return tops[idx_l[idx-1]]["depth"],max_bound
            else:
                return tops[idx_l[idx-1]]["depth"],tops[idx_l[idx+1]]["depth"]



        # #idx = strat.index(top_name)
        #
        # # Find shallower neighbor (earlier in strat list that exists in this well)
        # shallower_depth = None
        # for j in range(idx - 1, -1, -1):
        #     name_j = list(idx_map)[j]
        #     if name_j in tops:
        #         val = tops[name_j]
        #         shallower_depth = float(val["depth"] if isinstance(val, dict) else val)
        #         break
        #
        # # Find deeper neighbor (later in strat list that exists in this well)
        # deeper_depth = None
        # for j in range(idx, len(strat)):
        #     name_j = list(idx_map)[j]
        #     if name_j in tops:
        #         val = tops[name_j+1]
        #         deeper_depth = float(val["depth"] if isinstance(val, dict) else val)
        #         break
        #
        # eps = 1e-3  # small margin to avoid exact crossing
        #
        # # If we have a shallower neighbor, this sets the upper bound (shallower depth)
        # if shallower_depth is not None:
        #     min_bound = max(min_bound, shallower_depth + eps)
        #
        # # If we have a deeper neighbor, this sets the lower bound (deeper depth)
        # if deeper_depth is not None:
        #     max_bound = min(max_bound, deeper_depth - eps)
        #
        # # Ensure min_bound < max_bound (if strat is strange, just fall back)
        # if not (min_bound < max_bound):
        #     min_bound, max_bound = ref_depth, well_td

        return min_bound, max_bound

    def _add_formation_top_at_depth(self, well_index: int, depth: float):
        """
        At a picked depth in one well, find all stratigraphic units that can be
        inserted at that depth (without violating self.stratigraphy order),
        let the user choose one, and insert it.
        """
        well = self.wells[well_index]
        tops = well.setdefault("tops", {})

        if len(self._flatten_depths) > 0:
            flatten_depth = self._flatten_depths[wi_target]
        else:
            flatten_depth = 0

        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        # Basic sanity: depth must be within the well interval
        if not (ref_depth <= depth <= well_td):
            QMessageBox.information(
                self, "Add top",
                "Picked depth is outside the well interval."
            )
            return

        strat = getattr(self, "stratigraphy", None)
        if not strat:
            QMessageBox.information(
                self, "Add top",
                "No stratigraphic column is defined."
            )
            return

        # Build candidate list
        candidates: list[str] = []

        for name in strat:
            # Skip units already present in this well
            if name in tops:
                continue

            tops = well.get("tops", {})
            idx_map = {key: i for i, key in enumerate(tops)}
            idx = idx_map.get(name)
            idx_l = list(idx_map)
            shallower_depth = None
            deeper_depth = None
            ok = True

            if idx is None:
                shallower_depth = ref_depth
                deeper_depth = well_td
            else:
                if idx == 0:
                   shallower_depth = min_bound
                   deeper_depth = tops[idx_l[idx + 1]]["depth"]
                elif idx == len(idx_l) - 1:
                    shallower_depth=tops[idx_l[idx - 1]]["depth"]
                    deeper_depth = max_bound
                else:
                    shallower_depth = tops[idx_l[idx - 1]]["depth"]
                    deeper_depth = tops[idx_l[idx + 1]]["depth"]

                # Must be deeper than shallower neighbor (if it exists)
            if shallower_depth is not None and depth <= shallower_depth:
                ok = False
            # Must be shallower than deeper neighbor (if it exists)
            if deeper_depth is not None and depth >= deeper_depth:
                ok = False

            if ok:
                candidates.append(name)


            # # Find shallower neighbor in this well (in strat order)
            # shallower_depth = None
            # for j in range(idx - 1, -1, -1):
            #     n2 = strat[j]
            #     if n2 in tops:
            #         val2 = tops[n2]
            #         shallower_depth = float(val2["depth"] if isinstance(val2, dict) else val2)
            #         break
            #
            # # Find deeper neighbor in this well (in strat order)
            # deeper_depth = None
            # for j in range(idx + 1, len(strat)):
            #     n2 = strat[j]
            #     if n2 in tops:
            #         val2 = tops[n2]
            #         deeper_depth = float(val2["depth"] if isinstance(val2, dict) else val2)
            #         break



        if not candidates:
            QMessageBox.information(
                self, "Add top",
                "No stratigraphic units can be inserted at this depth\n"
                "without violating the stratigraphic order."
            )
            return

        # Let user choose which unit to insert
        dlg = AddFormationTopDialog(
            self,
            well_name=well.get("name", f"Well {well_index + 1}"),
            depth=depth,
            candidates=candidates,
        )

        if dlg.exec_() != QDialog.Accepted:
            return

        unit_name = dlg.selected_unit()
        if not unit_name:
            return

        # Insert new top at the picked depth
        # You can also choose to store dict with level/color if you like.
        # For now just store a numeric depth; your existing code handles that.
        tops[unit_name] = float(depth)

        # Clear highlight and redraw panel (tops, fills, correlations, etc.)
        self._clear_temp_highlight()
        self.draw_panel()

    def _build_axes(self):
        """(Re)build subplot layout and axis index from wells/tracks."""
        self.fig.clear()
        self.axes = []
        self.axis_index = {}

        self.n_wells = len(self.wells)
        self.n_tracks = len(self.tracks)

        # Example layout: each well has n_tracks + 1 spacer axes horizontally
        # adjust to your actual layout logic
        for wi in range(self.n_wells):
            for ti in range(self.n_tracks):
                ax = self.fig.add_subplot(
                    self.n_wells, self.n_tracks + 1, wi * (self.n_tracks + 1) + ti + 1
                )
                self.axes.append(ax)
                self.axis_index[ax] = (wi, ti)

            # spacer axis if you use one
            spacer_ax = self.fig.add_subplot(
                self.n_wells, self.n_tracks + 1, wi * (self.n_tracks + 1) + self.n_tracks + 1
            )
            spacer_ax.set_visible(False)
            self.axes.append(spacer_ax)

        self.fig.tight_layout()

    def _flatten_on_formation_top(self, top_name: str):
        """
        Compute per-well flatten depth for a given formation top, then redraw panel.

        For each well:
          - If the top exists: use its depth.
          - If not: use the midpoint between the nearest stratigraphic tops above
            and below (in this well's tops), based on self.stratigraphy.
        """
        if not self.stratigraphy or top_name not in self.stratigraphy:
            # Unknown in strat column -> do nothing
            return

        flatten_depths = []

        if type(self.stratigraphy) is list:
            idx_map = self.stratigraphy
        else:
            strat_keys = self.stratigraphy.keys()
            idx_map = list(strat_keys)

        idx_target = idx_map.index(top_name)

        for well in self.wells:
            tops = well.get("tops", {})

            # 1) Top exists in this well
            if top_name in tops:
                val = tops[top_name]
                d = float(val["depth"] if isinstance(val, dict) else val)
                flatten_depths.append(d)
                continue

            # 2) Top not present: find nearest above/below by stratigraphy
            shallower_depth = None
            deeper_depth = None

            # search shallower
            for j in range(idx_target - 1, -1, -1):
                nm = idx_map[j]
                if nm in tops:
                    v = tops[nm]
                    shallower_depth = float(v["depth"] if isinstance(v, dict) else v)
                    break

            # search deeper
            for j in range(idx_target + 1, len(self.stratigraphy)):
                nm = idx_map[j]
                if nm in tops:
                    v = tops[nm]
                    deeper_depth = float(v["depth"] if isinstance(v, dict) else v)
                    break

            # Decide flatten depth
            if shallower_depth is not None and deeper_depth is not None:
                d = 0.5 * (shallower_depth + deeper_depth)
            elif shallower_depth is not None:
                d = shallower_depth
            elif deeper_depth is not None:
                d = deeper_depth
            else:
                # No related tops at all -> fall back to reference depth
                ref_depth = well.get("reference_depth", 0.0)
                d = ref_depth

            flatten_depths.append(d)

        # Store state and redraw
        self._flatten_top_name = top_name
        self._flatten_depths = flatten_depths
        self.draw_panel()

    def _get_flatten_offset_for_well(self, wi: int) -> float:
        """Return flatten offset (true depth) for well index wi, or 0.0 if not flattened."""
        fd = getattr(self, "_flatten_depths", None)
        if not fd or wi >= len(fd):
            return 0.0
        return float(fd[wi])

    def _map_event_to_well_axes(self, event):
        """
        Map a Matplotlib event to (well_index, track_index, base_ax, depth_plot, depth_true).

        - depth_plot: what Matplotlib sees on the y-axis (flattened coordinates)
        - depth_true: physical depth, corrected by flatten offset
        """
        if event.inaxes is None or event.ydata is None:
            return None

        ax = event.inaxes

        # If event is on a twinx axis, map it to its base axis by overlap
        if ax not in self.axis_index:
            ax_pos = ax.get_position()
            best_ax = None
            best_overlap = 0.0
            for base_ax in self.axis_index.keys():
                pos = base_ax.get_position()
                x0 = max(ax_pos.x0, pos.x0)
                x1 = min(ax_pos.x1, pos.x1)
                y0 = max(ax_pos.y0, pos.y0)
                y1 = min(ax_pos.y1, pos.y1)
                overlap = max(0.0, x1 - x0) * max(0.0, y1 - y0)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_ax = base_ax
            if best_ax is None or best_overlap == 0.0:
                return None
            ax = best_ax

        wi, ti = self.axis_index[ax]
        depth_plot = float(event.ydata)
        offset = self._get_flatten_offset_for_well(wi)
        depth_true = depth_plot + offset

        return wi, ti, ax, depth_plot, depth_true

    def set_wells(self, wells):
        self.wells = wells
        self._flatten_depths = None
        self.draw_panel()

    def set_visible_tops(self, visible_tops):
        self.visible_tops = visible_tops
        self.draw_panel()

    def set_visible_logs(self, visible_logs):
        self.visible_logs = visible_logs
        self.draw_panel()

    def set_visible_tracks(self, visible_tracks):
        self.visible_tracks = visible_tracks
        self.draw_panel()
