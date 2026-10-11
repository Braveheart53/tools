#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Headless functional test of dwg2pdf_gui 0.2.0 and the dwg2pdf engine.

Runs against an offscreen Qt platform, so it needs no display.  Everything
below is inside ``run_test`` and behind an ``if __name__`` guard: a process
pool on the 'spawn' start method re-imports the entry module in every worker,
and an unguarded test would run itself once per worker.  That is not
hypothetical -- it happened, and finding it is what prompted the explicit
multiprocessing context in the GUI and engine.
"""
# %%% Author Information
# @author: William W. Wallace
# Author Email: naval.antennas@gmail.com
# Work Phone: (304) 456-2216

# %% Imports
import os
import sys
import time
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path                     # noqa: E402
from qtpy import QtWidgets                   # noqa: E402

import dwg2pdf as engine                     # noqa: E402


# %% Fixture bootstrap
def _ensure_fixtures() -> None:
    """Generate the test fixtures if this is a clean unpack.

    The suites must pass straight out of the archive; requiring the
    operator to run a generator first is how a release ends up looking
    broken when it is merely un-bootstrapped.
    """
    try:
        import make_test_drawings
    except Exception as exc:                               # noqa: BLE001
        print("  NOTE  cannot bootstrap fixtures: %s" % exc)
        return
    try:
        make_test_drawings.ensure_fixtures()
    except Exception as exc:                               # noqa: BLE001
        print("  NOTE  fixture generation failed: %s" % exc)

import dwg2pdf_gui as gui                    # noqa: E402

# %% State
RESULTS = {"pass": 0, "fail": 0, "skip": 0}


# %% Helpers
def chk(label: str, cond: bool) -> None:
    """Record and print one assertion."""
    print(("  PASS  " if cond else "  FAIL  ") + label)
    RESULTS["pass" if cond else "fail"] += 1


def skip(label: str, why: str) -> None:
    """Record an assertion that could not be run HERE, and say why.

    A skip is counted and printed, never silent.  0.5.2 added this after
    ``test_no_syntax_warnings`` was found to ``continue`` past a module that
    was not on disk: it printed nothing, recorded nothing, and reported PASS
    for a file it had never compiled -- which is how the ``\\A`` invalid
    escape shipped in 0.5.1 with a green suite.  A test that cannot run must
    say so in the summary line, or it is indistinguishable from one that
    passed.
    """
    print("  SKIP  %s -- %s" % (label, why))
    RESULTS["skip"] += 1


def dwg_backend_available() -> bool:
    """Can this HOST decode DWG at all?

    The vendor tree ships Windows x86-64 LibreDWG binaries, so a Linux test
    host legitimately has no DWG decoder (0.5.2 stopped _find_tool handing
    back a .exe that cannot execute).  The conversion tests are then skipped
    rather than aborting the suite: everything that does not need a decoder
    is still worth checking.
    """
    try:
        for cls in engine.available_backends():
            if getattr(cls, "reads_dwg", False):
                return True
    except Exception:       # noqa: BLE001 - availability probing is best-effort
        pass
    return False


# %% Test body
# %% 0.4.x parity: every engine fix must be reachable from this window
def check_engine_fix_coverage() -> None:
    """The GUI must expose, or at least not defeat, every engine fix.

    Written because one was silently missing.  The GUI drives
    ``engine._convert_task()`` in its own loop and never calls
    ``engine.run_batch()`` -- so ``engine.check_decoder()``, the
    out-of-date LibreDWG warning, never fired in the GUI at all.  A GUI
    operator got no hint that pass 1 was running on a 2020 decoder,
    which is exactly the failure that cost a field run.

    The lesson generalises: anything ``run_batch()`` does for the CLI is
    a thing this window has to do for itself, so it gets a check.
    """
    import inspect
    import pickle

    src = inspect.getsource(gui)
    # Strip comment-only lines: this module's revision history quotes the
    # very calls some checks below assert are GONE, so grepping the whole
    # source would test the changelog rather than the code.
    code = "\n".join(ln for ln in src.splitlines()
                      if not ln.lstrip().startswith("#"))

    # 0.5.0 -- all four field-run fixes need a surface here.
    chk("--accore-mode is exposed (0.5.0)", "--accore-mode" in code)
    chk("prompt mode reaches the engine",
        "AcCoreConsoleBackend.mode" in code)
    chk("--acad-attach is exposed, and defaults OFF",
        "--acad-attach" in code and "setChecked(False)" in code)
    chk("attaching reaches the engine", "AcadComBackend.attach" in code)
    chk("--acad-recycle-after is exposed",
        "--acad-recycle-after" in code)
    chk("recycling reaches the engine",
        "AcadComBackend.recycle_after" in code)

    # 0.4.4 -- library log noise. The GUI's Detailed log tab had the same
    # flood the CLI did, and naming individual messages was not enough.
    chk("the Qt handler caps library loggers (0.4.4)",
        "_LibraryCapFilter" in src)
    chk("the Qt handler collapses repeats",
        "_DedupFilter" in src)
    chk("library detail can still be turned back on",
        "verbose_libs" in src)

    # 0.4.5 -- THE structural fix. The GUI must call run_batch(), not
    # reimplement it: that duplication is why check_decoder() (0.4.3)
    # never fired here, and it would have hidden the next fix too.
    chk("the GUI calls engine.run_batch() (0.4.5)",
        "engine.run_batch(" in src)
    chk("it passes a cancel hook rather than owning the loop",
        "should_cancel=lambda" in src)
    chk("it passes a progress callback", "progress=on_progress" in src)
    chk("the duplicated serial loop is gone",
        "def _run_serial" not in code)
    chk("the duplicated process pool is gone",
        "def _run_parallel" not in code)
    chk("the duplicated pass-2 retry is gone",
        "def _serial_retry" not in code)
    chk("nothing drives _convert_task directly any more",
        "engine._convert_task(" not in code)

    # 0.4.3 -- and so the decoder warning now arrives via run_batch(),
    # reaching the log pane through QtLogHandler on the root logger.
    # Calling it here as well would print the paragraph twice.
    chk("check_decoder() is not called a second time here",
        "engine.check_decoder()" not in code)

    # 0.4.2 -- --exclude, and the system-printer guard.
    chk("--exclude is exposed (0.4.2)", "--exclude" in src)
    chk("excludes reach discover_inputs",
        "exclude=self._excludes()" in src)
    chk("a system printer is caught in the .pc3 field",
        "_is_system_printer" in src)

    # 0.4.1 / 0.4.0 -- the .pc3 override must reach BOTH backends, and
    # the window mode and calibration switch must reach the engine.
    chk("the .pc3 override reaches accoreconsole (0.4.1)",
        "AcCoreConsoleBackend.pc3" in src)
    chk("the .pc3 override reaches acad-com",
        "AcadComBackend.pc3" in src)
    chk("--acad-window is exposed (0.4.0)", "window_mode" in src)
    chk("calibration can be switched off", "CALIBRATE" in src)

    # 0.4.0 -- all of it must survive the trip to a spawned worker, and
    # that is now run_batch's responsibility rather than this window's.
    # Asserted on the ENGINE, because the GUI no longer has a call site
    # to get wrong.
    import inspect as _inspect
    chk("run_batch takes the settings snapshot for both code paths",
        "settings = backend_settings()"
        in _inspect.getsource(engine.run_batch))
    chk("run_batch accepts the cancel hook the GUI relies on",
        "should_cancel" in _inspect.signature(engine.run_batch).parameters)
    keys = engine.BACKEND_SETTING_KEYS
    chk("the snapshot covers both AutoCAD backends",
        "accoreconsole" in keys and "acad-com" in keys)
    snap = engine.backend_settings()
    chk("the snapshot is picklable, as spawn requires",
        pickle.loads(pickle.dumps(snap)) == snap)


def check_log_noise_is_filtered() -> None:
    """The Qt handler must collapse the flood, not merely import filters.

    Reproduces what a real drawing does: ezdxf's recover pass emitting
    dozens of identical lines between two per-drawing progress lines.
    """
    import logging

    captured = []
    handler = gui.install_logging(logging.INFO)
    handler.bridge.line.connect(captured.append)
    # The handler buffers until a sink connects, so nothing logged during
    # start-up is lost; go_live() is what MainWindow calls.
    captured.extend(handler.go_live())
    try:
        ez = logging.getLogger("ezdxf")
        eng = logging.getLogger(engine._LOG.name)
        eng.info("[1/1762] a.dwg -> 1 page file(s)")
        for _ in range(53):
            ez.info("Found non-unique entity handle #A1, "
                    "data validation is required.")
        for _ in range(54):
            ez.info("Found ENDBLK without a preceding BLOCK, "
                    "ignoring content.")
        eng.info("[2/1762] b.dwg -> 1 page file(s)")
        ez.warning("a real ezdxf warning")
    finally:
        logging.getLogger().removeHandler(handler)

    text = "\n".join(captured)
    chk("107 library lines do not reach the log pane",
        "non-unique" not in text and "ENDBLK" not in text)
    chk("both progress lines still reach the log pane",
        text.count("/1762]") == 2)
    chk("a real library WARNING still reaches the log pane",
        "a real ezdxf warning" in text)
    chk("the log pane stays readable",
        len([ln for ln in captured if ln.strip()]) < 8)


# %% 0.5.2 parity gates
#: Engine flags that deliberately have no GUI control, with the reason.
#: An entry here is a DECISION, not a backlog item -- anything not listed
#: fails check_cli_gui_parity() and blocks the release.
CLI_ONLY_FLAGS = {
    "--version": "the window shows the revision in its title bar",
    "--probe": "the Engine tab has a live backend probe panel instead",
    "--dry-run": "the output preview pane is a continuous dry run",
}


def check_cli_gui_parity() -> None:
    """Every engine option must be reachable from the window.

    Enforced mechanically rather than by review.  Parity has been broken
    silently before -- an option added to argparse and not to the window is
    invisible to a GUI operator, and nothing fails -- so this reads both
    sources and compares them.  The exemption list above is the only escape,
    and it requires a stated reason.

    Deliberately a SOURCE comparison, not a runtime one: a control that is
    built but never consulted would still pass a runtime check, and the flag
    string appearing in the GUI is what proves the control is wired into the
    command the engine is actually given.
    """
    import re

    eng_src = Path("dwg2pdf.py").read_text(encoding="utf-8")
    gui_src = Path("dwg2pdf_gui.py").read_text(encoding="utf-8")
    flags = sorted(set(re.findall(
        r'add_argument\(\s*\n?\s*"(--[a-z0-9-]+)"', eng_src)))
    chk("engine exposes a plausible number of options", len(flags) >= 40)

    missing = [f for f in flags
               if f not in gui_src and f not in CLI_ONLY_FLAGS]
    for f in missing:
        print("     no GUI control for %s" % f)
    chk("every engine option is reachable from the GUI (%d checked)"
        % len(flags), not missing)

    stale = [f for f in CLI_ONLY_FLAGS if f not in flags]
    chk("no stale entries in CLI_ONLY_FLAGS", not stale)


def check_setting_keys_cover_gui() -> None:
    """Anything the GUI assigns to a backend must survive 'spawn'.

    On Windows the pool re-imports the engine in each worker, so a class
    attribute set by the window exists ONLY in the parent unless it is listed
    in engine.BACKEND_SETTING_KEYS and therefore travels in the
    backend_settings() snapshot.

    This is not hypothetical.  It is the 0.4.x defect: settings chosen in the
    window silently reverted to their defaults in every worker, so a whole run
    used a configuration nobody had selected, and nothing anywhere said so.
    Every attribute added since is a fresh opportunity to repeat it, which is
    why this is a gate and not a comment.
    """
    import re

    gui_src = Path("dwg2pdf_gui.py").read_text(encoding="utf-8")
    by_class = {cls.__name__: name
                for name, cls in engine.BACKENDS_BY_NAME.items()}

    assigned = re.findall(
        r"engine\.([A-Za-z_]+Backend)\.([A-Za-z_][A-Za-z0-9_]*)\s*=", gui_src)
    chk("the GUI assigns backend settings at all", len(assigned) >= 5)

    unregistered = []
    for class_name, attr in sorted(set(assigned)):
        backend = by_class.get(class_name)
        if backend is None:
            continue
        if attr not in engine.BACKEND_SETTING_KEYS.get(backend, ()):
            unregistered.append("%s.%s (backend %r)"
                                % (class_name, attr, backend))
    for u in unregistered:
        print("     not in BACKEND_SETTING_KEYS: %s" % u)
    chk("every GUI-set backend attribute survives spawn (%d checked)"
        % len(set(assigned)), not unregistered)


def check_new_controls_present() -> None:
    """The 0.5.2 controls exist and are wired to the command the engine gets."""
    gui_src = Path("dwg2pdf_gui.py").read_text(encoding="utf-8")
    for widget, flag in (
        ("device_edit", "--acad-device"),
        ("probe_spin", "--acad-probe-timeout"),
        ("oda_edit", "--oda-exe"),
        ("acccmd_edit", "--accore-command"),
        ("imgdpi_spin", "--image-max-dpi"),
        ("imglossless_cb", "--image-lossless"),
        ("verboselibs_cb", "--verbose-libs"),
        ("logfile_edit", "--log-file"),
    ):
        chk("%s exists and emits %s" % (widget, flag),
            ("self.%s = " % widget) in gui_src and flag in gui_src)



def run_test() -> int:
    """Build the window, drive it, and verify a real conversion."""
    _ensure_fixtures()
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    gui.apply_theme(app, dark=False)
    w = gui.MainWindow()
    w.resize(1200, 900)
    w.show()
    app.processEvents()

    print("GUI FUNCTIONAL TEST")
    chk("window builds", w.isVisible())
    chk("five settings tabs", w.tabs.count() == 5)
    chk("tab names as designed",
        [w.tabs.tabText(i) for i in range(5)] ==
        ["Files && Output", "Engine", "Page Setup", "Performance", "Finish"])

    # -- parallelism resolution --------------------------------------
    chk("cores mode resolves", gui.resolve_worker_count("cores", 75, 4) >= 1)
    chk("jobs mode honours the number",
        gui.resolve_worker_count("jobs", 75, 3) == 3)
    chk("serial mode is one worker",
        gui.resolve_worker_count("serial", 75, 8) == 1)
    chk("worker cap enforced",
        gui.resolve_worker_count("jobs", 100, 999) == gui.WORKER_CAP)

    # -- TrueView must be gone ---------------------------------------
    combo = [w.backend_combo.itemData(i)
             for i in range(w.backend_combo.count())]
    chk("TrueView not selectable", "trueview" not in combo)
    chk("probe marks TrueView disabled",
        "DISABLED" in w.backend_view.toPlainText())
    strategies = [w.strategy_combo.itemData(i)
                  for i in range(w.strategy_combo.count())]
    chk("AutoCAD-only strategy offered", "autocad-only" in strategies)
    chk("no-AutoCAD strategy offered", "no-autocad" in strategies)
    chk("all five strategies offered", len(strategies) == 5)

    # -- page setup ---------------------------------------------------
    papers = [w.paper_combo.itemData(i)
              for i in range(w.paper_combo.count())]
    chk("AUTO paper detection is the default", papers[0] == "AUTO")
    chk("FIT still offered", "FIT" in papers)
    layouts = [w.layouts_combo.itemData(i)
               for i in range(w.layouts_combo.count())]
    chk("layouts AUTO is the default", layouts[0] == "auto")
    chk("all four layout modes offered", len(layouts) == 4)
    chk("AutoCAD script override field present",
        hasattr(w, "accscript_edit"))
    chk("AutoCAD language field present", hasattr(w, "acclang_edit"))
    chk("AutoCAD plotter (.pc3) field present", hasattr(w, "pc3_edit"))
    unit_vals = [w.units_combo.itemData(i)
                 for i in range(w.units_combo.count())]
    chk("drawing-units control present, auto by default",
        unit_vals[0] == "auto" and "inch" in unit_vals)

    # -- multi-directory input + structure preview --------------------
    w._append_input(str(Path("dwg_samples").resolve()))
    w._append_input(str(Path("test_drawings").resolve()))
    w.out_edit.setText(str(Path("gui_out2").resolve()))
    w.scan_inputs()
    app.processEvents()
    print("  found:", w.found_label.text())
    chk("two folders scanned into 8 drawings",
        "8 file(s)" in w.found_label.text())
    chk("image checkbox present and off by default",
        hasattr(w, "images_cb") and not w.images_cb.isChecked())
    chk("no image count shown while images are off",
        "image(s)" not in w.found_label.text())
    chk("input list shows both folders", w.in_list.count() == 2)
    chk("output preview populated", "->" in w.preview_view.toPlainText())

    mirrored = w.preview_view.toPlainText()
    w.rb_flat.setChecked(True)
    app.processEvents()
    chk("flatten changes the preview",
        w.preview_view.toPlainText() != mirrored)
    w.rb_mirror.setChecked(True)
    app.processEvents()

    # -- detachable log ----------------------------------------------
    w.open_log_window()
    app.processEvents()
    chk("log opens in its own window",
        w._log_window is not None and w._log_window.isVisible())
    w._log("shared-buffer probe line")
    app.processEvents()
    chk("detached log shares the buffer",
        "shared-buffer probe line" in w._log_window.view.toPlainText())

    # -- equivalent command ------------------------------------------
    w.trim_cb.setChecked(True)
    w.paper_combo.setCurrentIndex(0)
    app.processEvents()
    cmd = w.command_view.toPlainText()
    chk("command shows --trim-outliers", "--trim-outliers" in cmd)
    chk("command shows --paper AUTO", "--paper AUTO" in cmd)
    chk("layouts auto is implicit (not in the command)",
        "--layouts" not in cmd)
    chk("command shows --workers", "--workers" in cmd)
    chk("command lists both input folders",
        cmd.count("dwg_samples") == 1 and cmd.count("test_drawings") == 1)

    # -- archive naming -----------------------------------------------
    # -- merge bookmarks ----------------------------------------------
    bm = [w.bookmark_combo.itemData(i)
          for i in range(w.bookmark_combo.count())]
    chk("bookmark modes offered, tree by default",
        bm == ["tree", "flat", "none"])
    chk("bookmark control disabled until merging is on",
        not w.bookmark_combo.isEnabled())
    w.merge_cb.setChecked(True)
    app.processEvents()
    chk("bookmark control enabled with merging on",
        w.bookmark_combo.isEnabled())
    chk("tree is the engine default, so not in the command",
        "--merge-bookmarks" not in w.command_view.toPlainText())
    w.bookmark_combo.setCurrentIndex(1)          # flat
    app.processEvents()
    chk("a non-default bookmark mode reaches the command",
        "--merge-bookmarks flat" in w.command_view.toPlainText())
    w.merge_cb.setChecked(False)
    app.processEvents()

    chk("archive name carries both revisions",
        ("v" + engine.__revision__) in w.archive_edit.text()
        and ("gui" + gui.__revision__) in w.archive_edit.text())
    chk("archive defaults to 7z", w.archive_edit.text().endswith(".7z"))

    w.grab().save("gui2_light.png")
    w.set_theme(True)
    app.processEvents()
    w.grab().save("gui2_dark.png")
    w.set_theme(False)
    app.processEvents()

    # -- a real parallel conversion, then packaging -------------------
    shutil.rmtree("gui_out2", ignore_errors=True)
    for stale in Path(".").glob("gui_archive_test.*"):
        stale.unlink()
    w.par_combo.setCurrentIndex(1)       # fixed job count
    w.jobs_spin.setValue(3)
    w.skip_cb.setChecked(False)
    w.archive_cb.setChecked(True)
    w.archive_edit.setText(str(Path("gui_archive_test.7z").resolve()))
    app.processEvents()

    w.start_run()
    deadline = time.time() + 300
    while w._thread is not None and time.time() < deadline:
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()

    statuses = [w.table.item(r, 1).text() for r in range(w.table.rowCount())]
    print("  statuses:", statuses)
    if "failed" in statuses:
        for r in range(w.table.rowCount()):
            if w.table.item(r, 1).text() == "failed":
                print("     failure:", w.table.item(r, 0).text(),
                      "->", w.table.item(r, 4).text()[:160])

    # The 5 DWG fixtures need a DWG decoder; the 3 generated DXF ones do not.
    # On a host with no decoder the DWG rows legitimately fail, so assert what
    # this host can actually prove and SKIP the rest, loudly.
    if dwg_backend_available():
        chk("parallel run converted 8 of 8", statuses.count("ok") == 8)
        chk("progress bar completed", w.progress.value() == 8)
        chk("8 PDFs on disk",
            len(list(Path("gui_out2").rglob("*.pdf"))) == 8)
    else:
        why = "no DWG decoder on this host (vendor/ ships win64 binaries)"
        chk("every DXF fixture converted", statuses.count("ok") >= 3)
        chk("progress bar completed", w.progress.value() == 8)
        skip("parallel run converted 8 of 8", why)
        skip("8 PDFs on disk", why)
    chk("manifest written", Path("gui_out2/manifest.csv").is_file())
    # Two input roots, so their common parent is the mirror root: the tree
    # becomes gui_out2/<folder name>/...  A single root would give
    # gui_out2/sub directly.  Assert the real shape, not a guess at it.
    if dwg_backend_available():
        chk("source structure mirrored under each root",
            Path("gui_out2/dwg_samples").is_dir()
            and Path("gui_out2/test_drawings/sub").is_dir())
    else:
        # Nothing under dwg_samples converted, so no mirror directory is
        # created for it.  The DXF half still proves the mirroring logic.
        chk("source structure mirrored under each root",
            Path("gui_out2/test_drawings/sub").is_dir())
    archive = Path("gui_archive_test.7z")
    chk("7z archive created",
        archive.is_file() and archive.stat().st_size > 1000)
    chk("worker thread cleaned up", w._thread is None)
    check_engine_fix_coverage()
    check_cli_gui_parity()
    check_setting_keys_cover_gui()
    check_new_controls_present()
    check_log_noise_is_filtered()
    w.grab().save("gui2_results.png")

    print("\n  %d passed, %d failed, %d skipped"
          % (RESULTS["pass"], RESULTS["fail"], RESULTS["skip"]))
    return 0 if RESULTS["fail"] == 0 else 1


# %% Entry point
if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    # os._exit, not sys.exit: PySide6 running offscreen segfaults in its own
    # teardown AFTER run_test() has printed its summary, which turns a green
    # suite into exit 139 and makes the exit code useless for gating a
    # release.  The verdict is already computed; leave before Qt unwinds.
    _code = run_test()
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_code)
