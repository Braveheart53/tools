# AI_Local page set — rebuild v0.0.1

Author: William W. Wallace
Date: 2026-10-18

This archive contains the rebuilt `AI_Local` documentation set. It is a
**drop-in replacement for the HTML pages and a set of new files**; it does not
touch the binary installers, the extracted exporter archives, or
`setup_info.txt`.

---

## 1. What to copy where

Unpack the archive and copy the `AI_Local/` directory over your existing one.
Every path below is relative to `AI_Local/`.

### New files — nothing to overwrite

```
index.html                       landing page for the set
local-code-build-test.html       NEW: local code generation, build and test
ollama-model-selection.html      NEW: which models, and the fit arithmetic
claude-sandbox-local-env.html    NEW: sandboxed access to mamba environments
monitoring-sizing.html           NEW: the monitoring arithmetic
references.html                  NEW: one IEEE reference table for the set
CHANGELOG.html                   NEW: version history

assets/site.css                  base stylesheet, NEW pages only
assets/equations.css             equation + variable-table component
assets/equations.js              KaTeX rendering and the disclosure control
assets/sitenav.css               shared navigation strip
assets/sitenav.js                active-link marking and the theme control
assets/legacy-dark.css           dark theme for the three plain pages
assets/katex/                    vendored KaTeX (offline typesetting)

scripts/build_ai_local_site.py   regenerates and verifies the whole set
scripts/verify_rendering.py      browser checks the static pass cannot make
scripts/probe_model_throughput.py  measures throughput against the equations
scripts/build_cpp.ps1            CMake build wrapper with a bounded job count

config/docker-compose.openwebui.yml      Open WebUI + Open Terminal + Jupyter
config/Dockerfile.open-terminal-mamba    Open Terminal with micromamba
config/claude-settings.user.json         machine-wide sandbox restrictions
config/claude-settings.project.json      per-project sandbox grants
config/prometheus.ai-local.yml           scrape config with ingest costs noted
```

### Replaced files — your originals are modified, not rewritten

```
llama-rpc-vulkan-guide.html
Jupyter_Server_Setup_wsl.html
Dockler_Jupyter_withGPU_Passthru_nssm.html
Promethius_Grafana_windows11-llama-monitoring-tutorial.html
GPU_monitoring_setup.html
Grafana_Prometheus_install_windows.html
Grafan_Promethius_install_linux.html
Archive/Jupyter_Code_Eval_Setup.html
Archive/Windows_Exporter_Grafana_dashboard.html
```

Each of these keeps **its own stylesheet, layout, content, scripts and theme
control unchanged**. Exactly three things were added to each:

1. the shared `<link>` tags, immediately before `</head>`;
2. the navigation strip, immediately after the opening `<body>` tag;
3. the shared `<script>` tags, immediately before the final `</body>`.

Four of them additionally had a **duplicated artifact iframe wrapper**
removed — they each carried two `<!DOCTYPE>`, two `<html>` and two `<body>`
elements, with the real document nested inside the wrapper. Each is now one
valid document. No content was lost; run a diff to confirm.

### Untouched

The installers (`*.exe`, `*.msi`), the extracted exporter directories,
`setup_info.txt`, `Export_Model.py`, `amd_smi_wsl_bridgeScript.ps1` and
`Files_you_Will_need_that_areNot_here.txt` are not in this archive and are
not affected.

---

## 2. Checking it before you commit

The set ships with its own two verifiers. Neither needs network access.

### Static checks — standard library only

```bash
python scripts/build_ai_local_site.py \
    --src /path/to/your/original/AI_Local \
    --out /path/to/a/fresh/output/dir \
    --modules /path/to/the/page/modules
```

This regenerates the set from source and checks:

| Check | What it catches |
|---|---|
| structure | more than one doctype, `<html>` or `<body>` per page |
| equations | an `aria-controls` with no matching table, a derived result with no step list, a missing provenance pill, `$` used as a math delimiter |
| citations | a `[n]` that is not defined, an anchor whose visible number disagrees with its href |
| links | any relative href or src that does not resolve on disk |
| anchors | a cross-page `#fragment` that the target page does not have |
| collisions | a shared class name that a pre-existing page already uses |
| manifest | an HTML entity written into a plain-text manifest field |
| tables | a generated table with no `<caption>` |

The collision check exists because the first build of this set used `.snav`
for the navigation strip, and `llama-rpc-vulkan-guide.html` already defines
`.snav` for its own sidebar: the shared sheet silently repainted that page's
navigation. The prefix is now `ailnav`, and the check keeps it from
recurring.

### Rendered checks — needs Playwright

```bash
pip install playwright
python -m playwright install chromium

python scripts/verify_rendering.py --out . --src /path/to/your/original/AI_Local
```

This loads every page in a real browser and checks the four things the
static pass cannot see: that KaTeX actually typeset the math and left no
parse errors, that the "Define variables" button actually reveals its table,
that the theme control actually changes `data-theme`, and that no page
overflows horizontally at 390&nbsp;px. Passing `--src` lets it attribute an
overflow to the rebuild or to the page's own content.

Current result on this archive: **16 pages, all passing, zero console
errors.**

---

## 3. Known limitations

| Limitation | Detail |
|---|---|
| Three pages overflow at phone width | `Grafana_Prometheus_install_windows.html` (647&nbsp;px), `llama-rpc-vulkan-guide.html` (494&nbsp;px) and `Promethius_Grafana_windows11-llama-monitoring-tutorial.html` (436&nbsp;px). **Pre-existing** — measured identical before and after the rebuild — and caused by each page's own wide tables. Fixing it means editing a pre-existing page, so it is offered as a suggestion rather than applied. |
| `TERMINAL_SERVER_CONNECTIONS` format | Not published by Open WebUI, so the Open Terminal connection cannot be fully pre-seeded from the environment. |
| Quantisation on Ollama tags | Most tag pages do not state bits per weight, so the footprint equation's `b_q` input is a library default. Read the real value from `ollama show <tag>`. |
| Uncited planning estimates | Per-compiler memory, the throughput realisation factor, runtime VRAM reservation, GGUF container overhead, the Prometheus series counts and the 24&nbsp;GB worked fit's architecture figures are planning estimates. Every one is listed with its value and how to measure it in `references.html` §"Figures with no citation". |

---

## 4. Rebuilding after an edit

The pages are **generated**, so edit the source module, not the HTML:

| To change | Edit |
|---|---|
| An equation or its variable table | `eq_library.py` |
| A reference or its confidence class | `references.py` |
| A page's prose | `page_local_build.py`, `page_models.py`, `page_sandbox.py`, `page_monitoring.py` |
| The landing page, references page or change log | `page_meta.py` |
| The version stamp, or a changelog entry | `RELEASES` in `page_meta.py` |
| Which pages exist, or the nav | the manifest in `scripts/build_ai_local_site.py` |

Adding a page is one `PageSpec` entry: it appears in the navigation strip on
every page and on the landing page automatically.

Reference numbers are **permanent**. A retired reference keeps its number and
a new one takes the next free number, so a number written down elsewhere
never comes to mean something else. `references.validate()` enforces that the
numbering is unique and gap-free.
