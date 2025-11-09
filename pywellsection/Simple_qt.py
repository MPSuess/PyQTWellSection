import sys
from multi_wells_panel import draw_multi_wells_panel_on_figure
from sample_data import create_dummy_data
import matplotlib.pyplot as plt
from PyQt5 import QtGui
from PyQt5.QtWidgets import QAction
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import (
    QInputDialog, QMessageBox, QHBoxLayout, QPushButton, QComboBox, QLabel,
    QDialog, QFormLayout, QDialogButtonBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QMenu, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem, QDockWidget,
    QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QSizePolicy, QFileDialog)


import numpy as np

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qt5cairo import FigureCanvasQTCairo as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar

from matplotlib.figure import Figure

# --- import your plotting helper from above ---
# from your_module import draw_multi_wells_panel_on_figure


class WellLogWindow(QMainWindow):
    def __init__(self, wells, tracks, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-Well Log Panel (PyQt5)")

        # Central widget + layout
        central = QWidget(self)
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Matplotlib Figure and Canvas
        # self.fig = Figure(figsize=(12, 6))
        # self.canvas = FigureCanvas(self.fig)
        # layout.addWidget(self.canvas)

        self.fig = plt.Figure(figsize=(12, 6))
        self.canvas = FigureCanvas(self.fig)
        # Make canvas expand with available space
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.updateGeometry()
        self.canvas.installEventFilter(self)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # If you use a plain QWidget as central, also:
        cw = self.centralWidget()
        if cw:
            cw.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


        self.canvas.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.canvas.setFocus()
        toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar = toolbar


        # Move plot (toolbar + canvas) into a dockable panel
        plot_container = QtWidgets.QWidget(self)
        plot_v = QtWidgets.QVBoxLayout(plot_container)
        plot_v.setContentsMargins(0, 0, 0, 0)
        plot_v.addWidget(toolbar)
        plot_v.addWidget(self.canvas)
        # Ensure canvas fills remaining space in the dock
        plot_v.setStretch(0, 0)   # toolbar: no stretch
        plot_v.setStretch(1, 1)   # canvas: takes the stretch
        try:
            toolbar.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        except Exception:
            pass
        plot_container.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.setMinimumSize(1, 1)


        self.plot_dock = QtWidgets.QDockWidget("Plot", self)
        self.plot_dock.setObjectName("PlotDock")
        self.plot_dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        self.plot_dock.setWidget(plot_container)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.plot_dock)





        wells, tracks =  create_dummy_data()

        # Draw the wells on this figure
        draw_multi_wells_panel_on_figure(
            self.fig,
            wells,
            tracks,
            suptitle="Multi-Well Log Panel",
            well_gap_factor=3.0,
        )

        # Render
        self.canvas.draw()


if __name__ == "__main__":
    wells, tracks = create_dummy_data()

    app = QApplication(sys.argv)
    win = WellLogWindow(wells, tracks)
    win.resize(1200, 700)
    win.show()
    sys.exit(app.exec_())
