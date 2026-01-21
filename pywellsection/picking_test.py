from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QDialog, QFormLayout, QLabel,
    QDoubleSpinBox, QPushButton, QDialogButtonBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import sys
import numpy as np


class EditFormationTopDialog(QDialog):
    def __init__(self, parent, well_name, formation_name,
                 current_depth, min_bound, max_bound):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Top: {formation_name} • {well_name}")
        self.resize(380, 160)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        layout.addLayout(form)

        def fmt(v):
            return "-∞" if not np.isfinite(v) else f"{v:.3f}"
        self.bounds = (min_bound, max_bound)
        self.lbl_bounds = QLabel(f"Bounds: {fmt(min_bound)} … {fmt(max_bound)}")
        form.addRow("Limits:", self.lbl_bounds)

        self.spin = QDoubleSpinBox(self)
        mn = min_bound if np.isfinite(min_bound) else -1e9
        mx = max_bound if np.isfinite(max_bound) else 1e9
        self.spin.setRange(mn, mx)
        self.spin.setDecimals(3)
        self.spin.setSingleStep(0.1)
        self.spin.setValue(float(current_depth))
        form.addRow("Depth:", self.spin)

        self.btn_pick = QPushButton("Pick on plot", self)
        layout.addWidget(self.btn_pick)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.accepted.connect(self.accept)   # important
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def set_depth(self, d: float):
        mn, mx = self.bounds
        if np.isfinite(mn):
            d = max(d, mn + 1e-6)
        if np.isfinite(mx):
            d = min(d, mx - 1e-6)
        self.spin.setValue(float(d))

    def value(self) -> float:
        return float(self.spin.value())


class WellPanelWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.fig = Figure(figsize=(4, 6), dpi=100)
        self.canvas = FigureCanvas(self.fig)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        # one axis and one “top”
        self.ax = self.fig.add_subplot(111)
        self.ax.set_ylim(1000, 1100)
        self.ax.invert_yaxis()
        self.top_depth = 1050.0

        # picking state
        self._in_dialog_pick_mode = False
        self._dialog_pick_cid = None
        self._motion_pick_cid = None
        self._active_top_dialog = None
        self._active_pick_context = None
        self._pick_line_artists = []

        self._draw_top()

        # click on axis to open dialog
        self.canvas.mpl_connect("button_press_event", self._on_top_click)

    def _draw_top(self):
        self.ax.clear()
        self.ax.set_ylim(1000, 1100)
        self.ax.invert_yaxis()
        self.ax.axhline(self.top_depth, color="red", linewidth=2)

        # x in axes (0–1), y in data
        self.ax.text(
            0.05,
            self.top_depth,
            f"Top @ {self.top_depth:.2f}",
            transform=self.ax.get_yaxis_transform(),
            va="center",
            ha="left",
        )
        self.canvas.draw_idle()

    # ---------- MAIN TOP CLICK ----------
    def _on_top_click(self, event):
        # ignore if we're in pick mode already
        if self._in_dialog_pick_mode:
            return
        if event.button != 1 or event.inaxes != self.ax or event.ydata is None:
            return

        click_depth = float(event.ydata)
        # simple “nearest” logic: within 5m
        if abs(click_depth - self.top_depth) > 5.0:
            return

        # avoid re-opening multiple dialogs
        if self._active_top_dialog is not None:
            return

        # pick context (for pick-on-plot)
        self._active_pick_context = {
            "last_depth": self.top_depth,
        }

        dlg = EditFormationTopDialog(
            self,
            well_name="DemoWell",
            formation_name="DemoTop",
            current_depth=self.top_depth,
            min_bound=1000,
            max_bound=1100,
        )
        self._active_top_dialog = dlg

        # wire up actions
        dlg.btn_pick.clicked.connect(self._arm_pick_for_dialog)
        dlg.accepted.connect(self._dialog_accepted)
        dlg.rejected.connect(self._dialog_rejected)

        dlg.show()

    # ---------- DIALOG RESULT ----------
    def _dialog_accepted(self):
        """OK clicked on dialog: update top and redraw."""
        if self._active_top_dialog is None:
            return

        new_depth = self._active_top_dialog.value()
        self.top_depth = new_depth
        self._active_top_dialog = None
        self._active_pick_context = None
        self._clear_pick_line()
        self._draw_top()

    def _dialog_rejected(self):
        """Cancel clicked: just clean up."""
        self._active_top_dialog = None
        self._active_pick_context = None
        self._clear_pick_line()
        # no change to self.top_depth

    # ---------- PICK MODE ----------
    def _arm_pick_for_dialog(self):
        """Hide dialog and start pick-on-plot mode."""
        if self._active_top_dialog is None or self._active_pick_context is None:
            return

        self._active_top_dialog.hide()
        self._in_dialog_pick_mode = True

        # disconnect previous pick handlers
        if self._dialog_pick_cid is not None:
            self.canvas.mpl_disconnect(self._dialog_pick_cid)
            self._dialog_pick_cid = None
        if self._motion_pick_cid is not None:
            self.canvas.mpl_disconnect(self._motion_pick_cid)
            self._motion_pick_cid = None

        # connect handlers
        self._dialog_pick_cid = self.canvas.mpl_connect(
            "button_press_event", self._handle_dialog_pick_click
        )
        self._motion_pick_cid = self.canvas.mpl_connect(
            "motion_notify_event", self._handle_dialog_pick_move
        )

    def _clear_pick_line(self):
        for art in self._pick_line_artists:
            try:
                art.remove()
            except Exception:
                pass
        self._pick_line_artists = []
        self.canvas.draw_idle()

    def _handle_dialog_pick_move(self, event):
        """Show moving band at mouse depth while picking."""
        if not self._in_dialog_pick_mode:
            return
        if self._active_pick_context is None:
            return
        if event.ydata is None or event.inaxes != self.ax:
            return

        depth = float(event.ydata)
        self._active_pick_context["last_depth"] = depth

        self._clear_pick_line()

        y0, y1 = self.ax.get_ylim()
        depth_range = abs(y0 - y1) or 1.0
        thickness = depth_range * 0.01

        band = self.ax.axhspan(
            depth - thickness / 2.0,
            depth + thickness / 2.0,
            xmin=0.0,
            xmax=1.0,
            facecolor="yellow",
            alpha=0.3,
            hatch="///",
            edgecolor="red",
            linewidth=0.8,
            zorder=5,
        )
        self._pick_line_artists.append(band)
        self.canvas.draw_idle()

    def _handle_dialog_pick_click(self, event):
        """Click once to set depth and return to dialog."""
        if not self._in_dialog_pick_mode:
            return
        if self._active_pick_context is None:
            return

        ctx = self._active_pick_context
        depth = None
        if event.ydata is not None and event.inaxes == self.ax:
            depth = float(event.ydata)
            ctx["last_depth"] = depth
        else:
            depth = ctx.get("last_depth")

        if depth is not None and self._active_top_dialog is not None:
            self._active_top_dialog.set_depth(depth)

        # exit pick mode and remove band
        if self._dialog_pick_cid is not None:
            self.canvas.mpl_disconnect(self._dialog_pick_cid)
            self._dialog_pick_cid = None
        if self._motion_pick_cid is not None:
            self.canvas.mpl_disconnect(self._motion_pick_cid)
            self._motion_pick_cid = None

        self._in_dialog_pick_mode = False
        self._clear_pick_line()

        # show dialog again so user can OK/Cancel
        if self._active_top_dialog is not None:
            self._active_top_dialog.show()
            self._active_top_dialog.raise_()
            self._active_top_dialog.activateWindow()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pick-on-plot demo (non-modal)")
        self.widget = WellPanelWidget()
        self.setCentralWidget(self.widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(500, 800)
    win.show()
    sys.exit(app.exec_())
