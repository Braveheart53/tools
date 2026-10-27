# AI_Local page set — rebuild v0.0.4

Author: William W. Wallace
Date: 2026-10-26

This archive contains the rebuilt `AI_Local` documentation set **and a
repository-root homepage that integrates the whole repository into one
implementation flow**. It is a drop-in replacement for the HTML pages plus a
set of new files; it does not touch the binary installers, the extracted
exporter archives, or `setup_info.txt`.

---

## 1. What to copy where

Unpack the archive and copy **both** `index.html` and the `AI_Local/`
directory into the repository root, over your existing ones.

```
index.html      ← NEW: the repository homepage (repository ROOT, not AI_Local/)
AI_Local/       ← the page set, replacing your existing directory
```

The homepage deliberately loads its stylesheets and scripts from
`AI_Local/assets/`, so the two are **not** independent — copying one without
the other leaves the homepage unstyled. Everything below is relative to
`AI_Local/` unless stated otherwise.

### The repository homepage

`index.html` at the repository root is the front door. It organises the whole
repository around one structural fact — everything in it either builds the
Py3p12 mamba environment, runs inside it, or documents the physics behind
something that does — and turns that into a five-stage flow: **foundation →
serve → hands → watch → work**. Every project in the repository has a place
in that sequence.

It carries four interactive pieces, all vanilla JavaScript and all inert
without it:

| Piece | What it does |
|---|---|
| Hardware-tier selector | One machine / two / four. Dims the stages your shape does not need, rather than hiding them, so you can see what you are skipping and read why. |
| Progress tracker | Ticks off stages and shows a progress bar. In-memory only — see below — with a **Copy progress** button that emits a pasteable snapshot. |
| Model planner | Enter the card's VRAM once; it names the models that fit, largest first, with the published size, context, quantisation, capabilities and citation for each. A **near-miss band** lists models that fit the weights but leave under 1 GB for the cache, and says by how much — `gpt-oss:20b` misses a 16 GB card by 0.2 GB, and its own Ollama page still lists 16 GB as supported, so the band keeps the planner from silently contradicting the prose page. |
| Model-fit calculator | Evaluates the context-budget relation live against your own card, so you get a number instead of someone else's worked example. The planner feeds it: **Use in the calculator** on any model loads its published size, so the budget is evaluated for that actual tag rather than a figure you retyped. |

The tracker holds no browser storage on purpose: these pages are opened from
local disk and sometimes inside sandboxed frames, where storage access throws
rather than returning empty. That is why the copy button exists.

The planner and the model-selection page read **one** catalogue,
`src_modules/model_catalog.py`, and the build fails if they disagree: every
tag the planner offers must appear on that page, at the size stated in that
tag's own table row, citing a reference the page carries. The check is
one-directional on purpose — the prose page legitimately discusses models the
planner does not carry, such as the 480b and 123b tags no home deployment can
run. Writing that check is what surfaced a real error:
`qwen3-coder-next:q4_K_M` was recorded as needing 48 GB of VRAM while its
weights alone are 52 GB.

### New files — nothing to overwrite

```
../index.html                    NEW: repository homepage (repository root)
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
assets/home.css                  repository homepage only
assets/home.js                   repository homepage only
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
    --src       /path/to/your/original/AI_Local \
    --out       /path/to/a/fresh/output/AI_Local \
    --modules   src_modules \
    --repo-root /path/to/a/fresh/output \
    --repo-tree /path/to/your/real/repository
```

`--repo-root` also writes the repository homepage and adds the **Repo home**
back-link to every navigation strip. `--repo-tree` is what lets the link
checker verify the homepage's links into `ISP_Speed_Test`, `DWG_2_PDF`,
`Educational` and the rest: the build output holds only `AI_Local/`, so
without it those links are skipped — and the skip is reported rather than
passing silently.

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

python scripts/verify_rendering.py \
    --out  . \
    --home ../index.html \
    --src  /path/to/your/original/AI_Local
```

`--home` is needed because the repository homepage sits one level *above*
this directory, so scanning `--out` cannot find it.

This loads every page in a real browser and checks the four things the
static pass cannot see: that KaTeX actually typeset the math and left no
parse errors, that the "Define variables" button actually reveals its table,
that the theme control actually changes `data-theme`, and that no page
overflows horizontally at 390&nbsp;px. Passing `--src` lets it attribute an
overflow to the rebuild or to the page's own content.

Current result on this archive: **17 pages, all passing, zero console
errors**, with every homepage link verified against the real repository tree.

---

## 2a. What changed in v0.0.4 — re-verification against upstream

Every cited source was re-read against its **upstream documentation
repository** rather than its rendered site. That caught three things the
first pass could not:

| Finding | Why it matters |
|---|---|
| **The shipped Compose file had a security defect.** It set `OPEN_TERMINAL_ALLOWED_DOMAINS` without `cap_add: NET_ADMIN`. | Egress filtering installs dnsmasq and iptables inside the container, so without that capability the allowlist does nothing — an unfiltered container that *looks* filtered, which is worse than an obviously unfiltered one. Now fixed, and the verification sequence checks the start-up log as well as testing egress from inside. |
| **Ollama's context default is no longer a flat 4096.** It is chosen from VRAM: 4k below 24 GiB, 32k from 24–48 GiB, 256k at 48 GiB and above. | The pages stated the old flat default. The recommendation also rose from 32768 to the 64000 the documentation now gives for agents and coding tools. |
| **The llama.cpp RPC worker was renamed** `rpc-server` → `ggml-rpc-server`, and carries an explicit upstream warning. | "The functionality is fragile and insecure. Never run the RPC server on an open network or in a sensitive environment." There is no authentication on the worker port — previously left implicit behind a firewall rule. |

Also added: the `internal: true` Docker network as a harder alternative to the
egress allowlist; a Docker-socket warning; the `CONTEXT` column `ollama ps`
now reports; `--device` / `-c` / `GGML_RPC_DEBUG` on RPC workers; and the
fact that the default RPC split distributes weights *and the cache* in
proportion to free memory, which the distributed relations had treated as
something you choose.

References **[35]–[37]** carry a separate `RECHECKED` access date, so a reader
can tell which verification pass applies to the row they are looking at.

---

## 3. Known limitations

| Limitation | Detail |
|---|---|
| Three pages overflow at phone width | `Grafana_Prometheus_install_windows.html` (647&nbsp;px), `llama-rpc-vulkan-guide.html` (494&nbsp;px) and `Promethius_Grafana_windows11-llama-monitoring-tutorial.html` (436&nbsp;px). **Pre-existing** — measured identical before and after the rebuild — and caused by each page's own wide tables. Fixing it means editing a pre-existing page, so it is offered as a suggestion rather than applied. |
| `TERMINAL_SERVER_CONNECTIONS` format | Not published by Open WebUI, so the Open Terminal connection cannot be fully pre-seeded from the environment. |
| ~~Ollama's context default~~ | **Closed in v0.0.4.** Now documented, with VRAM tiers, a 64000 recommendation for agent work, and the `ollama ps` `CONTEXT` column. |
| Quantisation on Ollama tags | Most tag pages do not state bits per weight, so the footprint equation's `b_q` input is a library default. Read the real value from `ollama show <tag>`. |
| Uncited planning estimates | Per-compiler memory, the throughput realisation factor, runtime VRAM reservation, GGUF container overhead, the Prometheus series counts and the 24&nbsp;GB worked fit's architecture figures are planning estimates. Every one is listed with its value and how to measure it in `references.html` §"Figures with no citation". |

---

## 4. Rebuilding after an edit

The pages are **generated**, so edit the source module, not the HTML:

| To change | Edit |
|---|---|
| The homepage: the flow, the stages, the project catalogue, the hardware tiers | `repo_inventory.py` |
| The homepage's prose or section layout | `page_home.py` |
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
