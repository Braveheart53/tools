# -*- coding: utf-8 -*-
"""
page_meta.py -- body content for index.html, references.html and CHANGELOG.html

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

PURPOSE
-------
These three pages are generated from data rather than hand-written, so that
they cannot drift out of step with the rest of the set:

* ``index.html``      -- generated from the page manifest in
                         ``build_ai_local_site.py``, so a new page appears on
                         the landing page automatically.
* ``references.html`` -- generated from ``references.py``, so a citation and
                         its reference row can never disagree.
* ``CHANGELOG.html``  -- generated from :data:`RELEASES` below, which is also
                         the source of the version stamp printed in the
                         navigation strip of every page.

VERSIONING SCHEME
-----------------
Semantic, X.Y.Z, with 0.0.1 as the first internal draft, per the project's
convention.  The set as a whole carries one version; individual assets carry
their own version in their header comment.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from typing import Dict, List, Tuple

import references


# %% Release history ---------------------------------------------------------
#: Release history, newest first.  Each entry is
#: ``(version, iso_date, headline, {section: [bullet, ...]})``.
#: The first entry's version is the version stamped on every page.
RELEASES: List[Tuple[str, str, str, Dict[str, List[str]]]] = [
    (
        "0.0.1",
        "2026-10-18",
        "First internal draft of the rebuilt page set",
        {
            "Added": [
                "<strong>local-code-build-test.html</strong> &mdash; the page that was missing from the set: "
                "how to let a locally hosted model generate code and then build and test it on local hardware "
                "through Open WebUI. Covers the choice between Pyodide, the Jupyter engine and Open Terminal; "
                "the full variable set for each; wiring a named mamba environment in by either route; CMake and "
                "MSVC builds; Qt, Veusz and GPU specifics for Python; and a twelve-step verification sequence.",
                "<strong>ollama-model-selection.html</strong> &mdash; which models in the Ollama library are "
                "suited to local code and agent work, with every size, context window, capability label and "
                "published benchmark figure cited to its model page, and the memory and throughput arithmetic "
                "that decides whether a given tag will fit and run.",
                "<strong>claude-sandbox-local-env.html</strong> &mdash; granting a sandboxed agent prompt "
                "access to local mamba environments: what an OS-enforced command sandbox restricts, how it "
                "differs from a container backend, the settings that grant environment access, and the denial "
                "checks that confirm a policy actually took effect.",
                "<strong>monitoring-sizing.html</strong> &mdash; the four relations the existing "
                "monitoring install pages assume but never state: the disk cost of a retention "
                "window, what the scrape configuration actually ingests, the lower bound on a "
                "range-vector window that stops panels emptying intermittently, and the difference "
                "between a counter and a gauge when computing utilisation. Placed on its own page "
                "rather than duplicated as an appendix on each of the four monitoring pages.",
                "<strong>index.html</strong> &mdash; a landing page for the set, generated from the page "
                "manifest so a future page appears here without an edit.",
                "<strong>references.html</strong> &mdash; a single IEEE-format reference table for the whole "
                "set, generated from <span class=\"mono\">references.py</span>, with a per-reference sourcing-"
                "confidence class and one shared access date.",
                "<strong>CHANGELOG.html</strong> &mdash; this page.",
                "A shared navigation strip on every page, giving one consistent route between all pages in the "
                "set plus the version stamp and a link to this change log.",
                "A shared equation component (<span class=\"mono\">assets/equations.css</span>, "
                "<span class=\"mono\">assets/equations.js</span>) reproducing the equation and "
                "variable-definition pattern from <em>Atomic Theory Atlas</em>: a provenance pill, a "
                "<em>Define variables</em> disclosure that opens a symbol table with SI units, and an explicit "
                "step list behind every derived result.",
                "KaTeX vendored into <span class=\"mono\">assets/katex/</span> so equations typeset with no "
                "network access, consistent with the rest of the set being usable offline.",
                "A dark theme for the three pages that had none "
                "(<span class=\"mono\">assets/legacy-dark.css</span>), plus a theme control on every page that "
                "lacked one.",
                "<span class=\"mono\">scripts/probe_model_throughput.py</span> &mdash; measures prefill and "
                "decode rates through the Ollama API and prints them against what the equations predict.",
                "<span class=\"mono\">scripts/build_cpp.ps1</span> &mdash; a no-argument CMake build wrapper "
                "that discovers the MSVC toolchain with <span class=\"mono\">vswhere</span> instead of a "
                "hard-coded toolset path, and caps parallelism from free memory.",
                "<span class=\"mono\">config/</span> &mdash; ready-to-edit Open WebUI, Open Terminal and "
                "sandbox configuration files matching the worked examples on the pages.",
            ],
            "Changed": [
                "Fifteen equations that were previously implicit in prose or absent entirely are now explicit "
                "blocks with variable tables: weight footprint, active parameters for a routed mixture of "
                "experts, key/value cache size, context budget, the memory-bandwidth decode ceiling, layer "
                "offload count, distributed per-token time, the RPC break-even condition, safe parallel job "
                "count, Amdahl speed-up, agent-loop wall clock, Prometheus disk and ingest rate, the "
                "<span class=\"mono\">rate()</span> window condition, and counter-based utilisation.",
                "The four pre-existing pages that carry an artifact iframe wrapper "
                "(<span class=\"mono\">Dockler_Jupyter_withGPU_Passthru_nssm</span>, "
                "<span class=\"mono\">GPU_monitoring_setup</span>, "
                "<span class=\"mono\">Jupyter_Server_Setup_wsl</span> and the archived "
                "<span class=\"mono\">Jupyter_Code_Eval_Setup</span>) have the duplicate "
                "<span class=\"mono\">&lt;!DOCTYPE&gt;</span>, <span class=\"mono\">&lt;html&gt;</span> and "
                "<span class=\"mono\">&lt;body&gt;</span> elements removed, so each is now one valid document "
                "instead of two nested ones.",
                "Every pre-existing page keeps its own stylesheet, layout, content and theme toggle unchanged. "
                "The rebuild adds the navigation strip and the shared stylesheets and nothing else, so no "
                "existing guide looks different from how it looked before.",
            ],
            "Fixed": [
                "<span class=\"mono\">Grafan_Promethius_install_linux.html</span>, "
                "<span class=\"mono\">Grafana_Prometheus_install_windows.html</span> and the archived "
                "<span class=\"mono\">Windows_Exporter_Grafana_dashboard.html</span> had no dark theme and no "
                "theme control. Both are now present, scoped so the light rendering is byte-for-byte unchanged.",
                "Pages in the set had no way to reach each other; every page now carries the same navigation.",
                "Citations were previously inline URLs or absent. All claims now resolve to a numbered row in "
                "one reference table.",
            ],
            "Known limitations": [
                "The <span class=\"mono\">TERMINAL_SERVER_CONNECTIONS</span> format is not published by the "
                "vendor, so the Open Terminal connection cannot be fully pre-seeded from the environment. "
                "Recorded on the build page.",
                "Ollama tag pages do not state quantisation for most tags, so the footprint equation's "
                "bits-per-weight input is a library default rather than a published figure. The equation says so.",
                "Per-compiler memory, the throughput realisation factor, runtime VRAM reservation, GGUF "
                "container overhead and the Prometheus series counts are planning estimates for this class of "
                "hardware, stated as ranges and flagged in each equation block.",
                "The architectural quantities in the 24&nbsp;GB worked fit are placeholders of a plausible "
                "shape, not values read from a model. The table says so and names the command that produces "
                "the real ones.",
            ],
        },
    ),
]


# %% index.html --------------------------------------------------------------
def build_index(manifest) -> str:
    """Return the body fragment for index.html.

    Parameters
    ----------
    manifest : Sequence[PageSpec]
        The page manifest from ``build_ai_local_site.py``.  Each entry supplies
        ``filename``, ``nav_label``, ``title``, ``blurb``, ``group`` and
        ``is_new``, so the landing page is a projection of the manifest rather
        than a second list that could disagree with it.

    Returns
    -------
    str
        The complete body fragment.
    """
    version = RELEASES[0][0]

    # Group the manifest in a fixed display order.  Pages whose group is not
    # listed here are appended under "Other" rather than silently dropped.
    group_order = [
        ("build", "Local code generation and testing",
         "Giving a local model a real shell, a real compiler and a real Python "
         "environment, and choosing the model that will fit."),
        ("inference", "Serving the model",
         "Getting a model answering on the network, including across several "
         "machines when it will not fit on one."),
        ("monitoring", "Monitoring",
         "Knowing what the hardware is doing while it serves, on Windows and "
         "on Linux."),
        ("meta", "Reference",
         "Sources and revision history for the whole set."),
    ]

    sections: List[str] = []
    seen = set()

    for key, heading, intro in group_order:
        cards = []
        for spec in manifest:
            if spec.group != key:
                continue
            seen.add(spec.filename)
            badge = ('<span class="badge new">new</span> ' if spec.is_new else "")
            cards.append(
                f'      <a class="card" href="{spec.filename}">\n'
                f'        <span class="card-kicker">{badge}{spec.nav_label}</span>\n'
                f'        <h3>{spec.title}</h3>\n'
                f'        <p class="small muted">{spec.blurb}</p>\n'
                f'      </a>'
            )
        if not cards:
            continue
        sections.append(
            f'<section id="g-{key}">\n'
            f'  <div class="container">\n'
            f'    <h2>{heading}</h2>\n'
            f'    <p>{intro}</p>\n'
            f'    <div class="card-grid">\n'
            + "\n".join(cards) +
            f'\n    </div>\n'
            f'  </div>\n'
            f'</section>'
        )

    leftover = [s for s in manifest if s.filename not in seen]
    if leftover:
        cards = [
            f'      <a class="card" href="{s.filename}">\n'
            f'        <span class="card-kicker">{s.nav_label}</span>\n'
            f'        <h3>{s.title}</h3>\n'
            f'        <p class="small muted">{s.blurb}</p>\n'
            f'      </a>'
            for s in leftover
        ]
        sections.append(
            '<section id="g-other">\n  <div class="container">\n    <h2>Other</h2>\n'
            '    <div class="card-grid">\n' + "\n".join(cards) +
            '\n    </div>\n  </div>\n</section>'
        )

    body = r"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">AI_Local &middot; v""" + version + r"""</div>
    <h1>Running AI on your own hardware, end to end</h1>
    <p class="lead">A working set for deploying language models across a home or lab network: serving them, distributing them across several machines when one is not enough, monitoring what the hardware is doing, and &mdash; the part this revision adds &mdash; letting a model write, build and test code on machines you own, with nothing leaving the network.</p>
    <p class="small muted">Scientific and code-building work is the focus. Every page cites its sources to a numbered row in <a href="references.html">one reference table</a>, every equation carries a variable table with units, and every figure that is an estimate rather than a citation says so.</p>
  </div>
</section>

<section id="start-here">
  <div class="container">
    <h2>Start here</h2>
    <div class="grid-2">
      <div>
        <p>The set assumes one inference host with optional worker nodes. If you are building this from nothing, the order below gets you to a working loop with the fewest dead ends.</p>
        <ol>
          <li><strong>Pick a model that fits.</strong> <a href="ollama-model-selection.html">Model selection</a> has the criteria and the memory arithmetic. Doing this first avoids installing a stack around a model your card cannot hold.</li>
          <li><strong>Serve it.</strong> Ollama alone on one machine, or <a href="llama-rpc-vulkan-guide.html">llama.cpp with RPC workers</a> when the model is larger than any single card.</li>
          <li><strong>Give it a shell.</strong> <a href="local-code-build-test.html">Local build and test</a> covers Open Terminal, the Jupyter engine and wiring in a mamba environment.</li>
          <li><strong>Decide the boundary.</strong> <a href="claude-sandbox-local-env.html">Sandboxed access to local environments</a> covers the other containment model, for work that needs the host itself.</li>
          <li><strong>Watch it.</strong> The <a href="Promethius_Grafana_windows11-llama-monitoring-tutorial.html">Prometheus and Grafana</a> pages, which is how you find out a model quietly spilled to system RAM.</li>
        </ol>
      </div>
      <div class="card">
        <h3 style="margin-top:0">What this revision adds</h3>
        <p class="small">The set previously stopped at serving and monitoring a model. Three pages now cover the loop from a prompt to a passing test suite:</p>
        <ul class="small">
          <li>Execution backends and their variables, quoted verbatim</li>
          <li>Named mamba environments reached from a sandbox</li>
          <li>C++ and Python build and test paths</li>
          <li>Model selection with the fit arithmetic shown</li>
          <li>What each containment model actually contains</li>
        </ul>
        <p class="small muted" style="margin-bottom:0">See the <a href="CHANGELOG.html">change log</a> for the full list.</p>
      </div>
    </div>
  </div>
</section>

""" + "\n\n".join(sections) + r"""

<section id="conventions">
  <div class="container">
    <h2>Conventions used across the set</h2>

    <div class="table-wrap">
      <table>
        <caption>Reading conventions. The provenance pills and the variable-table disclosure follow the pattern established in the <em>Atomic Theory Atlas</em> page set in this repository.</caption>
        <thead><tr><th scope="col">Convention</th><th scope="col">Meaning</th></tr></thead>
        <tbody>
          <tr><td><span class="pill stated">Stated</span></td><td>Quoted from a cited source. Nothing was algebraically manipulated</td></tr>
          <tr><td><span class="pill derived">Derived here</span></td><td>Algebra or a numerical evaluation performed on these pages. Always followed by an explicit step list</td></tr>
          <tr><td><span class="pill data">Measured value</span></td><td>A tabulated experimental or defined number</td></tr>
          <tr><td><span class="badge high">primary</span></td><td>A normative or first-party specification: vendor documentation, a standards body, a reference manual</td></tr>
          <tr><td><span class="badge medium">vendor</span></td><td>First-party but commercial and revised without notice: a model card, a product page</td></tr>
          <tr><td><span class="badge medium">estimate</span></td><td>A planning figure for this class of hardware, stated as a range. Measure it before relying on it</td></tr>
          <tr><td><em>Define variables</em> button</td><td>Opens a table of every symbol in the equation with its SI or stated unit. Variable tables are always expanded when a page is printed</td></tr>
          <tr><td>Citation <span class="mono">[n]</span></td><td>Links to row <span class="mono">n</span> of the <a href="references.html">reference table</a></td></tr>
        </tbody>
      </table>
    </div>

    <h3>Offline by design</h3>
    <p>Every page in the set opens from a local disk with no network access. KaTeX<a class="cite" href="references.html#r31">[31]</a> is vendored into <span class="mono">assets/katex/</span> rather than loaded from a content-delivery network &mdash; it has no dependencies and is designed to be bundled with a site's own resources &mdash; and nothing in the set uses browser storage &mdash; so the pages also render correctly inside a sandboxed frame, where storage access throws. The theme follows the operating-system preference and can be overridden for the current page view.</p>

    <h3>Files you will need that are not in the repository</h3>
    <p>Installers specific to your hardware &mdash; CUDA, the Vulkan SDK, Docker Desktop, the Grafana MSI &mdash; are listed in <span class="mono">Files_you_Will_need_that_areNot_here.txt</span> alongside these pages<a class="cite" href="references.html#r32">[32]</a>.</p>
  </div>
</section>
"""
    return body


# %% references.html ---------------------------------------------------------
def build_references() -> str:
    """Return the body fragment for references.html, built from references.py."""
    references.validate()

    confidence_label = {
        "primary": ('<span class="badge high">primary</span>',
                    "Normative or first-party specification"),
        "vendor":  ('<span class="badge medium">vendor</span>',
                    "First-party but commercial; revised without notice"),
        "derived": ('<span class="badge new">derived</span>',
                    "Computed on these pages from a primary source"),
    }

    rows: List[str] = []
    for num, cite, cat, url in sorted(references.REFS, key=lambda e: e[0]):
        label = references.CAT_LABEL[cat]
        host = references.domain_of(url)
        conf = references.CONFIDENCE[num]
        badge = confidence_label[conf][0]
        rows.append(
            f'<tr id="r{num}">'
            f'<td class="ref-num">[{num}]</td>'
            f'<td class="ref-cite">{cite}'
            f'<div class="ref-link"><a href="{url}" target="_blank" rel="noopener noreferrer">{host}</a></div>'
            f'</td>'
            f'<td><span class="ref-cat">{label}</span></td>'
            f'<td>{badge}</td>'
            f'</tr>'
        )

    # Per-category counts, for the summary table.
    counts: Dict[str, int] = {}
    for _n, _c, cat, _u in references.REFS:
        counts[cat] = counts.get(cat, 0) + 1
    count_rows = "".join(
        f'<tr><td>{references.CAT_LABEL[k]}</td><td class="mono">{v}</td></tr>'
        for k, v in sorted(counts.items(), key=lambda kv: references.CAT_LABEL[kv[0]])
    )

    conf_counts: Dict[str, int] = {}
    for v in references.CONFIDENCE.values():
        conf_counts[v] = conf_counts.get(v, 0) + 1
    conf_rows = "".join(
        f'<tr><td>{confidence_label[k][0]}</td><td>{confidence_label[k][1]}</td>'
        f'<td class="mono">{v}</td></tr>'
        for k, v in sorted(conf_counts.items())
    )

    return r"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">References</div>
    <h1>Sources</h1>
    <p class="lead">Every bracketed citation anywhere in this page set links to a row below, and every row links out to the source it came from. Rows are grouped by subject and numbered permanently: a retired reference keeps its number and a new one takes the next free number, so a number written down elsewhere never comes to mean something else.</p>
    <p class="small muted">Every URL below was retrieved and its quoted content confirmed on """ + references.ACCESSED + r""". Citations are in IEEE style. The build refuses to produce a page that cites a number not defined here, so a dead citation is a build failure rather than a broken link.</p>
  </div>
</section>

<section id="list">
  <div class="container-wide">
    <h2>Numbered reference list</h2>
    <div class="table-wrap"><table class="ref-table">
      <caption>Complete IEEE-style numbered reference list for the AI_Local page set, with a sourcing-confidence class per row. Ordered by number, which follows first appearance by subject group.</caption>
      <thead><tr><th scope="col">No.</th><th scope="col">Reference</th><th scope="col">Subject</th><th scope="col">Confidence</th></tr></thead>
      <tbody>""" + "".join(rows) + r"""</tbody>
    </table></div>
  </div>
</section>

<section id="confidence">
  <div class="container">
    <h2>What the confidence classes mean</h2>

    <p>A page that mixes a project's own reference manual with a commercial model card ought to say which is which, because the two age very differently.</p>

    <div class="table-wrap">
      <table>
        <caption>Sourcing-confidence classes used in the table above, with how many references fall into each.</caption>
        <thead><tr><th scope="col">Class</th><th scope="col">Meaning</th><th scope="col">Count</th></tr></thead>
        <tbody>""" + conf_rows + r"""</tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong>The practical consequence.</strong> A <span class="badge high">primary</span> reference describes behaviour that changes on a release boundary, with a changelog. A <span class="badge medium">vendor</span> reference &mdash; every model card in this list &mdash; is revised in place: a tag's size changes when it is requantised, and tags are added and withdrawn without any record. Anything cited to a model card should be re-read before hardware is bought on the strength of it.</p>
    </div>

    <div class="table-wrap">
      <table>
        <caption>References per subject group.</caption>
        <thead><tr><th scope="col">Subject</th><th scope="col">Count</th></tr></thead>
        <tbody>""" + count_rows + r"""</tbody>
      </table>
    </div>
  </div>
</section>

<section id="not-cited">
  <div class="container">
    <h2>Figures with no citation</h2>

    <p>Some numbers on these pages are not in any source, because no source publishes them. They are planning estimates for this class of hardware and they are listed here so they are not mistaken for cited facts. Each is stated as a range at its point of use, and the equation block that consumes it names it as an estimate.</p>

    <div class="table-wrap">
      <table>
        <caption>Uncited planning estimates used across the set, with the value, where it is used, and how to replace it with a measurement.</caption>
        <thead><tr><th scope="col">Quantity</th><th scope="col">Value used</th><th scope="col">Used in</th><th scope="col">How to measure it</th></tr></thead>
        <tbody>
          <tr>
            <td>GGUF container overhead \(\varepsilon\)</td>
            <td class="mono">0.03 &ndash; 0.08</td>
            <td>Weight footprint</td>
            <td>Compare a published tag size against \(P b_{q}/8\) for a model whose parameter count and quantisation you know</td>
          </tr>
          <tr>
            <td>Throughput realisation factor \(\eta\)</td>
            <td class="mono">0.5 &ndash; 0.8</td>
            <td>Bandwidth ceiling</td>
            <td><span class="mono">scripts/probe_model_throughput.py</span>, then divide the measured rate by the computed bound</td>
          </tr>
          <tr>
            <td>Runtime VRAM reservation \(V_{\text{rt}}\)</td>
            <td class="mono">0.8 &ndash; 1.5 GB</td>
            <td>Context budget, layer offload</td>
            <td><span class="mono">nvidia-smi</span> with a model loaded, minus the published weight size</td>
          </tr>
          <tr>
            <td>Peak compiler resident set \(M_{\text{job}}\)</td>
            <td class="mono">1.5 &ndash; 2.5 GB</td>
            <td>Parallel job count</td>
            <td>Watch peak working set during a single-job build of your heaviest translation unit</td>
          </tr>
          <tr>
            <td>Exporter series counts</td>
            <td class="mono">~1500 / ~120 / ~30</td>
            <td>Prometheus ingest rate</td>
            <td>Query <span class="mono">prometheus_tsdb_head_series</span> on your own server</td>
          </tr>
          <tr>
            <td>Model architecture placeholders \(n_{\ell}=48,\ n_{kv}=8,\ d_{h}=128\)</td>
            <td class="mono">plausible shape only</td>
            <td>24&nbsp;GB worked fit</td>
            <td><span class="mono">ollama show &lt;tag&gt;</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>Why they are published at all.</strong> An equation with no numbers in it cannot be checked. These ranges make the worked examples concrete enough to verify the algebra and to sanity-check a result, which is worth more than leaving the examples symbolic &mdash; provided the estimates are labelled, which is the purpose of this table.</p>
    </div>
  </div>
</section>
"""


# %% CHANGELOG.html ----------------------------------------------------------
def current_version() -> str:
    """Return the version string stamped on every page in the set."""
    return RELEASES[0][0]


def build_changelog() -> str:
    """Return the body fragment for CHANGELOG.html, built from RELEASES."""
    blocks: List[str] = []

    for version, date, headline, sections in RELEASES:
        parts = [
            f'<div class="rel">\n'
            f'  <h3><span class="rel-ver">v{version}</span>'
            f'<span class="rel-date">{date}</span></h3>\n'
            f'  <p class="lead small">{headline}</p>'
        ]
        for section_name, bullets in sections.items():
            items = "\n".join(f'      <li>{b}</li>' for b in bullets)
            parts.append(
                f'  <h4>{section_name}</h4>\n'
                f'    <ul>\n{items}\n    </ul>'
            )
        parts.append("</div>")
        blocks.append("\n".join(parts))

    version = RELEASES[0][0]

    return r"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">Change log</div>
    <h1>Version history</h1>
    <p class="lead">The AI_Local page set carries one version, stamped in the navigation strip of every page. This log records what changed in each revision, including what was deliberately left alone.</p>
    <p class="small muted">Versioning is semantic, X.Y.Z, with 0.0.1 as the first internal draft. Current version: <span class="mono">v""" + version + r"""</span>.</p>
  </div>
</section>

<section id="scheme">
  <div class="container">
    <h2>Versioning scheme</h2>

    <div class="table-wrap">
      <table>
        <caption>What each component of the version number signifies for this page set.</caption>
        <thead><tr><th scope="col">Component</th><th scope="col">Increments when</th><th scope="col">Example</th></tr></thead>
        <tbody>
          <tr><td><strong>X</strong> &mdash; major</td><td>The set is restructured, or guidance changes in a way that invalidates a previous configuration</td><td>Moving the whole set off Open WebUI</td></tr>
          <tr><td><strong>Y</strong> &mdash; minor</td><td>A page is added or removed, or a page gains substantial new material</td><td>Adding the build-and-test page</td></tr>
          <tr><td><strong>Z</strong> &mdash; patch</td><td>Corrections, re-verified figures, new citations, styling fixes</td><td>Updating a model size after a requantisation</td></tr>
          <tr><td><strong>0.y.z</strong></td><td>Pre-release. The set is an internal draft until 1.0.0</td><td>v0.0.1, this revision</td></tr>
        </tbody>
      </table>
    </div>

    <p>Individual assets carry their own version in their header comment, which moves independently of the set version. Shell scripts and Python modules shipped alongside the pages follow the same scheme.</p>

    <div class="table-wrap">
      <table>
        <caption>Assets with their own independent version stamp, as of set version v""" + version + r""".</caption>
        <thead><tr><th scope="col">Asset</th><th scope="col">Version</th><th scope="col">Purpose</th></tr></thead>
        <tbody>
          <tr><td class="mono">assets/site.css</td><td class="mono">1.0.0</td><td>Base stylesheet for the new pages only</td></tr>
          <tr><td class="mono">assets/equations.css</td><td class="mono">1.0.0</td><td>Equation and variable-table component, shared by every page</td></tr>
          <tr><td class="mono">assets/equations.js</td><td class="mono">1.0.0</td><td>KaTeX rendering and the variable-table disclosure</td></tr>
          <tr><td class="mono">assets/sitenav.css</td><td class="mono">1.0.0</td><td>Shared navigation strip</td></tr>
          <tr><td class="mono">assets/sitenav.js</td><td class="mono">1.0.0</td><td>Active-link marking and the injected theme control</td></tr>
          <tr><td class="mono">assets/legacy-dark.css</td><td class="mono">1.0.0</td><td>Dark theme for the three plain-stylesheet pages</td></tr>
          <tr><td class="mono">scripts/build_ai_local_site.py</td><td class="mono">0.0.1</td><td>Generator and verifier for the whole set</td></tr>
          <tr><td class="mono">scripts/probe_model_throughput.py</td><td class="mono">0.0.1</td><td>Throughput measurement against the equations</td></tr>
          <tr><td class="mono">scripts/build_cpp.ps1</td><td class="mono">0.0.1</td><td>CMake build wrapper with a bounded job count</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="releases">
  <div class="container">
    <h2>Releases</h2>
""" + "\n\n".join(blocks) + r"""
  </div>
</section>

<section id="unchanged">
  <div class="container">
    <h2>What was deliberately not changed</h2>

    <p>The rebuild was additive by design. Recorded here so a future revision does not assume these were oversights.</p>

    <div class="table-wrap">
      <table>
        <caption>Deliberate non-changes in v""" + version + r""", with the reason each was left alone.</caption>
        <thead><tr><th scope="col">Left alone</th><th scope="col">Reason</th></tr></thead>
        <tbody>
          <tr>
            <td>Each pre-existing page's own stylesheet, layout and theme toggle</td>
            <td>The seven existing guides each have a distinct look that works. Imposing one stylesheet would have changed every page's appearance for no reader benefit, and would have risked breaking page-specific behaviour such as the tab widget on the Windows Prometheus page</td>
          </tr>
          <tr>
            <td>The technical content of the existing guides</td>
            <td>Nothing in them was found to be wrong. The rebuild adds the missing material rather than rewriting what was already correct</td>
          </tr>
          <tr>
            <td>Hard-coded IP addresses (<span class="mono">192.168.7.x</span>) and absolute paths</td>
            <td>They document this deployment, and replacing them with placeholders would make the commands less useful to their actual reader</td>
          </tr>
          <tr>
            <td>The binary installers and extracted exporter archives in the directory</td>
            <td>Outside the scope of a documentation rebuild, and the set's own <span class="mono">Files_you_Will_need_that_areNot_here.txt</span> already tracks what is missing</td>
          </tr>
          <tr>
            <td><span class="mono">setup_info.txt</span> as a scratch file</td>
            <td>It is a working notebook of commands, several marked as wrong in place. That record has value; the parts worth promoting were promoted into the new pages with citations, and the file stays as it is</td>
          </tr>
          <tr>
            <td>The two pages under <span class="mono">Archive/</span></td>
            <td>Kept where they are, with the navigation strip and shared stylesheets added, so an archived page is still reachable and still readable in both themes</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="next">
  <div class="container">
    <h2>Candidates for the next revision</h2>

    <p>Not implemented, and listed for a decision rather than as a plan.</p>

    <ul>
      <li><strong>Measured throughput tables.</strong> Running <span class="mono">probe_model_throughput.py</span> across the shortlisted models on the actual nodes would replace the realisation factor with a measurement and turn the model-selection page's estimates into data.</li>
      <li><strong>A Grafana dashboard JSON for the agent loop.</strong> Prompt rate, decode rate, iteration count and build duration on one board, so the loop equation's terms can be watched instead of computed.</li>
      <li><strong>Worked architecture tables per shortlisted model</strong>, read from <span class="mono">ollama show</span>, replacing the placeholder layer and head counts in the 24&nbsp;GB fit.</li>
      <li><strong>A single generated PDF of the whole set</strong>, bookmarked, with variable tables expanded. The print stylesheet already expands them; the remaining work is pagination.</li>
      <li><strong>An <span class="mono">mcpo</span> page.</strong> Exposing instrument control &mdash; Keysight or Lake Shore over VISA &mdash; to a local model as an MCP tool server is a natural extension of the build-and-test page and is currently only mentioned in passing.</li>
    </ul>
  </div>
</section>
"""
