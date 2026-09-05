#!/usr/bin/env python3
"""
Convolution Visualizer — qtpy / Python 3.8+
============================================
Animates the sliding convolution (f * g)(t) = ∫ f(τ) g(t-τ) dτ in real time.

Features
--------
• Four standard waveforms per signal: Rectangle, Triangle, Gaussian,
  Sinc, Sawtooth, Exponential Decay, Unit Step, Impulse Train
• Per-waveform sliders (amplitude, width/sigma, frequency, offset)
• Custom function text-entry box for arbitrary f(t) and g(t) (NumPy expressions)
• Animated sliding window showing f(τ), g(t−τ) flipped/shifted, and running
  accumulation integral coloured area
• Equation panel:
    – Convolution integral definition (mathtext pretty-print)
    – Live closed-form expression updated per selection
    – Numeric result display
    – LaTeX copy-to-clipboard buttons on every block
• Identical colour scheme and panel layout to the Fourier Spectrum Visualizer

Dependencies
------------
    pip install qtpy PyQt5 matplotlib numpy scipy
    (or PyQt6 / PySide2 / PySide6 in place of PyQt5)
"""

import sys
import math
import traceback
import numpy as np
from scipy import signal as sp_signal

from qtpy.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QSlider, QPushButton, QButtonGroup,
    QSplitter, QSizePolicy, QScrollArea, QFrame, QLineEdit,
    QGroupBox, QTabWidget, QComboBox, QCheckBox, QAbstractItemView,
    QHeaderView, QToolButton,
)
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import QColor, QPalette, QFontDatabase, QFont

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT

from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE  (matches Fourier Spectrum Visualizer)
# ─────────────────────────────────────────────────────────────────────────────
PAL = {
    "bg":         "#0e1117",
    "surface":    "#141820",
    "surface2":   "#1a1f2e",
    "surface3":   "#1f2535",
    "border":     "#2a3040",
    "border_hi":  "#3a4560",
    "text":       "#d4dbe8",
    "text_muted": "#7a8599",
    "text_faint": "#3d4558",
    "primary":    "#4fa3c8",
    "accent":     "#56e0b8",
    "warn":       "#f0b040",
    "error":      "#e05060",
    "success":    "#56c87a",
    # Signal colours
    "sig_f":      "#4fa3c8",   # f(τ)     — blue
    "sig_g":      "#f0b040",   # g(t-τ)   — amber
    "sig_conv":   "#56e0b8",   # (f*g)(t) — teal
    "sig_area":   "#c87af0",   # shaded integration area — purple
}


def p(key):
    """Python 3.8-safe palette accessor."""
    return PAL[key]


# ─────────────────────────────────────────────────────────────────────────────
# WAVEFORM ENGINE
# ─────────────────────────────────────────────────────────────────────────────
T_RANGE = 6.0       # display window: -T_RANGE to +T_RANGE
N_SAMPLES = 2000    # number of sample points

TAU = np.linspace(-T_RANGE, T_RANGE, N_SAMPLES)
DT  = TAU[1] - TAU[0]


WAVEFORMS = [
    "Rectangle",
    "Triangle",
    "Gaussian",
    "Sinc",
    "Sawtooth",
    "Exp. Decay",
    "Unit Step",
    "Impulse Train",
    "Custom",
]


def make_waveform(name: str, amplitude: float, width: float,
                  freq: float, offset: float,
                  custom_expr: str = "") -> np.ndarray:
    """
    Evaluate waveform on the global TAU grid.
    All parameters are user-controlled via sliders.
    """
    t = TAU - offset
    A = amplitude
    w = max(width, 0.05)
    f = freq

    if name == "Rectangle":
        y = A * (np.abs(t) <= w / 2).astype(float)

    elif name == "Triangle":
        y = A * np.maximum(0.0, 1.0 - np.abs(t) / w)

    elif name == "Gaussian":
        sigma = w / 2.5
        y = A * np.exp(-0.5 * (t / sigma) ** 2)

    elif name == "Sinc":
        arg = np.where(np.abs(t) < 1e-12, 1e-12, t)
        y = A * np.sinc(arg * f)  # np.sinc uses normalised sinc

    elif name == "Sawtooth":
        # periodic sawtooth, period = 1/f
        period = 1.0 / max(f, 0.05)
        y = A * sp_signal.sawtooth(2 * math.pi * t / period)

    elif name == "Exp. Decay":
        decay = 1.0 / max(w, 0.1)
        y = A * np.where(t >= 0, np.exp(-decay * t), 0.0)

    elif name == "Unit Step":
        y = A * np.where(t >= 0, 1.0, 0.0)

    elif name == "Impulse Train":
        period = 1.0 / max(f, 0.05)
        y = np.zeros_like(t)
        idx = np.round(t / period).astype(int)
        for i in range(-30, 31):
            mask = np.abs(t - i * period) < DT * 1.5
            y[mask] = A

    elif name == "Custom":
        try:
            safe = {"np": np, "sin": np.sin, "cos": np.cos, "exp": np.exp,
                    "sinc": np.sinc, "abs": np.abs, "sqrt": np.sqrt,
                    "pi": math.pi, "e": math.e, "t": t}
            y = np.asarray(eval(custom_expr, {"__builtins__": {}}, safe),
                           dtype=float)
            if y.shape != t.shape:
                y = np.broadcast_to(y, t.shape).copy()
        except Exception:
            y = np.zeros_like(t)
    else:
        y = np.zeros_like(t)

    return np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)


def compute_convolution(f: np.ndarray, g: np.ndarray) -> np.ndarray:
    """
    Linear convolution via FFT, trimmed to the same length as TAU,
    centred on zero lag.
    """
    n  = len(f) + len(g) - 1
    nf = int(2 ** math.ceil(math.log2(n)))
    F  = np.fft.rfft(f, nf)
    G  = np.fft.rfft(g, nf)
    c_full = np.fft.irfft(F * G, nf)[:n] * DT
    # Centre slice
    mid  = len(c_full) // 2
    half = N_SAMPLES // 2
    c    = c_full[mid - half: mid - half + N_SAMPLES]
    if len(c) < N_SAMPLES:
        c = np.pad(c, (0, N_SAMPLES - len(c)))
    return c


# ─────────────────────────────────────────────────────────────────────────────
# LATEX / EQUATION STRINGS
# ─────────────────────────────────────────────────────────────────────────────
WAVE_LATEX = {
    "Rectangle":     r"\mathrm{rect}\!\left(\frac{t}{w}\right)",
    "Triangle":      r"\Lambda\!\left(\frac{t}{w}\right)",
    "Gaussian":      r"e^{-t^2/(2\sigma^2)}",
    "Sinc":          r"\mathrm{sinc}(ft)",
    "Sawtooth":      r"\mathrm{saw}(t)",
    "Exp. Decay":    r"e^{-t/w}\,u(t)",
    "Unit Step":     r"u(t)",
    "Impulse Train": r"\mathrm{III}(ft)",
    "Custom":        r"f_{\mathrm{custom}}(t)",
}


def latex_conv_definition() -> tuple:
    """Returns (mathtext, latex_str) for the convolution integral definition."""
    mt = (r"$(f * g)(t) = \int_{-\infty}^{\infty}"
          r" f(\tau)\, g(t - \tau)\, d\tau$")
    lt = (r"(f * g)(t) = \int_{-\infty}^{\infty}"
          r" f(\tau)\, g(t - \tau)\, d\tau")
    return mt, lt


def latex_closed_form(f_name: str, g_name: str,
                      f_amp: float, g_amp: float) -> tuple:
    """Returns (mathtext, latex_str) for the current waveform pair."""
    fs = WAVE_LATEX.get(f_name, r"f(t)")
    gs = WAVE_LATEX.get(g_name, r"g(t)")
    A  = f_amp * g_amp
    mt = (r"$(f * g)(t) = \int_{-\infty}^{\infty}"
          + r" \left[" + "{:.2f}".format(f_amp) + r"\cdot " + fs
          + r"\right] \left[" + "{:.2f}".format(g_amp) + r"\cdot " + gs
          + r"\right]_{t-\tau}\, d\tau$")
    lt = (r"(f * g)(t) = \int_{-\infty}^{\infty}"
          + r" \left[{:.2f}\cdot ".format(f_amp) + fs
          + r"\right] \cdot \left[{:.2f}\cdot ".format(g_amp) + gs
          + r"\right]_{t-\tau}\, d\tau")
    return mt, lt


def latex_discrete_approx(dt: float) -> tuple:
    """Returns (mathtext, latex_str) for the discrete approximation."""
    mt = (r"$\approx \sum_{k} f(k\,\Delta\tau)\cdot"
          r" g(t - k\,\Delta\tau)\cdot\Delta\tau"
          + r",\quad \Delta\tau=" + "{:.4f}".format(dt) + r"$")
    lt = (r"\approx \sum_{k} f(k\,\Delta\tau)\cdot"
          r" g(t - k\,\Delta\tau)\cdot\Delta\tau"
          + r", \quad \Delta\tau={:.4f}".format(dt))
    return mt, lt


# ─────────────────────────────────────────────────────────────────────────────
# MATHTEXT CANVAS  — renders a single LaTeX/mathtext expression
# ─────────────────────────────────────────────────────────────────────────────
class MathCanvas(FigureCanvas):
    def __init__(self, height_px: int = 58, fontsize: int = 12, parent=None):
        fig = Figure(figsize=(10, height_px / 100), dpi=100)
        fig.patch.set_facecolor(p("surface2"))
        super().__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(height_px)
        self.setMaximumHeight(height_px)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_axis_off()
        ax.set_facecolor(p("surface2"))
        self._txt = ax.text(0.02, 0.5, "", ha="left", va="center",
                            fontsize=fontsize, color=p("text"),
                            transform=ax.transAxes)

    def set_equation(self, mathtext: str, color: str = None):
        self._txt.set_text(mathtext)
        if color:
            self._txt.set_color(color)
        self.figure.canvas.draw_idle()


# ─────────────────────────────────────────────────────────────────────────────
# EQUATION BLOCK  — header + MathCanvas + copy button
# ─────────────────────────────────────────────────────────────────────────────
class EqBlock(QWidget):
    def __init__(self, title: str, height: int = 58,
                 fontsize: int = 12, parent=None):
        super().__init__(parent)
        self._latex = ""
        self.setStyleSheet("background:" + p("surface2") + "; border-radius:6px;")

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # header
        hdr = QWidget()
        hdr.setFixedHeight(26)
        hdr.setStyleSheet(
            "background:" + p("surface3") + ";"
            "border-radius:6px 6px 0 0;"
            "border-bottom:1px solid " + p("border") + ";"
        )
        hr = QHBoxLayout(hdr)
        hr.setContentsMargins(10, 0, 6, 0)
        lbl = QLabel(title)
        lbl.setStyleSheet(
            "color:" + p("text_muted") + "; font-family:monospace;"
            "font-size:9px; font-weight:bold; letter-spacing:1.2px;"
            "background:transparent; border:none;"
        )
        self._copy_btn = QPushButton("\u2398 Copy LaTeX")
        self._copy_btn.setFixedHeight(18)
        self._copy_btn.setStyleSheet(self._btn_style())
        self._copy_btn.clicked.connect(self._copy)
        hr.addWidget(lbl)
        hr.addStretch()
        hr.addWidget(self._copy_btn)
        v.addWidget(hdr)

        self._canvas = MathCanvas(height_px=height, fontsize=fontsize)
        v.addWidget(self._canvas)

    def update_eq(self, mathtext: str, latex: str, color: str = None):
        self._latex = latex
        self._canvas.set_equation(mathtext, color)

    def _copy(self):
        QApplication.clipboard().setText(self._latex)
        orig = self._copy_btn.text()
        self._copy_btn.setText("\u2713 Copied!")
        self._copy_btn.setStyleSheet(self._btn_style(True))
        QTimer.singleShot(1400, lambda: (
            self._copy_btn.setText(orig),
            self._copy_btn.setStyleSheet(self._btn_style()),
        ))

    def _btn_style(self, success: bool = False) -> str:
        bg  = p("success") if success else p("surface")
        col = p("bg")      if success else p("text_muted")
        brd = p("success") if success else p("border")
        return (
            "QPushButton {"
            "background:" + bg + "; color:" + col + ";"
            "border:1px solid " + brd + "; border-radius:3px;"
            "font-family:monospace; font-size:8px; padding:0 8px;}"
            "QPushButton:hover { background:" + p("surface3") + ";}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# WAVEFORM SELECTOR WIDGET  (tabs + sliders + custom expr entry)
# ─────────────────────────────────────────────────────────────────────────────
class WaveSelector(QWidget):
    """
    Emits waveformChanged(name, amp, width, freq, offset, custom_expr)
    whenever any control changes.
    """
    waveformChanged = Signal(str, float, float, float, float, str)

    def __init__(self, label: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self._label = label
        self._name  = "Rectangle"
        self._custom_expr = "np.exp(-t**2)"

        self.setStyleSheet(
            "background:" + p("surface") + ";"
            "border:1px solid " + p("border") + ";"
            "border-radius:10px;"
        )
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 10)
        v.setSpacing(6)

        # Title
        title = QLabel(label + "   f(\u03c4)  or  g(t\u2212\u03c4)")
        title.setStyleSheet(
            "color:" + color + "; font-family:monospace; font-size:11px;"
            "font-weight:bold; background:transparent; border:none;"
        )
        v.addWidget(title)

        # Waveform dropdown
        row_wave = QHBoxLayout()
        wl = QLabel("Waveform:")
        wl.setStyleSheet(
            "color:" + p("text_muted") + "; font-family:monospace;"
            "font-size:10px; background:transparent; border:none;"
        )
        self._combo = QComboBox()
        self._combo.addItems(WAVEFORMS)
        self._combo.setStyleSheet(self._combo_style())
        self._combo.currentTextChanged.connect(self._on_combo)
        row_wave.addWidget(wl)
        row_wave.addWidget(self._combo, 1)
        v.addLayout(row_wave)

        # Sliders
        self._sl_amp    = self._make_slider("Amplitude", "A",   0.1, 3.0, 1.0, 0.01, "{:.2f}", "")
        self._sl_width  = self._make_slider("Width / \u03c3", "w",   0.1, 3.0, 1.0, 0.01, "{:.2f}", "")
        self._sl_freq   = self._make_slider("Frequency", "f",   0.1, 5.0, 1.0, 0.1,  "{:.1f}", " Hz")
        self._sl_offset = self._make_slider("Offset",    "\u03c4\u2080", -3.0, 3.0, 0.0, 0.05, "{:.2f}", "")
        for sl in (self._sl_amp, self._sl_width, self._sl_freq, self._sl_offset):
            v.addWidget(sl)

        # Custom expression entry
        self._custom_frame = QWidget()
        self._custom_frame.setStyleSheet("background:transparent; border:none;")
        cf_v = QVBoxLayout(self._custom_frame)
        cf_v.setContentsMargins(0, 2, 0, 0)
        cf_v.setSpacing(3)
        cf_lbl = QLabel("Custom f(t) expression  (NumPy, use 't'):")
        cf_lbl.setStyleSheet(
            "color:" + p("text_muted") + "; font-family:monospace; font-size:9px;"
            "background:transparent; border:none;"
        )
        self._expr_edit = QLineEdit(self._custom_expr)
        self._expr_edit.setStyleSheet(self._lineedit_style())
        self._expr_edit.setPlaceholderText("e.g.  np.exp(-t**2) * np.cos(4*np.pi*t)")
        self._expr_edit.returnPressed.connect(self._emit)
        self._expr_edit.textChanged.connect(self._emit)
        cf_v.addWidget(cf_lbl)
        cf_v.addWidget(self._expr_edit)
        self._err_lbl = QLabel("")
        self._err_lbl.setStyleSheet(
            "color:" + p("error") + "; font-family:monospace; font-size:8px;"
            "background:transparent; border:none;"
        )
        cf_v.addWidget(self._err_lbl)
        v.addWidget(self._custom_frame)
        self._custom_frame.setVisible(False)

    # ── helpers ─────────────────────────────────────────────────
    def _make_slider(self, label, sym, mn, mx, default, step, fmt, unit):
        sl = _LabelledSlider(label, sym, mn, mx, default, step, fmt, unit,
                             self._color)
        sl.valueChanged.connect(self._emit)
        return sl

    def _on_combo(self, name):
        self._name = name
        self._custom_frame.setVisible(name == "Custom")
        self._emit()

    def _emit(self, *_):
        expr = self._expr_edit.text().strip()
        self._custom_expr = expr
        # Quick syntax check
        if self._name == "Custom":
            try:
                t_test = np.linspace(-1, 1, 10)
                safe = {"np": np, "sin": np.sin, "cos": np.cos,
                        "exp": np.exp, "sinc": np.sinc, "abs": np.abs,
                        "sqrt": np.sqrt, "pi": math.pi, "e": math.e,
                        "t": t_test}
                eval(expr, {"__builtins__": {}}, safe)
                self._err_lbl.setText("")
            except Exception as ex:
                self._err_lbl.setText("Error: " + str(ex)[:60])
        self.waveformChanged.emit(
            self._name,
            self._sl_amp.get_value(),
            self._sl_width.get_value(),
            self._sl_freq.get_value(),
            self._sl_offset.get_value(),
            self._custom_expr,
        )

    def get_params(self):
        return (self._name,
                self._sl_amp.get_value(),
                self._sl_width.get_value(),
                self._sl_freq.get_value(),
                self._sl_offset.get_value(),
                self._custom_expr)

    def _combo_style(self):
        return (
            "QComboBox { background:" + p("surface2") + "; color:" + p("text") + ";"
            "border:1px solid " + p("border") + "; border-radius:4px;"
            "font-family:monospace; font-size:10px; padding:2px 6px; }"
            "QComboBox::drop-down { border:none; }"
            "QComboBox QAbstractItemView { background:" + p("surface2") + ";"
            "color:" + p("text") + "; selection-background-color:" + p("primary") + "; }"
        )

    def _lineedit_style(self):
        return (
            "QLineEdit { background:" + p("surface2") + "; color:" + p("text") + ";"
            "border:1px solid " + p("border") + "; border-radius:4px;"
            "font-family:monospace; font-size:10px; padding:3px 6px; }"
            "QLineEdit:focus { border-color:" + self._color + "; }"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LABELLED SLIDER
# ─────────────────────────────────────────────────────────────────────────────
class _LabelledSlider(QWidget):
    valueChanged = Signal(float)

    def __init__(self, label, sym, mn, mx, default, step, fmt, unit,
                 color=None, parent=None):
        super().__init__(parent)
        self._mn, self._step = mn, step
        self._steps = round((mx - mn) / step)
        self._fmt, self._unit = fmt, unit
        col = color or p("primary")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)

        hdr = QHBoxLayout()
        lbl_w = QLabel(label + "  ")
        lbl_w.setStyleSheet(
            "color:" + p("text_muted") + "; font-family:monospace;"
            "font-size:10px; background:transparent; border:none;"
        )
        sym_w = QLabel(sym)
        sym_w.setStyleSheet(
            "color:" + p("text_faint") + "; font-family:monospace;"
            "font-size:9px; font-style:italic; background:transparent; border:none;"
        )
        self._val_lbl = QLabel(fmt.format(default) + unit)
        self._val_lbl.setStyleSheet(
            "color:" + p("text") + "; font-family:monospace;"
            "font-size:11px; font-weight:bold; background:transparent; border:none;"
        )
        self._val_lbl.setAlignment(Qt.AlignRight)
        hdr.addWidget(lbl_w)
        hdr.addWidget(sym_w)
        hdr.addStretch()
        hdr.addWidget(self._val_lbl)
        lay.addLayout(hdr)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(self._steps)
        self._slider.setValue(round((default - mn) / step))
        self._slider.setStyleSheet(self._slider_style(col))
        self._slider.valueChanged.connect(self._on_change)
        lay.addWidget(self._slider)

    def _on_change(self, pos):
        v = self._mn + pos * self._step
        self._val_lbl.setText(self._fmt.format(v) + self._unit)
        self.valueChanged.emit(v)

    def get_value(self):
        return self._mn + self._slider.value() * self._step

    def _slider_style(self, col):
        return (
            "QSlider::groove:horizontal {"
            "height:4px; background:" + p("surface3") + ";"
            "border-radius:2px; border:1px solid " + p("border") + ";}"
            "QSlider::sub-page:horizontal { background:" + col + "; border-radius:2px;}"
            "QSlider::handle:horizontal {"
            "background:" + col + "; border:2px solid " + p("bg") + ";"
            "width:14px; height:14px; margin:-5px 0; border-radius:7px;}"
            "QSlider::handle:horizontal:hover { background:white;}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SEGMENTED BUTTON GROUP
# ─────────────────────────────────────────────────────────────────────────────
class SegGroup(QWidget):
    selectionChanged = Signal(str)

    def __init__(self, label, options, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        if label:
            lbl = QLabel(label + ":")
            lbl.setStyleSheet(
                "color:" + p("text_muted") + "; font-size:10px;"
                "font-family:monospace; background:transparent; border:none;"
            )
            row.addWidget(lbl)
            row.addSpacing(6)
        self._btns = {}
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        for i, (key, display) in enumerate(options):
            btn = QPushButton(display)
            btn.setCheckable(True)
            btn.setFixedHeight(22)
            rl = "3px 0 0 3px" if i == 0 else "0"
            rr = "0 3px 3px 0" if i == len(options) - 1 else "0"
            btn.setStyleSheet(
                "QPushButton { background:" + p("surface") + "; color:" + p("text_muted") + ";"
                "border:1px solid " + p("border") + "; padding:0 10px;"
                "font-size:10px; font-family:monospace;"
                "border-radius:" + rl + ";}"
                "QPushButton:checked { background:" + p("primary") + "; color:" + p("bg") + ";"
                "font-weight:bold;}"
                "QPushButton:hover:!checked { background:" + p("surface2") + ";"
                "color:" + p("text") + ";}"
            )
            self._btns[key] = btn
            grp.addButton(btn)
            row.addWidget(btn)
            btn.clicked.connect(lambda _, k=key: self.selectionChanged.emit(k))
        list(self._btns.values())[0].setChecked(True)

    def select(self, key):
        if key in self._btns:
            self._btns[key].setChecked(True)


# ─────────────────────────────────────────────────────────────────────────────
# CHIP / BADGE helper
# ─────────────────────────────────────────────────────────────────────────────
def _make_chip(text, accent=False):
    lbl = QLabel(text)
    col = p("primary") if accent else p("text_muted")
    lbl.setStyleSheet(
        "color:" + col + "; background:" + p("surface3") + ";"
        "border:1px solid " + p("border") + "; border-radius:3px;"
        "font-family:monospace; font-size:9px; padding:1px 6px;"
    )
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# ANIMATION CANVAS
# ─────────────────────────────────────────────────────────────────────────────
class ConvAnimCanvas(FigureCanvas):
    """
    Three-row matplotlib figure:
      Row 0 — f(τ) and g(t−τ) flipped & sliding
      Row 1 — overlap product f(τ)·g(t−τ), filled area
      Row 2 — accumulated convolution result (f*g)(t)
    """

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 7), dpi=100)
        self.fig.patch.set_facecolor(p("bg"))
        self.fig.subplots_adjust(hspace=0.42, left=0.07, right=0.97,
                                 top=0.94, bottom=0.07)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(420)

        self.ax0, self.ax1, self.ax2 = self.fig.subplots(3, 1)
        for ax in (self.ax0, self.ax1, self.ax2):
            self._style_ax(ax)

        # Will be set by update_data
        self._f     = np.zeros(N_SAMPLES)
        self._g     = np.zeros(N_SAMPLES)
        self._conv  = np.zeros(N_SAMPLES)
        self._t_pos = 0.0   # current sliding position
        self._anim  = None
        self._running = False
        self._speed   = 1.0

        self._init_artists()

    def _style_ax(self, ax):
        ax.set_facecolor(p("bg"))
        for sp in ax.spines.values():
            sp.set_color(p("border")); sp.set_linewidth(0.6)
        ax.tick_params(colors=p("text_faint"), labelsize=7, length=3, width=0.5)
        ax.xaxis.label.set_color(p("text_faint"))
        ax.yaxis.label.set_color(p("text_faint"))
        ax.xaxis.label.set_fontsize(8)
        ax.yaxis.label.set_fontsize(8)
        ax.grid(True, color=p("border"), lw=0.4, ls="--", alpha=0.6)

    def _init_artists(self):
        tau = TAU
        # Row 0 — signal traces + sliding indicator
        self._line_f,  = self.ax0.plot(tau, self._f,    color=p("sig_f"),
                                        lw=1.8, label="f(\u03c4)")
        self._line_g,  = self.ax0.plot(tau, self._g,    color=p("sig_g"),
                                        lw=1.8, label="g(t\u2212\u03c4)", ls="--")
        self._vline0   = self.ax0.axvline(0, color=p("sig_conv"),
                                          lw=1.2, ls=":", alpha=0.8)
        self.ax0.legend(loc="upper right", fontsize=7,
                        facecolor=p("surface"), edgecolor=p("border"),
                        labelcolor=p("text_muted"))
        self.ax0.set_ylabel("Amplitude", fontsize=8)
        self.ax0.set_title("f(\u03c4)  and  g(t\u2212\u03c4)  sliding",
                           color=p("text_muted"), fontsize=9, pad=4)

        # Row 1 — product overlap
        self._line_prod, = self.ax1.plot(tau, np.zeros(N_SAMPLES),
                                          color=p("sig_area"), lw=1.5)
        self._fill_prod   = self.ax1.fill_between(
            tau, np.zeros(N_SAMPLES), np.zeros(N_SAMPLES),
            color=p("sig_area"), alpha=0.28)
        self._vline1 = self.ax1.axvline(0, color=p("sig_conv"),
                                        lw=1.2, ls=":", alpha=0.8)
        self.ax1.set_ylabel("Product", fontsize=8)
        self.ax1.set_title("f(\u03c4)\u00b7g(t\u2212\u03c4)  — integration area",
                           color=p("text_muted"), fontsize=9, pad=4)

        # Row 2 — convolution accumulation
        self._line_conv, = self.ax2.plot(tau, self._conv,
                                          color=p("sig_conv"), lw=2.0)
        self._dot_conv,  = self.ax2.plot([], [], "o",
                                          color=p("sig_conv"), ms=5, zorder=5)
        self._vline2 = self.ax2.axvline(0, color=p("sig_conv"),
                                        lw=1.2, ls=":", alpha=0.8)
        self.ax2.set_ylabel("(f\u2217g)(t)", fontsize=8)
        self.ax2.set_xlabel("\u03c4 / t", fontsize=8)
        self.ax2.set_title("Convolution  (f\u2217g)(t) — running result",
                           color=p("text_muted"), fontsize=9, pad=4)

        for ax in (self.ax0, self.ax1, self.ax2):
            ax.set_xlim(-T_RANGE, T_RANGE)

    # ── public API ───────────────────────────────────────────────
    def update_data(self, f: np.ndarray, g: np.ndarray, conv: np.ndarray):
        self._f    = f
        self._g    = g
        self._conv = conv
        self._draw_static()

    def _draw_static(self):
        """Redraw static traces (called when data changes or animation is off)."""
        f, g, c = self._f, self._g, self._conv

        self._line_f.set_ydata(f)
        self._line_g.set_ydata(g)   # show unflipped g as reference
        prod = f * g
        self._line_prod.set_ydata(prod)

        # Rebuild fill (can't update in place easily — remove + re-add)
        self._fill_prod.remove()
        self._fill_prod = self.ax1.fill_between(
            TAU, prod, np.zeros_like(prod),
            color=p("sig_area"), alpha=0.28)

        self._line_conv.set_ydata(c)
        self._dot_conv.set_data([], [])

        # Auto-scale Y
        for ax, data in ((self.ax0, np.concatenate([f, g])),
                          (self.ax1, prod),
                          (self.ax2, c)):
            if data.size and np.any(np.isfinite(data)):
                mx = max(np.nanmax(np.abs(data)) * 1.25, 0.1)
                ax.set_ylim(-mx, mx)

        self.draw_idle()

    def start_animation(self, speed: float = 1.0):
        """Start the sliding convolution animation."""
        self._speed = speed
        if self._anim is not None:
            self._anim.event_source.stop()
        self._frame_idx = [0]
        n_frames = N_SAMPLES
        interval = max(1, int(40 / max(speed, 0.1)))

        def _update(frame):
            idx = self._frame_idx[0]
            if idx >= N_SAMPLES:
                self._frame_idx[0] = 0
                idx = 0
            t_val = TAU[idx]

            # g flipped and shifted to t_val: g(t_val - τ) = g(-(τ - t_val))
            g_shifted = np.interp(t_val - TAU, TAU, self._g,
                                  left=0.0, right=0.0)

            self._line_g.set_ydata(g_shifted)
            self._vline0.set_xdata([t_val, t_val])
            self._vline1.set_xdata([t_val, t_val])
            self._vline2.set_xdata([t_val, t_val])

            prod = self._f * g_shifted
            self._line_prod.set_ydata(prod)
            self._fill_prod.remove()
            self._fill_prod = self.ax1.fill_between(
                TAU, prod, np.zeros_like(prod),
                color=p("sig_area"), alpha=0.28)

            # Show convolution result up to current t
            c_partial = self._conv.copy()
            c_partial[idx + 1:] = np.nan
            self._line_conv.set_ydata(c_partial)
            self._dot_conv.set_data([t_val], [self._conv[idx]])

            self._frame_idx[0] = idx + max(1, int(speed * 3))
            return (self._line_f, self._line_g, self._line_prod,
                    self._line_conv, self._dot_conv,
                    self._vline0, self._vline1, self._vline2)

        self._anim = FuncAnimation(
            self.fig, _update,
            frames=N_SAMPLES,
            interval=interval,
            blit=False,
            repeat=True,
        )
        self._running = True
        self.draw_idle()

    def stop_animation(self):
        if self._anim is not None:
            self._anim.event_source.stop()
            self._anim = None
        self._running = False
        self._draw_static()

    def reset_animation(self):
        self.stop_animation()
        self._draw_static()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convolution Visualizer")
        self.resize(1440, 980)
        self._apply_palette()
        self._build_ui()
        self._update()

    # ── Qt palette ──────────────────────────────────────────────
    def _apply_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor(p("bg")))
        pal.setColor(QPalette.WindowText,      QColor(p("text")))
        pal.setColor(QPalette.Base,            QColor(p("surface")))
        pal.setColor(QPalette.AlternateBase,   QColor(p("surface2")))
        pal.setColor(QPalette.Text,            QColor(p("text")))
        pal.setColor(QPalette.Button,          QColor(p("surface")))
        pal.setColor(QPalette.ButtonText,      QColor(p("text")))
        pal.setColor(QPalette.Highlight,       QColor(p("primary")))
        pal.setColor(QPalette.HighlightedText, QColor(p("bg")))
        QApplication.setPalette(pal)
        QApplication.setStyle("Fusion")

    # ── UI assembly ──────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet("background:" + p("bg") + ";")
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(12, 8, 12, 12)
        vbox.setSpacing(8)

        vbox.addWidget(self._make_title_bar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background:transparent; width:6px;}")
        vbox.addWidget(splitter, stretch=1)

        # Left column: waveform selectors
        left = QWidget()
        left.setFixedWidth(380)
        left.setStyleSheet("background:" + p("bg") + ";")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)

        self._sel_f = WaveSelector("Signal  f", p("sig_f"))
        self._sel_g = WaveSelector("Signal  g", p("sig_g"))
        self._sel_f.waveformChanged.connect(lambda *_: self._update())
        self._sel_g.waveformChanged.connect(lambda *_: self._update())
        lv.addWidget(self._sel_f)
        lv.addWidget(self._sel_g)
        lv.addWidget(self._make_playback_controls())
        lv.addStretch()
        splitter.addWidget(left)

        # Right column: animation + equation panel
        right = QWidget()
        right.setStyleSheet("background:" + p("bg") + ";")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(8)

        self._anim_canvas = ConvAnimCanvas()
        rv.addWidget(self._wrap_panel("CONVOLUTION ANIMATION", self._anim_canvas))

        # Equation scroll area
        eq_scroll = QScrollArea()
        eq_scroll.setWidgetResizable(True)
        eq_scroll.setFixedHeight(310)
        eq_scroll.setStyleSheet(
            "background:" + p("bg") + "; border:none;"
        )
        eq_scroll.setWidget(self._make_equation_panel())
        rv.addWidget(eq_scroll)

        splitter.addWidget(right)
        splitter.setSizes([380, 1060])

    # ── Title bar ────────────────────────────────────────────────
    def _make_title_bar(self):
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            "background:" + p("surface") + "; border-radius:8px;"
            "border:1px solid " + p("border") + ";"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 0, 14, 0)
        title = QLabel("\u25a0 Convolution Visualizer")
        title.setStyleSheet(
            "color:" + p("text") + "; font-family:monospace;"
            "font-size:14px; font-weight:bold; background:transparent; border:none;"
        )
        import qtpy
        sub = QLabel(
            "Sliding Integral Animation  \u00b7  "
            "qtpy " + qtpy.__version__ + " / " + qtpy.API_NAME + " / Matplotlib"
        )
        sub.setStyleSheet(
            "color:" + p("text_faint") + "; font-family:monospace;"
            "font-size:10px; background:transparent; border:none;"
        )
        self._chip_result = _make_chip("(f\u2217g)(t\u2080) = 0.000", accent=True)
        row.addWidget(title)
        row.addSpacing(16)
        row.addWidget(sub)
        row.addStretch()
        row.addWidget(self._chip_result)
        return bar

    # ── Playback controls ────────────────────────────────────────
    def _make_playback_controls(self):
        box = QWidget()
        box.setStyleSheet(
            "background:" + p("surface") + "; border-radius:10px;"
            "border:1px solid " + p("border") + ";"
        )
        v = QVBoxLayout(box)
        v.setContentsMargins(12, 8, 12, 10)
        v.setSpacing(8)

        # Header
        hdr_lbl = QLabel("ANIMATION CONTROLS")
        hdr_lbl.setStyleSheet(
            "color:" + p("text_muted") + "; font-family:monospace;"
            "font-size:9px; font-weight:bold; letter-spacing:1.5px;"
            "background:transparent; border:none;"
        )
        v.addWidget(hdr_lbl)

        # Play / Pause / Reset buttons
        btn_row = QHBoxLayout()
        self._btn_play  = QPushButton("\u25b6  Play")
        self._btn_pause = QPushButton("\u23f8  Pause")
        self._btn_reset = QPushButton("\u23f9  Reset")
        for btn in (self._btn_play, self._btn_pause, self._btn_reset):
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { background:" + p("surface2") + "; color:" + p("text") + ";"
                "border:1px solid " + p("border") + "; border-radius:5px;"
                "font-family:monospace; font-size:10px; font-weight:bold; padding:0 10px;}"
                "QPushButton:hover { background:" + p("surface3") + ";}"
                "QPushButton:pressed { background:" + p("primary") + "; color:" + p("bg") + ";}"
            )
        self._btn_play.clicked.connect(self._play)
        self._btn_pause.clicked.connect(self._pause)
        self._btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(self._btn_play)
        btn_row.addWidget(self._btn_pause)
        btn_row.addWidget(self._btn_reset)
        v.addLayout(btn_row)

        # Speed slider
        self._sl_speed = _LabelledSlider("Speed", "v", 0.1, 5.0, 1.0, 0.1,
                                          "{:.1f}", "x", p("accent"))
        v.addWidget(self._sl_speed)

        # Loop toggle
        self._chk_loop = QCheckBox("Loop animation")
        self._chk_loop.setChecked(True)
        self._chk_loop.setStyleSheet(
            "QCheckBox { color:" + p("text_muted") + "; font-family:monospace;"
            "font-size:10px; background:transparent; border:none;}"
            "QCheckBox::indicator { width:13px; height:13px;"
            "border:1px solid " + p("border") + "; border-radius:3px;"
            "background:" + p("surface2") + ";}"
            "QCheckBox::indicator:checked { background:" + p("primary") + ";}"
        )
        v.addWidget(self._chk_loop)

        return box

    # ── Panel wrapper ────────────────────────────────────────────
    def _wrap_panel(self, title, widget):
        panel = QWidget()
        panel.setStyleSheet(
            "background:" + p("surface") + "; border-radius:10px;"
            "border:1px solid " + p("border") + ";"
        )
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            "background:" + p("surface2") + "; border-bottom:1px solid " + p("border") + ";"
            "border-top-left-radius:10px; border-top-right-radius:10px;"
        )
        hr = QHBoxLayout(hdr)
        hr.setContentsMargins(14, 0, 14, 0)
        tl = QLabel(title)
        tl.setStyleSheet(
            "color:" + p("text_muted") + "; font-family:monospace;"
            "font-size:9px; font-weight:bold; letter-spacing:1.5px;"
            "background:transparent; border:none;"
        )
        hr.addWidget(tl)
        hr.addStretch()
        v.addWidget(hdr)
        cw = QWidget()
        cw.setStyleSheet("background:" + p("bg") + "; border:none;")
        cl = QVBoxLayout(cw)
        cl.setContentsMargins(8, 6, 8, 6)
        cl.addWidget(widget)
        v.addWidget(cw)
        return panel

    # ── Equation panel ───────────────────────────────────────────
    def _make_equation_panel(self):
        panel = QWidget()
        panel.setStyleSheet(
            "background:" + p("surface") + "; border-radius:10px;"
            "border:1px solid " + p("border") + ";"
        )
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            "background:" + p("surface2") + "; border-bottom:1px solid " + p("border") + ";"
            "border-top-left-radius:10px; border-top-right-radius:10px;"
        )
        hr = QHBoxLayout(hdr)
        hr.setContentsMargins(14, 0, 14, 0)
        tl = QLabel("LIVE CONVOLUTION EQUATIONS")
        tl.setStyleSheet(
            "color:" + p("text_muted") + "; font-family:monospace;"
            "font-size:10px; font-weight:bold; letter-spacing:1.5px;"
            "background:transparent; border:none;"
        )
        self._badge_pair = _make_chip("rect \u2217 rect")
        hr.addWidget(tl); hr.addStretch(); hr.addWidget(self._badge_pair)
        v.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet("background:" + p("surface") + "; border:none;")
        bv = QVBoxLayout(body)
        bv.setContentsMargins(12, 10, 12, 12)
        bv.setSpacing(8)

        self._blk_def     = EqBlock("Convolution Integral Definition",   height=60, fontsize=12)
        self._blk_form    = EqBlock("Current Waveform Pair — Live Form", height=64, fontsize=11)
        self._blk_approx  = EqBlock("Discrete Approximation",           height=56, fontsize=11)

        bv.addWidget(self._blk_def)
        bv.addWidget(self._blk_form)
        bv.addWidget(self._blk_approx)
        v.addWidget(body)
        return panel

    # ── Slots ─────────────────────────────────────────────────────
    def _play(self):
        speed = self._sl_speed.get_value()
        self._anim_canvas.start_animation(speed)

    def _pause(self):
        if self._anim_canvas._anim is not None:
            self._anim_canvas._anim.event_source.stop()

    def _reset(self):
        self._anim_canvas.reset_animation()

    # ── Main update ───────────────────────────────────────────────
    def _update(self):
        # Build waveforms
        f_params = self._sel_f.get_params()
        g_params = self._sel_g.get_params()

        f = make_waveform(*f_params)
        g = make_waveform(*g_params)
        conv = compute_convolution(f, g)

        # Update animation canvas
        was_running = self._anim_canvas._running
        self._anim_canvas.update_data(f, g, conv)
        if was_running:
            self._anim_canvas.start_animation(self._sl_speed.get_value())

        # Metrics chip
        peak = np.nanmax(np.abs(conv)) if np.any(np.isfinite(conv)) else 0.0
        self._chip_result.setText(
            "peak (f\u2217g) = " + "{:.3f}".format(peak)
        )

        # Equation panel
        f_name, f_amp = f_params[0], f_params[1]
        g_name, g_amp = g_params[0], g_params[1]

        mt_def, lt_def = latex_conv_definition()
        self._blk_def.update_eq(mt_def, lt_def)

        mt_form, lt_form = latex_closed_form(f_name, g_name, f_amp, g_amp)
        self._blk_form.update_eq(mt_form, lt_form, color=p("sig_conv"))

        mt_approx, lt_approx = latex_discrete_approx(DT)
        self._blk_approx.update_eq(mt_approx, lt_approx)

        self._badge_pair.setText(f_name + " \u2217 " + g_name)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    import os
    os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")
    app = QApplication(sys.argv)
    app.setApplicationName("Convolution Visualizer")
    QFontDatabase.addApplicationFont("JetBrainsMono-Regular.ttf")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
