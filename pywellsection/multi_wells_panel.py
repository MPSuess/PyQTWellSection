import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.patches as patches
import numpy as np

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
    corr_artists=None,
    highlight_top=None,
):
    """
    Draw multi-well, multi-track log panel with:
      - independent depth axis per well
      - continuous logs
      - optional discrete log tracks (facies, lithology, etc.)
      - tops with hierarchy (formation/member/sequence/...)
      - colored top lines + interval fills per well
      - colored & hatched fills + correlation lines in spacer between wells

    Tops & correlations are handled in helper functions:
      - add_depth_range_labels(...)
      - add_tops_and_correlations(...)
    """

    fig.clf()

    n_wells = len(wells)
    n_tracks = len(tracks)

    # ---- Layout: tracks + spacer columns ----
    total_cols = n_wells * n_tracks + (n_wells - 1)
    width_ratios = []
    col_is_spacer = []

    if n_wells == 0:
        return

    for w in range(n_wells):
        for _ in range(n_tracks):
            width_ratios.append(1.0)
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

    # Spacer axes off
    for ax, is_spacer in zip(axes, col_is_spacer):
        if is_spacer:
            ax.axis("off")

    # One "main" axis per well (first track)
    well_main_axes = []

    ### ---- 1st pass: logs & axes (continuous + discrete) ----
    for wi, well in enumerate(wells):
        ref_depth = well["reference_depth"]
        well_td = ref_depth + well["total_depth"]

        first_track_idx = wi * (n_tracks + 1)
        main_ax = axes[first_track_idx]
        well_main_axes.append(main_ax)

        for ti, track in enumerate(tracks):
            col_idx = wi * (n_tracks + 1) + ti
            base_ax = axes[col_idx]

            base_ax.set_ylim(ref_depth, well_td)
            base_ax.invert_yaxis()
            base_ax.grid(True, linestyle="--", alpha=0.3)

            # Depth labels only 1st track of each well
            if ti == 0:
                base_ax.set_ylabel("Depth (m)", labelpad=8)
                base_ax.tick_params(axis="y", labelleft=True)
            else:
                base_ax.tick_params(axis="y", labelleft=False)

            base_ax.xaxis.set_visible(False)

            # Well title above middle track
            mid_track = n_tracks // 2
            if ti == mid_track:
                base_ax.set_title(well.get("name", f"Well {wi+1}"), pad=5)

            # ---- Continuous logs ----
            for j, log_cfg in enumerate(track.get("logs", [])):
                log_name = log_cfg["log"]
                log_def = well["logs"].get(log_name)
                if log_def is None:
                    continue

                depth = log_def["depth"]
                data = log_def["data"]

                twin_ax = base_ax.twiny()
                color = log_cfg.get("color", "black")
                label = log_cfg.get("label", log_name)

                twin_ax.plot(data, depth, color=color)

                # Only top spine
                for spine_name, spine in twin_ax.spines.items():
                    spine.set_visible(spine_name == "top")

                # Stack multiple logs upwards
                offset = 1.0 + j * 0.08
                twin_ax.spines["top"].set_position(("axes", offset))

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

            # ---- DISCRETE TRACK (optional) ----
            disc_cfg = track.get("discrete")
            if disc_cfg is not None:
                disc_name = disc_cfg["log"]
                disc_label = disc_cfg.get("label", disc_name)
                color_map = disc_cfg.get("color_map", {})
                default_color = disc_cfg.get("default_color", "#dddddd")

                disc_logs = well.get("discrete_logs", {})
                disc_def = disc_logs.get(disc_name)
                if disc_def is not None:
                    tops = np.array(disc_def.get("top_depths", []), dtype=float)
                    bottoms = np.array(disc_def.get("bottom_depths", []), dtype=float)
                    values = np.array(disc_def.get("values", []), dtype=object)

                    # Sort intervals by top depth
                    if tops.size > 0:
                        order = np.argsort(tops)
                        tops = tops[order]
                        bottoms = bottoms[order]
                        values = values[order]

                    base_ax.set_xlim(0, 1)
                    base_ax.set_xticks([])
                    base_ax.set_xlabel(disc_label, labelpad=2)

                    for top_d, bot_d, val in zip(tops, bottoms, values):
                        col = color_map.get(val, default_color)

                        base_ax.axhspan(
                            top_d,
                            bot_d,
                            xmin=0.0,
                            xmax=1.0,
                            facecolor=col,
                            edgecolor="k",
                            linewidth=0.3,
                            alpha=0.9,
                            zorder=0.8,
                        )

    ### ---- draw & add depth range labels ----

    fig.canvas.draw()
    add_depth_range_labels(fig, axes, wells, n_tracks)

    ### ---- tops + correlations (all the fancy stuff) ----
    if corr_artists is None:
        corr_artists = []

    add_tops_and_correlations(
        fig,
        axes,
        wells,
        well_main_axes,
        n_tracks,
        correlations_only=False,
        corr_artists=corr_artists,
        highlight_top=highlight_top,
    )

    ### Suptitle
    if suptitle:
        fig.suptitle(suptitle, fontsize=14, y=0.97)

    return axes, well_main_axes


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

from matplotlib.lines import Line2D
import matplotlib.patches as patches

def add_tops_and_correlations(
    fig,
    axes,
    wells,
    well_main_axes,
    n_tracks,
    correlations_only=False,
    corr_artists=None,
    highlight_top=None,
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

    # ---- pass 1: per-well tops & (optionally) within-well shading ----
    for wi, (well, main_ax) in enumerate(zip(wells, well_main_axes)):
        tops = well.get("tops", {})
        if not tops:
            continue

        # Normalize tops
        top_items = []
        for name, val in tops.items():
            if isinstance(val, dict):
                depth = float(val["depth"])
                color = val.get("color", get_top_color(name))
                level = val.get("level", default_level)
            else:
                depth = float(val)
                color = get_top_color(name)
                level = default_level
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

                    base_ax.axhline(
                        info["depth"],
                        xmin=0.0,
                        xmax=1.0,
                        color=info["color"],
                        linestyle=info["style"]["line_style"],
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
                    style = info["style"]
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
