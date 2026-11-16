# -*- coding: utf-8 -*-
"""
page_downloads.py -- body of downloads.html.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-11-15

PURPOSE
-------
Step 1 of the setup path: every program the deployment uses, where to get it
from its original creator, which version the deployment folder holds, and
which of them a reader who clones the repository will not find there.

Generated entirely from ``software_catalog.SOFTWARE`` and
``site_flow.STEPS``; this module contains layout only, no data.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import html
from typing import List

import site_flow
import software_catalog as sw

# %% Helpers -----------------------------------------------------------------
#: Small counts spelled out, so a sentence never starts with a numeral.
_COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
                7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}

IN_REPO_LABEL = {
    "yes": '<span class="badge high">in repository</span>',
    "no": '<span class="badge low">not in repository</span>',
    "partial": '<span class="badge medium">partly in repository</span>',
    "n/a": '<span class="badge">fetch from publisher</span>',
}


def _cite(number: int) -> str:
    """One IEEE citation anchor."""
    return f'<a class="cite" href="references.html#r{number}">[{number}]</a>'


def _link(program: sw.Program) -> str:
    """Official download link, with the host shown so the reader sees where it goes."""
    host = program.download.split("//", 1)[1].split("/", 1)[0]
    if host.startswith("www."):
        host = host[4:]
    return (f'<a href="{html.escape(program.download, quote=True)}" rel="noopener">'
            f'{html.escape(host)}</a>')


def _version_cell(program: sw.Program) -> str:
    """Current version, or an honest 'not checked'."""
    if program.current is None:
        return '<span class="muted">not checked</span>'
    return program.current


def _behind(program: sw.Program) -> str:
    """Compare the folder version with the current one, conservatively.

    Only a plain dotted version in both columns is compared; anything else
    (installer lists, branch descriptions) is left to the reader, because a
    wrong "up to date" is worse than none.
    """
    import re
    if not program.in_folder or not program.current:
        return ""
    have = re.fullmatch(r"(\d+(?:\.\d+)+)(?: .*)?", program.in_folder)
    want = re.fullmatch(r"(\d+(?:\.\d+)+)", program.current.split(";")[0].strip())
    if not (have and want):
        return ""
    a = tuple(int(x) for x in have.group(1).split("."))
    b = tuple(int(x) for x in want.group(1).split("."))
    if a == b:
        return '<span class="badge high">current</span>'
    return '<span class="badge medium">newer available</span>' if a < b else ""


def _row(program: sw.Program, show_folder: bool = True) -> str:
    """One table row for a program.

    Four columns, not six: the platform and the download link sit in the
    program cell.  With them in columns of their own, the notes column left
    them so narrow that a host name wrapped one letter per line.
    """
    optional = ' <span class="badge">optional</span>' if not program.required else ""
    folder = (html.escape(program.in_folder) if program.in_folder
              else '<span class="muted">&mdash;</span>')
    first = (f'<strong id="sw-{program.key}">{program.name}</strong>{optional}'
             f'<br><span class="small muted">{html.escape(program.publisher)} &middot; '
             f'{html.escape(program.platform)}</span>'
             f'<br><span class="small">Download: {_link(program)}</span>')
    role = program.role
    if program.notes:
        role += f'<br><span class="small">{program.notes}</span>'
    cells = [first, role]
    if show_folder:
        cells.append(folder + "<br>" + IN_REPO_LABEL[program.in_repo])
    cells.append(_version_cell(program) + _cite(program.ref) + " " + _behind(program))
    return "      <tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def _table(caption: str, programs: List[sw.Program], show_folder: bool = True) -> str:
    """A captioned table of programs."""
    heads = ["Program and download", "What it does here"]
    if show_folder:
        heads.append("In the folder")
    heads.append(f"Current ({sw.VERIFIED})")
    head = "".join(f'<th scope="col">{h}</th>' for h in heads)
    body = "\n".join(_row(p, show_folder) for p in programs)
    return (f'<div class="table-wrap"><table>\n    <caption>{caption}</caption>\n'
            f'    <thead><tr>{head}</tr></thead>\n    <tbody>\n{body}\n    </tbody>\n'
            f'  </table></div>')


# %% Sections ----------------------------------------------------------------
def _hero() -> str:
    missing = sw.not_in_repo()
    return f"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">Step 1 &middot; Software and downloads</div>
    <h1>Everything to install, and where to get it</h1>
    <p class="lead">Every program the deployment uses, linked to its original creator's download page, with the version found in the deployment folder beside the newest one published on {sw.VERIFIED}. {_COUNT_WORDS.get(len(missing), str(len(missing))).capitalize()} of the programs in the folder are not in the GitHub repository, because their installers are too large for it, so a reader who clones the repository has to fetch those from the publisher. They are listed first.</p>
    <p class="small muted">Download from the publisher, not from a mirror: an installer that runs as administrator and loads a kernel driver is the wrong place to save a click. Where a publisher ships source only, the row names the distributor the publisher's own documentation points to and says so.</p>
  </div>
</section>
"""


def _toc() -> str:
    return """
<section id="on-this-page">
  <div class="container">
    <h2>On this page</h2>
    <ul class="toc">
      <li><a href="#not-in-repo">1. Not in the repository: fetch these from the publisher</a></li>
      <li><a href="#minimum">2. The minimum set for your GPU</a></li>
      <li><a href="#by-step">3. Everything, by setup step</a></li>
      <li><a href="#unused">4. In the folder, but not yet used by any page</a></li>
      <li><a href="#method">5. How the versions were checked</a></li>
    </ul>
  </div>
</section>
"""


def _not_in_repo() -> str:
    return f"""
<section id="not-in-repo">
  <div class="container">
    <h2>1. Not in the repository: fetch these from the publisher</h2>
    <p>These were found in the deployment folder on {sw.VERIFIED} but are absent from the GitHub repository. Several are larger than GitHub's 100&nbsp;MB per-file limit.</p>
    {_table("Programs in the deployment folder that the repository does not carry, with the original creator's download page.", sw.not_in_repo())}
  </div>
</section>
"""


def _minimum() -> str:
    """Short per-vendor minimum: what to install to run, and what to add to build."""
    return """
<section id="minimum">
  <div class="container">
    <h2>2. The minimum set for your GPU</h2>
    <div class="table-wrap"><table>
      <caption>What each vendor's machines need to <em>run</em> a model, and what to add to <em>build</em> llama.cpp from source. Running is enough for single-machine use; building is needed for llama.cpp RPC clusters and for Pascal cards on CUDA 12.x.</caption>
      <thead><tr><th scope="col">GPU</th><th scope="col">To run</th><th scope="col">Add to build</th></tr></thead>
      <tbody>
        <tr><td>NVIDIA</td><td><a href="#sw-nvidia-driver">Driver</a>, <a href="#sw-ollama">Ollama</a></td><td><a href="#sw-cuda">CUDA Toolkit</a> (12.x for Pascal and older), <a href="#sw-vs-buildtools">Build Tools</a>, <a href="#sw-git">Git</a>, <a href="#sw-cmake">CMake</a></td></tr>
        <tr><td>AMD</td><td><a href="#sw-amd-driver">Adrenalin driver</a>, <a href="#sw-ollama">Ollama</a></td><td><a href="#sw-hip-sdk">HIP SDK</a> for ROCm builds, or the <a href="#sw-vulkan-sdk">Vulkan SDK</a> for Vulkan builds; <a href="#sw-vs-buildtools">Build Tools</a>, <a href="#sw-git">Git</a></td></tr>
        <tr><td>Intel</td><td>Intel graphics driver, <a href="#sw-ollama">Ollama</a></td><td><a href="#sw-vulkan-sdk">Vulkan SDK</a> or <a href="#sw-oneapi">oneAPI</a></td></tr>
        <tr><td>Every machine</td><td><a href="#sw-miniforge">Miniforge</a> for the Python steps</td><td>&mdash;</td></tr>
        <tr><td>Monitoring server</td><td><a href="#sw-prometheus">Prometheus</a>, <a href="#sw-grafana">Grafana</a>, <a href="#sw-nssm">NSSM</a></td><td>&mdash;</td></tr>
      </tbody>
    </table></div>
    <p>Which driver, toolkit and compiler versions to pair for your card is on the <a href="gpu-configuration.html#nvidia-matrix">GPU configuration page</a>.</p>
  </div>
</section>
"""


def _by_step() -> str:
    parts: List[str] = ["""
<section id="by-step">
  <div class="container">
    <h2>3. Everything, by setup step</h2>
    <p>Each program appears under the first step that needs it. Optional components are marked.</p>
"""]
    placed = set()
    for index, step in enumerate(site_flow.STEPS, start=1):
        programs = [p for p in sw.SOFTWARE
                    if p.steps and p.steps[0] == step.key and p.key not in placed
                    and (p.required or not p.in_folder or p.in_repo != "yes")]
        if not programs:
            continue
        placed.update(p.key for p in programs)
        parts.append(f'    <h3 id="step-{step.key}">Step {index}: {step.title} '
                     f'<span class="small muted">&middot; <a href="{step.page}">go to the page</a></span></h3>')
        parts.append("    " + _table(f"Programs first needed at step {index}, {step.title[:1].lower() + step.title[1:]}.", programs))
    parts.append("  </div>\n</section>\n")
    return "\n".join(parts)


def _unused() -> str:
    unused = [p for p in sw.SOFTWARE if not p.required and p.in_folder and p.in_repo == "yes"]
    return f"""
<section id="unused">
  <div class="container">
    <h2>4. In the folder, but not yet used by any page</h2>
    <p>These are in the repository's <span class="mono">Supporting_Software</span> folder but no page in the set configures them. They are listed so the inventory is complete, not as a recommendation to install them.</p>
    {_table("Programs present in the folder that no page in the set uses yet.", unused)}
  </div>
</section>
"""


def _method() -> str:
    return f"""
<section id="method">
  <div class="container">
    <h2>5. How the versions were checked</h2>
    <ul>
      <li><strong>In the folder</strong> is read from the installer and archive file names in <span class="mono">tools/AI_Local</span> on {sw.VERIFIED}. It is what was installed from, not a recommendation.</li>
      <li><strong>Current</strong> for GitHub-hosted projects is the highest release tag in the repository, read with <span class="mono">git ls-remote --tags</span>; for the others, the publisher's download or release-notes page cited in the row.</li>
      <li><strong>Newer available</strong> appears only where both columns are plain version numbers. A row without it has not been judged, not judged current.</li>
      <li>Every link on this page and across the set can be re-checked with <span class="mono">python scripts/check_links.py</span>, which reports links that no longer resolve.</li>
    </ul>
    <p>Version numbers move weekly. Treat the <strong>Current</strong> column as the state on {sw.VERIFIED} and the link as the thing to trust.</p>
  </div>
</section>
"""


# %% Entry point -------------------------------------------------------------
def build() -> str:
    """Return the body fragment of downloads.html."""
    sw.validate()
    return "".join([_hero(), _toc(), _not_in_repo(), _minimum(), _by_step(),
                    _unused(), _method()])
