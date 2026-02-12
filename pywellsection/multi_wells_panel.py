import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import (MultipleLocator, AutoMinorLocator)
from matplotlib.ticker import FormatStrFormatter
from matplotlib.lines import Line2D
import matplotlib.patches as patches
from matplotlib.image import BboxImage
from matplotlib.transforms import Bbox, TransformedBbox
from matplotlib.collections import LineCollection
from pywellsection.tools import _well_distance_m

import numpy as np

from numpy import ndarray
from numpy import dtype
from typing import Any

import logging
import pandas as pd
from pathlib import Path

logging.getLogger("ipykernel").setLevel("CRITICAL")
logging.getLogger("traitlets").setLevel("CRITICAL")
logging.getLogger("root").setLevel("CRITICAL")
logging.getLogger("parso").setLevel("CRITICAL")
logging.getLogger("parso.cache").setLevel("CRITICAL")
logging.getLogger("matplotlib.font_manager").setLevel("CRITICAL")
logging.getLogger("matplotlib.ticker").setLevel("CRITICAL")

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")



def scale_track_xaxis_fonts(fig, axes, wells, n_tracks, track_xaxes,
                            min_size=6, max_size=11):
    """
    Scale the font size of x-axis labels (and ticks) for each track according
    to the track's width in the figure.

    Parameters
    ----------
    fig : Figure
    axes : list[Axes]
        All axes including spacers.
    wells : list[dict]
    n_tracks : int
        Number of tracks per well.
    track_xaxes : dict[(wi, ti) -> list of XAxis]
        Mapping from (well_index, track_index) to the XAxis objects
        that belong to that track (twiny axes and/or base x-axes).
    min_size, max_size : float
        Min/max font size in points.
    """
    # Make sure positions are up to date
    fig.canvas.draw()

    # Measure widths per track
    widths = {}
    for wi in range(len(wells)):
        first_track_idx = wi * (n_tracks + 1)
        for ti in range(n_tracks):
            base_ax = axes[first_track_idx + ti]
            pos = base_ax.get_position()
            widths[(wi, ti)] = pos.width

    if not widths:
        return

    wmin = min(widths.values())
    wmax = max(widths.values())

    # Avoid division by zero if all tracks have same width
    def norm(w):
        if wmax == wmin:
            return 0.5
        return (w - wmin) / (wmax - wmin)

    # Scale font sizes and apply to all XAxis objects in each track
    for key, width in widths.items():
        wn = norm(width)
        size = min_size + wn * (max_size - min_size)

        for xaxis in track_xaxes.get(key, []):
            # Main axis label
            xaxis.label.set_fontsize(size)
            # Tick labels (if any)
            for ticklabel in xaxis.get_ticklabels():
                ticklabel.set_fontsize(size * 0.9)


def draw_multi_wells_panel_on_figure(fig,wells,tracks,suptitle=None,well_gap_factor=3.0, track_gap_factor=0.5,
                                     track_width = 1.0, corr_artists=None, highlight_top=None, flatten_depths=None,
                                     visible_wells=None, visible_tops = None, visible_logs = None,
                                     visible_discrete_logs = None, visible_bitmaps = None, visible_tracks = None,
                                     depth_window = None, stratigraphy = None, vertical_scale = 1.0,
                                     gap_proportional_to_distance = None, gap_distance_ref_m = 1000,
                                     gap_min_factor = 0.8, gap_max_factor = 8.0,
):
    """
    Draw multi-well, multi-track log panel with:
      - shared Y-scaling across wells
      - depth window based on:
          top_phys    = highest reference depth of all wells
          bottom_phys = deepest well bottom (reference_depth + total_depth)
      - when flattened, the displayed interval still contains *all* wells
        by transforming [top_phys, bottom_phys] into each well's plotting
        coordinates and taking the global min/max.
      - optional flattening (per-well offsets)
      - y-axis always labels TRUE depth (not relative depth)
    """

    #print(f" draw ! visible tops: {visible_tops}")

    fig.clf()

    if visible_wells is None:
        visible_wells = [w["name"] for w in wells]

    n_wells = len(visible_wells)

    if n_wells == 0:
        return n_wells

    selected_wells = [w for w in wells if (w.get("name") in visible_wells)]

    if visible_tracks is None:
        filtered_tracks = tracks[:]
    else:
        filtered_tracks = [t for t in tracks if t.get("name") in visible_tracks]


    if not filtered_tracks:
        n_tracks = 0
    else:
        n_tracks = len(filtered_tracks)

    if n_wells == 0:
        return None, None

    # ---- 1) Physical depth window (no offsets here) ----

    ref_depths = [w["reference_depth"] for w in selected_wells]
    bottoms = [w["reference_depth"] + w["total_depth"] for w in selected_wells]

    # top_phys = highest reference depth, bottom_phys = deepest bottom
    top_phys = max(ref_depths)
    bottom_phys = max(bottoms)

    for w in selected_wells:
        for log_name, log_def in w.get("logs", {}).items():
            depth = log_def["depth"]
            min_data_depth = np.nanmin(depth)
            max_data_depth = np.nanmax(depth)
            if max_data_depth < top_phys: top_phys = max_data_depth
            if min_data_depth > bottom_phys: bottom_phys = min_data_depth

    # ---- 2) Compute per-well offsets and global plotting range ----
    # offset_i is in TRUE depth coordinates (e.g. formation top depth)
    offsets = []
    for wi in range(n_wells):
        if flatten_depths is not None and wi < len(flatten_depths):
            offsets.append(flatten_depths[wi])
        else:
            offsets.append(0.0)

    global_top_plot = 99999.0
    global_bottom_plot = -99999.0
    gobal_mid_plot = 0.0

    if depth_window is not None:
        #print ("depth_window", depth_window)
        top_depth_window, bottom_depth_window = depth_window
        global_mid_plot = (top_depth_window + bottom_depth_window) / 2
        if top_depth_window < global_mid_plot < bottom_depth_window:
            global_top_plot = top_depth_window + offsets[0]
            global_bottom_plot = bottom_depth_window + offsets[0]
    else:
        print ("does this ever happen?")
        top_plot_candidates = []
        bottom_plot_candidates = []
        for off in offsets:
            top_plot_candidates.append(top_phys - off)
            bottom_plot_candidates.append(bottom_phys - off)

        # global plotting limits that include ALL wells after shifting
        global_top_plot = min(top_plot_candidates) + offsets[0]
        global_bottom_plot = max(bottom_plot_candidates) - offsets[0]
        global_mid_plot = (global_top_plot + global_bottom_plot) / 2


    if offsets[0] != 0.0:
        w = selected_wells[0]
        top_ref_depth = w["reference_depth"] - offsets[0]
        bottom_ref_depth = top_ref_depth + w["total_depth"]
        print (f"top_ref_depth={top_ref_depth:.2f} bottom_ref_depth={bottom_ref_depth:.2f}")
        global_top_plot = min(top_ref_depth, global_top_plot)
        global_bottom_plot = min(bottom_ref_depth, global_bottom_plot)


    print(f"global_top_plot={global_top_plot:.2f} global_bottom_plot={global_bottom_plot:.2f}")



    # ---- 3) Layout: tracks + spacer columns ----

    # --- compute per-gap spacer factors ---
    gap_factors = []
    if gap_proportional_to_distance and n_wells > 1:
        # distance (meters) between adjacent wells
        dists = []
        for i in range(n_wells - 1):
            d = _well_distance_m(wells[i], wells[i + 1])
            dists.append(d)

        # Convert distance to ratio relative to reference distance
        # factor = well_gap_factor * clamp( dist / ref )
        ref = float(gap_distance_ref_m) if gap_distance_ref_m else 1000.0
        ref = max(ref, 1e-6)

        for d in dists:
            if d is None or not np.isfinite(d) or d <= 0:
                # fallback to default constant gap
                f = well_gap_factor
            else:
                rel = d / ref
                rel = max(float(gap_min_factor), min(float(gap_max_factor), rel))
                f = well_gap_factor * rel
            gap_factors.append(f)
    else:
        gap_factors = [well_gap_factor] * max(0, n_wells - 1)

    # --- Layout: tracks + spacer columns ---
    total_cols = n_wells * (n_tracks+1) + (n_wells - 1)
    width_ratios = []
    col_is_spacer = []

    gap_i = 0
    for w in range(n_wells):
        width_ratios.append(track_width/2)
        col_is_spacer.append(False)
        for _ in range(n_tracks):
            width_ratios.append(track_width)
            col_is_spacer.append(False)
        if w != n_wells - 1:
            width_ratios.append(gap_factors[gap_i])
            col_is_spacer.append(True)
            gap_i += 1

    # total_cols = n_wells * (n_tracks+1) + (n_wells - 1)
    # width_ratios = []
    # col_is_spacer = []
    #
    # for w in range(n_wells):
    #     width_ratios.append(track_width/2)
    #     col_is_spacer.append(False)
    #     for _ in range(n_tracks):
    #         width_ratios.append(track_width)
    #         col_is_spacer.append(False)
    #     if w != n_wells - 1:
    #         width_ratios.append(well_gap_factor)
    #         col_is_spacer.append(True)

    gs = fig.add_gridspec(
        1,
        total_cols,
        width_ratios=width_ratios,
        wspace=0.05,
        left=0.1,
        right=0.90,
        #bottom=0.10,
        top= 0.8*vertical_scale,
        bottom=0.10/vertical_scale,
        #top=0.8/vertical_scale,
    )

    axes = [fig.add_subplot(gs[0, i]) for i in range(total_cols)]

    # Turn off spacer axes
    for ax, is_spacer in zip(axes, col_is_spacer):
        if is_spacer:
            ax.axis("off")
            ax.set_ylim(global_top_plot, global_bottom_plot)
            ax.invert_yaxis()

    add_well_distances_in_spacers(
        axes=axes,
        wells=wells,
        n_tracks=n_tracks+1,
        spacer_col_flags=col_is_spacer,
        fmt="Δ {d:.0f} m",
    )

    well_main_axes = []

    # ---- 4) Draw wells ----

    for wi, well in enumerate(selected_wells):

        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        offset = offsets[wi]  # TRUE depth offset for this well

        if offset != 0.0:
            depth_formatter = FuncFormatter(lambda y, pos, off=offset: f"{(y + off):.2f}")
        else:
            depth_formatter = None

        LOG.debug(f"depth_formatter={depth_formatter}")

        first_track_idx = wi * (n_tracks + 2)


        #print (f"wi={wi} first_track_idx={first_track_idx}")

        col_idx = wi * (n_tracks + 2)
        base_ax = axes[col_idx]
        base_ax.set_ylim(global_top_plot, global_bottom_plot)
        #print(f"base_ax.ylim={base_ax.get_ylim()}")
        base_ax.invert_yaxis()
        base_ax.grid(True, linestyle="--", alpha=0.3)
        base_ax.set_ylabel("Depth (m)", labelpad=8)
        base_ax.yaxis.set_minor_locator(AutoMinorLocator())
        base_ax.tick_params(axis="y", labelright = True, labelleft = False, direction="in", pad=-20, labelsize=6)
        base_ax.tick_params(which="minor", length = 3, labelleft = False, labelright = True, direction="in")
        base_ax.tick_params(which="major", length = 7)
        base_ax.xaxis.set_visible(False)
        #base_ax.set_title(well.get("name", f"Well {wi + 1}"), pad=70, fontsize=10)

        main_ax = axes[first_track_idx]

        well_main_axes.append(base_ax)

        # ---- Case: no tracks, just depth axis ----
        if not filtered_tracks:
            base_ax = main_ax
            base_ax.set_ylim(global_top_plot, global_bottom_plot)
            base_ax.invert_yaxis()
            base_ax.grid(True, linestyle="--", alpha=0.3)
            base_ax.set_ylabel("Depth (m)", labelpad=8)
            base_ax.tick_params(axis="y", labelleft=True, direction="in", pad=-10)
            base_ax.xaxis.set_visible(False)
            base_ax.set_title(well.get("name", f"Well {wi + 1}"), pad=70, fontsize=10)

            if depth_formatter is not None:
                base_ax.yaxis.set_major_formatter(depth_formatter)
            continue

        # ---- Normal multi-track case ----
        for ti, track in enumerate(filtered_tracks):
            col_idx = wi * (n_tracks + 2) + ti +1
            #print(f"col_idx={col_idx} wi={wi} ti={ti} n_tracks={n_tracks}")
            base_ax = axes[col_idx]
            #LOG.debug(f"track {ti+1}/{n_tracks} offset={offset:.0f} ref_depth={ref_depth:.0f} well_td={well_td:.0f}")
            # Shared plotting Y-range for all wells
            base_ax.set_ylim(global_top_plot, global_bottom_plot)
            base_ax.invert_yaxis()
            base_ax.grid(True, linestyle="--", alpha=0.3)


            base_ax.tick_params(axis="y", labelleft=False)
            base_ax.xaxis.set_visible(False)

            mid_track = (n_tracks) // 2
            if ti == mid_track:
                base_ax.set_title(well.get("name", f"Well {wi + 1}"), pad=5, y= 1.15,fontsize=10)

            Add_logs_to_track(base_ax, offset, track, visible_logs, well)

            if track.get("type") == "bitmap":
                _draw_bitmap_track(base_ax,well, track, offset, visible_bitmaps)

            disc_cfg = track.get("discrete")
            if disc_cfg is not None:
                _draw_discrete_track(base_ax, well, offset, disc_cfg, visible_discrete_logs)

            if track.get("type") == "lithofacies":
                _draw_lithofacies_track(base_ax,well,track, offset)


    add_depth_range_labels(fig, axes, selected_wells, n_tracks)

    if corr_artists is None:
        corr_artists = []

    add_tops_and_correlations(
        fig,
        axes,
        selected_wells,
        well_main_axes,
        n_tracks,
        correlations_only=False,
        corr_artists=corr_artists,
        highlight_top=highlight_top,
        flatten_depths=flatten_depths,
        visible_tops=visible_tops,
        visible_tracks = visible_tracks,
        stratigraphy = stratigraphy
    )

    if suptitle:
        fig.suptitle(suptitle, fontsize=14, y=0.97)

    print("now axes limits are:",axes[0].get_ylim())

    return axes, well_main_axes


def Add_logs_to_track(base_ax, offset, track, visible_logs, well):

    curve_cache = {}

    for j, log_cfg in enumerate(track.get("logs", [])):
        log_name = log_cfg["log"]

        if visible_logs is not None:
            if log_name not in visible_logs:
                continue

        log_def = well.get("logs", {}).get(log_name)
        if log_def is None:
            continue

        depth = log_def["depth"]
        data = log_def["data"]



        mask = [x > 0 for x in depth]




        # plotting depth: flattened if offset != 0
        depth_plot = [x - offset for x in depth]

        twin_ax = base_ax.twiny()
        label = log_cfg.get("label", log_name)
        # --- extract settings ---
        render = (log_cfg.get("render", "line") or "line").lower()
        color = log_cfg.get("color", "black")
        alpha = float(log_cfg.get("alpha", 1.0))
        linewidth = float(log_cfg.get("linewidth", 1.0))
        marker = log_cfg.get("marker", ".")
        markersize = float(log_cfg.get("markersize", 2.0))
        decimate = int(log_cfg.get("decimate", 1))
        clip = bool(log_cfg.get("clip", True))
        mask_nan = bool(log_cfg.get("mask_nan", True))
        zorder = int(log_cfg.get("zorder", 2))

        # --- prepare data ---
        x = np.asarray(data)
        y = np.asarray(depth_plot)

        if mask_nan:
            m = np.isfinite(x) & np.isfinite(y)
            x = x[m]
            y = y[m]

        if decimate > 1:
            x = x[::decimate]
            y = y[::decimate]

        if clip and "xlim" in log_cfg:
            xmin, xmax = log_cfg["xlim"]
            m = (x >= xmin) & (x <= xmax)
            x = x[m]
            y = y[m]

        mask = [t > 0 for t in x]


        # --- plot ---
        if render in ("points", "scatter", "markers"):
            twin_ax.plot(
                x, y,
                linestyle="None",
                marker=marker,
                markersize=markersize,
                color=color,
                alpha=alpha,
                zorder=zorder,
            )
        elif render == "color":
            x_min = np.nanmin(x)
            x_max = np.nanmax(x)
            x_range = x_max - x_min
            x_norm = (x-x_min)/(x_range)
            # ensure that we stay between 0 and 1
            x_norm = np.clip(x_norm, 0, 1)
            y_const = np.linspace(0.5, 0.5, len(depth_plot))

            bbox = twin_ax.get_window_extent()
            width = bbox.width

            colored_line(y_const, depth_plot, x_norm, twin_ax, linewidth=2*width, cmap="viridis")

        else:
            twin_ax.plot(
                x, y,
                linestyle=log_cfg.get("style", "-"),
                linewidth=linewidth,
                color=color,
                alpha=alpha,
                zorder=zorder,
            )


        # Only top spine visible
        for spine_name, spine in twin_ax.spines.items():
            spine.set_visible(spine_name == "top")

        # Stack multiple logs upwards
        offset_spine = 1.0 + j * 0.08
        twin_ax.spines["top"].set_position(("axes", offset_spine))

        xscale = log_cfg.get("xscale", "linear")
        twin_ax.set_xscale("log" if xscale == "log" else "linear")
        if "xlim" in log_cfg:
            twin_ax.set_xlim(log_cfg["xlim"])

        if log_cfg.get("direction", "normal") == "reverse":
            x_min, x_max = twin_ax.get_xlim()
            twin_ax.set_xlim(x_max, x_min)

        twin_ax.set_xlabel(label, color=color, labelpad=2, fontsize=5)
        twin_ax.xaxis.set_label_position("top")
        twin_ax.xaxis.tick_top()
        twin_ax.tick_params(
            axis="x",
            colors=color,
            top=True,
            bottom=False,
            labeltop=True,
            labelbottom=False,
            pad=2,
            labelsize=5,
        )

        twin_ax.grid(False)

        # cache for fills
        curve_cache[log_name] = {
            "depth_plot": depth_plot,
            "x": data,
            "twin_ax": twin_ax,
            "cfg": log_cfg,
        }

    _apply_track_fills(
        base_ax=base_ax,
        curve_cache=curve_cache,
        track=track
    )

def _draw_discrete_track(base_ax, well, offset, disc_cfg, visible_discrete_logs = None):
    """
    Render a discrete log track as colored intervals.

    Parameters
    ----------
    base_ax : matplotlib Axes
    well : dict
    offset : float
        Flattening offset to subtract from true depths.
    disc_cfg : dict
        Configuration with keys:
          - log (str)
          - label (str, optional)
          - color_map (dict, optional)
          - default_color (str, optional)
          - missing (any, optional; default -999)
    visible_discrete_logs : set[str] | None
        If provided, only draw when disc_cfg['log'] is in the set.
    """
    disc_name = disc_cfg["log"]


    if visible_discrete_logs is not None and disc_name not in visible_discrete_logs:
        return

    disc_label = disc_cfg.get("label", disc_name)
    color_map = disc_cfg.get("color_map", {})
    default_color = disc_cfg.get("default_color", "#dddddd")
    missing_code = disc_cfg.get("missing", -999)  # optional, default -999

    disc_logs = well.get("discrete_logs", {})
    disc_def = disc_logs.get(disc_name)
    if disc_def is None:
        return

    depths = np.array(disc_def.get("depth", []), dtype=float)
    values = np.array(disc_def.get("values", []), dtype=object)

    if depths.size == 0 or values.size == 0:
        return

    # sort by depth just in case
    order = np.argsort(depths)
    depths = depths[order]
    values = values[order]

    # flatten depths for plotting
    depths_plot = depths - offset  # kept for clarity; directly using top/bot below

    # we need a bottom bound for the last interval
    ref_depth = well["reference_depth"]
    well_td = ref_depth + well["total_depth"]
    last_bottom_phys = well_td
    last_bottom_plot = last_bottom_phys - offset

    base_ax.set_xlim(0, 1)
    base_ax.set_xticks([])
    base_ax.set_title(disc_label, fontsize = 5)

    # intervals between samples
    for i in range(len(depths) - 1):
        top_phys = depths[i]
        bot_phys = depths[i + 1]
        val = values[i]

        if val == missing_code:
            continue

        top_plot = top_phys - offset
        bot_plot = bot_phys - offset

        col = color_map.get(val, default_color)

        base_ax.axhspan(
            top_plot,
            bot_plot,
            xmin=0.0,
            xmax=1.0,
            facecolor=col,
            edgecolor="k",
            linewidth=0.3,
            alpha=0.9,
            zorder=0.8,
        )

    # last sample → extend to TD if not missing
    last_val = values[-1]
    if last_val != missing_code:
        top_phys = depths[-1]
        top_plot = top_phys - offset
        bot_plot = last_bottom_plot

        col = color_map.get(last_val, default_color)
        base_ax.axhspan(
            top_plot,
            bot_plot,
            xmin=0.0,
            xmax=1.0,
            facecolor=col,
            edgecolor="k",
            linewidth=0.3,
            alpha=0.9,
            zorder=0.8,
        )

def _draw_lithofacies_track(base_ax,well, track, offset = 0.0):

    import numpy as np
    from matplotlib.patches import Polygon

    spline_func=None


    intervals = well.get("facies_intervals", [])
    hatch_map = track.get("hatch_map", {})
    color_map = track.get("color_map", {})
    litho_hardness = track.get("litho_hardness", [])
    facies_cfg = track.get("config", {})
    hardness_scale = facies_cfg.get("hardness_scale", 1.0)
    spline_cfg = facies_cfg.get("spline", {})
    smooth = spline_cfg.get("smooth", 1)
    n_seg = spline_cfg.get("num_samples", 200)


    # ----------------------------
    # Defaults
    # ----------------------------
    if spline_func is None:
        spline_func = lambda s: smooth*(3.1*s**2.1 - 2.1*s**2.8) # cubic smoothstep

    def smoothstep(t, smooth):
        """Cubic Hermite spline between 0 and 1 with zero slope at both ends."""
        return smooth * (3.1 * t ** 2.1 - 2.1 * t ** 2.8)


    #3.1 * t ** 2.1 - 2.1 * t ** 2.8


    if hatch_map is None:
        hatch_map = {
            "Distributary Mouth Bar": "/",
            "Distributary Channel":   "\\",
            "Bay":                    ".",
            "Inner Marine Shelf":     "-",
            "Estuarine Bay–Lagoon":   "x",
        }

    if color_map is None:
        color_map = {
            "Distributary Mouth Bar": "red",
            "Distributary Channel":   "blue",
            "Bay":                    "orange",
            "Inner Marine Shelf":     "yellow",
            "Estuarine Bay–Lagoon":   "brown",
        }

    if litho_hardness is None:
        litho_hardness = {
            "SS":  3.0,
            "SSa": 2.0,
            "M":   1.0,
        }

    curve_depths = []
    curve_hardness = []

    # ----------------------------
    # Draw intervals
    # ----------------------------
    for iv in intervals:
        lt = iv["lithology"]
        trend =iv["trend"]
        env = iv.get("environment", "")
        top_true = iv["rel_top"]
        base_true = iv["rel_base"]

        # Apply flattening transform
        top_depth = top_true - offset
        base_depth = base_true - offset

        # Parse lithology + trend
        parts = [p.strip() for p in lt.split(",")]
        lith = parts[0]
        #trend = parts[1].lower() if len(parts) > 1 else None

        # Base hardness lookup
        h0 = litho_hardness.get(lith, 2.0)
        delta = 0.5

        # end-member hardness (raw)
        if trend == "fu":
            h_top_raw  = max(1.0, h0 - delta)
            h_base_raw = min(3.0, h0 + delta)
        elif trend == "cu":
            h_top_raw  = min(3.0, h0 + delta)
            h_base_raw = max(1.0, h0 - delta)
        else:
            h_top_raw = h_base_raw = h0

        # normalize 1–3 → 0–1
        h_top = h_top_raw / 3.0 * hardness_scale
        h_base = h_base_raw / 3.0 * hardness_scale

        # spline subdivision
        s = np.linspace(0, 1, n_seg)
        z_seg = top_depth + (base_depth - top_depth) * s

        if trend in ("fu", "cu"):
            #w = spline_func(s)
            w= smoothstep(s, smooth)
            h_seg = h_top + (h_base - h_top) * w
        else:
            h_seg = np.full_like(s, h_top)

        curve_depths.extend(z_seg)
        curve_hardness.extend(h_seg)

        # polygon under curve
        xs = [0.0] + list(h_seg) + [0.0]
        ys = [z_seg[0]] + list(z_seg) + [z_seg[-1]]

        poly = Polygon(
            list(zip(xs, ys)),
            closed=True,
            facecolor=color_map.get(env, "white"),
            edgecolor="black",
            hatch=hatch_map.get(env, ""),
            linewidth=0.6,
            alpha=0.9,
            zorder=0.8,
        )
        base_ax.add_patch(poly)

    # ----------------------------
    # Plot hardness curve
    # ----------------------------
    base_ax.plot(curve_hardness, curve_depths, color="black", linewidth=1.6)

    # ----------------------------
    # Axis formatting
    # ----------------------------
    base_ax.set_xlim(0, 1.0)
    base_ax.set_title("Lithofacies", fontsize=5)
    base_ax.xaxis.set_visible(False)
    base_ax.grid(False)

def _draw_bitmap_track(base_ax, well, track, offset = 0.0, visible_bitmaps = None):
    #global bitmap
    import numpy as np
    import matplotlib.image as mpimg

    track_cfg = track.get("bitmap", None)
    track_name = track.get("name", None)

    bitmaps = None
    # bmp = well.get("bitmap", None)
    #
    #
    # if bmp is not None:
    #     bitmaps=bmp.get("bitmaps", None)

    bitmaps = well.get("bitmaps", None)

    # Make it a full-width column (0..1)
    base_ax.set_xlim(0, 1)
    base_ax.set_xticks([])
    base_ax.set_title(track_name, fontsize=5)

    if bitmaps is not None and visible_bitmaps is not None:
        for bitmap in bitmaps:
            if bitmap is not None and bitmap in visible_bitmaps:
                bmp_cfg = bitmaps.get(bitmap, None)
                bmp_track = bmp_cfg.get("track", None)

                if bmp_cfg is not None and bmp_track == track_name:
                    # only draw if visible (optional) and the right track
                    bmp_top = bmp_cfg.get("top_depth", None)
                    bmp_base = bmp_cfg.get("base_depth", None)
                    if bmp_top is not None and bmp_base is not None:
                        # Load image
                        img = bmp_cfg.get("image", None)
                        if img is None:
                            path = bmp_cfg.get("path", None)
                            if path:
                                img = mpimg.imread(path)

                        if img is not None:
                            # Normalize order
                            top_phys = float(min(bmp_top, bmp_base))
                            base_phys = float(max(bmp_top, bmp_base))

                            # Apply flattening offset: plot depth = true depth - offset
                            top_plot = top_phys - offset
                            base_plot = base_phys - offset

                            # Optional flip (sometimes needed depending on how image is stored)
                            if track_cfg.get("flip_vertical", False):
                                img = np.flipud(img)

                            # IMPORTANT:
                            # - Use extent to map the image into depth coordinates.
                            # - With invert_yaxis(), you typically want origin="upper"
                            #   so row 0 aligns to the top of the interval.
                            base_ax.imshow(
                                img,
                                extent=(0.0, 1.0, top_plot, base_plot),
                                aspect="auto",
                                origin="upper",
                                alpha=float(track_cfg.get("alpha", 1.0)),
                                #cmap=track_cfg.get("cmap", None),
                                interpolation=track_cfg.get("interpolation", "nearest"),
                                zorder=int(track_cfg.get("zorder", 0)),
                            )
                else:
                    continue

def add_depth_range_labels(fig, axes, wells, n_tracks):
    """
    Add 'reference_depth–TD' labels below each well panel.
    """
    for wi, well in enumerate(wells):
        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        first_track_idx = wi * (n_tracks + 2)
        last_track_idx = first_track_idx + n_tracks
        left = axes[first_track_idx].get_position().x0
        right = axes[last_track_idx].get_position().x1
        mid_x = (left + right) / 2

        label = f"{ref_depth:.0f}–{well_td:.0f} m"
        fig.text(mid_x, 0.04, label, ha="center", va="center", fontsize=9)

def add_tops_and_correlations(fig,axes,wells,well_main_axes,n_tracks,correlations_only=False,corr_artists=None,
    highlight_top=None,flatten_depths=None,visible_tops=None,visible_tracks = None, stratigraphy = None):
    """
    Handle:
      - tops (lines, labels, within-well interval fill)
      - hatched interval just below deepest formation top
      - correlation lines between wells
      - colored/hatched fills in spacer columns between wells

    If correlations_only=True:
      - only correlation lines + spacer fills are (re)drawn
      - tops, within-well fills & labels are NOT redrawn

    corr_artists:
      - list that will collect Line2D and Polygon artists for correlations
        so they can be removed/redrawn when zooming.
    """
    if visible_tops is None:
        # do nothing if not visible_tops is provided
        return 0

    n_wells = len(wells)
    if corr_artists is None:
        corr_artists = []

    # Per well: store top depths and y-positions in figure coords
    well_top_depths = [dict() for _ in range(n_wells)]
    well_top_yfig = [dict() for _ in range(n_wells)]

    # Global color map for tops
    auto_top_color = {}
    top_color_palette = [
        "#e41a1c", "#377eb8", "#4daf4a", "#984ea3",
        "#ff7f00", "#a65628", "#f781bf", "#999999",
    ]

    # Level styles
    level_styles = {
        "formation": {"hatch": "//", "alpha": 0.18, "line_style": "-",  "line_width": 1.4},
        "member":    {"hatch": "",   "alpha": 0.10, "line_style": ":",  "line_width": 0.9},
        "sequence":  {"hatch": "xx", "alpha": 0.14, "line_style": "--", "line_width": 1.1},
    }
    default_level = "formation"

    def get_top_color(top_name):
        if top_name in auto_top_color:
            return auto_top_color[top_name]
        color = top_color_palette[len(auto_top_color) % len(top_color_palette)]
        auto_top_color[top_name] = color
        return color

    def get_level_style(level):
        return level_styles.get(level, level_styles[default_level])

    tops_by_name = {}


    ## ---- pass 1: per-well tops & (optionally) within-well shading ----
    for wi, (well, main_ax) in enumerate(zip(wells, well_main_axes)):
        tops = well.get("tops", {})
        if not tops:
            continue

        if flatten_depths is not None:
            if len(flatten_depths) != 0:
                flatten_depth = flatten_depths[wi]
            else:
                flatten_depth = 0.0
        else :
            flatten_depth = 0.0


        # Normalize tops
        top_items = []
        for name, val in tops.items():
            if visible_tops is not None and name not in visible_tops:
                continue # hide this top if not in visible_tops
            if isinstance(val, dict):
                depth = float(val["depth"])-flatten_depth
                color = val.get("color", get_top_color(name))
                level = val.get("level", default_level)
                role = val.get("role", "stratigraphy")
                hatch = val.get("hatch", "")
            else:
                depth = float(val)-flatten_depth
                color = get_top_color(name)
                level = default_level
                role = "stratigraphy"
            top_items.append((name, depth, color, level))

        # sort shallow -> deep
        top_items.sort(key=lambda t: t[1])
        top_names = [n for n, d, c, lvl in top_items]
        top_depths = [d for n, d, c, lvl in top_items]

        # meta
        top_meta = {}
        for name, depth, color, level in top_items:
            style = get_level_style(level)
            top_meta[name] = {"depth": depth, "color": color, "level": level, "style": style}
            well_top_depths[wi][name] = depth

        first_track_idx = wi * (n_tracks + 2)

        # Draw top lines and within-well fills only on full pass
        if not correlations_only:
            # horizontal top lines in ALL tracks of this well
            for ti in range(n_tracks+1):
                if ti == 0: continue
                col_idx = first_track_idx + ti
                base_ax = axes[col_idx]
                for name in top_names:

                    info = top_meta[name]

                    style = info["style"]

                    is_highlighted = (highlight_top is not None
                                      and highlight_top[0] == wi
                                      and highlight_top[1] == name)

                    linewidth = style["line_width"] * (1.0 if not is_highlighted else 1.8)
#                    print(stratigraphy)

                    if len(stratigraphy) == 0:
                        return len(stratigraphy)

#                    print(f"add_tops_and_correlations stratigraphy: {stratigraphy}")

                    if name not in stratigraphy.keys():
                        continue

                    if stratigraphy[name]['role'] == 'stratigraphy':
                        base_ax.axhline(
                            info["depth"],
                            xmin=0.0,
                            xmax=1.0,
                            color=stratigraphy[name]["color"],
                            linestyle=stratigraphy[name]["hatch"],
                            linewidth=linewidth,
                            zorder=1.2 if not is_highlighted else 1.8,
                        )
                    elif stratigraphy[name]['role'] == 'fault':
                        base_ax.axhline(
                            info["depth"],
                            xmin=0.0,
                            xmax=1.0,
                            color=stratigraphy[name]["color"],
                            linestyle=stratigraphy[name]["hatch"],
                            linewidth=linewidth,
                            zorder=1.2 if not is_highlighted else 1.8,
                        )


            # fill BETWEEN tops in this well using upper top's style
            if len(top_depths) >= 2:
                for i in range(len(top_depths) - 1):
                    name_upper = top_names[i]
                    d1 = top_depths[i]
                    d2 = top_depths[i + 1]
                    info = top_meta[name_upper]
                    color = info["color"]
                    #color = stratigraphy[name_upper]['color']
                    style = info["style"]
                    if name_upper not in stratigraphy.keys():
                        continue
                    if stratigraphy[name_upper]['role']=='stratigraphy':
                        for ti in range(n_tracks):
                            col_idx = first_track_idx + ti + 1
                            base_ax = axes[col_idx]
                            base_ax.axhspan(
                                d1,
                                d2,
                                facecolor=color,
                                alpha=style["alpha"],
                                hatch=style["hatch"],
                                edgecolor="none",
                                zorder=0.2,
                            )

            # hatched interval just below deepest formation top
            formation_depths = [
                depth for (name, depth, color, level) in top_items
                #if level == "formation"
            ]
            if formation_depths:
                deepest_formation = max(formation_depths)
                y0, y1 = main_ax.get_ylim()
                depth_max = max(y0, y1)
                depth_range = abs(y0 - y1) or 1.0
                thickness = depth_range * 0.001
                open_top = deepest_formation
                open_bottom = min(deepest_formation + thickness, depth_max)
                if open_bottom > open_top:

                    for ti in range(n_tracks):
                        col_idx = first_track_idx + ti +1
                        base_ax = axes[col_idx]
                        base_ax.axhspan(
                            open_top,
                            open_bottom,
                            facecolor="none",
                            hatch="///",
                            edgecolor="0.4",
                            linewidth=0.5,
                            zorder=0.3,
                        )

        # labels + figure-coordinate y positions
        x_min_main, x_max_main = main_ax.get_xlim()
        x_label_pos = x_min_main - 1.5* (x_max_main - x_min_main)
        #x_label_pos = xmin_main - 0.5 * (xmax_main - xmin_main)

        for name in top_names:
            info = top_meta[name]
            depth = info["depth"]
            color = info["color"]

            is_highlighted = (highlight_top is not None
                              and highlight_top[0] == wi
                              and highlight_top[1] == name)

            # thicker / brighter label for highlighted top
            label_kwargs = {
                "va": "center",
                "ha": "left",
                "fontsize": 7 if not is_highlighted else 9,
                "color": color,
                "bbox": dict(
                    facecolor="white" if not is_highlighted else "yellow",
                    alpha=0.6,
                    edgecolor="none" if not is_highlighted else "black",
                    pad=0.5,
                ),
                "zorder": 2 if not is_highlighted else 3,
            }

            main_ax.text(
                x_label_pos,
                depth,
                name,
                **label_kwargs,
            )

            # Optional: extra marker on highlighted top
            if is_highlighted:
                main_ax.plot(
                    [x_min_main + 0.01 * (x_max_main - x_min_main)],
                    [depth],
                    marker="o",
                    markersize=5,
                    markeredgecolor="black",
                    markerfacecolor="yellow",
                    zorder=3,
                )

            # compute y in figure coordinates (current zoom!)
            px, py = main_ax.transData.transform((x_min_main, depth))
            _, y_fig = fig.transFigure.inverted().transform((px, py))
            well_top_yfig[wi][name] = y_fig
            well_top_depths[wi][name] = depth

            if name not in tops_by_name:
                tops_by_name[name] = {
                    "color": color,
                    "level": info["level"],
                    "style": info["style"],
                    "entries": [],
                    "depth": [],
                }
            #tops_by_name[name]["entries"].append((wi, y_fig))
            tops_by_name[name]["entries"].append((wi, y_fig))
            tops_by_name[name]["depth"].append((wi, depth))

    # ---- pass 2: correlation lines in spacers ----
    for name, info in tops_by_name.items():
        color = info["color"]
        style = info["style"]
        entries = info["entries"]
        depth = info["depth"]
        if len(entries) < 2:
            continue

        entries_sorted = sorted(entries, key=lambda t: t[0])
        depth_sorted = sorted(depth, key=lambda t: t[0])

        # previous_depth = None
        # previous_color = None
        # previous_style = None

        for (w1, depth1), (w2, depth2) in zip(depth_sorted[:-1], depth_sorted[1:]):
            if w2 !=w1 +1:
                continue
            spacer_idx = w1 * (n_tracks + 2) + n_tracks + 1
            spacer_ax = axes[spacer_idx]
            spacer_ax.plot((0,1),(depth1,depth2), color=color, linewidth=style["line_width"], linestyle=style["line_style"], zorder=1.5)
            # if previous_depth is not None:
            #     spacer_ax.fill_between((0,1), (depth1,depth2), previous_depth,  color=previous_color,
            #                            alpha=previous_style["alpha"], hatch = previous_style["hatch"],zorder=1.4)
            # previous_depth = (depth1,depth2)
            # previous_color = color
            # previous_style = style


        # for (w1, y1), (w2, y2) in zip(entries_sorted[:-1], entries_sorted[1:]):
        #     if w2 != w1 + 1:
        #         continue  # only adjacent wells
        #
        #     spacer_idx = w1 * (n_tracks + 2) + n_tracks +1
        #     spacer_ax = axes[spacer_idx]
        #     left = spacer_ax.get_position().x0
        #     right = spacer_ax.get_position().x1
        #
        #     line = Line2D(
        #         [left, right],
        #         [y1, y2],
        #         transform=fig.transFigure,
        #         color=color,
        #         linewidth=style["line_width"],
        #         linestyle=style["line_style"],
        #         alpha=0.9,
        #     )
        #     fig.add_artist(line)
        #     corr_artists.append(line)
        #
        #     x_min_spacer, x_max_spacer = spacer_ax.get_xlim()




    # ---- pass 3: spacer fills between wells ----
    for w1 in range(n_wells - 1):
        w2 = w1 + 1

        shared_names = sorted(
            set(well_top_depths[w1].keys()) & set(well_top_depths[w2].keys()),
            key=lambda n: 0.5 * (well_top_depths[w1][n] + well_top_depths[w2][n]),
        )
        if len(shared_names) < 2:
            continue

        spacer_idx = w1 * (n_tracks + 2) + n_tracks + 1
        spacer_ax = axes[spacer_idx]
        x_left = spacer_ax.get_position().x0
        x_right = spacer_ax.get_position().x1

        for i in range(len(shared_names) - 1):
            name_upper = shared_names[i]
            name_lower = shared_names[i + 1]

            if name_upper not in tops_by_name:
                continue

            info = tops_by_name[name_upper]
            color = info["color"]
            style = info["style"]

            y1_left = well_top_yfig[w1][name_upper]
            y1_right = well_top_yfig[w2][name_upper]
            y2_left = well_top_yfig[w1][name_lower]
            y2_right = well_top_yfig[w2][name_lower]

            depth1_left = well_top_depths[w1][name_upper]
            depth1_right = well_top_depths[w2][name_upper]
            depth2_left = well_top_depths[w1][name_lower]
            depth2_right = well_top_depths[w2][name_lower]

            spacer_ax.fill_between([0, 1], [depth1_left, depth1_right], [depth2_left, depth2_right],
                                    color=color, alpha=style["alpha"], hatch=style["hatch"], zorder=0.1)

            # poly = patches.Polygon(
            #     [
            #         (x_left, y1_left),
            #         (x_right, y1_right),
            #         (x_right, y2_right),
            #         (x_left, y2_left),
            #     ],
            #     closed=True,
            #     transform=fig.transFigure,
            #     facecolor=color,
            #     alpha=style["alpha"],
            #     edgecolor="none",
            #     hatch=style["hatch"],
            #     zorder=0.2,
            # )
            # fig.add_artist(poly)
            # corr_artists.append(poly)

    return corr_artists

def _apply_track_fills(base_ax, curve_cache: dict, track: dict):
    """
    Draw fills for a track on base_ax using cached curves.

    Supported:
      - type: "to_value"      (curve vs constant)
      - type: "between_logs"  (curve vs curve)
      - type: "to_minmax"     (curve vs its track x-limits min/max)
    """
    fills = track.get("fills", []) or []
    if not fills:
        return





    for f in fills:
        ftype = (f.get("type") or "").strip().lower()
        alpha = float(f.get("alpha", 0.3))
        facecolor = f.get("facecolor", "#cccccc")
        facetype = f.get("facetype", "color")
        hatch = f.get("hatch", None)
        zorder = float(f.get("zorder", 0.6))


        ### type ... to_value

        if ftype == "to_value":
            log_name = f.get("log")
            color_type = f.get("color_type", "curve")
            if log_name not in curve_cache:
                continue

            logs = track.get("logs", []) or []
            for log in logs:
                track_log_name = log.get("log")
                if track_log_name == log_name:
                    track_xlim = log.get("xlim")
                    color_map = log.get("colorscale", None)
                    _, track_xmax = track_xlim or (0.0, 1.0)


            value = float(f.get("value", 0.0))
            where = (f.get("where") or "greater").lower()

            depth_plot = np.asarray(curve_cache[log_name]["depth_plot"], dtype=float)
            x = np.asarray(curve_cache[log_name]["x"], dtype=float)

            mask = (x < value) if where == "less" else (x > value)

            if facetype == "color":

                base_ax.fill_betweenx(
                    depth_plot, x, value,
                    where=mask, alpha=alpha,
                    facecolor=facecolor, hatch=hatch,
                    linewidth=0.0, zorder=zorder,
                )
            else:
                single_curve_log_color_fill(base_ax, depth_plot, mask, x, track_xlim, color_map)

                base_ax.fill_betweenx(
                    depth_plot, x, value,
                    where=mask, alpha=1,
                    facecolor="white",
                    linewidth=0.0, zorder=0.01,
                )

            log_cfg = curve_cache[log_name].get("cfg", None)
            xscale = log_cfg.get("xscale", "linear")
            base_ax.set_xscale("log" if xscale == "log" else "linear")
            if "xlim" in log_cfg:
                base_ax.set_xlim(log_cfg["xlim"])
            if log_cfg.get("direction", "normal") == "reverse":
                x_min, x_max = base_ax.get_xlim()
                base_ax.set_xlim(x_max, x_min)


        elif ftype == "to_minmax":
            log_name = f.get("log")
            if log_name not in curve_cache:
                continue

            side = (f.get("side") or "min").lower()  # "min" or "max"

            depth_plot = np.asarray(curve_cache[log_name]["depth_plot"], dtype=float)
            x = np.asarray(curve_cache[log_name]["x"], dtype=float)

            # Use the curve's displayed x-limits (track min/max) from the twiny axis
            twin_ax = curve_cache[log_name]["twin_ax"]
            x0, x1 = twin_ax.get_xlim()
            xmin, xmax = (min(x0, x1), max(x0, x1))
            bound = xmin if side == "min" else xmax

            logs = track.get("logs", []) or []
            for log in logs:
                track_log_name = log.get("log")
                if track_log_name == log_name:
                    track_xlim = log.get("xlim")
                    color_map = log.get("colorscale", None)
                    _, track_xmax = track_xlim or (0.0, 1.0)



            # Only fill inside the axis range
            if side == "min":
                mask = x > xmin
            else:
                mask = x < xmax

            # base_ax.fill_betweenx(
            #     depth_plot, x, bound,
            #     where=mask, alpha=alpha,
            #     facecolor=facecolor, hatch=hatch,
            #     linewidth=0.0, zorder=zorder,
            # )

            if facetype == "color":

                base_ax.fill_betweenx(
                    depth_plot, x, bound,
                    where=mask, alpha=alpha,
                    facecolor=facecolor, hatch=hatch,
                    linewidth=0.0, zorder=zorder,
                )
            else:
                single_curve_log_color_fill(base_ax, depth_plot, mask, x, track_xlim, color_map)

                base_ax.fill_betweenx(
                    depth_plot, x, bound,
                    where=mask, alpha=1,
                    facecolor="white",
                    linewidth=0.0, zorder=0.01,
                )


            log_cfg = curve_cache[log_name].get("cfg", None)
            xscale = log_cfg.get("xscale", "linear")
            base_ax.set_xscale("log" if xscale == "log" else "linear")
            if "xlim" in log_cfg:
                base_ax.set_xlim(log_cfg["xlim"])
            if log_cfg.get("direction", "normal") == "reverse":
                x_min, x_max = base_ax.get_xlim()
                base_ax.set_xlim(x_max, x_min)


        ### finaly the between logs case ....
        ###
        elif ftype == "between_logs":

            log_name = f.get("log_left")
            if log_name not in curve_cache:
                continue

            logs = track.get("logs", []) or []
            for log in logs:
                track_log_name = log.get("log")
                if track_log_name == log_name:
                    track_xlim = log.get("xlim")
                    color_map = log.get("colorscale", None)
                    _, track_xmax = track_xlim or (0.0, 1.0)

            twin_ax = curve_cache[log_name]["twin_ax"]
            x0, x1 = twin_ax.get_xlim()
            xmin, xmax = (min(x0, x1), max(x0, x1))


            left = f.get("log_left")
            right = f.get("log_right")
            if left not in curve_cache or right not in curve_cache:
                continue

            dl = np.asarray(curve_cache[left]["depth_plot"], dtype=float)
            xl = np.asarray(curve_cache[left]["x"], dtype=float)
            dr = np.asarray(curve_cache[right]["depth_plot"], dtype=float)
            xr = np.asarray(curve_cache[right]["x"], dtype=float)

            l_log_cfg = curve_cache[left].get("cfg", None)
            l_xlim = l_log_cfg.get("xlim", None) if l_log_cfg else None
            l_direction = l_log_cfg.get("direction", "normal") if l_log_cfg else "normal"
            l_xscale = l_log_cfg.get("xscale", "linear") if l_log_cfg else "linear"

            r_log_cfg = curve_cache[right].get("cfg", None)
            r_xlim = r_log_cfg.get("xlim", None) if r_log_cfg else None
            r_direction = r_log_cfg.get("direction", "normal") if r_log_cfg else "normal"
            r_xscale = r_log_cfg.get("xscale", "linear") if r_log_cfg else "linear"

            # we have to transform the right log curve to the left log value range and direction

            xr_min = r_xlim[0]
            xr_max = r_xlim[1]
            xl_min = l_xlim[0]
            xl_max = l_xlim[1]

            if l_direction == "reverse" or r_direction == "reverse":
                xr_min, xr_max = xr_max, xr_min

            xr = (xr - xr_min)/(xr_max - xr_min)
            xr = xr * (xl_max - xl_min) + xl_min



            # Resample right curve to left depth if needed
            if len(dl) != len(dr) or not np.allclose(dl, dr, atol=1e-6, rtol=0):
                ord_r = np.argsort(dr)
                drs = dr[ord_r]
                xrs = xr[ord_r]
                xr_i = np.interp(dl, drs, xrs)
            else:
                xr_i = xr

            where = (f.get("where") or "all").lower()
            if where == "left_greater":
                mask = xl > xr_i
            elif where == "right_greater":
                mask = xr_i > xl
            else:
                mask = None

            if facetype == "color":
                base_ax.fill_betweenx(
                    dl, xl, xr_i,
                    where=mask, alpha=alpha,
                    facecolor=facecolor, hatch=hatch,
                    linewidth=0.0, zorder=zorder,
                )

            else:
                single_curve_log_color_fill(base_ax, dl, mask, xl, track_xlim, color_map)

                base_ax.fill_betweenx(
                    dl, xl, xmin,
                    where=mask, alpha=1,
                    facecolor="white",
                    linewidth=0.0, zorder=zorder,
                )
                base_ax.fill_betweenx(
                    dl, xr_i,xmax,
                    where=mask, alpha=1,
                    facecolor="white",
                    linewidth=0.0, zorder=zorder,
                )




            base_ax.set_xscale("log" if l_xscale == "log" else "linear")
            if "xlim" in l_log_cfg:
                base_ax.set_xlim(l_log_cfg["xlim"])
            if l_log_cfg.get("direction", "normal") == "reverse":
                x_min, x_max = base_ax.get_xlim()
                base_ax.set_xlim(x_max, x_min)

def single_curve_log_color_fill(base_ax, depth_plot,mask, x, xlim, color_map=None):

    #x_min = np.nanmin(x[mask])
    #x_max = np.nanmax(x[mask])

    if color_map is None or color_map == "None":
        color_map = "viridis"

    x_min, x_max = xlim or (0.0, 1.0)


    x_range = x_max - x_min
    x_norm = (x - x_min) / (x_range)

    # ensure that we stay between 0 and 1

    x_norm = np.clip(x_norm, 0, 1)

    y_const = np.linspace(0.5, 0.5, len(depth_plot))
    x_max_const = np.linspace(x_max, x_max, len(depth_plot))

    bbox = base_ax.get_window_extent()
    width = bbox.width

    colored_line(y_const, depth_plot, x_norm, base_ax, linewidth=width * 2, cmap=color_map, zorder=0.001)

def colored_line_between_pts(x, y, c, ax, **lc_kwargs):
    """
    Plot a line with a color specified between (x, y) points by a third value.

    It does this by creating a collection of line segments between each pair of
    neighboring points. The color of each segment is determined by the
    made up of two straight lines each connecting the current (x, y) point to the
    midpoints of the lines connecting the current point with its two neighbors.
    This creates a smooth line with no gaps between the line segments.

    Parameters
    ----------
    x, y : array-like
        The horizontal and vertical coordinates of the data points.
    c : array-like
        The color values, which should have a size one less than that of x and y.
    ax : Axes
        Axis object on which to plot the colored line.
    **lc_kwargs
        Any additional arguments to pass to matplotlib.collections.LineCollection
        constructor. This should not include the array keyword argument because
        that is set to the color argument. If provided, it will be overridden.

    Returns
    -------
    matplotlib.collections.LineCollection
        The generated line collection representing the colored line.
    """
    if "array" in lc_kwargs:
        warnings.warn('The provided "array" keyword argument will be overridden')

    # Check color array size (LineCollection still works, but values are unused)
    if len(c) != len(x) - 1:
        LOG.debug(
            "The c argument should have a length one less than the length of x and y. "
            "If it has the same length, use the colored_line function instead."
        )

    # Create a set of line segments so that we can color them individually
    # This creates the points as an N x 1 x 2 array so that we can stack points
    # together easily to get the segments. The segments array for line collection
    # needs to be (numlines) x (points per line) x 2 (for x and y)
    points = np.array([y, x]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)
    lc = LineCollection(segments, **lc_kwargs)

    # Set the values used for colormapping
    lc.set_array(c)

    return ax.add_collection(lc)

def colored_line(x, y, c, ax, **lc_kwargs):
    """
    Plot a line with a color specified along the line by a third value.

    It does this by creating a collection of line segments. Each line segment is
    made up of two straight lines each connecting the current (x, y) point to the
    midpoints of the lines connecting the current point with its two neighbors.
    This creates a smooth line with no gaps between the line segments.

    Parameters
    ----------
    x, y : array-like
        The horizontal and vertical coordinates of the data points.
    c : array-like
        The color values, which should be the same size as x and y.
    ax : Axes
        Axis object on which to plot the colored line.
    **lc_kwargs
        Any additional arguments to pass to matplotlib.collections.LineCollection
        constructor. This should not include the array keyword argument because
        that is set to the color argument. If provided, it will be overridden.

    Returns
    -------
    matplotlib.collections.LineCollection
        The generated line collection representing the colored line.
    """
    if "array" in lc_kwargs:
        warnings.warn('The provided "array" keyword argument will be overridden')

    # Default the capstyle to butt so that the line segments smoothly line up
    default_kwargs = {"capstyle": "butt"}
    default_kwargs.update(lc_kwargs)

    # Compute the midpoints of the line segments. Include the first and last points
    # twice so we don't need any special syntax later to handle them.
    x = np.asarray(x)
    y = np.asarray(y)

    x = np.interp(x, np.linspace(0, 1, len(x)), np.linspace(0, 1, len(x)))



    x_midpts = np.hstack((x[0], 0.5 * (x[1:] + x[:-1]), x[-1]))
    y_midpts = np.hstack((y[0], 0.5 * (y[1:] + y[:-1]), y[-1]))

    # Determine the start, middle, and end coordinate pair of each line segment.
    # Use the reshape to add an extra dimension so each pair of points is in its
    # own list. Then concatenate them to create:
    # [
    #   [(x1_start, y1_start), (x1_mid, y1_mid), (x1_end, y1_end)],
    #   [(x2_start, y2_start), (x2_mid, y2_mid), (x2_end, y2_end)],
    #   ...
    # ]
    coord_start = np.column_stack((x_midpts[:-1], y_midpts[:-1]))[:, np.newaxis, :]
    coord_mid = np.column_stack((x, y))[:, np.newaxis, :]
    coord_end = np.column_stack((x_midpts[1:], y_midpts[1:]))[:, np.newaxis, :]
    segments = np.concatenate((coord_start, coord_mid, coord_end), axis=1)

    lc = LineCollection(segments, **default_kwargs)
    lc.set_array(c)  # set the colors of each segment

    return ax.add_collection(lc)

def add_well_distances_in_spacers(axes, wells, n_tracks, spacer_col_flags, fmt="Δ {d:.0f} m"):
    """
    Draw distance between adjacent wells into the spacer column between them.
    - axes: list of subplot axes including spacer columns
    - wells: in display order (left->right)
    - n_tracks: number of tracks per well used in this draw call
    - spacer_col_flags: list[bool] same length as axes (True if spacer column)
    """
    if len(wells) < 2:
        return

    # Collect spacer axes in left->right order
    spacer_axes = [ax for ax, is_spacer in zip(axes, spacer_col_flags) if is_spacer]
    # There should be exactly (n_wells-1) spacer axes if layout matches
    # but we won't hard-fail if it doesn't.
    for i in range(min(len(spacer_axes), len(wells) - 1)):
        w_left = wells[i]
        w_right = wells[i + 1]
        ax_sp = spacer_axes[i]

        d_m = _well_distance_m(w_left, w_right)

        if d_m is None:
            text = "Δ n/a"
        else:
            # switch to km if large
            if d_m >= 10000:
                text = f"Δ {d_m/1000:.2f} km"
            else:
                text = fmt.format(d=d_m)

        # Draw near top of spacer; zorder high so it sits on top of correlation fills
        ax_sp.text(
            0.5, 0.02, text,
            transform=ax_sp.transAxes,
            ha="center", va="bottom",
            fontsize=9,
            zorder=50,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75),
        )