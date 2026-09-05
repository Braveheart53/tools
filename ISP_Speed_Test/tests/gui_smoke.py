#!/usr/bin/env python3
"""GUI smoke test (version 1.1.0): runs a short simulated campaign inside the real MainWindow
(offscreen-capable) and saves a screenshot of every tab.

    QT_QPA_PLATFORM=offscreen python tests/gui_smoke.py ./gui_smoke_out

Revision history (newest first)
  1.1.0  2026-09-04  drives View ▸ Theme (dark / light / system), About and back-end check dialogs, lists menus
  1.0.1  2026-09-04  relative default output folder (no absolute paths)
  1.0.0  2026-09-04  initial
"""
__version__ = "1.1.0"
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("QT_API", "pyside6")

import isp_speed_monitor as m  # noqa: E402
from qtpy import QtCore, QtWidgets  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "./gui_smoke_out"
os.makedirs(out, exist_ok=True)

app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
win = m.MainWindow(app)
win.resize(1380, 900)
win.show()

cfg = m.selftest_config(out)
cfg.schedule.update({"mode": "interval", "interval_s": 4.0, "duration_s": 13.0})
win.apply_config(cfg)
win.cmb_backend.setCurrentIndex([win.cmb_backend.itemData(i) for i in range(win.cmb_backend.count())].index("simulated"))

state = {"shots": 0}


def shot(name):
    win.grab().save(os.path.join(out, f"{name}.png"))
    state["shots"] += 1


def step1():
    shot("01_setup")
    win.start_campaign()


def step2():
    win.tabs.setCurrentIndex(1)
    shot("02_live")
    win.tabs.setCurrentIndex(2)
    win.plot_panel.autoscale()
    shot("03_plots")
    win.tabs.setCurrentIndex(3)
    shot("04_data")


def step3():
    win.tabs.setCurrentIndex(2)
    win.plot_panel.autoscale()
    shot("05_plots_final")
    win.act_theme["dark"].trigger()
    for _ in range(5):
        app.processEvents()
    shot("06_plots_dark")
    win.tabs.setCurrentIndex(0)
    shot("07_setup_dark")
    win.act_theme["light"].trigger()
    for _ in range(5):
        app.processEvents()
    shot("08_setup_light")
    win.act_theme["system"].trigger()
    for _ in range(5):
        app.processEvents()
    shot("09_setup_system")
    # exercise the menu-only dialogs without blocking (auto-close the message boxes)
    QtCore.QTimer.singleShot(400, lambda: [w.accept() for w in app.topLevelWidgets() if isinstance(w, QtWidgets.QMessageBox)])
    win.show_about()
    QtCore.QTimer.singleShot(400, lambda: [w.accept() for w in app.topLevelWidgets() if isinstance(w, QtWidgets.QMessageBox)])
    win.check_backends()
    print("menus:", [m.title().replace("&", "") for m in win.menuBar().findChildren(QtWidgets.QMenu) if m.parent() is win.menuBar()])
    print("state:", win.ctrl.state, "rounds:", win.ctrl.round_seq, "shots:", state["shots"])
    win.close()
    QtCore.QTimer.singleShot(300, app.quit)


QtCore.QTimer.singleShot(1500, step1)
QtCore.QTimer.singleShot(9000, step2)
QtCore.QTimer.singleShot(17000, step3)
QtCore.QTimer.singleShot(40000, app.quit)  # hard stop
rc = app.exec()
print("files:", sorted(f for f in os.listdir(out) if f.endswith((".png", ".vszh5", ".json"))))
sys.exit(rc)
