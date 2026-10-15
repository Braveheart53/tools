#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 William W. Wallace <wwallace@nrao.edu>
# SPDX-FileCopyrightText: 2026 William W. Wallace, Adaptive Electrodynamics LLC dba AdaptEd
# %% ===========================================================================
#    MODULE HEADER
# =============================================================================
"""Build the LuaLaTeX user manual (.tex and .pdf) of the EMF Envelope FFT Analyzer.

===============================================================================
 Title          : EMF Envelope FFT Analyzer - Manual Builder
 Filename       : build_manual_pdf.py
 Version        : 0.0.2 (Semantic Versioning 2.0.0; follows the program)
 Author         : William W. Wallace
 Company        : NRAO/GBO
 Email          : wwallace@nrao.edu
 Created        : 2026-10-15
 Modified       : 2026-10-15
 Language       : Python 3.12
 Requires       : the analyzer (../emf_envelope_fft_v*.py) and its
                  dependencies; lualatex (TeX Live or MiKTeX) on the PATH or in
                  EMF_FFT_LUALATEX; pypdf (bookmark check)
 Optional       : Veusz (VEUSZ_EXE) to regenerate the figures (--figures)
 Licence        : GPL-3.0-or-later (GNU General Public License v3.0 or later)
 Copyright      : Copyright (C) 2026 William W. Wallace
 Derived from   : tools/build_readme_pdf.py of the QuickSyn SCPI controller
                  package 0.0.10 (LuaLaTeX, DejaVu fonts, bookmarks open).
 Status         : Internal draft.
===============================================================================

LICENCE
-------
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

DESCRIPTION
-----------
Writes docs/EMF_Envelope_FFT_Manual_v<version>.tex and compiles it with
LuaLaTeX into the PDF beside it. The LaTeX source is written directly (no
pandoc), so it is complete and editable on its own; edit this script rather
than the .tex, because the next build overwrites the .tex.

Generated from the analyzer itself, so they cannot drift from the code:
    * the command-line option table (build_parser())
    * the probe catalogue with Nyquist, |H| and first-null values (PROBES)
    * the column keyword lists (_TIME_WORDS, _VALUE_PREFER, _VALUE_AVOID)
    * the Spyder cell table (the "# %%" banners of the script)
    * the package file table (line counts, sizes)
    * the self-test table (the self-test is run during the build)
    * the numbers quoted in the derivations (sinc values, scalloping, ...)

Bookmarks: hyperref + bookmark turn every \\section and \\subsection
(appendices and references included) into a numbered PDF bookmark, and the
bookmark pane opens with the PDF. After the build the outline is read back
with pypdf and compared with the headings in the .tex.

USAGE
-----
    python tools/build_manual_pdf.py              # .tex + .pdf
    python tools/build_manual_pdf.py --figures    # also re-render figures (Veusz)
    python tools/build_manual_pdf.py --tex-only   # write the .tex, do not compile
In Spyder, run the cells in order; the last cell is a scratch cell.

REVISION HISTORY
----------------
0.0.2  2026-10-15  First version, released with the analyzer 0.0.2.
===============================================================================
"""

# %% ===========================================================================
#    IMPORTS
# =============================================================================
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

import numpy as np

__version__ = "0.0.2"
__author__ = "William W. Wallace"
__email__ = "wwallace@nrao.edu"
__license__ = "GPL-3.0-or-later"

# %% ===========================================================================
#    CONSTANTS AND PATHS
# =============================================================================
#: Package folder (this script lives in <package>/tools).
PACKAGE_FOLDER = Path(globals().get("__file__", Path.cwd() / "tools" / "_")).resolve().parents[1]
#: Output folder of the manual and its figures.
DOCS_FOLDER = PACKAGE_FOLDER / "docs"
FIGURE_FOLDER = DOCS_FOLDER / "figures"
#: Date written on the title page and in the .tex header.
BUILD_DATE = "2026-10-15"

#: Figures: file in docs/figures -> (source page name in the rendered example,
#: caption, label). The "live" figures are screenshots, copied by hand.
FIGURES = {
    "fig_fieldman_time.png": ("fieldman", "time",
                              "Synthetic FieldMan/Narda-TSX log (EFD-4091): field against the "
                              "instrument clock on a date axis. The 6\\,s gap at 300\\,s is "
                              "deliberate.", "fig:time"),
    "fig_fieldman_amplitude.png": ("fieldman", "amplitude",
                                   "Envelope amplitude spectrum of the same log: the 12\\,rpm radar "
                                   "family (0.2\\,Hz and harmonics), the 0.7\\,Hz source, the "
                                   "probe-corrected trace (dashed) and the X/Y/Z axes (dotted).",
                                   "fig:amplitude"),
    "fig_fieldman_zoom.png": ("fieldman", "zoom",
                              "Chirp-Z zoom around the strongest line: the dense CZT samples "
                              "(line) between the FFT bins (markers).", "fig:zoom"),
    "fig_fieldman_probe.png": ("fieldman", "probe",
                               "Probe integration model $|H(\\nu)| = |\\operatorname{sinc}(\\nu T)|$ "
                               "for $T = 265$\\,ms up to the Nyquist frequency.", "fig:probe"),
    "fig_signalshark_spectrogram.png": ("signalshark", "spectrogram",
                                        "Synthetic SignalShark spectrogram: two carriers whose "
                                        "levels vary at 3\\,Hz and 0.5\\,Hz.", "fig:spectrogram"),
    "fig_signalshark_modulation_map.png": ("signalshark", "modulation_map",
                                           "Envelope spectrum of every RF bin of that spectrogram: "
                                           "each carrier shows its own modulation frequency.",
                                           "fig:modmap"),
    "fig_live_window_dark.png": (None, None,
                                 "Live window (View $\\rightarrow$ Dark) following a growing file "
                                 "with 2\\,Hz and 7\\,Hz envelope tones.", "fig:live"),
}


# %% ===========================================================================
#    LOADING THE ANALYZER MODULE
# =============================================================================
def find_analyzer_script(package_folder: Path = PACKAGE_FOLDER) -> Path:
    """The newest emf_envelope_fft_v*.py in the package folder."""
    candidates = sorted(package_folder.glob("emf_envelope_fft_v*_*_*.py"),
                        key=lambda p: tuple(int(n) for n in re.findall(r"\d+", p.stem)[-3:]))
    if not candidates:
        raise FileNotFoundError(f"no emf_envelope_fft_v*.py in {package_folder}")
    return candidates[-1]


def load_analyzer(script_path: Path) -> ModuleType:
    """Import the analyzer from its file (it adds its folder to sys.path itself)."""
    spec = importlib.util.spec_from_file_location("emf_envelope_fft", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["emf_envelope_fft"] = module      # dataclasses need the module registered
    spec.loader.exec_module(module)
    return module


# %% ===========================================================================
#    LATEX HELPERS
# =============================================================================
_TEX_SPECIALS = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
                 "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
                 "^": r"\textasciicircum{}"}


def tex(text: Any) -> str:
    """Escape plain text for LaTeX (the ten special characters).

    "--" becomes "-\\kern0pt-" so that option names such as --value-col keep two
    hyphens instead of turning into an en dash (TeX ligature). An empty group
    "-{}-" is not enough in LuaTeX, which forms ligatures on the node list.
    """
    escaped = "".join(_TEX_SPECIALS.get(char, char) for char in str(text))
    return escaped.replace("--", r"-\kern0pt-")


def tt(text: Any) -> str:
    """Escaped text in typewriter type."""
    return r"\texttt{" + tex(text) + "}"


def tt_break(text: Any) -> str:
    """Typewriter text that may break after . _ ( = / (long calls in narrow columns)."""
    escaped = re.sub(r"(\.|\\_|\(|=|/|,)", r"\1\\allowbreak{}", tex(text))
    return r"\texttt{" + escaped + "}"


def tex_break(text: Any) -> str:
    """Plain text that may break after . and _ (long identifiers in narrow columns)."""
    return re.sub(r"(\.|\\_)", r"\1\\allowbreak{}", tex(text))


def path_tex(text: str) -> str:
    r"""A file or folder name that may break at / _ - . (\path from the url package)."""
    if any(char in text for char in "{}%#\\"):
        return tt(text)
    return r"\path{" + text + "}"


def longtable(caption: str, label: str, columns: Sequence[tuple[str, str]],
              rows: Sequence[Sequence[str]], size: str = r"\small") -> str:
    """A captioned longtable with booktabs rules and a repeated header.

    ``columns`` holds (header text in LaTeX, width as a fraction of the line);
    ``rows`` hold cells already in LaTeX.
    """
    # Each width is net of the column padding (2 \tabcolsep), so the table
    # never exceeds the line however many columns it has.
    spec = "@{}" + "".join(f"L{{\\dimexpr {width}\\linewidth-2\\tabcolsep\\relax}}"
                           for _, width in columns) + "@{}"
    header = " & ".join(r"\textbf{" + head + "}" for head, _ in columns) + r" \\"
    lines = [r"\begingroup" + size, r"\begin{longtable}{" + spec + "}",
             r"\caption{" + caption + r"}\label{" + label + r"}\\",
             r"\toprule", header, r"\midrule", r"\endfirsthead",
             r"\multicolumn{" + str(len(columns)) + r"}{@{}l}{\itshape\footnotesize Table \thetable{} (continued)}\\",
             r"\toprule", header, r"\midrule", r"\endhead",
             r"\bottomrule", r"\endlastfoot"]
    lines += [" & ".join(row) + r" \\" for row in rows]
    lines += [r"\end{longtable}", r"\endgroup", ""]
    return "\n".join(lines)


def fill(template: str, tokens: dict[str, str]) -> str:
    """Replace @@NAME@@ tokens; any token left over is an error."""
    for key, value in tokens.items():
        template = template.replace(f"@@{key}@@", value)
    leftover = re.findall(r"@@[A-Z0-9_]+@@", template)
    if leftover:
        raise KeyError(f"unfilled tokens: {sorted(set(leftover))}")
    return template


# %% ===========================================================================
#    GENERATED TABLES
# =============================================================================
def option_rows(analyzer: ModuleType) -> list[list[str]]:
    """Rows (option, default, description) from the analyzer's argparse parser."""
    rows = []
    for action in analyzer.build_parser()._actions:   # the documented argparse internals
        if isinstance(action, argparse._HelpAction):
            names = "-h, --help"
            description = "show the help text and exit"
            default_text = ""
        else:
            names = ", ".join(action.option_strings) or action.dest
            if action.nargs in ("*", "+"):
                names += " ..."
            elif action.metavar:
                names += f" {action.metavar}"
            elif action.option_strings and action.nargs != 0 and not isinstance(
                    action, (argparse._StoreTrueAction, argparse._VersionAction)):
                type_name = getattr(action.type, "__name__", "TEXT").upper()
                names += " " + ("FLOAT" if type_name == "FLOAT" else "INT" if type_name == "INT"
                                else "TEXT")
            description = action.help or ""
            if action.choices:
                description += " (choices: " + ", ".join(map(str, action.choices)) + ")"
            default = action.default
            default_text = "" if default in (None, False, argparse.SUPPRESS) or \
                isinstance(action, argparse._VersionAction) else str(
                    round(default, 9) if isinstance(default, float) else default)
        rows.append([tt(names), tt(default_text) if default_text else "--", tex(description)])
    return rows


def probe_rows(analyzer: ModuleType) -> list[list[str]]:
    """Probe catalogue with the derived envelope limits (Nyquist, |H|, first null)."""
    rows = []
    for spec in analyzer.PROBES.values():
        integration_s = spec.t_int_s or 1.0 / spec.fs_hz
        nyquist_hz = spec.fs_hz / 2
        response_db = 20 * math.log10(max(abs(np.sinc(nyquist_hz * integration_s)), 1e-12))
        rows.append([
            tex(spec.name) + r"\newline\footnotesize " + tex(spec.part),
            tex(_frequency_text(spec.f_lo_hz) + " -- " + _frequency_text(spec.f_hi_hz)),
            f"{spec.fs_hz:g}",
            (f"{spec.t_int_s * 1e3:g}" if spec.t_int_s else r"n/p\newline\footnotesize(1/fs used)"),
            f"{nyquist_hz:g}",
            f"{response_db:.1f}",
            f"{1.0 / integration_s:.4g}",
            (f"{spec.truerms_max_vm:g}" if spec.truerms_max_vm else "--"),
            tex(spec.axes),
            r"\cite{" + spec.ref + "}"])
    return rows


def _frequency_text(frequency_hz: float) -> str:
    """100000 -> '100 kHz', 6e9 -> '6 GHz'."""
    for divisor, unit in ((1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if frequency_hz >= divisor:
            return f"{frequency_hz / divisor:g} {unit}"
    return f"{frequency_hz:g} Hz"


def keyword_rows(analyzer: ModuleType) -> list[list[str]]:
    """The column-name keyword lists used by the text readers."""
    return [
        [tex("time column"), ", ".join(tt(w) for w in analyzer._TIME_WORDS),
         tex("a date column and a clock column are joined; otherwise the first match")],
        [tex("value column, preferred (+5)"), ", ".join(tt(w) for w in analyzer._VALUE_PREFER),
         tex("+3 more if the header names a unit; leftmost column wins ties")],
        [tex("value column, avoided (-6)"), ", ".join(tt(w) for w in analyzer._VALUE_AVOID),
         tex("statistics and house-keeping columns")],
        [tex("axis columns"), tt("X, Y, Z, E_x, H y, field_z, ..."),
         tex("used for per-axis spectra; their RSS is the value when no value column exists")],
    ]


def cell_rows(script_path: Path) -> list[list[str]]:
    """The Spyder cells of a script: banner title and the top-level definitions in it."""
    lines = script_path.read_text(encoding="utf-8").splitlines()
    cells: list[tuple[str, int, list[str]]] = []
    for index, line in enumerate(lines):
        if line.startswith("# %% ====") and index + 1 < len(lines):
            title = lines[index + 1].lstrip("#").strip()
            cells.append((title, index + 1, []))
        elif cells:
            match = re.match(r"^(?:def|class) (\w+)", line)
            if match:
                cells[-1][2].append(match.group(1))
    rows = []
    for number, (title, line_number, names) in enumerate(cells, start=1):
        shown = ", ".join(names[:9]) + (f", ... ({len(names)} in all)" if len(names) > 9 else "")
        rows.append([str(number), tex(title), str(line_number),
                     tex(shown) if shown else r"\textit{(constants, imports or comments)}"])
    return rows


def package_file_rows(package_folder: Path, script_path: Path, manual_stem: str) -> list[list[str]]:
    """Files of the package with their purpose (line counts measured at build time)."""
    def lines_of(path: Path) -> str:
        return f"{len(path.read_text(encoding='utf-8').splitlines())} lines" if path.is_file() else "--"

    writer = package_folder / "vszh5_writer.py"
    tool = package_folder / "tools" / "build_manual_pdf.py"
    return [
        [path_tex(script_path.name), "Python 3.12 script", lines_of(script_path),
         tex("The analyzer: readers, estimators, Veusz/CSV/JSON output, batch, live mode, "
             "self-test. Spyder cells (Table ") + r"\ref{tab:cells}" + tex(").")],
        [path_tex("vszh5_writer.py"), "Python module", lines_of(writer),
         tex("The author's Veusz HDF5 writer, 0.0.11: typed datasets, 2-D images, plot-page "
             "helpers, rendering to PDF (with bookmarks) and PNG. Must stay next to the script.")],
        [path_tex("emf_envelope_fft.yml"), "mamba environment", "--",
         tex("Creates the environment emf-fft from conda-forge (Python 3.12 and every "
             "dependency; CuPy commented out).")],
        [path_tex("LICENSE"), "text", "--", tex("GNU General Public License v3.0.")],
        [path_tex(f"docs/{manual_stem}.pdf"), "PDF", "--",
         tex("This manual, with heading-based bookmarks.")],
        [path_tex(f"docs/{manual_stem}.tex"), "LuaLaTeX source", "--",
         tex("Source of this manual; written by the build tool, compiles on its own with lualatex.")],
        [path_tex("docs/figures/*.png"), "PNG", "--",
         tex("Figures of this manual: Veusz pages rendered from the self-test's synthetic files, "
             "and screenshots of the live window.")],
        [path_tex("tools/build_manual_pdf.py"), "Python 3.12 script", lines_of(tool),
         tex("Builds this manual (generated tables, self-test run, LuaLaTeX, bookmark check).")],
    ]


def selftest_rows(analyzer: ModuleType) -> tuple[list[list[str]], bool, str]:
    """Run the analyzer's self-test and turn its report into table rows."""
    report = io.StringIO()
    with tempfile.TemporaryDirectory(prefix="emf_manual_selftest_") as folder, \
            contextlib.redirect_stdout(report):
        exit_code = analyzer.self_test(folder)
    rows = []
    for line in report.getvalue().splitlines():
        match = re.match(r"\s*\[(PASS|FAIL)\]\s*([^:]+)(?::\s*(.*))?$", line)
        if match:
            verdict, check, detail = match.groups()
            rows.append([tex(check.strip()), tex(detail or ""),
                         r"\textbf{" + verdict + "}" if verdict == "FAIL" else verdict])
    return rows, exit_code == 0, report.getvalue()


# %% ===========================================================================
#    COMPUTED NUMBERS (quoted in the derivations)
# =============================================================================
def computed_numbers(analyzer: ModuleType, writer_version: str) -> dict[str, str]:
    """Every number the text quotes, computed here so the text cannot be wrong."""
    def sinc_db(frequency_hz: float, integration_s: float) -> float:
        return 20 * math.log10(abs(np.sinc(frequency_hz * integration_s)))

    # Hann scalloping loss: window response half a bin off centre, relative to on-bin.
    n_window = 4096
    hann = analyzer.ssig.get_window("hann", n_window)
    half_bin = abs(np.sum(hann * np.exp(-1j * np.pi * np.arange(n_window) / n_window)))
    scalloping_db = 20 * math.log10(half_bin / hann.sum())
    max_gain = 10 ** (12 / 20)
    epsilon = 1 / (4 * max_gain ** 2)
    efd1891 = analyzer.PROBES["EFD-1891F"]
    return {
        "VERSION": analyzer.__version__, "WRITER_VERSION": writer_version, "DATE": BUILD_DATE,
        "Z0": f"{analyzer.Z0_OHM:.9f}",
        "DBM_TO_DBUV": f"{10 * math.log10(50 * 1e-3 / 1e-12):.4f}",
        "SINC_15": f"{sinc_db(1.5, 0.265):.2f}", "SINC_25": f"{sinc_db(2.5, 0.265):.2f}",
        "SINC_3": f"{sinc_db(3.0, 0.265):.1f}",
        "NULL_265": f"{1 / 0.265:.3f}",
        "HANN_SCALLOP": f"{scalloping_db:.2f}",
        "G_MAX": f"{max_gain:.3f}", "EPSILON": f"{epsilon:.5f}",
        "SWITCH_STEP": f"{20 * math.log10(5 / 4):.2f}",
        "EFD1891_NULL": f"{1 / efd1891.t_int_s:.1f}", "EFD1891_NYQ": f"{efd1891.fs_hz / 2:g}",
        "SPILL": f"{analyzer.SPILL_SAMPLES:,}".replace(",", r"\,"),
        "CHUNK": f"{analyzer.READ_CHUNK_ROWS:,}".replace(",", r"\,"),
        "MAX_IMAGE": str(analyzer.MAX_IMAGE_SIDE), "GAP": f"{analyzer.GAP_FACTOR:g}",
    }


# %% ===========================================================================
#    FIGURES
# =============================================================================
def make_figures(analyzer: ModuleType, figure_folder: Path = FIGURE_FOLDER) -> list[Path]:
    """Render the example pages from the self-test's synthetic files (needs Veusz).

    The rendered PNGs are copied to ``figure_folder`` under the names in
    FIGURES. Screenshots (source None) are left as they are.
    """
    figure_folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="emf_manual_figures_") as folder:
        work = Path(folder)
        files = analyzer.make_synthetic_files(work / "data")
        runs = {
            "fieldman": (files["fieldman"], analyzer.Options(probe="EFD-4091", correct_probe=True,
                                                             lomb="on", render=True,
                                                             out=str(work / "fieldman"))),
            "signalshark": (files["signalshark"], analyzer.Options(rf_channels="auto:2", render=True,
                                                                   out=str(work / "signalshark"))),
        }
        for source, (input_path, options) in runs.items():
            analyzer.process_file(str(input_path), options)
        for figure_name, (source, page, _, _) in FIGURES.items():
            if source is None:
                continue
            matches = sorted((work / source).glob(f"*_p[0-9][0-9]_{page}.png"))
            if matches:
                target = figure_folder / figure_name
                shutil.copyfile(matches[0], target)
                written.append(target)
    return written


def figure_tex(figure_name: str) -> str:
    """A float with the figure, or a framed note when the PNG is missing."""
    _, _, caption, label = FIGURES[figure_name]
    return "\n".join([
        r"\begin{figure}[htbp]", r"\centering",
        r"\IfFileExists{figures/" + figure_name + r"}{\includegraphics[width=0.92\linewidth]{figures/"
        + figure_name + r"}}{\fbox{\parbox{0.8\linewidth}{\centering Figure file \path{figures/"
        + figure_name + r"} not found: run \path{tools/build_manual_pdf.py --figures}.}}}",
        r"\caption{" + caption + r" \emph{(Synthetic data.)}}\label{" + label + "}",
        r"\end{figure}", ""])


# %% ===========================================================================
#    MANUAL TEXT: HEADER, PREAMBLE AND FRONT MATTER
# =============================================================================
TEX_HEADER = r"""% !TeX program = lualatex
% SPDX-License-Identifier: GPL-3.0-or-later
% SPDX-FileCopyrightText: 2026 William W. Wallace <wwallace@nrao.edu>
% SPDX-FileCopyrightText: 2026 William W. Wallace, Adaptive Electrodynamics LLC dba AdaptEd
% =============================================================================
%    FILE HEADER
% =============================================================================
%  Title          : EMF Envelope FFT Analyzer - User Manual
%  Filename       : @@MANUAL_STEM@@.tex
%  Version        : @@VERSION@@ (Semantic Versioning 2.0.0; follows the program)
%  Author         : William W. Wallace
%  Company        : NRAO/GBO
%  Email          : wwallace@nrao.edu
%  Created        : 2026-10-15
%  Modified       : @@DATE@@
%  Language       : LaTeX for LuaLaTeX (LuaHBTeX), TeX Live 2023+ or MiKTeX
%  Requires       : fontspec, unicode-math, amsmath, hyperref, bookmark,
%                   booktabs, longtable, array, fvextra, fancyhdr, graphicx,
%                   caption, float, enumitem, xcolor, url, tocloft; DejaVu fonts
%                   (Latin Modern is used when DejaVu is not installed)
%  Licence        : GPL-3.0-or-later (GNU General Public License v3.0 or later)
%  Copyright      : Copyright (C) 2026 William W. Wallace
%  Generated by   : tools/build_manual_pdf.py @@TOOL_VERSION@@. Edit that script, not
%                   this file: the next build overwrites this file.
%  Build          : lualatex @@MANUAL_STEM@@.tex   (three runs: contents,
%                   longtable widths, bookmarks), or run the build tool.
%  Bookmarks      : every \section and \subsection (appendices and references
%                   included) becomes a numbered PDF bookmark (hyperref +
%                   bookmark); the bookmark pane opens with the PDF.
% =============================================================================
"""

TEX_PREAMBLE = r"""
% =============================================================================
%    PREAMBLE
% =============================================================================
\documentclass[10pt,letterpaper]{article}
\usepackage[margin=2.0cm,headheight=14pt]{geometry}

% ---- fonts: DejaVu when installed (TeX Live ships it), else Latin Modern ----
\usepackage{amsmath}
\usepackage{unicode-math}
\IfFontExistsTF{DejaVu Serif}{%
  \setmainfont{DejaVu Serif}%
  \setsansfont{DejaVu Sans}%
  \setmonofont[Scale=0.85]{DejaVu Sans Mono}}{}
\IfFontExistsTF{DejaVu Math TeX Gyre}{\setmathfont{DejaVu Math TeX Gyre}}{\setmathfont{Latin Modern Math}}

% ---- layout, tables, figures, code ------------------------------------------
\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{array,booktabs,longtable}
\usepackage[font=small,labelfont=bf]{caption}
\usepackage{float}
\usepackage{enumitem}
\usepackage{fvextra}
\usepackage{fancyhdr}
\usepackage{url}
\def\UrlBreaks{\do\/\do\_\do\-\do\.\do\=\do\&}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\fvset{breaklines,breakanywhere,fontsize=\small,frame=leftline,framerule=0.6pt,rulecolor=\color{gray}}
\setlist{itemsep=1pt,topsep=3pt}
\setlength{\parskip}{3pt}
\setlength{\parindent}{0pt}
\sloppy
\renewcommand{\arraystretch}{1.12}
\usepackage[titles]{tocloft}            % wider number boxes: "10" and "5.10" fit
\setlength{\cftsecnumwidth}{2.0em}
\setlength{\cftsubsecnumwidth}{2.9em}
\setlength{\cfttabnumwidth}{2.3em}
\setlength{\cftfignumwidth}{2.3em}
\numberwithin{equation}{section}
\DeclareMathOperator{\sinc}{sinc}

% ---- header and footer -----------------------------------------------------------
\pagestyle{fancy}
\fancyhf{}
\lhead{\small EMF Envelope FFT Analyzer --- User Manual}
\rhead{\small\thepage}
\lfoot{\scriptsize Version @@VERSION@@ (@@DATE@@), GPL-3.0-or-later}
\rfoot{\scriptsize W.\,W.\ Wallace, NRAO/GBO}

% ---- hyperlinks and heading-based PDF bookmarks (load last) --------------------
\usepackage[bookmarks=true,bookmarksnumbered=true,bookmarksopen=true,
            bookmarksopenlevel=1,pdfpagemode=UseOutlines,colorlinks=true,
            linkcolor=blue!50!black,citecolor=green!40!black,
            urlcolor=blue!60!black]{hyperref}
\usepackage{bookmark}
\bookmarksetup{numbered,open,openlevel=1}
\hypersetup{
  pdftitle={EMF Envelope FFT Analyzer - User Manual, version @@VERSION@@},
  pdfauthor={William W. Wallace, NRAO/GBO},
  pdfsubject={Envelope (modulation) spectra of Narda broadband probe and SignalShark logs},
  pdfkeywords={EMF, envelope FFT, Welch, chirp-Z, Lomb-Scargle, Narda, FieldMan, SignalShark, Veusz},
  pdfcreator={tools/build_manual_pdf.py @@TOOL_VERSION@@ with LuaLaTeX}}
"""

TEX_FRONT = r"""
% =============================================================================
%    FRONT MATTER
% =============================================================================
\begin{document}
\begin{titlepage}
\pdfbookmark[section]{Title page}{titlepage}
\centering
\vspace*{3cm}
{\Huge\bfseries EMF Envelope FFT Analyzer\par}
\vspace{0.6cm}
{\Large User Manual\par}
\vspace{1.2cm}
{\large Envelope (modulation) spectra of broadband EMF probe logs\\
(FieldMan / Narda-TSX, NBM-550, EHP-50 TS) and SignalShark spectrograms\par}
\vspace{1.5cm}
{\large Program version @@VERSION@@ \quad$\cdot$\quad vszh5\_writer @@WRITER_VERSION@@ \quad$\cdot$\quad @@DATE@@\par}
\vspace{2cm}
{\large William W. Wallace\par}
NRAO/GBO\\
\href{mailto:wwallace@nrao.edu}{wwallace@nrao.edu}\par
\vfill
{\small Copyright \copyright{} 2026 William W. Wallace (Adaptive Electrodynamics LLC dba AdaptEd).\\
This manual and the programs it describes are free software under the\\
GNU General Public License v3.0 or later (GPL-3.0-or-later).\par}
\vspace{0.5cm}
{\small\itshape Internal draft: tested on synthetic files only (Section~\ref{sec:verification}).\par}
\end{titlepage}

\pdfbookmark[section]{Contents}{contents}
\tableofcontents
\clearpage
\pdfbookmark[section]{List of tables}{lot}
\listoftables
\pdfbookmark[section]{List of figures}{lof}
\listoffigures
\clearpage
"""


# %% ===========================================================================
#    MANUAL TEXT: SECTIONS
# =============================================================================
SECTION_INTRODUCTION = r"""
% =============================================================================
%    1  INTRODUCTION
% =============================================================================
\section{Introduction}\label{sec:intro}

A broadband diode probe such as the Narda EFD-4091, EFD-0691, EF\,0691 or
EFD-9091 adds the power of every source in its frequency range and reports one
number per sample \cite{R1,R2,R3}. Its log therefore holds no information about
the radio frequency of a source. It does hold how the total field changes in
time: a radar antenna rotating, a beam being scanned, a transmitter keyed on and
off, a duty cycle. The \emph{EMF Envelope FFT Analyzer} takes the Fourier
transform of that envelope, the \emph{modulation spectrum}, so that sources which
share an RF band but change at different rates can be told apart and their rates
measured (a rotating antenna appears as a line at its rotation frequency, with
harmonics from the beam shape).

The program reads the files written by the software of the instruments in use:
FieldMan and Narda-TSX exports for the EFD probes \cite{R5,R9}, NBM-550 or
NBM-TS logs for the EF\,0691 probe \cite{R6}, EHP-50 TS spectra of the EHP-50F
low-frequency analyzer \cite{R7}, and SignalShark spectrum or spectrogram files
\cite{R8}. A SignalShark spectrogram, unlike a probe log, does resolve RF
frequency; for it the envelope transform is taken for every frequency bin.

\subsection{What the analysis can and cannot tell you}
\begin{itemize}
\item \textbf{Can}: the rates at which the total field changes (rotation in rpm,
scan or keying periods), the relative strength of each modulation, and which
modulations come from the same source (harmonic families).
\item \textbf{Cannot}: the RF frequency of a source measured with a diode probe;
content faster than half the probe's sample rate (it folds back, Section~\ref{sec:sinc});
an exposure assessment, for which IEC~62232 \cite{R18} and calibrated probes
(IEEE~1309 \cite{R17}) remain the reference.
\item \textbf{Only partly}: content near the Nyquist frequency is attenuated by
the probe's own averaging; the program models and can partly undo that
(Section~\ref{sec:correction}).
\end{itemize}

\subsection{Status of this version}
Version @@VERSION@@ is an internal draft. No real export of FieldMan,
Narda-TSX, NBM-TS, EHP-50 TS or SignalShark has been available yet, so the
readers recognise file layouts by heuristics (Section~\ref{sec:inputs}) and
were tested on synthetic files written in the expected styles. Use
\texttt{--inspect} on every new kind of file before trusting an analysis, and
see Section~\ref{sec:limits} for the known limitations.

\subsection{Conventions}
\begin{itemize}
\item $f$ is an RF (or spectrum) frequency, $\nu$ an envelope (modulation)
frequency; $f_s$ is the sample rate of the log, $N$ the number of samples, and
$T$ the probe's integration time.
\item $\sinc x = \sin(\pi x)/(\pi x)$, the normalised form used by NumPy.
\item Versions follow Semantic Versioning (\texttt{X.Y.Z}); the manual carries
the version of the program it documents.
\item Commands are shown for a Windows or Linux shell inside the mamba
environment; \texttt{python} is the environment's interpreter.
\end{itemize}
"""

SECTION_INSTALL = r"""
% =============================================================================
%    2  INSTALLATION
% =============================================================================
\section{Installation}\label{sec:install}

\subsection{Mamba environment}
The environment file creates an environment named \texttt{emf-fft} from
conda-forge with Python~3.12 and every dependency \cite{B36}:
\begin{Verbatim}
mamba env create -f emf_envelope_fft.yml
mamba activate emf-fft
python emf_envelope_fft_v@@VERSION_US@@.py --selftest
\end{Verbatim}
The self-test (Section~\ref{sec:verification}) must end with
\texttt{SELF-TEST PASSED}. For a GPU (NVIDIA CUDA only), also install CuPy
(\texttt{mamba install -c conda-forge cupy}) and add \texttt{--gpu}.

\subsection{Package files}
Keep the files together as delivered; \path{vszh5_writer.py} must sit in the
same folder as the script, which puts its own folder first on the module search
path so that this copy is used rather than an older one (e.g.\ from the
QuickSyn package). Table~\ref{tab:files} lists the package.

@@TABLE_FILES@@

\subsection{Veusz and LuaLaTeX (optional)}
The \texttt{.vszh5} documents are written without Veusz; Veusz is needed only
to open them or to render them with \texttt{--render} \cite{B23}. The renderer
finds Veusz on the PATH, in the usual install folders, or through the
environment variable \texttt{VEUSZ\_EXE} (or \texttt{QUICKSYN\_VEUSZ}), e.g.\
\verb|set VEUSZ_EXE=C:\Program Files\Veusz\veusz.exe|. Rebuilding this manual
needs \texttt{lualatex} from TeX~Live or MiKTeX (or \texttt{EMF\_FFT\_LUALATEX}
pointing to it); its headings become the PDF bookmarks through hyperref and bookmark \cite{B37}.

\subsection{Spyder}
Select the interpreter of the \texttt{emf-fft} environment in Spyder
(\emph{Tools $\rightarrow$ Preferences $\rightarrow$ Python interpreter}; the
environment includes \texttt{spyder-kernels}) \cite{B35}. The script is
divided into \verb|# %%| cells (Section~\ref{sec:spyder}); run them in order
with \emph{Run cell}, then use the scratch cell at the end.
"""

SECTION_QUICKSTART = r"""
% =============================================================================
%    3  QUICK START
% =============================================================================
\section{Quick start}\label{sec:quickstart}

\begin{Verbatim}
:: 1  check the installation
python emf_envelope_fft_v@@VERSION_US@@.py --selftest

:: 2  see how a file will be read (columns, units, time base)
python emf_envelope_fft_v@@VERSION_US@@.py --inspect export.csv

:: 3  analyse one probe log; also render PDF and PNG with Veusz
python emf_envelope_fft_v@@VERSION_US@@.py export.csv --probe EFD-4091 --render

:: 4  undo the probe's averaging and force Lomb-Scargle
python emf_envelope_fft_v@@VERSION_US@@.py export.csv --probe EFD-4091 --correct-probe --lomb on

:: 5  several files in parallel, on the GPU if one is available
python emf_envelope_fft_v@@VERSION_US@@.py a.csv b.csv c.csv --jobs 3 --gpu

:: 6  SignalShark spectrogram, the five strongest carriers as channels
python emf_envelope_fft_v@@VERSION_US@@.py rec.h5 --source signalshark --rf-channels auto:5

:: 7  EHP-50 TS: the whole folder of auto-saved spectra
python emf_envelope_fft_v@@VERSION_US@@.py D:\EHP50\2026 --source ehp

:: 8  follow a file that another program is writing (live window)
python emf_envelope_fft_v@@VERSION_US@@.py --live growing.csv --probe EF0691 --window-s 120
\end{Verbatim}

\subsection{Typical workflow}
\begin{enumerate}
\item Export the measurement from the instrument software as text (CSV/TXT) or
Excel, or copy the SignalShark \texttt{.h5} file.
\item Run \texttt{--inspect} and check the detected delimiter, decimal mark,
columns, unit and sample interval. Correct anything wrong with the override
options (Section~\ref{sec:overrides}).
\item Run the analysis with \texttt{--probe} set, so that the sample rate,
integration time and range limits of the probe are known.
\item Open \path{<stem>_envelope_fft.vszh5} in Veusz, or use the rendered PDF,
whose bookmarks list every page (Section~\ref{sec:outputs}).
\item Read \path{<stem>_summary.json}: peaks, harmonic families with their rpm,
and warnings about timing, gaps, aliasing and range.
\end{enumerate}
"""

SECTION_INPUTS = r"""
% =============================================================================
%    4  INSTRUMENTS AND INPUT FILES
% =============================================================================
\section{Instruments and input files}\label{sec:inputs}

\subsection{Probe catalogue}
Table~\ref{tab:probes} lists the probes the program knows, from the
datasheets. \texttt{--probe} accepts the names in the first column (case and
spaces ignored) and the aliases \texttt{EFD-4091E} (treated as the EFD-4091;
no separate datasheet for an ``E'' variant was found), \texttt{EF-0691},
\texttt{EFD-1891FAST} and the forms without hyphens. The last four columns are
derived: the Nyquist frequency $f_s/2$, the response of the probe's averaging at
that frequency, and the first null $1/T$ of that response
(Section~\ref{sec:sinc}).

@@TABLE_PROBES@@

\subsection{Readers}
The reader is chosen from the file (Table~\ref{tab:readers}); \texttt{--source}
forces one.

@@TABLE_READERS@@

\subsection{How text exports are read}\label{sec:textreading}
Narda's software is German-made, so semicolon-separated files with a decimal
comma are expected as often as comma-separated files with a decimal point.
\begin{enumerate}
\item \textbf{Encoding}: UTF-8 (with or without byte-order mark), then
Windows-1252, then Latin-1.
\item \textbf{Delimiter}: the first of tab, \texttt{;}, \texttt{,}, \texttt{|}
that occurs the same number of times on the last 50 non-blank lines;
whitespace otherwise. Semicolon is tried before comma because a decimal comma
puts a comma inside every number.
\item \textbf{Decimal mark}: comma when numbers such as \texttt{1,23} appear
and the delimiter is not a comma.
\item \textbf{Header row}: the first row with the same number of fields as the
row below it and more text fields than that row, whose fields are mostly
numbers or date/times. Lines above it are kept as metadata and searched for a
unit.
\item \textbf{Columns}: chosen with the keyword lists of Table~\ref{tab:keywords};
the unit comes from \texttt{--unit}, the value column's header or the
metadata, in that order.
\item \textbf{Time}: numbers are seconds (milliseconds when the header says
\texttt{ms}); anything else is parsed as date/time, day first when dates look
like \texttt{dd.mm.yyyy}. A date column and a clock column are joined. The
first value is the origin of every chunk of a large file, so the time axis is
continuous.
\item \textbf{Size}: the file is read in chunks of @@CHUNK@@ rows; columns longer
than @@SPILL@@ samples move to a temporary file on disk (Section~\ref{sec:memory}).
\end{enumerate}

@@TABLE_KEYWORDS@@

\subsection{EHP-50 TS spectra}
EHP-50 TS saves one spectrum per file as \path{YYYY/MM/DD/hh_mm_ss_cc.TXT}
($cc$ = hundredths of a second) \cite{R7}. Given a folder, the program reads
every \texttt{.txt}/\texttt{.csv} below it, takes the time of each spectrum from
its path (the file date when the name does not match), sorts them, and puts
every spectrum on the frequency axis of the first one (linear interpolation
when they differ). The total or RSS column is preferred over X, Y, Z. The result
is analysed as a spectrogram (Section~\ref{sec:spectrogram}). Note that EHP-50 TS
records only the EHP-50F (1\,Hz to 400\,kHz); it cannot record the RF probes.

\subsection{SignalShark files}
The layout of SignalShark's \texttt{.h5} files is not published. The reader
takes the largest two-dimensional numeric dataset as levels (time $\times$
frequency, transposed if the axes say so), a one-dimensional dataset of matching
length whose name or values look like frequencies as the frequency axis, and one
that increases as the time axis; otherwise start/stop/centre/span and
time-resolution attributes. \texttt{--h5-level}, \texttt{--h5-freq} and
\texttt{--h5-time} name the datasets explicitly; \texttt{--inspect} prints the
whole HDF5 tree. CSV files made with Narda's NSL \emph{Converter} script
\cite{R8} are read in wide format (one row per spectrum, the header holding the
frequencies), long format (time, frequency, level columns) or transposed wide
format (one row per frequency). Levels in dBm or dB\textmu V are converted to
field strength only when an antenna factor is given (\texttt{--antenna-factor-db}).

\subsection{Overriding the detection}\label{sec:overrides}
\texttt{--source}, \texttt{--time-col} (\texttt{"Date+Time"} joins two columns),
\texttt{--value-col}, \texttt{--unit}, \texttt{--sep}, \texttt{--decimal},
\texttt{--dayfirst} and \texttt{--fs} (for files without a time column) override
the corresponding guess. Column names or zero-based indices are accepted.
"""

SECTION_THEORY = r"""
% =============================================================================
%    5  THEORY AND METHODS
% =============================================================================
\section{Theory and methods}\label{sec:theory}

\subsection{Square-law detection adds powers}\label{sec:powersum}
A diode detector operated in its square-law region delivers a voltage
proportional to the square of the RF voltage. Let the field at the probe be the
sum of $M$ sources,
\begin{equation}
E(t) = \sum_{i=1}^{M} E_i \cos(2\pi f_i t + \varphi_i).
\end{equation}
The detector output, averaged by a video filter that is much slower than any
difference frequency $|f_i - f_j|$, is
\begin{align}
\overline{E^2} &= \sum_{i}\sum_{j} E_i E_j\,\overline{\cos(2\pi f_i t+\varphi_i)\cos(2\pi f_j t+\varphi_j)} \nonumber\\
&= \sum_{i}\sum_{j} \frac{E_i E_j}{2}\Big[\overline{\cos\big(2\pi(f_i-f_j)t+\varphi_i-\varphi_j\big)}
 + \overline{\cos\big(2\pi(f_i+f_j)t+\varphi_i+\varphi_j\big)}\Big] \nonumber\\
&= \sum_{i} \frac{E_i^2}{2} = \sum_i E_{i,\mathrm{rms}}^2,
\label{eq:powersum}
\end{align}
because every term with $i\neq j$ and every sum-frequency term averages to
zero. Three orthogonal sensors add in the same way,
$E^2 = E_x^2 + E_y^2 + E_z^2$ (the isotropic RSS value). With the probe's
frequency response $r(f)$ and the plane-wave power density
$S = E_\mathrm{rms}^2 / Z_0$, the displayed value is
\begin{equation}
S_\mathrm{disp}(t) = \sum_i r(f_i)\, S_i(t),\qquad
E_\mathrm{disp}(t) = \sqrt{Z_0\, S_\mathrm{disp}(t)}.
\label{eq:sdisp}
\end{equation}
Equation~\eqref{eq:powersum} holds only while every diode stays in its
square-law region, which for the EFD probes is the True-RMS range of
Table~\ref{tab:probes}; above it the program warns.

\subsection{Why the transform is taken of power}\label{sec:whypower}
The Fourier transform is linear, so applying it to \eqref{eq:sdisp} gives
\begin{equation}
\mathcal{F}\{S_\mathrm{disp}\}(\nu) = \sum_i r(f_i)\,\mathcal{F}\{S_i\}(\nu):
\label{eq:linear}
\end{equation}
the envelope spectrum of the log is the weighted sum of the envelope spectra of
the sources, and each source's modulation lines appear unchanged. The field
$E_\mathrm{disp} = \sqrt{Z_0 S_\mathrm{disp}}$ does not have this property. Take
two sources $S_1 = a + b\cos 2\pi\nu_1 t$ and $S_2 = c + d\cos 2\pi\nu_2 t$ with
$A = a+c$ and $x(t) = b\cos 2\pi\nu_1 t + d\cos 2\pi\nu_2 t$, $|x| < A$. The
Taylor series of the square root gives
\begin{align}
\sqrt{A + x} &= \sqrt{A}\left(1 + \frac{x}{2A} - \frac{x^2}{8A^2} + \dots\right),\\
x^2 &= \frac{b^2+d^2}{2} + \frac{b^2}{2}\cos 4\pi\nu_1 t + \frac{d^2}{2}\cos 4\pi\nu_2 t \nonumber\\
 &\quad + bd\,\big[\cos 2\pi(\nu_1-\nu_2)t + \cos 2\pi(\nu_1+\nu_2)t\big],
\end{align}
so the spectrum of $E$ contains lines at $2\nu_1$, $2\nu_2$ and
$\nu_1\pm\nu_2$ that no source produces (intermodulation). The program
therefore analyses power density (W/m$^2$) by default (\texttt{--quantity power});
\texttt{field} and \texttt{db} are available for comparison only.

\subsection{Unit conversions}\label{sec:units}
\begin{itemize}
\item Power density from electric field (far field):
$S = E^2/Z_0$ with $Z_0 = \mu_0 c$. The program uses
$Z_0 = @@Z0@@\,\Omega$ (from the CODATA~2018 $\mu_0$); the CODATA~2022 value
is $376.730\,313\,412(59)\,\Omega$ \cite{B32}, a difference of
$7\times10^{-10}$. Narda's displays use round conversions near 377\,$\Omega$;
\texttt{--z0 377} reproduces them.
\item From magnetic field: $S = Z_0 H^2$ (far field only). Magnetic flux
density is analysed as $B^2$ (proportional to the magnetic energy density),
and EHP-50F fields as the field squared, because at 1\,Hz--400\,kHz the fields
are quasi-static and no plane-wave power density exists.
\item $1\,\mathrm{mW/cm^2} = 10^{-3}\,\mathrm{W}/10^{-4}\,\mathrm{m^2} = 10\,\mathrm{W/m^2}$;
$1\,\mathrm{\upmu W/cm^2} = 10^{-2}\,\mathrm{W/m^2}$.
\item From dB\textmu V/m: $E = 10^{(L-120)/20}$\,V/m, because
$L = 20\log_{10}(E/1\,\mathrm{\upmu V/m})$ and $1\,\mathrm{\upmu V} = 10^{-6}\,\mathrm{V}$.
\item From dBm at a 50\,$\Omega$ port: $P = V^2/R$ gives
\begin{align}
L_{\mathrm{dB\upmu V}} &= 20\log_{10}\frac{V}{1\,\mathrm{\upmu V}}
 = 10\log_{10}\frac{P R}{10^{-12}\,\mathrm{V^2}} \nonumber\\
 &= 10\log_{10}\frac{P}{1\,\mathrm{mW}} + 10\log_{10}\frac{10^{-3}\cdot 50}{10^{-12}}
 = L_\mathrm{dBm} + @@DBM_TO_DBUV@@,
\end{align}
rounded to 107\,dB, and with the antenna factor $\mathit{AF} = E/V$ in dB(1/m),
$L_{\mathrm{dB\upmu V/m}} = L_{\mathrm{dB\upmu V}} + \mathit{AF}$.
Without \texttt{--antenna-factor-db}, dBm levels are analysed as mW at the
analyzer port.
\end{itemize}

\subsection{Sampling, probe averaging and aliasing}\label{sec:sinc}
A log sampled at $f_s$ holds envelope content up to the Nyquist frequency
$\nu_N = f_s/2$, with resolution $\Delta\nu = f_s/N = 1/T_\mathrm{rec}$. Each
sample is an average over the integration time $T$. Modelling that average as
a moving (boxcar) average,
\begin{equation}
y(t) = \frac{1}{T}\int_{t-T}^{t} x(\tau)\,d\tau = (h * x)(t),\qquad
h(t) = \begin{cases} 1/T, & 0 \le t < T\\ 0, & \text{otherwise,}\end{cases}
\end{equation}
its frequency response is
\begin{align}
H(\nu) &= \int_0^T \frac{1}{T} e^{-i2\pi\nu t}\,dt
 = \frac{1 - e^{-i2\pi\nu T}}{i2\pi\nu T}
 = e^{-i\pi\nu T}\,\frac{e^{i\pi\nu T} - e^{-i\pi\nu T}}{2i\,\pi\nu T} \nonumber\\
&= e^{-i\pi\nu T}\,\frac{\sin \pi\nu T}{\pi\nu T} = e^{-i\pi\nu T}\sinc(\nu T),
\qquad |H(\nu)| = |\sinc(\nu T)|.
\label{eq:sinc}
\end{align}
For the EFD-4091 ($T = 265$\,ms) this gives $@@SINC_15@@$\,dB at 1.5\,Hz and
$@@SINC_25@@$\,dB at the Nyquist frequency 2.5\,Hz, with the first null at
$1/T = @@NULL_265@@$\,Hz. Sampling folds any content at $\nu$ to
\begin{equation}
\nu_\mathrm{alias} = \left|\,\nu - k f_s\right|,\qquad k = \operatorname{round}(\nu/f_s),
\end{equation}
attenuated only by $|H(\nu)|$: a 3\,Hz envelope line at $f_s = 5$\,Hz appears
at 2\,Hz, $@@SINC_3@@$\,dB down. The boxcar is a model; Narda publishes only a
nominal integration time. Figure~\ref{fig:probe} shows the model, and the
program reports in the warnings whether the first null lies above or below
$\nu_N$.

\subsection{Putting the log on a uniform grid}\label{sec:grid}
The FFT needs equally spaced samples. The sample interval is the mean of the
intervals that are not gaps (an interval longer than @@GAP@@ times the median
is a gap). The mean is used rather than the median because time stamps
rounded to a microsecond make the median of a 900\,Hz log 0.001111\,s, and a
grid 0.01\,\% off drifts in phase against the data, which adds side lines and
loses amplitude. When the stamps are within 1\,\% of uniform (median
$|\Delta t - \overline{\Delta t}|/\overline{\Delta t} < 0.01$), with no gaps and the
expected count, the samples are used as they are; otherwise they are linearly
interpolated onto the grid, gaps bridged. The gap-free blocks are recorded for
Welch, and the raw stamps are kept for Lomb--Scargle.

\subsection{Amplitude spectrum}\label{sec:fft}
With a window $w[n]$ and the mean removed, the DFT of the record is
\begin{equation}
X[k] = \sum_{n=0}^{N-1} w[n]\,\big(x[n]-\bar{x}\big)\,e^{-i2\pi kn/N},
\qquad \nu_k = k\,\frac{f_s}{N}.
\end{equation}
For a sinusoid $x[n] = A\cos(2\pi k_0 n/N + \varphi)$ on bin $k_0$,
\begin{equation}
X[k_0] = \frac{A}{2}e^{i\varphi}\sum_n w[n] + \frac{A}{2}e^{-i\varphi}\sum_n w[n]\,e^{-i4\pi k_0 n/N}
\approx \frac{A}{2}e^{i\varphi}\sum_n w[n],
\end{equation}
because the second sum is the window's transform $2k_0$ bins away from its
centre. Hence the single-sided amplitude
\begin{equation}
\hat{A}_k = \frac{2\,|X[k]|}{\sum_n w[n]}\quad(k \ne 0,\ k\ne N/2),
\label{eq:amplitude}
\end{equation}
and without the factor 2 at DC and Nyquist. $\sum_n w[n]/N$ is the window's
coherent gain (0.5 for Hann) \cite{R16}. A line between two bins reads low by
the scalloping loss, $@@HANN_SCALLOP@@$\,dB for Hann at half a bin (computed by
the build tool); the chirp-Z zoom removes it (Section~\ref{sec:czt}). Zero
padding interpolates the same spectrum; it does not improve the resolution
$f_s/N$.

\subsection{Welch power spectral density}\label{sec:welch}
The record is cut into $K$ segments of $L$ samples (\texttt{--nperseg}; by
default the largest power of two giving about seven averages) with 50\,\%
overlap, each windowed and transformed \cite{R11}:
\begin{equation}
\hat{P}(\nu_k) = \frac{c_k}{K f_s \sum_n w[n]^2}\sum_{m=0}^{K-1}
\left|\sum_{n=0}^{L-1} w[n]\big(x_m[n]-\bar{x}_m\big)e^{-i2\pi kn/L}\right|^2,
\qquad c_k = \begin{cases}1 & k = 0,\ L/2\\ 2 & \text{otherwise.}\end{cases}
\label{eq:welch}
\end{equation}
The normalisation follows from white noise of variance $\sigma^2$: then
$\mathrm{E}|X_m[k]|^2 = \sigma^2\sum_n w[n]^2$, so
$\hat{P} = 2\sigma^2/f_s$ and $\int_0^{f_s/2}\hat{P}\,d\nu = \sigma^2$
(Parseval). Averaging $K$ segments reduces the variance of the estimate roughly
$K$-fold at the price of resolution $f_s/L$. The program takes segments only
inside gap-free blocks and processes them 512 at a time, so the record may be a
disk-mapped array; the result equals \texttt{scipy.signal.welch} to rounding
error (Table~\ref{tab:selftest}).

\subsection{Chirp-Z zoom}\label{sec:czt}
The chirp-Z transform evaluates
\begin{equation}
X_k = \sum_{n=0}^{N-1} x[n]\,z_k^{-n},\qquad z_k = A\,W^{-k},\quad k = 0,\dots,M-1,
\end{equation}
on an arc of the $z$ plane \cite{R12}. For a zoom from $\nu_1$ to $\nu_2$ on the
unit circle, $A = e^{i2\pi\nu_1/f_s}$ and $W = e^{-i2\pi\Delta\nu/f_s}$ with
$\Delta\nu = (\nu_2-\nu_1)/(M-1)$. Bluestein's identity
$nk = \tfrac12\big[n^2 + k^2 - (k-n)^2\big]$ \cite{B19} turns the sum into a
convolution,
\begin{equation}
X_k = W^{k^2/2}\sum_{n=0}^{N-1}\Big(x[n]\,A^{-n}W^{n^2/2}\Big)\,W^{-(k-n)^2/2},
\end{equation}
which FFTs evaluate in $O\big((N+M)\log(N+M)\big)$ operations
(\texttt{scipy.signal.zoom\_fft} \cite{B31}). The program zooms $\pm16$ FFT bins
around the strongest line with 4096 points by default (1/128 of a bin). The
zoom samples the same windowed spectrum more densely: it locates a peak and
reads its amplitude without scalloping loss, but it does not separate two lines
closer than $f_s/N$. Figure~\ref{fig:zoom} shows the dense samples between the
FFT bins.

\subsection{Lomb--Scargle periodogram}\label{sec:lomb}
For irregular stamps $t_j$ (jitter, gaps), the classical Lomb--Scargle
periodogram fits a sinusoid at each frequency by least squares without
resampling \cite{R13,R14}. With $\omega = 2\pi\nu$, the offset $\tau$ is defined by
\begin{equation}
\tan 2\omega\tau = \frac{\sum_j \sin 2\omega t_j}{\sum_j \cos 2\omega t_j},
\end{equation}
which makes $\sum_j \cos\omega(t_j-\tau)\sin\omega(t_j-\tau) = 0$, and
\begin{equation}
P(\omega) = \frac12\left\{\frac{\big[\sum_j y_j\cos\omega(t_j-\tau)\big]^2}{\sum_j\cos^2\omega(t_j-\tau)}
 + \frac{\big[\sum_j y_j\sin\omega(t_j-\tau)\big]^2}{\sum_j\sin^2\omega(t_j-\tau)}\right\}.
\end{equation}
For $y_j = a\cos\omega(t_j-\tau) + b\sin\omega(t_j-\tau)$, $a^2+b^2 = A^2$, the
orthogonality gives $\sum_j y_j\cos(\cdot) = a\sum_j\cos^2(\cdot)$ and
$\sum_j y_j\sin(\cdot) = b\sum_j\sin^2(\cdot)$, so
$P = \tfrac12\big(a^2\sum\cos^2 + b^2\sum\sin^2\big)$. With samples spread over
many cycles $\sum\cos^2 \approx \sum\sin^2 \approx N/2$, hence
\begin{equation}
P \approx \frac{N A^2}{4}\quad\Longrightarrow\quad \hat{A} = \sqrt{\frac{4P}{N}},
\end{equation}
the amplitude the program reports, directly comparable with \eqref{eq:amplitude}.
It runs automatically when more than 0.1\,\% of the grid lies in gaps or the
jitter exceeds 1\,\% (\texttt{--lomb auto}), in chunks of frequencies to bound
memory.

\subsection{Envelope spectrogram}
For records of at least 16 Welch segments, the envelope is also shown as a
short-time PSD (time $\times$ envelope frequency), computed with
\texttt{scipy.signal.ShortTimeFFT} in one-sided, PSD-scaled form \cite{B30}, the
hop chosen so that at most 2000 slices are produced and slices hanging over the
ends omitted. It shows whether a modulation is steady or comes and goes.

\subsection{Probe correction}\label{sec:correction}
\texttt{--correct-probe} divides out the averaging \eqref{eq:sinc} where that is
safe. A plain inverse $1/|H|$ grows without bound near the null at $1/T$ and
amplifies noise, so the gain is limited to $g_\mathrm{max}$ (\texttt{--max-boost-db},
default 12\,dB, $g_\mathrm{max} = @@G_MAX@@$) with a Wiener-type form:
\begin{equation}
G(h) = \frac{h}{h^2 + \varepsilon},\qquad h = |H(\nu)|.
\end{equation}
Its maximum over $h$ follows from $dG/dh = (\varepsilon - h^2)/(h^2+\varepsilon)^2 = 0$:
$h = \sqrt{\varepsilon}$ and $G_\mathrm{max} = 1/(2\sqrt{\varepsilon})$. Setting
$G_\mathrm{max} = g_\mathrm{max}$ gives
\begin{equation}
\varepsilon = \frac{1}{4 g_\mathrm{max}^2} = @@EPSILON@@ .
\end{equation}
Where $h \ge 1/g_\mathrm{max}$ the exact inverse $1/h$ ($\le g_\mathrm{max}$) is
used, below it $G(h)$; bins at or beyond the first null ($\nu T \ge 1$) are left
empty (NaN). At the switch point $h = 1/g_\mathrm{max}$ the two gains are $g_\mathrm{max}$
and $G = \tfrac45 g_\mathrm{max}$, a step of @@SWITCH_STEP@@\,dB
(Section~\ref{sec:limits}). For the 5\,Hz probes $|H| > 1/g_\mathrm{max}$ up to
the Nyquist frequency ($@@SINC_25@@$\,dB at 2.5\,Hz), so the exact inverse
applies throughout; the step can appear only for probes whose first null lies
below their Nyquist frequency (EFD-1891 fast: @@EFD1891_NULL@@\,Hz against
@@EFD1891_NYQ@@\,Hz).

\subsection{Peaks and their exact frequency}
Peaks are local maxima standing at least \texttt{--snr} times (default 6) above
the median spectrum level, with a prominence of $(\mathrm{snr}-1)$ times the
median, within \texttt{--dyn-range-db} (default 50\,dB) of the strongest peak,
at most 12, DC and the first bin excluded. Each peak frequency is refined by a
parabola through the logarithms of the three bins around it,
$\alpha = \ln\hat{A}_{k-1}$, $\beta = \ln\hat{A}_k$, $\gamma = \ln\hat{A}_{k+1}$.
Fitting $p(x) = a x^2 + bx + c$ through $(-1,\alpha)$, $(0,\beta)$,
$(1,\gamma)$ gives $c = \beta$, $b = (\gamma-\alpha)/2$,
$a = (\alpha - 2\beta + \gamma)/2$, and the vertex
\begin{equation}
\delta = -\frac{b}{2a} = \frac{1}{2}\,\frac{\alpha - \gamma}{\alpha - 2\beta + \gamma},
\qquad \hat{\nu} = \nu_k + \delta\,\Delta\nu .
\end{equation}
The parabola is exact for a Gaussian window and a close approximation for
Hann. The CZT then gives the frequency and amplitude of the strongest line
(\texttt{f\_hz\_czt}, \texttt{amp\_czt} in the summary).

\subsection{Harmonic families and rotation rate}
A rotating antenna passes its beam over the probe once per turn, which gives a
line at the rotation frequency $\nu_0$ and harmonics $k\nu_0$ from the beam shape.
The program groups peaks into families: for each candidate $\nu_0$ (itself a
peak above two bins), the members are the peaks within
$\max(1.5\,\Delta\nu,\,0.01\,\nu_0)$ of a whole multiple $k\nu_0$, $k\ge1$; the
family with the largest total amplitude is taken, its members removed, and
the search repeated (three families at most). Each family is reported with
$\nu_0$, the period $1/\nu_0$ and the rate $60\,\nu_0$ in rpm. In
Figure~\ref{fig:amplitude} the 12\,rpm family (0.2\,Hz) and the separate
0.7\,Hz source are found this way.

\subsection{Spectrograms: envelope spectrum per frequency bin}\label{sec:spectrogram}
For a spectrogram $L(t_m, f_j)$ (SignalShark, EHP-50 TS folder), the levels are
converted to linear power $S(t_m, f_j)$ (Section~\ref{sec:units}), put on a
uniform time grid at the mean spectrum interval, and transformed along time for
every bin $j$ at once:
\begin{equation}
\hat{A}_j(\nu_k) = \frac{2}{\sum_m w[m]}\left|\sum_m w[m]\big(S(t_m,f_j) - \bar{S}_j\big)e^{-i2\pi km/N_t}\right| .
\end{equation}
The \emph{modulation map} (Figure~\ref{fig:modmap}) shows this in dB relative to
its maximum; the strongest envelope frequency of every bin is plotted
separately. In addition, \emph{channels} are analysed like probe logs, using the
sum of linear power over a band: the whole span (\texttt{total}) and the
strongest spectral peaks ($\pm2$ bins, \texttt{--rf-channels auto:N}) or bands
given in Hz (\texttt{--rf-channels f1:f2,f3:f4}). Images larger than
@@MAX_IMAGE@@ pixels per side are reduced by taking the maximum of neighbouring
cells for the Veusz document; the full-resolution arrays go to the
\texttt{.npz} file.
"""

SECTION_CLI = r"""
% =============================================================================
%    6  COMMAND-LINE REFERENCE
% =============================================================================
\section{Command-line reference}\label{sec:cli}
Table~\ref{tab:options} is generated from the program's own argument parser,
so it always matches \texttt{python} \path{emf_envelope_fft_v@@VERSION_US@@.py} \texttt{--help}.

@@TABLE_OPTIONS@@
"""

SECTION_OUTPUTS = r"""
% =============================================================================
%    7  OUTPUT FILES
% =============================================================================
\section{Output files}\label{sec:outputs}
Results go to the folder \path{<stem>_fft} beside the input, or to \texttt{--out}.

@@TABLE_OUTPUTS@@

\subsection{The Veusz document}
The \texttt{.vszh5} file is Veusz's native HDF5 format, written directly by
\path{vszh5_writer.py} (Appendix~\ref{app:writer}): the datasets with their types
and the plots as the Veusz command script, so the file opens with \emph{File
$\rightarrow$ Open} and every plot can be edited there. It is written to
\path{<name>.part} and moved into place at the end, so an open copy is never
half-written. Tables~\ref{tab:pages} and~\ref{tab:overview} list the pages; the
page titles are also the PDF bookmark titles.

@@TABLE_PAGES@@

@@TABLE_OVERVIEW@@

\subsection{Rendering to PDF and PNG}
With \texttt{--render}, \texttt{vszh5\_writer.render\_pages} drives Veusz in
listen mode and writes one multipage PDF and one PNG per page
(\path{<stem>_envelope_fft_pNN_<page>.png}). The PDF gets a bookmark tree: the
pages of a single log as a flat list; for a spectrogram an \emph{Overview}
entry, then one entry per channel (\emph{Channel 0: \dots}) holding its pages.

\subsection{Summary file}
\path{<stem>_summary.json} holds the input and quantity (\texttt{unit\_in},
\texttt{quantity}, \texttt{quantity\_note}), timing (\texttt{fs\_hz},
\texttt{nyquist\_hz}, \texttt{samples}, \texttt{duration\_s},
\texttt{resolution\_hz}, \texttt{start}, \texttt{t\_int\_s}), the Welch settings,
\texttt{peaks} (\texttt{f\_hz}, \texttt{amp}, \texttt{snr\_db}, and
\texttt{f\_hz\_czt}, \texttt{amp\_czt} for the zoomed line),
\texttt{harmonic\_families} (\texttt{f0\_hz}, \texttt{period\_s}, \texttt{rpm},
\texttt{harmonics}), the \texttt{warnings}, the compute back end and the program
version. For a spectrogram it holds the frequency range and bin count, the
spectrum rate and one such block per channel.

\subsection{Examples}
Figures~\ref{fig:time}--\ref{fig:modmap} were rendered by this program from the
synthetic files of its self-test.

@@FIGURE_TIME@@
@@FIGURE_AMPLITUDE@@
@@FIGURE_ZOOM@@
@@FIGURE_PROBE@@
@@FIGURE_SPECTROGRAM@@
@@FIGURE_MODMAP@@
\clearpage
"""

SECTION_LIVE = r"""
% =============================================================================
%    8  LIVE MODE
% =============================================================================
\section{Live mode}\label{sec:live}
\texttt{--live FILE} follows a text file that another program appends to. New
complete lines are read every \texttt{--update} seconds (default 1\,s; an
unfinished last line waits for the next poll), kept in a ring buffer twice the
size of the analysis window \texttt{--window-s} (default 120\,s), and the
envelope amplitude spectrum and Welch PSD of the latest window are recomputed
and drawn. Every sample is also appended to \path{<file>.live.f64}, raw float64
pairs (time, value) that can be read back with
\verb|np.fromfile(path).reshape(-1, 2)|. \texttt{--no-gui} prints the strongest
lines and families instead; \texttt{--live-seconds} stops after a time.

@@TABLE_MENUS@@

Neither FieldMan nor Narda-TSX documents a continuously written file or a
streaming interface for the broadband probes \cite{R5,R9}, so whether live mode
works with them depends on how they write data; it was tested with a file
written in real time by a script. NBM-550 remote output (\texttt{MEAS\_START},
5, 50 or 60 samples per second \cite{R6}) logged to a file by another tool is a
documented route.

@@FIGURE_LIVE@@
"""

SECTION_MEMORY = r"""
% =============================================================================
%    9  MEMORY, PARALLEL PROCESSING AND GPU
% =============================================================================
\section{Memory, parallel processing and GPU}\label{sec:memory}
\begin{itemize}
\item \textbf{Spill to disk}: a column longer than @@SPILL@@ samples is moved
from RAM to a temporary raw file and used as a memory map; the files are
deleted when the program exits. A 2.4-million-row, 900\,Hz test log was
analysed this way.
\item \textbf{Chunks and batches}: text files are read @@CHUNK@@ rows at a time;
Welch processes 512 segments at a time; Lomb--Scargle about 64\,MiB of
frequencies at a time; the per-bin modulation spectra in batches of about
256\,MiB.
\item \textbf{Freeing memory}: \texttt{flush\_memory()} runs the garbage
collector and empties the CuPy memory pools; batch mode calls it after each
file, and the live window's \emph{File $\rightarrow$ Clear buffer} too.
\texttt{--pickle} also writes the whole result object to
\path{<stem>_result.pkl} (load it with \texttt{load\_pickle}, only from files you
trust).
\item \textbf{Parallel}: \texttt{--jobs N} analyses N files in separate processes;
each process then uses one FFT thread so that the cores are not
oversubscribed. With one job, SciPy's FFTs use every core.
\item \textbf{GPU}: \texttt{--gpu} moves the FFTs, Welch segments, modulation
spectra and Lomb--Scargle sums to an NVIDIA GPU through CuPy \cite{B27}. Without
CuPy or a CUDA device the program continues on the CPU and says why in the
summary (\texttt{backend}).
\end{itemize}
"""

SECTION_SPYDER = r"""
% =============================================================================
%    10  WORKING IN SPYDER
% =============================================================================
\section{Working in Spyder}\label{sec:spyder}
The script is organised in Spyder cells, each opened by a banner
\verb|# %% ====| and a title line. Table~\ref{tab:cells} lists them with the
functions and classes each defines (generated from the script). Run the cells
from the top; the last cell is a commented scratch cell:
\begin{Verbatim}
opts = Options(probe="EFD-4091", correct_probe=True, lomb="on")
print(inspect_input(r"C:\path\to\export.csv", opts))
series = load_any(r"C:\path\to\export.csv", opts)
result = analyse_timeseries(series, opts)
print(result.peaks[:5], result.families)
write_outputs(result, Path(r"C:\path\to\out"), opts)
flush_memory()
\end{Verbatim}

@@TABLE_CELLS@@
"""

SECTION_VERIFICATION = r"""
% =============================================================================
%    11  VERIFICATION
% =============================================================================
\section{Verification}\label{sec:verification}
\texttt{--selftest} checks the estimators against known answers and then runs
every reader on synthetic files written in the styles expected from the
instruments (semicolon and decimal comma with German dates, a 1\,s NBM timer
log, an EHP-50 TS folder, a SignalShark-like HDF5 file and a converter CSV).
Table~\ref{tab:selftest} is the result of the run made while building this
manual.

@@TABLE_SELFTEST@@

Further checks made for version @@VERSION@@:
\begin{itemize}
\item Every summary and CSV of the self-test compared with version 0.0.1: all
numbers identical (two summary keys of the spectrogram result were renamed,
see Appendix~\ref{app:history}).
\item Rendering in Veusz 4.2.1 of a probe log (6 pages) and a SignalShark
spectrogram (16 pages): date axis, line styles, markers, colour bars and the
bookmark tree checked by eye and with pypdf.
\item Live mode, console and window (light and dark), following a file written
at 50 samples per second with 2\,Hz and 7\,Hz tones: both found; snapshot saved.
\item A 2.4-million-row 900\,Hz log through the spill-to-disk path: lines at
37.0 and 120.0\,Hz found exactly.
\item Three files with \texttt{--jobs 3 --gpu} on a machine without CuPy: all
analysed, CPU fallback reported.
\end{itemize}
"""

SECTION_LIMITS = r"""
% =============================================================================
%    12  LIMITATIONS AND KNOWN ISSUES
% =============================================================================
\section{Limitations and known issues}\label{sec:limits}
\begin{enumerate}
\item The readers are heuristic until real exports of FieldMan, Narda-TSX,
NBM-TS, EHP-50 TS and SignalShark have been examined; use \texttt{--inspect}.
\item ``EFD-4091E'' is treated as the EFD-4091; no datasheet for an E variant
was found.
\item The probe averaging is modelled as a boxcar of the nominal integration
time; the EF\,0691's integration time is not published, so $1/f_s$ is assumed.
\item The probe correction switches from the exact inverse to the Wiener-type
gain at $|H| = 1/g_\mathrm{max}$ with a step of @@SWITCH_STEP@@\,dB
(Section~\ref{sec:correction}); it matters only for probes whose first null lies
below their Nyquist frequency. A smooth transition is planned.
\item Content above the Nyquist frequency aliases; nothing in the data can
remove it after the fact.
\item Above the True-RMS range the diodes leave square-law operation and powers
no longer add; the envelope spectrum is then distorted (a warning is given).
\item The time page plots every sample, so very long logs make large PDFs.
\item Live mode depends on how the instrument software writes its files
(Section~\ref{sec:live}).
\end{enumerate}
"""

SECTION_TROUBLESHOOTING = r"""
% =============================================================================
%    13  TROUBLESHOOTING
% =============================================================================
\section{Troubleshooting}\label{sec:troubleshooting}

@@TABLE_TROUBLE@@
"""


# %% ===========================================================================
#    MANUAL TEXT: APPENDICES AND REFERENCES
# =============================================================================
APPENDIX_MODULES = r"""
% =============================================================================
%    APPENDIX A  PYTHON MODULES USED
% =============================================================================
\clearpage
\appendix
\section{Python modules used}\label{app:modules}
This appendix lists every Python module the analyzer uses, the functions,
classes and methods it calls, how it calls them and why that module was
chosen. Table~\ref{tab:modules} is the overview; the following subsections
give the details, module by module. Versions are those of the tested
environment (@@DATE@@).

@@TABLE_MODULES@@

\subsection{NumPy}\label{app:numpy}
NumPy \cite{B20} holds every array of the program. It was chosen because SciPy,
pandas, h5py, CuPy and pyqtgraph all exchange data as NumPy arrays, so no
conversion is needed anywhere.

@@TABLE_NUMPY@@

\subsection{SciPy}\label{app:scipy}
SciPy \cite{R10} supplies the spectral estimators. It provides, in one tested
library, everything the problem needs: real FFTs with multithreading, standard
windows, the chirp-Z zoom, the short-time FFT and peak finding. scikit-rf
\cite{R15} was considered and not used: it is built for network parameters
(S-parameters, Touchstone files, calibration), not for spectral analysis of time
series.

@@TABLE_SCIPY@@

\subsection{pandas and openpyxl}\label{app:pandas}
pandas \cite{B21} reads the text and Excel exports. Its CSV reader is fast (C
engine), reads in chunks, and its date parser copes with the many date and time
formats instrument software writes \cite{B33}. openpyxl \cite{B34} is not imported by the
program; pandas uses it as the engine for \texttt{.xlsx} files.

@@TABLE_PANDAS@@

\subsection{h5py}\label{app:h5py}
h5py \cite{B22} reads SignalShark \texttt{.h5} files and, through
\path{vszh5_writer.py}, writes the Veusz \texttt{.vszh5} documents, which are
HDF5 files. It gives direct access to groups, datasets, attributes and object
references, which the Veusz format needs.

@@TABLE_H5PY@@

\subsection{vszh5\_writer (the author's module, @@WRITER_VERSION@@)}\label{app:writer}
\path{vszh5_writer.py} writes Veusz's native HDF5 document format without
Veusz, and renders it to PDF and PNG when Veusz is installed. It came from the
author's \path{isp_speed_monitor.py} and the QuickSyn package (0.0.10); for this
program it was extended to 0.0.11 with two-dimensional datasets and plot-page
helpers, without changing any existing call; the 2-D layout follows the Veusz source \cite{B29}. The analyzer uses it for every
Veusz document, so the pages look the same as in the author's other programs.

@@TABLE_WRITER@@

\subsection{Qt.py, PySide6 and pyqtgraph}\label{app:qt}
The live window is written against Qt.py \cite{B24}, a thin layer that exposes
one Qt API over PySide6 or PyQt; the program asks for PySide6 \cite{B25}
(\texttt{QT\_PREFERRED\_BINDING}). pyqtgraph \cite{B26} draws the plots: it is
built for fast, repeated updates of large arrays, which a live display needs,
and runs on the same Qt binding.

@@TABLE_QT@@

\subsection{CuPy (optional)}\label{app:cupy}
CuPy \cite{B27} offers the NumPy interface on NVIDIA GPUs, so the same code runs
on either device through the program's \texttt{Backend} class (its \texttt{xp}
attribute is \texttt{numpy} or \texttt{cupy}). It is imported only when
\texttt{--gpu} is given.

@@TABLE_CUPY@@

\subsection{pypdf and Veusz (rendering only)}\label{app:render}
Neither is imported by the analyzer itself; \path{vszh5_writer.py} uses them
when \texttt{--render} is given, and the manual builder uses pypdf \cite{B28} to check the
bookmarks of this PDF.

@@TABLE_RENDER@@

\subsection{Python standard library}\label{app:stdlib}
@@TABLE_STDLIB@@
"""

APPENDIX_HISTORY = r"""
% =============================================================================
%    APPENDIX B  REVISION HISTORY
% =============================================================================
\section{Revision history}\label{app:history}
@@TABLE_HISTORY@@
"""

REFERENCES = r"""
% =============================================================================
%    REFERENCES (IEEE style)
% =============================================================================
\clearpage
\phantomsection
\addcontentsline{toc}{section}{References}
\renewcommand{\refname}{References}
\begin{thebibliography}{99}\small
\bibitem{R1} Narda Safety Test Solutions GmbH, ``Datasheet Probe EFD-4091,'' NSTS 0523-E0399A, 2023. [Online]. Available: \url{https://www.atecorp.com/getmedia/48a83a03-af45-41d0-820c-ecdb46ba1437/Narda_EFD-4091-datasheet.pdf}
\bibitem{R2} Narda Safety Test Solutions GmbH, ``Datasheet Probe EFD-0691,'' NSTS 0624-E0387B, 2024. [Online]. Available: \url{https://www.atecorp.com/getmedia/84e296e2-1bd2-4861-8a1f-e905f39d4910/Datasheet_EFD-0691.pdf}
\bibitem{R3} Narda Safety Test Solutions GmbH, ``Datasheet Probe EFD-9091,'' NSTS 0523-E0405A, 2023. [Online]. Available: \url{https://www.atecorp.com/getmedia/c56e0776-d855-4d49-9081-ff316ecaf68a/Datasheet_EFD-9091.pdf}
\bibitem{R4} Narda Safety Test Solutions GmbH, ``Datasheet Probe EFD-1891,'' NSTS 0723-E0398A, 2023. [Online]. Available: \url{https://www.atecorp.com/getmedia/d5ed148e-2dfc-4f3c-afa4-2b306fb7a781/Narda_EFD-1891-datasheet.pdf}
\bibitem{R5} Narda Safety Test Solutions GmbH, ``Datasheet Narda FieldMan,'' NSTS 0925-E0370D, 2025. [Online]. Available: \url{https://www.atecorp.com/getmedia/5511a8ac-b386-434f-bac9-fd22d18e2f48/Narda-Fieldman-Datasheet-2025.pdf}
\bibitem{R6} Narda Safety Test Solutions, ``NBM-550 Remote Control,'' V1.0. [Online]. Available: \url{https://wiki.radimation.com/wiki/images/7/7b/NBM-550_Remote_Control_V1_0.pdf}
\bibitem{R7} Narda Safety Test Solutions S.r.l., ``EHP-50F User's Manual,'' EHP50FEN-10107-1.73, 2021. [Online]. Available: \url{https://atecorp.com/getmedia/d53b58ae-844a-4a2d-b84e-6a9f98be805a/narda-ehp-50f-operating-manual.pdf}
\bibitem{R8} Narda Safety Test Solutions, ``SignalShark options and scripts.'' [Online]. Available: \url{https://www.narda-sts.com/en/products/receivers-/-direction-finders-/-spectrum-analyzers/signalshark-optionen/}
\bibitem{R9} Narda Safety Test Solutions, ``PC software Narda-TSX.'' [Online]. Available: \url{https://www.narda-sts.com/en/products/emc-products-and-streaming-solutions/pc-software-narda-tsx/}
\bibitem{R10} P. Virtanen \emph{et al.}, ``SciPy 1.0: Fundamental algorithms for scientific computing in Python,'' \emph{Nature Methods}, vol.~17, pp.~261--272, 2020, doi: \href{https://doi.org/10.1038/s41592-019-0686-2}{10.1038/s41592-019-0686-2}.
\bibitem{R11} P. D. Welch, ``The use of fast Fourier transform for the estimation of power spectra: A method based on time averaging over short, modified periodograms,'' \emph{IEEE Trans. Audio Electroacoust.}, vol.~AU-15, no.~2, pp.~70--73, Jun. 1967, doi: \href{https://doi.org/10.1109/TAU.1967.1161901}{10.1109/TAU.1967.1161901}.
\bibitem{R12} L. R. Rabiner, R. W. Schafer, and C. M. Rader, ``The chirp z-transform algorithm,'' \emph{IEEE Trans. Audio Electroacoust.}, vol.~AU-17, no.~2, pp.~86--92, Jun. 1969, doi: \href{https://doi.org/10.1109/TAU.1969.1162034}{10.1109/TAU.1969.1162034}.
\bibitem{R13} J. D. Scargle, ``Studies in astronomical time series analysis. II. Statistical aspects of spectral analysis of unevenly spaced data,'' \emph{Astrophys. J.}, vol.~263, pp.~835--853, 1982, doi: \href{https://doi.org/10.1086/160554}{10.1086/160554}.
\bibitem{R14} J. T. VanderPlas, ``Understanding the Lomb--Scargle periodogram,'' \emph{Astrophys. J. Suppl. Ser.}, vol.~236, no.~1, 2018, doi: \href{https://doi.org/10.3847/1538-4365/aab766}{10.3847/1538-4365/aab766}.
\bibitem{R15} scikit-rf developers, ``scikit-rf documentation.'' [Online]. Available: \url{https://scikit-rf.readthedocs.io/}
\bibitem{R16} F. J. Harris, ``On the use of windows for harmonic analysis with the discrete Fourier transform,'' \emph{Proc. IEEE}, vol.~66, no.~1, pp.~51--83, Jan. 1978, doi: \href{https://doi.org/10.1109/PROC.1978.10837}{10.1109/PROC.1978.10837}.
\bibitem{R17} \emph{IEEE Standard for Calibration of Electromagnetic Field Sensors and Probes (Excluding Antennas) from 9 kHz to 40 GHz}, IEEE Std 1309-2013. [Online]. Available: \url{https://standards.ieee.org/ieee/1309/5031}
\bibitem{R18} \emph{Determination of RF field strength, power density and SAR in the vicinity of base stations for the purpose of evaluating human exposure}, IEC 62232:2025. [Online]. Available: \url{https://webstore.iec.ch/en/publication/89073}
\bibitem{B19} L. I. Bluestein, ``A linear filtering approach to the computation of discrete Fourier transform,'' \emph{IEEE Trans. Audio Electroacoust.}, vol.~18, no.~4, pp.~451--455, Dec. 1970, doi: \href{https://doi.org/10.1109/TAU.1970.1162132}{10.1109/TAU.1970.1162132}.
\bibitem{B20} C. R. Harris \emph{et al.}, ``Array programming with NumPy,'' \emph{Nature}, vol.~585, pp.~357--362, 2020, doi: \href{https://doi.org/10.1038/s41586-020-2649-2}{10.1038/s41586-020-2649-2}.
\bibitem{B21} W. McKinney, ``Data structures for statistical computing in Python,'' in \emph{Proc. 9th Python in Science Conf. (SciPy 2010)}, S. van der Walt and J. Millman, Eds., 2010, pp.~56--61, doi: \href{https://doi.org/10.25080/Majora-92bf1922-00a}{10.25080/Majora-92bf1922-00a}.
\bibitem{B22} h5py developers, ``HDF5 for Python (h5py) documentation.'' [Online]. Available: \url{https://docs.h5py.org/}
\bibitem{B23} J. Sanders \emph{et al.}, ``Veusz --- a scientific plotting package.'' [Online]. Available: \url{https://veusz.github.io/}
\bibitem{B24} M. Ottosson \emph{et al.}, ``Qt.py: Minimal Python 2 \& 3 shim around all Qt bindings.'' [Online]. Available: \url{https://github.com/mottosso/Qt.py}
\bibitem{B25} The Qt Company, ``Qt for Python (PySide6) documentation.'' [Online]. Available: \url{https://doc.qt.io/qtforpython-6/}
\bibitem{B26} pyqtgraph developers, ``PyQtGraph: Scientific graphics and GUI library for Python.'' [Online]. Available: \url{https://www.pyqtgraph.org/}
\bibitem{B27} R. Okuta, Y. Unno, D. Nishino, S. Hido, and C. Loomis, ``CuPy: A NumPy-compatible library for NVIDIA GPU calculations,'' in \emph{Proc. Workshop on Machine Learning Systems (LearningSys), 31st Conf. Neural Information Processing Systems (NIPS)}, 2017. [Online]. Available: \url{http://learningsys.org/nips17/assets/papers/paper_16.pdf}
\bibitem{B28} pypdf developers, ``pypdf documentation.'' [Online]. Available: \url{https://pypdf.readthedocs.io/}
\bibitem{B29} Veusz developers, ``Veusz 4.2.1 source (document/doc.py, document/loader.py, datasets/twod.py),'' 2024. [Online]. Available: \url{https://pypi.org/project/veusz/4.2.1/}
\bibitem{B30} SciPy developers, ``scipy.signal.ShortTimeFFT.'' [Online]. Available: \url{https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.ShortTimeFFT.html}
\bibitem{B31} SciPy developers, ``scipy.signal.zoom\_fft.'' [Online]. Available: \url{https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.zoom_fft.html}
\bibitem{B32} P. J. Mohr, D. B. Newell, B. N. Taylor, and E. Tiesinga, ``CODATA recommended values of the fundamental physical constants: 2022,'' arXiv:2409.03787, 2024. [Online]. Available: \url{https://arxiv.org/abs/2409.03787}
\bibitem{B33} pandas developers, ``pandas documentation.'' [Online]. Available: \url{https://pandas.pydata.org/docs/}
\bibitem{B34} openpyxl developers, ``openpyxl documentation.'' [Online]. Available: \url{https://openpyxl.readthedocs.io/}
\bibitem{B35} Spyder project, ``Spyder --- the scientific Python development environment.'' [Online]. Available: \url{https://www.spyder-ide.org/}
\bibitem{B36} conda-forge, ``Miniforge (conda and mamba).'' [Online]. Available: \url{https://github.com/conda-forge/miniforge}
\bibitem{B37} H. Oberdiek and the LaTeX Project, ``The bookmark package.'' [Online]. Available: \url{https://ctan.org/pkg/bookmark}
\end{thebibliography}

\end{document}
"""


# %% ===========================================================================
#    STATIC TABLE CONTENT (descriptions written by hand)
# =============================================================================
def static_tables(analyzer: ModuleType) -> dict[str, str]:
    """Tables whose content is descriptive text (titles still come from the code)."""
    tables: dict[str, str] = {}
    tables["READERS"] = longtable(
        "Readers and how the input is recognised.", "tab:readers",
        [("\\texttt{--source}", 0.14), ("Instrument / software", 0.22), ("Files", 0.16),
         ("Auto-detected when", 0.24), ("Result", 0.20)],
        [[tt("fieldman, tsx"), tex("FieldMan or Narda-TSX with EFD-4091, -0691, -9091, -1891"),
          tex(".csv .txt"), tex("default for text files"), tex("time series (+ X/Y/Z)")],
         [tt("nbm"), tex("NBM-550 / NBM-TS with EF 0691"), tex(".csv .txt"),
          tex("a column named 'Result ...'"), tex("time series")],
         [tt("xlsx"), tex("any of the above saved as Excel"), tex(".xlsx .xls"),
          tex("by extension"), tex("time series")],
         [tt("ehp"), tex("EHP-50 TS with EHP-50F (1 Hz - 400 kHz)"),
          tex("folder, ") + path_tex("hh_mm_ss_cc.TXT"), tex("a folder, or the EHP file name"),
          tex("spectrogram (folder), spectrum, or time series (logger file)")],
         [tt("signalshark"), tex("SignalShark"), tex(".h5 .hdf5; converter .csv"),
          tex(".h5 extension; 8+ numeric column names or a frequency column"),
          tex("spectrogram (or level time series)")]])
    tables["OUTPUTS"] = longtable(
        "Output files (folder \\texttt{<stem>\\_fft}).", "tab:outputs",
        [("File", 0.36), ("Content", 0.44), ("Written", 0.16)],
        [[path_tex("<stem>_envelope_fft.vszh5"), tex("Veusz document: all datasets and pages"), tex("always")],
         [path_tex("<name>_amplitude.csv"), tex("f_hz, amplitude [, amplitude_corrected, amplitude_X/Y/Z]"),
          tex("per series / channel")],
         [path_tex("<name>_welch.csv"), tex("f_hz, psd (unit^2/Hz)"), tex("per series / channel")],
         [path_tex("<name>_zoom.csv"), tex("f_hz, amplitude (chirp-Z)"), tex("when a peak or --zoom")],
         [path_tex("<name>_lomb.csv"), tex("f_hz, amplitude (Lomb-Scargle)"), tex("gaps/jitter or --lomb on")],
         [path_tex("<stem>_modulation.npz"),
          tex("full-resolution spectrum, modulation image and dominant modulation per bin"),
          tex("spectrograms")],
         [path_tex("<stem>_summary.json"), tex("peaks, families, warnings, settings"), tex("always")],
         [path_tex("<stem>_result.pkl"), tex("the whole result object"), tex("--pickle")],
         [path_tex("<stem>_envelope_fft.pdf"), tex("all pages, bookmarked"), tex("--render")],
         [path_tex("<stem>_envelope_fft_pNN_<page>.png"), tex("one image per page (150 dpi)"),
          tex("--render")],
         [path_tex("<input>.live.f64"), tex("live mode: every sample, float64 (t, value) pairs"),
          tex("--live")]])
    page_text = {
        "time": "field strength against time (a date axis when the start time is known)",
        "amplitude": "single-sided amplitude spectrum, log scale; probe-corrected and X/Y/Z traces",
        "welch": "Welch PSD in dB, number and length of segments in the title",
        "zoom": "chirp-Z samples (line) and FFT bins (markers) around the strongest line",
        "lomb": "Lomb-Scargle amplitude from the raw stamps against the FFT",
        "probe": "|sinc(f T)| of the probe averaging in dB",
        "spectrogram": "image: time x envelope frequency, PSD in dB (60 dB range)",
    }
    tables["PAGES"] = longtable(
        "Pages written for every time series (prefix \\texttt{ch<k>\\_} for spectrogram channels).",
        "tab:pages", [("Page", 0.14), ("Bookmark title", 0.30), ("Content", 0.40), ("When", 0.12)],
        [[tt(name), tex(analyzer.SERIES_PAGE_TITLES[name]), tex(page_text[name]),
          tex({"zoom": "a peak", "lomb": "Lomb on", "probe": "T known",
               "spectrogram": "long logs"}.get(name, "always"))]
         for name in analyzer.SERIES_PAGE_TITLES])
    overview_text = {
        "spectrum": "mean and max-hold level per frequency (dB re W/m^2 or as given)",
        "spectrogram": "image: frequency x time, level in dB",
        "modulation_map": "image: frequency x envelope frequency, dB rel. maximum",
        "dominant_modulation": "strongest envelope frequency of every bin",
    }
    tables["OVERVIEW"] = longtable(
        "Overview pages of a spectrogram (SignalShark, EHP-50 TS), before the channel pages.",
        "tab:overview", [("Page", 0.22), ("Bookmark title", 0.34), ("Content", 0.40)],
        [[tt(name), tex(analyzer.OVERVIEW_PAGE_TITLES[name]), tex(overview_text[name])]
         for name in analyzer.OVERVIEW_PAGE_TITLES])
    tables["MENUS"] = longtable(
        "Menus of the live window.", "tab:menus",
        [("Menu", 0.12), ("Entry", 0.30), ("Action", 0.54)],
        [[tex("File"), tex("Save snapshot (.vszh5)"),
          tex("full analysis of the current window; writes the usual output files")],
         [tex("File"), tex("Clear buffer (free RAM)"), tex("empties the ring buffer, runs flush_memory()")],
         [tex("File"), tex("Quit"), tex("closes the window")],
         [tex("View"), tex("Light / Dark"), tex("palette of the window and plot colours")],
         [tex("Analysis"), tex("Correct probe response"), tex("applies --correct-probe live")]])
    tables["TROUBLE"] = longtable(
        "Troubleshooting.", "tab:trouble", [("Symptom", 0.30), ("Likely cause", 0.32), ("Remedy", 0.34)],
        [[tex("'no value column found'"), tex("unusual column names"), tex("--value-col NAME (or index)")],
         [tex("time axis wrong or 'cannot parse'"), tex("unusual date format, month/day order"),
          tex("--time-col, --dayfirst; check with --inspect")],
         [tex("numbers 1000x too large"), tex("decimal comma read as thousands"), tex("--decimal , --sep ;")],
         [tex("'measured sample rate differs'"), tex("logging interval longer than the probe rate"),
          tex("expected with timer logs; Nyquist is then lower")],
         [tex("lines at 2f, f1+f2"), tex("--quantity field"), tex("use the default --quantity power")],
         [tex("SignalShark axes look wrong"), tex("unknown .h5 layout"),
          tex("--inspect, then --h5-level/--h5-freq/--h5-time")],
         [tex("dBm levels, no W/m^2"), tex("no antenna factor"), tex("--antenna-factor-db AF")],
         [tex("--render: 'Veusz not found'"), tex("Veusz not on PATH"),
          tex("set VEUSZ_EXE to veusz.exe; the .vszh5 is written anyway")],
         [tex("ImportError: vszh5_writer too old"), tex("an older copy imported first (Spyder)"),
          tex("restart the kernel; keep 0.0.11 next to the script")],
         [tex("--gpu but 'CPU' in backend"), tex("no CuPy or CUDA device"),
          tex("mamba install -c conda-forge cupy; NVIDIA only")],
         [tex("live: 'waiting for data'"), tex("file has no complete row yet, or other layout"),
          tex("check the file grows; --inspect it once")]])
    tables["HISTORY"] = longtable(
        "Revision history of the program, the writer module and this manual.", "tab:history",
        [("Version", 0.10), ("Date", 0.12), ("Changes", 0.74)],
        [[tt("0.0.1"), tex("2026-10-15"),
          tex("First draft of the analyzer: readers, FFT, Welch, CZT, Lomb-Scargle, spectrogram, "
              "probe model and correction, harmonic families, per-bin modulation, .vszh5 output, "
              "batch, GPU option, live mode, self-test.")],
         [tt("0.0.2"), tex("2026-10-15"),
          tex("Readability pass (descriptive names, detailed comments; numerical results identical). "
              "Veusz output through vszh5_writer 0.0.11; date axis on time pages; zoom page with FFT "
              "bins; hierarchical PDF bookmarks; summary keys rf_bins/rf_range_hz renamed "
              "frequency_bins/frequency_range_hz; fuller dark palette. This manual and its build tool.")],
         [tt("writer 0.0.11"), tex("2026-10-15"),
          tex("vszh5_writer: dataset_2d, Trace, add_title, xy_page, image_page (manual colour bar, "
              "exact ranges), date axes; existing calls unchanged.")]])
    return tables


def module_tables() -> dict[str, str]:
    """Appendix A: the modules, the calls made and why (written from the code)."""
    columns = [("Call", 0.26), ("Where (function)", 0.22), ("How and why", 0.48)]

    def table(caption: str, label: str, rows: list[tuple[str, str, str]]) -> str:
        return longtable(caption, label, columns, [[tt_break(a), tex_break(b), tex(c)] for a, b, c in rows],
                         size=r"\footnotesize")

    tables: dict[str, str] = {}
    tables["MODULES"] = longtable(
        "Python modules used by the analyzer.", "tab:modules",
        [("Module", 0.17), ("Tested", 0.10), ("Needed for", 0.30), ("Why this module", 0.39)],
        [[tt("numpy"), "2.5.4", tex("all arrays and array maths"), tex("common array type of every library used")],
         [tt("scipy"), "1.18.1", tex("FFT, windows, CZT, short-time FFT, peaks, interpolation"),
          tex("tested implementations of every estimator needed; scikit-rf has none of them")],
         [tt("pandas"), "3.0.6", tex("reading text and Excel exports"),
          tex("fast chunked CSV reader, tolerant date parsing")],
         [tt("openpyxl"), "3.1.5", tex(".xlsx (engine of pandas)"), tex("pandas' reader for .xlsx")],
         [tt("h5py"), "3.16.0", tex("SignalShark .h5; .vszh5 output"), tex("direct HDF5 access incl. references")],
         [tt("vszh5_writer"), "0.0.11", tex("Veusz documents, rendering"), tex("the author's Veusz writer")],
         [tt("Qt.py + PySide6"), "2.0.7 / 6.12", tex("live window"), tex("one Qt API, PySide6 binding")],
         [tt("pyqtgraph"), "0.14.0", tex("live plots"), tex("fast repeated plot updates")],
         [tt("cupy"), tex("optional"), tex("--gpu"), tex("NumPy interface on NVIDIA GPUs")],
         [tt("pypdf"), "6.20.1", tex("PDF bookmarks (--render, manual check)"), tex("pure Python PDF editing")],
         [tt("veusz"), "4.2.1", tex("rendering (--render)"), tex("the plotting program of the documents")],
         [tex("standard library"), "3.12.13", tex("CLI, files, processes, time, JSON, ..."),
          tex("no extra dependency")]])
    tables["NUMPY"] = table("NumPy calls.", "tab:numpy", [
        ("np.asarray, np.ascontiguousarray", "everywhere",
         "convert inputs to float64; contiguous arrays for FFTs and HDF5 writes"),
        ("np.argsort(kind='stable'), np.unique", "make_uniform, read_signalshark_csv",
         "sort time stamps keeping equal stamps in order, drop duplicates; pivot long-format CSV"),
        ("np.diff, np.median, ndarray.mean", "make_uniform, analyse_spectrumset",
         "sample interval = mean of gap-free intervals; jitter = median deviation"),
        ("np.interp", "make_uniform, read_ehp_folder",
         "linear interpolation onto the uniform grid / common frequency axis: local, no overshoot, O(N)"),
        ("np.memmap, ndarray.tofile", "SpillBuffer, RingBuffer",
         "long columns live in a raw file mapped into memory, so RAM stays bounded; live log on disk"),
        ("np.sinc", "probe_response", "normalised sinc sin(pi x)/(pi x), the boxcar response of eq. (sinc)"),
        ("np.log10, np.maximum", "all dB conversions", "dB values with a floor, so log10(0) never occurs"),
        ("np.nanmean, np.nanmax, np.nansum, np.where", "analyse_spectrumset",
         "spectrogram statistics with missing cells (NaN) ignored"),
        ("np.stack, np.column_stack, np.vstack", "welch_blocks, readers, outputs",
         "batch of Welch segments; tables for CSV; spectra of an EHP folder"),
        ("np.linspace, np.arange", "czt_zoom, lomb_scargle, synthetic files",
         "frequency grids and time axes"),
        ("np.convolve", "_probe_filter (self-test)", "boxcar-average synthetic data like a probe"),
        ("np.savetxt, np.savez_compressed", "_write_csv, write_outputs", "CSV and compressed .npz outputs"),
        ("np.random.default_rng", "self-test", "reproducible synthetic noise and jitter"),
    ])
    tables["SCIPY"] = table("SciPy calls.", "tab:scipy", [
        ("scipy.fft.rfft(x, n, axis, workers)", "amplitude_spectrum, welch_blocks, analyse_spectrumset",
         "FFT of real data (half the work of a complex FFT); workers = threads (-1 all, 1 per process "
         "in batch mode)"),
        ("scipy.fft.rfftfreq(n, d)", "same", "frequency of every rfft bin"),
        ("scipy.signal.get_window(name, N)", "every estimator",
         "any SciPy window by name (--window); periodic form (fftbins=True), correct for spectral analysis"),
        ("scipy.signal.zoom_fft(x, [f1, f2], m, fs, endpoint=True)", "czt_zoom",
         "chirp-Z zoom (Bluestein), dense spectrum samples in a band"),
        ("scipy.signal.ShortTimeFFT(win, hop, fs, fft_mode='onesided2X', scale_to='psd')",
         "envelope_spectrogram",
         "spectrogram(detr='constant', p0, p1), lower_border_end, upper_border_begin, t(), f: "
         "one-sided PSD slices without the slices hanging over the ends (SciPy >= 1.12)"),
        ("scipy.signal.find_peaks(x, height, prominence)", "find_spectral_peaks, analyse_spectrumset",
         "local maxima above a level and prominence: envelope lines; carriers for channels"),
        ("scipy.signal.welch(...)", "self_test only", "reference to which welch_blocks is compared"),
        ("scipy.interpolate.interp1d(x, y, axis=0)", "analyse_spectrumset",
         "all frequency bins of a spectrogram onto a uniform time grid in one call "
         "(a legacy SciPy class, still supported)"),
    ])
    tables["PANDAS"] = table("pandas calls.", "tab:pandas", [
        ("pd.read_csv(sep, decimal, encoding, skiprows, header=None, usecols, dtype=str, chunksize, "
         "engine, on_bad_lines='skip')", "read_text_timeseries, read_text_spectrum, read_signalshark_csv",
         "reads only the needed columns as text, in chunks (bounded memory); bad lines skipped; "
         "numbers converted afterwards so decimal commas and thousands dots are handled"),
        ("Series.str.strip/.replace/.match", "_num, _to_seconds", "clean quotes and spaces; decimal comma"),
        ("pd.to_numeric(errors='coerce')", "_num, _to_seconds", "text to numbers, NaN where not a number"),
        ("pd.to_datetime(format='mixed', dayfirst, errors='coerce')", "_to_seconds, LiveTail.poll",
         "date/time strings of any common format; .dt.tz_convert(None), .dt.total_seconds() give seconds"),
        ("pd.read_excel(sheet_name=0, header=None, dtype=str)", "read_xlsx_timeseries",
         "first sheet as text (openpyxl engine), then the CSV reader path"),
        ("DataFrame.to_csv(sep=';')", "read_xlsx_timeseries", "temporary CSV of the sheet"),
    ])
    tables["H5PY"] = table("h5py calls.", "tab:h5py", [
        ("h5py.File(path, 'r')", "read_signalshark_h5, describe_h5, self_test", "open HDF5 read-only"),
        ("File.visititems(callback)", "read_signalshark_h5, describe_h5",
         "walk every group and dataset to find level and axis datasets / print the tree"),
        ("Dataset.ndim/.shape/.dtype, .attrs, .parent", "read_signalshark_h5",
         "choose datasets by shape and type; gather attributes up to the root (units, start/stop)"),
        ("h5py.File(path, 'w'), create_group, create_dataset(compression='gzip', compression_opts=4, "
         "shuffle=True)", "vszh5_writer.VeuszWriter", "the .vszh5 layout, gzip for arrays of 4096+ values"),
        ("Dataset.ref (object reference)", "vszh5_writer.VeuszWriter.dataset_2d",
         "links an image to its axis arrays (vsz_xrange etc.), as Veusz itself does"),
    ])
    tables["WRITER"] = table("vszh5\\_writer calls.", "tab:writer", [
        ("VeuszWriter(path, compress=True, writer_tag)", "write_vszh5_series, write_vszh5_spectrogram",
         "context manager; writes <path>.part, publishes with finish(), deletes on error (abort)"),
        ("dataset_1d / dataset_date / dataset_text", "_write_series_pages",
         "typed Veusz datasets: numbers, dates (seconds since 2009-01-01), the JSON summary"),
        ("dataset_2d(name, data, xcent=, ycent=)", "_write_series_pages, write_vszh5_spectrogram",
         "images; regular centres stored as xrange/yrange like Veusz (new in 0.0.11)"),
        ("VszDoc().text()", "write_vszh5_*", "the Veusz command script stored in the document"),
        ("Trace(x, y, label, style, marker, line)", "_write_series_pages",
         "one line or marker series of a page (new in 0.0.11)"),
        ("xy_page(doc, page, traces, title, xlabel, ylabel, xlog, ylog, xmin, xmode, x_autorange)",
         "_write_series_pages", "a complete line-plot page with title and legend (new in 0.0.11)"),
        ("image_page(doc, page, dataset, title, ..., zmin, zmax)", "_write_series_pages, "
         "write_vszh5_spectrogram", "a complete image page with colour bar (new in 0.0.11)"),
        ("render_pages(path, png_pages='all', bookmarks=callable, pdf_info)", "render_vszh5",
         "PDF and PNGs through Veusz; bookmarks from bookmark_outline()"),
    ])
    tables["QT"] = table("Qt.py, PySide6 and pyqtgraph calls.", "tab:qt", [
        ("from Qt import QtCore, QtGui, QtWidgets", "run_live_gui",
         "Qt.py picks the binding named in QT_PREFERRED_BINDING (PySide6)"),
        ("QApplication(), .setStyle('Fusion'), .setPalette(), .exec()", "run_live_gui, apply_theme",
         "event loop; Fusion style so a palette themes every widget; Light/Dark"),
        ("QMainWindow.menuBar().addMenu, .statusBar(), setCentralWidget", "LiveWindow",
         "File/View/Analysis menus and the status line"),
        ("QActionGroup (QtGui in Qt 6, QtWidgets in Qt 5)", "LiveWindow._build_menus",
         "exclusive Light/Dark choice; looked up in either module"),
        ("QtCore.QTimer.timeout, QTimer.singleShot", "LiveWindow", "periodic update; --live-seconds"),
        ("QtGui.QPalette, QColor; style().standardPalette()", "apply_theme", "dark and light palettes"),
        ("pyqtgraph.GraphicsLayoutWidget.addPlot", "LiveWindow", "three stacked plots"),
        ("PlotItem.plot, PlotDataItem.setData, setLogMode, setLabel, mkPen", "LiveWindow.tick",
         "fast redraw of the curves every update; log amplitude axis"),
        ("setBackground, getAxis().setPen/.setTextPen", "apply_theme", "plot colours of the theme"),
    ])
    tables["CUPY"] = table("CuPy calls (only with --gpu).", "tab:cupy", [
        ("cupy.cuda.runtime.getDeviceCount()", "Backend", "is a CUDA device present?"),
        ("cupy.asarray, cupy.fft.rfft", "Backend.asarray, Backend.rfft", "arrays and FFTs on the GPU"),
        ("ndarray.get()", "Backend.cpu", "copy results back to host memory"),
        ("get_default_memory_pool().free_all_blocks(), pinned pool", "flush_memory", "release GPU memory"),
    ])
    tables["RENDER"] = table("pypdf and Veusz (through vszh5\\_writer).", "tab:render", [
        ("veusz --listen --quiet (script on stdin)", "vszh5_writer.render_pages",
         "loader.loadHDF5Doc then Export(): veusz --export cannot open .vszh5 files"),
        ("pypdf.PdfWriter(clone_from), add_outline_item, add_metadata, page_mode", "add_pdf_bookmarks",
         "bookmark tree and document information written into the rendered PDF"),
        ("pypdf.PdfReader(...).outline", "build_manual_pdf.verify_bookmarks",
         "reads this manual's bookmarks back to check them"),
    ])
    tables["STDLIB"] = longtable(
        "Python standard library modules used.", "tab:stdlib",
        [("Module", 0.20), ("Calls", 0.36), ("Purpose", 0.40)],
        [[tt(a), tex(b), tex(c)] for a, b, c in [
            ("argparse", "ArgumentParser, add_argument", "command line (also read by the manual builder)"),
            ("atexit", "register", "delete spill files when the program exits"),
            ("concurrent.futures", "ProcessPoolExecutor, as_completed", "--jobs: files in parallel processes"),
            ("csv", "reader", "split lines with quoted fields"),
            ("dataclasses", "dataclass, field, asdict", "Options, TimeSeries, results"),
            ("datetime", "datetime, timedelta, timezone", "time origins, EHP file times, Veusz dates"),
            ("gc", "collect", "flush_memory()"),
            ("json", "dumps", "summary file and summary dataset"),
            ("math", "floor, ceil, log2, sqrt, isfinite", "segment lengths, scalars"),
            ("os", "fdopen, unlink, replace, environ", "spill files, atomic writes, Qt binding choice"),
            ("pathlib", "Path", "all file paths (Windows and Linux)"),
            ("pickle", "dump (protocol 5), load", "--pickle offload of results"),
            ("re", "search, match, fullmatch, compile", "units, headers, file names, bookmarks"),
            ("sys", "path, modules, argv, exit", "module path for vszh5_writer, CuPy check, CLI"),
            ("tempfile", "mkstemp, mkdtemp", "spill files, xlsx conversion, self-test folder"),
            ("time", "perf_counter, time, sleep", "timing reports, live polling"),
            ("typing", "Any, Sequence", "type hints"),
            ("warnings", "warn(RuntimeWarning)", "render problems reported without stopping"),
            ("subprocess, threading", "Popen, Timer", "vszh5_writer: drive Veusz with a timeout"),
        ]], size=r"\footnotesize")
    return tables


# %% ===========================================================================
#    BUILD (write the .tex, run LuaLaTeX)
# =============================================================================
def build_tex(analyzer: ModuleType, script_path: Path, run_selftest: bool = True) -> tuple[str, str, bool]:
    """The complete LaTeX source; returns (tex text, manual stem, self-test passed)."""
    writer_module = sys.modules["vszh5_writer"]
    version = analyzer.__version__
    manual_stem = f"EMF_Envelope_FFT_Manual_v{version}"
    tokens = computed_numbers(analyzer, writer_module.__version__)
    tokens.update(MANUAL_STEM=manual_stem, TOOL_VERSION=__version__,
                  VERSION_US=version.replace(".", "_"))
    # -- generated tables
    if run_selftest:
        selftest, passed, _ = selftest_rows(analyzer)
    else:
        selftest, passed = [[tex("self-test not run in this build"), "", "--"]], True
    tables = {
        "FILES": longtable("Files of the package.", "tab:files",
                           [("File", 0.30), ("Type", 0.16), ("Size", 0.10), ("Description", 0.40)],
                           package_file_rows(PACKAGE_FOLDER, script_path, manual_stem)),
        "PROBES": longtable(
            "Probe catalogue (datasheet values) and the derived envelope limits.", "tab:probes",
            [("Probe", 0.14), ("RF range", 0.13), ("$f_s$ (Hz)", 0.07), ("$T$ (ms)", 0.10),
             ("$\\nu_N$ (Hz)", 0.08), ("$|H(\\nu_N)|$ (dB)", 0.10), ("$1/T$ (Hz)", 0.08),
             ("True RMS to (V/m)", 0.10), ("Axes", 0.08), ("Ref.", 0.08)],
            probe_rows(analyzer), size=r"\footnotesize"),
        "KEYWORDS": longtable("Keywords that select columns (case ignored).", "tab:keywords",
                              [("Use", 0.20), ("Keywords", 0.46), ("Note", 0.30)],
                              keyword_rows(analyzer), size=r"\footnotesize"),
        "OPTIONS": longtable("Command-line options (from the program's parser).", "tab:options",
                             [("Option", 0.30), ("Default", 0.14), ("Description", 0.52)],
                             option_rows(analyzer), size=r"\footnotesize"),
        "CELLS": longtable(f"Spyder cells of {tex(script_path.name)}.", "tab:cells",
                           [("No.", 0.06), ("Cell", 0.27), ("Line", 0.07), ("Definitions", 0.58)],
                           cell_rows(script_path), size=r"\footnotesize"),
        "SELFTEST": longtable(f"Self-test result (program {version}, run during this build).",
                              "tab:selftest", [("Check", 0.42), ("Measured", 0.42), ("Result", 0.10)],
                              selftest, size=r"\footnotesize"),
    }
    tables.update(static_tables(analyzer))
    tables.update(module_tables())
    for key, table_text in tables.items():
        tokens[f"TABLE_{key}"] = table_text
    figure_tokens = {"TIME": "fig_fieldman_time.png", "AMPLITUDE": "fig_fieldman_amplitude.png",
                     "ZOOM": "fig_fieldman_zoom.png", "PROBE": "fig_fieldman_probe.png",
                     "SPECTROGRAM": "fig_signalshark_spectrogram.png",
                     "MODMAP": "fig_signalshark_modulation_map.png", "LIVE": "fig_live_window_dark.png"}
    for key, figure_name in figure_tokens.items():
        tokens[f"FIGURE_{key}"] = figure_tex(figure_name)
    parts = [TEX_HEADER, TEX_PREAMBLE, TEX_FRONT, SECTION_INTRODUCTION, SECTION_INSTALL,
             SECTION_QUICKSTART, SECTION_INPUTS, SECTION_THEORY, SECTION_CLI, SECTION_OUTPUTS,
             SECTION_LIVE, SECTION_MEMORY, SECTION_SPYDER, SECTION_VERIFICATION, SECTION_LIMITS,
             SECTION_TROUBLESHOOTING, APPENDIX_MODULES, APPENDIX_HISTORY, REFERENCES]
    # Tables contain no @@ tokens, so one pass of fill() over the joined text is safe.
    return fill("".join(parts), tokens), manual_stem, passed


def run_lualatex(tex_path: Path, runs: int = 3) -> tuple[bool, str]:
    """Compile with lualatex ``runs`` times (contents, longtable widths, bookmarks)."""
    lualatex = os.environ.get("EMF_FFT_LUALATEX") or shutil.which("lualatex")
    if not lualatex:
        return False, "lualatex not found (install TeX Live or MiKTeX, or set EMF_FFT_LUALATEX)"
    for run_number in range(1, runs + 1):
        completed = subprocess.run([lualatex, "-interaction=nonstopmode", "-halt-on-error",
                                    "-file-line-error", tex_path.name], cwd=tex_path.parent,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            log_text = tex_path.with_suffix(".log").read_text(encoding="utf-8", errors="replace") \
                if tex_path.with_suffix(".log").exists() else completed.stdout
            errors = [line for line in log_text.splitlines() if line.startswith("!") or ":error" in line
                      or re.match(r"^.*\.tex:\d+:", line)]
            return False, f"lualatex run {run_number} failed:\n" + "\n".join(errors[-20:])
    return True, "ok"


# %% ===========================================================================
#    VERIFY (the PDF bookmarks follow the headings)
# =============================================================================
def verify_bookmarks(pdf_path: Path, tex_text: str) -> tuple[bool, list[str]]:
    """Compare the PDF outline with the \\section/\\subsection headings of the .tex.

    Returns (every heading has a bookmark, outline printed as indented lines).
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    outline_lines: list[str] = []

    def walk(items: list, depth: int) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                page = reader.get_destination_page_number(item) + 1
                outline_lines.append("  " * depth + f"{item.title}  (p. {page})")

    walk(reader.outline, 0)
    def normalise(text: str) -> str:
        """Letters and digits only: dashes, escapes and macros do not matter."""
        return re.sub(r"[^a-z0-9]", "", re.sub(r"\\[a-zA-Z]+", "", text).lower())

    body = tex_text.split(r"\begin{document}", 1)[1]
    headings = re.findall(r"\\(?:sub)?section\{((?:[^{}]|\{[^{}]*\})*)\}", body)
    titles = normalise(" ".join(outline_lines))
    missing = [h for h in headings if normalise(h)[:24] not in titles]
    return not missing, outline_lines + [f"MISSING: {m}" for m in missing]


# %% ===========================================================================
#    COMMAND LINE
# =============================================================================
def main(argv: Sequence[str] | None = None) -> int:
    """Build the manual; returns 0 on success."""
    parser = argparse.ArgumentParser(description=f"Build the EMF Envelope FFT manual ({__version__}).")
    parser.add_argument("--figures", action="store_true", help="re-render the figures with Veusz first")
    parser.add_argument("--tex-only", action="store_true", help="write the .tex but do not compile it")
    parser.add_argument("--no-selftest", action="store_true", help="do not run the self-test table")
    parser.add_argument("--keep-aux", action="store_true", help="keep .aux/.log/.toc/.out files")
    args = parser.parse_args(argv)

    script_path = find_analyzer_script()
    analyzer = load_analyzer(script_path)
    print(f"analyzer {analyzer.__version__} from {script_path.name}; "
          f"vszh5_writer {sys.modules['vszh5_writer'].__version__}")
    if args.figures:
        written = make_figures(analyzer)
        print(f"figures: {len(written)} rendered into {FIGURE_FOLDER}")
    tex_text, manual_stem, selftest_passed = build_tex(analyzer, script_path, not args.no_selftest)
    DOCS_FOLDER.mkdir(parents=True, exist_ok=True)
    tex_path = DOCS_FOLDER / f"{manual_stem}.tex"
    tex_path.write_text(tex_text, encoding="utf-8")
    print(f"wrote {tex_path} ({len(tex_text.splitlines())} lines); self-test "
          f"{'passed' if selftest_passed else 'FAILED'}")
    if args.tex_only:
        return 0
    ok, message = run_lualatex(tex_path)
    if not ok:
        print(message)
        return 1
    pdf_path = tex_path.with_suffix(".pdf")
    if not args.keep_aux:
        for suffix in (".aux", ".log", ".toc", ".out", ".lot", ".lof"):
            tex_path.with_suffix(suffix).unlink(missing_ok=True)
    try:
        bookmarks_ok, outline = verify_bookmarks(pdf_path, tex_text)
    except ImportError:
        bookmarks_ok, outline = True, ["(pypdf not installed: bookmarks not checked)"]
    print(f"wrote {pdf_path}; bookmarks {'match the headings' if bookmarks_ok else 'INCOMPLETE'}:")
    print("\n".join("   " + line for line in outline))
    return 0 if bookmarks_ok and selftest_passed else 1


if __name__ == "__main__":
    sys.exit(main())


# %% ===========================================================================
#    INTERACTIVE SCRATCH CELL (Spyder)
# =============================================================================
# analyzer = load_analyzer(find_analyzer_script())
# text, stem, ok = build_tex(analyzer, find_analyzer_script(), run_selftest=False)
# print(text[:2000])
# main(["--tex-only"])
