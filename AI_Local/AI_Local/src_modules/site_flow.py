# -*- coding: utf-8 -*-
"""
site_flow.py -- the ordered setup path through the AI_Local page set.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-11-15

PURPOSE
-------
The set grew page by page, and each page was written to stand alone.  What a
reader actually needs is an order: which page first, what must be true before
moving on, and where the alternatives are.  This module is that order, written
once, and every place that shows it is generated from here:

* the numbered path on ``index.html`` (the start page);
* the "Step k of N" bar and the previous / next panel on every page;
* Part I of the PDF reference manual.

A page that is not in :data:`STEPS` and not in :data:`REFERENCE_PAGES` gets no
step bar, and the build reports it, so a new page cannot be added without
deciding where it belongs.

TIERS
-----
The same three hardware tiers as the repository homepage:

    single   one machine runs the model, the UI and the build loop
    pair     a serving node plus one other machine
    cluster  three or more machines, usually with llama.cpp RPC
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# %% Constants ---------------------------------------------------------------
TIERS: Tuple[str, ...] = ("single", "pair", "cluster")

TIER_LABEL: Dict[str, str] = {
    "single": "One machine",
    "pair": "Two machines",
    "cluster": "Three or more",
}


# %% Data model --------------------------------------------------------------
@dataclass(frozen=True)
class Alternative:
    """A page that does the same step a different way.

    Attributes
    ----------
    page : str
        File name inside ``AI_Local/``.
    label : str
        Short name for the link.
    when : str
        One clause: when to choose it instead of the primary page.
    """

    page: str
    label: str
    when: str


@dataclass(frozen=True)
class Step:
    """One step on the setup path.

    Attributes
    ----------
    key : str
        Stable id; used as the ``#step-<key>`` anchor on the start page and by
        ``software_catalog.Program.steps``.
    title : str
        Imperative title.
    page : str
        The primary page for the step.
    goal : str
        What the reader has at the end of the step (HTML allowed).
    done_when : str
        A concrete, checkable condition (HTML allowed).
    time : str
        Rough effort, as a range.  An estimate, and labelled as one.
    applies : tuple of str
        Tiers the step applies to.
    optional_for : tuple of str
        Tiers for which the step is optional rather than required.
    alternatives : tuple of Alternative
        Other pages that do the same step another way.
    related : tuple of (page, label)
        Pages worth reading alongside, not instead.
    """

    key: str
    title: str
    page: str
    goal: str
    done_when: str
    time: str
    applies: Tuple[str, ...] = TIERS
    optional_for: Tuple[str, ...] = ()
    alternatives: Tuple[Alternative, ...] = ()
    related: Tuple[Tuple[str, str], ...] = ()


# %% The path ----------------------------------------------------------------
STEPS: List[Step] = [
    Step("software", "Gather the software", "downloads.html",
         "Every installer your GPU vendor and operating system need, from the "
         "original publisher, at a version this set was checked against.",
         '<span class="mono">git --version</span> and <span class="mono">mamba --version</span> '
         'answer, and on Windows <span class="mono">cl</span> answers from a Developer prompt.',
         "30&ndash;60 min, mostly downloading",
         related=(("gpu-configuration.html", "Which CUDA and Visual Studio versions to pair"),)),

    Step("gpu", "Match the GPU stack to the card", "gpu-configuration.html",
         "A driver, toolkit and compiler chosen for your card's architecture, and "
         "the runtime settings that decide how much of a model stays on the GPU.",
         '<span class="mono">nvidia-smi</span> (or Adrenalin) lists every card, and '
         '<span class="mono">ollama ps</span> shows a loaded model at '
         '<span class="mono">100% GPU</span>.',
         "30&ndash;90 min",
         related=(("ollama-model-selection.html", "How much memory a model and its cache take"),
                  ("llama-rpc-vulkan-guide.html", "Vulkan device selection across nodes"))),

    Step("model", "Choose a model that fits", "ollama-model-selection.html",
         "A model tag whose weights, cache and runtime reservation fit your card "
         "with room to spare, and the context length it can afford.",
         "The planner on the start page shows the tag fitting with at least 1&nbsp;GiB "
         "left for the key/value cache.",
         "15&ndash;30 min",
         related=(("gpu-configuration.html#kv", "Cache type and Flash Attention"),)),

    Step("serve", "Serve it on the network", "llama-rpc-vulkan-guide.html",
         "Ollama (and, for more than one machine, llama.cpp RPC workers) reachable "
         "from the network, with Open WebUI in front.",
         "Open WebUI answers from another machine; with RPC, the "
         '<span class="mono">llama-server</span> log lists every worker.',
         "1&ndash;3 h",
         related=(("gpu-configuration.html#multi", "Splitting a model across GPUs"),
                  ("ollama-model-selection.html", "When a model does not fit on one machine"))),

    Step("hands", "Give the model a place to build and test", "local-code-build-test.html",
         "An execution backend with your mamba environment and compilers, so the "
         "model can write, build and test C++ and Python against your own tools.",
         "The verification sequence on that page passes, including "
         "the blocked-egress test.",
         "1&ndash;2 h",
         alternatives=(
             Alternative("Jupyter_Server_Setup_wsl.html", "Jupyter in WSL 2 with micromamba",
                         "you want the Jupyter engine running directly in WSL"),
             Alternative("Dockler_Jupyter_withGPU_Passthru_nssm.html",
                         "Jupyter in Docker with GPU passthrough",
                         "you want the Jupyter engine in a container"),
         ),
         related=(("claude-sandbox-local-env.html", "Containing an agent that runs on the host"),
                  ("gpu-configuration.html#docker", "GPU inside containers"))),

    Step("boundary", "Decide what the agent may touch", "claude-sandbox-local-env.html",
         "An OS-enforced boundary for an agent that runs on the host rather than "
         "in a container: which folders it may write, which hosts it may reach.",
         "The sandbox reports enabled, and a write outside the allowed folders fails.",
         "30 min",
         optional_for=TIERS,
         related=(("local-code-build-test.html#security", "Blast radius of each backend"),)),

    Step("monitor", "Install Prometheus and Grafana", "Grafana_Prometheus_install_windows.html",
         "A Prometheus server scraping every node, and Grafana reading from it.",
         'Prometheus <span class="mono">/targets</span> shows every node '
         '<span class="mono">UP</span>.',
         "about 1 h",
         optional_for=("single",),
         alternatives=(
             Alternative("Grafan_Promethius_install_linux.html", "Linux install",
                         "the monitoring server runs Linux"),
         ),
         related=(("monitoring-sizing.html", "Disk cost of the retention you choose"),)),

    Step("gpu-metrics", "Export GPU metrics", "GPU_monitoring_setup.html",
         "Per-GPU utilisation, memory and temperature in Prometheus for every node.",
         "A utilisation series for every GPU appears in Prometheus.",
         "30&ndash;60 min",
         optional_for=("single",),
         related=(("gpu-configuration.html#monitor", "Which exporter works for which vendor"),)),

    Step("fleet", "Build the fleet dashboard", "Promethius_Grafana_windows11-llama-monitoring-tutorial.html",
         "One Grafana dashboard showing every node's host, GPU and "
         '<span class="mono">llama-server</span> metrics.',
         "The dashboard shows token rate, queue depth and GPU load per node.",
         "1&ndash;2 h",
         optional_for=("single",),
         related=(("monitoring-sizing.html#windows", "Why a panel goes blank"),)),

    Step("size", "Size retention and fix blank panels", "monitoring-sizing.html",
         "A retention window chosen from the disk it costs, and rate windows that "
         "do not leave panels empty.",
         "Disk use after a day matches the estimate, and no panel shows "
         '<span class="mono">No data</span> at your scrape interval.',
         "30 min",
         optional_for=("single",)),
]

#: Pages that are not steps.  Each gets a "reference" bar instead of a step bar.
REFERENCE_PAGES: Dict[str, str] = {
    "index.html": "Start page",
    "references.html": "Reference list",
    "CHANGELOG.html": "Version history",
    "Archive/Jupyter_Code_Eval_Setup.html": "Archived, superseded by step 5",
    "Archive/Windows_Exporter_Grafana_dashboard.html": "Archived, superseded by step 9",
}


# %% Helpers -----------------------------------------------------------------
def step_index(key: str) -> int:
    """Return the 1-based position of a step; raises ``KeyError`` on a typo."""
    for index, step in enumerate(STEPS, start=1):
        if step.key == key:
            return index
    raise KeyError(key)


def by_key(key: str) -> Step:
    """Return one step by key."""
    return STEPS[step_index(key) - 1]


def locate(page: str) -> Optional[Tuple[Step, str]]:
    """Find the step a page belongs to.

    Returns
    -------
    (Step, role) or None
        ``role`` is ``"primary"`` or ``"alternative"``.  ``None`` for a page
        that is not on the path.
    """
    for step in STEPS:
        if step.page == page:
            return step, "primary"
        if any(alt.page == page for alt in step.alternatives):
            return step, "alternative"
    return None


def neighbours(key: str) -> Tuple[Optional[Step], Optional[Step]]:
    """Return the (previous, next) steps around one step."""
    index = step_index(key) - 1
    previous = STEPS[index - 1] if index > 0 else None
    following = STEPS[index + 1] if index + 1 < len(STEPS) else None
    return previous, following


def all_pages() -> List[str]:
    """Every page the path names, primary and alternative, without duplicates."""
    pages: List[str] = []
    for step in STEPS:
        for page in [step.page] + [alt.page for alt in step.alternatives]:
            if page not in pages:
                pages.append(page)
    return pages


def validate(existing_pages: Optional[List[str]] = None) -> None:
    """Fail loudly on a malformed path.

    Parameters
    ----------
    existing_pages : list of str, optional
        File names that exist in the built set.  When given, every page the
        path names must be one of them, and every related link's page part
        must be one of them.

    Raises
    ------
    ValueError
        Naming the first problem.
    """
    keys = [step.key for step in STEPS]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate step keys")
    for step in STEPS:
        for tier in step.applies + step.optional_for:
            if tier not in TIERS:
                raise ValueError(f"step {step.key}: unknown tier {tier!r}")
    if existing_pages is None:
        return
    for step in STEPS:
        names = [step.page] + [a.page for a in step.alternatives] + \
                [target.split("#", 1)[0] for target, _label in step.related]
        for name in names:
            if name not in existing_pages:
                raise ValueError(f"step {step.key}: page {name!r} is not in the set")
