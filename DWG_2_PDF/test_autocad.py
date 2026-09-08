#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Engine-side checks for the AutoCAD backends (dwg2pdf 0.3.15).

These run anywhere -- they exercise the parts of the AutoCAD path that are
pure Python: the generated ``.scr`` text, the COM busy-detection predicate,
and the Application liveness probe.  Actually plotting still needs Windows
and a licensed AutoCAD, but the three defects fixed in 0.3.15 all live in
logic that can be tested without one, which is the point of this file:

  * ``--monochrome`` was silently ignored by both AutoCAD backends;
  * one AutoCAD crash failed every remaining drawing in the run;
  * two unambiguous "busy" HRESULTs were treated as fatal.
"""
import sys

from pathlib import Path                      # noqa: E402

import dwg2pdf as engine                      # noqa: E402

RESULTS = {"pass": 0, "fail": 0}


def chk(label: str, cond: bool) -> None:
    """Record and print one assertion."""
    print(("  PASS  " if cond else "  FAIL  ") + label)
    RESULTS["pass" if cond else "fail"] += 1


class _ComError(Exception):
    """Stand-in for a pywin32 com_error, whose args[0] is the HRESULT."""

    def __init__(self, code: int, msg: str = "") -> None:
        super().__init__(code, msg)


def test_script_text() -> None:
    """The generated .scr must carry the plot style and quote its path."""
    target = Path("/tmp/x.pdf")
    mono = engine.AcCoreConsoleBackend._script_text(
        target, engine.PageSpec(paper="AUTO", monochrome=True))
    colour = engine.AcCoreConsoleBackend._script_text(
        target, engine.PageSpec(paper="AUTO", monochrome=False))

    chk("monochrome puts monochrome.ctb in the script",
        "monochrome.ctb" in mono)
    # StyleSheet without PlotWithPlotStyles is a no-op, which would look
    # exactly like the bug this fixes.
    chk("monochrome also sets PlotWithPlotStyles",
        "PlotWithPlotStyles" in mono)
    chk("--colour leaves the script clean", "monochrome.ctb" not in colour)
    chk("output path quoted in both (a space is Enter in a .scr)",
        mono.count('"%s"' % target) == 1
        and colour.count('"%s"' % target) == 1)

    lisp = [ln for ln in mono.splitlines() if ln.startswith("(")]
    chk("exactly one LISP line", len(lisp) == 1)
    chk("LISP expression is balanced",
        lisp[0].count("(") == lisp[0].count(")"))
    # Every other line must be space-free: outside a balanced expression or
    # a quoted string, a space in a script is Enter.
    loose = [ln for ln in mono.splitlines()
             if " " in ln and not ln.startswith(("(", '"'))]
    chk("no unquoted spaces on any other line", not loose)


def test_busy_detection() -> None:
    """Busy must be recognised by HRESULT as well as by message text."""
    backend = engine.AcadComBackend
    chk("RPC_E_CALL_REJECTED recognised by HRESULT",
        backend._is_busy(_ComError(-2147418111)))
    chk("RPC_E_SERVERCALL_RETRYLATER recognised by HRESULT",
        backend._is_busy(_ComError(-2147417846)))
    chk("'invalid execution context' still recognised by text",
        backend._is_busy(Exception("Invalid execution context")))
    # DISP_E_EXCEPTION is generic: raised for a broken drawing just as
    # readily as for a busy application, so the code alone must not count.
    chk("DISP_E_EXCEPTION alone is not 'busy'",
        not backend._is_busy(_ComError(-2147352567)))
    chk("a real error is not treated as busy",
        not backend._is_busy(_ComError(-2147352567, "drawing is corrupt")))


def test_liveness() -> None:
    """A dead Application must be detectable, or the whole run dies with it."""
    backend = engine.AcadComBackend
    original = backend._app
    try:
        backend._app = None
        chk("no cached application reads as not alive",
            not backend._app_is_alive())

        class Dead:
            @property
            def Documents(self):
                raise Exception("The RPC server is unavailable")

        backend._app = Dead()
        chk("a dead application is detected", not backend._app_is_alive())

        class Live:
            class Documents:
                Count = 0

        backend._app = Live()
        chk("a live application is detected", backend._app_is_alive())
    finally:
        backend._app = original

    chk("pc3 defaults to the stock plotter config",
        backend.PC3 == "DWG To PDF.pc3")
    chk("pc3 override is unset until --acad-pc3 is given",
        backend.pc3 is None)


def run_test() -> int:
    """Run every check and report."""
    print("AUTOCAD BACKEND CHECKS (engine %s)" % engine.__revision__)
    test_script_text()
    test_busy_detection()
    test_liveness()
    print("\n  %d passed, %d failed"
          % (RESULTS["pass"], RESULTS["fail"]))
    return 0 if RESULTS["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(run_test())
