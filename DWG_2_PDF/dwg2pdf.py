#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch conversion of 2D AutoCAD drawings (DWG/DXF) to PDF.

Written for the case where a directory tree of 2D AutoCAD drawings has to
become a directory tree of PDFs, repeatably, without a human clicking through
a plot dialog once per sheet -- and where the drawings are old enough that
several of them will not convert cleanly on the first attempt.

Why a *backend* abstraction
---------------------------
DWG is a closed binary format.  There is no pure-Python reader for it, so every
route to a PDF goes through some external program.  Which program you have
available depends on what is installed and on what you are licensed to use, and
those differ between machines.  Rather than hard-code one of them, this module
defines a small :class:`Backend` interface and ships seven implementations.
The CLI probes the machine, picks the best available one, and tells you what it
picked.  If you later install a better tool, nothing here has to change.

The backends, in the default preference order
---------------------------------------------
==== ======================== ============================================
Rank Backend                  Notes
==== ======================== ============================================
1    ``accoreconsole``        AutoCAD's headless core console.  Highest
                              fidelity: real plot styles (CTB/STB), real
                              page setups, real layouts.  Needs AutoCAD.
                              Parallel-safe.
2    ``acad-com``             The FULL AutoCAD, driven over COM with
                              ``Application.Visible = False``.  Same
                              fidelity plus xrefs and SHX fonts, no
                              window.  Windows + ``pywin32``.  SERIAL
                              ONLY -- one COM ``Application`` object.
3    ``qcad``                 QCAD Professional's ``dwg2pdf``.  Best CLI
                              ergonomics of the lot (paper, scale, margin,
                              mono, auto-fit as flags).  Paid, ~modest.
4    ``trueview``             Autodesk DWG TrueView driven by a ``.scr``
                              script.  **DISABLED** -- see the warning
                              below.  Listed for completeness only; it is
                              never placed in an automatic chain.
5    ``oda+ezdxf``            ODA File Converter does DWG->DXF, then ezdxf
                              renders the DXF.  Fully scriptable and cross
                              platform.  *Licence caveat below.*
6    ``libredwg+ezdxf``       GNU LibreDWG ``dwg2dxf`` does DWG->DXF, then
                              ezdxf renders it.  GPL-3, free for any use,
                              but the DWG decoder is less complete.
                              **Bundled** for Windows x86-64 in
                              ``vendor/libredwg-win64/``, so this route
                              needs nothing installed.
7    ``ezdxf``                No external tool at all.  DXF input only.
==== ======================== ============================================

.. warning::
   **DWG TrueView is disabled** (``TrueViewBackend.unreliable = True``).  It
   was tried on a real machine and did not fail gracefully: an
   ``Unhandled Exception c0000027`` (STATUS_UNWIND), and a modal
   *configuration file may be locked* dialog that blocks an unattended run
   indefinitely.  It is excluded from every automatic chain and cannot be
   substituted for ``accoreconsole``.

.. warning::
   **ODA File Converter licence.**  The Open Design Alliance states that its
   free tools may be used by non-members "for non-commercial applications
   only" [ODA-FAQ]_.  If this drawing set is being converted in support of paid
   or contract work, backend 4 is not licensed to you unless your organisation
   is an ODA member.  Backends 1, 2, 3 and 5 have no such restriction.  The
   module therefore never silently selects ``oda+ezdxf``: it must either be the
   only backend present, or be named explicitly with ``--backend``.

Revision history
----------------
Semantic versioning, newest first: External.Internal.Working.

0.3.13
    Documentation revision, no behavioural change.  The module header still
    described SIX backends with ``trueview`` at rank 3 and no mention of
    ``acad-com``; it now matches what the module actually ships, and
    carries the TrueView warning where a reader meets the list.  The
    revision history had been left at 0.1.0 while the module ran 0.3.12 --
    every revision from 0.2.0 forward is now recorded, newest first.
    ``--preset`` help and the worked ``.scr`` example genericised for
    public release.
0.3.12
    ``--recycle-after`` default changed **25 -> 0 (off)**.  Setting
    ``max_tasks_per_child`` silently forces the *spawn* start method, so
    every recycled worker re-imports the entry module before it can take
    another file.  Measured here: 24 trivial tasks complete in 1.21 s with
    recycling off and had NOT completed in two minutes with
    ``--recycle-after 1``.  Worse, the recycles are synchronised -- four
    workers at ``--recycle-after 25`` all respawn at file 100 together,
    which presents exactly as a freeze at the hundredth document.  Recycling
    is now opt-in, for the case ``--report-memory`` actually justifies.
0.3.11
    ``retry-pending`` result status.  A drawing that pass 1 could not
    convert was being reported as ``failed`` before ``acad-com`` had ever
    been tried on it, which read as "AutoCAD was tried and lost" when
    AutoCAD had not run at all.  Pass-1 misses are now ``retry-pending``
    until pass 2 resolves them.  No behavioural change to the conversion
    itself -- this was purely a truthfulness fix in the reporting.
0.3.10
    Documentation and identifier scrub for public release: worked examples,
    preset names and docstrings made generic, no site-, project- or
    user-specific paths anywhere in the shipped files.
0.3.9
    ``--units`` (default ``auto``).  A DXF stores bare numbers, so a
    44 x 34 **inch** ANSI E sheet was being rendered as a 44 x 34
    **millimetre** page.  Resolution order is ``$INSUNITS`` when
    meaningful, then ``$MEASUREMENT`` (0 = English -> inch), then
    millimetres; the resolved factor sets ``Settings.scale``.  Those
    sheets now come out at 1130.7 x 873.5 mm.
0.3.8
    Positional outlier detection in ``--trim-outliers``.  The original test
    found entities that were too *big*; it could not see an entity that is
    ordinary-sized but parked far away.  Added a median-absolute-deviation
    test on entity centres, which recovered a sheet whose extents were
    inflated from 72 x 115 to 4862 x 3654 by two distant strays.
0.3.7
    Bundled decoder now wins over ``PATH`` for ``dwg2dxf``.  conda-forge
    ships LibreDWG 0.11.3876 (2020); ``vendor/`` carries 0.14.8593.
    PATH-first silently preferred the older one -- the one that emitted the
    dangling ``*X`` block of 0.3.6.  Selection is platform-gated so a
    Windows binary is never offered to a POSIX host, and the resolved
    version is reported with a warning when it is old.
0.3.6
    Dangling block references repaired.  LibreDWG can emit an ``INSERT``
    naming a block with no definition; that fails at *render* time, not at
    load time, so the ``recover.readfile`` fallback never fired.  The
    missing block is now created empty -- non-destructive, and the rest of
    the sheet renders.  Also absorbs fontTools' ``'name' table
    stringOffset`` and ezdxf's ``ignoring DIMTXSTY override`` noise,
    explaining each once instead of once per font and per dimension.
    (Logger filters are NOT inherited by child loggers; the filters are
    attached to the exact emitting loggers, which was verified, not
    assumed.)
0.3.5
    AutoCAD script paths quoted.  **In a ``.scr`` file a SPACE is Enter**,
    so an unquoted output path was chopped at every space and its fragments
    executed as commands; AutoCAD exited 0 having written nothing.  Added
    ``--accore-script`` (replace the generated script wholesale) and
    ``--accore-lang``, and the full console is now captured on failure
    rather than a 400-character tail.
0.3.4
    ``--layouts auto``, and it is the new default.  Renders paper space
    where paper space has drawable content and model space otherwise,
    decided **per drawing**.  "Has content" means "has non-VIEWPORT
    entities", with a guaranteed model-space fallback, because a
    viewport-only layout defeated the first version of the test.
0.3.3
    Two-pass parallelism.  A chain ending in the serial-only ``acad-com``
    used to force the whole run to one worker.  Now
    :func:`split_chain_for_parallel` runs the parallel-safe prefix
    concurrently and retries only the failures serially against the full
    chain.  Verified with an injected serial-only backend: 6 drawings, 3
    failing in pass 1, all 3 recovered in pass 2.
0.3.2
    Multiprocessing context chosen deliberately (fork on POSIX, spawn on
    Windows) plus ``freeze_support()``.  Found because a test printed its
    own output four times.
0.3.1
    ``--paper AUTO`` (new default): the sheet size is read from the
    drawing's own paperspace page setup, falling back to FIT when there is
    none.
0.3.0
    ``acad-com`` backend -- the **full AutoCAD**, driven over COM with
    ``Application.Visible = False``: real plot styles, real page setups,
    xrefs and SHX fonts, no window.  Serial only; needs ``pywin32``;
    attaches to an already-running AutoCAD without hiding it.  DWG TrueView
    marked ``unreliable`` and excluded from every automatic chain after it
    crashed in the field (``Unhandled Exception c0000027`` = STATUS_UNWIND)
    and raised a modal *configuration file may be locked* dialog.  Adds
    ``--strategy`` (no-AutoCAD-first / AutoCAD-first / AutoCAD-only /
    single) and the per-drawing fallback chain with a recorded trail.
0.2.0
    Batch-usability revision: ``--preset`` (named ``--filter`` shortcuts),
    ``--filter``, ``--limit``, mtime-aware ``--skip-existing`` resume, and
    the guard that refuses to accept a TrueView console in place of
    ``accoreconsole``.  ``--probe`` supersedes the earlier
    ``--check-env``.
0.1.0
    First internal draft.  Six backends, recursive discovery, process-pool
    parallelism with per-backend serialisation, page/scale/margin control,
    optional merge, JSON+CSV manifest, ``--probe`` and ``--dry-run``.
    Never executed against a real DWG -- no DWG reader was installed.
0.1.0
    First revision proven end-to-end on REAL DWG files (R11, R14, R2000,
    R2004, R2013 -- 5 of 5), by building LibreDWG 0.14.8593 from source in
    the session container.  Testing found five defects, FOUR OF WHICH
    PRODUCED A SILENTLY WRONG PDF rather than an error:

    1. An empty paperspace layout failed the whole drawing, even when
       modelspace had already converted successfully.  Empty and
       unrenderable layouts are now skipped, not fatal.
    2. ``--layouts all`` reported a converted file as failed, orphaning its
       good PDF.  Same root cause; partial success is now success.
    3. **``--as=r2018`` silently emitted DXFs with an EMPTY ENTITIES
       section** whenever the target version did not match the source's
       era -- exit code 0, correct file size, no entities.  The flag is
       gone; see ``LibreDwgEzdxfBackend._dwg_to_dxf`` for the measured
       version matrix.
    4. **An auto-sized ("FIT") page came out 3.4 km across**, because
       drawing units are full scale.  Bounded by ``--max-page-mm``.
    5. **One stray entity spanning 3.4e6 units** (against a median of 838)
       collapsed the real drawing to a speck on the page.  Added
       ``--trim-outliers``, which fits the page to robust extents without
       deleting anything.

    Also repairs degenerate ``(0,0,0)`` extrusion vectors, which made ezdxf
    raise ``ZeroDivisionError`` on R11-era geometry.

References
----------
.. [ODA-FAQ] Open Design Alliance, "What are ODA Viewer and ODA File
   Converter?"  https://www.opendesign.com/faq/question/what-are-oda-viewer-and-oda-file-converter
.. [EZDXF-DRAW] M. Zimmermann, "Drawing / Export Add-on", ezdxf 1.4.4
   documentation.  https://ezdxf.readthedocs.io/en/stable/addons/drawing.html
.. [EZDXF-ODAFC] M. Zimmermann, "ODA File Converter Support", ezdxf 1.4.4
   documentation.  https://ezdxf.readthedocs.io/en/stable/addons/odafc.html
.. [QCAD-CLI] RibbonSoft, "QCAD Command Line Tools".
   https://www.qcad.org/en/qcad-command-line-tools
.. [LIBREDWG] Free Software Foundation, "Programs (LibreDWG 0.13.4)".
   https://www.gnu.org/software/libredwg/manual/html_node/Programs.html
"""

from __future__ import annotations

# --- Standard library -------------------------------------------------------
import argparse
import csv
import dataclasses
import gc
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Optional, Sequence

# ---------------------------------------------------------------------------
# Module metadata.  Semantic revisioning: X.Y.Z, 0.0.1 == first internal draft.
# ---------------------------------------------------------------------------
__revision__ = "0.3.13"
__all__ = [
    "PageSpec",
    "ConversionResult",
    "Backend",
    "EzdxfBackend",
    "OdaEzdxfBackend",
    "LibreDwgEzdxfBackend",
    "QcadBackend",
    "AcCoreConsoleBackend",
    "AcadComBackend",
    "TrueViewBackend",
    "available_backends",
    "select_backend",
    "install_noise_filters",
    "discover_inputs",
    "run_batch",
    "main",
]

_LOG = logging.getLogger("dwg2pdf")

#: Extensions treated as drawings.  Case-insensitive on all platforms.
DRAWING_SUFFIXES = frozenset({".dwg", ".dxf"})

#: Paper sizes understood by ``--paper``, in millimetres, portrait (w, h).
#: ezdxf ships its own table; this one is duplicated so that the non-ezdxf
#: backends (QCAD, AutoCAD) can be given the same vocabulary.
PAPER_SIZES_MM: dict[str, tuple[float, float]] = {
    "A0": (841.0, 1189.0),
    "A1": (594.0, 841.0),
    "A2": (420.0, 594.0),
    "A3": (297.0, 420.0),
    "A4": (210.0, 297.0),
    "LETTER": (215.9, 279.4),
    "LEGAL": (215.9, 355.6),
    "ANSI_A": (215.9, 279.4),
    "ANSI_B": (279.4, 431.8),
    "ANSI_C": (431.8, 558.8),
    "ANSI_D": (558.8, 863.6),
    "ANSI_E": (863.6, 1117.6),
    "ARCH_C": (457.2, 609.6),
    "ARCH_D": (609.6, 914.4),
    "ARCH_E": (914.4, 1219.2),
    "ARCH_E1": (762.0, 1066.8),
    # Neither of these is a paper size.
    #   FIT  -- make the page match the drawing extents (capped, see PageSpec)
    #   AUTO -- take the sheet size from the drawing's own paperspace page
    #           setup, and fall back to FIT when there isn't one
    "FIT": (0.0, 0.0),
    "AUTO": (0.0, 0.0),
}

#: Named path filters -- shorthand for a ``--filter`` regular expression.
#:
#: A drawing archive of any size is mostly parts you do not need on any given
#: day, and typing the same regex repeatedly is how mistakes happen.  Give the
#: subsets you actually use a name here and they become ``--preset <name>``
#: on the command line and a dropdown in the GUI.
#:
#: The entries below are examples showing the two shapes that come up most:
#: a drawing-number prefix, and an alternation of several.  Replace them with
#: your own; the keys are arbitrary strings.  ``all`` is the identity filter
#: and is worth keeping.
#:
#: Example -- a site whose sheets are numbered ``1205xx`` for assemblies and
#: ``1207xx`` for sub-assemblies::
#:
#:     PRESETS = {
#:         "assemblies":     r"1205\d\d",
#:         "sub-assemblies": r"1207\d\d",
#:         "revision-c":     r"_C\b",
#:         "all":            r".",
#:     }
PRESETS: dict[str, str] = {
    "example-prefix": r"^12\d{4}",
    "example-group": r"(_01_|_02_|_03_)",
    "all": r".",
}

#: Where each external tool is usually found.  Probed in order; the first hit
#: wins.  ``shutil.which`` is tried first for all of them, so a tool that is on
#: PATH does not need to appear here at all.
_DEFAULT_TOOL_PATHS: dict[str, tuple[str, ...]] = {
    "ODAFileConverter": (
        r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
        r"C:\Program Files\ODA\ODAFileConverter_title\ODAFileConverter.exe",
        "/usr/bin/ODAFileConverter",
        "/opt/ODAFileConverter/ODAFileConverter",
    ),
    "dwg2pdf": (
        r"C:\Program Files\QCAD\dwg2pdf.bat",
        r"C:\Program Files (x86)\QCAD\dwg2pdf.bat",
        "/usr/bin/dwg2pdf",
        "/opt/qcad/dwg2pdf",
    ),
    "accoreconsole": tuple(
        rf"C:\Program Files\Autodesk\AutoCAD {year}\accoreconsole.exe"
        for year in range(2028, 2012, -1)
    ),
    "dwgviewr": tuple(
        rf"C:\Program Files\Autodesk\DWG TrueView {year} - English\dwgviewr.exe"
        for year in range(2028, 2014, -1)
    ),
    "dwg2dxf": (
        # Bundled first: the distribution ships Windows x86-64 LibreDWG
        # binaries under vendor/, so a fresh Windows machine needs nothing
        # installed to convert DWG without AutoCAD.  _find_tool() resolves
        # these relative to this file, not to the working directory.
        "vendor/libredwg-win64/dwg2dxf.exe",
        "vendor/libredwg-linux-x64/dwg2dxf",
        "/usr/bin/dwg2dxf",
        "/usr/local/bin/dwg2dxf",
    ),
}

#: Directory containing this module, used to resolve bundled binaries.
_MODULE_DIR = Path(__file__).resolve().parent

#: Tools whose bundled copy should be preferred over anything on PATH.
#: See the note in :func:`_find_tool`.
_PREFER_BUNDLED = frozenset({"dwg2dxf"})


def _bundled_runs_here(relative_path: str) -> bool:
    """Can this bundled binary actually execute on this platform?

    The vendor directories are named by platform (``libredwg-win64``,
    ``libredwg-linux-x64``).  Preferring a bundled copy is only sensible
    when it can run: a Windows ``.exe`` sitting in the distribution is a
    perfectly good file on Linux and a completely useless one, and
    selecting it would shadow a working decoder on PATH.
    """
    token = relative_path.replace("\\", "/").lower()
    if "-win" in token:
        return os.name == "nt"
    if "-linux" in token:
        return os.name == "posix" and platform.system() == "Linux"
    if "-macos" in token or "-darwin" in token:
        return platform.system() == "Darwin"
    return True


# ===========================================================================
# Small helpers
# ===========================================================================
def _find_tool(stem: str) -> Optional[Path]:
    """Locate an external executable by name.

    Parameters
    ----------
    stem : str
        Bare program name, e.g. ``"accoreconsole"``.  The ``.exe``/``.bat``
        suffix is supplied by the platform search.

    Returns
    -------
    pathlib.Path or None
        Absolute path to the executable, or ``None`` if it cannot be found.

    Notes
    -----
    ``shutil.which`` is consulted first so that a user who has put the tool on
    PATH -- or who keeps it somewhere unusual -- always wins over the built-in
    guesses in :data:`_DEFAULT_TOOL_PATHS`.
    """
    # Bundled binaries FIRST for the DWG decoder.  A conda-forge install
    # puts libredwg 0.11.3876 (uploaded 2020-11-17) on PATH; the copy
    # shipped in vendor/ is 0.14.  Six years of decoder fixes separate them
    # -- the 0.11 decoder is what emitted the dangling "*X" block reference
    # that killed a sheet at render time.  PATH-first would silently prefer
    # the older one, so for this tool the bundled copy wins and PATH is the
    # fallback.  Everything else still resolves from PATH first.
    if stem in _PREFER_BUNDLED:
        for candidate in _DEFAULT_TOOL_PATHS.get(stem, ()):
            path = Path(candidate)
            if path.is_absolute() or not _bundled_runs_here(candidate):
                continue
            path = _MODULE_DIR / path
            if path.is_file():
                return path

    hit = shutil.which(stem)
    if hit:
        return Path(hit)
    # On Windows a QCAD-style ".bat" wrapper is not always picked up by which()
    # when the suffix is omitted, so try the common suffixes explicitly.
    if platform.system() == "Windows":
        for suffix in (".exe", ".bat", ".cmd"):
            hit = shutil.which(stem + suffix)
            if hit:
                return Path(hit)
    for candidate in _DEFAULT_TOOL_PATHS.get(stem, ()):
        path = Path(candidate)
        if not path.is_absolute():
            # A relative entry names a bundled binary; resolve it against the
            # module's own directory so it is found no matter where the user
            # happens to be when they run this.
            path = _MODULE_DIR / path
        if path.is_file():
            return path
    return None


def _run(
    args: Sequence[str],
    *,
    timeout: float,
    cwd: Optional[Path] = None,
) -> subprocess.CompletedProcess:
    """Run an external command, capturing both streams.

    Parameters
    ----------
    args : sequence of str
        Argument vector.  Never passed through a shell, so paths containing
        spaces need no quoting.
    timeout : float
        Seconds before the child is killed.  Every backend sets one: a CAD
        engine that hits an unexpected modal prompt will otherwise wait
        forever, and in a batch of a thousand sheets that is a hang, not an
        error.
    cwd : pathlib.Path, optional
        Working directory for the child.

    Returns
    -------
    subprocess.CompletedProcess
        With ``stdout`` and ``stderr`` decoded as text, errors replaced.
    """
    _LOG.debug("exec: %s", " ".join(str(a) for a in args))
    return subprocess.run(
        [str(a) for a in args],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
        cwd=str(cwd) if cwd else None,
        check=False,
    )


def is_trueview(path: Path | str) -> bool:
    """True if this executable belongs to DWG TrueView rather than AutoCAD.

    Used to keep TrueView's plotting-incapable ``accoreconsole.exe`` out of the
    AutoCAD backend; see :meth:`AcCoreConsoleBackend._exe` for why that matters.
    """
    low = str(path).lower()
    return "trueview" in low or "dwg true" in low


def _human_bytes(n: float) -> str:
    """Format a byte count for the log, e.g. ``"1.4 MiB"``."""
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TiB"


def _rss_bytes() -> Optional[int]:
    """Resident set size of this process, or ``None`` if unavailable.

    Used only for the ``--report-memory`` diagnostic.  ``psutil`` is optional;
    on Linux the value is read straight from ``/proc`` if psutil is absent.
    """
    try:
        import psutil  # type: ignore

        return int(psutil.Process().memory_info().rss)
    except Exception:
        pass
    try:
        with open("/proc/self/statm", "r", encoding="ascii") as handle:
            pages = int(handle.read().split()[1])
        return pages * os.sysconf("SC_PAGE_SIZE")
    except Exception:
        return None


# ===========================================================================
# Third-party log noise
# ===========================================================================
class _ThirdPartyNoiseFilter(logging.Filter):
    """Absorb known-benign chatter from ezdxf and fontTools.

    Both libraries log, at WARNING or ERROR, conditions that they then
    handle correctly and that the user can do nothing about.  On a cold
    start with a real drawing set that is dozens of alarming-looking lines
    before anything has gone wrong.  This filter drops exactly those
    messages, counts them, and explains each kind once.

    What is absorbed, and why each is harmless
    ------------------------------------------
    ``'name' table stringOffset incorrect. Expected: 222; Actual: 224``
        From ``fontTools.ttLib.tables._n_a_m_e``, at ERROR, while ezdxf
        builds its font-manager cache by opening every installed font.

        fontTools checks that the OpenType ``name`` table's
        ``stringOffset`` equals ``6 + count * 12`` -- string storage packed
        immediately behind the name records -- and complains when a font
        pads that gap.  The specification defines the field only as "Offset
        to start of string storage (from start of table)" [MS-NAME]; it
        does not require the packed layout, so the font is not clearly
        malformed.  And fontTools' very next statement is
        ``stringData = data[stringOffset:]`` -- it uses the real offset and
        reads the font correctly.  Purely cosmetic, logged at ERROR.

    ``Required text style #0 does not exist, ignoring DIMTXSTY override.``
        From ``ezdxf`` (``entities/dimension.py``), at WARNING, once per
        DIMENSION entity carrying the override.

        A DIMENSION may override its dimension style's text style by
        handle.  Here the handle is **#0**, the DXF null handle, which
        means "no object" -- so the drawing is overriding the text style
        with nothing.  ezdxf looks it up, does not find it, says so, and
        ignores the override, which leaves the dimension using its
        DIMSTYLE's own text style.  That is the correct outcome.

        It comes from the DWG decoder writing an explicit null handle
        instead of omitting the field, so it appears once per dimensioned
        sheet and says nothing about the geometry.

    Everything not listed is passed through untouched -- including
    ``skipping malformed name record``, which really does mean a broken
    font, and every ezdxf warning about the drawing itself.

    Attachment matters
    ------------------
    The filter must be attached to the logger that *creates* the record, or
    to a handler.  **Logger filters are not inherited by child loggers**:
    ``Logger.handle`` consults only its own filters, and propagation to an
    ancestor's handlers in ``callHandlers`` does not re-run the ancestor's
    filters.  A filter on ``fontTools`` therefore does nothing about
    records logged on ``fontTools.ttLib.tables._n_a_m_e`` -- verified, and
    the reason an earlier version of this filter silently absorbed nothing.
    :func:`install_noise_filters` attaches to the exact emitting loggers
    and offers itself as a handler filter as well.

    Attributes
    ----------
    counts : dict
        Per-pattern tally of what has been absorbed.

    .. [MS-NAME] Microsoft Corp., "name - Naming Table", *OpenType
       Specification*.
       https://learn.microsoft.com/en-us/typography/opentype/spec/name
    """

    #: ``(key, substring, one-line explanation)`` for each absorbed message.
    BENIGN: tuple[tuple[str, str, str], ...] = (
        (
            "font-name-table",
            "'name' table stringOffset incorrect",
            "a system font pads its OpenType 'name' table; fontTools flags "
            "it at ERROR but reads the font correctly, so it is cosmetic",
        ),
        (
            "dimtxsty-null-handle",
            "ignoring DIMTXSTY override",
            "a dimension overrides its text style with the DXF null handle "
            "#0, i.e. with nothing; ezdxf ignores the override and keeps "
            "the dimension style's own text style, which is correct",
        ),
    )

    def __init__(self) -> None:
        super().__init__()
        self.counts: dict[str, int] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        """Return ``False`` for a benign message, ``True`` for anything else."""
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - a bad record is not our problem
            return True

        for key, token, why in self.BENIGN:
            if token not in message:
                continue
            seen = self.counts.get(key, 0) + 1
            self.counts[key] = seen
            if seen == 1:
                _LOG.info("Suppressing a benign %s notice: %s.", key, why)
                _LOG.debug("first occurrence was: %s", message)
            return False
        return True

    def summary(self) -> str:
        """One line describing what was absorbed, or ``""`` if nothing was."""
        if not self.counts:
            return ""
        parts = ["%s x%d" % (k, n) for k, n in sorted(self.counts.items())]
        return "suppressed benign third-party notices: " + ", ".join(parts)


#: The shared filter instance, so callers can read its tallies afterwards.
NOISE_FILTER = _ThirdPartyNoiseFilter()

#: Loggers that actually create the absorbed records.  These are the exact
#: names, not parents: see the "Attachment matters" note above.
_NOISY_LOGGERS = (
    "ezdxf",
    "fontTools",
    "fontTools.ttLib.tables._n_a_m_e",
    "fontTools.ttLib.tables._c_m_a_p",
    "fontTools.ttLib",
)


def install_noise_filters() -> _ThirdPartyNoiseFilter:
    """Attach :data:`NOISE_FILTER` to the loggers that emit the noise.

    Returns
    -------
    _ThirdPartyNoiseFilter
        The shared filter; read ``.counts`` or call ``.summary()`` after a
        run to report what was absorbed.

    Notes
    -----
    Attaching to a handler as well is a useful backstop when a library
    logs from a module this list does not name; the GUI does that with its
    own handler.  Attaching to the root logger's *handlers* would work
    too, but attaching to the root *logger* would not: the record is
    filtered by the logger it was created on, not by its ancestors.
    """
    for name in _NOISY_LOGGERS:
        logger = logging.getLogger(name)
        if NOISE_FILTER not in logger.filters:
            logger.addFilter(NOISE_FILTER)
    return NOISE_FILTER


#: Backwards-compatible aliases (this filter used to cover fonts only).
FONT_NOISE_FILTER = NOISE_FILTER
install_font_noise_filter = install_noise_filters


# ===========================================================================
# Value objects
# ===========================================================================
@dataclasses.dataclass(frozen=True)
class PageSpec:
    """Everything about *how* a drawing is laid onto a page.

    Kept separate from the backend so that the same request can be handed to
    any of them.  Not every backend honours every field -- ``ezdxf`` has no
    concept of a named AutoCAD page setup, for instance -- and each backend's
    ``convert`` docstring says what it ignores.

    Attributes
    ----------
    paper : str
        Key into :data:`PAPER_SIZES_MM`, or one of two special values.

        ``"FIT"`` sizes the page to the drawing extents (bounded by
        ``max_page_mm``).  It never crops, which makes it the safe default
        for a drawing set nobody has inspected yet.

        ``"AUTO"`` asks the *drawing* what sheet it was set up for: the size
        stored in its paperspace page setup, which is what the person who
        drew it chose when they last plotted it.  When a layout carries no
        usable page setup -- true of any modelspace-only drawing -- AUTO
        falls back to FIT for that sheet, so a mixed archive still converts
        in one pass.  See :meth:`EzdxfBackend._auto_page_from_layout`.
    units : str
        What one drawing unit means: ``"auto"``, ``"mm"``, ``"inch"``,
        ``"ft"``, ``"cm"`` or ``"m"``.

        This decides the *physical size* of a fitted page and it matters
        more than it sounds.  A DXF stores coordinates as bare numbers, so
        a 44 x 34 unit ANSI E sheet becomes a 44 x 34 **millimetre** page --
        a legible drawing at 1/25th of its intended size -- unless
        something says those units were inches.

        ``"auto"`` asks the drawing: ``$INSUNITS`` when it is set to
        something meaningful, otherwise ``$MEASUREMENT`` (0 = imperial,
        1 = metric), otherwise millimetres.  Older US drawings often carry
        ``$INSUNITS`` 0 (unitless) with ``$MEASUREMENT`` 0, so auto reads
        them as inches -- which turns a 54 mm page into the 1118 x 864 mm
        ANSI E sheet the drawing actually is.
    landscape : bool
        Swap width and height.  Ignored when ``paper == "FIT"``.
    max_page_mm : float
        Upper bound on an auto-sized (``"FIT"``) page, in millimetres.  A CAD
        drawing is modelled at full scale, so an unbounded fit page can come
        out kilometres across; see the CAP note in ``_build_page``.  Default
        1189 mm, the long edge of ISO A0.  ``0`` disables the bound.
    trim_outliers : bool
        Fit the page to the drawing's *robust* extents, excluding stray
        far-flung entities from the fit.  Off by default because it changes
        what the page shows; see ``_robust_render_box``.
    outlier_factor : float
        How many times the 95th-percentile entity span an entity must exceed
        before it is treated as an outlier.  Default 20.
    margin_mm : float
        Uniform margin on all four sides.
    scale : float
        Drawing units per page unit, as a plain ratio.  ``0.0`` means "fit the
        drawing to the page", which is what you want unless the sheets are
        meant to be measured off.
    layouts : str
        ``"auto"``, ``"model"``, ``"paper"`` (every paperspace layout),
        ``"all"``, or an explicit layout name.

        ``"auto"`` renders paperspace where paperspace has content and
        modelspace otherwise, deciding per drawing.  That is the right mode
        for a mixed or uncatalogued archive: ``"paper"`` on a
        modelspace-only drawing finds AutoCAD's empty default ``Layout1``
        and renders nothing, while ``"model"`` on a drawing with a real
        title-block layout discards the sheet that was set up.
    monochrome : bool
        Force every entity to black on white.  This is what most plotted
        engineering drawings want, and it is what a CTB plot style usually
        does in AutoCAD.
    lineweight_scale : float
        Multiplier on DXF lineweights.  Thin-line drawings often need ~2.0 to
        be legible at A3.
    background : str
        ``"white"``, ``"black"``, ``"off"`` (transparent) or ``"default"``.
    dpi : int
        Only meaningful for raster fallbacks; carried here so the manifest
        records it.
    """

    paper: str = "FIT"
    units: str = "auto"
    landscape: bool = False
    max_page_mm: float = 1189.0
    trim_outliers: bool = False
    outlier_factor: float = 20.0
    margin_mm: float = 5.0
    scale: float = 0.0
    layouts: str = "model"
    monochrome: bool = True
    lineweight_scale: float = 1.0
    background: str = "white"
    dpi: int = 300

    def size_mm(self) -> tuple[float, float]:
        """Return ``(width, height)`` in millimetres, honouring orientation.

        Returns
        -------
        tuple of float
            ``(0.0, 0.0)`` for ``"FIT"``, which every backend reads as
            "derive the page from the drawing".
        """
        if self.paper.upper() in ("FIT", "AUTO"):
            return 0.0, 0.0
        try:
            width, height = PAPER_SIZES_MM[self.paper.upper()]
        except KeyError as exc:  # pragma: no cover - guarded by argparse
            raise ValueError(
                f"unknown paper size {self.paper!r}; "
                f"known: {', '.join(sorted(PAPER_SIZES_MM))}"
            ) from exc
        if self.landscape and width and height:
            width, height = height, width
        return width, height


@dataclasses.dataclass
class ConversionResult:
    """Outcome of converting one source drawing.

    One of these is produced per input file whatever happens, including for
    skips and failures, so the manifest is a complete census of the input tree
    rather than a list of successes.

    Attributes
    ----------
    source : pathlib.Path
        The input drawing.
    outputs : list of pathlib.Path
        Zero or more PDFs.  More than one when ``--layouts`` expands to
        several layouts and the backend writes one file each.
    backend : str
        Name of the backend that ran.
    status : str
        ``"ok"``, ``"skipped"``, ``"failed"`` or ``"dry-run"``.
    seconds : float
        Wall-clock time for this file.
    message : str
        Human-readable detail; the error text on failure.
    entity_count : int
        Number of DXF entities rendered, where the backend can count them.
        A sheet reporting zero entities converted "successfully" is the
        classic signature of a wrong layout selection, so it is worth having
        in the manifest.
    """

    source: Path
    outputs: list[Path] = dataclasses.field(default_factory=list)
    backend: str = ""
    status: str = "failed"
    seconds: float = 0.0
    message: str = ""
    entity_count: int = 0

    def as_row(self) -> dict[str, Any]:
        """Flatten to a dict suitable for :mod:`csv` and :mod:`json`."""
        return {
            "source": str(self.source),
            "outputs": ";".join(str(p) for p in self.outputs),
            "n_outputs": len(self.outputs),
            "backend": self.backend,
            "status": self.status,
            "seconds": round(self.seconds, 3),
            "entity_count": self.entity_count,
            "message": self.message,
        }


# ===========================================================================
# Backend interface
# ===========================================================================
class Backend:
    """Base class for a DWG/DXF-to-PDF conversion route.

    A backend is responsible for exactly one thing: turning a single source
    drawing into one or more PDFs.  Discovery, parallelism, retries and
    reporting all live in :func:`run_batch` and are shared.

    Subclasses set the class attributes below and implement
    :meth:`_convert_impl`.

    Attributes
    ----------
    name : str
        Short identifier used by ``--backend`` and written to the manifest.
    rank : int
        Preference order; lower is better.  :func:`select_backend` sorts on it.
    reads_dwg : bool
        Whether the backend can open ``.dwg`` directly (or via its own
        conversion step).  A ``False`` backend is offered only for ``.dxf``.
    parallel_safe : bool
        Whether several instances may run at once.  ``False`` for anything
        that drives a GUI application, because two copies of DWG TrueView
        fighting over the foreground window is not a batch process.
    needs_licence_optin : bool
        ``True`` marks a backend whose licence terms may not cover the user's
        situation.  Such a backend is never auto-selected when an alternative
        exists; see the ODA warning in the module docstring.
    unreliable : bool
        ``True`` marks a backend that has been observed to fail in the field
        in ways this code cannot work around.  It is excluded from every
        automatic chain and can only be reached by naming it explicitly.
        Currently only DWG TrueView; see :class:`TrueViewBackend`.
    """

    name: str = "abstract"
    rank: int = 99
    reads_dwg: bool = False
    parallel_safe: bool = True
    needs_licence_optin: bool = False
    unreliable: bool = False

    def __init__(self, timeout: float = 300.0) -> None:
        """
        Parameters
        ----------
        timeout : float
            Per-file wall-clock limit in seconds, passed to every child
            process this backend spawns.
        """
        self.timeout = timeout

    # -- discovery ---------------------------------------------------------
    @classmethod
    def available(cls) -> bool:
        """Whether this backend can run on this machine right now."""
        raise NotImplementedError

    @classmethod
    def describe(cls) -> str:
        """One-line description of what was found, for ``--probe``."""
        return cls.name

    # -- conversion --------------------------------------------------------
    def convert(self, source: Path, out_dir: Path, spec: PageSpec) -> ConversionResult:
        """Convert one drawing, catching everything.

        This wrapper exists so that a backend implementation can raise freely
        and a single bad sheet still cannot abort a thousand-sheet batch.

        Parameters
        ----------
        source : pathlib.Path
            Input ``.dwg`` or ``.dxf``.
        out_dir : pathlib.Path
            Directory to write into.  Created if absent.
        spec : PageSpec
            Page and plot-style request.

        Returns
        -------
        ConversionResult
            ``status`` is ``"ok"`` only if at least one non-empty PDF landed
            on disk.
        """
        started = time.perf_counter()
        result = ConversionResult(source=source, backend=self.name)
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            outputs, n_entities = self._convert_impl(source, out_dir, spec)
            # Trust nothing: a CAD engine can exit 0 and write no file, or
            # write a zero-byte file, and both must read as a failure here.
            good = [p for p in outputs if p.is_file() and p.stat().st_size > 0]
            if not good:
                result.status = "failed"
                result.message = "backend reported success but wrote no non-empty PDF"
            else:
                result.status = "ok"
                result.outputs = good
                result.entity_count = n_entities
                result.message = f"{len(good)} page file(s), " + ", ".join(
                    _human_bytes(p.stat().st_size) for p in good[:4]
                )
        except subprocess.TimeoutExpired:
            result.status = "failed"
            result.message = f"timed out after {self.timeout:.0f} s"
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all
            result.status = "failed"
            result.message = f"{type(exc).__name__}: {exc}"
            _LOG.debug("traceback for %s:\n%s", source, traceback.format_exc())
        finally:
            result.seconds = time.perf_counter() - started
        return result

    def _convert_impl(
        self, source: Path, out_dir: Path, spec: PageSpec
    ) -> tuple[list[Path], int]:
        """Do the actual work.  Subclass hook.

        Returns
        -------
        tuple
            ``(list_of_written_pdf_paths, entity_count)``.  ``entity_count``
            may be ``0`` where the backend cannot count.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 6. ezdxf -- pure Python, DXF only
# ---------------------------------------------------------------------------
class EzdxfBackend(Backend):
    """Render a DXF with ezdxf's drawing add-on and the PyMuPDF backend.

    This is the only backend with no external program at all, and it is the
    engine underneath the two DWG backends that work by first converting to
    DXF.  It produces true vector PDF -- text stays selectable, curves stay
    curves -- and it honours layers, colours, lineweights and linetypes.

    Its one structural limitation, stated by the add-on's own documentation
    [EZDXF-DRAW]_, is that there is no 3D rendering engine: everything is
    projected onto the xy-plane, and a paperspace VIEWPORT renders as a top
    view.  For a set of *2D* drawings, which is what this module was written
    for, that limitation costs nothing.
    """

    name = "ezdxf"
    rank = 7
    reads_dwg = False
    parallel_safe = True

    @classmethod
    def available(cls) -> bool:
        """True if ezdxf and PyMuPDF both import."""
        try:
            import ezdxf  # noqa: F401
            from ezdxf.addons.drawing import pymupdf  # noqa: F401

            return True
        except Exception:
            return False

    @classmethod
    def describe(cls) -> str:
        try:
            import ezdxf

            return f"ezdxf {ezdxf.__version__} + PyMuPDF (DXF input only)"
        except Exception:
            return "ezdxf (not importable)"

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _build_config(spec: PageSpec):
        """Translate a :class:`PageSpec` into an ezdxf ``Configuration``.

        The mapping is worth spelling out because the enum names are not
        obvious:

        * ``ColorPolicy.BLACK`` draws every entity black regardless of its
          layer colour -- the vector equivalent of a monochrome CTB.
        * ``LineweightPolicy.ABSOLUTE`` uses the DXF lineweight in millimetres
          as-is, which is what a plotted drawing expects.
        * ``BackgroundPolicy.WHITE`` matters because the DXF default is a
          dark modelspace background, and a PDF full of black rectangles is
          not what anybody wants to print.
        """
        from ezdxf.addons.drawing import config as dwg_config

        return dwg_config.Configuration(
            color_policy=(
                dwg_config.ColorPolicy.BLACK
                if spec.monochrome
                else dwg_config.ColorPolicy.COLOR
            ),
            background_policy={
                "white": dwg_config.BackgroundPolicy.WHITE,
                "black": dwg_config.BackgroundPolicy.BLACK,
                "off": dwg_config.BackgroundPolicy.OFF,
                "default": dwg_config.BackgroundPolicy.DEFAULT,
            }.get(spec.background, dwg_config.BackgroundPolicy.WHITE),
            lineweight_policy=dwg_config.LineweightPolicy.ABSOLUTE,
            lineweight_scaling=spec.lineweight_scale,
            # ACCURATE line policy renders linetypes properly rather than as
            # solid lines; on a drawing full of centre- and hidden-lines that
            # is the difference between a usable PDF and a wrong one.
            line_policy=dwg_config.LinePolicy.ACCURATE,
            hatch_policy=dwg_config.HatchPolicy.NORMAL,
        )

    #: Millimetres per drawing unit, by name.
    UNIT_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0,
               "inch": 25.4, "in": 25.4, "ft": 304.8, "feet": 304.8}

    #: $INSUNITS code -> unit name.  0 means "unitless", which is why the
    #: resolver has to fall through to $MEASUREMENT for those drawings.
    INSUNITS = {1: "inch", 2: "ft", 4: "mm", 5: "cm", 6: "m"}

    @classmethod
    def _mm_per_unit(cls, doc, spec: PageSpec) -> tuple[float, str]:
        """Decide how many millimetres one drawing unit represents.

        Returns
        -------
        tuple
            ``(mm_per_unit, explanation)``.

        Notes
        -----
        Order of evidence, most to least specific:

        1. ``spec.units`` when the user named a unit -- always wins.
        2. ``$INSUNITS``, the drawing's own declaration, when it is set to
           something other than 0 (unitless).
        3. ``$MEASUREMENT``: 0 = English, 1 = metric.  This is a coarser
           signal -- it selects which hatch-pattern and linetype files
           AutoCAD uses -- but on a drawing with ``$INSUNITS`` 0 it is the
           only statement about units the file makes, and for a US
           engineering drawing "English" means inches.
        4. Millimetres, as the least surprising default.
        """
        if spec.units and spec.units.lower() != "auto":
            name = spec.units.lower()
            if name in cls.UNIT_MM:
                return cls.UNIT_MM[name], f"forced by --units {name}"
            raise ValueError(f"unknown unit {spec.units!r}")

        try:
            insunits = int(doc.header.get("$INSUNITS", 0) or 0)
        except Exception:  # noqa: BLE001
            insunits = 0
        if insunits in cls.INSUNITS:
            name = cls.INSUNITS[insunits]
            return cls.UNIT_MM[name], f"$INSUNITS={insunits} ({name})"

        try:
            measurement = int(doc.header.get("$MEASUREMENT", 0) or 0)
        except Exception:  # noqa: BLE001
            measurement = 0
        if measurement == 0:
            return 25.4, "$INSUNITS unset; $MEASUREMENT=0 (English) -> inch"
        return 1.0, "$INSUNITS unset; $MEASUREMENT=1 (metric) -> mm"

    @staticmethod
    def _build_page(spec: PageSpec, dxf_layout=None, mm_per_unit: float = 1.0):
        """Build the ezdxf ``Page`` and ``Settings`` for one layout.

        Parameters
        ----------
        spec : PageSpec
            The user's request.
        dxf_layout : optional
            A paperspace ``DXFLayout``.  When given and ``spec.paper`` is
            ``"FIT"``, the sheet size is taken from the drawing's own page
            setup, which is almost always the right answer for a drawing that
            has real title-block layouts.

        Returns
        -------
        tuple
            ``(Page, Settings)``.
        """
        from ezdxf.addons.drawing import layout as dwg_layout

        margins = dwg_layout.Margins.all(spec.margin_mm)

        # THE CAP, and why "fit the page to the drawing" needs one.
        #
        # An auto-sized page (width = height = 0) takes its size from the
        # drawing's extents *in drawing units*, and a CAD drawing is modelled
        # at full scale.  A 100 m reflector is 100,000 units across, so the
        # "page" comes out 100 m wide.  Measured here on a real DWG before this
        # guard existed: a page 3411867 x 2727540 mm -- 3.4 km of paper.  The
        # PDF is produced without complaint; it is the *renderer* that then
        # refuses it ("Overly large image"), and a viewer shows a blank sheet.
        #
        # max_width/max_height bound the auto-sized page and let ezdxf scale
        # the content down to fit.  The default is 1189 mm, the long edge of
        # ISO A0, which comfortably covers every ANSI and ARCH sheet as well.
        cap = float(spec.max_page_mm) if spec.max_page_mm > 0 else 0.0

        if spec.paper.upper() in ("FIT", "AUTO"):
            if dxf_layout is not None:
                try:
                    page = dwg_layout.Page.from_dxf_layout(dxf_layout)
                    # from_dxf_layout brings the drawing's own margins; the
                    # explicit --margin overrides them only if the user asked.
                    if spec.margin_mm > 0:
                        page = dataclasses.replace(page, margins=margins)
                    page = dataclasses.replace(
                        page, max_width=cap, max_height=cap
                    )
                except Exception:
                    page = dwg_layout.Page(
                        0, 0, dwg_layout.Units.mm, margins,
                        max_width=cap, max_height=cap,
                    )
            else:
                # Width/height of 0 tells ezdxf to size the page to content --
                # see the CAP note below for why the maxima are not optional.
                page = dwg_layout.Page(
                    0, 0, dwg_layout.Units.mm, margins,
                    max_width=cap, max_height=cap,
                )
        else:
            width, height = spec.size_mm()
            page = dwg_layout.Page(width, height, dwg_layout.Units.mm, margins)

        # THE UNIT SCALE.  Page units are millimetres, so content measured
        # in drawing units has to be multiplied by millimetres-per-unit or
        # a 44-inch sheet comes out 44 mm across.  An explicit plot scale
        # composes with it: --scale 0.02 on an inch drawing is
        # 0.02 * 25.4 mm per unit.
        settings = dwg_layout.Settings(
            fit_page=(spec.scale == 0.0),
            scale=(spec.scale * mm_per_unit if spec.scale > 0.0
                   else mm_per_unit),
            # Keep hairlines visible: a 0-width DXF lineweight would otherwise
            # render as a sub-pixel stroke that some PDF viewers drop.
            min_stroke_width=0.05,
            fixed_stroke_width=0.15,
        )
        return page, settings

    @staticmethod
    def _sanitize(doc) -> int:
        """Repair decoder artefacts in place.  Returns the number of repairs.

        Two defects are fixed, both produced by DWG decoders rather than by
        the drawing, and both fatal to rendering if left alone.

        **1. Dangling block references.**  An ``INSERT`` may name a block
        that has no ``BLOCK`` definition -- observed in the field as an
        ``INSERT`` referring to ``"*X"``, a truncated anonymous-block name.
        Nothing about this shows up when the file is *loaded*: the renderer
        raises ``DXFStructureError: Required block definition for "*X" does
        not exist`` from ``explode.virtual_block_reference_entities`` when
        it tries to expand the reference, so the whole sheet fails at draw
        time and a ``recover.readfile`` fallback never gets a chance.

        The repair is to create the missing block as an **empty** block.
        That is the least destructive option available: the INSERT resolves,
        expands to nothing, and every other entity on the sheet renders.
        Deleting the INSERT would work too but changes the entity count and
        loses the placeholder; an empty block keeps the file's shape.  There
        was no geometry to draw either way -- the definition genuinely is
        not in the file.

        **2. Degenerate extrusion vectors.**  See below.

        Extrusion detail
        ----------------
        An entity's *extrusion* is the normal of its object coordinate system.
        The DXF specification's default is ``(0, 0, 1)`` and a valid extrusion
        is a non-zero vector, because the first thing any consumer does with it
        is normalise it.

        Old drawings decoded from DWG do not always honour that.  A zero
        extrusion ``(0, 0, 0)`` on an ``INSERT`` makes ezdxf raise
        ``ZeroDivisionError`` deep inside ``Vec3.normalize()`` while computing
        the block reference's transformation matrix -- observed here on an
        R11-era file, which is precisely the vintage a 1990s drawing archive is
        full of.  The traceback names ``ucs.py`` and gives no hint that the
        cause is one bad group code on one entity.

        Substituting the specification's own default is the conservative
        repair: for a 2D drawing lying in the world xy-plane, ``(0, 0, 1)`` is
        what the extrusion was always meant to be.  The source file is never
        modified -- this operates on the in-memory document only.
        """
        from ezdxf.math import Vec3

        repaired = 0

        # ---- 1. dangling block references --------------------------------
        # Collect every block name an INSERT refers to, across modelspace,
        # every paperspace, and every block definition (a nested INSERT
        # inside a block definition breaks every use of that block).
        missing: set[str] = set()

        def collect_missing(container) -> None:
            for entity in container:
                if entity.dxftype() != "INSERT":
                    continue
                try:
                    name = entity.dxf.name
                except Exception:  # noqa: BLE001
                    continue
                if name and name not in doc.blocks:
                    missing.add(name)

        try:
            for lay in doc.layouts:
                collect_missing(lay)
            for block in doc.blocks:
                collect_missing(block)
        except Exception as exc:  # noqa: BLE001 - never fail the scan
            _LOG.debug("block-reference scan failed: %s", exc)

        for name in sorted(missing):
            try:
                doc.blocks.new(name)
                repaired += 1
                _LOG.info(
                    "created empty definition for missing block %r "
                    "(dangling reference from the DWG decoder)", name
                )
            except Exception as exc:  # noqa: BLE001
                _LOG.debug("could not create block %r: %s", name, exc)

        # ---- 2. degenerate extrusion vectors -----------------------------
        def fix(container) -> int:
            n = 0
            for entity in container:
                if not entity.dxf.hasattr("extrusion"):
                    continue
                try:
                    if Vec3(entity.dxf.extrusion).magnitude > 1e-12:
                        continue
                except Exception:  # noqa: BLE001 - unreadable value counts as bad
                    pass
                entity.dxf.extrusion = (0.0, 0.0, 1.0)
                n += 1
            return n

        # Modelspace, every paperspace, and every block definition -- a bad
        # extrusion inside a block definition breaks every INSERT of it, so
        # the blocks matter as much as the layouts.
        for lay in doc.layouts:
            repaired += fix(lay)
        for block in doc.blocks:
            repaired += fix(block)
        return repaired

    @staticmethod
    def _robust_render_box(layout_obj, spec: PageSpec):
        """Find the drawing's *real* extents, ignoring stray entities.

        Returns ``(render_box_or_None, note_or_empty_string)``.

        Two kinds of stray, and they need different tests
        ------------------------------------------------
        **Outliers in size.**  One entity far larger than the rest --
        measured on a real DWG, an ``INSERT`` spanning 3,411,857 units
        against a median of 838 and a next-largest of 14,300, almost
        certainly a block reference carrying an absurd scale factor.

        **Outliers in position.**  Entities of perfectly ordinary size
        parked a long way from everything else.  Measured on a real
        archive: the sheet occupies (3130, -1846) to (3174, -1812),
        44 x 34 units, while a single ``TEXT`` sits at (4873, -3640) and a
        frozen layer sits at (11, 5).  Full extents 4862 x 3654;
        real content 72 x 115.  **Every entity is small** -- the largest
        spans 44 units, the median 0.5 -- so a size test sees nothing wrong
        and the page is still sized to the empty space between them.

        The first version of this method tested size only, which is why it
        reported "no outliers found" on exactly the drawings that needed it.
        Both tests now run.

        The positional test
        -------------------
        Entity centres are reduced to their median and their median absolute
        deviation (MAD) -- a robust scale estimator that a handful of strays
        cannot inflate, unlike a standard deviation.  An entity whose centre
        lies more than ``outlier_factor`` MADs from the median on either
        axis is excluded from the page fit.  With everything genuinely
        clustered on one sheet the MAD is small and the strays stand out by
        orders of magnitude; with content legitimately spread across the
        sheet the MAD is comparable to the sheet and nothing is excluded.

        Nothing is deleted either way.  The box is passed to the backend as
        ``render_box``, so an excluded entity is still drawn -- it is simply
        no longer allowed to define the page -- and the note is returned so
        the manifest records that it happened.
        """
        from ezdxf import bbox
        from ezdxf.math import BoundingBox2d

        records = []
        for entity in layout_obj:
            try:
                box = bbox.extents([entity], fast=True)
            except Exception:  # noqa: BLE001 - a bad entity is not fatal here
                continue
            if not box.has_data:
                continue
            centre = box.center
            records.append(
                (max(box.size.x, box.size.y), float(centre.x),
                 float(centre.y), box)
            )

        if len(records) < 8:
            # Too few entities for a percentile or a MAD to mean anything.
            return None, ""

        def _median(values: list[float]) -> float:
            ordered = sorted(values)
            mid = len(ordered) // 2
            if len(ordered) % 2:
                return ordered[mid]
            return 0.5 * (ordered[mid - 1] + ordered[mid])

        def _mad(values: list[float], centre: float) -> float:
            return _median([abs(v - centre) for v in values])

        spans = [r[0] for r in records]
        xs = [r[1] for r in records]
        ys = [r[2] for r in records]

        # --- size test -----------------------------------------------
        p95_span = sorted(spans)[int(0.95 * (len(spans) - 1))]
        span_limit = p95_span * spec.outlier_factor

        # --- position test --------------------------------------------
        med_x, med_y = _median(xs), _median(ys)
        mad_x, mad_y = _mad(xs, med_x), _mad(ys, med_y)
        # A MAD of zero (everything on one line) would reject everything;
        # fall back to the span scale, which is never zero for real content.
        scale_x = mad_x if mad_x > 0 else max(p95_span, 1e-9)
        scale_y = mad_y if mad_y > 0 else max(p95_span, 1e-9)
        pos_limit_x = scale_x * spec.outlier_factor
        pos_limit_y = scale_y * spec.outlier_factor

        keep, n_size, n_pos = [], 0, 0
        for span, cx, cy, box in records:
            if span > span_limit:
                n_size += 1
                continue
            if (abs(cx - med_x) > pos_limit_x
                    or abs(cy - med_y) > pos_limit_y):
                n_pos += 1
                continue
            keep.append(box)

        dropped = n_size + n_pos
        if dropped == 0 or not keep:
            return None, ""

        merged = BoundingBox2d()
        for box in keep:
            merged.extend([box.extmin, box.extmax])

        full = BoundingBox2d()
        for _s, _x, _y, box in records:
            full.extend([box.extmin, box.extmax])

        reasons = []
        if n_size:
            reasons.append(
                "%d oversized (largest span %.0f vs p95 %.0f)"
                % (n_size, max(spans), p95_span)
            )
        if n_pos:
            reasons.append("%d far from the rest" % n_pos)
        note = (
            "%d stray entity/entities excluded from the page fit "
            "[%s]; extents %.0fx%.0f -> %.0fx%.0f"
            % (dropped, ", ".join(reasons),
               full.size.x, full.size.y, merged.size.x, merged.size.y)
        )
        return merged, note

    def _iter_layouts(self, doc, spec: PageSpec):
        """Yield ``(name, layout_object, dxf_layout_or_None)`` per requested layout.

        The three modes exist because drawing sets are not consistent.  Older
        2D drawings frequently live entirely in modelspace with a title block
        drawn as geometry; newer ones use paperspace layouts.  ``--layouts
        all`` covers a mixed set at the cost of some redundant pages.
        """
        want = spec.layouts.lower()
        if want in ("model", "modelspace"):
            yield "Model", doc.modelspace(), None
            return

        paper_names = list(doc.layout_names_in_taborder())
        # layout_names_in_taborder() puts "Model" first; drop it for paper modes.
        paper_names = [n for n in paper_names if n.lower() != "model"]

        if want == "auto":
            # AUTO: use paperspace only where paperspace actually has
            # something on it, otherwise fall back to modelspace.
            #
            # This is the mode for an archive nobody has catalogued.  Asking
            # for "paper" on a drawing whose content lives in modelspace
            # finds AutoCAD's default empty Layout1 and renders nothing --
            # a whole run of failures whose real cause is one wrong setting.
            # Asking for "model" on a drawing with a proper title-block
            # layout throws away the sheet the draughtsman set up.  AUTO
            # decides per drawing, so a mixed set converts in one pass.
            # "Has content" has to mean "has something that can be DRAWN",
            # not merely "has entities".  Every paperspace layout carries at
            # least one VIEWPORT, and AutoCAD's default Layout1/Layout2
            # contain nothing else.  The drawing add-on has no 3D engine and
            # does not render viewport contents, so a viewport-only layout
            # yields an empty bounding box -- entities present, nothing
            # renderable.  Counting raw entities picks those layouts and then
            # fails; counting non-viewport entities does not.
            with_content = []
            for name in paper_names:
                psp = doc.paperspace(name)
                drawable = sum(
                    1 for e in psp if e.dxftype() not in ("VIEWPORT",)
                )
                if drawable > 0:
                    with_content.append((name, psp))
            if with_content:
                for name, psp in with_content:
                    yield name, psp, psp.dxf_layout
            else:
                yield "Model", doc.modelspace(), None
            return

        if want in ("paper", "paperspace"):
            for name in paper_names:
                psp = doc.paperspace(name)
                yield name, psp, psp.dxf_layout
        elif want == "all":
            yield "Model", doc.modelspace(), None
            for name in paper_names:
                psp = doc.paperspace(name)
                yield name, psp, psp.dxf_layout
        else:
            # An explicit layout name.  Match case-insensitively, because
            # "Layout1" and "LAYOUT1" both turn up in real drawing sets.
            for name in paper_names:
                if name.lower() == want:
                    psp = doc.paperspace(name)
                    yield name, psp, psp.dxf_layout
                    return
            raise KeyError(
                f"layout {spec.layouts!r} not in {source_layouts(doc)!r}"
            )

    def _convert_impl(
        self, source: Path, out_dir: Path, spec: PageSpec
    ) -> tuple[list[Path], int]:
        """Render every requested layout of a DXF to PDF.

        Notes
        -----
        Memory: the ``Drawing`` is dropped and the garbage collector run
        before returning.  ezdxf holds the whole DXF in memory as a Python
        object graph, so a large drawing can be hundreds of megabytes; in a
        long batch inside one process that would accumulate.  In the default
        process-pool mode each file is handled by a worker that is recycled
        every ``--recycle-after`` files, which bounds it further.
        """
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext
        from ezdxf.addons.drawing.pymupdf import PyMuPdfBackend

        doc = None
        written: list[Path] = []
        n_entities = 0
        try:
            # recover.readfile() is deliberately not the default: it is much
            # slower, and a DXF written by ODA or LibreDWG moments ago is
            # clean.  Fall back to it only when the strict reader refuses.
            try:
                doc = ezdxf.readfile(str(source))
            except ezdxf.DXFStructureError:
                from ezdxf import recover

                doc, _auditor = recover.readfile(str(source))

            repaired = self._sanitize(doc)
            if repaired:
                _LOG.info("%s: applied %d decoder-artefact repair(s)",
                          source.name, repaired)

            mm_per_unit, unit_why = self._mm_per_unit(doc, spec)
            if abs(mm_per_unit - 1.0) > 1e-9:
                _LOG.info("%s: 1 drawing unit = %g mm (%s)",
                          source.name, mm_per_unit, unit_why)

            cfg = self._build_config(spec)
            skipped_layouts: list[str] = []
            outlier_notes: list[str] = []
            attempted = 0

            for layout_name, layout_obj, dxf_layout in self._iter_layouts(doc, spec):
                attempted += 1

                # An empty layout is not an error.  Nearly every drawing
                # carries AutoCAD's default "Layout1"/"Layout2" whether or not
                # anyone ever drew on them, and a real drawing set is full of
                # them.  Skip those quietly rather than failing a sheet that
                # converted perfectly well in modelspace.
                layout_entities = sum(1 for _ in layout_obj)
                if layout_entities == 0:
                    skipped_layouts.append(f"{layout_name} (empty)")
                    continue

                page, settings = self._build_page(spec, dxf_layout, mm_per_unit)

                # Decide what the page should be fitted to, before drawing.
                render_box = None
                if spec.trim_outliers:
                    render_box, note = self._robust_render_box(layout_obj, spec)
                    if note:
                        outlier_notes.append(f"{layout_name}: {note}")

                backend = PyMuPdfBackend()
                Frontend(RenderContext(doc), backend, config=cfg).draw_layout(layout_obj)
                try:
                    pdf_bytes = backend.get_pdf_bytes(
                        page, settings=settings, render_box=render_box
                    )
                except ValueError as exc:
                    # ezdxf raises "empty bounding box" when a layout holds
                    # only entities it cannot draw -- most often a paperspace
                    # containing nothing but a VIEWPORT, since the add-on has
                    # no 3D engine and does not render viewport contents
                    # [EZDXF-DRAW].  That is a limitation to report, not a
                    # conversion failure.
                    if "empty bounding box" in str(exc).lower():
                        skipped_layouts.append(f"{layout_name} (nothing renderable)")
                        continue
                    raise

                stem = source.stem
                # Only decorate the filename when more than one page file can
                # result, so the common single-layout case gives "sheet.pdf".
                if spec.layouts.lower() in ("model", "modelspace"):
                    target = out_dir / f"{stem}.pdf"
                else:
                    safe = "".join(
                        ch if ch.isalnum() or ch in "-_." else "_" for ch in layout_name
                    )
                    target = out_dir / f"{stem}__{safe}.pdf"

                target.write_bytes(pdf_bytes)
                written.append(target)
                n_entities += layout_entities

            if not written and spec.layouts.lower() == "auto":
                # Belt and braces.  The non-viewport test above catches the
                # common case, but a layout could hold only some other
                # entity this renderer cannot draw.  AUTO promises a PDF
                # wherever the drawing has one to give, so fall back to
                # modelspace rather than failing a sheet that has content.
                _LOG.info(
                    "%s: paper space produced nothing renderable; "
                    "falling back to model space",
                    source.name,
                )
                msp = doc.modelspace()
                msp_entities = sum(1 for _ in msp)
                if msp_entities:
                    page, settings = self._build_page(spec, None, mm_per_unit)
                    render_box = None
                    if spec.trim_outliers:
                        render_box, note = self._robust_render_box(msp, spec)
                        if note:
                            outlier_notes.append("Model: " + note)
                    backend = PyMuPdfBackend()
                    Frontend(
                        RenderContext(doc), backend, config=cfg
                    ).draw_layout(msp)
                    target = out_dir / f"{source.stem}.pdf"
                    target.write_bytes(
                        backend.get_pdf_bytes(
                            page, settings=settings, render_box=render_box
                        )
                    )
                    written.append(target)
                    n_entities += msp_entities

            if not written:
                detail = (
                    "; ".join(skipped_layouts) if skipped_layouts
                    else "no layouts matched"
                )
                hint = ""
                if spec.layouts.lower() in ("paper", "paperspace"):
                    # By far the most common cause, and the fix is one
                    # setting -- so say so rather than leaving the user to
                    # infer it from an empty-layout message.
                    hint = (
                        "  This drawing's content is almost certainly in "
                        "MODEL space: the paper space layout is empty. "
                        "Set Layouts to 'Automatic' (or 'Model space only') "
                        "and run again."
                    )
                raise RuntimeError(
                    f"nothing to render for --layouts {spec.layouts!r}: "
                    f"{detail}.{hint}"
                )
            if skipped_layouts:
                _LOG.info(
                    "%s: skipped %d of %d layout(s): %s",
                    source.name,
                    len(skipped_layouts),
                    attempted,
                    ", ".join(skipped_layouts),
                )
            for note in outlier_notes:
                _LOG.warning("%s: %s", source.name, note)
        finally:
            # Explicit teardown; see the memory note in the docstring.
            del doc
            gc.collect()
        return written, n_entities


def source_layouts(doc) -> list[str]:
    """Return the layout names of an ezdxf document, for error messages."""
    try:
        return list(doc.layout_names_in_taborder())
    except Exception:
        return []


# ---------------------------------------------------------------------------
# A shared mixin for "convert DWG to DXF with tool X, then render with ezdxf"
# ---------------------------------------------------------------------------
class _DwgViaDxfBackend(Backend):
    """Common machinery for the two convert-then-render backends.

    Both ODA File Converter and LibreDWG's ``dwg2dxf`` do the same job -- turn
    a ``.dwg`` into a ``.dxf`` -- so the only thing that differs between the
    two backends is the argument vector.  Everything after that is
    :class:`EzdxfBackend`.

    The intermediate DXF goes in a per-file temporary directory that is
    removed on the way out, so a batch never accumulates scratch files next to
    the user's drawings.
    """

    reads_dwg = True
    parallel_safe = True

    def _dwg_to_dxf(self, source: Path, work_dir: Path) -> Path:
        """Convert one DWG to DXF inside *work_dir*.  Subclass hook."""
        raise NotImplementedError

    def _convert_impl(
        self, source: Path, out_dir: Path, spec: PageSpec
    ) -> tuple[list[Path], int]:
        renderer = EzdxfBackend(timeout=self.timeout)
        if source.suffix.lower() == ".dxf":
            # Nothing to convert; hand it straight to the renderer.
            return renderer._convert_impl(source, out_dir, spec)

        with tempfile.TemporaryDirectory(prefix="dwg2pdf_") as tmp:
            work = Path(tmp)
            dxf_path = self._dwg_to_dxf(source, work)
            if not dxf_path.is_file() or dxf_path.stat().st_size == 0:
                raise RuntimeError(
                    f"{self.name}: DWG->DXF step produced no usable DXF for {source.name}"
                )
            # Render under the *source* stem, not the temporary one, so the
            # output filename tracks the drawing rather than the scratch file.
            staged = work / (source.stem + ".dxf")
            if dxf_path != staged:
                dxf_path.replace(staged)
            return renderer._convert_impl(staged, out_dir, spec)


# ---------------------------------------------------------------------------
# 4. ODA File Converter + ezdxf
# ---------------------------------------------------------------------------
class OdaEzdxfBackend(_DwgViaDxfBackend):
    """DWG -> DXF with the ODA File Converter, then render with ezdxf.

    The ODA File Converter is the reference implementation for reading DWG:
    the Open Design Alliance maintains the format libraries that most non-
    Autodesk CAD software is built on, so its DWG support is complete and
    current.  This is the most reliable non-Autodesk route to a correct DXF.

    Command line, quoted from ezdxf's own wrapper [EZDXF-ODAFC]_::

        ODAFileConverter "Input Folder" "Output Folder" version type recurse audit [filter]

    with ``version`` in ``ACAD9``..``ACAD2018``, ``type`` in ``DWG``/``DXF``/
    ``DXB``, and ``recurse``/``audit`` as ``"0"``/``"1"``.  Note that it takes
    *folders*, not files -- hence the per-file temporary input directory
    below.

    .. warning::
       Non-members of the ODA may use this tool for non-commercial
       applications only [ODA-FAQ]_.  See the module docstring.
    """

    name = "oda+ezdxf"
    rank = 5
    needs_licence_optin = True

    #: Output DXF version.  R2018 keeps everything the source could hold; an
    #: older target would silently drop newer entity types.
    DXF_VERSION = "ACAD2018"

    @classmethod
    def _exe(cls) -> Optional[Path]:
        return _find_tool("ODAFileConverter")

    @classmethod
    def available(cls) -> bool:
        return cls._exe() is not None and EzdxfBackend.available()

    @classmethod
    def describe(cls) -> str:
        exe = cls._exe()
        return (
            f"ODA File Converter at {exe} + ezdxf  [NON-COMMERCIAL USE ONLY "
            f"for ODA non-members]"
            if exe
            else "ODA File Converter (not found)"
        )

    def _dwg_to_dxf(self, source: Path, work_dir: Path) -> Path:
        exe = self._exe()
        if exe is None:
            raise RuntimeError("ODAFileConverter not found")

        # ODAFileConverter works folder-to-folder, so give it a folder that
        # contains exactly this one drawing.  Doing otherwise would convert
        # every sibling on every call.
        in_dir = work_dir / "in"
        out_dir = work_dir / "out"
        in_dir.mkdir()
        out_dir.mkdir()
        shutil.copy2(source, in_dir / source.name)

        args = [
            exe,
            str(in_dir),
            str(out_dir),
            self.DXF_VERSION,
            "DXF",
            "0",              # recurse: no, the folder holds one file
            "0",              # audit: off; audit costs time and this is a copy
            source.name,      # input filter
        ]
        env_note = ""
        if platform.system() == "Linux":
            # The converter is a Qt application and wants a display even in
            # command-line mode; ezdxf's wrapper solves this with xvfb and so
            # do we.  Absence of xvfb-run is not fatal on a machine with a
            # display, so this is a best-effort prefix.
            if shutil.which("xvfb-run"):
                args = ["xvfb-run", "-a"] + [str(a) for a in args]
                env_note = " (under xvfb-run)"
        proc = _run(args, timeout=self.timeout)
        # ODAFileConverter's exit code is not reliable across versions, so the
        # real test is whether a DXF appeared.
        produced = sorted(out_dir.glob("*.dxf")) + sorted(out_dir.glob("*.DXF"))
        if not produced:
            raise RuntimeError(
                f"ODAFileConverter{env_note} produced no DXF "
                f"(rc={proc.returncode}): {proc.stderr.strip()[:400]}"
            )
        return produced[0]


# ---------------------------------------------------------------------------
# 5. LibreDWG + ezdxf
# ---------------------------------------------------------------------------
class LibreDwgEzdxfBackend(_DwgViaDxfBackend):
    """DWG -> DXF with GNU LibreDWG's ``dwg2dxf``, then render with ezdxf.

    LibreDWG is GPL-3, so unlike the ODA converter there is no restriction on
    commercial use.  The trade-off is completeness: the project's own manual
    describes parts of the toolchain as experimental, and its direct SVG and
    PostScript writers support only a handful of entity types [LIBREDWG]_.
    Going through ``dwg2dxf`` and letting ezdxf do the rendering side-steps
    that, because only the *decoder* is being relied on.

    Treat this as the licence-clean fallback, and spot-check a few sheets
    against a known-good render before trusting a whole batch to it.
    """

    name = "libredwg+ezdxf"
    rank = 6

    @classmethod
    def _exe(cls) -> Optional[Path]:
        return _find_tool("dwg2dxf")

    @classmethod
    def available(cls) -> bool:
        return cls._exe() is not None and EzdxfBackend.available()

    #: Oldest decoder version considered current enough to trust silently.
    MIN_VERSION = (0, 13)

    @classmethod
    def version(cls) -> Optional[tuple[int, ...]]:
        """Return the decoder's version as a tuple, or ``None``.

        Worth knowing rather than guessing: conda-forge ships libredwg
        0.11.3876 (uploaded 2020-11-17), which is six years of decoder
        fixes behind the 0.14 bundled here, and is the version that emitted
        the dangling ``"*X"`` block reference seen in the field.
        """
        exe = cls._exe()
        if exe is None:
            return None
        try:
            proc = _run([exe, "--version"], timeout=20.0)
            text = (proc.stdout or "") + (proc.stderr or "")
            match = re.search(r"(\d+)\.(\d+)\.?(\d+)?", text)
            if match:
                return tuple(
                    int(g) for g in match.groups(default="0")
                )
        except Exception:  # noqa: BLE001 - a version probe is not critical
            pass
        return None

    @classmethod
    def describe(cls) -> str:
        exe = cls._exe()
        if exe is None:
            return "LibreDWG (not found)"
        ver = cls.version()
        vtext = ".".join(str(v) for v in ver) if ver else "unknown version"
        bundled = " [bundled]" if _MODULE_DIR in Path(exe).parents else ""
        warn = ""
        if ver and ver[:2] < cls.MIN_VERSION:
            warn = (
                "  <-- OLD: %s predates many decoder fixes; the copy in "
                "vendor/ is newer" % vtext
            )
        return f"LibreDWG dwg2dxf {vtext} at {exe}{bundled} + ezdxf{warn}"

    def _dwg_to_dxf(self, source: Path, work_dir: Path) -> Path:
        """Decode one DWG to DXF, letting LibreDWG choose the DXF version.

        .. warning::
           **Do not pass ``--as=``.**  Revision 0.0.1 passed ``--as=r2018`` on
           the reasoning that the newest target keeps the most entity types.
           It does the opposite: when the requested version does not match the
           source's native era, LibreDWG writes a structurally valid DXF whose
           **ENTITIES section is empty** -- and it exits 0 while doing it.  The
           result is a well-formed, correctly-sized, completely blank drawing,
           which converts to a blank PDF with no error anywhere in the chain.

           Measured on LibreDWG 0.14.8593 across five source versions, entity
           count in the emitted modelspace:

           ==============  ======  =====  =====  =====
           source           none   r2000  r2013  r2018
           ==============  ======  =====  =====  =====
           r11 entities-2d     13      0      0      0
           r14 v.dwg           17     17      0      0
           r2000 example       67     67      0      0
           r2004 example       67      0     67     67
           r2013 example       67      0     67     67
           ==============  ======  =====  =====  =====

           The "none" column is the only one that is correct for every input.
           So no version is requested, and the DXF comes out in whatever
           version LibreDWG considers native to the source.  ezdxf reads all
           of them, so nothing is lost by not asking.
        """
        exe = self._exe()
        if exe is None:
            raise RuntimeError("dwg2dxf not found")
        if not getattr(type(self), "_version_warned", False):
            type(self)._version_warned = True
            ver = self.version()
            if ver and ver[:2] < self.MIN_VERSION:
                _LOG.warning(
                    "using LibreDWG %s from %s -- this is an old decoder "
                    "(conda-forge ships 0.11 from 2020). The copy bundled "
                    "in vendor/ is newer and fixes decode defects such as "
                    "dangling block references. Remove the old one from "
                    "PATH, or let the bundled copy be found first.",
                    ".".join(str(v) for v in ver), exe,
                )
        target = work_dir / (source.stem + ".dxf")
        # -y overwrites without prompting.  No --as: see the warning above.
        proc = _run([exe, "-y", "-o", str(target), str(source)], timeout=self.timeout)
        if not target.is_file():
            raise RuntimeError(
                f"dwg2dxf failed (rc={proc.returncode}): {proc.stderr.strip()[:400]}"
            )
        return target


# ---------------------------------------------------------------------------
# 2. QCAD Professional dwg2pdf
# ---------------------------------------------------------------------------
class QcadBackend(Backend):
    """QCAD Professional's bundled ``dwg2pdf`` command-line tool.

    Of all the routes here this is the one designed for exactly this job: it
    reads DWG and DXF directly, writes PDF directly, and exposes paper size,
    scale, margin, auto-fit, orientation, monochrome and block/layout
    selection as ordinary flags [QCAD-CLI]_.  There is no intermediate file
    and nothing to go wrong in a prompt sequence.

    It ships only with QCAD *Professional*; the free Community edition does
    not include the command-line tools or the DWG import plugin.

    Options used below, from the published option list [QCAD-CLI]_:

    ``-f``
        Force overwrite of an existing output file.
    ``-o FILE``
        Output path.
    ``-p WxH`` / ``-p A4``
        Paper size in millimetres or by name.
    ``-l``
        Landscape.
    ``-a``
        Auto-fit and centre the drawing on the paper.
    ``-s SCALE``
        Fixed scale, e.g. ``1:50``.
    ``-m M``
        Margin.
    ``-n``
        Monochrome.
    ``-block NAMES``
        Export the named layouts/blocks rather than the default view.
    """

    name = "qcad"
    rank = 3
    reads_dwg = True
    parallel_safe = True

    @classmethod
    def _exe(cls) -> Optional[Path]:
        return _find_tool("dwg2pdf")

    @classmethod
    def available(cls) -> bool:
        return cls._exe() is not None

    @classmethod
    def describe(cls) -> str:
        exe = cls._exe()
        return f"QCAD Professional dwg2pdf at {exe}" if exe else "QCAD dwg2pdf (not found)"

    def _convert_impl(
        self, source: Path, out_dir: Path, spec: PageSpec
    ) -> tuple[list[Path], int]:
        exe = self._exe()
        if exe is None:
            raise RuntimeError("QCAD dwg2pdf not found")

        target = out_dir / f"{source.stem}.pdf"
        args: list[str] = [str(exe), "-f", "-o", str(target)]

        if spec.paper.upper() != "FIT":
            width, height = PAPER_SIZES_MM[spec.paper.upper()]
            # Pass explicit millimetres rather than the name: QCAD's own name
            # table and ours could differ, and an explicit WxH cannot.
            args += ["-p", f"{width:g}x{height:g}"]
            if spec.landscape:
                args.append("-l")
        else:
            # No paper given: let QCAD choose orientation from the extents.
            args.append("--auto-orientation")

        if spec.scale > 0.0:
            args += ["-s", f"{spec.scale:g}"]
        else:
            args.append("-a")            # auto-fit and centre

        args += ["-m", f"{spec.margin_mm:g}"]

        if spec.monochrome:
            args.append("-n")

        # A named layout maps onto QCAD's -block selection.  "model", "paper"
        # and "all" have no direct equivalent, so they are left to the default
        # (which exports the current/main view) and noted in the manifest.
        want = spec.layouts.lower()
        if want not in ("model", "modelspace", "paper", "paperspace", "all"):
            args += [f"-block={spec.layouts}"]

        args.append(str(source))

        proc = _run(args, timeout=self.timeout)
        if not target.is_file():
            raise RuntimeError(
                f"dwg2pdf failed (rc={proc.returncode}): "
                f"{(proc.stderr or proc.stdout).strip()[:400]}"
            )
        return [target], 0


# ---------------------------------------------------------------------------
# 1. AutoCAD accoreconsole
# ---------------------------------------------------------------------------
class AcCoreConsoleBackend(Backend):
    """AutoCAD's headless core console, driven by a generated ``.scr`` script.

    This is the highest-fidelity route by a distance, because it *is* AutoCAD:
    plot styles, page setups, xrefs, SHX fonts, dynamic blocks and annotative
    scaling all behave exactly as they do when a person plots the sheet.  If
    the machine has AutoCAD, use this.

    Invocation::

        accoreconsole.exe /i drawing.dwg /s script.scr /l en-US

    The generated script drives ``-EXPORTPDF``, the command-line form of
    EXPORTPDF, which avoids the long ``-PLOT`` prompt sequence.

    .. note::
       The prompt sequence of ``-EXPORTPDF`` varies slightly between AutoCAD
       releases and localisations.  The script below is written for a US
       English install and is deliberately kept in one place
       (:meth:`_script_text`) so that it can be adjusted once if a particular
       release disagrees.  Run with ``--verbose`` to see the console
       transcript, which shows exactly which prompt went unanswered.
    """

    name = "accoreconsole"
    rank = 1
    reads_dwg = True

    #: Replaces the generated ``.scr`` entirely; ``{output}`` is substituted
    #: with the target PDF path.  Set from ``--accore-script``.
    script_override: Optional[str] = None
    #: ``/l`` language code.  Left unset by default: passing a language pack
    #: the machine does not have fails with "Unable to Process Configuration
    #: File", which reads like a plot problem and is not one.
    language: Optional[str] = None
    #: AutoCAD is licensed per seat and the core console counts against it,
    #: so several at once may fail on licence checkout.  Kept True because a
    #: network licence usually permits it; drop to False with --workers 1 if
    #: licence errors appear.
    parallel_safe = True

    @classmethod
    def _exe(cls) -> Optional[Path]:
        """Locate AutoCAD's accoreconsole.exe -- never DWG TrueView's.

        .. warning::
           **DWG TrueView installs a file called ``accoreconsole.exe`` too**,
           in a folder directly beside AutoCAD's under ``C:\\Program
           Files\\Autodesk``, and it starts up and accepts ``/i`` and ``/s``
           identically.  What it does not have is the plotting engine:
           ``-EXPORTPDF`` and ``-PLOT`` do not exist there, so every drawing
           fails with nothing but the startup banner.

           Worse, the obvious discovery order walks the Autodesk folder in
           reverse alphabetical order to get the newest release first -- and
           ``"DWG TrueView 2025 - English"`` sorts *above* ``"AutoCAD 2025"``.
           On a machine with both, the naive search picks the wrong one every
           single time.  That defect cost a full field run.

           So candidates are ranked with AutoCAD first and a TrueView console
           is rejected outright rather than used as a last resort: it cannot
           plot at all, so it is not a fallback, it is a guaranteed failure.
        """
        found = _find_tool("accoreconsole")
        if found is not None and is_trueview(found):
            return None
        return found

    @classmethod
    def available(cls) -> bool:
        return cls._exe() is not None

    @classmethod
    def describe(cls) -> str:
        exe = cls._exe()
        if exe:
            return f"AutoCAD core console at {exe}"
        stray = _find_tool("accoreconsole")
        if stray is not None and is_trueview(stray):
            return (
                f"accoreconsole found but it is DWG TrueView's ({stray}) -- "
                f"TrueView has no plotting engine, so it is not usable"
            )
        return "accoreconsole (not found)"

    @staticmethod
    def _script_text(target: Path, spec: PageSpec) -> str:
        """Build the ``.scr`` contents for one drawing.

        .. warning::
           **In an AutoCAD script a SPACE is Enter.**  Autodesk's own
           guidance is explicit: a name containing spaces must be given
           *in double quotes* [CADF-SPACE].  Without them a path like::

               C:\\Drawings\\Drawing Set\\Assembly Details\\sheet.pdf

           is chopped at every space: AutoCAD takes ``C:\\Drawings\\Drawing``
           as the filename and then feeds ``Set``, ``Assembly``,
           ``Details`` ... to the command line as commands.  It exits 0
           having written no PDF, and the console tail is a meaningless
           fragment.  Observed
           exactly that on a path containing four separate spaces, which is
           an entirely ordinary thing for a path to contain.  Hence the
           quoting below, which is not cosmetic.

        Notes
        -----
        A blank line is also Enter, so the trailing newline is significant
        and the file must end with one.  ``FILEDIA 0`` suppresses the file
        dialog that would otherwise block a headless run.

        The ``-EXPORTPDF`` prompt sequence varies a little between AutoCAD
        releases and localisations, which is why this is the only place it
        is written and why ``--accore-script`` exists to replace it
        wholesale.

        .. [CADF-SPACE] CAD Studio, "In my AutoCAD script file (.SCR) I
           cannot enter a name containing a space", tip 14045.
           https://www.cadforum.cz/en/in-my-autocad-script-file-scr-i-cannot-enter-a-name-with-space-tip14045
        """
        want = spec.layouts.lower()
        if want in ("all", "paper", "paperspace"):
            export_scope = "_A"     # All layouts
        else:
            export_scope = "_C"     # Current layout
        lines = [
            "FILEDIA",              # set on its own line: a space is Enter
            "0",
            "CMDDIA",
            "0",
            "-EXPORTPDF",
            export_scope,
            # QUOTED -- see the warning above.  This is the fix for
            # "accoreconsole wrote no PDF (rc=0)".
            '"%s"' % target,
            "FILEDIA",
            "1",
            "",
        ]
        return "\n".join(lines)

    def _convert_impl(
        self, source: Path, out_dir: Path, spec: PageSpec
    ) -> tuple[list[Path], int]:
        exe = self._exe()
        if exe is None:
            raise RuntimeError("accoreconsole not found")

        target = out_dir / f"{source.stem}.pdf"
        script_text = self.script_override or self._script_text(target, spec)
        if self.script_override:
            # A user-supplied template: substitute the output path.  It is
            # the caller's job to quote it if their template needs it.
            script_text = script_text.replace("{output}", str(target))

        with tempfile.TemporaryDirectory(prefix="dwg2pdf_scr_") as tmp:
            script = Path(tmp) / "export.scr"
            script.write_text(script_text, encoding="ascii", errors="replace")
            args = [exe, "/i", str(source), "/s", str(script)]
            if self.language:
                # /l with a language pack the machine does not have is a
                # documented cause of "Unable to Process Configuration
                # File", so it is omitted unless explicitly requested.
                args += ["/l", self.language]
            proc = _run(args, timeout=self.timeout)

        if not target.is_file():
            # Report the WHOLE console, not a tail.  A truncated tail once
            # reduced a real failure to the single character "d", which said
            # nothing about the cause (an unquoted path with spaces).
            console = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            _LOG.debug("accoreconsole script was:\n%s", script_text)
            _LOG.debug("accoreconsole console output:\n%s", console)
            raise RuntimeError(
                f"accoreconsole wrote no PDF (rc={proc.returncode}). "
                f"Console: {' '.join(console.split())[:900] or '(empty)'}"
            )
        return [target], 0


# ---------------------------------------------------------------------------
# 1b. Full AutoCAD over COM, with the window hidden
# ---------------------------------------------------------------------------
class AcadComBackend(Backend):
    """Drive the *full* AutoCAD application over COM, invisibly.

    This is the answer to "can I use the installed AutoCAD rather than
    accoreconsole, without a window popping up?"  Yes -- but not with
    ``acad.exe``.

    Why not ``acad.exe /b script.scr``
    ----------------------------------
    ``acad.exe`` accepts ``/b`` and will run a script, but it has no
    supported headless mode: the application window appears, and a batch of
    a thousand drawings means a thousand window activations stealing focus.
    Being headless is exactly what ``accoreconsole.exe`` exists for.

    What works instead
    ------------------
    AutoCAD's COM automation server exposes ``Application.Visible``.  Set it
    to ``False`` and the full application runs with no window while
    remaining the full application -- real CTB/STB plot styles, named page
    setups, xrefs, SHX fonts, dynamic blocks and annotative scaling, all
    behaving exactly as they do when a person plots the sheet.

    Not hijacking a session you are using
    -------------------------------------
    If AutoCAD is *already running*, this backend attaches to that instance
    and **leaves its visibility alone**.  Hiding a window someone is working
    in would be indefensible, and un-hiding it afterwards would still have
    stolen their session for the duration.  Only an instance this backend
    started itself is hidden.  Close AutoCAD first if you want the
    invisible path.

    Serial by construction
    ----------------------
    COM gives one ``Application`` object per machine session, so
    :attr:`parallel_safe` is ``False`` and the run is forced to one worker.
    ``accoreconsole`` is the parallel option; this one trades throughput for
    using the application itself.

    .. important::
       **Not executed by its author.**  There is no AutoCAD, no Windows and
       no COM in the environment this was written in, so everything below is
       reasoned from Autodesk's ActiveX reference and from the field
       failures recorded in ``autocad-dwg-to-pdf.md`` -- including the
       quiescence waits and busy-aware retry, which were worked out against
       a real "Invalid execution context" failure and are reused here rather
       than reinvented.  Treat the first run as a test: convert five sheets
       with ``--limit 5`` before committing to the archive.

    Requirements
    ------------
    Windows, a full AutoCAD install, and ``pywin32`` (``pip install
    pywin32``; the import is ``win32com``, which trips people up).
    """

    name = "acad-com"
    rank = 2
    reads_dwg = True
    #: One COM Application per session: this cannot be parallelised.
    parallel_safe = False

    #: Plotter configuration used when a layout names none.
    PC3 = "DWG To PDF.pc3"

    #: HRESULTs and message fragments that mean "busy, ask again" rather
    #: than "this drawing is broken".  DISP_E_EXCEPTION is generic, so the
    #: message text is what distinguishes the two cases.
    _BUSY_TEXT = (
        "invalid execution context",
        "call was rejected",
        "server is busy",
        "retrylater",
        "the message filter",
    )

    #: Cached per worker process: starting AutoCAD costs many seconds, so it
    #: is started once and reused for every drawing that worker handles.
    _app = None
    _app_was_running = False

    # -- discovery ---------------------------------------------------------
    @classmethod
    def available(cls) -> bool:
        """Windows + pywin32 + a registered ``AutoCAD.Application``.

        Deliberately does **not** launch AutoCAD.  Probing by ``Dispatch``
        would start the application just to answer "is it installed?", which
        on a cold machine is a 30-second surprise every time ``--probe``
        runs.  The registry tells us the same thing instantly.
        """
        if platform.system() != "Windows":
            return False
        try:
            import win32com.client  # noqa: F401
        except ImportError:
            return False
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "AutoCAD.Application"):
                return True
        except OSError:
            return False

    @classmethod
    def describe(cls) -> str:
        if platform.system() != "Windows":
            return "AutoCAD via COM (Windows only)"
        try:
            import win32com.client  # noqa: F401
        except ImportError:
            return "AutoCAD via COM (needs: pip install pywin32)"
        if cls.available():
            return "full AutoCAD via COM, window hidden (serial)"
        return "AutoCAD via COM (AutoCAD.Application not registered)"

    # -- COM plumbing ------------------------------------------------------
    @classmethod
    def _is_busy(cls, exc: Exception) -> bool:
        """Is this exception AutoCAD saying "not now" rather than "no"?"""
        return any(token in str(exc).lower() for token in cls._BUSY_TEXT)

    @classmethod
    def _retry(cls, fn, tries: int = 6, base: float = 0.5):
        """Call *fn*, retrying while AutoCAD reports itself busy.

        Back-off is linear, not exponential: the wait is AutoCAD finishing a
        plot -- a second or two -- not a network round trip.  A non-busy
        exception re-raises at once, so a genuinely broken drawing fails
        fast and gets logged instead of burning six retries.
        """
        last: Optional[Exception] = None
        for attempt in range(tries):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                if not cls._is_busy(exc):
                    raise
                last = exc
                time.sleep(base * (attempt + 1))
        raise last  # type: ignore[misc]

    @classmethod
    def _wait_quiescent(cls, app, timeout: float = 30.0) -> None:
        """Block until AutoCAD is idle, or give up quietly.

        ``AcadState.IsQuiescent`` is Autodesk's own "is it safe to talk to
        me" flag.  Polling it before each document operation is what turns
        an intermittent "Invalid execution context" into a wait.  Some
        states never report quiescent, so a timeout proceeds anyway rather
        than failing -- the call may well still succeed.
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                if app.GetAcadState().IsQuiescent:
                    return
            except Exception:  # noqa: BLE001 - refusal is itself an answer
                pass
            time.sleep(0.2)

    @classmethod
    def _get_app(cls):
        """Return the COM Application, starting a hidden one if needed."""
        if cls._app is not None:
            return cls._app

        import pythoncom
        import win32com.client as win32

        pythoncom.CoInitialize()
        try:
            # Attach to a running instance if there is one.
            cls._app = win32.GetActiveObject("AutoCAD.Application")
            cls._app_was_running = True
            _LOG.info(
                "attached to a running AutoCAD; leaving its window visible "
                "(close AutoCAD first if you want the hidden path)"
            )
        except Exception:  # noqa: BLE001 - nothing running, start our own
            cls._app = win32.DispatchEx("AutoCAD.Application")
            cls._app_was_running = False
            try:
                cls._app.Visible = False
                _LOG.info("started AutoCAD with the window hidden")
            except Exception as exc:  # noqa: BLE001
                _LOG.warning("could not hide the AutoCAD window: %s", exc)
        return cls._app

    @staticmethod
    def _quiet(doc) -> None:
        """Turn off everything that can raise a modal dialog mid-batch.

        One dialog stops an unattended run dead and waits for a human; it is
        the main way a batch of a thousand old drawings fails.

        ``BACKGROUNDPLOT`` **must** be 0.  With background plotting on,
        ``PlotToFile`` returns as soon as the job is *queued*, so the script
        races ahead and the next ``Close`` can kill the plot before the PDF
        is written -- silent, intermittent, and very hard to diagnose.
        """
        for var, val in (
            ("FILEDIA", 0), ("CMDDIA", 0), ("EXPERT", 5),
            ("PROXYNOTICE", 0), ("PROXYSHOW", 1),
            ("XREFNOTIFY", 0), ("XLOADCTL", 0),
            ("SDI", 0), ("PLQUIET", 1),
            ("BACKGROUNDPLOT", 0),
        ):
            try:
                doc.SetVariable(var, val)
            except Exception:  # noqa: BLE001 - not every release has each
                pass

    # -- conversion --------------------------------------------------------
    def _convert_impl(
        self, source: Path, out_dir: Path, spec: PageSpec
    ) -> tuple[list[Path], int]:
        app = self._get_app()
        target = out_dir / f"{source.stem}.pdf"

        self._wait_quiescent(app)
        doc = self._retry(lambda: app.Documents.Open(str(source), True))
        try:
            # Open usually activates the new document, but Plot belongs to
            # the ACTIVE document's state machine and "usually" is not good
            # enough -- addressing a non-active document is the other half
            # of the "Invalid execution context" story.
            try:
                self._retry(lambda: setattr(app, "ActiveDocument", doc))
            except Exception:  # noqa: BLE001 - single-document mode
                pass
            self._wait_quiescent(app)
            self._quiet(doc)

            layout_obj = doc.ActiveLayout
            if not getattr(layout_obj, "ConfigName", ""):
                layout_obj.ConfigName = self.PC3

            if spec.paper.upper() not in ("AUTO", "FIT"):
                # Only override the sheet when a specific size was asked
                # for; AUTO/FIT mean "use what the layout already says",
                # which for AutoCAD is the page setup the draughtsman saved.
                try:
                    layout_obj.UseStandardScale = True
                    layout_obj.StandardScale = 0        # acScaleToFit
                    layout_obj.CenterPlot = True
                    layout_obj.PlotWithLineweights = True
                except Exception as exc:  # noqa: BLE001
                    _LOG.debug("layout override skipped: %s", exc)

            self._wait_quiescent(app)
            self._retry(lambda: doc.Plot.PlotToFile(str(target), self.PC3))

            # PlotToFile is synchronous only because BACKGROUNDPLOT is 0.
            # The file can still lag the call on a network share, so give it
            # a bounded chance to appear rather than trusting either.
            for _ in range(40):
                if target.is_file() and target.stat().st_size > 1024:
                    break
                time.sleep(0.25)
        finally:
            try:
                self._retry(lambda: doc.Close(False))   # False = do not save
            except Exception:  # noqa: BLE001
                pass

        if not (target.is_file() and target.stat().st_size > 1024):
            raise RuntimeError(
                "AutoCAD (COM) produced no usable PDF for this drawing"
            )
        return [target], 0


# ---------------------------------------------------------------------------
# 3. Autodesk DWG TrueView
# ---------------------------------------------------------------------------
class TrueViewBackend(Backend):
    """Autodesk DWG TrueView driven by a ``.scr`` script.

    TrueView is Autodesk's free DWG viewer.  It is not headless -- it opens a
    window -- but it accepts the same ``/b`` script switch AutoCAD does, so a
    batch can be driven without anybody clicking::

        dwgviewr.exe "drawing.dwg" /b "plot.scr" /nologo

    That technique is documented in the CAD Forum tip on unattended plotting
    without AutoCAD [CADF]_.

    Two consequences follow from it being a GUI application, and both are
    handled here:

    * :attr:`parallel_safe` is ``False``.  Several copies competing for the
      foreground window interleave their keystrokes and produce garbage.
    * The timeout matters more than for the other backends, because an
      unexpected modal dialog waits forever rather than failing.

    .. [CADF] CAD Studio, "Unattended DWG plotting and PDF publishing without
       AutoCAD", tip 10461.
       https://www.cadforum.cz/en/unattended-dwg-plotting-and-pdf-publishing-without-autocad-tip10461

    .. danger::
       **This backend does not work, and is disabled by default.**

       It was tried against DWG TrueView 2025 on the target machine and
       produced two failures, neither of which this code can work around:

       1. ``Unhandled Exception c0000027 (c0000027h) at address 7513187ah``
          -- ``STATUS_UNWIND``: TrueView crashed while unwinding an
          exception, i.e. it fell over inside its own error handling.  There
          is no PDF and no useful diagnostic.
       2. ``Configuration file may be locked by another process or have been
          set Read Only (.cfg, .bak). File: ...\\dwgviewr2025.cfg`` -- a
          modal dialog demanding Retry or Cancel.  A modal dialog in an
          unattended batch is a hang, and it is exactly the failure mode
          script-driving a GUI application invites.

       Both are consistent with what TrueView is: a *viewer*.  Autodesk does
       not support driving it as a plot engine, so it has no obligation to
       behave when scripted, and it does not.

       :attr:`unreliable` is therefore ``True``, which removes it from every
       automatic chain.  It can still be selected explicitly
       (``--backend trueview``), which logs a warning first -- kept only so
       that the option is documented rather than mysteriously absent.  If
       there is AutoCAD on the machine, use ``accoreconsole``; if there is
       not, use ``libredwg+ezdxf``, which is bundled.
    """

    name = "trueview"
    rank = 4
    reads_dwg = True
    parallel_safe = False
    #: EXCLUDED FROM EVERY AUTOMATIC CHAIN.  See the class docstring: this
    #: backend was tried in the field and crashed rather than plotting.
    unreliable = True

    @classmethod
    def _exe(cls) -> Optional[Path]:
        return _find_tool("dwgviewr")

    @classmethod
    def available(cls) -> bool:
        return platform.system() == "Windows" and cls._exe() is not None

    @classmethod
    def describe(cls) -> str:
        exe = cls._exe()
        if exe:
            return (
                f"Autodesk DWG TrueView at {exe} -- DISABLED: crashes when "
                f"script-driven (see class docstring)"
            )
        return "DWG TrueView (not found; disabled anyway)"

    @staticmethod
    def _script_text(target: Path, spec: PageSpec) -> str:
        """Build the ``-PLOT`` script.

        The ``-PLOT`` prompt sequence, in order, is: detailed-config?, layout
        name, output device, paper size, units, orientation, plot-upside-down?,
        plot area, plot scale, plot offset, plot lineweights?, plot style
        table, plot with styles?, shade plot, write to file?, save changes?,
        proceed?.  Every one of them is answered below, and a blank string
        means "accept the default".
        """
        width, height = spec.size_mm()
        paper = "ANSI full bleed A (8.50 x 11.00 Inches)" if width == 0 else spec.paper
        lines = [
            "FILEDIA 0",
            "-PLOT",
            "Y",                                   # detailed plot configuration
            "",                                    # layout: current
            "DWG To PDF.pc3",                      # output device
            paper,                                 # paper size
            "Millimeters",                         # units
            "Landscape" if spec.landscape else "Portrait",
            "N",                                   # plot upside down
            "Extents",                             # plot area
            "Fit" if spec.scale == 0.0 else f"{spec.scale:g}",
            "Center" if spec.scale == 0.0 else "0,0",
            "Y",                                   # plot with lineweights
            "monochrome.ctb" if spec.monochrome else ".",
            "Y",                                   # plot with plot styles
            "N",                                   # shade plot: as displayed
            '"%s"' % target,                       # write to file (quoted)
            "N",                                   # save changes to page setup
            "Y",                                   # proceed
            "FILEDIA 1",
            "QUIT",
            "Y",
            "",
        ]
        return "\n".join(lines)

    def _convert_impl(
        self, source: Path, out_dir: Path, spec: PageSpec
    ) -> tuple[list[Path], int]:
        exe = self._exe()
        if exe is None:
            raise RuntimeError("dwgviewr not found")
        target = out_dir / f"{source.stem}.pdf"
        with tempfile.TemporaryDirectory(prefix="dwg2pdf_scr_") as tmp:
            script = Path(tmp) / "plot.scr"
            script.write_text(self._script_text(target, spec), encoding="ascii")
            proc = _run(
                [exe, str(source), "/b", str(script), "/nologo"],
                timeout=self.timeout,
            )
        if not target.is_file():
            raise RuntimeError(
                f"DWG TrueView wrote no PDF (rc={proc.returncode}). "
                f"The -PLOT prompt sequence differs between releases; "
                f"run one file by hand with --verbose and compare."
            )
        return [target], 0


# ===========================================================================
# Backend registry and selection
# ===========================================================================
#: Every backend class, in no particular order; ranking happens in
#: :func:`select_backend`.
BACKEND_CLASSES: tuple[type[Backend], ...] = (
    AcCoreConsoleBackend,
    AcadComBackend,
    QcadBackend,
    TrueViewBackend,
    OdaEzdxfBackend,
    LibreDwgEzdxfBackend,
    EzdxfBackend,
)

BACKENDS_BY_NAME: dict[str, type[Backend]] = {c.name: c for c in BACKEND_CLASSES}

#: Backends that drive a real AutoCAD.  The strategies treat these as one
#: group: "AutoCAD first" means either of them, best first.
AUTOCAD_BACKENDS = ("accoreconsole", "acad-com")


def available_backends() -> list[type[Backend]]:
    """Return every backend that can run here, best first.

    Returns
    -------
    list of type
        Sorted by :attr:`Backend.rank`.  Availability is decided by each
        class's own :meth:`Backend.available`, which probes for its tool.
    """
    found = [
        cls for cls in BACKEND_CLASSES
        if cls.available() and not cls.unreliable
    ]
    return sorted(found, key=lambda c: c.rank)


def select_backend(
    requested: Optional[str], need_dwg: bool
) -> type[Backend]:
    """Choose a backend, honouring an explicit request.

    Parameters
    ----------
    requested : str or None
        A backend name from :data:`BACKENDS_BY_NAME`, or ``None`` for
        automatic selection.
    need_dwg : bool
        Whether the input set contains ``.dwg`` files.  When ``False`` the
        pure-Python :class:`EzdxfBackend` is eligible.

    Returns
    -------
    type
        The chosen backend class.

    Raises
    ------
    SystemExit
        With an explanatory message if nothing suitable is installed, or if
        the explicitly requested backend is not available.

    Notes
    -----
    A backend flagged :attr:`Backend.needs_licence_optin` -- currently only
    the ODA route -- is skipped during automatic selection whenever any other
    usable backend exists.  It can still be chosen deliberately with
    ``--backend oda+ezdxf``.  This is a licensing safeguard, not a technical
    one: see the module docstring.
    """
    if requested:
        cls = BACKENDS_BY_NAME.get(requested)
        if cls is None:
            raise SystemExit(
                f"unknown backend {requested!r}; "
                f"choose from {', '.join(sorted(BACKENDS_BY_NAME))}"
            )
        if not cls.available():
            raise SystemExit(
                f"backend {requested!r} is not available on this machine: "
                f"{cls.describe()}"
            )
        if need_dwg and not cls.reads_dwg:
            raise SystemExit(
                f"backend {requested!r} cannot read DWG; the input set "
                f"contains .dwg files"
            )
        if cls.unreliable:
            _LOG.warning(
                "Backend %r is disabled by default because it has been "
                "observed to CRASH rather than plot. You asked for it "
                "explicitly, so it will be used -- expect failures. See its "
                "class docstring for what was seen.",
                requested,
            )
        return cls

    candidates = [c for c in available_backends() if c.reads_dwg or not need_dwg]
    if not candidates:
        raise SystemExit(_no_backend_message(need_dwg))

    unrestricted = [c for c in candidates if not c.needs_licence_optin]
    if unrestricted:
        return unrestricted[0]

    chosen = candidates[0]
    _LOG.warning(
        "Only %s is available, and its licence permits non-members "
        "non-commercial use only. Selecting it because there is no "
        "alternative; see --probe.",
        chosen.name,
    )
    return chosen


def select_backend_chain(
    requested: Optional[str],
    need_dwg: bool,
    *,
    strategy: str = "no-autocad-first",
) -> list[type[Backend]]:
    """Build the ordered chain of backends each drawing will try.

    Parameters
    ----------
    requested : str or None
        A single backend name to use alone, or ``None`` to build a chain.
    need_dwg : bool
        Whether the input set contains ``.dwg`` files.
    strategy : {"no-autocad-first", "autocad-first", "autocad-only", "single"}
        ``"no-autocad-first"``
            Try the routes that need no Autodesk software, then fall back to
            AutoCAD.  This is the default and it is the right default even on
            a machine that *has* AutoCAD: the free routes are faster (no
            application start-up per drawing), they parallelise, and they do
            not consume an AutoCAD licence seat.  AutoCAD is then there for
            the sheets that actually need it.
        ``"autocad-first"``
            Try AutoCAD first, falling back to the free routes.  Choose this
            when fidelity matters more than throughput -- AutoCAD is the only
            backend that honours CTB/STB plot styles, named page setups,
            SHX fonts and dynamic blocks exactly.
        ``"autocad-only"``
            AutoCAD and nothing else.  Use when the output must be exactly
            what AutoCAD would plot -- correct plot styles, page setups and
            SHX fonts -- and a fallback that renders differently would be
            worse than a failure.
        ``"single"``
            No fallback: use only the best available backend.

    Backends flagged :attr:`Backend.unreliable` (currently DWG TrueView) are
    excluded from every chain built here, whatever the strategy.

    Returns
    -------
    list of type
        The chain, best-first.  Never empty (raises instead).

    Raises
    ------
    SystemExit
        If nothing suitable is installed, with guidance on what to install.

    Notes
    -----
    The licence-restricted ODA backend is excluded from an automatic chain
    whenever an alternative exists, exactly as in :func:`select_backend`; it
    has to be asked for by name.
    """
    if requested:
        return [select_backend(requested, need_dwg)]

    usable = [c for c in available_backends() if c.reads_dwg or not need_dwg]
    if not usable:
        raise SystemExit(_no_backend_message(need_dwg))

    unrestricted = [c for c in usable if not c.needs_licence_optin]
    pool = unrestricted or usable

    if strategy == "single":
        return pool[:1]

    # Both AutoCAD-driven backends count as "AutoCAD" for the strategies:
    # accoreconsole (headless, parallel) is preferred, acad-com (the full
    # application with its window hidden) is the fallback within that group.
    autocad = [c for c in pool if c.name in AUTOCAD_BACKENDS]
    others = [c for c in pool if c.name not in AUTOCAD_BACKENDS]

    if strategy == "autocad-only":
        if not autocad:
            raise SystemExit(
                "strategy 'autocad-only' was requested but no AutoCAD "
                "backend is available.\n"
                "Either accoreconsole.exe was not found, or (for the "
                "hidden-window COM route) pywin32 is not installed:\n"
                "  pip install pywin32\n"
                "It ships with every AutoCAD since 2013, normally at\n"
                "  C:\\Program Files\\Autodesk\\AutoCAD <year>\\accoreconsole.exe\n"
                "Point at it with --accoreconsole, or choose another "
                "strategy.\n"
                "NOTE: a DWG TrueView console is deliberately NOT accepted "
                "here -- TrueView has no plotting engine."
            )
        return autocad

    if strategy == "autocad-first":
        chain = autocad + others
    else:
        chain = others + autocad

    return chain or pool[:1]


def _no_backend_message(need_dwg: bool) -> str:
    """Compose the 'nothing installed' error, with what to do about it."""
    what = "DWG" if need_dwg else "DXF"
    return (
        f"No backend on this machine can convert {what} to PDF.\n"
        "\n"
        "Options, best first:\n"
        "  1. AutoCAD          -- accoreconsole.exe ships with every AutoCAD\n"
        "                         since 2013; nothing to install if you have it.\n"
        "  2. QCAD Professional -- includes the dwg2pdf command-line tool.\n"
        "                         https://www.qcad.org/en/qcad-command-line-tools\n"
        "  3. DWG TrueView     -- free from Autodesk, Windows only.\n"
        "                         https://www.autodesk.com/products/dwg-trueview/overview\n"
        "  4. LibreDWG         -- GPL-3, no usage restriction:\n"
        "                         mamba install -c conda-forge libredwg\n"
        "  5. ODA File Converter -- free download, but NON-COMMERCIAL USE ONLY\n"
        "                         for ODA non-members.\n"
        "                         https://www.opendesign.com/guestfiles/oda_file_converter\n"
        "\n"
        "For DXF input only, `pip install ezdxf pymupdf` needs no CAD software.\n"
    )


# ===========================================================================
# Discovery
# ===========================================================================
def discover_inputs(
    roots: Sequence[Path],
    *,
    recursive: bool = True,
    include_dxf: bool = True,
    pattern: Optional[str] = None,
    regex: Optional[str] = None,
) -> list[Path]:
    """Collect the drawings to convert.

    Parameters
    ----------
    roots : sequence of pathlib.Path
        Files and/or directories given on the command line.
    recursive : bool
        Walk directories depth-first.  ``False`` looks only at the top level.
    include_dxf : bool
        Include ``.dxf`` alongside ``.dwg``.
    pattern : str, optional
        Extra glob applied to the file *name*, e.g. ``"ASSY-*"``.
    regex : str, optional
        Case-insensitive regular expression matched against the path relative
        to its root.  This is what ``--preset`` and ``--filter`` use; on an
        archive of thousands of drawings it is how you get the twenty you
        actually need without waiting for the rest.

    Returns
    -------
    list of pathlib.Path
        Sorted, de-duplicated, absolute paths.

    Notes
    -----
    Sorting is not cosmetic.  A deterministic order makes a resumed run
    (``--skip-existing``) predictable, and makes two runs on the same tree
    comparable line-by-line in the manifest.
    """
    suffixes = {".dwg"} | ({".dxf"} if include_dxf else set())
    found: set[Path] = set()
    rx = re.compile(regex, re.I) if regex else None

    for root in roots:
        root = root.expanduser().resolve()
        if root.is_file():
            if root.suffix.lower() in suffixes and (
                rx is None or rx.search(root.name)
            ):
                found.add(root)
            continue
        if not root.is_dir():
            _LOG.warning("input path does not exist, skipping: %s", root)
            continue
        walker: Iterable[Path] = root.rglob("*") if recursive else root.glob("*")
        for path in walker:
            if not path.is_file():
                continue
            if path.suffix.lower() not in suffixes:
                continue
            # Skip AutoCAD's own backups and autosaves; converting a .bak
            # produces a duplicate PDF of an older revision, which is worse
            # than useless in a drawing set.
            if path.name.lower().endswith((".bak", ".sv$", ".dwl")):
                continue
            if pattern and not path.match(pattern):
                continue
            if rx is not None and not rx.search(str(path.relative_to(root))):
                continue
            found.add(path.resolve())

    return sorted(found)


def plan_output(source: Path, in_root: Path, out_root: Path, flat: bool) -> Path:
    """Decide which directory a source drawing's PDFs go in.

    Parameters
    ----------
    source : pathlib.Path
        The drawing.
    in_root : pathlib.Path
        Common root of the inputs, used to compute the relative path.
    out_root : pathlib.Path
        Destination root.
    flat : bool
        ``True`` puts every PDF straight in *out_root*; ``False`` mirrors the
        input tree, which is what you want for a structured drawing set.

    Returns
    -------
    pathlib.Path
        The output directory (not the file).
    """
    if flat:
        return out_root
    try:
        relative = source.parent.relative_to(in_root)
    except ValueError:
        # Source lies outside in_root (mixed roots on the command line);
        # fall back to flat rather than writing outside out_root.
        return out_root
    return out_root / relative


# ===========================================================================
# Worker
# ===========================================================================
def _convert_task(
    source_str: str,
    out_dir_str: str,
    backend_names: list[str],
    spec_dict: dict[str, Any],
    timeout: float,
    skip_existing: bool,
) -> dict[str, Any]:
    """Convert one file, trying each backend in turn until one succeeds.

    Everything crossing the process boundary is a plain built-in type, because
    :class:`Backend` subclasses and :class:`pathlib.Path` pickle awkwardly (and
    a backend may hold an open handle).  The worker rebuilds what it needs from
    names and a dict.

    The fallback chain
    ------------------
    ``backend_names`` is an ordered chain, not a single choice.  Each backend
    is tried in order and the first one that produces a non-empty PDF wins.
    This is what makes "try without AutoCAD, fall back to AutoCAD if it
    struggles" a per-drawing decision rather than a per-run one -- which is the
    right granularity, because in a real archive it is individual sheets that
    defeat a decoder, not the whole set.

    A drawing that needed a fallback still counts as converted; the manifest
    records which backend actually produced it and what the earlier ones said,
    so a pattern ("every R11 sheet fell through to AutoCAD") is visible
    afterwards rather than lost.

    Parameters
    ----------
    source_str, out_dir_str : str
        Paths as strings.
    backend_names : list of str
        Ordered chain of keys into :data:`BACKENDS_BY_NAME`.
    spec_dict : dict
        :class:`PageSpec` as a dict.
    timeout : float
        Per-file limit in seconds, applied to *each* attempt.
    skip_existing : bool
        Return ``"skipped"`` without work if the expected PDF already exists
        and is no older than the source.

    Returns
    -------
    dict
        :meth:`ConversionResult.as_row` output.
    """
    source = Path(source_str)
    out_dir = Path(out_dir_str)
    spec = PageSpec(**spec_dict)

    if skip_existing and _already_done(source, out_dir):
        return ConversionResult(
            source=source,
            outputs=sorted(out_dir.glob(f"{source.stem}*.pdf")),
            backend=backend_names[0] if backend_names else "",
            status="skipped",
            message="output already present and newer than the drawing",
        ).as_row()

    attempts: list[str] = []
    last: Optional[ConversionResult] = None

    for index, name in enumerate(backend_names):
        cls = BACKENDS_BY_NAME.get(name)
        if cls is None or not cls.available():
            continue
        # A DXF-only backend cannot be asked to open a DWG; skip rather than
        # burn an attempt and a confusing error message on it.
        if source.suffix.lower() == ".dwg" and not cls.reads_dwg:
            continue

        result = cls(timeout=timeout).convert(source, out_dir, spec)
        if result.status == "ok":
            if index > 0:
                # Record the whole trail, not just the winner.
                result.message = (
                    f"{result.message} [fell back to {name} after: "
                    f"{'; '.join(attempts)}]"
                )
            return result.as_row()

        attempts.append(f"{name}: {result.message}")
        last = result

    if last is None:
        return ConversionResult(
            source=source,
            status="failed",
            message="no usable backend for this file",
        ).as_row()

    last.message = " | ".join(attempts)
    return last.as_row()


def split_chain_for_parallel(
    chain: Sequence[type[Backend]],
) -> tuple[list[type[Backend]], bool]:
    """Split a backend chain into the part that may run in parallel.

    Parameters
    ----------
    chain : sequence of type
        The full, ordered backend chain.

    Returns
    -------
    tuple
        ``(parallel_prefix, needs_serial_pass)``.  ``parallel_prefix`` is
        the leading run of backends that are safe to run concurrently;
        ``needs_serial_pass`` says whether anything was left out.

    Why not simply force one worker
    -------------------------------
    ``acad-com`` drives a single COM ``Application`` object and cannot be
    run concurrently, so a chain containing it is not wholly parallel-safe.
    The blunt response -- drop the whole run to one worker -- is a poor
    trade: on a machine with AutoCAD the default chain is
    ``libredwg+ezdxf -> accoreconsole -> acad-com``, and the COM backend is
    a last resort reached by a handful of sheets.  Serialising three
    thousand drawings to accommodate a fallback used by thirty of them
    turns a coffee break back into an afternoon.

    So the run is done in two passes instead: everything goes through the
    parallel-safe prefix concurrently, and only the sheets that *failed*
    are retried serially against the full chain.  Same final outcome, same
    fallback behaviour, without paying for it on every drawing.

    A chain whose *first* backend is not parallel-safe (``--backend
    acad-com``, say) yields an empty prefix, and the caller runs entirely
    serially -- which is correct, because there is nothing else to try.
    """
    prefix: list[type[Backend]] = []
    for cls in chain:
        if not cls.parallel_safe:
            break
        prefix.append(cls)
    return prefix, len(prefix) < len(chain)


def _already_done(source: Path, out_dir: Path) -> bool:
    """True if this drawing already has a usable, up-to-date PDF.

    Resume has to cope with two things a naive ``exists()`` gets wrong.  A
    multi-layout drawing writes ``name__layout.pdf`` rather than ``name.pdf``,
    so the plain path being absent does not mean the work was not done; and a
    PDF older than the drawing it came from is stale, which matters when an
    archive is still being revised.  Both are handled here, and a
    suspiciously small file (under 1 KiB) is treated as not done, because that
    is what a half-written PDF from an interrupted run looks like.
    """
    if not out_dir.is_dir():
        return False
    try:
        source_mtime = source.stat().st_mtime
    except OSError:
        return False
    for candidate in out_dir.glob(f"{source.stem}*.pdf"):
        try:
            stat = candidate.stat()
        except OSError:
            continue
        if stat.st_size > 1024 and stat.st_mtime >= source_mtime:
            return True
    return False


# ===========================================================================
# Batch driver
# ===========================================================================
def run_batch(
    sources: Sequence[Path],
    in_root: Path,
    out_root: Path,
    backend_chain: Sequence[type[Backend]],
    spec: PageSpec,
    *,
    workers: int = 0,
    flat: bool = False,
    timeout: float = 300.0,
    skip_existing: bool = False,
    recycle_after: int = 0,
    dry_run: bool = False,
    report_memory: bool = False,
    progress: Optional[Callable[[int, int, dict[str, Any]], None]] = None,
) -> list[dict[str, Any]]:
    """Convert a whole drawing set.

    Parameters
    ----------
    sources : sequence of pathlib.Path
        Drawings, from :func:`discover_inputs`.
    in_root, out_root : pathlib.Path
        Input and output roots; see :func:`plan_output`.
    backend_chain : sequence of type
        Ordered backend classes.  Each drawing tries them in turn and the
        first that produces a PDF wins; see :func:`_convert_task`.
    spec : PageSpec
        Page and plot-style request.
    workers : int
        Number of parallel workers.  ``0`` means ``os.cpu_count()``, capped so
        that a 64-core machine does not launch 64 CAD engines.  Forced to 1
        for a backend with :attr:`Backend.parallel_safe` ``False``.
    flat : bool
        Flatten the output tree.
    timeout : float
        Per-file limit in seconds.
    skip_existing : bool
        Resume mode: leave already-converted sheets alone.
    recycle_after : int
        ``max_tasks_per_child`` for the pool.  **Off by default, and that is
        deliberate.**

        It bounds resident memory -- ezdxf holds a whole drawing as a Python
        object graph, so a worker that has done hundreds of large sheets
        keeps a high-water heap.  But on Windows the pool must use the
        'spawn' start method, where every recycled worker **re-imports the
        entry module**; launched from the GUI that means re-importing Qt.
        Worse, all workers hit the limit at the same drawing and respawn
        together: with 4 workers and N=25 that lands exactly on drawing 100,
        and the run appears to freeze.

        Measured here with a Qt-importing entry module under spawn: 24
        trivial tasks took 1.2 s with recycling off and did not finish in two
        minutes with it on.

        Memory is already bounded per drawing -- each ``_convert_impl`` drops
        its ``Drawing`` and runs the collector before returning -- so leave
        this off unless you have measured a leak.
    dry_run : bool
        List what would happen and touch nothing.
    report_memory : bool
        Log this process's RSS every ten completions.
    progress : callable, optional
        Called as ``progress(done, total, row)`` after each file.

    Returns
    -------
    list of dict
        One :meth:`ConversionResult.as_row` per input.

    Notes
    -----
    **Parallelism.**  Conversion is embarrassingly parallel -- every sheet is
    independent -- so a process pool is close to a linear speed-up until the
    disk or the licence server becomes the limit.  Processes rather than
    threads, because the work is either in a subprocess or in ezdxf's
    CPU-bound C extensions, and because a crash in one worker then cannot take
    the run down.

    **Why not GPU.**  There is no GPU work in this pipeline.  DXF-to-PDF is a
    vector-to-vector transform: parse an entity graph, emit path operators.
    It is branch-heavy pointer chasing with no dense arithmetic kernel, so a
    GPU has nothing to do.  The only step in the neighbourhood that *would*
    suit one is rasterising a PDF to images afterwards, which is not what this
    module produces.  Scale this by cores, not by cards.
    """
    total = len(sources)
    if total == 0:
        _LOG.warning("no input drawings found")
        return []

    if not backend_chain:
        raise ValueError("backend_chain is empty")
    # Parallelism and logging are governed by the chain as a whole: if ANY
    # backend in it drives a GUI, the run has to be serialised, because that
    # backend may be reached on any drawing.
    backend_cls = backend_chain[0]
    chain_names = [c.name for c in backend_chain]
    chain_parallel_safe = all(c.parallel_safe for c in backend_chain)

    # -- decide worker count ------------------------------------------------
    # A chain that is not wholly parallel-safe is handled in two passes
    # rather than by dropping the whole run to one worker; see
    # split_chain_for_parallel for why.
    parallel_prefix, needs_serial_pass = split_chain_for_parallel(backend_chain)
    if not parallel_prefix:
        if workers not in (0, 1):
            _LOG.warning(
                "%s cannot run concurrently and leads the chain; "
                "running serially",
                backend_chain[0].name,
            )
        workers = 1
    elif needs_serial_pass and workers != 1:
        _LOG.info(
            "chain is %s; %s cannot run concurrently, so pass 1 runs "
            "%s in parallel and only the failures are retried serially "
            "against the full chain",
            " -> ".join(chain_names),
            ", ".join(c.name for c in backend_chain
                      if not c.parallel_safe),
            " -> ".join(c.name for c in parallel_prefix),
        )
    if workers <= 0:
        workers = max(1, min(os.cpu_count() or 1, 8))

    _LOG.info(
        "%d drawing(s), backend chain %s, %d worker(s), output -> %s",
        total,
        " -> ".join(chain_names),
        workers,
        out_root,
    )

    # -- build the job list -------------------------------------------------
    jobs: list[tuple[str, str]] = []
    for source in sources:
        out_dir = plan_output(source, in_root, out_root, flat)
        jobs.append((str(source), str(out_dir)))

    if dry_run:
        rows = []
        for source_str, out_dir_str in jobs:
            row = ConversionResult(
                source=Path(source_str),
                outputs=[Path(out_dir_str) / f"{Path(source_str).stem}.pdf"],
                backend=backend_cls.name,
                status="dry-run",
                message="not executed",
            ).as_row()
            rows.append(row)
            _LOG.info("would convert %s -> %s", source_str, row["outputs"])
        return rows

    spec_dict = dataclasses.asdict(spec)
    rows: list[dict[str, Any]] = []
    done = 0

    if workers == 1:
        # Serial path.  Deliberately not a 1-worker pool: it keeps tracebacks
        # readable and makes Ctrl-C behave, which matters when a GUI backend
        # has gone wrong and you want to stop it.
        for source_str, out_dir_str in jobs:
            row = _convert_task(
                source_str, out_dir_str, chain_names, spec_dict, timeout,
                skip_existing,
            )
            rows.append(row)
            done += 1
            _log_row(row, done, total)
            if progress:
                progress(done, total, row)
            if report_memory and done % 10 == 0:
                _log_memory()
    else:
        # ProcessPoolExecutor gained max_tasks_per_child in Python 3.11; guard
        # it so the module still runs on 3.10.
        # See the long note in dwg2pdf_gui.ConversionWorker._run_parallel:
        # max_tasks_per_child silently forces the 'spawn' start method (and
        # is rejected outright by 'fork'), which makes every worker
        # re-import the entry module.  The context is therefore chosen here
        # rather than inherited.
        import multiprocessing

        pool_kwargs: dict[str, Any] = {"max_workers": workers}
        if os.name == "nt":
            pool_kwargs["mp_context"] = multiprocessing.get_context("spawn")
            if sys.version_info >= (3, 11) and recycle_after > 0:
                pool_kwargs["max_tasks_per_child"] = recycle_after
        else:
            pool_kwargs["mp_context"] = multiprocessing.get_context("fork")
            if recycle_after > 0:
                _LOG.debug(
                    "worker recycling is Windows-only; using 'fork' here"
                )

        with ProcessPoolExecutor(**pool_kwargs) as pool:
            pass1_names = [c.name for c in parallel_prefix] or chain_names
            futures = {
                pool.submit(
                    _convert_task,
                    source_str,
                    out_dir_str,
                    pass1_names,
                    spec_dict,
                    timeout,
                    skip_existing,
                ): source_str
                for source_str, out_dir_str in jobs
            }
            for future in as_completed(futures):
                source_str = futures[future]
                try:
                    row = future.result()
                except Exception as exc:  # worker died outright
                    row = ConversionResult(
                        source=Path(source_str),
                        backend=backend_cls.name,
                        status="failed",
                        message=f"worker process failed: {type(exc).__name__}: {exc}",
                    ).as_row()
                if (needs_serial_pass and row["status"] == "failed"):
                    # Not a verdict yet: the serial-only backends have not
                    # been tried.  Calling this "failed" mid-run reads as
                    # final and is the single most misleading thing a
                    # two-pass run can print.
                    row["status"] = "retry-pending"
                rows.append(row)
                done += 1
                _log_row(row, done, total)
                if progress:
                    progress(done, total, row)
                if report_memory and done % 10 == 0:
                    _log_memory()

    # -- pass 2: retry failures serially against the full chain ------------
    if needs_serial_pass and workers > 1:
        retry = [r for r in rows if r["status"] == "retry-pending"]
        if retry:
            _LOG.info(
                "pass 2: retrying %d failed drawing(s) serially against "
                "the full chain (%s)",
                len(retry), " -> ".join(chain_names),
            )
            by_source = {r["source"]: r for r in rows}
            for index, row in enumerate(retry, 1):
                source = Path(row["source"])
                out_dir = plan_output(source, in_root, out_root, flat)
                new_row = _convert_task(
                    str(source), str(out_dir), chain_names, spec_dict,
                    timeout, skip_existing,
                )
                by_source[row["source"]] = new_row
                _log_row(new_row, index, len(retry))
                if progress:
                    progress(done, total, new_row)
            rows = list(by_source.values())
        for row in rows:
            if row["status"] == "retry-pending":
                row["status"] = "failed"

    # Restore input order; as_completed returns them scrambled.
    order = {str(p): i for i, p in enumerate(sources)}
    rows.sort(key=lambda r: order.get(r["source"], 0))
    return rows


def _log_row(row: dict[str, Any], done: int, total: int) -> None:
    """Emit one progress line at a level that matches the outcome."""
    name = Path(row["source"]).name
    if row["status"] == "ok":
        _LOG.info("[%d/%d] %s -> %s (%.1fs)", done, total, name, row["message"], row["seconds"])
    elif row["status"] == "retry-pending":
        _LOG.info(
            "[%d/%d] %s -- pass 1 could not convert it; queued for the "
            "serial retry with the full engine chain", done, total, name,
        )
    elif row["status"] == "skipped":
        _LOG.info("[%d/%d] %s -- skipped", done, total, name)
    else:
        _LOG.error("[%d/%d] %s -- %s: %s", done, total, name, row["status"], row["message"])


def _log_memory() -> None:
    """Log the driver's own RSS, if it can be determined."""
    rss = _rss_bytes()
    if rss is not None:
        _LOG.info("driver RSS: %s", _human_bytes(rss))


# ===========================================================================
# Reporting
# ===========================================================================
def write_manifest(rows: Sequence[dict[str, Any]], out_root: Path, spec: PageSpec,
                   backend_name: str) -> tuple[Path, Path]:
    """Write ``manifest.csv`` and ``manifest.json`` beside the output.

    The manifest is the point of the whole exercise for a drawing set of any
    size: it is the record of which sheets converted, which did not and why,
    and what settings produced them.  Without it, "the batch finished" is not
    a statement anybody can check.

    Returns
    -------
    tuple of pathlib.Path
        ``(csv_path, json_path)``.
    """
    out_root.mkdir(parents=True, exist_ok=True)
    csv_path = out_root / "manifest.csv"
    json_path = out_root / "manifest.json"

    fields = ["source", "outputs", "n_outputs", "backend", "status", "seconds",
              "entity_count", "message"]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "tool": "dwg2pdf.py",
        "revision": __revision__,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "backend": backend_name,
        "page_spec": dataclasses.asdict(spec),
        "summary": summarise(rows),
        "files": list(rows),
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return csv_path, json_path


def summarise(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Count outcomes and total time.

    Returns
    -------
    dict
        Keys ``total``, ``ok``, ``skipped``, ``failed``, ``dry_run``,
        ``pdfs``, ``seconds``.
    """
    counts = {"total": len(rows), "ok": 0, "skipped": 0, "failed": 0,
              "dry_run": 0, "retry_pending": 0}
    pdfs = 0
    seconds = 0.0
    for row in rows:
        key = row["status"].replace("-", "_")
        counts[key] = counts.get(key, 0) + 1
        pdfs += int(row.get("n_outputs", 0) or 0)
        seconds += float(row.get("seconds", 0.0) or 0.0)
    counts["pdfs"] = pdfs
    counts["seconds"] = round(seconds, 2)
    return counts


def merge_pdfs(rows: Sequence[dict[str, Any]], target: Path) -> Optional[Path]:
    """Concatenate every produced PDF into one file, in manifest order.

    Parameters
    ----------
    rows : sequence of dict
        Manifest rows.
    target : pathlib.Path
        Output path for the merged document.

    Returns
    -------
    pathlib.Path or None
        The merged file, or ``None`` if no PDF library is importable or there
        was nothing to merge.

    Notes
    -----
    Merging is streamed page-by-page rather than by loading every document at
    once; a few hundred D-size sheets is a large amount of memory otherwise.
    """
    paths: list[Path] = []
    for row in rows:
        if row["status"] != "ok":
            continue
        for chunk in str(row["outputs"]).split(";"):
            if chunk:
                paths.append(Path(chunk))
    if not paths:
        return None

    try:
        import pymupdf  # type: ignore
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError:
            _LOG.warning("--merge needs PyMuPDF; skipping merge")
            return None

    merged = pymupdf.open()
    try:
        for path in paths:
            with pymupdf.open(str(path)) as doc:
                merged.insert_pdf(doc)
        target.parent.mkdir(parents=True, exist_ok=True)
        merged.save(str(target))
    finally:
        merged.close()
        gc.collect()
    _LOG.info("merged %d PDF(s) -> %s", len(paths), target)
    return target


# ===========================================================================
# Command-line interface
# ===========================================================================
def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser.

    Kept as its own function so the parser can be imported and inspected by a
    test or a GUI front-end without running anything.
    """
    parser = argparse.ArgumentParser(
        prog="dwg2pdf.py",
        description=(
            "Batch-convert 2D AutoCAD drawings (DWG/DXF) to PDF using whichever "
            "conversion backend is installed."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples\n"
            "--------\n"
            "  # What can this machine do?\n"
            "  python dwg2pdf.py --probe\n"
            "\n"
            "  # See the plan without converting anything\n"
            "  python dwg2pdf.py drawings/ -o pdf/ --dry-run\n"
            "\n"
            "  # Whole tree, mirrored output, 6 workers\n"
            "  python dwg2pdf.py drawings/ -o pdf/ --workers 6\n"
            "\n"
            "  # Fixed A3 landscape at 1:50, monochrome, all paperspace layouts\n"
            "  python dwg2pdf.py drawings/ -o pdf/ --paper A3 --landscape \\\n"
            "                     --scale 0.02 --layouts paper\n"
            "\n"
            "  # Resume an interrupted run and merge the result into one PDF\n"
            "  python dwg2pdf.py drawings/ -o pdf/ --skip-existing --merge set.pdf\n"
        ),
    )

    parser.add_argument(
        "inputs", nargs="*", type=Path,
        help="drawing files and/or directories to convert",
    )
    parser.add_argument(
        "-o", "--out", type=Path, default=Path("pdf_out"),
        help="output root directory (default: ./pdf_out)",
    )

    group = parser.add_argument_group("selection")
    group.add_argument(
        "--no-recursive", action="store_true",
        help="do not descend into subdirectories",
    )
    group.add_argument(
        "--no-dxf", action="store_true",
        help="convert .dwg only, ignore .dxf",
    )
    group.add_argument(
        "--pattern", default=None,
        help="extra filename glob, e.g. 'ASSY-*.dwg'",
    )
    group.add_argument(
        "--filter", default=None, metavar="REGEX",
        help="case-insensitive regular expression matched against each "
             "drawing's path relative to the root",
    )
    group.add_argument(
        "--preset", default=None, choices=sorted(PRESETS),
        help="a named --filter, i.e. a shorthand for a regular expression "
             "you use often. The shipped entries are placeholders; edit the "
             "PRESETS dict at the top of this module to name the subsets "
             "your own drawing archive is organised around",
    )
    group.add_argument(
        "--limit", type=int, default=0, metavar="N",
        help="stop after N drawings, for a trial run",
    )
    group.add_argument(
        "--flat", action="store_true",
        help="write every PDF into the output root instead of mirroring the "
             "input tree",
    )
    group.add_argument(
        "--skip-existing", action="store_true",
        help="leave sheets that already have a non-empty PDF (resume mode)",
    )

    group = parser.add_argument_group("page setup")
    group.add_argument(
        "--paper", default="FIT",
        choices=sorted(PAPER_SIZES_MM),
        help="paper size; FIT sizes the page to the drawing (default), AUTO "
             "takes the sheet size from the drawing's own paperspace page "
             "setup and falls back to FIT when there isn't one",
    )
    group.add_argument(
        "--units", default="auto",
        choices=("auto", "mm", "cm", "m", "inch", "ft"),
        help="what one drawing unit means, for sizing a fitted page. "
             "'auto' reads $INSUNITS, then $MEASUREMENT (0=English->inch), "
             "then falls back to mm. Without this a 44x34 INCH sheet comes "
             "out as a 44x34 mm page (default: auto)",
    )
    group.add_argument("--landscape", action="store_true", help="landscape orientation")
    group.add_argument(
        "--max-page-mm", type=float, default=1189.0, metavar="MM",
        help="cap on an auto-sized (--paper FIT) page. A CAD drawing is at "
             "full scale, so an uncapped fit page can be kilometres across "
             "(default: 1189, the long edge of A0; 0 disables)",
    )
    group.add_argument(
        "--trim-outliers", action="store_true",
        help="fit the page to the drawing's robust extents, so one stray "
             "far-flung entity cannot shrink the whole drawing to a speck. "
             "Nothing is deleted -- the outlier is still drawn, it just no "
             "longer defines the page. Every exclusion is logged",
    )
    group.add_argument(
        "--outlier-factor", type=float, default=20.0, metavar="K",
        help="with --trim-outliers, an entity is an outlier when its span "
             "exceeds K x the 95th-percentile span (default: 20)",
    )
    group.add_argument(
        "--margin", type=float, default=5.0, metavar="MM",
        help="uniform page margin in millimetres (default: 5)",
    )
    group.add_argument(
        "--scale", type=float, default=0.0, metavar="RATIO",
        help="fixed plot scale as a ratio, e.g. 0.02 for 1:50; "
             "0 means fit to page (default: 0)",
    )
    group.add_argument(
        "--layouts", default="model",
        help="'auto' (paper space where it has content, else model space -- "
             "the safe choice for an uncatalogued archive), 'model', "
             "'paper', 'all', or an explicit layout name (default: model)",
    )
    group.add_argument(
        "--colour", dest="colour", action="store_true",
        help="keep entity colours; the default is monochrome, as most plotted "
             "engineering drawings are",
    )
    group.add_argument(
        "--lineweight-scale", type=float, default=1.0, metavar="K",
        help="multiply DXF lineweights by K; try 2.0 if lines look too thin "
             "(default: 1.0)",
    )
    group.add_argument(
        "--background", default="white", choices=("white", "black", "off", "default"),
        help="page background (default: white)",
    )

    group = parser.add_argument_group("execution")
    group.add_argument(
        "--backend", default=None, choices=sorted(BACKENDS_BY_NAME),
        help="force one specific backend and disable the fallback chain",
    )
    group.add_argument(
        "--strategy", default="no-autocad-first",
        choices=("no-autocad-first", "autocad-first", "autocad-only", "single"),
        help="fallback order. 'no-autocad-first' (default) tries the routes "
             "needing no Autodesk software and falls back to AutoCAD per "
             "drawing; 'autocad-first' reverses that when fidelity matters "
             "more than throughput; 'autocad-only' uses AutoCAD and nothing "
             "else; 'single' disables fallback. DWG TrueView is excluded "
             "from all of them -- it crashes when script-driven",
    )
    group.add_argument(
        "--accore-script", default=None, metavar="FILE",
        help="replace the generated AutoCAD .scr with this template. "
             "'{output}' is substituted with the target PDF path. Use when "
             "your AutoCAD release's -EXPORTPDF prompt sequence differs. "
             "Remember that a SPACE is Enter in a script: quote any path",
    )
    group.add_argument(
        "--accore-lang", default=None, metavar="CODE",
        help="AutoCAD /l language code, e.g. en-US. Omitted by default: "
             "an uninstalled language pack fails with 'Unable to Process "
             "Configuration File'",
    )
    group.add_argument(
        "--workers", type=int, default=0, metavar="N",
        help="parallel workers; 0 = min(cpu_count, 8) (default: 0)",
    )
    group.add_argument(
        "--timeout", type=float, default=300.0, metavar="SEC",
        help="per-drawing time limit (default: 300)",
    )
    group.add_argument(
        "--recycle-after", type=int, default=0, metavar="N",
        help="restart each worker process after N drawings. DEFAULT 0 (off) "
             "-- on Windows the pool uses the 'spawn' start method, so every "
             "recycled worker re-imports the entry module (and, from the "
             "GUI, all of Qt). With N workers they all hit the limit at the "
             "same drawing and respawn together, which looks exactly like a "
             "freeze. Memory is already bounded per drawing, so leave this "
             "off unless you have measured a leak",
    )

    group = parser.add_argument_group("output and diagnostics")
    group.add_argument(
        "--merge", type=Path, default=None, metavar="FILE",
        help="also concatenate every produced PDF into FILE",
    )
    group.add_argument(
        "--no-manifest", action="store_true",
        help="do not write manifest.csv / manifest.json",
    )
    group.add_argument("--probe", action="store_true",
                       help="report which backends are available, then exit")
    group.add_argument("--dry-run", action="store_true",
                       help="list what would be converted and exit")
    group.add_argument("--report-memory", action="store_true",
                       help="log resident memory every ten drawings")
    group.add_argument("-v", "--verbose", action="store_true", help="debug logging")
    group.add_argument("-q", "--quiet", action="store_true", help="warnings and errors only")
    group.add_argument("--version", action="version",
                       version=f"dwg2pdf.py revision {__revision__}")
    return parser


def _configure_logging(verbose: bool, quiet: bool) -> None:
    """Set up console logging at the requested level."""
    level = logging.DEBUG if verbose else (logging.WARNING if quiet else logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(levelname)-7s %(message)s",
        stream=sys.stderr,
    )


def _print_probe() -> int:
    """Print the backend availability report.  Returns an exit code."""
    print(f"dwg2pdf.py revision {__revision__}")
    print(f"Python {sys.version.split()[0]} on {platform.platform()}")
    print()
    print("Backends, best first:")
    any_available = False
    for cls in sorted(BACKEND_CLASSES, key=lambda c: c.rank):
        ok = cls.available()
        any_available = any_available or ok
        mark = "available" if ok else "  --     "
        flags = []
        if not cls.reads_dwg:
            flags.append("DXF only")
        if not cls.parallel_safe:
            flags.append("serial only")
        if cls.needs_licence_optin:
            flags.append("licence opt-in")
        if cls.unreliable:
            flags.append("DISABLED - crashes when scripted")
        suffix = f"  [{', '.join(flags)}]" if flags else ""
        print(f"  {mark}  {cls.rank}. {cls.name:<16} {cls.describe()}{suffix}")
    print()
    if not any_available:
        print(_no_backend_message(need_dwg=True))
        return 1
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point.

    Parameters
    ----------
    argv : sequence of str, optional
        Argument vector; ``None`` uses ``sys.argv[1:]``.

    Returns
    -------
    int
        Process exit status: ``0`` if every drawing converted or was skipped,
        ``1`` if any failed, ``2`` for a usage or environment problem.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(args.verbose, args.quiet)
    install_noise_filters()

    if args.probe:
        return _print_probe()

    if not args.inputs:
        parser.error("no input files or directories given (use --probe to "
                     "check the environment)")

    # -- discovery ---------------------------------------------------------
    regex = args.filter or (PRESETS[args.preset] if args.preset else None)
    sources = discover_inputs(
        args.inputs,
        recursive=not args.no_recursive,
        include_dxf=not args.no_dxf,
        pattern=args.pattern,
        regex=regex,
    )
    if regex:
        _LOG.info("filter %r matched %d drawing(s)", regex, len(sources))
    if args.limit:
        sources = sources[: args.limit]
    if not sources:
        _LOG.error("no .dwg/.dxf files found under: %s",
                   ", ".join(str(p) for p in args.inputs))
        return 2

    need_dwg = any(p.suffix.lower() == ".dwg" for p in sources)

    # The common root is what the mirrored output tree is relative to.  For a
    # single directory argument that is the directory itself; for a mixed set
    # it is their common ancestor.
    if len(args.inputs) == 1 and args.inputs[0].is_dir():
        in_root = args.inputs[0].expanduser().resolve()
    else:
        in_root = Path(os.path.commonpath([str(p.parent) for p in sources]))

    # -- backend -----------------------------------------------------------
    try:
        chain = select_backend_chain(
            args.backend, need_dwg, strategy=args.strategy
        )
    except SystemExit as exc:
        # select_backend raises SystemExit with a long explanatory message;
        # print it and use exit code 2 (environment problem), not 1.
        print(exc, file=sys.stderr)
        return 2

    if args.accore_script:
        try:
            AcCoreConsoleBackend.script_override = Path(
                args.accore_script
            ).read_text(encoding="utf-8")
            _LOG.info("using AutoCAD script template %s", args.accore_script)
        except OSError as exc:
            print(f"cannot read --accore-script: {exc}", file=sys.stderr)
            return 2
    if args.accore_lang:
        AcCoreConsoleBackend.language = args.accore_lang

    backend_cls = chain[0]
    if len(chain) > 1:
        _LOG.info("backend chain: %s", " -> ".join(c.name for c in chain))
    if backend_cls.needs_licence_optin:
        _LOG.warning(
            "Backend %s: ODA's free tools may be used by non-members for "
            "NON-COMMERCIAL applications only. Confirm your licence position "
            "before using this output for paid work.",
            backend_cls.name,
        )

    spec = PageSpec(
        paper=args.paper,
        units=args.units,
        landscape=args.landscape,
        max_page_mm=args.max_page_mm,
        trim_outliers=args.trim_outliers,
        outlier_factor=args.outlier_factor,
        margin_mm=args.margin,
        scale=args.scale,
        layouts=args.layouts,
        monochrome=not args.colour,
        lineweight_scale=args.lineweight_scale,
        background=args.background,
    )

    out_root = args.out.expanduser().resolve()

    # -- run ---------------------------------------------------------------
    started = time.perf_counter()
    rows = run_batch(
        sources,
        in_root,
        out_root,
        chain,
        spec,
        workers=args.workers,
        flat=args.flat,
        timeout=args.timeout,
        skip_existing=args.skip_existing,
        recycle_after=args.recycle_after,
        dry_run=args.dry_run,
        report_memory=args.report_memory,
    )
    elapsed = time.perf_counter() - started

    # -- report ------------------------------------------------------------
    stats = summarise(rows)
    if args.merge and not args.dry_run:
        merge_pdfs(rows, args.merge.expanduser().resolve())

    if not args.no_manifest and not args.dry_run:
        csv_path, json_path = write_manifest(
            rows, out_root, spec, " -> ".join(c.name for c in chain)
        )
        _LOG.info("manifest: %s and %s", csv_path.name, json_path.name)

    print(
        f"\n{stats['total']} drawing(s): "
        f"{stats['ok']} converted, {stats['skipped']} skipped, "
        f"{stats['failed']} failed -> {stats['pdfs']} PDF(s) "
        f"in {elapsed:.1f} s wall ({' -> '.join(c.name for c in chain)})",
        file=sys.stderr,
    )

    if stats["failed"]:
        print("\nFailures:", file=sys.stderr)
        for row in rows:
            if row["status"] == "failed":
                print(f"  {row['source']}\n      {row['message']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    # Guards a spawned worker against re-entering main() on Windows.
    import multiprocessing

    multiprocessing.freeze_support()
    raise SystemExit(main())
