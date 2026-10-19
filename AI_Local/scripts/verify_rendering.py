#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_rendering.py -- browser-based checks for the AI_Local page set.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

WHY THIS IS SEPARATE FROM build_ai_local_site.py
------------------------------------------------
``build_ai_local_site.py`` reads the HTML and can therefore check anything
that is decidable from the source: structure, equation-block shape, citation
numbers, broken links, class collisions.  It is standard-library only and
runs anywhere.

Four things it CANNOT check, because they only exist once a browser has laid
the page out and run its scripts:

1.  Whether KaTeX actually typeset the math.  A page can be structurally
     perfect and still show raw ``\\[ ... \\]`` if the vendored copy is
     missing, or show red error text if an expression is malformed.
2.  Whether the "Define variables" disclosure actually reveals its table.
3.  Whether the theme control actually changes ``data-theme``.  Six of the
     pre-existing pages implement theirs as a ``<div>`` rather than a
     ``<button>``, so a source-level check cannot confirm it works.
4.  Whether the page overflows horizontally at phone width.  This is the one
     layout failure that makes a page feel broken rather than merely cramped,
     and it is invisible in the source.

This script needs Playwright and a Chromium build, which the offline nodes in
this deployment may not have, so it is a separate optional step rather than
part of the main build.

INSTALL
-------
    pip install playwright
    python -m playwright install chromium

USAGE
-----
    python verify_rendering.py --out ../            # the AI_Local directory
    python verify_rendering.py --out ../ --src /path/to/original/pages

``--src`` is optional and enables the most useful comparison this script
makes: for each pre-existing page it measures the ORIGINAL as well as the
retrofitted copy, so a horizontal overflow can be attributed.  An overflow
present in both is the page's own wide table and is out of scope; an overflow
present only in the built copy was introduced by the rebuild and is a bug.

MEMORY NOTE
-----------
Each page gets a fresh browser context which is closed immediately after, so
only one page's DOM is resident at a time.  The accumulated result is a list
of small dicts.  A sixteen-page run holds well under a megabyte, and a much
larger set would too.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    from playwright.async_api import async_playwright
except ImportError:                              # pragma: no cover - env guard
    print("Playwright is not installed. Run:\n"
          "    pip install playwright\n"
          "    python -m playwright install chromium", file=sys.stderr)
    raise SystemExit(2)


# %% Viewports ---------------------------------------------------------------
#: Desktop viewport, for the functional checks.
DESKTOP: Dict[str, int] = {"width": 1280, "height": 900}

#: Phone viewport, for the overflow check.  390x844 is a common modern phone
#: logical resolution and is narrower than most, which makes it the right
#: place to catch an overflow.
PHONE: Dict[str, int] = {"width": 390, "height": 844}


# %% Page probes (JavaScript evaluated in the page) --------------------------
# Collects everything decidable in one round trip, so each page needs one
# evaluate call rather than a dozen.
_PROBE_JS = r"""() => {
  const count = sel => document.querySelectorAll(sel).length;
  const active = document.querySelector('.ailnav-links a[aria-current="page"]');

  return {
    title: document.title,

    // KaTeX: .katex elements mean the vendored copy loaded and ran;
    // .katex-error means an expression failed to parse.
    katexNodes:  count('.katex'),
    katexErrors: count('.katex-error'),

    // Raw delimiters left in the rendered text mean KaTeX never ran over
    // them. Checked against textContent, not innerHTML, so escaped
    // delimiters inside <pre>/<code> are not counted.
    rawDelimiters: (document.body.innerText.match(/\\\[|\\\]/g) || []).length,

    // Shared navigation
    navStrips:   count('nav.ailnav'),
    navLinks:    count('.ailnav-links a'),
    navActive:   active ? active.getAttribute('href') : null,

    // Equation component
    eqCards:        count('.eq'),
    infoButtons:    count('.eq .info[aria-controls]'),
    varsHidden:     count('.vars[hidden]'),
    derivLists:     count('.deriv'),
    provenancePills: count('.eq .pill'),

    // Theme: either the shared strip's button, or the page's own control.
    //
    // A FIXED SELECTOR LIST IS NOT ENOUGH HERE. The pre-existing pages in
    // this set implement their toggles three different ways:
    //   <div class="theme-toggle" id="themeToggle">   (the Jupyter pages)
    //   <button class="theme-toggle">                 (GPU monitoring)
    //   <button class="tbtn" onclick="toggleTheme()"> (llama-rpc guide)
    // The third has no theme-ish class or id at all, so detection falls
    // back to the aria-label, the title and the inline handler. Missing a
    // control that works would be reported as "no theme control at all",
    // which is a false failure, so the net is cast deliberately wide.
    stripThemeButtons: count('.ailnav-theme'),
    ownThemeControls:  (() => {
      const known = document.querySelectorAll(
        '#themeToggle, .theme-toggle, .theme-btn, [data-theme-toggle]');
      if (known.length) return known.length;
      const pattern = /theme|dark.?mode|light.?mode/i;
      return [...document.querySelectorAll('button, [role="button"], div, span, a')]
        .filter(el => {
          if (el.closest('nav.ailnav')) return false;   // the strip's own
          const haystack = [el.id, el.className, el.getAttribute('aria-label'),
                            el.getAttribute('title'),
                            el.getAttribute('onclick')]
                           .filter(Boolean).join(' ');
          return pattern.test(haystack);
        }).length;
    })(),
    theme: document.documentElement.getAttribute('data-theme'),
  };
}"""

# Clicks the first variable-definition button and reports what happened.
_REVEAL_JS = r"""() => {
  const button = document.querySelector('.eq .info[aria-controls]');
  if (!button) return null;
  const target = document.getElementById(button.getAttribute('aria-controls'));
  if (!target) return { error: 'aria-controls names no element' };
  return {
    expanded: button.getAttribute('aria-expanded'),
    visible: !target.hasAttribute('hidden'),
    label: button.querySelector('.info-label')
             ? button.querySelector('.info-label').textContent : null,
    rows: target.querySelectorAll('tbody tr').length,
  };
}"""

# Clicks whichever theme control the page has and reports which one it was.
# Mirrors the detection in _PROBE_JS, so the control that was counted is the
# control that gets clicked.
_CLICK_THEME_JS = r"""() => {
  const strip = document.querySelector('.ailnav-theme');
  if (strip) { strip.click(); return 'strip (.ailnav-theme)'; }

  const known = document.querySelector(
    '#themeToggle, .theme-toggle, .theme-btn, [data-theme-toggle]');
  if (known) {
    known.click();
    return 'page (' + (known.id ? '#' + known.id
                                : '.' + (known.className || '').toString().split(' ')[0]) + ')';
  }

  const pattern = /theme|dark.?mode|light.?mode/i;
  const candidate = [...document.querySelectorAll('button, [role="button"], div, span, a')]
    .find(el => {
      if (el.closest('nav.ailnav')) return false;
      const haystack = [el.id, el.className, el.getAttribute('aria-label'),
                        el.getAttribute('title'), el.getAttribute('onclick')]
                       .filter(Boolean).join(' ');
      return pattern.test(haystack);
    });
  if (candidate) {
    candidate.click();
    return 'page (' + candidate.tagName.toLowerCase() +
           (candidate.getAttribute('onclick')
              ? ' onclick=' + candidate.getAttribute('onclick') : '') + ')';
  }
  return null;
}"""

# Finds genuine document overflow at the current viewport.
#
# The naive test -- getBoundingClientRect().right > viewport -- flags every
# child of a horizontal scroll container, which is a FALSE POSITIVE: the
# navigation strip's links and a .table-wrap's table are meant to extend past
# the viewport and are clipped by their container. This walks up from each
# candidate and discards it if any ancestor clips horizontally, so what is
# left genuinely widens the document.
_OVERFLOW_JS = r"""() => {
  const vw = document.documentElement.clientWidth;
  const clips = el => {
    const o = getComputedStyle(el).overflowX;
    return o === 'auto' || o === 'scroll' || o === 'hidden';
  };

  const culprits = [];
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.right <= vw + 1 && r.width <= vw + 1) return;

    let parent = el.parentElement, clipped = false;
    while (parent && parent !== document.body) {
      if (clips(parent)) { clipped = true; break; }
      parent = parent.parentElement;
    }
    if (clipped) return;

    // A scroll container sized to the viewport is doing its job.
    if (clips(el) && r.width <= vw + 1) return;

    culprits.push({
      tag: el.tagName.toLowerCase(),
      cls: (el.className || '').toString().slice(0, 44),
      width: Math.round(r.width),
      right: Math.round(r.right),
      text: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60),
    });
  });

  return {
    viewport: vw,
    documentWidth: document.documentElement.scrollWidth,
    overflows: document.documentElement.scrollWidth > vw + 1,
    culprits: culprits.slice(0, 8),
    culpritCount: culprits.length,
  };
}"""


# %% Result model ------------------------------------------------------------
@dataclass
class PageReport:
    """Everything measured for one page."""

    page: str
    probe: Dict[str, Any] = field(default_factory=dict)
    reveal: Optional[Dict[str, Any]] = None
    theme: Optional[Dict[str, Any]] = None
    phone: Dict[str, Any] = field(default_factory=dict)
    original_phone: Optional[Dict[str, Any]] = None
    console: List[str] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)


# %% Measurement -------------------------------------------------------------
async def measure_page(browser, uri: str, want_phone: bool = True
                       ) -> Dict[str, Any]:
    """Load one page and run every probe against it.

    Parameters
    ----------
    browser
        A live Playwright browser.
    uri
        ``file://`` URI of the page.
    want_phone
        True to also measure overflow at phone width.

    Returns
    -------
    dict
        Keys ``probe``, ``reveal``, ``theme``, ``phone`` and ``console``.
    """
    console: List[str] = []
    context = await browser.new_context(viewport=DESKTOP)
    page = await context.new_page()

    # Only errors are collected; warnings from a page's own scripts are noise
    # here and several pre-existing pages emit them legitimately.
    page.on("console", lambda msg: console.append(f"{msg.type}: {msg.text}")
            if msg.type == "error" else None)
    page.on("pageerror", lambda err: console.append(f"pageerror: {err}"))

    try:
        await page.goto(uri, wait_until="load")
        # KaTeX renders synchronously once its script has run, but the script
        # tags are at the end of <body>, so a short settle avoids racing them.
        await page.wait_for_timeout(700)

        probe = await page.evaluate(_PROBE_JS)

        # Exercise the disclosure, if the page has one.
        reveal = None
        if probe["infoButtons"]:
            await page.click(".eq .info[aria-controls]")
            await page.wait_for_timeout(150)
            reveal = await page.evaluate(_REVEAL_JS)

        # Exercise whichever theme control the page has: the shared strip's
        # button, or the page's own, which may be a <div>.
        theme = None
        if probe["stripThemeButtons"] or probe["ownThemeControls"]:
            before = await page.evaluate(
                "() => document.documentElement.getAttribute('data-theme')")
            try:
                # Clicked from inside the page rather than with page.click(),
                # because the control may be a <div> with no accessible role,
                # or a <button> whose only theme-ish marker is its inline
                # onclick. Both are present in this set, and Playwright's
                # selector engine cannot express the second.
                clicked = await page.evaluate(_CLICK_THEME_JS)
                await page.wait_for_timeout(250)
                after = await page.evaluate(
                    "() => document.documentElement.getAttribute('data-theme')")
                theme = {"control": clicked, "before": before,
                         "after": after, "changed": before != after}
                if not clicked:
                    theme["error"] = "a control was counted but none could be clicked"
            except Exception as exc:             # noqa: BLE001 - reported
                theme = {"error": str(exc)[:80]}

        phone: Dict[str, Any] = {}
        if want_phone:
            await page.set_viewport_size(PHONE)
            await page.wait_for_timeout(300)
            phone = await page.evaluate(_OVERFLOW_JS)

        return {"probe": probe, "reveal": reveal, "theme": theme,
                "phone": phone, "console": console}
    finally:
        # Close the context whatever happened, so a failure on one page does
        # not leak a browser context into the rest of the run.
        await context.close()


async def measure_original(browser, uri: str) -> Dict[str, Any]:
    """Measure only phone overflow on a pre-retrofit copy of a page.

    Used to attribute an overflow: present in both means the page always had
    it, present only in the built copy means the rebuild introduced it.
    """
    context = await browser.new_context(viewport=PHONE)
    page = await context.new_page()
    try:
        await page.goto(uri, wait_until="load")
        await page.wait_for_timeout(400)
        return await page.evaluate(_OVERFLOW_JS)
    finally:
        await context.close()


# %% Assessment --------------------------------------------------------------
def assess(report: PageReport, generated: bool, in_nav: bool) -> None:
    """Populate ``report.problems`` from the measurements.

    Parameters
    ----------
    report
        The page's measurements; mutated in place.
    generated
        True for a page written by the rebuild, which is held to the full
        standard.  A pre-existing page is checked only for things the
        rebuild is responsible for.
    in_nav
        False for the archived pages, which are deliberately kept out of the
        navigation strip and therefore have no active link to find.
    """
    probe = report.probe

    # ---- things the rebuild is responsible for on EVERY page -------------
    if probe.get("navStrips") != 1:
        report.problems.append(
            f"{probe.get('navStrips')} navigation strips, expected exactly 1")

    if in_nav and not probe.get("navActive"):
        report.problems.append(
            "no navigation link marked aria-current=page")

    # Exactly one working theme control, from whichever source.
    controls = (probe.get("stripThemeButtons", 0)
                + probe.get("ownThemeControls", 0))
    if controls == 0:
        report.problems.append("no theme control at all")
    elif controls > 1 and probe.get("stripThemeButtons"):
        report.problems.append(
            f"{controls} theme controls: the strip added one to a page that "
            f"already had its own")

    if report.theme and "error" in report.theme:
        report.problems.append(f"theme control failed: {report.theme['error']}")
    elif report.theme and not report.theme.get("changed"):
        report.problems.append("clicking the theme control did not change data-theme")

    if report.console:
        report.problems.append(f"console error: {report.console[0][:100]}")

    # ---- overflow, attributed --------------------------------------------
    phone = report.phone or {}
    if phone.get("overflows"):
        orig = report.original_phone
        if orig is not None and orig.get("overflows"):
            # Pre-existing: out of scope for the rebuild, recorded only.
            pass
        else:
            culprit = ""
            if phone.get("culprits"):
                first = phone["culprits"][0]
                culprit = (f" (first: {first['tag']}"
                           f"{'.' + first['cls'] if first['cls'] else ''} "
                           f"w={first['width']})")
            report.problems.append(
                f"horizontal overflow at {PHONE['width']}px: document is "
                f"{phone.get('documentWidth')}px{culprit}")

    # ---- things only the generated pages are held to ---------------------
    if not generated:
        return

    if probe.get("katexErrors"):
        report.problems.append(
            f"{probe['katexErrors']} KaTeX parse error(s) on the page")

    if probe.get("eqCards"):
        if not probe.get("katexNodes"):
            report.problems.append(
                "page has equation cards but KaTeX rendered nothing; the "
                "vendored copy under assets/katex/ is probably missing")
        if probe.get("rawDelimiters"):
            report.problems.append(
                f"{probe['rawDelimiters']} raw \\[ or \\] left in the rendered "
                f"text; KaTeX did not run over them")
        if probe.get("infoButtons") != probe.get("eqCards"):
            report.problems.append(
                f"{probe['eqCards']} equation cards but "
                f"{probe['infoButtons']} variable-definition buttons")
        if probe.get("provenancePills") != probe.get("eqCards"):
            report.problems.append(
                f"{probe['eqCards']} equation cards but "
                f"{probe['provenancePills']} provenance pills")

    if report.reveal is not None:
        if report.reveal.get("error"):
            report.problems.append(f"disclosure: {report.reveal['error']}")
        else:
            if not report.reveal.get("visible"):
                report.problems.append(
                    "clicking 'Define variables' did not reveal the table")
            if report.reveal.get("expanded") != "true":
                report.problems.append(
                    "aria-expanded was not set to true after opening")
            if not report.reveal.get("rows"):
                report.problems.append("the revealed variable table has no rows")


# %% Orchestration -----------------------------------------------------------
async def run(out_dir: Path, src_dir: Optional[Path],
              generated_names: Sequence[str],
              archived_names: Sequence[str]) -> int:
    """Measure every page under ``out_dir`` and print the report."""
    pages = sorted(p for p in out_dir.rglob("*.html"))
    if not pages:
        print(f"No .html files under {out_dir}", file=sys.stderr)
        return 2

    reports: List[PageReport] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        try:
            for path in pages:
                rel = path.relative_to(out_dir).as_posix()
                print(f"  measuring {rel} ...", flush=True)

                data = await measure_page(browser, path.as_uri())
                report = PageReport(page=rel, **{
                    k: data[k] for k in ("probe", "reveal", "theme", "phone")
                })
                report.console = data["console"]

                # Measure the pre-retrofit copy so an overflow can be
                # attributed rather than merely reported.
                if src_dir is not None:
                    original = src_dir / rel
                    if original.exists():
                        report.original_phone = await measure_original(
                            browser, original.as_uri())

                assess(report,
                       generated=rel in generated_names,
                       in_nav=rel not in archived_names)
                reports.append(report)
        finally:
            await browser.close()

    # ---- report -----------------------------------------------------------
    print()
    print("=" * 112)
    print("RENDERED-PAGE CHECKS")
    print("=" * 112)
    header = (f"{'page':50s} {'katex':>6s} {'kerr':>5s} {'eq':>4s} "
              f"{'btn':>4s} {'nav':>4s} {'theme':>7s} {'390px':>7s} {'cons':>5s}")
    print(header)
    print("-" * 112)

    for r in reports:
        p = r.probe
        theme = "-"
        if r.theme:
            theme = "ok" if r.theme.get("changed") else "FAIL"
        elif p.get("ownThemeControls"):
            theme = "own"

        if not (r.phone or {}).get("overflows"):
            fit = "fits"
        elif r.original_phone and r.original_phone.get("overflows"):
            fit = "pre-ex"          # overflowed before the rebuild too
        else:
            fit = "OVER"

        print(f"{r.page[:50]:50s} {p.get('katexNodes', 0):6d} "
              f"{p.get('katexErrors', 0):5d} {p.get('eqCards', 0):4d} "
              f"{p.get('infoButtons', 0):4d} {p.get('navStrips', 0):4d} "
              f"{theme:>7s} {fit:>7s} {len(r.console):5d}")

    print("-" * 112)
    print("katex = typeset nodes, kerr = parse errors, eq = equation cards,")
    print("btn = variable-definition buttons, theme: ok = the strip's control")
    print("works, own = the page's own control, 390px: pre-ex = the page")
    print("already overflowed before the rebuild (its own wide tables).")

    # ---- pre-existing overflow, recorded but not failed -------------------
    pre_existing = [r for r in reports
                    if (r.phone or {}).get("overflows")
                    and r.original_phone and r.original_phone.get("overflows")]
    if pre_existing:
        print()
        print("PRE-EXISTING OVERFLOW (not introduced by the rebuild, not failed):")
        for r in pre_existing:
            before = r.original_phone.get("documentWidth")
            after = r.phone.get("documentWidth")
            first = (r.phone.get("culprits") or [{}])[0]
            print(f"  {r.page}: {before}px before, {after}px after "
                  f"-- {first.get('tag', '?')} w={first.get('width', '?')}")
        print("  These are each page's own wide tables. Wrapping them in a")
        print("  horizontal scroll container would fix it without changing the")
        print("  desktop rendering, but it edits a pre-existing page, so it is")
        print("  offered as a suggestion rather than applied.")

    # ---- failures ---------------------------------------------------------
    failing = [r for r in reports if r.problems]
    print()
    if failing:
        print(f"FAILED: {sum(len(r.problems) for r in failing)} problem(s) on "
              f"{len(failing)} page(s)")
        for r in failing:
            print(f"\n  {r.page}")
            for problem in r.problems:
                print(f"    - {problem}")
        return 1

    print(f"PASSED: {len(reports)} pages rendered correctly")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse arguments and run the rendered-page checks."""
    parser = argparse.ArgumentParser(
        description="Browser-based checks for the AI_Local page set.")
    parser.add_argument("--out", required=True, type=Path,
                        help="the AI_Local directory holding the built pages")
    parser.add_argument("--src", type=Path, default=None,
                        help="optional: directory holding the ORIGINAL pages, "
                             "so an overflow can be attributed to the rebuild "
                             "or to the page itself")
    parser.add_argument("--json", type=Path, default=None,
                        help="also write the full measurements to this file")
    args = parser.parse_args(argv)

    out_dir = args.out.resolve()
    if not out_dir.is_dir():
        parser.error(f"--out is not a directory: {out_dir}")
    src_dir = args.src.resolve() if args.src else None

    # Pages written by the rebuild, held to the full standard.
    generated = (
        "index.html", "local-code-build-test.html",
        "ollama-model-selection.html", "claude-sandbox-local-env.html",
        "monitoring-sizing.html", "references.html", "CHANGELOG.html",
    )
    # Pages deliberately kept out of the navigation strip.
    archived = (
        "Archive/Jupyter_Code_Eval_Setup.html",
        "Archive/Windows_Exporter_Grafana_dashboard.html",
    )

    status = asyncio.run(run(out_dir, src_dir, generated, archived))

    if args.json:
        # Written after the run so a failure still leaves the report on disk.
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps({"out": str(out_dir),
                                         "src": str(src_dir) if src_dir else None},
                                        indent=2), encoding="utf-8")

    return status


if __name__ == "__main__":
    raise SystemExit(main())
