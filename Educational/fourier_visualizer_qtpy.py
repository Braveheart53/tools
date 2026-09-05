#!/usr/bin/env python3
"""
Fourier Spectrum Visualizer — qtpy / Python 3.8+
=================================================
Waveforms : Square (odd), Sawtooth (odd+even),
            Half-Wave Symmetric (odd only),
            Full-Wave Rectified (even + DC)

Equation panel
  • General / closed-form  — rendered with matplotlib mathtext
  • Expanded series        — every term live, colour-coded HTML
  • Integral form          — aₙ / bₙ coefficient integrals, rendered mathtext
  • LaTeX copy buttons     — one per block, copies LaTeX string to clipboard

Dependencies:
    pip install qtpy PyQt5   # or PyQt6 / PySide2 / PySide6
    pip install matplotlib numpy

    qtpy auto-selects whichever Qt binding is installed.
    Override with:  QT_API=pyqt6 python fourier_visualizer_qtpy.py
"""

import sys
import math
import numpy as np

from qtpy.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QSlider, QPushButton, QButtonGroup,
    QGroupBox, QSplitter, QSizePolicy, QTableWidget, QTableWidgetItem,
    QScrollArea, QFrame, QAbstractItemView, QHeaderView, QToolTip,
)
from qtpy.QtCore import Qt, QTimer, Signal
from qtpy.QtGui import QFont, QColor, QPalette, QFontDatabase

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure
import matplotlib.ticker as mticker
import matplotlib.patheffects as pe

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR PALETTE  (oscilloscope dark theme)
# ─────────────────────────────────────────────────────────────────────────────
PAL = {
    "bg":          "#0e1117",
    "surface":     "#141820",
    "surface2":    "#1a1f2e",
    "surface3":    "#1f2535",
    "border":      "#2a3040",
    "border_hi":   "#3a4560",
    "text":        "#d4dbe8",
    "text_muted":  "#7a8599",
    "text_faint":  "#3d4558",
    "primary":     "#4fa3c8",
    "accent":      "#56e0b8",
    "warn":        "#f0b040",
    "error":       "#e05060",
    "success":     "#56c87a",
    "square":      "#4fa3c8",
    "sawtooth":    "#f0b040",
    "halfwave":    "#56e0b8",
    "fullwave":    "#c87af0",
}


# ─────────────────────────────────────────────────────────────────────────────
# FOURIER ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def get_coefficients(wave: str, N: int, amplitude: float,
                     duty: float, phase_deg: float) -> list:
    A, d, phi = amplitude, duty, phase_deg
    terms = []

    if wave == "square":
        dc = A * (2 * d - 1)
        if abs(dc) > 1e-9:
            terms.append({"n": 0, "An": dc, "phase_deg": 0.0, "type": "dc"})
        for n in range(1, N + 1):
            raw = (2 * A / (n * math.pi)) * math.sin(n * math.pi * d)
            if abs(raw) < 1e-12:
                continue
            terms.append({"n": n, "An": abs(raw),
                          "phase_deg": phi if raw >= 0 else phi + 180.0,
                          "type": "odd" if n % 2 else "even"})

    elif wave == "sawtooth":
        for n in range(1, N + 1):
            raw = ((-1) ** (n + 1)) * (2 * A) / (n * math.pi)
            terms.append({"n": n, "An": abs(raw),
                          "phase_deg": phi if raw >= 0 else phi + 180.0,
                          "type": "odd" if n % 2 else "even"})

    elif wave == "halfwave":
        for n in range(1, N + 1):
            if n % 2 == 0:
                continue
            terms.append({"n": n, "An": (4 * A) / (n * math.pi),
                          "phase_deg": phi, "type": "odd"})

    elif wave == "fullwave":
        terms.append({"n": 0, "An": (2 * A) / math.pi,
                      "phase_deg": 0.0, "type": "dc"})
        idx = 0
        for n in range(2, (N + 1) * 2 + 1, 2):
            idx += 1
            if idx > N:
                break
            terms.append({"n": n, "An": abs((4 * A) / (math.pi * (n*n - 1))),
                          "phase_deg": phi + 180.0, "type": "even"})
    return terms


def sample_wave(wave, t, N, amplitude, duty, phase_deg):
    y = np.zeros_like(t)
    for term in get_coefficients(wave, N, amplitude, duty, phase_deg):
        p = math.radians(term["phase_deg"])
        if term["n"] == 0:
            y += term["An"]
        else:
            y += term["An"] * np.sin(2 * math.pi * term["n"] * t + p)
    return y


def compute_thd(terms):
    fund = next((t["An"] for t in terms if t["n"] == 1), None)
    if not fund:
        return 0.0
    return math.sqrt(sum(t["An"]**2 for t in terms if t["n"] >= 2)) / fund * 100.0


def compute_rms(terms):
    dc = next((t["An"] for t in terms if t["n"] == 0), 0.0)
    return math.sqrt(dc**2 + sum(t["An"]**2 / 2 for t in terms if t["n"] > 0))


# ─────────────────────────────────────────────────────────────────────────────
# LATEX STRING GENERATORS
#   Returns (display_mathtext, latex_for_clipboard) for each form
# ─────────────────────────────────────────────────────────────────────────────
def latex_general(wave: str, amplitude: float, duty: float,
                  phase_deg: float) -> tuple:
    """Returns (mathtext_str, latex_str) for the general / closed form."""
    A  = amplitude
    d  = duty
    _ph_deg = int(round(phase_deg))
    ph = (" + " + str(_ph_deg) + "^{\\circ}") if phase_deg else ""

    if wave == "square":
        dc   = A * (2 * d - 1)
        dc_s = (f"\\frac{{{dc:+.3f}}}{{1}} + " if abs(dc) > 1e-9 else "")
        mt = (
            r"$f(t) = " + dc_s +
            r"\frac{2A}{\pi}\sum_{n=1,3,5}^{N}"
            r"\frac{\sin(n\pi\delta)}{n}\sin\!\left(2\pi n f_0 t" + ph + r"\right)"
            r"\quad A=" + f"{A:.2f}" + r"\,\mathrm{V},\;\delta=" + f"{d*100:.0f}" + r"\%$"
        )
        lt = (
            r"f(t) = " + (f"{dc:+.3f} + " if abs(dc) > 1e-9 else "") +
            r"\frac{2A}{\pi}\sum_{n=1,3,5}^{N}\frac{\sin(n\pi\delta)}{n}"
            r"\sin\!\left(2\pi n f_0 t" + ph + r"\right)"
        )
    elif wave == "sawtooth":
        mt = (
            r"$f(t) = \frac{2A}{\pi}\sum_{n=1}^{N}"
            r"\frac{(-1)^{n+1}}{n}\sin\!\left(2\pi n f_0 t" + ph + r"\right)"
            r"\quad A=" + f"{A:.2f}" + r"\,\mathrm{V}$"
        )
        lt = (
            r"f(t) = \frac{2A}{\pi}\sum_{n=1}^{N}"
            r"\frac{(-1)^{n+1}}{n}\sin\!\left(2\pi n f_0 t" + ph + r"\right)"
        )
    elif wave == "halfwave":
        mt = (
            r"$f(t) = \frac{4A}{\pi}\sum_{n=1,3,5}^{N}"
            r"\frac{1}{n}\sin\!\left(2\pi n f_0 t" + ph + r"\right)"
            r"\quad A=" + f"{A:.2f}" + r"\,\mathrm{V}$"
        )
        lt = (
            r"f(t) = \frac{4A}{\pi}\sum_{n=1,3,5}^{N}"
            r"\frac{1}{n}\sin\!\left(2\pi n f_0 t" + ph + r"\right)"
        )
    else:  # fullwave
        dc_val = (2 * A) / math.pi
        mt = (
            r"$f(t) = \frac{2A}{\pi} + \sum_{n=2,4,6}^{N}"
            r"\frac{-4A}{\pi(n^2-1)}\cos\!\left(2\pi n f_0 t" + ph + r"\right)"
            r"\quad A=" + f"{A:.2f}" + r"\,\mathrm{V}$"
        )
        lt = (
            r"f(t) = \frac{2A}{\pi} + \sum_{n=2,4,6}^{N}"
            r"\frac{-4A}{\pi(n^2-1)}\cos\!\left(2\pi n f_0 t" + ph + r"\right)"
        )
    return mt, lt


def latex_expanded(wave: str, terms: list, phase_deg: float) -> tuple:
    """Returns (mathtext_str, latex_str) for the expanded numeric series."""
    non_dc  = [t for t in terms if t["n"] > 0]
    dc_term = next((t for t in terms if t["n"] == 0), None)
    fund_An = non_dc[0]["An"] if non_dc else 1.0

    parts_lt = []
    if dc_term and abs(dc_term["An"]) > 1e-9:
        parts_lt.append(f"{dc_term['An']:.4f}")

    SHOW = min(len(non_dc), 12)
    for i, term in enumerate(non_dc[:SHOW]):
        n, An, phi = term["n"], term["An"], term["phase_deg"]
        arg = f"2\\pi" + ("" if n == 1 else f" \\cdot {n}") + " f_0 t"
        if phi:
            arg += " + " + str(int(round(phi))) + "^{\\circ}"
        parts_lt.append(f"{An:.5f}\\sin\\!\\left({arg}\\right)")

    if len(non_dc) > SHOW:
        parts_lt.append(f"\\cdots \\;({len(non_dc)-SHOW}\\text{{ more}})")

    lt = "f(t) = " + " + ".join(parts_lt)

    # Mathtext is just the first few terms (can't fit all in one line)
    SHOW_MT = min(len(non_dc), 5)
    mt_parts = []
    if dc_term and abs(dc_term["An"]) > 1e-9:
        mt_parts.append(f"{dc_term['An']:.4f}")
    for term in non_dc[:SHOW_MT]:
        n, An = term["n"], term["An"]
        arg = "f_0 t" if n == 1 else f"{n}f_0 t"
        mt_parts.append(f"{An:.4f}\\sin(2\\pi {arg})")
    if len(non_dc) > SHOW_MT:
        mt_parts.append(r"\cdots")
    mt = "$f(t) = " + " + ".join(mt_parts) + "$"
    return mt, lt


def latex_integral(wave: str, amplitude: float, duty: float) -> tuple:
    """Returns (mathtext_str, latex_str) for the Fourier coefficient integrals."""
    A, d = amplitude, duty

    # General Fourier coefficient integrals (always valid)
    base_mt = (
        r"$a_n = \frac{2}{T}\!\int_{0}^{T}\!f(t)\cos\!\left(\frac{2\pi n t}{T}\right)dt"
        r",\quad"
        r"b_n = \frac{2}{T}\!\int_{0}^{T}\!f(t)\sin\!\left(\frac{2\pi n t}{T}\right)dt$"
    )
    base_lt = (
        r"a_n = \frac{2}{T}\int_{0}^{T} f(t)\cos\!\left(\frac{2\pi n t}{T}\right)dt, \quad"
        r"b_n = \frac{2}{T}\int_{0}^{T} f(t)\sin\!\left(\frac{2\pi n t}{T}\right)dt"
    )

    # Waveform-specific solved form
    if wave == "square":
        dc = A * (2 * d - 1)
        mt2 = (
            r"$b_n = \frac{2A}{n\pi}\sin(n\pi\delta)"
            + (r",\quad a_0 = A(2\delta - 1) = " + f"{dc:.3f}" + r"\,\mathrm{V}" if abs(dc) > 1e-9 else "")
            + r",\quad a_n = 0$"
        )
        lt2 = (
            r"b_n = \frac{2A}{n\pi}\sin(n\pi\delta), \quad a_n = 0"
            + (r", \quad a_0 = A(2\delta-1)" if abs(dc) > 1e-9 else "")
        )
    elif wave == "sawtooth":
        mt2 = (
            r"$b_n = \frac{(-1)^{n+1} \cdot 2A}{n\pi},\quad a_n = 0$"
        )
        lt2 = r"b_n = \frac{(-1)^{n+1} \cdot 2A}{n\pi}, \quad a_n = 0"
    elif wave == "halfwave":
        mt2 = (
            r"$b_n = \frac{4A}{n\pi}\;(n\;\mathrm{odd}),\quad b_n = 0\;(n\;\mathrm{even}),"
            r"\quad a_n = 0$"
        )
        lt2 = (
            r"b_n = \frac{4A}{n\pi}\;(n\;\text{odd}),\quad "
            r"b_n = 0\;(n\;\text{even}),\quad a_n = 0"
        )
    else:  # fullwave
        dc_val = (2 * A) / math.pi
        mt2 = (
            r"$a_0 = \frac{2A}{\pi} = " + f"{dc_val:.4f}" + r"\,\mathrm{V},"
            r"\quad a_n = \frac{-4A}{\pi(n^2-1)}\;(n\;\mathrm{even}),"
            r"\quad b_n = 0$"
        )
        lt2 = (
            r"a_0 = \frac{2A}{\pi},\quad "
            r"a_n = \frac{-4A}{\pi(n^2-1)}\;(n\;\text{even}),\quad b_n = 0"
        )

    # Combined multiline for display: base integral definition + solved result
    mt_combined = base_mt  # show just the definition in the pretty canvas
    lt_combined = base_lt + "\n\n% Solved coefficients:\n" + lt2
    return mt_combined, lt_combined, mt2, lt2


# ─────────────────────────────────────────────────────────────────────────────
# MATHTEXT CANVAS  — renders a single LaTeX/mathtext string as a mini figure
# ─────────────────────────────────────────────────────────────────────────────
class MathCanvas(FigureCanvas):
    """Renders a single mathtext expression on a dark background."""

    def __init__(self, height_px: int = 56, fontsize: int = 13, parent=None):
        self._fontsize = fontsize
        self._height_px = height_px
        fig = Figure(figsize=(10, height_px / 100), dpi=100)
        fig.patch.set_facecolor(PAL["surface2"])
        super().__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(height_px)
        self.setMaximumHeight(height_px)
        self._ax = fig.add_axes([0, 0, 1, 1])
        self._ax.set_axis_off()
        self._ax.set_facecolor(PAL["surface2"])
        self._text_obj = self._ax.text(
            0.02, 0.5, "",
            ha="left", va="center",
            fontsize=self._fontsize,
            color=PAL["text"],
            transform=self._ax.transAxes,
            wrap=False,
        )

    def set_equation(self, mathtext: str, color: str = PAL["text"]):
        self._text_obj.set_text(mathtext)
        self._text_obj.set_color(color)
        self.figure.canvas.draw_idle()

    def set_wave_color(self, color: str):
        self._text_obj.set_color(color)
        self.figure.canvas.draw_idle()


# ─────────────────────────────────────────────────────────────────────────────
# EQUATION BLOCK  — label + mathtext canvas + copy button in one row
# ─────────────────────────────────────────────────────────────────────────────
class EqBlock(QWidget):
    """
    A titled equation row containing:
      [section label]  [MathCanvas (pretty-print)]  [copy LaTeX button]
    """
    def __init__(self, section_title: str, canvas_height: int = 58,
                 fontsize: int = 13, parent=None):
        super().__init__(parent)
        self._latex_str = ""
        self.setStyleSheet(f"background:{PAL['surface2']}; border-radius:6px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── row header: title + copy button ──────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(26)
        hdr.setStyleSheet(
            f"background:{PAL['surface3']}; border-radius:6px 6px 0 0;"
            f"border-bottom:1px solid {PAL['border']};"
        )
        hdr_row = QHBoxLayout(hdr)
        hdr_row.setContentsMargins(10, 0, 6, 0)
        hdr_row.setSpacing(6)

        self._title_lbl = QLabel(section_title)
        self._title_lbl.setStyleSheet(
            f"color:{PAL['text_muted']}; font-family:monospace; font-size:9px;"
            f"font-weight:bold; letter-spacing:1.2px; text-transform:uppercase;"
            f"background:transparent; border:none;"
        )
        self._copy_btn = QPushButton("⎘ Copy LaTeX")
        self._copy_btn.setFixedHeight(18)
        self._copy_btn.setStyleSheet(self._copy_btn_style())
        self._copy_btn.clicked.connect(self._copy_latex)

        hdr_row.addWidget(self._title_lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(self._copy_btn)
        outer.addWidget(hdr)

        # ── math canvas ───────────────────────────────────────────────────────
        self._canvas = MathCanvas(height_px=canvas_height, fontsize=fontsize)
        outer.addWidget(self._canvas)

    def update_eq(self, mathtext: str, latex_str: str, wave_color: str = PAL["text"]):
        self._latex_str = latex_str
        self._canvas.set_equation(mathtext, color=wave_color)

    def _copy_latex(self):
        cb = QApplication.clipboard()
        cb.setText(self._latex_str)
        # Brief visual feedback
        orig = self._copy_btn.text()
        self._copy_btn.setText("✓ Copied!")
        self._copy_btn.setStyleSheet(self._copy_btn_style(success=True))
        QTimer.singleShot(1400, lambda: (
            self._copy_btn.setText(orig),
            self._copy_btn.setStyleSheet(self._copy_btn_style()),
        ))

    def _copy_btn_style(self, success: bool = False) -> str:
        bg  = PAL["success"] if success else PAL["surface"]
        col = PAL["bg"]      if success else PAL["text_muted"]
        brd = PAL["success"] if success else PAL["border"]
        return (
            f"QPushButton {{"
            f"  background:{bg}; color:{col}; border:1px solid {brd};"
            f"  border-radius:3px; font-family:monospace; font-size:8px;"
            f"  padding:0 8px;"
            f"}}"
            f"QPushButton:hover:!checked {{ background:{PAL['surface3']}; color:{PAL['text']}; }}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# EXPANDED SERIES BLOCK  — HTML scrollable + copy button
# ─────────────────────────────────────────────────────────────────────────────
class ExpandedSeriesBlock(QWidget):
    """Scrollable HTML expanded series + copy LaTeX button."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._latex_str = ""
        self.setStyleSheet(f"background:{PAL['surface2']}; border-radius:6px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(26)
        hdr.setStyleSheet(
            f"background:{PAL['surface3']}; border-radius:6px 6px 0 0;"
            f"border-bottom:1px solid {PAL['border']};"
        )
        hdr_row = QHBoxLayout(hdr)
        hdr_row.setContentsMargins(10, 0, 6, 0)
        lbl = QLabel("EXPANDED SERIES — EVERY TERM (LIVE)")
        lbl.setStyleSheet(
            f"color:{PAL['text_muted']}; font-family:monospace; font-size:9px;"
            f"font-weight:bold; letter-spacing:1.2px; background:transparent; border:none;"
        )
        self._copy_btn = QPushButton("⎘ Copy LaTeX")
        self._copy_btn.setFixedHeight(18)
        self._copy_btn.setStyleSheet(self._copy_btn_style())
        self._copy_btn.clicked.connect(self._copy_latex)
        hdr_row.addWidget(lbl)
        hdr_row.addStretch()
        hdr_row.addWidget(self._copy_btn)
        outer.addWidget(hdr)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(78)
        scroll.setStyleSheet(
            f"background:{PAL['surface2']}; border:none; border-radius:0 0 6px 6px;"
        )
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._eq_lbl = QLabel()
        self._eq_lbl.setTextFormat(Qt.RichText)
        self._eq_lbl.setWordWrap(False)
        self._eq_lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._eq_lbl.setStyleSheet(
            f"background:{PAL['surface2']}; color:{PAL['text']};"
            f"font-family:monospace; font-size:12px; padding:8px 12px; border:none;"
        )
        scroll.setWidget(self._eq_lbl)
        outer.addWidget(scroll)

    def update_series(self, terms: list, wave: str, phase_deg: float,
                      latex_str: str):
        self._latex_str = latex_str
        wave_col = PAL.get(wave, PAL["primary"])
        non_dc   = [t for t in terms if t["n"] > 0]
        dc_term  = next((t for t in terms if t["n"] == 0), None)
        fund_An  = non_dc[0]["An"] if non_dc else 1.0

        parts = [
            f"<span style='color:{wave_col}; font-weight:bold;'>f(t)</span>"
            f"<span style='color:{PAL['text_muted']}'> = </span>"
        ]
        if dc_term and abs(dc_term["An"]) > 1e-9:
            parts.append(
                f"<span style='color:{PAL['accent']}; font-weight:bold;'>"
                f"{dc_term['An']:.4f}</span>"
                f"<span style='color:{PAL['text_muted']}'> + </span>"
            )

        SHOW = min(len(non_dc), 20)
        for i, term in enumerate(non_dc[:SHOW]):
            n, An, phi = term["n"], term["An"], term["phase_deg"]
            col   = (wave_col if n == 1
                     else PAL["warn"] if term["type"] == "even"
                     else PAL["primary"])
            fade  = "opacity:0.32;" if An < fund_An * 0.015 else ""
            sign  = "" if i == 0 else f"<span style='color:{PAL['text_muted']}'>+ </span>"
            _n_prefix = "" if n == 1 else str(n) + "\u00b7"
            arg   = "2\u03c0\u00b7" + _n_prefix + "f\u2080t"
            if phi:
                arg += f" + {phi:.0f}\u00b0"
            dbc = 20 * math.log10(An / fund_An)
            parts.append(
                f"{sign}"
                f"<span style='{fade}' title='n={n}  |  {dbc:.1f} dBc'>"
                f"<span style='color:{col}; font-weight:bold;'>{An:.5f}</span>"
                f"<span style='color:{PAL['text_muted']}'>·sin(</span>"
                f"<span style='color:{PAL['text_faint']}'>{arg}</span>"
                f"<span style='color:{PAL['text_muted']}'>)</span>"
                f"</span> "
            )
        if len(non_dc) > SHOW:
            parts.append(
                f"<span style='color:{PAL['text_faint']}'>"
                f"+ \u2026 ({len(non_dc)-SHOW} more terms)</span>"
            )
        self._eq_lbl.setText("".join(parts))

    def _copy_latex(self):
        QApplication.clipboard().setText(self._latex_str)
        orig = self._copy_btn.text()
        self._copy_btn.setText("✓ Copied!")
        self._copy_btn.setStyleSheet(self._copy_btn_style(success=True))
        QTimer.singleShot(1400, lambda: (
            self._copy_btn.setText(orig),
            self._copy_btn.setStyleSheet(self._copy_btn_style()),
        ))

    def _copy_btn_style(self, success: bool = False) -> str:
        bg  = PAL["success"] if success else PAL["surface"]
        col = PAL["bg"]      if success else PAL["text_muted"]
        brd = PAL["success"] if success else PAL["border"]
        return (
            f"QPushButton {{ background:{bg}; color:{col}; border:1px solid {brd};"
            f"border-radius:3px; font-family:monospace; font-size:8px; padding:0 8px; }}"
            f"QPushButton:hover:!checked {{ background:{PAL['surface3']}; color:{PAL['text']}; }}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# EQUATION PANEL  (all three forms stacked)
# ─────────────────────────────────────────────────────────────────────────────
class EquationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{PAL['surface']}; border-radius:10px;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── panel header ─────────────────────────────────────────────────────
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            f"background:{PAL['surface2']}; border-bottom:1px solid {PAL['border']};"
            f"border-top-left-radius:10px; border-top-right-radius:10px;"
        )
        hdr_row = QHBoxLayout(hdr)
        hdr_row.setContentsMargins(14, 0, 14, 0)
        title = QLabel("LIVE FOURIER SERIES — ALL EQUATION FORMS")
        title.setStyleSheet(
            f"color:{PAL['text_muted']}; font-family:monospace; font-size:10px;"
            f"font-weight:bold; letter-spacing:1.5px; background:transparent; border:none;"
        )
        self._badge_wave  = _make_chip("Square Wave")
        self._badge_nharm = _make_chip("15 harmonics", accent=True)
        hdr_row.addWidget(title)
        hdr_row.addStretch()
        hdr_row.addWidget(self._badge_wave)
        hdr_row.addSpacing(4)
        hdr_row.addWidget(self._badge_nharm)
        outer.addWidget(hdr)

        # ── body ─────────────────────────────────────────────────────────────
        body = QWidget()
        body.setStyleSheet(f"background:{PAL['surface']}; border:none;")
        body_v = QVBoxLayout(body)
        body_v.setContentsMargins(12, 10, 12, 12)
        body_v.setSpacing(8)

        # 1. General / closed form
        self._blk_general  = EqBlock("General Form",        canvas_height=62, fontsize=12)
        # 2. Expanded series (HTML)
        self._blk_expanded = ExpandedSeriesBlock()
        # 3. Integral form — definition
        self._blk_integral_def = EqBlock("Integral Definition  (aₙ, bₙ)",
                                         canvas_height=56, fontsize=11)
        # 4. Integral form — solved coefficients
        self._blk_integral_sol = EqBlock("Solved Coefficients",
                                         canvas_height=54, fontsize=11)

        body_v.addWidget(self._blk_general)
        body_v.addWidget(self._blk_expanded)
        body_v.addWidget(self._blk_integral_def)
        body_v.addWidget(self._blk_integral_sol)

        outer.addWidget(body)

    # ── public update ─────────────────────────────────────────────────────────
    def update(self, wave: str, N: int, terms: list,
               amplitude: float, duty: float, phase_deg: float):
        wave_names = {"square": "Square Wave", "sawtooth": "Sawtooth",
                      "halfwave": "Half-Wave Sym.", "fullwave": "Full-Wave Rect."}
        wave_col = PAL.get(wave, PAL["primary"])

        self._badge_wave.setText(wave_names.get(wave, wave))
        self._badge_wave.setStyleSheet(
            f"color:{wave_col}; background:{PAL['surface3']};"
            f"border:1px solid {wave_col}; border-radius:3px;"
            f"font-family:monospace; font-size:9px; padding:1px 6px;"
        )
        self._badge_nharm.setText(f"{N} harmonics")

        # 1 — General form
        mt_gen, lt_gen = latex_general(wave, amplitude, duty, phase_deg)
        self._blk_general.update_eq(mt_gen, lt_gen, wave_color=wave_col)

        # 2 — Expanded series
        _mt_exp, lt_exp = latex_expanded(wave, terms, phase_deg)
        self._blk_expanded.update_series(terms, wave, phase_deg, lt_exp)

        # 3 & 4 — Integral forms
        mt_def, lt_def, mt_sol, lt_sol = latex_integral(wave, amplitude, duty)
        self._blk_integral_def.update_eq(mt_def, lt_def, wave_color=PAL["text"])
        self._blk_integral_sol.update_eq(mt_sol, lt_sol, wave_color=wave_col)


# ─────────────────────────────────────────────────────────────────────────────
# PLOT CANVAS (time / freq)
# ─────────────────────────────────────────────────────────────────────────────
class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, height_px: int = 200):
        fig = Figure(figsize=(6, height_px / 100), dpi=100)
        fig.patch.set_facecolor(PAL["bg"])
        super().__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(height_px)
        self.ax = fig.add_subplot(111)
        self._style_ax()

    def _style_ax(self):
        ax = self.ax
        ax.set_facecolor(PAL["bg"])
        for spine in ax.spines.values():
            spine.set_color(PAL["border"]); spine.set_linewidth(0.6)
        ax.tick_params(colors=PAL["text_faint"], labelsize=7, length=3, width=0.5)
        ax.xaxis.label.set_color(PAL["text_faint"])
        ax.yaxis.label.set_color(PAL["text_faint"])
        ax.xaxis.label.set_fontsize(8)
        ax.yaxis.label.set_fontsize(8)
        ax.grid(True, color=PAL["border"], linewidth=0.4, linestyle="--", alpha=0.6)
        self.figure.tight_layout(pad=0.8)

    def clear(self):
        self.ax.cla()
        self._style_ax()


# ─────────────────────────────────────────────────────────────────────────────
# LABELLED SLIDER
# ─────────────────────────────────────────────────────────────────────────────
class LabelledSlider(QWidget):
    valueChanged = Signal(float)

    def __init__(self, label, symbol, mn, mx, default,
                 step=1, fmt="{:.0f}", unit="", parent=None):
        super().__init__(parent)
        self._fmt, self._unit = fmt, unit
        self._mn, self._step = mn, step
        self._steps = round((mx - mn) / step)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        hdr = QHBoxLayout()
        lbl = QLabel(f"{label}  <span style='color:{PAL['text_faint']}'><i>{symbol}</i></span>")
        lbl.setStyleSheet(f"color:{PAL['text_muted']}; font-size:11px; font-family:monospace;")
        lbl.setTextFormat(Qt.RichText)
        self._val_lbl = QLabel(self._fmt.format(default) + unit)
        self._val_lbl.setStyleSheet(
            f"color:{PAL['text']}; font-size:12px; font-weight:bold; font-family:monospace;")
        self._val_lbl.setAlignment(Qt.AlignRight)
        hdr.addWidget(lbl); hdr.addStretch(); hdr.addWidget(self._val_lbl)
        lay.addLayout(hdr)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(self._steps)
        self._slider.setValue(round((default - mn) / step))
        self._slider.setStyleSheet(self._slider_style())
        self._slider.valueChanged.connect(self._on_change)
        lay.addWidget(self._slider)

    def _on_change(self, pos):
        v = self._mn + pos * self._step
        self._val_lbl.setText(self._fmt.format(v) + self._unit)
        self.valueChanged.emit(v)

    def get_value(self):
        return self._mn + self._slider.value() * self._step

    def set_wave_color(self, color):
        self._slider.setStyleSheet(self._slider_style(color))

    def _slider_style(self, color=PAL["primary"]):
        return f"""
            QSlider::groove:horizontal {{
                height:4px; background:{PAL['surface3']};
                border-radius:2px; border:1px solid {PAL['border']};
            }}
            QSlider::sub-page:horizontal {{ background:{color}; border-radius:2px; }}
            QSlider::handle:horizontal {{
                background:{color}; border:2px solid {PAL['bg']};
                width:14px; height:14px; margin:-5px 0; border-radius:7px;
            }}
            QSlider::handle:horizontal:hover {{ background:white; }}
        """


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
        lbl = QLabel(f"{label}:")
        lbl.setStyleSheet(
            f"color:{PAL['text_muted']}; font-size:10px; font-family:monospace;")
        row.addWidget(lbl)
        row.addSpacing(6)
        self._btns = {}
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        for i, (key, display) in enumerate(options):
            btn = QPushButton(display)
            btn.setCheckable(True)
            btn.setFixedHeight(22)
            btn.setStyleSheet(self._btn_style(i, len(options)))
            self._btns[key] = btn
            grp.addButton(btn)
            row.addWidget(btn)
            btn.clicked.connect(lambda _, k=key: self.selectionChanged.emit(k))
        list(self._btns.values())[0].setChecked(True)

    def select(self, key):
        if key in self._btns:
            self._btns[key].setChecked(True)

    def _btn_style(self, idx, total):
        rl = "3px 0 0 3px" if idx == 0 else "0"
        rr = "0 3px 3px 0" if idx == total - 1 else "0"
        return (
            f"QPushButton {{ background:{PAL['surface']}; color:{PAL['text_muted']};"
            f"border:1px solid {PAL['border']}; padding:0 10px;"
            f"font-size:10px; font-family:monospace; border-radius:{rl}; }}"
            f"QPushButton:checked {{ background:{PAL['primary']}; color:{PAL['bg']}; font-weight:bold; }}"
            f"QPushButton:hover:!checked {{ background:{PAL['surface2']}; color:{PAL['text']}; }}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# HARMONIC TABLE
# ─────────────────────────────────────────────────────────────────────────────
class HarmonicTable(QTableWidget):
    HEADERS = ["n", "Type", "Frequency", "Aₙ (V pk)", "Phase (°)", "dBc", "% Fund."]

    def __init__(self, parent=None):
        super().__init__(0, len(self.HEADERS), parent)
        self.setHorizontalHeaderLabels(self.HEADERS)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(True)
        self.setAlternatingRowColors(True)
        self.setStyleSheet(f"""
            QTableWidget {{
                background:{PAL['surface']}; color:{PAL['text_muted']};
                gridline-color:{PAL['border']}; border:none;
                font-family:monospace; font-size:10px;
            }}
            QTableWidget::item {{ padding:3px 8px; border:none; }}
            QTableWidget::item:alternate {{ background:{PAL['surface2']}; }}
            QTableWidget::item:selected {{ background:{PAL['surface3']}; color:{PAL['text']}; }}
            QHeaderView::section {{
                background:{PAL['surface2']}; color:{PAL['text_muted']};
                border:none; border-bottom:1px solid {PAL['border']};
                font-family:monospace; font-size:9px; font-weight:bold;
                text-transform:uppercase; padding:4px 8px;
            }}
        """)

    def populate(self, terms, f0_hz, wave_col):
        non_dc  = [t for t in terms if t["n"] > 0]
        fund_An = non_dc[0]["An"] if non_dc else 1.0
        self.setRowCount(len(terms))
        for row, term in enumerate(terms):
            n, An, p, tp = term["n"], term["An"], term["phase_deg"], term["type"]
            fund = (n == 1)
            dbc  = "—" if n == 0 else f"{20*math.log10(An/fund_An):.1f}"
            pct  = "—" if n == 0 else f"{An/fund_An*100:.1f}%"
            freq = "DC" if n == 0 else _fmt_freq(n * f0_hz)
            badge = "DC" if n == 0 else ("Fund." if fund else ("Odd" if tp == "odd" else "Even"))
            cells = [str(n) if n > 0 else "DC", badge, freq,
                     f"{An:.5f}", "—" if n == 0 else f"{p:.1f}°", dbc, pct]
            for col, val in enumerate(cells):
                item = QTableWidgetItem(val)
                item.setTextAlignment(
                    Qt.AlignLeft if col < 2 else Qt.AlignRight | Qt.AlignVCenter)
                if fund:
                    item.setForeground(QColor(wave_col))
                    f = item.font(); f.setBold(True); item.setFont(f)
                elif n == 0:
                    item.setForeground(QColor(PAL["accent"]))
                elif tp == "even":
                    item.setForeground(QColor(PAL["warn"]))
                self.setItem(row, col, item)


def _fmt_freq(hz):
    if hz >= 1e6: return f"{hz/1e6:.2f} MHz"
    if hz >= 1e3: return f"{hz/1e3:.2f} kHz"
    return f"{hz:.0f} Hz"


def _make_chip(text, accent=False):
    lbl = QLabel(text)
    col = PAL["primary"] if accent else PAL["text_muted"]
    lbl.setStyleSheet(
        f"color:{col}; background:{PAL['surface3']};"
        f"border:1px solid {PAL['border']}; border-radius:3px;"
        f"font-family:monospace; font-size:9px; padding:1px 6px;"
    )
    return lbl


# ─────────────────────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fourier Spectrum Visualizer")
        self.resize(1440, 960)
        self._wave      = "square"
        self._N         = 15
        self._duty      = 0.50
        self._amplitude = 1.0
        self._phase     = 0.0
        self._y_mode    = "db"
        self._disp_mode = "bars"
        self._w_mode    = "composite"
        self._periods   = 2
        self._apply_palette()
        self._build_ui()
        self._render()

    def _apply_palette(self):
        pal = QPalette()
        pal.setColor(QPalette.Window,          QColor(PAL["bg"]))
        pal.setColor(QPalette.WindowText,      QColor(PAL["text"]))
        pal.setColor(QPalette.Base,            QColor(PAL["surface"]))
        pal.setColor(QPalette.AlternateBase,   QColor(PAL["surface2"]))
        pal.setColor(QPalette.Text,            QColor(PAL["text"]))
        pal.setColor(QPalette.Button,          QColor(PAL["surface"]))
        pal.setColor(QPalette.ButtonText,      QColor(PAL["text"]))
        pal.setColor(QPalette.Highlight,       QColor(PAL["primary"]))
        pal.setColor(QPalette.HighlightedText, QColor(PAL["bg"]))
        QApplication.setPalette(pal)
        QApplication.setStyle("Fusion")

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root.setStyleSheet(f"background:{PAL['bg']};")
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(12, 8, 12, 12)
        vbox.setSpacing(8)

        vbox.addWidget(self._make_title_bar())
        vbox.addWidget(self._make_wave_selector())

        splitter = QSplitter(Qt.Vertical)
        splitter.setStyleSheet("QSplitter::handle { background:transparent; height:6px; }")
        vbox.addWidget(splitter, stretch=1)

        # Top: time + freq plots
        cw = QWidget()
        cw.setStyleSheet(f"background:{PAL['bg']};")
        cl = QHBoxLayout(cw)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(8)
        self._canvas_time = PlotCanvas(height_px=220)
        self._canvas_freq = PlotCanvas(height_px=220)
        cl.addWidget(self._wrap_plot("TIME DOMAIN", self._canvas_time, is_time=True))
        cl.addWidget(self._wrap_plot("FREQUENCY DOMAIN", self._canvas_freq, is_time=False))
        splitter.addWidget(cw)

        # Middle: equation panel (scrollable)
        eq_scroll = QScrollArea()
        eq_scroll.setWidgetResizable(True)
        eq_scroll.setStyleSheet(
            f"background:{PAL['bg']}; border:none;"
        )
        self._eq_panel = EquationPanel()
        eq_scroll.setWidget(self._eq_panel)
        splitter.addWidget(eq_scroll)

        # Bottom: controls + table
        bot = QWidget()
        bot.setStyleSheet(f"background:{PAL['bg']};")
        bh = QHBoxLayout(bot)
        bh.setContentsMargins(0, 0, 0, 0)
        bh.setSpacing(8)
        bh.addWidget(self._make_controls(), stretch=0)
        bh.addWidget(self._make_table_panel(), stretch=1)
        splitter.addWidget(bot)

        splitter.setSizes([260, 420, 280])

    # ── title bar ──────────────────────────────────────────────
    def _make_title_bar(self):
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(
            f"background:{PAL['surface']}; border-radius:8px;"
            f"border:1px solid {PAL['border']};"
        )
        row = QHBoxLayout(bar)
        row.setContentsMargins(14, 0, 14, 0)
        title = QLabel("⬛ Fourier Spectrum Visualizer")
        title.setStyleSheet(
            f"color:{PAL['text']}; font-family:monospace; font-size:14px; font-weight:bold;")
        import qtpy
        sub = QLabel(
            f"Harmonic Analyzer  ·  qtpy {qtpy.__version__} / {qtpy.API_NAME} / Matplotlib")
        sub.setStyleSheet(
            f"color:{PAL['text_faint']}; font-family:monospace; font-size:10px;")
        row.addWidget(title)
        row.addSpacing(16)
        row.addWidget(sub)
        row.addStretch()
        return bar

    # ── waveform tabs ───────────────────────────────────────────
    def _make_wave_selector(self):
        c = QWidget()
        c.setStyleSheet(f"background:{PAL['bg']};")
        row = QHBoxLayout(c)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        lbl = QLabel("WAVEFORM")
        lbl.setStyleSheet(
            f"color:{PAL['text_muted']}; font-family:monospace; font-size:9px;"
            f"font-weight:bold; letter-spacing:1.5px;")
        row.addWidget(lbl)
        row.addSpacing(6)
        self._wave_btns = {}
        grp = QButtonGroup(self)
        grp.setExclusive(True)
        WAVES = [
            ("square",   "Square",           "n=1,3,5…  odd only"),
            ("sawtooth", "Sawtooth",          "n=1,2,3…  all"),
            ("halfwave", "Half-Wave Sym.",    "n=1,3,5…  half-sym"),
            ("fullwave", "Full-Wave Rect.",   "n=0,2,4…  even+DC"),
        ]
        for key, name, desc in WAVES:
            col = PAL.get(key, PAL["primary"])
            btn = QPushButton(f"  {name}\n  {desc}")
            btn.setCheckable(True)
            btn.setFixedHeight(48)
            btn.setMinimumWidth(160)
            btn.setStyleSheet(self._tab_style(col))
            btn.clicked.connect(lambda _, k=key: self._set_wave(k))
            self._wave_btns[key] = btn
            grp.addButton(btn)
            row.addWidget(btn)
        self._wave_btns["square"].setChecked(True)
        row.addStretch()
        return c

    def _tab_style(self, col):
        return (
            f"QPushButton {{ background:{PAL['surface']}; color:{PAL['text_muted']};"
            f"border:1.5px solid {PAL['border']}; border-radius:10px;"
            f"text-align:left; font-family:monospace; font-size:10px; padding:4px 10px; }}"
            f"QPushButton:checked {{ border-color:{col}; color:{PAL['text']};"
            f"background:{PAL['surface2']}; font-weight:bold; }}"
            f"QPushButton:hover:!checked {{ border-color:{PAL['border_hi']};"
            f"color:{PAL['text']}; background:{PAL['surface2']}; }}"
        )

    # ── plot panel wrapper ──────────────────────────────────────
    def _wrap_plot(self, title, canvas, is_time):
        panel = QWidget()
        panel.setStyleSheet(
            f"background:{PAL['surface']}; border-radius:10px;"
            f"border:1px solid {PAL['border']};")
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            f"background:{PAL['surface2']}; border-bottom:1px solid {PAL['border']};"
            f"border-top-left-radius:10px; border-top-right-radius:10px;")
        hr = QHBoxLayout(hdr)
        hr.setContentsMargins(12, 0, 12, 0)
        tl = QLabel(title)
        tl.setStyleSheet(
            f"color:{PAL['text_muted']}; font-family:monospace; font-size:9px;"
            f"font-weight:bold; letter-spacing:1.5px; background:transparent; border:none;")
        hr.addWidget(tl)
        hr.addStretch()
        if is_time:
            self._chip_dc  = _make_chip("DC = 0.000 V")
            self._chip_rms = _make_chip("RMS = 0.000 V")
            hr.addWidget(self._chip_dc)
            hr.addSpacing(4)
            hr.addWidget(self._chip_rms)
        else:
            self._chip_thd = _make_chip("THD = 0.0%", accent=True)
            self._chip_n   = _make_chip("N = 15")
            hr.addWidget(self._chip_thd)
            hr.addSpacing(4)
            hr.addWidget(self._chip_n)
        v.addWidget(hdr)
        cw = QWidget()
        cw.setStyleSheet(f"background:{PAL['bg']}; border:none;")
        cl = QVBoxLayout(cw)
        cl.setContentsMargins(8, 6, 8, 6)
        cl.addWidget(canvas)
        v.addWidget(cw)
        return panel

    # ── controls ────────────────────────────────────────────────
    def _make_controls(self):
        box = QWidget()
        box.setFixedWidth(480)
        box.setStyleSheet(
            f"background:{PAL['surface']}; border-radius:10px;"
            f"border:1px solid {PAL['border']};")
        v = QVBoxLayout(box)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(12)

        self._sl_N     = LabelledSlider("Harmonics",  "N", 1,   60,  15, 1,    "{:.0f}")
        self._sl_duty  = LabelledSlider("Duty Cycle", "δ", 5,   95,  50, 1,    "{:.0f}", "%")
        self._sl_amp   = LabelledSlider("Amplitude",  "A", 0.1, 2.0, 1.0, 0.01,"{:.2f}", " V")
        self._sl_phase = LabelledSlider("Phase",      "φ", 0,   360, 0,  1,    "{:.0f}", "°")

        for sl in (self._sl_N, self._sl_duty, self._sl_amp, self._sl_phase):
            v.addWidget(sl)
            sl.valueChanged.connect(self._on_slider)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{PAL['border']};")
        v.addWidget(sep)

        tg = QGridLayout()
        tg.setSpacing(8)
        self._seg_y = SegGroup("Y-axis",   [("db","dBc"), ("linear","Linear")])
        self._seg_d = SegGroup("Spectrum", [("bars","Bars"), ("stems","Stems")])
        self._seg_w = SegGroup("Time",     [("composite","Composite"), ("partials","Partials")])
        self._seg_p = SegGroup("Periods",  [("1","1"), ("2","2"), ("3","3")])
        self._seg_p.select("2")
        tg.addWidget(self._seg_y, 0, 0)
        tg.addWidget(self._seg_d, 0, 1)
        tg.addWidget(self._seg_w, 1, 0)
        tg.addWidget(self._seg_p, 1, 1)
        v.addLayout(tg)

        self._seg_y.selectionChanged.connect(lambda s: setattr(self, '_y_mode',    s) or self._render())
        self._seg_d.selectionChanged.connect(lambda s: setattr(self, '_disp_mode', s) or self._render())
        self._seg_w.selectionChanged.connect(lambda s: setattr(self, '_w_mode',    s) or self._render())
        self._seg_p.selectionChanged.connect(lambda s: setattr(self, '_periods', int(s)) or self._render())
        return box

    def _make_table_panel(self):
        panel = QWidget()
        panel.setStyleSheet(
            f"background:{PAL['surface']}; border-radius:10px;"
            f"border:1px solid {PAL['border']};")
        v = QVBoxLayout(panel)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        hdr = QWidget(); hdr.setFixedHeight(36)
        hdr.setStyleSheet(
            f"background:{PAL['surface2']}; border-bottom:1px solid {PAL['border']};"
            f"border-top-left-radius:10px; border-top-right-radius:10px;")
        hr = QHBoxLayout(hdr); hr.setContentsMargins(14, 0, 14, 0)
        tl = QLabel("HARMONIC COEFFICIENTS")
        tl.setStyleSheet(
            f"color:{PAL['text_muted']}; font-family:monospace; font-size:9px;"
            f"font-weight:bold; letter-spacing:1.5px; background:transparent; border:none;")
        self._table_sub = QLabel("15 terms")
        self._table_sub.setStyleSheet(
            f"color:{PAL['text_faint']}; font-family:monospace; font-size:9px;")
        hr.addWidget(tl); hr.addStretch(); hr.addWidget(self._table_sub)
        v.addWidget(hdr)
        self._table = HarmonicTable()
        v.addWidget(self._table)
        return panel

    # ── slots ────────────────────────────────────────────────────
    def _set_wave(self, wave):
        self._wave = wave
        self._sl_duty.setEnabled(wave == "square")
        col = PAL.get(wave, PAL["primary"])
        for sl in (self._sl_N, self._sl_duty, self._sl_amp, self._sl_phase):
            sl.set_wave_color(col)
        self._render()

    def _on_slider(self, _):
        self._N         = int(self._sl_N.get_value())
        self._duty      = self._sl_duty.get_value() / 100.0
        self._amplitude = self._sl_amp.get_value()
        self._phase     = self._sl_phase.get_value()
        self._render()

    # ── render ───────────────────────────────────────────────────
    def _render(self):
        wave, N, A, duty, phi = (
            self._wave, self._N, self._amplitude, self._duty, self._phase)
        col   = PAL.get(wave, PAL["primary"])
        terms = get_coefficients(wave, N, A, duty, phi)

        self._draw_time(terms, col)
        self._draw_freq(terms, col)
        self._eq_panel.update(wave, N, terms, A, duty, phi)
        self._table.populate(terms, f0_hz=1000.0, wave_col=col)
        self._table_sub.setText(f"{len(terms)} terms shown")
        self._update_chips(terms, col)

    def _draw_time(self, terms, col):
        c = self._canvas_time; c.clear(); ax = c.ax
        periods = self._periods
        t = np.linspace(0, periods, 2000)
        A = self._amplitude
        if self._w_mode == "partials":
            pcs = ["#e05060","#f0b040","#56e0b8","#4fa3c8","#c87af0",
                   "#56c87a","#f07080","#80d0f0"]
            for i, term in enumerate([x for x in terms if x["n"] > 0]):
                p  = math.radians(term["phase_deg"])
                yp = term["An"] * np.sin(2*math.pi*term["n"]*t + p)
                ax.plot(t, yp, color=pcs[i % len(pcs)], lw=0.9, alpha=0.45)
        y = np.zeros_like(t)
        for term in terms:
            p = math.radians(term["phase_deg"])
            y += term["An"] if term["n"] == 0 else term["An"] * np.sin(2*math.pi*term["n"]*t+p)
        ax.plot(t, y, color=col, lw=2.0,
                path_effects=[pe.withSimplePatchShadow(
                    offset=(0,0), shadow_rgbFace=col, alpha=0.3, rho=2.0)])
        ax.axhline(0, color=PAL["border_hi"], lw=0.7, ls="--")
        ax.set_xlim(0, periods); ax.set_ylim(-A*1.25, A*1.25)
        ax.set_xlabel("Periods (T)", fontsize=8)
        ax.set_ylabel("Amplitude (V)", fontsize=8)
        c.draw()

    def _draw_freq(self, terms, col):
        c = self._canvas_freq; c.clear(); ax = c.ax
        non_dc  = [t for t in terms if t["n"] > 0]
        dc_term = next((t for t in terms if t["n"] == 0), None)
        if not non_dc: c.draw(); return
        fund_An = non_dc[0]["An"]
        max_n   = max(t["n"] for t in non_dc)
        for term in non_dc:
            n, An, tp = term["n"], term["An"], term["type"]
            yval  = 20*math.log10(An/(fund_An or 1e-12)) if self._y_mode=="db" else An
            ybase = -90 if self._y_mode == "db" else 0
            bc = col if n==1 else (PAL["warn"] if tp=="even" else PAL["primary"])
            if self._disp_mode == "bars":
                ax.bar(n, yval-ybase, bottom=ybase, width=0.6,
                       color=bc, alpha=0.85 if n>1 else 1.0, zorder=3)
            else:
                ax.vlines(n, ybase, yval, colors=bc, lw=2,
                          alpha=0.85 if n>1 else 1.0)
                ax.scatter([n], [yval], color=bc, s=28, zorder=5)
        if dc_term and abs(dc_term["An"]) > 1e-9:
            dc_y = 0.0 if self._y_mode=="db" else dc_term["An"]
            ax.axhline(dc_y, color=PAL["accent"], lw=1, ls=":", alpha=0.8)
            ax.text(0.5, dc_y, "DC", color=PAL["accent"],
                    fontsize=7, va="bottom", family="monospace")
        ax.set_xlabel("Harmonic order n", fontsize=8)
        ax.set_ylabel("|Aₙ| dBc" if self._y_mode=="db" else "|Aₙ| V pk", fontsize=8)
        ax.set_xlim(0, max_n+1)
        if self._y_mode == "db": ax.set_ylim(-90, 10)
        c.draw()

    def _update_chips(self, terms, col):
        dc  = next((t["An"] for t in terms if t["n"] == 0), 0.0)
        rms = compute_rms(terms)
        thd = compute_thd(terms)
        self._chip_dc.setText(f"DC = {dc:.3f} V")
        self._chip_rms.setText(f"RMS = {rms:.3f} V")
        self._chip_thd.setText(f"THD = {thd:.1f}%")
        self._chip_n.setText(f"N = {self._N}")
        self._chip_thd.setStyleSheet(
            f"color:{col}; background:{PAL['surface3']}; border:1px solid {col};"
            f"border-radius:3px; font-family:monospace; font-size:9px; padding:1px 6px;")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def main():
    import os
    os.environ.setdefault("QT_LOGGING_RULES", "*.debug=false;qt.qpa.*=false")
    app = QApplication(sys.argv)
    app.setApplicationName("Fourier Spectrum Visualizer")
    QFontDatabase.addApplicationFont("JetBrainsMono-Regular.ttf")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
