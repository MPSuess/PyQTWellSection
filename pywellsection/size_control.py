import sys
import numpy as np

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from multi_wells_panel import draw_multi_wells_panel_on_figure
from sample_data import create_dummy_data


# -------------------------------------------------------------------
# Scrollable window with fixed-size Matplotlib figure
# -------------------------------------------------------------------
class WellLogScrollWindow(QMainWindow):
    def __init__(self, wells, tracks, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-Well Log Panel (Fixed Figure + Scrollable Window)")

        # Create a Matplotlib Figure
        # figsize doesn't control the *widget* size, but DPI * figsize = px
        self.fig = Figure(figsize=(16, 9), dpi=100)  # internal logical size
        self.canvas = FigureCanvas(self.fig)

        # Make the canvas a fixed pixel size (e.g. 1600x900 px)
        self.canvas.setFixedSize(1600, 900)
        self.canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        wells, tracks = create_dummy_data()

        # Draw your well logs onto this figure
        draw_multi_wells_panel_on_figure(
            self.fig,
            wells,
            tracks,
            suptitle="Multi-Well Panel (Fixed Figure Size)",
            well_gap_factor=3.0,
        )
        self.canvas.draw()

        # Put the canvas inside a QScrollArea
        scroll = QScrollArea(self)
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)  # keep canvas size fixed
        self.setCentralWidget(scroll)

        # Now the window can be resized independently of the figure
        self.resize(1000, 700)  # initial window size


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
if __name__ == "__main__":
    wells, tracks = create_dummy_data()

    app = QApplication(sys.argv)
    win = WellLogScrollWindow(wells, tracks)
    win.show()
    sys.exit(app.exec_())
