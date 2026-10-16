#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2026 William W. Wallace <wwallace@nrao.edu>
# SPDX-FileCopyrightText: 2026 William W. Wallace, Adaptive Electrodynamics LLC dba AdaptEd
# %% ===========================================================================
#    MODULE HEADER
# =============================================================================
"""Envelope (modulation) spectra of broadband EMF probe and analyzer logs.

===============================================================================
 Title          : EMF Envelope FFT Analyzer
 Filename       : emf_envelope_fft_v0_0_4.py
 Version        : 0.0.4 (Semantic Versioning 2.0.0, MAJOR.MINOR.PATCH)
 Author         : William W. Wallace
 Company        : NRAO/GBO
 Email          : wwallace@nrao.edu
 Created        : 2026-10-15
 Modified       : 2026-10-15
 Language       : Python 3.12
 Requires       : numpy, scipy (>= 1.12), pandas, h5py, and vszh5_writer.py
                  0.0.13 (same author, shipped next to this script);
                  for the GUI: Qt.py (or QtPy) + PySide6 + pyqtgraph
 Optional       : cupy (GPU FFTs), openpyxl (.xlsx exports), Veusz + pypdf
                  (rendering the .vszh5 to PDF with bookmarks and PNG)
 Licence        : GPL-3.0-or-later (GNU General Public License v3.0 or later)
 Copyright      : Copyright (C) 2026 William W. Wallace
 Derived from   : Veusz output through vszh5_writer.py 0.0.13 (same author;
                  extended for this program from 0.0.10 of the QuickSyn
                  package with 2-D datasets and page helpers). GUI layout,
                  ThemeManager and About dialog follow the author's QuickSyn
                  SCPI controller GUI 0.0.10.
 Manual         : docs/EMF_Envelope_FFT_Manual_v0.0.4.pdf (LuaLaTeX source
                  beside it; rebuild with tools/build_manual_pdf.py)
 Status         : Internal draft. Tested on synthetic files only: no real
                  FieldMan, Narda-TSX, NBM-TS, EHP-50 TS or SignalShark export
                  has been seen yet, so the readers are heuristic.
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
A broadband diode probe (EFD-4091, EFD-0691, EF 0691, EFD-9091) reports one
power-summed value per sample, so its log holds no RF-frequency information.
What it does hold is how the total field changes in time: antenna rotation,
beam scanning, duty cycles, on/off keying. This program takes the Fourier
transform of that envelope:

    P_disp(t) = sum_i r(f_i) P_i(t)      (square-law diodes add powers)
    F{P_disp}(nu) = sum_i r(f_i) F{P_i}(nu)

so sources that share an RF band but change at different rates separate in
the envelope ("modulation") spectrum. Analysis is done on power density
(W/m^2) by default, because the transform is linear in power, not in V/m.

A SignalShark spectrogram does hold RF frequency, so for it the envelope
transform is taken per RF bin, giving a 2-D map of RF frequency versus
modulation frequency, plus per-channel analyses.

Spectral estimators (SciPy [R10]; GPU through CuPy when requested):
    * direct FFT amplitude spectrum, windowed, coherent-gain corrected
    * Welch PSD [R11] over gap-free blocks, streamed in batches (bounded RAM)
    * chirp-Z zoom [R12] (scipy.signal.zoom_fft) around a peak: denser
      sampling of the same spectrum, NOT finer resolution (still 1/T_record);
      it also removes the window's scalloping loss at the peak
    * Lomb-Scargle [R13][R14] for irregular time stamps and gappy logs
    * short-time FFT spectrogram of the envelope for long logs
    * probe integration model |H(nu)| = |sinc(nu T_int)| with an optional,
      boost-limited (Wiener-type) correction below the first null

GUI (0.0.3): running the script without arguments (or with --gui) opens a
Qt window (Qt.py or QtPy over PySide6): input list and every option on the
left, result tabs (time, amplitude, Welch, CZT, Lomb-Scargle, probe model,
spectrograms, modulation map, peaks and families, summary, inspect,
verification) in the centre, live mode, a log, menus File/Edit/View/
Analysis/Veusz/Help with Light/Dark/System themes, display units, export,
and an About dialog (author, version, GPL-3.0-or-later). Analysis runs in a
background thread.

Unit control (0.0.4): every plot, table, summary and Veusz page can be shown
in a unit of the quantity's family (power density W/m^2 ... uW/cm^2 and
dBW/m^2, dBm/m^2; electric field V/m ... dBuV/m; magnetic field A/m ...
dBuA/m; flux density T ... pT; port power W ... dBm; port voltage V ...
dBuV; squared fields from their root unit), one choice per family. Time
plots show power density, E or H (plane wave, Z0) or the logged field;
RF spectrogram levels power density or field. Veusz documents can carry
several units at once: a section of pages per extra unit in one document
(bookmarked per unit) or one document per unit. The same settings apply in
post-processing (GUI, batch, command line) and in live mode (plots and
snapshots). Data files (CSV, NPZ, JSON) stay in SI units.

Verification (0.0.3): --verify checks every transform and unit conversion
three ways (analytic answer, independent reference implementation,
internal identity); see verify_transforms().

Why not scikit-rf: scikit-rf is built for network parameters (Touchstone,
S-parameters, calibration, frequency-domain network data) [R15]; it has no
time-series spectral estimators (Welch, Lomb-Scargle, CZT), which is what
this problem needs. SciPy provides all of them.

INPUTS (auto-detected; force with --source)
-------------------------------------------
    fieldman / tsx : FieldMan or Narda-TSX exports (.csv/.txt/.xlsx), probe
                     values vs time; EFD-0691 X/Y/Z columns are used if present
    nbm            : NBM-550 / NBM-TS exports (EF 0691 NBM probe)
    ehp            : EHP-50 TS auto-saved spectra (YYYY/MM/DD/hh_mm_ss_cc.TXT)
                     or a folder of them (built into a spectrogram), or the
                     EHP-50F stand-alone logger text file (a time series).
                     NOTE: EHP-50 TS only records the EHP-50F (1 Hz-400 kHz);
                     it cannot record the RF probes.
    signalshark    : SignalShark .h5 spectrum/spectrogram files, or the CSV
                     made from them by Narda's NSL "Converter" script
Use --inspect FILE to see how a file is read before analysing it.

OUTPUTS (folder "<stem>_fft" next to the input, or --out)
---------------------------------------------------------
    <stem>_envelope_fft.vszh5   Veusz document, written directly with h5py
                                through vszh5_writer.py (no Veusz needed)
    <stem>_amplitude.csv, _welch.csv, _zoom.csv, _lomb.csv, _modulation.npz
    <stem>_summary.json         peaks, harmonic families (rpm), warnings
    <stem>_envelope_fft.pdf/png with --render (needs vszh5_writer + Veusz)

LIVE ("during measurement")
---------------------------
--live FILE follows a file another program is appending to, keeps a rolling
window in a fixed-size ring buffer (every sample is also appended to a
binary log on disk) and updates the envelope spectrum every --update
seconds, in a Qt.py/pyqtgraph window (View > Light/Dark) or on the console
(--no-gui). Neither FieldMan nor Narda-TSX documents a continuously written
file or a streaming API for the broadband probes, so live mode depends on
how your software writes data; NBM-550 remote output (MEAS_START, 5/50/60
Hz) [R6] logged to a file by another tool works.

LIMITS THAT COME FROM THE PROBES (datasheets)
--------------------------------------------
    EFD-4091  5 Hz / 265 ms   -> envelope content to 2.5 Hz (Nyquist)   [R1]
    EFD-0691  5 Hz / 265 ms   -> 2.5 Hz; 3 separate axes                [R2]
    EF 0691   NBM-550 5 Hz, 50/60 Hz in remote mode -> 2.5 / 25 / 30 Hz [R6]
    EFD-9091  5 Hz / 275 ms   -> 2.5 Hz                                 [R3]
    EFD-1891 fast 900 Hz / 2.3 ms -> 450 Hz                             [R4]
Integration of T seconds attenuates envelope frequency nu by |sinc(nu T)|:
-2.4 dB at 1.5 Hz and -7.6 dB at 2.5 Hz for T = 265 ms. Content above the
Nyquist frequency folds back (aliases) instead of vanishing. The boxcar
model of the integration is an assumption; Narda states only nominal
figures.

USAGE
-----
    python emf_envelope_fft_v0_0_4.py                      (opens the GUI)
    python emf_envelope_fft_v0_0_4.py a.csv b.h5 --gui     (GUI, inputs listed)
    python emf_envelope_fft_v0_0_4.py --selftest
    python emf_envelope_fft_v0_0_4.py --verify
    python emf_envelope_fft_v0_0_4.py --inspect log.csv
    python emf_envelope_fft_v0_0_4.py log.csv --probe EFD-4091 --lomb on --render
    python emf_envelope_fft_v0_0_4.py log.csv --display-unit mW/cm2
    python emf_envelope_fft_v0_0_4.py log.csv --display-unit mW/cm2,dBuV/m --time-display "E field"
    python emf_envelope_fft_v0_0_4.py log.csv --veusz-units W/m2,uW/cm2,dBm/m2,dBuV/m --render
    python emf_envelope_fft_v0_0_4.py log.csv --veusz-units dBuV/m --veusz-layout files
    python emf_envelope_fft_v0_0_4.py --list-units
    python emf_envelope_fft_v0_0_4.py a.csv b.csv c.csv --jobs 3 --gpu
    python emf_envelope_fft_v0_0_4.py rec.h5 --source signalshark --rf-channels auto:5 --rbw-hz 1e5
    python emf_envelope_fft_v0_0_4.py --live growing.csv --probe EF0691 --window-s 120
In Spyder, run the file (GUI) or the cells; the last cell is a scratch cell.

REFERENCES
----------
[R1]  Narda Safety Test Solutions GmbH, "Datasheet Probe EFD-4091," NSTS
      0523-E0399A, 2023.
      https://www.atecorp.com/getmedia/48a83a03-af45-41d0-820c-ecdb46ba1437/Narda_EFD-4091-datasheet.pdf
[R2]  Narda Safety Test Solutions GmbH, "Datasheet Probe EFD-0691," NSTS
      0624-E0387B, 2024.
      https://www.atecorp.com/getmedia/84e296e2-1bd2-4861-8a1f-e905f39d4910/Datasheet_EFD-0691.pdf
[R3]  Narda Safety Test Solutions GmbH, "Datasheet Probe EFD-9091," NSTS
      0523-E0405A, 2023.
      https://www.atecorp.com/getmedia/c56e0776-d855-4d49-9081-ff316ecaf68a/Datasheet_EFD-9091.pdf
[R4]  Narda Safety Test Solutions GmbH, "Datasheet Probe EFD-1891," NSTS
      0723-E0398A, 2023.
      https://www.atecorp.com/getmedia/d5ed148e-2dfc-4f3c-afa4-2b306fb7a781/Narda_EFD-1891-datasheet.pdf
[R5]  Narda Safety Test Solutions GmbH, "Datasheet Narda FieldMan," NSTS
      0925-E0370D, 2025.
      https://www.atecorp.com/getmedia/5511a8ac-b386-434f-bac9-fd22d18e2f48/Narda-Fieldman-Datasheet-2025.pdf
[R6]  Narda Safety Test Solutions, "NBM-550 Remote Control," V1.0.
      https://wiki.radimation.com/wiki/images/7/7b/NBM-550_Remote_Control_V1_0.pdf
[R7]  Narda Safety Test Solutions S.r.l., "EHP-50F User's Manual,"
      EHP50FEN-10107-1.73, 2021.
      https://atecorp.com/getmedia/d53b58ae-844a-4a2d-b84e-6a9f98be805a/narda-ehp-50f-operating-manual.pdf
[R8]  Narda Safety Test Solutions, "SignalShark Options and Scripts."
      https://www.narda-sts.com/en/products/receivers-/-direction-finders-/-spectrum-analyzers/signalshark-optionen/
[R9]  Narda Safety Test Solutions, "PC Software Narda-TSX."
      https://www.narda-sts.com/en/products/emc-products-and-streaming-solutions/pc-software-narda-tsx/
[R10] P. Virtanen et al., "SciPy 1.0: Fundamental algorithms for scientific
      computing in Python," Nature Methods, vol. 17, pp. 261-272, 2020.
      https://doi.org/10.1038/s41592-019-0686-2
[R11] P. D. Welch, "The use of fast Fourier transform for the estimation of
      power spectra," IEEE Trans. Audio Electroacoust., vol. AU-15, no. 2,
      pp. 70-73, 1967. https://doi.org/10.1109/TAU.1967.1161901
[R12] L. R. Rabiner, R. W. Schafer, C. M. Rader, "The chirp z-transform
      algorithm," IEEE Trans. Audio Electroacoust., vol. AU-17, no. 2,
      pp. 86-92, 1969. https://doi.org/10.1109/TAU.1969.1162034
[R13] J. D. Scargle, "Studies in astronomical time series analysis. II,"
      Astrophys. J., vol. 263, pp. 835-853, 1982.
      https://doi.org/10.1086/160554
[R14] J. T. VanderPlas, "Understanding the Lomb-Scargle periodogram,"
      Astrophys. J. Suppl., vol. 236, no. 1, 2018.
      https://doi.org/10.3847/1538-4365/aab766
[R15] scikit-rf developers, "scikit-rf documentation."
      https://scikit-rf.readthedocs.io/
[R16] F. J. Harris, "On the use of windows for harmonic analysis with the
      discrete Fourier transform," Proc. IEEE, vol. 66, no. 1, pp. 51-83,
      1978. https://doi.org/10.1109/PROC.1978.10837
[R17] IEEE Std 1309-2013, Calibration of Electromagnetic Field Sensors and
      Probes (Excluding Antennas) from 9 kHz to 40 GHz.
      https://standards.ieee.org/ieee/1309/5031
[R18] IEC 62232:2025, Determination of RF field strength, power density and
      SAR in the vicinity of base stations for the purpose of evaluating
      human exposure. https://webstore.iec.ch/en/publication/89073
[R19] IEC 60027-3:2002, Letter symbols to be used in electrical technology -
      Part 3: Logarithmic and related quantities, and their units, ed. 3.0.
      https://webstore.iec.ch/en/publication/94
[R20] ISO 80000-1:2022, Quantities and units - Part 1: General.
      https://www.iso.org/standard/76921.html

REVISION HISTORY
----------------
0.0.4  2026-10-15  Unit control.
                   * Display units for every unit family the readers know
                     (DISPLAY_UNITS): power density W/m^2, mW/m^2, uW/m^2,
                     mW/cm^2, uW/cm^2, nW/cm^2, dBW/m^2, dBm/m^2; E field
                     V/m, mV/m, uV/m, kV/m, dBV/m, dBuV/m; H field A/m,
                     mA/m, uA/m, dBuA/m; flux density T, mT, uT, nT, pT;
                     port power W, mW, uW, nW, dBW, dBm; port voltage V,
                     mV, uV, dBV, dBuV. Squared fields (EHP-50 TS, B^2,
                     uV^2) use the square of the chosen root unit. dB units
                     are 10 log10 for power quantities, 20 log10 for field
                     quantities; PSDs are dB re 1 (unit)^2/Hz.
                   * One choice per family (--display-unit LIST, GUI
                     "Units" group, toolbar, View menu); time plots show
                     power density, E or H (plane wave), the logged field
                     or the analysed quantity (--time-display); RF levels
                     as power density, E or H (--rf-level-display).
                   * Veusz in several units at once (--veusz-units LIST,
                     --veusz-layout sections|files; GUI "Veusz units"):
                     one document with a bookmarked section per unit, or one
                     document per unit; Veusz > Write .vszh5 again re-writes
                     the current result in the current units without
                     re-analysing. Units apply in live mode too (plots,
                     console lines, snapshots).
                   * --list-units prints the unit table; verify_transforms
                     checks every display unit (round trips, dB conventions,
                     plane-wave relations): 54 checks.
                   * Live tab "Clear buffer" and Edit > Free memory (also in
                     the 0.0.3 package).
0.0.3  2026-10-15  GUI and verification release.
                   * GUI (default when run without arguments; --gui):
                     Qt.py/QtPy over PySide6, layout and theming as in the
                     QuickSyn controller (System/Light/Dark), toolbar,
                     File/Edit/View/Analysis/Veusz/Help menus, recent
                     inputs, drag and drop, results tabs, peaks/families
                     tables, cursor readout, plot/table/log export, live
                     tab, verification tab, keyboard-shortcut and probe
                     catalogue dialogs, About (author, version, GPL),
                     settings kept between sessions (QSettings); analysis in
                     a QThread (or a process pool), stoppable.
                   * Display units for power density (W/m^2 default, mW/m^2,
                     uW/m^2, mW/cm^2, uW/cm^2; --display-unit) in the GUI and
                     the Veusz pages; data files stay in SI. Time plots also
                     as field strength (V/m, dBuV/m). New Veusz pages:
                     summary (text), overview (2 x 2 grid), power density vs
                     time (vszh5_writer 0.0.12: grid_page, text_page).
                   * verify_transforms() / --verify: 44 checks of every
                     transform and unit conversion (analytic, SciPy/brute-
                     force reference, identities); part of the self-test.
                   * FIXES found by the verification: per-bin modulation
                     spectra doubled the Nyquist row; unit headers mW/m^2,
                     uW/m^2 and dB(uV/m) were not recognised and dBm/m^2 was
                     read as dBm; dBm -> dBuV used the rounded 107 dB (now
                     106.99 dB); the probe-correction gain stepped by
                     1.94 dB (now min(1/|H|, g_max), continuous).
                   * Channel power of spectrograms: --rbw-hz/--enbw-factor
                     give absolute channel power (sum x bin / (RBW x ENBW));
                     power-density readings shown as field use E = sqrt(S Z0).
0.0.2  2026-10-15  Readability pass, no change to the numerical methods:
                   descriptive names for variables, dataclass fields and
                   Veusz datasets (e.g. SeriesResult.fft_amplitude instead
                   of Result1D.amp); detailed comments throughout.
                   Veusz output now goes through the author's
                   vszh5_writer.py (extended to 0.0.11: dataset_2d,
                   Trace, xy_page, image_page) instead of a private copy of
                   its writer. Time page on a date axis when the wall-clock
                   start is known; zoom page shows the FFT bins as markers;
                   rendered PDFs get a bookmark hierarchy (overview pages,
                   then one entry per channel). Spectrogram summary keys
                   rf_bins/rf_range_hz renamed frequency_bins/
                   frequency_range_hz (EHP-50 TS spectra are not RF).
                   All self-test numbers and CSV outputs equal 0.0.1's.
                   Dark palette completed (highlight, tool tips, disabled
                   text, every colour group) so menus and selections are
                   dark too; light mode uses the style's standard palette.
                   New: LuaLaTeX user manual (docs/) with heading-based PDF
                   bookmarks, file-description tables and an appendix on
                   the Python modules used, built by tools/build_manual_pdf.py
                   from this module's own option parser and probe catalogue.
0.0.1  2026-10-15  First internal draft. Readers for FieldMan/Narda-TSX,
                   NBM, EHP-50 TS and SignalShark (.h5 and converter CSV),
                   all heuristic until real exports are available; FFT,
                   Welch (streamed, gap-aware), CZT zoom, Lomb-Scargle,
                   envelope spectrogram; probe-integration model and
                   correction; harmonic families (rpm); per-RF-bin
                   modulation spectra for spectrograms; .vszh5 output;
                   parallel batch; optional CuPy GPU; live mode with
                   Qt.py/pyqtgraph window; built-in self-test.
===============================================================================
"""

# %% ===========================================================================
#    IMPORTS
# =============================================================================
from __future__ import annotations

import argparse
import atexit
import concurrent.futures as cf
import csv
import datetime as _dt
import gc
import json
import math
import os
import pickle
import re
import sys
import tempfile
import time
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import scipy.fft as sfft
import scipy.signal as ssig

try:                                   # pandas: tolerant, chunked text reading
    import pandas as pd
except ImportError:  # pragma: no cover - reported when a reader needs it
    pd = None

try:                                   # h5py: SignalShark .h5 and .vszh5 output
    import h5py
except ImportError:  # pragma: no cover
    h5py = None

# The author's Veusz HDF5 writer, shipped next to this script. 0.0.13 or
# later is needed (2-D datasets, xy/image/grid/text page helpers, reading
# text datasets back for the bookmarks of multi-unit documents). The
# script's folder goes first on sys.path so that copy wins over an older
# one elsewhere (e.g. the QuickSyn package); Spyder's runcell defines
# __file__, a bare interpreter session falls back to the working folder.
_SCRIPT_FOLDER = Path(globals().get("__file__", Path.cwd() / "_")).resolve().parent
if str(_SCRIPT_FOLDER) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_FOLDER))
import vszh5_writer                     # noqa: E402 - needs the path set above
if not hasattr(vszh5_writer, "read_text_dataset"):     # an older copy was imported first
    raise ImportError(f"vszh5_writer {vszh5_writer.__version__} ({vszh5_writer.__file__}) is too "
                      f"old: 0.0.13 or later, shipped with this script, is needed")
from vszh5_writer import (Panel, Trace, VeuszWriter, VszDoc, grid_page,  # noqa: E402
                          image_page, read_text_dataset, render_pages, text_page, xy_page)

__version__ = "0.0.4"                  # Semantic Versioning 2.0.0
__author__ = "William W. Wallace"
__email__ = "wwallace@nrao.edu"
__company__ = "NRAO/GBO"
__license__ = "GPL-3.0-or-later"       # SPDX identifier
__copyright__ = "Copyright (C) 2026 William W. Wallace"

PROGRAM_NAME = "EMF Envelope FFT Analyzer"

# %% ===========================================================================
#    CONSTANTS, PROBE CATALOGUE AND UNITS
# =============================================================================
#: Impedance of free space (CODATA 2018, mu0*c), ohm. Narda displays round
#: conversions (e.g. 0.2 mW/cm^2 = 27.5 V/m implies ~378 ohm); use --z0 377
#: to reproduce the instrument's own unit conversion exactly.
Z0_OHM = 376.730313668
#: Veusz date origin (seconds since 2009-01-01 naive wall-clock time).
VEUSZ_EPOCH = _dt.datetime(2009, 1, 1)
#: Above this many samples a column is kept on disk (memmap), not in RAM.
SPILL_SAMPLES = 20_000_000
#: Rows per pandas chunk when reading large text exports.
READ_CHUNK_ROWS = 500_000
#: Largest image (pixels per side) put into the Veusz document; the full
#: resolution data go to the .npz file.
MAX_IMAGE_SIDE = 1500
#: Samples further apart than this many nominal intervals mark a gap.
GAP_FACTOR = 1.6
#: Noise-equivalent bandwidth of a Gaussian resolution filter divided by its
#: 3 dB bandwidth: integral of exp(-4 ln2 f^2/RBW^2) df / RBW = sqrt(pi/(4 ln 2)).
GAUSSIAN_ENBW_FACTOR = math.sqrt(math.pi / (4.0 * math.log(2.0)))


@dataclass(frozen=True)
class ProbeSpec:
    """Timing and range data for one probe (from the datasheets in the header).

    Attributes
    ----------
    name, part:
        Model and Narda part number.
    f_lo_hz, f_hi_hz:
        RF frequency range.
    fs_hz:
        Nominal output sampling rate.
    t_int_s:
        Nominal integration time; None when not published (then 1/fs is used).
    truerms_max_vm, cw_max_vm:
        Upper True-RMS and CW range limits in V/m (None when unknown).
    axes:
        "rss" (only the combined value is available) or "xyz".
    ref:
        Reference tag in the module header.
    """
    name: str
    part: str
    f_lo_hz: float
    f_hi_hz: float
    fs_hz: float
    t_int_s: float | None
    truerms_max_vm: float | None
    cw_max_vm: float | None
    axes: str
    ref: str


PROBES: dict[str, ProbeSpec] = {
    "EFD-4091": ProbeSpec("EFD-4091", "2462/19", 2e6, 40e9, 5.0, 0.265, 65.0, 800.0, "rss", "R1"),
    "EFD-0691": ProbeSpec("EFD-0691", "2462/14B", 1e5, 6e9, 5.0, 0.265, 17.0, 650.0, "xyz", "R2"),
    # NBM probe: sampling is set by the meter (NBM-550: 5 Hz, or 50/60 Hz in
    # remote mode [R6]; FieldMan with the A/D Probe Converter: 5 Hz reference
    # condition). Integration time not published -> 1/fs is assumed.
    "EF0691": ProbeSpec("EF 0691 (NBM)", "NBM probe", 1e5, 6e9, 5.0, None, 22.0, 650.0, "rss", "R6"),
    "EFD-9091": ProbeSpec("EFD-9091", "2462/18", 1e8, 90e9, 5.0, 0.275, 61.4, 400.0, "rss", "R3"),
    "EFD-1891F": ProbeSpec("EFD-1891 Fast", "2462/23", 2e6, 18e9, 900.0, 0.0023, None, None, "rss", "R4"),
}
#: Spellings accepted for --probe (upper-cased, spaces removed).
PROBE_ALIASES = {
    "EFD4091": "EFD-4091", "EFD-4091E": "EFD-4091", "EFD4091E": "EFD-4091",
    "EFD0691": "EFD-0691", "EF-0691": "EF0691", "EF0691NBM": "EF0691",
    "EFD9091": "EFD-9091", "EFD1891F": "EFD-1891F", "EFD-1891FAST": "EFD-1891F",
}


def lookup_probe(probe_name: str | None) -> ProbeSpec | None:
    """Return the ProbeSpec for a user-supplied probe name, or None.

    Accepts the catalogue keys and the spellings in PROBE_ALIASES, case and
    spaces ignored (so "efd 4091", "EFD-4091E" and "EFD4091" all match).
    """
    if not probe_name:
        return None
    key = probe_name.strip().upper().replace(" ", "")
    key = PROBE_ALIASES.get(key, key)
    if key not in PROBES:
        raise ValueError(f"unknown probe {probe_name!r}; known: {', '.join(PROBES)}")
    return PROBES[key]


# ---- units ----------------------------------------------------------------------
#: Canonical unit keys and the regular expressions that recognise them in
#: header text. Order matters: longer, more specific patterns come first so
#: that, for example, "dBuV/m" is not taken for "V/m".
_UNIT_PATTERNS: list[tuple[str, str]] = [
    # Micro is matched as "u", the micro sign U+00B5 or the Greek mu U+03BC.
    # Order matters: the longer, more specific pattern comes first, so that
    # "dBuV/m" is not taken for "V/m" and "dBm/m^2" not for "dBm" (0.0.3 fix).
    ("dBuV/m", r"db\s*\(?\s*[\u00b5\u03bcu]v\s*/\s*m"),        # also dB(uV/m)
    ("dBuV", r"db\s*\(?\s*[\u00b5\u03bcu]v(?!\s*/)"),
    ("dBmW/m2", r"dbm\s*w?\s*/\s*m\s*\^?\s*[2\u00b2]"),       # dBm/m^2, dBmW/m2
    ("dBm", r"dbm(?![a-z])"),
    ("mW/cm2", r"mw\s*/\s*cm\s*\^?\s*[2\u00b2]"),
    ("uW/cm2", r"[\u00b5\u03bcu]w\s*/\s*cm\s*\^?\s*[2\u00b2]"),
    ("nW/cm2", r"nw\s*/\s*cm\s*\^?\s*[2\u00b2]"),
    ("mW/m2", r"mw\s*/\s*m\s*\^?\s*[2\u00b2]"),                 # 0.0.3: was not recognised
    ("uW/m2", r"[\u00b5\u03bcu]w\s*/\s*m\s*\^?\s*[2\u00b2]"),   # 0.0.3: was not recognised
    ("W/m2", r"(?<![a-z\u00b5\u03bc])w\s*/\s*m\s*\^?\s*[2\u00b2]"),
    ("kV/m", r"kv\s*/\s*m"),
    ("mV/m", r"mv\s*/\s*m"),
    ("uV/m", r"[\u00b5\u03bcu]v\s*/\s*m"),
    ("V/m", r"(?<![a-z\u00b5\u03bc])v\s*/\s*m"),
    ("mA/m", r"ma\s*/\s*m"),
    ("A/m", r"(?<![a-z\u00b5\u03bc])a\s*/\s*m"),
    ("mT", r"(?<![a-z])mt(?![a-z])"),
    ("uT", r"[\u00b5\u03bcu]t(?![a-z])"),
    ("nT", r"(?<![a-z])nt(?![a-z])"),
    ("%", r"%"),
]

#: dBm at a 50-ohm port to dBuV: 10 log10(50 ohm x 1e-3 W / 1e-12 V^2)
#: = 106.9897 dB (0.0.3: was the rounded 107).
DBM_TO_DBUV_50OHM = 10.0 * math.log10(50.0 * 1e-3 / 1e-12)


def parse_unit(text: str) -> str | None:
    """Find a known unit in header or metadata text; None if there is none."""
    lowered = str(text).lower().replace("**", "^")
    for unit_key, pattern in _UNIT_PATTERNS:
        if re.search(pattern, lowered):
            return unit_key
    return None


def to_power_like(values: np.ndarray, unit: str | None, z0_ohm: float = Z0_OHM,
                  antenna_factor_db: float | None = None) -> tuple[np.ndarray, str, str]:
    """Convert readings to a quantity proportional to power.

    Fourier analysis of envelopes is linear only in power, so this is the
    default analysis quantity.

    Parameters
    ----------
    values:
        Readings in ``unit``.
    unit:
        Canonical unit key (see parse_unit); None means unknown.
    z0_ohm:
        Wave impedance used for E^2/Z0 and Z0*H^2 (far field).
    antenna_factor_db:
        Antenna factor in dB(1/m) for dBm/dBuV inputs (SignalShark without
        field-strength units): E[dBuV/m] = V[dBuV] + AF, V[dBuV] = P[dBm] + 107
        (50 ohm; the exact 106.99 dB, see DBM_TO_DBUV_50OHM).

    Returns
    -------
    (power_values, power_unit_label, conversion_note)
    """
    readings = np.asarray(values, dtype=float)
    if unit in ("kV/m", "V/m", "mV/m", "uV/m"):
        to_volts_per_metre = {"kV/m": 1e3, "V/m": 1.0, "mV/m": 1e-3, "uV/m": 1e-6}[unit]
        return ((readings * to_volts_per_metre) ** 2 / z0_ohm, "W/m^2",
                f"S = E^2/Z0, Z0 = {z0_ohm:.3f} ohm")
    if unit == "dBuV/m":
        field_v_per_m = 10.0 ** ((readings - 120.0) / 20.0)
        return field_v_per_m ** 2 / z0_ohm, "W/m^2", "dBuV/m -> V/m -> E^2/Z0"
    if unit in POWER_DENSITY_TO_SI:
        # 1 mW/cm^2 = 1e-3 W / 1e-4 m^2 = 10 W/m^2, 1 uW/cm^2 = 1e-2 W/m^2, ...
        to_watts_per_m2 = POWER_DENSITY_TO_SI[unit]
        return readings * to_watts_per_m2, "W/m^2", "power density"
    if unit == "dBmW/m2":
        return 1e-3 * 10.0 ** (readings / 10.0), "W/m^2", "dBm/m^2 -> W/m^2"
    if unit in ("A/m", "mA/m"):
        to_amps_per_metre = 1.0 if unit == "A/m" else 1e-3
        return z0_ohm * (readings * to_amps_per_metre) ** 2, "W/m^2", "S = Z0 H^2 (far field)"
    if unit in ("mT", "uT", "nT"):
        to_tesla = {"mT": 1e-3, "uT": 1e-6, "nT": 1e-9}[unit]
        return (readings * to_tesla) ** 2, "T^2", "B^2 (proportional to magnetic energy density)"
    if unit in ("dBm", "dBuV"):
        if antenna_factor_db is not None:
            level_dbuv = readings + DBM_TO_DBUV_50OHM if unit == "dBm" else readings
            field_v_per_m = 10.0 ** ((level_dbuv + antenna_factor_db - 120.0) / 20.0)
            return (field_v_per_m ** 2 / z0_ohm, "W/m^2",
                    f"{unit} + AF {antenna_factor_db:g} dB/m -> E^2/Z0")
        if unit == "dBm":
            return 10.0 ** (readings / 10.0), "mW", "dBm -> mW at the analyzer port (no AF given)"
        return 10.0 ** (readings / 10.0), "uV^2", "dBuV -> uV^2 (no AF given)"
    if unit == "%":
        return readings, "% of standard", "analysed as given (Narda shaped-probe % of standard)"
    return readings, unit or "a.u.", "unit unknown: analysed as given"


def to_field_like(values: np.ndarray, unit: str | None,
                  z0_ohm: float = Z0_OHM) -> tuple[np.ndarray, str]:
    """Readings as field strength (V/m, A/m or T) for the time-series page.

    Power-density readings are converted to the equivalent plane-wave field
    E = sqrt(S Z0) (0.0.3; before, they were shown as logged).
    """
    readings = np.asarray(values, dtype=float)
    scale_and_label = {"kV/m": (1e3, "V/m"), "V/m": (1.0, "V/m"), "mV/m": (1e-3, "V/m"),
                       "uV/m": (1e-6, "V/m"), "A/m": (1.0, "A/m"), "mA/m": (1e-3, "A/m"),
                       "mT": (1e-3, "T"), "uT": (1e-6, "T"), "nT": (1e-9, "T")}
    if unit in scale_and_label:
        scale, label = scale_and_label[unit]
        return readings * scale, label
    if unit == "dBuV/m":
        return 10.0 ** ((readings - 120.0) / 20.0), "V/m"
    if unit in POWER_DENSITY_TO_SI or unit == "dBmW/m2":
        power_w_m2, _, _ = to_power_like(readings, unit, z0_ohm)
        return power_to_field(power_w_m2, z0_ohm), "V/m"
    return readings, unit or "a.u."


# ---- display units (0.0.3, extended to every unit family in 0.0.4) ------------------
#: Power-density units: key -> W/m^2 per unit (reading x factor = W/m^2).
POWER_DENSITY_TO_SI: dict[str, float] = {
    "W/m2": 1.0, "mW/m2": 1e-3, "uW/m2": 1e-6,
    "mW/cm2": 10.0, "uW/cm2": 1e-2, "nW/cm2": 1e-5,
}


@dataclass(frozen=True)
class DisplayUnit:
    """One unit in which a quantity can be shown (0.0.4).

    A value v, held in the base unit of its family (W/m^2, V/m, A/m, T, mW
    or uV, see UNIT_FAMILIES), is shown as

        linear unit (db == 0):  factor * v                       e.g. mW/cm^2
        level unit  (db > 0) :  db * log10(factor * v)           e.g. dBuV/m

    with db = 10 for power quantities (power density, port power) and
    db = 20 for root-power (field) quantities (E, H, B, port voltage), the
    convention for levels of power and root-power quantities [R19][R20].

    Attributes
    ----------
    key:
        Canonical key used on the command line and in settings ("mW/cm2").
    family:
        UNIT_FAMILIES key: "S", "E", "H", "B", "P" or "V" ("E2" etc. for the
        squared units made by squared_unit()).
    factor:
        Multiplier from the family's base unit to this unit (linear part).
    label:
        Text for axes and tables ("mW/cm²", "dBµV/m").
    db:
        0 (linear), 10 (power level) or 20 (field level).
    ref:
        The reference unit of a level unit ("µV/m" for dBµV/m); for a linear
        unit the label itself.
    """
    key: str
    family: str
    factor: float
    label: str
    db: int = 0
    ref: str = ""

    @property
    def ref_label(self) -> str:
        """Unit in which the linear quantity is expressed (for PSD labels)."""
        return self.ref or self.label

    @property
    def is_level(self) -> bool:
        """True for dB units."""
        return self.db > 0


@dataclass(frozen=True)
class UnitFamily:
    """A physical quantity whose values can be shown in several units."""
    title: str        # "Power density"
    base: str         # unit of the values held by the program ("W/m²")
    default: str      # default display unit key
    power_like: bool  # True: levels are 10 log10; False: 20 log10


#: Unit families (0.0.4). The base unit is the unit of the analysed values:
#: SI for fields and power density, mW for dBm inputs without an antenna
#: factor and uV (as uV^2) for dBuV inputs without one.
UNIT_FAMILIES: dict[str, UnitFamily] = {
    "S": UnitFamily("Power density", "W/m²", "W/m2", True),
    "E": UnitFamily("Electric field E", "V/m", "V/m", False),
    "H": UnitFamily("Magnetic field H", "A/m", "A/m", False),
    "B": UnitFamily("Magnetic flux density B", "T", "uT", False),
    "P": UnitFamily("Port power (no antenna factor)", "mW", "dBm", True),
    "V": UnitFamily("Port voltage (no antenna factor)", "µV", "dBuV", False),
}

_MU = "µ"
#: Every display unit, by key. Factors are exact powers of ten (1 mW/cm^2
#: = 1e-3 W / 1e-4 m^2 = 10 W/m^2, so 1 W/m^2 = 0.1 mW/cm^2).
DISPLAY_UNITS: dict[str, DisplayUnit] = {unit.key: unit for unit in (
    # power density (base W/m^2)
    DisplayUnit("W/m2", "S", 1.0, "W/m²"),
    DisplayUnit("mW/m2", "S", 1e3, "mW/m²"),
    DisplayUnit("uW/m2", "S", 1e6, f"{_MU}W/m²"),
    DisplayUnit("mW/cm2", "S", 0.1, "mW/cm²"),
    DisplayUnit("uW/cm2", "S", 100.0, f"{_MU}W/cm²"),
    DisplayUnit("nW/cm2", "S", 1e5, "nW/cm²"),
    DisplayUnit("dBW/m2", "S", 1.0, "dBW/m²", 10, "W/m²"),
    DisplayUnit("dBm/m2", "S", 1e3, "dBm/m²", 10, "mW/m²"),
    # electric field strength (base V/m)
    DisplayUnit("V/m", "E", 1.0, "V/m"),
    DisplayUnit("mV/m", "E", 1e3, "mV/m"),
    DisplayUnit("uV/m", "E", 1e6, f"{_MU}V/m"),
    DisplayUnit("kV/m", "E", 1e-3, "kV/m"),
    DisplayUnit("dBV/m", "E", 1.0, "dBV/m", 20, "V/m"),
    DisplayUnit("dBuV/m", "E", 1e6, f"dB{_MU}V/m", 20, f"{_MU}V/m"),
    # magnetic field strength (base A/m)
    DisplayUnit("A/m", "H", 1.0, "A/m"),
    DisplayUnit("mA/m", "H", 1e3, "mA/m"),
    DisplayUnit("uA/m", "H", 1e6, f"{_MU}A/m"),
    DisplayUnit("dBuA/m", "H", 1e6, f"dB{_MU}A/m", 20, f"{_MU}A/m"),
    # magnetic flux density (base T)
    DisplayUnit("T", "B", 1.0, "T"),
    DisplayUnit("mT", "B", 1e3, "mT"),
    DisplayUnit("uT", "B", 1e6, f"{_MU}T"),
    DisplayUnit("nT", "B", 1e9, "nT"),
    DisplayUnit("pT", "B", 1e12, "pT"),
    # power at the analyzer port, dBm inputs without antenna factor (base mW)
    DisplayUnit("W", "P", 1e-3, "W"),
    DisplayUnit("mW", "P", 1.0, "mW"),
    DisplayUnit("uW", "P", 1e3, f"{_MU}W"),
    DisplayUnit("nW", "P", 1e6, "nW"),
    DisplayUnit("dBW", "P", 1e-3, "dBW", 10, "W"),
    DisplayUnit("dBm", "P", 1.0, "dBm", 10, "mW"),
    # voltage at the analyzer port, dBuV inputs without antenna factor (base uV)
    DisplayUnit("V", "V", 1e-6, "V"),
    DisplayUnit("mV", "V", 1e-3, "mV"),
    DisplayUnit("uV", "V", 1.0, f"{_MU}V"),
    DisplayUnit("dBV", "V", 1e-6, "dBV", 20, "V"),
    DisplayUnit("dBuV", "V", 1.0, f"dB{_MU}V", 20, f"{_MU}V"),
)}
#: Other spellings accepted by lookup_display_unit (after normalisation).
_DISPLAY_UNIT_ALIASES = {"dbmw/m2": "dBm/m2", "dbm/m2": "dBm/m2", "dbw/m2": "dBW/m2",
                         "db(uv/m)": "dBuV/m", "db(ua/m)": "dBuA/m", "db(uv)": "dBuV",
                         "db(w/m2)": "dBW/m2", "db(mw/m2)": "dBm/m2"}

#: Analysed quantity unit (as produced by to_power_like / to_field_like /
#: analyse_spectrumset) -> (root family, squared?). A squared quantity
#: (field squared of the EHP-50 TS, B^2, uV^2) is shown in the square of the
#: root family's chosen unit.
QUANTITY_FAMILY: dict[str, tuple[str, bool]] = {
    "W/m^2": ("S", False), "V/m": ("E", False), "A/m": ("H", False), "T": ("B", False),
    "mW": ("P", False), "uV^2": ("V", True), "T^2": ("B", True),
    "(V/m)^2": ("E", True), "(A/m)^2": ("H", True), "(T)^2": ("B", True),
}
#: Field unit of SeriesResult.field_values -> family of the logged field.
FIELD_FAMILY = {"V/m": "E", "A/m": "H", "T": "B"}

#: What the time plot / time pages show (0.0.4; 0.0.3 had "power density",
#: "field V/m" and "field dBuV/m", mapped by normalise_time_display).
TIME_DISPLAY_MODES: dict[str, str] = {
    "power density": "S", "E field": "E", "H field": "H",
    "logged field": "logged", "analysed quantity": "quantity",
}
#: How RF spectrogram levels are shown (power-density inputs only offer E/H).
RF_LEVEL_MODES: dict[str, str] = {"power density": "S", "E field": "E", "H field": "H"}
#: Veusz layouts for several units.
VEUSZ_LAYOUTS = ("sections", "files")


def lookup_display_unit(text: str) -> DisplayUnit:
    """The DisplayUnit for a key or a common spelling ("mW/cm^2", "dB(µV/m)", "dBm/m²").

    Raises ValueError for an unknown unit (the message lists the keys).
    """
    cleaned = (str(text).strip().replace("µ", "u").replace("μ", "u")
               .replace("²", "2").replace("^2", "2").replace("**2", "2").replace(" ", ""))
    lowered = cleaned.lower()
    if lowered in _DISPLAY_UNIT_ALIASES:
        return DISPLAY_UNITS[_DISPLAY_UNIT_ALIASES[lowered]]
    if cleaned in DISPLAY_UNITS:
        return DISPLAY_UNITS[cleaned]
    matches = [unit for key, unit in DISPLAY_UNITS.items() if key.lower() == lowered]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"unknown display unit {text!r}; known: {', '.join(DISPLAY_UNITS)}")


def _split_units(spec: str | Sequence[str] | None) -> list[str]:
    """Comma/semicolon separated unit list (or a sequence) -> list of non-empty items."""
    if spec is None:
        return []
    parts = re.split(r"[;,]", spec) if isinstance(spec, str) else list(spec)
    return [part.strip() for part in parts if part and part.strip()]


def unit_selection(spec: str | Sequence[str] | None = None,
                   base: dict[str, str] | None = None) -> dict[str, str]:
    """Display unit per family: the defaults (or ``base``) overridden by ``spec``.

    ``spec`` is a list such as "mW/cm2,dBuV/m"; each unit sets its own family,
    so the order does not matter. Returns {family: unit key}.
    """
    selection = dict(base) if base else {name: family.default for name, family in UNIT_FAMILIES.items()}
    for item in _split_units(spec):
        unit = lookup_display_unit(item)
        selection[unit.family] = unit.key
    return selection


def selection_text(selection: dict[str, str]) -> str:
    """Inverse of unit_selection: "W/m2,V/m,A/m,uT,dBm,dBuV" (family order)."""
    return ",".join(selection[name] for name in UNIT_FAMILIES)


def _squared_label(label: str) -> str:
    """'V/m' -> '(V/m)²', 'µT' -> 'µT²'."""
    return f"({label})²" if "/" in label else f"{label}²"


def squared_unit(unit: DisplayUnit) -> DisplayUnit:
    """The unit of the square of a quantity shown in ``unit``.

    A linear unit squares its factor (µT -> µT², factor 1e12). A field level
    20 log10(x/ref) becomes the power level 10 log10(x²/ref²) of the square:
    the same number for x² = (field)², labelled "dB re 1 (ref)²".
    """
    if unit.is_level:
        ref = _squared_label(unit.ref)
        return DisplayUnit(unit.key + "^2", unit.family + "2", unit.factor ** 2, f"dB re 1 {ref}", 10, ref)
    return DisplayUnit(unit.key + "^2", unit.family + "2", unit.factor ** 2, _squared_label(unit.label))


def unit_for_quantity(quantity_unit: str | None, selection: dict[str, str]) -> DisplayUnit | None:
    """Display unit of an analysed quantity, or None when it has no family (%, dB rel., a.u.)."""
    family_info = QUANTITY_FAMILY.get(quantity_unit or "")
    if family_info is None:
        return None
    root_family, squared = family_info
    unit = DISPLAY_UNITS[selection.get(root_family, UNIT_FAMILIES[root_family].default)]
    return squared_unit(unit) if squared else unit


def to_display(values: Any, unit: DisplayUnit | None, floor_rel: float = 1e-15) -> np.ndarray:
    """Values held in the family base unit, expressed in ``unit``.

    Linear units scale; level units take db*log10, with values at or below
    zero clipped to ``floor_rel`` times the largest positive value (NaN stays
    NaN). None returns the values unchanged.
    """
    array = np.asarray(values, dtype=float)
    if unit is None:
        return array
    scaled = array * unit.factor
    if not unit.is_level:
        return scaled
    positive = scaled[np.isfinite(scaled) & (scaled > 0)]
    floor = float(positive.max()) * floor_rel if positive.size else 1e-300
    with np.errstate(invalid="ignore"):
        return unit.db * np.log10(np.where(np.isnan(scaled), np.nan, np.maximum(scaled, floor)))


def from_display(shown: Any, unit: DisplayUnit) -> np.ndarray:
    """Inverse of to_display (values back in the family base unit)."""
    array = np.asarray(shown, dtype=float)
    if unit.is_level:
        return 10.0 ** (array / unit.db) / unit.factor
    return array / unit.factor


def display_label(unit: DisplayUnit | None, quantity_unit: str | None = None) -> str:
    """Axis/table label of a unit (the analysis unit when there is no display unit)."""
    return unit.label if unit is not None else unit_label(quantity_unit)


def psd_to_display_db(psd: Any, unit: DisplayUnit | None, quantity_unit: str | None = None,
                      floor_rel: float = 1e-15) -> tuple[np.ndarray, str]:
    """A PSD (base unit squared per Hz) as 10 log10 of (display unit)^2/Hz.

    For a linear unit with factor k: 10 log10(k² PSD) in dB re 1 (unit)²/Hz.
    For a level unit the same with its linear reference (dBµV/m -> (µV/m)²/Hz),
    so the Welch PSD and the spectrogram read the same in mW/cm² and in
    dBm/m² apart from the reference.
    """
    factor = unit.factor if unit is not None else 1.0
    shown = np.asarray(psd, dtype=float) * factor ** 2
    finite = shown[np.isfinite(shown)]
    floor = float(finite.max()) * floor_rel if finite.size and finite.max() > 0 else 1e-300
    reference = unit.ref_label if unit is not None else unit_label(quantity_unit)
    return 10.0 * np.log10(np.maximum(shown, floor)), f"dB re 1 ({reference})²/Hz"


def psd_db_offset(unit: DisplayUnit | None) -> float:
    """dB to add to 10 log10(PSD in base units) for the display unit: 20 log10(factor)."""
    return 20.0 * math.log10(unit.factor) if unit is not None else 0.0


def power_to_field(power_w_m2: Any, z0_ohm: float = Z0_OHM) -> np.ndarray:
    """Plane-wave field strength E = sqrt(S Z0) in V/m from S in W/m^2."""
    return np.sqrt(np.maximum(np.asarray(power_w_m2, dtype=float), 0.0) * z0_ohm)


def power_to_h_field(power_w_m2: Any, z0_ohm: float = Z0_OHM) -> np.ndarray:
    """Plane-wave magnetic field H = sqrt(S / Z0) = E / Z0 in A/m from S in W/m^2."""
    return np.sqrt(np.maximum(np.asarray(power_w_m2, dtype=float), 0.0) / z0_ohm)


def field_to_dbuv_m(field_v_m: Any) -> np.ndarray:
    """E in dB(uV/m): 20 log10(E / 1 uV/m) = 20 log10(E / 1 V/m) + 120."""
    return 20.0 * np.log10(np.maximum(np.asarray(field_v_m, dtype=float), 1e-30)) + 120.0


def time_quantity(result: Any, family: str) -> np.ndarray | None:
    """The record of a SeriesResult as ``family`` (S, E, H, B) in base units, or None.

    Uses what was logged plus the far-field plane-wave relations with the
    result's Z0:  S = E²/Z0 = Z0 H²,  E = sqrt(S Z0) = Z0 H,  H = sqrt(S/Z0).
    B is only available when B was logged (no free-space conversion is
    assumed for low-frequency magnetic fields).
    """
    z0_ohm = float(getattr(result, "z0_ohm", Z0_OHM))
    logged_family = FIELD_FAMILY.get(result.field_unit)
    logged = np.asarray(result.field_values, dtype=float)
    power: np.ndarray | None = None
    if result.quantity_unit == "W/m^2" and np.asarray(result.quantity).size == logged.size:
        power = np.asarray(result.quantity, dtype=float)
    elif logged_family == "E":
        power = logged ** 2 / z0_ohm
    elif logged_family == "H":
        power = z0_ohm * logged ** 2
    if family == logged_family:
        return logged
    if family == "S":
        return power
    if family == "E" and power is not None:
        return power_to_field(power, z0_ohm)
    if family == "H" and power is not None:
        return power_to_h_field(power, z0_ohm)
    return None


def available_time_families(result: Any) -> list[str]:
    """Families time_quantity() can give for ``result`` (order S, E, H, B)."""
    return [family for family in ("S", "E", "H", "B") if time_quantity(result, family) is not None]


def normalise_time_display(mode: str | None) -> str:
    """Accept the 0.0.3 names ('field V/m', 'field dBuV/m') and return a TIME_DISPLAY_MODES key."""
    if mode in TIME_DISPLAY_MODES:
        return str(mode)
    if mode and str(mode).startswith("field"):
        return "E field"
    return "power density"


def time_display_values(result: Any, mode: str, selection: dict[str, str]) -> tuple[np.ndarray, str, str]:
    """(values, axis label, family) for a time plot of ``result`` in ``mode``.

    Falls back to the analysed quantity when the mode's quantity cannot be
    derived from the record (e.g. E field of a dBm port log); the axis label
    then names what is shown.
    """
    mode = normalise_time_display(mode)
    family = TIME_DISPLAY_MODES[mode]
    if family == "logged":
        family = FIELD_FAMILY.get(result.field_unit, "quantity")
    if family in UNIT_FAMILIES:
        values = time_quantity(result, family)
        if values is not None:
            unit = DISPLAY_UNITS[selection[family]]
            return to_display(values, unit), f"{UNIT_FAMILIES[family].title} ({unit.label})", family
    unit = unit_for_quantity(result.quantity_unit, selection)
    name = "Power density" if result.quantity_unit == "W/m^2" else "Analysed quantity"
    return (to_display(result.quantity, unit), f"{name} ({display_label(unit, result.quantity_unit)})",
            "quantity")


def rf_level_display(level_db: Any, power_unit: str, selection: dict[str, str], mode: str = "power density",
                     z0_ohm: float = Z0_OHM) -> tuple[np.ndarray, str]:
    """RF levels (10 log10 of power in the base unit of ``power_unit``) in the display unit.

    Power-like units: level + 10 log10(factor), label "dBm/m²" for a level
    unit or "dB re 1 mW/cm²" for a linear one. For power-density levels
    ``mode`` may ask for E or H of the equivalent plane wave:
    20 log10(k E) = level + 10 log10(Z0) + 20 log10(k) and
    20 log10(k H) = level - 10 log10(Z0) + 20 log10(k).
    """
    levels = np.asarray(level_db, dtype=float)
    family_info = QUANTITY_FAMILY.get(power_unit)
    target = RF_LEVEL_MODES.get(mode, "S")
    if family_info == ("S", False) and target in ("E", "H"):
        unit = DISPLAY_UNITS[selection[target]]
        offset = (1.0 if target == "E" else -1.0) * 10 * math.log10(z0_ohm) + 20 * math.log10(unit.factor)
        label = unit.label if unit.is_level else f"dB re 1 {unit.label}"
        return levels + offset, label
    unit = unit_for_quantity(power_unit, selection)
    if unit is None:
        return levels, f"dB re 1 {unit_label(power_unit)}"
    label = unit.label if unit.is_level else f"dB re 1 {unit.label}"
    return levels + 10 * math.log10(unit.factor), label


def rf_level_families(power_unit: str) -> list[str]:
    """Families in which RF levels of ``power_unit`` can be shown."""
    family_info = QUANTITY_FAMILY.get(power_unit)
    if family_info is None:
        return []
    return ["S", "E", "H"] if family_info == ("S", False) else [family_info[0]]


def unit_table_rows() -> list[tuple[str, str, str, str, str]]:
    """(family, key, label, conversion, level rule) for --list-units and the manual."""
    rows = []
    for unit in DISPLAY_UNITS.values():
        family = UNIT_FAMILIES[unit.family]
        if unit.is_level:
            conversion = f"{unit.db} log10({unit.factor:g} x value in {family.base})"
            rule = f"{unit.db} log10 ({'power' if unit.db == 10 else 'root-power'} level re 1 {unit.ref})"
        else:
            conversion = f"{unit.factor:g} x value in {family.base}"
            rule = "linear"
        rows.append((family.title, unit.key, unit.label, conversion, rule))
    return rows


# ---- 0.0.3 helpers kept for compatibility (power density only) ----------------------
#: Display units for power density: key -> (factor applied to W/m^2, label).
POWER_DISPLAY_UNITS: dict[str, tuple[float, str]] = {
    key: (unit.factor, unit.label) for key, unit in DISPLAY_UNITS.items() if unit.family == "S" and not unit.db}


def display_power(values_w_m2: Any, display_unit: str = "W/m2") -> tuple[np.ndarray, str]:
    """Power-density values in a display unit (any S-family unit, dB units included)."""
    unit = lookup_display_unit(display_unit)
    return to_display(values_w_m2, unit), unit.label


def display_psd(psd_w2_m4_hz: Any, display_unit: str = "W/m2") -> tuple[np.ndarray, str]:
    """A PSD in (W/m^2)^2/Hz expressed in (display unit)^2/Hz (factor squared, linear)."""
    unit = lookup_display_unit(display_unit)
    return np.asarray(psd_w2_m4_hz, dtype=float) * unit.factor ** 2, f"({unit.ref_label})²/Hz"


def unit_label(unit: str | None) -> str:
    """Readable label of an analysis unit ("W/m^2" -> "W/m²", "uV^2" -> "µV²")."""
    text = (unit or "a.u.").replace("^2", "²").replace("dBu", "dBµ")
    return re.sub(r"\bu(?=[VWAT])", "µ", text)


# %% ===========================================================================
#    DATA MODEL
# =============================================================================
@dataclass
class TimeSeries:
    """One probe log: values against time.

    Attributes
    ----------
    name:
        Label (file stem or channel name).
    time_s:
        Seconds since the first sample (float64, may be a memmap).
    values:
        Readings in ``unit`` (combined/RSS value).
    unit:
        Canonical unit key or None.
    axes:
        Optional per-axis readings {"X": ..., "Y": ..., "Z": ...}.
    t0_veusz:
        Wall-clock time of the first sample as Veusz date seconds, or None.
    t0_text:
        Same as ISO text, for titles and the summary.
    source:
        Reader that produced it.
    meta:
        Header lines, column choices and reader notes.
    """
    name: str
    time_s: np.ndarray
    values: np.ndarray
    unit: str | None
    axes: dict[str, np.ndarray] = field(default_factory=dict)
    t0_veusz: float | None = None
    t0_text: str = ""
    source: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpectrumSet:
    """A sequence of RF (or LF) spectra: a spectrogram.

    ``level`` has shape (n_time, n_freq) in ``unit``.
    """
    name: str
    time_s: np.ndarray
    freq_hz: np.ndarray
    level: np.ndarray
    unit: str | None
    t0_veusz: float | None = None
    t0_text: str = ""
    source: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Options:
    """Analysis settings (one object passed to every worker).

    The field names match the command-line options (see build_parser).
    """
    probe: str | None = None
    source: str = "auto"
    fs: float | None = None
    t_int: float | None = None
    quantity: str = "power"           # power | field | db
    window: str = "hann"
    nperseg: int | None = None
    zoom: tuple[float, float] | None = None
    zoom_points: int = 4096
    lomb: str = "auto"                # auto | on | off
    correct_probe: bool = False
    max_boost_db: float = 12.0
    rf_channels: str = "auto:3"
    antenna_factor_db: float | None = None
    z0: float = Z0_OHM
    out: str | None = None
    gpu: bool = False
    fft_workers: int = -1
    render: bool = False
    pickle: bool = False
    time_col: str | None = None
    value_col: str | None = None
    unit: str | None = None
    sep: str | None = None
    decimal: str | None = None
    dayfirst: bool | None = None
    h5_level: str | None = None
    h5_freq: str | None = None
    h5_time: str | None = None
    snr: float = 6.0
    max_peaks: int = 12
    dyn_range_db: float = 50.0
    # -- unit control (0.0.4): display only; CSV/NPZ/JSON files stay in SI units
    display_unit: str = "W/m2"        # display units, one per family: "mW/cm2,dBuV/m" (DISPLAY_UNITS)
    time_display: str = "power density"   # TIME_DISPLAY_MODES key
    rf_level_display: str = "power density"   # RF_LEVEL_MODES key
    veusz_units: str = ""             # extra units for the Veusz documents ("dBm/m2,dBuV/m")
    veusz_layout: str = "sections"    # sections: one document, a section per unit; files: one per unit
    rbw_hz: float | None = None       # spectrogram RBW: absolute channel power (0.0.3)
    enbw_factor: float = GAUSSIAN_ENBW_FACTOR


# %% ===========================================================================
#    MEMORY HELPERS (bounded RAM for long logs)
# =============================================================================
#: Spill files created in this process; deleted at exit (a file that is still
#: memory-mapped cannot be deleted on Windows before then).
_SPILL_FILES: list[str] = []


@atexit.register
def _remove_spill_files() -> None:
    """Delete this process's spill files (best effort)."""
    gc.collect()
    for spill_path in _SPILL_FILES:
        try:
            os.unlink(spill_path)
        except OSError:
            pass


class SpillBuffer:
    """Append-only float64 buffer that moves to a disk memmap when it grows.

    Values are kept in RAM until ``limit`` samples, then written to a temporary
    raw file; ``array()`` returns an ndarray (small) or a read-only memmap
    (large). Call ``close()`` (or use as a context manager) to release it.
    """

    def __init__(self, limit: int = SPILL_SAMPLES, workdir: str | None = None) -> None:
        self.limit = int(limit)
        self.workdir = workdir
        self._ram_chunks: list[np.ndarray] = []
        self._n_in_ram = 0
        self._spill_handle: Any = None
        self._spill_path: str | None = None
        self._n_on_disk = 0

    def extend(self, values: np.ndarray) -> None:
        """Append values (converted to float64)."""
        new_values = np.ascontiguousarray(values, dtype=np.float64)
        if self._spill_handle is None and self._n_in_ram + new_values.size <= self.limit:
            self._ram_chunks.append(new_values)
            self._n_in_ram += new_values.size
            return
        if self._spill_handle is None:             # first spill: move RAM to disk
            fd, self._spill_path = tempfile.mkstemp(suffix=".f64", prefix="emf_fft_spill_",
                                                    dir=self.workdir)
            self._spill_handle = os.fdopen(fd, "wb")
            _SPILL_FILES.append(self._spill_path)
            for chunk in self._ram_chunks:
                chunk.tofile(self._spill_handle)
            self._n_on_disk = self._n_in_ram
            self._ram_chunks, self._n_in_ram = [], 0
        new_values.tofile(self._spill_handle)
        self._n_on_disk += new_values.size

    def __len__(self) -> int:
        return self._n_in_ram + self._n_on_disk

    def array(self) -> np.ndarray:
        """All values: an ndarray, or a read-only memmap when spilled."""
        if self._spill_handle is None:
            return np.concatenate(self._ram_chunks) if self._ram_chunks else np.empty(0)
        self._spill_handle.flush()
        return np.memmap(self._spill_path, dtype=np.float64, mode="r", shape=(self._n_on_disk,))

    def close(self) -> None:
        """Release RAM and try to delete the spill file (memmaps must be dropped first)."""
        self._ram_chunks = []
        if self._spill_handle is not None:
            self._spill_handle.close()
            self._spill_handle = None
            try:
                os.unlink(self._spill_path)
            except OSError:                        # still mapped (Windows): removed at exit
                pass

    def __enter__(self) -> "SpillBuffer":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


def flush_memory() -> int:
    """Run the garbage collector (and free the CuPy memory pool if loaded).

    Returns the number of objects collected. Call after analysing large files.
    """
    n_collected = gc.collect()
    if "cupy" in sys.modules:
        try:
            cupy_module = sys.modules["cupy"]
            cupy_module.get_default_memory_pool().free_all_blocks()
            cupy_module.get_default_pinned_memory_pool().free_all_blocks()
        except Exception:  # noqa: BLE001 - optional
            pass
    return n_collected


def save_pickle(obj: Any, path: str | os.PathLike) -> Path:
    """Offload a result object to disk (pickle protocol 5) and return the path."""
    pickle_path = Path(path)
    with open(pickle_path, "wb") as file_handle:
        pickle.dump(obj, file_handle, protocol=5)
    return pickle_path


def load_pickle(path: str | os.PathLike) -> Any:
    """Load an object written by save_pickle (only open files you trust)."""
    with open(path, "rb") as file_handle:
        return pickle.load(file_handle)


# %% ===========================================================================
#    COMPUTE BACKEND (CPU / optional GPU)
# =============================================================================
class Backend:
    """Array namespace and FFT for CPU (NumPy/SciPy) or GPU (CuPy).

    The GPU is used only when ``use_gpu`` is set and CuPy imports and finds a
    device; everything else falls back to the CPU silently (the reason is in
    ``self.note``). ``workers`` sets SciPy's FFT thread count (-1 = all).
    """

    def __init__(self, use_gpu: bool = False, workers: int = -1) -> None:
        self.workers = workers
        self.gpu = False
        self.xp = np                               # array namespace in use
        self.note = "CPU (NumPy/SciPy)"
        if use_gpu:
            try:
                import cupy as cp
                cp.cuda.runtime.getDeviceCount()
                self.xp = cp
                self.gpu = True
                self.note = f"GPU (CuPy {cp.__version__})"
            except Exception as exc:  # noqa: BLE001 - no CUDA, no CuPy, ...
                self.note = f"CPU (GPU requested but unavailable: {type(exc).__name__})"

    def asarray(self, array: Any) -> Any:
        """Move an array to the active device."""
        return self.xp.asarray(array)

    def cpu(self, array: Any) -> np.ndarray:
        """Bring an array back to host memory."""
        return array.get() if self.gpu else np.asarray(array)

    def rfft(self, array: Any, n: int | None = None, axis: int = -1) -> Any:
        """Real FFT on the active device (SciPy threads on the CPU)."""
        if self.gpu:
            return self.xp.fft.rfft(array, n=n, axis=axis)
        return sfft.rfft(array, n=n, axis=axis, workers=self.workers)


# %% ===========================================================================
#    TEXT EXPORT SNIFFING AND READING
# =============================================================================
#: Words that mark a time/date column header (English and German).
_TIME_WORDS = ("time", "zeit", "uhrzeit", "timestamp", "date", "datum",
               "elapsed", "t [s]", "t(s)", "t/s", "sec", "hh:mm")
#: Words that make a column the preferred measured value.
_VALUE_PREFER = ("actual", "act", "rss", "total", "result 1", "isotrop", "value",
                 "wert", "e-field", "e field", "field", "level")
#: Words that make a column an unlikely measured value (statistics, house-keeping).
_VALUE_AVOID = ("max", "min", "avg", "mean", "average", "batt", "temp", "humid",
                "press", "lat", "lon", "alt", "gps", "index", "no.", "nr", "flag",
                "dist", "comment")


@dataclass
class TextLayout:
    """How a delimited text export is laid out (result of sniff_text)."""
    path: str
    encoding: str
    sep: str                 # delimiter; r"\s+" for whitespace
    decimal: str
    header_row: int          # 0-based line index of the column-name row (-1: none)
    columns: list[str]
    meta_lines: list[str]
    unit_hint: str | None


def _read_head(path: str | os.PathLike, n_lines: int = 400) -> tuple[list[str], str]:
    """First ``n_lines`` lines and the encoding that decoded them."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=encoding, newline="") as file_handle:
                head_lines = []
                for _ in range(n_lines):
                    line = file_handle.readline()
                    if not line:
                        break
                    head_lines.append(line.rstrip("\r\n"))
            return head_lines, encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode {path}")


def _is_number(token: str, decimal: str) -> bool:
    """True if ``token`` parses as a number with the given decimal mark."""
    cleaned = token.strip().strip('"')
    if decimal == "," and cleaned.count(",") == 1:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        float(cleaned)
        return True
    except ValueError:
        return False


def _split(line: str, sep: str) -> list[str]:
    """Split one line on ``sep`` (CSV quoting honoured; r"\\s+" = whitespace)."""
    if sep == r"\s+":
        return line.split()
    return next(csv.reader([line], delimiter=sep))


def sniff_text(path: str | os.PathLike, sep: str | None = None,
               decimal: str | None = None) -> TextLayout:
    """Work out delimiter, decimal mark, header row and metadata of a text export.

    Narda software is German-made, so ';' with a decimal comma is expected
    as often as ',' with a decimal point; both are detected. Lines before
    the column-name row are kept as metadata (and searched for a unit).
    """
    head_lines, encoding = _read_head(path)
    nonblank = [line for line in head_lines if line.strip()]
    if not nonblank:
        raise ValueError(f"{path}: empty file")
    # -- delimiter: priority tab, ';', ',', '|': the first that appears the
    #    same number of times on every data line wins. ';' before ',' because
    #    a decimal comma puts a ',' inside every number (European exports).
    if sep is None:
        sep = r"\s+"
        data_tail = nonblank[-50:]
        for candidate in ("\t", ";", ",", "|"):
            counts = [line.count(candidate) for line in data_tail]
            if min(counts) >= 1 and max(counts) - min(counts) <= max(1, 0.1 * np.median(counts)):
                sep = candidate
                break
    # -- decimal mark: ',' if numbers like 1,23 appear and ',' is not the sep
    if decimal is None:
        decimal = "."
        if sep != ",":
            sample_text = " ".join(nonblank[-50:])
            if re.search(r"\d,\d", sample_text) and not re.search(
                    r"\d\.\d+\D", sample_text.replace(":", " ")):
                decimal = ","
            elif re.search(r"(?<![\d.])\d+,\d+(?![\d.])", sample_text) and sep in (";", "\t"):
                decimal = ","

    # -- header row: a row with the same field count as the row below it,
    #    holding text where that row (mostly numbers or date/times) has data.
    #    This also finds wide spectrogram headers ("Time [s];2400.0;2400.25;...").
    def is_data_like(token: str) -> bool:
        return _is_number(token, decimal) or bool(re.match(r"^\s*\"?\d{1,4}[./:-]\d", token))

    header_row = -1
    for line_index, line in enumerate(head_lines):
        if not line.strip():
            continue
        fields = _split(line, sep)
        if len(fields) < 2:
            continue
        next_line = next((head_lines[j] for j in range(line_index + 1, min(line_index + 4, len(head_lines)))
                          if head_lines[j].strip()), "")
        next_fields = _split(next_line, sep) if next_line else []
        if not next_fields or abs(len(next_fields) - len(fields)) > 1:
            continue
        text_here = sum(not is_data_like(f) for f in fields if f.strip())
        text_next = sum(not is_data_like(f) for f in next_fields if f.strip())
        data_next = len(next_fields) - text_next
        if text_here > text_next and data_next >= max(1, len(next_fields) // 2):
            header_row = line_index
            break
    if header_row < 0:                             # no header: numeric from the top
        first_data_row = next(i for i, line in enumerate(head_lines) if line.strip()
                              and any(_is_number(f, decimal) for f in _split(line, sep)))
        header_row = first_data_row - 1
        columns = [f"col{k}" for k in range(len(_split(head_lines[first_data_row], sep)))]
    else:
        columns = [name.strip().strip('"') for name in _split(head_lines[header_row], sep)]
    meta_lines = [line for line in head_lines[:max(header_row, 0)] if line.strip()]
    unit_hint = None
    for text in columns + meta_lines:
        unit_hint = unit_hint or parse_unit(text)
    return TextLayout(str(path), encoding, sep, decimal, header_row, columns, meta_lines, unit_hint)


def _pick_columns(layout: TextLayout, time_col: str | None,
                  value_col: str | None) -> tuple[list[int], int | None, dict[str, int]]:
    """Choose the time column(s), the value column and X/Y/Z columns.

    Returns (time_indices, value_index, axis_indices) where time_indices may
    hold a date and a time column to be joined.
    """
    lower_names = [name.lower() for name in layout.columns]

    def find_column(requested: str) -> int:
        for index, name in enumerate(layout.columns):
            if name == requested or name.lower() == requested.lower():
                return index
        if requested.isdigit():
            return int(requested)
        raise KeyError(f"column {requested!r} not found in {layout.columns}")

    # -- time: explicit, or a date column plus a time column, or one column
    if time_col:
        time_indices = [find_column(part) for part in time_col.split("+")]
    else:
        time_indices = [i for i, name in enumerate(lower_names) if any(w in name for w in _TIME_WORDS)]
        date_indices = [i for i in time_indices if "dat" in lower_names[i]]
        clock_indices = [i for i in time_indices if i not in date_indices]
        time_indices = (date_indices[:1] + clock_indices[:1]) if date_indices and clock_indices \
            else time_indices[:1]
    # -- axes X/Y/Z (EFD-0691 has three separate axes [R2])
    axis_indices: dict[str, int] = {}
    for index, name in enumerate(lower_names):
        match = re.match(r"^\s*(?:e[_ -]?|h[_ -]?|field[_ ]?)?([xyz])(?:[\s_\[(]|$)", name)
        if match and index not in time_indices:
            axis_indices.setdefault(match.group(1).upper(), index)
    # -- value: explicit, or the best-scoring remaining column
    if value_col:
        value_index: int | None = find_column(value_col)
    else:
        candidates = [i for i in range(len(lower_names))
                      if i not in time_indices and i not in axis_indices.values()]
        scored = []
        for index in candidates:
            name = lower_names[index]
            score = 5 * any(w in name for w in _VALUE_PREFER)
            score += 3 * (parse_unit(name) is not None)
            score -= 6 * any(w in name for w in _VALUE_AVOID)
            scored.append((score, -index, index))  # ties: leftmost column
        value_index = max(scored)[2] if scored else None
        if value_index is not None and max(scored)[0] < 0 and axis_indices:
            value_index = None                     # only axes: RSS computed later
    return time_indices, value_index, axis_indices


@dataclass
class TimeOrigin:
    """Origin of a time column, fixed by the first chunk and reused after it.

    kind is "num" (seconds; ``first`` holds the first value) or "dt"
    (date/time strings; ``first`` holds the first pandas Timestamp).
    """
    kind: str
    first: Any
    scale: float = 1.0
    dayfirst: bool = False


def _to_seconds(raw_column: Any, header: str, dayfirst: bool | None,
                origin: TimeOrigin | None = None) -> tuple[np.ndarray, TimeOrigin]:
    """Parse a time column (numbers or date/time strings) to seconds.

    The first call (``origin`` None) fixes the origin from the first valid
    value; later calls (further chunks of the same file) are measured from
    that same origin, so a chunked read gives one continuous axis.
    """
    text = pd.Series(raw_column).astype(str).str.strip().str.strip('"')
    if origin is None or origin.kind == "num":
        numeric = pd.to_numeric(text.str.replace(",", ".", regex=False), errors="coerce")
        if origin is not None or numeric.notna().mean() > 0.95:   # numeric: s or ms
            seconds = numeric.to_numpy(dtype=float)
            if origin is None:
                scale = 1e-3 if re.search(r"\bms\b|\[ms\]|\(ms\)", header.lower()) else 1.0
                origin = TimeOrigin("num", float(np.nanmin(seconds)), scale)
            return (seconds - origin.first) * origin.scale, origin
    if origin is None:                              # dd.mm.yy(yy) -> day first
        use_dayfirst = dayfirst if dayfirst is not None else \
            bool(text.str.match(r"^\d{1,2}\.\d{1,2}\.\d{2,4}").mean() > 0.5)
    else:
        use_dayfirst = origin.dayfirst
    stamps = pd.to_datetime(text, format="mixed", dayfirst=use_dayfirst, errors="coerce")
    if stamps.notna().mean() < 0.95:
        raise ValueError(f"time column {header!r}: cannot parse {text.iloc[0]!r}")
    if getattr(stamps.dt, "tz", None) is not None:
        stamps = stamps.dt.tz_convert(None)
    if origin is None:
        origin = TimeOrigin("dt", stamps.dropna().iloc[0], 1.0, use_dayfirst)
    return (stamps - origin.first).dt.total_seconds().to_numpy(dtype=float), origin


def _origin_text(origin: TimeOrigin | None) -> tuple[float | None, str]:
    """(Veusz date seconds, ISO text) of a date/time origin; (None, '') otherwise."""
    if origin is None or origin.kind != "dt":
        return None, ""
    first_stamp = origin.first.to_pydatetime()
    return (first_stamp - VEUSZ_EPOCH).total_seconds(), first_stamp.isoformat()


def _num(column: Any, decimal: str) -> np.ndarray:
    """Text column -> float64, honouring a decimal comma (thousands dots removed)."""
    text = column.astype(str).str.strip().str.strip('"')
    if decimal == ",":
        text = text.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(text, errors="coerce").to_numpy(dtype=float)


def read_text_timeseries(path: str | os.PathLike, opts: Options,
                         source: str = "fieldman") -> TimeSeries:
    """Read a FieldMan / Narda-TSX / NBM / EHP-logger text export.

    Large files are read in chunks; values are kept in SpillBuffers so a
    multi-hour 900 Hz log does not have to fit in RAM.
    """
    if pd is None:
        raise RuntimeError("pandas is required (mamba install -c conda-forge pandas)")
    layout = sniff_text(path, opts.sep, opts.decimal)
    time_indices, value_index, axis_indices = _pick_columns(layout, opts.time_col, opts.value_col)
    unit = (opts.unit and parse_unit(opts.unit)) or (
        parse_unit(layout.columns[value_index]) if value_index is not None else None) \
        or layout.unit_hint
    used_columns = sorted(set(time_indices + ([value_index] if value_index is not None else [])
                              + list(axis_indices.values())))
    chunk_reader = pd.read_csv(
        layout.path, sep=layout.sep, decimal=layout.decimal, encoding=layout.encoding,
        skiprows=max(layout.header_row, 0) + (1 if layout.header_row >= 0 else 0),
        header=None, usecols=used_columns, dtype=str, chunksize=READ_CHUNK_ROWS,
        engine="python" if layout.sep not in (",", ";", "\t", r"\s+") else "c",
        skip_blank_lines=True, on_bad_lines="skip")
    time_buffer, value_buffer = SpillBuffer(), SpillBuffer()
    axis_buffers = {axis: SpillBuffer() for axis in axis_indices}
    origin: TimeOrigin | None = None
    time_header = " ".join(layout.columns[i] for i in time_indices)
    for chunk in chunk_reader:
        chunk.columns = used_columns
        if time_indices:
            raw_time = chunk[time_indices[0]] if len(time_indices) == 1 else \
                chunk[time_indices[0]].str.strip() + " " + chunk[time_indices[1]].str.strip()
            chunk_seconds, origin = _to_seconds(raw_time, time_header, opts.dayfirst, origin)
            time_buffer.extend(chunk_seconds)
        for axis, column_index in axis_indices.items():
            axis_buffers[axis].extend(_num(chunk[column_index], layout.decimal))
        if value_index is not None:
            value_buffer.extend(_num(chunk[value_index], layout.decimal))
    t0_veusz, t0_text = _origin_text(origin)
    time_s = time_buffer.array()
    axis_arrays = {axis: buffer.array() for axis, buffer in axis_buffers.items()}
    if value_index is not None:
        values = value_buffer.array()
    elif axis_arrays:                               # RSS of the three axes
        values = np.sqrt(sum(np.asarray(a) ** 2 for a in axis_arrays.values()))
    else:
        raise ValueError(f"{path}: no value column found; use --value-col")
    if not time_indices:                            # no time column: need fs
        probe = lookup_probe(opts.probe) if opts.probe else None
        sample_rate_hz = opts.fs or (probe.fs_hz if probe else None)
        if not sample_rate_hz:
            raise ValueError(f"{path}: no time column; give --fs or --probe")
        time_s = np.arange(len(values)) / sample_rate_hz
    meta = {"layout": {k: v for k, v in asdict(layout).items() if k != "meta_lines"},
            "header_lines": layout.meta_lines[:40],
            "time_columns": [layout.columns[i] for i in time_indices],
            "value_column": layout.columns[value_index] if value_index is not None else "RSS(X,Y,Z)",
            "axis_columns": {axis: layout.columns[i] for axis, i in axis_indices.items()}}
    return TimeSeries(Path(path).stem, np.asarray(time_s, float), np.asarray(values, float), unit,
                      {axis: np.asarray(a, float) for axis, a in axis_arrays.items()},
                      t0_veusz, t0_text, source, meta)


def read_xlsx_timeseries(path: str | os.PathLike, opts: Options) -> TimeSeries:
    """Read an Excel export by converting its first sheet to CSV first (needs openpyxl)."""
    if pd is None:
        raise RuntimeError("pandas is required")
    sheet = pd.read_excel(path, sheet_name=0, header=None, dtype=str)
    temporary_csv = Path(tempfile.mkdtemp()) / (Path(path).stem + ".csv")
    sheet.to_csv(temporary_csv, sep=";", index=False, header=False)
    try:
        series = read_text_timeseries(temporary_csv, opts, source="xlsx")
    finally:
        try:
            temporary_csv.unlink()
        except OSError:
            pass
    series.name = Path(path).stem
    return series


# ---- EHP-50 TS spectra --------------------------------------------------------------
#: EHP-50 TS auto-save file name hh_mm_ss_cc.TXT (cc = centiseconds) [R7].
_EHP_NAME = re.compile(r"(\d{2})_(\d{2})_(\d{2})_(\d{2})\.txt$", re.I)


def _ehp_time_from_path(file_path: Path) -> _dt.datetime | None:
    """EHP-50 TS auto-save path YYYY/MM/DD/hh_mm_ss_cc.TXT -> datetime [R7]."""
    match = _EHP_NAME.search(file_path.name)
    if not match:
        return None
    hours, minutes, seconds, centiseconds = (int(g) for g in match.groups())
    try:
        day = int(file_path.parent.name)
        month = int(file_path.parent.parent.name)
        year = int(file_path.parent.parent.parent.name)
        return _dt.datetime(year, month, day, hours, minutes, seconds, centiseconds * 10_000)
    except (ValueError, IndexError):               # not inside YYYY/MM/DD folders
        return _dt.datetime(2000, 1, 1, hours, minutes, seconds, centiseconds * 10_000)


def read_text_spectrum(path: str | os.PathLike, opts: Options) -> tuple[np.ndarray, np.ndarray, str | None]:
    """One spectrum file: (frequency Hz, level, unit). Total/RSS column preferred."""
    layout = sniff_text(path, opts.sep, opts.decimal)
    lower_names = [name.lower() for name in layout.columns]
    freq_index = next((i for i, name in enumerate(lower_names)
                       if "freq" in name or name.strip() in ("f", "hz", "f [hz]")), 0)
    level_candidates = [i for i in range(len(lower_names)) if i != freq_index]
    preferred = [i for i in level_candidates
                 if any(w in lower_names[i] for w in ("total", "rss", "iso", "wide", "tot"))]
    level_index = preferred[0] if preferred else level_candidates[-1]
    table = pd.read_csv(layout.path, sep=layout.sep, decimal=layout.decimal,
                        encoding=layout.encoding, skiprows=layout.header_row + 1,
                        header=None, usecols=[freq_index, level_index], dtype=str,
                        engine="python" if layout.sep == "|" else "c")
    freq = _num(table[freq_index], layout.decimal)
    level = _num(table[level_index], layout.decimal)
    freq_scale = 1e3 if "khz" in lower_names[freq_index] else 1e6 if "mhz" in lower_names[freq_index] else 1.0
    unit = parse_unit(layout.columns[level_index]) or layout.unit_hint
    valid = np.isfinite(freq) & np.isfinite(level)
    return freq[valid] * freq_scale, level[valid], unit


def read_ehp_folder(spectrum_files: Sequence[Path], opts: Options, name: str) -> SpectrumSet:
    """Many EHP-50 TS spectra (one per file) -> one SpectrumSet in time order."""
    stamped_files = []
    for file_path in spectrum_files:
        stamp = _ehp_time_from_path(file_path) or _dt.datetime.fromtimestamp(file_path.stat().st_mtime)
        stamped_files.append((stamp, file_path))
    stamped_files.sort()
    reference_freq, _, unit = read_text_spectrum(stamped_files[0][1], opts)
    level_rows, stamps = [], []
    for stamp, file_path in stamped_files:
        freq, level, _ = read_text_spectrum(file_path, opts)
        if freq.size != reference_freq.size or not np.allclose(freq, reference_freq, rtol=1e-6):
            level = np.interp(reference_freq, freq, level, left=np.nan, right=np.nan)
        level_rows.append(level)
        stamps.append(stamp)
    first_stamp = stamps[0]
    time_s = np.array([(s - first_stamp).total_seconds() for s in stamps])
    return SpectrumSet(name, time_s, reference_freq, np.vstack(level_rows), unit,
                       (first_stamp - VEUSZ_EPOCH).total_seconds(), first_stamp.isoformat(),
                       "ehp", {"files": len(spectrum_files), "first_file": str(stamped_files[0][1])})


# ---- SignalShark --------------------------------------------------------------------
def describe_h5(path: str | os.PathLike, max_lines: int = 200) -> list[str]:
    """Readable tree of an HDF5 file: groups, datasets (shape, dtype), attributes."""
    if h5py is None:
        raise RuntimeError("h5py is required (mamba install -c conda-forge h5py)")
    tree_lines: list[str] = []

    def visit(object_name: str, h5_object: Any) -> None:
        if len(tree_lines) >= max_lines:
            return
        indent = "  " * object_name.count("/")
        if isinstance(h5_object, h5py.Dataset):
            tree_lines.append(f"{indent}{object_name}  dataset {h5_object.shape} {h5_object.dtype}")
        else:
            tree_lines.append(f"{indent}{object_name}/  group")
        for attr_name, attr_value in list(h5_object.attrs.items())[:12]:
            shown = attr_value.decode(errors="replace") if isinstance(attr_value, bytes) else attr_value
            tree_lines.append(f"{indent}    @{attr_name} = {str(shown)[:80]}")

    with h5py.File(path, "r") as h5_file:
        for attr_name, attr_value in list(h5_file.attrs.items())[:20]:
            tree_lines.append(f"@{attr_name} = {str(attr_value)[:80]}")
        h5_file.visititems(visit)
    return tree_lines


def _attr_lookup(attributes: Any, *words: str) -> Any:
    """First attribute whose lower-case name contains all ``words``."""
    for attr_name, attr_value in attributes.items():
        lowered = attr_name.lower()
        if all(w in lowered for w in words):
            return attr_value.decode() if isinstance(attr_value, bytes) else attr_value
    return None


def read_signalshark_h5(path: str | os.PathLike, opts: Options) -> SpectrumSet:
    """Heuristic reader for SignalShark spectrum/spectrogram HDF5 files [R8].

    The file layout is not published. The largest 2-D numeric dataset is
    taken as levels (time x frequency); 1-D datasets whose length matches
    an axis and whose name or values look like frequencies/times become the
    axes; otherwise start/stop/span and time-resolution attributes are
    used. Override with --h5-level/--h5-freq/--h5-time (dataset paths) and
    check the result with --inspect.
    """
    if h5py is None:
        raise RuntimeError("h5py is required")
    with h5py.File(path, "r") as h5_file:
        numeric_datasets: dict[str, Any] = {}
        h5_file.visititems(lambda name, obj: numeric_datasets.__setitem__(name, obj)
                           if isinstance(obj, h5py.Dataset) and obj.dtype.kind in "fiu" else None)
        # -- the level dataset: explicit, else the largest 2-D (or 1-D) array
        if opts.h5_level:
            level_name = opts.h5_level.strip("/")
        else:
            two_d = [(obj.size, name) for name, obj in numeric_datasets.items()
                     if obj.ndim == 2 and min(obj.shape) > 1]
            if two_d:
                level_name = max(two_d)[1]
            else:                                  # a single spectrum
                level_name = max((obj.size, name) for name, obj in numeric_datasets.items()
                                 if obj.ndim == 1)[1]
        level_dataset = h5_file[level_name]
        level = np.array(level_dataset, dtype=float)
        if level.ndim == 1:
            level = level[None, :]
        # -- attributes of the dataset and all its parent groups
        all_attributes = dict(level_dataset.attrs)
        parent_group = level_dataset.parent
        while True:
            for attr_name, attr_value in parent_group.attrs.items():
                all_attributes.setdefault(attr_name, attr_value)
            if parent_group.name == "/":
                break
            parent_group = parent_group.parent

        def find_axis(explicit_name: str | None, length: int, name_words: tuple[str, ...],
                      plausible: Any) -> tuple[np.ndarray | None, str]:
            """A 1-D dataset of ``length`` that looks like the wanted axis."""
            if explicit_name:
                return np.array(h5_file[explicit_name.strip("/")], dtype=float), explicit_name
            same_length = [(name, obj) for name, obj in numeric_datasets.items()
                           if obj.ndim == 1 and obj.shape[0] == length and name != level_name]
            named = [(name, obj) for name, obj in same_length
                     if any(w in name.lower() for w in name_words)]
            for name, obj in named + same_length:
                candidate = np.array(obj, dtype=float)
                if plausible(candidate):
                    return candidate, name
            return None, ""

        n_time, n_freq = level.shape
        increasing = lambda a: a.size > 1 and np.all(np.diff(a) > 0)  # noqa: E731
        freq_axis, freq_source = find_axis(opts.h5_freq, n_freq, ("freq",),
                                           lambda a: increasing(a) and a[-1] > 1e3)
        if freq_axis is None and n_time != n_freq:  # maybe stored frequency x time
            alt_axis, alt_source = find_axis(opts.h5_freq, n_time, ("freq",),
                                             lambda a: increasing(a) and a[-1] > 1e3)
            if alt_axis is not None:
                level, (n_time, n_freq) = level.T, (n_freq, n_time)
                freq_axis, freq_source = alt_axis, alt_source + " (transposed)"
        if freq_axis is None:
            start = _attr_lookup(all_attributes, "start", "freq") or _attr_lookup(all_attributes, "fstart")
            stop = _attr_lookup(all_attributes, "stop", "freq") or _attr_lookup(all_attributes, "fstop")
            center = _attr_lookup(all_attributes, "center", "freq")
            span = _attr_lookup(all_attributes, "span")
            if start is not None and stop is not None:
                freq_axis, freq_source = np.linspace(float(start), float(stop), n_freq), "attrs start/stop"
            elif center is not None and span is not None:
                half_span = float(span) / 2
                freq_axis = np.linspace(float(center) - half_span, float(center) + half_span, n_freq)
                freq_source = "attrs center/span"
            else:
                freq_axis, freq_source = np.arange(n_freq, dtype=float), "bin index (no frequency axis found)"
        time_axis, time_source = find_axis(opts.h5_time, n_time, ("time", "stamp"), increasing)
        if time_axis is None:
            time_step = _attr_lookup(all_attributes, "time", "res") or _attr_lookup(all_attributes, "dt") \
                or (1.0 / opts.fs if opts.fs else None)
            if time_step is None:
                raise ValueError(f"{path}: no time axis; give --h5-time or --fs")
            time_axis, time_source = np.arange(n_time) * float(time_step), "attrs time resolution"
        time_axis = time_axis - time_axis[0]
        if time_axis[-1] > 1e12:                     # nanosecond stamps
            time_axis = time_axis / 1e9
        unit_text = _attr_lookup(all_attributes, "unit") or ""
        unit = parse_unit(str(unit_text)) or (opts.unit and parse_unit(opts.unit)) or "dBm"
    meta = {"level_dataset": level_name, "freq_axis": freq_source, "time_axis": time_source,
            "unit_attr": str(unit_text)}
    return SpectrumSet(Path(path).stem, time_axis, freq_axis, level, unit, None, "", "signalshark", meta)


def _safe_float(text: str) -> float:
    """float(text) with a decimal comma allowed; NaN when not a number."""
    try:
        return float(str(text).replace(",", "."))
    except ValueError:
        return float("nan")


def read_signalshark_csv(path: str | os.PathLike, opts: Options) -> SpectrumSet | TimeSeries:
    """CSV made by Narda's NSL Converter (h5 -> csv) or a similar export.

    Accepts wide format (one row per time, one column per frequency, the
    header holding frequencies), long format (time, frequency, level
    columns) and transposed wide format (one row per frequency).
    """
    layout = sniff_text(path, opts.sep, opts.decimal)
    table = pd.read_csv(layout.path, sep=layout.sep, decimal=layout.decimal,
                        encoding=layout.encoding, skiprows=max(layout.header_row, 0),
                        header=0 if layout.header_row >= 0 else None, dtype=str,
                        engine="python" if layout.sep == "|" else "c")
    column_names = [str(c) for c in table.columns]
    header_numbers = np.array([_safe_float(c.split()[0] if c.split() else c) for c in column_names])
    unit = (opts.unit and parse_unit(opts.unit)) or layout.unit_hint or "dBm"
    if np.isfinite(header_numbers).sum() >= 8:       # wide: header = frequencies
        freq_columns = [i for i, v in enumerate(header_numbers) if np.isfinite(v)]
        time_column = next((i for i in range(len(column_names)) if i not in freq_columns), None)
        freq = header_numbers[freq_columns]
        all_text = " ".join(layout.meta_lines + column_names).lower()
        freq_scale = 1e6 if "mhz" in all_text and freq.max() < 1e6 else 1.0
        level = np.column_stack([_num(table.iloc[:, i], layout.decimal) for i in freq_columns])
        if time_column is not None:
            time_s, origin = _to_seconds(table.iloc[:, time_column], column_names[time_column], opts.dayfirst)
            t0_veusz, t0_text = _origin_text(origin)
        else:
            time_s, t0_veusz, t0_text = np.arange(level.shape[0]) / (opts.fs or 1.0), None, ""
        return SpectrumSet(Path(path).stem, time_s, freq * freq_scale, level, unit, t0_veusz, t0_text,
                           "signalshark-csv", {"format": "wide"})
    lower_names = [c.lower() for c in column_names]
    freq_index = next((i for i, c in enumerate(lower_names) if "freq" in c), None)
    time_index = next((i for i, c in enumerate(lower_names)
                       if any(w in c for w in ("time", "zeit", "stamp"))), None)
    if freq_index is not None and time_index is not None:   # long format -> pivot
        level_index = next(i for i in range(len(column_names)) if i not in (freq_index, time_index))
        unit = parse_unit(column_names[level_index]) or unit
        time_s, origin = _to_seconds(table.iloc[:, time_index], column_names[time_index], opts.dayfirst)
        t0_veusz, t0_text = _origin_text(origin)
        freq = _num(table.iloc[:, freq_index], layout.decimal)
        level_values = _num(table.iloc[:, level_index], layout.decimal)
        unique_times, time_position = np.unique(time_s, return_inverse=True)
        unique_freqs, freq_position = np.unique(freq, return_inverse=True)
        level_grid = np.full((unique_times.size, unique_freqs.size), np.nan)
        level_grid[time_position, freq_position] = level_values
        return SpectrumSet(Path(path).stem, unique_times, unique_freqs, level_grid, unit,
                           t0_veusz, t0_text, "signalshark-csv", {"format": "long"})
    if freq_index is not None:                       # transposed: rows = frequencies
        freq = _num(table.iloc[:, freq_index], layout.decimal)
        level_columns = [i for i in range(len(column_names)) if i != freq_index]
        level = np.column_stack([_num(table.iloc[:, i], layout.decimal) for i in level_columns]).T
        time_s = np.arange(level.shape[0]) / (opts.fs or 1.0)
        return SpectrumSet(Path(path).stem, time_s, freq, level, unit, None, "",
                           "signalshark-csv", {"format": "transposed"})
    return read_text_timeseries(path, opts, source="signalshark-level")


# ---- dispatcher -----------------------------------------------------------------------
def detect_source(path: Path) -> str:
    """Guess the reader for a file or folder (overridden by --source)."""
    if path.is_dir():
        return "ehp"
    suffix = path.suffix.lower()
    if suffix in (".h5", ".hdf5", ".hdf"):
        return "signalshark"
    if suffix in (".xlsx", ".xls"):
        return "xlsx"
    if _EHP_NAME.search(path.name):
        return "ehp"
    try:
        layout = sniff_text(path)
    except Exception:  # noqa: BLE001 - unreadable: let the default reader report it
        return "fieldman"
    header_numbers = [_safe_float(c.split()[0] if c.split() else c) for c in layout.columns]
    has_freq_column = any("freq" in c.lower() for c in layout.columns)
    if sum(np.isfinite(header_numbers)) >= 8 or has_freq_column:
        return "signalshark" if not has_freq_column or len(layout.columns) > 6 else "spectrum"
    if any("result" in c.lower() for c in layout.columns):
        return "nbm"
    return "fieldman"


def load_any(path: str | os.PathLike, opts: Options) -> TimeSeries | SpectrumSet:
    """Read any supported input (file or EHP folder) into the data model."""
    input_path = Path(path)
    source = opts.source if opts.source != "auto" else detect_source(input_path)
    if input_path.is_dir():
        spectrum_files = sorted(q for q in input_path.rglob("*")
                                if q.is_file() and q.suffix.lower() in (".txt", ".csv"))
        if not spectrum_files:
            raise ValueError(f"{input_path}: no .txt/.csv spectra inside")
        return read_ehp_folder(spectrum_files, opts, input_path.name)
    if source == "signalshark":
        if input_path.suffix.lower() in (".h5", ".hdf5", ".hdf"):
            return read_signalshark_h5(input_path, opts)
        return read_signalshark_csv(input_path, opts)
    if source == "xlsx":
        return read_xlsx_timeseries(input_path, opts)
    if source in ("ehp", "spectrum"):
        layout = sniff_text(input_path, opts.sep, opts.decimal)
        if any("freq" in c.lower() for c in layout.columns):
            freq, level, unit = read_text_spectrum(input_path, opts)   # a single spectrum
            stamp = _ehp_time_from_path(input_path)
            return SpectrumSet(input_path.stem, np.zeros(1), freq, level[None, :], unit,
                               (stamp - VEUSZ_EPOCH).total_seconds() if stamp else None,
                               stamp.isoformat() if stamp else "", "ehp", {})
        return read_text_timeseries(input_path, opts, source="ehp-logger")
    return read_text_timeseries(input_path, opts, source=source)


def inspect_input(path: str | os.PathLike, opts: Options) -> str:
    """Report how a file will be read (layout, columns, units, timing)."""
    input_path = Path(path)
    report = [f"File      : {input_path}",
              f"Detected  : {detect_source(input_path)} (force with --source)"]
    if input_path.suffix.lower() in (".h5", ".hdf5", ".hdf"):
        report += ["HDF5 tree :"] + ["  " + line for line in describe_h5(input_path)]
    elif input_path.is_file() and input_path.suffix.lower() not in (".xlsx", ".xls"):
        layout = sniff_text(input_path, opts.sep, opts.decimal)
        report += [f"Encoding  : {layout.encoding}", f"Delimiter : {layout.sep!r}",
                   f"Decimal   : {layout.decimal!r}", f"Header row: {layout.header_row}",
                   f"Columns   : {layout.columns}", f"Unit hint : {layout.unit_hint}",
                   "Metadata  :"] + ["  " + line for line in layout.meta_lines[:15]]
    try:
        data = load_any(input_path, opts)
        if isinstance(data, TimeSeries):
            intervals = np.diff(np.asarray(data.time_s[:200000]))
            report += [f"Read as   : time series, {len(data.values)} samples, unit {data.unit}",
                       f"Columns   : time {data.meta.get('time_columns')}, value "
                       f"{data.meta.get('value_column')}, axes {data.meta.get('axis_columns')}",
                       f"Start     : {data.t0_text or 'relative time only'}",
                       f"dt        : median {np.median(intervals):.6g} s, min {intervals.min():.6g}, "
                       f"max {intervals.max():.6g}" if intervals.size else "dt        : n/a"]
        else:
            report += [f"Read as   : spectra {data.level.shape} (time x freq), unit {data.unit}",
                       f"Frequency : {data.freq_hz[0]:.6g} .. {data.freq_hz[-1]:.6g} Hz",
                       f"Time      : {data.time_s[0]:.6g} .. {data.time_s[-1]:.6g} s",
                       f"Notes     : {data.meta}"]
    except Exception as exc:  # noqa: BLE001 - the report is the deliverable
        report.append(f"Read error: {type(exc).__name__}: {exc}")
    return "\n".join(report)


# %% ===========================================================================
#    PRE-PROCESSING: TIMING, GAPS, UNIFORM GRID
# =============================================================================
@dataclass
class UniformSeries:
    """A series on a uniform time grid, with its gap-free blocks."""
    sample_rate_hz: float
    values: np.ndarray               # record on the grid (gaps linearly bridged)
    blocks: list[tuple[int, int]]    # [start, stop) index ranges without gaps
    filled_fraction: float           # share of grid points that lie in gaps
    jitter_rel: float                # median |interval - dt| / dt
    time_raw_s: np.ndarray           # original stamps (for Lomb-Scargle)
    values_raw: np.ndarray


def make_uniform(time_s: np.ndarray, values: np.ndarray, fs_hint: float | None = None,
                 gap_factor: float = GAP_FACTOR) -> UniformSeries:
    """Put a series on a uniform grid at its mean sample interval.

    Samples further apart than ``gap_factor`` intervals mark a gap. The FFT
    uses the record with gaps linearly bridged (fraction reported); Welch
    uses only the gap-free blocks; Lomb-Scargle uses the raw stamps.
    """
    stamps = np.asarray(time_s, float)
    readings = np.asarray(values, float)
    valid = np.isfinite(stamps) & np.isfinite(readings)
    stamps, readings = stamps[valid], readings[valid]
    order = np.argsort(stamps, kind="stable")
    stamps, readings = stamps[order], readings[order]
    unique = np.concatenate(([True], np.diff(stamps) > 0))     # drop duplicate stamps
    stamps, readings = stamps[unique], readings[unique]
    if stamps.size < 8:
        raise ValueError("fewer than 8 valid samples")
    intervals = np.diff(stamps)
    if fs_hint:
        sample_interval = 1.0 / fs_hint
    else:
        # Mean of the gap-free intervals, not the median: stamps rounded to
        # e.g. 1 us make the median biased (0.001111 s for 900 Hz), and a
        # grid 0.01 % off makes the resampling phase drift, which adds side
        # peaks and loses amplitude.
        median_interval = float(np.median(intervals))
        gap_free = intervals < gap_factor * median_interval
        sample_interval = float(intervals[gap_free].mean()) if gap_free.any() else median_interval
    jitter_rel = float(np.median(np.abs(intervals - sample_interval)) / sample_interval)
    gap_positions = np.flatnonzero(intervals > gap_factor * sample_interval)
    n_grid = int(round((stamps[-1] - stamps[0]) / sample_interval)) + 1
    grid = stamps[0] + np.arange(n_grid) * sample_interval
    if jitter_rel < 0.01 and gap_positions.size == 0 and n_grid == stamps.size:
        # Uniform within 1 %: use the samples as they are. Interpolating
        # rounded or slightly jittered stamps would low-pass the data and add
        # spurs; the stamp jitter is reported, and Lomb-Scargle uses the stamps.
        grid_values = readings.copy()
    else:
        grid_values = np.interp(grid, stamps, readings)
    # -- blocks of grid indices that do not cross a gap
    blocks, block_start = [], 0
    for gap in gap_positions:
        block_stop = int(np.searchsorted(grid, stamps[gap], side="right"))
        next_start = int(np.searchsorted(grid, stamps[gap + 1], side="left"))
        blocks.append((block_start, block_stop))
        block_start = next_start
    blocks.append((block_start, n_grid))
    blocks = [(start, stop) for start, stop in blocks if stop - start >= 2]
    covered = sum(stop - start for start, stop in blocks)
    return UniformSeries(1.0 / sample_interval, grid_values, blocks, 1.0 - covered / n_grid,
                         jitter_rel, stamps, readings)


def analysis_quantity(values: np.ndarray, unit: str | None, opts: Options) -> tuple[np.ndarray, str, str]:
    """Quantity that is transformed: power (default), field or dB."""
    if opts.quantity == "field":
        field_values, field_unit = to_field_like(values, unit, opts.z0)
        return field_values, field_unit, "field strength (non-linear in power: cross-products appear)"
    power_values, power_unit, note = to_power_like(values, unit, opts.z0, opts.antenna_factor_db)
    if opts.quantity == "db":
        reference = np.nanmax(power_values) if np.nanmax(power_values) > 0 else 1.0
        level_db = 10 * np.log10(np.maximum(power_values, reference * 1e-12) / reference)
        return level_db, "dB rel. max", "log-power"
    return power_values, power_unit, note


# %% ===========================================================================
#    SPECTRAL ESTIMATORS
# =============================================================================
def amplitude_spectrum(values: np.ndarray, sample_rate_hz: float, window: str, backend: Backend,
                       nfft: int | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Single-sided amplitude spectrum of the (mean-removed) record.

    Scaled by the window's coherent gain, so a sinusoid of amplitude A in the
    envelope reads A at its frequency [R16] (less the scalloping loss when it
    falls between bins). Resolution is fs/N; zero padding (``nfft``)
    interpolates the same spectrum.
    """
    n_samples = len(values)
    window_values = ssig.get_window(window, n_samples)
    windowed = backend.asarray((np.asarray(values, float) - float(np.mean(values))) * window_values)
    nfft = nfft or n_samples
    amplitude = backend.cpu(abs(backend.rfft(windowed, n=nfft))) * (2.0 / window_values.sum())
    amplitude[0] /= 2.0                     # DC is not doubled
    if nfft % 2 == 0:
        amplitude[-1] /= 2.0                # nor is the Nyquist bin
    return sfft.rfftfreq(nfft, 1.0 / sample_rate_hz), amplitude


def welch_blocks(values: np.ndarray, blocks: Sequence[tuple[int, int]], sample_rate_hz: float,
                 nperseg: int, window: str, backend: Backend, overlap: float = 0.5,
                 batch: int = 512) -> tuple[np.ndarray, np.ndarray, int]:
    """Welch PSD from gap-free blocks, streamed ``batch`` segments at a time.

    Same estimator and scaling as scipy.signal.welch(detrend='constant',
    scaling='density', one-sided, average='mean') [R11]; only ``batch``
    segments are in memory at once, so ``values`` can be a disk memmap.

    Returns (frequency, PSD in unit^2/Hz, number of segments averaged).
    """
    window_values = ssig.get_window(window, nperseg)
    step = max(1, int(round(nperseg * (1.0 - overlap))))
    density_scale = 1.0 / (sample_rate_hz * np.sum(window_values ** 2))
    power_sum = np.zeros(nperseg // 2 + 1)
    n_segments = 0
    window_on_device = backend.asarray(window_values)
    for block_start, block_stop in blocks:
        if block_stop - block_start < nperseg:
            continue
        segment_starts = np.arange(block_start, block_stop - nperseg + 1, step)
        for first in range(0, segment_starts.size, batch):
            starts = segment_starts[first:first + batch]
            segments = np.stack([np.asarray(values[s:s + nperseg], float) for s in starts])
            segments = backend.asarray(segments - segments.mean(axis=1, keepdims=True))
            spectra = backend.rfft(segments * window_on_device, axis=1)
            power_sum += backend.cpu((spectra.real ** 2 + spectra.imag ** 2).sum(axis=0))
            n_segments += starts.size
    if n_segments == 0:
        raise ValueError(f"no gap-free block is {nperseg} samples long; lower --nperseg")
    psd = power_sum / n_segments * density_scale
    psd[1:-1 if nperseg % 2 == 0 else None] *= 2.0       # one-sided: double all but DC/Nyquist
    return sfft.rfftfreq(nperseg, 1.0 / sample_rate_hz), psd, n_segments


def czt_zoom(values: np.ndarray, sample_rate_hz: float, band_hz: tuple[float, float],
             n_points: int, window: str) -> tuple[np.ndarray, np.ndarray]:
    """Chirp-Z (zoom FFT) amplitude spectrum over ``band_hz`` with ``n_points`` [R12].

    Evaluates the same windowed DTFT as amplitude_spectrum on a denser grid
    inside the band, to read a peak frequency (e.g. a rotation rate) and
    amplitude precisely. It does not improve resolution, which stays fs/N.
    """
    n_samples = len(values)
    window_values = ssig.get_window(window, n_samples)
    windowed = (np.asarray(values, float) - float(np.mean(values))) * window_values
    f_low, f_high = band_hz
    zoomed = ssig.zoom_fft(windowed, [f_low, f_high], m=n_points, fs=sample_rate_hz, endpoint=True)
    return np.linspace(f_low, f_high, n_points), np.abs(zoomed) * (2.0 / window_values.sum())


def lomb_scargle(time_s: np.ndarray, values: np.ndarray, freq_hz: np.ndarray, backend: Backend,
                 chunk_bytes: int = 64 * 2 ** 20) -> np.ndarray:
    """Classical Lomb-Scargle periodogram returned as sinusoid amplitude [R13][R14].

    Works on irregular stamps without resampling. For a sinusoid of
    amplitude A the result is about A, comparable with amplitude_spectrum.
    Frequencies are processed in chunks so memory stays near ``chunk_bytes``
    (and the work runs on the GPU when the backend has one).
    """
    xp = backend.xp
    stamps = np.asarray(time_s, float) - float(np.asarray(time_s, float)[0])
    centred = np.asarray(values, float) - float(np.mean(values))
    n_samples = stamps.size
    stamps_dev, centred_dev = backend.asarray(stamps), backend.asarray(centred)
    amplitude = np.empty(freq_hz.size)
    freqs_per_chunk = max(1, int(chunk_bytes // (8 * n_samples * 4)))
    for first in range(0, freq_hz.size, freqs_per_chunk):
        omega = backend.asarray(2 * np.pi * np.asarray(freq_hz[first:first + freqs_per_chunk], float))[:, None]
        omega = xp.where(omega == 0, 1e-12, omega)
        # time offset tau that makes the sine and cosine terms orthogonal
        tau = xp.arctan2(xp.sin(2 * omega * stamps_dev).sum(axis=1),
                         xp.cos(2 * omega * stamps_dev).sum(axis=1))[:, None] / (2 * omega)
        phase = omega * (stamps_dev - tau)
        cos_term, sin_term = xp.cos(phase), xp.sin(phase)
        power = 0.5 * ((centred_dev * cos_term).sum(axis=1) ** 2 / (cos_term * cos_term).sum(axis=1)
                       + (centred_dev * sin_term).sum(axis=1) ** 2 / (sin_term * sin_term).sum(axis=1))
        amplitude[first:first + freqs_per_chunk] = backend.cpu(xp.sqrt(4.0 * power / n_samples))
    return amplitude


def envelope_spectrogram(values: np.ndarray, sample_rate_hz: float, nperseg: int, window: str,
                         max_slices: int = 2000) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Short-time PSD of the envelope (time x modulation frequency).

    Hop chosen so at most ``max_slices`` columns are produced. Returns
    (slice centres in s, frequency in Hz, PSD array shape (n_freq, n_slices)).
    """
    n_samples = len(values)
    hop = max(nperseg // 4, int(math.ceil(n_samples / max_slices)))
    window_values = ssig.get_window(window, nperseg)
    stft = ssig.ShortTimeFFT(window_values, hop, sample_rate_hz, fft_mode="onesided2X", scale_to="psd")
    first_slice = stft.lower_border_end[1]          # skip slices hanging off the ends
    last_slice = stft.upper_border_begin(n_samples)[1]
    if last_slice <= first_slice:
        raise ValueError("record too short for a spectrogram")
    psd = stft.spectrogram(np.asarray(values, float), detr="constant", p0=first_slice, p1=last_slice)
    return stft.t(n_samples, p0=first_slice, p1=last_slice), stft.f, psd


def modulation_spectra(power_on_grid: np.ndarray, interval_s: float, window: str, backend: Backend,
                       batch_bytes: int = 256 * 2 ** 20) -> tuple[np.ndarray, np.ndarray]:
    """Envelope amplitude spectrum of every column of a (time x bin) array.

    The same estimator and scaling as amplitude_spectrum (mean removed,
    window, 2|X|/sum(w), DC and Nyquist not doubled), applied to all
    frequency bins of a spectrogram in batches of about ``batch_bytes``.
    0.0.3 fix: the Nyquist row was doubled in 0.0.2.

    Returns (modulation frequency in Hz, amplitude array (n_freq_mod, n_bins)).
    """
    n_grid, n_bins = power_on_grid.shape
    window_values = ssig.get_window(window, n_grid)
    modulation_freq_hz = sfft.rfftfreq(n_grid, interval_s)
    amplitude = np.empty((modulation_freq_hz.size, n_bins))
    columns_per_batch = max(1, int(batch_bytes // (8 * n_grid * 2)))
    window_on_device = backend.asarray(window_values[:, None])
    for first in range(0, n_bins, columns_per_batch):
        block = np.asarray(power_on_grid[:, first:first + columns_per_batch], dtype=float)
        centred = backend.asarray(block - block.mean(axis=0, keepdims=True))
        amplitude[:, first:first + columns_per_batch] = backend.cpu(
            abs(backend.rfft(centred * window_on_device, axis=0))) * (2.0 / window_values.sum())
    amplitude[0] /= 2.0                     # DC is not doubled
    if n_grid % 2 == 0:
        amplitude[-1] /= 2.0                # nor is the Nyquist bin (0.0.3 fix)
    return modulation_freq_hz, amplitude


def probe_response(freq_hz: np.ndarray, integration_time_s: float) -> np.ndarray:
    """|H(nu)| of a T-second moving-average (boxcar) integrator: |sinc(nu T)|."""
    return np.abs(np.sinc(np.asarray(freq_hz, float) * integration_time_s))


def correction_gain(freq_hz: np.ndarray, integration_time_s: float, max_boost_db: float) -> np.ndarray:
    """Gain that undoes the integration roll-off: G = min(1/|H|, g_max).

    g_max = 10^(max_boost_db/20). The exact inverse 1/|H| is used wherever it
    is at most g_max; beyond that the gain is held at g_max (the line is then
    under-corrected, never over-amplified); bins at or beyond the first null
    (nu T >= 1) are NaN, because nothing there can be recovered.

    0.0.3: replaces the 0.0.2 Wiener-type form h/(h^2 + eps) below
    |H| = 1/g_max, which was 1.94 dB discontinuous at the switch point
    (it gave 0.8 g_max there instead of g_max). This gain is continuous.
    """
    response = probe_response(freq_hz, integration_time_s)
    max_gain = 10 ** (max_boost_db / 20.0)
    gain = np.minimum(1.0 / np.maximum(response, 1e-300), max_gain)
    return np.where(np.asarray(freq_hz, dtype=float) * integration_time_s < 1.0, gain, np.nan)


def correct_probe(amplitude: np.ndarray, freq_hz: np.ndarray, integration_time_s: float,
                  max_boost_db: float) -> np.ndarray:
    """Amplitude spectrum with the integration roll-off undone (see correction_gain)."""
    return np.asarray(amplitude, dtype=float) * correction_gain(freq_hz, integration_time_s, max_boost_db)


# %% ===========================================================================
#    PEAKS AND HARMONIC FAMILIES
# =============================================================================
def find_spectral_peaks(freq_hz: np.ndarray, amplitude: np.ndarray, snr: float,
                        max_peaks: int, dyn_range_db: float = 50.0) -> list[dict[str, float]]:
    """Peaks standing ``snr`` times above the median level (DC excluded) and
    within ``dyn_range_db`` of the strongest one, refined by parabolic
    interpolation of the log amplitude."""
    amp = np.asarray(amplitude, float)
    if amp.size < 5:
        return []
    noise_floor = float(np.nanmedian(amp[1:])) or 1e-300
    peak_indices, _ = ssig.find_peaks(np.nan_to_num(amp), height=snr * noise_floor,
                                      prominence=(snr - 1) * noise_floor)
    peak_indices = peak_indices[peak_indices >= 2]
    if peak_indices.size:
        strongest = amp[peak_indices].max()
        peak_indices = peak_indices[amp[peak_indices] >= strongest * 10 ** (-dyn_range_db / 20.0)]
    peak_indices = peak_indices[np.argsort(amp[peak_indices])[::-1]][:max_peaks]
    bin_width = freq_hz[1] - freq_hz[0]
    peaks = []
    for index in sorted(peak_indices):
        if 0 < index < amp.size - 1 and min(amp[index - 1:index + 2]) > 0:
            log_left, log_centre, log_right = np.log(amp[index - 1:index + 2])
            curvature = log_left - 2 * log_centre + log_right
            offset_bins = 0.5 * (log_left - log_right) / curvature if curvature != 0 else 0.0
        else:
            offset_bins = 0.0
        peaks.append({"f_hz": float(freq_hz[index] + offset_bins * bin_width),
                      "amp": float(amp[index]),
                      "snr_db": float(20 * np.log10(amp[index] / noise_floor))})
    return peaks


def harmonic_families(peaks: list[dict[str, float]], bin_width_hz: float, nyquist_hz: float,
                      max_families: int = 3) -> list[dict[str, Any]]:
    """Group peaks into harmonic series k*f0 (k >= 1, f0 itself must be a peak).

    A rotating antenna (radar, beam scan) gives a fundamental at the rotation
    rate and harmonics from the beam shape, so f0 -> rpm = 60 f0. Families
    are taken greedily by total member amplitude, up to ``max_families``.
    """
    remaining = sorted(peaks, key=lambda peak: -peak["amp"])
    families: list[dict[str, Any]] = []
    while remaining and len(families) < max_families:
        best = None
        for candidate in remaining:
            f0 = candidate["f_hz"]
            if f0 < 2 * bin_width_hz:
                continue
            tolerance = max(1.5 * bin_width_hz, 0.01 * f0)
            members = [peak for peak in remaining
                       if round(peak["f_hz"] / f0) >= 1
                       and abs(peak["f_hz"] / f0 - round(peak["f_hz"] / f0)) * f0 <= tolerance]
            score = sum(peak["amp"] for peak in members)
            if best is None or score > best[0] * 1.000001:
                best = (score, f0, members)
        if best is None:
            break
        _, f0, members = best
        families.append({"f0_hz": f0, "period_s": 1.0 / f0, "rpm": 60.0 * f0,
                         "harmonics": sorted(int(round(peak["f_hz"] / f0)) for peak in members),
                         "n_members": len(members), "within_nyquist_to": nyquist_hz})
        remaining = [peak for peak in remaining if peak not in members]
    return families


# %% ===========================================================================
#    ANALYSIS DRIVERS
# =============================================================================
@dataclass
class SeriesResult:
    """Everything computed for one time series (one probe log or channel)."""
    name: str
    source: str
    unit_in: str | None
    quantity_unit: str
    quantity_note: str
    sample_rate_hz: float
    n_samples: int
    duration_s: float
    t0_text: str
    t0_veusz: float | None
    time_s: np.ndarray
    quantity: np.ndarray
    field_values: np.ndarray
    field_unit: str
    fft_freq_hz: np.ndarray
    fft_amplitude: np.ndarray
    fft_amplitude_corrected: np.ndarray | None
    welch_freq_hz: np.ndarray
    welch_psd: np.ndarray
    welch_segments: int
    welch_nperseg: int
    zoom_freq_hz: np.ndarray | None
    zoom_amplitude: np.ndarray | None
    lomb_freq_hz: np.ndarray | None
    lomb_amplitude: np.ndarray | None
    spectrogram_time_s: np.ndarray | None
    spectrogram_freq_hz: np.ndarray | None
    spectrogram_db: np.ndarray | None
    probe_response: np.ndarray | None
    integration_time_s: float | None
    axis_amplitudes: dict[str, np.ndarray]
    peaks: list[dict[str, float]]
    families: list[dict[str, Any]]
    warnings: list[str]
    backend_note: str
    meta: dict[str, Any]
    z0_ohm: float = Z0_OHM                 # wave impedance used (plane-wave unit conversions)


def _default_nperseg(n_samples: int) -> int:
    """Largest power of two giving at least ~7 Welch averages (50 % overlap)."""
    if n_samples < 64:
        return max(8, n_samples)
    return int(2 ** max(5, int(math.floor(math.log2(n_samples / 4)))))


def analyse_timeseries(series: TimeSeries, opts: Options, backend: Backend | None = None) -> SeriesResult:
    """Full envelope analysis of one time series (see module description)."""
    backend = backend or Backend(opts.gpu, opts.fft_workers)
    notes: list[str] = []
    probe = lookup_probe(opts.probe)
    quantity, quantity_unit, quantity_note = analysis_quantity(series.values, series.unit, opts)
    uniform = make_uniform(series.time_s, quantity, opts.fs)
    sample_rate_hz, n_samples = uniform.sample_rate_hz, len(uniform.values)
    longest_block = max(stop - start for start, stop in uniform.blocks)

    # -- timing and data-quality notes ------------------------------------------
    if probe and abs(sample_rate_hz - probe.fs_hz) / probe.fs_hz > 0.05:
        notes.append(f"measured sample rate {sample_rate_hz:.4g} Hz differs from {probe.name} nominal "
                     f"{probe.fs_hz:g} Hz (logging interval or meter setting)")
    if uniform.filled_fraction > 0:
        notes.append(f"{100 * uniform.filled_fraction:.2f} % of the grid lies in gaps (bridged "
                     f"linearly for the FFT; Welch uses gap-free blocks; see Lomb-Scargle)")
    if uniform.jitter_rel > 0.01:
        notes.append(f"time-stamp jitter {100 * uniform.jitter_rel:.1f} % of the interval")
    integration_time_s = opts.t_int or (probe.t_int_s if probe and probe.t_int_s else None)
    if integration_time_s is None and probe:
        integration_time_s = 1.0 / probe.fs_hz
        notes.append(f"{probe.name}: integration time not published; 1/fs = {integration_time_s:.4g} s assumed")
    if integration_time_s:
        nyquist_hz = sample_rate_hz / 2
        response_at_nyquist = float(probe_response(np.array([nyquist_hz]), integration_time_s)[0])
        head = (f"probe integration {integration_time_s * 1e3:.3g} ms: |H| = "
                f"{20 * np.log10(max(response_at_nyquist, 1e-12)):.1f} dB at Nyquist {nyquist_hz:.4g} Hz; ")
        first_null_hz = 1.0 / integration_time_s
        if integration_time_s * sample_rate_hz < 1.0:
            notes.append("integration shorter than the sample interval: envelope content "
                         "above fs/2 aliases with little attenuation")
        elif first_null_hz > nyquist_hz:
            notes.append(head + f"content between {nyquist_hz:.4g} and {first_null_hz:.4g} Hz (first "
                         f"null) aliases into the band, attenuated only by |H|")
        else:
            notes.append(head + f"first null {first_null_hz:.4g} Hz lies below Nyquist; content "
                         f"above {nyquist_hz:.4g} Hz aliases through the sinc side lobes "
                         f"(-13 dB or less)")
    if probe and probe.truerms_max_vm and series.unit in ("V/m", "mV/m", "uV/m"):
        field_values, _ = to_field_like(series.values, series.unit)
        share_over = float(np.mean(np.asarray(field_values) > probe.truerms_max_vm))
        if share_over > 0:
            notes.append(f"{100 * share_over:.1f} % of samples exceed the True-RMS limit "
                         f"{probe.truerms_max_vm:g} V/m: diodes leave square-law, powers no "
                         f"longer add (envelope spectrum distorted)")

    # -- spectra ------------------------------------------------------------------------
    fft_freq_hz, fft_amplitude = amplitude_spectrum(uniform.values, sample_rate_hz, opts.window, backend)
    welch_nperseg = min(opts.nperseg or _default_nperseg(longest_block), longest_block)
    welch_freq_hz, welch_psd, welch_segments = welch_blocks(
        uniform.values, uniform.blocks, sample_rate_hz, welch_nperseg, opts.window, backend)
    fft_amplitude_corrected, response = None, None
    if integration_time_s:
        response = probe_response(fft_freq_hz, integration_time_s)
        if opts.correct_probe:
            fft_amplitude_corrected = correct_probe(fft_amplitude, fft_freq_hz, integration_time_s,
                                                    opts.max_boost_db)
    peak_source = fft_amplitude_corrected if fft_amplitude_corrected is not None else fft_amplitude
    peaks = find_spectral_peaks(fft_freq_hz, peak_source, opts.snr, opts.max_peaks, opts.dyn_range_db)
    families = harmonic_families(peaks, fft_freq_hz[1] - fft_freq_hz[0], sample_rate_hz / 2)

    # -- chirp-Z zoom around the requested band or the strongest peak
    zoom_freq_hz = zoom_amplitude = None
    zoom_band = opts.zoom
    if zoom_band is None and peaks:
        # +-16 FFT bins around the strongest peak: with the default 4096
        # points that is 1/128-bin spacing, enough to read the peak precisely.
        strongest_hz = max(peaks, key=lambda peak: peak["amp"])["f_hz"]
        half_width_hz = 16 * sample_rate_hz / n_samples
        zoom_band = (max(strongest_hz - half_width_hz, sample_rate_hz / n_samples),
                     min(strongest_hz + half_width_hz, sample_rate_hz / 2))
    if zoom_band:
        zoom_freq_hz, zoom_amplitude = czt_zoom(uniform.values, sample_rate_hz, zoom_band,
                                                opts.zoom_points, opts.window)
        if peaks:
            # The zoom samples the spectrum between FFT bins, so its maximum
            # also removes the window's scalloping loss (up to 1.4 dB, Hann).
            zoom_max = int(np.argmax(zoom_amplitude))
            for peak in peaks:
                if abs(peak["f_hz"] - zoom_freq_hz[zoom_max]) < 2 * sample_rate_hz / n_samples:
                    peak["f_hz_czt"] = float(zoom_freq_hz[zoom_max])
                    peak["amp_czt"] = float(zoom_amplitude[zoom_max])

    # -- Lomb-Scargle on the raw stamps (gaps or jitter, or when asked)
    lomb_freq_hz = lomb_amplitude = None
    use_lomb = opts.lomb == "on" or (opts.lomb == "auto" and
                                     (uniform.filled_fraction > 0.001 or uniform.jitter_rel > 0.01))
    if use_lomb:
        record_span_s = uniform.time_raw_s[-1] - uniform.time_raw_s[0]
        lomb_freq_hz = np.linspace(1.0 / record_span_s, sample_rate_hz / 2, min(4 * n_samples, 20000))
        lomb_amplitude = lomb_scargle(uniform.time_raw_s, uniform.values_raw, lomb_freq_hz, backend)

    # -- envelope spectrogram for long records
    spectrogram_time_s = spectrogram_freq_hz = spectrogram_db = None
    if n_samples >= 16 * welch_nperseg:
        try:
            spectrogram_time_s, spectrogram_freq_hz, spectrogram_psd = envelope_spectrogram(
                uniform.values, sample_rate_hz, welch_nperseg, opts.window)
            spectrogram_db = 10 * np.log10(np.maximum(spectrogram_psd, np.max(spectrogram_psd) * 1e-12))
        except ValueError:
            pass

    # -- per-axis spectra (EFD-0691 reports X/Y/Z separately [R2])
    axis_amplitudes = {}
    for axis, axis_values in series.axes.items():
        axis_quantity, _, _ = analysis_quantity(axis_values, series.unit, opts)
        axis_uniform = make_uniform(series.time_s, axis_quantity, opts.fs)
        axis_amplitudes[axis] = amplitude_spectrum(axis_uniform.values[:n_samples], sample_rate_hz,
                                                   opts.window, backend)[1]
    field_values, field_unit = to_field_like(series.values, series.unit, opts.z0)
    return SeriesResult(
        series.name, series.source, series.unit, quantity_unit, quantity_note, sample_rate_hz,
        n_samples, n_samples / sample_rate_hz, series.t0_text, series.t0_veusz,
        np.asarray(series.time_s, float), np.asarray(quantity, float),
        np.asarray(field_values, float), field_unit,
        fft_freq_hz, fft_amplitude, fft_amplitude_corrected,
        welch_freq_hz, welch_psd, welch_segments, welch_nperseg,
        zoom_freq_hz, zoom_amplitude, lomb_freq_hz, lomb_amplitude,
        spectrogram_time_s, spectrogram_freq_hz, spectrogram_db,
        response, integration_time_s, axis_amplitudes, peaks, families, notes,
        backend.note, series.meta, opts.z0)


@dataclass
class SpectrogramResult:
    """Per-frequency-bin envelope analysis of a spectrogram."""
    name: str
    source: str
    unit_in: str | None
    power_unit: str
    freq_hz: np.ndarray
    time_s: np.ndarray
    spectra_rate_hz: float                 # spectra per second (envelope sample rate)
    mean_level_db: np.ndarray
    max_level_db: np.ndarray
    level_db_image: np.ndarray             # (n_time, n_freq), decimated for Veusz
    image_time_s: np.ndarray
    image_freq_hz: np.ndarray
    modulation_freq_hz: np.ndarray
    modulation_db_image: np.ndarray        # (n_modulation, n_freq), decimated
    modulation_image_freq_hz: np.ndarray
    dominant_modulation_hz: np.ndarray     # per frequency bin
    channels: list[SeriesResult]
    warnings: list[str]
    meta: dict[str, Any]
    z0_ohm: float = Z0_OHM                 # wave impedance used (RF levels shown as E or H)


def _decimate_max(array: np.ndarray, max_cells: int, axis: int) -> tuple[np.ndarray, np.ndarray]:
    """Max-pool along ``axis`` to at most ``max_cells``; returns (array, cell-centre indices)."""
    n_cells = array.shape[axis]
    if n_cells <= max_cells:
        return array, np.arange(n_cells, dtype=float)
    factor = int(math.ceil(n_cells / max_cells))
    n_used = n_cells // factor * factor
    trimmed = np.take(array, np.arange(n_used), axis=axis)
    shape = list(trimmed.shape)
    shape[axis:axis + 1] = [n_used // factor, factor]
    return np.nanmax(trimmed.reshape(shape), axis=axis + 1), np.arange(n_used // factor) * factor + (factor - 1) / 2


def analyse_spectrumset(spectra: SpectrumSet, opts: Options, backend: Backend | None = None) -> SpectrogramResult:
    """Envelope (modulation) spectrum for every frequency bin, plus channel analyses."""
    backend = backend or Backend(opts.gpu, opts.fft_workers)
    notes: list[str] = []
    if spectra.source.startswith("ehp") and spectra.unit in ("V/m", "mV/m", "uV/m", "A/m", "mA/m",
                                                              "mT", "uT", "nT"):
        # EHP-50F fields (1 Hz-400 kHz) are quasi-static near fields: there is
        # no far-field power density, so the field squared is analysed.
        field_values, field_unit = to_field_like(spectra.level, spectra.unit)
        power, power_unit = field_values ** 2, f"({field_unit})^2"
        conversion_note = "field squared (LF quasi-static field; E^2/Z0 would not be meaningful)"
    else:
        power, power_unit, conversion_note = to_power_like(spectra.level, spectra.unit, opts.z0,
                                                           opts.antenna_factor_db)
    power = np.where(np.isfinite(power), power, np.nan)
    freq_divisor, freq_unit_label = _freq_unit(float(np.nanmax(spectra.freq_hz)))
    mean_level_db = 10 * np.log10(np.maximum(np.nanmean(power, axis=0), 1e-300))
    max_level_db = 10 * np.log10(np.maximum(np.nanmax(power, axis=0), 1e-300))
    level_image, image_time_index = _decimate_max(10 * np.log10(np.maximum(power, 1e-300)), MAX_IMAGE_SIDE, 0)
    level_image, image_freq_index = _decimate_max(level_image, MAX_IMAGE_SIDE, 1)
    image_time_s = np.interp(image_time_index, np.arange(spectra.time_s.size), spectra.time_s)
    image_freq_hz = np.interp(image_freq_index, np.arange(spectra.freq_hz.size), spectra.freq_hz)
    channels: list[SeriesResult] = []
    if spectra.level.shape[0] < 16:
        notes.append("fewer than 16 spectra in time: no envelope analysis possible")
        return SpectrogramResult(spectra.name, spectra.source, spectra.unit, power_unit, spectra.freq_hz,
                                 spectra.time_s, float("nan"), mean_level_db, max_level_db,
                                 level_image, image_time_s, image_freq_hz, np.zeros(1),
                                 np.zeros((1, level_image.shape[1])), image_freq_hz,
                                 np.full(spectra.freq_hz.size, np.nan), channels, notes, spectra.meta,
                                 opts.z0)

    # -- uniform time grid for all bins at once (mean of gap-free intervals)
    stamps = np.asarray(spectra.time_s, float)
    intervals = np.diff(stamps)
    gap_free = intervals < GAP_FACTOR * np.median(intervals)
    spectrum_interval = float(intervals[gap_free].mean()) if gap_free.any() else float(np.median(intervals))
    n_grid = int(round((stamps[-1] - stamps[0]) / spectrum_interval)) + 1
    grid = stamps[0] + np.arange(n_grid) * spectrum_interval
    column_means = np.nanmean(power, axis=0, keepdims=True)
    filled_power = np.where(np.isfinite(power), power, column_means)    # NaN -> bin mean
    if n_grid != stamps.size or np.max(np.abs(intervals - spectrum_interval)) > 0.01 * spectrum_interval:
        from scipy.interpolate import interp1d
        power_on_grid = interp1d(stamps, filled_power, axis=0, assume_sorted=True)(grid)
        notes.append("spectra not evenly spaced in time: interpolated onto a uniform grid")
    else:
        power_on_grid = filled_power
    spectra_rate_hz = 1.0 / spectrum_interval

    # -- modulation spectrum per bin, batched over columns (bounded memory)
    modulation_freq_hz, modulation_amplitude = modulation_spectra(
        power_on_grid, spectrum_interval, opts.window, backend)
    if modulation_freq_hz.size > 1:
        dominant_modulation_hz = modulation_freq_hz[1:][np.argmax(modulation_amplitude[1:], axis=0)]
        reference = np.nanmax(modulation_amplitude[1:])
    else:
        dominant_modulation_hz = np.full(modulation_amplitude.shape[1], np.nan)
        reference = 1.0
    modulation_db = 20 * np.log10(np.maximum(modulation_amplitude / reference, 1e-6))
    modulation_image, modulation_freq_index = _decimate_max(modulation_db, MAX_IMAGE_SIDE, 1)
    modulation_image, modulation_row_index = _decimate_max(modulation_image, MAX_IMAGE_SIDE, 0)

    # -- channels: the whole band, the strongest spectral peaks (or user bands)
    bands: list[tuple[str, float, float]] = [("total", float(spectra.freq_hz[0]), float(spectra.freq_hz[-1]))]
    channel_spec = opts.rf_channels or ""
    bin_width = float(np.median(np.diff(spectra.freq_hz))) if spectra.freq_hz.size > 1 else 1.0
    if channel_spec.startswith("auto"):
        n_auto = int(channel_spec.split(":")[1]) if ":" in channel_spec else 3
        peak_bins, _ = ssig.find_peaks(mean_level_db, prominence=3.0)
        peak_bins = peak_bins[np.argsort(mean_level_db[peak_bins])[::-1]][:n_auto]
        # +-2 bins, or +-1.5 RBW when the RBW is known (the filter skirt of a
        # carrier spans several bins when the trace is oversampled)
        half_width = max(2 * bin_width, 1.5 * opts.rbw_hz) if opts.rbw_hz else 2 * bin_width
        for peak_bin in sorted(peak_bins):
            centre = spectra.freq_hz[peak_bin]
            bands.append((f"f_{centre / freq_divisor:.6g}{freq_unit_label}",
                          float(centre - half_width), float(centre + half_width)))
    elif channel_spec:
        for part in channel_spec.split(","):
            f_low, f_high = (float(v) for v in part.split(":"))
            bands.append((f"f_{f_low / freq_divisor:.6g}-{f_high / freq_divisor:.6g}{freq_unit_label}",
                          f_low, f_high))
    channel_opts = Options(**{**asdict(opts), "probe": None, "fs": None, "quantity": "power",
                              "unit": None, "correct_probe": False})
    # Channel power: a trace bin holds the power inside the RBW filter around
    # it, so a carrier appears in every bin under the filter. The absolute
    # channel power is sum(P_bin) * bin_width / (RBW * ENBW factor); without
    # the RBW the plain sum is used (its modulation spectrum has the right
    # shape and frequencies, its level is too high by RBW*ENBW/bin_width).
    if opts.rbw_hz:
        channel_scale = bin_width / (opts.rbw_hz * opts.enbw_factor)
        notes.append(f"channel power = bin sum x {channel_scale:.4g} (bin {bin_width:.6g} Hz, RBW "
                     f"{opts.rbw_hz:.6g} Hz, ENBW factor {opts.enbw_factor:.4f})")
    else:
        channel_scale = 1.0
        notes.append("channel level = plain sum of bin powers (give --rbw-hz for absolute channel "
                     "power); envelope frequencies are not affected")
    for label, f_low, f_high in bands:
        in_band = (spectra.freq_hz >= f_low) & (spectra.freq_hz <= f_high)
        if not in_band.any():
            continue
        band_power = np.nansum(power_on_grid[:, in_band], axis=1) * channel_scale
        channel_series = TimeSeries(f"{spectra.name}_{label}", grid - grid[0], band_power,
                                    "W/m2" if power_unit == "W/m^2" else None, {}, spectra.t0_veusz,
                                    spectra.t0_text, spectra.source, {"band_hz": [f_low, f_high]})
        try:
            channel_result = analyse_timeseries(channel_series, channel_opts, backend)
            channel_result.quantity_unit = power_unit
            channel_result.quantity_note = (f"sum of linear power over {f_low:.6g}-{f_high:.6g} Hz; "
                                            f"{conversion_note}")
            channels.append(channel_result)
        except ValueError as exc:
            notes.append(f"channel {label}: {exc}")
    return SpectrogramResult(
        spectra.name, spectra.source, spectra.unit, power_unit, spectra.freq_hz, spectra.time_s,
        spectra_rate_hz, mean_level_db, max_level_db, level_image, image_time_s, image_freq_hz,
        np.interp(modulation_row_index, np.arange(modulation_freq_hz.size), modulation_freq_hz),
        modulation_image,
        np.interp(modulation_freq_index, np.arange(spectra.freq_hz.size), spectra.freq_hz),
        dominant_modulation_hz, channels, notes, {**spectra.meta, "power_note": conversion_note}, opts.z0)


# %% ===========================================================================
#    VEUSZ .vszh5 OUTPUT (through the author's vszh5_writer.py)
# =============================================================================
# Documents are written with vszh5_writer.VeuszWriter (typed datasets, gzip,
# atomic ".part" write) and vszh5_writer.VszDoc (the Veusz command script);
# pages are built with its xy_page()/image_page() helpers, so the pages look
# the same as in the author's other programs. Dataset names are
# <prefix><descriptive name>, e.g. "ch1_fft_amplitude"; the prefix is empty
# for a single probe log and "ch<k>_" for spectrogram channels.

#: Readable titles of the pages written for one time series, used for the
#: PDF bookmarks (page name without the "ch<k>_" prefix -> title).
SERIES_PAGE_TITLES = {
    "summary": "Summary (units, timing, peaks, warnings)",
    "overview": "Overview (time, spectrum, PSD, zoom)",
    "time": "Logged field vs time",
    "density": "Power density vs time",
    "efield": "Electric field E vs time (plane wave)",
    "hfield": "Magnetic field H vs time (plane wave)",
    "amplitude": "Envelope amplitude spectrum (FFT)",
    "welch": "Welch power spectral density",
    "zoom": "Chirp-Z zoom around the strongest peak",
    "lomb": "Lomb-Scargle periodogram (raw stamps)",
    "probe": "Probe integration model |sinc|",
    "spectrogram": "Envelope spectrogram",
}
#: Titles of the overview pages of a spectrogram (SignalShark, EHP-50 TS).
OVERVIEW_PAGE_TITLES = {
    "summary": "Summary (units, channels, warnings)",
    "spectrum": "Mean and max-hold spectrum",
    "spectrogram": "Spectrogram (level vs time and frequency)",
    "modulation_map": "Envelope spectrum per frequency bin",
    "dominant_modulation": "Strongest envelope frequency per bin",
}
#: Page names of an extra unit section start with "u<k>__" (0.0.4).
SECTION_PAGE_PATTERN = re.compile(r"u(\d+)__(.+)")


def _freq_unit(f_max_hz: float) -> tuple[float, str]:
    """(divisor, label) so a spectrum frequency axis reads in Hz/kHz/MHz/GHz."""
    for divisor, label in ((1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if f_max_hz >= 10 * divisor:
            return divisor, label
    return 1.0, "Hz"


def _outline_for(indexed_names: Sequence[tuple[int, str]],
                 channel_names: Sequence[str] | None) -> list[tuple]:
    """Bookmarks of one set of pages (page names without a section tag)."""
    overview: list[tuple] = []
    flat: list[tuple] = []
    channels: dict[int, list[tuple]] = {}
    for page_index, page_name in indexed_names:
        channel_match = re.fullmatch(r"ch(\d+)_(.+)", page_name)
        if channel_match:
            channel_index = int(channel_match.group(1))
            title = SERIES_PAGE_TITLES.get(channel_match.group(2), channel_match.group(2))
            channels.setdefault(channel_index, []).append((title, page_index))
        elif page_name in OVERVIEW_PAGE_TITLES and channel_names is not None:
            overview.append((OVERVIEW_PAGE_TITLES[page_name], page_index))
        else:
            flat.append((SERIES_PAGE_TITLES.get(page_name, page_name), page_index))
    if not overview and not channels:
        return flat
    outline: list[tuple] = []
    if overview:
        outline.append(("Overview", None, overview))
    for channel_index in sorted(channels):
        label = channel_names[channel_index] if channel_names and channel_index < len(channel_names) else ""
        outline.append((f"Channel {channel_index}: {label}".rstrip(": "), None, channels[channel_index]))
    return outline + flat


def bookmark_outline(page_names: Sequence[str], channel_names: Sequence[str] | None = None,
                     section_titles: Sequence[str] | None = None) -> list[tuple]:
    """PDF bookmark hierarchy for vszh5_writer.render_pages().

    ``channel_names`` is None for a single series, else the channel names of
    a spectrogram result (possibly empty). A single series gives a flat list
    of its pages; a spectrogram an "Overview" entry holding the overview
    pages, then one entry per channel ("Channel 1: <name>") holding that
    channel's pages. With several unit sections (0.0.4: page names
    "u<k>__<page>", ``section_titles`` naming them, the primary set first)
    each section becomes a top-level entry holding that structure. Entries
    follow vszh5_writer.OutlineEntry: (title, page index) or (title, None,
    children).
    """
    sections: dict[int, list[tuple[int, str]]] = {}
    for page_index, page_name in enumerate(page_names):
        section_match = SECTION_PAGE_PATTERN.fullmatch(page_name)
        section = int(section_match.group(1)) if section_match else 0
        sections.setdefault(section, []).append((page_index, section_match.group(2) if section_match
                                                 else page_name))
    if len(sections) <= 1 or not section_titles:
        return _outline_for([pair for k in sorted(sections) for pair in sections[k]], channel_names)
    outline = []
    for section in sorted(sections):
        title = section_titles[section] if section < len(section_titles) else f"Units {section}"
        outline.append((title, None, _outline_for(sections[section], channel_names)))
    return outline


@dataclass
class UnitView:
    """Display choices one set of plots is drawn with (0.0.4).

    The GUI draws with one view; a Veusz document holds the primary view and,
    with several --veusz-units, one extra view per unit.

    Attributes
    ----------
    selection:
        Display unit per family (unit_selection()).
    time_display / rf_level_display:
        TIME_DISPLAY_MODES / RF_LEVEL_MODES keys.
    focus:
        None for a complete set of pages; the family of an extra unit for a
        Veusz section, which then holds only the pages that depend on it.
    tag:
        "" for the primary set, "u1", "u2", ... for extra sections (page and
        dataset name prefix).
    unit_key:
        The extra unit of a section or file ("" for the primary set).
    """
    selection: dict[str, str]
    time_display: str = "power density"
    rf_level_display: str = "power density"
    focus: str | None = None
    tag: str = ""
    unit_key: str = ""


def primary_view(opts: Options) -> UnitView:
    """The display units, time and RF-level modes of ``opts``."""
    return UnitView(unit_selection(opts.display_unit), normalise_time_display(opts.time_display),
                    opts.rf_level_display if opts.rf_level_display in RF_LEVEL_MODES else "power density")


def _focus_view(primary: UnitView, unit: DisplayUnit, tag: str, focus: bool) -> UnitView:
    """The primary view with ``unit`` chosen for its family; time and RF modes follow that family."""
    family = unit.family
    time_display = {"S": "power density", "E": "E field", "H": "H field",
                    "B": "logged field"}.get(family, "analysed quantity")
    rf_display = {"S": "power density", "E": "E field", "H": "H field"}.get(family, primary.rf_level_display)
    return UnitView({**primary.selection, family: unit.key}, time_display, rf_display,
                    family if focus else None, tag, unit.key)


def veusz_views(opts: Options) -> list[UnitView]:
    """Primary view plus one view per extra Veusz unit (duplicates of the primary skipped).

    With layout "sections" the extra views are focused (only the pages that
    use their family); with "files" every view is a complete document.
    """
    primary = primary_view(opts)
    views = [primary]
    focus = opts.veusz_layout != "files"
    seen: set[str] = set()
    for item in _split_units(opts.veusz_units):
        unit = lookup_display_unit(item)
        if unit.key in seen:
            continue
        seen.add(unit.key)
        # A unit equal to the primary choice of its family still gets a
        # section, holding only the pages the primary set lacks (e.g. H vs
        # time); series_page_kinds() removes the rest.
        views.append(_focus_view(primary, unit, f"u{len(views)}", focus))
    return views


def safe_unit_tag(unit_key: str) -> str:
    """File-name-safe form of a unit key: 'mW/cm2' -> 'mWcm2', 'dBuV/m' -> 'dBuVm'."""
    return re.sub(r"[^A-Za-z0-9]", "", unit_key)


def _result_units(result: Any, view: UnitView) -> list[str]:
    """Labels of the units the pages of ``result`` use in ``view`` (for titles)."""
    labels: list[str] = []
    if isinstance(result, SpectrogramResult):
        level_label = rf_level_display(np.zeros(1), result.power_unit, view.selection, view.rf_level_display,
                                       result.z0_ohm)[1]
        labels.append(level_label.replace("dB re 1 ", ""))
        series = result.channels[0] if result.channels else None
    else:
        series = result
    if series is not None:
        labels.append(display_label(unit_for_quantity(series.quantity_unit, view.selection),
                                    series.quantity_unit))
        time_label = time_display_values(series, view.time_display, view.selection)[1]
        labels.append(time_label[time_label.index(" (") + 2:-1])      # "Name (unit)" -> "unit"
        logged_family = FIELD_FAMILY.get(series.field_unit)
        if logged_family:
            labels.append(DISPLAY_UNITS[view.selection[logged_family]].label)
    return list(dict.fromkeys(labels))


def view_title(result: Any, view: UnitView) -> str:
    """Bookmark title of a unit section."""
    if view.focus is None and not view.unit_key:
        return "Display units: " + ", ".join(_result_units(result, view))
    unit = DISPLAY_UNITS[view.unit_key]
    return f"In {unit.label} ({UNIT_FAMILIES[unit.family].title})"


def _lower_first(text: str) -> str:
    """'Electric field E' -> 'electric field E' (keeps symbols upper-case)."""
    return text[:1].lower() + text[1:]


class _DocContext:
    """Writer, command script and the datasets already written (shared axes)."""

    def __init__(self, writer: VeuszWriter, doc: VszDoc) -> None:
        self.writer = writer
        self.doc = doc
        self.datasets: set[str] = set()

    def data_1d(self, name: str, values: Any, tags: Sequence[str]) -> str:
        """Write a 1-D dataset once; return its name."""
        if name not in self.datasets:
            self.writer.dataset_1d(name, values, tags=tags)
            self.datasets.add(name)
        return name

    def data_date(self, name: str, values: Any, tags: Sequence[str]) -> str:
        """Write a date dataset once; return its name."""
        if name not in self.datasets:
            self.writer.dataset_date(name, values, tags=tags)
            self.datasets.add(name)
        return name


def series_page_kinds(result: SeriesResult, view: UnitView, primary: UnitView | None = None) -> set[str]:
    """The pages written for ``result`` in ``view`` (see SERIES_PAGE_TITLES).

    A complete view gets every page that has data; a focused view (an extra
    Veusz unit) only the pages whose values are in its family: the spectra
    and the overview when the analysed quantity is in that family, the power
    density, logged field or plane-wave E/H against time when that is. When
    the focused unit is also the ``primary`` view's choice for its family,
    the pages the primary set already has are left out.
    """
    if view.focus is not None and primary is not None and \
            view.selection.get(view.focus) == primary.selection.get(view.focus):
        return series_page_kinds(result, UnitView(view.selection, view.time_display, view.rf_level_display,
                                                  view.focus)) - series_page_kinds(result, primary)
    spectral_family = QUANTITY_FAMILY.get(result.quantity_unit, (None, False))[0]
    logged_family = FIELD_FAMILY.get(result.field_unit)
    available = available_time_families(result)
    time_family = TIME_DISPLAY_MODES[normalise_time_display(view.time_display)]
    if view.focus is None:
        kinds = {"overview", "time", "amplitude", "welch", "zoom", "lomb", "probe", "spectrogram"}
        if "S" in available:
            kinds.add("density")
        if time_family in ("E", "H") and time_family != logged_family and time_family in available:
            kinds.add("efield" if time_family == "E" else "hfield")
        return kinds
    kinds = set()
    family = view.focus
    if family == spectral_family:
        kinds |= {"overview", "amplitude", "welch", "zoom", "lomb", "spectrogram"}
    if family == "S" and "S" in available:
        kinds.add("density")
    if family == logged_family:
        kinds.add("time")
    elif family in ("E", "H") and family in available:
        kinds.add("efield" if family == "E" else "hfield")
    return kinds


def _write_series_pages(context: _DocContext, result: SeriesResult, prefix: str,
                        view: UnitView | None = None, primary: UnitView | None = None) -> list[str]:
    """Datasets and pages for one SeriesResult in one unit view; returns the page names.

    ``prefix`` is "" for a single series or "ch<k>_" for a spectrogram
    channel. Pages and value datasets of an extra view get "u<k>__" / "u<k>_"
    in front; axes (time, frequency) are written once and shared. Values are
    written in the view's display units; the CSV/NPZ/JSON outputs stay in SI
    units. dB conventions: PSD 10 log10 (a squared quantity), |H| 20 log10
    (filter response), level units 10 or 20 log10 (DisplayUnit.db).
    """
    view = view or UnitView(unit_selection(None))
    kinds = series_page_kinds(result, view, primary)
    pages: list[str] = []
    if not kinds:
        return pages
    writer, doc = context.writer, context.doc
    page_prefix = f"{view.tag}__{prefix}" if view.tag else prefix
    value_prefix = f"{view.tag}_{prefix}" if view.tag else prefix
    tags = (prefix.rstrip("_") or "series",) + ((view.tag,) if view.tag else ())
    start_text = f" (start {result.t0_text})" if result.t0_text else ""
    unit = unit_for_quantity(result.quantity_unit, view.selection)
    quantity_label = display_label(unit, result.quantity_unit)
    spectrum_log = unit is None or not unit.is_level        # dB values go on a linear axis
    unit_note = f" ({quantity_label})"

    # -- shared axes
    context.data_1d(f"{prefix}time_s", result.time_s, tags)
    if result.t0_veusz is not None:
        time_dataset = context.data_date(f"{prefix}time_date", result.t0_veusz + result.time_s, tags)
        time_label, time_mode = "Date and time (instrument clock)", "datetime"
    else:
        time_dataset, time_label, time_mode = f"{prefix}time_s", "Time since start (s)", "numeric"
    freq_dataset = context.data_1d(f"{prefix}fft_freq_hz", result.fft_freq_hz, tags)
    welch_freq_dataset = context.data_1d(f"{prefix}welch_freq_hz", result.welch_freq_hz, tags)

    # -- values in this view's units
    amplitude_dataset = context.data_1d(f"{value_prefix}fft_amplitude", to_display(result.fft_amplitude, unit),
                                        tags)
    welch_db, psd_label = psd_to_display_db(result.welch_psd, unit, result.quantity_unit)
    welch_dataset = context.data_1d(f"{value_prefix}welch_psd_db", welch_db, tags)

    def time_page_data(family: str) -> tuple[str, str]:
        """Dataset and y label of the record as ``family`` (written once per view)."""
        name = {"S": "density", "E": "efield", "H": "hfield", "B": "bfield"}.get(family, "quantity")
        if family == FIELD_FAMILY.get(result.field_unit):
            name = "field"
        if family in UNIT_FAMILIES:
            family_unit = DISPLAY_UNITS[view.selection[family]]
            label = f"{UNIT_FAMILIES[family].title} ({family_unit.label})"
            return context.data_1d(f"{value_prefix}{name}", to_display(time_quantity(result, family), family_unit),
                                   tags), label
        return (context.data_1d(f"{value_prefix}{name}", to_display(result.quantity, unit), tags),
                f"Analysed quantity ({quantity_label})")

    # -- overview: four panels on one page (vszh5_writer.grid_page)
    if "overview" in kinds:
        _, _, shown_family = time_display_values(result, view.time_display, view.selection)
        overview_time_dataset, overview_time_label = time_page_data(shown_family)
        overview_panels = [
            Panel([Trace(time_dataset, overview_time_dataset)], time_label, overview_time_label, "Time series",
                  xmode=time_mode, x_autorange="exact"),
            Panel([Trace(freq_dataset, amplitude_dataset)], "Envelope frequency (Hz)",
                  f"Amplitude ({quantity_label})", "Envelope amplitude spectrum", ylog=spectrum_log, xmin=0.0),
            Panel([Trace(welch_freq_dataset, welch_dataset, colour=vszh5_writer.TRACE_COLOURS[2])],
                  "Envelope frequency (Hz)", f"PSD ({psd_label})", "Welch PSD", xmin=0.0),
        ]
        if result.zoom_freq_hz is not None:
            zoom_freq_dataset = context.data_1d(f"{prefix}zoom_freq_hz", result.zoom_freq_hz, tags)
            context.data_1d(f"{value_prefix}zoom_amplitude", to_display(result.zoom_amplitude, unit), tags)
            overview_panels.append(Panel([Trace(zoom_freq_dataset, f"{value_prefix}zoom_amplitude",
                                                colour=vszh5_writer.TRACE_COLOURS[1])],
                                         "Envelope frequency (Hz)", f"Amplitude ({quantity_label})",
                                         "Chirp-Z zoom around the strongest line"))
        page = f"{page_prefix}overview"
        grid_page(doc, page, overview_panels, title=f"{result.name}: overview{unit_note}{start_text}")
        pages.append(page)
    # -- time pages: logged field, power density, plane-wave E or H
    for kind, family in (("time", FIELD_FAMILY.get(result.field_unit)), ("density", "S"),
                         ("efield", "E"), ("hfield", "H")):
        if kind not in kinds:
            continue
        if kind == "time" and family is None:                 # e.g. dBm or % logs: as logged
            dataset = context.data_1d(f"{value_prefix}field", result.field_values, tags)
            label = f"Logged value ({unit_label(result.field_unit)})"
        else:
            dataset, label = time_page_data(family)
        page = f"{page_prefix}{kind}"
        xy_page(doc, page, [Trace(time_dataset, dataset, label.split(" (")[0])],
                title=f"{result.name}: {_lower_first(label.split(' (')[0])} vs time{start_text}", xlabel=time_label,
                ylabel=label, xmode=time_mode, x_autorange="exact")
        pages.append(page)
    # -- amplitude spectrum (+ probe-corrected, + per-axis X/Y/Z)
    if "amplitude" in kinds:
        traces = [Trace(freq_dataset, amplitude_dataset, "FFT amplitude")]
        if result.fft_amplitude_corrected is not None:
            context.data_1d(f"{value_prefix}fft_amplitude_corrected",
                            to_display(result.fft_amplitude_corrected, unit), tags)
            traces.append(Trace(freq_dataset, f"{value_prefix}fft_amplitude_corrected", "probe-corrected",
                                style="dashed"))
        for axis, axis_amplitude in result.axis_amplitudes.items():
            context.data_1d(f"{value_prefix}fft_amplitude_{axis}", to_display(axis_amplitude, unit), tags)
            traces.append(Trace(freq_dataset, f"{value_prefix}fft_amplitude_{axis}", f"axis {axis}",
                                style="dotted"))
        page = f"{page_prefix}amplitude"
        xy_page(doc, page, traces, title=f"{result.name}: envelope amplitude spectrum{unit_note}",
                xlabel="Envelope (modulation) frequency (Hz)", ylabel=f"Amplitude ({quantity_label})",
                xmin=0.0, ylog=spectrum_log)
        pages.append(page)
    # -- Welch PSD in dB re 1 (display unit)^2/Hz
    if "welch" in kinds:
        page = f"{page_prefix}welch"
        xy_page(doc, page, [Trace(welch_freq_dataset, welch_dataset, "Welch")],
                title=f"{result.name}: Welch PSD, {result.welch_segments} segments of {result.welch_nperseg}",
                xlabel="Envelope frequency (Hz)", ylabel=f"PSD ({psd_label})", xmin=0.0)
        pages.append(page)
    # -- chirp-Z zoom, with the FFT bins in the same band as markers
    if "zoom" in kinds and result.zoom_freq_hz is not None:
        zoom_freq_dataset = context.data_1d(f"{prefix}zoom_freq_hz", result.zoom_freq_hz, tags)
        context.data_1d(f"{value_prefix}zoom_amplitude", to_display(result.zoom_amplitude, unit), tags)
        in_band = (result.fft_freq_hz >= result.zoom_freq_hz[0]) & (result.fft_freq_hz <= result.zoom_freq_hz[-1])
        zoom_fft_freq = context.data_1d(f"{prefix}zoom_fft_freq_hz", result.fft_freq_hz[in_band], tags)
        context.data_1d(f"{value_prefix}zoom_fft_amplitude", to_display(result.fft_amplitude[in_band], unit), tags)
        page = f"{page_prefix}zoom"
        xy_page(doc, page, [Trace(zoom_freq_dataset, f"{value_prefix}zoom_amplitude", "chirp-Z (dense)"),
                            Trace(zoom_fft_freq, f"{value_prefix}zoom_fft_amplitude", "FFT bins",
                                  marker="circle", line=False)],
                title=f"{result.name}: chirp-Z zoom{unit_note}", xlabel="Envelope frequency (Hz)",
                ylabel=f"Amplitude ({quantity_label})")
        pages.append(page)
    # -- Lomb-Scargle against the FFT
    if "lomb" in kinds and result.lomb_freq_hz is not None:
        lomb_freq = context.data_1d(f"{prefix}lomb_freq_hz", result.lomb_freq_hz, tags)
        context.data_1d(f"{value_prefix}lomb_amplitude", to_display(result.lomb_amplitude, unit), tags)
        page = f"{page_prefix}lomb"
        xy_page(doc, page, [Trace(lomb_freq, f"{value_prefix}lomb_amplitude", "Lomb-Scargle"),
                            Trace(freq_dataset, amplitude_dataset, "FFT (uniform grid)", style="dashed")],
                title=f"{result.name}: Lomb-Scargle (raw time stamps){unit_note}",
                xlabel="Envelope frequency (Hz)", ylabel=f"Amplitude ({quantity_label})",
                ylog=spectrum_log, xmin=0.0)
        pages.append(page)
    # -- probe integration model (filter response: 20 log10 |H|; no unit)
    if "probe" in kinds and result.probe_response is not None:
        context.data_1d(f"{prefix}probe_response_db", 20 * np.log10(np.maximum(result.probe_response, 1e-6)), tags)
        page = f"{page_prefix}probe"
        xy_page(doc, page, [Trace(freq_dataset, f"{prefix}probe_response_db", "|H|")],
                title=f"Probe integration model |sinc(f T)|, T = {result.integration_time_s * 1e3:.4g} ms",
                xlabel="Envelope frequency (Hz)", ylabel="20 log10 |H| (dB)", xmin=0.0)
        pages.append(page)
    # -- envelope spectrogram: rows = envelope frequency (y), columns = time (x)
    if "spectrogram" in kinds and result.spectrogram_db is not None:
        spectrogram_display_db = result.spectrogram_db + psd_db_offset(unit)     # PSD x factor^2
        writer.dataset_2d(f"{value_prefix}spectrogram_db", spectrogram_display_db,
                          xcent=result.spectrogram_time_s, ycent=result.spectrogram_freq_hz, tags=tags)
        page = f"{page_prefix}spectrogram"
        peak_db = float(np.nanmax(spectrogram_display_db))
        image_page(doc, page, f"{value_prefix}spectrogram_db", title=f"{result.name}: envelope spectrogram",
                   xlabel="Time (s)", ylabel="Envelope frequency (Hz)",
                   zlabel=f"PSD ({psd_label})", zmin=peak_db - 60, zmax=peak_db)
        pages.append(page)
    return pages


def _as_view(units: UnitView | dict[str, str] | str | None) -> UnitView:
    """Accept a UnitView, a selection dict, a unit list string ("mW/cm2,dBuV/m") or None."""
    if isinstance(units, UnitView):
        return units
    if isinstance(units, dict):
        return UnitView(dict(units))
    return UnitView(unit_selection(units))


def _shown(value: float, unit: DisplayUnit | None) -> float:
    """One amplitude in a display unit (level units: db log10 without a floor)."""
    if unit is None:
        return float(value)
    scaled = float(value) * unit.factor
    if unit.is_level:
        return unit.db * math.log10(scaled) if scaled > 0 else float("-inf")
    return scaled


def summary_lines(result: SeriesResult | SpectrogramResult,
                  units: UnitView | dict[str, str] | str | None = None) -> list[str]:
    """Plain-text summary for the first page of a document (and the GUI).

    Amplitudes are given in the display unit of the analysed quantity
    (``units``: a UnitView, a selection or a unit list); frequencies in Hz.
    """
    import textwrap

    view = _as_view(units)

    def wrap(text: str, indent: str = "    ") -> list[str]:
        return textwrap.wrap(text, 108, initial_indent=indent, subsequent_indent=indent + "  ") or [indent]

    if isinstance(result, SpectrogramResult):
        _, level_label = rf_level_display(np.zeros(1), result.power_unit, view.selection,
                                          view.rf_level_display, result.z0_ohm)
        lines = [f"Input            {result.name}   (reader {result.source}, unit {unit_label(result.unit_in)})",
                 f"Spectra          {result.time_s.size} x {result.freq_hz.size} bins, "
                 f"{result.freq_hz[0]:.6g} .. {result.freq_hz[-1]:.6g} Hz, at {result.spectra_rate_hz:.4g} spectra/s",
                 f"Levels           {level_label} (analysed as {unit_label(result.power_unit)}; "
                 f"power levels 10 log10)", "", "Channels (envelope analysis):"]
        for channel in result.channels:
            family = channel.families[0] if channel.families else None
            text = (f"f0 {family['f0_hz']:.5g} Hz = {family['rpm']:.4g} rpm" if family else
                    (f"strongest line {channel.peaks[0]['f_hz']:.5g} Hz" if channel.peaks else "no line"))
            lines.append(f"    {channel.name:<46} {text}")
        lines += ["", "Notes:"] + [line for note in result.warnings for line in wrap("- " + note)]
        lines += ["", f"{PROGRAM_NAME} {__version__}"]
        return lines
    unit = unit_for_quantity(result.quantity_unit, view.selection)
    quantity_label = display_label(unit, result.quantity_unit)
    _, time_label, time_family = time_display_values(result, view.time_display, view.selection)
    derived = time_family in ("S", "E", "H") and time_family != FIELD_FAMILY.get(result.field_unit) and \
        not (time_family == "S" and result.quantity_unit == "W/m^2")
    lines = [f"Input            {result.name}   (reader {result.source}, unit {unit_label(result.unit_in)})",
             f"Start            {result.t0_text or 'relative time only'}",
             f"Analysed         {unit_label(result.quantity_unit)} ({result.quantity_note}); spectra shown in "
             f"{quantity_label}",
             f"Time plot        {time_label}" + (f" (plane wave, Z0 = {result.z0_ohm:.6g} ohm)"
                                                 if derived else ""),
             f"Sampling         fs {result.sample_rate_hz:.6g} Hz, Nyquist {result.sample_rate_hz / 2:.6g} Hz, "
             f"{result.n_samples} samples, {result.duration_s:.6g} s, resolution "
             f"{result.sample_rate_hz / result.n_samples:.4g} Hz",
             f"Welch            {result.welch_segments} segments of {result.welch_nperseg} "
             f"(resolution {result.sample_rate_hz / result.welch_nperseg:.4g} Hz)"]
    if result.integration_time_s:
        nyquist_db = 20 * math.log10(max(abs(float(np.sinc(result.sample_rate_hz / 2 * result.integration_time_s))),
                                         1e-12))
        lines.append(f"Probe model      boxcar T = {result.integration_time_s * 1e3:.4g} ms, |H(Nyquist)| = "
                     f"{nyquist_db:.2f} dB (20 log10), first null {1 / result.integration_time_s:.4g} Hz")
    lines += ["", f"Peaks            frequency (Hz)   amplitude ({quantity_label})   SNR (dB)   period (s)"]
    for peak in result.peaks:
        lines.append(f"                 {peak['f_hz']:>14.6g}   {_shown(peak['amp'], unit):>14.5g}   "
                     f"{peak['snr_db']:>8.1f}   {1 / peak['f_hz']:>10.5g}")
    lines += ["", "Harmonic families (rotation or repetition rate):"]
    for family in result.families:
        lines.append(f"    f0 {family['f0_hz']:.6g} Hz   period {family['period_s']:.6g} s   "
                     f"{family['rpm']:.5g} rpm   harmonics {', '.join(map(str, family['harmonics']))}")
    if not result.families:
        lines.append("    none found")
    lines += ["", "Notes:"] + [line for note in result.warnings for line in wrap("- " + note)]
    lines += ["", f"Compute backend  {result.backend_note};  {PROGRAM_NAME} {__version__}"]
    return lines


def _views_argument(units: Sequence[UnitView] | UnitView | dict[str, str] | str | None) -> list[UnitView]:
    """A list of views from what the writers accept (0.0.3 passed a power-density unit key)."""
    if isinstance(units, (list, tuple)):
        return list(units) or [UnitView(unit_selection(None))]
    return [_as_view(units)]


def _units_dataset(context: _DocContext, result: Any, views: Sequence[UnitView],
                   written_tags: set[str] | None = None) -> None:
    """Record the units of every section in the document (text datasets).

    One title per view, in view order (the section index of the page names);
    a requested unit that added no page is marked so.
    """
    titles = [view_title(result, view) + ("" if written_tags is None or view.tag in written_tags
                                          else " (no pages: nothing new in this unit)") for view in views]
    context.writer.dataset_text("display_unit", titles)
    context.writer.dataset_text("unit_sections", [json.dumps({
        "tag": view.tag, "unit": view.unit_key, "selection": view.selection, "time_display": view.time_display,
        "rf_level_display": view.rf_level_display, "focus": view.focus}) for view in views])


def write_vszh5_series(result: SeriesResult, path: Path,
                       units: Sequence[UnitView] | UnitView | dict[str, str] | str | None = None) -> Path:
    """Veusz document for one time-series result.

    ``units``: one view (or a unit list such as "mW/cm2,dBuV/m") for a
    single set of pages, or several views (veusz_views) for a document with
    a section per unit; each section starts with its own summary page.
    """
    views = _views_argument(units)
    with VeuszWriter(path, compress=True, writer_tag=f"{PROGRAM_NAME} {__version__}") as writer:
        doc = VszDoc(f"{PROGRAM_NAME} {__version__}")
        context = _DocContext(writer, doc)
        written_tags: set[str] = set()
        for view in views:
            if view.focus is not None and not series_page_kinds(result, view, views[0]):
                continue                                    # nothing new in this unit's family
            written_tags.add(view.tag)
            summary_page = f"{view.tag}__summary" if view.tag else "summary"
            text_page(doc, summary_page, f"{result.name}: summary ({view_title(result, view)})",
                      summary_lines(result, view))
            _write_series_pages(context, result, "", view, views[0])
        writer.dataset_text("summary", [json.dumps(_jsonable(_summary_series(result)))])
        _units_dataset(context, result, views, written_tags)
        return writer.finish(doc.text())


def _rf_section_mode(result: SpectrogramResult, view: UnitView, primary: UnitView | None) -> str | None:
    """RF-level mode of a view's spectrum pages, or None when it has none (or the primary has the same)."""
    if view.focus is None:
        return view.rf_level_display
    if view.focus not in rf_level_families(result.power_unit):
        return None
    mode = {"E": "E field", "H": "H field"}.get(view.focus, "power density")
    if primary is not None:
        primary_shown = rf_level_display(np.zeros(1), result.power_unit, primary.selection,
                                         primary.rf_level_display, result.z0_ohm)[1]
        if rf_level_display(np.zeros(1), result.power_unit, view.selection, mode, result.z0_ohm)[1] == primary_shown:
            return None
    return mode


def _write_spectrogram_overview(context: _DocContext, result: SpectrogramResult, view: UnitView,
                                primary: UnitView | None = None) -> list[str]:
    """Spectrum and spectrogram pages (and, for the primary view, the modulation pages)."""
    writer, doc = context.writer, context.doc
    freq_divisor, freq_unit_label = _freq_unit(float(np.nanmax(result.freq_hz)))
    bin_kind = "RF" if result.source.startswith("signalshark") else "spectral"
    page_prefix = f"{view.tag}__" if view.tag else ""
    value_prefix = f"{view.tag}_" if view.tag else ""
    tags = ("spectrum",) + ((view.tag,) if view.tag else ())
    pages: list[str] = []
    rf_mode = _rf_section_mode(result, view, primary)
    if rf_mode is None:
        return pages
    mean_shown, level_label = rf_level_display(result.mean_level_db, result.power_unit, view.selection, rf_mode,
                                               result.z0_ohm)
    max_shown, _ = rf_level_display(result.max_level_db, result.power_unit, view.selection, rf_mode, result.z0_ohm)
    spectrum_freq = context.data_1d("spectrum_freq", result.freq_hz / freq_divisor, ("spectrum",))
    writer.dataset_1d(f"{value_prefix}spectrum_mean_db", mean_shown, tags=tags)
    writer.dataset_1d(f"{value_prefix}spectrum_max_db", max_shown, tags=tags)
    xy_page(doc, f"{page_prefix}spectrum", [Trace(spectrum_freq, f"{value_prefix}spectrum_mean_db", "mean"),
                                            Trace(spectrum_freq, f"{value_prefix}spectrum_max_db", "max hold",
                                                  style="dashed")],
            title=f"{result.name}: mean and max-hold spectrum (input {unit_label(result.unit_in)})",
            xlabel=f"Frequency ({freq_unit_label})", ylabel=f"Level ({level_label})")
    pages.append(f"{page_prefix}spectrum")
    # -- spectrogram image: rows = time (y), columns = frequency (x)
    level_image, _ = rf_level_display(result.level_db_image, result.power_unit, view.selection, rf_mode,
                                      result.z0_ohm)
    writer.dataset_2d(f"{value_prefix}spectrum_level_db", level_image,
                      xcent=result.image_freq_hz / freq_divisor, ycent=result.image_time_s, tags=tags)
    peak_db = float(np.nanmax(level_image))
    image_page(doc, f"{page_prefix}spectrogram", f"{value_prefix}spectrum_level_db",
               title=f"{result.name}: spectrogram ({level_label})",
               xlabel=f"Frequency ({freq_unit_label})", ylabel="Time (s)",
               zlabel=level_label, zmin=peak_db - 60, zmax=peak_db)
    pages.append(f"{page_prefix}spectrogram")
    # -- envelope spectrum of every bin (relative dB: no unit), primary view only
    if view.focus is None and not view.tag and result.modulation_db_image.shape[0] > 1:
        writer.dataset_2d("modulation_db", result.modulation_db_image,
                          xcent=result.modulation_image_freq_hz / freq_divisor,
                          ycent=result.modulation_freq_hz, tags=("modulation",))
        image_page(doc, "modulation_map", "modulation_db",
                   title=f"{result.name}: envelope spectrum per {bin_kind} bin "
                         f"(spectra at {result.spectra_rate_hz:.4g} Hz)",
                   xlabel=f"{bin_kind} frequency ({freq_unit_label})", ylabel="Envelope frequency (Hz)",
                   zlabel="dB rel. max (20 log10)", zmin=-60.0, zmax=0.0)
        writer.dataset_1d("dominant_modulation_hz", result.dominant_modulation_hz, tags=("modulation",))
        xy_page(doc, "dominant_modulation", [Trace(spectrum_freq, "dominant_modulation_hz", "dominant")],
                title=f"{result.name}: strongest envelope frequency per {bin_kind} bin",
                xlabel=f"{bin_kind} frequency ({freq_unit_label})", ylabel="Envelope frequency (Hz)")
        pages += ["modulation_map", "dominant_modulation"]
    return pages


def write_vszh5_spectrogram(result: SpectrogramResult, path: Path,
                            units: Sequence[UnitView] | UnitView | dict[str, str] | str | None = None) -> Path:
    """Veusz document for a spectrogram result (overview images + channel pages), one section per view."""
    views = _views_argument(units)
    with VeuszWriter(path, compress=True, writer_tag=f"{PROGRAM_NAME} {__version__}") as writer:
        doc = VszDoc(f"{PROGRAM_NAME} {__version__}")
        context = _DocContext(writer, doc)
        written_tags: set[str] = set()
        for view in views:
            if view.focus is not None and _rf_section_mode(result, view, views[0]) is None and not any(
                    series_page_kinds(channel, view, views[0]) for channel in result.channels):
                continue                                    # nothing new in this unit's family
            written_tags.add(view.tag)
            summary_page = f"{view.tag}__summary" if view.tag else "summary"
            text_page(doc, summary_page, f"{result.name}: summary ({view_title(result, view)})",
                      summary_lines(result, view))
            _write_spectrogram_overview(context, result, view, views[0])
            # -- the channels (whole band and the strongest spectral peaks)
            for channel_index, channel in enumerate(result.channels):
                _write_series_pages(context, channel, f"ch{channel_index}_", view, views[0])
        writer.dataset_text("summary", [json.dumps(_jsonable(_summary_spectrogram(result)))])
        _units_dataset(context, result, views, written_tags)
        return writer.finish(doc.text())


# %% ===========================================================================
#    OTHER OUTPUTS: CSV, NPZ, JSON SUMMARY, OPTIONAL RENDER
# =============================================================================
def _summary_series(result: SeriesResult) -> dict[str, Any]:
    """JSON-ready summary of one time-series result."""
    return {"name": result.name, "source": result.source, "unit_in": result.unit_in,
            "quantity": result.quantity_unit, "quantity_note": result.quantity_note,
            "fs_hz": result.sample_rate_hz, "nyquist_hz": result.sample_rate_hz / 2,
            "samples": result.n_samples, "duration_s": result.duration_s,
            "resolution_hz": result.sample_rate_hz / result.n_samples, "start": result.t0_text,
            "t_int_s": result.integration_time_s,
            "welch": {"nperseg": result.welch_nperseg, "segments": result.welch_segments,
                      "resolution_hz": result.sample_rate_hz / result.welch_nperseg},
            "peaks": result.peaks, "harmonic_families": result.families, "warnings": result.warnings,
            "backend": result.backend_note, "program": f"{PROGRAM_NAME} {__version__}"}


def _summary_spectrogram(result: SpectrogramResult) -> dict[str, Any]:
    """JSON-ready summary of a spectrogram result (with its channels)."""
    return {"name": result.name, "source": result.source, "unit_in": result.unit_in,
            "power_unit": result.power_unit, "spectra": int(result.time_s.size),
            "frequency_bins": int(result.freq_hz.size),
            "frequency_range_hz": [float(result.freq_hz[0]), float(result.freq_hz[-1])],
            "envelope_fs_hz": result.spectra_rate_hz,
            "channels": [_summary_series(c) for c in result.channels],
            "warnings": result.warnings, "meta": _jsonable(result.meta),
            "program": f"{PROGRAM_NAME} {__version__}"}


def _jsonable(obj: Any) -> Any:
    """Convert NumPy scalars and nested containers to plain JSON types."""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, np.integer)):
        return obj.item()
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def _write_csv(path: Path, columns: dict[str, np.ndarray]) -> Path:
    """Columns of equal length to a CSV (comma, decimal point, header row)."""
    names = list(columns)
    table = np.column_stack([np.asarray(columns[k], float) for k in names])
    np.savetxt(path, table, delimiter=",", header=",".join(names), comments="", fmt="%.10g")
    return path


def write_outputs(result: SeriesResult | SpectrogramResult, outdir: Path, opts: Options) -> list[Path]:
    """Write the .vszh5, CSVs/NPZ and JSON summary; optionally pickle and render."""
    outdir.mkdir(parents=True, exist_ok=True)
    stem = result.name
    written: list[Path] = []
    series_results = [result] if isinstance(result, SeriesResult) else result.channels
    for series_result in series_results:
        written.append(_write_csv(outdir / f"{series_result.name}_amplitude.csv", {
            "f_hz": series_result.fft_freq_hz, "amplitude": series_result.fft_amplitude,
            **({"amplitude_corrected": series_result.fft_amplitude_corrected}
               if series_result.fft_amplitude_corrected is not None else {}),
            **{f"amplitude_{axis}": a for axis, a in series_result.axis_amplitudes.items()}}))
        written.append(_write_csv(outdir / f"{series_result.name}_welch.csv",
                                  {"f_hz": series_result.welch_freq_hz, "psd": series_result.welch_psd}))
        if series_result.zoom_freq_hz is not None:
            written.append(_write_csv(outdir / f"{series_result.name}_zoom.csv",
                                      {"f_hz": series_result.zoom_freq_hz,
                                       "amplitude": series_result.zoom_amplitude}))
        if series_result.lomb_freq_hz is not None:
            written.append(_write_csv(outdir / f"{series_result.name}_lomb.csv",
                                      {"f_hz": series_result.lomb_freq_hz,
                                       "amplitude": series_result.lomb_amplitude}))
    if isinstance(result, SpectrogramResult):
        npz_path = outdir / f"{stem}_modulation.npz"
        np.savez_compressed(npz_path, freq_hz=result.freq_hz, time_s=result.time_s,
                            mean_level_db=result.mean_level_db, max_level_db=result.max_level_db,
                            modulation_freq_hz=result.modulation_freq_hz,
                            modulation_db_image=result.modulation_db_image,
                            dominant_modulation_hz=result.dominant_modulation_hz)
        written.append(npz_path)
        summary = _summary_spectrogram(result)
    else:
        summary = _summary_series(result)
    documents = write_veusz(result, outdir, opts)
    written += [path for path, _ in documents]
    summary_path = outdir / f"{stem}_summary.json"
    summary_path.write_text(json.dumps(_jsonable(summary), indent=2), encoding="utf-8")
    written.append(summary_path)
    if opts.pickle:
        written.append(save_pickle(result, outdir / f"{stem}_result.pkl"))
    if opts.render:
        written += render_documents(result, documents)
    return written


def write_veusz(result: SeriesResult | SpectrogramResult, outdir: Path,
                opts: Options) -> list[tuple[Path, list[str]]]:
    """Write the Veusz document(s) of a result in the units of ``opts`` (0.0.4).

    Returns (path, section titles) per document. Layout "sections" (default)
    writes <stem>_envelope_fft.vszh5 holding the primary units and one
    bookmarked section per extra --veusz-units unit; layout "files" writes the
    primary document plus <stem>_envelope_fft_<unit>.vszh5 per extra unit,
    each complete. Also used by the GUI (Veusz > Write .vszh5 again) to
    re-write a result in new units without re-analysing it.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    views = veusz_views(opts)
    writer_function = write_vszh5_spectrogram if isinstance(result, SpectrogramResult) else write_vszh5_series
    base_path = outdir / f"{result.name}_envelope_fft.vszh5"
    if opts.veusz_layout == "files":
        documents = []
        for view in views:
            single = UnitView(view.selection, view.time_display, view.rf_level_display, None, "", view.unit_key)
            path = base_path if not view.unit_key else \
                outdir / f"{result.name}_envelope_fft_{safe_unit_tag(view.unit_key)}.vszh5"
            documents.append((writer_function(result, path, [single]), [view_title(result, single)]))
        return documents
    return [(writer_function(result, base_path, views), [view_title(result, view) for view in views])]


def render_documents(result: SeriesResult | SpectrogramResult,
                     documents: Sequence[tuple[Path, Sequence[str]]]) -> list[Path]:
    """Render every document written by write_veusz (PDF with bookmarks, PNG pages)."""
    channel_names = ([channel.name for channel in result.channels]
                     if isinstance(result, SpectrogramResult) else None)
    rendered: list[Path] = []
    for path, section_titles in documents:
        rendered += render_vszh5(path, channel_names, section_titles)
    return rendered


def render_vszh5(path: Path, channel_names: Sequence[str] | None = None,
                 section_titles: Sequence[str] | None = None) -> list[Path]:
    """One PDF (bookmark hierarchy, see bookmark_outline) and one PNG per page.

    Uses vszh5_writer.render_pages, which drives an installed Veusz (or the
    veusz Python package) and adds the bookmarks with pypdf. A missing Veusz
    is reported as a warning, not an error: the .vszh5 is already written.
    ``section_titles`` name the unit sections of a multi-unit document;
    when not given they are read back from the document (text dataset
    "display_unit", one title per section, written by write_vszh5_*).
    """
    if section_titles is None:
        try:
            section_titles = read_text_dataset(path, "display_unit")
        except (OSError, RuntimeError):
            section_titles = None
    try:
        return list(render_pages(
            path, png_pages="all",
            bookmarks=lambda page_names: bookmark_outline(page_names, channel_names, section_titles),
            pdf_info={"title": f"Envelope FFT: {path.stem}", "author": __author__,
                      "subject": f"{PROGRAM_NAME} {__version__}"}))
    except RuntimeError as exc:
        warnings.warn(f"render failed: {exc}", RuntimeWarning, stacklevel=2)
        return []


# %% ===========================================================================
#    BATCH (PARALLEL) PROCESSING
# =============================================================================
def analyse_path(path: str, opts: Options, backend: Backend | None = None) -> SeriesResult | SpectrogramResult:
    """Read and analyse one input (no files written)."""
    data = load_any(path, opts)
    backend = backend or Backend(opts.gpu, opts.fft_workers)
    if isinstance(data, TimeSeries):
        return analyse_timeseries(data, opts, backend)
    return analyse_spectrumset(data, opts, backend)


def output_folder(path: str, opts: Options) -> Path:
    """Folder for the outputs of ``path``: --out, or "<stem>_fft" beside the input."""
    input_path = Path(path)
    return Path(opts.out) if opts.out else input_path.parent / f"{input_path.stem}_fft"


def analyse_and_write(path: str, opts: Options, write_files: bool = True) -> tuple[str, Any, list[Path]]:
    """Analyse one input and (optionally) write its outputs: (path, result, files written).

    Used by the GUI (in its worker thread or process pool) and by process_file.
    """
    result = analyse_path(path, opts)
    written = write_outputs(result, output_folder(path, opts), opts) if write_files else []
    return path, result, written


def process_file(path: str, opts: Options) -> dict[str, Any]:
    """Read, analyse and write one input; returns a small report (picklable)."""
    started = time.perf_counter()
    backend = Backend(opts.gpu, opts.fft_workers)
    result = analyse_path(path, opts, backend)
    input_path = Path(path)
    outdir = output_folder(path, opts)
    written = write_outputs(result, outdir, opts)
    report = {"input": str(input_path), "outdir": str(outdir), "files": [str(f) for f in written],
              "seconds": round(time.perf_counter() - started, 3), "backend": backend.note}
    if isinstance(result, SeriesResult):
        report.update(peaks=result.peaks[:5], families=result.families, warnings=result.warnings)
    else:
        report.update(channels=[{"name": c.name, "families": c.families} for c in result.channels],
                      warnings=result.warnings)
    del result                              # free the arrays before the next file
    flush_memory()
    return report


def process_files(paths: Sequence[str], opts: Options, jobs: int = 1) -> list[dict[str, Any]]:
    """Process several inputs, in parallel processes when ``jobs`` > 1.

    Each worker gets one FFT thread so processes do not oversubscribe the
    CPU; with one job the FFTs use all cores instead.
    """
    if jobs <= 1 or len(paths) == 1:
        return [process_file(p, opts) for p in paths]
    worker_opts = Options(**{**asdict(opts), "fft_workers": 1})
    reports: list[dict[str, Any]] = []
    with cf.ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = {executor.submit(process_file, p, worker_opts): p for p in paths}
        for future in cf.as_completed(futures):
            try:
                reports.append(future.result())
            except Exception as exc:  # noqa: BLE001 - report and continue with the others
                reports.append({"input": futures[future], "error": f"{type(exc).__name__}: {exc}"})
    return reports


# %% ===========================================================================
#    LIVE MODE: FOLLOW A GROWING FILE
# =============================================================================
class LiveTail:
    """Yield new rows (t seconds, value) from a text file another program appends to.

    The layout is sniffed once (needs a header and a few rows). Incomplete
    last lines are held back until finished. Times are seconds from the
    first row read.
    """

    def __init__(self, path: str | os.PathLike, opts: Options) -> None:
        self.path = Path(path)
        self.opts = opts
        self.layout = sniff_text(self.path, opts.sep, opts.decimal)
        self.time_indices, self.value_index, self.axis_indices = _pick_columns(
            self.layout, opts.time_col, opts.value_col)
        self.unit = (opts.unit and parse_unit(opts.unit)) or (
            parse_unit(self.layout.columns[self.value_index]) if self.value_index is not None else None) \
            or self.layout.unit_hint
        self.byte_position = 0                    # next byte to read
        self.line_number = 0                      # lines consumed so far
        self.first_time: float | None = None
        self.n_rows = 0
        probe = lookup_probe(opts.probe)
        self.fallback_rate_hz = opts.fs or (probe.fs_hz if probe else 5.0)

    def poll(self) -> tuple[np.ndarray, np.ndarray]:
        """New complete rows since the last call: (time_s, value) arrays."""
        # Read bytes and advance by bytes: re-encoding decoded text to find the
        # new position is wrong for 'utf-8-sig' (it adds a 3-byte BOM).
        try:
            with open(self.path, "rb") as file_handle:
                file_handle.seek(self.byte_position)
                raw_bytes = file_handle.read()
        except FileNotFoundError:
            return np.empty(0), np.empty(0)
        last_newline = raw_bytes.rfind(b"\n")
        if last_newline < 0:                       # no complete line yet
            return np.empty(0), np.empty(0)
        encoding = self.layout.encoding if self.byte_position == 0 else \
            self.layout.encoding.replace("-sig", "")
        new_text = raw_bytes[:last_newline + 1].decode(encoding, errors="replace")
        self.byte_position += last_newline + 1
        times, values = [], []
        for line in new_text.splitlines():
            self.line_number += 1
            if self.line_number <= self.layout.header_row + 1 or not line.strip():
                continue
            fields = _split(line, self.layout.sep)
            try:
                value_columns = [self.value_index] if self.value_index is not None \
                    else list(self.axis_indices.values())
                readings = []
                for column in value_columns:
                    token = fields[column].strip().strip('"')
                    if self.layout.decimal == ",":
                        token = token.replace(".", "").replace(",", ".")
                    readings.append(float(token))
                value = readings[0] if self.value_index is not None else math.sqrt(sum(r * r for r in readings))
                if self.time_indices:
                    raw_time = " ".join(fields[i].strip() for i in self.time_indices)
                    seconds = _safe_float(raw_time)
                    if not math.isfinite(seconds):
                        stamp = pd.to_datetime(raw_time, dayfirst=bool(
                            self.opts.dayfirst or re.match(r"^\d{1,2}\.\d{1,2}\.", raw_time)))
                        seconds = stamp.timestamp()
                else:
                    seconds = self.n_rows / self.fallback_rate_hz
            except (IndexError, ValueError):       # malformed row: skip it
                continue
            if self.first_time is None:
                self.first_time = seconds
            times.append(seconds - self.first_time)
            values.append(value)
            self.n_rows += 1
        return np.asarray(times, float), np.asarray(values, float)


class RingBuffer:
    """Fixed-size (time, value) ring buffer; every sample is also logged to disk.

    Keeps RAM constant during long live sessions; ``spill_path`` (raw
    float64 pairs) holds the whole session for later offline analysis.
    """

    def __init__(self, capacity: int, spill_path: str | os.PathLike | None = None) -> None:
        self.capacity = int(capacity)
        self.time_s = np.empty(self.capacity)
        self.values = np.empty(self.capacity)
        self.n = 0                                 # valid samples held
        self.head = 0                              # next write position
        self.spill_path = Path(spill_path) if spill_path else None

    def extend(self, new_times: np.ndarray, new_values: np.ndarray) -> None:
        """Append samples (and log them to the disk file)."""
        if self.spill_path is not None and new_times.size:
            with open(self.spill_path, "ab") as file_handle:
                np.column_stack([new_times, new_values]).astype(np.float64).tofile(file_handle)
        for sample_time, sample_value in zip(new_times, new_values):
            self.time_s[self.head] = sample_time
            self.values[self.head] = sample_value
            self.head = (self.head + 1) % self.capacity
            self.n = min(self.n + 1, self.capacity)

    def window(self, seconds: float) -> tuple[np.ndarray, np.ndarray]:
        """The most recent ``seconds`` of data, oldest first."""
        if self.n == 0:
            return np.empty(0), np.empty(0)
        order = (self.head - self.n + np.arange(self.n)) % self.capacity
        times, values = self.time_s[order], self.values[order]
        recent = times >= times[-1] - seconds
        return times[recent], values[recent]

    def clear(self) -> None:
        """Forget the buffered data (the disk log is kept)."""
        self.n = 0
        self.head = 0


def live_update(time_s: np.ndarray, values: np.ndarray, unit: str | None, opts: Options,
                backend: Backend) -> dict[str, Any] | None:
    """Envelope amplitude and Welch spectra of the current live window."""
    if time_s.size < 32:
        return None
    quantity, quantity_unit, _ = analysis_quantity(values, unit, opts)
    uniform = make_uniform(time_s, quantity, opts.fs)
    freq_hz, amplitude = amplitude_spectrum(uniform.values, uniform.sample_rate_hz, opts.window, backend)
    probe = lookup_probe(opts.probe)
    integration_time_s = opts.t_int or (probe.t_int_s if probe and probe.t_int_s else None)
    if opts.correct_probe and integration_time_s:
        amplitude = correct_probe(amplitude, freq_hz, integration_time_s, opts.max_boost_db)
    longest_block = max(stop - start for start, stop in uniform.blocks)
    welch_nperseg = min(opts.nperseg or _default_nperseg(longest_block), longest_block)
    welch_freq_hz, welch_psd, _ = welch_blocks(uniform.values, uniform.blocks, uniform.sample_rate_hz,
                                               welch_nperseg, opts.window, backend)
    peaks = find_spectral_peaks(freq_hz, amplitude, opts.snr, opts.max_peaks, opts.dyn_range_db)
    families = harmonic_families(peaks, freq_hz[1] - freq_hz[0], uniform.sample_rate_hz / 2)
    field_values, field_unit = to_field_like(values, unit, opts.z0)      # for E/H/S time plots (0.0.4)
    return {"time_s": time_s, "quantity": quantity, "quantity_unit": quantity_unit,
            "field_values": np.asarray(field_values, float), "field_unit": field_unit, "z0_ohm": opts.z0,
            "freq_hz": freq_hz, "amplitude": amplitude, "welch_freq_hz": welch_freq_hz,
            "welch_psd": welch_psd, "fs": uniform.sample_rate_hz, "peaks": peaks, "families": families}


def live_record(update: dict[str, Any]) -> Any:
    """A live update as an object with the SeriesResult fields that the unit helpers read."""
    from types import SimpleNamespace
    return SimpleNamespace(field_values=update["field_values"], field_unit=update["field_unit"],
                           quantity=update["quantity"], quantity_unit=update["quantity_unit"],
                           z0_ohm=update["z0_ohm"])


def _live_ring(path: str, opts: Options, window_s: float) -> RingBuffer:
    """Ring buffer sized for twice the window at the expected rate, logged to <file>.live.f64."""
    probe = lookup_probe(opts.probe)
    expected_rate_hz = opts.fs or (probe.fs_hz if probe else 1000.0)
    return RingBuffer(int(window_s * expected_rate_hz * 2) + 1024, Path(path).with_suffix(".live.f64"))


def run_live_console(path: str, opts: Options, window_s: float, update_s: float,
                     duration_s: float | None = None) -> int:
    """Console live mode: print the strongest envelope lines every update."""
    tail = LiveTail(path, opts)
    ring = _live_ring(path, opts, window_s)
    backend = Backend(opts.gpu, opts.fft_workers)
    end_time = time.time() + duration_s if duration_s else None
    selection = unit_selection(opts.display_unit)
    print(f"[live] following {path} (window {window_s:g} s, update {update_s:g} s); Ctrl+C stops")
    try:
        while end_time is None or time.time() < end_time:
            ring.extend(*tail.poll())
            update = live_update(*ring.window(window_s), tail.unit, opts, backend)
            if update:
                unit = unit_for_quantity(update["quantity_unit"], selection)
                label = display_label(unit, update["quantity_unit"])
                strongest = sorted(update["peaks"], key=lambda peak: -peak["amp"])[:4]
                peak_text = ", ".join(f"{peak['f_hz']:.4g} Hz ({_shown(peak['amp'], unit):.4g} {label})"
                                      for peak in strongest)
                family_text = "; ".join(f"f0 {fam['f0_hz']:.4g} Hz = {fam['rpm']:.3g} rpm"
                                        for fam in update["families"][:2])
                print(f"[live] n={ring.n} fs={update['fs']:.4g} Hz  peaks: {peak_text or '-'}  {family_text}")
            time.sleep(update_s)
    except KeyboardInterrupt:
        pass
    return 0


#: Filled by launch_gui/run_live_gui on exit (used by tests and Spyder sessions).
live_gui_state: dict[str, Any] = {}


# %% ===========================================================================
#    GUI: QT BINDING (Qt.py or QtPy abstraction layer, PySide6 binding)
# =============================================================================
# The GUI is written once against an abstraction layer so the same source
# runs on any binding; PySide6 is the binding asked for. The layer is chosen
# in this order: Qt.py (as in the QuickSyn controller), QtPy, PySide6
# directly. EMF_FFT_QT_LAYER=qtpy puts QtPy first. The command line, batch
# and verification code never need Qt: without a binding the module still
# imports (the GUI classes are then defined on a placeholder) and only
# launch_gui() reports what is missing.
QT_LAYER_PREFERENCE = os.environ.get("EMF_FFT_QT_LAYER", "qt.py").strip().lower()


class _QtMissingMeta(type):
    """Metaclass of the placeholder: any class attribute is the placeholder itself."""

    def __getattr__(cls, name: str) -> Any:
        return cls


class _QtMissing(metaclass=_QtMissingMeta):
    """Stands in for QtCore/QtGui/QtWidgets/pg when no Qt binding is installed."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        return _QtMissing


def _import_qt() -> tuple[Any, Any, Any, str, str, list[str]]:
    """Import QtCore, QtGui, QtWidgets through the preferred abstraction layer.

    Returns (QtCore, QtGui, QtWidgets, layer description, binding description,
    errors of the layers that failed).
    """
    os.environ.setdefault("QT_PREFERRED_BINDING", "PySide6")   # read by Qt.py
    os.environ.setdefault("QT_API", "pyside6")                  # read by QtPy
    os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")        # read by pyqtgraph
    order = ["qtpy", "qt.py"] if QT_LAYER_PREFERENCE == "qtpy" else ["qt.py", "qtpy"]
    errors: list[str] = []
    for layer in order + ["pyside6"]:
        try:
            if layer == "qt.py":
                import Qt as qt_layer
                from Qt import QtCore as core, QtGui as gui, QtWidgets as widgets
                return (core, gui, widgets, f"Qt.py {qt_layer.__version__}",
                        f"{qt_layer.__binding__} {qt_layer.__binding_version__} (Qt {qt_layer.__qt_version__})",
                        errors)
            if layer == "qtpy":
                import qtpy as qt_layer
                from qtpy import QtCore as core, QtGui as gui, QtWidgets as widgets
                return (core, gui, widgets, f"QtPy {qt_layer.__version__}",
                        f"{qt_layer.API_NAME} (Qt {qt_layer.QT_VERSION})", errors)
            import PySide6
            from PySide6 import QtCore as core, QtGui as gui, QtWidgets as widgets
            return (core, gui, widgets, "PySide6 directly (no abstraction layer installed)",
                    f"PySide6 {PySide6.__version__}", errors)
        except Exception as exc:  # noqa: BLE001 - try the next layer
            errors.append(f"{layer}: {type(exc).__name__}: {exc}")
    return _QtMissing, _QtMissing, _QtMissing, "none", "none", errors


QtCore, QtGui, QtWidgets, QT_ABSTRACTION, QT_BINDING, _QT_IMPORT_ERRORS = _import_qt()
HAVE_QT = QtCore is not _QtMissing
try:                                   # pyqtgraph draws every plot of the GUI
    if not HAVE_QT:
        raise ImportError("no Qt binding")
    import pyqtgraph as pg
    HAVE_PYQTGRAPH = True
except Exception:  # noqa: BLE001 - the GUI then shows a message instead of plots
    pg = _QtMissing
    HAVE_PYQTGRAPH = False

#: QAction and QActionGroup live in QtGui in Qt 6 and in QtWidgets in Qt 5.
QAction = getattr(QtGui, "QAction", None) or getattr(QtWidgets, "QAction", _QtMissing)
QActionGroup = getattr(QtGui, "QActionGroup", None) or getattr(QtWidgets, "QActionGroup", _QtMissing)

#: Application identity (window title, QSettings, About dialog).
APP_NAME = PROGRAM_NAME
APP_ORG = "NRAO-GBO"
#: (organisation, application) under which QSettings keeps the GUI state;
#: tools that open the window (manual builder, tests) point it elsewhere so
#: the user's own settings are never read or overwritten.
SETTINGS_SCOPE = (APP_ORG, APP_NAME)
#: Plot colours, the same order as the Veusz pages (vszh5_writer.TRACE_COLOURS).
PLOT_COLOURS = vszh5_writer.TRACE_COLOURS
#: Offset from Veusz date seconds (since 2009-01-01) to Unix seconds.
VEUSZ_TO_UNIX_S = (VEUSZ_EPOCH - _dt.datetime(1970, 1, 1)).total_seconds()
#: Spectrum y-axis choices of the Display group.
SPECTRUM_SCALES = ("log", "linear", "dB rel. max (20 log10)")


# %% ===========================================================================
#    GUI: THEME MANAGER (light / dark / system, as in the QuickSyn controller)
# =============================================================================
class ThemeManager:
    """Applies light, dark or system palettes to the whole application.

    Qt 6 exposes a colour-scheme hint, but it is honoured inconsistently
    across platforms, so explicit palettes are supplied for the two forced
    modes and the platform default is restored for "system". pyqtgraph plots
    are recoloured by the main window (they do not follow the Qt palette).
    """

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"

    def __init__(self, app: Any) -> None:
        self.app = app
        self._default_palette = QtGui.QPalette(app.palette())
        self._default_style = app.style().objectName() if app.style() else "fusion"
        self.current = self.SYSTEM

    @staticmethod
    def _dark_palette() -> Any:
        """A neutral dark palette suitable for long lab sessions."""
        role = QtGui.QPalette.ColorRole
        group = QtGui.QPalette.ColorGroup
        palette = QtGui.QPalette()
        base = QtGui.QColor(32, 33, 36)
        alternate = QtGui.QColor(42, 43, 47)
        text = QtGui.QColor(226, 228, 231)
        accent = QtGui.QColor(72, 140, 214)
        palette.setColor(role.Window, base)
        palette.setColor(role.WindowText, text)
        palette.setColor(role.Base, QtGui.QColor(24, 25, 28))
        palette.setColor(role.AlternateBase, alternate)
        palette.setColor(role.ToolTipBase, alternate)
        palette.setColor(role.ToolTipText, text)
        palette.setColor(role.Text, text)
        palette.setColor(role.Button, alternate)
        palette.setColor(role.ButtonText, text)
        palette.setColor(role.BrightText, QtGui.QColor(255, 96, 96))
        palette.setColor(role.Link, accent)
        palette.setColor(role.Highlight, accent)
        palette.setColor(role.HighlightedText, QtGui.QColor(18, 18, 20))
        for disabled_role in (role.Text, role.ButtonText, role.WindowText):
            palette.setColor(group.Disabled, disabled_role, QtGui.QColor(128, 130, 134))
        return palette

    @staticmethod
    def _light_palette() -> Any:
        """A neutral light palette."""
        role = QtGui.QPalette.ColorRole
        palette = QtGui.QPalette()
        palette.setColor(role.Window, QtGui.QColor(246, 246, 248))
        palette.setColor(role.WindowText, QtGui.QColor(24, 25, 28))
        palette.setColor(role.Base, QtGui.QColor(255, 255, 255))
        palette.setColor(role.AlternateBase, QtGui.QColor(238, 239, 242))
        palette.setColor(role.ToolTipBase, QtGui.QColor(255, 255, 220))
        palette.setColor(role.ToolTipText, QtGui.QColor(24, 25, 28))
        palette.setColor(role.Text, QtGui.QColor(24, 25, 28))
        palette.setColor(role.Button, QtGui.QColor(240, 241, 244))
        palette.setColor(role.ButtonText, QtGui.QColor(24, 25, 28))
        palette.setColor(role.BrightText, QtGui.QColor(190, 30, 30))
        palette.setColor(role.Highlight, QtGui.QColor(50, 118, 198))
        palette.setColor(role.HighlightedText, QtGui.QColor(255, 255, 255))
        return palette

    def apply(self, mode: str) -> None:
        """Apply one of ``light``, ``dark`` or ``system``."""
        self.current = mode
        if mode == self.DARK:
            self.app.setStyle("Fusion")
            self.app.setPalette(self._dark_palette())
        elif mode == self.LIGHT:
            self.app.setStyle("Fusion")
            self.app.setPalette(self._light_palette())
        else:
            self.app.setStyle(self._default_style)
            self.app.setPalette(self._default_palette)

    def is_dark(self) -> bool:
        """True when the active palette has a dark window background."""
        return self.app.palette().color(QtGui.QPalette.ColorRole.Window).lightness() < 128


# %% ===========================================================================
#    GUI: SMALL WIDGETS AND HELPERS
# =============================================================================
def make_double_spin(minimum: float, maximum: float, value: float, decimals: int = 3,
                     step: float = 1.0, suffix: str = "", special: str = "") -> Any:
    """A QDoubleSpinBox; ``special`` is shown instead of the minimum (e.g. "auto")."""
    spin = QtWidgets.QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setValue(value)
    if suffix:
        spin.setSuffix(suffix)
    if special:
        spin.setSpecialValueText(special)
    spin.setKeyboardTracking(False)
    return spin


def make_int_spin(minimum: int, maximum: int, value: int, step: int = 1, special: str = "") -> Any:
    """A QSpinBox; ``special`` is shown instead of the minimum."""
    spin = QtWidgets.QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setValue(value)
    if special:
        spin.setSpecialValueText(special)
    spin.setKeyboardTracking(False)
    return spin


def make_combo(items: Sequence[tuple[str, Any]], current: Any = None) -> Any:
    """A QComboBox of (text, data) items with ``current`` data selected."""
    combo = QtWidgets.QComboBox()
    for text, data in items:
        combo.addItem(text, data)
    if current is not None:
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
    return combo


def import_qt_module(name: str) -> Any:
    """Another Qt module (e.g. "QtSvg") through the same abstraction layer as QtCore."""
    import importlib
    if QT_ABSTRACTION.startswith("Qt.py"):
        import Qt
        module = getattr(Qt, name, None)
        if module is not None:
            return module
    elif QT_ABSTRACTION.startswith("QtPy"):
        return importlib.import_module(f"qtpy.{name}")
    return importlib.import_module(f"PySide6.{name}")


def export_widget_svg(widget: Any, path: str, title: str = "") -> None:
    """Vector SVG of a widget drawn by Qt itself (QSvgGenerator).

    Used when pyqtgraph's SVG exporter fails, which it does on curves with
    gaps (the NaN points used for log axes).
    """
    qt_svg = import_qt_module("QtSvg")
    generator = qt_svg.QSvgGenerator()
    generator.setFileName(str(path))
    size = widget.size()
    generator.setSize(size)
    generator.setViewBox(QtCore.QRect(0, 0, size.width(), size.height()))
    generator.setTitle(title or APP_NAME)
    generator.setDescription(f"{APP_NAME} {__version__}")
    painter = QtGui.QPainter(generator)
    try:
        widget.render(painter)
    finally:
        painter.end()


def monospace_font() -> Any:
    """The system fixed-pitch font (log, summary and inspect panes)."""
    return QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)


def _finite_positive(values: np.ndarray) -> np.ndarray:
    """Values for a log axis: non-positive and non-finite become NaN (gaps)."""
    array = np.asarray(values, dtype=float).copy()
    array[~np.isfinite(array) | (array <= 0)] = np.nan
    return array


# %% ===========================================================================
#    GUI: PLOT PANELS (pyqtgraph)
# =============================================================================
class PlotPanel(QtWidgets.QWidget):
    """One pyqtgraph plot with legend, grid, peak downsampling, cursor readout,
    export and theming. Right-click gives pyqtgraph's own menu (view all,
    axis ranges, log axes, grid, export)."""

    cursorMoved = QtCore.Signal(str)

    def __init__(self, date_axis: bool = False, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.message = QtWidgets.QLabel("")
        self.message.setWordWrap(True)
        if not HAVE_PYQTGRAPH:
            self.message.setText("pyqtgraph is not installed: mamba install -c conda-forge pyqtgraph")
            layout.addWidget(self.message)
            self.plot_widget = None
            return
        # The instrument clock is naive wall-clock time: show it as UTC so the
        # axis reads exactly what the instrument logged.
        self.date_axis = bool(date_axis)
        axis_items = {"bottom": pg.DateAxisItem(orientation="bottom", utcOffset=0)} if date_axis else None
        self.plot_widget = pg.PlotWidget(axisItems=axis_items)
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=0.25)
        self.plot_item.setDownsampling(auto=True, mode="peak")    # long logs stay fast
        self.plot_item.setClipToView(True)
        self.legend = self.plot_item.addLegend(offset=(-10, 10))
        for axis_name in ("left", "bottom"):
            # Never rescale to "(x0.001)": values must read in the unit named on the axis.
            self.plot_item.getAxis(axis_name).enableAutoSIPrefix(False)
        layout.addWidget(self.plot_widget, 1)
        layout.addWidget(self.message)
        self.dark = False
        self.log_y = False
        self.x_label = ""
        self.y_label = ""
        self.plot_widget.scene().sigMouseMoved.connect(self._mouse_moved)

    def _mouse_moved(self, position: Any) -> None:
        """Emit the data coordinates under the mouse (status-bar readout)."""
        if not self.plot_item.sceneBoundingRect().contains(position):
            return
        point = self.plot_item.vb.mapSceneToView(position)
        x_value, y_value = point.x(), point.y()
        if self.log_y:
            y_value = 10.0 ** y_value
        if self.date_axis:
            try:
                x_text = _dt.datetime.fromtimestamp(x_value, _dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            except (OverflowError, OSError, ValueError):
                x_text = f"{x_value:.6g}"
        else:
            x_text = f"{x_value:.6g}"
        self.cursorMoved.emit(f"{self.x_label or 'x'}: {x_text}    {self.y_label or 'y'}: {y_value:.6g}")

    def export(self, path: str) -> None:
        """Save the plot as PNG/JPG (1600 px wide), SVG, or the curve data as CSV."""
        import pyqtgraph.exporters as exporters
        suffix = Path(path).suffix.lower()
        exporter_class = {".png": exporters.ImageExporter, ".jpg": exporters.ImageExporter,
                          ".svg": exporters.SVGExporter, ".csv": exporters.CSVExporter}.get(suffix)
        if exporter_class is None:
            raise ValueError(f"unsupported export format {suffix!r} (png, jpg, svg, csv)")
        exporter = exporter_class(self.plot_item)
        if exporter_class is exporters.ImageExporter:
            exporter.parameters()["width"] = 1600
        try:
            exporter.export(str(path))
        except Exception:  # noqa: BLE001 - pyqtgraph's SVG writer fails on curves with gaps
            if suffix != ".svg":
                raise
            export_widget_svg(self.plot_widget, path, self.plot_item.titleLabel.text)

    def auto_range(self) -> None:
        """Show all data again after zooming."""
        if self.plot_widget is not None:
            self.plot_item.enableAutoRange()

    def use_date_axis(self, on: bool) -> None:
        """Date/time labels on x (Unix seconds shown as UTC = the logged wall clock) or numbers."""
        if self.plot_widget is None or bool(on) == self.date_axis:
            return
        axis = pg.DateAxisItem(orientation="bottom", utcOffset=0) if on else pg.AxisItem(orientation="bottom")
        axis.enableAutoSIPrefix(False)
        self.plot_item.setAxisItems({"bottom": axis})
        self.date_axis = bool(on)
        self.apply_theme(self.dark)

    def clear(self, message: str = "") -> None:
        """Remove every curve; show ``message`` under the plot."""
        self.message.setText(message)
        if self.plot_widget is None:
            return
        self.plot_item.clear()
        self.legend.clear()

    def set_labels(self, title: str, xlabel: str, ylabel: str) -> None:
        """Plot title and axis labels."""
        if self.plot_widget is None:
            return
        self.x_label, self.y_label = xlabel, ylabel
        self.plot_item.setTitle(title)
        self.plot_item.setLabel("bottom", xlabel)
        self.plot_item.setLabel("left", ylabel)

    def set_log_y(self, log_y: bool) -> None:
        """Logarithmic or linear y axis."""
        if self.plot_widget is not None:
            self.log_y = bool(log_y)
            self.plot_item.setLogMode(x=False, y=log_y)

    def add_curve(self, x_values: Any, y_values: Any, name: str = "", colour_index: int = 0,
                  style: str = "solid", width: float = 1.5, symbol: str | None = None) -> None:
        """Add a line (or markers only with ``style="none"``)."""
        if self.plot_widget is None:
            return
        colour = PLOT_COLOURS[colour_index % len(PLOT_COLOURS)]
        pen_style = {"solid": QtCore.Qt.PenStyle.SolidLine, "dashed": QtCore.Qt.PenStyle.DashLine,
                     "dotted": QtCore.Qt.PenStyle.DotLine}.get(style, QtCore.Qt.PenStyle.SolidLine)
        pen = None if style == "none" else pg.mkPen(colour, width=width, style=pen_style)
        self.plot_item.plot(np.asarray(x_values, float), np.asarray(y_values, float), pen=pen,
                            name=name or None, symbol=symbol, symbolSize=6, symbolBrush=colour,
                            symbolPen=colour, connect="finite")

    def apply_theme(self, dark: bool) -> None:
        """Plot background and text colours of the theme."""
        self.dark = dark
        if self.plot_widget is None:
            return
        background, foreground = ("#18191c", "#e2e4e7") if dark else ("#ffffff", "#18191c")
        self.plot_widget.setBackground(background)
        for axis_name in ("left", "bottom", "right", "top"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setPen(foreground)
            axis.setTextPen(foreground)
        self.plot_item.titleLabel.setText(self.plot_item.titleLabel.text, color=foreground)
        self.legend.setLabelTextColor(foreground)


class ImagePanel(QtWidgets.QWidget):
    """A 2-D image (spectrogram, modulation map) with a colour bar, cursor
    readout of x, y and the pixel value, and export."""

    cursorMoved = QtCore.Signal(str)

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.message = QtWidgets.QLabel("")
        self.message.setWordWrap(True)
        if not HAVE_PYQTGRAPH:
            self.message.setText("pyqtgraph is not installed: mamba install -c conda-forge pyqtgraph")
            layout.addWidget(self.message)
            self.plot_widget = None
            return
        self.plot_widget = pg.PlotWidget()
        self.plot_item = self.plot_widget.getPlotItem()
        self.image_item = pg.ImageItem(axisOrder="row-major")      # data[row = y, column = x]
        self.plot_item.addItem(self.image_item)
        self.colour_bar = pg.ColorBarItem(values=(0.0, 1.0), colorMap=pg.colormap.get("viridis"),
                                          interactive=True)
        self.colour_bar.setImageItem(self.image_item, insert_in=self.plot_item)
        for axis_name in ("left", "bottom"):
            self.plot_item.getAxis(axis_name).enableAutoSIPrefix(False)
        layout.addWidget(self.plot_widget, 1)
        layout.addWidget(self.message)
        self.image: np.ndarray | None = None
        self.labels = ("x", "y", "z")
        self.plot_widget.scene().sigMouseMoved.connect(self._mouse_moved)

    def _mouse_moved(self, position: Any) -> None:
        """Emit x, y and the image value under the mouse."""
        if self.image is None or not self.plot_item.sceneBoundingRect().contains(position):
            return
        point = self.plot_item.vb.mapSceneToView(position)
        pixel = self.image_item.mapFromScene(position)
        row, column = int(np.floor(pixel.y())), int(np.floor(pixel.x()))
        value = (f"{self.image[row, column]:.4g}" if 0 <= row < self.image.shape[0]
                 and 0 <= column < self.image.shape[1] else "-")
        self.cursorMoved.emit(f"{self.labels[0]}: {point.x():.6g}    {self.labels[1]}: {point.y():.6g}    "
                              f"{self.labels[2]}: {value}")

    def export(self, path: str) -> None:
        """Save the image plot as PNG/JPG or SVG."""
        import pyqtgraph.exporters as exporters
        suffix = Path(path).suffix.lower()
        if suffix not in (".png", ".jpg", ".svg"):
            raise ValueError("images export as png, jpg or svg (the data are in the .vszh5 and .npz)")
        exporter = (exporters.SVGExporter if suffix == ".svg" else exporters.ImageExporter)(self.plot_item)
        if suffix != ".svg":
            exporter.parameters()["width"] = 1600
        try:
            exporter.export(str(path))
        except Exception:  # noqa: BLE001 - fall back to Qt's own SVG generator
            if suffix != ".svg":
                raise
            export_widget_svg(self.plot_widget, path, self.plot_item.titleLabel.text)

    def auto_range(self) -> None:
        """Show the whole image again after zooming."""
        if self.plot_widget is not None:
            self.plot_item.autoRange()

    def clear(self, message: str = "") -> None:
        """Empty image and a message."""
        self.message.setText(message)
        self.image = None
        if self.plot_widget is not None:
            self.image_item.clear()
            self.plot_item.setTitle("")

    def set_image(self, image: np.ndarray, x_centres: np.ndarray, y_centres: np.ndarray,
                  zmin: float, zmax: float, title: str, xlabel: str, ylabel: str, zlabel: str) -> None:
        """Show ``image`` (rows = y) over the given pixel centres, colours from zmin to zmax."""
        self.message.setText("")
        if self.plot_widget is None:
            return
        x_centres = np.asarray(x_centres, float)
        y_centres = np.asarray(y_centres, float)
        x_step = (x_centres[-1] - x_centres[0]) / max(x_centres.size - 1, 1) if x_centres.size > 1 else 1.0
        y_step = (y_centres[-1] - y_centres[0]) / max(y_centres.size - 1, 1) if y_centres.size > 1 else 1.0
        self.image = np.asarray(image, float)
        self.labels = (xlabel, ylabel, zlabel)
        self.image_item.setImage(np.nan_to_num(self.image, nan=zmin), autoLevels=False)
        self.image_item.setRect(QtCore.QRectF(x_centres[0] - x_step / 2, y_centres[0] - y_step / 2,
                                              x_step * x_centres.size, y_step * y_centres.size))
        self.colour_bar.setLevels((zmin, zmax))
        self.colour_bar.axis.setLabel(zlabel)
        self.plot_item.setTitle(title)
        self.plot_item.setLabel("bottom", xlabel)
        self.plot_item.setLabel("left", ylabel)
        self.plot_item.autoRange()

    def apply_theme(self, dark: bool) -> None:
        """Plot background and text colours of the theme."""
        if self.plot_widget is None:
            return
        background, foreground = ("#18191c", "#e2e4e7") if dark else ("#ffffff", "#18191c")
        self.plot_widget.setBackground(background)
        for axis_name in ("left", "bottom"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setPen(foreground)
            axis.setTextPen(foreground)
        self.colour_bar.axis.setPen(foreground)
        self.colour_bar.axis.setTextPen(foreground)
        self.plot_item.titleLabel.setText(self.plot_item.titleLabel.text, color=foreground)


# %% ===========================================================================
#    GUI: BACKGROUND TASKS (analysis, inspect, verification in a QThread)
# =============================================================================
class TaskThread(QtCore.QThread):
    """Runs ``job(report, deliver, is_cancelled)`` off the GUI thread.

    ``report(text)`` logs a line, ``deliver(obj)`` hands a partial result to
    the window (one per analysed file), ``is_cancelled()`` is polled between
    files. NumPy/SciPy release the GIL in their FFTs, so the window stays
    responsive while a long log is analysed.

    Signals
    -------
    messageLogged(str), resultDelivered(object), taskFinished(object),
    taskFailed(str)
    """

    messageLogged = QtCore.Signal(str)
    resultDelivered = QtCore.Signal(object)
    taskFinished = QtCore.Signal(object)
    taskFailed = QtCore.Signal(str)

    def __init__(self, name: str, job: Any, parent: Any = None) -> None:
        super().__init__(parent)
        self.task_name = name
        self.job = job
        self._cancelled = False

    def cancel(self) -> None:
        """Ask the job to stop after the current file."""
        self._cancelled = True

    def run(self) -> None:  # noqa: D401 - Qt API
        try:
            value = self.job(self.messageLogged.emit, self.resultDelivered.emit, lambda: self._cancelled)
            self.taskFinished.emit(value)
        except Exception as exc:  # noqa: BLE001 - shown in the log, never crashes the GUI
            self.taskFailed.emit(f"{self.task_name}: {type(exc).__name__}: {exc}")


def analysis_job(paths: Sequence[str], opts: Options, write_files: bool, jobs: int) -> Any:
    """A TaskThread job: analyse ``paths``; deliver (path, result, written) per file."""
    def job(report: Any, deliver: Any, is_cancelled: Any) -> int:
        delivered = 0
        if jobs > 1 and len(paths) > 1:
            worker_opts = Options(**{**asdict(opts), "fft_workers": 1})
            with cf.ProcessPoolExecutor(max_workers=jobs) as executor:
                futures = {executor.submit(analyse_and_write, p, worker_opts, write_files): p for p in paths}
                for future in cf.as_completed(futures):
                    try:
                        deliver(future.result())
                        delivered += 1
                    except Exception as exc:  # noqa: BLE001
                        report(f"ERROR {Path(futures[future]).name}: {type(exc).__name__}: {exc}")
            return delivered
        for index, path in enumerate(paths, start=1):
            if is_cancelled():
                report("stopped by the user")
                break
            report(f"[{index}/{len(paths)}] analysing {Path(path).name} ...")
            try:
                deliver(analyse_and_write(path, opts, write_files))
                delivered += 1
            except Exception as exc:  # noqa: BLE001 - next file
                report(f"ERROR {Path(path).name}: {type(exc).__name__}: {exc}")
        return delivered
    return job


# %% ===========================================================================
#    GUI: SETTINGS PANEL (inputs, analysis options, output, display units)
# =============================================================================
class SettingsPanel(QtWidgets.QScrollArea):
    """Left-hand panel: input files and every analysis, output and display option.

    ``options()`` returns an Options object for the analysis functions;
    ``display()`` the display choices, which change the plots without
    re-analysing (the results are kept in SI units).
    """

    displayChanged = QtCore.Signal()
    inspectRequested = QtCore.Signal()
    analyseRequested = QtCore.Signal()
    stopRequested = QtCore.Signal()

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(370)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(6, 6, 6, 6)
        defaults = Options()

        # -- inputs ------------------------------------------------------------------
        inputs_box = QtWidgets.QGroupBox("Input files and folders")
        inputs_layout = QtWidgets.QVBoxLayout(inputs_box)
        self.input_list = QtWidgets.QListWidget()
        self.input_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.input_list.setMinimumHeight(90)
        self.input_list.setToolTip("FieldMan/Narda-TSX, NBM, EHP-50 TS and SignalShark files; "
                                   "an EHP-50 TS folder of spectra. Drag files here too.")
        self.input_list.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.input_list.customContextMenuRequested.connect(self._input_menu)
        inputs_layout.addWidget(self.input_list)
        buttons = QtWidgets.QHBoxLayout()
        self.add_files_button = QtWidgets.QPushButton("Add files...")
        self.add_folder_button = QtWidgets.QPushButton("Add folder...")
        self.remove_button = QtWidgets.QPushButton("Remove")
        self.clear_button = QtWidgets.QPushButton("Clear")
        for button in (self.add_files_button, self.add_folder_button, self.remove_button, self.clear_button):
            buttons.addWidget(button)
        inputs_layout.addLayout(buttons)
        layout.addWidget(inputs_box)

        # -- instrument ----------------------------------------------------------------
        instrument_box = QtWidgets.QGroupBox("Instrument")
        form = QtWidgets.QFormLayout(instrument_box)
        self.source_combo = make_combo([(s, s) for s in ("auto", "fieldman", "tsx", "nbm", "ehp",
                                                          "signalshark", "xlsx")], "auto")
        self.probe_combo = make_combo([("(none)", "")] + [(f"{k}  ({v.part})", k) for k, v in PROBES.items()], "")
        self.fs_spin = make_double_spin(0.0, 1e7, 0.0, 4, 1.0, " Hz", "from file")
        self.t_int_spin = make_double_spin(0.0, 1e5, 0.0, 3, 1.0, " ms", "catalogue")
        self.source_combo.setToolTip("Reader; 'auto' detects it from the file (see Inspect)")
        self.probe_combo.setToolTip("Sets the nominal sample rate, integration time and range limits")
        self.fs_spin.setToolTip("Only for files without a time column")
        self.t_int_spin.setToolTip("Probe integration time for the sinc model; overrides the catalogue")
        form.addRow("Source", self.source_combo)
        form.addRow("Probe", self.probe_combo)
        form.addRow("Sample rate", self.fs_spin)
        form.addRow("Integration T", self.t_int_spin)
        layout.addWidget(instrument_box)

        # -- analysis --------------------------------------------------------------------
        analysis_box = QtWidgets.QGroupBox("Analysis")
        form = QtWidgets.QFormLayout(analysis_box)
        self.quantity_combo = make_combo([("power density (linear in sources)", "power"),
                                          ("field strength", "field"), ("dB (log power)", "db")], "power")
        self.window_combo = make_combo([(w, w) for w in ("hann", "hamming", "blackman", "blackmanharris",
                                                         "flattop", "boxcar")], "hann")
        self.nperseg_spin = make_int_spin(0, 2 ** 24, 0, 64, "auto")
        self.zoom_check = QtWidgets.QCheckBox("fixed band")
        self.zoom_low = make_double_spin(0.0, 1e6, 0.0, 5, 0.01, " Hz")
        self.zoom_high = make_double_spin(0.0, 1e6, 1.0, 5, 0.01, " Hz")
        zoom_row = QtWidgets.QHBoxLayout()
        for widget in (self.zoom_check, self.zoom_low, self.zoom_high):
            zoom_row.addWidget(widget)
        self.zoom_points_spin = make_int_spin(16, 1 << 20, defaults.zoom_points, 256)
        self.lomb_combo = make_combo([("auto (gaps / jitter)", "auto"), ("on", "on"), ("off", "off")], "auto")
        self.correct_check = QtWidgets.QCheckBox("undo probe averaging")
        self.boost_spin = make_double_spin(0.0, 40.0, defaults.max_boost_db, 1, 1.0, " dB")
        self.snr_spin = make_double_spin(1.5, 1000.0, defaults.snr, 1, 0.5, " x median")
        self.dyn_spin = make_double_spin(1.0, 200.0, defaults.dyn_range_db, 1, 5.0, " dB")
        self.z0_spin = make_double_spin(1.0, 1000.0, defaults.z0, 6, 0.1, " Ω")
        self.quantity_combo.setToolTip("Power density is linear in the sources (recommended); "
                                       "field strength creates intermodulation lines")
        self.window_combo.setToolTip("FFT/Welch/CZT window; flattop for amplitude accuracy, hann in general")
        self.nperseg_spin.setToolTip("Welch segment length; auto = about seven averages")
        self.correct_check.setToolTip("Divide by |sinc(f T)|, at most the maximum boost; NaN from 1/T")
        self.snr_spin.setToolTip("A peak must stand this many times above the median spectrum level")
        self.z0_spin.setToolTip("Wave impedance for S = E^2/Z0; 377 reproduces Narda displays")
        form.addRow("Quantity", self.quantity_combo)
        form.addRow("Window", self.window_combo)
        form.addRow("Welch nperseg", self.nperseg_spin)
        form.addRow("CZT zoom", zoom_row)
        form.addRow("Zoom points", self.zoom_points_spin)
        form.addRow("Lomb-Scargle", self.lomb_combo)
        form.addRow("Probe correction", self.correct_check)
        form.addRow("Max boost", self.boost_spin)
        form.addRow("Peak threshold", self.snr_spin)
        form.addRow("Dynamic range", self.dyn_spin)
        form.addRow("Z0", self.z0_spin)
        layout.addWidget(analysis_box)

        # -- spectrograms (SignalShark, EHP-50 TS) -------------------------------------------
        spectrogram_box = QtWidgets.QGroupBox("Spectrograms (SignalShark, EHP-50 TS)")
        form = QtWidgets.QFormLayout(spectrogram_box)
        self.channels_edit = QtWidgets.QLineEdit(defaults.rf_channels)
        self.channels_edit.setToolTip("'auto:N' (N strongest carriers) or 'f1:f2,f3:f4' in Hz")
        self.af_check = QtWidgets.QCheckBox("antenna factor")
        self.af_spin = make_double_spin(-100.0, 200.0, 0.0, 2, 0.5, " dB/m")
        af_row = QtWidgets.QHBoxLayout()
        af_row.addWidget(self.af_check)
        af_row.addWidget(self.af_spin)
        self.rbw_check = QtWidgets.QCheckBox("RBW")
        self.rbw_spin = make_double_spin(0.001, 1e9, 100e3, 3, 1000.0, " Hz")
        rbw_row = QtWidgets.QHBoxLayout()
        rbw_row.addWidget(self.rbw_check)
        rbw_row.addWidget(self.rbw_spin)
        self.enbw_spin = make_double_spin(0.5, 3.0, GAUSSIAN_ENBW_FACTOR, 4, 0.01, " x RBW")
        form.addRow("Channels", self.channels_edit)
        form.addRow("dBm/dBuV", af_row)
        form.addRow("Channel power", rbw_row)
        form.addRow("ENBW factor", self.enbw_spin)
        layout.addWidget(spectrogram_box)

        # -- columns and format overrides ------------------------------------------------------
        format_box = QtWidgets.QGroupBox("Columns and format (blank = detect)")
        form = QtWidgets.QFormLayout(format_box)
        self.time_col_edit = QtWidgets.QLineEdit()
        self.time_col_edit.setPlaceholderText("e.g. Date+Time")
        self.value_col_edit = QtWidgets.QLineEdit()
        self.unit_edit = QtWidgets.QLineEdit()
        self.unit_edit.setPlaceholderText("e.g. V/m, mW/cm2, dBuV/m")
        self.sep_edit = QtWidgets.QLineEdit()
        self.decimal_edit = QtWidgets.QLineEdit()
        self.dayfirst_combo = make_combo([("detect", None), ("yes", True), ("no", False)], None)
        self.h5_level_edit = QtWidgets.QLineEdit()
        self.h5_freq_edit = QtWidgets.QLineEdit()
        self.h5_time_edit = QtWidgets.QLineEdit()
        for label, widget in (("Time column", self.time_col_edit), ("Value column", self.value_col_edit),
                              ("Unit", self.unit_edit), ("Delimiter", self.sep_edit),
                              ("Decimal mark", self.decimal_edit), ("Day first", self.dayfirst_combo),
                              ("HDF5 levels", self.h5_level_edit), ("HDF5 frequency", self.h5_freq_edit),
                              ("HDF5 time", self.h5_time_edit)):
            form.addRow(label, widget)
        layout.addWidget(format_box)

        # -- output ------------------------------------------------------------------------------
        output_box = QtWidgets.QGroupBox("Output")
        form = QtWidgets.QFormLayout(output_box)
        self.write_check = QtWidgets.QCheckBox("write .vszh5, CSV, JSON")
        self.write_check.setChecked(True)
        self.out_edit = QtWidgets.QLineEdit()
        self.out_edit.setPlaceholderText("<input>_fft beside each input")
        self.out_button = QtWidgets.QPushButton("...")
        self.out_button.setMaximumWidth(32)
        out_row = QtWidgets.QHBoxLayout()
        out_row.addWidget(self.out_edit)
        out_row.addWidget(self.out_button)
        self.render_check = QtWidgets.QCheckBox("render PDF/PNG with Veusz")
        self.pickle_check = QtWidgets.QCheckBox("also offload result to .pkl")
        self.jobs_spin = make_int_spin(1, max(1, os.cpu_count() or 1), 1)
        self.gpu_check = QtWidgets.QCheckBox("use CuPy/CUDA when available")
        form.addRow("Files", self.write_check)
        form.addRow("Folder", out_row)
        form.addRow("Render", self.render_check)
        form.addRow("Pickle", self.pickle_check)
        form.addRow("Parallel files", self.jobs_spin)
        form.addRow("GPU", self.gpu_check)
        layout.addWidget(output_box)

        # -- units (re-plot at once, no re-analysis; 0.0.4: one unit per family) ------------------
        display_box = QtWidgets.QGroupBox("Units and display")
        form = QtWidgets.QFormLayout(display_box)
        #: family -> combo of its display units (DISPLAY_UNITS)
        self.unit_combos: dict[str, Any] = {}
        family_tips = {
            "S": "Power density of plots, peaks and Veusz pages; data files stay in W/m\u00b2",
            "E": "Electric field: logged E, or E = sqrt(S Z0) of the plane wave",
            "H": "Magnetic field: logged H, or H = sqrt(S/Z0) of the plane wave",
            "B": "Magnetic flux density (B logged, e.g. EHP-50 TS in \u00b5T); B\u00b2 uses its square",
            "P": "Power at the analyzer port (dBm inputs without an antenna factor)",
            "V": "Voltage at the analyzer port (dB\u00b5V inputs without an antenna factor)"}
        for family_key, family in UNIT_FAMILIES.items():
            combo = make_combo([(unit.label, unit.key) for unit in DISPLAY_UNITS.values()
                                if unit.family == family_key], family.default)
            combo.setToolTip(family_tips[family_key])
            self.unit_combos[family_key] = combo
            form.addRow(family.title.replace(" (no antenna factor)", ""), combo)
        self.unit_combo = self.unit_combos["S"]          # 0.0.3 name: the power-density unit
        self.time_mode_combo = make_combo([(mode, mode) for mode in TIME_DISPLAY_MODES], "power density")
        self.time_mode_combo.setToolTip("E and H of power-density logs use the plane-wave relations with Z0; "
                                        "a mode that cannot be derived shows the analysed quantity")
        self.rf_mode_combo = make_combo([(mode, mode) for mode in RF_LEVEL_MODES], "power density")
        self.rf_mode_combo.setToolTip("Spectrogram levels of power-density inputs as power density or as the "
                                      "field of the equivalent plane wave")
        self.spectrum_scale_combo = make_combo([(s, s) for s in SPECTRUM_SCALES], "log")
        self.spectrum_scale_combo.setToolTip("log/linear for linear units; dB units are always drawn on a "
                                             "linear axis")
        form.addRow("Time plot shows", self.time_mode_combo)
        form.addRow("RF levels as", self.rf_mode_combo)
        form.addRow("Spectrum y axis", self.spectrum_scale_combo)
        layout.addWidget(display_box)
        for combo in list(self.unit_combos.values()) + [self.time_mode_combo, self.rf_mode_combo,
                                                        self.spectrum_scale_combo]:
            combo.currentIndexChanged.connect(lambda _index: self.displayChanged.emit())

        # -- Veusz in several units (0.0.4) --------------------------------------------------------------
        veusz_box = QtWidgets.QGroupBox("Veusz documents in several units")
        veusz_layout = QtWidgets.QVBoxLayout(veusz_box)
        self.veusz_units_list = QtWidgets.QListWidget()
        self.veusz_units_list.setToolTip("Tick the units to add to the Veusz output, besides the display "
                                         "units above (pages in other families are left out)")
        for unit in DISPLAY_UNITS.values():
            item = QtWidgets.QListWidgetItem(f"{UNIT_FAMILIES[unit.family].title.split(' (')[0]}: {unit.label}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, unit.key)
            item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.veusz_units_list.addItem(item)
        self.veusz_units_list.setMaximumHeight(150)
        self.veusz_layout_combo = make_combo([("one document, a section per unit", "sections"),
                                              ("one document per unit", "files")], "sections")
        self.veusz_layout_combo.setToolTip("Sections are bookmarked per unit in the rendered PDF; files are "
                                           "<stem>_envelope_fft_<unit>.vszh5")
        veusz_layout.addWidget(QtWidgets.QLabel("Extra units"))
        veusz_layout.addWidget(self.veusz_units_list)
        layout_row = QtWidgets.QHBoxLayout()
        layout_row.addWidget(QtWidgets.QLabel("Layout"))
        layout_row.addWidget(self.veusz_layout_combo, 1)
        veusz_layout.addLayout(layout_row)
        layout.addWidget(veusz_box)

        # -- actions --------------------------------------------------------------------------------
        action_row = QtWidgets.QHBoxLayout()
        self.inspect_button = QtWidgets.QPushButton("Inspect")
        self.inspect_button.setToolTip("Show how the selected input is read (Ctrl+I)")
        self.analyse_button = QtWidgets.QPushButton("Analyse")
        self.analyse_button.setToolTip("Analyse every input (F5)")
        self.analyse_button.setDefault(True)
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setEnabled(False)
        for button in (self.inspect_button, self.analyse_button, self.stop_button):
            action_row.addWidget(button)
        layout.addLayout(action_row)
        layout.addStretch(1)
        self.setWidget(body)

        self.add_files_button.clicked.connect(self.browse_files)
        self.add_folder_button.clicked.connect(self.browse_folder)
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button.clicked.connect(self.input_list.clear)
        self.out_button.clicked.connect(self.browse_output)
        self.inspect_button.clicked.connect(self.inspectRequested.emit)
        self.analyse_button.clicked.connect(self.analyseRequested.emit)
        self.stop_button.clicked.connect(self.stopRequested.emit)
        self.last_folder = str(Path.home())

    # -- inputs ---------------------------------------------------------------------------------
    def add_paths(self, paths: Iterable[str]) -> None:
        """Append paths that are not listed yet."""
        listed = set(self.input_paths())
        for path in paths:
            if path and path not in listed:
                self.input_list.addItem(str(path))
                listed.add(path)
                self.last_folder = str(Path(path).parent)

    def input_paths(self) -> list[str]:
        """All listed inputs."""
        return [self.input_list.item(i).text() for i in range(self.input_list.count())]

    def selected_paths(self) -> list[str]:
        """Selected inputs (all when none is selected)."""
        selected = [item.text() for item in self.input_list.selectedItems()]
        return selected or self.input_paths()

    def _input_menu(self, position: Any) -> None:
        """Right-click menu of the input list."""
        menu = QtWidgets.QMenu(self)
        menu.addAction("Inspect", self.inspectRequested.emit)
        menu.addAction("Remove", self.remove_selected)
        menu.addAction("Open containing folder", self._open_input_folder)
        menu.addSeparator()
        menu.addAction("Clear list", self.input_list.clear)
        menu.exec(self.input_list.mapToGlobal(position))

    def _open_input_folder(self) -> None:
        paths = self.selected_paths()
        if paths:
            folder = Path(paths[0]) if Path(paths[0]).is_dir() else Path(paths[0]).parent
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    def browse_files(self) -> None:
        """File dialog for exports and SignalShark files."""
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add measurement files", self.last_folder,
            "Measurement files (*.csv *.txt *.TXT *.xlsx *.xls *.h5 *.hdf5);;All files (*)")
        self.add_paths(paths)

    def browse_folder(self) -> None:
        """Folder dialog (EHP-50 TS auto-save folders)."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Add an EHP-50 TS folder", self.last_folder)
        if folder:
            self.add_paths([folder])

    def browse_output(self) -> None:
        """Folder dialog for the output folder."""
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Output folder", self.last_folder)
        if folder:
            self.out_edit.setText(folder)

    def remove_selected(self) -> None:
        """Remove the selected inputs."""
        for item in self.input_list.selectedItems():
            self.input_list.takeItem(self.input_list.row(item))

    # -- options ----------------------------------------------------------------------------------
    def options(self) -> Options:
        """The analysis options set in the panel."""
        def text_or_none(edit: Any) -> str | None:
            return edit.text().strip() or None

        return Options(
            probe=self.probe_combo.currentData() or None, source=self.source_combo.currentData(),
            fs=self.fs_spin.value() or None, t_int=(self.t_int_spin.value() / 1e3) or None,
            quantity=self.quantity_combo.currentData(), window=self.window_combo.currentData(),
            nperseg=self.nperseg_spin.value() or None,
            zoom=(self.zoom_low.value(), self.zoom_high.value()) if self.zoom_check.isChecked() else None,
            zoom_points=self.zoom_points_spin.value(), lomb=self.lomb_combo.currentData(),
            correct_probe=self.correct_check.isChecked(), max_boost_db=self.boost_spin.value(),
            rf_channels=self.channels_edit.text().strip() or "auto:3",
            antenna_factor_db=self.af_spin.value() if self.af_check.isChecked() else None,
            z0=self.z0_spin.value(), out=text_or_none(self.out_edit), gpu=self.gpu_check.isChecked(),
            render=self.render_check.isChecked(), pickle=self.pickle_check.isChecked(),
            time_col=text_or_none(self.time_col_edit), value_col=text_or_none(self.value_col_edit),
            unit=text_or_none(self.unit_edit), sep=text_or_none(self.sep_edit),
            decimal=text_or_none(self.decimal_edit), dayfirst=self.dayfirst_combo.currentData(),
            h5_level=text_or_none(self.h5_level_edit), h5_freq=text_or_none(self.h5_freq_edit),
            h5_time=text_or_none(self.h5_time_edit), snr=self.snr_spin.value(),
            dyn_range_db=self.dyn_spin.value(), display_unit=selection_text(self.unit_selection()),
            time_display=self.time_mode_combo.currentData(), rf_level_display=self.rf_mode_combo.currentData(),
            veusz_units=",".join(self.veusz_units()), veusz_layout=self.veusz_layout_combo.currentData(),
            rbw_hz=self.rbw_spin.value() if self.rbw_check.isChecked() else None,
            enbw_factor=self.enbw_spin.value())

    def unit_selection(self) -> dict[str, str]:
        """Display unit per family, as chosen in the Units group."""
        return {family: combo.currentData() for family, combo in self.unit_combos.items()}

    def veusz_units(self) -> list[str]:
        """Keys of the units ticked for the Veusz documents."""
        items = (self.veusz_units_list.item(i) for i in range(self.veusz_units_list.count()))
        return [item.data(QtCore.Qt.ItemDataRole.UserRole) for item in items
                if item.checkState() == QtCore.Qt.CheckState.Checked]

    def set_veusz_units(self, keys: Iterable[str]) -> None:
        """Tick exactly the units ``keys`` in the Veusz list."""
        wanted = {lookup_display_unit(key).key for key in keys}
        for index in range(self.veusz_units_list.count()):
            item = self.veusz_units_list.item(index)
            item.setCheckState(QtCore.Qt.CheckState.Checked if item.data(QtCore.Qt.ItemDataRole.UserRole)
                               in wanted else QtCore.Qt.CheckState.Unchecked)

    def select_unit(self, key: str) -> None:
        """Choose ``key`` for its family (emits displayChanged when it changes)."""
        unit = lookup_display_unit(key)
        combo = self.unit_combos[unit.family]
        combo.setCurrentIndex(combo.findData(unit.key))

    def set_options(self, opts: Options) -> None:
        """Show ``opts`` in the panel (used when settings are loaded)."""
        def select(combo: Any, data: Any) -> None:
            index = combo.findData(data)
            if index >= 0:
                combo.setCurrentIndex(index)

        try:                               # any accepted spelling -> catalogue key
            spec = lookup_probe(opts.probe)
            probe_key = next(key for key, value in PROBES.items() if value is spec) if spec else ""
        except (ValueError, StopIteration):
            probe_key = ""
        select(self.probe_combo, probe_key)
        select(self.source_combo, opts.source)
        self.fs_spin.setValue(opts.fs or 0.0)
        self.t_int_spin.setValue((opts.t_int or 0.0) * 1e3)
        select(self.quantity_combo, opts.quantity)
        select(self.window_combo, opts.window)
        self.nperseg_spin.setValue(opts.nperseg or 0)
        self.zoom_check.setChecked(opts.zoom is not None)
        if opts.zoom:
            self.zoom_low.setValue(opts.zoom[0])
            self.zoom_high.setValue(opts.zoom[1])
        self.zoom_points_spin.setValue(opts.zoom_points)
        select(self.lomb_combo, opts.lomb)
        self.correct_check.setChecked(opts.correct_probe)
        self.boost_spin.setValue(opts.max_boost_db)
        self.channels_edit.setText(opts.rf_channels)
        self.af_check.setChecked(opts.antenna_factor_db is not None)
        self.af_spin.setValue(opts.antenna_factor_db or 0.0)
        self.rbw_check.setChecked(opts.rbw_hz is not None)
        if opts.rbw_hz:
            self.rbw_spin.setValue(opts.rbw_hz)
        self.enbw_spin.setValue(opts.enbw_factor)
        self.z0_spin.setValue(opts.z0)
        self.out_edit.setText(opts.out or "")
        self.gpu_check.setChecked(opts.gpu)
        self.render_check.setChecked(opts.render)
        self.pickle_check.setChecked(opts.pickle)
        for edit, value in ((self.time_col_edit, opts.time_col), (self.value_col_edit, opts.value_col),
                            (self.unit_edit, opts.unit), (self.sep_edit, opts.sep),
                            (self.decimal_edit, opts.decimal), (self.h5_level_edit, opts.h5_level),
                            (self.h5_freq_edit, opts.h5_freq), (self.h5_time_edit, opts.h5_time)):
            edit.setText(value or "")
        select(self.dayfirst_combo, opts.dayfirst)
        self.snr_spin.setValue(opts.snr)
        self.dyn_spin.setValue(opts.dyn_range_db)
        try:
            selection = unit_selection(opts.display_unit)
        except ValueError:
            selection = unit_selection(None)
        for family, combo in self.unit_combos.items():
            select(combo, selection[family])
        select(self.time_mode_combo, normalise_time_display(opts.time_display))
        select(self.rf_mode_combo, opts.rf_level_display)
        try:
            self.set_veusz_units(_split_units(opts.veusz_units))
        except ValueError:
            self.set_veusz_units([])
        select(self.veusz_layout_combo, opts.veusz_layout)

    def display(self) -> dict[str, Any]:
        """Display choices: units per family, time-plot quantity, RF levels, spectrum scale.

        "unit" (the power-density unit) is kept for 0.0.3 callers.
        """
        selection = self.unit_selection()
        return {"units": selection, "unit": selection["S"], "time_mode": self.time_mode_combo.currentData(),
                "rf_mode": self.rf_mode_combo.currentData(),
                "spectrum_scale": self.spectrum_scale_combo.currentData()}

    def set_busy(self, busy: bool) -> None:
        """Enable Stop while a task runs; the other actions otherwise."""
        self.inspect_button.setEnabled(not busy)
        self.analyse_button.setEnabled(not busy)
        self.stop_button.setEnabled(busy)


# %% ===========================================================================
#    GUI: RESULTS VIEW (plots, peaks, summary, inspect, verification)
# =============================================================================
class ResultsView(QtWidgets.QWidget):
    """Tabs showing one selected result in the chosen display units.

    The result selector lists every analysed series: a probe log, or the
    channels of a spectrogram (whose overview images are on the RF tabs).
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        selector_row = QtWidgets.QHBoxLayout()
        selector_row.addWidget(QtWidgets.QLabel("Result"))
        self.selector = QtWidgets.QComboBox()
        self.selector.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToContents)
        selector_row.addWidget(self.selector, 1)
        layout.addLayout(selector_row)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, 1)

        self.time_plot = PlotPanel(date_axis=True)
        self.amplitude_plot = PlotPanel()
        self.welch_plot = PlotPanel()
        self.zoom_plot = PlotPanel()
        self.lomb_plot = PlotPanel()
        self.probe_plot = PlotPanel()
        self.envelope_image = ImagePanel()
        self.rf_spectrum_plot = PlotPanel()
        self.rf_image = ImagePanel()
        self.modulation_image = ImagePanel()
        self.peaks_table = QtWidgets.QTableWidget(0, 6)
        self.peaks_table.setHorizontalHeaderLabels(["Frequency (Hz)", "Amplitude", "SNR (dB)",
                                                    "CZT frequency (Hz)", "CZT amplitude", "Period (s)"])
        self.families_table = QtWidgets.QTableWidget(0, 5)
        self.families_table.setHorizontalHeaderLabels(["f0 (Hz)", "Period (s)", "Rate (rpm)",
                                                       "Harmonics", "Members"])
        for table in (self.peaks_table, self.families_table):
            table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
        peaks_page = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        peaks_page.addWidget(self.peaks_table)
        peaks_page.addWidget(self.families_table)
        self.summary_text = QtWidgets.QPlainTextEdit()
        self.inspect_text = QtWidgets.QPlainTextEdit()
        for text in (self.summary_text, self.inspect_text):
            text.setReadOnly(True)
            text.setFont(monospace_font())
        self.verify_table = QtWidgets.QTableWidget(0, 6)
        self.verify_table.setHorizontalHeaderLabels(["Result", "Group", "Method", "Check", "Measured", "Limit"])
        self.verify_table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.verify_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verify_table.setAlternatingRowColors(True)

        for widget, title in ((self.time_plot, "Time"), (self.amplitude_plot, "Amplitude spectrum"),
                              (self.welch_plot, "Welch PSD"), (self.zoom_plot, "Chirp-Z zoom"),
                              (self.lomb_plot, "Lomb-Scargle"), (self.probe_plot, "Probe model"),
                              (self.envelope_image, "Envelope spectrogram"),
                              (self.rf_spectrum_plot, "RF spectrum"), (self.rf_image, "RF spectrogram"),
                              (self.modulation_image, "Modulation map"), (peaks_page, "Peaks and families"),
                              (self.summary_text, "Summary"), (self.inspect_text, "Inspect"),
                              (self.verify_table, "Verification")):
            self.tabs.addTab(widget, title)
        self.entries: list[dict[str, Any]] = []
        self.display_settings: dict[str, Any] = {"units": unit_selection(None), "unit": "W/m2",
                                                 "time_mode": "power density", "rf_mode": "power density",
                                                 "spectrum_scale": "log"}
        self.selector.currentIndexChanged.connect(lambda _i: self.render())
        self.clear_all()

    # -- bookkeeping ---------------------------------------------------------------------------------
    def panels(self) -> list[Any]:
        """Every plot and image panel (for theming)."""
        return [self.time_plot, self.amplitude_plot, self.welch_plot, self.zoom_plot, self.lomb_plot,
                self.probe_plot, self.envelope_image, self.rf_spectrum_plot, self.rf_image,
                self.modulation_image]

    def clear_all(self) -> None:
        """Forget every result."""
        self.entries.clear()
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.blockSignals(False)
        for panel in self.panels():
            panel.clear("Add inputs on the left and press Analyse (F5).")
        self.peaks_table.setRowCount(0)
        self.families_table.setRowCount(0)
        self.summary_text.clear()

    def add_result(self, path: str, result: Any, written: Sequence[Path]) -> None:
        """Register a finished analysis and show it."""
        stem = Path(path).name
        if isinstance(result, SpectrogramResult):
            if not result.channels:
                self.entries.append({"label": f"{stem}: overview", "parent": result, "series": None,
                                     "written": written, "path": path})
            for channel in result.channels:
                self.entries.append({"label": f"{stem}: {channel.name.replace(result.name + '_', '')}",
                                     "parent": result, "series": channel, "written": written, "path": path})
        else:
            self.entries.append({"label": stem, "parent": result, "series": result, "written": written,
                                 "path": path})
        self.selector.addItems([entry["label"] for entry in self.entries[self.selector.count():]])
        self.selector.setCurrentIndex(self.selector.count() - 1)

    def current_entry(self) -> dict[str, Any] | None:
        """The selected entry, or None."""
        index = self.selector.currentIndex()
        return self.entries[index] if 0 <= index < len(self.entries) else None

    def set_display(self, display: dict[str, Any]) -> None:
        """New display choices: re-plot."""
        self.display_settings = dict(display)
        self.display_settings.setdefault("units", unit_selection(display.get("unit")))
        self.render()

    def view(self) -> UnitView:
        """The current display choices as a UnitView (also used to re-write Veusz files)."""
        return UnitView(dict(self.display_settings["units"]),
                        normalise_time_display(self.display_settings.get("time_mode")),
                        self.display_settings.get("rf_mode", "power density"))

    # -- drawing -----------------------------------------------------------------------------------------
    def render(self) -> None:
        """Draw the selected entry in the current display units."""
        entry = self.current_entry()
        if entry is None:
            return
        series: SeriesResult | None = entry["series"]
        parent = entry["parent"]
        if series is not None:
            self._render_series(series)
        else:
            for panel in (self.time_plot, self.amplitude_plot, self.welch_plot, self.zoom_plot,
                          self.lomb_plot, self.probe_plot, self.envelope_image):
                panel.clear("Too few spectra in time for an envelope analysis.")
        if isinstance(parent, SpectrogramResult):
            self._render_spectrogram(parent)
        else:
            for panel in (self.rf_spectrum_plot, self.rf_image, self.modulation_image):
                panel.clear("Only for spectrogram inputs (SignalShark, EHP-50 TS folders).")
        view = self.view()
        text_lines = summary_lines(parent, view)
        if isinstance(parent, SpectrogramResult) and series is not None:
            text_lines += ["", f"Selected channel: {series.name}", ""] + summary_lines(series, view)
        summary = _summary_spectrogram(parent) if isinstance(parent, SpectrogramResult) else _summary_series(parent)
        files = "\n".join(f"  {f}" for f in entry["written"]) or "  (no files written)"
        self.summary_text.setPlainText("\n".join(text_lines) + "\n\nFiles written:\n" + files
                                       + "\n\nSummary file content (SI units):\n"
                                       + json.dumps(_jsonable(summary), indent=2))

    def _render_series(self, result: SeriesResult) -> None:
        view = self.view()
        unit = unit_for_quantity(result.quantity_unit, view.selection)
        quantity_label = display_label(unit, result.quantity_unit)
        spectrum_scale = self.display_settings["spectrum_scale"]
        level_unit = unit is not None and unit.is_level            # dB values: linear axis
        # -- time: power density, E, H, the logged field or the analysed quantity
        if result.t0_veusz is not None:
            x_time = result.time_s + result.t0_veusz + VEUSZ_TO_UNIX_S
            x_label = f"Instrument clock (start {result.t0_text})"
        else:
            x_time = result.time_s
            x_label = "Time since start (s)"
        self.time_plot.clear()
        y_time, y_label, _ = time_display_values(result, view.time_display, view.selection)
        # a date axis only with a wall-clock start; plain seconds would read as 1970
        self.time_plot.use_date_axis(result.t0_veusz is not None)
        n_time = min(len(x_time), len(y_time))
        self.time_plot.add_curve(x_time[:n_time], y_time[:n_time], "", 0, width=1.0)
        self.time_plot.set_labels(f"{result.name}: {_lower_first(y_label.split(' (')[0])} vs time", x_label,
                                  y_label)
        # -- amplitude spectrum
        self.amplitude_plot.clear()
        traces = [(result.fft_amplitude, "FFT amplitude", "solid")]
        if result.fft_amplitude_corrected is not None:
            traces.append((result.fft_amplitude_corrected, "probe-corrected", "dashed"))
        traces += [(a, f"axis {k}", "dotted") for k, a in result.axis_amplitudes.items()]
        reference = float(np.nanmax(result.fft_amplitude[1:])) if result.fft_amplitude.size > 1 else 1.0
        for index, (values, name, style) in enumerate(traces):
            y_values = self._spectrum_values(values, reference, spectrum_scale, unit)
            self.amplitude_plot.add_curve(result.fft_freq_hz, y_values, name, index, style)
        if result.peaks:
            peak_f = np.array([p["f_hz"] for p in result.peaks])
            peak_a = np.array([p["amp"] for p in result.peaks])
            self.amplitude_plot.add_curve(peak_f, self._spectrum_values(peak_a, reference, spectrum_scale, unit),
                                          "peaks", 4, "none", symbol="t")
        relative = spectrum_scale == SPECTRUM_SCALES[2]
        y_axis = "dB rel. max (20 log10)" if relative else f"Amplitude ({quantity_label})"
        self.amplitude_plot.set_labels(f"{result.name}: envelope amplitude spectrum",
                                       "Envelope (modulation) frequency (Hz)", y_axis)
        self.amplitude_plot.set_log_y(spectrum_scale == "log" and not level_unit)
        # -- Welch PSD (10 log10 of (unit)^2/Hz)
        self.welch_plot.clear()
        welch_db, psd_label = psd_to_display_db(result.welch_psd, unit, result.quantity_unit)
        self.welch_plot.add_curve(result.welch_freq_hz, welch_db, "Welch", 2)
        self.welch_plot.set_labels(f"Welch PSD: {result.welch_segments} segments of {result.welch_nperseg}",
                                   "Envelope frequency (Hz)", f"PSD ({psd_label})")
        # -- chirp-Z zoom
        self.zoom_plot.clear()
        if result.zoom_freq_hz is not None:
            in_band = (result.fft_freq_hz >= result.zoom_freq_hz[0]) & (result.fft_freq_hz <= result.zoom_freq_hz[-1])
            self.zoom_plot.add_curve(result.zoom_freq_hz, to_display(result.zoom_amplitude, unit), "chirp-Z (dense)", 0)
            self.zoom_plot.add_curve(result.fft_freq_hz[in_band], to_display(result.fft_amplitude[in_band], unit),
                                     "FFT bins", 1, "none", symbol="o")
            self.zoom_plot.set_labels("Chirp-Z zoom", "Envelope frequency (Hz)", f"Amplitude ({quantity_label})")
        else:
            self.zoom_plot.clear("No zoom: no peak found and no fixed band set.")
        # -- Lomb-Scargle
        self.lomb_plot.clear()
        if result.lomb_freq_hz is not None:
            lomb_shown = to_display(result.lomb_amplitude, unit)
            fft_shown = to_display(result.fft_amplitude, unit)
            if not level_unit:
                lomb_shown, fft_shown = _finite_positive(lomb_shown), _finite_positive(fft_shown)
            self.lomb_plot.add_curve(result.lomb_freq_hz, lomb_shown, "Lomb-Scargle", 0)
            self.lomb_plot.add_curve(result.fft_freq_hz, fft_shown, "FFT (uniform grid)", 1, "dashed")
            self.lomb_plot.set_labels("Lomb-Scargle (raw time stamps)", "Envelope frequency (Hz)",
                                      f"Amplitude ({quantity_label})")
            self.lomb_plot.set_log_y(not level_unit)
        else:
            self.lomb_plot.clear("Not computed: the log has no gaps or jitter (set Lomb-Scargle to 'on').")
        # -- probe model
        self.probe_plot.clear()
        if result.probe_response is not None:
            self.probe_plot.add_curve(result.fft_freq_hz, 20 * np.log10(np.maximum(result.probe_response, 1e-6)),
                                      "|H| = |sinc(f T)|", 0)
            self.probe_plot.set_labels(f"Probe averaging model, T = {result.integration_time_s * 1e3:.4g} ms",
                                       "Envelope frequency (Hz)", "20 log10 |H| (dB)")
        else:
            self.probe_plot.clear("No probe selected and no integration time set.")
        # -- envelope spectrogram (PSD: + 20 log10(factor))
        if result.spectrogram_db is not None:
            image = result.spectrogram_db + psd_db_offset(unit)
            peak_db = float(np.nanmax(image))
            self.envelope_image.set_image(image, result.spectrogram_time_s, result.spectrogram_freq_hz,
                                          peak_db - 60, peak_db, "Envelope spectrogram", "Time (s)",
                                          "Envelope frequency (Hz)", f"PSD ({psd_label})")
        else:
            self.envelope_image.clear("Log too short for a spectrogram (needs 16 Welch segments).")
        # -- peaks and families
        self.peaks_table.setRowCount(len(result.peaks))
        self.peaks_table.setHorizontalHeaderItem(1, QtWidgets.QTableWidgetItem(f"Amplitude ({quantity_label})"))
        self.peaks_table.setHorizontalHeaderItem(4, QtWidgets.QTableWidgetItem(f"CZT amplitude ({quantity_label})"))
        for row, peak in enumerate(result.peaks):
            cells = [f"{peak['f_hz']:.6g}", f"{_shown(peak['amp'], unit):.6g}", f"{peak['snr_db']:.1f}",
                     f"{peak['f_hz_czt']:.6g}" if "f_hz_czt" in peak else "",
                     f"{_shown(peak['amp_czt'], unit):.6g}" if "amp_czt" in peak else "",
                     f"{1.0 / peak['f_hz']:.6g}" if peak["f_hz"] > 0 else ""]
            for column, text in enumerate(cells):
                self.peaks_table.setItem(row, column, QtWidgets.QTableWidgetItem(text))
        self.families_table.setRowCount(len(result.families))
        for row, family in enumerate(result.families):
            cells = [f"{family['f0_hz']:.6g}", f"{family['period_s']:.6g}", f"{family['rpm']:.4g}",
                     ", ".join(map(str, family["harmonics"])), str(family["n_members"])]
            for column, text in enumerate(cells):
                self.families_table.setItem(row, column, QtWidgets.QTableWidgetItem(text))

    @staticmethod
    def _spectrum_values(values: np.ndarray, reference: float, spectrum_scale: str,
                         unit: DisplayUnit | None = None) -> np.ndarray:
        """Amplitudes for the chosen y axis: relative dB, or the display unit (log axes need > 0)."""
        if spectrum_scale == SPECTRUM_SCALES[2]:
            return 20 * np.log10(np.maximum(np.asarray(values, float), reference * 1e-12) / reference)
        shown = to_display(values, unit)
        if spectrum_scale == "log" and not (unit is not None and unit.is_level):
            return _finite_positive(shown)
        return shown

    def _render_spectrogram(self, result: SpectrogramResult) -> None:
        view = self.view()
        divisor, freq_label = _freq_unit(float(np.nanmax(result.freq_hz)))
        mean_shown, level_label = rf_level_display(result.mean_level_db, result.power_unit, view.selection,
                                                   view.rf_level_display, result.z0_ohm)
        max_shown, _ = rf_level_display(result.max_level_db, result.power_unit, view.selection,
                                        view.rf_level_display, result.z0_ohm)
        self.rf_spectrum_plot.clear()
        self.rf_spectrum_plot.add_curve(result.freq_hz / divisor, mean_shown, "mean", 0)
        self.rf_spectrum_plot.add_curve(result.freq_hz / divisor, max_shown, "max hold", 1, "dashed")
        self.rf_spectrum_plot.set_labels(f"{result.name}: mean and max-hold spectrum",
                                         f"Frequency ({freq_label})", f"Level ({level_label})")
        image, _ = rf_level_display(result.level_db_image, result.power_unit, view.selection,
                                    view.rf_level_display, result.z0_ohm)
        peak_db = float(np.nanmax(image))
        self.rf_image.set_image(image, result.image_freq_hz / divisor, result.image_time_s, peak_db - 60, peak_db,
                                f"{result.name}: spectrogram", f"Frequency ({freq_label})", "Time (s)",
                                level_label)
        if result.modulation_db_image.shape[0] > 1:
            self.modulation_image.set_image(result.modulation_db_image, result.modulation_image_freq_hz / divisor,
                                            result.modulation_freq_hz, -60.0, 0.0,
                                            f"Envelope spectrum per bin (spectra at {result.spectra_rate_hz:.4g} Hz)",
                                            f"Frequency ({freq_label})", "Envelope frequency (Hz)",
                                            "dB rel. max (20 log10)")
        else:
            self.modulation_image.clear("Too few spectra for a modulation map.")

    def show_verification(self, checks: Sequence[Check]) -> None:
        """Fill the Verification tab."""
        self.verify_table.setRowCount(len(checks))
        for row, check in enumerate(checks):
            cells = ["PASS" if check.passed else "FAIL", check.group, check.method, check.name,
                     check.measured, check.limit]
            for column, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                if column == 0:
                    item.setForeground(QtGui.QColor("#2e7d32" if check.passed else "#c62828"))
                self.verify_table.setItem(row, column, item)
        self.verify_table.resizeColumnsToContents()
        self.tabs.setCurrentWidget(self.verify_table)

    def apply_theme(self, dark: bool) -> None:
        """Recolour every plot."""
        for panel in self.panels():
            panel.apply_theme(dark)


# %% ===========================================================================
#    GUI: LIVE PANEL (follow a growing file)
# =============================================================================
class LivePanel(QtWidgets.QWidget):
    """Follow a file another program appends to; update the spectra periodically.

    Uses LiveTail (complete new lines), RingBuffer (fixed RAM, every sample
    also logged to <file>.live.f64) and live_update (amplitude and Welch).
    """

    messageLogged = QtCore.Signal(str)

    def __init__(self, options_provider: Any, display_provider: Any, parent: Any = None) -> None:
        super().__init__(parent)
        self.options_provider = options_provider
        self.display_provider = display_provider
        self.tail: LiveTail | None = None
        self.ring: RingBuffer | None = None
        self.backend = Backend()
        self.last_update: dict[str, Any] | None = None
        self.last_snapshot: list[Path] = []
        layout = QtWidgets.QVBoxLayout(self)
        controls = QtWidgets.QHBoxLayout()
        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setPlaceholderText("file being written by the instrument software")
        self.browse_button = QtWidgets.QPushButton("...")
        self.browse_button.setMaximumWidth(32)
        self.window_spin = make_double_spin(2.0, 86400.0, 120.0, 1, 10.0, " s window")
        self.update_spin = make_double_spin(0.1, 60.0, 1.0, 1, 0.5, " s update")
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.snapshot_button = QtWidgets.QPushButton("Save snapshot")
        self.clear_button = QtWidgets.QPushButton("Clear buffer")
        self.clear_button.setToolTip("Empty the RAM ring buffer and run flush_memory(); "
                                     "the .live.f64 disk log keeps every sample")
        self.stop_button.setEnabled(False)
        for widget in (self.path_edit, self.browse_button, self.window_spin, self.update_spin,
                       self.start_button, self.stop_button, self.snapshot_button, self.clear_button):
            controls.addWidget(widget, 1 if widget is self.path_edit else 0)
        layout.addLayout(controls)
        self.time_plot = PlotPanel()
        self.amplitude_plot = PlotPanel()
        self.welch_plot = PlotPanel()
        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
        for panel in (self.time_plot, self.amplitude_plot, self.welch_plot):
            splitter.addWidget(panel)
        layout.addWidget(splitter, 1)
        self.status = QtWidgets.QLabel("Not running.")
        layout.addWidget(self.status)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.browse_button.clicked.connect(self._browse)
        self.start_button.clicked.connect(lambda: self.start(self.path_edit.text()))
        self.stop_button.clicked.connect(self.stop)
        self.snapshot_button.clicked.connect(self.save_snapshot)
        self.clear_button.clicked.connect(self.clear_buffer)

    def _browse(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "File to follow", self.path_edit.text())
        if path:
            self.path_edit.setText(path)

    def start(self, path: str, window_s: float | None = None, update_s: float | None = None) -> None:
        """Begin following ``path``."""
        if not path:
            self.status.setText("Choose a file to follow.")
            return
        if window_s:
            self.window_spin.setValue(window_s)
        if update_s:
            self.update_spin.setValue(update_s)
        self.path_edit.setText(path)
        opts = self.options_provider()
        try:
            self.tail = LiveTail(path, opts)
        except Exception as exc:  # noqa: BLE001 - e.g. file not there yet
            self.status.setText(f"Cannot follow {path}: {type(exc).__name__}: {exc}")
            return
        self.ring = _live_ring(path, opts, self.window_spin.value())
        self.backend = Backend(opts.gpu, opts.fft_workers)
        self.timer.start(int(self.update_spin.value() * 1000))
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.messageLogged.emit(f"live: following {path} (all samples also in {self.ring.spill_path.name})")
        self.tick()

    def stop(self) -> None:
        """Stop following (the disk log is kept)."""
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status.setText(f"Stopped. {self.ring.n if self.ring else 0} samples in the buffer.")

    def tick(self) -> None:
        """Read new rows, recompute the spectra and redraw."""
        if self.tail is None or self.ring is None:
            return
        opts = self.options_provider()
        self.ring.extend(*self.tail.poll())
        update = live_update(*self.ring.window(self.window_spin.value()), self.tail.unit, opts, self.backend)
        if not update:
            self.status.setText(f"Waiting for data ({self.ring.n} samples).")
            return
        self.last_update = update
        live_gui_state["last_update"] = update
        live_gui_state["samples"] = self.ring.n
        # Same unit control as the Analysis tab (0.0.4): time plot mode, unit per family
        display = self.display_provider()
        selection = display.get("units") or unit_selection(display.get("unit"))
        record = live_record(update)
        unit = unit_for_quantity(update["quantity_unit"], selection)
        label = display_label(unit, update["quantity_unit"])
        level_unit = unit is not None and unit.is_level
        y_time, y_label, _ = time_display_values(record, display.get("time_mode", "power density"), selection)
        self.time_plot.clear()
        n_time = min(len(update["time_s"]), len(y_time))
        self.time_plot.add_curve(update["time_s"][:n_time], y_time[:n_time], "", 0, width=1.0)
        self.time_plot.set_labels(f"{y_label.split(' (')[0]} vs time", "Time (s)", y_label)
        self.amplitude_plot.clear()
        positive = update["freq_hz"] > 0
        shown = to_display(update["amplitude"][positive], unit)
        self.amplitude_plot.add_curve(update["freq_hz"][positive],
                                      shown if level_unit else _finite_positive(shown), "amplitude", 1)
        self.amplitude_plot.set_labels("Envelope amplitude spectrum", "Envelope frequency (Hz)",
                                       f"Amplitude ({label})")
        self.amplitude_plot.set_log_y(not level_unit)
        self.welch_plot.clear()
        welch_db, psd_label = psd_to_display_db(update["welch_psd"], unit, update["quantity_unit"])
        self.welch_plot.add_curve(update["welch_freq_hz"], welch_db, "Welch", 2)
        self.welch_plot.set_labels("Welch PSD", "Envelope frequency (Hz)", f"PSD ({psd_label})")
        message = f"{self.ring.n} samples, fs {update['fs']:.4g} Hz"
        if update["families"]:
            family = update["families"][0]
            message += f" | f0 {family['f0_hz']:.4g} Hz = {family['rpm']:.4g} rpm"
        self.status.setText(message)

    def save_snapshot(self) -> None:
        """Analyse the current window fully and write the usual outputs."""
        if self.ring is None or self.tail is None:
            return
        window_times, window_values = self.ring.window(self.window_spin.value())
        if window_times.size < 32:
            self.status.setText("Too few samples for a snapshot.")
            return
        path = Path(self.path_edit.text())
        opts = self.options_provider()
        snapshot = TimeSeries(path.stem + "_live", window_times - window_times[0], window_values, self.tail.unit,
                              source="live")
        result = analyse_timeseries(snapshot, opts, self.backend)
        outdir = Path(opts.out) if opts.out else path.parent / f"{path.stem}_fft"
        written = write_outputs(result, outdir, opts)
        vszh5_files = [f for f in written if f.suffix == ".vszh5"]
        self.status.setText(f"Saved {', '.join(f.name for f in vszh5_files) if vszh5_files else outdir}")
        self.messageLogged.emit(f"live snapshot written to {outdir} (units {opts.display_unit}"
                                + (f"; Veusz also in {opts.veusz_units}, {opts.veusz_layout}" if opts.veusz_units
                                   else "") + ")")
        self.last_snapshot = written

    def clear_buffer(self) -> int:
        """Empty the RAM ring buffer and the plots, then collect garbage.

        Following continues if it was running (new rows refill the buffer);
        the disk log ``<file>.live.f64`` is untouched. Returns the number of
        objects the garbage collector freed.
        """
        held = self.ring.n if self.ring else 0
        if self.ring is not None:
            self.ring.clear()
        self.last_update = None
        live_gui_state["last_update"] = None
        live_gui_state["samples"] = 0
        for panel in self.panels():
            panel.clear("Buffer cleared.")
        n_collected = flush_memory()
        self.status.setText(f"Buffer cleared ({held} samples released; disk log kept).")
        self.messageLogged.emit(f"live: buffer cleared, {held} samples released, "
                                f"{n_collected} objects collected")
        return n_collected

    def panels(self) -> list[Any]:
        """The three plots (for theming)."""
        return [self.time_plot, self.amplitude_plot, self.welch_plot]


# %% ===========================================================================
#    GUI: ABOUT DIALOG CONTENT
# =============================================================================
def _module_version(module_name: str) -> str:
    """Version of an imported or importable module, or 'not installed'."""
    try:
        module = sys.modules.get(module_name) or __import__(module_name)
        return str(getattr(module, "__version__", "installed"))
    except Exception:  # noqa: BLE001
        return "not installed"


def build_about_content() -> dict[str, str]:
    """The three text blocks of the About dialog (as in the QuickSyn controller).

    Returns
    -------
    dict
        ``text``    rich text: name, version, author, company, email link,
                    licence and copyright.
        ``notice``  rich text: the GPL warranty and redistribution notice.
        ``runtime`` plain text for "Show Details": versions in use.
    """
    import html
    import platform

    escape = html.escape
    mail = escape(__email__, quote=True)
    text = (
        f"<h3>{escape(APP_NAME)}</h3>"
        f"<p>Version <b>{escape(__version__)}</b> (Semantic Versioning 2.0.0)</p>"
        f"<p>Envelope (modulation) spectra of broadband EMF probe logs (FieldMan / Narda-TSX, "
        f"NBM-550, EHP-50 TS) and SignalShark spectrograms: FFT, Welch, chirp-Z, "
        f"Lomb-Scargle.</p>"
        f"<table cellspacing='4'>"
        f"<tr><td><b>Author</b></td><td>{escape(__author__)}</td></tr>"
        f"<tr><td><b>Company</b></td><td>{escape(__company__)}</td></tr>"
        f"<tr><td><b>Email</b></td><td><a href='mailto:{mail}'>{mail}</a></td></tr>"
        f"<tr><td><b>Licence</b></td><td>GNU General Public License v3.0 or later "
        f"({escape(__license__)})</td></tr>"
        f"<tr><td><b>Copyright</b></td><td>{escape(__copyright__)}</td></tr>"
        f"</table>"
    )
    notice = (
        "<p>This program is free software: you can redistribute it and/or modify it under "
        "the terms of the GNU General Public License as published by the Free Software "
        "Foundation, either version 3 of the License, or (at your option) any later "
        "version.</p><p>This program is distributed in the hope that it will be useful, but "
        "WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or "
        "FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more "
        "details: <a href='https://www.gnu.org/licenses/gpl-3.0.html'>"
        "https://www.gnu.org/licenses/gpl-3.0.html</a>.</p>"
    )
    runtime_lines = [
        f"{APP_NAME} {__version__} (internal draft: tested on synthetic files)",
        f"Python {platform.python_version()} on {platform.platform()}",
        f"Qt abstraction layer: {QT_ABSTRACTION}",
        f"Qt binding: {QT_BINDING}",
        f"pyqtgraph {_module_version('pyqtgraph')}",
        f"NumPy {np.__version__}",
        f"SciPy {_module_version('scipy')}",
        f"pandas {pd.__version__ if pd is not None else 'not installed'}",
        f"h5py {h5py.__version__ if h5py is not None else 'not installed'}",
        f"vszh5_writer {vszh5_writer.__version__}",
        f"CuPy {_module_version('cupy') if 'cupy' in sys.modules else 'not loaded (only with GPU)'}",
    ]
    return {"text": text, "notice": notice, "runtime": "\n".join(runtime_lines)}


# %% ===========================================================================
#    GUI: MAIN WINDOW
# =============================================================================
class MainWindow(QtWidgets.QMainWindow):
    """Menu bar, settings dock (left), results/live tabs (centre), log dock (bottom)."""

    def __init__(self, theme: ThemeManager, inputs: Sequence[str] = (), opts: Options | None = None) -> None:
        super().__init__()
        self.theme = theme
        self.task: TaskThread | None = None
        self.settings_store = QtCore.QSettings(*SETTINGS_SCOPE)
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        screen = QtGui.QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else None
        width, height = 1400, 900
        if available is not None:          # never open larger than the screen
            width, height = min(width, available.width()), min(height, available.height() - 40)
        self.resize(width, height)

        # -- central tabs: results and live --------------------------------------------------
        self.results = ResultsView()
        self.settings = SettingsPanel()
        self.live = LivePanel(self.settings.options, self.settings.display)
        self.central_tabs = QtWidgets.QTabWidget()
        self.central_tabs.addTab(self.results, "Analysis")
        self.central_tabs.addTab(self.live, "Live")
        self.setCentralWidget(self.central_tabs)

        # -- docks: settings (left) and log (bottom) ------------------------------------------
        self.settings_dock = QtWidgets.QDockWidget("Settings", self)
        self.settings_dock.setObjectName("settings_dock")
        self.settings_dock.setWidget(self.settings)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.settings_dock)
        self.log_text = QtWidgets.QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(monospace_font())
        self.log_text.setMaximumBlockCount(5000)         # bounded memory
        self.log_dock = QtWidgets.QDockWidget("Log", self)
        self.log_dock.setObjectName("log_dock")
        self.log_dock.setWidget(self.log_text)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.resizeDocks([self.log_dock], [150], QtCore.Qt.Orientation.Vertical)
        self.cursor_label = QtWidgets.QLabel("")
        self.cursor_label.setMinimumWidth(380)
        self.statusBar().addPermanentWidget(self.cursor_label)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setMaximumWidth(220)
        self.progress.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress)
        self.setAcceptDrops(True)                          # drop files or folders anywhere
        self.recent_inputs: list[str] = []
        self.shortcut_actions: list[Any] = []

        self._build_menus()
        self._build_toolbar()
        for panel in self.results.panels() + self.live.panels():
            panel.cursorMoved.connect(self.cursor_label.setText)
        self.results.selector.currentIndexChanged.connect(lambda _i: self._update_title())
        self.settings.inspectRequested.connect(self.inspect_selected)
        self.settings.analyseRequested.connect(self.run_analysis)
        self.settings.stopRequested.connect(self.stop_task)
        self.settings.displayChanged.connect(self._display_changed)
        self.live.messageLogged.connect(self.log)
        self._restore_settings(opts)
        if inputs:
            self.settings.add_paths([str(p) for p in inputs])
        self.statusBar().showMessage("Ready. Add inputs and press Analyse (F5).")
        self.log(f"{APP_NAME} {__version__}; Qt layer {QT_ABSTRACTION}, binding {QT_BINDING}")

    # -- menus ------------------------------------------------------------------------------------------
    def _action(self, menu: Any, text: str, slot: Any, shortcut: Any = None, tip: str = "") -> Any:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip:
            action.setStatusTip(tip)
        action.triggered.connect(lambda _checked=False: slot())
        if menu is not None:
            menu.addAction(action)
        self.shortcut_actions.append(action)
        return action

    def _build_menus(self) -> None:
        """File, Edit, View, Analysis, Veusz and Help menus."""
        menubar = self.menuBar()
        # -- File
        file_menu = menubar.addMenu("&File")
        self.act_add_files = self._action(file_menu, "&Add files...", self.settings.browse_files,
                                          QtGui.QKeySequence.StandardKey.Open, "Add measurement files")
        self.act_add_folder = self._action(file_menu, "Add &folder (EHP-50 TS)...", self.settings.browse_folder,
                                           "Ctrl+Shift+O", "Add a folder of EHP-50 TS spectra")
        self.recent_menu = file_menu.addMenu("&Recent inputs")
        self._action(file_menu, "&Clear inputs", self.settings.input_list.clear)
        file_menu.addSeparator()
        self._action(file_menu, "&Export current plot (PNG, SVG, CSV)...", self.export_current_plot, "Ctrl+E")
        self._action(file_menu, "Export &peaks table (CSV)...", self.export_peaks_table)
        self._action(file_menu, "Save &log...", self.save_log)
        self._action(file_menu, "Open &output folder", self.open_output_folder)
        file_menu.addSeparator()
        self._action(file_menu, "&Load settings...", self.load_settings_file)
        self._action(file_menu, "&Save settings...", self.save_settings_file, QtGui.QKeySequence.StandardKey.Save)
        self._action(file_menu, "&Reset settings to defaults", self.reset_settings)
        file_menu.addSeparator()
        self._action(file_menu, "&Quit", self.close, QtGui.QKeySequence.StandardKey.Quit)
        # -- Edit
        edit_menu = menubar.addMenu("&Edit")
        self._action(edit_menu, "Copy &summary", self.copy_summary, "Ctrl+Shift+S")
        self._action(edit_menu, "Copy &peaks table", self.copy_peaks, "Ctrl+Shift+P")
        self._action(edit_menu, "Copy &log", lambda: QtWidgets.QApplication.clipboard().setText(
            self.log_text.toPlainText()))
        edit_menu.addSeparator()
        self._action(edit_menu, "C&lear log", self.log_text.clear)
        self._action(edit_menu, "Clear &results", self.results.clear_all)
        self._action(edit_menu, "&Free memory (results, live buffer, GC)", self.free_memory, None,
                     "Forget the results and the live buffer, then run flush_memory()")
        # -- View
        view_menu = menubar.addMenu("&View")
        theme_menu = view_menu.addMenu("&Theme")
        self._theme_group = QActionGroup(self)
        self._theme_group.setExclusive(True)
        self._theme_actions = {}
        for mode, caption in ((ThemeManager.SYSTEM, "&System default"), (ThemeManager.LIGHT, "&Light"),
                              (ThemeManager.DARK, "&Dark")):
            action = QAction(caption, self)
            action.setCheckable(True)
            action.setData(mode)
            action.triggered.connect(lambda _checked=False, m=mode: self.set_theme(m))
            self._theme_group.addAction(action)
            theme_menu.addAction(action)
            self._theme_actions[mode] = action
        # 0.0.4: a unit submenu per family, mirroring the Units group of the settings panel
        units_menu = view_menu.addMenu("&Units")
        self._family_unit_actions = {
            family: self._combo_menu(units_menu, UNIT_FAMILIES[family].title.replace(" (no antenna factor)", ""),
                                     combo) for family, combo in self.settings.unit_combos.items()}
        self._unit_actions = self._family_unit_actions["S"]           # 0.0.3 name
        self._time_actions = self._combo_menu(view_menu, "Time plot &shows", self.settings.time_mode_combo)
        self._rf_actions = self._combo_menu(view_menu, "&RF levels as", self.settings.rf_mode_combo)
        self._scale_actions = self._combo_menu(view_menu, "Spectrum &y axis", self.settings.spectrum_scale_combo)
        view_menu.addSeparator()
        self._action(view_menu, "&Auto-range current plot", self.auto_range_current, "Ctrl+0")
        view_menu.addSeparator()
        self.toolbar_toggle_menu = view_menu         # the toolbar toggle is added in _build_toolbar
        settings_toggle = self.settings_dock.toggleViewAction()
        settings_toggle.setText("&Settings panel")
        settings_toggle.setShortcut("Ctrl+Shift+E")
        view_menu.addAction(settings_toggle)
        log_toggle = self.log_dock.toggleViewAction()
        log_toggle.setText("&Log panel")
        log_toggle.setShortcut("Ctrl+Shift+L")
        view_menu.addAction(log_toggle)
        self._action(view_menu, "&Full screen", self.toggle_full_screen, "F11")
        # -- Analysis
        analysis_menu = menubar.addMenu("&Analysis")
        self.act_inspect = self._action(analysis_menu, "&Inspect selected input", self.inspect_selected, "Ctrl+I",
                                        "Show how the selected input is read")
        self.act_analyse = self._action(analysis_menu, "&Run analysis", self.run_analysis, "F5",
                                        "Analyse every listed input")
        self.act_stop = self._action(analysis_menu, "S&top after this file", self.stop_task, "Esc",
                                     "Stop the running analysis after the current file")
        analysis_menu.addSeparator()
        self.act_verify = self._action(analysis_menu, "&Verify transforms and units", self.run_verification,
                                       "Ctrl+Shift+V", "Every transform and unit conversion against analytic "
                                       "and reference results")
        self._action(analysis_menu, "Run &self-test", self.run_selftest)
        analysis_menu.addSeparator()
        self._action(analysis_menu, "&Live mode", lambda: self.central_tabs.setCurrentWidget(self.live), "Ctrl+L")
        # -- Veusz
        veusz_menu = menubar.addMenu("Veu&sz")
        self.act_veusz = self._action(veusz_menu, "&Open result .vszh5 in Veusz", self.open_in_veusz, "Ctrl+Shift+Z")
        self.act_rewrite = self._action(veusz_menu, "&Write .vszh5 again (current units)", self.rewrite_veusz,
                                        "Ctrl+Shift+W", "Re-write the selected result's Veusz document(s) in "
                                        "the current display and Veusz units, without re-analysing")
        self.act_render = self._action(veusz_menu, "&Render result to PDF/PNG", self.render_current)
        self._action(veusz_menu, "Open rendered &PDF", self.open_rendered_pdf)
        # -- Help
        help_menu = menubar.addMenu("&Help")
        self._action(help_menu, "User &manual (PDF)", self.open_manual, QtGui.QKeySequence.StandardKey.HelpContents)
        self._action(help_menu, "&Keyboard shortcuts", self.show_shortcuts)
        self._action(help_menu, "&Probe catalogue", self.show_probe_catalogue)
        help_menu.addSeparator()
        self._action(help_menu, f"&About {APP_NAME}", self.show_about)
        self._action(help_menu, "About &Qt", QtWidgets.QApplication.aboutQt)

    def _combo_menu(self, parent_menu: Any, title: str, combo: Any) -> dict[Any, Any]:
        """An exclusive submenu that mirrors a combo box of the settings panel."""
        menu = parent_menu.addMenu(title)
        group = QActionGroup(self)
        group.setExclusive(True)
        actions = {}
        for index in range(combo.count()):
            action = QAction(combo.itemText(index), self)
            action.setCheckable(True)
            data = combo.itemData(index)
            action.triggered.connect(lambda _checked=False, c=combo, d=data: c.setCurrentIndex(c.findData(d)))
            group.addAction(action)
            menu.addAction(action)
            actions[data] = action
        return actions

    def _build_toolbar(self) -> None:
        """Main toolbar: inputs, analysis, verification, export, Veusz, theme, unit."""
        toolbar = self.addToolBar("Main")
        toolbar.setObjectName("main_toolbar")
        toolbar.setMovable(True)
        toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextOnly)
        for action in (self.act_add_files, self.act_add_folder):
            toolbar.addAction(action)
        toolbar.addSeparator()
        for action in (self.act_inspect, self.act_analyse, self.act_stop):
            toolbar.addAction(action)
        toolbar.addSeparator()
        toolbar.addAction(self.act_verify)
        export_action = QAction("Export plot", self)
        export_action.triggered.connect(lambda _checked=False: self.export_current_plot())
        toolbar.addAction(export_action)
        toolbar.addAction(self.act_veusz)
        toolbar.addSeparator()
        theme_button = QAction("Light/Dark", self)
        theme_button.setToolTip("Switch between the light and dark theme")
        theme_button.triggered.connect(lambda _checked=False: self.set_theme(
            ThemeManager.LIGHT if self.theme.is_dark() else ThemeManager.DARK))
        toolbar.addAction(theme_button)
        toolbar.addSeparator()
        # 0.0.4: power-density and E-field units on the toolbar (all families: View > Units)
        self.toolbar_units: dict[str, Any] = {}
        for family, caption in (("S", " S "), ("E", " E ")):
            toolbar.addWidget(QtWidgets.QLabel(caption))
            combo = make_combo([(unit.label, unit.key) for unit in DISPLAY_UNITS.values() if unit.family == family],
                               UNIT_FAMILIES[family].default)
            combo.setToolTip(f"{UNIT_FAMILIES[family].title} unit of plots and tables (all units: View > Units)")
            combo.currentIndexChanged.connect(lambda _i, c=combo: self._select_unit(c.currentData()))
            toolbar.addWidget(combo)
            self.toolbar_units[family] = combo
        self.toolbar_unit = self.toolbar_units["S"]                # 0.0.3 name
        toggle = toolbar.toggleViewAction()
        toggle.setText("&Toolbar")
        self.toolbar_toggle_menu.insertAction(self.settings_dock.toggleViewAction(), toggle)
        self.act_stop.setEnabled(False)

    # -- theme and display ------------------------------------------------------------------------
    def set_theme(self, mode: str) -> None:
        """Apply a theme to the window and every plot; remember it."""
        self.theme.apply(mode)
        if mode in self._theme_actions:
            self._theme_actions[mode].setChecked(True)
        dark = mode == ThemeManager.DARK or (mode == ThemeManager.SYSTEM and self.theme.is_dark())
        self.results.apply_theme(dark)
        for panel in self.live.panels():
            panel.apply_theme(dark)
        self.settings_store.setValue("theme", mode)
        self.statusBar().showMessage(f"Theme set to {mode}.", 4000)

    def _select_unit(self, key: str) -> None:
        """Choose a display unit (any family) from the toolbar, a menu or a script."""
        try:
            self.settings.select_unit(key)                     # emits displayChanged
        except ValueError as exc:
            self.statusBar().showMessage(str(exc), 6000)

    def _display_changed(self) -> None:
        display = self.settings.display()
        for family, actions in self._family_unit_actions.items():
            if display["units"][family] in actions:
                actions[display["units"][family]].setChecked(True)
        for actions, key in ((self._time_actions, "time_mode"), (self._rf_actions, "rf_mode"),
                             (self._scale_actions, "spectrum_scale")):
            if display[key] in actions:
                actions[display[key]].setChecked(True)
        for family, combo in getattr(self, "toolbar_units", {}).items():
            if combo.currentData() != display["units"][family]:
                combo.blockSignals(True)
                combo.setCurrentIndex(combo.findData(display["units"][family]))
                combo.blockSignals(False)
        self.results.set_display(display)
        self.live.tick()

    # -- log -------------------------------------------------------------------------------------------
    def log(self, text: str) -> None:
        """Append a time-stamped line to the log panel."""
        stamp = _dt.datetime.now().strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"{stamp}  {text}")

    # -- tasks -----------------------------------------------------------------------------------------
    def _start_task(self, name: str, job: Any, on_result: Any, on_finished: Any) -> bool:
        if self.task is not None and self.task.isRunning():
            self.statusBar().showMessage("A task is still running.", 4000)
            return False
        self.task = TaskThread(name, job, self)
        self.task.messageLogged.connect(self.log)
        self.task.resultDelivered.connect(on_result)
        self.task.taskFinished.connect(on_finished)
        self.task.taskFailed.connect(self._task_failed)
        self.task.finished.connect(lambda: self._set_busy(False))
        self.task.finished.connect(lambda: self.progress.setVisible(False))
        self._set_busy(True)
        self.progress.setRange(0, 0)                       # busy indicator (set per task below)
        self.progress.setVisible(True)
        self.statusBar().showMessage(f"{name} ...")
        self.task.start()
        return True

    def _set_busy(self, busy: bool) -> None:
        """Enable Stop while a task runs, the starting actions otherwise."""
        self.settings.set_busy(busy)
        for action in (self.act_inspect, self.act_analyse, self.act_verify):
            action.setEnabled(not busy)
        self.act_stop.setEnabled(busy)

    def _task_failed(self, message: str) -> None:
        self.log(f"ERROR {message}")
        self.statusBar().showMessage(message, 10000)

    def stop_task(self) -> None:
        """Stop the running analysis after the current file."""
        if self.task is not None and self.task.isRunning():
            self.task.cancel()
            self.log("stop requested: finishing the current file")

    def run_analysis(self) -> None:
        """Analyse every listed input in the background."""
        paths = self.settings.input_paths()
        if not paths:
            self.statusBar().showMessage("Add input files or folders first (File > Add files).", 6000)
            return
        opts = self.settings.options()
        self.results.clear_all()
        self.results.set_display(self.settings.display())
        views = veusz_views(opts)
        extra = ", ".join(DISPLAY_UNITS[view.unit_key].label for view in views[1:])
        self.log(f"analysing {len(paths)} input(s); probe {opts.probe or '-'}, quantity {opts.quantity}, "
                 f"display units {opts.display_unit}; time plot {opts.time_display}"
                 + (f"; Veusz also in {extra} ({opts.veusz_layout})" if extra else ""))
        self.analysis_errors = 0
        if self._start_task("Analysis", analysis_job(paths, opts, self.settings.write_check.isChecked(),
                                                     self.settings.jobs_spin.value()),
                            self._analysis_result, self._analysis_finished):
            self.progress.setRange(0, len(paths))        # files done / files listed
            self.progress.setValue(0)
            self._remember_recent(paths)

    def _analysis_result(self, delivered: Any) -> None:
        path, result, written = delivered
        warnings_list = result.warnings
        for note in warnings_list:
            self.log(f"  note: {note}")
        if isinstance(result, SeriesResult) and result.families:
            family = result.families[0]
            self.log(f"  {Path(path).name}: f0 {family['f0_hz']:.5g} Hz = {family['rpm']:.4g} rpm")
        for file_path in written:
            if Path(file_path).suffix in (".vszh5", ".pdf"):
                self.log(f"  wrote {file_path}")
        self.results.add_result(path, result, written)
        self.central_tabs.setCurrentWidget(self.results)
        self.progress.setValue(self.progress.value() + 1)

    def _analysis_finished(self, count: Any) -> None:
        total = len(self.settings.input_paths())
        self.statusBar().showMessage(f"Analysis finished: {count} of {total} input(s).", 8000)
        self.log(f"analysis finished: {count} of {total} input(s)")
        if count == 0 and total:
            QtWidgets.QMessageBox.warning(self, APP_NAME, "No input could be analysed; the log says why. "
                                          "Use Inspect (Ctrl+I) to see how a file is read.")
        flush_memory()
        self._update_title()

    def inspect_selected(self) -> None:
        """Report how the selected input will be read (Inspect tab)."""
        paths = self.settings.selected_paths()
        if not paths:
            self.statusBar().showMessage("Add an input first.", 4000)
            return
        opts = self.settings.options()

        def job(report: Any, deliver: Any, is_cancelled: Any) -> str:
            return "\n\n".join(inspect_input(p, opts) for p in paths)

        self._start_task("Inspect", job, lambda _r: None, self._inspect_finished)

    def _inspect_finished(self, text: Any) -> None:
        self.results.inspect_text.setPlainText(str(text))
        self.results.tabs.setCurrentWidget(self.results.inspect_text)
        self.central_tabs.setCurrentWidget(self.results)
        self.statusBar().showMessage("Inspect finished.", 4000)

    def run_verification(self) -> None:
        """Run verify_transforms() and show the table."""
        def job(report: Any, deliver: Any, is_cancelled: Any) -> Any:
            return verify_transforms(verbose=False)

        self._start_task("Verification", job, lambda _r: None, self._verification_finished)

    def _verification_finished(self, value: Any) -> None:
        checks, passed = value
        self.results.show_verification(checks)
        self.central_tabs.setCurrentWidget(self.results)
        summary = f"verification {'PASSED' if passed else 'FAILED'}: {sum(c.passed for c in checks)}/{len(checks)}"
        self.log(summary)
        self.statusBar().showMessage(summary, 10000)

    def run_selftest(self) -> None:
        """Run the self-test; its report goes to the log."""
        def job(report: Any, deliver: Any, is_cancelled: Any) -> int:
            import contextlib
            import io
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = self_test(None)
            for line in buffer.getvalue().splitlines():
                report(line)
            return code

        self._start_task("Self-test", job, lambda _r: None,
                         lambda code: self.statusBar().showMessage(
                             "Self-test passed." if code == 0 else "Self-test FAILED (see the log).", 10000))

    # -- files, Veusz and help -----------------------------------------------------------------------
    def _current_vszh5(self) -> Path | None:
        entry = self.results.current_entry()
        if entry is None:
            return None
        return next((Path(f) for f in entry["written"] if Path(f).suffix == ".vszh5"), None)

    def open_output_folder(self) -> None:
        """Show the output folder of the selected result."""
        target = self._current_vszh5()
        folder = target.parent if target else Path(self.settings.out_edit.text() or self.settings.last_folder)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(folder)))

    def open_in_veusz(self) -> None:
        """Open the selected result's .vszh5 in Veusz."""
        target = self._current_vszh5()
        if target is None:
            self.statusBar().showMessage("No .vszh5 for this result (tick 'write .vszh5' and analyse).", 6000)
            return
        exe = vszh5_writer.find_veusz_exe()
        if not exe:
            self.statusBar().showMessage("Veusz not found: set VEUSZ_EXE to veusz.exe.", 8000)
            return
        import subprocess
        subprocess.Popen([exe, str(target)])
        self.log(f"opened {target.name} in Veusz")

    def render_current(self) -> None:
        """Render the selected result's .vszh5 document(s) to PDF (bookmarked) and PNG in the background.

        Unit-section titles of multi-unit documents are read back from the
        documents (render_vszh5), so the bookmarks are grouped per unit.
        """
        entry = self.results.current_entry()
        targets = [Path(f) for f in entry["written"] if Path(f).suffix == ".vszh5"] if entry else []
        if not targets:
            self.statusBar().showMessage("No .vszh5 for this result.", 6000)
            return
        parent = entry["parent"]
        channel_names = [c.name for c in parent.channels] if isinstance(parent, SpectrogramResult) else None

        def job(report: Any, deliver: Any, is_cancelled: Any) -> list[Path]:
            rendered: list[Path] = []
            for target in targets:
                report(f"rendering {target.name}")
                rendered += render_vszh5(target, channel_names)
            return rendered

        self._start_task("Render", job, lambda _r: None,
                         lambda files: self.log(f"rendered {len(files)} file(s) from {len(targets)} document(s)"))

    def rewrite_veusz(self) -> None:
        """Write the selected result's Veusz document(s) again in the current units (no re-analysis).

        Uses the display units, time-plot and RF-level modes and the Veusz
        extra units and layout of the settings panel; renders too when
        "render" is ticked. Works for results of the Analysis tab, whatever
        units they were first written in.
        """
        entry = self.results.current_entry()
        if entry is None:
            self.statusBar().showMessage("Analyse an input first.", 6000)
            return
        opts = self.settings.options()
        parent, path = entry["parent"], entry["path"]
        outdir = output_folder(path, opts)

        def job(report: Any, deliver: Any, is_cancelled: Any) -> list[Path]:
            documents = write_veusz(parent, outdir, opts)
            files = [document for document, _ in documents]
            for document, titles in documents:
                report(f"wrote {document} ({'; '.join(titles)})")
            if opts.render:
                files += render_documents(parent, documents)
            return files

        def finished(files: Any) -> None:
            kept = [f for f in entry["written"] if Path(f).suffix != ".vszh5"]
            for other in self.results.entries:            # every channel entry of this input
                if other["path"] == path:
                    other["written"] = kept + [f for f in files if Path(f) not in kept]
            self.results.render()
            self.statusBar().showMessage(f"Veusz written again: {len(files)} file(s).", 6000)

        self._start_task("Write Veusz", job, lambda _r: None, finished)

    def open_rendered_pdf(self) -> None:
        """Open the rendered PDF of the selected result."""
        target = self._current_vszh5()
        pdf = target.with_suffix(".pdf") if target else None
        if pdf is None or not pdf.exists():
            self.statusBar().showMessage("No rendered PDF yet (Veusz > Render result).", 6000)
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(pdf)))

    def open_manual(self) -> None:
        """Open docs/EMF_Envelope_FFT_Manual_v<version>.pdf."""
        manual = _SCRIPT_FOLDER / "docs" / f"EMF_Envelope_FFT_Manual_v{__version__}.pdf"
        if not manual.exists():
            self.statusBar().showMessage(f"Manual not found: {manual}", 8000)
            return
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(manual)))

    def build_about_box(self) -> Any:
        """The About dialog: author, version, GPL notice; runtime under Show Details."""
        content = build_about_content()
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle(f"About {APP_NAME}")
        box.setIcon(QtWidgets.QMessageBox.Icon.Information)
        box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        box.setText(content["text"])
        box.setInformativeText(content["notice"])
        box.setDetailedText(content["runtime"])
        box.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextBrowserInteraction)
        box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        return box

    def show_about(self) -> None:
        """Show the About dialog modally."""
        box = self.build_about_box()
        box.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        box.exec()

    # -- window conveniences -----------------------------------------------------------------------
    def _update_title(self) -> None:
        entry = self.results.current_entry()
        suffix = f" - {entry['label']}" if entry else ""
        self.setWindowTitle(f"{APP_NAME} v{__version__}{suffix}")

    def dragEnterEvent(self, event: Any) -> None:  # noqa: N802 - Qt API
        """Accept dragged files and folders."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:  # noqa: N802 - Qt API
        """Add dropped files and folders to the inputs."""
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        self.settings.add_paths(paths)
        self.log(f"added {len(paths)} input(s) by drag and drop")

    def _remember_recent(self, paths: Sequence[str]) -> None:
        for path in paths:
            if path in self.recent_inputs:
                self.recent_inputs.remove(path)
            self.recent_inputs.insert(0, path)
        del self.recent_inputs[12:]
        self._fill_recent_menu()

    def _fill_recent_menu(self) -> None:
        self.recent_menu.clear()
        for path in self.recent_inputs:
            action = self.recent_menu.addAction(path)
            action.triggered.connect(lambda _checked=False, p=path: self.settings.add_paths([p]))
        if self.recent_inputs:
            self.recent_menu.addSeparator()
            self.recent_menu.addAction("Clear recent list", lambda: (self.recent_inputs.clear(),
                                                                     self._fill_recent_menu()))
        self.recent_menu.setEnabled(bool(self.recent_inputs))

    def _current_panel(self) -> Any:
        """The plot or image panel in front, or None."""
        if self.central_tabs.currentWidget() is self.live:
            return self.live.amplitude_plot
        widget = self.results.tabs.currentWidget()
        return widget if isinstance(widget, (PlotPanel, ImagePanel)) else None

    def export_current_plot(self) -> None:
        """Save the plot in front as PNG, SVG or (curves) CSV."""
        panel = self._current_panel()
        if panel is None or panel.plot_widget is None:
            self.statusBar().showMessage("Bring a plot tab to the front first.", 5000)
            return
        entry = self.results.current_entry()
        stem = Path(entry["path"]).stem if entry else "plot"
        tab = self.results.tabs.tabText(self.results.tabs.currentIndex()).replace(" ", "_").lower()
        suggested = str(Path(self.settings.last_folder) / f"{stem}_{tab}.png")
        filters = "PNG image (*.png);;SVG drawing (*.svg);;Curve data (*.csv)"
        if isinstance(panel, ImagePanel):
            filters = "PNG image (*.png);;SVG drawing (*.svg)"
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export plot", suggested, filters)
        if path:
            try:
                panel.export(path)
                self.log(f"plot exported to {path}")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR export: {type(exc).__name__}: {exc}")

    def _peaks_rows(self) -> tuple[list[str], list[list[str]]]:
        table = self.results.peaks_table
        header = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
        rows = [[(table.item(r, c).text() if table.item(r, c) else "") for c in range(table.columnCount())]
                for r in range(table.rowCount())]
        return header, rows

    def export_peaks_table(self) -> None:
        """Save the peaks of the selected result as CSV (display unit)."""
        header, rows = self._peaks_rows()
        if not rows:
            self.statusBar().showMessage("No peaks to export.", 5000)
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export peaks", str(Path(self.settings.last_folder)
                                                        / "peaks.csv"), "CSV (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as file_handle:
                writer = csv.writer(file_handle)
                writer.writerow(header)
                writer.writerows(rows)
            self.log(f"peaks exported to {path}")

    def copy_peaks(self) -> None:
        """Peaks table to the clipboard (tab separated, pastes into a spreadsheet)."""
        header, rows = self._peaks_rows()
        QtWidgets.QApplication.clipboard().setText("\n".join("\t".join(r) for r in [header] + rows))
        self.statusBar().showMessage(f"{len(rows)} peak(s) copied.", 3000)

    def copy_summary(self) -> None:
        """Summary text to the clipboard."""
        QtWidgets.QApplication.clipboard().setText(self.results.summary_text.toPlainText())
        self.statusBar().showMessage("Summary copied.", 3000)

    def save_log(self) -> None:
        """Save the log panel to a text file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save log", str(Path(self.settings.last_folder)
                                                        / "emf_envelope_fft_log.txt"), "Text (*.txt)")
        if path:
            Path(path).write_text(self.log_text.toPlainText(), encoding="utf-8")

    def auto_range_current(self) -> None:
        """Show all the data of the plot in front again."""
        panel = self._current_panel()
        if panel is not None:
            panel.auto_range()

    def toggle_full_screen(self) -> None:
        """Full screen on and off (F11)."""
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def free_memory(self) -> int:
        """Release RAM: forget results, empty the live buffer, collect garbage.

        Output files already written stay on disk (use --pickle to keep a
        whole result object); a running live session keeps following.
        """
        n_results = len(self.results.entries)
        self.results.clear_all()
        n_collected = self.live.clear_buffer()
        n_collected += flush_memory()
        self.log(f"memory freed: {n_results} result(s) forgotten, live buffer emptied, "
                 f"{n_collected} objects collected")
        self.statusBar().showMessage("Memory freed.", 5000)
        self._update_title()
        return n_collected

    def reset_settings(self) -> None:
        """All options back to their defaults (inputs are kept)."""
        self.settings.set_options(Options())
        self.log("settings reset to defaults")

    def show_shortcuts(self) -> None:
        """A table of every menu command with a keyboard shortcut."""
        rows = [(a.text().replace("&", ""), a.shortcut().toString(QtGui.QKeySequence.SequenceFormat.NativeText))
                for a in self.shortcut_actions if not a.shortcut().isEmpty()]
        rows += [("Settings panel", "Ctrl+Shift+E"), ("Log panel", "Ctrl+Shift+L")]
        self._table_dialog("Keyboard shortcuts", ["Command", "Shortcut"], rows)

    def show_probe_catalogue(self) -> None:
        """The probe catalogue with the derived envelope limits."""
        rows = []
        for key, spec in PROBES.items():
            integration_s = spec.t_int_s or 1.0 / spec.fs_hz
            nyquist_hz = spec.fs_hz / 2
            response_db = 20 * math.log10(max(abs(float(np.sinc(nyquist_hz * integration_s))), 1e-12))
            rows.append((key, spec.part, f"{spec.f_lo_hz / 1e6:g} MHz - {spec.f_hi_hz / 1e9:g} GHz",
                         f"{spec.fs_hz:g}", f"{spec.t_int_s * 1e3:g}" if spec.t_int_s else "n/p (1/fs)",
                         f"{nyquist_hz:g}", f"{response_db:.1f}", f"{1 / integration_s:.4g}",
                         f"{spec.truerms_max_vm:g}" if spec.truerms_max_vm else "-", spec.axes, spec.ref))
        self._table_dialog("Probe catalogue (datasheet values and derived envelope limits)",
                           ["Probe", "Part", "RF range", "fs (Hz)", "T (ms)", "Nyquist (Hz)",
                            "|H(Nyquist)| (dB)", "1/T (Hz)", "True RMS to (V/m)", "Axes", "Ref."], rows)

    def _table_dialog(self, title: str, header: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        layout = QtWidgets.QVBoxLayout(dialog)
        table = QtWidgets.QTableWidget(len(rows), len(header))
        table.setHorizontalHeaderLabels(list(header))
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        for row_index, row in enumerate(rows):
            for column, text in enumerate(row):
                table.setItem(row_index, column, QtWidgets.QTableWidgetItem(str(text)))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(min(1200, 80 + table.horizontalHeader().length()), 120 + 30 * len(rows))
        dialog.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        self.last_dialog = dialog                          # kept for tests
        dialog.show()

    # -- settings persistence ----------------------------------------------------------------------
    def _restore_settings(self, opts: Options | None) -> None:
        stored = self.settings_store.value("options", "")
        if opts is None and stored:
            try:
                values = json.loads(stored)
                values = {k: v for k, v in values.items() if k in Options.__dataclass_fields__}
                if values.get("zoom"):
                    values["zoom"] = tuple(values["zoom"])
                opts = Options(**values)
            except Exception:  # noqa: BLE001 - ignore damaged settings
                opts = None
        self.settings.set_options(opts or Options())
        self.settings.last_folder = str(self.settings_store.value("last_folder", str(Path.home())))
        try:
            self.recent_inputs = [p for p in json.loads(self.settings_store.value("recent_inputs", "[]") or "[]")]
        except (TypeError, ValueError):
            self.recent_inputs = []
        self._fill_recent_menu()
        geometry = self.settings_store.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = self.settings_store.value("window_state")
        if state is not None:
            self.restoreState(state)
        self.set_theme(str(self.settings_store.value("theme", ThemeManager.SYSTEM)))
        self._display_changed()

    def _store_settings(self) -> None:
        self.settings_store.setValue("options", json.dumps(_jsonable(asdict(self.settings.options()))))
        self.settings_store.setValue("last_folder", self.settings.last_folder)
        self.settings_store.setValue("recent_inputs", json.dumps(self.recent_inputs))
        self.settings_store.setValue("geometry", self.saveGeometry())
        self.settings_store.setValue("window_state", self.saveState())

    def save_settings_file(self) -> None:
        """Save the options to a JSON file."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save settings", self.settings.last_folder,
                                                        "Settings (*.json)")
        if path:
            Path(path).write_text(json.dumps(_jsonable(asdict(self.settings.options())), indent=2), encoding="utf-8")
            self.log(f"settings saved to {path}")

    def load_settings_file(self) -> None:
        """Load options from a JSON file written by Save settings."""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load settings", self.settings.last_folder,
                                                        "Settings (*.json)")
        if not path:
            return
        values = {k: v for k, v in json.loads(Path(path).read_text(encoding="utf-8")).items()
                  if k in Options.__dataclass_fields__}
        if values.get("zoom"):
            values["zoom"] = tuple(values["zoom"])
        self.settings.set_options(Options(**values))
        self.log(f"settings loaded from {path}")

    def closeEvent(self, event: Any) -> None:  # noqa: N802 - Qt API
        """Stop live mode and background work, remember the settings."""
        if self.task is not None and self.task.isRunning() and self.isVisible() and not getattr(self, "force_close", False):
            answer = QtWidgets.QMessageBox.question(
                self, APP_NAME, "An analysis is still running. Stop it after the current file and quit?")
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        try:
            self.live.timer.stop()
            if self.task is not None and self.task.isRunning():
                self.task.cancel()
                self.task.wait(10000)
            self._store_settings()
        except Exception:  # noqa: BLE001 - never block the close
            pass
        super().closeEvent(event)


# %% ===========================================================================
#    GUI: ENTRY POINT
# =============================================================================
#: The open main window (kept so Spyder's event loop does not lose it).
_GUI_WINDOW: Any = None


def launch_gui(inputs: Sequence[str] = (), opts: Options | None = None, live_path: str | None = None,
               window_s: float | None = None, update_s: float | None = None,
               duration_s: float | None = None) -> int:
    """Open the main window (the default when the script runs without arguments).

    Parameters
    ----------
    inputs:
        Files or folders to list at start.
    opts:
        Options to show (default: the last session's, from QSettings).
    live_path, window_s, update_s:
        Start live mode on this file.
    duration_s:
        Close the window after this many seconds (tests).

    Returns the Qt exit code. In a console that already runs a Qt event loop
    (Spyder with the Qt graphics backend, IPython %gui qt) the window is
    shown and the function returns at once.
    """
    global _GUI_WINDOW
    if not HAVE_QT:
        raise RuntimeError("the GUI needs Qt.py (or QtPy) and PySide6: mamba install -c conda-forge "
                           "qt.py qtpy pyside6 pyqtgraph\n" + "\n".join(_QT_IMPORT_ERRORS))
    app = QtWidgets.QApplication.instance()
    created_here = app is None
    if created_here:
        app = QtWidgets.QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(APP_ORG)
    if HAVE_PYQTGRAPH:
        pg.setConfigOptions(antialias=True, imageAxisOrder="row-major")
    theme = ThemeManager(app)
    window = MainWindow(theme, inputs, opts)
    window.show()
    _GUI_WINDOW = window
    if live_path:
        window.central_tabs.setCurrentWidget(window.live)
        window.live.start(live_path, window_s, update_s)
    if duration_s:
        QtCore.QTimer.singleShot(int(duration_s * 1000), window.close)
    if not created_here and "IPython" in sys.modules:
        return 0                                     # an event loop is already running
    exit_code = app.exec() if hasattr(app, "exec") else app.exec_()
    live_gui_state["samples"] = window.live.ring.n if window.live.ring else 0
    return int(exit_code or 0)


def run_live_gui(path: str, opts: Options, window_s: float, update_s: float,
                 duration_s: float | None = None) -> int:
    """Live mode in the main window (kept for the --live command line)."""
    return launch_gui(opts=opts, live_path=path, window_s=window_s, update_s=update_s, duration_s=duration_s)


# %% ===========================================================================
#    VERIFICATION OF TRANSFORMS AND UNIT CONVERSIONS (0.0.3)
# =============================================================================
# Every transform is checked three independent ways where possible:
#   (1) ANALYTIC   a signal whose answer is known exactly (on-bin sinusoid,
#                  hand-computed unit values, the sinc of a boxcar);
#   (2) REFERENCE  an independent implementation: scipy.signal.periodogram,
#                  welch, spectrogram and lombscargle, or a brute-force DFT;
#   (3) IDENTITY   an internal consistency law: Parseval, Lomb-Scargle equal
#                  to the FFT on a uniform grid, CZT equal to the FFT on the
#                  bin frequencies, conversion round trips.
# Run with --verify, from the GUI (Analysis > Verify transforms) or inside
# the self-test. The manual's verification table is produced from it.
@dataclass
class Check:
    """One verification result."""
    group: str          # what is checked (FFT, Welch, CZT, ...)
    name: str           # the check
    method: str         # analytic | reference | identity
    measured: str       # the measured error or value
    limit: str          # the acceptance limit
    passed: bool


def verify_transforms(verbose: bool = True) -> tuple[list[Check], bool]:
    """Run all transform and unit checks; returns (checks, all passed)."""
    checks: list[Check] = []
    backend = Backend()
    rng = np.random.default_rng(2026)

    def record(group: str, name: str, method: str, error: float, limit: float,
               text: str | None = None) -> None:
        passed = bool(np.isfinite(error) and error <= limit)
        checks.append(Check(group, name, method, text or f"{error:.2e}", f"<= {limit:.0e}", passed))

    def rel(a: Any, b: Any) -> float:
        a, b = np.asarray(a, float), np.asarray(b, float)
        return float(np.max(np.abs(a - b)) / max(np.max(np.abs(b)), 1e-300))

    # ---------------------------------------------------------------- units
    z0 = Z0_OHM
    header_cases = {
        "E-Field [V/m]": "V/m", "E [mV/m]": "mV/m", "E [kV/m]": "kV/m", "E [µV/m]": "uV/m",
        "Level [dBµV/m]": "dBuV/m", "Level dB(µV/m)": "dBuV/m", "Level [dBuV]": "dBuV",
        "P [dBm]": "dBm", "S [dBm/m²]": "dBmW/m2", "S [dBmW/m2]": "dBmW/m2",
        "S [W/m²]": "W/m2", "S [W/m^2]": "W/m2", "S [mW/m^2]": "mW/m2", "S [µW/m²]": "uW/m2",
        "S [μW/m2]": "uW/m2", "Result 1 [mW/cm^2]": "mW/cm2", "S [µW/cm²]": "uW/cm2",
        "S [nW/cm2]": "nW/cm2", "H [A/m]": "A/m", "H [mA/m]": "mA/m", "B [µT]": "uT",
        "B [nT]": "nT", "B [mT]": "mT", "% of standard": "%", "Time [s]": None,
    }
    wrong = [h for h, expected in header_cases.items() if parse_unit(h) != expected]
    checks.append(Check("Units", f"parse_unit on {len(header_cases)} header spellings", "analytic",
                        "all recognised" if not wrong else "wrong: " + "; ".join(wrong), "all", not wrong))
    #  (reading, unit, expected W/m^2) worked by hand
    power_cases = [
        (1.0, "V/m", 1.0 / z0), (1000.0, "mV/m", 1.0 / z0), (1e6, "uV/m", 1.0 / z0),
        (1.0, "kV/m", 1e6 / z0), (120.0, "dBuV/m", 1.0 / z0),           # 120 dBuV/m = 1 V/m
        (1.0, "W/m2", 1.0), (1.0, "mW/m2", 1e-3), (1.0, "uW/m2", 1e-6),
        (1.0, "mW/cm2", 10.0), (1.0, "uW/cm2", 1e-2), (1.0, "nW/cm2", 1e-5),
        (0.0, "dBmW/m2", 1e-3),                                          # 0 dBm/m^2 = 1 mW/m^2
        (1.0, "A/m", z0), (1.0, "mA/m", z0 * 1e-6),
    ]
    worst = max(abs(float(to_power_like(np.array([v]), u, z0)[0][0]) - e) / e for v, u, e in power_cases)
    record("Units", f"to_power_like: {len(power_cases)} hand-worked values (V/m, dBuV/m, W/m2, mW/cm2, A/m, ...)",
           "analytic", worst, 1e-12)
    #  dBm + 50-ohm constant + antenna factor: -20 dBm, AF 30 dB/m
    level_dbuv_m = -20.0 + 10 * math.log10(50 * 1e-3 / 1e-12) + 30.0
    expected = (10 ** ((level_dbuv_m - 120) / 20)) ** 2 / z0
    got = float(to_power_like(np.array([-20.0]), "dBm", z0, 30.0)[0][0])
    record("Units", "dBm -> dBuV (+106.99 dB, 50 ohm) -> + AF -> E^2/Z0", "analytic", abs(got - expected) / expected, 1e-12)
    record("Units", "dBm without AF -> mW (0 dBm = 1 mW); dBuV -> uV^2 (20 dBuV = 100 uV^2)", "analytic",
           max(abs(float(to_power_like(np.array([0.0]), "dBm")[0][0]) - 1.0),
               abs(float(to_power_like(np.array([20.0]), "dBuV")[0][0]) - 100.0) / 100.0), 1e-12)
    fields = rng.uniform(0.01, 80.0, 50)
    record("Units", "round trip E -> S = E^2/Z0 -> E = sqrt(S Z0)", "identity",
           rel(power_to_field(to_power_like(fields, "V/m", z0)[0], z0), fields), 1e-12)
    record("Units", "E in dBuV/m: 1 V/m = 120, 1 mV/m = 60", "analytic",
           float(np.max(np.abs(field_to_dbuv_m([1.0, 1e-3]) - [120.0, 60.0]))), 1e-9)
    display_expected = {"W/m2": 1.0, "mW/m2": 1e3, "uW/m2": 1e6, "mW/cm2": 0.1, "uW/cm2": 100.0}
    record("Units", "display units: 1 W/m2 = 1e3 mW/m2 = 1e6 uW/m2 = 0.1 mW/cm2 = 100 uW/cm2", "analytic",
           max(abs(float(display_power(1.0, k)[0]) - v) / v for k, v in display_expected.items()), 1e-15)
    record("Units", "display units of a PSD scale with the factor squared", "identity",
           abs(float(display_psd(1.0, "uW/cm2")[0]) - 1e4) / 1e4, 1e-15)
    record("Units", "to_field_like: 1 mW/cm2 -> sqrt(10 Z0) = 61.38 V/m", "analytic",
           abs(float(to_field_like(np.array([1.0]), "mW/cm2", z0)[0][0]) - math.sqrt(10 * z0)) / math.sqrt(10 * z0),
           1e-12)

    # ---------------------------------------------------------------- display units (0.0.4)
    spellings = {"mW/cm^2": "mW/cm2", "mW/cm²": "mW/cm2", "µW/cm2": "uW/cm2", "μW/m²": "uW/m2",
                 "dB(µV/m)": "dBuV/m", "dBµV/m": "dBuV/m", "dbuv/m": "dBuV/m", "dBmW/m2": "dBm/m2",
                 "dBm/m²": "dBm/m2", "dB(µA/m)": "dBuA/m", "µT": "uT", "W/m^2": "W/m2", "dBm": "dBm"}
    wrong = [text for text, key in spellings.items() if lookup_display_unit(text).key != key]
    checks.append(Check("Display units", f"lookup_display_unit on {len(spellings)} spellings (µ/μ/u, ^2/², dB(...))",
                        "analytic", "all recognised" if not wrong else "wrong: " + "; ".join(wrong), "all",
                        not wrong))
    #  (base value, unit key, expected shown value) worked by hand
    shown_cases = [
        (1.0, "W/m2", 1.0), (1.0, "mW/cm2", 0.1), (1.0, "uW/cm2", 100.0), (1.0, "nW/cm2", 1e5),
        (1.0, "mW/m2", 1e3), (1.0, "dBW/m2", 0.0), (1.0, "dBm/m2", 30.0), (1e-3, "dBm/m2", 0.0),
        (1.0, "V/m", 1.0), (1.0, "mV/m", 1e3), (1.0, "kV/m", 1e-3), (1.0, "dBV/m", 0.0), (1.0, "dBuV/m", 120.0),
        (1e-3, "dBuV/m", 60.0), (1e-3, "dBuA/m", 60.0), (1e-6, "uT", 1.0), (1e-6, "nT", 1e3), (1e-6, "pT", 1e6),
        (1.0, "dBm", 0.0), (1.0, "dBW", -30.0), (1e-3, "dBm", -30.0), (1.0, "uW", 1e3),
        (1.0, "dBuV", 0.0), (1.0, "dBV", -120.0), (1e6, "V", 1.0),
    ]
    worst = max(abs(float(to_display([value], DISPLAY_UNITS[key])[0]) - expected) / max(abs(expected), 1.0)
                for value, key, expected in shown_cases)
    record("Display units", f"{len(shown_cases)} hand-worked values: 1 W/m2 = 0.1 mW/cm2 = 30 dBm/m2, "
           "1 V/m = 120 dBuV/m, 1 mW = -30 dBW, ...", "analytic", worst, 1e-12)
    samples = rng.uniform(1e-6, 1e3, 40)
    worst = max(rel(from_display(to_display(samples, unit), unit), samples) for unit in DISPLAY_UNITS.values())
    record("Display units", f"round trip to_display -> from_display for all {len(DISPLAY_UNITS)} units",
           "identity", worst, 1e-12)
    level_steps = [float(np.diff(to_display([1.0, 10.0], unit))[0]) - unit.db
                   for unit in DISPLAY_UNITS.values() if unit.is_level]
    record("Display units", "level rule: x10 in value = +10 dB (power units), +20 dB (root-power units)",
           "analytic", float(np.max(np.abs(level_steps))), 1e-12)
    root_field = rng.uniform(1e-3, 100.0, 30)
    squared_errors = []
    for key in ("V/m", "mV/m", "dBuV/m", "uT", "dBuA/m", "uV", "dBuV"):
        root_unit = DISPLAY_UNITS[key]
        shown_square = to_display(root_field ** 2, squared_unit(root_unit))
        if root_unit.is_level:      # 10 log10(k^2 x^2) = 20 log10(k x): the same number (dB)
            squared_errors.append(float(np.max(np.abs(shown_square - to_display(root_field, root_unit)))))
        else:                       # (k x)^2
            squared_errors.append(rel(shown_square, to_display(root_field, root_unit) ** 2))
    worst = max(squared_errors)
    record("Display units", "squared quantities: (k x)^2 for linear units; dB re 1 (ref)^2 of x^2 = level of x",
           "identity", worst, 1e-12)
    psd_offsets = [psd_to_display_db(np.array([1.0]), DISPLAY_UNITS[key])[0][0] - expected
                   for key, expected in (("mW/cm2", -20.0), ("dBm/m2", 60.0), ("dBuV/m", 120.0), ("W/m2", 0.0))]
    record("Display units", "PSD in dB re 1 (unit)^2/Hz: mW/cm2 -20 dB, dBm/m2 (mW/m2) +60 dB, dBuV/m +120 dB",
           "analytic", float(np.max(np.abs(psd_offsets))), 1e-12)
    from types import SimpleNamespace
    power_density = rng.uniform(1e-3, 10.0, 30)
    record_s = SimpleNamespace(field_values=power_to_field(power_density, z0), field_unit="V/m",
                               quantity=power_density, quantity_unit="W/m^2", z0_ohm=z0)
    e_field, h_field = time_quantity(record_s, "E"), time_quantity(record_s, "H")
    record("Display units", "plane wave: E/H = Z0 and E x H = S for the time-plot conversions", "identity",
           rel(e_field / h_field, np.full(30, z0)) + rel(e_field * h_field, power_density), 1e-12)
    one_mw_cm2 = SimpleNamespace(field_values=np.array([math.sqrt(10 * z0)]), field_unit="V/m",
                                 quantity=np.array([10.0]), quantity_unit="W/m^2", z0_ohm=z0)
    selection = unit_selection("dBuV/m,mA/m")
    e_shown = time_display_values(one_mw_cm2, "E field", selection)[0][0]
    h_shown = time_display_values(one_mw_cm2, "H field", selection)[0][0]
    e_expected, h_expected = 20 * math.log10(math.sqrt(10 * z0) * 1e6), math.sqrt(10 / z0) * 1e3
    record("Display units", f"1 mW/cm2 as E = {e_expected:.3f} dBuV/m and H = {h_expected:.3f} mA/m", "analytic",
           max(abs(e_shown - e_expected) / e_expected, abs(h_shown - h_expected) / h_expected), 1e-12)
    rf_e = rf_level_display(np.array([0.0]), "W/m^2", selection, "E field", z0)[0][0]
    rf_s = rf_level_display(np.array([0.0]), "W/m^2", unit_selection("dBm/m2"), "power density", z0)[0][0]
    rf_p = rf_level_display(np.array([0.0]), "mW", unit_selection("dBW"), "power density", z0)[0][0]
    rf_error = max(abs(rf_e - (10 * math.log10(z0) + 120.0)), abs(rf_s - 30.0), abs(rf_p + 30.0))
    record("Display units", "RF levels: 0 dB(W/m2) = 30 dBm/m2 = 145.76 dBuV/m (plane wave); 0 dBm = -30 dBW",
           "analytic", rf_error, 1e-9)
    selection_ok = (unit_selection("dBuV/m,mW/cm2")["S"] == "mW/cm2" and unit_selection("dBuV/m,mW/cm2")["E"] ==
                    "dBuV/m" and unit_selection("mW/cm2")["E"] == UNIT_FAMILIES["E"].default and
                    selection_text(unit_selection("mA/m")).split(",")[2] == "mA/m")
    checks.append(Check("Display units", "unit_selection: each unit sets its own family (0.0.3 single keys accepted)",
                        "analytic", "consistent" if selection_ok else "inconsistent", "all", selection_ok))

    # ---------------------------------------------------------------- FFT amplitude
    fs, n, k0, amplitude_true = 5.0, 2000, 50, 0.8
    time_s = np.arange(n) / fs
    for window in ("hann", "hamming", "blackmanharris", "flattop", "boxcar"):
        signal = 3.0 + amplitude_true * np.cos(2 * np.pi * k0 * fs / n * time_s + 0.7)
        _, amp = amplitude_spectrum(signal, fs, window, backend)
        record("FFT", f"on-bin sinusoid amplitude, {window} window", "analytic",
               abs(amp[k0] - amplitude_true) / amplitude_true, 1e-9)
    noise = rng.standard_normal(n) + 2.0
    for window in ("hann", "flattop"):
        freq, amp = amplitude_spectrum(noise, fs, window, backend)
        f_ref, p_ref = ssig.periodogram(noise, fs, window=window, scaling="spectrum", detrend="constant")
        record("FFT", f"amplitude = sqrt(2 x scipy periodogram 'spectrum'), {window}, random data", "reference",
               rel(amp[1:-1], np.sqrt(2 * p_ref[1:-1])) + rel(freq, f_ref), 1e-10)
    window_values = ssig.get_window("hann", n)
    centred = noise - noise.mean()
    bins = np.array([1, 17, 123, 999])
    brute = np.array([abs(np.sum(window_values * centred * np.exp(-2j * np.pi * k * np.arange(n) / n)))
                      for k in bins]) * 2 / window_values.sum()
    record("FFT", "brute-force DFT sum at 4 bins (Hann)", "reference",
           rel(amplitude_spectrum(noise, fs, "hann", backend)[1][bins], brute), 1e-10)
    nyquist_signal = 0.5 * np.cos(np.pi * np.arange(n))                  # exactly fs/2
    record("FFT", "Nyquist bin not doubled: cos(pi n) of amplitude 0.5 reads 0.5", "analytic",
           abs(amplitude_spectrum(nyquist_signal, fs, "boxcar", backend)[1][-1] - 0.5) / 0.5, 1e-12)
    _, amp_box = amplitude_spectrum(noise, fs, "boxcar", backend)
    parseval_power = 0.5 * np.sum(amp_box[1:-1] ** 2) + amp_box[-1] ** 2
    record("FFT", "Parseval (boxcar): sum A_k^2/2 + A_Nyq^2 = variance", "identity",
           abs(parseval_power - centred.var()) / centred.var(), 1e-12)
    half_bin = 3.0 + amplitude_true * np.cos(2 * np.pi * (k0 + 0.5) * fs / n * time_s)
    scallop_theory = abs(np.sum(window_values * np.exp(-1j * np.pi * np.arange(n) / n))) / window_values.sum()
    measured_db = 20 * np.log10(amplitude_spectrum(half_bin, fs, "hann", backend)[1].max() / amplitude_true)
    record("FFT", "Hann scalloping at half a bin equals the window response (-1.42 dB)", "analytic",
           abs(measured_db - 20 * np.log10(scallop_theory)), 0.01, f"{measured_db:.3f} dB")

    # ---------------------------------------------------------------- Welch
    long_noise = rng.standard_normal(20000)
    for window, nperseg in (("hann", 256), ("hamming", 255), ("blackmanharris", 128), ("flattop", 64)):
        step = max(1, int(round(nperseg * 0.5)))
        f_ours, p_ours, _ = welch_blocks(long_noise, [(0, long_noise.size)], fs, nperseg, window, backend)
        f_ref, p_ref = ssig.welch(long_noise, fs, window=window, nperseg=nperseg, noverlap=nperseg - step,
                                  detrend="constant")
        record("Welch", f"= scipy.signal.welch, {window}, nperseg {nperseg}", "reference",
               rel(p_ours, p_ref) + rel(f_ours, f_ref), 1e-10)
    blocks = [(0, 7000), (7600, 20000)]
    _, p_gappy, n_segments = welch_blocks(long_noise, blocks, fs, 256, "hann", backend)
    weighted = np.zeros_like(p_gappy)
    total_segments = 0
    for start, stop in blocks:
        _, p_block = ssig.welch(long_noise[start:stop], fs, window="hann", nperseg=256, noverlap=128)
        k_block = (stop - start - 256) // 128 + 1
        weighted += k_block * p_block
        total_segments += k_block
    record("Welch", "gap-aware: = segment-weighted mean of scipy welch per block", "reference",
           rel(p_gappy, weighted / total_segments) + float(n_segments != total_segments), 1e-10)
    f_w, p_w, _ = welch_blocks(long_noise, [(0, long_noise.size)], fs, 256, "hann", backend)
    window_256 = ssig.get_window("hann", 256)
    starts = np.arange(0, long_noise.size - 256 + 1, 128)
    segment_power = np.mean([np.sum((window_256 * (long_noise[s:s + 256] - long_noise[s:s + 256].mean())) ** 2)
                             for s in starts]) / np.sum(window_256 ** 2)
    record("Welch", "Parseval: sum P df = mean windowed segment power / sum w^2", "identity",
           abs(np.sum(p_w) * (f_w[1] - f_w[0]) - segment_power) / segment_power, 1e-10)

    # ---------------------------------------------------------------- chirp-Z zoom
    f0 = (k0 + 0.37) * fs / n
    off_bin = 1.0 + amplitude_true * np.cos(2 * np.pi * f0 * time_s + 0.3) + 0.01 * rng.standard_normal(n)
    band = (f0 - 8 * fs / n, f0 + 8 * fs / n)
    zoom_f, zoom_a = czt_zoom(off_bin, fs, band, 257, "hann")
    centred_off = off_bin - off_bin.mean()
    dtft = np.array([abs(np.sum(window_values * centred_off * np.exp(-2j * np.pi * f * np.arange(n) / fs)))
                     for f in zoom_f]) * 2 / window_values.sum()
    record("CZT", "= brute-force DTFT on the 257 zoom frequencies", "reference", rel(zoom_a, dtft), 1e-9)
    k1, k2 = 40, 60
    zoom_f2, zoom_a2 = czt_zoom(off_bin, fs, (k1 * fs / n, k2 * fs / n), k2 - k1 + 1, "hann")
    fft_f, fft_a = amplitude_spectrum(off_bin, fs, "hann", backend)
    record("CZT", "zoom on the FFT bin frequencies = FFT amplitudes", "identity",
           rel(zoom_a2, fft_a[k1:k2 + 1]) + rel(zoom_f2, fft_f[k1:k2 + 1]), 1e-9)
    zoom_f3, zoom_a3 = czt_zoom(off_bin, fs, band, 8193, "hann")
    peak = int(np.argmax(zoom_a3))
    record("CZT", "off-bin line (k0 + 0.37): frequency error / bin width", "analytic",
           abs(zoom_f3[peak] - f0) / (fs / n), 2e-3)
    record("CZT", "off-bin line: amplitude error (no scalloping loss)", "analytic",
           abs(zoom_a3[peak] - amplitude_true) / amplitude_true, 3e-3)

    # ---------------------------------------------------------------- Lomb-Scargle
    stamps = np.sort(rng.uniform(0, 600, 3000))
    values = 0.8 * np.sin(2 * np.pi * 0.21 * stamps + 0.4) + 0.05 * rng.standard_normal(stamps.size) + 2.0
    freqs = np.linspace(0.05, 1.0, 400)
    ours = lomb_scargle(stamps, values, freqs, backend)
    scipy_power = ssig.lombscargle(stamps, values - values.mean(), 2 * np.pi * freqs)
    record("Lomb-Scargle", "= scipy.signal.lombscargle, amplitude sqrt(4P/N)", "reference",
           rel(ours, np.sqrt(4 * scipy_power / stamps.size)), 1e-8)
    fine = np.linspace(0.20, 0.22, 2001)
    fine_amp = lomb_scargle(stamps, values, fine, backend)
    record("Lomb-Scargle", "irregular stamps: amplitude 0.8 at 0.21 Hz", "analytic",
           abs(fine_amp.max() - 0.8) / 0.8, 0.02, f"{fine_amp.max():.4f} at {fine[np.argmax(fine_amp)]:.5f} Hz")
    uniform_t = np.arange(n) / fs
    lomb_on_bins = lomb_scargle(uniform_t, noise, fft_f[1:200], backend)
    record("Lomb-Scargle", "uniform stamps at Fourier frequencies = boxcar FFT amplitude", "identity",
           rel(lomb_on_bins, amp_box[1:200]), 1e-9)

    # ---------------------------------------------------------------- envelope spectrogram
    spec_noise = rng.standard_normal(8192)
    t_ours, f_ours, s_ours = envelope_spectrogram(spec_noise, fs, 256, "hann")
    f_ref, t_ref, s_ref = ssig.spectrogram(spec_noise, fs, window="hann", nperseg=256, noverlap=192,
                                           detrend="constant", scaling="density", mode="psd")
    common = [(i, int(np.argmin(np.abs(t_ref - t)))) for i, t in enumerate(t_ours)
              if np.min(np.abs(t_ref - t)) < 1e-9]
    matched = rel(s_ours[:, [i for i, _ in common]], s_ref[:, [j for _, j in common]]) if common else np.inf
    record("Spectrogram", f"= scipy.signal.spectrogram on {len(common)} common slices", "reference",
           matched + rel(f_ours, f_ref), 1e-9)

    # ---------------------------------------------------------------- probe model and correction
    integration_s = 0.265
    test_freqs = np.linspace(0.05, 3.7, 200)
    fine_rate = 1e6
    taps = int(round(integration_s * fine_rate))
    discrete = np.abs(np.sin(np.pi * test_freqs * taps / fine_rate) /
                      (taps * np.sin(np.pi * test_freqs / fine_rate)))
    record("Probe model", "|sinc(f T)| = moving average of T at 1 MHz (closed form)", "reference",
           float(np.max(np.abs(probe_response(test_freqs, integration_s) - discrete))), 1e-6)
    sim_rate, mod_hz = 1000.0, 1.5
    sim_t = np.arange(0, 210, 1 / sim_rate)
    sim_power = 1.0 + 0.5 * np.cos(2 * np.pi * mod_hz * sim_t)
    averaged = np.convolve(sim_power, np.ones(taps // 1000) / (taps // 1000), mode="valid")
    sampled = averaged[::200][:1000]                                         # 5 Hz, 200 s
    sim_f, sim_a = amplitude_spectrum(sampled, 5.0, "hann", backend)
    k_mod = int(round(mod_hz / (sim_f[1] - sim_f[0])))
    response = float(probe_response(np.array([mod_hz]), integration_s)[0])
    record("Probe model", "simulated 265 ms average of a 1.5 Hz modulation: ratio = |sinc|", "analytic",
           abs(sim_a[k_mod] / 0.5 - response), 1e-3, f"{sim_a[k_mod] / 0.5:.5f} vs {response:.5f}")
    corrected = correct_probe(sim_a, sim_f, integration_s, 12.0)
    record("Probe model", "correction restores the 0.5 modulation amplitude", "analytic",
           abs(corrected[k_mod] - 0.5) / 0.5, 1e-3)
    gain_freqs = np.linspace(0.001, 3.77, 20001)
    gain = correction_gain(gain_freqs, integration_s, 12.0)
    finite = gain[np.isfinite(gain)]
    checks.append(Check("Probe model", "correction gain <= g_max, continuous, NaN from the first null",
                        "identity", f"max {20 * np.log10(finite.max()):.2f} dB, largest step "
                                    f"{20 * np.log10(np.max(finite[1:] / finite[:-1])):.4f} dB",
                        "<= 12 dB, step < 0.01 dB",
                        bool(finite.max() <= 10 ** 0.6 + 1e-12 and np.max(finite[1:] / finite[:-1]) < 10 ** (0.01 / 20)
                             and np.all(np.isnan(correction_gain(np.array([1 / integration_s, 5.0]),
                                                                 integration_s, 12.0))))))

    # ---------------------------------------------------------------- peaks and families
    k_off = 300.3
    peak_signal = 1.0 + 0.5 * np.cos(2 * np.pi * k_off * fs / 4096 * np.arange(4096) / fs)
    pf, pa = amplitude_spectrum(peak_signal, fs, "hann", backend)
    found = find_spectral_peaks(pf, pa, 6.0, 3)
    error_bins = abs(found[0]["f_hz"] - k_off * fs / 4096) / (fs / 4096) if found else np.inf
    record("Peaks", "parabolic interpolation of an off-bin line (k + 0.3), Hann", "analytic", error_bins, 0.05,
           f"{error_bins:.4f} bin")
    family_peaks = [{"f_hz": f, "amp": a, "snr_db": 30.0} for f, a in
                    ((0.2, 1.0), (0.4, 0.9), (0.6, 0.7), (0.7, 0.8), (0.8, 0.5), (1.0, 0.3))]
    families = harmonic_families(family_peaks, 0.005, 2.5)
    record("Peaks", "harmonic families: 0.2 Hz (12 rpm, 5 members) and 0.7 Hz", "analytic",
           abs(families[0]["rpm"] - 12.0) + abs(families[1]["f0_hz"] - 0.7) + abs(families[0]["n_members"] - 5),
           1e-9)

    # ---------------------------------------------------------------- per-bin modulation spectra
    grid = rng.standard_normal((512, 7)) + 5.0
    grid[:, 3] += 0.25 * np.cos(np.pi * np.arange(512))                       # a Nyquist modulation
    mod_f, mod_a = modulation_spectra(grid, 0.05, "hann", backend)
    columns = np.column_stack([amplitude_spectrum(grid[:, j], 20.0, "hann", backend)[1] for j in range(7)])
    record("Modulation map", "every bin = amplitude_spectrum of its power series (incl. Nyquist row)",
           "identity", rel(mod_a, columns) + rel(mod_f, amplitude_spectrum(grid[:, 0], 20.0, "hann", backend)[0]),
           1e-12)

    # ---------------------------------------------------------------- channel power from a trace
    carrier_w_m2, rbw_hz, bin_hz = 1e-3, 100e3, 25e3                     # trace 4x oversampled
    trace_f = 2.4e9 + np.arange(-200, 201) * bin_hz
    shape = np.exp(-4 * np.log(2) * (trace_f - 2.4e9) ** 2 / rbw_hz ** 2)   # Gaussian RBW, power
    field_trace = np.sqrt(carrier_w_m2 * shape * z0)                      # V/m per bin
    trace_t = np.arange(64) * 0.05
    level = np.tile(field_to_dbuv_m(field_trace), (trace_t.size, 1))
    level[:, 0] += 1e-9 * np.arange(trace_t.size)                         # keep the array non-constant
    spectra_test = SpectrumSet("rbw_check", trace_t, trace_f, level, "dBuV/m", source="signalshark")
    channel_result = analyse_spectrumset(spectra_test, Options(rf_channels="auto:1", rbw_hz=rbw_hz), backend)
    carrier_channel = channel_result.channels[1]
    record("Units", "channel power from an oversampled Gaussian-RBW trace = carrier (W/m2)", "analytic",
           abs(float(np.mean(carrier_channel.quantity)) - carrier_w_m2) / carrier_w_m2, 1e-3,
           f"{np.mean(carrier_channel.quantity):.6e} W/m2")

    # ---------------------------------------------------------------- uniform grid
    rate = 900.0
    rounded = np.round(np.arange(9000) / rate, 6)                          # stamps rounded to 1 us
    grid_values = rng.standard_normal(9000)
    uniform = make_uniform(rounded, grid_values)
    record("Grid", "900 Hz stamps rounded to 1 us: rate from the mean interval, samples untouched", "analytic",
           abs(uniform.sample_rate_hz - rate) / rate + float(not np.array_equal(uniform.values, grid_values)), 1e-6)
    gappy_t = np.concatenate([np.arange(0, 300, 0.2), np.arange(306, 600, 0.2)])
    gappy = make_uniform(gappy_t, np.ones(gappy_t.size))
    record("Grid", "a 6 s gap gives two gap-free blocks and ~1 % bridged", "analytic",
           abs(len(gappy.blocks) - 2) + abs(gappy.filled_fraction - 5.8 / 600), 2e-3,
           f"{len(gappy.blocks)} blocks, {100 * gappy.filled_fraction:.2f} %")

    all_passed = all(check.passed for check in checks)
    if verbose:
        print(f"{PROGRAM_NAME} {__version__}: verification of transforms and units")
        for check in checks:
            print(f"  [{'PASS' if check.passed else 'FAIL'}] {check.group:<15} {check.method:<9} "
                  f"{check.name}: {check.measured} ({check.limit})")
        print(f"VERIFICATION {'PASSED' if all_passed else 'FAILED'}: "
              f"{sum(c.passed for c in checks)}/{len(checks)} checks")
    return checks, all_passed


# %% ===========================================================================
#    SELF-TEST WITH SYNTHETIC EXPORTS
# =============================================================================
def _synthetic_radar(time_s: np.ndarray, rpm: float = 12.0, peak_w_m2: float = 4.0,
                     beam_width_s: float = 0.12, second_source_hz: float = 0.7,
                     base_w_m2: float = 1.0) -> np.ndarray:
    """Power density (W/m^2): rotating radar beam + a second, 0.7 Hz modulated source."""
    rotation_period_s = 60.0 / rpm
    beam_phase_s = (time_s % rotation_period_s) - rotation_period_s / 2
    radar = peak_w_m2 * np.exp(-0.5 * (beam_phase_s / beam_width_s) ** 2)
    second = base_w_m2 * (1 + 0.5 * np.sin(2 * np.pi * second_source_hz * time_s))
    return radar + second


def _probe_filter(fine_time_s: np.ndarray, power: np.ndarray, integration_time_s: float,
                  output_rate_hz: float) -> tuple[np.ndarray, np.ndarray]:
    """Boxcar-integrate a finely sampled power record and sample it at ``output_rate_hz``."""
    fine_step = fine_time_s[1] - fine_time_s[0]
    boxcar_length = max(1, int(round(integration_time_s / fine_step)))
    integrated = np.convolve(power, np.ones(boxcar_length) / boxcar_length, mode="same")
    decimation = int(round(1.0 / (output_rate_hz * fine_step)))
    return fine_time_s[::decimation], integrated[::decimation]


def make_synthetic_files(folder: Path) -> dict[str, Path]:
    """Write one synthetic export per supported format into ``folder``.

    The layouts are guesses at the real exports (none seen yet); they cover
    the reader features: ';' + decimal comma with German date/time, ',' with
    a 1 s timer log, an EHP-50 TS folder of spectra, a SignalShark-like HDF5
    spectrogram and a converter-style wide CSV.
    """
    rng = np.random.default_rng(7)
    folder.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    fine_time_s = np.arange(0, 600, 1e-3)
    fine_power = _synthetic_radar(fine_time_s)
    start_stamp = _dt.datetime(2026, 10, 15, 14, 3, 5)
    # 1) FieldMan / TSX style: ';' + decimal comma, German stamps, jitter + a 6 s gap
    times_5hz, power_5hz = _probe_filter(fine_time_s, fine_power, 0.265, 5.0)
    times_5hz = times_5hz + rng.normal(0, 0.004, times_5hz.size)
    keep = ~((times_5hz > 300) & (times_5hz < 306))
    field_v_per_m = np.sqrt(power_5hz * Z0_OHM)
    axis_weights = np.array([0.6, 0.64, 0.48]) / np.linalg.norm([0.6, 0.64, 0.48])
    lines = ["Narda-TSX export (synthetic)", "Device;FieldMan", "Probe;EFD-4091 (2462/19)",
             "Unit;V/m", "", "Date;Time;E RSS [V/m];X;Y;Z"]
    for sample_time, field_value in zip(times_5hz[keep], field_v_per_m[keep]):
        stamp = start_stamp + _dt.timedelta(seconds=float(sample_time))
        components = field_value * axis_weights
        lines.append(f"{stamp:%d.%m.%Y};{stamp:%H:%M:%S}.{stamp.microsecond // 1000:03d};"
                     + ";".join(f"{v:.5f}".replace(".", ",") for v in (field_value, *components)))
    files["fieldman"] = folder / "fieldman_efd4091_tsx.csv"
    files["fieldman"].write_text("\n".join(lines) + "\n", encoding="cp1252")
    # 2) NBM-style 1 s timer log in mW/cm^2, ',' separated, 6 rpm radar
    times_1hz, power_1hz = _probe_filter(fine_time_s, _synthetic_radar(fine_time_s, rpm=6.0, beam_width_s=0.4),
                                         1.0, 1.0)
    lines = ["Date,Time,Result 1 [mW/cm^2],Battery [%]"]
    for sample_time, power_value in zip(times_1hz, power_1hz):
        stamp = start_stamp + _dt.timedelta(seconds=float(sample_time))
        lines.append(f"{stamp:%d.%m.%y},{stamp:%H:%M:%S},{power_value / 10:.6g},88")
    files["nbm"] = folder / "nbm550_ef0691_timer.csv"
    files["nbm"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    # 3) EHP-50 TS auto-saved spectra (1 per second for 120 s), 50 Hz line AM at 0.05 Hz
    ehp_day_folder = folder / "ehp" / "2026" / "10" / "15"
    ehp_day_folder.mkdir(parents=True, exist_ok=True)
    spectrum_freq_hz = np.arange(1, 1001, 1.0)
    for second in range(120):
        stamp = _dt.datetime(2026, 10, 15, 9, 0, 0) + _dt.timedelta(seconds=second)
        line_amplitude = 10.0 * (1 + 0.5 * np.sin(2 * np.pi * 0.05 * second))
        spectrum = 0.01 + rng.random(spectrum_freq_hz.size) * 0.002
        spectrum[49] = line_amplitude                       # the 50 Hz bin
        rows = ["Frequency [Hz]\tX [V/m]\tY [V/m]\tZ [V/m]\tTotal [V/m]"]
        rows += [f"{f:.1f}\t{s / 3:.5f}\t{s / 3:.5f}\t{s / 3:.5f}\t{s:.5f}"
                 for f, s in zip(spectrum_freq_hz, spectrum)]
        (ehp_day_folder / f"{stamp:%H_%M_%S}_00.TXT").write_text("\n".join(rows) + "\n", encoding="utf-8")
    files["ehp"] = folder / "ehp"
    # 4) SignalShark-like HDF5 spectrogram (dBuV/m), 20 spectra/s for 60 s, two carriers
    n_spectra, rf_freq_hz = 1200, np.linspace(2.40e9, 2.50e9, 401)
    spectrum_times_s = np.arange(n_spectra) / 20.0
    level_dbuv_m = 40 + rng.normal(0, 0.5, (n_spectra, rf_freq_hz.size))
    carrier_a, carrier_b = 100, 300
    level_dbuv_m[:, carrier_a - 1:carrier_a + 2] += 40 + 6 * np.sin(2 * np.pi * 3.0 * spectrum_times_s)[:, None]
    level_dbuv_m[:, carrier_b - 1:carrier_b + 2] += 35 + 6 * np.sin(2 * np.pi * 0.5 * spectrum_times_s)[:, None]
    files["signalshark"] = folder / "signalshark_spectrogram.h5"
    with h5py.File(files["signalshark"], "w") as h5_file:
        group = h5_file.create_group("Measurement/Spectrogram")
        levels = group.create_dataset("Levels", data=level_dbuv_m)
        levels.attrs["Unit"] = "dBuV/m"
        group.create_dataset("Frequencies", data=rf_freq_hz)
        group.create_dataset("Timestamps", data=1.76e9 + spectrum_times_s)
    # 5) SignalShark converter CSV, wide format (rows = time, header = MHz)
    lines = ["Converted with NSL Converter (synthetic)", "Unit;dBuV/m",
             "Time [s];" + ";".join(f"{v / 1e6:.3f}".replace(".", ",") for v in rf_freq_hz[::4])]
    for row in range(0, n_spectra, 2):
        lines.append(f"{spectrum_times_s[row]:.3f}".replace(".", ",") + ";"
                     + ";".join(f"{v:.2f}".replace(".", ",") for v in level_dbuv_m[row, ::4]))
    files["signalshark_csv"] = folder / "signalshark_converted.csv"
    files["signalshark_csv"].write_text("\n".join(lines) + "\n", encoding="utf-8")
    return files


def self_test(keep_folder: str | None = None) -> int:
    """Unit checks of the estimators, then every reader on synthetic exports.

    Returns 0 when all checks pass.
    """
    all_passed = True

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal all_passed
        all_passed &= bool(condition)
        print(f"  [{'PASS' if condition else 'FAIL'}] {name}{(': ' + detail) if detail else ''}")

    print(f"{PROGRAM_NAME} {__version__} self-test")
    backend = Backend()
    rng = np.random.default_rng(1)
    sample_rate_hz, n_samples = 5.0, 3000
    time_s = np.arange(n_samples) / sample_rate_hz
    test_signal = 2.0 + 0.8 * np.sin(2 * np.pi * 0.21 * time_s) + 0.05 * rng.standard_normal(n_samples)
    # 1 streamed Welch equals scipy.signal.welch
    _, psd_streamed, _ = welch_blocks(test_signal, [(0, n_samples)], sample_rate_hz, 256, "hann", backend)
    _, psd_scipy = ssig.welch(test_signal, sample_rate_hz, window="hann", nperseg=256, noverlap=128,
                              detrend="constant")
    relative_error = np.max(np.abs(psd_streamed - psd_scipy) / np.maximum(psd_scipy, 1e-30))
    check("streamed Welch == scipy.signal.welch", np.allclose(psd_streamed, psd_scipy, rtol=1e-10),
          f"max rel err {relative_error:.1e}")
    # 2 amplitude scaling and CZT refinement
    _, fft_amp = amplitude_spectrum(test_signal, sample_rate_hz, "hann", backend)
    zoom_freq, zoom_amp = czt_zoom(test_signal, sample_rate_hz, (0.15, 0.27), 4001, "hann")
    check("FFT amplitude of 0.8 sinusoid", abs(fft_amp.max() - 0.8) < 0.12, f"{fft_amp.max():.3f}")
    check("CZT peak frequency", abs(zoom_freq[np.argmax(zoom_amp)] - 0.21) < 2e-4,
          f"{zoom_freq[np.argmax(zoom_amp)]:.5f} Hz")
    # 3 Lomb-Scargle amplitude on irregular stamps
    irregular_times = np.sort(rng.uniform(0, 600, 2500))
    irregular_values = 0.8 * np.sin(2 * np.pi * 0.21 * irregular_times)
    lomb_freq = np.linspace(0.18, 0.24, 601)
    lomb_amp = lomb_scargle(irregular_times, irregular_values, lomb_freq, backend)
    check("Lomb-Scargle amplitude and frequency",
          abs(lomb_amp.max() - 0.8) < 0.05 and abs(lomb_freq[np.argmax(lomb_amp)] - 0.21) < 5e-4,
          f"{lomb_amp.max():.3f} at {lomb_freq[np.argmax(lomb_amp)]:.4f} Hz")
    # 4 the sinc model at 1.5 Hz for a 265 ms boxcar
    response_db = 20 * np.log10(probe_response(np.array([1.5]), 0.265)[0])
    check("|sinc| at 1.5 Hz, T=265 ms", abs(response_db - (-2.37)) < 0.1, f"{response_db:.2f} dB")
    # 5 every transform and unit conversion (analytic, reference, identity)
    verification, verification_passed = verify_transforms(verbose=False)
    check("transform and unit verification (--verify)", verification_passed,
          f"{sum(c.passed for c in verification)}/{len(verification)} checks")
    # 6 readers + analyses on synthetic exports
    folder = Path(keep_folder) if keep_folder else Path(tempfile.mkdtemp(prefix="emf_fft_selftest_"))
    files = make_synthetic_files(folder)
    report = process_file(str(files["fieldman"]), Options(probe="EFD-4091", lomb="auto", correct_probe=True))
    families = report.get("families", [])
    check("FieldMan/TSX: radar 12 rpm family",
          bool(families) and abs(families[0]["rpm"] - 12.0) < 0.2,
          f"{[round(fam['rpm'], 3) for fam in families]}")
    check("FieldMan/TSX: 0.7 Hz source found",
          any(abs(peak["f_hz"] - 0.7) < 0.01 for peak in report.get("peaks", []))
          or any(abs(fam["f0_hz"] - 0.7) < 0.01 for fam in families))
    report = process_file(str(files["nbm"]), Options(probe="EF0691"))
    families = report.get("families", [])
    check("NBM timer log: 6 rpm", bool(families) and abs(families[0]["rpm"] - 6.0) < 0.2,
          f"{[round(fam['rpm'], 3) for fam in families]}")
    report = process_file(str(files["ehp"]), Options())
    found = [round(fam["f0_hz"], 4) for channel in report.get("channels", []) for fam in channel["families"]]
    check("EHP-50 TS spectra folder: 0.05 Hz modulation of 50 Hz line",
          any(abs(f0 - 0.05) < 0.005 for f0 in found), f"{found}")
    for key in ("signalshark", "signalshark_csv"):
        report = process_file(str(files[key]), Options(rf_channels="auto:2"))
        found = sorted(round(fam["f0_hz"], 3) for channel in report.get("channels", [])[1:]
                       for fam in channel["families"][:1])
        check(f"{key}: per-channel envelope 0.5 and 3 Hz",
              any(abs(f0 - 0.5) < 0.05 for f0 in found) and any(abs(f0 - 3.0) < 0.05 for f0 in found),
              f"{found}")
    # 7 .vszh5 structure
    vszh5_path = next(folder.rglob("*_envelope_fft.vszh5"))
    with h5py.File(vszh5_path, "r") as h5_file:
        layout_ok = h5_file["Veusz"].attrs["vsz_format"] == 1 and "document" in h5_file["Veusz/Document"]
    check(".vszh5 layout (Veusz format 1)", layout_ok, vszh5_path.name)
    # 8 unit control (0.0.4): several units in one document (sections) and one document per unit
    multi_opts = Options(probe="EFD-4091", display_unit="mW/cm2,dBuV/m", veusz_units="W/m2,dBm/m2,mA/m")
    fieldman_result = analyse_path(str(files["fieldman"]), multi_opts)
    sections = write_veusz(fieldman_result, folder / "units_sections", multi_opts)
    names = set(vszh5_writer.dataset_names(sections[0][0]))
    titles = read_text_dataset(sections[0][0], "display_unit") or []
    sections_ok = (len(sections) == 1 and {"fft_amplitude", "u1_fft_amplitude", "u2_fft_amplitude",
                                            "u3_hfield"} <= names and len(titles) == 4)
    check("Veusz sections: W/m2, dBm/m2 and mA/m sections in one document", sections_ok,
          f"{len(names)} datasets; sections {titles}")
    with h5py.File(sections[0][0], "r") as h5_file:
        stored = h5_file["Veusz/Data/fft_amplitude/data"][()]
        stored_dbm = h5_file["Veusz/Data/u2_fft_amplitude/data"][()]
    peak = int(np.argmax(fieldman_result.fft_amplitude[1:])) + 1
    values_ok = (abs(stored[peak] - 0.1 * fieldman_result.fft_amplitude[peak]) <= 1e-12 * stored[peak] and
                 abs(stored_dbm[peak] - 10 * math.log10(1e3 * fieldman_result.fft_amplitude[peak])) < 1e-9)
    check("Veusz values in mW/cm2 (x0.1) and dBm/m2 (10 log10(x1e3)) at the strongest line", values_ok,
          f"{stored[peak]:.6g} mW/cm2, {stored_dbm[peak]:.4f} dBm/m2")
    outline = bookmark_outline(["summary", "amplitude", "u1__summary", "u1__amplitude"], None, titles[:2])
    check("bookmarks grouped per unit section", len(outline) == 2 and outline[1][0] == titles[1],
          f"{[entry[0] for entry in outline]}")
    files_opts = Options(**{**asdict(multi_opts), "veusz_layout": "files"})
    per_unit = write_veusz(fieldman_result, folder / "units_files", files_opts)
    check("Veusz one document per unit", len(per_unit) == 4 and all(path.exists() for path, _ in per_unit),
          ", ".join(path.name for path, _ in per_unit))
    print(f"  outputs in {folder}")
    print("SELF-TEST", "PASSED" if all_passed else "FAILED")
    return 0 if all_passed else 1


# %% ===========================================================================
#    COMMAND LINE
# =============================================================================
def build_parser() -> argparse.ArgumentParser:
    """The command-line interface (also read by tools/build_manual_pdf.py)."""
    parser = argparse.ArgumentParser(
        prog=Path(__file__).name,
        description=f"{PROGRAM_NAME} {__version__}: envelope FFT of FieldMan/Narda-TSX, NBM, "
                    "EHP-50 TS and SignalShark data.")
    add = parser.add_argument
    add("inputs", nargs="*", help="files or EHP-50 TS folders (none: the GUI opens)")
    add("--gui", action="store_true", help="open the GUI with the given inputs listed")
    add("--probe", help=f"probe model ({', '.join(PROBES)}); sets fs and T_int defaults")
    add("--source", default="auto",
        choices=["auto", "fieldman", "tsx", "nbm", "ehp", "signalshark", "xlsx"],
        help="force a reader instead of auto-detection")
    add("--fs", type=float, help="sample rate (Hz) when the file has no time column")
    add("--t-int", type=float, help="probe integration time (s), overrides the catalogue")
    add("--quantity", default="power", choices=["power", "field", "db"],
        help="quantity transformed: power (linear in sources), field or dB")
    add("--window", default="hann", help="SciPy window name (hann, blackmanharris, flattop, ...)")
    add("--nperseg", type=int, help="Welch segment length (samples)")
    add("--zoom", help="CZT zoom band 'f1:f2' in Hz (default: around the strongest peak)")
    add("--zoom-points", type=int, default=4096, help="number of CZT points in the zoom band")
    add("--lomb", default="auto", choices=["auto", "on", "off"],
        help="Lomb-Scargle on the raw stamps (auto: with gaps or jitter)")
    add("--correct-probe", action="store_true", help="undo the integration roll-off")
    add("--max-boost-db", type=float, default=12.0, help="largest gain the correction may apply")
    add("--rf-channels", default="auto:3",
        help="spectrogram channels: 'auto:N' or 'f1:f2,f3:f4' (Hz)")
    add("--antenna-factor-db", type=float, help="AF (dB/m) for dBm/dBuV spectrogram levels")
    add("--rbw-hz", type=float, help="spectrogram resolution bandwidth (Hz): absolute channel power")
    add("--enbw-factor", type=float, default=GAUSSIAN_ENBW_FACTOR,
        help="noise bandwidth / RBW of the analyzer filter (1.0645 = Gaussian)")
    add("--display-unit", default="W/m2", type=_unit_list_argument,
        help="display units, one per family, comma separated, e.g. 'mW/cm2,dBuV/m,mA/m' "
             "(--list-units; data files stay in SI units)")
    add("--time-display", default="power density", choices=list(TIME_DISPLAY_MODES),
        help="what time plots and time pages show (E/H of power-density logs: plane wave, Z0)")
    add("--rf-level-display", default="power density", choices=list(RF_LEVEL_MODES),
        help="spectrogram levels of power-density inputs as power density or plane-wave E/H")
    add("--veusz-units", default="", type=_unit_list_argument,
        help="extra units for the Veusz documents, e.g. 'W/m2,dBm/m2,dBuV/m'")
    add("--veusz-layout", default="sections", choices=list(VEUSZ_LAYOUTS),
        help="several units: one document with a section per unit, or one document per unit")
    add("--list-units", action="store_true", help="print every display unit and exit")
    add("--z0", type=float, default=Z0_OHM, help="wave impedance (ohm); 377 matches Narda displays")
    add("--snr", type=float, default=6.0, help="peak threshold over the median level (linear)")
    add("--dyn-range-db", type=float, default=50.0,
        help="ignore peaks more than this many dB below the strongest")
    add("--out", help="output folder (default <input>_fft)")
    add("--jobs", type=int, default=1, help="parallel processes for several inputs")
    add("--gpu", action="store_true", help="use CuPy/CUDA FFTs when available")
    add("--render", action="store_true", help="PDF/PNG via vszh5_writer.py + Veusz")
    add("--pickle", action="store_true", help="also offload the full result to .pkl")
    add("--time-col", help="time column name/index ('Date+Time' joins two)")
    add("--value-col", help="value column name/index")
    add("--unit", help="unit of the values, e.g. 'V/m', 'mW/cm2', 'dBuV/m'")
    add("--sep", help="delimiter (default: sniffed)")
    add("--decimal", help="decimal mark (default: sniffed)")
    add("--dayfirst", action="store_true", default=None, help="dates are day-first")
    add("--h5-level", help="SignalShark .h5: level dataset path")
    add("--h5-freq", help="SignalShark .h5: frequency dataset path")
    add("--h5-time", help="SignalShark .h5: time dataset path")
    add("--inspect", action="store_true", help="only report how each input is read")
    add("--live", metavar="FILE", help="follow a growing file and update live")
    add("--window-s", type=float, default=120.0, help="live: rolling window (s)")
    add("--update", type=float, default=1.0, help="live: update interval (s)")
    add("--live-seconds", type=float, help="live: stop after this many seconds")
    add("--no-gui", action="store_true", help="live: console output only")
    add("--selftest", nargs="?", const="", metavar="DIR",
        help="run the built-in self-test (optionally keep outputs in DIR)")
    add("--verify", action="store_true",
        help="verify every transform and unit conversion (analytic, reference, identity checks)")
    add("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def options_from_args(args: argparse.Namespace) -> Options:
    """Options from parsed command-line arguments."""
    zoom_band = tuple(float(v) for v in args.zoom.split(":")) if args.zoom else None
    return Options(probe=args.probe, source=args.source, fs=args.fs, t_int=args.t_int,
                   quantity=args.quantity, window=args.window, nperseg=args.nperseg, zoom=zoom_band,
                   zoom_points=args.zoom_points, lomb=args.lomb, correct_probe=args.correct_probe,
                   max_boost_db=args.max_boost_db, rf_channels=args.rf_channels,
                   antenna_factor_db=args.antenna_factor_db, z0=args.z0, out=args.out, gpu=args.gpu,
                   render=args.render, pickle=args.pickle, time_col=args.time_col,
                   value_col=args.value_col, unit=args.unit, sep=args.sep, decimal=args.decimal,
                   dayfirst=args.dayfirst, h5_level=args.h5_level, h5_freq=args.h5_freq,
                   h5_time=args.h5_time, snr=args.snr, dyn_range_db=args.dyn_range_db,
                   display_unit=args.display_unit, time_display=args.time_display,
                   rf_level_display=args.rf_level_display, veusz_units=args.veusz_units,
                   veusz_layout=args.veusz_layout, rbw_hz=args.rbw_hz, enbw_factor=args.enbw_factor)


def _unit_list_argument(text: str) -> str:
    """argparse type: a comma-separated list of display units, normalised to their keys."""
    try:
        return ",".join(lookup_display_unit(item).key for item in _split_units(text))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def print_unit_table() -> None:
    """--list-units: every display unit with its conversion and level rule."""
    print(f"{'Family':<34} {'Key':<9} {'Label':<10} {'Shown value':<36} Rule")
    for family, key, label, conversion, rule in unit_table_rows():
        print(f"{family:<34} {key:<9} {label:<10} {conversion:<36} {rule}")
    print("\nSquared quantities (EHP-50 TS field squared, B^2, uV^2) use the square of the chosen unit; "
          "PSDs are dB re 1 (unit)^2/Hz.")


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point: the GUI without arguments (or with --gui), else the command line.

    Returns the process exit code.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    args = build_parser().parse_args(argv)
    if args.selftest is not None:
        return self_test(args.selftest or None)
    if args.verify:
        return 0 if verify_transforms(verbose=True)[1] else 1
    if args.list_units:
        print_unit_table()
        return 0
    opts = options_from_args(args)
    if args.live:
        if args.no_gui:
            return run_live_console(args.live, opts, args.window_s, args.update, args.live_seconds)
        return run_live_gui(args.live, opts, args.window_s, args.update, args.live_seconds)
    if args.gui or not argv:
        if not HAVE_QT:
            print("The GUI needs Qt.py (or QtPy) and PySide6; command-line help follows.\n"
                  + "\n".join(_QT_IMPORT_ERRORS))
            build_parser().print_help()
            return 2
        return launch_gui(args.inputs, opts if argv else None, duration_s=args.live_seconds)
    if not args.inputs:
        build_parser().print_help()
        return 2
    if args.inspect:
        for input_path in args.inputs:
            print(inspect_input(input_path, opts), "\n")
        return 0
    reports = process_files(args.inputs, opts, args.jobs)
    for report in reports:
        print(json.dumps(_jsonable(report), indent=2))
    return 1 if any("error" in report for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())


# %% ===========================================================================
#    INTERACTIVE SCRATCH CELL (Spyder)
# =============================================================================
# opts = Options(probe="EFD-4091", correct_probe=True, lomb="on",
#                display_unit="mW/cm2,dBuV/m", veusz_units="dBm/m2,mA/m")
# print(inspect_input(r"C:\path\to\export.csv", opts))
# series = load_any(r"C:\path\to\export.csv", opts)
# result = analyse_timeseries(series, opts)
# print(result.peaks[:5], result.families)
# print("\n".join(summary_lines(result, "uW/cm2,dBuV/m")))
# write_outputs(result, Path(r"C:\path\to\out"), opts)
# opts.veusz_units, opts.veusz_layout = "W/m2,uW/cm2", "files"      # other units,
# write_veusz(result, Path(r"C:\path\to\out"), opts)              # no re-analysis
# print_unit_table()
# flush_memory()
