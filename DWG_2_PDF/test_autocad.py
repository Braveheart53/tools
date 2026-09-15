#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Engine-side checks for the AutoCAD backends (dwg2pdf 0.4.1).

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


# %% Runner
def run_test() -> int:
    """Run every check and report."""
    print("AUTOCAD BACKEND CHECKS (engine %s)" % engine.__revision__)
    test_script_text()
    test_faults()
    test_device_candidates()
    test_answer_forms()
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
