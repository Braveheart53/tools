# ISP Speed Monitor

| | |
|---|---|
| Bundle version | 1.6.0 |
| Script version | isp_speed_monitor.py 1.2.0 |
| README version | 1.6.0 |

## Revision history (newest first)

| Version | Date | Item | Change |
|---|---|---|---|
| 1.6.0 | 2026-09-05 | bundle | Script 1.2.0: write-through of every test to SQLite/JSONL, "Refresh output files every N tests/rounds" (stable file names, atomic replace, partial/final flag), interrupted-campaign detection, Veusz label escaping; README 1.6.0; pyproject 1.2.0; REQUIRED_MODULES 1.3.2; sample config updated |
| 1.5.1 | 2026-09-05 | bundle | Script 1.1.1: Ookla endpoints use `--server-id=<id>` / `--host=<fqdn>` / no flag for auto, host names accepted in "Add by ID", command line logged per test, Tools ▸ Diagnose selected endpoint…; README 1.5.1 (endpoint entry section); pyproject 1.1.1; REQUIRED_MODULES 1.3.1 |
| 1.5.0 | 2026-09-04 | bundle | Script 1.1.0: menu bar (File / Campaign / View / Tools / Help), View ▸ Theme = System / Light / Dark with explicit Fusion palettes (fixes light/dark not changing on system-dark Windows), Help ▸ About with author/contact/library versions, Tools ▸ Re-export from database / template config / back-end check / log; author contact block in header; finer Spyder cells. Tests 1.1.0 exercise all three themes. README 1.5.0, REQUIRED_MODULES 1.3.0, pyproject 1.1.0 |
| 1.4.1 | 2026-09-04 | bundle | Script 1.0.3: winget package folder scanned one level deeper; README 1.4.1 documents the winget install location; pyproject 1.0.3 |
| 1.4.0 | 2026-09-04 | bundle | Script 1.0.2 (Ookla detection skips the python speedtest-cli shim, probes all PATH entries + winget/Program Files folders); speedtest-cli commented out of requirements.txt 1.1.0 / environment.yml 1.1.0; README 1.4.0 troubleshooting note; REQUIRED_MODULES 1.2.0; pyproject 1.0.2 |
| 1.3.1 | 2026-09-04 | bundle | README 1.3.0: added Ookla Speedtest CLI install instructions (Windows/winget, Debian, RHEL, macOS, first run) |
| 1.3.0 | 2026-09-04 | bundle | Privacy scrub: script 1.0.1 (neutral author, generic QSettings org), tests 1.0.1 (no absolute paths), sample_output reduced to a scrubbed example config + GUI plot screenshot; README 1.2.0 |
| 1.2.0 | 2026-09-04 | bundle | Added uv project (pyproject.toml, .python-version, uv.lock); README 1.1.0; REQUIRED_MODULES.txt 1.1.0; CHANGELOG.md |
| 1.1.0 | 2026-09-04 | bundle | Added environment.yml (mamba) and REQUIRED_MODULES.txt 1.0.0; delivered as 7z |
| 1.0.0 | 2026-09-04 | bundle | Initial release: isp_speed_monitor.py 1.0.0, README 1.0.0, requirements.txt 1.0.0, tests 1.0.0, sample_output |

Scheduled / random, multi-endpoint ISP speed-test logger with a qtpy (PySide6)
GUI, live pyqtgraph plots, a SQLite system of record, JSONL/JSON/CSV exports and
a native **Veusz `.vszh5`** document whose pages mirror the GUI panels.

```
isp_speed_monitor.py      the whole application (single file, `# %%` cells)
pyproject.toml, .python-version   uv project (uv sync)
environment.yml           mamba/conda environment
requirements.txt          pip requirements
REQUIRED_MODULES.txt      module list with purpose and tested versions
tests/gui_smoke.py        offscreen GUI smoke test (screenshots every tab)
tests/render_in_veusz.sh  loads a .vszh5 in a real Veusz binary (PATH or $VEUSZ_BIN) and renders every page to PNG
sample_output/            example campaign config + GUI plot screenshot
```

## Install (Python 3.12)

uv (fastest):
```bash
uv sync                      # .venv with Python 3.12 from pyproject.toml / .python-version
uv run isp_speed_monitor.py  # add --extra fallback to `uv sync` for python speedtest-cli
```
mamba / conda:
```bash
mamba env create -f environment.yml && mamba activate isp-speed-monitor
```
plain pip:
```bash
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
`REQUIRED_MODULES.txt` lists every module with its purpose and tested version.

Back-ends (install at least one; the GUI shows which are detected in the status bar):

| Back-end | Install | What you get |
|---|---|---|
| **Ookla Speedtest CLI** (recommended) | https://www.speedtest.net/apps/cli — put `speedtest` on PATH or browse to it in the GUI | idle latency, jitter, packet loss, download/upload Mbit/s + bytes + elapsed, **loaded latency** (IQM) under download and upload, ISP, external IP, result URL, server id/host/location. Server list via `speedtest -L`. |
| LibreSpeed CLI | https://github.com/librespeed/speedtest-cli (Go binary `librespeed-cli`) | ping, jitter, download/upload; supports `--no-download/--no-upload`; can point at your own LibreSpeed server. |
| python `speedtest-cli` (sivel) | `pip install speedtest-cli` | fallback only: ping + throughput, no jitter/loss, frequently HTTP 403 rate-limited. |
| Simulated | built in | synthetic diurnal data for exercising the pipeline with no network. |

### Installing the Ookla Speedtest CLI (1.2.x)

Official instructions: https://www.speedtest.net/apps/cli

Windows 10/11 (x64 only):
```powershell
winget install -e --id Ookla.Speedtest.CLI
# or download https://install.speedtest.net/app/cli/ookla-speedtest-1.2.0-win64.zip,
# unzip speedtest.exe to a permanent folder and add it to PATH (or browse to it
# in the "Ookla exe" field on the Setup tab)
```
winget installs the portable exe under
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ookla.Speedtest.CLI_Microsoft.Winget.Source_8wekyb3d8bbwe\`
and adds a `speedtest.exe` link in `%LOCALAPPDATA%\Microsoft\WinGet\Links\`;
the monitor searches both automatically.
Ubuntu / Debian (including WSL):
```bash
sudo apt-get remove speedtest-cli          # unofficial package conflicts with the official one
sudo apt-get install curl
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt-get install speedtest
```
RHEL / Fedora:
```bash
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.rpm.sh | sudo bash
sudo yum install speedtest
```
macOS:
```bash
brew tap teamookla/speedtest && brew update && brew install speedtest --force
```
Troubleshooting — status bar says `...\Scripts\speedtest.EXE is not the Ookla CLI
(found: 'speedtest-cli 2.1.3 ...')`: the python `speedtest-cli` package installs
its own `speedtest` shim into the environment's `Scripts`/`bin` folder, which
comes first on PATH. From v1.0.2 the monitor probes every `speedtest` on PATH
(plus the winget, Program Files, Chocolatey and Homebrew folders) and picks the
one that reports "Speedtest by Ookla", so the message only remains if the Ookla
CLI is genuinely not installed. Either install it (above), point the "Ookla exe"
field at `speedtest.exe`, or remove the shim: `pip uninstall speedtest-cli` /
`mamba remove speedtest-cli`.

Then run it once by hand and check the server list:
```bash
speedtest --accept-license --accept-gdpr
speedtest -L
```
Once `speedtest --version` works in a fresh terminal, the Setup tab's
"Refresh server list" will populate. WSL measures through the Windows host's
virtual NIC; for a clean long-term series on Windows use the native
`speedtest.exe`.

Important Ookla caveat: CLI 1.2.x has **no** partial-test switch. The "Download" /
"Upload" check boxes therefore only affect LibreSpeed and python speedtest-cli;
Ookla always measures both. The first Ookla run needs the licence accepted; the
script passes `--accept-license --accept-gdpr` automatically.

## Run

```bash
python isp_speed_monitor.py                                   # GUI
python isp_speed_monitor.py --headless --config campaign.json # server / cron / Task Scheduler
python isp_speed_monitor.py --make-config campaign.json       # template config
python isp_speed_monitor.py --reexport out/speedtests.sqlite3 [--campaign-id N] [--time-axis utc]
python isp_speed_monitor.py --selftest                        # ~15 s simulated campaign, all exports
```

Headless mode is the same engine driven by a QCoreApplication; Ctrl-C (SIGINT)
finishes the in-flight test, writes the round, exports and exits cleanly.
Closing the GUI mid-campaign does the same.

## GUI

* **Setup** — choose a back-end, refresh/filter the server list, add any number
  of endpoints (or type an id; `auto` = Ookla's nearest server). Every round
  tests the selected endpoints **sequentially** (never in parallel, so they do
  not share the access link) and stores a per-round average. Schedule modes:
  * fixed interval (seconds → months),
  * random gap between tests (uniform between min and max),
  * N tests at random times inside each window (e.g. 6 per hour),
  plus campaign length (or "run until stopped"), optional ISO start/end times,
  per-test timeout, pause between endpoints. Configs save/load as JSON.
* **Live** — state, countdown to next test, rounds completed, last round
  average, progress bar over the endpoints, scrolling log.
* **Plots** — 3×2 grid (Download, Upload, Idle latency, Jitter, Packet loss,
  Loaded latency) with raw per-endpoint traces and the bold round-average
  ±std trace; UTC/local axis toggle; recoloured with the theme.
* **Data** — round-average table and raw-result table (newest first).

### Entering endpoints

Pick servers from the fetched list (*Refresh server list*, filter, *Add selected*)
or type into the *server id* box and press *Add by ID*:

| You type | Ookla CLI flag used | Notes |
|---|---|---|
| `14229` (digits) | `--server-id=14229` | any server id from the list or from speedtest.net |
| `ashburn.va.speedtest.frontier.com` | `--host=ashburn.va.speedtest.frontier.com` | host name / FQDN; URLs and `:port` are trimmed. Ookla only |
| `auto` (or blank) | no flag | Ookla chooses the nearest server for every test |

LibreSpeed and python speedtest-cli endpoints take numeric ids only. The exact
command line is written to the Live log before every test (`ookla cmd: …`), and
a failed test keeps the CLI's own error text in the `error` column, e.g.
`Configuration - No servers defined (NoServersException)` for an id that does
not exist. *Tools ▸ Diagnose selected endpoint…* runs one raw test outside the
campaign and shows the command, return code, stdout and stderr in a dialog.

### Menu bar

| Menu | Items |
|---|---|
| **File** | New campaign config (Ctrl+N), Open config… (Ctrl+O), Save config… (Ctrl+S), Export now (Ctrl+E), Open output folder (Ctrl+Shift+O), Quit (Ctrl+Q) |
| **Campaign** | Start (F5), Stop (Shift+F5), Run one round now (F6), Refresh server list (F7) |
| **View** | Theme ▸ System (follow OS) / Light / Dark; Go to tab (Ctrl+1…4); Reset window size |
| **Tools** | Re-export from database… (pick a `speedtests.sqlite3`, a campaign and an output folder), Write template config…, Check back-ends (probe Ookla / LibreSpeed / python speedtest-cli), Diagnose selected endpoint… (runs one raw CLI test for the highlighted endpoint and shows the exact command line, return code, stdout and stderr), Open log file |
| **Help** | README, Ookla CLI download page, LibreSpeed CLI releases, Veusz home page, About (author, contact, version, library versions, settings-file location), About Qt |

The toolbar keeps the most-used actions (Start / Stop / Run one round / Export /
Open output folder / Save / Open config). Window geometry, last config and the
theme choice are remembered via QSettings.

### Theme

*View ▸ Theme* is a three-way choice, stored in QSettings:

* **System (follow OS)** — native style and the palette Windows / macOS / the
  desktop provides; plots follow the detected OS scheme.
* **Light** / **Dark** — force the Qt *Fusion* style with an explicit palette.
  This is deliberate: the native `windows11`/`windowsvista` styles ignore most
  palette roles, and on Qt ≥ 6.5 Fusion's own default palette follows the OS
  scheme — which is why an earlier "light" request still looked dark on a
  system-dark Windows PC. On Qt ≥ 6.8 (PySide6 ≥ 6.8) the window title bar
  follows the choice as well; on older Qt the title bar stays in the OS colour.

## Outputs (all in the chosen output folder)

| File | Content |
|---|---|
| `speedtests.sqlite3` | always written; tables `campaigns`, `endpoints`, `rounds`, `results` (WAL mode, indexed on campaign/time). Multiple campaigns accumulate in the same file. |
| `results.jsonl`, `rounds.jsonl` | append-only, one JSON object per line (raw test / round average). |
| `<name>_c<id>.json` | complete campaign dump: `generator` (incl. `campaign_status`, `complete`, `n_rounds`, `n_results`), `campaign`, `endpoints`, `rounds`, `results`, `field_notes`. Rewritten in place at every refresh and at the end. |
| `<name>_c<id>_results.csv`, `<name>_c<id>_rounds.csv` | flat CSV for spreadsheets; rewritten in place likewise. |
| `<name>_c<id>.vszh5` | native Veusz document (below); rewritten in place likewise. `meta/export_status` states whether the file is partial or final. |
| `<name>_c<id>_<stamp>_manual.*`, `..._reexport.*` | time-stamped snapshots written by *Export now* and by re-export; never overwritten. |
| `isp_speed_monitor.log` | appended log. |

Every raw record carries `ts_utc` (ISO-8601 Z), `ts_local` (ISO-8601 with
offset), `epoch_s`, `tz_name`, `utc_offset_s`, `endpoint_key`, `endpoint_name`
(your label), `backend`, `server_id/name/host/location` (the server actually
used), `ok`, `error`, `latency_ms`, `jitter_ms`, `packet_loss_pct`,
`download_mbps`, `upload_mbps`, `download_bytes`, `upload_bytes`,
`download_elapsed_ms`, `upload_elapsed_ms`, `dl_loaded_latency_ms`,
`ul_loaded_latency_ms`, `isp`, `external_ip`, `internal_ip`, `interface`,
`result_url`, `duration_s`, `raw_json` (verbatim back-end payload).
Round records carry the same time stamps plus `n_planned/n_ok/n_fail`,
`round_duration_s` and `stats[metric] = {mean, median, min, max, std, n}` over
the endpoints that succeeded.

### When files are written (no data loss on crash / power failure)

1. **After every single test** the result row is committed to
   `speedtests.sqlite3` (the system of record) and appended to `results.jsonl`.
   The round row is created when the round starts and its statistics are filled
   in when the last endpoint finishes, so even a half-finished round is on disk.
2. **"Refresh output files every N tests | rounds"** (Setup ▸ Outputs;
   `export_every_n` / `export_every_unit` in the config, default: every 1 test)
   rewrites `<name>_c<id>.json`, `_results.csv`, `_rounds.csv` and `.vszh5`
   from the database, so those files always hold the complete data set as of the
   last refresh. Each file is written to `<file>.part` first and then atomically
   renamed over the old one, so Veusz or a script reading the file never sees a
   truncated file. When the unit is *tests* and the N-th test is the last of a
   round, the refresh is deferred by a second or two until the round average has
   been computed, so `avg/*` never lags `raw/*`. `0` = write only at the end.
   A refresh of a 12-test campaign takes well under 0.1 s; a months-long campaign
   with tens of thousands of tests takes a few seconds, so use a larger N there.
3. **At the end** (finished, stopped, or window closed while running) the same
   stable files are written a final time with `complete=true`.
4. If the program is killed, the next campaign started against the same database
   flags the old one `interrupted`; nothing is lost — *Tools ▸ Re-export from
   database…* (or `--reexport`) regenerates every file from SQLite.

Configs written by versions ≤ 1.1.1 with `export_every_n_rounds` are migrated
automatically (unit = rounds).

## Veusz file layout

Written directly with h5py in Veusz's own HDF5 save format (no Veusz
installation needed to write it; verified to load and render in Veusz 4.2.1).
Open it with File → Open in Veusz, or `veusz file.vszh5`.

Datasets (Data → Edit in Veusz), all tagged so they can be filtered:

```
raw/ep00_<slug>/time_local, time_utc      Veusz date datasets (x axes)
raw/ep00_<slug>/epoch_s, ts_utc_iso, ts_local_iso, utc_offset_s, round_id, ok, error
raw/ep00_<slug>/download_mbps, upload_mbps, latency_ms, jitter_ms, packet_loss_pct,
                dl_loaded_latency_ms, ul_loaded_latency_ms, download_bytes, upload_bytes,
                download_elapsed_ms, upload_elapsed_ms, duration_s
raw/ep01_.../…                            one group per endpoint (tag: raw)
raw/all/…  (+ endpoint, endpoint_key, endpoint_index, server_location, external_ip)
                                          every raw test combined, in time order (tag: raw)
avg/time_local, avg/time_utc, avg/epoch_s, ts_*_iso, round_seq, round_id, n_planned, n_ok, n_fail
avg/<metric>            round mean with symmetric error = std (tag: averaged)
avg/<metric>_std, _median, _min, _max, _n    separate arrays
meta/campaign_json, meta/endpoint_labels, meta/endpoint_keys, meta/endpoint_slugs, meta/generator
```

Pages: `page_download`, `page_upload`, `page_latency`, `page_jitter`,
`page_packet_loss`, `page_loaded_latency` (one large graph each, raw traces in
the same colours as the GUI plus the bold "Round average ± std" trace) and
`page_overview` (the 3×2 grid). The x axes are Veusz `datetime` axes; choose
local or UTC with "Veusz time axis" / `--time-axis`. Both time arrays are always
present so you can re-point any plot.

## Notes

* Failed tests are stored (with `ok = 0` and the error text) but excluded from
  round averages and plotted as gaps.
* Round time stamps are the round start; each raw result has its own stamp.
* Endpoints are tested back-to-back, so a round with many endpoints takes
  roughly 30–45 s per Ookla endpoint. The Setup summary warns when the
  interval is shorter than a round.
* Safe degradation: missing pyqtgraph → plots tab shows a hint; missing h5py →
  Veusz export skipped with a log error; missing back-end → clear status-bar
  message and refusal to start.
