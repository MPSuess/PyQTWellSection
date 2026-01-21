import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QDockWidget
from PySide6.QtCore import Qt


class MapPanelWidget(QWidget):
    """
    Analogous to WellPanelWidget:
      - owns Figure+Canvas
      - does drawing
      - exposes a small API to set data and redraw
    """

    def __init__(self, wells, profiles, map_panel_settings,
                 title = None, parent=None):
        super().__init__(parent)

        self.fig = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.fig)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)



        self.wells = wells
        self.profiles = profiles
        self.layout_settings = map_panel_settings
        self.title = title
        self.type = "MapWindow"
        self.visible = True
        self.tabified = False
        self.setObjectName(title)
        self.setWindowTitle(title.replace("_", " "))

        self.use_fixed_limits = False
        self.fixed_limits = None  # (xmin, xmax, ymin, ymax)
        self.ax = None


    # -------------------------
    # Data / redraw interface
    # -------------------------
    def set_data(self, wells, profiles):
        self.wells = wells or []
        self.profiles = profiles or []
        self.draw_panel()

    def draw_panel(self):
        self.fig.clf()
        ax = self.fig.add_subplot(111)

        show_labels = bool(self.layout_settings.get("show_labels", True))
        equal_aspect = bool(self.layout_settings.get("equal_aspect", True))
        show_grid = bool(self.layout_settings.get("show_grid", True))

        # --- wells ---
        xs, ys, names = [], [], []
        for w in self.wells:
            x, y = w.get("x"), w.get("y")
            if x is None or y is None:
                continue
            try:
                xs.append(float(x))
                ys.append(float(y))
                names.append(w.get("name", ""))
            except Exception:
                pass

        if xs:
            ax.scatter(xs, ys, s=30 )
            if show_labels:
                for x, y, nm in zip(xs, ys, names):
                    if nm:
                        ax.text(x, y, " " + nm, fontsize=8, va="center")

        # --- section profiles ---
        for p in (self.profiles or []):
            pts = p.get("points") or []
            if len(pts) < 2:
                continue
            arr = np.asarray(pts, dtype=float)
            ax.plot(arr[:, 0], arr[:, 1], linewidth=2)

            if show_labels:
                mid = arr[len(arr) // 2]
                ax.text(mid[0], mid[1], f" {p.get('name','Section')}", fontsize=9, weight="bold")

        ax.set_title("Well Map / Section Profiles")

        if equal_aspect:
            ax.set_aspect("equal", adjustable="datalim")

        if show_grid:
            ax.grid(True, linestyle="--", alpha=0.3)

        # apply limits
        if self.use_fixed_limits and self.fixed_limits:
            xmin, xmax, ymin, ymax = self.fixed_limits
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymin, ymax)

        ax.set_aspect("equal", adjustable="box")

        self.canvas.draw_idle()



class MapDockWindow(QDockWidget):
    """
    Analogous to WellPanelDock:
      - owns docking/window settings
      - hosts a MapPanelWidget
      - provides a minimal interface to set data / redraw
    """
    _counter = 1

    def __init__(self, parent, wells, profiles, map_layout_settings = None, title="Map"):
        title = f"Map_Window_{MapDockWindow._counter}"
        super().__init__(title, parent)
        self.setObjectName("MapDockWindow")
        MapDockWindow._counter += 1

        self.wells = wells
        self.profiles = profiles
        self.layout_settings = map_layout_settings

        self.title = title
        self.type = "MapWindow"
        self.visible = True
        self.tabified = False
        self.setObjectName(title)
        self.setWindowTitle(title.replace("_", " "))


        # allow docking in common areas
        self.setAllowedAreas(
            Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea |
            Qt.BottomDockWidgetArea | Qt.TopDockWidgetArea
        )
        self.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable |
            QDockWidget.DockWidgetClosable
        )

        self.panel = MapPanelWidget(wells, profiles, map_layout_settings, title)
        self.setWidget(self.panel)

    # pass-through convenience methods
    def set_data(self, wells, profiles):
        self.panel.set_data(wells, profiles)

    def draw_panel(self):
        self.panel.draw_panel()

    def get_title(self):
        return self.title

    def set_visible(self, state):
        if state:
            self.visible = True
        else:
            self.visible = False

    def get_visible(self):
        return self.visible

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
        return self.panel

    def set_layout_settings(self, settings):
        self.layout_settings = settings


