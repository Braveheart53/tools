# ISP Speed Monitor — Packaging, Distribution and C++ Port Plan

| Field | Value |
|---|---|
| Document version | 1.0.2 |
| Status | IN PROGRESS — Step 1 delivered in script 1.3.0 (see docs/PROGRESS.md) |
| Applies to | isp_speed_monitor.py 1.2.0 (bundle 1.6.x) and later |
| Product name | ISP Speed Monitor |
| Publisher | Adaptive Electrodynamics LLC dba AdaptEd |
| Author | William W. Wallace — adaptive.electrodynamics@gmail.com (subject: ISP speed test feedback and support) |
| Editions | Full (licensed, distribution restricted) and Demo (freely distributable, feature-limited) |

Revision history (newest first)

| Version | Date | Change |
|---|---|---|
| 1.0.2 | 2026-10-03 | §4 Step 2/4: explicit per-component install dialog flow (ask, show links, automatic or manual install, wait for user, verify, continue; bundled components only announced). |
| 1.0.1 | 2026-10-03 | Publisher corrected to Adaptive Electrodynamics LLC dba AdaptEd; author e-mail, no phone; Step 1 marked delivered; author-block open item closed. |
| 1.0.0 | 2026-09-06 | Initial plan: decisions, licence constraints, prerequisite installers (Ookla, LibreSpeed, Veusz), Linux DEB/RPM, Windows EXE/MSI, C++23 port, Demo edition limits, release checks. |

---

## 1. Decisions already taken

| Topic | Decision |
|---|---|
| Ookla Speedtest CLI | Never bundled. Installer dialog downloads/installs it from Ookla's own channels, shows Ookla's EULA for the user to accept, waits for completion, verifies, then continues. A commercial Ookla licence will be obtained before any for-profit distribution. |
| LibreSpeed CLI | Bundled (LGPL-3.0; notices and source offer included). |
| Veusz | Optional install-time download of the latest GitHub release, checked by default; success verified by `veusz --version` and a headless render of a bundled sample `.vszh5`. Non-fatal on failure (Retry / Skip / continue). Never linked into the product (GPL); launched as an external tool only. |
| Windows build infrastructure | Local build scripts only (`build_windows.ps1`, `build_windows_cpp.ps1`). No interaction with any source repository. |
| Windows code signing | EV code-signing certificate from a public CA, applied with `signtool`. A step-by-step acquisition guide is delivered before the first Windows build (Step 4). |
| Linux package signing | GPG detached signatures and signed repository metadata using keys supplied by the publisher; keys are passed to the scripts by key ID and never stored with the sources. |
| C++ plotting | Custom QPainter widget. No Qwt, no Qt Charts/Qt Graphs (GPL/commercial), no QCustomPlot. |
| Step ordering | Best build-and-test flow, not credit optimisation. |
| EULAs | Full edition: standard proprietary EULA (licence grant, restrictions on redistribution/reverse engineering, IP, limited warranty, limitation of liability, termination, governing law). Demo edition: freely distributable demo EULA (no fee, redistribution of the unmodified installer permitted, no warranty, feature limits disclosed). Both drafted from the customary proprietary/demo EULA structure and flagged for legal review before sale. |

Author block (closed 2026-10-03): William W. Wallace — Adaptive Electrodynamics LLC dba AdaptEd, e-mail only (no phone); About dialog mailto pre-fills the subject "ISP speed test feedback and support".

## 2. Licence constraints that shape the build

| Component | Licence | Consequence |
|---|---|---|
| Ookla Speedtest CLI | Proprietary; personal, non-commercial use only without a commercial agreement | Not bundled; user installs and accepts EULA at install time. |
| librespeed-cli | LGPL-3.0 | Bundled with notice and source offer. |
| PySide6 / Qt 6 (Core, Gui, Widgets, Sql) | LGPL v3 | Closed source allowed if Qt remains a replaceable shared library: PyInstaller one-folder only (never one-file); C++ linked dynamically. |
| Qt Charts, Qt Graphs, QCustomPlot | GPL v3 / commercial | Not used. |
| pyqtgraph, numpy, h5py, HDF5, HighFive, SQLite | MIT / BSD / Boost / public domain | Notices only. |
| SQLCipher (demo DB encryption) | BSD-style | Notices only. |
| Veusz | GPL | External program, downloaded separately, never linked. |

Every installer ships `THIRD_PARTY_NOTICES.txt` and a CycloneDX SBOM.

## 3. Editions

### 3.1 Full edition
All features as in the current Python application.

### 3.2 Demo edition (built after the Full release candidate)
Identical code base; limits are compiled in through an `EDITION` build constant (not a runtime setting) so the same installer framework, scripts and tests are reused.

| # | Limit | Implementation |
|---|---|---|
| 1 | Campaign duration capped at 3 hours | Config validation and scheduler hard stop; duration widgets clamp to 3 h. |
| 2 | "Refresh output files every N tests/rounds" disabled | Widgets greyed out, value forced to 0 (write at end only). |
| 3 | Database encrypted, not user-readable | SQLCipher (`sqlcipher3` in Python; SQLite3 Multiple Ciphers or SQLCipher via Qt SQL plugin in C++) with an embedded, obfuscated key; Tools ▸ Re-export from database disabled. Note: an embedded key deters casual access only. |
| 4 | Export to CSV disabled | Checkbox greyed out and forced off. |
| 5 | JSONL appending disabled | Checkbox greyed out and forced off. |
| 6 | Fixed interval limited to 15 min – 3 h in 15-minute steps | Spin box range 15–180 min, single step 15, validated on load. |
| 7 | "N random tests per window" disabled | Mode greyed out. |
| 8 | Random-gap mode fixed: campaign length 3 h, gap 30 min | Fields shown read-only with those values. |

JSON export and Veusz export at campaign end remain available in the Demo. Demo and Full installers use different MSI UpgradeCodes / package names so both can be installed side by side, with a Demo → Full upgrade path that migrates the config and, if the user wishes, re-exports the demo campaigns to plain JSON before removal. The Demo About dialog and title bar show "Demo" and the limits.

## 4. Steps (build-and-test order)

### Step 1 — Application hardening (Python → 1.3.0)
- Per-OS data directories; log rotation; `--portable` mode.
- Sanitized export (removes IPs, MAC, ISP, result URLs, hostname, platform, paths, notes) and first-run privacy notice.
- Tool discovery: env var (`ISP_SPEED_MONITOR_OOKLA|LIBRESPEED|VEUSZ`) → installer-recorded path → PATH → bundled `tools/`.
- Tools ▸ Install/Update Ookla / LibreSpeed / Veusz…, Open latest export in Veusz, Render Veusz pages to PNG.
- `EDITION` constant and the Demo limit hooks (inactive in Full).
- Test suite (pytest: DB, exports, scheduler, crash safety), ruff, mypy, bandit, `pip-licenses`, SBOM.

### Step 2 — Prerequisite installer scripts (shared by all packages)

Install-time dialog contract (same on Windows MSI/EXE, DEB, RPM, and in Tools ▸ Install / update prerequisite tools):

| Component | Shipped in package? | Dialog behaviour |
|---|---|---|
| LibreSpeed CLI | Yes (bundled, LGPL) | Announced only ("included, version X"); no question asked. Verified with `--version` after copy. |
| Ookla Speedtest CLI | No (licence) | Ask "Install now?" with the download/licence link shown. Choices: **Install automatically** (winget / Ookla ZIP / packagecloud repo, Ookla EULA displayed for acceptance), **I will install it myself** (link opened; dialog waits on "Continue" until the user says it is done), **Skip**. |
| Veusz | No (GPL, external viewer) | Same three choices; automatic path downloads the latest GitHub release with SHA-256 check. Link to veusz.github.io shown. |

For every component that is not skipped the installer **waits**, then **verifies** (`speedtest --version`, `veusz --version` plus a headless render of the bundled sample `.vszh5`), records the path in `ISP_SPEED_MONITOR_<TOOL>` for the chosen scope, and only then **continues**. On a failed check it shows the reason and offers Retry / Install myself / Skip; the main installation is never blocked by an optional component. Headless/unattended installs (`/quiet`, debconf preseed, `--non-interactive`) take the answers from properties/preseed values and default to Skip.
- `install_prereqs.ps1` and `install_prereqs.sh`, common contract:
  `--component ookla|librespeed|veusz --scope user|system --version latest|<pin> --log <file>`; documented exit codes.
- Ookla: winget (`Ookla.Speedtest.CLI`) or Ookla ZIP on Windows; packagecloud apt/dnf repo on Linux; EULA shown; wait for completion; verify with `speedtest --version`.
- LibreSpeed: install bundled binary; verify with `librespeed-cli --version`.
- Veusz: GitHub releases API for latest (pinned fallback when offline), SHA-256 verification, silent install (Windows setup EXE) or tarball / pipx / distro package (Linux), verify with `veusz --version` and headless `veusz --export` of a bundled sample under an offscreen platform; set `ISP_SPEED_MONITOR_VEUSZ`.
- Environment variables and PATH: Windows `HKCU\Environment` or `HKLM\...\Session Manager\Environment` plus `WM_SETTINGCHANGE`; Linux `/etc/profile.d/isp-speed-monitor.sh` (system) or `~/.bashrc`, `~/.profile`, `~/.config/environment.d/` (user); idempotent marker lines.
- Tests: Ubuntu 22.04/24.04 and UBI 9 containers; PSScriptAnalyzer and Pester for PowerShell (run on the publisher's Windows machine).

### Step 3 — Linux packages (DEB, RPM)
- PyInstaller one-folder in glibc-matched containers (Ubuntu 22.04, UBI 9); xcb and wayland Qt plugins included.
- Layout `/opt/isp-speed-monitor/`, `/usr/bin/isp-speed-monitor`, `.desktop`, icons, `.vszh5` MIME, man page, docs.
- `isp-speed-monitor-setup` helper (whiptail/dialog, plain-prompt fallback) launched by postinst only when a TTY exists; debconf questions for non-interactive installs.
- GPG signing hooks (detached `.asc`, signed `Release`/`repomd.xml`); `lintian` and `rpmlint` clean.
- Matrix: install, upgrade, remove, purge; SIGKILL data-safety test on the packaged binary.

### Step 4 — Windows EXE and MSI
- Deliver `docs/EV_CODE_SIGNING_GUIDE.md` first (choosing a CA, organisation validation documents, hardware token vs cloud HSM, `signtool` usage, timestamping, testing SmartScreen).
- `build_windows.ps1`: PyInstaller one-folder, version resource, manifest (longPathAware, per-monitor DPI), `signtool` step with timestamp server, parameters for certificate thumbprint or HSM reference.
- WiX Toolset v5 sources: feature tree, prerequisite dialog (Ookla, LibreSpeed, Veusz checkboxes; scope radio user/system; progress, wait-and-verify, Retry/Skip), Burn bootstrapper EXE, per-user/per-machine installs, upgrade codes.
- The WiX project is validated here with a stub payload; the real payload is built by the publisher with the script and the log/artifact reviewed.

### Step 5 — Release candidates of the Python product (Full, then Demo)
- Full: clean-VM install matrix (Windows by publisher, Linux containers here), VirusTotal scan, PII review of default outputs, third-party notices, CHANGELOG, 7z bundle.
- Golden outputs (SQLite dump, JSON, CSV, `.vszh5` datasets) from simulated campaigns, kept for C++ conformance.
- Demo: same pipeline with `EDITION=demo`, plus tests that each limit is enforced (clamped values, disabled widgets, encrypted DB unreadable by plain sqlite3, CSV/JSONL absent).

### Step 6 — C++23 port (Qt 6.8 LTS or later), sub-deliveries
- 6a Core library: config, scheduler, SQLite schema (identical), JSON/CSV writers, HDF5 `.vszh5` writer (HDF5 C + HighFive) — GoogleTest conformance against Step 5 golden files.
- 6b Back-ends: QProcess drivers for Ookla and LibreSpeed, simulated back-end, timeouts and kill handling.
- 6c GUI: Qt Widgets, custom QPainter plot widget (time axis, multi-series, legend, themes), menus and About mirroring the Python app, `EDITION` compile-time definition.
- 6d Hardening: clang-tidy, cppcheck, ASan/UBSan, `-Wall -Wextra -Werror` clean on MSVC 2022, GCC 14, Clang 18; CMake 3.28+ presets; vcpkg manifest.
- Linux compiles/tests here; Windows via `build_windows_cpp.ps1` run by the publisher.

### Step 7 — C++ packaging (Full and Demo)
- CPack producing DEB, RPM, MSI and Burn EXE; reuse Step 2 scripts and Step 3/4 installer sources; `windeployqt` / `linuxdeployqt` staging; same signing hooks; same install matrix; second release candidates and 7z bundles.

## 5. Release checklist (applies to every installer)
- Licence audit and SBOM regenerated; notices complete.
- All binaries and scripts signed (Authenticode EV; GPG for Linux packages and repo metadata).
- VirusTotal scan clean; SmartScreen check on a clean Windows VM.
- Install, upgrade, remove, purge on clean systems; prerequisite dialog paths (each component, each scope, offline fallback, skip path) exercised.
- Crash-safety test (SIGKILL / power loss) on the packaged binary.
- PII review of default outputs; sanitized export verified.
- HiDPI, Wayland/X11, dark/light theme pass.
- Versions bumped (semantic), CHANGELOG and release notes written, 7z bundle built, no local paths or user names in any file.

## 6. Hand-offs required from the publisher
- EV certificate (thumbprint or HSM reference) and GPG key ID at build time.
- Running `build_windows.ps1` / `build_windows_cpp.ps1` and returning logs.
- Confirmation of the code-header author/contact lines for the commercial build.
- Legal review of both EULAs before sale.
