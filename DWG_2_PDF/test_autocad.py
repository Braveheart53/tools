#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Engine-side checks for the AutoCAD backends (dwg2pdf 0.5.0).

These run anywhere -- they exercise the parts of the AutoCAD path that are
pure Python: the generated ``.scr`` text, the plot-device calibration, the
console fault detection, the COM busy/context predicates, the window-state
escalation, and the Application liveness probe.  Actually plotting still
needs Windows and a licensed AutoCAD, but every defect fixed here lives in
logic that can be tested without one, which is the point of this file.

Fixed in 0.3.15:

  * ``--monochrome`` was silently ignored by both AutoCAD backends;
  * one AutoCAD crash failed every remaining drawing in the run;
  * two unambiguous "busy" HRESULTs were treated as fatal.

Fixed in 0.4.2, after driving accoreconsole directly on the failing
machine confirmed the 0.4.1 diagnosis:

  * a rejected device does not always print "not found" -- the only
    signal can be the device prompt being asked twice;
  * ``?`` at the device prompt lists nothing in the core console, so the
    probe must not be the FIRST candidate and cost a whole timeout;
  * ``--timeout`` was applied per calibration ATTEMPT, not per drawing,
    so eleven candidates meant eleven times the budget, silently;
  * Windows system printers (Adobe PDF, Microsoft Print to PDF) take
    their output path from a modal save dialog and cannot be used
    headlessly at all.

Fixed in 0.4.1:

  * the plotter was never missing -- our own QUOTING was inside the device
    name AutoCAD searched for (``<"DWG To PDF.pc3"> not found.``), so the
    quoting is now a calibration variant rather than an assumption.

Fixed in 0.4.0, from a 1876-drawing run in which all three engines failed:

  * accoreconsole answered the device prompt with a name the core console
    could not resolve, which desynchronised the whole blind ``-PLOT``
    answer sequence and exited **0 with no PDF**;
  * ``acad-com`` was refused with ``Invalid execution context`` on every
    single drawing because its window was hidden;
  * per-run backend settings never reached the worker processes at all.
"""
# %%% Author Information
# @author: William W. Wallace
# Author Email: naval.antennas@gmail.com
# Work Phone: (304) 456-2216

# %% Imports
import os
import sys

from pathlib import Path                      # noqa: E402

import dwg2pdf as engine                      # noqa: E402


# %% Fixture bootstrap
def _ensure_fixtures() -> None:
    """Generate the test fixtures if this is a clean unpack.

    This file needed none until 0.4.5 added test_cancel_hook(), which
    converts real drawings to prove run_batch() can be stopped.  Without
    this the suite died on a clean unpack with ZeroDivisionError -- an
    empty fixture list and a modulo -- which is a worse failure than the
    one it was testing for.
    """
    try:
        import make_test_drawings
        make_test_drawings.ensure_fixtures()
    except Exception as exc:                               # noqa: BLE001
        print("  NOTE  cannot bootstrap fixtures: %s" % exc)


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
    # 0.4.1 REVERSED this.  Quoting the plotter name looked right -- a
    # space in a script is Enter -- but the console's own rejection,
    # <"DWG To PDF.pc3"> not found, shows the quotes went INTO the name
    # it searched for.  The bare name is now the uncalibrated default.
    chk("the plotter name is NOT quoted by default (0.4.1)",
        ('"%s"' % backend.PC3) not in mono and backend.PC3 in mono)

    # The output PATH is a different prompt and stays quoted: nothing has
    # shown it behaves like the device prompt, and it is under our control.
    loose = [ln for ln in mono.splitlines()
             if " " in ln and not ln.startswith('"')
             and ln != backend.PC3]
    chk("the only unquoted spaces are the plotter name", not loose)

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


# %% Console fault detection
#: The transcript that cost 850 drawings, reproduced verbatim.
DESYNC = (
    "Command: -PLOT Detailed plot configuration? [Yes/No] <No>: Y\r\n"
    "Enter a layout name or [?] <Model>:\r\n"
    'Enter an output device name or [?] <Adobe PDF>: "DWG To PDF.pc3"\r\n'
    '<"DWG To PDF.pc3"> not found.\r\n'
    "Enter an output device name or [?] <Adobe PDF>:\r\n"
    "Enter paper size or [?] <Letter>: L\r\n"
    'Command: N Unknown command "N".  Press F1 for help.\r\n'
)

CLEAN = (
    "Command: -PLOT Detailed plot configuration? [Yes/No] <No>: Y\r\n"
    "Enter a layout name or [?] <Model>:\r\n"
    'Enter an output device name or [?] <None>: "DWG To PDF.pc3"\r\n'
    "Enter paper size or [?] <ANSI expand D (34.00 x 22.00 Inches)>:\r\n"
    "Effective plotting area:  863.60 wide by 558.80 high\r\n"
    "Plotting viewport 1.\r\n"
)


def test_faults() -> None:
    """A console that says the plot failed must not be read as success.

    accoreconsole exits 0 whether it plotted or not, so the transcript is
    the only witness.  Nothing read it before 0.4.0.
    """
    backend = engine.AcCoreConsoleBackend
    faults = backend._faults(DESYNC)
    joined = " ".join(faults).lower()
    chk("the rejected plot device is detected", "not found" in joined)
    chk("the spilled answer is detected", "unknown command" in joined)
    chk("a clean plot reports no faults", not backend._faults(CLEAN))
    chk("an empty console reports no faults", not backend._faults(""))
    chk("faults are de-duplicated",
        len(backend._faults(DESYNC + DESYNC)) == len(faults))


# %% Plot-device calibration
def test_device_candidates() -> None:
    """Candidates must be quoted, ordered, and unique."""
    backend = engine.AcCoreConsoleBackend
    saved = (backend.pc3, backend._device_list)
    try:
        # An explicit --acad-pc3 is used ALONE: second-guessing an operator
        # who named a device hides their mistake behind a lucky fallback.
        # ...but its QUOTING is ours, not theirs, and 0.4.1 learned that
        # our quoting was the defect: the console reported
        # <"DWG To PDF.pc3"> not found, quotes inside the brackets.
        backend.pc3 = "NRAO PDF.pc3"
        backend._device_list = ["DWG To PDF.pc3"]
        only = backend._device_candidates(Path("x"), Path("y"), 1.0)
        chk("--acad-pc3 offers only that name",
            all("NRAO PDF.pc3" in c for c in only))
        chk("--acad-pc3 is tried both bare and quoted",
            set(only) == {"NRAO PDF.pc3", '"NRAO PDF.pc3"'})
        chk("the bare form leads, since the quotes were what failed",
            only[0] == "NRAO PDF.pc3")

        backend.pc3 = None
        backend._device_list = ["Default Windows System Printer.pc3",
                                "AutoCAD PDF (General Documentation).pc3",
                                "DWG To PDF.pc3"]
        cands = backend._device_candidates(Path("x"), Path("y"), 1.0)
        chk("the stock DWG To PDF device is tried first",
            cands[0] == "DWG To PDF.pc3")
        chk("its quoted form is still offered, second",
            cands[1] == '"DWG To PDF.pc3"')
        chk("another PDF device is kept as a fallback",
            "AutoCAD PDF (General Documentation).pc3" in cands)
        chk("a non-PDF device is not offered",
            not any("System Printer" in c for c in cands))
        chk("candidates are unique", len(cands) == len(set(cands)))
        chk("both quotings of every device are present",
            all(('"%s"' % c) in cands
                for c in cands if not c.startswith('"')))
    finally:
        backend.pc3, backend._device_list = saved


def test_answer_forms() -> None:
    """Quoting variants, and the inference that picked their order."""
    backend = engine.AcCoreConsoleBackend

    spaced = backend._answer_forms("DWG To PDF.pc3")
    # The rejection <"DWG To PDF.pc3"> not found proves the whole quoted
    # string arrived as ONE value: had a space been Enter at this prompt,
    # the brackets would have held `"DWG` instead.  So the prompt reads to
    # end of line and the quotes were contamination, not protection.
    chk("a spaced name leads with the bare form",
        spaced[0] == "DWG To PDF.pc3")
    chk("a spaced name still offers the quoted form",
        spaced == ["DWG To PDF.pc3", '"DWG To PDF.pc3"'])

    plain = backend._answer_forms("MyPlot.pc3")
    chk("a name without spaces leads bare too", plain[0] == "MyPlot.pc3")
    chk("quoting a space-free name could only hurt, so it trails",
        plain == ["MyPlot.pc3", '"MyPlot.pc3"'])

    chk("forms are unique",
        len(spaced) == len(set(spaced)) and len(plain) == len(set(plain)))

    # _short_path is Windows-only by construction; off Windows it must
    # decline rather than raise, so the candidate list stays usable in
    # this very test run.
    chk("the 8.3 short form is skipped off Windows",
        backend._short_path(Path("/tmp/x y.pc3")) is None
        or os.name == "nt")

    path = r"C:\Users\w\AppData\Roaming\Autodesk\Plotters\DWG To PDF.pc3"
    forms = backend._answer_forms(path, is_path=True)
    chk("a full path is offered bare and quoted",
        path in forms and ('"%s"' % path) in forms)


def test_device_probe() -> None:
    """The ``?`` listing must be parsed out of a core-console transcript."""
    backend = engine.AcCoreConsoleBackend
    saved = backend._device_list
    listing = (
        "Command: -PLOT Detailed plot configuration? [Yes/No] <No>: Y\r\n"
        "Enter a layout name or [?] <Model>:\r\n"
        "Enter an output device name or [?] <None>: ?\r\n"
        "Available devices:\r\n"
        "    None\r\n"
        "    Default Windows System Printer.pc3\r\n"
        "    DWG To PDF.pc3\r\n"
        "    AutoCAD PDF (High Quality Print).pc3\r\n"
        "    Adobe PDF\r\n"
        "Enter an output device name or [?] <None>:\r\n"
    )
    try:
        backend._device_list = None
        backend._run_console = classmethod(          # type: ignore[method-assign]
            lambda cls, exe, src, script, timeout: (0, listing))
        names = backend._probe_devices(Path("acc.exe"), Path("a.dwg"), 1.0)
        chk("the stock device is found in the listing",
            "DWG To PDF.pc3" in names)
        chk("a parenthesised device name survives",
            "AutoCAD PDF (High Quality Print).pc3" in names)
        chk("a bare system printer is not collected",
            "Adobe PDF" not in names)
        chk("the listing is cached",
            backend._probe_devices(Path("acc.exe"), Path("a.dwg"), 1.0)
            is names)
    finally:
        del backend._run_console
        backend._device_list = saved


def test_calibration() -> None:
    """Calibration must find the working device and then stop looking."""
    import tempfile

    backend = engine.AcCoreConsoleBackend
    saved = (backend._device, backend._device_list,
             backend._calibration_error, backend._calibration_failures)
    tried: list = []
    try:
        backend._device = None
        backend._device_list = ["DWG To PDF.pc3", "AutoCAD PDF (X).pc3"]
        backend._calibration_error = None
        backend._calibration_failures = 0

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sheet.pdf"

            def fake_attempt(self, exe, source, tgt, spec, device=None):
                """Succeed only on the SECOND candidate."""
                tried.append(device)
                if len(tried) == 2:
                    tgt.write_bytes(b"%PDF-1.4\n" + b"x" * 2048)
                return DESYNC if len(tried) != 2 else CLEAN

            backend._attempt = fake_attempt      # type: ignore[assignment]
            inst = backend(timeout=5.0)
            outputs, _ = inst._calibrate(
                Path("acc.exe"), Path("sheet.dwg"), target,
                engine.PageSpec(paper="AUTO"))

            chk("calibration converts the drawing it calibrates on",
                outputs == [target] and target.is_file())
            chk("it stopped at the candidate that worked", len(tried) == 2)
            chk("the winner is cached for the rest of the run",
                backend._device == tried[1])
            # The cached answer must be what later drawings actually use.
            script = backend._script_text(target,
                                          engine.PageSpec(paper="AUTO"))
            chk("later sheets use the calibrated device",
                tried[1] in script)
    finally:
        del backend._attempt
        (backend._device, backend._device_list,
         backend._calibration_error, backend._calibration_failures) = saved


def test_calibration_gives_up() -> None:
    """Failing every candidate on N drawings must stop the run, not repeat it.

    The 0.3.18 run spent 3.1 hours relaunching AutoCAD for 850 drawings
    that were all failing for the same reason.
    """
    import tempfile

    backend = engine.AcCoreConsoleBackend
    saved = (backend._device, backend._device_list,
             backend._calibration_error, backend._calibration_failures)
    try:
        backend._device = None
        backend._device_list = ["DWG To PDF.pc3"]
        backend._calibration_error = None
        backend._calibration_failures = 0
        backend._attempt = (                     # type: ignore[assignment]
            lambda self, exe, source, tgt, spec, device=None: DESYNC)

        inst = backend(timeout=5.0)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sheet.pdf"
            messages = []
            for _ in range(backend.CALIBRATION_GIVE_UP_AFTER):
                try:
                    inst._calibrate(Path("acc.exe"), Path("s.dwg"), target,
                                    engine.PageSpec(paper="AUTO"))
                except RuntimeError as exc:
                    messages.append(str(exc))

            chk("every failed calibration is reported",
                len(messages) == backend.CALIBRATION_GIVE_UP_AFTER)
            chk("the message names the console fault, not the drawing",
                "not found" in messages[0].lower())
            chk("the message lists what the console could see",
                "DWG To PDF.pc3" in messages[0])
            chk("the message says how to fix it",
                "--acad-pc3" in messages[0])
            chk("the backend gives up rather than retrying for hours",
                backend._calibration_error is not None)
    finally:
        del backend._attempt
        (backend._device, backend._device_list,
         backend._calibration_error, backend._calibration_failures) = saved


# %% Execution-context recovery
def test_context_recovery() -> None:
    """A hidden AutoCAD that refuses automation must be shown, not retried."""
    backend = engine.AcadComBackend
    chk("'Invalid execution context' is recognised",
        backend._is_context_error(_ComError(-2147352567,
                                            "Invalid execution context")))
    chk("an unrelated COM error is not",
        not backend._is_context_error(_ComError(-2147352567,
                                                "drawing is corrupt")))

    saved = (backend._app, backend.window_mode, backend._visible_escalated)
    try:
        class App:
            Visible = False
            WindowState = 1

            @staticmethod
            def GetAcadState():
                class State:
                    IsQuiescent = True
                return State()

        app = App()
        backend._app = app
        backend.window_mode = "auto"
        backend._visible_escalated = False

        chk("escalation reports that it changed something",
            backend._escalate_visibility())
        chk("the window is made visible", app.Visible is True)
        chk("the window is minimised, not thrown in the operator's face",
            app.WindowState == 2)
        chk("escalation happens once per run, not once per drawing",
            not backend._escalate_visibility())

        # --acad-window hidden is an instruction, not a suggestion.
        backend._visible_escalated = False
        backend.window_mode = "hidden"
        app.Visible = False
        chk("--acad-window hidden is never overridden",
            not backend._escalate_visibility() and app.Visible is False)
    finally:
        (backend._app, backend.window_mode,
         backend._visible_escalated) = saved


def test_window_mode() -> None:
    """_set_window must follow the requested mode."""
    backend = engine.AcadComBackend
    saved = (backend.window_mode, backend._visible_escalated)

    class App:
        Visible = None
        WindowState = 1

    try:
        backend._visible_escalated = False
        for mode, expect in (("hidden", False), ("auto", False),
                             ("visible", True)):
            app = App()
            backend.window_mode = mode
            backend._set_window(app)
            chk("--acad-window %s -> Visible=%s" % (mode, expect),
                app.Visible is expect)

        # After escalation, 'auto' must come up visible on a restart --
        # otherwise the restarted application repeats the failure.
        app = App()
        backend.window_mode = "auto"
        backend._visible_escalated = True
        backend._set_window(app)
        chk("a restart after escalation comes up visible",
            app.Visible is True)
    finally:
        backend.window_mode, backend._visible_escalated = saved


# %% Viewer immunity
def test_move_into_place() -> None:
    """The PDF viewer must not be able to break the run.

    AutoCAD's PDF driver may hand each finished PDF to the default viewer;
    that is a custom property of the .pc3 and no system variable turns it
    off.  So the plot lands in a scratch folder and the deliverable is a
    rename -- and the rename is retried, because it is the one step a
    viewer holding the OLD file open can block.
    """
    import tempfile

    backend = engine.AcadComBackend
    with tempfile.TemporaryDirectory() as tmp:
        plotted = Path(tmp) / "scratch.pdf"
        target = Path(tmp) / "sheet.pdf"
        plotted.write_bytes(b"%PDF-1.4\n" + b"x" * 2048)
        backend._move_into_place(plotted, target)
        chk("the plotted file becomes the deliverable",
            target.is_file() and not plotted.exists())

        # Simulate a viewer holding the destination open.
        plotted.write_bytes(b"%PDF-1.4\n" + b"y" * 2048)
        real_replace = engine.os.replace
        engine.os.replace = lambda *a, **k: (_ for _ in ()).throw(
            OSError(13, "used by another process"))
        try:
            backend._move_into_place(plotted, target)
            chk("a locked destination raises", False)
        except RuntimeError as exc:
            message = str(exc).lower()
            chk("a locked destination raises", True)
            chk("the error blames the viewer, not the drawing",
                "viewer" in message)
            chk("the error names the escape hatch",
                "--acad-pc3" in message)
        finally:
            engine.os.replace = real_replace


# %% Settings across the process boundary
def test_settings_propagation() -> None:
    """CLI backend settings must survive 'spawn' into a worker.

    Before 0.4.0 these were class attributes assigned in ``main``, so a
    spawned worker -- which re-imports the module and never runs ``main``
    -- silently used the defaults.  Every AutoCAD flag was ignored for the
    whole of pass 1.
    """
    accore = engine.AcCoreConsoleBackend
    com = engine.AcadComBackend
    saved = (accore.pc3, accore.CALIBRATE, com.pc3, com.window_mode)
    try:
        accore.pc3 = "NRAO PDF.pc3"
        accore.CALIBRATE = False
        com.pc3 = "NRAO PDF.pc3"
        com.window_mode = "visible"
        snapshot = engine.backend_settings()

        # What a fresh worker looks like.
        accore.pc3, accore.CALIBRATE = None, True
        com.pc3, com.window_mode = None, "auto"
        engine.apply_backend_settings(snapshot)

        chk("--acad-pc3 reaches the worker (accoreconsole)",
            accore.pc3 == "NRAO PDF.pc3")
        chk("--no-accore-calibrate reaches the worker",
            accore.CALIBRATE is False)
        chk("--acad-pc3 reaches the worker (acad-com)",
            com.pc3 == "NRAO PDF.pc3")
        chk("--acad-window reaches the worker",
            com.window_mode == "visible")

        chk("no settings is a no-op, not a crash",
            engine.apply_backend_settings(None) is None)
        engine.apply_backend_settings({"acad-com": {"timeout": 1},
                                       "no-such-backend": {"x": 1}})
        chk("an unknown attribute is ignored, not set",
            not hasattr(com, "timeout") or com.timeout != 1)
    finally:
        (accore.pc3, accore.CALIBRATE, com.pc3, com.window_mode) = saved




# %% 0.4.2: what the direct accoreconsole probe taught
def test_prompt_repeat_fault() -> None:
    """A repeated device prompt is the desync, even with no error text.

    This is the transcript that confirmed 0.4.1 on the real machine.  Note
    what it does NOT contain: any "not found" line.  Text matching alone
    called this run clean, which is why _faults() now counts the prompt --
    a prompt that was answered successfully is never asked again.
    """
    backend = engine.AcCoreConsoleBackend

    refused = (
        "Detailed plot configuration? [Yes/No] <No>: Y\r\n"
        "Enter a layout name or [?] <Model>:\r\n"
        'Enter an output device name or [?] <Adobe PDF>: "DWG To PDF.pc3"\r\n'
        "Enter an output device name or [?] <Adobe PDF>:\r\n"
        "Enter paper size or [?] <Letter>:\r\n"
    )
    accepted = (
        "Detailed plot configuration? [Yes/No] <No>: Y\r\n"
        "Enter a layout name or [?] <Model>:\r\n"
        "Enter an output device name or [?] <Adobe PDF>: DWG To PDF.pc3\r\n"
        "Enter paper size or [?] <ANSI A (11.00 x 8.50 Inches)>:\r\n"
    )

    faults = backend._faults(refused)
    chk("a repeated device prompt is reported as a fault", bool(faults))
    chk("the fault says the answer was refused",
        any("refused" in f for f in faults))
    chk("it counts the prompts", any("2 times" in f for f in faults))
    # The accepted transcript is the control: same drawing, same script,
    # two characters of difference, and the paper-size default moves to
    # ANSI A -- DWG To PDF's OWN paper, where the refused run is left on
    # Letter, which is Adobe PDF's.  The device really did change.
    chk("the accepted transcript is clean", backend._faults(accepted) == [])
    chk("only the quoting differs between them",
        '"DWG To PDF.pc3"' in refused and '"DWG To PDF.pc3"' not in accepted)
    chk("the accepted run asks for the device exactly once",
        accepted.lower().count(backend._DEVICE_PROMPT) == 1)


def test_system_printers() -> None:
    """A Windows printer cannot be a headless plot device."""
    backend = engine.AcCoreConsoleBackend
    for name in ("Adobe PDF", "Microsoft Print to PDF",
                 "Microsoft XPS Document Writer",
                 "Default Windows System Printer.pc3"):
        chk("%s is recognised as a system printer" % name,
            backend._is_system_printer(name))
    # DWG To PDF is Autodesk's OWN PDF driver -- no Adobe involved, and it
    # writes to the path the script gives it.  Excluding it would remove
    # the one device that has been PROVEN to work on the target machine.
    for name in ("DWG To PDF.pc3", "AutoCAD PDF (High Quality Print).pc3"):
        chk("%s is NOT a system printer" % name,
            not backend._is_system_printer(name))

    saved = (backend.pc3, backend._device_list)
    try:
        backend.pc3 = None
        backend._device_list = ["Adobe PDF", "Microsoft Print to PDF",
                                "NRAO PDF Plot.pc3"]
        cands = backend._device_candidates(Path("x"), Path("y"), 1.0)
        chk("no system printer reaches the candidate list",
            not any(backend._is_system_printer(c) for c in cands))
        chk("a real probed PDF plotter still does",
            any("NRAO PDF Plot.pc3" in c for c in cands))
        # `?` lists nothing in the core console on the target machine, so
        # the probe must not be what the first attempt waits for.
        chk("the stock bare name leads, ahead of the probe",
            cands[0] == "DWG To PDF.pc3")
    finally:
        backend.pc3, backend._device_list = saved


def test_calibration_timeout_budget() -> None:
    """--timeout is per DRAWING; calibration must divide it, not multiply.

    Applied per attempt, eleven candidates meant eleven times the stated
    budget with nothing logged in between -- reported, understandably, as
    a hang.
    """
    backend = engine.AcCoreConsoleBackend
    saved = (backend.pc3, backend._device_list, backend._device,
             backend._calibration_failures, backend._attempt)
    seen = []
    try:
        backend.pc3 = None
        backend._device = None
        backend._device_list = []
        backend._calibration_failures = 0

        def fake_attempt(self, exe, source, target, spec, device=None):
            seen.append(self.timeout)
            return "Enter an output device name or [?] <None>:"

        backend._attempt = fake_attempt
        inst = backend(timeout=300.0)
        try:
            inst._calibrate(Path("acc.exe"), Path("a.dwg"),
                            Path("/nonexistent/a.pdf"),
                            engine.PageSpec(paper="AUTO"))
        except RuntimeError:
            pass

        chk("more than one candidate was attempted", len(seen) > 1)
        chk("no attempt got the whole per-drawing budget",
            all(t < 300.0 for t in seen))
        chk("no attempt is shorter than the floor",
            all(t >= min(300.0, backend.CALIBRATION_MIN_ATTEMPT)
                for t in seen))
        chk("the floor is long enough to finish a real plot",
            backend.CALIBRATION_MIN_ATTEMPT >= 30.0)
        chk("the per-drawing timeout is restored afterwards",
            inst.timeout == 300.0)
    finally:
        (backend.pc3, backend._device_list, backend._device,
         backend._calibration_failures, backend._attempt) = saved


def test_cancel_hook() -> None:
    """run_batch must be stoppable, on both paths, without losing work.

    This is the hook whose ABSENCE made the GUI reimplement the whole
    orchestration -- and that duplicate is why check_decoder() never
    fired there.  One orchestrator only works if it can be cancelled.
    """
    import shutil
    import tempfile

    chain = [engine.LibreDwgEzdxfBackend, engine.EzdxfBackend]
    if not all(c.available() for c in chain):
        chk("cancel hook accepts should_cancel",
            "should_cancel" in
            __import__("inspect").signature(engine.run_batch).parameters)
        return

    base = sorted(Path("test_drawings").rglob("*.dxf"))
    if not base:
        chk("cancel hook exists (no fixtures to exercise it with)",
            "should_cancel" in
            __import__("inspect").signature(engine.run_batch).parameters)
        return

    with tempfile.TemporaryDirectory(prefix="dwg2pdf_cancel_") as tmp:
        root = Path(tmp) / "in"
        root.mkdir()
        for i in range(12):
            shutil.copy(base[i % len(base)], root / ("sheet-%02d.dxf" % i))
        sources = sorted(root.glob("*.dxf"))

        # Serial path: stops BEFORE starting another drawing.
        out = Path(tmp) / "serial"
        calls = {"n": 0}

        def stop_after_one() -> bool:
            calls["n"] += 1
            return calls["n"] > 1

        rows = engine.run_batch(
            sources, root, out, chain, engine.PageSpec(paper="AUTO"),
            workers=1, should_cancel=stop_after_one)
        chk("serial: cancelling stops the run",
            0 < len(rows) < len(sources))
        chk("serial: completed work is still returned",
            all(r["status"] == "ok" for r in rows))
        chk("serial: no PDF for a drawing that never ran",
            len(list(out.rglob("*.pdf"))) == len(rows))

        # Parallel path.  MORE JOBS THAN WORKERS, deliberately: with one
        # job per worker every future is already in flight when the
        # first completes, and letting in-flight drawings finish is the
        # documented behaviour -- killing a worker mid-plot can leave a
        # half-written PDF where a deliverable should be.
        out = Path(tmp) / "parallel"
        calls = {"n": 0}

        def stop_after_three() -> bool:
            calls["n"] += 1
            return calls["n"] > 3

        rows = engine.run_batch(
            sources, root, out, chain, engine.PageSpec(paper="AUTO"),
            workers=2, should_cancel=stop_after_three)
        chk("parallel: cancelling stops the run",
            0 < len(rows) < len(sources))
        chk("parallel: completed work is still returned", bool(rows))

        # An absent hook must change nothing at all.
        out = Path(tmp) / "nohook"
        rows = engine.run_batch(
            sources, root, out, chain, engine.PageSpec(paper="AUTO"),
            workers=2)
        chk("no hook: every drawing still converts",
            sum(1 for r in rows if r["status"] == "ok") == len(sources))

    import inspect
    src = inspect.getsource(engine.run_batch)
    chk("cancellation is checked BEFORE each serial drawing",
        "Cancel should not start" in src)
    chk("pass 2 is not entered after a cancel",
        "cancelled before pass 2" in src)


def test_log_noise() -> None:
    """A healthy run must stay readable, and the detail must survive.

    A 1762-drawing run converting at 1-3 s/sheet with nothing failing was
    reported as HUNG, because ezdxf's recover pass logs one line per
    repaired structure irregularity -- 107 of them between two
    consecutive progress lines -- and -v lets library loggers through.
    A progress display that cannot be read is not a progress display.
    """
    import io
    import logging
    import tempfile

    with tempfile.TemporaryDirectory(prefix="dwg2pdf_log_") as tmp:
        log_file = Path(tmp) / "run.log"
        buf, real = io.StringIO(), sys.stderr
        sys.stderr = buf
        try:
            engine._configure_logging(verbose=True, quiet=False,
                                      log_file=log_file)
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
            for _ in range(20):
                eng.debug("plot device attempt 1/4: DWG To PDF.pc3")
            ez.warning("a real ezdxf warning")
            eng.info("[3/1762] c.dwg -> 1 page file(s)")
            for handler in logging.getLogger().handlers:
                handler.flush()
        finally:
            sys.stderr = real
            engine._configure_logging(verbose=False, quiet=True)

        out = buf.getvalue()
        lines = [ln for ln in out.strip().splitlines() if ln.strip()]

        chk("107 library lines do not reach the console",
            "non-unique" not in out and "ENDBLK" not in out)
        chk("every progress line survives", out.count("/1762]") == 3)
        chk("a real library WARNING still gets through",
            "a real ezdxf warning" in out)
        chk("the console stays readable (< 12 lines, not 127)",
            len(lines) < 12)
        # No orphaned tallies: a count for a message the cap hid would be
        # worse than the noise, because it is unattributable.
        chk("no tally for a message that was never shown",
            out.count("previous message repeated")
            <= out.count("plot device attempt"))
        chk("repeats of OUR OWN messages are collapsed with a count",
            "plot device attempt" in out
            and "repeated 19 more times" in out)

        # The file is for reading afterwards, so it keeps everything --
        # capping the LOGGER instead of the handler would have discarded
        # these at source, which was the first attempt at this fix.
        detail = log_file.read_text(encoding="utf-8")
        chk("the log file keeps all 107 library lines",
            detail.count("non-unique") + detail.count("ENDBLK") == 107)
        chk("the log file is undeduplicated",
            detail.count("plot device attempt") == 20)
        chk("the log file names the logger, for triage",
            "ezdxf" in detail)

    chk("--verbose-libs exists as the escape hatch",
        "--verbose-libs" in engine.build_parser().format_help())
    chk("--log-file exists",
        "--log-file" in engine.build_parser().format_help())


def test_decoder_warning() -> None:
    """The old-decoder advice must describe what is actually on disk.

    0.4.2 asserted "the copy bundled in vendor/ is newer" without
    checking that vendor/ existed, and sent an operator to inspect PATH
    ordering for a file that was not there.
    """
    backend = engine.LibreDwgEzdxfBackend
    saved = (backend.version, backend._exe)
    try:
        # A current decoder must say nothing at all.
        backend.version = classmethod(lambda cls: (0, 14, 8593))
        backend._exe = classmethod(lambda cls: Path("/usr/bin/dwg2dxf"))
        chk("a current decoder produces no warning",
            backend.decoder_warning() is None)

        # An old one must warn, and name the version and the path.
        backend.version = classmethod(lambda cls: (0, 11, 3876))
        msg = backend.decoder_warning()
        chk("an old decoder warns", bool(msg))
        chk("the warning names the version", "0.11.3876" in (msg or ""))
        chk("the warning names the executable it resolved",
            "dwg2dxf" in (msg or ""))

        # Off Windows there is no linux vendor dir in this tree, so this
        # exercises the honest branch: say the bundled copy is absent and
        # that PATH order cannot help, rather than advising a reorder.
        if backend.bundled_decoder() is None:
            chk("it says the bundled copy is NOT on disk",
                "NOT on disk" in (msg or ""))
            chk("it names where it looked",
                str(backend.bundled_decoder_dir()) in (msg or ""))
            chk("it does not advise reordering PATH for a missing file",
                "PATH order is irrelevant" in (msg or ""))
        else:
            chk("a present bundled copy is reported as unexpected",
                "unexpected" in (msg or ""))
            chk("it names the bundled copy it found",
                str(backend.bundled_decoder()) in (msg or ""))
            chk("it does not claim the file is missing",
                "NOT on disk" not in (msg or ""))

        # No decoder at all: nothing to warn ABOUT, and certainly no
        # advice to give about its version.
        backend._exe = classmethod(lambda cls: None)
        chk("no decoder at all warns about nothing",
            backend.decoder_warning() is None)
    finally:
        backend.version, backend._exe = saved

    chk("check_decoder is callable from the parent",
        callable(engine.check_decoder))
    # Proof the warning is emitted by the PARENT, not per worker: the
    # backend's own inline notice is DEBUG now.
    import inspect
    src = inspect.getsource(engine.LibreDwgEzdxfBackend._dwg_to_dxf)
    chk("the in-worker notice is DEBUG, not WARNING",
        "_LOG.debug" in src and "_LOG.warning" not in src)
    chk("run_batch performs the check in the parent",
        "check_decoder()" in inspect.getsource(engine.run_batch))


def test_stdin_is_devnull() -> None:
    """A short script must not leave accoreconsole reading the console.

    accoreconsole does not stop when its /s script runs out: it falls
    back to reading stdin and waits.  A desynchronised answer sequence
    IS a short script, so with an inherited stdin every such drawing
    burned the whole --timeout waiting for a keypress nobody was there
    to make.  Noticed only because a hand-run probe needed Enter pressed
    several times to advance.
    """
    import inspect
    import subprocess as sp

    src = inspect.getsource(engine._run)
    chk("_run passes stdin explicitly", "stdin=" in src)
    chk("_run uses DEVNULL, not inherited stdin",
        "subprocess.DEVNULL" in src or "sp.DEVNULL" in src)

    # And prove it end to end: a child that reads stdin must see EOF at
    # once rather than blocking until the timeout.
    proc = engine._run(
        [__import__("sys").executable, "-c",
         "import sys; sys.stdout.write(repr(sys.stdin.read()))"],
        timeout=10.0,
    )
    chk("a child reading stdin gets EOF immediately",
        proc.returncode == 0 and proc.stdout.strip() == "''")
    chk("DEVNULL is what subprocess was given", sp.DEVNULL == -3)


def test_exclude() -> None:
    """--exclude must prune a duplicate archive tree, by name or by path.

    The GBT tree really does carry ``ROSE_GBT/Achive/RoseGBT/`` as a full
    duplicate of the live tree, misspelling included, so a recursive run
    converted much of the set twice -- doubling a 3.1-hour run and
    reporting each failure twice as if it were two drawings.
    """
    import tempfile

    with tempfile.TemporaryDirectory(prefix="dwg2pdf_x_") as tmp:
        root = Path(tmp)
        live = root / "Live" / "121729 - Weldment"
        arch = root / "Achive" / "RoseGBT" / "Live" / "121729 - Weldment"
        for folder in (live, arch):
            folder.mkdir(parents=True)
            (folder / "121729_01_A.dwg").write_bytes(b"not a real drawing")

        chk("both copies are found without --exclude",
            len(engine.discover_inputs([root])) == 2)
        chk("a bare directory name prunes it",
            len(engine.discover_inputs([root], exclude=["Achive"])) == 1)
        chk("a path glob prunes it too",
            len(engine.discover_inputs([root], exclude=["*/achive/*"])) == 1)
        chk("matching is case-insensitive",
            len(engine.discover_inputs([root], exclude=["ACHIVE"])) == 1)
        chk("a non-matching glob prunes nothing",
            len(engine.discover_inputs([root], exclude=["Nope"])) == 2)
        chk("the surviving copy is the live one",
            "Achive" not in str(
                engine.discover_inputs([root], exclude=["Achive"])[0]))





# %% 0.5.0: the field run's four defects
def test_prompt_answers() -> None:
    """Answers must be bound to QUESTIONS, not to positions.

    The field run's calibration accepted the device on attempt 1 -- the
    paper default moved to ANSI A, DWG To PDF's own -- and then failed
    two prompts later::

        Enter paper size or [?] <ANSI A (11.00 x 8.50 Inches)>:
        Enter paper units [Inches/Millimeters] <Inches>: L
        Command: N  Unknown command "N".

    "Enter paper units" was a prompt the fixed answer list did not know
    about, so the ORIENTATION answer fed it and everything after shifted
    by one.  The prompt set also varies between devices and drawings, so
    no fixed list can be right.
    """
    backend = engine.AcCoreConsoleBackend

    # The prompt that caused it.
    chk("the paper-units prompt is now answered",
        backend._answer_for(
            "Enter paper units [Inches/Millimeters] <Inches>:") == "")
    # ...and not with the orientation answer, which is what went wrong.
    chk("orientation is bound to the orientation prompt",
        backend._answer_for(
            "Enter drawing orientation [Portrait/Landscape] <Landscape>:")
        == "@ORIENT@")
    chk("the device is bound to the device prompt",
        backend._answer_for(
            "Enter an output device name or [?] <Adobe PDF>:") == "@DEVICE@")
    chk("the output path is bound to the file-name prompt",
        backend._answer_for("Enter file name <x.pdf>:") == "@TARGET@")

    # An unknown prompt must take the DEFAULT, never another answer.
    chk("an unknown prompt returns None, meaning 'press Enter'",
        backend._answer_for("Enter something never seen before:") is None)

    # Overlapping fragments must not shadow each other.
    chk("'plot upside down' is not swallowed by a looser 'plot' rule",
        backend._answer_for("Plot upside down? [Yes/No] <No>:") == "N")
    chk("'plot with lineweights' keeps its own answer",
        backend._answer_for("Plot with lineweights? [Yes/No] <Yes>:") == "Y")
    chk("'plot with plot styles' keeps its own answer",
        backend._answer_for("Plot with plot styles? [Yes/No] <Yes>:") == "Y")
    chk("every rule has a distinct fragment",
        len({f for f, _ in backend._PROMPT_ANSWERS})
        == len(backend._PROMPT_ANSWERS))
    chk("prompt mode is the default (0.5.0)", backend.mode == "prompt")
    chk("the .scr path is still reachable for comparison",
        "script" in engine.build_parser().format_help())


def test_no_hijacking_autocad() -> None:
    """A batch must not run inside the operator's own AutoCAD session.

    On the field run it attached to the running instance, plotted through
    the window the operator was working in, and died with
    "FATAL ERROR: Unhandled Access Violation Reading 0x05aa".
    """
    backend = engine.AcadComBackend
    chk("attaching is OFF by default (0.5.0)", backend.attach is False)
    chk("--acad-attach exists to opt back in",
        "--acad-attach" in engine.build_parser().format_help())

    # Recycling: an automation session that faults outright must cost one
    # restart, not the run -- but not a restart per sheet either, which
    # would be 30-60 s of start-up each.
    chk("the COM session is recycled periodically",
        backend.recycle_after > 1)
    chk("recycling is not per drawing", backend.recycle_after >= 10)
    chk("--acad-recycle-after exposes it",
        "--acad-recycle-after" in engine.build_parser().format_help())
    chk("both reach the workers",
        "attach" in engine.BACKEND_SETTING_KEYS["acad-com"]
        and "recycle_after" in engine.BACKEND_SETTING_KEYS["acad-com"])
    chk("the accore mode reaches the workers too",
        "mode" in engine.BACKEND_SETTING_KEYS["accoreconsole"])


def test_plot_straight_to_destination() -> None:
    """The scratch rename turned a viewer LOCK into a viewer DIALOG.

    0.4.0 plotted into .dwg2pdf_plot and renamed, which did defeat the
    lock -- and handed the viewer a path the rename had already moved::

        Cannot open the document ... \\.dwg2pdf_plot\\<sheet>.pdf
        Error [Operating system]: The system cannot find the path specified.

    Once per sheet, modal, in a 956-sheet serial run.
    """
    import tempfile

    backend = engine.AcadComBackend
    with tempfile.TemporaryDirectory(prefix="dwg2pdf_dest_") as tmp:
        target = Path(tmp) / "sheet.pdf"
        chk("a free destination needs no clearing",
            backend._clear_destination(target))

        target.write_bytes(b"%PDF-1.4 last run")
        chk("an existing deliverable is removed so the plot can go there",
            backend._clear_destination(target) and not target.exists())

        # A directory cannot be unlinked, which stands in for a locked
        # file: the caller must learn that and fall back, not crash.
        blocked = Path(tmp) / "blocked.pdf"
        blocked.mkdir()
        chk("an unremovable destination reports False, it does not raise",
            backend._clear_destination(blocked, attempts=2) is False)

    import inspect
    # _plot_once is where the plot actually happens; _convert_impl is the
    # thin wrapper that retries it on a context error.
    src = inspect.getsource(backend._plot_once)
    chk("the plot target IS the deliverable by default",
        "plotted, scratch = target, None" in src)
    chk("the scratch path survives only as the fallback",
        "_clear_destination" in src and ".dwg2pdf_plot" in src)
    chk("no rename happens when we plotted straight there",
        "if plotted != target:" in src)


def test_layouts_default() -> None:
    """Paper-space-only sheets must not fail pass 1 for nothing.

    "nothing to render for --layouts 'model': Model (empty)" accounted
    for a large share of the field run's 956 pass-1 failures -- sheets
    whose content is in paper space, sent to the AutoCAD passes by a
    default that never suited a drawing set.
    """
    chk("PageSpec defaults to 'auto' (0.5.0)",
        engine.PageSpec(paper="AUTO").layouts == "auto")
    chk("the CLI default matches the dataclass",
        engine.build_parser().get_default("layouts") == "auto")
    chk("'model' is still selectable",
        engine.PageSpec(paper="AUTO", layouts="model").layouts == "model")


# %% Entry point
def run_test() -> int:
    """Run every check and report."""
    _ensure_fixtures()
    print("AUTOCAD BACKEND CHECKS (engine %s)" % engine.__revision__)
    test_script_text()
    test_faults()
    test_device_candidates()
    test_answer_forms()
    test_prompt_repeat_fault()
    test_system_printers()
    test_calibration_timeout_budget()
    test_prompt_answers()
    test_no_hijacking_autocad()
    test_plot_straight_to_destination()
    test_layouts_default()
    test_cancel_hook()
    test_log_noise()
    test_decoder_warning()
    test_stdin_is_devnull()
    test_exclude()
    test_device_probe()
    test_calibration()
    test_calibration_gives_up()
    test_context_recovery()
    test_window_mode()
    test_move_into_place()
    test_settings_propagation()
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
