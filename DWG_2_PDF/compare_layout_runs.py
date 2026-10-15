#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Compare two dwg2pdf output trees to verify a ``--layouts`` change.

Purpose
-------
``--layouts auto`` recovered 84 drawings that ``--layouts model`` failed on
(GBT archive, 2026-10-06).  Before ``auto`` becomes the default it has to be
shown that it does **not** regress the sheets ``model`` already handled.
That is the failure mode seen in dwg2pdf 0.5.0: ``auto`` selected a
title-block paperspace layout in preference to a populated model space, and
the output went from 94.5 KiB of drawing to 1.5 KiB of border.

A large *drop* in output size for the same drawing is the signature of that
regression, so pairs are ranked by size ratio.  Size equality is necessary
but NOT sufficient, so ``--deep`` additionally compares page count, page
geometry and per-page drawing/text content.

The filename-suffix trap  (this cost a false alarm on 2026-10-06)
-----------------------------------------------------------------
dwg2pdf names a single-layout export ``<stem>.pdf`` but a layout-selected
export ``<stem>__<layout>.pdf``.  So a ``--layouts model`` tree and a
``--layouts auto`` tree of the SAME drawings do not share filenames: every
sheet appears as "lost from baseline" plus "new in candidate", and the size
histogram piles up at ratio 0 and ratio inf.  Revision 0.0.1 did exactly
that and reported 806 phantom regressions.

0.0.2 therefore strips a trailing ``__<layout>`` from BOTH sides before
pairing, and reports which layout the candidate run actually chose.
``--no-strip-suffix`` restores the literal behaviour.

Baseline contamination
----------------------
A baseline tree that has been topped up by a later pass with a different
``--layouts`` setting is a MIXTURE.  Pass ``--baseline-manifest`` pointing at
the manifest of the run you want as the reference to restrict the comparison
to the sheets that run converted.  Without it the script still runs and warns.

Revision history
----------------
0.0.1   First internal draft.  Pairs by exact relative path, size ratios,
        CSV, optional histogram (Veusz preferred, matplotlib fallback).
0.0.2   Pair on the layout-suffix-stripped stem (0.0.1 reported every sheet
        as lost+new when the two runs used different ``--layouts`` modes).
        Report the layout chosen per sheet.  New ``--deep`` content check
        via PyMuPDF: page count, page geometry, drawing-object and text
        counts -- because equal byte size does not prove equal content.
        Deep comparison runs on a PROCESS pool (PDF parsing is CPU bound);
        the metadata scan stays on a THREAD pool (it is I/O bound).

Notes on the implementation choices
-----------------------------------
* ``stat()`` on a few thousand files is I/O bound -> threads.  PDF parsing
  is CPU bound -> processes.  GPU offload is meaningless for both; flagged
  here rather than shoehorned in.
* Memory stays bounded: one small dict per PDF, and ``--deep`` opens one
  document at a time per worker and keeps only the scalar counts.  Nothing
  accumulates per page.

Usage
-----
    python compare_layout_runs.py ^
        --baseline  C:\ATEMP\GBT_PDF ^
        --candidate C:\ATEMP\GBT_PDF_autochk ^
        --csv C:\ATEMP\layout_diff.csv --plot C:\ATEMP\layout_diff.png ^
        --deep
"""

from __future__ import annotations

# %% Module metadata
__author__ = "William W. Wallace"
__revision__ = "0.0.2"

import argparse
import csv
import os
import re
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Classification thresholds.
#
# REGRESSION_RATIO: a candidate smaller than this fraction of the baseline is
# a suspected wrong-layout pick.  0.5 is generous -- the 0.5.0 regression was
# a factor of 63 -- but the renderer is deterministic, so real differences
# are either ~0 or enormous, and nothing legitimate lands near 0.5.
#
# NOISE_RATIO: two renders of identical content still differ by a few bytes
# (layout name and producer string land in the PDF), so an exact-equality
# test would be useless.  Field data: 163 of 890 sheets differed, by at most
# 7 bytes -- worst ratio 0.9993.
# ---------------------------------------------------------------------------
REGRESSION_RATIO: float = 0.50
NOISE_RATIO: float = 0.01
TINY_BYTES: int = 4096          # below this a PDF is almost certainly a border

#: Trailing ``__<layout>`` that dwg2pdf appends when it selects a layout.
_SUFFIX = re.compile(r"__([^\\/]{1,120})\.pdf$", re.IGNORECASE)


# %% Pairing keys
def split_layout(key: str, strip: bool = True) -> Tuple[str, Optional[str]]:
    """Split ``name__layout.pdf`` into ``("name.pdf", "layout")``.

    Returns ``(key, None)`` when there is no suffix, or when *strip* is False.
    """
    if not strip:
        return key, None
    m = _SUFFIX.search(key)
    if not m:
        return key, None
    return key[:m.start()] + ".pdf", m.group(1)


# %% Scanning
def scan_tree(root: Path, workers: int = 8) -> Dict[str, int]:
    """Map every PDF under *root* to its size in bytes, keyed by relative path.

    Keys are lower-cased and forward-slashed so a Windows tree and a POSIX
    tree compare equal.  Threads, not processes: see the module docstring.
    """
    if not root.is_dir():
        raise SystemExit("not a directory: %s" % root)

    paths: List[Path] = [p for p in root.rglob("*.pdf") if p.is_file()]

    def _one(p: Path) -> Tuple[str, int]:
        return p.relative_to(root).as_posix().lower(), p.stat().st_size

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(_one, paths))


def manifest_ok_keys(manifest: Path, baseline_root: Path) -> Optional[set]:
    """Relative keys of the PDFs a manifest records as successfully converted.

    Returns ``None`` if unreadable, so the caller can warn and carry on.
    """
    try:
        rows = list(csv.DictReader(
            manifest.open(newline="", encoding="utf-8")))
    except OSError as exc:
        print("  ! cannot read manifest %s: %s" % (manifest, exc))
        return None

    keys: set = set()
    prefix = str(baseline_root).rstrip("\\/").lower().replace("\\", "/") + "/"
    for row in rows:
        if row.get("status") != "ok":
            continue
        for out in (row.get("outputs") or "").split(";"):
            out = out.strip().lower().replace("\\", "/")
            if not out:
                continue
            keys.add(out[len(prefix):] if out.startswith(prefix)
                     else Path(out).name)
    return keys or None


# %% Deep content comparison
def _page_fingerprint(path_str: str) -> Optional[dict]:
    """Summarise a PDF's content.  Module-level so a process pool can pickle it.

    Returns ``None`` when PyMuPDF is unavailable or the file will not open --
    the caller degrades to the size-only verdict rather than failing.
    """
    try:
        # Modern name first: ``import fitz`` is deprecated in PyMuPDF >= 1.24
        # and prints a warning once per worker process -- which, on a process
        # pool, is once per worker and pure log noise.
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz                               # PyMuPDF < 1.24
    except ImportError:
        return None
    try:
        with fitz.open(path_str) as doc:
            pages = doc.page_count
            boxes, draws, chars = [], 0, 0
            for page in doc:
                r = page.rect
                # Rounded: a sub-point difference is not a layout change.
                boxes.append((round(r.width), round(r.height)))
                draws += len(page.get_drawings())
                chars += len(page.get_text("text"))
            return {"pages": pages, "boxes": boxes,
                    "draws": draws, "chars": chars}
    except Exception:                                  # noqa: BLE001
        return None


def deep_compare(pairs: List[Tuple[str, str, str]],
                 workers: int) -> Dict[str, str]:
    """Fingerprint both sides of each pair and label the content difference.

    Parameters
    ----------
    pairs : list of (stem, baseline_abs_path, candidate_abs_path)
    workers : int
        Process-pool width.  PDF parsing is CPU bound.

    Returns
    -------
    dict
        ``{stem: content_verdict}``.
    """
    paths = [p for _, b, c in pairs for p in (b, c)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        prints = list(pool.map(_page_fingerprint, paths, chunksize=8))

    out: Dict[str, str] = {}
    for i, (stem, _b, _c) in enumerate(pairs):
        fb, fc = prints[2 * i], prints[2 * i + 1]
        if fb is None or fc is None:
            out[stem] = "deep-unavailable"
            continue
        if fb["pages"] != fc["pages"]:
            out[stem] = "DIFFERENT-page-count %d->%d" % (fb["pages"],
                                                         fc["pages"])
        elif fb["boxes"] != fc["boxes"]:
            out[stem] = "DIFFERENT-page-size %s->%s" % (fb["boxes"][:1],
                                                        fc["boxes"][:1])
        elif fb["draws"] != fc["draws"]:
            out[stem] = "DIFFERENT-vectors %d->%d" % (fb["draws"],
                                                      fc["draws"])
        elif fb["chars"] != fc["chars"]:
            out[stem] = "DIFFERENT-text %d->%d" % (fb["chars"], fc["chars"])
        else:
            out[stem] = "identical-content"
    return out


# %% Classification
def classify(base: Optional[int], cand: Optional[int]) -> Tuple[str, float]:
    """Label one baseline/candidate pair and return ``(verdict, ratio)``."""
    if base is None and cand is None:
        return "both-missing", float("nan")
    if base is None:
        return "new-in-candidate", float("inf")
    if cand is None:
        return "LOST-in-candidate", 0.0

    ratio = cand / base if base else float("inf")
    if cand < TINY_BYTES <= base:
        return "REGRESSION-tiny", ratio
    if ratio < REGRESSION_RATIO:
        return "REGRESSION-smaller", ratio
    if abs(ratio - 1.0) <= NOISE_RATIO:
        return "same", ratio
    return ("larger" if ratio > 1.0 else "smaller"), ratio


# %% Plotting
def write_plot(ratios: Iterable[float], out_path: Path) -> str:
    """Plot the size-ratio distribution.  Veusz preferred, matplotlib fallback.

    Infinite and zero ratios are excluded: they mean "unpaired", which is a
    pairing question, not a size question, and plotting them produces the
    misleading twin spikes that 0.0.1 generated.
    """
    data = [r for r in ratios
            if r == r and r not in (float("inf"),) and r > 0.0]
    if not data:
        return "no finite non-zero ratios to plot"

    try:
        import veusz.embed as veusz                    # type: ignore

        emb = veusz.Embedded("layout diff", hidden=True)
        graph = emb.Root.Add("page").Add("graph")
        hist = graph.Add("histo")
        emb.SetData("ratio", data)
        hist.data.val = "ratio"
        graph.x.label.val = "candidate / baseline PDF size"
        graph.y.label.val = "sheets"
        emb.Export(str(out_path))
        emb.Close()
        return "veusz"
    except Exception as exc:                           # noqa: BLE001
        veusz_why = "%s: %s" % (type(exc).__name__, exc)

    try:
        import matplotlib
        matplotlib.use("Agg")                          # headless
        import matplotlib.pyplot as plt

        lo, hi = min(data), max(data)
        fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
        # Narrow range -> a 60-bin histogram over [0,1] hides everything, so
        # the range is set from the data with a small margin.
        span = max(hi - lo, 1e-6)
        ax.hist(data, bins=60, range=(lo - 0.05 * span, hi + 0.05 * span))
        if lo < REGRESSION_RATIO < hi:
            ax.axvline(REGRESSION_RATIO, linestyle="--",
                       label="regression threshold (%.2f)" % REGRESSION_RATIO)
        ax.axvline(1.0, linestyle=":", label="unchanged")
        ax.set_xlabel("candidate / baseline PDF size")
        ax.set_ylabel("sheets")
        ax.set_title("--layouts auto vs --layouts model, output size ratio")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_path)
        plt.close(fig)
        return "matplotlib (veusz unavailable: %s)" % veusz_why
    except Exception as exc:                           # noqa: BLE001
        return "no plot (veusz: %s; matplotlib: %s)" % (veusz_why, exc)


# %% Entry point
def main(argv: Optional[List[str]] = None) -> int:
    """Parse arguments, compare the trees, print and write the report."""
    ap = argparse.ArgumentParser(
        description="Compare two dwg2pdf output trees to verify a "
                    "--layouts change (revision %s)." % __revision__)
    ap.add_argument("--baseline", required=True, type=Path,
                    help="output root of the reference run (--layouts model)")
    ap.add_argument("--candidate", required=True, type=Path,
                    help="output root of the run under test (--layouts auto)")
    ap.add_argument("--baseline-manifest", type=Path, default=None,
                    help="manifest.csv of the reference run, to exclude files "
                         "a later pass added to the same tree")
    ap.add_argument("--no-strip-suffix", action="store_true",
                    help="pair on literal filenames; do NOT strip a trailing "
                         "__<layout>. Only useful when both runs used the "
                         "same --layouts mode.")
    ap.add_argument("--deep", action="store_true",
                    help="also compare page count, page geometry, vector and "
                         "text counts with PyMuPDF. Equal size is not equal "
                         "content.")
    ap.add_argument("--csv", type=Path, default=None,
                    help="write the per-sheet table here")
    ap.add_argument("--plot", type=Path, default=None,
                    help="write a size-ratio histogram here (.pdf or .png)")
    ap.add_argument("--workers", type=int,
                    default=min(8, (os.cpu_count() or 2)),
                    help="pool width for the scan and the deep compare")
    ap.add_argument("--top", type=int, default=25,
                    help="how many worst offenders to print")
    args = ap.parse_args(argv)
    strip = not args.no_strip_suffix

    print("compare_layout_runs.py %s" % __revision__)
    print("  baseline : %s" % args.baseline)
    print("  candidate: %s" % args.candidate)

    base_raw = scan_tree(args.baseline, args.workers)
    cand_raw = scan_tree(args.candidate, args.workers)
    print("  baseline PDFs : %d" % len(base_raw))
    print("  candidate PDFs: %d" % len(cand_raw))

    if args.baseline_manifest:
        keys = manifest_ok_keys(args.baseline_manifest, args.baseline)
        if keys:
            before = len(base_raw)
            base_raw = {k: v for k, v in base_raw.items()
                        if k in keys or Path(k).name in keys}
            print("  baseline restricted by manifest: %d -> %d"
                  % (before, len(base_raw)))
        else:
            print("  ! manifest gave no usable 'ok' rows; comparing everything")

    # ---- fold the __<layout> suffix into the key ---------------------------
    base: Dict[str, int] = {}
    cand: Dict[str, int] = {}
    chosen: Dict[str, str] = {}          # stem -> layout the candidate picked
    for k, v in base_raw.items():
        stem, _ = split_layout(k, strip)
        base[stem] = max(base.get(stem, 0), v)
    for k, v in cand_raw.items():
        stem, layout = split_layout(k, strip)
        cand[stem] = max(cand.get(stem, 0), v)
        if layout:
            chosen[stem] = layout
    if strip:
        print("  paired on layout-stripped stems: %d baseline, %d candidate"
              % (len(base), len(cand)))

    # ---- pair up -----------------------------------------------------------
    rows: List[dict] = []
    for stem in sorted(set(base) | set(cand)):
        b, c = base.get(stem), cand.get(stem)
        verdict, ratio = classify(b, c)
        rows.append({
            "sheet": stem,
            "candidate_layout": chosen.get(stem, ""),
            "baseline_bytes": b if b is not None else "",
            "candidate_bytes": c if c is not None else "",
            "ratio": "" if ratio != ratio else "%.4f" % ratio,
            "verdict": verdict,
            "content": "",
        })

    # ---- optional content comparison ---------------------------------------
    if args.deep:
        inv_b = {}
        inv_c = {}
        for k in base_raw:
            inv_b.setdefault(split_layout(k, strip)[0], k)
        for k in cand_raw:
            inv_c.setdefault(split_layout(k, strip)[0], k)
        pairs = [(r["sheet"],
                  str(args.baseline / inv_b[r["sheet"]]),
                  str(args.candidate / inv_c[r["sheet"]]))
                 for r in rows
                 if r["sheet"] in inv_b and r["sheet"] in inv_c]
        print("  deep-comparing %d pairs on %d processes..."
              % (len(pairs), args.workers))
        verdicts = deep_compare(pairs, args.workers)
        for r in rows:
            r["content"] = verdicts.get(r["sheet"], "")

    # ---- summary -----------------------------------------------------------
    tally: Dict[str, int] = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print("\n  %-22s %7s" % ("verdict", "sheets"))
    print("  %-22s %7s" % ("-" * 22, "-" * 7))
    for v, n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print("  %-22s %7d" % (v, n))

    if chosen:
        lay: Dict[str, int] = {}
        for v in chosen.values():
            lay[v] = lay.get(v, 0) + 1
        print("\n  layout chosen by the candidate run:")
        for v, n in sorted(lay.items(), key=lambda kv: -kv[1])[:10]:
            print("    %-28s %d" % (v, n))

    if args.deep:
        cont: Dict[str, int] = {}
        for r in rows:
            if r["content"]:
                head = r["content"].split(" ")[0]
                cont[head] = cont.get(head, 0) + 1
        print("\n  content comparison:")
        for v, n in sorted(cont.items(), key=lambda kv: -kv[1]):
            print("    %-28s %d" % (v, n))

    finite = [float(r["ratio"]) for r in rows
              if r["ratio"] and 0.0 < float(r["ratio"]) < float("inf")]
    if finite:
        print("\n  size ratio: n=%d  mean=%.4f  median=%.4f  min=%.4f  "
              "max=%.4f" % (len(finite), statistics.mean(finite),
                            statistics.median(finite), min(finite),
                            max(finite)))

    bad = [r for r in rows
           if r["verdict"].startswith(("REGRESSION", "LOST"))
           or r["content"].startswith("DIFFERENT")]
    print("\n  SUSPECTED REGRESSIONS: %d" % len(bad))
    if bad:
        bad.sort(key=lambda r: float(r["ratio"] or 0.0))
        print("  %-10s %-10s %-8s %-14s %s"
              % ("baseline", "candidate", "ratio", "layout", "sheet"))
        for r in bad[:args.top]:
            print("  %-10s %-10s %-8s %-14s %s"
                  % (r["baseline_bytes"], r["candidate_bytes"],
                     r["ratio"] or "-", r["candidate_layout"][:14],
                     r["sheet"][:80]))

    # ---- outputs -----------------------------------------------------------
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print("\n  wrote %s" % args.csv)

    if args.plot:
        args.plot.parent.mkdir(parents=True, exist_ok=True)
        print("  plot backend: %s"
              % write_plot((float(r["ratio"]) for r in rows if r["ratio"]),
                           args.plot))

    # Non-zero exit on anything suspicious, so this can gate a default change.
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
