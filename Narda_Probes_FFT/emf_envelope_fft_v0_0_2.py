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
 Filename       : emf_envelope_fft_v0_0_2.py
 Version        : 0.0.2 (Semantic Versioning 2.0.0, MAJOR.MINOR.PATCH)
 Author         : William W. Wallace
 Company        : NRAO/GBO
 Email          : wwallace@nrao.edu
 Created        : 2026-10-15
 Modified       : 2026-10-15
 Language       : Python 3.12
 Requires       : numpy, scipy (>= 1.12), pandas, h5py, and vszh5_writer.py
                  0.0.11 (same author, shipped next to this script)
 Optional       : cupy (GPU FFTs), Qt.py + PySide6 + pyqtgraph (live window),
                  openpyxl (.xlsx exports), Veusz + pypdf (rendering the
                  .vszh5 to PDF with bookmarks and PNG, --render)
 Licence        : GPL-3.0-or-later (GNU General Public License v3.0 or later)
 Copyright      : Copyright (C) 2026 William W. Wallace
 Derived from   : Veusz output through vszh5_writer.py 0.0.11 (same author;
                  extended for this program from 0.0.10 of the QuickSyn
                  package with 2-D datasets and plot-page helpers).
 Manual         : docs/EMF_Envelope_FFT_Manual_v0.0.2.pdf (LuaLaTeX source
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
    python emf_envelope_fft_v0_0_2.py --selftest
    python emf_envelope_fft_v0_0_2.py --inspect log.csv
    python emf_envelope_fft_v0_0_2.py log.csv --probe EFD-4091 --lomb on --render
    python emf_envelope_fft_v0_0_2.py a.csv b.csv c.csv --jobs 3 --gpu
    python emf_envelope_fft_v0_0_2.py rec.h5 --source signalshark --rf-channels auto:5
    python emf_envelope_fft_v0_0_2.py --live growing.csv --probe EF0691 --window-s 120
In Spyder, run the cells; the last cell is a scratch cell.

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

REVISION HISTORY
----------------
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
from typing import Any, Sequence

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

# The author's Veusz HDF5 writer, shipped next to this script. 0.0.11 or
# later is needed (2-D datasets and the xy_page/image_page helpers). The
# script's folder goes first on sys.path so that copy wins over an older
# one elsewhere (e.g. the QuickSyn package); Spyder's runcell defines
# __file__, a bare interpreter session falls back to the working folder.
_SCRIPT_FOLDER = Path(globals().get("__file__", Path.cwd() / "_")).resolve().parent
if str(_SCRIPT_FOLDER) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_FOLDER))
import vszh5_writer                     # noqa: E402 - needs the path set above
from vszh5_writer import (Trace, VeuszWriter, VszDoc, image_page,  # noqa: E402
                          render_pages, xy_page)

if not hasattr(VeuszWriter, "dataset_2d"):   # an older copy was imported first
    raise ImportError(f"vszh5_writer {vszh5_writer.__version__} ({vszh5_writer.__file__}) is too "
                      f"old: 0.0.11 or later, shipped with this script, is needed")

__version__ = "0.0.2"                  # Semantic Versioning 2.0.0
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
    ("dBuV/m", r"db\s*[µu]v\s*/\s*m"),
    ("dBuV", r"db\s*[µu]v(?!\s*/)"),
    ("dBm", r"dbm(?!w)"),
    ("dBmW/m2", r"dbm\s*w?\s*/\s*m\s*\^?2|dbmw/m²"),
    ("mW/cm2", r"mw\s*/\s*cm\s*\^?\s*[2²]"),
    ("uW/cm2", r"[µu]w\s*/\s*cm\s*\^?\s*[2²]"),
    ("nW/cm2", r"nw\s*/\s*cm\s*\^?\s*[2²]"),
    ("W/m2", r"(?<![a-z])w\s*/\s*m\s*\^?\s*[2²]"),
    ("mV/m", r"mv\s*/\s*m"),
    ("uV/m", r"[µu]v\s*/\s*m"),
    ("V/m", r"(?<![a-z])v\s*/\s*m"),
    ("mA/m", r"ma\s*/\s*m"),
    ("A/m", r"(?<![a-z])a\s*/\s*m"),
    ("mT", r"(?<![a-z])mt(?![a-z])"),
    ("uT", r"[µu]t(?![a-z])"),
    ("nT", r"(?<![a-z])nt(?![a-z])"),
    ("%", r"%"),
]


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
        (50 ohm).

    Returns
    -------
    (power_values, power_unit_label, conversion_note)
    """
    readings = np.asarray(values, dtype=float)
    if unit in ("V/m", "mV/m", "uV/m"):
        to_volts_per_metre = {"V/m": 1.0, "mV/m": 1e-3, "uV/m": 1e-6}[unit]
        return ((readings * to_volts_per_metre) ** 2 / z0_ohm, "W/m^2",
                f"S = E^2/Z0, Z0 = {z0_ohm:.3f} ohm")
    if unit == "dBuV/m":
        field_v_per_m = 10.0 ** ((readings - 120.0) / 20.0)
        return field_v_per_m ** 2 / z0_ohm, "W/m^2", "dBuV/m -> V/m -> E^2/Z0"
    if unit in ("W/m2", "mW/cm2", "uW/cm2", "nW/cm2"):
        to_watts_per_m2 = {"W/m2": 1.0, "mW/cm2": 10.0, "uW/cm2": 1e-2, "nW/cm2": 1e-5}[unit]
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
            level_dbuv = readings + 107.0 if unit == "dBm" else readings
            field_v_per_m = 10.0 ** ((level_dbuv + antenna_factor_db - 120.0) / 20.0)
            return (field_v_per_m ** 2 / z0_ohm, "W/m^2",
                    f"{unit} + AF {antenna_factor_db:g} dB/m -> E^2/Z0")
        if unit == "dBm":
            return 10.0 ** (readings / 10.0), "mW", "dBm -> mW at the analyzer port (no AF given)"
        return 10.0 ** (readings / 10.0), "uV^2", "dBuV -> uV^2 (no AF given)"
    if unit == "%":
        return readings, "% of standard", "analysed as given (Narda shaped-probe % of standard)"
    return readings, unit or "a.u.", "unit unknown: analysed as given"


def to_field_like(values: np.ndarray, unit: str | None) -> tuple[np.ndarray, str]:
    """Readings as field strength (V/m, A/m or T) for the time-series page."""
    readings = np.asarray(values, dtype=float)
    scale_and_label = {"V/m": (1.0, "V/m"), "mV/m": (1e-3, "V/m"), "uV/m": (1e-6, "V/m"),
                       "A/m": (1.0, "A/m"), "mA/m": (1e-3, "A/m"),
                       "mT": (1e-3, "T"), "uT": (1e-6, "T"), "nT": (1e-9, "T")}
    if unit in scale_and_label:
        scale, label = scale_and_label[unit]
        return readings * scale, label
    if unit == "dBuV/m":
        return 10.0 ** ((readings - 120.0) / 20.0), "V/m"
    return readings, unit or "a.u."


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
        field_values, field_unit = to_field_like(values, unit)
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


def probe_response(freq_hz: np.ndarray, integration_time_s: float) -> np.ndarray:
    """|H(nu)| of a T-second moving-average (boxcar) integrator: |sinc(nu T)|."""
    return np.abs(np.sinc(np.asarray(freq_hz, float) * integration_time_s))


def correct_probe(amplitude: np.ndarray, freq_hz: np.ndarray, integration_time_s: float,
                  max_boost_db: float) -> np.ndarray:
    """Undo the integration roll-off, boost-limited (Wiener-type).

    A_c = A |H| / (|H|^2 + eps), eps chosen so the boost never exceeds
    ``max_boost_db``; where |H| >= 1/g_max the exact inverse A/|H| is used;
    bins at or beyond the first null (1/T) become NaN.
    """
    response = probe_response(freq_hz, integration_time_s)
    max_gain = 10 ** (max_boost_db / 20.0)
    epsilon = 1.0 / (4.0 * max_gain ** 2)    # peak of h/(h^2+eps) is 1/(2 sqrt(eps)) = g_max
    corrected = amplitude * response / (response ** 2 + epsilon) if max_gain > 1 else amplitude.copy()
    corrected = np.where(response >= 1.0 / max_gain, amplitude / np.maximum(response, 1e-12), corrected)
    return np.where(np.asarray(freq_hz) * integration_time_s < 1.0, corrected, np.nan)


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
    field_values, field_unit = to_field_like(series.values, series.unit)
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
        backend.note, series.meta)


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
                                 np.full(spectra.freq_hz.size, np.nan), channels, notes, spectra.meta)

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
    window_values = ssig.get_window(opts.window, n_grid)
    modulation_freq_hz = sfft.rfftfreq(n_grid, spectrum_interval)
    modulation_amplitude = np.empty((modulation_freq_hz.size, power_on_grid.shape[1]))
    columns_per_batch = max(1, int(256 * 2 ** 20 // (8 * n_grid * 2)))
    window_on_device = backend.asarray(window_values[:, None])
    for first in range(0, power_on_grid.shape[1], columns_per_batch):
        block = power_on_grid[:, first:first + columns_per_batch]
        centred = backend.asarray(block - block.mean(axis=0, keepdims=True))
        modulation_amplitude[:, first:first + columns_per_batch] = backend.cpu(
            abs(backend.rfft(centred * window_on_device, axis=0))) * (2.0 / window_values.sum())
    modulation_amplitude[0] /= 2.0
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
    if channel_spec.startswith("auto"):
        n_auto = int(channel_spec.split(":")[1]) if ":" in channel_spec else 3
        peak_bins, _ = ssig.find_peaks(mean_level_db, prominence=3.0)
        peak_bins = peak_bins[np.argsort(mean_level_db[peak_bins])[::-1]][:n_auto]
        bin_width = float(np.median(np.diff(spectra.freq_hz))) if spectra.freq_hz.size > 1 else 1.0
        for peak_bin in sorted(peak_bins):
            centre = spectra.freq_hz[peak_bin]
            bands.append((f"f_{centre / freq_divisor:.6g}{freq_unit_label}",
                          float(centre - 2 * bin_width), float(centre + 2 * bin_width)))
    elif channel_spec:
        for part in channel_spec.split(","):
            f_low, f_high = (float(v) for v in part.split(":"))
            bands.append((f"f_{f_low / freq_divisor:.6g}-{f_high / freq_divisor:.6g}{freq_unit_label}",
                          f_low, f_high))
    channel_opts = Options(**{**asdict(opts), "probe": None, "fs": None, "quantity": "power",
                              "unit": None, "correct_probe": False})
    for label, f_low, f_high in bands:
        in_band = (spectra.freq_hz >= f_low) & (spectra.freq_hz <= f_high)
        if not in_band.any():
            continue
        band_power = np.nansum(power_on_grid[:, in_band], axis=1)     # sum of linear power
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
        dominant_modulation_hz, channels, notes, {**spectra.meta, "power_note": conversion_note})


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
    "time": "Field vs time",
    "amplitude": "Envelope amplitude spectrum (FFT)",
    "welch": "Welch power spectral density",
    "zoom": "Chirp-Z zoom around the strongest peak",
    "lomb": "Lomb-Scargle periodogram (raw stamps)",
    "probe": "Probe integration model |sinc|",
    "spectrogram": "Envelope spectrogram",
}
#: Titles of the overview pages of a spectrogram (SignalShark, EHP-50 TS).
OVERVIEW_PAGE_TITLES = {
    "spectrum": "Mean and max-hold spectrum",
    "spectrogram": "Spectrogram (level vs time and frequency)",
    "modulation_map": "Envelope spectrum per frequency bin",
    "dominant_modulation": "Strongest envelope frequency per bin",
}


def _freq_unit(f_max_hz: float) -> tuple[float, str]:
    """(divisor, label) so a spectrum frequency axis reads in Hz/kHz/MHz/GHz."""
    for divisor, label in ((1e9, "GHz"), (1e6, "MHz"), (1e3, "kHz")):
        if f_max_hz >= 10 * divisor:
            return divisor, label
    return 1.0, "Hz"


def bookmark_outline(page_names: Sequence[str],
                     channel_names: Sequence[str] | None = None) -> list[tuple]:
    """PDF bookmark hierarchy for vszh5_writer.render_pages().

    ``channel_names`` is None for a single series, else the channel names of
    a spectrogram result (possibly empty). A single series gives a flat list of its pages. A spectrogram gives an
    "Overview" entry holding the overview pages, then one entry per channel
    ("Channel 1: <name>") holding that channel's pages. Entries follow
    vszh5_writer.OutlineEntry: (title, page index) or (title, None, children).
    """
    overview: list[tuple] = []
    flat: list[tuple] = []
    channels: dict[int, list[tuple]] = {}
    for page_index, page_name in enumerate(page_names):
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


def _write_series_pages(writer: VeuszWriter, doc: VszDoc, result: SeriesResult, prefix: str) -> list[str]:
    """Datasets and pages for one SeriesResult; returns the page names."""
    pages: list[str] = []
    tags = (prefix.rstrip("_") or "series",)
    start_text = f" (start {result.t0_text})" if result.t0_text else ""
    # -- time series: on a date axis when the wall-clock start is known
    writer.dataset_1d(f"{prefix}time_s", result.time_s, tags=tags)
    writer.dataset_1d(f"{prefix}field", result.field_values, tags=tags)
    writer.dataset_1d(f"{prefix}quantity", result.quantity, tags=tags)
    page = f"{prefix}time"
    if result.t0_veusz is not None:
        writer.dataset_date(f"{prefix}time_date", result.t0_veusz + result.time_s, tags=tags)
        xy_page(doc, page, [Trace(f"{prefix}time_date", f"{prefix}field", "field")],
                title=f"{result.name}: field vs time{start_text}",
                xlabel="Date and time (instrument clock)", ylabel=f"Field ({result.field_unit})",
                xmode="datetime", x_autorange="exact")
    else:
        xy_page(doc, page, [Trace(f"{prefix}time_s", f"{prefix}field", "field")],
                title=f"{result.name}: field vs time", xlabel="Time since start (s)",
                ylabel=f"Field ({result.field_unit})", x_autorange="exact")
    pages.append(page)
    # -- amplitude spectrum (+ probe-corrected, + per-axis X/Y/Z)
    writer.dataset_1d(f"{prefix}fft_freq_hz", result.fft_freq_hz, tags=tags)
    writer.dataset_1d(f"{prefix}fft_amplitude", result.fft_amplitude, tags=tags)
    traces = [Trace(f"{prefix}fft_freq_hz", f"{prefix}fft_amplitude", "FFT amplitude")]
    if result.fft_amplitude_corrected is not None:
        writer.dataset_1d(f"{prefix}fft_amplitude_corrected", result.fft_amplitude_corrected, tags=tags)
        traces.append(Trace(f"{prefix}fft_freq_hz", f"{prefix}fft_amplitude_corrected",
                            "probe-corrected", style="dashed"))
    for axis, axis_amplitude in result.axis_amplitudes.items():
        writer.dataset_1d(f"{prefix}fft_amplitude_{axis}", axis_amplitude, tags=tags)
        traces.append(Trace(f"{prefix}fft_freq_hz", f"{prefix}fft_amplitude_{axis}",
                            f"axis {axis}", style="dotted"))
    page = f"{prefix}amplitude"
    xy_page(doc, page, traces, title=f"{result.name}: envelope amplitude spectrum ({result.quantity_unit})",
            xlabel="Envelope (modulation) frequency (Hz)", ylabel=f"Amplitude ({result.quantity_unit})",
            xmin=0.0, ylog=True)
    pages.append(page)
    # -- Welch PSD in dB
    writer.dataset_1d(f"{prefix}welch_freq_hz", result.welch_freq_hz, tags=tags)
    writer.dataset_1d(f"{prefix}welch_psd_db",
                      10 * np.log10(np.maximum(result.welch_psd, np.max(result.welch_psd) * 1e-15)),
                      tags=tags)
    page = f"{prefix}welch"
    xy_page(doc, page, [Trace(f"{prefix}welch_freq_hz", f"{prefix}welch_psd_db", "Welch")],
            title=f"{result.name}: Welch PSD, {result.welch_segments} segments of {result.welch_nperseg}",
            xlabel="Envelope frequency (Hz)", ylabel=f"PSD (dB re ({result.quantity_unit})^2/Hz)",
            xmin=0.0)
    pages.append(page)
    # -- chirp-Z zoom, with the FFT bins in the same band as markers
    if result.zoom_freq_hz is not None:
        writer.dataset_1d(f"{prefix}zoom_freq_hz", result.zoom_freq_hz, tags=tags)
        writer.dataset_1d(f"{prefix}zoom_amplitude", result.zoom_amplitude, tags=tags)
        in_band = (result.fft_freq_hz >= result.zoom_freq_hz[0]) & (result.fft_freq_hz <= result.zoom_freq_hz[-1])
        writer.dataset_1d(f"{prefix}zoom_fft_freq_hz", result.fft_freq_hz[in_band], tags=tags)
        writer.dataset_1d(f"{prefix}zoom_fft_amplitude", result.fft_amplitude[in_band], tags=tags)
        page = f"{prefix}zoom"
        xy_page(doc, page, [Trace(f"{prefix}zoom_freq_hz", f"{prefix}zoom_amplitude", "chirp-Z (dense)"),
                            Trace(f"{prefix}zoom_fft_freq_hz", f"{prefix}zoom_fft_amplitude",
                                  "FFT bins", marker="circle", line=False)],
                title=f"{result.name}: chirp-Z zoom", xlabel="Envelope frequency (Hz)",
                ylabel=f"Amplitude ({result.quantity_unit})")
        pages.append(page)
    # -- Lomb-Scargle against the FFT
    if result.lomb_freq_hz is not None:
        writer.dataset_1d(f"{prefix}lomb_freq_hz", result.lomb_freq_hz, tags=tags)
        writer.dataset_1d(f"{prefix}lomb_amplitude", result.lomb_amplitude, tags=tags)
        page = f"{prefix}lomb"
        xy_page(doc, page, [Trace(f"{prefix}lomb_freq_hz", f"{prefix}lomb_amplitude", "Lomb-Scargle"),
                            Trace(f"{prefix}fft_freq_hz", f"{prefix}fft_amplitude", "FFT (uniform grid)",
                                  style="dashed")],
                title=f"{result.name}: Lomb-Scargle (raw time stamps)", xlabel="Envelope frequency (Hz)",
                ylabel=f"Amplitude ({result.quantity_unit})", ylog=True, xmin=0.0)
        pages.append(page)
    # -- probe integration model
    if result.probe_response is not None:
        writer.dataset_1d(f"{prefix}probe_response_db",
                          20 * np.log10(np.maximum(result.probe_response, 1e-6)), tags=tags)
        page = f"{prefix}probe"
        xy_page(doc, page, [Trace(f"{prefix}fft_freq_hz", f"{prefix}probe_response_db", "|H|")],
                title=f"Probe integration model |sinc(f T)|, T = {result.integration_time_s * 1e3:.4g} ms",
                xlabel="Envelope frequency (Hz)", ylabel="|H| (dB)", xmin=0.0)
        pages.append(page)
    # -- envelope spectrogram: rows = envelope frequency (y), columns = time (x)
    if result.spectrogram_db is not None:
        writer.dataset_2d(f"{prefix}spectrogram_db", result.spectrogram_db,
                          xcent=result.spectrogram_time_s, ycent=result.spectrogram_freq_hz, tags=tags)
        page = f"{prefix}spectrogram"
        peak_db = float(np.nanmax(result.spectrogram_db))
        image_page(doc, page, f"{prefix}spectrogram_db", title=f"{result.name}: envelope spectrogram",
                   xlabel="Time (s)", ylabel="Envelope frequency (Hz)", zlabel="PSD (dB)",
                   zmin=peak_db - 60, zmax=peak_db)
        pages.append(page)
    return pages


def write_vszh5_series(result: SeriesResult, path: Path) -> Path:
    """Veusz document for one time-series result."""
    with VeuszWriter(path, compress=True, writer_tag=f"{PROGRAM_NAME} {__version__}") as writer:
        doc = VszDoc(f"{PROGRAM_NAME} {__version__}")
        _write_series_pages(writer, doc, result, "")
        writer.dataset_text("summary", [json.dumps(_jsonable(_summary_series(result)))])
        return writer.finish(doc.text())


def write_vszh5_spectrogram(result: SpectrogramResult, path: Path) -> Path:
    """Veusz document for a spectrogram result (overview images + channel pages)."""
    freq_divisor, freq_unit_label = _freq_unit(float(np.nanmax(result.freq_hz)))
    bin_kind = "RF" if result.source.startswith("signalshark") else "spectral"
    overview_tags = ("spectrum",)
    with VeuszWriter(path, compress=True, writer_tag=f"{PROGRAM_NAME} {__version__}") as writer:
        doc = VszDoc(f"{PROGRAM_NAME} {__version__}")
        # -- mean and max-hold spectrum
        writer.dataset_1d("spectrum_freq", result.freq_hz / freq_divisor, tags=overview_tags)
        writer.dataset_1d("spectrum_mean_db", result.mean_level_db, tags=overview_tags)
        writer.dataset_1d("spectrum_max_db", result.max_level_db, tags=overview_tags)
        xy_page(doc, "spectrum", [Trace("spectrum_freq", "spectrum_mean_db", "mean"),
                                  Trace("spectrum_freq", "spectrum_max_db", "max hold", style="dashed")],
                title=f"{result.name}: mean and max-hold spectrum ({result.unit_in})",
                xlabel=f"Frequency ({freq_unit_label})", ylabel=f"Level (dB re {result.power_unit})")
        # -- spectrogram image: rows = time (y), columns = frequency (x)
        writer.dataset_2d("spectrum_level_db", result.level_db_image,
                          xcent=result.image_freq_hz / freq_divisor, ycent=result.image_time_s,
                          tags=overview_tags)
        peak_db = float(np.nanmax(result.level_db_image))
        image_page(doc, "spectrogram", "spectrum_level_db", title=f"{result.name}: spectrogram",
                   xlabel=f"Frequency ({freq_unit_label})", ylabel="Time (s)",
                   zlabel=f"dB re {result.power_unit}", zmin=peak_db - 60, zmax=peak_db)
        # -- envelope spectrum of every bin: rows = envelope frequency, columns = bin
        if result.modulation_db_image.shape[0] > 1:
            writer.dataset_2d("modulation_db", result.modulation_db_image,
                              xcent=result.modulation_image_freq_hz / freq_divisor,
                              ycent=result.modulation_freq_hz, tags=("modulation",))
            image_page(doc, "modulation_map", "modulation_db",
                       title=f"{result.name}: envelope spectrum per {bin_kind} bin "
                             f"(spectra at {result.spectra_rate_hz:.4g} Hz)",
                       xlabel=f"{bin_kind} frequency ({freq_unit_label})", ylabel="Envelope frequency (Hz)",
                       zlabel="dB rel. max", zmin=-60.0, zmax=0.0)
            writer.dataset_1d("dominant_modulation_hz", result.dominant_modulation_hz, tags=("modulation",))
            xy_page(doc, "dominant_modulation", [Trace("spectrum_freq", "dominant_modulation_hz", "dominant")],
                    title=f"{result.name}: strongest envelope frequency per {bin_kind} bin",
                    xlabel=f"{bin_kind} frequency ({freq_unit_label})", ylabel="Envelope frequency (Hz)")
        # -- the channels (whole band and the strongest spectral peaks)
        for channel_index, channel in enumerate(result.channels):
            _write_series_pages(writer, doc, channel, f"ch{channel_index}_")
        writer.dataset_text("summary", [json.dumps(_jsonable(_summary_spectrogram(result)))])
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
        written.append(write_vszh5_spectrogram(result, outdir / f"{stem}_envelope_fft.vszh5"))
    else:
        summary = _summary_series(result)
        written.append(write_vszh5_series(result, outdir / f"{stem}_envelope_fft.vszh5"))
    summary_path = outdir / f"{stem}_summary.json"
    summary_path.write_text(json.dumps(_jsonable(summary), indent=2), encoding="utf-8")
    written.append(summary_path)
    if opts.pickle:
        written.append(save_pickle(result, outdir / f"{stem}_result.pkl"))
    if opts.render:
        channel_names = ([channel.name for channel in result.channels]
                         if isinstance(result, SpectrogramResult) else None)
        written += render_vszh5(outdir / f"{stem}_envelope_fft.vszh5", channel_names)
    return written


def render_vszh5(path: Path, channel_names: Sequence[str] | None = None) -> list[Path]:
    """One PDF (bookmark hierarchy, see bookmark_outline) and one PNG per page.

    Uses vszh5_writer.render_pages, which drives an installed Veusz (or the
    veusz Python package) and adds the bookmarks with pypdf. A missing Veusz
    is reported as a warning, not an error: the .vszh5 is already written.
    """
    try:
        return list(render_pages(
            path, png_pages="all",
            bookmarks=lambda page_names: bookmark_outline(page_names, channel_names),
            pdf_info={"title": f"Envelope FFT: {path.stem}", "author": __author__,
                      "subject": f"{PROGRAM_NAME} {__version__}"}))
    except RuntimeError as exc:
        warnings.warn(f"render failed: {exc}", RuntimeWarning, stacklevel=2)
        return []


# %% ===========================================================================
#    BATCH (PARALLEL) PROCESSING
# =============================================================================
def process_file(path: str, opts: Options) -> dict[str, Any]:
    """Read, analyse and write one input; returns a small report (picklable)."""
    started = time.perf_counter()
    data = load_any(path, opts)
    backend = Backend(opts.gpu, opts.fft_workers)
    if isinstance(data, TimeSeries):
        result: SeriesResult | SpectrogramResult = analyse_timeseries(data, opts, backend)
    else:
        result = analyse_spectrumset(data, opts, backend)
    input_path = Path(path)
    outdir = Path(opts.out) if opts.out else input_path.parent / f"{input_path.stem}_fft"
    written = write_outputs(result, outdir, opts)
    report = {"input": str(input_path), "outdir": str(outdir), "files": [str(f) for f in written],
              "seconds": round(time.perf_counter() - started, 3), "backend": backend.note}
    if isinstance(result, SeriesResult):
        report.update(peaks=result.peaks[:5], families=result.families, warnings=result.warnings)
    else:
        report.update(channels=[{"name": c.name, "families": c.families} for c in result.channels],
                      warnings=result.warnings)
    del data, result
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
    return {"time_s": time_s, "quantity": quantity, "quantity_unit": quantity_unit,
            "freq_hz": freq_hz, "amplitude": amplitude, "welch_freq_hz": welch_freq_hz,
            "welch_psd": welch_psd, "fs": uniform.sample_rate_hz, "peaks": peaks, "families": families}


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
    print(f"[live] following {path} (window {window_s:g} s, update {update_s:g} s); Ctrl+C stops")
    try:
        while end_time is None or time.time() < end_time:
            ring.extend(*tail.poll())
            update = live_update(*ring.window(window_s), tail.unit, opts, backend)
            if update:
                strongest = sorted(update["peaks"], key=lambda peak: -peak["amp"])[:4]
                peak_text = ", ".join(f"{peak['f_hz']:.4g} Hz" for peak in strongest)
                family_text = "; ".join(f"f0 {fam['f0_hz']:.4g} Hz = {fam['rpm']:.3g} rpm"
                                        for fam in update["families"][:2])
                print(f"[live] n={ring.n} fs={update['fs']:.4g} Hz  peaks: {peak_text or '-'}  {family_text}")
            time.sleep(update_s)
    except KeyboardInterrupt:
        pass
    return 0


#: Filled by run_live_gui on exit (used by tests and Spyder sessions).
live_gui_state: dict[str, Any] = {}


def run_live_gui(path: str, opts: Options, window_s: float, update_s: float,
                 duration_s: float | None = None) -> int:
    """Live window (Qt.py abstraction on PySide6 + pyqtgraph) with a Light/Dark menu."""
    os.environ.setdefault("QT_PREFERRED_BINDING", "PySide6")
    os.environ.setdefault("PYQTGRAPH_QT_LIB", "PySide6")
    from Qt import QtCore, QtGui, QtWidgets   # Qt.py
    import pyqtgraph as pg

    tail = LiveTail(path, opts)
    ring = _live_ring(path, opts, window_s)
    backend = Backend(opts.gpu, opts.fft_workers)

    class LiveWindow(QtWidgets.QMainWindow):
        """Rolling time series, envelope amplitude spectrum and Welch PSD."""

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle(f"{PROGRAM_NAME} {__version__} - live: {Path(path).name}")
            self.resize(1100, 800)
            self.dark = False
            self.last_update: dict[str, Any] | None = None
            central = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(central)
            self.plot_area = pg.GraphicsLayoutWidget()
            layout.addWidget(self.plot_area)
            self.setCentralWidget(central)
            self.time_plot = self.plot_area.addPlot(row=0, col=0, title="Envelope vs time")
            self.time_plot.setLabel("bottom", "Time (s)")
            self.amplitude_plot = self.plot_area.addPlot(row=1, col=0, title="Envelope amplitude spectrum")
            self.amplitude_plot.setLabel("bottom", "Envelope frequency (Hz)")
            self.amplitude_plot.setLogMode(y=True)
            self.welch_plot = self.plot_area.addPlot(row=2, col=0, title="Welch PSD (dB)")
            self.welch_plot.setLabel("bottom", "Envelope frequency (Hz)")
            self.time_curve = self.time_plot.plot([], [], pen=pg.mkPen("#1f77b4", width=1))
            self.amplitude_curve = self.amplitude_plot.plot([], [], pen=pg.mkPen("#d62728", width=1))
            self.welch_curve = self.welch_plot.plot([], [], pen=pg.mkPen("#2ca02c", width=1))
            self.status = self.statusBar()
            self._build_menus()
            self.apply_theme(False)
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(self.tick)
            self.timer.start(int(update_s * 1000))
            if duration_s:
                QtCore.QTimer.singleShot(int(duration_s * 1000), self.close)

        def _build_menus(self) -> None:
            """File (snapshot, clear, quit), View (Light/Dark), Analysis (probe correction)."""
            file_menu = self.menuBar().addMenu("&File")
            file_menu.addAction("Save snapshot (.vszh5)").triggered.connect(self.save_snapshot)
            file_menu.addAction("Clear buffer (free RAM)").triggered.connect(
                lambda: (ring.clear(), flush_memory()))
            file_menu.addSeparator()
            file_menu.addAction("Quit").triggered.connect(self.close)
            view_menu = self.menuBar().addMenu("&View")
            action_group_class = getattr(QtGui, "QActionGroup", None) or QtWidgets.QActionGroup
            theme_group = action_group_class(self)
            for label, dark in (("Light", False), ("Dark", True)):
                action = view_menu.addAction(label)
                action.setCheckable(True)
                action.setChecked(dark is False)
                action.triggered.connect(lambda _checked=False, d=dark: self.apply_theme(d))
                theme_group.addAction(action)
            analysis_menu = self.menuBar().addMenu("&Analysis")
            correction_action = analysis_menu.addAction("Correct probe response")
            correction_action.setCheckable(True)
            correction_action.setChecked(opts.correct_probe)
            correction_action.toggled.connect(lambda on: setattr(opts, "correct_probe", bool(on)))

        def apply_theme(self, dark: bool) -> None:
            """Light or dark palette for the Qt widgets and the plots.

            Dark: every colour role is set for the active, inactive and
            disabled groups, so menu highlights, tool tips and disabled
            entries are dark-themed too. Light: the style's own standard
            palette. The change reaches every widget on the next pass of the
            event loop (a screenshot taken in the same call is still old).
            """
            self.dark = dark
            app = QtWidgets.QApplication.instance()
            if dark:
                palette = QtGui.QPalette()
                dark_colours = {
                    "Window": "#202124", "WindowText": "#e8eaed", "Base": "#2b2c2f",
                    "AlternateBase": "#303134", "Text": "#e8eaed", "Button": "#303134",
                    "ButtonText": "#e8eaed", "ToolTipBase": "#303134", "ToolTipText": "#e8eaed",
                    "Highlight": "#8ab4f8", "HighlightedText": "#202124", "Light": "#3c4043",
                    "Midlight": "#35363a", "Mid": "#2b2c2f", "Dark": "#17181a", "Shadow": "#000000",
                    "PlaceholderText": "#9aa0a6", "BrightText": "#ffffff", "Link": "#8ab4f8"}
                colour_role_enum = getattr(QtGui.QPalette, "ColorRole", QtGui.QPalette)
                colour_group_enum = getattr(QtGui.QPalette, "ColorGroup", QtGui.QPalette)
                for role_name, colour in dark_colours.items():
                    role = getattr(colour_role_enum, role_name, None)
                    if role is None:                   # role missing in an old Qt
                        continue
                    for group_name in ("Active", "Inactive", "Disabled"):
                        shade = QtGui.QColor(colour)
                        if group_name == "Disabled" and "Text" in role_name:
                            shade = shade.darker(160)  # greyed-out text when disabled
                        palette.setColor(getattr(colour_group_enum, group_name), role, shade)
            else:
                palette = app.style().standardPalette()
            app.setPalette(palette)
            background, foreground = ("#202124", "#e8eaed") if dark else ("w", "k")
            self.plot_area.setBackground(background)
            for plot in (self.time_plot, self.amplitude_plot, self.welch_plot):
                for axis_name in ("left", "bottom"):
                    plot.getAxis(axis_name).setPen(foreground)
                    plot.getAxis(axis_name).setTextPen(foreground)
                plot.titleLabel.setText(plot.titleLabel.text, color=foreground)

        def tick(self) -> None:
            """Read new rows, recompute the spectra and redraw."""
            ring.extend(*tail.poll())
            update = live_update(*ring.window(window_s), tail.unit, opts, backend)
            if not update:
                self.status.showMessage(f"waiting for data ({ring.n} samples)")
                return
            self.last_update = update
            self.time_curve.setData(update["time_s"], update["quantity"])
            self.time_plot.setLabel("left", update["quantity_unit"])
            positive = update["freq_hz"] > 0                 # log axis: no DC
            self.amplitude_curve.setData(update["freq_hz"][positive],
                                         np.maximum(np.nan_to_num(update["amplitude"][positive]), 1e-30))
            self.welch_curve.setData(update["welch_freq_hz"],
                                     10 * np.log10(np.maximum(update["welch_psd"], 1e-300)))
            message = f"{ring.n} samples, fs {update['fs']:.4g} Hz"
            if update["families"]:
                family = update["families"][0]
                message += f" | f0 {family['f0_hz']:.4g} Hz = {family['rpm']:.4g} rpm"
            self.status.showMessage(message)

        def save_snapshot(self) -> None:
            """Analyse the current window fully and write the usual outputs."""
            window_times, window_values = ring.window(window_s)
            if window_times.size < 32:
                return
            snapshot = TimeSeries(Path(path).stem + "_live", window_times - window_times[0],
                                  window_values, tail.unit, source="live")
            result = analyse_timeseries(snapshot, opts, backend)
            outdir = Path(opts.out) if opts.out else Path(path).parent / f"{Path(path).stem}_fft"
            written = write_outputs(result, outdir, opts)
            vszh5_files = [f for f in written if f.suffix == ".vszh5"]
            self.status.showMessage(f"saved {vszh5_files[0].name if vszh5_files else outdir}")

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")          # palette (light/dark) applies to every widget
    window = LiveWindow()
    window.show()
    exit_code = app.exec() if hasattr(app, "exec") else app.exec_()
    live_gui_state["last_update"] = window.last_update
    live_gui_state["samples"] = ring.n
    return int(exit_code or 0)


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
    # 5 readers + analyses on synthetic exports
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
    # 6 .vszh5 structure
    vszh5_path = next(folder.rglob("*_envelope_fft.vszh5"))
    with h5py.File(vszh5_path, "r") as h5_file:
        layout_ok = h5_file["Veusz"].attrs["vsz_format"] == 1 and "document" in h5_file["Veusz/Document"]
    check(".vszh5 layout (Veusz format 1)", layout_ok, vszh5_path.name)
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
    add("inputs", nargs="*", help="files or EHP-50 TS folders")
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
                   h5_time=args.h5_time, snr=args.snr, dyn_range_db=args.dyn_range_db)


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point; returns the process exit code."""
    args = build_parser().parse_args(argv)
    if args.selftest is not None:
        return self_test(args.selftest or None)
    opts = options_from_args(args)
    if args.live:
        live_runner = run_live_console if args.no_gui else run_live_gui
        return live_runner(args.live, opts, args.window_s, args.update, args.live_seconds)
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
# opts = Options(probe="EFD-4091", correct_probe=True, lomb="on")
# print(inspect_input(r"C:\path\to\export.csv", opts))
# series = load_any(r"C:\path\to\export.csv", opts)
# result = analyse_timeseries(series, opts)
# print(result.peaks[:5], result.families)
# write_outputs(result, Path(r"C:\path\to\out"), opts)
# flush_memory()
