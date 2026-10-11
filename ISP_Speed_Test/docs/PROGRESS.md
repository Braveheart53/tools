# Build-plan progress log

| Field | Value |
|---|---|
| Document version | 1.0.1 |
| Plan | docs/BUILD_PLAN.md 1.0.1 |

Revision history (newest first)

| Version | Date | Change |
|---|---|---|
| 1.0.1 | 2026-10-11 | Step 1 follow-up: Veusz review fixes in script 1.3.1 (escaping, page renderer, render script). |
| 1.0.0 | 2026-10-03 | Created; Step 1 recorded as delivered. |

## Status by step

| Step | Status | Delivered in | Notes / resume point |
|---|---|---|---|
| 1 Application hardening | DONE (core) | script 1.3.1, bundle 1.7.2 | Author/publisher, EDITION + Demo limits, per-OS data dir, env-var/bundled tool discovery, Veusz discovery, sanitized export, Tools menu entries, `--sanitize`, `--portable`. Deferred to Step 5 (Demo RC): SQLCipher database encryption, first-run EULA/privacy notice, log rotation, pytest suite beyond selftest/gui_smoke, SBOM generation. |
| 2 Prerequisite installer scripts | NOT STARTED | — | Create `scripts/install_prereqs.ps1` and `scripts/install_prereqs.sh` per BUILD_PLAN §4 Step 2; the app already launches them from Tools ▸ Install / update prerequisite tools (`-Interactive` / `--interactive` flag). |
| 3 Linux packages (DEB, RPM) | NOT STARTED | — | PyInstaller one-folder in glibc-matched containers; CPack/fpm; GPG hooks. |
| 4 Windows EXE and MSI | NOT STARTED | — | Deliver `docs/EV_CODE_SIGNING_GUIDE.md` first; `build_windows.ps1`; WiX v5. |
| 5 Release candidates (Full, Demo) | NOT STARTED | — | Demo build = `EDITION = "demo"` set by the build script (`sed`/PowerShell replace on the constant) before PyInstaller. |
| 6 C++23 port | NOT STARTED | — | |
| 7 C++ packaging | NOT STARTED | — | |

## Verification record for Step 1 (2026-10-03)
- `py_compile -W error` clean; `--selftest` passes with stable exports; `--reexport --sanitize`
  produced `_sanitized` JSON/CSV/.vszh5 with host/platform redacted, config paths and notes
  blanked, result IPs/ISP/URL/raw cleared, while the stable files still hold the raw data.
- GUI smoke (offscreen) passes: 4 rounds, 9 screenshots.
- Demo build test (constant switched to `"demo"` in a scratch copy): title shows DEMO; CSV, JSONL,
  periodic refresh, per-window mode, end-at, run-until-stopped and Re-export disabled; interval
  spin 15–180 min step 15; random gap fixed 1800 s; `enforce_edition` clamps interval 200 s → 900 s,
  duration 0 → 10800 s, per-window → interval, random gap 5/9999 s → 1800/1800 s.
