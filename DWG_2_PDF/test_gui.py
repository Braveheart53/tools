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
import os
import sys
import time
import shutil

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path                     # noqa: E402
from qtpy import QtWidgets                   # noqa: E402

import dwg2pdf as engine                     # noqa: E402
import dwg2pdf_gui as gui                    # noqa: E402

RESULTS = {"pass": 0, "fail": 0}


def chk(label: str, cond: bool) -> None:
    """Record and print one assertion."""
    print(("  PASS  " if cond else "  FAIL  ") + label)
    RESULTS["pass" if cond else "fail"] += 1


def run_test() -> int:
    """Build the window, drive it, and verify a real conversion."""
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
    chk("all four strategies offered", len(strategies) == 4)

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
        "8 drawing(s)" in w.found_label.text())
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

    chk("parallel run converted 8 of 8", statuses.count("ok") == 8)
    chk("progress bar completed", w.progress.value() == 8)
    chk("8 PDFs on disk",
        len(list(Path("gui_out2").rglob("*.pdf"))) == 8)
    chk("manifest written", Path("gui_out2/manifest.csv").is_file())
    # Two input roots, so their common parent is the mirror root: the tree
    # becomes gui_out2/<folder name>/...  A single root would give
    # gui_out2/sub directly.  Assert the real shape, not a guess at it.
    chk("source structure mirrored under each root",
        Path("gui_out2/dwg_samples").is_dir()
        and Path("gui_out2/test_drawings/sub").is_dir())
    archive = Path("gui_archive_test.7z")
    chk("7z archive created",
        archive.is_file() and archive.stat().st_size > 1000)
    chk("worker thread cleaned up", w._thread is None)
    w.grab().save("gui2_results.png")

    print("\n  %d passed, %d failed" % (RESULTS["pass"], RESULTS["fail"]))
    return 0 if RESULTS["fail"] == 0 else 1


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()
    sys.exit(run_test())
