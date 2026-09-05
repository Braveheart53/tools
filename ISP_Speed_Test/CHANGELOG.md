# ISP Speed Monitor — CHANGELOG (bundle)

Semantic versioning (MAJOR.MINOR.PATCH); newest first. Each file also carries
its own version and revision history in its header.

## 1.6.0 — 2026-09-05
- `isp_speed_monitor.py` → 1.2.0: per-test write-through to SQLite + JSONL;
  "Refresh output files every N tests|rounds" rewrites JSON/CSV/Veusz to stable
  `<name>_c<id>.*` names atomically with a partial/final flag; interrupted
  campaigns detected; export on window close; Veusz label escaping.
- `README.md` → 1.6.0 (When files are written), `pyproject.toml` → 1.2.0,
  `REQUIRED_MODULES.txt` → 1.3.2, `sample_output/example_campaign_config.json` regenerated.

## 1.5.1 — 2026-09-05
- `isp_speed_monitor.py` → 1.1.1: Ookla selection flags made explicit
  (`--server-id=<id>`, `--host=<fqdn>`, none for auto); host names accepted in
  "Add by ID"; command line logged before each test; raw CLI error kept in the
  result; Tools ▸ Diagnose selected endpoint…
- `README.md` → 1.5.1 (Entering endpoints), `pyproject.toml` → 1.1.1, `REQUIRED_MODULES.txt` → 1.3.1

## 1.5.0 — 2026-09-04
- `isp_speed_monitor.py` → 1.1.0: menu bar (File / Campaign / View / Tools / Help);
  View ▸ Theme = System / Light / Dark with explicit Fusion palettes and Qt ≥ 6.8
  colour-scheme hint (light/dark now switch on system-dark Windows); Help ▸ About
  (author, contact, versions); Tools ▸ Re-export from database…, Write template
  config…, Check back-ends, Open log file; author contact block in header;
  `# %%%`/`# %%%%` Spyder cells throughout the GUI and back-end sections
- `tests/gui_smoke.py` → 1.1.0, `README.md` → 1.5.0, `REQUIRED_MODULES.txt` → 1.3.0, `pyproject.toml` → 1.1.0

## 1.4.1 — 2026-09-04
- `isp_speed_monitor.py` → 1.0.3: winget `Packages\Ookla.Speedtest.CLI_*` folder scanned one level deeper
- `README.md` → 1.4.1 (winget install location), `pyproject.toml` → 1.0.3

## 1.4.0 — 2026-09-04
- `isp_speed_monitor.py` → 1.0.2: Ookla CLI detection probes every `speedtest`
  on PATH and well-known install folders, skipping the python speedtest-cli shim
  of the same name; clearer status-bar message
- `requirements.txt` → 1.1.0, `environment.yml` → 1.1.0: speedtest-cli commented out
- `README.md` → 1.4.0 (troubleshooting note), `REQUIRED_MODULES.txt` → 1.2.0, `pyproject.toml` → 1.0.2

## 1.3.1 — 2026-09-04
- `README.md` → 1.3.0: Ookla Speedtest CLI install section (winget / zip, apt, yum, brew, first-run licence step)

## 1.3.0 — 2026-09-04
- Privacy scrub of the whole bundle: no local paths, user names, host names or
  project names in code, docs or samples
- `isp_speed_monitor.py` → 1.0.1 (author placeholder, QSettings org "ISPSpeedMonitor")
- `tests/gui_smoke.py`, `tests/render_in_veusz.sh` → 1.0.1 (relative / PATH-based defaults)
- `sample_output/` reduced to `example_campaign_config.json` (scrubbed) and `gui_plots_tab.png`
- `README.md` → 1.2.0, `REQUIRED_MODULES.txt` → 1.1.1

## 1.2.0 — 2026-09-04
- Added uv project: `pyproject.toml` 1.0.0, `.python-version`, `uv.lock`
- `README.md` → 1.1.0 (uv/mamba/pip install section, file index)
- `REQUIRED_MODULES.txt` → 1.1.0 (uv route)
- Added this CHANGELOG; archive now named `isp_speed_monitor_v<bundle>.7z`

## 1.1.0 — 2026-09-04
- Added `environment.yml` 1.0.0 (mamba/conda) and `REQUIRED_MODULES.txt` 1.0.0
- Delivery switched to a single 7z archive

## 1.0.0 — 2026-09-04
- Initial release: `isp_speed_monitor.py` 1.0.0, `README.md` 1.0.0,
  `requirements.txt` 1.0.0, `tests/gui_smoke.py` 1.0.0,
  `tests/render_in_veusz.sh` 1.0.0, `sample_output/`
