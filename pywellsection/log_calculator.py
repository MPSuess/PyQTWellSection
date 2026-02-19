import re
import numpy as np

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QListWidget, QListWidgetItem, QPlainTextEdit, QLineEdit,
    QPushButton, QComboBox, QDialogButtonBox, QLabel, QMessageBox,
    QInputDialog, QGridLayout
)

import re

import re

def _preprocess_expr(expr: str) -> str:
    """
    - allow '!' as NOT (converted to '~' but keep '!=')
    - allow 'if(' as alias for 'IF(' (since 'if' is a Python keyword)
    """
    expr = expr.strip()

    # replace '!' not followed by '=' with '~'
    expr = re.sub(r"!(?!=)", "~", expr)

    # replace keyword-like "if(" with "IF(" in a safe way:
    # - only when 'if' appears as a standalone token (word boundary)
    # - allows whitespace: if ( ... ) -> IF(
    expr = re.sub(r"\bif\s*\(", "IF(", expr)

    return expr


def _preprocess_inline_if(expr: str) -> str:
    """
    Convert inline numpy-style:
        a if condition else b
    into:
        where(condition, a, b)

    Only supports single inline expression.
    """

    # match: <true_expr> if <condition> else <false_expr>
    import re

    pattern = r"(.+?)\s+if\s+(.+?)\s+else\s+(.+)"
    match = re.fullmatch(pattern, expr.strip())
    if not match:
        return expr

    true_expr = match.group(1).strip()
    condition = match.group(2).strip()
    false_expr = match.group(3).strip()

    return f"where({condition}, {true_expr}, {false_expr})"

# ============================================================
# 1) Safe evaluation helpers (numpy only)
# ============================================================

def AND(a, b): return np.logical_and(a, b)
def OR(a, b):  return np.logical_or(a, b)
def NOT(a):    return np.logical_not(a)

def GT(a, b): return np.greater(a, b)
def GE(a, b): return np.greater_equal(a, b)
def LT(a, b): return np.less(a, b)
def LE(a, b): return np.less_equal(a, b)
def EQ(a, b): return np.equal(a, b)
def NE(a, b): return np.not_equal(a, b)

def IN(x, choices):
    """
    Vectorized membership check.
    - x can be numeric or string array
    - choices is list/tuple/set
    """
    # np.isin supports dtype=object well
    return np.isin(x, list(choices))

def IF(cond, a, b):
    return np.where(cond, a, b)

_ALLOWED_MATH = {
    # constants
    "pi": np.pi,
    "e": np.e,

    # basic numpy
    "abs": np.abs,
    "sqrt": np.sqrt,
    "exp": np.exp,
    "log": np.log,
    "log10": np.log10,
    "sin": np.sin,
    "cos": np.cos,
    "tan": np.tan,
    "arcsin": np.arcsin,
    "arccos": np.arccos,
    "arctan": np.arctan,
    "sinh": np.sinh,
    "cosh": np.cosh,
    "tanh": np.tanh,

    "minimum": np.minimum,
    "maximum": np.maximum,
    "clip": np.clip,
    "where": np.where,

    "nan": np.nan,
    "isnan": np.isnan,
    "isfinite": np.isfinite,

    # common geoscience-friendly helpers
    "smooth1d": None,  # filled below

    "AND": AND,
    "OR": OR,
    "NOT": NOT,
    "GT": GT,
    "GE": GE,
    "LT": LT,
    "LE": LE,
    "EQ": EQ,
    "NE": NE,
    "IN": IN,
    "if": IF,        # lowercase version
    "IF": IF,        # optional uppercase support
}



def _parse_expression(expr: str):
    """
    Supports either:
      - simple expression:  GR * 100
      - assignment:         DT100 = DT * 100

    Returns
    -------
    (output_name_or_None, rhs_expression)
    """
    expr = expr.strip()
    print(expr)
    # detect single assignment (not '==')
    if "=" in expr and "==" not in expr:
        parts = expr.split("=", 1)
        lhs = parts[0].strip()
        rhs = parts[1].strip()

        if not _is_valid_var(lhs):
            raise ValueError(f"Invalid output variable name: {lhs}")

        return lhs, rhs

    return None, expr

def _smooth1d(x, win=11):
    """Simple moving average smoothing (odd win recommended)."""
    x = np.asarray(x, dtype=float)
    if win is None:
        return x
    win = int(win)
    win = max(1, win)
    if win % 2 == 0:
        win += 1
    if win == 1:
        return x
    k = np.ones(win, dtype=float) / win
    # pad edges to avoid shrink
    pad = win // 2
    xp = np.pad(x, (pad, pad), mode="edge")
    return np.convolve(xp, k, mode="valid")

_ALLOWED_MATH["smooth1d"] = _smooth1d


def _safe_eval_numpy(expr: str, env: dict):
    """
    Evaluate expression with restricted globals.
    - no builtins
    - only provided env symbols
    """
    code = compile(expr, "<logcalc>", "eval")
    return eval(code, {"__builtins__": {}}, env)


def _is_valid_var(name: str) -> bool:
    return bool(re.match(r"^[A-Za-z_]\w*$", name))


def _sanitize_symbol(name: str) -> str:
    """
    Turn a log name into a valid python identifier.
    Example: "Gamma Ray (API)" -> "Gamma_Ray_API"
    """
    s = re.sub(r"\W+", "_", str(name).strip())
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "LOG"
    if s[0].isdigit():
        s = "L_" + s
    return s


def _interp_to_depth(depth_src, data_src, depth_target):
    """Linear interp; preserves NaN for out-of-range."""
    depth_src = np.asarray(depth_src, dtype=float)
    data_src = np.asarray(data_src, dtype=float)
    depth_target = np.asarray(depth_target, dtype=float)

    # sort required for np.interp
    order = np.argsort(depth_src)
    ds = depth_src[order]
    xs = data_src[order]

    # mask finite points
    m = np.isfinite(ds) & np.isfinite(xs)
    ds = ds[m]
    xs = xs[m]
    if ds.size < 2:
        return np.full_like(depth_target, np.nan, dtype=float)

    y = np.interp(depth_target, ds, xs)
    # set out-of-range to NaN
    y[(depth_target < ds.min()) | (depth_target > ds.max())] = np.nan
    return y


# ============================================================
# 2) Calculator Dialog
# ============================================================

class LogCalculatorDialog(QDialog):
    """
    A log calculator:
      - expression input (python syntax, numpy functions via buttons)
      - list of existing logs (insert symbol)
      - function buttons (sin, log, where, etc.)
      - output settings: name + continuous/discrete
    """

    def __init__(self, parent, panel, all_wells):
        """
        panel should provide access to project data:
          - panel.wells: list of wells
          - panel.draw_panel()
        """
        super().__init__(parent)
        self.setWindowTitle("Log Calculator")
        self.resize(980, 520)

        self.panel = panel
        self.all_wells = all_wells

        layout = QHBoxLayout(self)

        # ---- Left: Log list ----
        left = QVBoxLayout()
        left.addWidget(QLabel("Available continuous logs (pick to insert):", self))

        self.lst_logs = QListWidget(self)
        #self.lst_logs.setSelectionMode(self.lst_logs.SingleSelection)
        left.addWidget(self.lst_logs, 1)

        btn_insert = QPushButton("Insert selected log", self)
        btn_insert.clicked.connect(self._insert_selected_log)
        left.addWidget(btn_insert)

        layout.addLayout(left, 1)

        # ---- Center: Editor + buttons ----
        center = QVBoxLayout()

        center.addWidget(QLabel("Formula (Python syntax):", self))
        self.txt_expr = QPlainTextEdit(self)
        self.txt_expr.setPlaceholderText("Example: (GR - smooth1d(GR, 21)) / maximum(1e-6, RHOB)\n"
                                         "Use log symbols from the left (e.g. GR, RHOB).")
        self.txt_expr.setTabChangesFocus(False)
        center.addWidget(self.txt_expr, 2)

        # --- inside LogCalculatorDialog.__init__ (replace your current button layout) ---
        # Five rows x six columns = 30 buttons
        btn_grid = QGridLayout()
        btn_grid.setHorizontalSpacing(6)
        btn_grid.setVerticalSpacing(6)

        # (label, insert_text)

        buttons_5x6 = [
            # Row 1
            ("sin", "sin("), ("cos", "cos("), ("tan", "tan("), ("sqrt", "sqrt("), ("abs", "abs("), ("exp", "exp("),

            # Row 2
            ("log", "log("), ("log10", "log10("), ("where", "where("), ("min", "minimum("), ("max", "maximum("),
            ("clip", "clip("),

            # Row 3
            ("smooth", "smooth1d("), ("bins", "bins("), ("(", "("), (")", ")"), (",", ", "), ("nan", "nan"),

            # Row 4
            (">", " > "), ("<", " < "), (">=", " >= "), ("<=", " <= "), ("==", " == "), ("!=", " != "),

            # Row 5
            ("&", " & "), ("|", " | "), ("~", "~"), ("if", " if "), ("else", " else "), ("!", "!"),
        ]


        # Create 5x6 grid
        for idx, (label, insert_text) in enumerate(buttons_5x6):
            r = idx // 6
            c = idx % 6
            b = QPushButton(label, self)
            b.setMinimumWidth(28)
            b.setMinimumHeight(28)
            b.clicked.connect(lambda _, s=insert_text: self._insert_text(s))
            btn_grid.addWidget(b, r, c)

        # Add the grid into the center layout where your previous button row(s) were
        center.addWidget(QLabel("Calculator:", self))
        center.addLayout(btn_grid)


        # function buttons
        # center.addWidget(QLabel("Scientific functions:", self))
        # grid = QHBoxLayout()
        #
        # self._fn_buttons = [
        #     # scientific functions
        #     ("sin(", "sin("),
        #     ("cos(", "cos("),
        #     ("tan(", "tan("),
        #     ("log(", "log("),
        #     ("log10(", "log10("),
        #     ("exp(", "exp("),
        #     ("sqrt(", "sqrt("),
        #     ("abs(", "abs("),
        #     ("where(", "where("),
        #     ("minimum(", "minimum("),
        #     ("maximum(", "maximum("),
        #     ("clip(", "clip("),
        #     ("smooth1d(", "smooth1d("),
        #     ("bins(", "bins("),
        #
        #     # ---- boolean / logical operators ----
        #     (">", " > "),
        #     ("<", " < "),
        #     (">=", " >= "),
        #     ("<=", " <= "),
        #     ("==", " == "),
        #     ("!=", " != "),
        #     ("!", "!"),  # will be preprocessed to '~' (NOT)
        #     ("&", " & "),  # AND for arrays
        #     ("|", " | "),  # OR for arrays
        #     ("~", "~"),  # NOT for arrays (native)
        #     ("(", "("),
        #     (")", ")"),
        # ]
        # for label, insert in self._fn_buttons:
        #     b = QPushButton(label, self)
        #     b.clicked.connect(lambda _, s=insert: self._insert_text(s))
        #     grid.addWidget(b)
        #
        # center.addLayout(grid)

        # ---- Output options ----
        form = QFormLayout()

        self.ed_out_name = QLineEdit(self)
        self.ed_out_name.setPlaceholderText("New log name (e.g. GR_Detrended)")
        form.addRow("Output log name:", self.ed_out_name)

        self.cmb_kind = QComboBox(self)
        self.cmb_kind.addItems(["continuous", "discrete"])
        form.addRow("Output type:", self.cmb_kind)

        center.addLayout(form)

        # ---- Run / Close ----
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        btns.button(QDialogButtonBox.Ok).setText("Run (Enter)")
        btns.accepted.connect(self._run)
        btns.rejected.connect(self.reject)
        center.addWidget(btns)

        layout.addLayout(center, 2)

        # Keyboard convenience: Ctrl+Enter / Enter triggers run
        self.txt_expr.installEventFilter(self)

        # populate log list
        self._log_symbol_map = {}  # display -> symbol
        self._populate_logs()

    def eventFilter(self, obj, event):
        # Only handle key presses from the expression editor
        if obj is self.txt_expr and event.type() == QEvent.KeyPress:
            key = event.key()
            mods = event.modifiers()

            # Run on Ctrl+Enter
            if (key in (Qt.Key_Return, Qt.Key_Enter)) and (mods & Qt.ControlModifier):
                self._run()
                return True

        return super().eventFilter(obj, event)


    def _populate_logs(self):
        self.lst_logs.clear()
        self._log_symbol_map.clear()

        # Collect union of continuous log names across wells
        log_names = set()
        # for w in (getattr(self.panel, "wells", None) or []):
        #     for ln in (w.get("logs") or {}).keys():
        #         log_names.add(ln)

        for w in (self.all_wells or []):
            for ln in (w.get("logs") or {}).keys():
                log_names.add(ln)
            for ln in (w.get("discrete_logs") or {}).keys():
                log_names.add(ln)

        # Make stable sorted list
        for ln in sorted(log_names):
            sym = _sanitize_symbol(ln)
            # ensure uniqueness of symbol
            base = sym
            k = 2
            while sym in self._log_symbol_map.values():
                sym = f"{base}_{k}"
                k += 1

            it = QListWidgetItem(f"{ln}   →   {sym}")
            it.setData(Qt.UserRole, (ln, sym))
            self.lst_logs.addItem(it)
            self._log_symbol_map[ln] = sym

    def _insert_text(self, s: str):
        cur = self.txt_expr.textCursor()
        cur.insertText(s)
        self.txt_expr.setFocus()

    def _insert_selected_log(self):
        it = self.lst_logs.currentItem()
        if not it:
            return
        ln, sym = it.data(Qt.UserRole)
        self._insert_text(sym)

    # ============================================================
    # 3) Execution: compute log per well and add to wells
    # ============================================================

    def _run(self):
        expr_raw = self.txt_expr.toPlainText().strip()
        if not expr_raw:
            QMessageBox.warning(self, "Log Calculator", "Please enter a formula.")
            return

        try:
            assigned_name, expr = _parse_expression(expr_raw)
        except Exception as e:
            QMessageBox.warning(self, "Log Calculator", str(e))
            return

        # If assignment was used, override output name
        if assigned_name:
            out_name = assigned_name
        else:
            out_name = self.ed_out_name.text().strip()
            if not out_name:
                out_name, ok = QInputDialog.getText(self, "Output name", "Enter output log name:")
                if not ok or not out_name.strip():
                    return
                out_name = out_name.strip()


        kind = self.cmb_kind.currentText().strip().lower()
        if kind not in ("continuous", "discrete"):
            kind = "continuous"

        #wells = getattr(self.panel, "wells", None) or []
        wells = self.all_wells or []
        if not wells:
            QMessageBox.warning(self, "Log Calculator", "No wells available.")
            return

        # Determine which symbols are referenced in the expression
        # We'll simply provide ALL symbols; safe_eval prevents other globals anyway.
        # For each well, build env mapping symbols -> arrays (on a common depth grid).
        n_done = 0
        n_skipped = 0
        errors = []

        expr = _preprocess_expr(expr)
        #expr = _preprocess_inline_if(expr)


        for w in wells:
            # skip wells without any logs
            w_logs = w.get("logs") or {}
            if not w_logs:
                n_skipped += 1
                continue

            # Build per-well symbol env from available logs
            # Choose a common depth grid: depth of the first available log in this well
            first_log = next(iter(w_logs.values()))
            depth0 = np.asarray(first_log.get("depth", []), dtype=float)
            if depth0.size < 2:
                n_skipped += 1
                continue

            env = dict(_ALLOWED_MATH)

            # Add all log symbols found in this well (interpolated to depth0)
            for ln, sym in self._log_symbol_map.items():
                ld = w_logs.get(ln)
                if ld is None:
                    continue
                d = np.asarray(ld.get("depth", []), dtype=float)
                x = np.asarray(ld.get("data", []), dtype=float)
                if d.size < 2 or x.size < 2:
                    continue
                env[sym] = _interp_to_depth(d, x, depth0)

            # Provide depth as a variable too
            env["DEPTH"] = depth0

            # Evaluate
            try:
                y = _safe_eval_numpy(expr, env)
            except Exception as e:
                errors.append(f"{w.get('name','(well)')}: {e}")
                n_skipped += 1
                continue

            y = np.asarray(y)

            # Convert result to continuous/discrete format
            if kind == "continuous":
                # force float
                y = y.astype(float, copy=False)
                w.setdefault("logs", {})
                w["logs"][out_name] = {"depth": depth0.tolist(), "data": y.tolist()}
                n_done += 1
            else:
                # DISCRETE: store (depth, values) with -999 meaning "no value below"
                # Here we convert numeric result to categories by keeping values as strings of rounded number.
                # If you want true categorical mapping later, you can replace this.
                vals = []
                for v in y:
                    if not np.isfinite(v):
                        vals.append("-999")
                    else:
                        vals.append(f"{float(v):.4g}")
                w.setdefault("discrete_logs", {})
                w["discrete_logs"][out_name] = {"depth": depth0.tolist(), "values": vals}
                n_done += 1

        if errors:
            QMessageBox.warning(
                self,
                "Log Calculator",
                "Some wells could not be processed:\n\n" + "\n".join(errors[:10]) +
                ("" if len(errors) <= 10 else f"\n… ({len(errors)-10} more)")
            )

        if n_done == 0:
            QMessageBox.information(self, "Log Calculator", "No logs were generated.")
            return

        # Add new log to visibility (optional)
        if kind == "continuous":
            if hasattr(self.panel, "add_visible_log_by_name"):
                self.panel.add_visible_log_by_name(out_name, redraw=False)
        else:
            if hasattr(self.panel, "add_visible_discrete_log_by_name"):
                self.panel.add_visible_discrete_log_by_name(out_name, redraw=False)

        # Redraw once
        if hasattr(self.panel, "draw_panel"):
            self.panel.draw_panel()

        QMessageBox.information(
            self,
            "Log Calculator",
            f"Generated '{out_name}' ({kind}) for {n_done} well(s).\nSkipped: {n_skipped}"
        )
        self.accept()

