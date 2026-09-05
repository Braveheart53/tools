#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
dwg2pdf_gui.py
-----------------------------------------------------------------------------
# %% Header Info
Qt front-end for ``dwg2pdf.py`` -- batch conversion of 2D AutoCAD drawings
(DWG/DXF) to PDF, with or without AutoCAD installed.

All conversion logic lives in ``dwg2pdf.py``.  This file collects settings,
runs the batch off the GUI thread, shows progress and results, and packages
the output.  Every command-line option of the engine is exposed here, and the
window shows the equivalent command line so the two stay interchangeable.
# %%% Author Information
@author: (set your name here)
Author Email: (set your email here)
# %%% Revisions
Semantic versioning: External Release.Internal Release.Working version
# %%%% 0.2.9: Revision history completed; scrub verified.
# Date: 2026-09-03
#              Documentation revision, no behavioural change.  The history
#              block below stopped at 0.2.0 while this file ran 0.2.8;
#              every revision from 0.2.1 forward is now recorded, newest
#              first, per the project template.  Final audit for public
#              release: no site-, project- or user-specific names or paths
#              in any shipped file.
# %%%% 0.2.8: Worker recycling off by default.
# Date: 2026-09-03
#              "Recycle worker after N files" now defaults to 0 (off) and
#              says so in its tooltip.  max_tasks_per_child silently forces
#              the spawn start method, so every recycled worker re-imports
#              this module -- Qt included -- before it can take another
#              file.  Measured: 24 trivial tasks, 1.21 s with recycling off
#              vs not finished in two minutes with it on.  The recycles are
#              also synchronised: 4 workers x 25 files means all four
#              respawn at file 100 at once, which looks exactly like the
#              GUI freezing at the hundredth document.  Enable it only when
#              "Report memory" shows RSS actually climbing.
# %%%% 0.2.7: retry-pending status in the results table.
# Date: 2026-09-03
#              A drawing that pass 1 could not convert was shown in red as
#              "failed" before the AutoCAD COM backend had been tried on it
#              at all -- it only runs in pass 2.  Pass-1 misses are now
#              amber "retry-pending", with "queued for the serial retry
#              with the full engine chain" in the log, and resolve to ok or
#              failed once pass 2 has actually run them.  Because pass 2
#              starts only after pass 1 has finished every drawing, the
#              amber rows can persist for a long time on a large run; that
#              is the design and the log now says so.
# %%%% 0.2.6: Documentation and identifier scrub for public release.
# Date: 2026-09-03
#              Tooltips, worked examples and the author block made generic:
#              no site-, project- or user-specific paths or names in any
#              shipped file.
# %%%% 0.2.5: Drawing-units control on the Page Setup tab.
# Date: 2026-09-03
#              Units selector (auto / mm / inch / m ...), auto by default,
#              exposing the engine's --units.  Without it a 44 x 34 inch
#              ANSI E sheet rendered as a 44 x 34 mm page.
# %%%% 0.2.4: Two-pass parallelism honoured in the worker.
# Date: 2026-09-03
#              The GUI previously ignored Backend.parallel_safe, which
#              would have put several workers on one COM Application
#              object.  ConversionWorker now splits the chain: _run_parallel
#              over the parallel-safe prefix, then _serial_retry of the
#              failures against the full chain.  The Performance tab states
#              which case applies before the run starts.
# %%%% 0.2.3: AutoCAD script overrides and full console capture.
# Date: 2026-09-03
#              Fields for --accore-script and --accore-lang, and the whole
#              accoreconsole transcript reaches the Detailed log on failure
#              instead of a truncated tail.
# %%%% 0.2.2: All Python logging routed into the Detailed log.
# Date: 2026-09-03
#              LogBridge/QtLogHandler installed on the root logger, so
#              engine, ezdxf and fontTools messages appear in the GUI and
#              in the detached log window rather than only on stderr.
# %%%% 0.2.1: Detachable log window.
# Date: 2026-09-03
#              View -> Open log in window (Ctrl+L).  The detached window
#              shares the same QTextDocument as the embedded tab, so the
#              two never diverge and nothing is buffered twice.
# %%%% 0.2.0: Full-option restructure; bundled LibreDWG; TrueView removed.
# Date: 2026-09-03
#              GUI restructured into five tabs so that EVERY engine option
#              is reachable -- the previous single-pane layout could not
#              hold them.
#                * NEW "Files & Output" tab: a real multi-directory list
#                  (add/remove, mixed files and folders), an explicit
#                  output-path panel, and a Structure radio pair --
#                  "Replicate source folder tree" vs "Flatten into one
#                  folder".  A live preview shows exactly where the first
#                  few PDFs will land, so the choice is visible rather
#                  than described.
#                * NEW "Performance" tab: parallelism is now chosen by
#                  MODE rather than by a bare number --
#                     - "Automatic (by CPU cores)" with a percentage,
#                     - "Fixed job count",
#                     - "Serial".
#                  See PARALLEL_MODE_NOTE for why cores is the better
#                  default here.  Adds worker recycling and RSS logging.
#                * NEW "Engine" tab: strategy selector now offers
#                  no-AutoCAD-first / AutoCAD-first / AutoCAD-ONLY /
#                  single, an explicit accoreconsole.exe path override,
#                  a per-drawing timeout, and the live backend probe.
#                * NEW "Page Setup" tab: paper (including AUTO, which
#                  reads the sheet size from the drawing's own paperspace
#                  page setup), orientation, max-page cap, margin, scale,
#                  monochrome, line-weight multiplier, background, and
#                  stray-entity trimming with its factor.
#                * NEW "Finish" tab: merge-to-single-PDF, manifest
#                  toggle, and 7-Zip/ZIP packaging of the whole output
#                  with a revision-stamped archive name.
#                * NEW detachable log: the log pane can be popped into
#                  its own resizable window ("Open log in window"), so a
#                  long run can be watched while the settings tabs stay
#                  usable.  Both views share one buffer.
#                * The batch now runs through a real ProcessPoolExecutor
#                  when more than one worker is selected -- 0.1.0 was
#                  serial for cancellation's sake.  Cancellation is still
#                  responsive because it is checked between completed
#                  futures rather than between files.
#                * DWG TrueView is gone from the engine list.  It is not
#                  hidden out of preference: it was tried and it crashed
#                  (STATUS_UNWIND c0000027) and raised a modal
#                  config-file-locked dialog.  See TrueViewBackend in the
#                  engine module.
#                * Windows LibreDWG binaries now ship beside this file in
#                  vendor/libredwg-win64/, so a Windows machine with no
#                  Autodesk software converts DWG out of the box.
# %%%% 0.1.0: First GUI.
# Date: 2026-09-02
#              Backend probe panel, fallback-chain strategy selector, page
#              setup, filters/presets, threaded run with live progress and
#              per-file results table, light/dark theme menu, and the
#              equivalent-command display.
# %%%%% Function Descriptions
#       main: build QApplication, apply theme, open the window, run the loop.
#       apply_theme: swap the whole application between light and dark
#           QPalettes.  Fusion style is forced first -- the native Windows
#           style ignores palettes, which would make the Dark menu item do
#           nothing at all.
#       resolve_worker_count: turn the chosen parallel MODE into an integer
#           worker count.  The one place that decision is made.
#       ConversionWorker: QObject moved onto a QThread; runs the batch,
#           emits progress/message/finished, supports cooperative cancel.
#       LogWindow: detachable log viewer sharing the main window's buffer.
#       MainWindow: the five-tab window and all of its handlers.
# %%%%% Variable Descriptions
#       DEFAULT_CORE_PERCENT: percent of logical cores used in Automatic mode.
#       WORKER_CAP: hard ceiling on workers, so a 64-core box does not launch
#           64 CAD processes at once.
#       PARALLEL_MODE_NOTE: the reasoning shown in the Performance tab.
# %%%%% More Info
#       Toolkit is QtPy (the abstraction layer) with PySide6 as the binding,
#       so ``from qtpy import QtWidgets`` rather than importing PySide6
#       directly.  A future environment with PyQt5/6 needs no change here,
#       only QT_API.
=============================================================================
"""
# %% Imports
from __future__ import annotations
# ============================================================================
# %%% IMPORTS - Standard library
# ============================================================================
import logging
import os
import subprocess
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional
# ============================================================================
# %%% IMPORTS - Qt, through the QtPy abstraction layer
# ============================================================================
try:
    from qtpy import QtCore, QtGui, QtWidgets
    from qtpy.QtCore import Qt, Signal, Slot
except ImportError as _exc:  # pragma: no cover - environment, not logic
    sys.stderr.write(
        "This GUI needs QtPy and a Qt binding:\n"
        "    pip install qtpy PySide6\n"
        f"(import failed: {_exc})\n"
    )
    raise SystemExit(2)
# ============================================================================
# %%% IMPORTS - the conversion engine (same folder)
# ============================================================================
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)
import dwg2pdf as engine   # noqa: E402

# ============================================================================
# %% SCRIPT-LEVEL KNOBS  (kept at the top per spec)
# ============================================================================
__revision__ = "0.2.9"

#: Percent of logical cores used by the "Automatic (by CPU cores)" mode.
DEFAULT_CORE_PERCENT = 75

#: Hard ceiling on workers regardless of mode or core count.  Past roughly
#: this many concurrent conversions the disk, not the CPU, is the limit --
#: and with the AutoCAD backend every worker is a licence checkout.
WORKER_CAP = 16

#: Shown in the Performance tab.  Kept as a constant so the reasoning lives
#: with the code that implements it rather than only in a docstring.
PARALLEL_MODE_NOTE = (
    "Cores is the better default. Each drawing is independent, so this "
    "scales almost linearly until the disk saturates. The work is split "
    "between a decoder subprocess (I/O-bound, releases the GIL) and ezdxf's "
    "C extensions (CPU-bound), so ~75% of logical cores keeps every core fed "
    "without thrashing.\n\n"
    "Choose a fixed job count when something else is competing for the "
    "machine, or when the AutoCAD backend is in use and licence seats are "
    "limited — every worker checks one out.\n\n"
    "There is no GPU path: DXF-to-PDF is a vector-to-vector transform with "
    "no dense arithmetic kernel. Scale by cores, not cards."
)

#: Default window geometry.
_DEFAULT_SIZE = (1180, 860)


# ============================================================================
# %% THEME
# ============================================================================
def apply_theme(app: QtWidgets.QApplication, dark: bool) -> None:
    """Switch the whole application between a light and a dark palette.

    Parameters
    ----------
    app : QtWidgets.QApplication
        The running application.
    dark : bool
        ``True`` for the dark palette.

    Notes
    -----
    Implemented as a :class:`QPalette` swap rather than a stylesheet, so it
    reaches every standard widget without enumerating them.  The Fusion style
    is forced in :func:`main` because the native Windows style paints from the
    OS theme and ignores the application palette -- without Fusion the Dark
    menu item would appear to do nothing.
    """
    if not dark:
        app.setPalette(app.style().standardPalette())
        return

    bg = QtGui.QColor(37, 37, 40)
    base = QtGui.QColor(28, 28, 30)
    text = QtGui.QColor(228, 228, 232)
    accent = QtGui.QColor(58, 130, 205)
    disabled = QtGui.QColor(130, 130, 136)

    pal = QtGui.QPalette()
    pal.setColor(QtGui.QPalette.Window, bg)
    pal.setColor(QtGui.QPalette.WindowText, text)
    pal.setColor(QtGui.QPalette.Base, base)
    pal.setColor(QtGui.QPalette.AlternateBase, bg)
    pal.setColor(QtGui.QPalette.ToolTipBase, base)
    pal.setColor(QtGui.QPalette.ToolTipText, text)
    pal.setColor(QtGui.QPalette.Text, text)
    pal.setColor(QtGui.QPalette.Button, bg)
    pal.setColor(QtGui.QPalette.ButtonText, text)
    pal.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 90, 90))
    pal.setColor(QtGui.QPalette.Highlight, accent)
    pal.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(255, 255, 255))
    pal.setColor(QtGui.QPalette.Link, accent)
    for role in (QtGui.QPalette.WindowText, QtGui.QPalette.Text,
                 QtGui.QPalette.ButtonText):
        pal.setColor(QtGui.QPalette.Disabled, role, disabled)
    app.setPalette(pal)


# ============================================================================
# %% PYTHON LOGGING -> THE DETAILED LOG PANEL
# ============================================================================
class LogBridge(QtCore.QObject):
    """Carries formatted log lines from any thread to the GUI thread.

    A :class:`logging.Handler` can be called from a worker thread or from
    inside a library, and Qt widgets may only be touched from the GUI
    thread.  Emitting a signal is the sanctioned crossing: Qt queues it
    automatically when the emitter and receiver live on different threads.
    """

    line = Signal(str)


class QtLogHandler(logging.Handler):
    """A logging handler that feeds the GUI's Detailed log tab.

    Records that arrive before the window exists are buffered and replayed
    once a sink connects, so nothing logged during start-up is lost --
    which matters here, because the noisiest moment is ezdxf building its
    font cache during the very first backend probe.
    """

    def __init__(self, bridge: LogBridge) -> None:
        super().__init__()
        self.bridge = bridge
        self._buffer: List[str] = []
        self._live = False
        self.setFormatter(logging.Formatter("%(levelname)-7s %(name)s: %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            text = self.format(record)
        except Exception:  # noqa: BLE001 - never let logging break the app
            return
        if self._live:
            self.bridge.line.emit(text)
        else:
            self._buffer.append(text)

    def go_live(self) -> List[str]:
        """Switch to live emission and hand back anything buffered."""
        self._live = True
        buffered, self._buffer = self._buffer, []
        return buffered


def install_logging(level: int = logging.INFO) -> QtLogHandler:
    """Route Python logging into the GUI and silence the benign font noise.

    Parameters
    ----------
    level : int
        Root logger level.  ``INFO`` shows the engine's per-drawing lines.

    Returns
    -------
    QtLogHandler
        The handler, for :meth:`MainWindow._attach_logging` to connect.

    Notes
    -----
    Two things happen here, and they are related.

    The engine, ezdxf and fontTools all log through the standard library.
    Without a handler those messages go to stderr -- invisible to anyone
    who launched the GUI by double-clicking it, and mixed in with the
    console for anyone who did not.  Sending them to the Detailed log tab
    is what makes that tab a real diagnostic view rather than a transcript
    of what this file chose to print.

    :func:`dwg2pdf.install_noise_filters` then absorbs the two known-benign
    third-party messages -- fontTools' ``'name' table stringOffset``
    complaint and ezdxf's ``ignoring DIMTXSTY override`` -- each explained
    once instead of repeated per font and per dimension.  See
    :class:`dwg2pdf._ThirdPartyNoiseFilter` for why both are harmless.
    Everything else, including genuinely broken fonts and every warning
    about the drawing itself, still reaches the panel.
    """
    noise = engine.install_noise_filters()
    bridge = LogBridge()
    handler = QtLogHandler(bridge)
    # Backstop: also filter at the handler, in case a library logs the same
    # thing from a module the engine's logger list does not name.  Handler
    # filters DO drop records (the level check that precedes them only
    # matters if you try to demote a level rather than reject the record).
    handler.addFilter(noise)
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
    return handler


# ============================================================================
# %% PARALLELISM
# ============================================================================
def resolve_worker_count(mode: str, percent: int, fixed: int) -> int:
    """Turn the chosen parallel mode into an integer worker count.

    Parameters
    ----------
    mode : {"cores", "jobs", "serial"}
        ``"cores"`` scales with the machine, ``"jobs"`` is an explicit
        number, ``"serial"`` is one worker.
    percent : int
        Percent of logical cores to use in ``"cores"`` mode.
    fixed : int
        Worker count for ``"jobs"`` mode.

    Returns
    -------
    int
        At least 1, at most :data:`WORKER_CAP`.

    Notes
    -----
    This is the single place the decision is made, so the Performance tab,
    the equivalent-command display and the actual run can never disagree --
    which they would if each recomputed it.
    """
    if mode == "serial":
        return 1
    if mode == "jobs":
        return max(1, min(int(fixed), WORKER_CAP))
    cores = os.cpu_count() or 1
    want = int(round(cores * (max(1, min(100, int(percent))) / 100.0)))
    return max(1, min(want, WORKER_CAP))


# ============================================================================
# %% WORKER THREAD
# ============================================================================
class ConversionWorker(QtCore.QObject):
    """Runs a batch conversion off the GUI thread.

    Signals
    -------
    progress(int done, int total, dict row)
        Emitted after each drawing.  ``row`` is a manifest row.
    message(str)
        A line for the log pane.
    finished(list rows, float seconds, bool cancelled)
        Emitted exactly once when the run ends, however it ends.

    Notes
    -----
    A batch of thousands of drawings takes minutes to hours.  Running it on
    the GUI thread would give a frozen "not responding" window for the whole
    run, so the work happens here and results arrive as queued signals -- the
    widgets are only ever touched from the GUI thread.

    Cancellation is cooperative.  With a process pool it is checked between
    completed futures; the pool is then shut down with ``cancel_futures`` so
    queued work is dropped while running work finishes.  Killing a worker
    mid-write would leave a truncated PDF, and the resume logic would then
    have to tell "half written" from "finished", which it should not have to.
    """

    progress = Signal(int, int, dict)
    message = Signal(str)
    finished = Signal(list, float, bool)

    def __init__(self, options: Dict[str, Any]) -> None:
        super().__init__()
        self._options = options
        self._cancel = False

    @Slot()
    def cancel(self) -> None:
        """Ask the run to stop; in-flight drawings finish first."""
        self._cancel = True
        self.message.emit("Cancelling - letting in-flight drawings finish...")

    # ------------------------------------------------------------------
    @Slot()
    def run(self) -> None:
        """Do the conversion.  Invoked by the thread's ``started`` signal."""
        started = time.perf_counter()
        rows: List[Dict[str, Any]] = []
        cancelled = False
        opts = self._options

        try:
            sources = opts["sources"]
            total = len(sources)
            chain_names = [c.name for c in opts["chain"]]
            workers = int(opts["workers"])

            self.message.emit("Engine chain : " + " -> ".join(chain_names))
            self.message.emit("Workers      : %d" % workers)
            self.message.emit("Output root  : %s" % opts["out_root"])
            self.message.emit("Structure    : %s"
                              % ("flattened" if opts["flat"]
                                 else "mirrors the source tree"))
            self.message.emit("Drawings     : %d" % total)
            self.message.emit("-" * 60)

            spec_dict = engine.dataclasses.asdict(opts["spec"])
            jobs = []
            for src in sources:
                out_dir = engine.plan_output(
                    src, opts["in_root"], opts["out_root"], opts["flat"]
                )
                out_dir.mkdir(parents=True, exist_ok=True)
                jobs.append((str(src), str(out_dir)))

            # A chain containing a backend that cannot run concurrently
            # (acad-com drives one COM Application) is NOT run serially
            # throughout -- that would pay for a last-resort fallback on
            # every drawing.  Pass 1 runs the parallel-safe prefix
            # concurrently; pass 2 retries only the failures serially
            # against the full chain.  See
            # dwg2pdf.split_chain_for_parallel.
            prefix, needs_serial = engine.split_chain_for_parallel(
                opts["chain"])
            prefix_names = [c.name for c in prefix]
            if not prefix:
                self.message.emit(
                    "%s cannot run concurrently and leads the chain - "
                    "running serially." % chain_names[0]
                )
                workers = 1
            elif needs_serial and workers > 1:
                self.message.emit(
                    "Pass 1: %s in parallel. %s cannot run concurrently, "
                    "so only failures are retried against the full chain."
                    % (" -> ".join(prefix_names),
                       ", ".join(c.name for c in opts["chain"]
                                 if not c.parallel_safe))
                )

            self._needs_serial = needs_serial
            if workers <= 1:
                rows, cancelled = self._run_serial(
                    jobs, chain_names, spec_dict, opts, total
                )
            else:
                rows, cancelled = self._run_parallel(
                    jobs, prefix_names or chain_names, spec_dict, opts,
                    total, workers
                )
                if needs_serial and not cancelled:
                    rows = self._serial_retry(
                        rows, chain_names, spec_dict, opts, total
                    )

            # Restore input order; a pool returns results scrambled.
            order = {str(p): i for i, p in enumerate(sources)}
            rows.sort(key=lambda r: order.get(r["source"], 0))

            if rows and opts.get("write_manifest", True):
                csv_path, json_path = engine.write_manifest(
                    rows, opts["out_root"], opts["spec"],
                    " -> ".join(chain_names),
                )
                self.message.emit("Manifest: %s, %s"
                                  % (csv_path.name, json_path.name))

            if rows and opts.get("merge_path"):
                merged = engine.merge_pdfs(rows, Path(opts["merge_path"]))
                if merged:
                    self.message.emit("Merged PDF: %s" % merged)

            if rows and opts.get("archive_path"):
                made = self._make_archive(
                    opts["out_root"], Path(opts["archive_path"]),
                    opts.get("archive_format", "7z"),
                )
                if made:
                    self.message.emit("Archive: %s (%s)"
                                      % (made, _human(made.stat().st_size)))

        except Exception as exc:  # noqa: BLE001 - a GUI must not die silently
            self.message.emit("ERROR: %s: %s" % (type(exc).__name__, exc))
            self.message.emit(traceback.format_exc())

        self.finished.emit(rows, time.perf_counter() - started, cancelled)

    # ------------------------------------------------------------------
    def _run_serial(self, jobs, chain_names, spec_dict, opts, total):
        """One drawing at a time, in this thread.  Exact progress."""
        rows = []
        for index, (src, out_dir) in enumerate(jobs, 1):
            if self._cancel:
                return rows, True
            row = engine._convert_task(
                src, out_dir, chain_names, spec_dict,
                opts["timeout"], opts["skip_existing"],
            )
            rows.append(row)
            self.progress.emit(index, total, row)
        return rows, False

    # ------------------------------------------------------------------
    def _run_parallel(self, jobs, chain_names, spec_dict, opts, total, workers):
        """Process pool.  Cancellation is checked between completions."""
        rows = []
        cancelled = False
        needs_serial = getattr(self, "_needs_serial", False)
        pool_kwargs: Dict[str, Any] = {"max_workers": workers}
        recycle = int(opts.get("recycle_after", 0) or 0)

        # THE MULTIPROCESSING CONTEXT, AND WHY IT IS CHOSEN EXPLICITLY.
        #
        # ``max_tasks_per_child`` looks like a free win -- it recycles a
        # worker after N drawings, which bounds resident memory.  But
        # passing it with no ``mp_context`` SILENTLY SWITCHES THE POOL TO
        # THE 'spawn' START METHOD, and it is incompatible with 'fork'
        # outright (ValueError).  Under spawn every worker re-imports the
        # program's entry module.  For a GUI that means each worker
        # importing Qt, and any unguarded top-level code running once per
        # worker.  Caught here by a test whose own output appeared four
        # times over.
        #
        # So the context is chosen deliberately rather than inherited:
        #   POSIX  -- 'fork'.  No re-import, near-instant worker start.
        #             Recycling is unavailable, and is not needed: the
        #             engine already drops each Drawing and runs the
        #             collector before returning.
        #   Windows -- 'spawn' is the only start method there anyway, so
        #             recycling costs nothing extra and is switched on.
        #             Re-import is safe because everything in this module
        #             below ``main()`` is behind an ``if __name__`` guard.
        import multiprocessing

        if os.name == "nt":
            pool_kwargs["mp_context"] = multiprocessing.get_context("spawn")
            if sys.version_info >= (3, 11) and recycle > 0:
                pool_kwargs["max_tasks_per_child"] = recycle
        else:
            pool_kwargs["mp_context"] = multiprocessing.get_context("fork")
            if recycle > 0:
                self.message.emit(
                    "Note: worker recycling is a Windows-only setting; on "
                    "this platform the 'fork' start method is used instead "
                    "(faster, and memory is bounded per drawing)."
                )

        with ProcessPoolExecutor(**pool_kwargs) as pool:
            futures = {
                pool.submit(
                    engine._convert_task, src, out_dir, chain_names,
                    spec_dict, opts["timeout"], opts["skip_existing"],
                ): src
                for src, out_dir in jobs
            }
            done_n = 0
            for fut in as_completed(futures):
                src = futures[fut]
                try:
                    row = fut.result()
                except Exception as exc:  # a worker died outright
                    row = engine.ConversionResult(
                        source=Path(src),
                        status="failed",
                        message="worker process failed: %s: %s"
                                % (type(exc).__name__, exc),
                    ).as_row()
                if needs_serial and row["status"] == "failed":
                    # Pass 2 has not run yet -- see the engine's note.
                    row["status"] = "retry-pending"
                rows.append(row)
                done_n += 1
                self.progress.emit(done_n, total, row)

                if self._cancel:
                    cancelled = True
                    # Drop everything not yet started; let running work end.
                    try:
                        pool.shutdown(wait=False, cancel_futures=True)
                    except TypeError:      # Python < 3.9
                        pool.shutdown(wait=False)
                    break
        return rows, cancelled

    # ------------------------------------------------------------------
    def _serial_retry(self, rows, chain_names, spec_dict, opts, total):
        """Retry failed drawings serially against the full backend chain.

        Pass 1 deliberately used only the parallel-safe prefix, so a sheet
        that failed there has not yet seen the serial-only backends.  This
        gives it that chance without having serialised the whole run.
        """
        failed = [r for r in rows if r["status"] == "retry-pending"]
        if not failed:
            for row in rows:
                if row["status"] == "retry-pending":
                    row["status"] = "failed"
            return rows
        self.message.emit(
            "Pass 2: retrying %d failed drawing(s) serially against %s"
            % (len(failed), " -> ".join(chain_names))
        )
        by_source = {r["source"]: r for r in rows}
        for index, row in enumerate(failed, 1):
            if self._cancel:
                break
            source = Path(row["source"])
            out_dir = engine.plan_output(
                source, opts["in_root"], opts["out_root"], opts["flat"]
            )
            new_row = engine._convert_task(
                str(source), str(out_dir), chain_names, spec_dict,
                opts["timeout"], opts["skip_existing"],
            )
            by_source[row["source"]] = new_row
            self.progress.emit(total, total, new_row)
        out = list(by_source.values())
        for row in out:
            if row["status"] == "retry-pending":
                row["status"] = "failed"   # pass 2 was cancelled
        return out

    # ------------------------------------------------------------------
    def _make_archive(self, out_root: Path, target: Path,
                      fmt: str) -> Optional[Path]:
        """Package the whole output folder into one archive.

        Parameters
        ----------
        out_root : pathlib.Path
            Folder to archive.
        target : pathlib.Path
            Archive path.  Its suffix is corrected to match *fmt*.
        fmt : {"7z", "zip"}
            ``"7z"`` is tried first when requested; if no 7-Zip binary is on
            the machine the code falls back to ZIP and says so, rather than
            failing at the very end of a long run.

        Returns
        -------
        pathlib.Path or None
            The archive written, or ``None`` on failure.
        """
        import shutil

        if fmt == "7z":
            exe = (shutil.which("7z") or shutil.which("7za")
                   or shutil.which("7zz")
                   or _first_existing([
                       r"C:\Program Files\7-Zip\7z.exe",
                       r"C:\Program Files (x86)\7-Zip\7z.exe",
                   ]))
            if exe:
                target = target.with_suffix(".7z")
                if target.exists():
                    target.unlink()
                self.message.emit("Packaging with 7-Zip: %s" % exe)
                proc = subprocess.run(
                    [str(exe), "a", "-t7z", "-mx=7", str(target),
                     str(out_root / "*")],
                    capture_output=True, text=True, errors="replace",
                )
                if target.is_file() and target.stat().st_size > 0:
                    return target
                self.message.emit(
                    "7-Zip failed (rc=%d): %s -- falling back to ZIP"
                    % (proc.returncode,
                       (proc.stderr or proc.stdout).strip()[:200])
                )
            else:
                self.message.emit(
                    "No 7-Zip binary found (7z/7za/7zz). Falling back to "
                    "ZIP. Install 7-Zip from https://www.7-zip.org for .7z."
                )

        # ZIP fallback: pure standard library, always available.
        base = str(target.with_suffix(""))
        made = shutil.make_archive(base, "zip", root_dir=str(out_root))
        return Path(made)


def _first_existing(paths) -> Optional[str]:
    """Return the first path in *paths* that exists on disk, else ``None``."""
    for p in paths:
        if os.path.isfile(p):
            return p
    return None


def _human(n: float) -> str:
    """Format a byte count, e.g. ``"1.4 MiB"``."""
    for unit in ("B", "KiB", "MiB", "GiB"):
        if abs(n) < 1024.0:
            return "%.1f %s" % (n, unit)
        n /= 1024.0
    return "%.1f TiB" % n


# ============================================================================
# %% DETACHABLE LOG WINDOW
# ============================================================================
class LogWindow(QtWidgets.QMainWindow):
    """A free-standing viewer onto the main window's log buffer.

    A long conversion is exactly when you want to read the log and change
    settings at the same time, which a tab cannot do.  This is a real
    top-level window, so it can be moved to a second monitor and resized
    independently.  It shares the parent's :class:`QTextDocument`, so both
    views scroll the same text with no copying and no risk of divergence.
    """

    def __init__(self, source_view: QtWidgets.QPlainTextEdit, parent=None):
        super().__init__(parent)
        self.setWindowTitle("dwg2pdf - detailed log")
        self.resize(920, 620)

        self.view = QtWidgets.QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(QtGui.QFont("Monospace", 9))
        self.view.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        # Share the document rather than copy the text.
        self.view.setDocument(source_view.document())
        self.setCentralWidget(self.view)

        bar = self.addToolBar("log")
        act_bottom = bar.addAction("Scroll to end")
        act_bottom.triggered.connect(
            lambda: self.view.verticalScrollBar().setValue(
                self.view.verticalScrollBar().maximum()
            )
        )
        act_copy = bar.addAction("Copy all")
        act_copy.triggered.connect(
            lambda: QtWidgets.QApplication.clipboard().setText(
                self.view.toPlainText()
            )
        )
        act_save = bar.addAction("Save as...")
        act_save.triggered.connect(self._save)

    def _save(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save log", "dwg2pdf_log.txt", "Text files (*.txt)"
        )
        if fn:
            Path(fn).write_text(self.view.toPlainText(), encoding="utf-8")


# ============================================================================
# %% MAIN WINDOW
# ============================================================================
class MainWindow(QtWidgets.QMainWindow):
    """The application window: five settings tabs plus results and log."""

    def __init__(self, log_handler: Optional["QtLogHandler"] = None) -> None:
        super().__init__()
        self.setWindowTitle(
            "dwg2pdf %s - DWG/DXF to PDF (GUI %s)"
            % (engine.__revision__, __revision__)
        )
        self._log_handler = log_handler
        self.resize(*_DEFAULT_SIZE)

        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[ConversionWorker] = None
        self._sources: List[Path] = []
        self._log_window: Optional[LogWindow] = None
        self._dark = False

        self._build_menu()
        self._build_ui()
        self._attach_logging()
        self.refresh_backends()
        self._update_command()

    # ------------------------------------------------------------------
    # %%% Construction
    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        """File / View / Help menus, including the Light/Dark switch."""
        m_file = self.menuBar().addMenu("&File")
        m_file.addAction("Add &folder...").triggered.connect(self._add_folder)
        m_file.addAction("Add f&iles...").triggered.connect(self._add_files)
        m_file.addSeparator()
        m_file.addAction("Re-&probe engines").triggered.connect(
            self.refresh_backends)
        m_file.addSeparator()
        act_quit = m_file.addAction("&Quit")
        act_quit.setShortcut(QtGui.QKeySequence.Quit)
        act_quit.triggered.connect(self.close)

        m_view = self.menuBar().addMenu("&View")
        self._theme_group = QtGui.QActionGroup(self)
        self._theme_group.setExclusive(True)
        for label, is_dark in (("&Light", False), ("&Dark", True)):
            act = QtGui.QAction(label, self, checkable=True)
            act.setChecked(is_dark == self._dark)
            act.triggered.connect(lambda _=False, d=is_dark: self.set_theme(d))
            self._theme_group.addAction(act)
            m_view.addAction(act)
        m_view.addSeparator()
        act_log = m_view.addAction("Open &log in window")
        act_log.setShortcut("Ctrl+L")
        act_log.triggered.connect(self.open_log_window)

        m_help = self.menuBar().addMenu("&Help")
        m_help.addAction("&About").triggered.connect(self._about)

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        outer = QtWidgets.QVBoxLayout(central)

        split = QtWidgets.QSplitter(Qt.Vertical)
        outer.addWidget(split, 1)

        self.tabs = QtWidgets.QTabWidget()
        self.tabs.addTab(self._tab_files(), "Files && Output")
        self.tabs.addTab(self._tab_engine(), "Engine")
        self.tabs.addTab(self._tab_page(), "Page Setup")
        self.tabs.addTab(self._tab_performance(), "Performance")
        self.tabs.addTab(self._tab_finish(), "Finish")
        split.addWidget(self.tabs)
        split.addWidget(self._results_panel())
        split.setSizes([470, 330])

        outer.addWidget(self._command_panel())
        outer.addLayout(self._action_bar())
        self.statusBar().showMessage("Ready")

    # -- Tab 1: Files & Output ----------------------------------------
    def _tab_files(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        # --- selected inputs -----------------------------------------
        gb_in = QtWidgets.QGroupBox("Selected drawing folders and files")
        v = QtWidgets.QVBoxLayout(gb_in)
        self.in_list = QtWidgets.QListWidget()
        self.in_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.in_list.setToolTip(
            "Any mix of folders and individual drawings. Folders are "
            "searched (recursively unless turned off below)."
        )
        v.addWidget(self.in_list, 1)
        row = QtWidgets.QHBoxLayout()
        for text, slot in (("Add folder...", self._add_folder),
                           ("Add files...", self._add_files),
                           ("Remove selected", self._remove_selected),
                           ("Clear", self._clear_inputs)):
            b = QtWidgets.QPushButton(text)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        lay.addWidget(gb_in, 1)

        # --- filters --------------------------------------------------
        gb_f = QtWidgets.QGroupBox("Which drawings")
        f = QtWidgets.QFormLayout(gb_f)
        self.preset_combo = QtWidgets.QComboBox()
        self.preset_combo.addItem("(everything)", None)
        for key in sorted(engine.PRESETS):
            if key != "all":
                self.preset_combo.addItem(key, engine.PRESETS[key])
        self.preset_combo.setToolTip(
            "Named path filters - shorthand for a --filter regular "
            "expression.\n\nEdit PRESETS at the top of dwg2pdf.py to name "
            "the subsets you actually use; they appear here automatically."
        )
        self.preset_combo.currentIndexChanged.connect(self._rescan)
        f.addRow("Preset", self.preset_combo)

        self.filter_edit = QtWidgets.QLineEdit()
        self.filter_edit.setPlaceholderText(
            "case-insensitive regular expression; overrides the preset")
        self.filter_edit.textChanged.connect(self._rescan)
        f.addRow("Filter (regex)", self.filter_edit)

        self.pattern_edit = QtWidgets.QLineEdit()
        self.pattern_edit.setPlaceholderText("filename glob, e.g. ASSY-*.dwg")
        self.pattern_edit.textChanged.connect(self._rescan)
        f.addRow("Filename glob", self.pattern_edit)

        self.limit_spin = QtWidgets.QSpinBox()
        self.limit_spin.setRange(0, 1000000)
        self.limit_spin.setSpecialValueText("no limit")
        self.limit_spin.setToolTip("Stop after N drawings, for a trial run.")
        self.limit_spin.valueChanged.connect(self._rescan)
        f.addRow("Limit", self.limit_spin)

        hb = QtWidgets.QHBoxLayout()
        self.recursive_cb = QtWidgets.QCheckBox("Search subfolders")
        self.recursive_cb.setChecked(True)
        self.recursive_cb.stateChanged.connect(self._rescan)
        self.dxf_cb = QtWidgets.QCheckBox("Include .dxf")
        self.dxf_cb.setChecked(True)
        self.dxf_cb.stateChanged.connect(self._rescan)
        self.skip_cb = QtWidgets.QCheckBox("Skip already-converted")
        self.skip_cb.setChecked(True)
        self.skip_cb.setToolTip(
            "Resume: a drawing whose PDF exists and is no older than the "
            "drawing is left alone."
        )
        self.skip_cb.stateChanged.connect(self._update_command)
        for cb in (self.recursive_cb, self.dxf_cb, self.skip_cb):
            hb.addWidget(cb)
        hb.addStretch(1)
        f.addRow("", hb)

        self.found_label = QtWidgets.QLabel("Nothing selected")
        font = self.found_label.font()
        font.setBold(True)
        self.found_label.setFont(font)
        f.addRow("Matched", self.found_label)
        lay.addWidget(gb_f)

        # --- output ---------------------------------------------------
        gb_out = QtWidgets.QGroupBox("Output")
        o = QtWidgets.QFormLayout(gb_out)
        self.out_edit = QtWidgets.QLineEdit()
        self.out_edit.setPlaceholderText("where the PDFs go")
        self.out_edit.textChanged.connect(self._refresh_preview)
        o.addRow("Output folder", self._with_browse(
            self.out_edit, self._pick_output))

        self.structure_group = QtWidgets.QButtonGroup(self)
        self.rb_mirror = QtWidgets.QRadioButton(
            "Replicate the source folder structure")
        self.rb_flat = QtWidgets.QRadioButton(
            "Flatten - every PDF in the output folder")
        self.rb_mirror.setChecked(True)
        self.rb_mirror.setToolTip(
            "The output tree mirrors the input tree, so a drawing in "
            "Sheets\\Panels lands in <output>\\Sheets\\Panels."
        )
        self.rb_flat.setToolTip(
            "Everything in one folder. Watch for name collisions - two "
            "drawings called Detail.dwg in different folders become one PDF."
        )
        self.structure_group.addButton(self.rb_mirror, 0)
        self.structure_group.addButton(self.rb_flat, 1)
        self.rb_mirror.toggled.connect(self._refresh_preview)
        sv = QtWidgets.QVBoxLayout()
        sv.addWidget(self.rb_mirror)
        sv.addWidget(self.rb_flat)
        o.addRow("Structure", sv)

        self.preview_view = QtWidgets.QPlainTextEdit()
        self.preview_view.setReadOnly(True)
        self.preview_view.setMaximumHeight(110)
        self.preview_view.setFont(QtGui.QFont("Monospace", 8))
        self.preview_view.setToolTip(
            "Where the first few PDFs will actually be written.")
        o.addRow("Preview", self.preview_view)
        lay.addWidget(gb_out)
        return w

    # -- Tab 2: Engine -------------------------------------------------
    def _tab_engine(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        gb = QtWidgets.QGroupBox("Conversion strategy")
        f = QtWidgets.QFormLayout(gb)
        self.strategy_combo = QtWidgets.QComboBox()
        self.strategy_combo.addItem(
            "Without AutoCAD first, fall back to AutoCAD", "no-autocad-first")
        self.strategy_combo.addItem(
            "AutoCAD first, fall back to the rest", "autocad-first")
        self.strategy_combo.addItem(
            "AutoCAD only (no fallback)", "autocad-only")
        self.strategy_combo.addItem(
            "Best available only (no fallback)", "single")
        self.strategy_combo.setToolTip(
            "The fallback is per drawing, not per run: if one sheet defeats "
            "the first engine, only that sheet goes to the next one."
        )
        self.strategy_combo.currentIndexChanged.connect(self._update_command)
        f.addRow("Strategy", self.strategy_combo)

        self.backend_combo = QtWidgets.QComboBox()
        self.backend_combo.currentIndexChanged.connect(self._update_command)
        self.backend_combo.setToolTip(
            "Force one engine and disable the fallback chain entirely.")
        f.addRow("Force engine", self.backend_combo)

        self.acc_edit = QtWidgets.QLineEdit()
        self.acc_edit.setPlaceholderText(
            r"auto-detected; e.g. C:\Program Files\Autodesk\AutoCAD 2025\accoreconsole.exe")
        self.acc_edit.setToolTip(
            "Override the path to AutoCAD's accoreconsole.exe.\n"
            "Only needed if AutoCAD is installed somewhere unusual."
        )
        f.addRow("accoreconsole.exe", self._with_browse(
            self.acc_edit, self._pick_accore))

        self.timeout_spin = QtWidgets.QSpinBox()
        self.timeout_spin.setRange(10, 3600)
        self.timeout_spin.setValue(300)
        self.timeout_spin.setSuffix(" s")
        self.timeout_spin.valueChanged.connect(self._update_command)
        f.addRow("Timeout per drawing", self.timeout_spin)

        self.accscript_edit = QtWidgets.QLineEdit()
        self.accscript_edit.setPlaceholderText(
            "optional .scr template; '{output}' is replaced with the PDF path")
        self.accscript_edit.setToolTip(
            "Replaces the generated AutoCAD script entirely. Use if your\n"
            "AutoCAD release's -EXPORTPDF prompt sequence differs.\n\n"
            "Remember: in an AutoCAD script a SPACE is Enter, so any path\n"
            "must be in double quotes."
        )
        self.accscript_edit.textChanged.connect(self._update_command)
        f.addRow("AutoCAD script", self._with_browse(
            self.accscript_edit, self._pick_accscript))

        self.acclang_edit = QtWidgets.QLineEdit()
        self.acclang_edit.setPlaceholderText("blank = do not pass /l")
        self.acclang_edit.setToolTip(
            "AutoCAD /l language code, e.g. en-US. Leave blank unless you\n"
            "know the pack is installed: passing an absent one fails with\n"
            "'Unable to Process Configuration File', which looks like a plot\n"
            "problem and is not one."
        )
        self.acclang_edit.textChanged.connect(self._update_command)
        f.addRow("AutoCAD language", self.acclang_edit)
        lay.addWidget(gb)

        gb2 = QtWidgets.QGroupBox("Engines detected on this machine")
        v2 = QtWidgets.QVBoxLayout(gb2)
        self.backend_view = QtWidgets.QPlainTextEdit()
        self.backend_view.setReadOnly(True)
        self.backend_view.setFont(QtGui.QFont("Monospace", 8))
        self.backend_view.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        v2.addWidget(self.backend_view)
        b = QtWidgets.QPushButton("Re-probe")
        b.clicked.connect(self.refresh_backends)
        v2.addWidget(b, 0, Qt.AlignLeft)
        lay.addWidget(gb2, 1)

        acad_note = QtWidgets.QLabel(
            "<b>Two ways to use AutoCAD.</b> <tt>accoreconsole</tt> is "
            "AutoCAD's headless core console - no window, and it "
            "parallelises. <tt>acad-com</tt> drives the <i>full</i> AutoCAD "
            "application over COM with <tt>Application.Visible = False</tt>, "
            "so you get real plot styles, page setups, xrefs and SHX fonts "
            "with no window; it is serial, and it needs "
            "<tt>pip install pywin32</tt>. If AutoCAD is already running it "
            "attaches to that instance and leaves your window visible rather "
            "than hiding a session you are working in. "
            "(<tt>acad.exe /b</tt> is not used: it has no headless mode.)"
        )
        acad_note.setWordWrap(True)
        acad_note.setStyleSheet("QLabel { padding: 6px; }")
        lay.addWidget(acad_note)

        note = QtWidgets.QLabel(
            "<b>DWG TrueView is deliberately excluded.</b> It was tried and it "
            "crashed - <tt>Unhandled Exception c0000027</tt> (STATUS_UNWIND) - "
            "and separately raised a modal <i>configuration file may be "
            "locked</i> dialog, which in an unattended batch is a hang. "
            "TrueView is a viewer with no plotting engine; Autodesk does not "
            "support driving it this way. Use AutoCAD, or the bundled "
            "LibreDWG, which needs no Autodesk software at all."
        )
        note.setWordWrap(True)
        note.setStyleSheet("QLabel { padding: 6px; }")
        lay.addWidget(note)
        return w

    # -- Tab 3: Page setup ---------------------------------------------
    def _tab_page(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        f = QtWidgets.QFormLayout(w)

        self.layouts_combo = QtWidgets.QComboBox()
        self.layouts_combo.addItem(
            "Automatic - paper space where it has content, else model", "auto")
        self.layouts_combo.addItem("Model space only", "model")
        self.layouts_combo.addItem("Paper space layouts", "paper")
        self.layouts_combo.addItem("Both", "all")
        self.layouts_combo.setToolTip(
            "Automatic decides per drawing and is the safe choice for an\n"
            "uncatalogued archive.\n\n"
            "Choosing 'Paper space layouts' on a drawing whose content is in\n"
            "model space finds AutoCAD's empty default Layout1 and renders\n"
            "nothing - a whole run of failures from one wrong setting.\n"
            "Choosing 'Model space only' on a drawing with a real title-block\n"
            "layout throws that sheet away."
        )
        self.layouts_combo.currentIndexChanged.connect(self._update_command)
        f.addRow("Layouts", self.layouts_combo)

        self.layout_name_edit = QtWidgets.QLineEdit()
        self.layout_name_edit.setPlaceholderText(
            "optional: one named layout, overrides the choice above")
        self.layout_name_edit.textChanged.connect(self._update_command)
        f.addRow("Named layout", self.layout_name_edit)

        self.paper_combo = QtWidgets.QComboBox()
        self.paper_combo.addItem(
            "AUTO - detect from the drawing's paper space", "AUTO")
        self.paper_combo.addItem("FIT - size the page to the drawing", "FIT")
        for key in sorted(k for k in engine.PAPER_SIZES_MM
                          if k not in ("FIT", "AUTO")):
            self.paper_combo.addItem(key, key)
        self.paper_combo.setToolTip(
            "AUTO reads the sheet size stored in the drawing's paper space "
            "page setup - what the draughtsman chose when they last plotted "
            "it - and falls back to FIT for a drawing that has none."
        )
        self.paper_combo.currentIndexChanged.connect(self._update_command)
        f.addRow("Paper", self.paper_combo)

        self.units_combo = QtWidgets.QComboBox()
        for label, val in (
            ("Automatic - read the drawing's own units", "auto"),
            ("Inches", "inch"), ("Feet", "ft"),
            ("Millimetres", "mm"), ("Centimetres", "cm"), ("Metres", "m"),
        ):
            self.units_combo.addItem(label, val)
        self.units_combo.setToolTip(
            "What one drawing unit means. This sets the PHYSICAL SIZE of a\n"
            "fitted page and matters more than it sounds:\n\n"
            "A DXF stores bare numbers, so a 44 x 34 unit ANSI E sheet\n"
            "becomes a 44 x 34 MILLIMETRE page unless something says those\n"
            "units were inches.\n\n"
            "Automatic reads $INSUNITS, then $MEASUREMENT (0 = English ->\n"
            "inches), then falls back to mm. Older US drawings are often\n"
            "unitless with $MEASUREMENT=0, so Automatic reads them as\n"
            "inches - turning a 54 mm page into the 1118 x 864 mm sheet\n"
            "the drawing actually is."
        )
        self.units_combo.currentIndexChanged.connect(self._update_command)
        f.addRow("Drawing units", self.units_combo)

        self.landscape_cb = QtWidgets.QCheckBox("Landscape")
        self.landscape_cb.stateChanged.connect(self._update_command)
        f.addRow("", self.landscape_cb)

        self.maxpage_spin = QtWidgets.QDoubleSpinBox()
        self.maxpage_spin.setRange(0.0, 10000.0)
        self.maxpage_spin.setValue(1189.0)
        self.maxpage_spin.setSuffix(" mm")
        self.maxpage_spin.setToolTip(
            "Cap on an auto-sized page. A CAD drawing is modelled at full "
            "scale, so an uncapped fit page can come out kilometres across.\n"
            "1189 mm is the long edge of A0. 0 disables the cap."
        )
        self.maxpage_spin.valueChanged.connect(self._update_command)
        f.addRow("Max page", self.maxpage_spin)

        self.margin_spin = QtWidgets.QDoubleSpinBox()
        self.margin_spin.setRange(0.0, 100.0)
        self.margin_spin.setValue(5.0)
        self.margin_spin.setSuffix(" mm")
        self.margin_spin.valueChanged.connect(self._update_command)
        f.addRow("Margin", self.margin_spin)

        self.scale_spin = QtWidgets.QDoubleSpinBox()
        self.scale_spin.setRange(0.0, 1000.0)
        self.scale_spin.setDecimals(6)
        self.scale_spin.setSingleStep(0.01)
        self.scale_spin.setValue(0.0)
        self.scale_spin.setSpecialValueText("fit to page")
        self.scale_spin.setToolTip(
            "Plot scale as a ratio: 0.02 is 1:50. Leave at 'fit to page' "
            "unless the PDFs will be measured off."
        )
        self.scale_spin.valueChanged.connect(self._update_command)
        f.addRow("Scale", self.scale_spin)

        self.mono_cb = QtWidgets.QCheckBox(
            "Monochrome (as a plotted drawing usually is)")
        self.mono_cb.setChecked(True)
        self.mono_cb.stateChanged.connect(self._update_command)
        f.addRow("", self.mono_cb)

        self.lw_spin = QtWidgets.QDoubleSpinBox()
        self.lw_spin.setRange(0.1, 10.0)
        self.lw_spin.setSingleStep(0.5)
        self.lw_spin.setValue(1.0)
        self.lw_spin.setToolTip("Try 2.0 if the lines look too thin.")
        self.lw_spin.valueChanged.connect(self._update_command)
        f.addRow("Line weight multiplier", self.lw_spin)

        self.bg_combo = QtWidgets.QComboBox()
        for label, val in (("White", "white"), ("Black", "black"),
                           ("Transparent", "off"), ("Drawing default",
                                                    "default")):
            self.bg_combo.addItem(label, val)
        self.bg_combo.currentIndexChanged.connect(self._update_command)
        f.addRow("Background", self.bg_combo)

        self.trim_cb = QtWidgets.QCheckBox(
            "Ignore stray far-flung entities when fitting the page")
        self.trim_cb.setChecked(True)
        self.trim_cb.setToolTip(
            "One entity with an absurd scale can define the page and shrink "
            "the real drawing to a speck. Measured on a real DWG: a single "
            "INSERT spanning 3,411,857 units against a median of 838.\n"
            "Nothing is deleted - the outlier just no longer sets the page.\n"
            "Recommended for an old archive."
        )
        self.trim_cb.stateChanged.connect(self._update_command)
        f.addRow("", self.trim_cb)

        self.outlier_spin = QtWidgets.QDoubleSpinBox()
        self.outlier_spin.setRange(1.0, 1000.0)
        self.outlier_spin.setValue(20.0)
        self.outlier_spin.setToolTip(
            "An entity is an outlier when its span exceeds this many times "
            "the 95th-percentile span."
        )
        self.outlier_spin.valueChanged.connect(self._update_command)
        f.addRow("Outlier factor", self.outlier_spin)
        return w

    # -- Tab 4: Performance --------------------------------------------
    def _tab_performance(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        gb = QtWidgets.QGroupBox("Parallelism")
        f = QtWidgets.QFormLayout(gb)
        self.par_combo = QtWidgets.QComboBox()
        self.par_combo.addItem("Automatic (by CPU cores)", "cores")
        self.par_combo.addItem("Fixed job count", "jobs")
        self.par_combo.addItem("Serial (one at a time)", "serial")
        self.par_combo.currentIndexChanged.connect(self._parallel_changed)
        f.addRow("Mode", self.par_combo)

        self.core_pct_spin = QtWidgets.QSpinBox()
        self.core_pct_spin.setRange(10, 100)
        self.core_pct_spin.setValue(DEFAULT_CORE_PERCENT)
        self.core_pct_spin.setSuffix(" % of cores")
        self.core_pct_spin.valueChanged.connect(self._parallel_changed)
        f.addRow("Core usage", self.core_pct_spin)

        self.jobs_spin = QtWidgets.QSpinBox()
        self.jobs_spin.setRange(1, WORKER_CAP)
        self.jobs_spin.setValue(max(1, min(4, os.cpu_count() or 1)))
        self.jobs_spin.valueChanged.connect(self._parallel_changed)
        f.addRow("Jobs", self.jobs_spin)

        self.workers_label = QtWidgets.QLabel()
        wf = self.workers_label.font()
        wf.setBold(True)
        self.workers_label.setFont(wf)
        f.addRow("Workers to use", self.workers_label)
        lay.addWidget(gb)

        gb2 = QtWidgets.QGroupBox("Memory")
        f2 = QtWidgets.QFormLayout(gb2)
        self.recycle_spin = QtWidgets.QSpinBox()
        self.recycle_spin.setRange(0, 10000)
        self.recycle_spin.setValue(0)
        self.recycle_spin.setSpecialValueText("never (recommended)")
        self.recycle_spin.setToolTip(
            "Restart each worker after this many drawings.\n\n"
            "OFF BY DEFAULT, deliberately. On Windows the pool uses the\n"
            "'spawn' start method, so every recycled worker re-imports the\n"
            "entry module - from the GUI that means re-importing all of Qt.\n"
            "All workers also hit the limit on the SAME drawing and respawn\n"
            "together: 4 workers with N=25 lands exactly on drawing 100, and\n"
            "the run appears to freeze.\n\n"
            "Memory is already bounded per drawing, so leave this off unless\n"
            "you have measured a leak."
        )
        self.recycle_spin.valueChanged.connect(self._update_command)
        f2.addRow("Recycle worker after", self.recycle_spin)

        self.mem_cb = QtWidgets.QCheckBox(
            "Log resident memory every ten drawings")
        self.mem_cb.stateChanged.connect(self._update_command)
        f2.addRow("", self.mem_cb)
        lay.addWidget(gb2)

        warn = QtWidgets.QLabel(
            "<b>Leave worker recycling off unless you have measured a "
            "leak.</b> On Windows a recycled worker re-imports the entry "
            "module (all of Qt, from here), and every worker hits the limit "
            "on the same drawing - 4 workers with N=25 respawn together at "
            "drawing 100 and the run looks frozen."
        )
        warn.setWordWrap(True)
        warn.setStyleSheet("QLabel { padding: 6px; }")
        lay.addWidget(warn)

        note = QtWidgets.QLabel(PARALLEL_MODE_NOTE)
        note.setWordWrap(True)
        note.setStyleSheet("QLabel { padding: 8px; }")
        lay.addWidget(note)
        lay.addStretch(1)
        self._parallel_changed()
        return w

    # -- Tab 5: Finish -------------------------------------------------
    def _tab_finish(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)

        gb = QtWidgets.QGroupBox("After the conversion")
        f = QtWidgets.QFormLayout(gb)

        self.manifest_cb = QtWidgets.QCheckBox(
            "Write manifest.csv and manifest.json")
        self.manifest_cb.setChecked(True)
        self.manifest_cb.setToolTip(
            "A complete census of the input set: what converted, what did "
            "not and why, which engine produced each PDF, and the settings "
            "used. On a set of any size this is the only way to check that "
            "'the batch finished' means what it says."
        )
        self.manifest_cb.stateChanged.connect(self._update_command)
        f.addRow("", self.manifest_cb)

        self.merge_cb = QtWidgets.QCheckBox(
            "Also merge every PDF into one document")
        self.merge_cb.stateChanged.connect(self._update_command)
        f.addRow("", self.merge_cb)

        self.archive_cb = QtWidgets.QCheckBox(
            "Package the output folder into one archive")
        self.archive_cb.setChecked(True)
        self.archive_cb.stateChanged.connect(self._archive_changed)
        f.addRow("", self.archive_cb)

        self.archive_fmt = QtWidgets.QComboBox()
        self.archive_fmt.addItem("7z (7-Zip, smaller)", "7z")
        self.archive_fmt.addItem("zip (no extra software needed)", "zip")
        self.archive_fmt.setToolTip(
            "7z needs 7-Zip on the machine. If it is not found the run "
            "falls back to ZIP and says so rather than failing at the end "
            "of a long batch."
        )
        self.archive_fmt.currentIndexChanged.connect(self._archive_changed)
        f.addRow("Archive format", self.archive_fmt)

        self.archive_edit = QtWidgets.QLineEdit()
        self.archive_edit.setToolTip(
            "Archive path. The default name carries the engine and GUI "
            "revisions and a timestamp, so two runs never overwrite one "
            "another and any archive can be traced to the code that made it."
        )
        f.addRow("Archive file", self._with_browse(
            self.archive_edit, self._pick_archive))
        lay.addWidget(gb)

        lay.addStretch(1)
        self._archive_changed()
        return w

    # -- results + log --------------------------------------------------
    def _results_panel(self) -> QtWidgets.QWidget:
        tabs = QtWidgets.QTabWidget()

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Drawing", "Status", "Entities", "Engine", "Detail"])
        head = self.table.horizontalHeader()
        for col in range(4):
            head.setSectionResizeMode(
                col, QtWidgets.QHeaderView.ResizeToContents)
        head.setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        tabs.addTab(self.table, "Results")

        log_page = QtWidgets.QWidget()
        lv = QtWidgets.QVBoxLayout(log_page)
        lv.setContentsMargins(0, 0, 0, 0)
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QtGui.QFont("Monospace", 8))
        self.log_view.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.log_view.setMaximumBlockCount(200000)
        lv.addWidget(self.log_view, 1)
        hb = QtWidgets.QHBoxLayout()
        b_open = QtWidgets.QPushButton("Open log in window")
        b_open.clicked.connect(self.open_log_window)
        b_clear = QtWidgets.QPushButton("Clear")
        b_clear.clicked.connect(self.log_view.clear)
        b_save = QtWidgets.QPushButton("Save log...")
        b_save.clicked.connect(self._save_log)
        for b in (b_open, b_clear, b_save):
            hb.addWidget(b)
        hb.addStretch(1)
        lv.addLayout(hb)
        tabs.addTab(log_page, "Detailed log")
        return tabs

    def _command_panel(self) -> QtWidgets.QWidget:
        gb = QtWidgets.QGroupBox("Equivalent command line")
        v = QtWidgets.QVBoxLayout(gb)
        self.command_view = QtWidgets.QPlainTextEdit()
        self.command_view.setReadOnly(True)
        self.command_view.setMaximumHeight(76)
        self.command_view.setFont(QtGui.QFont("Monospace", 8))
        self.command_view.setToolTip(
            "Exactly these settings, as a command. Copy it into a terminal "
            "for scripted or scheduled runs."
        )
        v.addWidget(self.command_view)
        b = QtWidgets.QPushButton("Copy command")
        b.clicked.connect(
            lambda: QtWidgets.QApplication.clipboard().setText(
                self.command_view.toPlainText()))
        v.addWidget(b, 0, Qt.AlignLeft)
        return gb

    def _action_bar(self) -> QtWidgets.QHBoxLayout:
        bar = QtWidgets.QHBoxLayout()
        self.progress = QtWidgets.QProgressBar()
        self.progress.setTextVisible(True)
        bar.addWidget(self.progress, 1)

        self.dry_btn = QtWidgets.QPushButton("Dry run")
        self.dry_btn.setToolTip("List what would be produced. Converts nothing.")
        self.dry_btn.clicked.connect(self.dry_run)
        bar.addWidget(self.dry_btn)

        self.run_btn = QtWidgets.QPushButton("Convert")
        self.run_btn.setDefault(True)
        self.run_btn.clicked.connect(self.start_run)
        bar.addWidget(self.run_btn)

        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        bar.addWidget(self.cancel_btn)
        return bar

    @staticmethod
    def _with_browse(edit: QtWidgets.QLineEdit, slot) -> QtWidgets.QWidget:
        """A line edit with a Browse button glued to its right."""
        wrap = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(wrap)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(edit, 1)
        b = QtWidgets.QPushButton("Browse...")
        b.clicked.connect(slot)
        row.addWidget(b)
        return wrap

    # ------------------------------------------------------------------
    # %%% Behaviour
    # ------------------------------------------------------------------
    def set_theme(self, dark: bool) -> None:
        """Apply the light or dark palette to the whole application."""
        self._dark = dark
        apply_theme(QtWidgets.QApplication.instance(), dark)

    def _attach_logging(self) -> None:
        """Connect the log handler to the panel and replay the backlog.

        Called after the widgets exist but before the first backend probe,
        so the font-cache chatter that probe provokes lands in the panel
        rather than on a console nobody is looking at.
        """
        if self._log_handler is None:
            return
        self._log_handler.bridge.line.connect(self._log)
        for line in self._log_handler.go_live():
            self._log(line)

    def open_log_window(self) -> None:
        """Pop the log out into its own resizable top-level window."""
        if self._log_window is None:
            self._log_window = LogWindow(self.log_view, self)
        self._log_window.show()
        self._log_window.raise_()
        self._log_window.activateWindow()

    def _save_log(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save log", "dwg2pdf_log.txt", "Text files (*.txt)")
        if fn:
            Path(fn).write_text(self.log_view.toPlainText(), encoding="utf-8")

    def _about(self) -> None:
        QtWidgets.QMessageBox.about(
            self, "About dwg2pdf",
            "<b>dwg2pdf</b><br>Engine revision %s, GUI revision %s<br><br>"
            "Batch conversion of 2D AutoCAD drawings to PDF.<br><br>"
            "Works with or without AutoCAD. Windows LibreDWG binaries are "
            "bundled, so a machine with no Autodesk software can still "
            "convert DWG; where AutoCAD is present it is used as a "
            "per-drawing fallback, or exclusively if you ask."
            % (engine.__revision__, __revision__)
        )

    # -- inputs ---------------------------------------------------------
    def _add_folder(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Add a drawings folder")
        if path:
            self._append_input(path)
            if not self.out_edit.text().strip():
                self.out_edit.setText(str(Path(path) / "PDF"))

    def _add_files(self) -> None:
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add drawings", "",
            "Drawings (*.dwg *.dxf);;All files (*)")
        for f in files:
            self._append_input(f)

    def _append_input(self, path: str) -> None:
        existing = {self.in_list.item(i).text()
                    for i in range(self.in_list.count())}
        if path not in existing:
            self.in_list.addItem(path)
        self._rescan()

    def _remove_selected(self) -> None:
        for item in self.in_list.selectedItems():
            self.in_list.takeItem(self.in_list.row(item))
        self._rescan()

    def _clear_inputs(self) -> None:
        self.in_list.clear()
        self._rescan()

    def _input_paths(self) -> List[Path]:
        return [Path(self.in_list.item(i).text()).expanduser()
                for i in range(self.in_list.count())]

    def _pick_output(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Output folder")
        if path:
            self.out_edit.setText(path)

    def _pick_accore(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Locate accoreconsole.exe", "",
            "accoreconsole (accoreconsole.exe);;All files (*)")
        if fn:
            self.acc_edit.setText(fn)
            self.refresh_backends()

    def _pick_accscript(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "AutoCAD script template", "",
            "AutoCAD scripts (*.scr);;All files (*)")
        if fn:
            self.accscript_edit.setText(fn)

    def _pick_archive(self) -> None:
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Archive file", self.archive_edit.text(),
            "Archives (*.7z *.zip);;All files (*)")
        if fn:
            self.archive_edit.setText(fn)

    # -- probing / scanning ---------------------------------------------
    def refresh_backends(self) -> None:
        """Probe the machine and repopulate the engine list."""
        override = self.acc_edit.text().strip() if hasattr(self, "acc_edit") else ""
        if override and os.path.isfile(override):
            # Put the user's explicit path at the front of the search list.
            engine._DEFAULT_TOOL_PATHS["accoreconsole"] = (
                (override,) + tuple(engine._DEFAULT_TOOL_PATHS["accoreconsole"])
            )

        self.backend_combo.blockSignals(True)
        self.backend_combo.clear()
        self.backend_combo.addItem("Automatic (use the strategy above)", None)

        lines: List[str] = []
        n_ok = 0
        for cls in sorted(engine.BACKEND_CLASSES, key=lambda c: c.rank):
            ok = cls.available()
            usable = ok and not cls.unreliable
            mark = "available" if usable else ("DISABLED " if cls.unreliable
                                              else "   --    ")
            lines.append("%s  %d. %-16s %s" % (mark, cls.rank, cls.name,
                                               cls.describe()))
            if usable:
                n_ok += 1
                self.backend_combo.addItem(cls.name, cls.name)
        self.backend_view.setPlainText("\n".join(lines))
        self.backend_combo.blockSignals(False)

        if n_ok == 0:
            self.statusBar().showMessage(
                "No usable conversion engine found - see the Engine tab")
            self._log(engine._no_backend_message(need_dwg=True))
        else:
            self.statusBar().showMessage("%d conversion engine(s) available"
                                         % n_ok)
        self._update_command()

    def _rescan(self) -> None:
        """Rescan the inputs, debounced so typing does not walk the tree."""
        if not hasattr(self, "_scan_timer"):
            self._scan_timer = QtCore.QTimer(self)
            self._scan_timer.setSingleShot(True)
            self._scan_timer.setInterval(350)
            self._scan_timer.timeout.connect(self.scan_inputs)
        self._scan_timer.start()

    def scan_inputs(self) -> None:
        """Discover matching drawings and report the count."""
        roots = self._input_paths()
        self._sources = []
        if not roots:
            self.found_label.setText("Nothing selected")
            self._refresh_preview()
            return
        try:
            self._sources = engine.discover_inputs(
                roots,
                recursive=self.recursive_cb.isChecked(),
                include_dxf=self.dxf_cb.isChecked(),
                pattern=self.pattern_edit.text().strip() or None,
                regex=self._active_regex(),
            )
        except Exception as exc:  # noqa: BLE001
            self.found_label.setText("scan failed: %s" % exc)
            return
        limit = self.limit_spin.value()
        if limit:
            self._sources = self._sources[:limit]
        n_dwg = sum(1 for p in self._sources if p.suffix.lower() == ".dwg")
        self.found_label.setText(
            "%d drawing(s) - %d DWG, %d DXF"
            % (len(self._sources), n_dwg, len(self._sources) - n_dwg)
        )
        self._refresh_preview()

    def _active_regex(self) -> Optional[str]:
        """The filter in force: an explicit regex beats the preset."""
        text = self.filter_edit.text().strip()
        return text if text else self.preset_combo.currentData()

    def _in_root(self) -> Path:
        """Common root the mirrored output tree is relative to."""
        roots = self._input_paths()
        if len(roots) == 1 and roots[0].is_dir():
            return roots[0].resolve()
        if self._sources:
            return Path(os.path.commonpath(
                [str(p.parent) for p in self._sources]))
        return Path.cwd()

    def _refresh_preview(self) -> None:
        """Show where the first few PDFs will actually land."""
        if not hasattr(self, "preview_view"):
            return
        out_text = self.out_edit.text().strip()
        if not self._sources or not out_text:
            self.preview_view.setPlainText(
                "Select drawings and an output folder to see the plan.")
            self._update_command()
            return
        out_root = Path(out_text).expanduser()
        in_root = self._in_root()
        flat = self.rb_flat.isChecked()
        lines = []
        for src in self._sources[:6]:
            d = engine.plan_output(src, in_root, out_root, flat)
            lines.append("%s\n    -> %s" % (src.name, d / (src.stem + ".pdf")))
        if len(self._sources) > 6:
            lines.append("... and %d more" % (len(self._sources) - 6))
        self.preview_view.setPlainText("\n".join(lines))
        self._update_command()

    def _parallel_changed(self) -> None:
        """Enable the relevant control and show the resolved worker count."""
        mode = self.par_combo.currentData()
        self.core_pct_spin.setEnabled(mode == "cores")
        self.jobs_spin.setEnabled(mode == "jobs")
        n = resolve_worker_count(mode, self.core_pct_spin.value(),
                                 self.jobs_spin.value())
        note = ""
        try:
            chain = engine.select_backend_chain(
                self.backend_combo.currentData(), True,
                strategy=self.strategy_combo.currentData())
            prefix, needs_serial = engine.split_chain_for_parallel(chain)
            if not prefix:
                note = "  - forced serial: %s cannot run concurrently" % chain[0].name
            elif needs_serial:
                note = ("  - pass 1 parallel, failures retried serially "
                        "(%s is serial-only)"
                        % ", ".join(c.name for c in chain
                                    if not c.parallel_safe))
        except Exception:  # noqa: BLE001 - probing must never break the tab
            pass
        self.workers_label.setText(
            "%d  (this machine reports %d logical cores; cap %d)%s"
            % (n, os.cpu_count() or 1, WORKER_CAP, note)
        )
        self._update_command()

    def _archive_changed(self) -> None:
        """Enable the archive controls and refresh the default name."""
        on = self.archive_cb.isChecked()
        self.archive_fmt.setEnabled(on)
        self.archive_edit.setEnabled(on)
        if on and not self.archive_edit.text().strip():
            self.archive_edit.setText(str(self._default_archive_path()))
        self._update_command()

    def _default_archive_path(self) -> Path:
        """Revision- and timestamp-stamped archive name.

        Both revisions and a timestamp are in the name so that two runs never
        overwrite one another and any archive can be traced back to the exact
        code that produced it.
        """
        ext = self.archive_fmt.currentData() if hasattr(self, "archive_fmt") else "7z"
        stamp = time.strftime("%Y%m%d-%H%M%S")
        name = "dwg2pdf_out_v%s_gui%s_%s.%s" % (
            engine.__revision__, __revision__, stamp, ext)
        out_text = self.out_edit.text().strip() if hasattr(self, "out_edit") else ""
        parent = Path(out_text).expanduser().parent if out_text else Path.cwd()
        return parent / name

    # -- settings -> engine objects -------------------------------------
    def _spec(self) -> "engine.PageSpec":
        """Build a :class:`~dwg2pdf.PageSpec` from the widgets."""
        named = self.layout_name_edit.text().strip()
        return engine.PageSpec(
            paper=self.paper_combo.currentData(),
            units=self.units_combo.currentData(),
            landscape=self.landscape_cb.isChecked(),
            max_page_mm=self.maxpage_spin.value(),
            trim_outliers=self.trim_cb.isChecked(),
            outlier_factor=self.outlier_spin.value(),
            margin_mm=self.margin_spin.value(),
            scale=self.scale_spin.value(),
            layouts=named if named else self.layouts_combo.currentData(),
            monochrome=self.mono_cb.isChecked(),
            lineweight_scale=self.lw_spin.value(),
            background=self.bg_combo.currentData(),
        )

    def _update_command(self) -> None:
        """Show the command line equivalent to the current settings."""
        if not hasattr(self, "command_view"):
            return
        spec = self._spec()
        roots = self._input_paths()
        parts = ["python dwg2pdf.py"]
        parts += ['"%s"' % r for r in (roots or ["INPUT"])]
        parts += ["-o", '"%s"' % (self.out_edit.text().strip() or "OUTPUT")]

        forced = self.backend_combo.currentData()
        if forced:
            parts += ["--backend", forced]
        else:
            parts += ["--strategy", self.strategy_combo.currentData()]

        if spec.layouts != "auto":
            parts += ["--layouts", spec.layouts]
        if spec.paper != "FIT":
            parts += ["--paper", spec.paper]
        if spec.units != "auto":
            parts += ["--units", spec.units]
        if spec.landscape:
            parts.append("--landscape")
        if spec.max_page_mm != 1189.0:
            parts += ["--max-page-mm", "%g" % spec.max_page_mm]
        if spec.margin_mm != 5.0:
            parts += ["--margin", "%g" % spec.margin_mm]
        if spec.scale:
            parts += ["--scale", "%g" % spec.scale]
        if not spec.monochrome:
            parts.append("--colour")
        if spec.lineweight_scale != 1.0:
            parts += ["--lineweight-scale", "%g" % spec.lineweight_scale]
        if spec.background != "white":
            parts += ["--background", spec.background]
        if spec.trim_outliers:
            parts.append("--trim-outliers")
        if spec.outlier_factor != 20.0:
            parts += ["--outlier-factor", "%g" % spec.outlier_factor]

        regex = self.filter_edit.text().strip()
        if regex:
            parts += ["--filter", '"%s"' % regex]
        elif self.preset_combo.currentData():
            parts += ["--preset", self.preset_combo.currentText()]
        if self.pattern_edit.text().strip():
            parts += ["--pattern", '"%s"' % self.pattern_edit.text().strip()]
        if self.limit_spin.value():
            parts += ["--limit", str(self.limit_spin.value())]
        if not self.recursive_cb.isChecked():
            parts.append("--no-recursive")
        if not self.dxf_cb.isChecked():
            parts.append("--no-dxf")
        if self.rb_flat.isChecked():
            parts.append("--flat")
        if self.skip_cb.isChecked():
            parts.append("--skip-existing")
        if not self.manifest_cb.isChecked():
            parts.append("--no-manifest")
        if self.merge_cb.isChecked():
            parts += ["--merge", '"merged.pdf"']
        if self.mem_cb.isChecked():
            parts.append("--report-memory")
        if self.recycle_spin.value():
            parts += ["--recycle-after", str(self.recycle_spin.value())]
        if self.timeout_spin.value() != 300:
            parts += ["--timeout", str(self.timeout_spin.value())]
        if self.accscript_edit.text().strip():
            parts += ["--accore-script",
                      '"%s"' % self.accscript_edit.text().strip()]
        if self.acclang_edit.text().strip():
            parts += ["--accore-lang", self.acclang_edit.text().strip()]

        n = resolve_worker_count(self.par_combo.currentData(),
                                 self.core_pct_spin.value(),
                                 self.jobs_spin.value())
        parts += ["--workers", str(n)]
        self.command_view.setPlainText(" ".join(parts))

    def _log(self, text: str) -> None:
        self.log_view.appendPlainText(text)

    # -- running --------------------------------------------------------
    def _validate(self) -> Optional[Dict[str, Any]]:
        """Check the settings and assemble the worker's option dict."""
        self.scan_inputs()
        if not self._sources:
            QtWidgets.QMessageBox.warning(
                self, "Nothing to convert",
                "No .dwg or .dxf files matched. Check the selected folders "
                "and the filters on the Files tab.")
            return None
        out_text = self.out_edit.text().strip()
        if not out_text:
            QtWidgets.QMessageBox.warning(
                self, "No output folder",
                "Choose where the PDFs should go, on the Files tab.")
            return None

        need_dwg = any(p.suffix.lower() == ".dwg" for p in self._sources)
        forced = self.backend_combo.currentData()
        try:
            chain = engine.select_backend_chain(
                forced, need_dwg,
                strategy=self.strategy_combo.currentData())
        except SystemExit as exc:
            QtWidgets.QMessageBox.critical(self, "No usable engine", str(exc))
            self._log(str(exc))
            return None

        # Apply the AutoCAD overrides to the backend class before the run.
        script_path = self.accscript_edit.text().strip()
        if script_path:
            try:
                engine.AcCoreConsoleBackend.script_override = Path(
                    script_path).read_text(encoding="utf-8")
            except OSError as exc:
                QtWidgets.QMessageBox.warning(
                    self, "Script template unreadable",
                    "Could not read %s:\n%s" % (script_path, exc))
                return None
        else:
            engine.AcCoreConsoleBackend.script_override = None
        engine.AcCoreConsoleBackend.language = (
            self.acclang_edit.text().strip() or None)

        out_root = Path(out_text).expanduser().resolve()
        archive = None
        if self.archive_cb.isChecked():
            archive = (self.archive_edit.text().strip()
                       or str(self._default_archive_path()))

        return {
            "sources": self._sources,
            "in_root": self._in_root(),
            "out_root": out_root,
            "chain": chain,
            "spec": self._spec(),
            "flat": self.rb_flat.isChecked(),
            "timeout": float(self.timeout_spin.value()),
            "skip_existing": self.skip_cb.isChecked(),
            "workers": resolve_worker_count(
                self.par_combo.currentData(),
                self.core_pct_spin.value(),
                self.jobs_spin.value()),
            "recycle_after": self.recycle_spin.value(),
            "write_manifest": self.manifest_cb.isChecked(),
            "merge_path": (str(out_root / "merged.pdf")
                           if self.merge_cb.isChecked() else None),
            "archive_path": archive,
            "archive_format": self.archive_fmt.currentData(),
        }

    def dry_run(self) -> None:
        """Show what would be produced, without converting anything."""
        opts = self._validate()
        if not opts:
            return
        self.table.setRowCount(0)
        self._log("=" * 66)
        self._log("DRY RUN - %d drawing(s), nothing will be written."
                  % len(opts["sources"]))
        self._log("Engine chain : %s"
                  % " -> ".join(c.name for c in opts["chain"]))
        self._log("Workers      : %d" % opts["workers"])
        self._log("Structure    : %s" % ("flattened" if opts["flat"]
                                         else "mirrors the source tree"))
        self._log("=" * 66)
        for src in opts["sources"][:500]:
            out_dir = engine.plan_output(
                src, opts["in_root"], opts["out_root"], opts["flat"])
            self._add_row({
                "source": str(src), "status": "dry-run", "entity_count": 0,
                "backend": opts["chain"][0].name,
                "message": str(out_dir / (src.stem + ".pdf")),
            })
        if len(opts["sources"]) > 500:
            self._log("... and %d more" % (len(opts["sources"]) - 500))
        self.statusBar().showMessage("Dry run complete - nothing was written")

    def start_run(self) -> None:
        """Kick off the conversion on a worker thread."""
        opts = self._validate()
        if not opts:
            return

        self.table.setRowCount(0)
        self.progress.setRange(0, len(opts["sources"]))
        self.progress.setValue(0)
        self._set_running(True)

        self._thread = QtCore.QThread(self)
        self._worker = ConversionWorker(opts)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.message.connect(self._log)
        self._worker.finished.connect(self.on_finished)
        self._thread.start()

    def _on_cancel_clicked(self) -> None:
        """Forward Cancel to whichever worker is currently running.

        The button is connected to this once, at construction, rather than to
        each new worker.  A stale connection to a finished worker is an easy
        bug to introduce, and PySide warns on disconnecting a signal that has
        no connections; one permanent connection avoids the whole class.
        """
        if self._worker is not None:
            self._worker.cancel()

    @Slot(int, int, dict)
    def on_progress(self, done: int, total: int, row: dict) -> None:
        self.progress.setValue(done)
        self._add_row(row)
        name = Path(row["source"]).name
        if row["status"] == "failed":
            self._log("[%d/%d] FAILED %s : %s"
                      % (done, total, name, row.get("message", "")))
        elif row["status"] == "retry-pending":
            self._log("[%d/%d] pass 1 could not convert %s - queued for the "
                      "serial retry with the full engine chain"
                      % (done, total, name))
        self.statusBar().showMessage("%d of %d - %s" % (done, total, name))

    @Slot(list, float, bool)
    def on_finished(self, rows: list, seconds: float, cancelled: bool) -> None:
        stats = engine.summarise(rows) if rows else {}
        summary = (
            "%d converted, %d skipped, %d failed -> %d PDF(s) in %.1f s"
            % (stats.get("ok", 0), stats.get("skipped", 0),
               stats.get("failed", 0), stats.get("pdfs", 0), seconds)
        )
        if cancelled:
            summary = "CANCELLED. " + summary
        self._log("-" * 60)
        self._log(summary)
        noise = engine.NOISE_FILTER.summary()
        if noise:
            self._log(noise)
        self.statusBar().showMessage(summary)
        self._set_running(False)
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
        self._worker = None

    def _set_running(self, running: bool) -> None:
        self.run_btn.setEnabled(not running)
        self.dry_btn.setEnabled(not running)
        self.cancel_btn.setEnabled(running)
        self.tabs.setEnabled(not running)

    def _add_row(self, row: dict) -> None:
        """Append one manifest row to the results table, colour-coded."""
        i = self.table.rowCount()
        self.table.insertRow(i)
        cells = [
            Path(row["source"]).name,
            row["status"],
            str(row.get("entity_count", "")),
            row.get("backend", ""),
            row.get("message", ""),
        ]
        colour = {
            "ok": QtGui.QColor(46, 140, 62),
            "failed": QtGui.QColor(190, 60, 60),
            "retry-pending": QtGui.QColor(190, 140, 40),   # amber, not red
            "skipped": QtGui.QColor(140, 140, 140),
        }.get(row["status"])
        for col, text in enumerate(cells):
            item = QtWidgets.QTableWidgetItem(text)
            if colour and col == 1:
                item.setForeground(colour)
            self.table.setItem(i, col, item)
        self.table.scrollToBottom()

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        """Stop a running conversion cleanly before the window goes away."""
        if self._thread is not None and self._thread.isRunning():
            ans = QtWidgets.QMessageBox.question(
                self, "Conversion running",
                "A conversion is still running. Stop it and quit?")
            if ans != QtWidgets.QMessageBox.Yes:
                event.ignore()
                return
            if self._worker is not None:
                self._worker.cancel()
            self._thread.quit()
            self._thread.wait(5000)
        if self._log_window is not None:
            self._log_window.close()
        event.accept()


# ============================================================================
# %% ENTRY POINT
# ============================================================================
def main(argv: Optional[List[str]] = None) -> int:
    """Build the application, show the window and run the event loop."""
    app = (QtWidgets.QApplication.instance()
           or QtWidgets.QApplication(argv if argv is not None else sys.argv))
    # Required before any process pool on Windows / frozen builds: without
    # it a spawned worker can re-enter main() and open another window.
    import multiprocessing
    multiprocessing.freeze_support()

    app.setApplicationName("dwg2pdf")
    # Fusion is not cosmetic: the native Windows style paints from the OS
    # theme and ignores the application palette, so the dark palette would
    # apply to almost nothing and the Dark menu item would appear dead.
    app.setStyle("Fusion")
    apply_theme(app, dark=False)

    # Install logging BEFORE the window is built: constructing it runs the
    # first backend probe, which imports ezdxf, which builds its font cache
    # and produces the only start-up noise this program has.
    handler = install_logging()
    win = MainWindow(log_handler=handler)
    win.show()

    summary = engine.NOISE_FILTER.summary()
    if summary:
        win.statusBar().showMessage("Ready  (%s - see the Detailed log)"
                                    % summary)
    return app.exec_() if hasattr(app, "exec_") else app.exec()


if __name__ == "__main__":
    sys.exit(main())
