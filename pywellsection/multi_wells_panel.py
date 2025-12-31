import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.ticker import FormatStrFormatter
from matplotlib.lines import Line2D
import matplotlib.patches as patches

import numpy as np

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


def draw_multi_wells_panel_on_figure(
    fig,
    wells,
    tracks,
    suptitle=None,
    well_gap_factor=3.0,
    track_gap_factor=0.5,
    track_width = 1.0,
    corr_artists=None,
    highlight_top=None,
    flatten_depths=None,
    visible_wells=None,
    visible_tops = None,
    visible_logs = None,
    visible_discrete_logs = None,
    visible_tracks = None,
    depth_window = None,
    stratigraphy = None,
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

    print(f" draw ! visible tops: {visible_tops}")

    fig.clf()



    n_wells = len(visible_wells)

    if n_wells == 0:
        return n_wells

    selected_wells = [w for w in wells if (w.get("name") in visible_wells)]

    if visible_tracks is None:
        filtered_tracks = tracks[:]
    else:
        filtered_tracks = [t for t in tracks if t.get("name") in visible_tracks]


    if not filtered_tracks:
        n_tracks = 1
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

    # ---- 2) Compute per-well offsets and global plotting range ----
    # offset_i is in TRUE depth coordinates (e.g. formation top depth)
    offsets = []
    for wi in range(n_wells):
        if flatten_depths is not None and wi < len(flatten_depths):
            offsets.append(flatten_depths[wi])
        else:
            offsets.append(0.0)

    top_plot_candidates = []
    bottom_plot_candidates = []
    for off in offsets:
        top_plot_candidates.append(top_phys - off)
        bottom_plot_candidates.append(bottom_phys - off)

    # global plotting limits that include ALL wells after shifting
    global_top_plot = min(top_plot_candidates) + offsets[0]
    global_bottom_plot = max(bottom_plot_candidates) - offsets[0]
    global_mid_plot = (global_top_plot + global_bottom_plot) / 2


    if depth_window is not None:
        print ("depth_window", depth_window)
        top_depth_window, bottom_depth_window = depth_window
        if top_depth_window < global_mid_plot < bottom_depth_window:
            global_top_plot = top_depth_window
            global_bottom_plot = bottom_depth_window



    # ---- 3) Layout: tracks + spacer columns ----
    total_cols = n_wells * n_tracks + (n_wells - 1)
    width_ratios = []
    col_is_spacer = []

    for w in range(n_wells):
        for _ in range(n_tracks):
            width_ratios.append(track_width)
            col_is_spacer.append(False)
        if w != n_wells - 1:
            width_ratios.append(well_gap_factor)
            col_is_spacer.append(True)

    gs = fig.add_gridspec(
        1,
        total_cols,
        width_ratios=width_ratios,
        wspace=0.05,
        left=0.1,
        right=0.90,
        bottom=0.10,
        top=0.8,
    )

    axes = [fig.add_subplot(gs[0, i]) for i in range(total_cols)]

    # Turn off spacer axes
    for ax, is_spacer in zip(axes, col_is_spacer):
        if is_spacer:
            ax.axis("off")

    well_main_axes = []

    # ---- 4) Draw wells ----



    for wi, well in enumerate(selected_wells):


        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        offset = offsets[wi]  # TRUE depth offset for this well

        #print(f"well {wi+1}/{n_wells} offset={offset:.0f} ref_depth={ref_depth:.0f} well_td={well_td:.0f}")

        # formatter to show TRUE depth: depth = plot_value + offset
        if offset != 0.0:
            depth_formatter = FuncFormatter(lambda y, pos, off=offset: f"{(y + off):.2f}")
        else:
            depth_formatter = None

        LOG.debug(f"depth_formatter={depth_formatter}")

        first_track_idx = wi * (n_tracks + 1)
        main_ax = axes[first_track_idx]
        well_main_axes.append(main_ax)

        # ---- Case: no tracks, just depth axis ----
        if not filtered_tracks:
            base_ax = main_ax
            base_ax.set_ylim(global_top_plot, global_bottom_plot)
            base_ax.invert_yaxis()
            base_ax.grid(True, linestyle="--", alpha=0.3)
            base_ax.set_ylabel("Depth (m)", labelpad=8)
            base_ax.tick_params(axis="y", labelleft=True)
            base_ax.xaxis.set_visible(False)
            base_ax.set_title(well.get("name", f"Well {wi + 1}"), pad=5, fontsize=10)

            if depth_formatter is not None:
                base_ax.yaxis.set_major_formatter(depth_formatter)
            continue

        # ---- Normal multi-track case ----
        for ti, track in enumerate(filtered_tracks):
            col_idx = wi * (n_tracks + 1) + ti
            base_ax = axes[col_idx]

            LOG.debug(f"track {ti+1}/{n_tracks} offset={offset:.0f} ref_depth={ref_depth:.0f} well_td={well_td:.0f}")

            # Shared plotting Y-range for all wells
            base_ax.set_ylim(global_top_plot, global_bottom_plot)

            base_ax.invert_yaxis()
            base_ax.grid(True, linestyle="--", alpha=0.3)

            if ti == 0:
                base_ax.set_ylabel("Depth (m)", labelpad=8)
                base_ax.tick_params(axis="y", labelleft=True)
                if depth_formatter is not None:
                    base_ax.yaxis.set_major_formatter(depth_formatter)
            else:
                base_ax.tick_params(axis="y", labelleft=False )

            base_ax.xaxis.set_visible(False)

            mid_track = n_tracks // 2
            if ti == mid_track:
                base_ax.set_title(well.get("name", f"Well {wi + 1}"), pad=5, fontsize=10)

            # If track is hidden: just leave the axis empty (depth axis still there).
            #if track_hidden:
                # no logs, no discrete fill
            #    continue

            # ---- Continuous logs ----
            Add_logs_to_track(base_ax, offset, track, visible_logs, well)

            if track.get("type") == "bitmap":
                _draw_bitmap_track(base_ax,well, track, offset)

            disc_cfg = track.get("discrete")
            if disc_cfg is not None:
                _draw_discrete_track(base_ax, well, offset, disc_cfg, visible_discrete_logs=None)

            if track.get("type") == "lithofacies":
                _draw_lithofacies_track(base_ax,well,track, offset)



    fig.canvas.draw()
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

    return axes, well_main_axes


def Add_logs_to_track(base_ax, offset, track, visible_logs, well):
    for j, log_cfg in enumerate(track.get("logs", [])):
        log_name = log_cfg["log"]

        if visible_logs is not None and log_name not in visible_logs:
            continue

        log_def = well.get("logs", {}).get(log_name)
        if log_def is None:
            continue

        depth = log_def["depth"]
        data = log_def["data"]

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

def _draw_discrete_track(base_ax, well, offset, disc_cfg, visible_discrete_logs=None):
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

def _draw_bitmap_track(base_ax, well, track, offset = 0.0):
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

    if bitmaps is not None:
        for bitmap in bitmaps:
            if bitmap is not None:
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

        first_track_idx = wi * (n_tracks + 1)
        last_track_idx = first_track_idx + n_tracks - 1
        left = axes[first_track_idx].get_position().x0
        right = axes[last_track_idx].get_position().x1
        mid_x = (left + right) / 2

        label = f"{ref_depth:.0f}–{well_td:.0f} m"
        fig.text(mid_x, 0.04, label, ha="center", va="center", fontsize=9)

def add_tops_and_correlations(
    fig,
    axes,
    wells,
    well_main_axes,
    n_tracks,
    correlations_only=False,
    corr_artists=None,
    highlight_top=None,
    flatten_depths=None,
    visible_tops=None,
    visible_tracks = None,
    stratigraphy = None,
):
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

        first_track_idx = wi * (n_tracks + 1)

        # Draw top lines and within-well fills only on full pass
        if not correlations_only:
            # horizontal top lines in ALL tracks of this well
            for ti in range(n_tracks):
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
                    if stratigraphy[name_upper]['role']=='stratigraphy':
                        for ti in range(n_tracks):
                            col_idx = first_track_idx + ti
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
                thickness = depth_range * 0.01
                open_top = deepest_formation
                open_bottom = min(deepest_formation + thickness, depth_max)
                if open_bottom > open_top:
                    for ti in range(n_tracks):
                        col_idx = first_track_idx + ti
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
        x_label_pos = x_min_main + 0.02 * (x_max_main - x_min_main)

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

            if name not in tops_by_name:
                tops_by_name[name] = {
                    "color": color,
                    "level": info["level"],
                    "style": info["style"],
                    "entries": [],
                }
            tops_by_name[name]["entries"].append((wi, y_fig))

    # ---- pass 2: correlation lines in spacers ----
    for name, info in tops_by_name.items():
        color = info["color"]
        style = info["style"]
        entries = info["entries"]
        if len(entries) < 2:
            continue

        entries_sorted = sorted(entries, key=lambda t: t[0])

        for (w1, y1), (w2, y2) in zip(entries_sorted[:-1], entries_sorted[1:]):
            if w2 != w1 + 1:
                continue  # only adjacent wells

            spacer_idx = w1 * (n_tracks + 1) + n_tracks
            spacer_ax = axes[spacer_idx]
            left = spacer_ax.get_position().x0
            right = spacer_ax.get_position().x1

            line = Line2D(
                [left, right],
                [y1, y2],
                transform=fig.transFigure,
                color=color,
                linewidth=style["line_width"],
                linestyle=style["line_style"],
                alpha=0.9,
            )
            fig.add_artist(line)
            corr_artists.append(line)

    # ---- pass 3: spacer fills between wells ----
    for w1 in range(n_wells - 1):
        w2 = w1 + 1

        shared_names = sorted(
            set(well_top_depths[w1].keys()) & set(well_top_depths[w2].keys()),
            key=lambda n: 0.5 * (well_top_depths[w1][n] + well_top_depths[w2][n]),
        )
        if len(shared_names) < 2:
            continue

        spacer_idx = w1 * (n_tracks + 1) + n_tracks
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

            poly = patches.Polygon(
                [
                    (x_left, y1_left),
                    (x_right, y1_right),
                    (x_right, y2_right),
                    (x_left, y2_left),
                ],
                closed=True,
                transform=fig.transFigure,
                facecolor=color,
                alpha=style["alpha"],
                edgecolor="none",
                hatch=style["hatch"],
                zorder=0.2,
            )
            fig.add_artist(poly)
            corr_artists.append(poly)

    return corr_artists


