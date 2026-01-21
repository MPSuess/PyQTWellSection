import logging

from PySide6.QtGui import QFont
from PySide6.QtCore import (Qt, QAbstractTableModel, QModelIndex)
from PySide6.QtCore import Signal as pyqtSignal
from PySide6.QtWidgets import QPlainTextEdit, QDockWidget

from pandas import DataFrame

LOG = logging.getLogger(__name__)
LOG.setLevel("INFO")

class QTextEditLogger(QPlainTextEdit, logging.Handler):
    write_text_signal = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.write_text_signal.connect(self.widget.appendPlainText)

        self.widget.setFont(QFont("Courier", 12))

    def emit(self, record):
        msg = self.format(record)
        self.write_text_signal.emit(msg)


class QTextEditCommands(QPlainTextEdit):
    """Displays commands as they are run by the GUI"""

    write_text_signal = pyqtSignal(str)

    def __init__(self, parent):
        super(QTextEditCommands, self).__init__(parent)
        self.setReadOnly(True)
        self.write_text_signal.connect(self.appendPlainText)

        self.setFont(QFont("Courier", 12))

    def add_command(self, command):
        """Writes a command to the panel"""
        if command:
            self.write_text_signal.emit("%s\n" % command)


class PandasModel(QAbstractTableModel):
    """A model to interface a Qt view with pandas dataframe """

    def __init__(self, dataframe: DataFrame, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._dataframe = dataframe

    def rowCount(self, parent=QModelIndex()) -> int:
        """ Override method from QAbstractTableModel

        Return row count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe)

        return 0

    def columnCount(self, parent=QModelIndex()) -> int:
        """Override method from QAbstractTableModel

        Return column count of the pandas DataFrame
        """
        if parent == QModelIndex():
            return len(self._dataframe.columns)
        return 0

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        """Override method from QAbstractTableModel

        Return data cell from the pandas DataFrame
        """
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return str(self._dataframe.iloc[index.row(), index.column()])

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole
    ):
        """Override method from QAbstractTableModel

        Return dataframe index as vertical header data and columns as horizontal header data.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._dataframe.columns[section])

            if orientation == Qt.Vertical:
                return str(self._dataframe.index[section])

        return None

class DockWidget (QDockWidget):
     hasFocus=pyqtSignal([QDockWidget])
     isActive=pyqtSignal([QDockWidget])
     FocusIn=pyqtSignal([QDockWidget])

     def __init__(self,text, parent=None):
         super().__init__(text, parent=parent)
         self.setObjectName(text)

