#from sample_data import create_dummy_data
#from Qt_Well_Widget import WellPanelWidget
from PySide6 import QtWidgets, QtCore

from PySide6.QtWidgets import (
    QApplication
)
import sys

from qdarkstyle import load_stylesheet_pyside6 as qdarkstyle

#import qtass


from pywellsection.MainWindow import MainWindow




if __name__ == "__main__":

    # style = qtass.QtAdvancedStylesheet()
    # style.set_styles_dir_path("styles")
    # print("Available styles:", style.styles)
    # style.output_dir = "build/style_output2"
    # style.set_current_style("metro")
    # style.set_default_theme()
    # style.update_stylesheet()


    if sys.platform == "darwin":
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_DontUseNativeMenuBar, True)
    app = QApplication(sys.argv)
    #app.setStyleSheet(qdarkstyle())
    #app.setStyleSheet(style.stylesheet)
    w = MainWindow()
    w.resize(1250, 900)
    w.show()
    sys.exit(app.exec_())


