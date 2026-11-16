# -*- coding: utf-8 -*-
"""
page_start.py -- body of AI_Local/index.html, the start page of the set.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-11-15

PURPOSE
-------
The start page brings the set together in the order a reader needs it:

1. *Your setup*: the hardware tier, which dims the steps that do not apply;
2. *The setup path*: the ten steps of ``site_flow.STEPS``, each with its
   goal, a checkable "done when", the programs it needs, and the page that
   does it (plus alternatives);
3. *Will it fit?*: the VRAM planner, shared with the repository homepage;
4. *Every page*: the catalogue, grouped;
5. *Conventions*: how to read the set.

INTERACTIVITY
-------------
The tier selector, the step checkboxes with their progress bar, and the
planner are driven by ``assets/home.js``, which wires each feature only when
its markup is present.  So this module emits markup in the same classes the
repository homepage uses (``.tier``, ``.stage``, ``.stage-done``,
``.progress-*``) and adds no script of its own.  Nothing is stored in the
browser: progress resets on reload, by design.

The page is fully readable with scripts disabled: every step is plain HTML,
and the interactive parts only dim, tick and compute.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import html
from typing import List

import page_home
import page_meta
import site_flow
import software_catalog as sw

# %% Helpers -----------------------------------------------------------------
def _applies_chips(step: site_flow.Step) -> str:
    """Small tier chips; an optional tier is marked as such."""
    chips = []
    for tier in site_flow.TIERS:
        if tier not in step.applies:
            continue
        label = site_flow.TIER_LABEL[tier]
        if tier in step.optional_for:
            label += " (optional)"
        chips.append(f'<li><span class="xs">{label}</span></li>')
    return '<ul class="inline-list">' + "".join(chips) + "</ul>"


def _software_links(step: site_flow.Step) -> str:
    """Links into downloads.html for the programs this step needs."""
    programs = sw.for_step(step.key)
    if not programs:
        return ""
    links = ", ".join(f'<a href="downloads.html#sw-{p.key}">{p.name}</a>' for p in programs)
    return (f'<div class="stage-projects"><h4 class="xs">Software for this step</h4>'
            f'<p class="small">{links}</p></div>')


def _stage(index: int, step: site_flow.Step) -> str:
    """One step as a .stage article, in the markup home.js expects."""
    previous, following = site_flow.neighbours(step.key)
    alternatives = ""
    if step.alternatives:
        items = "".join(
            f'<li><a href="{alt.page}">{alt.label}</a> <span class="small muted">&mdash; if {alt.when}</span></li>'
            for alt in step.alternatives)
        alternatives = f'<p class="small"><strong>Alternatives:</strong></p><ul class="small">{items}</ul>'
    related = ""
    if step.related:
        items = "".join(f'<li><a href="{target}">{label}</a></li>' for target, label in step.related)
        related = f'<p class="small"><strong>Read alongside:</strong></p><ul class="small">{items}</ul>'
    next_line = (f'<p class="stage-next small muted">When the check passes, go to '
                 f'<a href="#step-{following.key}">step {index + 1}, {following.title[:1].lower() + following.title[1:]}</a>.</p>'
                 if following else
                 '<p class="stage-next small muted">That completes the path. The '
                 '<a href="references.html">reference list</a> and <a href="CHANGELOG.html">change log</a> '
                 'cover the whole set.</p>')
    applies = " ".join(step.applies)
    return f"""
  <article class="stage" id="step-{step.key}" data-applies="{applies}">
    <header class="stage-head">
      <div class="stage-num" aria-hidden="true">{index}</div>
      <div class="stage-title-wrap">
        <h3 class="stage-title">{step.title}</h3>
        <p class="stage-goal">{step.goal}</p>
      </div>
      <label class="stage-done">
        <input type="checkbox" data-stage="{step.key}">
        <span>Done</span>
      </label>
    </header>
    <div class="stage-body">
      <p><a class="btn-copy" href="{step.page}">Open the page for this step &rarr;</a></p>
      {alternatives}
      {related}
      {_software_links(step)}
      <div class="stage-foot">
        <p class="stage-check"><strong>Done when:</strong> {step.done_when}</p>
        <p class="stage-time xs faint">Typical time: {step.time} (an estimate)</p>
        {_applies_chips(step)}
      </div>
      {next_line}
    </div>
  </article>"""


# %% Sections ----------------------------------------------------------------
def _hero(version: str) -> str:
    return f"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">AI_Local &middot; v{version} &middot; Start here</div>
    <h1>Running AI on your own hardware, end to end</h1>
    <p class="lead">A working set for deploying language models across a home or lab network: choosing the hardware path, serving models on one machine or several, letting a model write, build and test code on machines you own, and monitoring what the hardware is doing. Follow the ten numbered steps below in order; each one ends with a check that tells you it worked.</p>
    <p class="small muted">Scientific and code-building work is the focus. Every page cites its sources to a numbered row in <a href="references.html">one reference table</a>, every equation carries a variable table with units, and every figure that is an estimate rather than a citation says so.</p>
  </div>
</section>
"""


def _your_setup() -> str:
    """Tier selector in the same markup as the repository homepage."""
    hardware = {
        "single": "A single desktop or laptop with one GPU",
        "pair": "A serving machine plus one other machine",
        "cluster": "An inference host plus llama.cpp RPC workers",
    }
    buttons = []
    for tier in site_flow.TIERS:
        steps = [str(i) for i, s in enumerate(site_flow.STEPS, start=1)
                 if tier in s.applies and tier not in s.optional_for]
        buttons.append(f"""      <button class="tier" type="button" data-tier="{tier}" aria-pressed="false">
        <span class="tier-name">{site_flow.TIER_LABEL[tier]}</span>
        <span class="tier-hw small muted">{hardware[tier]}</span>
        <span class="tier-stages xs faint">Required steps: {", ".join(steps)}</span>
      </button>""")
    notes = {
        "single": "On one machine, monitoring (steps 7&ndash;10) is optional: <span class=\"mono\">ollama ps</span> answers the question a dashboard would. Steps 1&ndash;5 are the whole job.",
        "pair": "With two machines, the monitoring steps earn their place: they are how you see that the second machine is actually being used.",
        "cluster": "With RPC workers, build llama.cpp on every node for its own card (step 2 explains why mixed generations need different CUDA versions), and do every monitoring step.",
    }
    note_html = "\n".join(
        f'      <div class="tier-note" data-tier-note="{t}" hidden><p>{notes[t]}</p></div>'
        for t in site_flow.TIERS)
    return f"""
<section id="your-setup">
  <div class="container">
    <h2>Your setup</h2>
    <p>Pick the closest shape. Steps that do not apply are dimmed rather than hidden, so you can see what you are skipping.</p>
    <div class="tier-grid">
{chr(10).join(buttons)}
    </div>
    <div id="tier-notes">
{note_html}
      <div class="tier-note" data-tier-note="none"><p class="small muted">No setup chosen: every step is shown.</p></div>
    </div>
    <p class="small">GPU vendor shortcuts: <a href="gpu-configuration.html#nvidia-matrix">NVIDIA</a> &middot; <a href="gpu-configuration.html#amd">AMD</a> &middot; <a href="gpu-configuration.html#intel-apple">Intel and Apple</a> &middot; <a href="gpu-configuration.html#vulkan">any vendor through Vulkan</a></p>
  </div>
</section>
"""


def _path() -> str:
    """The ten steps, with the shared progress bar."""
    total = len(site_flow.STEPS)
    stages = "\n".join(_stage(i, s) for i, s in enumerate(site_flow.STEPS, start=1))
    return f"""
<section id="path">
  <div class="container">
    <h2>The setup path</h2>
    <p>Each step produces what the next one needs, so the order is a dependency chain rather than a preference. If a step's check does not pass, the next step will fail in a way that is harder to diagnose.</p>
    <div class="progress-wrap">
      <div class="progress-bar" role="progressbar" aria-valuemin="0" aria-valuemax="{total}" aria-valuenow="0" aria-label="Steps completed">
        <div class="progress-fill" style="width:0%"></div>
      </div>
      <div class="progress-row">
        <span class="progress-text small muted">0 of {total} stages marked done</span>
        <button type="button" class="btn-copy" id="copy-progress">Copy progress</button>
      </div>
      <p class="xs faint">Progress is held in this page only and resets when you reload. Nothing is written to browser storage.</p>
    </div>
    <div class="stages">
{stages}
    </div>
  </div>
</section>
"""


def _planner() -> str:
    """The VRAM planner, reused from the repository homepage.

    Its links are written relative to the repository root; inside AI_Local/
    the ``AI_Local/`` prefix is removed so they resolve.
    """
    markup = page_home._calculator()
    markup = markup.replace('href="AI_Local/', 'href="')
    return markup


def _catalogue(manifest) -> str:
    """Every page, grouped, as cards."""
    order = [
        ("setup", "Setup and hardware", "The first two steps: what to install, and how to match it to the card."),
        ("build", "Local code generation and testing", "Giving a model a shell, a compiler and your Python environment, and choosing the model."),
        ("inference", "Serving the model", "Getting a model answering on the network, across several machines when it will not fit on one."),
        ("monitoring", "Monitoring", "Knowing what the hardware is doing while it serves."),
        ("meta", "Reference", "Sources and revision history for the whole set."),
    ]
    sections: List[str] = []
    for key, heading, intro in order:
        cards = []
        for spec in manifest:
            if spec.group != key or not spec.in_nav or spec.filename == "index.html":
                continue
            located = site_flow.locate(spec.filename)
            kicker = html.escape(spec.nav_label)
            if located:
                kicker = f"Step {site_flow.step_index(located[0].key)} &middot; " + kicker
            badge = '<span class="badge new">new</span> ' if spec.is_new else ""
            cards.append(f'      <a class="card" href="{spec.filename}">\n'
                         f'        <span class="card-kicker">{badge}{kicker}</span>\n'
                         f'        <h3>{html.escape(spec.title)}</h3>\n'
                         f'        <p class="small muted">{html.escape(spec.blurb)}</p>\n'
                         f'      </a>')
        if cards:
            sections.append(f'<section id="g-{key}">\n  <div class="container">\n'
                            f'    <h2>{heading}</h2>\n    <p>{intro}</p>\n'
                            f'    <div class="card-grid">\n' + "\n".join(cards) +
                            '\n    </div>\n  </div>\n</section>')
    return '\n<div id="every-page"></div>\n' + "\n".join(sections)


def _conventions(manifest) -> str:
    """The conventions section, taken from page_meta so it is written once."""
    full = page_meta.build_index(manifest)
    start = full.find('<section id="conventions">')
    return full[start:] if start >= 0 else ""


# %% Entry point -------------------------------------------------------------
def build(manifest, version: str) -> str:
    """Return the body fragment of AI_Local/index.html."""
    sw.validate()
    return "".join([_hero(version), _your_setup(), _path(), _planner(),
                    _catalogue(manifest), _conventions(manifest)])
