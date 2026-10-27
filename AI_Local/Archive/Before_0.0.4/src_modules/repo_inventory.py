# -*- coding: utf-8 -*-
"""
repo_inventory.py -- machine-readable inventory of the Braveheart53/tools repo.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-20

PURPOSE
-------
The repository homepage is generated from this module rather than hand-written,
for the same reason the AI_Local pages are: a hand-written catalogue of
fourteen projects drifts the first time one of them is renamed or revised.

Every entry below was read from the repository working tree on 2026-10-20:
the version from each project's own README or module header, the entry point
from the file that actually exists, the size from the files on disk.  Nothing
here is inferred.

HOW THE PIECES RELATE
---------------------
The organising idea of the homepage is that this repository is not a pile of
unrelated tools.  It has ONE foundation -- the Py3p12 mamba environment -- and
everything else either builds that foundation, runs inside it, or documents
the physics behind something that runs inside it:

    Py3p12 mamba environment          the foundation everything else assumes
      |
      +-- AI_Local                    a local model that writes code FOR that
      |                               environment, and builds and tests it
      |
      +-- engineering tools           what actually runs in the environment
      |
      +-- Educational                 the physics and DSP behind those tools

:data:`STAGES` encodes that as a five-stage implementation flow, and
:data:`PROJECTS` is the catalogue each stage points into.  Both are consumed
by ``page_home.py``.

FIELD CONVENTIONS
-----------------
All strings are PLAIN TEXT, never HTML.  They are escaped at the point of use,
so writing ``&amp;`` here produces a literal ``&amp;`` on the page.  The build
script's ``check_manifest_plaintext()`` enforces this for the page manifest
and :func:`validate` enforces it here.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


# %% Repository metadata -----------------------------------------------------
#: Date this inventory was taken from the working tree.
SURVEYED: str = "2026-10-20"

#: The repository this homepage fronts.
REPO_URL: str = "https://github.com/Braveheart53/tools"

#: Version of the homepage itself, independent of the AI_Local set version.
HOME_VERSION: str = "0.0.2"


# %% Project catalogue -------------------------------------------------------
@dataclass
class Project:
    """One project or tool in the repository.

    Attributes
    ----------
    path
        Directory or file, relative to the repository root.  Used as the link
        target and shown verbatim so a reader can find it on disk.
    name
        Human-readable name.
    version
        The project's own version, as its README or module header states it.
        ``None`` where the project does not carry one.
    summary
        One or two sentences: what it does and why it exists.
    stage
        Which flow stage this belongs to -- a key of :data:`STAGES`, or
        ``"toolbox"`` for something that is used rather than installed.
    language
        Primary implementation language or format.
    entry
        The file to run or open first.  ``None`` for a data or document
        directory.
    environment
        Which environment it needs: ``"Py3p12"``, ``"own"`` (it ships its own
        environment file), ``"none"`` (no Python), or a specific note.
    needs
        Paths of other entries in this catalogue that must be in place first.
    docs
        Documentation files inside the project worth opening, relative to
        ``path``.
    notes
        Anything a reader should know before using it, including gaps.
    """

    path: str
    name: str
    summary: str
    stage: str
    language: str
    version: Optional[str] = None
    entry: Optional[str] = None
    environment: str = "Py3p12"
    needs: Sequence[str] = field(default_factory=tuple)
    docs: Sequence[str] = field(default_factory=tuple)
    notes: str = ""


#: Every project in the repository, in the order the homepage lists them.
PROJECTS: List[Project] = [

    # ---- Stage 0: the foundation everything else assumes ------------------
    Project(
        path="Py3p12_Mamba_Yamls",
        name="Py3p12 mamba environment",
        version="Py3p12_Clean + 20260904_2245",
        summary="The Python 3.12 mamba environment every Python tool in this "
                "repository is written against, as two YAML files: a minimal "
                "base to create from, then a full update that reproduces the "
                "working install.",
        stage="foundation",
        language="conda/mamba YAML",
        entry="Py3p12_Clean.yml",
        environment="creates it",
        docs=("Readme.md",
              "Mamba on Windows — Install, Shell Setup, and YAML Environments.md",
              "Mamba on Windows 10   11 — Setup Guide (PDF).pdf"),
        notes="Create from Py3p12_Clean.yml first, then update from the dated "
              "YAML. The setup guide covers the part that actually causes "
              "trouble: making activation work in PowerShell 7 and Windows "
              "PowerShell separately, and the CONDA_ENVS_DIRS special case.",
    ),
    Project(
        path="devenv/pip_updates.py",
        name="pip update helper",
        summary="Reports and applies pip updates inside a mamba environment, "
                "reading the environment YAML so conda-managed packages are "
                "not clobbered by pip.",
        stage="foundation",
        language="Python",
        entry="pip_updates.py",
        needs=("Py3p12_Mamba_Yamls",),
        notes="Run it before a long session rather than after something breaks.",
    ),

    # ---- Stage 1-4: the local AI deployment -------------------------------
    Project(
        path="AI_Local",
        name="AI_Local — local AI deployment set",
        version="0.0.1",
        summary="Sixteen pages covering the whole local-AI deployment: serving "
                "a model, splitting one across several machines, letting it "
                "build and test code against the Py3p12 environment, and "
                "monitoring the hardware while it runs.",
        stage="serve",
        language="HTML documentation + Python/PowerShell scripts",
        entry="index.html",
        environment="Py3p12 for the scripts",
        needs=("Py3p12_Mamba_Yamls",),
        docs=("index.html", "README_REBUILD.md", "CHANGELOG.html",
              "references.html"),
        notes="Start at AI_Local/index.html, which has its own staged reading "
              "order. The binary installers it references are listed in "
              "Files_you_Will_need_that_areNot_here.txt and are not all in "
              "the repository.",
    ),

    # ---- Toolbox: what runs in the environment ----------------------------
    Project(
        path="Narda_Probes_FFT",
        name="EMF Envelope FFT Analyzer",
        version="0.0.4",
        summary="Computes envelope (modulation) spectra from broadband EMF "
                "probe and spectrum-analyzer logs, writing native Veusz "
                ".vszh5 output. Built for Narda probe data.",
        stage="toolbox",
        language="Python / QtPy",
        entry="emf_envelope_fft_v0_0_4.py",
        environment="own",
        needs=("Py3p12_Mamba_Yamls",),
        docs=("docs/EMF_Envelope_FFT_Manual_v0.0.4.pdf", "emf_envelope_fft.yml"),
        notes="Ships its own environment YAML and a LaTeX-built manual. "
              "vszh5_writer.py is the reusable Veusz HDF5 writer, shared in "
              "spirit with the FitsAutoPlot repository.",
    ),
    Project(
        path="ISP_Speed_Test",
        name="ISP Speed Monitor",
        version="1.7.2 (script 1.3.1)",
        summary="Long-running internet speed monitoring with a Qt GUI, "
                "campaign configuration files and native Veusz .vszh5 output "
                "for the plots.",
        stage="toolbox",
        language="Python / QtPy",
        entry="isp_speed_monitor.py",
        environment="own",
        needs=("Py3p12_Mamba_Yamls",),
        docs=("README.md", "CHANGELOG.md", "docs/BUILD_PLAN.md",
              "environment.yml"),
        notes="Has its own environment.yml, a pyproject.toml and a uv.lock, so "
              "it can be installed standalone. A GUI smoke test lives in "
              "tests/gui_smoke.py.",
    ),
    Project(
        path="DWG_2_PDF",
        name="dwg2pdf — batch drawing conversion",
        version="engine 0.5.2 / GUI 0.2.21",
        summary="Converts a tree of 2D AutoCAD drawings (.dwg, .dxf) into a "
                "mirrored tree of PDFs with a manifest recording what happened "
                "to every sheet. Command line for the batch, GUI for the rest.",
        stage="toolbox",
        language="Python / QtPy, around LibreDWG",
        entry="README.md",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
        docs=("README.md", "docs/Dwg2Pdf_0.5.1_pass1_field_results.md",
              "MANIFEST.sha256"),
        notes="MIT-licensed tooling around GPL-3 LibreDWG. Validated on real "
              "production sheets mixing AutoCAD R14 and R2018. The working "
              "code ships as dated .7z bundles under Archive/.",
    ),
    Project(
        path="GBO Sidelobe",
        name="Sidelobe — telescope strayscan computation",
        summary="Computes telescope sidelobe contributions, convolving the "
                "sidelobe pattern with an all-sky map to produce strayscan "
                "correction files. Supports GBT and the NRAO 140-foot, in "
                "both SDD and SDFITS formats.",
        stage="toolbox",
        language="Python + a legacy binary",
        entry="sidelobe.py",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
        docs=("sidelobe-readme.md", "sidelobe-technical.md",
              "sidelobe-userguide.md"),
        notes="Includes sidelobe_gui.py and PreReqsInstall.py. The base32 and "
              "base64 text files are encoded copies of the legacy binary; "
              "secret scanners flag them as false positives because 'AKIA' "
              "occurs by chance in base32 data.",
    ),
    Project(
        path="Dysh_Play",
        name="Dysh GUI experiments",
        summary="A GUI front end and setup helper for dysh, the GBO single-dish "
                "data reduction package.",
        stage="toolbox",
        language="Python",
        entry="Daves_dysh_setup.py",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
        notes="Exploratory. Each .py has a matching .txt copy, so diff them "
              "before assuming which is current.",
    ),
    Project(
        path="Keysight_Agilent_RS232_test.py",
        name="Keysight/Agilent RS-232 test",
        summary="Serial instrument communication against Keysight and Agilent "
                "equipment over RS-232, for bringing up a link before writing "
                "a full driver.",
        stage="toolbox",
        language="Python",
        entry="Keysight_Agilent_RS232_test.py",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
        notes="The fuller instrument-control work lives in the companion "
              "RF_Equipment_Comms repository.",
    ),
    Project(
        path="Inventor_Parameter_XML2XLSX.py",
        name="Inventor parameter export",
        summary="Exports Autodesk Inventor user parameters from the XML files "
                "Inventor writes into Excel workbooks, for review and bulk "
                "edit outside the CAD tool.",
        stage="toolbox",
        language="Python",
        entry="Inventor_Parameter_XML2XLSX.py",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
        docs=("Example_Inventor_XML_File.xml",),
        notes="Example_Inventor_XML_File.xml at the repository root is the "
              "sample input.",
    ),
    Project(
        path="Convert-VisioLegacyFiles.ps1",
        name="Visio legacy file converter",
        summary="Batch-converts legacy Visio binary files (.vsd, .vss, .vst) "
                "to the modern Open XML formats via Visio COM automation, "
                "then sorts the output into per-extension folders.",
        stage="toolbox",
        language="PowerShell",
        entry="Convert-VisioLegacyFiles.ps1",
        environment="none",
        notes="Needs a local Visio installation; it drives a hidden COM "
              "instance. An alternative implementation and three older "
              "single-purpose scripts are in Archive/.",
    ),
    Project(
        path="misc/github-repo-size.py",
        name="GitHub repository size report",
        summary="Reports the size of a list of GitHub repositories and opens "
                "the result in a browser, for finding which repository is "
                "carrying the weight.",
        stage="toolbox",
        language="Python",
        entry="github-repo-size.py",
        environment="Py3p12",
        notes="Reads the repository list from misc/repos.txt.",
    ),

    # ---- Reference: the physics behind the tools --------------------------
    Project(
        path="Educational/Atomic Theory Atlas.zip",
        name="Atomic Theory Atlas",
        summary="A cited reference on atomic theory from QED up to the "
                "macroscopic permittivity an electromagnetic solver consumes, "
                "stopping at the atomic transitions used for masing and "
                "timekeeping.",
        stage="reference",
        language="HTML page set",
        entry="index.html (inside the archive)",
        environment="none",
        notes="This is the page set whose equation and variable-definition "
              "pattern the AI_Local pages follow: a provenance pill, a "
              "'Define variables' table with SI units, and an explicit "
              "derivation behind every derived result.",
    ),
    Project(
        path="Educational/Precision Timing Reference — Local _ Deploy Bundle.zip",
        name="Precision Timing Reference",
        summary="Reference bundle on precision timing and frequency standards, "
                "packaged to deploy locally.",
        stage="reference",
        language="HTML page set",
        environment="none",
    ),
    Project(
        path="Educational/matched-filtering-v3.zip",
        name="Matched filtering",
        summary="Reference material on matched filtering, the detection "
                "problem it solves and its signal-processing derivation.",
        stage="reference",
        language="HTML page set",
        environment="none",
    ),
    Project(
        path="Educational/fourier_visualizer_qtpy.py",
        name="Fourier visualizer",
        summary="Interactive Qt visualiser for Fourier decomposition, for "
                "building intuition and for teaching.",
        stage="reference",
        language="Python / QtPy",
        entry="fourier_visualizer_qtpy.py",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
    ),
    Project(
        path="Educational/convolution_visualizer.py",
        name="Convolution visualizer",
        summary="Interactive Qt visualiser for convolution, the operation "
                "underlying both the matched filter and the sidelobe "
                "strayscan computation in this repository.",
        stage="reference",
        language="Python / QtPy",
        entry="convolution_visualizer.py",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
    ),
    Project(
        path="Educational/trig_function_plotter.py",
        name="Trig function plotter",
        summary="Interactive plotter for trigonometric functions.",
        stage="reference",
        language="Python / QtPy",
        entry="trig_function_plotter.py",
        environment="Py3p12",
        needs=("Py3p12_Mamba_Yamls",),
    ),
]


# %% The implementation flow -------------------------------------------------
@dataclass
class Stage:
    """One stage of the staged implementation flow.

    Attributes
    ----------
    key
        Stable identifier, also the DOM id and the value a project's
        ``stage`` field carries.
    number
        Display number.  Stage 0 is the foundation, which is why these start
        at zero rather than one.
    title
        Short title.
    goal
        One sentence: what is true once this stage is done.
    why
        Why this stage comes where it does, which is the part a link list
        cannot convey.
    steps
        Ordered actions, each a (action, where) pair.  ``where`` is a path in
        the repository or an empty string.
    time
        Rough wall-clock estimate, stated as a range.
    checkpoint
        A concrete command or observation that proves the stage is complete.
    applies_to
        Hardware tiers this stage applies to: any of ``"single"``, ``"pair"``,
        ``"cluster"``.  Used by the tier selector on the page.
    """

    key: str
    number: int
    title: str
    goal: str
    why: str
    steps: Sequence[Tuple[str, str]]
    time: str
    checkpoint: str
    applies_to: Sequence[str] = ("single", "pair", "cluster")


#: The five-stage flow, in order.  Each stage's prerequisite is the previous
#: one, so a reader can start anywhere above their current position.
STAGES: List[Stage] = [
    Stage(
        key="foundation",
        number=0,
        title="Build the foundation",
        goal="A named Py3p12 mamba environment exists and activates in your "
             "shell, and a C++ toolchain is on PATH.",
        why="Every Python tool in this repository is written against this one "
            "environment, and the local model in stage 2 will be told to run "
            "Python only through it. Getting it right once removes a whole "
            "class of problem later: a model that reports a library is "
            "missing when it is simply looking at the system interpreter.",
        steps=(
            ("Read the setup guide, particularly the PowerShell activation and "
             "CONDA_ENVS_DIRS sections",
             "Py3p12_Mamba_Yamls/Mamba on Windows — Install, Shell Setup, and YAML Environments.md"),
            ("Create the base environment: mamba env create -c conda-forge "
             "--strict-channel-priority -f Py3p12_Clean.yml",
             "Py3p12_Mamba_Yamls/Py3p12_Clean.yml"),
            ("Update it to the full working set: mamba env update -c "
             "conda-forge --strict-channel-priority -n Py3p12 -f "
             "Py3p12_20260904_2245.yml",
             "Py3p12_Mamba_Yamls/Py3p12_20260904_2245.yml"),
            ("Install the Visual Studio C++ build tools, so the model can "
             "compile in stage 2",
             "AI_Local/local-code-build-test.html#cpp"),
        ),
        time="45–90 min, mostly the solve",
        checkpoint="mamba run -n Py3p12 python -c \"import PySide6, numpy, "
                   "h5py; print('ok')\"  prints ok",
    ),
    Stage(
        key="serve",
        number=1,
        title="Serve a model",
        goal="A model answers on your network, and you know why you picked "
             "that model rather than another.",
        why="This comes before giving the model a shell because the model "
            "choice constrains everything after it. Picking the model first "
            "avoids building a stack around something your card cannot hold, "
            "which is the expensive version of this mistake.",
        steps=(
            ("Work out what will fit: the criteria, then the memory arithmetic",
             "AI_Local/ollama-model-selection.html"),
            ("Install Ollama and pull the chosen tag; raise "
             "OLLAMA_CONTEXT_LENGTH from its 4096 default",
             "AI_Local/ollama-model-selection.html#recommend"),
            ("If the model will not fit on one machine, build llama.cpp with "
             "RPC and split it across nodes",
             "AI_Local/llama-rpc-vulkan-guide.html"),
            ("Put Open WebUI in front of it",
             "AI_Local/local-code-build-test.html#topology"),
        ),
        time="1–3 h, plus model download",
        checkpoint="ollama ps shows the model resident on the GPU, not split "
                   "with the CPU",
    ),
    Stage(
        key="hands",
        number=2,
        title="Give the model hands",
        goal="The model can run a command, compile code and read the error, "
             "against the Py3p12 environment from stage 0.",
        why="This is the stage that turns a chat window into something that "
            "does work. It is also the stage with a real blast radius, which "
            "is why the containment decision is made here and verified rather "
            "than assumed.",
        steps=(
            ("Choose an execution backend. Open Terminal in Docker is the "
             "recommended default",
             "AI_Local/local-code-build-test.html#decision"),
            ("Wire in the Py3p12 environment, by host kernel or by rebuilding "
             "it inside the container",
             "AI_Local/local-code-build-test.html#mamba"),
            ("Bound what it can reach: egress allowlist, CORS, file-browser "
             "root, session cap",
             "AI_Local/local-code-build-test.html#security"),
            ("For work that must touch the host itself, use the OS-enforced "
             "sandbox instead and run its denial checks",
             "AI_Local/claude-sandbox-local-env.html#project"),
        ),
        time="1–2 h",
        checkpoint="Ask the model to run the tests, fix the first failure and "
                   "re-run. Two test runs with an edit between them.",
    ),
    Stage(
        key="watch",
        number=3,
        title="Watch the hardware",
        goal="You can see GPU utilisation, VRAM and token rate, and you would "
             "notice a model quietly spilling to system RAM.",
        why="The failure that wastes the most time in a local deployment is "
            "invisible from the chat window: weights spill to system RAM and "
            "throughput drops roughly ninefold while everything still works. "
            "A VRAM gauge makes it obvious.",
        steps=(
            ("Size the stack before installing it: retention disk, ingest "
             "rate, and the query window that stops panels emptying",
             "AI_Local/monitoring-sizing.html"),
            ("Install Prometheus and Grafana",
             "AI_Local/Grafana_Prometheus_install_windows.html"),
            ("Add the GPU exporters, checking which metrics are counters and "
             "which are gauges",
             "AI_Local/GPU_monitoring_setup.html"),
            ("Scrape llama-server's own metrics and add a resident-VRAM gauge",
             "AI_Local/Promethius_Grafana_windows11-llama-monitoring-tutorial.html"),
        ),
        time="2–4 h",
        checkpoint="A Grafana panel shows resident VRAM per node next to "
                   "decode rate",
        applies_to=("pair", "cluster"),
    ),
    Stage(
        key="work",
        number=4,
        title="Put it to work",
        goal="The model is maintaining real code in this repository, in the "
             "environment from stage 0.",
        why="Everything above is scaffolding. These are the programs the "
            "scaffolding exists to maintain, and they are also the honest "
            "test of whether the setup works: a model that cannot get a Qt "
            "test to run headless has not been configured, however good its "
            "benchmark scores are.",
        steps=(
            ("Point it at a tool with tests and a clear entry point",
             "ISP_Speed_Test"),
            ("For instrument and signal work, the FFT analyzer and its Veusz "
             "writer", "Narda_Probes_FFT"),
            ("For batch document work, the drawing converter", "DWG_2_PDF"),
            ("Remember the Qt rule: there is no display in a container, so "
             "set QT_QPA_PLATFORM=offscreen",
             "AI_Local/local-code-build-test.html#python"),
        ),
        time="ongoing",
        checkpoint="A change the model wrote, built and tested is in your "
                   "working tree and you have reviewed it",
    ),
]


# %% Hardware tiers ----------------------------------------------------------
@dataclass
class Tier:
    """A hardware shape the flow adapts to.

    The project's stated goal is an instruction set for a variety of hardware
    setups, so the homepage lets a reader pick their shape and hides the
    stages that do not apply to it.
    """

    key: str
    name: str
    hardware: str
    model_hint: str
    stages: Sequence[str]
    note: str


#: The three shapes this repository's documentation actually covers.
TIERS: List[Tier] = [
    Tier(
        key="single",
        name="One machine",
        hardware="A single desktop or laptop with one GPU",
        model_hint="Pick the largest tag that leaves roughly a third of VRAM "
                   "free for the key/value cache. Below 16 GB, prefer a small "
                   "model that fits entirely over a large one that spills.",
        stages=("foundation", "serve", "hands", "work"),
        note="Monitoring is optional on one machine: ollama ps answers the "
             "question a dashboard would. Skip stage 3 until you have a "
             "second node.",
    ),
    Tier(
        key="pair",
        name="Two machines",
        hardware="A workstation plus one other machine with a GPU",
        model_hint="Keep the model on whichever machine has the most VRAM and "
                   "put the execution sandbox on the other, so a build cannot "
                   "evict the model from memory.",
        stages=("foundation", "serve", "hands", "watch", "work"),
        note="This is the shape where separating inference from execution "
             "first pays off, and where monitoring starts to earn its keep.",
    ),
    Tier(
        key="cluster",
        name="Four machines",
        hardware="One inference host plus three RPC workers, as the existing "
                 "pages document",
        model_hint="Distribution is for escaping a spill, not for adding "
                   "bandwidth. Check the break-even condition before switching "
                   "a worker on.",
        stages=("foundation", "serve", "hands", "watch", "work"),
        note="The llama.cpp RPC guide and the monitoring pages are written "
             "for exactly this layout.",
    ),
]


# %% Companion repositories --------------------------------------------------
#: Related repositories by the same author, with what each one holds.  Facts
#: here were read from clones of each repository on 2026-10-20; repository
#: SETTINGS such as branch protection were not observable without an
#: authenticated API session and are deliberately not claimed.
COMPANIONS: List[Dict[str, str]] = [
    {
        "name": "RF_Equipment_Comms",
        "url": "https://github.com/Braveheart53/RF_Equipment_Comms",
        "summary": "Instrument communication and control: SCPI drivers, "
                   "signal-generator control and the USB/RS-232 adapter "
                   "drivers that go with them.",
        "relation": "The full version of the RS-232 bring-up script in this "
                    "repository.",
        "facts": "39 commits, GPL-2.0, 3 stale branches",
    },
    {
        "name": "FitsAutoPlot",
        "url": "https://github.com/Braveheart53/FitsAutoPlot",
        "summary": "FITS and Touchstone auto-plotting: S-parameter "
                   "processing, time gating, Smith charts, and native Veusz "
                   ".vszh5 HDF5 export.",
        "relation": "Shares the Veusz .vszh5 writing approach with the EMF "
                    "FFT analyzer here.",
        "facts": "301 commits, GPL-3.0, 13 branches",
    },
    {
        "name": "PowerLineRFI",
        "url": "https://github.com/Braveheart53/PowerLineRFI",
        "summary": "Power-line EMI and radio-telescope interference: "
                   "literature reference and site analysis.",
        "relation": "The interference side of the same EMF measurement work "
                    "the FFT analyzer here supports.",
        "facts": "3 commits, GPL-3.0, new as of 2026-10-18",
    },
]


# %% Helpers -----------------------------------------------------------------
def projects_in_stage(stage_key: str) -> List[Project]:
    """Return every project belonging to one stage, in catalogue order."""
    return [p for p in PROJECTS if p.stage == stage_key]


def stage_by_key(key: str) -> Stage:
    """Return the stage with the given key.

    Raises
    ------
    KeyError
        If no such stage exists.  Raising rather than returning None is
        deliberate: a typo in a page should stop the build.
    """
    for stage in STAGES:
        if stage.key == key:
            return stage
    raise KeyError(f"unknown stage {key!r}; known: {[s.key for s in STAGES]}")


def validate() -> None:
    """Fail loudly on an inconsistent inventory.

    Checks that every project's stage exists, that every ``needs`` entry names
    a real project path, that every tier references real stages, and that no
    field was written as pre-escaped HTML.

    Raises
    ------
    ValueError
        With a message naming every problem found, so one run fixes them all.
    """
    problems: List[str] = []

    stage_keys = {s.key for s in STAGES} | {"toolbox", "reference"}
    paths = {p.path for p in PROJECTS}

    for project in PROJECTS:
        if project.stage not in stage_keys:
            problems.append(
                f"{project.path}: unknown stage {project.stage!r}")
        for need in project.needs:
            if need not in paths:
                problems.append(
                    f"{project.path}: needs {need!r}, which is not a project")

    for tier in TIERS:
        for key in tier.stages:
            if key not in {s.key for s in STAGES}:
                problems.append(
                    f"tier {tier.key}: unknown stage {key!r}")

    # Pre-escaped HTML in a plain-text field renders literally, and no other
    # check in the build would catch it.
    entities = ("&amp;", "&lt;", "&gt;", "&quot;", "&mdash;", "&nbsp;")
    for project in PROJECTS:
        for field_name in ("name", "summary", "notes", "version"):
            value = getattr(project, field_name) or ""
            for entity in entities:
                if entity in value:
                    problems.append(
                        f"{project.path}.{field_name} contains {entity!r}; "
                        f"inventory strings are plain text")
    for stage in STAGES:
        for field_name in ("title", "goal", "why", "checkpoint"):
            value = getattr(stage, field_name) or ""
            for entity in entities:
                if entity in value:
                    problems.append(
                        f"stage {stage.key}.{field_name} contains {entity!r}")

    # Stage numbering must be contiguous from 0, so the page's "Stage N of M"
    # labels mean what they say.
    numbers = sorted(s.number for s in STAGES)
    if numbers != list(range(len(STAGES))):
        problems.append(f"stage numbers are not contiguous from 0: {numbers}")

    # Prose that names a stage by number must name a stage that EXISTS.
    #
    # A stricter rule was tried and removed: forbidding a stage from
    # referring forward to a later one. It flagged correct prose, because
    # stage 0's whole justification is what stage 2 will need from it, and a
    # flow whose stages cannot explain why they matter downstream is the
    # link-list this page exists to avoid. Forward references are the point.
    #
    # What a structural check CANNOT catch is the error this replaced: the
    # first draft said the C++ toolchain was for "stage 3" when compiling
    # happens in stage 2. Both numbers exist, so only reading finds that.
    # The check below is therefore the weaker, honest one.
    import re as _re
    valid_numbers = {s.number for s in STAGES}
    for stage in STAGES:
        prose = " ".join(
            [stage.goal, stage.why, stage.checkpoint]
            + [action for action, _where in stage.steps])
        for match in _re.finditer(r"\bstage (\d+)\b", prose, _re.IGNORECASE):
            referenced = int(match.group(1))
            if referenced not in valid_numbers:
                problems.append(
                    f"stage {stage.key} refers to stage {referenced}, "
                    f"which does not exist")

    if problems:
        raise ValueError("repo inventory problems:\n  " + "\n  ".join(problems))
