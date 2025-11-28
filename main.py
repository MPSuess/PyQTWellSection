#from sample_data import create_dummy_data
#from Qt_Well_Widget import WellPanelWidget
from PyQt5 import QtWidgets, QtCore

from PyQt5.QtWidgets import (
    QApplication
)
import sys


from pywellsection.MainWindow import MainWindow




if __name__ == "__main__":
    if sys.platform == "darwin":
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_DontUseNativeMenuBar, True)
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(1250, 900)
    w.show()
    sys.exit(app.exec_())


