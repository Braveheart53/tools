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
# %%% Author Information
# @author: William W. Wallace
# Author Email: naval.antennas@gmail.com
# Work Phone: (304) 456-2216

# %% Imports
import sys

from pathlib import Path                      # noqa: E402

import dwg2pdf as engine                      # noqa: E402

# %% State
RESULTS = {"pass": 0, "fail": 0}


# %% Helpers
def chk(label: str, cond: bool) -> None:
    """Record and print one assertion."""
    print(("  PASS  " if cond else "  FAIL  ") + label)
    RESULTS["pass" if cond else "fail"] += 1


# %% Fixtures
class _ComError(Exception):
    """Stand-in for a pywin32 com_error, whose args[0] is the HRESULT."""

    def __init__(self, code: int, msg: str = "") -> None:
        super().__init__(code, msg)


# %% Script generation
def test_script_text() -> None:
    """The generated .scr must drive -PLOT, quote every name, and set the style.

    ``-EXPORTPDF`` is an ``acad.exe`` command and does not exist in the core
    console; using it meant this backend never once succeeded.  These checks
    exist so it cannot come back by accident.
    """
    target = Path("/tmp/x.pdf")
    backend = engine.AcCoreConsoleBackend
    mono = backend._script_text(
        target, engine.PageSpec(paper="AUTO", monochrome=True))
    colour = backend._script_text(
        target, engine.PageSpec(paper="AUTO", monochrome=False))

    chk("the script drives -PLOT", "-PLOT" in mono)
    chk("-EXPORTPDF is gone (it is not a core command)",
        "-EXPORTPDF" not in mono)
    chk("no AutoLISP (vlax-get-acad-object is nil in the core console)",
        "vlax" not in mono and "vla-" not in mono)
    chk("monochrome answers the plot-style prompt with monochrome.ctb",
        '"monochrome.ctb"' in mono)
    chk("--colour answers that prompt with '.' (no style table)",
        "monochrome.ctb" not in colour and "\n.\n" in colour)
    chk("output path quoted in both (a space is Enter in a .scr)",
        mono.count('"%s"' % target) == 1
        and colour.count('"%s"' % target) == 1)
    # "DWG To PDF.pc3" unquoted would answer THREE prompts, not one --
    # exactly the defect of section 9.7, one prompt earlier.
    chk("the plotter name is quoted too",
        '"%s"' % backend.PC3 in mono)

    # Outside a quoted string, a space in a script is Enter.
    loose = [ln for ln in mono.splitlines()
             if " " in ln and not ln.startswith('"')]
    chk("no unquoted spaces anywhere in the script", not loose)

    landscape = backend._script_text(
        target, engine.PageSpec(paper="AUTO", landscape=True))
    portrait = backend._script_text(
        target, engine.PageSpec(paper="AUTO", landscape=False))
    chk("orientation follows --landscape", landscape != portrait)

    # The escape hatch must still produce the old command when asked.
    try:
        backend.command = "exportpdf"
        legacy = backend._script_text(target, engine.PageSpec(paper="AUTO"))
        chk("--accore-command exportpdf still generates -EXPORTPDF",
            "-EXPORTPDF" in legacy)
    finally:
        backend.command = "plot"


# %% COM busy detection
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


# %% Application liveness
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


# %% Console decoding
def test_console_decoding() -> None:
    """accoreconsole writes UTF-16LE; it must survive the trip to the log.

    subprocess(text=True) decodes it with the locale encoding, so every
    real character arrives followed by a NUL.  Collapsing whitespace then
    turned those NULs into spaces, which is how a real failure was reported
    first as "Console tail: d" and later as "Console: R".
    """
    real = (
        "Redirect stdout (file: C:\\ATEMP\\accc331682).\r\n"
        "AcCoreConsole: StdOutConsoleMode: processed-output: disabled,auto\r\n"
        "AutoCAD Core Engine Console - Copyright 2024 Autodesk, Inc.  "
        "All rights reserved. (V.116.0.0)\r\n"
        "Execution Path:  C:\\Program Files\\Autodesk\\AutoCAD 2025\r\n"
        "Current Directory: C:\\somewhere\r\n"
        "Version Number: V.116.0.0 (UNICODE)\r\n"
        "Command: -EXPORTPDF\r\n"
        'Unknown command "EXPORTPDF".  Press F1 for help.\r\n'
    )
    mangled = real.encode("utf-16-le").decode("latin-1")

    chk("UTF-16 console is re-decoded",
        "\x00" not in engine._decode_console(mangled))
    chk("clean ASCII is left alone",
        engine._decode_console("plain text") == "plain text")
    chk("round-trips an exact string",
        engine._decode_console(
            "FATAL ERROR: x".encode("utf-16-le").decode("latin-1")
        ) == "FATAL ERROR: x")

    excerpt = engine._console_excerpt(mangled)
    # The error is what the program said LAST; the banner is ~450 characters
    # of preamble, so truncating from the front showed only the banner.
    chk("the real error survives the excerpt",
        'Unknown command "EXPORTPDF"' in excerpt)
    chk("the start-up banner is dropped",
        "Copyright 2024 Autodesk" not in excerpt)
    chk("empty console reads as empty, not as ''",
        engine._console_excerpt("") == "(empty)")


# %% Shutdown
def test_shutdown() -> None:
    """AutoCAD must be quit -- but only one this process started."""
    backend = engine.AcadComBackend
    saved = (backend._app, backend._app_was_running)
    try:
        class App:
            quit_called = False
            class Documents:
                @staticmethod
                def Close(save): pass
            def Quit(self):
                type(self).quit_called = True

        # An application we started: quit it.
        app = App()
        backend._app, backend._app_was_running = app, False
        backend.shutdown()
        chk("quits an AutoCAD this run started", App.quit_called)
        chk("clears the cached application after shutdown",
            backend._app is None)

        # One the user already had open: leave it alone.
        App.quit_called = False
        backend._app, backend._app_was_running = App(), True
        backend.shutdown()
        chk("never quits a pre-existing AutoCAD session",
            not App.quit_called)

        # Idempotent, and safe with nothing cached.
        backend._app = None
        backend.shutdown()
        chk("shutdown with no application is a no-op", backend._app is None)

        # A Quit() that raises must not propagate out of interpreter exit.
        class Angry(App):
            def Quit(self): raise Exception("RPC server unavailable")
        backend._app, backend._app_was_running = Angry(), False
        try:
            backend.shutdown()
            chk("a raising Quit() is swallowed", True)
        except Exception:
            chk("a raising Quit() is swallowed", False)
    finally:
        backend._app, backend._app_was_running = saved


# %% Runner
def run_test() -> int:
    """Run every check and report."""
    print("AUTOCAD BACKEND CHECKS (engine %s)" % engine.__revision__)
    test_script_text()
    test_busy_detection()
    test_liveness()
    test_console_decoding()
    test_shutdown()
    print("\n  %d passed, %d failed"
          % (RESULTS["pass"], RESULTS["fail"]))
    return 0 if RESULTS["fail"] == 0 else 1


# %% Entry point
if __name__ == "__main__":
    sys.exit(run_test())
