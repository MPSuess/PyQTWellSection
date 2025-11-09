#from sample_data import create_dummy_data
#from Qt_Well_Widget import WellPanelWidget
from PyQt5.QtWidgets import (
    QApplication, QMainWindow,
)
import sys

from pywellsection.Qt_Well_Widget import WellPanelWidget
from pywellsection.sample_data import create_dummy_data


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Well Panel with Toolbar")

        wells, tracks, stratigraphy = create_dummy_data()

        self.panel = WellPanelWidget(wells,tracks, stratigraphy)
        self.setCentralWidget(self.panel)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1250, 900)
    w.show()
    sys.exit(app.exec_())


