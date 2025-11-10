from PyQt5.QtWidgets import (
    QMainWindow, QAction, QFileDialog, QMessageBox
)
from pywellsection.Qt_Well_Widget import WellPanelWidget
from pywellsection.sample_data import create_dummy_data
from pywellsection.io_utils import export_project_to_json, load_project_from_json

import json
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Well Log / Picking Panel")
        self.resize(1000, 800)

        # ---- central widget ----

        wells, tracks, stratigraphy = create_dummy_data()
        self.panel = WellPanelWidget(wells, tracks, stratigraphy)
        self.setCentralWidget(self.panel)

        # ---- build menu bar ----
        self._create_menubar()

    # ------------------------------------------------
    # MENU BAR SETUP
    # ------------------------------------------------
    def _create_menubar(self):
        menubar = self.menuBar()

        # --- File menu ---
        file_menu = menubar.addMenu("&File")

        act_open = QAction("Open...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._project_file_open)
        file_menu.addAction(act_open)

        act_save = QAction("Save...", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._project_file_save)
        file_menu.addAction(act_save)

        file_menu.addSeparator()

        act_exit = QAction("Exit", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # --- optional Help menu ---
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("About...", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------
    # FILE HANDLERS (placeholders for now)
    # ------------------------------------------------

    def _project_file_open(self):
        """Load wells/tracks data from a JSON file (example)."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open well data",
            "",
            "Well data (*.json);;All files (*.*)"
        )
        if not path:
            return

        try:

            #path = Path(path)

            self.wells, self.tracks, self.stratigraphy, meta_data = load_project_from_json(path)

            self.panel.update_panel(self.wells, self.tracks, self.stratigraphy)
            self.panel.draw_panel()

        except Exception as e:
            QMessageBox.critical(self, "Open error", f"Failed to open file:\n{e}")

    def _project_file_save(self):
        """Save wells/tracks data to a JSON file (example)."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save project",
            "",
            "Well project (*.json);;All files (*.*)"
        )
        if not path:
            return

        path = Path(path)

        try:
            wells = getattr(self.panel, "wells", [])
            #print ("Saving",wells[0])

            for well in wells:
                print("Saving",well["name"], "")

            tracks = getattr(self.panel, "tracks", [])
            stratigraphy = getattr(self.panel, "stratigraphy", None)
            extra_metadata = {
                "app": "pywellsection",
                "version": "0.1.0",
            }

            project = export_project_to_json(path, wells, tracks, stratigraphy, extra_metadata)



            print("Saving",project["wells"][0]["name"], "done")



        except Exception as e:
            QMessageBox.critical(self, "Save error", f"Failed to save project:\n{e}")

    def _show_about(self):
        QMessageBox.information(
            self,
            "About",
            "Well Panel Demo\n\n"
            "Includes well log visualization, top picking, and stratigraphic editing."
        )
