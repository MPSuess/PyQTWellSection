from multiprocessing.forkserver import set_forkserver_preload

from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure

from string import Template
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QScrollArea, QDialog, QMenu, QVBoxLayout, QMessageBox,
    QDockWidget
)

from PySide6.QtCore import (Qt, QEvent, QSize)
from PySide6.QtCore import Signal as pyqtSignal
#from scipy.stats import false_discovery_control
from PySide6.QtGui import QPalette

from .multi_wells_panel import draw_multi_wells_panel_on_figure
from .multi_wells_panel import add_tops_and_correlations
from .sample_data import create_dummy_data
from .dialogs import EditFormationTopDialog
from .dialogs import AddFormationTopDialog
from .dialogs import AddLogToTrackDialog

import logging
from pathlib import Path

logging.getLogger("ipykernel").setLevel("CRITICAL")
logging.getLogger("traitlets").setLevel("CRITICAL")
logging.getLogger("root").setLevel("CRITICAL")
logging.getLogger("parso").setLevel("CRITICAL")
logging.getLogger("parso.cache").setLevel("CRITICAL")

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")

import numpy as np


#from mpl_interactions import panhandler

class  WellPanelWidget(QWidget):
    def __init__(self, wells, tracks, stratigraphy, panel_settings, well_panel_title = None, parent=None):
        super().__init__(parent)

        self.wells = wells
        self.well = None
        self.tracks = tracks
        self.all_tracks = tracks
        self.n_tracks = len(tracks)
        self.stratigraphy = stratigraphy
        self.logs = None
        self.depth_window = None
        self.type = "well_panel"

        self._scroll_cid = None

        self.panel_settings = panel_settings

        self.active_well_panel = False

        self.well_gap_factor = panel_settings["well_gap_factor"]
        self.track_gap_factor = panel_settings["track_gap_factor"]
        self.track_width = panel_settings["track_width"]

        self.gap_proportional_to_distance = panel_settings.get("gap_proportional_to_distance",False)
        self.gap_distance_mode = panel_settings.get("gap_distance_mode","auto")
        self.gap_distance_ref_m = panel_settings.get("gap_distance_ref_m", 1000)
        self.gap_min_factor = panel_settings.get("gap_min_factor",0.8)
        self.gap_max_factor = panel_settings.get("gap_max_factor",8.0)

        self.redraw_requested = False

        if not panel_settings.get("vertical_scale", 0):
            self.vertical_scale = 1.0
        else:
            self.vertical_scale = panel_settings["vertical_scale"]
#        self.well_panel_title = panel_settings["well_panel_title"]
#        self.window_name = panel_settings["window_name"]

        #self.well_panel_title = self.parent.objectName()
        self.well_panel_title = well_panel_title

        self.highlight_top = None
        self.visible_tops = None
        self.visible_logs = None
        self.visible_discrete_logs = None
        self.visible_bitmaps = None
        self.visible_tracks = tracks
        self.visible_wells = set()

        #self._temp_highlight_top = None

        self.fig = Figure(figsize=(12, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFixedSize(400, 800)
        self._px_per_track = 100
        self._px_per_well = 100
        self._px_per_well_gap = 10
        self._px_per_depth_track = 100
        self._min_canvas_width = 50

        self.enable_track_mouse_scrolling()
        self.depth_window = None

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setWidget(self.canvas)

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
        self.axes = None

        # temporary highlight of a selected top (optional)
        self._temp_highlight_artists = []

        # hatched moving line during 'pick on plot'
        self._pick_line_artists = []

        self._picked_depth = None
        self._picked_formation = None

        self._flatten_top_name = None
        self._flatten_depths = []
        self.current_depth_window = None  # (top_true, bottom_true) or None

        self.draw_well_panel()
        self.enable_top_picking()
        self.offset0 = 0

    def draw_well_panel(self):


        redraw_requested = self.panel_settings.get("redraw_requested",None)

        LOG.debug(f"redraw requested: {self.visible_wells}")

        if not redraw_requested:
            return

        if self.visible_wells is None:
            self.fig.clear()
            self.canvas.draw()
            return

        self.wells = self._apply_well_order_and_visibility()


        if len(self.visible_wells) == 0:
            self.fig.clear()
            self.canvas.draw()
            return

        if len(self.visible_wells)!= 0:

            top_true = bottom_true = None
            if hasattr(self, "axes") and self.axes:
                # Take the first main axis as reference (row 0, track 0)
                ref_ax = self.axes[0]
                y0, y1 = ref_ax.get_ylim()

                offset0 = 0.0
                if getattr(self, "_flatten_depths", None):
                    # first well offset
                    if len(self._flatten_depths) > 0:
                        offset0 = float(self._flatten_depths[0])


                top_true = min(y0, y1)
                bottom_true = max(y0, y1)
                self.offset0 = offset0

                if self.current_depth_window is None:
                    self.current_depth_window = (top_true, bottom_true)

            # 2) Redraw everything (this will clear fig and rebuild axe
            self.fig.clear()
            self._corr_artists = []
            flatten_depths = self._flatten_depths
            visible_tops = self.visible_tops
            visible_logs = self.visible_logs
            visible_discrete_logs = self.visible_discrete_logs
            visible_tracks = self.visible_tracks
            visible_bitmaps = self.visible_bitmaps

            n_wells = len(self.visible_wells)

            if visible_tracks is None:
                filtered_tracks = self.tracks[:]
            else:
                filtered_tracks = [t for t in self.tracks if t.get("name") in visible_tracks]

            if not filtered_tracks:
                n_tracks = 0
            else:
                n_tracks = len(filtered_tracks)

            self.update_canvas_size_from_layout()

            depth_window = self.get_current_depth_window()


            self.axes, self.well_main_axes = draw_multi_wells_panel_on_figure(
                self.fig,
                self.wells,
                self.tracks,
                well_gap_factor=self.well_gap_factor,
                track_gap_factor=self.track_gap_factor,
                track_width=self.track_width,
                suptitle=self.well_panel_title,
                corr_artists=self._corr_artists,
                highlight_top=self.highlight_top,
                flatten_depths=flatten_depths,
                visible_wells=self.visible_wells,
                visible_tops = visible_tops,
                visible_logs = visible_logs,
                visible_discrete_logs=visible_discrete_logs,
                visible_bitmaps=visible_bitmaps,
                visible_tracks = visible_tracks,
                depth_window=depth_window,
                stratigraphy=self.stratigraphy,
                vertical_scale=self.vertical_scale,
                gap_proportional_to_distance = self.gap_proportional_to_distance,
                gap_distance_ref_m = self.gap_distance_ref_m,
                gap_min_factor = self.gap_min_factor,
                gap_max_factor = self.gap_max_factor,
            )
            self._connect_ylim_sync()
            self._build_axis_index()

            self.canvas.draw()

    def update_well_panel(self,tracks, wells, stratigraphy, panel_settings):
        self.tracks = tracks
        self.n_tracks = len(tracks)
        self.wells = wells
        self.stratigraphy = stratigraphy
        self.panel_settings = panel_settings
        LOG.debug(f"stratigraphy: {stratigraphy}")
        self.draw_well_panel()

    def enable_top_picking(self):
        """
        Connect a mouse-click handler so the user can pick & edit formation tops.
        """
        if self._pick_cid is None:
            self._pick_cid = self.canvas.mpl_connect(
                "button_press_event", self._on_top_click
            )

        #--- Helpers

    def edit_top_dialog_accepted(self):
        """OK clicked on dialog: update top and redraw."""
        if self._active_top_dialog is None:
            LOG.debug ("no more top dialog?")
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
        self.draw_well_panel()

    def edit_top_dialog_rejected(self):
        """Cancel clicked: just clean up."""
        self._active_top_dialog = None
        self._active_pick_context = None
        self._clear_pick_line()
        # no change to self.top_depth

    # ---------- PICK MODE ----------
    def _arm_pick_for_dialog(self):
        """Hide dialog and start pick-on-plot mode."""

        #print("startin dialog pick mode")

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
            if len(self._flatten_depths) > 0:
                flatten_depth = self._flatten_depths[wi]
            else:
                flatten_depth = 0
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

        LOG.debug(f"min={min} max={max} depth={depth} flatten_depth={flatten_depth}")

        # if depth < min+flatten_depth:
        #     depth = min
        # if depth > max+flatten_depth:
        #     depth = max

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
            # 1) if toolbar is in zoom or pan mode, do NOT pick
        if hasattr(self, "toolbar") and getattr(self.toolbar, "mode", ""):
            # toolbar.mode is '' when inactive, 'zoom rect' or 'pan/zoom' when active
            return

        #print("top click")


        mapped = self._map_event_to_well_axes(event)
        if mapped is None:
            return
        wi, ti, ax, depth_plot, depth_true = mapped
        # ("received:",event.button, wi, ti, ax, depth_plot, depth_true)

        if self._in_dialog_pick_mode:
            return
        if event.button != 1:
            return

        #if ti-wi <= 0: return 0

        well = self.wells[wi]
        if "tops" not in well or not well["tops"]:
            tops = None

        else: # --- find nearest top in TRUE depth space ---
            tops = well["tops"]

        nearest_name = None
        nearest_depth = None
        min_dist = 99999

        if tops is not None:
            for name, val in tops.items():
                d = float(val["depth"] if isinstance(val, dict) else val)
                dist = abs(d - depth_true)
                if min_dist is None or dist < min_dist:
                    min_dist = dist
                    nearest_name = name
                    nearest_depth = d

        if nearest_name is not None:
            self._picked_depth = nearest_depth
            self._picked_formation = nearest_name

        # we now setup the menu
        menu = QMenu(self)

        act_edit = None
        act_delete = None
        act_flatten = None
        act_unflatten = None
        act_add = None
        act_move_well = None

                # distance threshold based on TRUE depth range
        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]
        depth_range = abs(well_td - ref_depth) or 1.0
        max_pick_distance = depth_range * 0.02
        if min_dist > max_pick_distance or tops is None:
            act_add = menu.addAction(f"Add top '{depth_true:.2f} m'...'")
            act_move_well = menu.addAction(f"Move well relative position ...")
        else:

            # highlight top (your existing helper should already respect flattening
            # via add_tops_and_correlations if you pass flatten_depths there)
            self._clear_temp_highlight()
            self._draw_temp_highlight(wi, nearest_name)
            #self.draw_well_panel()

            # --- context menu ---
            act_edit = menu.addAction(f"Edit top '{nearest_name}'…")
            act_delete = menu.addAction(f"Delete top '{nearest_name}'")
            act_flatten = menu.addAction(f"Flatten on '{nearest_name}'")
            act_unflatten = menu.addAction(f"Unflatten section'")

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

        if act_unflatten is not None and chosen == act_unflatten:
            self._reset_flatten()
            return

        if chosen == act_move_well:
            self._move_well_to(well_index = wi, depth = depth_true)
            return

    def _build_axis_index(self):
        """
        Map each base track axis to its (well_index, track_index).
        Spacer axes are ignored.
        """
        self.axis_index.clear()
        n_wells = len(self.visible_wells)
        #n_tracks = len(self.tracks)

        if self.visible_tracks is None:
            filtered_tracks = self.tracks[:]
        else:
            filtered_tracks = [t for t in self.tracks if t.get("name") in self.visible_tracks]

        if not filtered_tracks:
            n_tracks = 0
        else:
            n_tracks = len(filtered_tracks)


        # layout is [Depth, W0T0, W0T1, ..., spacer, Depth, W1T0, W1T1, ..., spacer, ...]
        for wi in range(n_wells):
            first_track_idx = wi * (n_tracks + 2)
            #print ("first track idx:", first_track_idx)
            for ti in range(n_tracks):
                ax_index = first_track_idx + ti +1
                if ax_index < n_wells * (n_tracks +2):
                    ax = self.axes[first_track_idx + ti+1]
                    #print ("added ax number:", first_track_idx + ti+1 )
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
            LOG.debug("dialog is None")

        if not self._in_dialog_pick_mode:
            return
        if self._active_pick_context is None:
            return
        if event.ydata is None:
            return

        wi_target = self._active_pick_context["wi"]
        print ("currently_picked:" ,wi_target)
        depth = float(event.ydata)
        if len(self._flatten_depths)>0:
        #if len(self._flatten_depths) > 0:
            flatten_depth = self._flatten_depths[wi_target]
        else:
            flatten_depth = 0

        LOG.debug(f"depth={depth} flatten_depth={flatten_depth}")

        depth = depth - flatten_depth

        LOG.debug (f"recalculated depth={depth}")

        formation_name = self._active_pick_context["formation_name"]

        if formation_name is not None:
            min,max = self._get_stratigraphic_bounds(formation_name)

            # if depth < min-flatten_depth:
            #     depth = min-flatten_depth
            # if depth > max-flatten_depth:
            #     depth = max-flatten_depth


        #LOG.debug("move", event.ydata, min, max, depth, flatten_depth)


        # draw a thin hatched band across ALL tracks of the selected well
        self._clear_pick_line()

        if self.visible_tracks is None: # in this case all tracks are visible
            self.visible_tracks = [t.get("name") for t in self.tracks]
        n_tracks = len(self.visible_tracks)
        first_track_idx = wi_target * (n_tracks + 2)



        for ti in range(n_tracks):
            base_ax = self.axes[first_track_idx + ti +1]

            # choose a small thickness relative to the depth range
            y0, y1 = base_ax.get_ylim()


            band = base_ax.axhline(depth+flatten_depth, color="tab:red", lw=1.2, ls="--", zorder=10)

            self._pick_line_artists.append(band)
            #if True: return
            #self.draw_well_panel()

        self.canvas.draw_idle()
        #self.draw_well_panel()

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

        if self._flatten_depths is not None:
            if len(self._flatten_depths) > 0:
                flatten_depth = self._flatten_depths[wi]
            else: flatten_depth = 0
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
            depth-flatten_depth,
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
        from PySide6.QtWidgets import QDialog

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

        if top_name is not None:
            min_bound,max_bound= self._get_stratigraphic_bounds(top_name)

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
        dlg.accepted.connect(self.edit_top_dialog_accepted)
        dlg.rejected.connect(self.edit_top_dialog_rejected)
        #
        LOG.debug ("Starting Dialog")
        dlg.show()

    def _delete_formation_top(self, well_index: int, top_name: str):
        """
        Delete a formation top from a given well, after user confirmation.
        Redraws the well_panel and clears any highlight.
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
        self.draw_well_panel()

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
        elif len(idx_l)==1:
            return min_bound, max_bound
        else:
            if idx==0:
                if type(tops[idx_l[idx]])==float:
                    return min_bound, tops[idx_l[idx+1]]
                else:
                    return min_bound,tops[idx_l[idx+1]]["depth"]
            elif idx==len(idx_l)-1:
                if type(tops[idx_l[idx]])==float:
                    return tops[idx_l[idx-1]], max_bound
                else:
                    return tops[idx_l[idx-1]]["depth"],max_bound
            else:
                if type(tops[idx_l[idx]])==float:
                    return tops[idx_l[idx-1]], tops[idx_l[idx+1]]
                else:
                    return tops[idx_l[idx-1]]["depth"],tops[idx_l[idx+1]]["depth"]

        return min_bound, max_bound

    def _add_formation_top_at_depth(self, well_index: int, depth: float):
        """
        At a picked depth in one well, find all stratigraphic units that can be
        inserted at that depth (without violating self.stratigraphy order),
        let the user choose one, and insert it.
        """

        wells = [w for w in self.wells if (w.get("name") in self.visible_wells)]

        well = wells[well_index]
        tops = well.setdefault("tops", {})

        # if len(self._flatten_depths) != 0:
        #     flatten_depth = self._flatten_depths[well_index]
        # else:
        #     flatten_depth = 0

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

        # Clear highlight and redraw well_panel (tops, fills, correlations, etc.)
        self._clear_temp_highlight()
        self.draw_well_panel()

    def _flatten_on_formation_top(self, top_name: str):
        """ Compute per-well flatten depth for a given formation top, then redraw well_panel.

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
        #self.current_depth_window = None
        self.draw_well_panel()

    def _set_offset_for_well(self, wi: int, depth: float):

        fd = getattr(self,"_flatten_depth", None)
        if not fd or wi >= len(fd):
            return
        setattr(self,"_flatten_depth", fd)

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

        #print("event axis:", ax)

        #print ("self.axis_index", self.axis_index)

        # If event is on a twinx axis, map it to its base axis by overlap
        if ax not in self.axis_index:
            ax_pos = ax.get_position()
            best_ax = None
            best_overlap = 0.0
            for base_ax in self.axis_index.keys():
                pos = base_ax.get_position()
                #print(base_ax)
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

        #print ("found wi, ti, depth_plot, depth_true: ", wi, ti, depth_plot, depth_true)

        return wi, ti, ax, depth_plot, depth_true

    def set_wells(self, wells):
        self.wells = wells
        #self.visible_wells = wells
        self._flatten_depths = None

    def set_visible_wells(self, visible_wells):
        self.visible_wells = visible_wells

    def get_visible_wells(self):
        return self.visible_wells

    def set_visible_tops(self, visible_tops):
        self.visible_tops = visible_tops

    def get_visible_tops(self):
        return self.visible_tops

    def set_visible_logs(self, visible_logs):
        self.visible_logs = visible_logs

    def set_visible_discrete_logs(self, visible_discrete_logs):
        self.visible_discrete_logs = visible_discrete_logs

    def get_visible_discrete_logs(self):
        return self.visible_discrete_logs

    def set_visible_bitmaps(self, visible_bitmaps):
        self.visible_bitmaps = visible_bitmaps

    def get_visible_bitmaps(self):
        return self.visible_bitmaps

    def get_visible_logs(self):
        return self.visible_logs

    def set_visible_tracks(self, visible_tracks):
        self.visible_tracks = visible_tracks
        self.draw_well_panel()

    def get_visible_tracks(self):
        return  self.visible_tracks

    def _reset_flatten(self):
        """
        Turn off flattening and redraw in true depth.
        """
        self._flatten_top_name = None
        self._flatten_depths = None
        #self.current_depth_window = None  # optional: reset zoom as well
        self.draw_well_panel()
        
    def set_panel_settings(self, settings):
        self.well_gap_factor = settings["well_gap_factor"]
        self.track_gap_factor = settings["track_gap_factor"]
        self.track_width = settings["track_width"]
        self.vertical_scale = settings["vertical_scale"]

        self.gap_proportional_to_distance = settings.get("gap_proportional_to_distance",False)
        self.gap_distance_mode = settings.get("gap_distance_mode","auto")
        self.gap_distance_ref_m = settings.get("gap_distance_ref_m", 1000)
        self.gap_min_factor = settings.get("gap_min_factor",0.8)
        self.gap_max_factor = settings.get("gap_max_factor",8.0)





    def set_vertical_scale(self, vertical_scale):
        self.vertical_scale = vertical_scale
        self.draw_well_panel()

    def set_draw_well_panel(self, state = True):
        self.panel_settings["redraw_requested"] = state
        return state

    def arm_bitmap_pick(self, dialog, well_name: str, bitmap_key: str, which: str):
        """
        Arms a one-click pick. On click in the target well area, computes TRUE depth and
        calls dialog.set_picked_depth(true_depth).
        """

        # store pick context
        self._bitmap_pick_ctx = {
            "dialog": dialog,
            "well_name": well_name,
            "bitmap_key": bitmap_key,
            "which": which,
        }

        # disconnect previous temporary handler if present
        if getattr(self, "_bitmap_pick_cid", None) is not None:
            try:
                self.canvas.mpl_disconnect(self._bitmap_pick_cid)
            except Exception:
                pass
            self._bitmap_pick_cid = None

        # connect click handler
        self._bitmap_pick_cid = self.canvas.mpl_connect("button_press_event", self._on_bitmap_pick_click)

    def _on_bitmap_pick_click(self, event):
        ctx = getattr(self, "_bitmap_pick_ctx", None)
        if ctx is None:
            return
        if event.button != 1 or event.inaxes is None or event.ydata is None:
            return

        # Determine which well was clicked, using your axis_index mapping:
        # axis_index[base_ax] -> (wi, ti)
        ax = event.inaxes
        if ax not in getattr(self, "axis_index", {}):
            # if it's a twiny axis or other, map to base axis by overlap (same approach you used for tops)
            ax_pos = ax.get_position()
            best_ax = None
            best_overlap = 0.0
            for base_ax in self.axis_index.keys():
                pos = base_ax.get_position()
                x0 = max(ax_pos.x0, pos.x0);
                x1 = min(ax_pos.x1, pos.x1)
                y0 = max(ax_pos.y0, pos.y0);
                y1 = min(ax_pos.y1, pos.y1)
                overlap = max(0.0, x1 - x0) * max(0.0, y1 - y0)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_ax = base_ax
            if best_ax is None or best_overlap == 0.0:
                return
            ax = best_ax

        wi, ti = self.axis_index[ax]
        well = self.wells[wi]
        if well.get("name") != ctx["well_name"]:
            # user clicked a different well: ignore
            return

        y_plot = float(event.ydata)

        # Convert plot depth → TRUE depth using your flatten offset for this well
        # You likely store flatten_depths or offsets in the widget; adapt as needed.
        offset = 0.0
        if getattr(self, "flatten_depths", None) is not None and wi < len(self.flatten_depths):
            offset = float(self.flatten_depths[wi] or 0.0)

        depth_true = y_plot + offset

        # send to dialog
        dlg = ctx["dialog"]
        if dlg is not None and hasattr(dlg, "set_picked_depth"):
            dlg.set_picked_depth(depth_true)

        # cleanup
        if getattr(self, "_bitmap_pick_cid", None) is not None:
            try:
                self.canvas.mpl_disconnect(self._bitmap_pick_cid)
            except Exception:
                pass
            self._bitmap_pick_cid = None
        self._bitmap_pick_ctx = None

    def get_current_depth_window(self):

        if self.current_depth_window is not None:
            return self.current_depth_window
        else:
            ref_depths = [w["reference_depth"] for w in self.wells]
            bottoms = [w["reference_depth"] + w["total_depth"] for w in self.wells]

            return ((min(ref_depths), max(bottoms)))

    def set_current_depth_window(self, min_depth, max_depth):
        self.current_depth_window = (min_depth, max_depth)
        return self.current_depth_window

    def zoom_in_out(self, event):
        #print (event.angleDelta().y() / 120)
        if event.angleDelta().y() > 0:
            self.well_main_axes[0].yaxis.pan(0.05)
        else:
            self.well_main_axes[0].yaxis.pan(0.05)

        #self.draw_well_panel()

    def change_canvas_size (self, event):
        self.fig_set_size(event.width(), event.height())

    def fig_set_size(self, width, height):
        #print (width, height)
        return

    def update_canvas_size_from_layout(self):
        """
        Height follows the widget/scroll viewport height.
        Width depends on number of wells and visible tracks.
        """
        #if 1:
        #    return

        dpi = float(self.fig.get_dpi() or 100.0)

        n_wells = len(self.visible_wells) if self.wells else 0

        # visible tracks filtering (if you use it)
        tracks = self.tracks or []
        visible_tracks = getattr(self, "visible_tracks", None)
        if visible_tracks is not None:
            tracks = [t for t in tracks if t.get("name") in visible_tracks]

        n_tracks = len(tracks) if tracks else 1  # ensure at least 1 track to compute width

        total_cols = n_wells * (n_tracks + 1) + (n_wells - 1)

        #print (total_cols, n_tracks, n_wells)

        # compute width in pixels: tracks + gaps
        if n_wells <= 0:
            width_px = self._min_canvas_width
        else:
            tracks_px = n_wells * n_tracks * self._px_per_track * self.track_width
            depth_track_px = n_wells * self._px_per_depth_track
            gaps_px = (n_wells - 1) * self._px_per_well_gap
            width_px = max(self._min_canvas_width, tracks_px + gaps_px + depth_track_px)

        # height in pixels: follow scroll viewport height (or this widget height)
        viewport_h = self.scroll_area.viewport().height() if hasattr(self, "scroll") else self.height()
        height_px = max(200, int(viewport_h))

        # set canvas widget size (controls scrollbars)
        self.canvas.setFixedSize(QSize(int(width_px), int(height_px)))

        # set matplotlib figure size in inches to match pixel size
        self.fig.set_size_inches(width_px / dpi, height_px / dpi, forward=True)


    def enable_track_mouse_scrolling(self):
        """Enable mouse-wheel scrolling inside tracks (pan/zoom depth window)."""
        if getattr(self, "_scroll_cid", None) is not None:
            return
        self._scroll_cid = self.canvas.mpl_connect("scroll_event", self.on_scroll)

    def draw_idle(self):
        self.canvas.draw_idle()

    def on_scroll(self, event):

        #print("start on_scroll")

        key = (event.modifiers or "")
        ctrl = ("control" in key) or ("ctrl" in key)

        #print("ctrl, event_modifier", ctrl,  event.modifiers)



        # Do not interfere with toolbar pan/zoom modes
        tb = getattr(self, "toolbar", None)  # if you attached NavigationToolbar2QT to self.toolbar
        if event.inaxes is None or event.ydata is None:
            if tb is not None and getattr(tb, "mode", ""):
                # mode is e.g. "pan/zoom" or "zoom rect"
                return

            # Do not interfere with your picking modes
            if getattr(self, "_in_dialog_pick_mode", False):
                return
            if getattr(self, "_bitmap_pick_ctx", None) is not None:
                return
            return


        ax = event.inaxes
        if ax is None:
            return
        # Fake a mouse button for drag_pan


        button = 1 # left mouse button
        if ctrl:
            button = 3  # left mouse button scroll

        # Scroll direction controls pan direction
        dx = 0
        dy = 20 if event.step > 0 else -20

        # Initialize pan
        ax.start_pan(event.x, event.y, button)

        # Apply pan movement
        ax.drag_pan(button, key, event.x + dx, event.y + dy)

        # Finish pan
        ax.end_pan()

        self.draw_idle()

    def _apply_well_order_and_visibility(self):
        wells = self.wells or []

        # # visible filter
        # vw = getattr(self, "visible_wells", None)
        # if vw is not None:
        #     vw_set = set(vw)
        #     wells = [w for w in wells if w.get("name") in vw_set]

        # ordering
        order = getattr(self, "well_order", None)
        if isinstance(order, list) and order:
            idx = {nm: i for i, nm in enumerate(order)}
            wells.sort(key=lambda w: idx.get(w.get("name", ""), 10 ** 9))

        return wells

    def add_visible_well_by_name(self, well_name: str, *, redraw: bool = True) -> bool:
        """
        Add a well (by name) to this panel's visible_wells list.
        Keeps order stable (appends if not already present).

        Returns True if the well was added (or already present), False if name not found in panel.wells.
        """
        well_name = (well_name or "").strip()
        if not well_name:
            return False

        wells = getattr(self, "wells", []) or []
        all_names = [w.get("name", "") for w in wells if w.get("name")]

        if well_name not in all_names:
            return False

        # Ensure visible_wells list exists (None means "all wells visible")
        vw = getattr(self, "visible_wells", None)
        if vw is None:
            vw = list(all_names)  # start from "all"
            self.visible_wells = vw

        if vw == set():
            vw = list()

        if well_name not in vw:
            vw.append(well_name)

        # Keep optional explicit ordering consistent
        if hasattr(self, "well_order"):
            wo = getattr(self, "well_order", None)
            if wo is None:
                self.well_order = list(vw)
            elif well_name not in wo:
                wo.append(well_name)

        if redraw:
            self.draw_well_panel()

        return True

    def remove_visible_well_by_name(self, well_name: str, *, redraw: bool = True) -> bool:
        """
        Remove a well (by name) from this panel's visible_wells list.

        Returns
        -------
        bool
            True if removal happened,
            False if well not found or not currently visible.
        """
        well_name = (well_name or "").strip()
        if not well_name:
            return False

        wells = getattr(self, "wells", []) or []
        all_names = [w.get("name", "") for w in wells if w.get("name")]

        if well_name not in all_names:
            return False

        vw = getattr(self, "visible_wells", None)

        # If visible_wells is None, it means "all wells visible"
        if vw is None:
            # Initialize explicit list excluding the removed well
            self.visible_wells = [n for n in all_names if n != well_name]
        else:
            if well_name not in vw:
                return False
            self.visible_wells = [n for n in vw if n != well_name]

        # Keep well_order consistent
        if hasattr(self, "well_order"):
            wo = getattr(self, "well_order", None)
            if isinstance(wo, list):
                self.well_order = [n for n in wo if n != well_name]

        if redraw:
            self.draw_well_panel()

        return True

    def add_visible_top_by_name(self, top_name: str, *, redraw: bool = True) -> bool:
        """
        Add a stratigraphic unit/top (by name) to this panel's visible_tops filter.

        Semantics:
          - visible_tops is None  => all tops are visible (no filtering)
          - visible_tops is list  => only listed tops are visible
        This function ensures top_name becomes visible under both semantics.

        Returns True if top_name is valid and ends up visible, False if top_name unknown.
        """
        top_name = (top_name or "").strip()
        if not top_name:
            return False

        # determine known tops from project stratigraphy if available
        known = set()
        strat = getattr(self, "stratigraphy", None)
        if isinstance(strat, dict):
            known.update(strat.keys())

        # also accept tops that exist in any well (helps when stratigraphy dict is incomplete)
        for w in (getattr(self, "wells", None) or []):
            tops = w.get("tops") or {}
            known.update(tops.keys())

        if known and top_name not in known:
            return False

        vt = getattr(self, "visible_tops", None)

        if vt is None:
            # all visible already
            if redraw:
                self.draw_well_panel()
            return True

        if vt == set():
            vt = list()

        if top_name not in vt:
            vt.append(top_name)

        if redraw:
            self.draw_well_panel()

        return True

    def remove_visible_top_by_name(self, top_name: str, *, redraw: bool = True) -> bool:
        """
        Remove a stratigraphic unit/top (by name) from this panel's visible_tops filter.

        Semantics:
          - visible_tops is None  => all tops visible; removing one requires turning
                                    the filter into an explicit list of known tops minus this one.
          - visible_tops is list  => remove from the list.

        Returns True if removal happened, False otherwise.
        """
        top_name = (top_name or "").strip()
        if not top_name:
            return False

        # gather known tops (same as in add)
        known = set()
        strat = getattr(self, "stratigraphy", None)
        if isinstance(strat, dict):
            known.update(strat.keys())
        for w in (getattr(self, "wells", None) or []):
            tops = w.get("tops") or {}
            known.update(tops.keys())

        vt = getattr(self, "visible_tops", None)

        if vt is None:
            # all visible -> convert to explicit list excluding top_name
            if known and top_name not in known:
                return False
            self.visible_tops = sorted([nm for nm in known if nm != top_name])
            changed = True
        else:
            if top_name not in vt:
                return False
            self.visible_tops = [nm for nm in vt if nm != top_name]
            changed = True

        if changed and redraw:
            self.draw_well_panel()

        return True

    def add_visible_track_by_name(self, track_name: str, *, redraw: bool = True) -> bool:
        """
        Add a track (by name) to this panel's visible_tracks filter.

        Returns
        -------
        bool
            True if track is valid and visible afterwards,
            False if track name does not exist.
        """
        track_name = (track_name or "").strip()
        if not track_name:
            return False

        tracks = getattr(self, "tracks", []) or []
        all_names = [t.get("name", "") for t in tracks if t.get("name")]

        if track_name not in all_names:
            return False

        vt = getattr(self, "visible_tracks", None)

        if vt is None:
            # already all visible
            if redraw:
                self.draw_well_panel()
            return True

        if track_name not in vt:
            vt.append(track_name)

        if redraw:
            self.draw_well_panel()

        return True

    def remove_visible_track_by_name(self, track_name: str, *, redraw: bool = True) -> bool:
        """
        Remove a track (by name) from this panel's visible_tracks filter.

        Returns
        -------
        bool
            True if removal happened,
            False if track not found or already hidden.
        """
        track_name = (track_name or "").strip()
        if not track_name:
            return False

        tracks = getattr(self, "tracks", []) or []
        all_names = [t.get("name", "") for t in tracks if t.get("name")]

        if track_name not in all_names:
            return False

        vt = getattr(self, "visible_tracks", None)

        if vt is None:
            # convert from "all visible" to explicit list excluding this track
            self.visible_tracks = [n for n in all_names if n != track_name]
        else:
            if track_name not in vt:
                return False
            self.visible_tracks = [n for n in vt if n != track_name]

        if redraw:
            self.draw_well_panel()

        return True

    def add_visible_log_by_name(self, log_name: str, *, redraw: bool = True) -> bool:
        """
        Add a log (by name) to this panel's visible_logs filter.

        Returns
        -------
        bool
            True if log is valid and visible afterwards,
            False if log name does not exist.
        """
        log_name = (log_name or "").strip()
        if not log_name:
            return False

        # Collect all known log names from panel wells
        all_logs = set()
        for w in (getattr(self, "wells", None) or []):
            logs = w.get("logs") or {}
            all_logs.update(logs.keys())

        if log_name not in all_logs:
            return False

        vl = getattr(self, "visible_logs", None)

        if vl is None:
            # already all visible
            if redraw:
                self.draw_well_panel()
            return True

        if log_name not in vl:
            vl.append(log_name)

        if redraw:
            self.draw_well_panel()

        return True

    def remove_visible_log_by_name(self, log_name: str, *, redraw: bool = True) -> bool:
        """
        Remove a log (by name) from this panel's visible_logs filter.

        Returns
        -------
        bool
            True if removal happened,
            False if log not found or already hidden.
        """
        log_name = (log_name or "").strip()
        if not log_name:
            return False

        # Collect known logs
        all_logs = set()
        for w in (getattr(self, "wells", None) or []):
            logs = w.get("logs") or {}
            all_logs.update(logs.keys())

        if log_name not in all_logs:
            return False

        vl = getattr(self, "visible_logs", None)

        if vl is None:
            # convert from "all visible" to explicit list excluding this log
            self.visible_logs = sorted(n for n in all_logs if n != log_name)
        else:
            if log_name not in vl:
                return False
            self.visible_logs = [n for n in vl if n != log_name]

        if redraw:
            self.draw_well_panel()

        return True

    def add_visible_discrete_log_by_name(self, log_name: str, *, redraw: bool = True) -> bool:
        """
        Add a discrete log (by name) to this panel's visible_discrete_logs filter.

        Returns
        -------
        bool
            True if log exists and is visible afterwards,
            False if log does not exist.
        """
        log_name = (log_name or "").strip()
        if not log_name:
            return False

        # Collect all known discrete logs from panel wells
        all_logs = set()
        for w in (getattr(self, "wells", None) or []):
            dlogs = w.get("discrete_logs") or {}
            all_logs.update(dlogs.keys())

        if log_name not in all_logs:
            return False

        vdl = getattr(self, "visible_discrete_logs", None)

        if vdl is None:
            # already all visible
            if redraw:
                self.draw_well_panel()
            return True

        if log_name not in vdl:
            vdl.append(log_name)

        if redraw:
            self.draw_well_panel()

        return True

    def remove_visible_discrete_log_by_name(self, log_name: str, *, redraw: bool = True) -> bool:
        """
        Remove a discrete log (by name) from this panel's visible_discrete_logs filter.

        Returns
        -------
        bool
            True if removal happened,
            False if log not found or already hidden.
        """
        log_name = (log_name or "").strip()
        if not log_name:
            return False

        # Collect known discrete logs
        all_logs = set()
        for w in (getattr(self, "wells", None) or []):
            dlogs = w.get("discrete_logs") or {}
            all_logs.update(dlogs.keys())

        if log_name not in all_logs:
            return False

        vdl = getattr(self, "visible_discrete_logs", None)

        if vdl is None:
            # convert from "all visible" to explicit list excluding this log
            self.visible_discrete_logs = sorted(n for n in all_logs if n != log_name)
        else:
            if log_name not in vdl:
                return False
            self.visible_discrete_logs = [n for n in vdl if n != log_name]

        if redraw:
            self.draw_well_panel()

        return True

    def add_visible_bitmap_by_name(self, bitmap_name: str, *, redraw: bool = True) -> bool:
        """
        Add a bitmap (by name) to this panel's visible_bitmaps_logs filter.

        Returns
        -------
        bool
            True if bitmap exists and is visible afterwards,
            False if bitmap does not exist.
        """
        bitmap_name = (bitmap_name or "").strip()
        if not bitmap_name:
            return False

        # Collect all known bitmaps across wells
        all_bitmaps = set()
        for w in (getattr(self, "wells", None) or []):
            bitmaps = w.get("bitmaps") or {}
            all_bitmaps.update(bitmaps.keys())

        if bitmap_name not in all_bitmaps:
            return False

        vbl = getattr(self, "visible_bitmaps", None)

        if vbl is None:
            # already all visible
            if redraw:
                self.draw_well_panel()
            return True

        if bitmap_name not in vbl:
            vbl.append(bitmap_name)

        if redraw:
            self.draw_well_panel()

        return True

    def remove_visible_bitmap_by_name(self, bitmap_name: str, *, redraw: bool = True) -> bool:
        """
        Remove a bitmap (by name) from this panel's visible_bitmaps_logs filter.

        Returns
        -------
        bool
            True if removal happened,
            False if bitmap not found or already hidden.
        """
        bitmap_name = (bitmap_name or "").strip()
        if not bitmap_name:
            return False

        # Collect known bitmaps
        all_bitmaps = set()
        for w in (getattr(self, "wells", None) or []):
            bitmaps = w.get("bitmaps") or {}
            all_bitmaps.update(bitmaps.keys())

        if bitmap_name not in all_bitmaps:
            return False

        vbl = getattr(self, "visible_bitmaps", None)

        if vbl is None:
            # convert from "all visible" to explicit list excluding this bitmap
            self.visible_bitmaps = sorted(n for n in all_bitmaps if n != bitmap_name)
        else:
            if bitmap_name not in vbl:
                return False
            self.visible_bitmaps = [n for n in vbl if n != bitmap_name]

        if redraw:
            self.draw_well_panel()

        return True





class WellPanelDock(QDockWidget):
    activated = pyqtSignal(object)  # emits self when activated

    _counter = 1

    def __init__(self, parent, wells, tracks, stratigraphy, panel_settings):
        title = f"Well_Section_{WellPanelDock._counter}"
        super().__init__(title, parent)
        WellPanelDock._counter += 1


        self.title = title
        self.type = "WellSection"
        self.visible = True
        self.tabified = False
        self.setObjectName(title)
        self.setWindowTitle(title.replace("_", " "))

        self.setAllowedAreas(
            Qt.LeftDockWidgetArea |
            Qt.RightDockWidgetArea |
            Qt.TopDockWidgetArea |
            Qt.BottomDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetClosable |
            QDockWidget.DockWidgetFloatable
        )


 #       self.tabifiedDockWidgetActivated.connect(self.window_activate)

        self.well_panel = WellPanelWidget(wells, tracks, stratigraphy, panel_settings, title)
        self.setWidget(self.well_panel)
        self.well_panel.draw_well_panel()

        self.title_background_color = None
        self.window_activated()

        self.background_template = Template('QDockWidget::title{background-color: $title_bgc; '
                                            'padding: 3px; spacing: 4px; border: none;}')



        # Detect “activation” by focus/click inside well_panel
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self:
            if event.type() in (QEvent.MouseButtonPress, QEvent.FocusIn):
                self.activated.emit(self)
                #self.window_activated()
            if event.type() == QEvent.Resize:
                #print("resizing")
                self.well_panel.update_canvas_size_from_layout()
            # if event.type() == QEvent.WindowActivate:
            #     self.window_activated()
        return super().eventFilter(obj, event)

    def draw_well_panel(self):
        self.well_panel.draw_well_panel()

    def window_activated(self):
        palette = self.palette()
        self.title_background_color = palette.color(QPalette.ColorGroup.Active, QPalette.Window)
        self.setStyleSheet('QDockWidget::title{background-color: grey ;  padding: 3px; spacing: 4px; border: none;}')

    def window_deactivated(self):
        self.setStyleSheet(self.background_template.substitute(title_bgc=self.title_background_color))

    def window_activate(self,dockwidget):
        if isinstance(dockwidget,bool):
            return
        else:
            name=dockwidget.objectName()
            children=dockwidget.children()
            dockwidget.window_activated()
            for child in children:
                LOG.debug(f'We try to activate {child}')
        return

    def set_visible(self, state):
        if state:
            self.visible = True
        else:
            self.visible = False

    def get_visible(self):
        return self.visible

    def get_title(self):
        return self.title

    def istabified(self):
        if self.tabified:
            return True
        else:
            return False

    def set_title(self, title):
        self.title = title
        self.setWindowTitle(title)
        self.well_panel.well_panel_title = title
        self.setObjectName(title)

    def get_type(self):
        return self.type

    def get_panel(self):
        return self.well_panel





