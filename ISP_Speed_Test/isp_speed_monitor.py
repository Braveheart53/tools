#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# %% isp_speed_monitor.py Info
=============================================================================
ISP Speed Monitor — Scheduled / Random, Multi-Endpoint Speed-Test Logger
=============================================================================

Runs ISP throughput / latency tests against one or MANY endpoints (speed-test
servers) on a fixed, random, or "N-per-window" schedule for any campaign
length from minutes to months, and stores every measurement in:

  • SQLite database   (always on — the system of record, raw + per-round avg)
  • JSONL append logs (one JSON object per line; raw tests and round averages)
  • JSON campaign dump (complete, self-describing, written at end / on demand)
  • CSV (raw results + round summaries)
  • Veusz HDF5 document (.vszh5) — native Veusz save format written with h5py.
    Raw per-endpoint arrays, combined raw arrays and averaged arrays are ALL
    stored as separate Veusz datasets, and the document contains pages whose
    plots mirror the live GUI panels (Download, Upload, Latency, Jitter,
    Packet loss, Loaded latency + a 3x2 "overview" grid).

GUI: qtpy (PySide6 preferred) + pyqtgraph for fast live plots.
Headless mode (no display) uses the identical engine for servers / cron.

Every record carries: UTC ISO-8601 timestamp, local ISO-8601 timestamp with
offset, Unix epoch seconds, tz name, UTC offset, endpoint identity (backend,
server id, name, host, location), and every metric the backend reports.

# %%% Author Info
@Author: W. Wallace — NRAO / Green Bank Observatory
Phone  : +1 (304) 456-2216
Email  : wwallace@nrao.edu
Email2 : naval.antennas@gmail.com
Date   : 2026-09-04
Python : 3.12  (tested with PySide6 6.11 / pyqtgraph 0.13 / h5py 3.x; 3.10+ should work)
Version: 1.2.0
Deps   : qtpy, PySide6, pyqtgraph, numpy, h5py   (pip install -r requirements.txt)
         .vszh5 output verified to load and render in Veusz 4.2.1.
         Optional back-ends: Ookla Speedtest CLI (`speedtest` binary),
         LibreSpeed CLI (`librespeed-cli` binary), python `speedtest-cli`.

# %%% Usage
-----
GUI:
    python isp_speed_monitor.py

Headless campaign from a saved config (write one from the GUI: "Save Config"):
    python isp_speed_monitor.py --headless --config my_campaign.json

Write a template config:
    python isp_speed_monitor.py --make-config my_campaign.json

Re-export JSON / CSV / Veusz from an existing database (latest campaign
unless --campaign-id is given):
    python isp_speed_monitor.py --reexport ./speedtest_output/speedtests.sqlite3

Quick built-in self-test with the Simulated back-end (no network):
    python isp_speed_monitor.py --selftest

# %%% Back-end notes
-----------------
Ookla Speedtest CLI (recommended): https://www.speedtest.net/apps/cli
    `speedtest -L -f json` lists nearby servers; `speedtest --server-id=<id>`
    tests one server by id, `speedtest --host=<fqdn>` by host name, no flag =
    nearest server ("auto"). Bandwidth is reported in BYTES/s (converted to Mbit/s
    here). Ookla 1.2.x has no partial (download-only) switch.
LibreSpeed CLI: https://github.com/librespeed/speedtest-cli
    `librespeed-cli --list`, `--server <id> --json`, `--no-download/--no-upload`.
Python speedtest-cli (sivel): `pip install speedtest-cli` — fallback only,
    no jitter / packet-loss, frequently rate-limited (HTTP 403).
Simulated: synthetic diurnal data with noise — for exercising the pipeline.

Tests are run SEQUENTIALLY (never in parallel) so endpoints do not compete
for the same access link; the round average is therefore a spread-in-time
average over the selected endpoints.

# %%% Revision History (newest first)
--------------------------------------
1.2.0  2026-09-05  Data safety: every test is committed to SQLite and appended
                   to results.jsonl the moment it finishes (round row opened at
                   round start, statistics filled at round end). New Setup field
                   "Refresh output files every N tests|rounds"
                   (export_every_n / export_every_unit, default 1 test): JSON,
                   CSV and .vszh5 are rewritten from the database to STABLE
                   names <name>_c<id>.* via write-to-.part + atomic rename; the
                   files carry campaign_status / complete / n_rounds / n_results
                   (JSON generator block, Veusz meta/export_status). Export now
                   and re-export still write time-stamped snapshots. Campaigns
                   left 'running' by a kill are flagged 'interrupted' on the
                   next start; export also runs when the window is closed while
                   running. Veusz labels escape _ ^ { } so campaign names render
                   literally. Old configs with export_every_n_rounds migrate.
1.1.1  2026-09-05  Ookla endpoints: explicit `--server-id=<id>` for numeric ids,
                   `--host=<fqdn>` when a host name is entered, no flag for
                   'auto'; "Add by ID" accepts host names; the exact command line
                   is logged before every test and the raw CLI error is kept in
                   the result; Tools ▸ Diagnose selected endpoint… runs one raw
                   test and shows command / rc / stdout / stderr.
1.1.0  2026-09-04  Menu bar (File / Campaign / View / Tools / Help) added above
                   the tabbed interface. Theme is now a View ▸ Theme radio group
                   (System / Light / Dark) instead of a toolbar toggle: explicit
                   light and dark palettes on the Fusion style so the choice is
                   honoured on Windows with system dark mode, and Qt ≥ 6.8
                   colour-scheme hint so the title bar follows the theme too.
                   Help ▸ About shows author / contact / version / library
                   versions; Tools ▸ Re-export from database… ; author contact
                   block restored in the header; finer `# %%%` Spyder cells.
1.0.3  2026-09-04  winget package folder scan also looks one directory level
                   below %LOCALAPPDATA%/Microsoft/WinGet/Packages/Ookla.Speedtest.CLI_*.
1.0.2  2026-09-04  Ookla detection probes EVERY `speedtest` on PATH (+ winget /
                   Program Files / Homebrew folders) and picks the one reporting
                   "Ookla", so the python speedtest-cli shim of the same name
                   no longer shadows the real CLI; clearer status message.
1.0.1  2026-09-04  Scrubbed personal identifiers: neutral author placeholder,
                   QSettings organisation renamed to "ISPSpeedMonitor".
1.0.0  2026-09-04  Initial release: qtpy/PySide6 GUI, pyqtgraph live plots,
                   Ookla / LibreSpeed / python-speedtest / Simulated back-ends,
                   interval / random-gap / random-per-window scheduler,
                   SQLite + JSONL + JSON + CSV + native Veusz .vszh5 export,
                   headless mode, re-export, self-test.
"""

# ===========================================================================
# %% STANDARD-LIBRARY IMPORTS
# ===========================================================================
from __future__ import annotations

import os
import re
import sys
import csv
import html
import json
import math
import time
import random
import shutil
import signal
import socket
import sqlite3
import logging
import argparse
import datetime
import platform
import subprocess
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# ===========================================================================
# %% THIRD-PARTY IMPORTS (Qt binding is chosen BEFORE qtpy/pyqtgraph import)
# ===========================================================================
os.environ.setdefault("QT_API", "pyside6")

import numpy as np

try:
    import h5py
except ImportError:  # pragma: no cover
    h5py = None

from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtCore import Qt, Signal, Slot

try:
    import pyqtgraph as pg
except ImportError:  # pragma: no cover
    pg = None

__version__ = "1.2.0"
APP_NAME = "ISP Speed Monitor"
ORG_NAME = "ISPSpeedMonitor"
AUTHOR = "W. Wallace"
AUTHOR_ORG = "NRAO / Green Bank Observatory"
AUTHOR_CONTACT = {"Phone": "+1 (304) 456-2216", "Email": "wwallace@nrao.edu", "Email2": "naval.antennas@gmail.com"}
URL_OOKLA_CLI = "https://www.speedtest.net/apps/cli"
URL_LIBRESPEED_CLI = "https://github.com/librespeed/speedtest-cli/releases"
URL_VEUSZ = "https://veusz.github.io/"

# ===========================================================================
# %% USER-TUNABLE DEFAULTS
# ===========================================================================
DEFAULT_OUTPUT_DIR = os.path.join(os.path.abspath(os.getcwd()), "speedtest_output")
DB_FILENAME = "speedtests.sqlite3"          # single DB, many campaigns
RESULTS_JSONL = "results.jsonl"             # raw per-test append log
ROUNDS_JSONL = "rounds.jsonl"               # per-round average append log
LOG_FILENAME = "isp_speed_monitor.log"

DEFAULT_TEST_TIMEOUT_S = 120                # per endpoint test
DEFAULT_PAUSE_BETWEEN_ENDPOINTS_S = 2.0     # let the link settle between tests
DEFAULT_EXPORT_EVERY_N = 1                  # refresh output files every N tests/rounds (0 = only at end)
DEFAULT_EXPORT_UNIT = "tests"               # "tests" | "rounds"
EXPORT_UNITS = ("tests", "rounds")
MAX_TABLE_ROWS = 5000                       # GUI table cap (DB keeps everything)
PLOT_COLORS = [                             # tab10, per endpoint
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]
AVG_COLOR_LIGHT = "#000000"
AVG_COLOR_DARK = "#ffffff"

SECONDS_PER_UNIT = {
    "seconds": 1, "minutes": 60, "hours": 3600, "days": 86400,
    "weeks": 7 * 86400, "months (30 d)": 30 * 86400,
}

# ===========================================================================
# %% LOGGING
# ===========================================================================
logger = logging.getLogger("isp_speed_monitor")


def setup_logging(output_dir: str, level: int = logging.INFO) -> None:
    """Console + rotating-ish file logging (file is appended, never rotated
    automatically so long campaigns keep a single audit trail)."""
    logger.setLevel(level)
    logger.propagate = False            # never double-print through the root logger
    if logger.handlers:
        return
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    try:
        os.makedirs(output_dir, exist_ok=True)
        fh = logging.FileHandler(os.path.join(output_dir, LOG_FILENAME), encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError as exc:
        logger.warning("Could not open log file: %s", exc)


# ===========================================================================
# %% TIME HELPERS
# ===========================================================================
VEUSZ_EPOCH = datetime.datetime(2009, 1, 1)                     # Veusz date origin
UNIX_TO_VEUSZ_S = (datetime.datetime(1970, 1, 1) - VEUSZ_EPOCH).total_seconds()  # -1230768000


def now_stamps(t: Optional[float] = None) -> Dict[str, Any]:
    """Return a dict with UTC/local ISO strings, epoch, tz name and offset."""
    utc = (datetime.datetime.fromtimestamp(t, datetime.timezone.utc) if t is not None
           else datetime.datetime.now(datetime.timezone.utc))
    loc = utc.astimezone()
    return {
        "ts_utc": utc.isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "ts_local": loc.isoformat(timespec="milliseconds"),
        "epoch_s": utc.timestamp(),
        "tz_name": loc.tzname() or "",
        "utc_offset_s": int(loc.utcoffset().total_seconds()) if loc.utcoffset() else 0,
    }


def epoch_to_veusz(epoch_s: np.ndarray, offset_s: np.ndarray | float = 0.0) -> np.ndarray:
    """Unix epoch seconds -> Veusz datetime float (naive seconds since 2009-01-01).
    Pass the UTC offset (s) to obtain a *local wall-clock* Veusz time axis."""
    return np.asarray(epoch_s, dtype=float) + np.asarray(offset_s, dtype=float) + UNIX_TO_VEUSZ_S


def fmt_duration(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)
    if d:
        return f"{d}d {h:02d}:{m:02d}:{s:02d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def local_iso_to_epoch(text: str) -> Optional[float]:
    """Parse an ISO datetime typed by the user (local time if no offset)."""
    text = (text or "").strip()
    if not text:
        return None
    dt = datetime.datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.astimezone()  # interpret as local
    return dt.timestamp()


def slugify(text: str, maxlen: int = 32) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return (s or "x")[:maxlen]


# ===========================================================================
# %% DATA MODEL
# ===========================================================================
@dataclass
class Endpoint:
    backend: str                 # 'ookla' | 'librespeed' | 'pyspeedtest' | 'simulated'
    server_id: str
    name: str = ""
    host: str = ""
    location: str = ""
    country: str = ""

    @property
    def key(self) -> str:
        return f"{self.backend}:{self.server_id}"

    @property
    def label(self) -> str:
        loc = f" — {self.location}" if self.location else ""
        return f"[{self.backend}] {self.server_id} {self.name}{loc}"

    def slug(self, index: int) -> str:
        return f"ep{index:02d}_{slugify(self.name or self.host or self.server_id, 24)}"


@dataclass
class TestResult:
    endpoint_key: str
    backend: str
    server_id: str
    endpoint_name: str = ""               # user-given endpoint name from the config
    server_name: str = ""                 # actual server used (Ookla: sponsor name)
    server_host: str = ""
    server_location: str = ""
    ts_utc: str = ""
    ts_local: str = ""
    epoch_s: float = 0.0
    tz_name: str = ""
    utc_offset_s: int = 0
    ok: bool = False
    error: str = ""
    latency_ms: float = math.nan          # idle ping
    jitter_ms: float = math.nan
    packet_loss_pct: float = math.nan
    download_mbps: float = math.nan
    upload_mbps: float = math.nan
    download_bytes: float = math.nan
    upload_bytes: float = math.nan
    download_elapsed_ms: float = math.nan
    upload_elapsed_ms: float = math.nan
    dl_loaded_latency_ms: float = math.nan  # Ookla download.latency.iqm
    ul_loaded_latency_ms: float = math.nan
    isp: str = ""
    external_ip: str = ""
    internal_ip: str = ""
    interface: str = ""
    result_url: str = ""
    duration_s: float = math.nan            # wall-clock time of the test call
    raw_json: str = ""                      # verbatim back-end payload

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k, v in d.items():
            if isinstance(v, float) and math.isnan(v):
                d[k] = None
        return d


METRICS = ["download_mbps", "upload_mbps", "latency_ms", "jitter_ms",
           "packet_loss_pct", "dl_loaded_latency_ms", "ul_loaded_latency_ms"]
METRIC_LABELS = {
    "download_mbps": ("Download", "Mbit/s"),
    "upload_mbps": ("Upload", "Mbit/s"),
    "latency_ms": ("Idle latency", "ms"),
    "jitter_ms": ("Jitter", "ms"),
    "packet_loss_pct": ("Packet loss", "%"),
    "dl_loaded_latency_ms": ("Loaded latency (download)", "ms"),
    "ul_loaded_latency_ms": ("Loaded latency (upload)", "ms"),
}
STATS = ["mean", "median", "min", "max", "std"]


@dataclass
class RoundSummary:
    seq: int
    ts_utc: str
    ts_local: str
    epoch_s: float
    tz_name: str
    utc_offset_s: int
    n_planned: int
    n_ok: int
    n_fail: int
    round_duration_s: float
    stats: Dict[str, Dict[str, float]] = field(default_factory=dict)  # metric -> stat -> value

    def get(self, metric: str, stat: str = "mean") -> float:
        return self.stats.get(metric, {}).get(stat, math.nan)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["stats"] = {m: {s: (None if (isinstance(v, float) and math.isnan(v)) else v)
                          for s, v in sd.items()} for m, sd in self.stats.items()}
        return d


def summarize_round(seq: int, results: List[TestResult], started_epoch: float,
                    n_planned: int) -> RoundSummary:
    """Mean/median/min/max/std over the successful tests of one round."""
    stamps = now_stamps(started_epoch)
    ok = [r for r in results if r.ok]
    stats: Dict[str, Dict[str, float]] = {}
    for m in METRICS:
        vals = np.array([getattr(r, m) for r in ok], dtype=float)
        vals = vals[np.isfinite(vals)]
        if vals.size:
            stats[m] = {"mean": float(vals.mean()), "median": float(np.median(vals)),
                        "min": float(vals.min()), "max": float(vals.max()),
                        "std": float(vals.std(ddof=0)), "n": float(vals.size)}
        else:
            stats[m] = {s: math.nan for s in STATS} | {"n": 0.0}
    return RoundSummary(seq=seq, ts_utc=stamps["ts_utc"], ts_local=stamps["ts_local"],
                        epoch_s=stamps["epoch_s"], tz_name=stamps["tz_name"],
                        utc_offset_s=stamps["utc_offset_s"], n_planned=n_planned,
                        n_ok=len(ok), n_fail=len(results) - len(ok),
                        round_duration_s=time.time() - started_epoch, stats=stats)


@dataclass
class ScheduleConfig:
    mode: str = "interval"          # 'interval' | 'random_gap' | 'random_per_window'
    interval_s: float = 900.0       # interval mode
    min_gap_s: float = 300.0        # random_gap mode
    max_gap_s: float = 1800.0
    window_s: float = 3600.0        # random_per_window mode
    per_window: int = 4
    duration_s: float = 86400.0     # 0 -> run until stopped
    end_at_local: str = ""          # optional ISO end datetime (overrides duration)
    start_at_local: str = ""        # optional ISO start datetime ('' -> now)
    first_test_immediately: bool = True
    random_seed: Optional[int] = None


@dataclass
class CampaignConfig:
    name: str = "campaign"
    output_dir: str = DEFAULT_OUTPUT_DIR
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    schedule: Dict[str, Any] = field(default_factory=lambda: asdict(ScheduleConfig()))
    ookla_exe: str = ""             # '' -> search PATH
    librespeed_exe: str = ""
    test_download: bool = True      # honoured by librespeed / pyspeedtest only
    test_upload: bool = True
    test_timeout_s: int = DEFAULT_TEST_TIMEOUT_S
    pause_between_endpoints_s: float = DEFAULT_PAUSE_BETWEEN_ENDPOINTS_S
    write_jsonl: bool = True
    export_json: bool = True
    export_csv: bool = True
    export_veusz: bool = True
    veusz_time_axis: str = "local"  # 'local' | 'utc'
    export_every_n: int = DEFAULT_EXPORT_EVERY_N     # refresh JSON/CSV/Veusz every N ... (0 = only at end)
    export_every_unit: str = DEFAULT_EXPORT_UNIT     # "tests" | "rounds"
    notes: str = ""

    # ---- (de)serialisation -------------------------------------------------
    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CampaignConfig":
        cfg = cls()
        for k, v in d.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        if "export_every_n_rounds" in d and "export_every_n" not in d:   # <= 1.1.1 configs
            cfg.export_every_n, cfg.export_every_unit = int(d["export_every_n_rounds"] or 0), "rounds"
        if cfg.export_every_unit not in EXPORT_UNITS:
            cfg.export_every_unit = DEFAULT_EXPORT_UNIT
        sched = asdict(ScheduleConfig())
        sched.update(cfg.schedule or {})
        cfg.schedule = sched
        return cfg

    @classmethod
    def load(cls, path: str) -> "CampaignConfig":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.to_json())

    def endpoint_objs(self) -> List[Endpoint]:
        return [Endpoint(**{k: e.get(k, "") for k in ("backend", "server_id", "name", "host",
                                                        "location", "country")})
                for e in self.endpoints]

    def schedule_obj(self) -> ScheduleConfig:
        return ScheduleConfig(**self.schedule)


# ===========================================================================
# %% SPEED-TEST BACK-ENDS
# ===========================================================================
def _popen_kwargs() -> Dict[str, Any]:
    kw: Dict[str, Any] = {}
    if os.name == "nt":
        kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    return kw


def _find_exe(candidates: List[str], explicit: str = "") -> str:
    if explicit:
        return explicit if os.path.isfile(explicit) else ""
    for c in candidates:
        p = shutil.which(c)
        if p:
            return p
    return ""


def _all_on_path(names: List[str]) -> List[str]:
    """Every executable matching `names` anywhere on PATH (not just the first),
    followed by well-known install folders. Order = PATH order."""
    found: List[str] = []
    dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d]
    if os.name == "nt":
        la = os.environ.get("LOCALAPPDATA", "")
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        extra = [os.path.join(la, "Microsoft", "WinGet", "Links"),
                 os.path.join(pf, "Ookla", "Speedtest CLI"),
                 r"C:\ProgramData\chocolatey\bin", r"C:\Tools\speedtest"]
        # winget package folders: %LOCALAPPDATA%\Microsoft\WinGet\Packages\Ookla.Speedtest.CLI_*
        pk = os.path.join(la, "Microsoft", "WinGet", "Packages")
        if la and os.path.isdir(pk):
            for d in os.listdir(pk):
                if d.startswith("Ookla.Speedtest.CLI"):
                    top = os.path.join(pk, d)
                    extra.append(top)                      # speedtest.exe normally sits here
                    extra += [os.path.join(top, sub) for sub in os.listdir(top)
                              if os.path.isdir(os.path.join(top, sub))]   # ...or one level down
        dirs += extra
    else:
        dirs += ["/usr/bin", "/usr/local/bin", "/opt/homebrew/bin", os.path.expanduser("~/.local/bin")]
    seen = set()
    for d in dirs:
        for n in names:
            fp = os.path.join(d, n)
            key = os.path.normcase(os.path.abspath(fp))
            if key not in seen and os.path.isfile(fp) and os.access(fp, os.X_OK):
                seen.add(key)
                found.append(fp)
    return found


_OOKLA_EXE_CACHE: Dict[str, str] = {}   # exe path -> "--version" text (probed once)


def _probe_version(exe: str, timeout: float = 15) -> str:
    if exe not in _OOKLA_EXE_CACHE:
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=timeout, **_popen_kwargs())
            _OOKLA_EXE_CACHE[exe] = (r.stdout + r.stderr).strip()
        except Exception as exc:
            _OOKLA_EXE_CACHE[exe] = f"<cannot run: {exc}>"
    return _OOKLA_EXE_CACHE[exe]


def find_ookla_exe(explicit: str = "") -> Tuple[str, str]:
    """Locate the *real* Ookla CLI. The python `speedtest-cli` package installs a
    `speedtest`/`speedtest.exe` shim of the same name (typically first on PATH in
    a conda/venv), so every candidate is probed with --version and the first one
    reporting "Ookla" wins. Returns (path, note); path == "" if none found."""
    if explicit:
        if not os.path.isfile(explicit):
            return "", f"Ookla exe not found: {explicit}"
        txt = _probe_version(explicit)
        return (explicit, txt.splitlines()[0]) if "Ookla" in txt else ("", f"{explicit} is not the Ookla CLI (found: {txt[:60]!r})")
    cands = _all_on_path(["speedtest", "speedtest.exe"] if os.name == "nt" else ["speedtest"])
    shadowed: List[str] = []
    for c in cands:
        txt = _probe_version(c)
        if "Ookla" in txt:
            note = txt.splitlines()[0]
            if shadowed:
                note += f"  (note: {shadowed[0]} on PATH is the python speedtest-cli shim, skipped)"
            return c, note
        shadowed.append(c)
    if shadowed:
        return "", (f"{shadowed[0]} is not the Ookla CLI (python speedtest-cli shim?). Install the Ookla CLI "
                    f"(README) or set its full path in 'Ookla exe'.")
    return "", "Ookla `speedtest` executable not found (install it or set its path in 'Ookla exe')"


class BackendBase:
    key = "base"
    label = "Base"
    supports_partial = False

    def __init__(self, exe_path: str = ""):
        self.exe_path = exe_path
        self._proc: Optional[subprocess.Popen] = None
        self._abort = False

    # -- process helpers ------------------------------------------------------
    def _run_cmd(self, args: List[str], timeout: float) -> Tuple[int, str, str]:
        self._abort = False
        self._proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True, encoding="utf-8", errors="replace",
                                      **_popen_kwargs())
        try:
            out, err = self._proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            out, err = self._proc.communicate()
            raise TimeoutError(f"timed out after {timeout:.0f} s")
        finally:
            rc = self._proc.returncode
            self._proc = None
        if self._abort:
            raise RuntimeError("aborted")
        return rc, out or "", err or ""

    def abort(self) -> None:
        self._abort = True
        p = self._proc
        if p is not None:
            try:
                p.kill()
            except Exception:
                pass

    # -- interface ------------------------------------------------------------
    def available(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def list_servers(self) -> List[Endpoint]:
        raise NotImplementedError

    def run_test(self, ep: Endpoint, do_download: bool, do_upload: bool,
                 timeout: float) -> TestResult:
        raise NotImplementedError

    def _new_result(self, ep: Endpoint) -> TestResult:
        st = now_stamps()
        return TestResult(endpoint_key=ep.key, endpoint_name=ep.name, backend=ep.backend, server_id=str(ep.server_id),
                          server_name=ep.name, server_host=ep.host, server_location=ep.location,
                          ts_utc=st["ts_utc"], ts_local=st["ts_local"], epoch_s=st["epoch_s"],
                          tz_name=st["tz_name"], utc_offset_s=st["utc_offset_s"])


def _json_lines(text: str) -> List[Dict[str, Any]]:
    """Parse every line that is a JSON object (Ookla mixes log lines in)."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


# %%% Ookla Speedtest CLI back-end
class OoklaBackend(BackendBase):
    key = "ookla"
    label = "Ookla Speedtest CLI"
    supports_partial = False

    def exe(self) -> str:
        return find_ookla_exe(self.exe_path)[0]

    def available(self) -> Tuple[bool, str]:
        exe, note = find_ookla_exe(self.exe_path)
        return (bool(exe), note)

    def list_servers(self) -> List[Endpoint]:
        exe = self.exe()
        rc, out, err = self._run_cmd([exe, "--accept-license", "--accept-gdpr", "-L", "-f", "json"], 60)
        eps: List[Endpoint] = []
        for obj in _json_lines(out):
            if obj.get("type") == "serverList":
                for s in obj.get("servers", []):
                    eps.append(Endpoint("ookla", str(s.get("id")), s.get("name", ""), s.get("host", ""),
                                        s.get("location", ""), s.get("country", "")))
        if not eps:
            raise RuntimeError(f"no servers parsed (rc={rc}): {err.strip()[:200]}")
        return eps

    @staticmethod
    def selector_args(server_id: str, host: str = "") -> List[str]:
        """Translate an endpoint into Ookla CLI selection flags.

        * ``auto`` / blank         -> no flag (Ookla picks the nearest server)
        * digits, e.g. ``14229``   -> ``--server-id=14229``
        * anything else, e.g. ``ashburn.va.speedtest.frontier.com`` -> ``--host=<fqdn>``
          (the ``host`` argument wins when the id is not numeric)
        """
        sid = (server_id or "").strip()
        if sid == "" or sid.lower() == "auto":
            return []
        if sid.isdigit():
            return [f"--server-id={sid}"]
        h = (host or sid).strip()
        h = re.sub(r"^[a-z]+://", "", h).split("/")[0].split(":")[0]     # tolerate URLs / ports
        return [f"--host={h}"]

    def build_test_args(self, ep: Endpoint) -> List[str]:
        exe = self.exe()
        if not exe:
            raise RuntimeError(find_ookla_exe(self.exe_path)[1])
        return [exe, "--accept-license", "--accept-gdpr", "-f", "json", "-p", "no"] + self.selector_args(ep.server_id, ep.host)

    def run_test(self, ep: Endpoint, do_download: bool, do_upload: bool, timeout: float) -> TestResult:
        r = self._new_result(ep)
        t0 = time.time()
        try:
            args = self.build_test_args(ep)
            logger.info("  ookla cmd: %s", subprocess.list2cmdline(args[1:]))
            rc, out, err = self._run_cmd(args, timeout)
            payload = None
            for obj in _json_lines(out + "\n" + err):
                if obj.get("type") == "result":
                    payload = obj
                elif obj.get("type") == "log" and obj.get("level") == "error":
                    r.error = obj.get("message", "")
            if payload is None:
                tail = (err.strip() or out.strip())[:300]
                raise RuntimeError(r.error or f"no result from Ookla CLI (rc={rc}): {tail or 'no output'}")
            r.raw_json = json.dumps(payload, separators=(",", ":"))
            ping = payload.get("ping", {}) or {}
            dl = payload.get("download", {}) or {}
            ul = payload.get("upload", {}) or {}
            srv = payload.get("server", {}) or {}
            iface = payload.get("interface", {}) or {}
            r.latency_ms = float(ping.get("latency", math.nan))
            r.jitter_ms = float(ping.get("jitter", math.nan))
            pl = payload.get("packetLoss")
            r.packet_loss_pct = float(pl) if pl is not None else math.nan
            if "bandwidth" in dl:
                r.download_mbps = dl["bandwidth"] * 8.0 / 1e6
                r.download_bytes = float(dl.get("bytes", math.nan))
                r.download_elapsed_ms = float(dl.get("elapsed", math.nan))
                r.dl_loaded_latency_ms = float((dl.get("latency") or {}).get("iqm", math.nan))
            if "bandwidth" in ul:
                r.upload_mbps = ul["bandwidth"] * 8.0 / 1e6
                r.upload_bytes = float(ul.get("bytes", math.nan))
                r.upload_elapsed_ms = float(ul.get("elapsed", math.nan))
                r.ul_loaded_latency_ms = float((ul.get("latency") or {}).get("iqm", math.nan))
            r.server_name = srv.get("name", r.server_name)
            r.server_host = srv.get("host", r.server_host)
            r.server_location = ", ".join(x for x in (srv.get("location", ""), srv.get("country", "")) if x)
            r.server_id = str(srv.get("id", r.server_id))
            r.isp = payload.get("isp", "")
            r.external_ip = iface.get("externalIp", "")
            r.internal_ip = iface.get("internalIp", "")
            r.interface = iface.get("name", "")
            r.result_url = (payload.get("result") or {}).get("url", "")
            r.ok = True
            r.error = ""
        except Exception as exc:
            r.ok = False
            r.error = r.error or str(exc)
        r.duration_s = time.time() - t0
        return r


# %%% LibreSpeed CLI back-end
class LibreSpeedBackend(BackendBase):
    key = "librespeed"
    label = "LibreSpeed CLI"
    supports_partial = True

    def exe(self) -> str:
        return _find_exe(["librespeed-cli", "librespeed-cli.exe"], self.exe_path)

    def available(self) -> Tuple[bool, str]:
        exe = self.exe()
        if not exe:
            return False, "`librespeed-cli` executable not found"
        try:
            rc, out, err = self._run_cmd([exe, "--version"], 15)
            return True, (out + err).strip().splitlines()[0] if (out + err).strip() else exe
        except Exception as exc:
            return False, str(exc)

    def list_servers(self) -> List[Endpoint]:
        rc, out, err = self._run_cmd([self.exe(), "--list"], 60)
        eps: List[Endpoint] = []
        for line in out.splitlines():
            m = re.match(r"^\s*(\d+):\s*(.*?)\s*(?:\((.*)\))?\s*$", line)
            if m:
                eps.append(Endpoint("librespeed", m.group(1), m.group(2), m.group(3) or ""))
        if not eps:
            raise RuntimeError(f"no servers parsed (rc={rc}): {err.strip()[:200]}")
        return eps

    def run_test(self, ep: Endpoint, do_download: bool, do_upload: bool, timeout: float) -> TestResult:
        r = self._new_result(ep)
        t0 = time.time()
        args = [self.exe(), "--json", "--server", str(ep.server_id)]
        if not do_download:
            args.append("--no-download")
        if not do_upload:
            args.append("--no-upload")
        try:
            rc, out, err = self._run_cmd(args, timeout)
            start = out.find("[") if out.lstrip().startswith("[") else out.find("{")
            if start < 0:
                raise RuntimeError(f"no JSON (rc={rc}): {err.strip()[:200]}")
            payload = json.loads(out[start:])
            if isinstance(payload, list):
                payload = payload[0] if payload else {}
            r.raw_json = json.dumps(payload, separators=(",", ":"))
            r.latency_ms = float(payload.get("ping", math.nan))
            r.jitter_ms = float(payload.get("jitter", math.nan))
            if do_download:
                r.download_mbps = float(payload.get("download", math.nan))
                r.download_bytes = float(payload.get("bytes_received", math.nan))
            if do_upload:
                r.upload_mbps = float(payload.get("upload", math.nan))
                r.upload_bytes = float(payload.get("bytes_sent", math.nan))
            srv = payload.get("server", {}) or {}
            cli = payload.get("client", {}) or {}
            r.server_name = srv.get("name", r.server_name)
            r.server_host = srv.get("url", r.server_host)
            r.isp = cli.get("org", cli.get("isp", ""))
            r.external_ip = cli.get("ip", "")
            r.result_url = payload.get("share", "")
            r.ok = True
        except Exception as exc:
            r.ok = False
            r.error = str(exc)
        r.duration_s = time.time() - t0
        return r


# %%% python speedtest-cli back-end (fallback)
class PySpeedtestBackend(BackendBase):
    key = "pyspeedtest"
    label = "Python speedtest-cli (fallback)"
    supports_partial = True

    def available(self) -> Tuple[bool, str]:
        try:
            import speedtest  # noqa: F401
            return True, f"speedtest-cli {getattr(speedtest, '__version__', '?')}"
        except ImportError:
            return False, "python module `speedtest` not installed (pip install speedtest-cli)"

    def list_servers(self) -> List[Endpoint]:
        import speedtest
        st = speedtest.Speedtest(secure=True)
        servers = st.get_servers()
        eps: List[Endpoint] = []
        for dist in sorted(servers):
            for s in servers[dist]:
                eps.append(Endpoint("pyspeedtest", str(s["id"]), s.get("sponsor", ""), s.get("host", ""),
                                    s.get("name", ""), s.get("country", "")))
        return eps[:60]

    def run_test(self, ep: Endpoint, do_download: bool, do_upload: bool, timeout: float) -> TestResult:
        r = self._new_result(ep)
        t0 = time.time()
        try:
            import speedtest
            st = speedtest.Speedtest(secure=True, timeout=min(timeout, 60))
            if ep.server_id and ep.server_id != "auto":
                st.get_servers([int(ep.server_id)])
            st.get_best_server()
            if do_download:
                st.download()
            if do_upload:
                st.upload()
            d = st.results.dict()
            r.raw_json = json.dumps(d, separators=(",", ":"), default=str)
            r.latency_ms = float(d.get("ping", math.nan))
            if do_download:
                r.download_mbps = float(d.get("download", math.nan)) / 1e6
                r.download_bytes = float(d.get("bytes_received", math.nan))
            if do_upload:
                r.upload_mbps = float(d.get("upload", math.nan)) / 1e6
                r.upload_bytes = float(d.get("bytes_sent", math.nan))
            srv = d.get("server", {}) or {}
            cli = d.get("client", {}) or {}
            r.server_name = srv.get("sponsor", r.server_name)
            r.server_host = srv.get("host", r.server_host)
            r.server_location = ", ".join(x for x in (srv.get("name", ""), srv.get("country", "")) if x)
            r.isp = cli.get("isp", "")
            r.external_ip = cli.get("ip", "")
            r.result_url = d.get("share") or ""
            r.ok = True
        except Exception as exc:
            r.ok = False
            r.error = str(exc)
        r.duration_s = time.time() - t0
        return r


# %%% Simulated back-end (pipeline testing, no network)
class SimulatedBackend(BackendBase):
    """Synthetic diurnal traffic model — used by --selftest and for dry runs."""
    key = "simulated"
    label = "Simulated (no network)"
    supports_partial = True
    _SERVERS = [("1", "Sim Alpha (near)", "sim-a.example", "Knoxville, TN", "US", 940.0, 40.0, 6.0),
                ("2", "Sim Bravo (regional)", "sim-b.example", "Atlanta, GA", "US", 880.0, 38.0, 14.0),
                ("3", "Sim Charlie (far)", "sim-c.example", "Seattle, WA", "US", 610.0, 30.0, 62.0),
                ("4", "Sim Delta (flaky)", "sim-d.example", "Chicago, IL", "US", 700.0, 35.0, 28.0)]

    def available(self) -> Tuple[bool, str]:
        return True, "simulated"

    def list_servers(self) -> List[Endpoint]:
        return [Endpoint("simulated", *s[:5]) for s in self._SERVERS]

    def run_test(self, ep: Endpoint, do_download: bool, do_upload: bool, timeout: float) -> TestResult:
        r = self._new_result(ep)
        t0 = time.time()
        row = next((s for s in self._SERVERS if s[0] == str(ep.server_id)), self._SERVERS[0])
        base_dl, base_ul, base_lat = row[5], row[6], row[7]
        for _ in range(10):                       # ~1 s, abortable
            if self._abort:
                r.error = "aborted"
                r.duration_s = time.time() - t0
                return r
            time.sleep(0.1)
        hour = datetime.datetime.now().hour + datetime.datetime.now().minute / 60
        diurnal = 1.0 - 0.18 * math.sin(2 * math.pi * (hour - 6) / 24)  # slower in evening
        if row[0] == "4" and random.random() < 0.15:
            r.error = "simulated failure: socket timeout"
            r.duration_s = time.time() - t0
            return r
        r.download_mbps = max(1.0, random.gauss(base_dl * diurnal, base_dl * 0.05)) if do_download else math.nan
        r.upload_mbps = max(0.5, random.gauss(base_ul, base_ul * 0.06)) if do_upload else math.nan
        r.latency_ms = max(0.5, random.gauss(base_lat, base_lat * 0.08))
        r.jitter_ms = abs(random.gauss(1.5, 0.8))
        r.packet_loss_pct = 0.0 if random.random() < 0.85 else round(random.uniform(0.1, 2.5), 2)
        r.download_bytes = r.download_mbps * 1e6 / 8 * 10 if do_download else math.nan
        r.upload_bytes = r.upload_mbps * 1e6 / 8 * 10 if do_upload else math.nan
        r.download_elapsed_ms = 10000.0
        r.upload_elapsed_ms = 10000.0
        r.dl_loaded_latency_ms = r.latency_ms + abs(random.gauss(25, 10))
        r.ul_loaded_latency_ms = r.latency_ms + abs(random.gauss(15, 8))
        r.isp = "Simulated ISP"
        r.external_ip = "203.0.113.7"
        r.internal_ip = "192.168.1.20"
        r.interface = "sim0"
        r.raw_json = json.dumps({"type": "simulated", "server": row[0]})
        r.ok = True
        r.duration_s = time.time() - t0
        return r


BACKEND_CLASSES = {c.key: c for c in (OoklaBackend, LibreSpeedBackend, PySpeedtestBackend, SimulatedBackend)}


def make_backend(key: str, cfg: CampaignConfig) -> BackendBase:
    cls = BACKEND_CLASSES[key]
    exe = {"ookla": cfg.ookla_exe, "librespeed": cfg.librespeed_exe}.get(key, "")
    return cls(exe)


# ===========================================================================
# %% STORAGE — SQLite (system of record) + JSONL append logs
# ===========================================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY, name TEXT, created_utc TEXT, created_local TEXT,
    host TEXT, platform TEXT, script_version TEXT, config_json TEXT,
    finished_utc TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS endpoints (
    id INTEGER PRIMARY KEY, campaign_id INTEGER, idx INTEGER, backend TEXT, server_id TEXT,
    name TEXT, host TEXT, location TEXT, country TEXT,
    UNIQUE(campaign_id, backend, server_id));
CREATE TABLE IF NOT EXISTS rounds (
    id INTEGER PRIMARY KEY, campaign_id INTEGER, seq INTEGER, ts_utc TEXT, ts_local TEXT,
    epoch_s REAL, tz_name TEXT, utc_offset_s INTEGER, n_planned INTEGER, n_ok INTEGER,
    n_fail INTEGER, round_duration_s REAL, stats_json TEXT);
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY, campaign_id INTEGER, round_id INTEGER, endpoint_id INTEGER,
    endpoint_key TEXT, endpoint_name TEXT, backend TEXT, server_id TEXT, server_name TEXT, server_host TEXT,
    server_location TEXT, ts_utc TEXT, ts_local TEXT, epoch_s REAL, tz_name TEXT,
    utc_offset_s INTEGER, ok INTEGER, error TEXT, latency_ms REAL, jitter_ms REAL,
    packet_loss_pct REAL, download_mbps REAL, upload_mbps REAL, download_bytes REAL,
    upload_bytes REAL, download_elapsed_ms REAL, upload_elapsed_ms REAL,
    dl_loaded_latency_ms REAL, ul_loaded_latency_ms REAL, isp TEXT, external_ip TEXT,
    internal_ip TEXT, interface TEXT, result_url TEXT, duration_s REAL, raw_json TEXT);
CREATE INDEX IF NOT EXISTS ix_results_campaign ON results(campaign_id, epoch_s);
CREATE INDEX IF NOT EXISTS ix_rounds_campaign ON rounds(campaign_id, seq);
"""

RESULT_COLS = ["endpoint_key", "endpoint_name", "backend", "server_id", "server_name", "server_host", "server_location",
               "ts_utc", "ts_local", "epoch_s", "tz_name", "utc_offset_s", "ok", "error", "latency_ms",
               "jitter_ms", "packet_loss_pct", "download_mbps", "upload_mbps", "download_bytes",
               "upload_bytes", "download_elapsed_ms", "upload_elapsed_ms", "dl_loaded_latency_ms",
               "ul_loaded_latency_ms", "isp", "external_ip", "internal_ip", "interface", "result_url",
               "duration_s", "raw_json"]


def _nan_to_none(v):
    return None if (isinstance(v, float) and math.isnan(v)) else v


class SpeedDB:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(SCHEMA)
        have = {r[1] for r in self.conn.execute("PRAGMA table_info(results)")}
        for col, typ in (("endpoint_name", "TEXT"),):      # additive migrations
            if col not in have:
                self.conn.execute(f"ALTER TABLE results ADD COLUMN {col} {typ}")
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.commit()
            self.conn.close()
        except Exception:
            pass

    # -- writes ---------------------------------------------------------------
    def new_campaign(self, cfg: CampaignConfig) -> int:
        st = now_stamps()
        cur = self.conn.execute(
            "INSERT INTO campaigns(name, created_utc, created_local, host, platform, script_version, "
            "config_json, status) VALUES (?,?,?,?,?,?,?,?)",
            (cfg.name, st["ts_utc"], st["ts_local"], socket.gethostname(), platform.platform(),
             __version__, cfg.to_json(), "running"))
        self.conn.commit()
        return int(cur.lastrowid)

    def finish_campaign(self, cid: int, status: str = "finished") -> None:
        self.conn.execute("UPDATE campaigns SET finished_utc=?, status=? WHERE id=?",
                          (now_stamps()["ts_utc"], status, cid))
        self.conn.commit()

    def ensure_endpoints(self, cid: int, eps: List[Endpoint]) -> Dict[str, int]:
        ids: Dict[str, int] = {}
        for i, ep in enumerate(eps):
            self.conn.execute(
                "INSERT OR IGNORE INTO endpoints(campaign_id, idx, backend, server_id, name, host, location, "
                "country) VALUES (?,?,?,?,?,?,?,?)",
                (cid, i, ep.backend, str(ep.server_id), ep.name, ep.host, ep.location, ep.country))
            row = self.conn.execute("SELECT id FROM endpoints WHERE campaign_id=? AND backend=? AND server_id=?",
                                    (cid, ep.backend, str(ep.server_id))).fetchone()
            ids[ep.key] = int(row[0])
        self.conn.commit()
        return ids

    def open_round(self, cid: int, seq: int, started_epoch: float, n_planned: int) -> int:
        """Insert the round row when the round STARTS so results can be written as they arrive."""
        st = now_stamps(started_epoch)
        cur = self.conn.execute(
            "INSERT INTO rounds(campaign_id, seq, ts_utc, ts_local, epoch_s, tz_name, utc_offset_s, n_planned, "
            "n_ok, n_fail, round_duration_s, stats_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, seq, st["ts_utc"], st["ts_local"], st["epoch_s"], st["tz_name"], st["utc_offset_s"],
             n_planned, 0, 0, None, "{}"))
        self.conn.commit()
        return int(cur.lastrowid)

    def close_round(self, rid: int, rs: RoundSummary) -> None:
        """Fill in counts, duration and statistics once every endpoint of the round has finished."""
        self.conn.execute("UPDATE rounds SET n_ok=?, n_fail=?, round_duration_s=?, stats_json=? WHERE id=?",
                          (rs.n_ok, rs.n_fail, rs.round_duration_s, json.dumps(rs.to_dict()["stats"]), rid))
        self.conn.commit()

    def mark_interrupted(self) -> List[int]:
        """Campaigns still flagged 'running' when a new one starts were killed (crash/power); flag them."""
        rows = self.conn.execute("SELECT id FROM campaigns WHERE status='running'").fetchall()
        ids = [int(r[0]) for r in rows]
        if ids:
            self.conn.execute(f"UPDATE campaigns SET status='interrupted' WHERE id IN ({','.join('?' * len(ids))})", ids)
            self.conn.commit()
        return ids

    def add_round(self, cid: int, rs: RoundSummary) -> int:
        cur = self.conn.execute(
            "INSERT INTO rounds(campaign_id, seq, ts_utc, ts_local, epoch_s, tz_name, utc_offset_s, n_planned, "
            "n_ok, n_fail, round_duration_s, stats_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, rs.seq, rs.ts_utc, rs.ts_local, rs.epoch_s, rs.tz_name, rs.utc_offset_s, rs.n_planned,
             rs.n_ok, rs.n_fail, rs.round_duration_s, json.dumps(rs.to_dict()["stats"])))
        self.conn.commit()
        return int(cur.lastrowid)

    def add_result(self, cid: int, round_id: int, endpoint_id: int, r: TestResult) -> int:
        vals = [cid, round_id, endpoint_id] + [_nan_to_none(getattr(r, c)) for c in RESULT_COLS]
        vals[RESULT_COLS.index("ok") + 3] = 1 if r.ok else 0
        cols = ["campaign_id", "round_id", "endpoint_id"] + RESULT_COLS
        cur = self.conn.execute(f"INSERT INTO results({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
        self.conn.commit()
        return int(cur.lastrowid)

    # -- reads (used by exporters) --------------------------------------------
    def latest_campaign_id(self) -> Optional[int]:
        row = self.conn.execute("SELECT id FROM campaigns ORDER BY id DESC LIMIT 1").fetchone()
        return int(row[0]) if row else None

    def list_campaigns(self) -> List[Dict[str, Any]]:
        """id / name / created_local / status / number of rounds for every campaign (oldest first)."""
        cur = self.conn.execute(
            "SELECT c.id, c.name, c.created_local, c.status, COUNT(r.id) AS n_rounds FROM campaigns c "
            "LEFT JOIN rounds r ON r.campaign_id = c.id GROUP BY c.id ORDER BY c.id")
        return [{"id": int(a), "name": b or "", "started_local": c or "", "status": d or "", "n_rounds": int(e)}
                for a, b, c, d, e in cur.fetchall()]

    def campaign(self, cid: int) -> Dict[str, Any]:
        cur = self.conn.execute("SELECT * FROM campaigns WHERE id=?", (cid,))
        row = cur.fetchone()
        if not row:
            raise KeyError(f"campaign {cid} not found")
        return dict(zip([d[0] for d in cur.description], row))

    def endpoints(self, cid: int) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM endpoints WHERE campaign_id=? ORDER BY idx, id", (cid,))
        return [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

    def rounds(self, cid: int) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM rounds WHERE campaign_id=? ORDER BY seq", (cid,))
        out = []
        for r in cur.fetchall():
            d = dict(zip([c[0] for c in cur.description], r))
            d["stats"] = json.loads(d.pop("stats_json") or "{}")
            out.append(d)
        return out

    def results(self, cid: int) -> List[Dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM results WHERE campaign_id=? ORDER BY epoch_s, id", (cid,))
        return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


# %%% JSONL append logs
class JsonlWriter:
    def __init__(self, path: str, enabled: bool = True):
        self.path = path
        self.enabled = enabled

    def write(self, obj: Dict[str, Any]) -> None:
        if not self.enabled:
            return
        try:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(obj, separators=(",", ":"), default=str) + "\n")
        except OSError as exc:
            logger.error("JSONL write failed (%s): %s", self.path, exc)


# ===========================================================================
# %% EXPORTERS — JSON, CSV, Veusz (.vszh5)
# ===========================================================================
def campaign_bundle(db: SpeedDB, cid: int) -> Dict[str, Any]:
    """Everything about one campaign as plain Python (feeds every exporter)."""
    camp = db.campaign(cid)
    try:
        camp["config"] = json.loads(camp.pop("config_json") or "{}")
    except json.JSONDecodeError:
        camp["config"] = {}
    results = db.results(cid)
    for r in results:
        try:
            r["raw"] = json.loads(r.pop("raw_json") or "null")
        except json.JSONDecodeError:
            r["raw"] = None
    rounds = db.rounds(cid)
    used = {r.get("round_id") for r in results}
    rounds = [rd for rd in rounds if rd["stats"] or rd["id"] in used]   # drop a round that was opened but never got a test
    complete = camp.get("status") in ("finished", "stopped")
    return {
        "generator": {"tool": "isp_speed_monitor.py", "version": __version__,
                      "exported_utc": now_stamps()["ts_utc"], "exported_local": now_stamps()["ts_local"],
                      "campaign_status": camp.get("status"), "complete": complete,
                      "n_rounds": len(rounds), "n_results": len(results),
                      "note": "complete=false means the campaign was still running when this file was refreshed; "
                              "the file is rewritten from the SQLite database at every refresh and at the end"},
        "campaign": camp,
        "endpoints": db.endpoints(cid),
        "rounds": rounds,
        "results": results,
        "field_notes": {
            "download_mbps/upload_mbps": "Mbit/s (decimal mega)",
            "latency_ms": "idle ping (ms); jitter_ms (ms); packet_loss_pct (%)",
            "dl_loaded_latency_ms/ul_loaded_latency_ms": "Ookla loaded-latency IQM (ms) when available",
            "epoch_s": "Unix seconds UTC; ts_utc ISO-8601 Z; ts_local ISO-8601 with offset",
            "rounds.stats": "per-metric mean/median/min/max/std/n over OK tests of that round",
        },
    }


def _atomic_path(path: str) -> str:
    """Temporary sibling name; callers write there and then os.replace() onto ``path``."""
    return path + ".part"


def _commit_atomic(tmp: str, path: str) -> str:
    """Replace ``path`` by ``tmp`` in one step so a reader (Veusz, a script) never sees a half-written file."""
    os.replace(tmp, path)
    return path


def export_json(db: SpeedDB, cid: int, path: str) -> str:
    tmp = _atomic_path(path)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(campaign_bundle(db, cid), fh, indent=1, default=str)
    return _commit_atomic(tmp, path)


def export_csv(db: SpeedDB, cid: int, results_path: str, rounds_path: str) -> Tuple[str, str]:
    results = db.results(cid)
    cols = ["id", "round_id", "endpoint_id"] + [c for c in RESULT_COLS if c != "raw_json"]
    with open(_atomic_path(results_path), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    rounds = db.rounds(cid)
    rcols = ["id", "seq", "ts_utc", "ts_local", "epoch_s", "tz_name", "utc_offset_s", "n_planned", "n_ok",
             "n_fail", "round_duration_s"] + [f"{m}_{s}" for m in METRICS for s in STATS + ["n"]]
    with open(_atomic_path(rounds_path), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rcols, extrasaction="ignore")
        w.writeheader()
        for rd in rounds:
            row = {k: rd.get(k) for k in rcols}
            for m in METRICS:
                for s in STATS + ["n"]:
                    row[f"{m}_{s}"] = rd["stats"].get(m, {}).get(s)
            w.writerow(row)
    return (_commit_atomic(_atomic_path(results_path), results_path),
            _commit_atomic(_atomic_path(rounds_path), rounds_path))


# ---------------------------------------------------------------------------
# %%% Veusz native HDF5 writer
# ---------------------------------------------------------------------------
# Format confirmed against veusz/document/doc.py (saveToHDF5File) and
# veusz/document/loader.py (loadHDF5Doc) of Veusz 4.x:
#   /Veusz                    attrs: vsz_version, vsz_saved_at, vsz_format=1
#   /Veusz/Data/<name>        group, attr vsz_datatype in {'1d','date','text'}
#        .../data (+ serr/perr/nerr for '1d'), attr vsz_name
#        ('/' in a dataset name is escaped as '`SL', '`' as '`BT')
#   /Veusz/Document/document  1-element byte-string array: the command script
#   /Veusz/Document/Tags/<tag> array of dataset-name byte strings
# Datetime datasets are floats: seconds since 2009-01-01 00:00:00 (naive).
# ---------------------------------------------------------------------------
class VszDoc:
    """Tiny builder for the Veusz command script stored in the document."""

    def __init__(self) -> None:
        self.lines: List[str] = [f"# Veusz saved document (version 4.2.1)",
                                 f"# Generated by isp_speed_monitor.py {__version__}",
                                 f"# Saved at {datetime.datetime.now(datetime.timezone.utc).isoformat()}", ""]

    def add(self, wtype: str, name: str, **kw) -> None:
        extra = "".join(f", {k}={v!r}" for k, v in kw.items())
        self.lines.append(f"Add({wtype!r}, name={name!r}, autoadd=False{extra})")

    def to(self, name: str) -> None:
        self.lines.append(f"To({name!r})")

    def up(self) -> None:
        self.lines.append("To('..')")

    def set(self, path: str, value: Any) -> None:
        self.lines.append(f"Set({path!r}, {value!r})")

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


def vz_text(text: str) -> str:
    """Escape Veusz text-markup characters so user strings render literally.

    Veusz treats ``_`` / ``^`` as subscript / superscript and ``{ }`` as grouping;
    a campaign called ``Frontier_WV_20260904`` would otherwise render as
    "Frontier" with "WV" as a subscript.
    """
    return re.sub(r"([_^{}\\])", r"\\\1", str(text))


def _escape_hdf_name(name: str) -> str:
    return name.replace("`", "`BT").replace("/", "`SL")


class VeuszWriter:
    def __init__(self, path: str):
        if h5py is None:
            raise RuntimeError("h5py is required for Veusz export (pip install h5py)")
        self.f = h5py.File(path, "w")
        self.root = self.f.create_group("Veusz")
        self.root.attrs["vsz_version"] = "4.2.1"
        self.root.attrs["vsz_saved_at"] = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
        self.root.attrs["vsz_format"] = 1
        self.data = self.root.create_group("Data")
        self.docgrp = self.root.create_group("Document")
        self.tags: Dict[str, List[str]] = {}

    def _tag(self, name: str, tags: Tuple[str, ...]) -> None:
        for t in tags:
            self.tags.setdefault(t, []).append(name)

    def dataset_1d(self, name: str, data, serr=None, tags: Tuple[str, ...] = ()) -> None:
        g = self.data.create_group(_escape_hdf_name(name))
        g.attrs["vsz_datatype"] = "1d"
        g["data"] = np.asarray(data, dtype=float)
        g["data"].attrs["vsz_name"] = name.encode("utf-8")
        if serr is not None:
            g["serr"] = np.asarray(serr, dtype=float)
            g["serr"].attrs["vsz_name"] = (name + " (+-)").encode("utf-8")
        self._tag(name, tags)

    def dataset_date(self, name: str, veusz_seconds, tags: Tuple[str, ...] = ()) -> None:
        g = self.data.create_group(_escape_hdf_name(name))
        g.attrs["vsz_datatype"] = "date"
        g["data"] = np.asarray(veusz_seconds, dtype=float)
        g["data"].attrs["vsz_convert_datetime"] = 1
        g["data"].attrs["vsz_name"] = name.encode("utf-8")
        self._tag(name, tags)

    def dataset_text(self, name: str, strings: List[str], tags: Tuple[str, ...] = ()) -> None:
        g = self.data.create_group(_escape_hdf_name(name))
        g.attrs["vsz_datatype"] = "text"
        g["data"] = [str(s).encode("utf-8") for s in strings]
        g["data"].attrs["vsz_name"] = name.encode("utf-8")
        self._tag(name, tags)

    def finish(self, document_text: str) -> None:
        tagsgrp = self.docgrp.create_group("Tags")
        for tag, names in sorted(self.tags.items()):
            tagsgrp[tag] = [n.encode("utf-8") for n in sorted(names)]
        self.docgrp["document"] = [document_text.encode("utf-8")]
        self.f.close()


def _add_time_graph(doc: VszDoc, gname: str, xlabel: str, ylabel: str, series: List[Dict[str, Any]],
                    with_key: bool = True) -> None:
    """One graph with datetime x axis; `series` items: dict(name, x, y, color, key, avg:bool)."""
    doc.add("graph", gname)
    doc.to(gname)
    doc.set("leftMargin", "1.9cm")
    doc.set("rightMargin", "0.4cm")
    doc.set("topMargin", "1.1cm")
    doc.set("bottomMargin", "1.4cm")
    doc.add("axis", "x")
    doc.add("axis", "y")
    doc.set("x/mode", "datetime")
    doc.set("x/label", xlabel)
    doc.set("x/autoRange", "+2%")
    doc.set("x/TickLabels/rotate", "-45")
    doc.set("x/TickLabels/size", "7pt")
    doc.set("y/direction", "vertical")
    doc.set("y/label", ylabel)
    doc.set("y/min", 0.0)                 # every metric here is non-negative
    doc.set("y/autoRange", "+5%")
    doc.set("y/TickLabels/size", "7pt")
    doc.set("y/GridLines/hide", False)
    doc.set("y/GridLines/color", "#c8c8c8")
    doc.set("y/GridLines/style", "dotted")
    for s in series:
        doc.add("xy", s["name"])
        doc.to(s["name"])
        doc.set("xData", s["x"])
        doc.set("yData", s["y"])
        doc.set("key", s["key"])
        doc.set("thinfactor", 1)
        if s.get("avg"):
            doc.set("marker", "square")
            doc.set("markerSize", "2.5pt")
            doc.set("PlotLine/width", "1.5pt")
            doc.set("PlotLine/color", s["color"])
            doc.set("MarkerFill/color", s["color"])
            doc.set("MarkerLine/hide", True)
            doc.set("errorStyle", "bar")
            doc.set("ErrorBarLine/color", s["color"])
            doc.set("ErrorBarLine/width", "0.5pt")
            doc.set("ErrorBarLine/transparency", 40)
        else:
            doc.set("marker", "circle")
            doc.set("markerSize", "1.8pt")
            doc.set("PlotLine/width", "0.5pt")
            doc.set("PlotLine/color", s["color"])
            doc.set("PlotLine/transparency", 35)
            doc.set("MarkerFill/color", s["color"])
            doc.set("MarkerLine/hide", True)
        doc.up()
    if with_key:
        doc.add("key", "key1")
        doc.set("key1/horzPosn", "right")
        doc.set("key1/vertPosn", "top")
        doc.set("key1/Text/size", "7pt")
        doc.set("key1/Border/hide", True)
        doc.set("key1/Background/transparency", 30)
    doc.up()


def export_veusz(db: SpeedDB, cid: int, path: str, time_axis: str = "local") -> str:
    """Write a native Veusz .vszh5 document: raw per-endpoint arrays, combined
    raw arrays, averaged arrays (mean with std as symmetric error), metadata,
    and pages that mirror the GUI plots."""
    bundle = campaign_bundle(db, cid)
    camp, eps, rounds, results = bundle["campaign"], bundle["endpoints"], bundle["rounds"], bundle["results"]
    final_path, path = path, _atomic_path(path)
    if os.path.exists(path):
        os.remove(path)
    w = VeuszWriter(path)
    doc = VszDoc()

    time_axis = "utc" if time_axis == "utc" else "local"
    xds_suffix = "time_utc" if time_axis == "utc" else "time_local"
    xlabel = "Time (UTC)" if time_axis == "utc" else "Time (local wall clock)"

    def arr(rows: List[Dict[str, Any]], key: str) -> np.ndarray:
        return np.array([math.nan if r.get(key) is None else float(r.get(key)) for r in rows], dtype=float)

    def write_block(prefix: str, rows: List[Dict[str, Any]], tags: Tuple[str, ...]) -> None:
        ep_s = arr(rows, "epoch_s")
        off = arr(rows, "utc_offset_s")
        w.dataset_date(f"{prefix}/time_utc", epoch_to_veusz(ep_s, 0.0), tags)
        w.dataset_date(f"{prefix}/time_local", epoch_to_veusz(ep_s, off), tags)
        w.dataset_1d(f"{prefix}/epoch_s", ep_s, tags=tags)
        w.dataset_1d(f"{prefix}/utc_offset_s", off, tags=tags)
        w.dataset_text(f"{prefix}/ts_utc_iso", [r.get("ts_utc", "") for r in rows], tags)
        w.dataset_text(f"{prefix}/ts_local_iso", [r.get("ts_local", "") for r in rows], tags)
        for m in METRICS + ["download_bytes", "upload_bytes", "download_elapsed_ms", "upload_elapsed_ms",
                            "duration_s"]:
            w.dataset_1d(f"{prefix}/{m}", arr(rows, m), tags=tags)
        w.dataset_1d(f"{prefix}/ok", np.array([1.0 if r.get("ok") else 0.0 for r in rows]), tags=tags)
        w.dataset_1d(f"{prefix}/round_id", arr(rows, "round_id"), tags=tags)
        w.dataset_text(f"{prefix}/error", [r.get("error") or "" for r in rows], tags)

    # ---- raw: per endpoint ----------------------------------------------------
    ep_slugs: Dict[int, str] = {}
    ep_labels: Dict[int, str] = {}
    for i, e in enumerate(eps):
        epo = Endpoint(e["backend"], str(e["server_id"]), e.get("name") or "", e.get("host") or "",
                       e.get("location") or "", e.get("country") or "")
        ep_slugs[e["id"]] = epo.slug(i)
        ep_labels[e["id"]] = f"{epo.name or epo.host or epo.server_id} ({epo.backend} {epo.server_id})"
        rows = [r for r in results if r["endpoint_id"] == e["id"]]
        write_block(f"raw/{ep_slugs[e['id']]}", rows, ("raw", f"endpoint:{ep_slugs[e['id']]}"))

    # ---- raw: all endpoints combined ----------------------------------------
    write_block("raw/all", results, ("raw",))
    w.dataset_1d("raw/all/endpoint_index",
                 np.array([next((i for i, e in enumerate(eps) if e["id"] == r["endpoint_id"]), -1)
                           for r in results], dtype=float), tags=("raw",))
    w.dataset_text("raw/all/endpoint", [ep_labels.get(r["endpoint_id"], "?") for r in results], ("raw",))
    w.dataset_text("raw/all/endpoint_key", [r.get("endpoint_key", "") for r in results], ("raw",))
    w.dataset_text("raw/all/server_location", [r.get("server_location") or "" for r in results], ("raw",))
    w.dataset_text("raw/all/external_ip", [r.get("external_ip") or "" for r in results], ("raw",))

    # ---- averaged (per round) -----------------------------------------------
    r_ep = arr(rounds, "epoch_s")
    r_off = arr(rounds, "utc_offset_s")
    w.dataset_date("avg/time_utc", epoch_to_veusz(r_ep, 0.0), ("averaged",))
    w.dataset_date("avg/time_local", epoch_to_veusz(r_ep, r_off), ("averaged",))
    w.dataset_1d("avg/epoch_s", r_ep, tags=("averaged",))
    w.dataset_1d("avg/utc_offset_s", r_off, tags=("averaged",))
    w.dataset_1d("avg/round_seq", arr(rounds, "seq"), tags=("averaged",))
    w.dataset_1d("avg/round_id", arr(rounds, "id"), tags=("averaged",))
    w.dataset_1d("avg/n_ok", arr(rounds, "n_ok"), tags=("averaged",))
    w.dataset_1d("avg/n_fail", arr(rounds, "n_fail"), tags=("averaged",))
    w.dataset_1d("avg/n_planned", arr(rounds, "n_planned"), tags=("averaged",))
    w.dataset_1d("avg/round_duration_s", arr(rounds, "round_duration_s"), tags=("averaged",))
    w.dataset_text("avg/ts_utc_iso", [r.get("ts_utc", "") for r in rounds], ("averaged",))
    w.dataset_text("avg/ts_local_iso", [r.get("ts_local", "") for r in rounds], ("averaged",))

    def stat_arr(metric: str, stat: str) -> np.ndarray:
        out = []
        for rd in rounds:
            v = rd["stats"].get(metric, {}).get(stat)
            out.append(math.nan if v is None else float(v))
        return np.array(out, dtype=float)

    for m in METRICS:
        mean, std = stat_arr(m, "mean"), stat_arr(m, "std")
        w.dataset_1d(f"avg/{m}", mean, serr=np.nan_to_num(std, nan=0.0), tags=("averaged",))  # mean ± std
        for s in ("median", "min", "max", "std", "n"):
            w.dataset_1d(f"avg/{m}_{s}", stat_arr(m, s), tags=("averaged",))

    # ---- metadata ------------------------------------------------------------
    w.dataset_text("meta/endpoint_labels", [ep_labels[e["id"]] for e in eps], ("meta",))
    w.dataset_text("meta/endpoint_slugs", [ep_slugs[e["id"]] for e in eps], ("meta",))
    w.dataset_text("meta/endpoint_keys", [f"{e['backend']}:{e['server_id']}" for e in eps], ("meta",))
    w.dataset_text("meta/campaign_json", [json.dumps({k: v for k, v in camp.items()}, default=str)], ("meta",))
    g = bundle["generator"]
    w.dataset_text("meta/export_status", [f"campaign_status={g['campaign_status']}", f"complete={g['complete']}",
                                           f"n_rounds={g['n_rounds']}", f"n_results={g['n_results']}",
                                           f"exported_utc={g['exported_utc']}"], ("meta",))
    w.dataset_text("meta/generator", [f"isp_speed_monitor.py {__version__}", f"exported {now_stamps()['ts_utc']}",
                                       "time_utc / time_local are Veusz datetime floats (s since 2009-01-01)",
                                       "avg/<metric> carries std as symmetric error; separate arrays hold "
                                       "median/min/max/std/n"], ("meta",))

    # ---- pages mirroring the GUI ----------------------------------------------
    colors = [PLOT_COLORS[i % len(PLOT_COLORS)] for i in range(len(eps))]
    panels = [("download", "download_mbps"), ("upload", "upload_mbps"), ("latency", "latency_ms"),
              ("jitter", "jitter_ms"), ("packet_loss", "packet_loss_pct"), ("loaded_latency", "dl_loaded_latency_ms")]

    def series_for(metric: str) -> List[Dict[str, Any]]:
        ser = []
        for i, e in enumerate(eps):
            slug = ep_slugs[e["id"]]
            ser.append({"name": f"raw_{slug}", "x": f"raw/{slug}/{xds_suffix}", "y": f"raw/{slug}/{metric}",
                        "color": colors[i], "key": vz_text(ep_labels[e["id"]]), "avg": False})
        ser.append({"name": "avg", "x": f"avg/{xds_suffix}", "y": f"avg/{metric}", "color": "#000000",
                    "key": "Round average ± std", "avg": True})
        return ser

    title = f"{camp.get('name', 'campaign')} — {camp.get('created_local', '')} — {camp.get('host', '')}"
    for pname, metric in panels:
        label, unit = METRIC_LABELS[metric]
        doc.add("page", f"page_{pname}")
        doc.to(f"page_{pname}")
        doc.set("width", "25cm")
        doc.set("height", "15cm")
        doc.add("label", "title")
        doc.set("title/label", vz_text(f"{label} — {title}"))
        doc.set("title/xPos", [0.5])
        doc.set("title/yPos", [0.965])
        doc.set("title/alignHorz", "centre")
        doc.set("title/Text/size", "10pt")
        _add_time_graph(doc, f"g_{pname}", xlabel, f"{label} ({unit})", series_for(metric))
        doc.up()

    # overview grid: 3 rows x 2 cols, same order as the GUI
    doc.add("page", "page_overview")
    doc.to("page_overview")
    doc.set("width", "30cm")
    doc.set("height", "24cm")
    doc.add("label", "title")
    doc.set("title/label", vz_text(f"Overview — {title}"))
    doc.set("title/xPos", [0.5])
    doc.set("title/yPos", [0.975])
    doc.set("title/alignHorz", "centre")
    doc.set("title/Text/size", "11pt")
    doc.add("grid", "grid1")
    doc.to("grid1")
    doc.set("rows", 3)
    doc.set("columns", 2)
    doc.set("topMargin", "1.0cm")
    doc.set("bottomMargin", "0.3cm")
    doc.set("leftMargin", "0.3cm")
    doc.set("rightMargin", "0.3cm")
    doc.set("scaleRows", [1.0, 1.0, 1.0])
    for k, (pname, metric) in enumerate(panels):
        label, unit = METRIC_LABELS[metric]
        _add_time_graph(doc, f"g_{pname}", xlabel, f"{label} ({unit})", series_for(metric), with_key=(k == 0))
    doc.up()
    doc.up()

    w.finish(doc.text())
    return _commit_atomic(path, final_path)


def export_all(db: SpeedDB, cid: int, cfg: CampaignConfig, tag: str = "") -> List[str]:
    """Run every enabled exporter and return the list of written files.

    * ``tag == ""`` (periodic refresh and final export): files use the STABLE name
      ``<campaign>_c<id>.<ext>`` and are rewritten in place (atomically) from the
      SQLite database, so the file set on disk always holds the full data set as
      of the last refresh.
    * any other tag (e.g. ``_manual`` from Export now): a time-stamped SNAPSHOT
      ``<campaign>_c<id>_<YYYYmmdd_HHMMSS><tag>.<ext>`` is written alongside.
    """
    out: List[str] = []
    os.makedirs(cfg.output_dir, exist_ok=True)
    if tag:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = os.path.join(cfg.output_dir, f"{slugify(cfg.name, 40)}_c{cid}_{stamp}{tag}")
    else:
        base = os.path.join(cfg.output_dir, f"{slugify(cfg.name, 40)}_c{cid}")
    if cfg.export_json:
        out.append(export_json(db, cid, base + ".json"))
    if cfg.export_csv:
        out.extend(export_csv(db, cid, base + "_results.csv", base + "_rounds.csv"))
    if cfg.export_veusz:
        if h5py is None:
            logger.error("Veusz export skipped: h5py not installed")
        else:
            out.append(export_veusz(db, cid, base + ".vszh5", cfg.veusz_time_axis))
    return out


# ===========================================================================
# %% SCHEDULER
# ===========================================================================
class Scheduler:
    """Computes fire times for a campaign. All times are Unix epoch seconds."""

    def __init__(self, sc: ScheduleConfig):
        self.sc = sc
        self.rng = random.Random(sc.random_seed)
        self.t_start: float = 0.0
        self.t_end: Optional[float] = None
        self._window_start: Optional[float] = None
        self._window_times: List[float] = []

    def start(self, now: float) -> None:
        sc = self.sc
        start_at = local_iso_to_epoch(sc.start_at_local) if sc.start_at_local else None
        self.t_start = max(now, start_at) if start_at else now
        end_at = local_iso_to_epoch(sc.end_at_local) if sc.end_at_local else None
        if end_at:
            self.t_end = end_at
        elif sc.duration_s and sc.duration_s > 0:
            self.t_end = self.t_start + sc.duration_s
        else:
            self.t_end = None

    def first_fire(self) -> Optional[float]:
        if self.sc.first_test_immediately or self.sc.mode == "random_per_window":
            return self._clip(self.t_start if self.sc.mode != "random_per_window" else self._next_window(self.t_start))
        return self.next_fire(self.t_start)

    def next_fire(self, last_fire: float) -> Optional[float]:
        sc = self.sc
        if sc.mode == "interval":
            nxt = last_fire + max(1.0, sc.interval_s)
        elif sc.mode == "random_gap":
            lo, hi = sorted((max(1.0, sc.min_gap_s), max(1.0, sc.max_gap_s)))
            nxt = last_fire + self.rng.uniform(lo, hi)
        elif sc.mode == "random_per_window":
            nxt = self._next_window(last_fire)
        else:
            raise ValueError(f"unknown schedule mode {sc.mode!r}")
        return self._clip(nxt)

    def _next_window(self, after: float) -> Optional[float]:
        """Random N tests per window: draw all times for the window on entry."""
        W = max(10.0, self.sc.window_s)
        n = max(1, int(self.sc.per_window))
        while True:
            if self._window_start is None:
                self._window_start = self.t_start
                self._draw(W, n)
            cand = [t for t in self._window_times if t > after]
            if cand:
                self._window_times = cand
                return cand[0]
            self._window_start += W
            if self.t_end is not None and self._window_start >= self.t_end:
                return None
            self._draw(W, n)

    def _draw(self, W: float, n: int) -> None:
        assert self._window_start is not None
        self._window_times = sorted(self._window_start + self.rng.uniform(0, W) for _ in range(n))

    def _clip(self, t: Optional[float]) -> Optional[float]:
        if t is None:
            return None
        if self.t_end is not None and t > self.t_end:
            return None
        return t

    def describe(self) -> str:
        sc = self.sc
        if sc.mode == "interval":
            s = f"every {fmt_duration(sc.interval_s)}"
        elif sc.mode == "random_gap":
            s = f"random gap {fmt_duration(sc.min_gap_s)} – {fmt_duration(sc.max_gap_s)}"
        else:
            s = f"{sc.per_window} random tests per {fmt_duration(sc.window_s)} window"
        if self.t_end:
            s += f", until {datetime.datetime.fromtimestamp(self.t_end).strftime('%Y-%m-%d %H:%M:%S')} local"
        else:
            s += ", until stopped"
        return s


# ===========================================================================
# %% CAMPAIGN ENGINE (shared by GUI and headless mode)
# ===========================================================================
class RoundWorker(QtCore.QThread):
    """Runs one round: every selected endpoint, sequentially."""
    result_ready = Signal(object)          # TestResult
    progress = Signal(int, int, str)       # done, total, label
    round_done = Signal(object, float)     # list[TestResult], started_epoch

    def __init__(self, backends: Dict[str, BackendBase], endpoints: List[Endpoint], cfg: CampaignConfig,
                 parent=None):
        super().__init__(parent)
        self.backends = backends
        self.endpoints = endpoints
        self.cfg = cfg
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True
        for b in self.backends.values():
            b.abort()

    def run(self) -> None:  # noqa: D401
        started = time.time()
        results: List[TestResult] = []
        total = len(self.endpoints)
        for i, ep in enumerate(self.endpoints):
            if self._stop:
                break
            self.progress.emit(i, total, ep.label)
            be = self.backends[ep.backend]
            try:
                r = be.run_test(ep, self.cfg.test_download, self.cfg.test_upload, self.cfg.test_timeout_s)
            except Exception as exc:  # belt and braces — back-ends already catch
                r = be._new_result(ep)
                r.error = f"{type(exc).__name__}: {exc}"
            if self._stop and not r.ok:
                r.error = r.error or "aborted"
            results.append(r)
            self.result_ready.emit(r)
            if i < total - 1 and not self._stop:
                t_end = time.time() + max(0.0, self.cfg.pause_between_endpoints_s)
                while time.time() < t_end and not self._stop:
                    time.sleep(0.1)
        self.progress.emit(total, total, "")
        self.round_done.emit(results, started)


class CampaignController(QtCore.QObject):
    """Owns config, DB, scheduler and the worker; emits everything the UI needs."""
    sig_log = Signal(str)
    sig_state = Signal(str)                       # 'idle' | 'waiting' | 'testing' | 'finished'
    sig_result = Signal(object)                   # TestResult
    sig_round = Signal(object)                    # RoundSummary
    sig_progress = Signal(int, int, str)
    sig_tick = Signal(float, int)                 # next fire epoch (or -1), rounds done
    sig_exported = Signal(object)                 # list[str]
    sig_finished = Signal(str)                    # status

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cfg: Optional[CampaignConfig] = None
        self.db: Optional[SpeedDB] = None
        self.cid: Optional[int] = None
        self.endpoints: List[Endpoint] = []
        self.endpoint_ids: Dict[str, int] = {}
        self.backends: Dict[str, BackendBase] = {}
        self.scheduler: Optional[Scheduler] = None
        self.worker: Optional[RoundWorker] = None
        self.state = "idle"
        self.round_seq = 0
        self._rid: Optional[int] = None
        self._tests_since_export = 0
        self._tests_in_round = 0
        self.next_fire: Optional[float] = None
        self._pending_fire = False
        self._manual_round = False
        self._stopping = False
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        self._tick = QtCore.QTimer(self)
        self._tick.setInterval(1000)
        self._tick.timeout.connect(self._on_tick)
        self.results_jsonl: Optional[JsonlWriter] = None
        self.rounds_jsonl: Optional[JsonlWriter] = None

    # -- helpers ----------------------------------------------------------------
    def log(self, msg: str, level: int = logging.INFO) -> None:
        logger.log(level, msg)
        self.sig_log.emit(f"{datetime.datetime.now().strftime('%H:%M:%S')}  {msg}")

    @property
    def running(self) -> bool:
        return self.state in ("waiting", "testing")

    def _set_state(self, s: str) -> None:
        self.state = s
        self.sig_state.emit(s)

    # -- lifecycle ----------------------------------------------------------------
    def open_db(self, cfg: CampaignConfig) -> SpeedDB:
        if self.db is None or self.db.path != os.path.join(cfg.output_dir, DB_FILENAME):
            if self.db:
                self.db.close()
            self.db = SpeedDB(os.path.join(cfg.output_dir, DB_FILENAME))
        return self.db

    def start(self, cfg: CampaignConfig) -> None:
        if self.running:
            raise RuntimeError("campaign already running")
        eps = cfg.endpoint_objs()
        if not eps:
            raise ValueError("no endpoints selected")
        os.makedirs(cfg.output_dir, exist_ok=True)
        self.cfg = cfg
        self.endpoints = eps
        self.backends = {k: make_backend(k, cfg) for k in {e.backend for e in eps}}
        for k, b in self.backends.items():
            ok, msg = b.available()
            if not ok:
                raise RuntimeError(f"back-end {k}: {msg}")
            self.log(f"back-end {k}: {msg}")
        db = self.open_db(cfg)
        for old in db.mark_interrupted():
            self.log(f"campaign #{old} was still flagged 'running' (program killed?) -> marked 'interrupted'; "
                     f"its data is intact in the database — use Tools ▸ Re-export to regenerate its files", logging.WARNING)
        self.cid = db.new_campaign(cfg)
        self._tests_since_export = 0
        self._rid = None
        self.endpoint_ids = db.ensure_endpoints(self.cid, eps)
        self.results_jsonl = JsonlWriter(os.path.join(cfg.output_dir, RESULTS_JSONL), cfg.write_jsonl)
        self.rounds_jsonl = JsonlWriter(os.path.join(cfg.output_dir, ROUNDS_JSONL), cfg.write_jsonl)
        self.scheduler = Scheduler(cfg.schedule_obj())
        self.scheduler.start(time.time())
        self.round_seq = 0
        self._stopping = False
        self._pending_fire = False
        self.log(f"campaign '{cfg.name}' #{self.cid} started — {len(eps)} endpoint(s), "
                 f"{self.scheduler.describe()}; DB: {db.path}")
        for e in eps:
            self.log(f"  endpoint: {e.label}")
        self.next_fire = self.scheduler.first_fire()
        self._tick.start()
        self._arm()

    def _arm(self) -> None:
        if self.next_fire is None:
            self._finish("finished")
            return
        delay_ms = max(0, int((self.next_fire - time.time()) * 1000))
        self._set_state("waiting")
        self._timer.start(min(delay_ms, 2_000_000_000))
        self.sig_tick.emit(self.next_fire, self.round_seq)

    def _fire(self) -> None:
        if self._stopping:
            return
        if self.worker is not None and self.worker.isRunning():
            self._pending_fire = True     # a manual round is running; run when it ends
            return
        self._start_round(manual=False)

    def run_once(self) -> None:
        """Manual, out-of-schedule round (also works while waiting)."""
        if self.cfg is None or self.cid is None:
            raise RuntimeError("start a campaign first (or use Run Once from the GUI setup)")
        if self.worker is not None and self.worker.isRunning():
            raise RuntimeError("a round is already in progress")
        self._start_round(manual=True)

    def _start_round(self, manual: bool) -> None:
        assert self.cfg is not None
        self._manual_round = manual
        self.round_seq += 1
        self._set_state("testing")
        self.log(f"round {self.round_seq} {'(manual) ' if manual else ''}starting")
        self._tests_in_round = 0
        if self.db is not None and self.cid is not None:
            self._rid = self.db.open_round(self.cid, self.round_seq, time.time(), len(self.endpoints))
        self.worker = RoundWorker(self.backends, self.endpoints, self.cfg)
        self.worker.result_ready.connect(self._on_result)
        self.worker.progress.connect(self.sig_progress)
        self.worker.round_done.connect(self._on_round_done)
        self.worker.start()

    @Slot(object)
    def _on_result(self, r: TestResult) -> None:
        # stored when the round completes (needs round_id); echo now for the UI
        who = r.endpoint_name or r.server_name or r.server_id
        if r.server_name and r.server_name != r.endpoint_name:
            who += f" [{r.server_name}, {r.server_location}]" if r.server_location else f" [{r.server_name}]"
        if r.ok:
            self.log(f"  {who}: ↓ {r.download_mbps:.1f}  ↑ {r.upload_mbps:.1f} Mbit/s, "
                     f"ping {r.latency_ms:.1f} ms, jitter {r.jitter_ms:.1f} ms, loss "
                     f"{'n/a' if math.isnan(r.packet_loss_pct) else f'{r.packet_loss_pct:.1f}%'}")
        else:
            self.log(f"  {who}: FAILED — {r.error}", logging.WARNING)
        # write-through: every single test lands in SQLite (+ JSONL) the moment it finishes
        if self.db is not None and self.cid is not None and self._rid is not None:
            try:
                self.db.add_result(self.cid, self._rid, self.endpoint_ids.get(r.endpoint_key, -1), r)
                if self.results_jsonl:
                    d = r.to_dict()
                    d.update({"campaign_id": self.cid, "round_id": self._rid, "round_seq": self.round_seq})
                    self.results_jsonl.write(d)
            except Exception as exc:
                self.log(f"could not store result: {exc}", logging.ERROR)
        self.sig_result.emit(r)
        self._tests_since_export += 1
        self._tests_in_round += 1
        if self._tests_in_round < len(self.endpoints) and self._tests_refresh_due():
            self._refresh_exports(f"{self._tests_since_export} test(s)")   # last test of a round: see _on_round_done

    @Slot(object, float)
    def _on_round_done(self, results: List[TestResult], started: float) -> None:
        assert self.cfg is not None and self.db is not None and self.cid is not None
        rs = summarize_round(self.round_seq, results, started, len(self.endpoints))
        if self._rid is None:                       # defensive: round row missing -> create it now
            self._rid = self.db.add_round(self.cid, rs)
            for r in results:
                self.db.add_result(self.cid, self._rid, self.endpoint_ids.get(r.endpoint_key, -1), r)
        else:
            self.db.close_round(self._rid, rs)
        rid = self._rid
        if self.rounds_jsonl:
            d = rs.to_dict()
            d.update({"campaign_id": self.cid, "round_id": rid})
            self.rounds_jsonl.write(d)
        dl, ul = rs.get("download_mbps"), rs.get("upload_mbps")
        self.log(f"round {rs.seq} done: {rs.n_ok}/{rs.n_planned} ok — avg ↓ {dl:.1f}  ↑ {ul:.1f} Mbit/s, "
                 f"ping {rs.get('latency_ms'):.1f} ms ({rs.round_duration_s:.0f} s)")
        self.sig_round.emit(rs)
        self.worker = None
        self._rid = None
        if self.cfg.export_every_unit == "rounds" and self.cfg.export_every_n > 0 \
                and rs.seq % self.cfg.export_every_n == 0:
            self._refresh_exports(f"round {rs.seq}")
        elif self._tests_refresh_due():                 # deferred from the round's last test so avg/* is complete
            self._refresh_exports(f"{self._tests_since_export} test(s)")
        if self._stopping:
            self._finish("stopped")
            return
        if self._manual_round and self.scheduler is not None and not self._pending_fire:
            self._set_state("waiting")
            self.sig_tick.emit(self.next_fire if self.next_fire else -1, self.round_seq)
            return
        if self._pending_fire:
            self._pending_fire = False
        if self.scheduler is None:
            self._finish("finished")
            return
        base = self.next_fire if self.next_fire is not None else started
        self.next_fire = self.scheduler.next_fire(base)
        # if we fell behind (long rounds), skip fires that are already in the past
        guard = 0
        while self.next_fire is not None and self.next_fire < time.time() - 1 and guard < 10000:
            self.next_fire = self.scheduler.next_fire(self.next_fire)
            guard += 1
        self._arm()

    def stop(self) -> None:
        if not self.running and self.worker is None:
            return
        self._stopping = True
        self._timer.stop()
        if self.worker is not None and self.worker.isRunning():
            self.log("stop requested — aborting current test")
            self.worker.request_stop()
        else:
            self._finish("stopped")

    def _finish(self, status: str) -> None:
        self._timer.stop()
        self._tick.stop()
        if self.db and self.cid:
            self.db.finish_campaign(self.cid, status)
        self._set_state("finished")
        self.log(f"campaign {status} after {self.round_seq} round(s)")
        files: List[str] = []
        if self.cfg and self.cid and self.round_seq > 0:
            try:
                files = self.export()
                self.log("final export: " + "; ".join(os.path.basename(f) for f in files))
            except Exception as exc:
                self.log(f"final export failed: {exc}", logging.ERROR)
                logger.debug(traceback.format_exc())
        self.sig_tick.emit(-1, self.round_seq)
        self.sig_finished.emit(status)

    def _tests_refresh_due(self) -> bool:
        return bool(self.cfg and self.cfg.export_every_unit == "tests" and self.cfg.export_every_n > 0
                    and self._tests_since_export >= self.cfg.export_every_n)

    def _refresh_exports(self, why: str) -> None:
        """Rewrite the stable JSON/CSV/Veusz files from the database (periodic, mid-campaign)."""
        t0 = time.time()
        try:
            files = self.export()
            self._tests_since_export = 0
            self.log(f"output files refreshed after {why} ({len(files)} file(s), {time.time() - t0:.2f} s)")
        except Exception as exc:
            self.log(f"periodic export failed: {exc}", logging.ERROR)
            logger.debug(traceback.format_exc())

    def export(self, tag: str = "") -> List[str]:
        assert self.cfg is not None and self.db is not None and self.cid is not None
        files = export_all(self.db, self.cid, self.cfg, tag)
        for f in files:
            logger.info("exported %s", f)
        self.sig_exported.emit(files)
        return files

    def shutdown(self, wait_ms: int = 5000) -> None:
        self._stopping = True
        self._timer.stop()
        self._tick.stop()
        if self.worker is not None and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(wait_ms)
        if self.db:
            if self.cid and self.state in ("waiting", "testing"):
                self.db.finish_campaign(self.cid, "aborted")
                try:                                  # leave a complete file set behind even on window close
                    if self.cfg and self.round_seq > 0:
                        export_all(self.db, self.cid, self.cfg)
                except Exception as exc:
                    logger.error("export on shutdown failed: %s", exc)
            self.db.close()
            self.db = None

    def _on_tick(self) -> None:
        self.sig_tick.emit(self.next_fire if (self.next_fire and self.state == "waiting") else -1, self.round_seq)


# ===========================================================================
# %% GUI
# ===========================================================================
# %%% Theme engine (System / Light / Dark)
# ---------------------------------------------------------------------------
THEME_MODES = ("system", "light", "dark")
_SYSTEM_STYLE_NAME: Optional[str] = None      # captured on first apply_theme()
_SYSTEM_PALETTE: Optional[QtGui.QPalette] = None


def _palette_from(spec: Dict[str, Tuple[int, int, int]]) -> QtGui.QPalette:
    p = QtGui.QPalette()
    c = {k: QtGui.QColor(*v) for k, v in spec.items()}
    P = QtGui.QPalette
    for role, key in ((P.Window, "window"), (P.WindowText, "text"), (P.Base, "base"), (P.AlternateBase, "alt"),
                      (P.ToolTipBase, "tip"), (P.ToolTipText, "tiptext"), (P.Text, "text"), (P.Button, "button"),
                      (P.ButtonText, "text"), (P.BrightText, "bright"), (P.Link, "link"), (P.Highlight, "hl"),
                      (P.HighlightedText, "hltext"), (P.PlaceholderText, "disabled"), (P.Light, "light"),
                      (P.Midlight, "midlight"), (P.Mid, "mid"), (P.Dark, "dark"), (P.Shadow, "shadow")):
        if key in c:
            p.setColor(role, c[key])
    for role in (P.Text, P.ButtonText, P.WindowText, P.Highlight, P.HighlightedText):
        p.setColor(P.Disabled, role, c["disabled"] if role not in (P.Highlight, P.HighlightedText) else c["mid"])
    return p


LIGHT_PALETTE_SPEC = {
    "window": (239, 239, 239), "base": (255, 255, 255), "alt": (247, 247, 247), "text": (0, 0, 0),
    "button": (239, 239, 239), "bright": (255, 255, 255), "link": (0, 90, 200), "hl": (48, 140, 198),
    "hltext": (255, 255, 255), "tip": (255, 255, 220), "tiptext": (0, 0, 0), "disabled": (150, 150, 150),
    "light": (255, 255, 255), "midlight": (227, 227, 227), "mid": (184, 184, 184), "dark": (159, 159, 159),
    "shadow": (118, 118, 118),
}
DARK_PALETTE_SPEC = {
    "window": (45, 45, 48), "base": (30, 30, 32), "alt": (40, 40, 44), "text": (225, 225, 225),
    "button": (53, 53, 56), "bright": (255, 80, 80), "link": (90, 160, 255), "hl": (42, 130, 218),
    "hltext": (255, 255, 255), "tip": (60, 60, 64), "tiptext": (225, 225, 225), "disabled": (128, 128, 128),
    "light": (80, 80, 84), "midlight": (64, 64, 68), "mid": (38, 38, 40), "dark": (28, 28, 30),
    "shadow": (10, 10, 10),
}


def system_prefers_dark(app: QtWidgets.QApplication) -> bool:
    """Best-effort detection of the OS colour scheme (Qt >= 6.5 hint, else palette luminance)."""
    try:
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        pass
    pal = _SYSTEM_PALETTE or app.palette()
    return pal.color(QtGui.QPalette.Window).lightness() < 128


def apply_theme(app: QtWidgets.QApplication, mode: str) -> bool:
    """Apply "system" / "light" / "dark". Returns the EFFECTIVE dark flag (used by plots).

    Light/Dark force the Fusion style with an explicit palette, because the
    native "windows11"/"windowsvista" styles ignore most palette roles and
    Fusion's standardPalette() follows the OS scheme on Qt >= 6.5 — which is why
    a plain "light" request looked dark on a system-dark Windows machine.
    On Qt >= 6.8 the colour-scheme hint is set too so the title bar follows.
    """
    global _SYSTEM_STYLE_NAME, _SYSTEM_PALETTE
    if _SYSTEM_STYLE_NAME is None:
        _SYSTEM_STYLE_NAME = app.style().objectName() or "Fusion"
        _SYSTEM_PALETTE = QtGui.QPalette(app.palette())
    mode = mode if mode in THEME_MODES else "system"
    # title-bar / native-dialog hint (Qt >= 6.8; silently ignored elsewhere)
    try:
        hints = app.styleHints()
        hints.setColorScheme({"light": Qt.ColorScheme.Light, "dark": Qt.ColorScheme.Dark}.get(mode, Qt.ColorScheme.Unknown))
    except Exception:
        pass
    if mode == "system":
        app.setStyle(_SYSTEM_STYLE_NAME)
        app.setPalette(_SYSTEM_PALETTE if _SYSTEM_PALETTE is not None else app.style().standardPalette())
        dark = system_prefers_dark(app)
    else:
        app.setStyle("Fusion")
        dark = mode == "dark"
        app.setPalette(_palette_from(DARK_PALETTE_SPEC if dark else LIGHT_PALETTE_SPEC))
    if pg:
        pg.setConfigOptions(background=(30, 30, 32) if dark else "w", foreground=(220, 220, 220) if dark else "k")
    return dark


# ---------------------------------------------------------------------------
# %%% Small widgets and workers
# ---------------------------------------------------------------------------
class DurationEdit(QtWidgets.QWidget):
    """Spin box + unit combo returning seconds."""

    def __init__(self, value: float, unit: str = "minutes", parent=None, minimum: float = 0.0):
        super().__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setRange(minimum, 1e7)
        self.spin.setDecimals(2)
        self.spin.setValue(value)
        self.unit = QtWidgets.QComboBox()
        self.unit.addItems(list(SECONDS_PER_UNIT))
        self.unit.setCurrentText(unit)
        lay.addWidget(self.spin, 1)
        lay.addWidget(self.unit)

    def seconds(self) -> float:
        return self.spin.value() * SECONDS_PER_UNIT[self.unit.currentText()]

    def set_seconds(self, s: float) -> None:
        for unit in reversed(list(SECONDS_PER_UNIT)):          # pick the largest clean unit
            f = SECONDS_PER_UNIT[unit]
            if s >= f and abs(s / f - round(s / f, 2)) < 1e-9:
                self.unit.setCurrentText(unit)
                self.spin.setValue(s / f)
                return
        self.unit.setCurrentText("seconds")
        self.spin.setValue(s)


class ServerListWorker(QtCore.QThread):
    done = Signal(object, str)  # list[Endpoint], error

    def __init__(self, backend: BackendBase, parent=None):
        super().__init__(parent)
        self.backend = backend

    def run(self) -> None:
        try:
            self.done.emit(self.backend.list_servers(), "")
        except Exception as exc:
            self.done.emit([], str(exc))


# ---------------------------------------------------------------------------
# %%% Plot panel (pyqtgraph grid mirrored by the Veusz export)
# ---------------------------------------------------------------------------
class PlotPanel(QtWidgets.QWidget):
    """Six linked pyqtgraph panels (3 rows x 2 cols) — mirrored by the Veusz export."""
    PANELS = [("download_mbps", 0, 0), ("upload_mbps", 0, 1), ("latency_ms", 1, 0),
              ("jitter_ms", 1, 1), ("packet_loss_pct", 2, 0), ("dl_loaded_latency_ms", 2, 1)]

    def __init__(self, dark: bool, parent=None):
        super().__init__(parent)
        self.dark = dark
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        bar = QtWidgets.QHBoxLayout()
        self.chk_raw = QtWidgets.QCheckBox("Raw per-endpoint")
        self.chk_raw.setChecked(True)
        self.chk_avg = QtWidgets.QCheckBox("Round average ± std")
        self.chk_avg.setChecked(True)
        self.chk_utc = QtWidgets.QCheckBox("UTC time axis")
        self.btn_auto = QtWidgets.QPushButton("Autoscale")
        for wdg in (self.chk_raw, self.chk_avg, self.chk_utc):
            bar.addWidget(wdg)
        bar.addStretch(1)
        bar.addWidget(self.btn_auto)
        lay.addLayout(bar)
        if pg is None:
            lay.addWidget(QtWidgets.QLabel("pyqtgraph not installed — pip install pyqtgraph"))
            return
        self.glw = pg.GraphicsLayoutWidget()
        lay.addWidget(self.glw, 1)
        self.plots: Dict[str, Any] = {}
        self.raw_items: Dict[str, Dict[str, Any]] = {m: {} for m, _, _ in self.PANELS}   # metric -> ep -> item
        self.avg_items: Dict[str, Any] = {}
        self.err_items: Dict[str, Any] = {}
        self.raw_data: Dict[str, Dict[str, List[float]]] = {}  # ep_key -> {'t': [], metric: []}
        self.avg_data: Dict[str, List[float]] = {"t": []} | {f"{m}_{s}": [] for m in METRICS for s in ("mean", "std")}
        self.ep_color: Dict[str, str] = {}
        self.ep_label: Dict[str, str] = {}
        first = None
        for metric, row, col in self.PANELS:
            label, unit = METRIC_LABELS[metric]
            axis = pg.DateAxisItem(orientation="bottom")
            p = self.glw.addPlot(row=row, col=col, axisItems={"bottom": axis})
            p.setTitle(label, size="10pt")
            p.setLabel("left", unit)
            p.getAxis("left").enableAutoSIPrefix(False)   # no "% (x0.001)" style prefixes
            p.showGrid(x=True, y=True, alpha=0.25)
            p.setClipToView(True)
            if first is None:
                first = p
                p.addLegend(offset=(-10, 10), labelTextSize="8pt", brush=pg.mkBrush(255, 255, 255, 170))
            else:
                p.setXLink(first)
            self.plots[metric] = p
        self.chk_raw.toggled.connect(self._toggle_vis)
        self.chk_avg.toggled.connect(self._toggle_vis)
        self.chk_utc.toggled.connect(self._set_axis_mode)
        self.btn_auto.clicked.connect(self.autoscale)

    # -- theming ------------------------------------------------------------------
    def set_dark(self, dark: bool) -> None:
        """Re-colour an existing plot grid for the light/dark theme (pyqtgraph's
        global foreground option only affects items created afterwards)."""
        self.dark = dark
        if pg is None or not hasattr(self, "glw"):
            return
        fg = (220, 220, 220) if dark else "k"
        avg_col = AVG_COLOR_DARK if dark else AVG_COLOR_LIGHT
        self.glw.setBackground((30, 30, 32) if dark else "w")
        for metric, p in self.plots.items():
            label, unit = METRIC_LABELS[metric]
            p.setTitle(label, size="10pt", color=fg)
            for side in ("left", "bottom"):
                ax = p.getAxis(side)
                ax.setPen(pg.mkPen(fg))
                ax.setTextPen(pg.mkPen(fg))
            p.setLabel("left", unit, color=fg)
            if p.legend is not None:
                p.legend.setLabelTextColor(fg)
                p.legend.setBrush(pg.mkBrush(40, 40, 44, 200) if dark else pg.mkBrush(255, 255, 255, 170))
            if metric in self.avg_items:
                self.avg_items[metric].setPen(pg.mkPen(avg_col, width=2.5))
                self.avg_items[metric].setSymbolBrush(avg_col)
            if metric in self.err_items:
                self.err_items[metric].setData(pen=pg.mkPen(avg_col, width=1))

    # -- data management --------------------------------------------------------
    def reset(self, endpoints: List[Endpoint]) -> None:
        if pg is None:
            return
        for metric, p in self.plots.items():
            p.clear()
            if p.legend is not None:
                p.legend.clear()
        self.raw_items = {m: {} for m, _, _ in self.PANELS}
        self.avg_items, self.err_items, self.raw_data = {}, {}, {}
        self.avg_data = {"t": []} | {f"{m}_{s}": [] for m in METRICS for s in ("mean", "std")}
        self.ep_color, self.ep_label = {}, {}
        avg_col = AVG_COLOR_DARK if self.dark else AVG_COLOR_LIGHT
        for i, ep in enumerate(endpoints):
            c = PLOT_COLORS[i % len(PLOT_COLORS)]
            self.ep_color[ep.key] = c
            self.ep_label[ep.key] = ep.name or ep.host or ep.server_id
            self.raw_data[ep.key] = {"t": []} | {m: [] for m in METRICS}
            for metric, p in self.plots.items():
                item = p.plot([], [], pen=pg.mkPen(c, width=1), symbol="o", symbolSize=4,
                              symbolBrush=c, symbolPen=None, name=self.ep_label[ep.key] if metric == "download_mbps" else None)
                self.raw_items[metric][ep.key] = item
        for metric, p in self.plots.items():
            self.err_items[metric] = pg.ErrorBarItem(x=np.array([]), y=np.array([]), height=np.array([]),
                                                     beam=0, pen=pg.mkPen(avg_col, width=1))
            p.addItem(self.err_items[metric])
            self.avg_items[metric] = p.plot([], [], pen=pg.mkPen(avg_col, width=2.5), symbol="s", symbolSize=6,
                                            symbolBrush=avg_col, symbolPen=None,
                                            name="Round average ± std" if metric == "download_mbps" else None)
        self._toggle_vis()

    def add_result(self, r: TestResult) -> None:
        if pg is None or r.endpoint_key not in self.raw_data:
            return
        d = self.raw_data[r.endpoint_key]
        d["t"].append(r.epoch_s)
        for m in METRICS:
            d[m].append(getattr(r, m) if r.ok else math.nan)
        for m in METRICS:
            if m in self.raw_items:
                self.raw_items[m][r.endpoint_key].setData(np.array(d["t"]), np.array(d[m]), connect="finite")

    def add_round(self, rs: RoundSummary) -> None:
        if pg is None:
            return
        self.avg_data["t"].append(rs.epoch_s)
        for m in METRICS:
            self.avg_data[f"{m}_mean"].append(rs.get(m, "mean"))
            self.avg_data[f"{m}_std"].append(rs.get(m, "std"))
        t = np.array(self.avg_data["t"])
        for m in self.plots:
            y = np.array(self.avg_data[f"{m}_mean"])
            s = np.nan_to_num(np.array(self.avg_data[f"{m}_std"]), nan=0.0)
            self.avg_items[m].setData(t, y, connect="finite")
            ok = np.isfinite(y)
            self.err_items[m].setData(x=t[ok], y=y[ok], height=2 * s[ok])

    def _toggle_vis(self) -> None:
        if pg is None:
            return
        for m in self.plots:
            for it in self.raw_items[m].values():
                it.setVisible(self.chk_raw.isChecked())
            if m in self.avg_items:
                self.avg_items[m].setVisible(self.chk_avg.isChecked())
                self.err_items[m].setVisible(self.chk_avg.isChecked())

    def _set_axis_mode(self, utc: bool) -> None:
        for m, p in self.plots.items():
            p.setAxisItems({"bottom": pg.DateAxisItem(orientation="bottom", utcOffset=0 if utc else None)})

    def autoscale(self) -> None:
        for p in self.plots.values():
            p.enableAutoRange()


# ---------------------------------------------------------------------------
# %%% Main window
# ---------------------------------------------------------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, app: QtWidgets.QApplication):
        super().__init__()
        self.app = app
        self.settings = QtCore.QSettings(ORG_NAME, "isp_speed_monitor")
        self.theme_mode = str(self.settings.value("theme", "system"))
        if self.theme_mode not in THEME_MODES:          # migrate pre-1.1 "dark" bool
            self.theme_mode = "dark" if self.settings.value("dark", False, type=bool) else "system"
        self.dark = apply_theme(app, self.theme_mode)
        self.setWindowTitle(f"{APP_NAME} v{__version__}")
        self.resize(1380, 900)
        self.ctrl = CampaignController(self)
        self.selected: List[Endpoint] = []
        self.server_cache: List[Endpoint] = []
        self._list_worker: Optional[ServerListWorker] = None
        self._build_ui()
        self._wire()
        self._load_settings()
        self._refresh_backend_status()
        QtCore.QTimer.singleShot(400, self.refresh_servers)

    # ---------------------------------------------------------------- UI build
    # %%%% UI build: menu bar, tool bar, tabs
    def _build_ui(self) -> None:
        self._build_actions()
        self._build_menubar()
        tb = self.addToolBar("Main")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        for a in (self.act_start, self.act_stop, self.act_once, None, self.act_export, self.act_open_dir,
                  None, self.act_save_cfg, self.act_load_cfg):
            tb.addSeparator() if a is None else tb.addAction(a)

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tabs.addTab(self._build_setup_tab(), "Setup")
        self.tabs.addTab(self._build_live_tab(), "Live")
        self.plot_panel = PlotPanel(self.dark)
        self.tabs.addTab(self.plot_panel, "Plots")
        self.tabs.addTab(self._build_data_tab(), "Data")
        self.status_backend = QtWidgets.QLabel("")
        self.statusBar().addPermanentWidget(self.status_backend)
        self.statusBar().showMessage("Ready")

    def _build_actions(self) -> None:
        st, SP = self.style(), QtWidgets.QStyle
        def act(text, icon=None, shortcut=None, tip=None, checkable=False):
            a = QtGui.QAction(st.standardIcon(icon), text, self) if icon is not None else QtGui.QAction(text, self)
            if shortcut:
                a.setShortcut(QtGui.QKeySequence(shortcut))
            if tip:
                a.setStatusTip(tip)
            a.setCheckable(checkable)
            return a
        # File
        self.act_new_cfg = act("&New campaign config", SP.SP_FileIcon, "Ctrl+N", "Reset all Setup fields to defaults")
        self.act_load_cfg = act("&Open config…", SP.SP_DialogOpenButton, "Ctrl+O", "Load a campaign config JSON")
        self.act_save_cfg = act("&Save config…", SP.SP_DialogSaveButton, "Ctrl+S", "Save the current Setup as JSON")
        self.act_export = act("&Export now (JSON/CSV/Veusz)", SP.SP_DriveHDIcon, "Ctrl+E", "Write JSON, CSV and .vszh5 for the current/latest campaign")
        self.act_open_dir = act("Open output &folder", SP.SP_DirOpenIcon, "Ctrl+Shift+O")
        self.act_quit = act("&Quit", SP.SP_DialogCloseButton, "Ctrl+Q")
        # Campaign
        self.act_start = act("&Start campaign", SP.SP_MediaPlay, "F5")
        self.act_stop = act("S&top", SP.SP_MediaStop, "Shift+F5")
        self.act_stop.setEnabled(False)
        self.act_once = act("Run &one round now", SP.SP_MediaSkipForward, "F6", "One test round over the selected endpoints, no schedule")
        self.act_refresh_servers = act("&Refresh server list", SP.SP_BrowserReload, "F7")
        # View
        self.theme_group = QtGui.QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.act_theme: Dict[str, QtGui.QAction] = {}
        for key, label in (("system", "&System (follow OS)"), ("light", "&Light"), ("dark", "&Dark")):
            a = act(label, checkable=True)
            a.setData(key)
            a.setChecked(key == self.theme_mode)
            self.theme_group.addAction(a)
            self.act_theme[key] = a
        self.act_tab: List[QtGui.QAction] = [act(f"&{i + 1} {name}", shortcut=f"Ctrl+{i + 1}")
                                              for i, name in enumerate(("Setup", "Live", "Plots", "Data"))]
        self.act_reset_layout = act("Reset &window size")
        # Tools
        self.act_reexport = act("Re-export from &database…", tip="Regenerate JSON/CSV/Veusz from an existing speedtests.sqlite3")
        self.act_template = act("Write &template config…")
        self.act_check_backends = act("&Check back-ends", tip="Probe Ookla / LibreSpeed / python speedtest-cli availability")
        self.act_diagnose = act("&Diagnose selected endpoint…", tip="Run one raw test for the highlighted endpoint and show the exact command line and output")
        self.act_view_log = act("Open &log file")
        # Help
        self.act_readme = act("&README (bundle)")
        self.act_url_ookla = act("Ookla Speedtest &CLI download")
        self.act_url_libre = act("&LibreSpeed CLI releases")
        self.act_url_veusz = act("&Veusz home page")
        self.act_about = act("&About " + APP_NAME, SP.SP_MessageBoxInformation)
        self.act_about_qt = act("About &Qt")

    def _build_menubar(self) -> None:
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        for a in (self.act_new_cfg, self.act_load_cfg, self.act_save_cfg, None, self.act_export, self.act_open_dir,
                  None, self.act_quit):
            m_file.addSeparator() if a is None else m_file.addAction(a)
        m_camp = mb.addMenu("&Campaign")
        for a in (self.act_start, self.act_stop, self.act_once, None, self.act_refresh_servers):
            m_camp.addSeparator() if a is None else m_camp.addAction(a)
        m_view = mb.addMenu("&View")
        m_theme = m_view.addMenu("&Theme")
        for a in self.act_theme.values():
            m_theme.addAction(a)
        m_view.addSeparator()
        m_tabs = m_view.addMenu("&Go to tab")
        for a in self.act_tab:
            m_tabs.addAction(a)
        m_view.addSeparator()
        m_view.addAction(self.act_reset_layout)
        m_tools = mb.addMenu("&Tools")
        for a in (self.act_reexport, self.act_template, None, self.act_check_backends, self.act_diagnose, self.act_view_log):
            m_tools.addSeparator() if a is None else m_tools.addAction(a)
        m_help = mb.addMenu("&Help")
        for a in (self.act_readme, None, self.act_url_ookla, self.act_url_libre, self.act_url_veusz, None,
                  self.act_about, self.act_about_qt):
            m_help.addSeparator() if a is None else m_help.addAction(a)

    # %%%% UI build: Setup tab
    def _build_setup_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        outer = QtWidgets.QHBoxLayout(w)
        # ---- left: endpoints -------------------------------------------------
        grp_ep = QtWidgets.QGroupBox("Endpoints (speed-test servers)")
        v = QtWidgets.QVBoxLayout(grp_ep)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Back-end:"))
        self.cmb_backend = QtWidgets.QComboBox()
        for k, c in BACKEND_CLASSES.items():
            self.cmb_backend.addItem(c.label, k)
        row.addWidget(self.cmb_backend, 1)
        self.btn_refresh = QtWidgets.QPushButton("Refresh server list")
        row.addWidget(self.btn_refresh)
        v.addLayout(row)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Ookla exe:"))
        self.ed_ookla = QtWidgets.QLineEdit()
        self.ed_ookla.setPlaceholderText("auto (PATH)")
        row.addWidget(self.ed_ookla, 1)
        b = QtWidgets.QPushButton("…")
        b.setFixedWidth(28)
        b.clicked.connect(lambda: self._browse_exe(self.ed_ookla))
        row.addWidget(b)
        row.addWidget(QtWidgets.QLabel("LibreSpeed exe:"))
        self.ed_libre = QtWidgets.QLineEdit()
        self.ed_libre.setPlaceholderText("auto (PATH)")
        row.addWidget(self.ed_libre, 1)
        b = QtWidgets.QPushButton("…")
        b.setFixedWidth(28)
        b.clicked.connect(lambda: self._browse_exe(self.ed_libre))
        row.addWidget(b)
        v.addLayout(row)
        self.ed_filter = QtWidgets.QLineEdit()
        self.ed_filter.setPlaceholderText("filter servers (name / location / host / id)…")
        v.addWidget(self.ed_filter)
        self.tbl_servers = QtWidgets.QTableWidget(0, 5)
        self.tbl_servers.setHorizontalHeaderLabels(["ID", "Name", "Location", "Country", "Host"])
        self.tbl_servers.horizontalHeader().setStretchLastSection(True)
        self.tbl_servers.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_servers.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.tbl_servers.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl_servers.verticalHeader().setVisible(False)
        v.addWidget(self.tbl_servers, 2)
        row = QtWidgets.QHBoxLayout()
        self.btn_add_sel = QtWidgets.QPushButton("Add selected ↓")
        self.ed_manual_id = QtWidgets.QLineEdit()
        self.ed_manual_id.setToolTip("Server id (e.g. 14229), Ookla host name (e.g. ashburn.va.speedtest.frontier.com) or auto = nearest")
        self.ed_manual_id.setPlaceholderText("server id (e.g. 14229), host name (Ookla, e.g. ashburn.va.speedtest.frontier.com) or 'auto'")
        self.btn_add_manual = QtWidgets.QPushButton("Add by ID")
        row.addWidget(self.btn_add_sel)
        row.addStretch(1)
        row.addWidget(self.ed_manual_id, 1)
        row.addWidget(self.btn_add_manual)
        v.addLayout(row)
        v.addWidget(QtWidgets.QLabel("Selected endpoints — tested sequentially every round, averaged per round:"))
        self.lst_selected = QtWidgets.QListWidget()
        self.lst_selected.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        v.addWidget(self.lst_selected, 1)
        row = QtWidgets.QHBoxLayout()
        self.btn_remove = QtWidgets.QPushButton("Remove selected")
        self.btn_clear = QtWidgets.QPushButton("Clear")
        row.addWidget(self.btn_remove)
        row.addWidget(self.btn_clear)
        row.addStretch(1)
        v.addLayout(row)
        outer.addWidget(grp_ep, 3)

        # ---- right: schedule + outputs ---------------------------------------
        right = QtWidgets.QVBoxLayout()
        grp_s = QtWidgets.QGroupBox("Schedule")
        f = QtWidgets.QFormLayout(grp_s)
        f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.rad_interval = QtWidgets.QRadioButton("Fixed interval")
        self.rad_random = QtWidgets.QRadioButton("Random gap between tests")
        self.rad_window = QtWidgets.QRadioButton("N random tests per window")
        self.rad_interval.setChecked(True)
        self.dur_interval = DurationEdit(15, "minutes", minimum=0.01)
        self.dur_min = DurationEdit(5, "minutes", minimum=0.01)
        self.dur_max = DurationEdit(30, "minutes", minimum=0.01)
        self.spn_per_window = QtWidgets.QSpinBox()
        self.spn_per_window.setRange(1, 10000)
        self.spn_per_window.setValue(4)
        self.dur_window = DurationEdit(1, "hours", minimum=0.01)
        f.addRow(self.rad_interval, self.dur_interval)
        f.addRow(self.rad_random, self._hbox(QtWidgets.QLabel("min"), self.dur_min, QtWidgets.QLabel("max"), self.dur_max))
        f.addRow(self.rad_window, self._hbox(self.spn_per_window, QtWidgets.QLabel("tests per"), self.dur_window))
        self.chk_first_now = QtWidgets.QCheckBox("First test immediately at start")
        self.chk_first_now.setChecked(True)
        f.addRow("", self.chk_first_now)
        self.dur_total = DurationEdit(1, "days", minimum=0.0)
        self.chk_indef = QtWidgets.QCheckBox("Run until stopped")
        f.addRow("Campaign length:", self._hbox(self.dur_total, self.chk_indef))
        self.ed_end_at = QtWidgets.QLineEdit()
        self.ed_end_at.setPlaceholderText("optional ISO end, e.g. 2026-10-01T06:00 (local) — overrides length")
        f.addRow("End at:", self.ed_end_at)
        self.ed_start_at = QtWidgets.QLineEdit()
        self.ed_start_at.setPlaceholderText("optional ISO start, e.g. 2026-09-05T00:00 (local); blank = now")
        f.addRow("Start at:", self.ed_start_at)
        self.spn_timeout = QtWidgets.QSpinBox()
        self.spn_timeout.setRange(10, 3600)
        self.spn_timeout.setValue(DEFAULT_TEST_TIMEOUT_S)
        self.spn_timeout.setSuffix(" s")
        self.spn_pause = QtWidgets.QDoubleSpinBox()
        self.spn_pause.setRange(0, 3600)
        self.spn_pause.setValue(DEFAULT_PAUSE_BETWEEN_ENDPOINTS_S)
        self.spn_pause.setSuffix(" s")
        f.addRow("Per-test timeout:", self._hbox(self.spn_timeout, QtWidgets.QLabel("pause between endpoints"), self.spn_pause))
        self.chk_dl = QtWidgets.QCheckBox("Download")
        self.chk_ul = QtWidgets.QCheckBox("Upload")
        self.chk_dl.setChecked(True)
        self.chk_ul.setChecked(True)
        f.addRow("Test:", self._hbox(self.chk_dl, self.chk_ul, QtWidgets.QLabel("(Ookla CLI always runs both)")))
        self.lbl_sched_summary = QtWidgets.QLabel("")
        self.lbl_sched_summary.setWordWrap(True)
        f.addRow("Summary:", self.lbl_sched_summary)
        right.addWidget(grp_s)

        grp_o = QtWidgets.QGroupBox("Outputs")
        f = QtWidgets.QFormLayout(grp_o)
        f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        self.ed_name = QtWidgets.QLineEdit("campaign")
        f.addRow("Campaign name:", self.ed_name)
        self.ed_outdir = QtWidgets.QLineEdit(DEFAULT_OUTPUT_DIR)
        b = QtWidgets.QPushButton("…")
        b.setFixedWidth(28)
        b.clicked.connect(self._browse_outdir)
        f.addRow("Output folder:", self._hbox(self.ed_outdir, b))
        self.chk_jsonl = QtWidgets.QCheckBox("JSONL append logs (results.jsonl / rounds.jsonl)")
        self.chk_json = QtWidgets.QCheckBox("JSON campaign dump")
        self.chk_csv = QtWidgets.QCheckBox("CSV (results + rounds)")
        self.chk_veusz = QtWidgets.QCheckBox("Veusz HDF5 document (.vszh5)")
        for c in (self.chk_jsonl, self.chk_json, self.chk_csv, self.chk_veusz):
            c.setChecked(True)
            f.addRow("", c)
        self.cmb_vz_axis = QtWidgets.QComboBox()
        self.cmb_vz_axis.addItems(["local", "utc"])
        f.addRow("Veusz time axis:", self.cmb_vz_axis)
        self.spn_autoexp = QtWidgets.QSpinBox()
        self.spn_autoexp.setRange(0, 100000)
        self.spn_autoexp.setValue(DEFAULT_EXPORT_EVERY_N)
        self.spn_autoexp.setSpecialValueText("only at end")
        self.spn_autoexp.setToolTip("Rewrite the JSON / CSV / Veusz files from the database every N tests or rounds "
                                    "(stable file names, atomic replace). 0 = write them only when the campaign ends.\n"
                                    "SQLite and the JSONL logs are always written after every single test.")
        self.cmb_export_unit = QtWidgets.QComboBox()
        self.cmb_export_unit.addItems(list(EXPORT_UNITS))
        self.cmb_export_unit.setCurrentText(DEFAULT_EXPORT_UNIT)
        row_exp = QtWidgets.QHBoxLayout()
        row_exp.addWidget(self.spn_autoexp, 1)
        row_exp.addWidget(self.cmb_export_unit)
        f.addRow("Refresh output files every:", row_exp)
        self.ed_notes = QtWidgets.QLineEdit()
        self.ed_notes.setPlaceholderText("free-text notes stored with the campaign (ISP plan, location, …)")
        f.addRow("Notes:", self.ed_notes)
        lbl = QtWidgets.QLabel("SQLite database and JSONL logs are written after every test: <output folder>/" + DB_FILENAME + "; "
                              "JSON/CSV/Veusz are rewritten in place at the refresh interval above and at the end")
        lbl.setEnabled(False)
        f.addRow("", lbl)
        right.addWidget(grp_o)
        right.addStretch(1)
        outer.addLayout(right, 2)
        return w

    # %%%% UI build: Live tab
    def _build_live_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        grid = QtWidgets.QGridLayout()
        big = QtGui.QFont()
        big.setPointSize(big.pointSize() + 6)
        big.setBold(True)
        self.lbl_state = QtWidgets.QLabel("idle")
        self.lbl_state.setFont(big)
        self.lbl_next = QtWidgets.QLabel("—")
        self.lbl_next.setFont(big)
        self.lbl_rounds = QtWidgets.QLabel("0")
        self.lbl_rounds.setFont(big)
        self.lbl_last = QtWidgets.QLabel("—")
        self.lbl_last.setFont(big)
        for i, (cap, lab) in enumerate([("State", self.lbl_state), ("Next test in", self.lbl_next),
                                        ("Rounds completed", self.lbl_rounds), ("Last round avg ↓ / ↑ / ping", self.lbl_last)]):
            c = QtWidgets.QLabel(cap)
            c.setEnabled(False)
            grid.addWidget(c, 0, i)
            grid.addWidget(lab, 1, i)
        v.addLayout(grid)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setFormat("%v / %m endpoints")
        self.lbl_progress = QtWidgets.QLabel("")
        v.addWidget(self.progress)
        v.addWidget(self.lbl_progress)
        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumBlockCount(5000)
        self.txt_log.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        v.addWidget(self.txt_log, 1)
        return w

    # %%%% UI build: Data tab
    def _build_data_tab(self) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        split = QtWidgets.QSplitter(Qt.Vertical)
        self.tbl_rounds = QtWidgets.QTableWidget(0, 12)
        self.tbl_rounds.setHorizontalHeaderLabels(["Round", "UTC", "Local", "OK/plan", "↓ mean", "↓ std", "↑ mean", "↑ std",
                                                   "ping mean", "jitter mean", "loss mean", "dur s"])
        self.tbl_results = QtWidgets.QTableWidget(0, 13)
        self.tbl_results.setHorizontalHeaderLabels(["UTC", "Local", "Endpoint", "Backend", "ID", "OK", "↓ Mbit/s", "↑ Mbit/s",
                                                    "ping ms", "jitter ms", "loss %", "loaded ↓ ms", "Error / URL"])
        for t in (self.tbl_rounds, self.tbl_results):
            t.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            t.verticalHeader().setVisible(False)
            t.horizontalHeader().setStretchLastSection(True)
            t.setAlternatingRowColors(True)
        box1 = QtWidgets.QGroupBox("Round averages (newest first)")
        QtWidgets.QVBoxLayout(box1).addWidget(self.tbl_rounds)
        box2 = QtWidgets.QGroupBox("Raw results (newest first)")
        QtWidgets.QVBoxLayout(box2).addWidget(self.tbl_results)
        split.addWidget(box1)
        split.addWidget(box2)
        split.setSizes([300, 500])
        v.addWidget(split)
        return w

    @staticmethod
    def _hbox(*widgets) -> QtWidgets.QWidget:
        w = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        for x in widgets:
            h.addWidget(x, 1 if isinstance(x, (QtWidgets.QLineEdit, DurationEdit)) else 0)
        return w

    # ---------------------------------------------------------------- wiring
    # %%%% Signal wiring
    def _wire(self) -> None:
        self.act_start.triggered.connect(self.start_campaign)
        self.act_stop.triggered.connect(self.ctrl.stop)
        self.act_once.triggered.connect(self.run_once)
        self.act_export.triggered.connect(self.export_now)
        self.act_open_dir.triggered.connect(self.open_outdir)
        self.act_save_cfg.triggered.connect(self.save_config)
        self.act_load_cfg.triggered.connect(self.load_config)
        self.act_new_cfg.triggered.connect(self.new_config)
        self.act_quit.triggered.connect(self.close)
        self.act_refresh_servers.triggered.connect(self.refresh_servers)
        self.theme_group.triggered.connect(lambda a: self.set_theme(a.data()))
        for i, a in enumerate(self.act_tab):
            a.triggered.connect(lambda _c=False, i=i: self.tabs.setCurrentIndex(i))
        self.act_reset_layout.triggered.connect(lambda: self.resize(1380, 900))
        self.act_reexport.triggered.connect(self.reexport_dialog)
        self.act_template.triggered.connect(self.write_template)
        self.act_check_backends.triggered.connect(self.check_backends)
        self.act_diagnose.triggered.connect(self.diagnose_endpoint)
        self.act_view_log.triggered.connect(self.open_log)
        self.act_readme.triggered.connect(self.open_readme)
        self.act_url_ookla.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(URL_OOKLA_CLI)))
        self.act_url_libre.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(URL_LIBRESPEED_CLI)))
        self.act_url_veusz.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(URL_VEUSZ)))
        self.act_about.triggered.connect(self.show_about)
        self.act_about_qt.triggered.connect(lambda: QtWidgets.QMessageBox.aboutQt(self, "About Qt"))
        self.btn_refresh.clicked.connect(self.refresh_servers)
        self.cmb_backend.currentIndexChanged.connect(lambda _i: (self._refresh_backend_status(), self.refresh_servers()))
        self.ed_filter.textChanged.connect(self._filter_servers)
        self.btn_add_sel.clicked.connect(self.add_selected_servers)
        self.tbl_servers.doubleClicked.connect(lambda _i: self.add_selected_servers())
        self.btn_add_manual.clicked.connect(self.add_manual_id)
        self.ed_manual_id.returnPressed.connect(self.add_manual_id)
        self.btn_remove.clicked.connect(self.remove_selected)
        self.btn_clear.clicked.connect(lambda: (self.selected.clear(), self._refresh_selected()))
        for wdg in (self.rad_interval, self.rad_random, self.rad_window, self.chk_indef, self.chk_first_now):
            wdg.toggled.connect(self._update_summary)
        for de in (self.dur_interval, self.dur_min, self.dur_max, self.dur_window, self.dur_total):
            de.spin.valueChanged.connect(self._update_summary)
            de.unit.currentIndexChanged.connect(self._update_summary)
        self.spn_per_window.valueChanged.connect(self._update_summary)
        self.ed_end_at.textChanged.connect(self._update_summary)
        self.ed_start_at.textChanged.connect(self._update_summary)
        self.chk_indef.toggled.connect(lambda on: self.dur_total.setEnabled(not on))
        c = self.ctrl
        c.sig_log.connect(self.txt_log.appendPlainText)
        c.sig_state.connect(self._on_state)
        c.sig_result.connect(self._on_result)
        c.sig_round.connect(self._on_round)
        c.sig_progress.connect(self._on_progress)
        c.sig_tick.connect(self._on_tick)
        c.sig_finished.connect(self._on_finished)
        c.sig_exported.connect(lambda files: self.statusBar().showMessage("Exported: " + "; ".join(os.path.basename(f) for f in files), 15000))
        self._update_summary()

    # ---------------------------------------------------------------- config <-> widgets
    # %%%% Config <-> widgets, persistent settings
    def collect_config(self) -> CampaignConfig:
        sc = ScheduleConfig(
            mode="interval" if self.rad_interval.isChecked() else "random_gap" if self.rad_random.isChecked() else "random_per_window",
            interval_s=self.dur_interval.seconds(), min_gap_s=self.dur_min.seconds(), max_gap_s=self.dur_max.seconds(),
            window_s=self.dur_window.seconds(), per_window=self.spn_per_window.value(),
            duration_s=0.0 if self.chk_indef.isChecked() else self.dur_total.seconds(),
            end_at_local=self.ed_end_at.text().strip(), start_at_local=self.ed_start_at.text().strip(),
            first_test_immediately=self.chk_first_now.isChecked())
        return CampaignConfig(
            name=self.ed_name.text().strip() or "campaign", output_dir=self.ed_outdir.text().strip() or DEFAULT_OUTPUT_DIR,
            endpoints=[asdict(e) for e in self.selected], schedule=asdict(sc),
            ookla_exe=self.ed_ookla.text().strip(), librespeed_exe=self.ed_libre.text().strip(),
            test_download=self.chk_dl.isChecked(), test_upload=self.chk_ul.isChecked(),
            test_timeout_s=self.spn_timeout.value(), pause_between_endpoints_s=self.spn_pause.value(),
            write_jsonl=self.chk_jsonl.isChecked(), export_json=self.chk_json.isChecked(),
            export_csv=self.chk_csv.isChecked(), export_veusz=self.chk_veusz.isChecked(),
            veusz_time_axis=self.cmb_vz_axis.currentText(), export_every_n=self.spn_autoexp.value(),
            export_every_unit=self.cmb_export_unit.currentText(),
            notes=self.ed_notes.text())

    def apply_config(self, cfg: CampaignConfig) -> None:
        sc = cfg.schedule_obj()
        {"interval": self.rad_interval, "random_gap": self.rad_random, "random_per_window": self.rad_window}.get(sc.mode, self.rad_interval).setChecked(True)
        self.dur_interval.set_seconds(sc.interval_s)
        self.dur_min.set_seconds(sc.min_gap_s)
        self.dur_max.set_seconds(sc.max_gap_s)
        self.dur_window.set_seconds(sc.window_s)
        self.spn_per_window.setValue(int(sc.per_window))
        self.chk_indef.setChecked(not sc.duration_s)
        if sc.duration_s:
            self.dur_total.set_seconds(sc.duration_s)
        self.ed_end_at.setText(sc.end_at_local)
        self.ed_start_at.setText(sc.start_at_local)
        self.chk_first_now.setChecked(sc.first_test_immediately)
        self.ed_name.setText(cfg.name)
        self.ed_outdir.setText(cfg.output_dir)
        self.ed_ookla.setText(cfg.ookla_exe)
        self.ed_libre.setText(cfg.librespeed_exe)
        self.chk_dl.setChecked(cfg.test_download)
        self.chk_ul.setChecked(cfg.test_upload)
        self.spn_timeout.setValue(int(cfg.test_timeout_s))
        self.spn_pause.setValue(float(cfg.pause_between_endpoints_s))
        self.chk_jsonl.setChecked(cfg.write_jsonl)
        self.chk_json.setChecked(cfg.export_json)
        self.chk_csv.setChecked(cfg.export_csv)
        self.chk_veusz.setChecked(cfg.export_veusz)
        self.cmb_vz_axis.setCurrentText(cfg.veusz_time_axis)
        self.spn_autoexp.setValue(int(cfg.export_every_n))
        self.cmb_export_unit.setCurrentText(cfg.export_every_unit if cfg.export_every_unit in EXPORT_UNITS else DEFAULT_EXPORT_UNIT)
        self.ed_notes.setText(cfg.notes)
        self.selected = cfg.endpoint_objs()
        self._refresh_selected()
        self._update_summary()

    def _load_settings(self) -> None:
        geo = self.settings.value("geometry")
        if geo:
            self.restoreGeometry(geo)
        raw = self.settings.value("last_config", "")
        if raw:
            try:
                self.apply_config(CampaignConfig.from_dict(json.loads(raw)))
            except Exception as exc:
                logger.warning("could not restore last config: %s", exc)

    def _save_settings(self) -> None:
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("theme", self.theme_mode)
        try:
            self.settings.setValue("last_config", self.collect_config().to_json())
        except Exception:
            pass

    # ---------------------------------------------------------------- servers
    # %%%% Back-end status and server list
    def _current_backend(self) -> BackendBase:
        key = self.cmb_backend.currentData()
        cfg = CampaignConfig(ookla_exe=self.ed_ookla.text().strip(), librespeed_exe=self.ed_libre.text().strip())
        return make_backend(key, cfg)

    def _refresh_backend_status(self) -> None:
        be = self._current_backend()
        ok, msg = be.available()
        self.status_backend.setText(("✓ " if ok else "✗ ") + msg)
        self.status_backend.setStyleSheet("" if ok else "color:#d62728")

    def refresh_servers(self) -> None:
        if self._list_worker is not None and self._list_worker.isRunning():
            return
        be = self._current_backend()
        ok, msg = be.available()
        if not ok:
            self.tbl_servers.setRowCount(0)
            self.statusBar().showMessage(msg, 8000)
            return
        self.btn_refresh.setEnabled(False)
        self.statusBar().showMessage(f"Fetching server list from {be.label}…")
        self._list_worker = ServerListWorker(be, self)
        self._list_worker.done.connect(self._on_servers)
        self._list_worker.start()

    @Slot(object, str)
    def _on_servers(self, eps: List[Endpoint], err: str) -> None:
        self.btn_refresh.setEnabled(True)
        if err:
            self.statusBar().showMessage(f"Server list failed: {err}", 10000)
        self.server_cache = eps
        self._filter_servers(self.ed_filter.text())
        self.statusBar().showMessage(f"{len(eps)} servers listed", 5000)

    def _filter_servers(self, text: str) -> None:
        text = (text or "").lower()
        t = self.tbl_servers
        t.setSortingEnabled(False)
        t.setRowCount(0)
        for ep in self.server_cache:
            hay = " ".join((ep.server_id, ep.name, ep.location, ep.country, ep.host)).lower()
            if text and text not in hay:
                continue
            r = t.rowCount()
            t.insertRow(r)
            for c, val in enumerate((ep.server_id, ep.name, ep.location, ep.country, ep.host)):
                it = QtWidgets.QTableWidgetItem(val)
                if c == 0:
                    it.setData(Qt.UserRole, ep.key)
                t.setItem(r, c, it)
        t.resizeColumnsToContents()
        t.setSortingEnabled(True)

    def add_selected_servers(self) -> None:
        rows = {i.row() for i in self.tbl_servers.selectedIndexes()}
        keys = {self.tbl_servers.item(r, 0).data(Qt.UserRole) for r in rows}
        for ep in self.server_cache:
            if ep.key in keys and all(ep.key != s.key for s in self.selected):
                self.selected.append(ep)
        self._refresh_selected()

    def add_manual_id(self) -> None:
        sid = self.ed_manual_id.text().strip()
        if not sid:
            return
        key = self.cmb_backend.currentData()
        ep = next((e for e in self.server_cache if e.server_id == sid or (e.host and e.host.lower() == sid.lower())), None)
        if ep is None:
            if sid.lower() == "auto":
                ep = Endpoint(key, "auto", "nearest (auto)" if key == "ookla" else "auto")
            elif sid.isdigit():
                ep = Endpoint(key, sid, f"server {sid}")
            else:                                   # host name / FQDN (Ookla --host=)
                if key != "ookla":
                    QtWidgets.QMessageBox.information(self, APP_NAME, "Host names are only supported by the Ookla back-end; "
                                                      "use the numeric server id for other back-ends.")
                    return
                host = re.sub(r"^[a-z]+://", "", sid).split("/")[0].split(":")[0]
                ep = Endpoint(key, host, f"host {host}", host)
        if all(ep.key != s.key for s in self.selected):
            self.selected.append(ep)
        self.ed_manual_id.clear()
        self._refresh_selected()

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.lst_selected.selectedIndexes()}, reverse=True)
        for r in rows:
            del self.selected[r]
        self._refresh_selected()

    def _refresh_selected(self) -> None:
        self.lst_selected.clear()
        for i, ep in enumerate(self.selected):
            it = QtWidgets.QListWidgetItem(ep.label)
            it.setForeground(QtGui.QColor(PLOT_COLORS[i % len(PLOT_COLORS)]))
            self.lst_selected.addItem(it)
        self._update_summary()

    def _update_summary(self, *_a) -> None:
        try:
            cfg = self.collect_config()
            sch = Scheduler(cfg.schedule_obj())
            sch.start(time.time())
            n = len(self.selected)
            per_round = n * (cfg.test_timeout_s * 0.4 + cfg.pause_between_endpoints_s)
            txt = f"{n} endpoint(s); {sch.describe()}. Rough round duration ≈ {fmt_duration(per_round)} " \
                  f"(≈40 s per endpoint typical)."
            sc = cfg.schedule_obj()
            if sc.mode == "interval" and sc.interval_s < per_round:
                txt += "  ⚠ interval shorter than a round — tests will run back-to-back."
            self.lbl_sched_summary.setText(txt)
        except Exception as exc:
            self.lbl_sched_summary.setText(f"⚠ {exc}")

    # ---------------------------------------------------------------- actions
    # %%%% Menu / tool-bar actions
    def start_campaign(self) -> None:
        cfg = self.collect_config()
        if not cfg.endpoints:
            QtWidgets.QMessageBox.warning(self, APP_NAME, "Select at least one endpoint first.")
            return
        try:
            setup_logging(cfg.output_dir)
            self.plot_panel.reset(cfg.endpoint_objs())
            self.tbl_rounds.setRowCount(0)
            self.tbl_results.setRowCount(0)
            self.ctrl.start(cfg)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, APP_NAME, f"Could not start:\n{exc}")
            logger.debug(traceback.format_exc())
            return
        self._save_settings()
        self.act_start.setEnabled(False)
        self.act_stop.setEnabled(True)
        self.tabs.setCurrentIndex(1)

    def run_once(self) -> None:
        try:
            if self.ctrl.cfg is None or self.ctrl.state in ("idle", "finished"):
                # single-round "campaign": start with a schedule that ends immediately
                cfg = self.collect_config()
                if not cfg.endpoints:
                    QtWidgets.QMessageBox.warning(self, APP_NAME, "Select at least one endpoint first.")
                    return
                cfg.schedule.update({"mode": "interval", "interval_s": 1e9, "duration_s": 1.0,
                                     "end_at_local": "", "start_at_local": "", "first_test_immediately": True})
                cfg.name = cfg.name + "_single"
                setup_logging(cfg.output_dir)
                self.plot_panel.reset(cfg.endpoint_objs())
                self.tbl_rounds.setRowCount(0)
                self.tbl_results.setRowCount(0)
                self.ctrl.start(cfg)
                self.act_start.setEnabled(False)
                self.act_stop.setEnabled(True)
            else:
                self.ctrl.run_once()
            self.tabs.setCurrentIndex(1)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, APP_NAME, str(exc))

    def export_now(self) -> None:
        try:
            if self.ctrl.cfg is None or self.ctrl.cid is None:
                # export latest campaign in the configured DB
                cfg = self.collect_config()
                db = self.ctrl.open_db(cfg)
                cid = db.latest_campaign_id()
                if cid is None:
                    raise RuntimeError("no campaign in database yet")
                files = export_all(db, cid, cfg, "_manual")
                self.statusBar().showMessage("Exported: " + "; ".join(os.path.basename(f) for f in files), 15000)
            else:
                self.ctrl.export("_manual")
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, APP_NAME, f"Export failed:\n{exc}")
            logger.debug(traceback.format_exc())

    def open_outdir(self) -> None:
        d = self.ed_outdir.text().strip() or DEFAULT_OUTPUT_DIR
        os.makedirs(d, exist_ok=True)
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(d))

    def save_config(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save campaign config", os.path.join(self.ed_outdir.text(), "campaign.json"), "JSON (*.json)")
        if path:
            self.collect_config().save(path)
            self.statusBar().showMessage(f"Saved {path}", 6000)

    def load_config(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load campaign config", self.ed_outdir.text(), "JSON (*.json)")
        if path:
            try:
                self.apply_config(CampaignConfig.load(path))
                self.statusBar().showMessage(f"Loaded {path}", 6000)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, APP_NAME, f"Could not load config:\n{exc}")

    def set_theme(self, mode: str) -> None:
        self.theme_mode = mode if mode in THEME_MODES else "system"
        self.dark = apply_theme(self.app, self.theme_mode)
        self.plot_panel.set_dark(self.dark)
        self.settings.setValue("theme", self.theme_mode)
        self.act_theme[self.theme_mode].setChecked(True)
        self.statusBar().showMessage(f"Theme: {self.theme_mode}" + (" (OS reports dark)" if self.theme_mode == "system" and self.dark
                                                                    else " (OS reports light)" if self.theme_mode == "system" else ""), 4000)

    def new_config(self) -> None:
        if self.ctrl.running:
            QtWidgets.QMessageBox.information(self, APP_NAME, "Stop the running campaign before resetting the configuration.")
            return
        if QtWidgets.QMessageBox.question(self, APP_NAME, "Reset all Setup fields to defaults?",
                                          QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            self.apply_config(CampaignConfig())
            self.statusBar().showMessage("Configuration reset to defaults", 5000)

    def reexport_dialog(self) -> None:
        start = os.path.join(self.ed_outdir.text().strip() or DEFAULT_OUTPUT_DIR, DB_FILENAME)
        db_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select speed-test database", start, "SQLite (*.sqlite3 *.db *.sqlite);;All files (*)")
        if not db_path:
            return
        try:
            db = SpeedDB(db_path)
            camps = db.list_campaigns()
            db.close()
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, APP_NAME, f"Cannot open database:\n{exc}")
            return
        cid: Optional[int] = None
        if camps:
            labels = [f"{c['id']}: {c['name']}  ({c['started_local']}, {c['n_rounds']} rounds, {c['status']})" for c in camps]
            pick, ok = QtWidgets.QInputDialog.getItem(self, "Re-export", "Campaign:", labels, len(labels) - 1, False)
            if not ok:
                return
            cid = int(pick.split(":", 1)[0])
        outdir = QtWidgets.QFileDialog.getExistingDirectory(self, "Output folder for re-export", os.path.dirname(db_path))
        if not outdir:
            return
        axis = "utc" if self.cmb_vz_axis.currentText().lower().startswith("utc") else "local"
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            rc = reexport(db_path, cid, outdir, axis)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        if rc == 0:
            self.statusBar().showMessage(f"Re-exported campaign {cid if cid is not None else '(latest)'} to {outdir}", 10000)
        else:
            QtWidgets.QMessageBox.warning(self, APP_NAME, "Re-export failed — see the log for details.")

    def write_template(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Write template config", os.path.join(self.ed_outdir.text(), "campaign_template.json"), "JSON (*.json)")
        if path:
            CampaignConfig(endpoints=[asdict(Endpoint("ookla", "auto", "Ookla nearest (auto)"))]).save(path)
            self.statusBar().showMessage(f"Template written: {path}", 6000)

    def check_backends(self) -> None:
        cfg = self.collect_config()
        lines = []
        for key in ("ookla", "librespeed", "pyspeedtest", "simulated"):
            try:
                be = make_backend(key, cfg)
                ok, msg = be.available()
            except Exception as exc:
                ok, msg = False, str(exc)
            lines.append(f"{'OK ' if ok else 'NO '} {key:<12} {msg}")
        QtWidgets.QMessageBox.information(self, "Back-end check", "<pre>" + "\n".join(html.escape(l) for l in lines) + "</pre>")

    def diagnose_endpoint(self) -> None:
        """Run the exact back-end command for one endpoint and show command / rc / stdout / stderr."""
        if self.ctrl.running:
            QtWidgets.QMessageBox.information(self, APP_NAME, "Stop the running campaign first (tests must not overlap).")
            return
        rows = sorted({i.row() for i in self.lst_selected.selectedIndexes()})
        if not rows and self.selected:
            rows = [0]
        if not rows:
            QtWidgets.QMessageBox.information(self, APP_NAME, "Add an endpoint to the selected list first.")
            return
        ep = self.selected[rows[0]]
        cfg = self.collect_config()
        try:
            be = make_backend(ep.backend, cfg)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, APP_NAME, f"Back-end error:\n{exc}")
            return
        if isinstance(be, OoklaBackend):
            try:
                args = be.build_test_args(ep)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, APP_NAME, str(exc))
                return
        elif isinstance(be, LibreSpeedBackend):
            args = [be.exe(), "--json", "--server", str(ep.server_id)]
        else:
            QtWidgets.QMessageBox.information(self, APP_NAME, f"Diagnose runs external CLIs only; '{ep.backend}' is tested "
                                              f"through 'Run one round now'.")
            return
        dlg = QtWidgets.QProgressDialog(f"Running {ep.label} …\n{subprocess.list2cmdline(args)}", "Cancel", 0, 0, self)
        dlg.setWindowTitle("Diagnose endpoint")
        dlg.setMinimumDuration(0)
        dlg.setMinimumWidth(640)
        res: Dict[str, Any] = {}

        class _W(QtCore.QThread):
            def run(self_inner) -> None:
                t0 = time.time()
                try:
                    rc, out, err = be._run_cmd(args, cfg.test_timeout_s)
                    res.update(rc=rc, out=out, err=err)
                except Exception as exc:
                    res.update(rc=None, out="", err=str(exc))
                res["dt"] = time.time() - t0

        w = _W(self)
        w.finished.connect(dlg.reset)
        dlg.canceled.connect(be.abort)
        w.start()
        dlg.exec()
        w.wait(3000)
        if not res:
            return
        out_short = res["out"] if len(res["out"]) < 6000 else res["out"][:6000] + "\n… (truncated)"
        text = (f"<b>Endpoint:</b> {html.escape(ep.label)}<br><b>Command:</b><pre>{html.escape(subprocess.list2cmdline(args))}</pre>"
                f"<b>Return code:</b> {res['rc']}   <b>Elapsed:</b> {res['dt']:.1f} s<br>"
                f"<b>stdout:</b><pre>{html.escape(out_short) or '(empty)'}</pre>"
                f"<b>stderr:</b><pre>{html.escape(res['err'][:3000]) or '(empty)'}</pre>")
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Diagnose endpoint")
        box.setTextFormat(Qt.RichText)
        box.setText(text)
        box.setStandardButtons(QtWidgets.QMessageBox.Ok)
        box.exec()

    def open_log(self) -> None:
        d = self.ed_outdir.text().strip() or DEFAULT_OUTPUT_DIR
        path = os.path.join(d, LOG_FILENAME)
        if os.path.isfile(path):
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
        else:
            self.statusBar().showMessage(f"No log file yet at {path}", 6000)

    def open_readme(self) -> None:
        here = os.path.dirname(os.path.abspath(__file__))
        for cand in (os.path.join(here, "README.md"), os.path.join(here, "..", "README.md")):
            if os.path.isfile(cand):
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.path.abspath(cand)))
                return
        QtWidgets.QMessageBox.information(self, APP_NAME, "README.md was not found next to the script.")

    def show_about(self) -> None:
        try:
            import qtpy
            binding = f"{qtpy.API_NAME} {qtpy.PYSIDE_VERSION or qtpy.PYQT_VERSION}  (Qt {qtpy.QT_VERSION})"
        except Exception:
            binding = "qtpy"
        libs = [f"Python {sys.version.split()[0]}", binding, f"numpy {np.__version__}",
                f"pyqtgraph {pg.__version__ if pg else 'n/a'}", f"h5py {h5py.__version__ if h5py else 'n/a'}"]
        contact = "".join(f"<tr><td>{k}</td><td>{html.escape(v)}</td></tr>" for k, v in AUTHOR_CONTACT.items())
        text = (f"<h3>{APP_NAME} v{__version__}</h3>"
                f"<p>Scheduled / random multi-endpoint ISP speed-test logger with SQLite, JSON/JSONL, CSV and "
                f"native Veusz .vszh5 output.</p>"
                f"<p><b>Author:</b> {html.escape(AUTHOR)} — {html.escape(AUTHOR_ORG)}</p>"
                f"<table cellpadding='2'>{contact}</table>"
                f"<p><b>Libraries:</b><br>{'<br>'.join(html.escape(l) for l in libs)}</p>"
                f"<p><b>Settings:</b> {html.escape(self.settings.fileName())}<br>"
                f"<b>Theme:</b> {self.theme_mode} (effective: {'dark' if self.dark else 'light'}, style: {self.app.style().objectName()})</p>"
                f"<p>Back-ends: <a href='{URL_OOKLA_CLI}'>Ookla Speedtest CLI</a> · "
                f"<a href='{URL_LIBRESPEED_CLI}'>LibreSpeed CLI</a> · python speedtest-cli · Simulated<br>"
                f"Export format: <a href='{URL_VEUSZ}'>Veusz</a> HDF5 document</p>")
        QtWidgets.QMessageBox.about(self, f"About {APP_NAME}", text)

    def _browse_exe(self, edit: QtWidgets.QLineEdit) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select executable", edit.text() or os.getcwd())
        if path:
            edit.setText(path)
            self._refresh_backend_status()

    def _browse_outdir(self) -> None:
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Output folder", self.ed_outdir.text() or os.getcwd())
        if d:
            self.ed_outdir.setText(d)

    # ---------------------------------------------------------------- controller slots
    # %%%% Campaign controller slots
    @Slot(str)
    def _on_state(self, s: str) -> None:
        self.lbl_state.setText(s)
        colour = {"testing": "#2ca02c", "waiting": "#1f77b4", "finished": "#7f7f7f"}.get(s, "")
        self.lbl_state.setStyleSheet(f"color:{colour}" if colour else "")
        if s == "testing":
            self.progress.setValue(0)

    @Slot(int, int, str)
    def _on_progress(self, done: int, total: int, label: str) -> None:
        self.progress.setMaximum(max(1, total))
        self.progress.setValue(done)
        self.lbl_progress.setText(f"testing: {label}" if label else "")

    @Slot(float, int)
    def _on_tick(self, next_fire: float, rounds: int) -> None:
        self.lbl_rounds.setText(str(rounds))
        if next_fire is None or next_fire < 0:
            self.lbl_next.setText("—" if self.ctrl.state != "testing" else "running")
        else:
            remaining = next_fire - time.time()
            when = datetime.datetime.fromtimestamp(next_fire).strftime("%H:%M:%S")
            self.lbl_next.setText(f"{fmt_duration(max(0.0, remaining))}  ({when})")

    @staticmethod
    def _fmt(v: float, nd: int = 1) -> str:
        return "—" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"

    @Slot(object)
    def _on_result(self, r: TestResult) -> None:
        self.plot_panel.add_result(r)
        t = self.tbl_results
        t.insertRow(0)
        vals = [r.ts_utc, r.ts_local, r.server_name or r.server_id, r.backend, r.server_id, "yes" if r.ok else "NO",
                self._fmt(r.download_mbps), self._fmt(r.upload_mbps), self._fmt(r.latency_ms, 2), self._fmt(r.jitter_ms, 2),
                self._fmt(r.packet_loss_pct), self._fmt(r.dl_loaded_latency_ms), r.error or r.result_url]
        for c, v in enumerate(vals):
            it = QtWidgets.QTableWidgetItem(str(v))
            if not r.ok:
                it.setForeground(QtGui.QColor("#d62728"))
            elif c == 2:
                it.setForeground(QtGui.QColor(self.plot_panel.ep_color.get(r.endpoint_key, "#000000")))
            t.setItem(0, c, it)
        while t.rowCount() > MAX_TABLE_ROWS:
            t.removeRow(t.rowCount() - 1)
        if t.rowCount() < 50:
            t.resizeColumnsToContents()

    @Slot(object)
    def _on_round(self, rs: RoundSummary) -> None:
        self.plot_panel.add_round(rs)
        self.lbl_last.setText(f"{self._fmt(rs.get('download_mbps'))} / {self._fmt(rs.get('upload_mbps'))} Mbit/s / "
                              f"{self._fmt(rs.get('latency_ms'))} ms")
        t = self.tbl_rounds
        t.insertRow(0)
        vals = [str(rs.seq), rs.ts_utc, rs.ts_local, f"{rs.n_ok}/{rs.n_planned}",
                self._fmt(rs.get("download_mbps")), self._fmt(rs.get("download_mbps", "std")),
                self._fmt(rs.get("upload_mbps")), self._fmt(rs.get("upload_mbps", "std")),
                self._fmt(rs.get("latency_ms"), 2), self._fmt(rs.get("jitter_ms"), 2),
                self._fmt(rs.get("packet_loss_pct")), f"{rs.round_duration_s:.0f}"]
        for c, v in enumerate(vals):
            t.setItem(0, c, QtWidgets.QTableWidgetItem(v))
        while t.rowCount() > MAX_TABLE_ROWS:
            t.removeRow(t.rowCount() - 1)
        if t.rowCount() < 50:
            t.resizeColumnsToContents()
        self.lbl_progress.setText("")

    @Slot(str)
    def _on_finished(self, status: str) -> None:
        self.act_start.setEnabled(True)
        self.act_stop.setEnabled(False)
        self.lbl_next.setText("—")
        self.statusBar().showMessage(f"Campaign {status}", 10000)

    # ---------------------------------------------------------------- close
    # %%%% Close handling
    def closeEvent(self, ev: QtGui.QCloseEvent) -> None:
        if self.ctrl.running:
            ans = QtWidgets.QMessageBox.question(
                self, APP_NAME, "A campaign is running. Stop it and exit?\n(Data already collected stays in the database; "
                "final exports are written on stop.)",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
            if ans != QtWidgets.QMessageBox.Yes:
                ev.ignore()
                return
            self.ctrl.stop()
            # let the worker abort and the final export run (bounded wait)
            deadline = time.time() + 8.0
            while self.ctrl.state != "finished" and time.time() < deadline:
                self.app.processEvents(QtCore.QEventLoop.AllEvents, 100)
                time.sleep(0.05)
        self._save_settings()
        if self._list_worker is not None and self._list_worker.isRunning():
            self._list_worker.wait(2000)
        self.ctrl.shutdown()
        super().closeEvent(ev)


# ===========================================================================
# %% HEADLESS MODE
# ===========================================================================
def run_headless(cfg: CampaignConfig) -> int:
    """Run a campaign with no GUI (QCoreApplication event loop). Returns exit code."""
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication(sys.argv)
    os.makedirs(cfg.output_dir, exist_ok=True)
    setup_logging(cfg.output_dir)
    ctrl = CampaignController()          # logger (console + file) already echoes every message
    rc = {"code": 0}

    def _done(status: str) -> None:
        rc["code"] = 0 if status in ("finished", "stopped") else 1
        QtCore.QTimer.singleShot(200, app.quit)

    ctrl.sig_finished.connect(_done)

    def _tick(next_fire: float, rounds: int) -> None:
        if next_fire and next_fire > 0 and ctrl.state == "waiting":
            rem = next_fire - time.time()
            if int(rem) % 60 == 0 and rem > 1:       # one line a minute keeps logs readable
                print(f"           next round in {fmt_duration(rem)}", flush=True)

    ctrl.sig_tick.connect(_tick)

    def _sigint(*_a) -> None:
        print("\nSIGINT — stopping gracefully (final export will run)…", flush=True)
        ctrl.stop()

    signal.signal(signal.SIGINT, _sigint)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _sigint)
    keepalive = QtCore.QTimer()          # lets Python service signals while Qt idles
    keepalive.timeout.connect(lambda: None)
    keepalive.start(250)
    try:
        ctrl.start(cfg)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    app.exec()
    ctrl.shutdown()
    return rc["code"]


def run_gui() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    win = MainWindow(app)
    win.show()
    # Ctrl-C in the launching console closes the window cleanly
    signal.signal(signal.SIGINT, lambda *_a: win.close())
    keepalive = QtCore.QTimer()
    keepalive.timeout.connect(lambda: None)
    keepalive.start(250)
    return app.exec()


def selftest_config(outdir: str) -> CampaignConfig:
    sim = SimulatedBackend()
    eps = sim.list_servers()[:3]
    cfg = CampaignConfig(name="selftest", output_dir=outdir, endpoints=[asdict(e) for e in eps],
                         test_timeout_s=10, pause_between_endpoints_s=0.0, export_every_n=2, export_every_unit="tests", notes="self-test")
    cfg.schedule.update({"mode": "random_per_window", "per_window": 3, "window_s": 6.0, "duration_s": 14.0,
                         "first_test_immediately": True})
    return cfg


def reexport(db_path: str, cid: Optional[int], outdir: Optional[str], time_axis: str) -> int:
    if not os.path.isfile(db_path):
        print(f"ERROR: database not found: {db_path}", file=sys.stderr)
        return 2
    db = SpeedDB(db_path)
    try:
        cid = cid or db.latest_campaign_id()
        if cid is None:
            print("ERROR: no campaigns in database", file=sys.stderr)
            return 2
        row = db.campaign(cid)
        cfg = CampaignConfig.from_dict(json.loads(row["config_json"])) if row.get("config_json") else CampaignConfig()
        cfg.output_dir = outdir or os.path.dirname(os.path.abspath(db_path))
        cfg.export_json = cfg.export_csv = cfg.export_veusz = True
        cfg.veusz_time_axis = time_axis
        for f in export_all(db, cid, cfg, "_reexport"):
            print(f"wrote {f}")
        return 0
    finally:
        db.close()


# ===========================================================================
# %% ENTRY POINT
# ===========================================================================
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=f"{APP_NAME} v{__version__}")
    ap.add_argument("--headless", action="store_true", help="run without GUI (needs --config)")
    ap.add_argument("--config", help="campaign config JSON (from GUI 'Save config' or --make-config)")
    ap.add_argument("--make-config", metavar="PATH", help="write a template config JSON and exit")
    ap.add_argument("--reexport", metavar="DB", help="re-export JSON/CSV/Veusz from an existing SQLite database")
    ap.add_argument("--campaign-id", type=int, help="campaign id for --reexport (default: latest)")
    ap.add_argument("--outdir", help="output folder for --reexport / --selftest")
    ap.add_argument("--time-axis", choices=["local", "utc"], default="local", help="Veusz x-axis for --reexport")
    ap.add_argument("--selftest", action="store_true", help="short headless campaign with the Simulated back-end")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s")

    if args.make_config:
        cfg = CampaignConfig(endpoints=[asdict(Endpoint("ookla", "auto", "Ookla nearest (auto)"))])
        cfg.save(args.make_config)
        print(f"template written: {args.make_config}")
        return 0
    if args.reexport:
        return reexport(args.reexport, args.campaign_id, args.outdir, args.time_axis)
    if args.selftest:
        outdir = args.outdir or os.path.join(DEFAULT_OUTPUT_DIR, "selftest")
        return run_headless(selftest_config(outdir))
    if args.headless:
        if not args.config:
            ap.error("--headless requires --config")
        return run_headless(CampaignConfig.load(args.config))
    if args.config:
        # GUI with a pre-loaded config
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        app.setOrganizationName(ORG_NAME)
        win = MainWindow(app)
        win.apply_config(CampaignConfig.load(args.config))
        win.show()
        return app.exec()
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
