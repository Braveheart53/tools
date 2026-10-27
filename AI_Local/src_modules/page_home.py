# -*- coding: utf-8 -*-
"""
page_home.py -- body content for the repository-root index.html

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-20

PURPOSE
-------
Generates the overarching homepage that sits at the root of the
Braveheart53/tools repository and ties every part of it into one
implementation flow.

WHAT MAKES IT COHERENT RATHER THAN A LINK LIST
----------------------------------------------
A homepage that just lists fourteen directories is a table of contents, not an
integration.  This page is organised around the one structural fact that makes
the repository a whole rather than a pile:

    everything in it either builds the Py3p12 mamba environment,
    runs inside it, or documents the physics behind something that does.

That gives a five-stage flow -- foundation, serve, hands, watch, work -- where
each stage's output is the next stage's prerequisite, and where every project
in the repository has a place.  ``repo_inventory.py`` holds that structure as
data; this module renders it.

The page is generated, not hand-written, so the catalogue cannot drift out of
step with the flow: a project added to ``PROJECTS`` appears in its stage AND
in the toolbox table AND in the repository map, with no second edit.

INTERACTION
-----------
Three interactive pieces, all vanilla JavaScript, all inert without it:

1.  A hardware-tier selector.  The stated goal of this work is an instruction
    set for a variety of hardware setups, so the reader picks their shape and
    the flow dims the stages that do not apply to it.
2.  A progress tracker across the stages, with a copyable text summary.
3.  A model planner and fit calculator, which are ONE tool rather than two:
    the reader enters their VRAM once, the planner names the models that fit
    it, and choosing one loads its published figures into the calculator so
    the context budget is evaluated for that actual tag.  Splitting them
    would make the reader retype a number they had already given, and would
    invite the two halves to disagree about what "fits" means.

    Both halves read ``model_catalog.py``, which is also what
    ``ollama-model-selection.html`` is checked against, so the planner cannot
    recommend a tag at a size the prose table does not state.  The build
    enforces that with ``verify_catalog_consistency()``.

NO BROWSER STORAGE is used, consistent with the rest of this page set: the
pages are opened from local disk and sometimes inside sandboxed frames where
storage access throws.  The progress tracker is therefore in-memory, and the
copy button exists precisely because of that -- see the comment on it in the
script.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import html
from typing import List

import model_catalog as cat
import repo_inventory as inv


# %% Small rendering helpers -------------------------------------------------
def _esc(text: str) -> str:
    """Escape a plain-text inventory string for safe inclusion in HTML.

    Every string in ``repo_inventory`` is plain text by contract, so each one
    passes through here exactly once.  Centralising it means a future field is
    escaped by default rather than by remembering.
    """
    return html.escape(text, quote=True)


def _doc_path(project, doc: str) -> str:
    """Resolve a project's documentation entry to a repository-relative path.

    ``Project.path`` is a directory for most entries but a file for a few
    single-script tools.  A doc listed against a file-path project is already
    repository-relative and must not be joined onto that file, which would
    produce something like ``Inventor_Parameter_XML2XLSX.py/Example.xml``.

    Parameters
    ----------
    project : repo_inventory.Project
        The project the doc belongs to.
    doc : str
        The doc entry as written in the inventory.

    Returns
    -------
    str
        A path relative to the repository root.
    """
    # The heuristic is deliberately narrow: a project path with a recognised
    # script or document extension is a file, everything else is a directory.
    # Guessing by probing the filesystem is not available here, because this
    # module runs without the repository tree beside it.
    file_suffixes = (".py", ".ps1", ".sh", ".md", ".zip", ".7z",
                     ".yml", ".yaml", ".json", ".xml")
    if project.path.lower().endswith(file_suffixes):
        return doc
    return f"{project.path}/{doc}"


def _path_link(path: str, label: str = "") -> str:
    """Render a repository path as a link, relative to the repository root.

    Parameters
    ----------
    path
        Path relative to the repository root, exactly as it appears on disk.
        May carry a ``#fragment``.
    label
        Link text.  Defaults to the path itself, which is usually what a
        reader wants to see.

    Returns
    -------
    str
        An anchor element, or a plain code span when the target is an archive
        or a binary that a browser cannot usefully open.
    """
    shown = _esc(label or path)

    # An href has to be URL-escaped where a path contains spaces or an
    # em dash; html.escape alone is not enough for the attribute value.
    href = (path.replace("%", "%25")
                .replace(" ", "%20")
                .replace("—", "%E2%80%94"))

    # Archives and installers are not browsable. Showing them as a link that
    # downloads a 20 MB zip when clicked is worse than showing the path.
    if path.rsplit("#", 1)[0].lower().endswith((".zip", ".7z", ".msi", ".exe")):
        return f'<span class="mono">{shown}</span>'

    return f'<a class="mono" href="{href}">{shown}</a>'


# %% Section builders --------------------------------------------------------
def _hero() -> str:
    """Hero section: what the repository is, in one screen."""
    n_projects = len(inv.PROJECTS)
    n_stages = len(inv.STAGES)
    return f"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">Braveheart53 / tools &middot; v{_esc(inv.HOME_VERSION)}</div>
    <h1>Local AI, and the engineering work it is for</h1>
    <p class="lead">This repository is a working set for deploying language models across your own hardware and then pointing them at real engineering code. It is not a collection of unrelated utilities: everything in it either builds one Python environment, runs inside that environment, or documents the physics behind something that does.</p>
    <p>That single fact is what the page below is organised around. {n_stages} stages take you from an empty machine to a model that writes, compiles and tests code in your environment, and every one of the {n_projects} projects in this repository has a place in that sequence.</p>
    <div class="callout info-box">
      <p><strong>If you only read one thing:</strong> do <a href="#stage-foundation">stage 0</a> before anything else. Every Python tool here is written against one named mamba environment, and the local model in <a href="#stage-hands">stage 2</a> is explicitly told to use it. Skipping it produces a model that reports libraries are missing when it is simply looking at the wrong interpreter, and that failure is tedious to diagnose from the other end.</p>
    </div>
  </div>
</section>
"""


def _tier_selector() -> str:
    """Hardware tier selector: adapts the flow to the reader's machines."""
    cards: List[str] = []
    for tier in inv.TIERS:
        stage_list = ", ".join(
            str(inv.stage_by_key(k).number) for k in tier.stages)
        cards.append(f"""
      <button class="tier" type="button" data-tier="{_esc(tier.key)}"
              aria-pressed="false">
        <span class="tier-name">{_esc(tier.name)}</span>
        <span class="tier-hw small muted">{_esc(tier.hardware)}</span>
        <span class="tier-stages xs faint">Stages {stage_list}</span>
      </button>""")

    notes: List[str] = []
    for tier in inv.TIERS:
        notes.append(f"""
      <div class="tier-note" data-tier-note="{_esc(tier.key)}" hidden>
        <p><strong>{_esc(tier.name)}.</strong> {_esc(tier.note)}</p>
        <p class="small muted"><strong>Model sizing:</strong> {_esc(tier.model_hint)}</p>
      </div>""")

    return f"""
<section id="your-setup">
  <div class="container">
    <h2>1. Start with what you have</h2>
    <p>The flow below adapts to the hardware you are working with. Pick the closest shape; stages that do not apply to it are dimmed rather than hidden, so you can still see what you are skipping and why.</p>

    <div class="tier-grid">{''.join(cards)}
    </div>

    <div id="tier-notes">{''.join(notes)}
      <div class="tier-note" data-tier-note="none">
        <p class="small muted">No shape selected, so every stage is shown. Choosing one dims the stages it does not need.</p>
      </div>
    </div>
  </div>
</section>
"""


def _flow() -> str:
    """The staged implementation flow: the spine of the page."""
    blocks: List[str] = []
    total = len(inv.STAGES)

    for index, stage in enumerate(inv.STAGES):
        # Steps are numbered within the stage, with their link target shown so
        # a reader can see where they are being sent before clicking.
        steps = []
        for action, where in stage.steps:
            target = _path_link(where) if where else ""
            steps.append(
                f'        <li>{_esc(action)}'
                + (f'<br><span class="step-where">{target}</span>'
                   if target else "")
                + "</li>")

        # Which tiers this stage applies to, as data attributes the selector
        # reads. Written as a space-separated list so a CSS/JS match is a
        # simple token test.
        applies = " ".join(stage.applies_to)

        # Projects that belong to this stage, shown as a compact strip so the
        # catalogue and the flow cannot disagree about what is in each stage.
        owned = inv.projects_in_stage(stage.key)
        project_strip = ""
        if owned:
            items = "".join(
                f'<li>{_path_link(p.path, p.name)}'
                + (f' <span class="xs faint">v{_esc(p.version)}</span>'
                   if p.version else "")
                + "</li>"
                for p in owned)
            project_strip = (
                '      <div class="stage-projects">\n'
                '        <h4 class="xs">In this repository</h4>\n'
                f'        <ul class="inline-list">{items}</ul>\n'
                "      </div>\n")

        next_hint = ""
        if index + 1 < total:
            nxt = inv.STAGES[index + 1]
            next_hint = (
                f'      <p class="stage-next small muted">Once the checkpoint '
                f'passes, go to <a href="#stage-{_esc(nxt.key)}">stage '
                f'{nxt.number}, {_esc(nxt.title.lower())}</a>.</p>\n')

        blocks.append(f"""
  <article class="stage" id="stage-{_esc(stage.key)}" data-applies="{applies}">
    <header class="stage-head">
      <div class="stage-num" aria-hidden="true">{stage.number}</div>
      <div class="stage-title-wrap">
        <h3 class="stage-title">{_esc(stage.title)}</h3>
        <p class="stage-goal">{_esc(stage.goal)}</p>
      </div>
      <label class="stage-done">
        <input type="checkbox" data-stage="{_esc(stage.key)}">
        <span>Done</span>
      </label>
    </header>

    <div class="stage-body">
      <p class="stage-why"><strong>Why here:</strong> {_esc(stage.why)}</p>

      <ol class="stage-steps">
{chr(10).join(steps)}
      </ol>

{project_strip}      <div class="stage-foot">
        <p class="stage-check"><strong>Checkpoint.</strong> <span class="mono">{_esc(stage.checkpoint)}</span></p>
        <p class="stage-time xs faint">Typical time: {_esc(stage.time)}</p>
      </div>
{next_hint}    </div>
  </article>""")

    return f"""
<section id="flow">
  <div class="container">
    <h2>2. The implementation flow</h2>
    <p>Each stage produces the thing the next one needs, so the order is a dependency chain rather than a preference. Every stage ends with a checkpoint that is a command or an observation, not a feeling &mdash; if the checkpoint does not pass, the next stage will fail in a way that is harder to diagnose.</p>

    <div class="progress-wrap">
      <div class="progress-bar" role="progressbar" aria-valuemin="0"
           aria-valuemax="{total}" aria-valuenow="0"
           aria-label="Stages completed">
        <div class="progress-fill" style="width:0%"></div>
      </div>
      <div class="progress-row">
        <span class="progress-text small muted">0 of {total} stages marked done</span>
        <button type="button" class="btn-copy" id="copy-progress">Copy progress</button>
      </div>
      <p class="xs faint">Progress is held in this page only and resets when you reload. Nothing here writes to browser storage, because these pages are opened from local disk and sometimes inside sandboxed frames where storage access throws. Use <em>Copy progress</em> to paste a snapshot into your own notes.</p>
    </div>

    <div class="stages">{''.join(blocks)}
    </div>
  </div>
</section>
"""


def _calculator() -> str:
    """Model planner and live fit calculator, sharing one VRAM figure.

    The planner lists what fits the reader's card; the calculator evaluates
    the context-budget relation for whichever model they pick.  Both read the
    catalogue emitted below, which is the same module
    ``ollama-model-selection.html`` is verified against, so a tag can never
    be recommended here at a size the prose table does not state.

    Returns
    -------
    str
        The complete ``#fit`` section, with the catalogue JSON substituted
        into its data island.
    """
    # Substituted rather than interpolated: the body is a raw string full of
    # LaTeX braces, which an f-string would try to read as fields.
    return _FIT_SECTION.replace("__CATALOG_JSON__", cat.as_javascript())


_FIT_SECTION = r"""
<section id="fit">
  <div class="container">
    <h2>3. Which model, and will it fit?</h2>

    <p>Stage 1 turns on two questions that have to be answered together: which model to run, and whether your card can actually hold it. Reading someone else&rsquo;s worked example is a poor substitute for either, so both are evaluated here against your own hardware. The arithmetic is the same as the <a href="AI_Local/ollama-model-selection.html#fit">model selection page</a>, which shows every derivation; the figures are the same ones that page cites, because both are generated from one catalogue.</p>

    <!-- ===================================================================
         PLANNER

         One VRAM input drives both halves of this section. The planner
         names what fits; choosing a model loads its published size into the
         calculator below, so the reader never retypes a number they have
         already given and the two halves cannot disagree about it.

         The catalogue is baked into the page at build time (see
         window.AILocalCatalog in home.js) rather than fetched, because
         these pages open from local disk with no network access.
         =================================================================== -->
    <form class="planner" id="planner" autocomplete="off">
      <div class="planner-head">
        <label for="p-vram"><strong>How much VRAM does the card have?</strong>
          <span class="calc-unit">GB</span>
        </label>
        <input type="number" id="p-vram" value="24" min="2" max="192" step="1"
               aria-describedby="p-note">
      </div>
      <p class="small muted" id="p-note">A model &ldquo;fits&rdquo; here when its weight file, the runtime reservation and at least 1&nbsp;GB of cache all sit on the card. A model that is technically resident but cannot hold a useful prompt is not a fit.</p>
      <div class="planner-out" id="planner-out" role="status" aria-live="polite"></div>
    </form>

    <div class="eq" id="eq-fit-live">
      <div class="eq-head">
        <h3 class="eq-title">Context a card can hold, once weights and runtime are placed</h3>
        <div class="eq-tools"><span class="pill derived">Derived here</span>
          <button class="info" aria-controls="v-fit-live" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
      </div>
      <div class="eq-body">\[ L_{\max} \;=\; \left\lfloor \frac{V_{\text{tot}} - S_{w} - V_{\text{rt}}}{2\,n_{\ell}\,n_{kv}\,d_{h}\,n_{\text{seq}}\,b_{kv}} \right\rfloor \]</div>
      <p class="eq-note">The window a model page advertises is what its weights were trained to attend over. This is what your hardware can allocate, which is the number that constrains your work.</p>
      <div class="deriv"><ol>
        <li>Autoregressive attention caches one key vector and one value vector per token per layer, so one token of context costs \( 2\,n_{\ell}\,n_{kv}\,d_{h}\,b_{kv} \) bytes, times \( n_{\text{seq}} \) for concurrent sequences that each keep their own cache.</li>
        <li>The cache shares the device with the weights \( S_{w} \) and the runtime's own allocations \( V_{\text{rt}} \), so the bytes available to it are \( V_{\text{tot}} - S_{w} - V_{\text{rt}} \).</li>
        <li>Divide the remainder by the per-token cost and take the floor, since a partial token cannot be cached.</li>
        <li>Treat the result as an upper bound. Allocators fragment, and on Windows the display driver can page VRAM out from under the runtime.</li>
        <li>Each step above is worked in full, with the intermediate forms, on the <a href="AI_Local/ollama-model-selection.html#eq-ctx-budget">model selection page</a>.</li>
      </ol></div>
      <div class="vars" id="v-fit-live" hidden><div class="table-wrap"><table>
        <caption>Symbols in the context-budget relation. Read the architectural quantities from <span class="mono">ollama show &lt;tag&gt;</span>; the defaults below are a plausible shape for a 30B-class model and are not a measurement.</caption>
        <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
        <tbody>
          <tr><td>\(L_{\max}\)</td><td>Largest context that fits once weights and runtime are placed</td><td>token</td></tr>
          <tr><td>\(V_{\text{tot}}\)</td><td>Total device memory on the accelerator</td><td>B</td></tr>
          <tr><td>\(S_{w}\)</td><td>Weight footprint, the size the model tag lists</td><td>B</td></tr>
          <tr><td>\(V_{\text{rt}}\)</td><td>Runtime, driver and compute-buffer reservation</td><td>B</td></tr>
          <tr><td>\(n_{\ell}\)</td><td>Transformer layers</td><td>dimensionless</td></tr>
          <tr><td>\(n_{kv}\)</td><td>Key/value heads per layer</td><td>dimensionless</td></tr>
          <tr><td>\(d_{h}\)</td><td>Head dimension</td><td>dimensionless</td></tr>
          <tr><td>\(n_{\text{seq}}\)</td><td>Concurrent sequences, <span class="mono">--parallel</span> or <span class="mono">OLLAMA_NUM_PARALLEL</span></td><td>dimensionless</td></tr>
          <tr><td>\(b_{kv}\)</td><td>Bytes per cached element, set by <span class="mono">OLLAMA_KV_CACHE_TYPE</span></td><td>B</td></tr>
        </tbody>
      </table></div></div>
    </div>

    <form class="calc" id="fit-calc" autocomplete="off">
      <div class="calc-grid">
        <label>Card VRAM, \(V_{\text{tot}}\)
          <span class="calc-unit">GB</span>
          <input type="number" id="c-vram" value="24" min="2" max="192" step="1">
        </label>
        <label>Model size, \(S_{w}\)
          <span class="calc-unit">GB</span>
          <input type="number" id="c-weights" value="15" min="0.3" max="400" step="0.1">
        </label>
        <label>Runtime reserve, \(V_{\text{rt}}\)
          <span class="calc-unit">GB</span>
          <input type="number" id="c-runtime" value="1.2" min="0" max="8" step="0.1">
        </label>
        <label>Layers, \(n_{\ell}\)
          <span class="calc-unit">count</span>
          <input type="number" id="c-layers" value="48" min="1" max="200" step="1">
        </label>
        <label>KV heads, \(n_{kv}\)
          <span class="calc-unit">count</span>
          <input type="number" id="c-kvheads" value="8" min="1" max="128" step="1">
        </label>
        <label>Head dim, \(d_{h}\)
          <span class="calc-unit">count</span>
          <input type="number" id="c-headdim" value="128" min="8" max="512" step="8">
        </label>
        <label>Concurrent, \(n_{\text{seq}}\)
          <span class="calc-unit">count</span>
          <input type="number" id="c-parallel" value="1" min="1" max="16" step="1">
        </label>
        <label>Cache type, \(b_{kv}\)
          <span class="calc-unit">bytes</span>
          <select id="c-kvtype">
            <option value="2" selected>f16 (2 B, default)</option>
            <option value="1">q8_0 (1 B)</option>
            <option value="0.5">q4_0 (0.5 B)</option>
          </select>
        </label>
      </div>

      <output class="calc-out" id="calc-out" for="c-vram c-weights c-runtime c-layers c-kvheads c-headdim c-parallel c-kvtype"></output>
    </form>

    <!-- The model catalogue, emitted from model_catalog.py at build time.
         application/json rather than a <script> that assigns a global: the
         browser does not execute it, so the page carries no inline
         executable code and the content-security story stays simple. -->
    <script type="application/json" id="model-catalog">__CATALOG_JSON__</script>

    <div class="callout">
      <p><strong>The bandwidth cliff is the thing this is protecting you from.</strong> If the result is negative, the weights do not fit and llama.cpp or Ollama will place some layers in system RAM. The same weight set streams roughly nine times slower from system RAM than from VRAM, so a smaller model fully resident beats a larger one that spills &mdash; essentially always. Confirm residency with <span class="mono">ollama ps</span> rather than assuming it.</p>
    </div>
  </div>
</section>
"""


def _toolbox() -> str:
    """The catalogue: every project, with what it needs to run."""
    def table_for(stage_key: str, caption: str) -> str:
        rows = []
        for p in inv.projects_in_stage(stage_key):
            entry = (f'<span class="mono">{_esc(p.entry)}</span>'
                     if p.entry else '<span class="faint">&mdash;</span>')
            version = (f'<span class="mono">{_esc(p.version)}</span>'
                       if p.version else '<span class="faint">&mdash;</span>')
            env = {
                "Py3p12": '<span class="badge high">Py3p12</span>',
                "own": '<span class="badge medium">own env</span>',
                "none": '<span class="badge">no Python</span>',
                "creates it": '<span class="badge new">creates it</span>',
            }.get(p.environment, _esc(p.environment))

            # A project's path may be a FILE rather than a directory
            # (Inventor_Parameter_XML2XLSX.py, for instance). Joining a doc
            # onto a file path produces a path that cannot exist, so a doc
            # is resolved against the project directory only when the
            # project IS a directory; otherwise it is already repo-relative.
            docs = " ".join(
                _path_link(_doc_path(p, d), d.split("/")[-1])
                for d in p.docs) if p.docs else ""

            rows.append(
                "<tr>"
                f'<td>{_path_link(p.path, p.name)}<div class="xs faint">{_esc(p.path)}</div></td>'
                f"<td>{version}</td>"
                f"<td>{_esc(p.language)}</td>"
                f"<td>{entry}</td>"
                f"<td>{env}</td>"
                f'<td class="small">{_esc(p.summary)}'
                + (f'<div class="xs muted" style="margin-top:.35rem">{_esc(p.notes)}</div>'
                   if p.notes else "")
                + (f'<div class="xs" style="margin-top:.35rem">{docs}</div>'
                   if docs else "")
                + "</td>"
                "</tr>")

        return (
            '    <div class="table-wrap"><table>\n'
            f"      <caption>{caption}</caption>\n"
            '      <thead><tr><th scope="col">Project</th><th scope="col">Version</th>'
            '<th scope="col">Language</th><th scope="col">Entry point</th>'
            '<th scope="col">Environment</th><th scope="col">What it does</th></tr></thead>\n'
            f"      <tbody>{''.join(rows)}</tbody>\n"
            "    </table></div>\n")

    return f"""
<section id="toolbox">
  <div class="container-wide">
    <h2>4. The toolbox</h2>
    <p>What actually runs once the foundation is in place. The <strong>Environment</strong> column is the one to read first: <span class="badge high">Py3p12</span> means the shared environment from stage 0, <span class="badge medium">own env</span> means the project ships its own YAML and can be installed standalone, and <span class="badge">no Python</span> means it needs something else entirely.</p>

{table_for("toolbox", "Engineering and instrumentation tools in this repository, with the entry point and environment each one needs. Versions are as each project's own README or module header states them, read on " + _esc(inv.SURVEYED) + ".")}

    <h3>Reference material</h3>
    <p>The physics and signal processing behind the tools above. The Atomic Theory Atlas is also the source of the equation and variable-definition pattern used throughout the AI_Local pages.</p>

{table_for("reference", "Educational and reference material. The archives are page sets: unpack one and open its index.html.")}
  </div>
</section>
"""


def _companions() -> str:
    """Related repositories, with what each holds and how it connects."""
    rows = []
    for c in inv.COMPANIONS:
        rows.append(
            "<tr>"
            f'<td><a href="{_esc(c["url"])}" target="_blank" '
            f'rel="noopener noreferrer">{_esc(c["name"])}</a></td>'
            f'<td class="small">{_esc(c["summary"])}</td>'
            f'<td class="small">{_esc(c["relation"])}</td>'
            f'<td class="xs faint">{_esc(c["facts"])}</td>'
            "</tr>")

    return f"""
<section id="companions">
  <div class="container">
    <h2>5. Companion repositories</h2>
    <p>Three related repositories by the same author. They are separate because they have separate lifecycles, but they share conventions with this one &mdash; the Veusz <span class="mono">.vszh5</span> writing approach in particular appears in three of the four.</p>

    <div class="table-wrap"><table>
      <caption>Related repositories, with how each connects to the work here. Commit counts and licences were read from clones on {_esc(inv.SURVEYED)}.</caption>
      <thead><tr><th scope="col">Repository</th><th scope="col">Holds</th><th scope="col">Connection</th><th scope="col">As of {_esc(inv.SURVEYED)}</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>

    <div class="callout">
      <p><strong>Licence mismatch worth knowing about.</strong> <span class="mono">RF_Equipment_Comms</span> is GPL-2.0 while <span class="mono">FitsAutoPlot</span> and <span class="mono">PowerLineRFI</span> are GPL-3.0. GPL-2.0-only code cannot be combined with GPL-3.0 code, so if a module is ever shared between them that is a real conflict rather than a paperwork detail. This repository currently carries no licence at all, which means default copyright: nobody may legally reuse it.</p>
    </div>
  </div>
</section>
"""


def _map() -> str:
    """A directory map, so the repository can be navigated without this page."""
    rows = []
    seen = set()
    for p in inv.PROJECTS:
        top = p.path.split("/")[0]
        if top in seen:
            continue
        seen.add(top)
        stage = p.stage
        stage_label = {
            "toolbox": "Toolbox",
            "reference": "Reference",
        }.get(stage) or f"Stage {inv.stage_by_key(stage).number}"
        rows.append(
            "<tr>"
            f"<td>{_path_link(top)}</td>"
            f"<td>{stage_label}</td>"
            f'<td class="small">{_esc(p.name)}</td>'
            "</tr>")

    # Directories that hold no catalogued project but exist in the tree, so
    # the map is complete rather than merely representative.
    extras = [
        ("Archive/", "Toolbox",
         "Earlier single-purpose Visio conversion scripts, superseded by "
         "Convert-VisioLegacyFiles.ps1"),
        ("devenv/", "Stage 0", "Development environment helpers"),
        ("misc/", "Toolbox", "Small standalone utilities"),
    ]
    for path, stage_label, note in extras:
        if path.rstrip("/") in seen:
            continue
        rows.append(
            "<tr>"
            f"<td>{_path_link(path.rstrip('/'))}</td>"
            f"<td>{stage_label}</td>"
            f'<td class="small">{_esc(note)}</td>'
            "</tr>")

    return f"""
<section id="map">
  <div class="container">
    <h2>6. Repository map</h2>
    <p>Every top-level directory, and where it sits in the flow. Use this when you know what you want and do not need the guided path.</p>

    <div class="table-wrap"><table>
      <caption>Top-level directories of this repository, as surveyed on {_esc(inv.SURVEYED)}, with the flow stage each belongs to.</caption>
      <thead><tr><th scope="col">Path</th><th scope="col">Stage</th><th scope="col">What it is</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>

    <div class="callout info-box">
      <p><strong>Large binaries.</strong> <span class="mono">AI_Local/</span> carries about 488&nbsp;MB of third-party installers &mdash; Visual Studio build tools, the Go MSI, Prometheus exporters &mdash; which is most of this repository's weight. <span class="mono">AI_Local/Files_you_Will_need_that_areNot_here.txt</span> lists the ones that are <em>not</em> committed and must be downloaded for your own hardware, CUDA and the Vulkan SDK among them.</p>
    </div>
  </div>
</section>
"""


def _conventions() -> str:
    """How to read the documentation, and what the markers mean."""
    return """
<section id="conventions">
  <div class="container">
    <h2>7. How to read the documentation here</h2>

    <p>The HTML page sets in this repository share one set of conventions, borrowed from the <span class="mono">Atomic Theory Atlas</span> and applied to the AI_Local pages during the v0.0.1 rebuild. They are worth two minutes before reading a page in anger.</p>

    <div class="table-wrap">
      <table>
        <caption>Reading conventions shared by the AI_Local pages and the Educational page sets.</caption>
        <thead><tr><th scope="col">Marker</th><th scope="col">Means</th></tr></thead>
        <tbody>
          <tr><td><span class="pill stated">Stated</span></td><td>Quoted from a cited source. Nothing was algebraically manipulated</td></tr>
          <tr><td><span class="pill derived">Derived here</span></td><td>Algebra or a numerical evaluation performed on the page. Always followed by an explicit step list</td></tr>
          <tr><td><span class="pill data">Measured value</span></td><td>A tabulated experimental or defined number</td></tr>
          <tr><td><span class="badge high">primary</span></td><td>A normative or first-party specification: vendor documentation, a standards body, a reference manual</td></tr>
          <tr><td><span class="badge medium">vendor</span></td><td>First-party but commercial and revised in place without notice: a model card, a product page</td></tr>
          <tr><td><em>Define variables</em> button</td><td>Opens a table of every symbol in the equation with its SI or stated unit. Always expanded when a page is printed</td></tr>
          <tr><td>Citation <span class="mono">[n]</span></td><td>Links to row <span class="mono">n</span> of that page set's reference table</td></tr>
        </tbody>
      </table>
    </div>

    <h3>Offline by design</h3>
    <p>Every HTML page in this repository opens from local disk with no network access. KaTeX is vendored rather than loaded from a content-delivery network, and nothing uses browser storage, so the pages also render correctly inside a sandboxed frame. The theme follows your operating-system preference and can be overridden for the current page view.</p>

    <h3>Where the numbers come from</h3>
    <p>Figures in the AI_Local pages are either cited to a source or shown with their derivation. The ones that are neither &mdash; planning estimates for a class of hardware, such as per-compiler memory or the throughput realisation factor &mdash; are listed together with their values and how to measure them on <a href="AI_Local/references.html#not-cited">the references page</a>. That list exists so an estimate is never mistaken for a citation.</p>
  </div>
</section>
"""


# %% Public entry point ------------------------------------------------------
def build() -> str:
    """Return the complete body fragment for the repository-root index.html.

    Raises
    ------
    ValueError
        Propagated from :func:`repo_inventory.validate`, so an inconsistent
        inventory stops the build rather than producing a broken page.
    """
    inv.validate()

    return "\n".join([
        _hero(),
        _tier_selector(),
        _flow(),
        _calculator(),
        _toolbox(),
        _companions(),
        _map(),
        _conventions(),
    ])
