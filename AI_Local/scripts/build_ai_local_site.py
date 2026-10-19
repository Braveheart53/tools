#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_ai_local_site.py -- generator and verifier for the AI_Local page set.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

WHAT THIS DOES
--------------
Two jobs, in one pass:

1. **Generates** the six new pages (index, the three technical pages,
   references and the change log) by wrapping a body fragment from a page
   module in the shared page shell.

2. **Retrofits** the seven pre-existing guides, plus the two archived pages,
   by injecting the shared navigation strip and the shared stylesheets into
   each one *without altering its own stylesheet, layout, content or theme
   control*.  Four of those pages also carry a duplicated artifact iframe
   wrapper, which is unwrapped so each becomes one valid document.

Then it verifies the result and refuses to declare success if any check fails.

WHY A GENERATOR AND NOT HAND-EDITED HTML
----------------------------------------
Nine pages sharing one navigation strip, one version stamp and one reference
numbering is exactly the situation where hand editing drifts.  A generator
makes the navigation a projection of a single manifest, the version stamp a
projection of a single changelog, and every citation checkable against a
single reference list.  Adding a page later is one manifest entry.

USAGE
-----
    python build_ai_local_site.py --src <dir of original pages> \
                                  --out <output AI_Local dir>

Both directories are required so the script never writes next to its inputs.
With ``--verify-only`` it checks an already-built tree and generates nothing.

PYTHON CONVENTIONS
------------------
PEP 8, type hints throughout, dataclass for the manifest entries, Spyder cell
separators (``# %%``) dividing the phases.  Standard library only: this has to
run inside a minimal environment.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# The page-content modules live beside this script's source tree rather than in
# the published output, so the import path is extended by the caller via
# --modules.  Resolved in main() before the page modules are imported.


# %% Manifest ----------------------------------------------------------------
@dataclass
class PageSpec:
    """One page in the set.

    Attributes
    ----------
    filename
        Output file name, relative to the AI_Local directory.  A page under
        ``Archive/`` carries the prefix here.
    nav_label
        Short label shown in the shared navigation strip.  Kept under about
        18 characters so the strip does not need to scroll on a laptop.

        PLAIN TEXT, not HTML.  Every field in this dataclass is escaped with
        html.escape() at the point of use, so writing "&amp;" here produces a
        literal "&amp;" on the page.  Write "&".
    title
        Full title, used on the landing page card and as the ``<title>`` of a
        generated page.  For a retrofitted page the existing ``<title>`` is
        left untouched and this is used only on the landing-page card.
    blurb
        One or two sentences for the landing-page card.
    group
        Display group on the landing page: ``build``, ``inference``,
        ``monitoring`` or ``meta``.
    generated
        True for a page this script writes from a body fragment; False for a
        pre-existing page that is only retrofitted.
    builder
        Callable returning the body fragment.  Required when ``generated``.
    is_new
        True to mark the page with a "new" badge on the landing page.
    in_nav
        False to keep the page out of the navigation strip while still
        retrofitting it.  Used for the archived pages, which would otherwise
        make the strip too long.
    description
        ``<meta name="description">`` content for a generated page.
    icon
        Short generic word used to pick the inline favicon glyph.
    """

    filename: str
    nav_label: str
    title: str
    blurb: str
    group: str
    generated: bool = False
    builder: Optional[Callable[[], str]] = field(default=None, repr=False)
    is_new: bool = False
    in_nav: bool = True
    description: str = ""
    icon: str = "doc"


# %% Shared page shell -------------------------------------------------------
#: Inline SVG favicon: a simple node-and-link glyph standing for a small
#: cluster of machines.  Inline as a data URI so the pages need no extra file.
_FAVICON = (
    "data:image/svg+xml,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='32' rx='7' fill='%230f5f66'/%3E"
    "%3Cg stroke='%23e3efef' stroke-width='2' fill='none'%3E"
    "%3Cpath d='M16 9v6M16 15l-6 6M16 15l6 6'/%3E%3C/g%3E"
    "%3Cg fill='%23e3efef'%3E"
    "%3Ccircle cx='16' cy='8' r='3'/%3E"
    "%3Ccircle cx='9' cy='23' r='3'/%3E"
    "%3Ccircle cx='23' cy='23' r='3'/%3E%3C/g%3E%3C/svg%3E"
)


def _brand_svg() -> str:
    """Return the inline brand mark used in the navigation strip."""
    return (
        '<svg viewBox="0 0 32 32" aria-hidden="true" fill="none">'
        '<g stroke="currentColor" stroke-width="2.4" stroke-linecap="round">'
        '<path d="M16 10v5M16 15l-6 6M16 15l6 6"/></g>'
        '<g fill="currentColor">'
        '<circle cx="16" cy="7" r="3"/>'
        '<circle cx="9" cy="24" r="3"/>'
        '<circle cx="23" cy="24" r="3"/></g></svg>'
    )


def build_nav(manifest: Sequence[PageSpec],
              version: str,
              depth: int,
              with_theme_button: bool) -> str:
    """Return the shared navigation strip markup.

    Parameters
    ----------
    manifest
        The page manifest.  Entries with ``in_nav`` False are omitted.
    version
        Version string for the stamp, without a leading "v".
    depth
        Directory depth of the page being built, relative to the AI_Local
        directory.  0 for a top-level page, 1 for a page under ``Archive/``.
        Used to prefix every href with the right number of ``../`` segments,
        so the same strip works from both levels.
    with_theme_button
        True to include the strip's own theme control.  Passed False for a
        page that already has a theme toggle of its own, so no page ever
        shows two.

    Returns
    -------
    str
        The ``<nav class="ailnav">`` element.
    """
    up = "../" * depth

    links: List[str] = []
    for spec in manifest:
        if not spec.in_nav:
            continue
        label = html.escape(spec.nav_label)
        # A nav entry for a page in a subdirectory needs its own prefix too.
        href = up + spec.filename
        links.append(f'<a href="{href}">{label}</a>')

    theme = ""
    if with_theme_button:
        theme = (
            '<button class="ailnav-theme" type="button" '
            'aria-label="Switch theme" aria-pressed="false">'
            '<span class="ailnav-theme-icon" aria-hidden="true">\u263E</span>'
            '<span class="ailnav-theme-label">Dark</span>'
            '</button>'
        )

    return (
        '<nav class="ailnav" aria-label="AI_Local page set">\n'
        '  <div class="ailnav-inner">\n'
        f'    <a class="ailnav-brand" href="{up}index.html">'
        f'{_brand_svg()}<span>AI_Local</span></a>\n'
        f'    <span class="ailnav-ver">v{html.escape(version)}</span>\n'
        '    <div class="ailnav-links">\n'
        f'      {"".join(links)}\n'
        '    </div>\n'
        f'    {theme}\n'
        '  </div>\n'
        '</nav>'
    )


def asset_links(depth: int, *, include_site_css: bool,
                include_legacy_dark: bool) -> str:
    """Return the shared ``<link>`` and ``<script>`` tags for a page.

    Parameters
    ----------
    depth
        Directory depth relative to the AI_Local directory.
    include_site_css
        True only for the generated pages, which use ``site.css`` as their
        base stylesheet.  A pre-existing page keeps its own inline stylesheet
        and must NOT receive this, or its appearance would change.
    include_legacy_dark
        True for the three pages that had no dark theme at all.

    Returns
    -------
    str
        Markup to insert before ``</head>``.
    """
    up = "../" * depth
    out: List[str] = []

    if include_site_css:
        out.append(f'<link rel="stylesheet" href="{up}assets/site.css">')

    # Order matters: KaTeX's stylesheet first, then the equation component,
    # which styles the cards KaTeX renders into.
    out.append(f'<link rel="stylesheet" href="{up}assets/katex/katex.min.css">')
    out.append(f'<link rel="stylesheet" href="{up}assets/equations.css">')
    out.append(f'<link rel="stylesheet" href="{up}assets/sitenav.css">')

    if include_legacy_dark:
        # Last, so it can override the page's own inline stylesheet on equal
        # specificity. Scoped to [data-theme="dark"], so it is inert otherwise.
        out.append(f'<link rel="stylesheet" href="{up}assets/legacy-dark.css">')

    return "\n".join(out)


def asset_scripts(depth: int) -> str:
    """Return the shared ``<script>`` tags, for insertion before ``</body>``."""
    up = "../" * depth
    return "\n".join([
        f'<script src="{up}assets/katex/katex.min.js"></script>',
        f'<script src="{up}assets/katex/contrib/auto-render.min.js"></script>',
        f'<script src="{up}assets/equations.js"></script>',
        f'<script src="{up}assets/sitenav.js"></script>',
    ])


def wrap_page(spec: PageSpec,
              body: str,
              manifest: Sequence[PageSpec],
              version: str) -> str:
    """Wrap a body fragment in the full page shell.

    Used for generated pages only.  Produces a complete, valid, standalone
    HTML document with exactly one doctype, one ``<html>`` and one ``<body>``.
    """
    depth = spec.filename.count("/")
    up = "../" * depth
    nav = build_nav(manifest, version, depth, with_theme_button=True)
    title = html.escape(spec.title)
    desc = html.escape(spec.description or spec.blurb)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="author" content="William W. Wallace">
<meta name="generator" content="build_ai_local_site.py 0.0.1">
<link rel="icon" href="{_FAVICON}" type="image/svg+xml">
{asset_links(depth, include_site_css=True, include_legacy_dark=False)}
</head>
<body class="ail">
<a class="skip" href="#content">Skip to content</a>
{nav}
<main id="content">
{body.strip()}
</main>
<footer class="foot">
  <div class="container">
    <p><strong>AI_Local</strong> v{html.escape(version)} &middot; William W. Wallace &middot;
       <a href="{up}CHANGELOG.html">change log</a> &middot;
       <a href="{up}references.html">references</a></p>
    <p class="small">Equations typeset offline with KaTeX. Every page in this set opens
       from local disk with no network access, and nothing here uses browser storage.</p>
  </div>
</footer>
{asset_scripts(depth)}
</body>
</html>
"""


# %% Retrofit of the pre-existing pages --------------------------------------
# Regular expressions used to detect and strip the artifact iframe wrapper
# that four of the source pages carry.  The wrapper takes the form:
#
#     <!DOCTYPE html><html lang="en"><head>...white background...</head><body>
#         <!DOCTYPE html><html lang="en" data-theme="dark"> ... </html>
#         <script></script></body></html>
#
# so the real document is nested inside the wrapper's <body>.  Leaving it in
# place gives a document with two doctypes and two <body> elements, which
# browsers recover from but which no validator accepts and which makes
# injecting anything into "the" <head> ambiguous.

_DOCTYPE_HTML = re.compile(r"<!DOCTYPE\s+html\s*>\s*<html", re.IGNORECASE)
_HEAD_CLOSE = re.compile(r"</head\s*>", re.IGNORECASE)
_BODY_OPEN = re.compile(r"<body\b[^>]*>", re.IGNORECASE)
_BODY_CLOSE_LAST = re.compile(r"</body\s*>", re.IGNORECASE)

#: Markers that indicate a page already owns a theme control, so the shared
#: strip must not add a second one.
_THEME_MARKERS = (
    "theme-toggle", "themeToggle", "data-theme-toggle",
    "theme-btn", "toggleTheme", "setTheme",
)

#: Marker that indicates a page already has dark-theme rules of its own.
_DARK_MARKERS = ('[data-theme="dark"]', "prefers-color-scheme")


def unwrap_artifact_shell(source: str) -> Tuple[str, bool]:
    """Remove a duplicated artifact iframe wrapper, if present.

    A wrapped page has two ``<!DOCTYPE html><html`` occurrences: the wrapper's
    and the real document's.  The real document runs from the second
    occurrence to its matching ``</html>``, and everything outside it is
    wrapper scaffolding with no content.

    Parameters
    ----------
    source
        The raw page text.

    Returns
    -------
    (str, bool)
        The unwrapped document and whether anything was removed.  When no
        wrapper is detected the input is returned unchanged.
    """
    starts = [m.start() for m in _DOCTYPE_HTML.finditer(source)]
    if len(starts) < 2:
        return source, False

    inner_start = starts[1]

    # The real document ends at its own </html>.  Find the LAST </html> that
    # still precedes the wrapper's trailing scaffolding: the wrapper emits
    # "</html>\n<script></script></body></html>", so the inner document's
    # closing tag is the second-to-last one.
    closes = [m.end() for m in re.finditer(r"</html\s*>", source, re.IGNORECASE)]
    if len(closes) < 2:
        return source, False

    inner_end = closes[-2]
    inner = source[inner_start:inner_end]

    # Sanity check before accepting the slice: the extracted document must be
    # the bulk of the file and must contain a <body>.  Anything else means the
    # page is not shaped the way this function assumes, and it is safer to
    # leave it alone than to truncate it.
    if len(inner) < 0.5 * len(source) or not _BODY_OPEN.search(inner):
        return source, False

    return inner.strip() + "\n", True


def retrofit_page(source: str,
                  spec: PageSpec,
                  manifest: Sequence[PageSpec],
                  version: str) -> Tuple[str, Dict[str, bool]]:
    """Add the shared navigation and stylesheets to a pre-existing page.

    The page's own stylesheet, layout, content, scripts and theme control are
    left byte-for-byte unchanged.  Exactly four things are inserted:

    * the shared ``<link>`` tags, immediately before ``</head>``;
    * the navigation strip, immediately after the opening ``<body>`` tag;
    * the shared ``<script>`` tags, immediately before the final ``</body>``;
    * nothing else.

    Parameters
    ----------
    source
        Raw page text, already unwrapped if it carried an artifact wrapper.
    spec
        The page's manifest entry.
    manifest
        The whole manifest, for the navigation strip.
    version
        Version string for the stamp.

    Returns
    -------
    (str, dict)
        The retrofitted page and a dict of what was done, for the report.
    """
    depth = spec.filename.count("/")

    owns_theme = any(marker in source for marker in _THEME_MARKERS)
    has_dark = any(marker in source for marker in _DARK_MARKERS)

    actions = {
        "owns_theme_control": owns_theme,
        "had_dark_theme": has_dark,
        "legacy_dark_added": not has_dark,
        "head_injected": False,
        "nav_injected": False,
        "scripts_injected": False,
    }

    out = source

    # --- 1. stylesheets, before </head> ---------------------------------
    links = asset_links(
        depth,
        include_site_css=False,          # never: it would restyle the page
        include_legacy_dark=not has_dark,
    )
    match = _HEAD_CLOSE.search(out)
    if match:
        out = out[:match.start()] + links + "\n" + out[match.start():]
        actions["head_injected"] = True

    # --- 2. navigation strip, after <body ...> --------------------------
    nav = build_nav(manifest, version, depth,
                    with_theme_button=not owns_theme)
    match = _BODY_OPEN.search(out)
    if match:
        out = out[:match.end()] + "\n" + nav + "\n" + out[match.end():]
        actions["nav_injected"] = True

    # --- 3. shared scripts, before the final </body> --------------------
    # rfind on the regex: take the LAST </body>, which is the document's own.
    closes = list(_BODY_CLOSE_LAST.finditer(out))
    if closes:
        at = closes[-1].start()
        out = out[:at] + asset_scripts(depth) + "\n" + out[at:]
        actions["scripts_injected"] = True

    return out, actions


# %% Verification ------------------------------------------------------------
@dataclass
class Problem:
    """One verification failure."""

    page: str
    kind: str
    detail: str

    def __str__(self) -> str:                       # pragma: no cover - display
        return f"[{self.kind}] {self.page}: {self.detail}"


def verify_equation_blocks(page: str, text: str) -> List[Problem]:
    """Check every equation block against the Atomic Theory Atlas pattern.

    Enforced rules, from ``PATTERNS.md``:

    * the ``aria-controls`` of each ``.info`` button names an existing
      ``.vars`` block, and that block is ``hidden`` initially;
    * each ``.vars`` id is unique within the page;
    * a block whose pill reads "Derived here" carries a ``.deriv`` step list;
    * the math uses ``\\[``/``\\]`` or ``\\(``/``\\)``, never ``$`` or ``$$``;
    * every block has a ``.eq-note``.
    """
    problems: List[Problem] = []

    # Split on the opening of each .eq card.  A non-greedy slice to the next
    # card start (or end of text) is sufficient here because the cards are
    # emitted by eq_library and are never nested.
    cards = re.findall(r'<div class="eq" id="(eq-[^"]+)">(.*?)(?=<div class="eq" id="|\Z)',
                       text, re.DOTALL)

    seen_var_ids: Dict[str, int] = {}

    for eq_id, card in cards:
        slug = eq_id[3:]

        # aria-controls -> .vars id
        ctrl = re.search(r'<button class="info" aria-controls="([^"]+)"', card)
        if not ctrl:
            problems.append(Problem(page, "eq", f"{eq_id}: no .info button with aria-controls"))
        else:
            target = ctrl.group(1)
            if target != f"v-{slug}":
                problems.append(Problem(
                    page, "eq",
                    f"{eq_id}: aria-controls is {target!r}, expected 'v-{slug}'"))
            if f'id="{target}"' not in card:
                problems.append(Problem(
                    page, "eq", f"{eq_id}: no .vars block with id {target!r}"))
            seen_var_ids[target] = seen_var_ids.get(target, 0) + 1

        # .vars must start hidden, so the page is compact until asked
        vars_tag = re.search(r'<div class="vars" id="[^"]+"([^>]*)>', card)
        if not vars_tag:
            problems.append(Problem(page, "eq", f"{eq_id}: no .vars block"))
        elif "hidden" not in vars_tag.group(1):
            problems.append(Problem(page, "eq", f"{eq_id}: .vars block is not hidden"))

        # A derived result must show its steps
        if 'class="pill derived"' in card and 'class="deriv"' not in card:
            problems.append(Problem(
                page, "eq", f"{eq_id}: tagged 'Derived here' but has no .deriv step list"))

        # Every block explains itself
        if 'class="eq-note"' not in card:
            problems.append(Problem(page, "eq", f"{eq_id}: no .eq-note"))

        # Exactly one provenance pill
        pills = re.findall(r'<span class="pill (stated|derived|data)">', card)
        if len(pills) != 1:
            problems.append(Problem(
                page, "eq", f"{eq_id}: expected 1 provenance pill, found {len(pills)}"))

        # Display math present
        if "\\[" not in card:
            problems.append(Problem(page, "eq", f"{eq_id}: no display math \\[ ... \\]"))

    for var_id, count in seen_var_ids.items():
        if count > 1:
            problems.append(Problem(page, "eq", f"duplicate .vars id {var_id!r} ({count}x)"))

    return problems


def verify_dollar_math(page: str, text: str) -> List[Problem]:
    """Check that no equation card uses ``$`` as a math delimiter.

    These pages are full of shell variables (``$env:USERPROFILE``,
    ``${VERSION}``, ``$svcArgs``), so ``$`` must never be a delimiter.  The
    check is scoped to the equation cards, where a stray ``$`` would be a
    mistake, rather than to the whole page, where ``$`` is legitimate shell.
    """
    problems: List[Problem] = []
    for eq_id, card in re.findall(
            r'<div class="eq" id="(eq-[^"]+)">(.*?)(?=<div class="eq" id="|\Z)',
            text, re.DOTALL):
        body = re.search(r'<div class="eq-body">(.*?)</div>', card, re.DOTALL)
        if body and "$" in body.group(1):
            problems.append(Problem(
                page, "math", f"{eq_id}: '$' inside .eq-body; use \\[ ... \\]"))
    return problems


def verify_citations(page: str, text: str, valid: Sequence[int]) -> List[Problem]:
    """Check every ``[n]`` citation resolves to a defined reference number."""
    problems: List[Problem] = []
    found = set()
    for raw in re.findall(r'references\.html#r(\d+)', text):
        found.add(int(raw))
    for num in sorted(found - set(valid)):
        problems.append(Problem(
            page, "cite", f"cites [{num}], which is not defined in references.py"))

    # A citation anchor whose visible text disagrees with its href is a
    # copy-paste error that is invisible on the rendered page.
    for href_num, shown in re.findall(
            r'href="references\.html#r(\d+)"[^>]*>\[(\d+)\]</a>', text):
        if href_num != shown:
            problems.append(Problem(
                page, "cite", f"anchor to r{href_num} displays [{shown}]"))
    return problems


def strip_inert(text: str) -> str:
    """Return the page with ``<script>``, ``<style>`` and comment bodies blanked.

    Structural tag counting has to ignore markup that only *appears* in the
    document.  Two real cases in this page set:

    * ``GPU_monitoring_setup.html`` builds a self-download in JavaScript with
      ``const htmlContent = '<!DOCTYPE html>\\n' + ...``, so a naive count sees
      two doctypes in a perfectly well-formed page.
    * Several pages show HTML snippets inside ``<pre><code>`` blocks, where the
      angle brackets are escaped and so are already harmless, but a future
      page may not escape them.

    Replacing each blanked region with spaces of the same length keeps every
    offset intact, so a position reported against the stripped text still
    points at the right place in the original.
    """
    def blank(match: "re.Match[str]") -> str:
        return " " * len(match.group(0))

    out = re.sub(r"(?is)<script\b[^>]*>.*?</script\s*>", blank, text)
    out = re.sub(r"(?is)<style\b[^>]*>.*?</style\s*>", blank, out)
    out = re.sub(r"(?s)<!--.*?-->", blank, out)
    return out


def verify_structure(page: str, text: str, *, generated: bool) -> List[Problem]:
    """Check the document is one well-formed page with the shared assets."""
    problems: List[Problem] = []

    # Count structural tags on the inert-stripped text, so a doctype or a
    # <body> that only exists inside a script string is not counted.
    structural = strip_inert(text)

    n_doctype = len(re.findall(r"<!DOCTYPE", structural, re.IGNORECASE))
    n_html_open = len(re.findall(r"<html\b", structural, re.IGNORECASE))
    n_html_close = len(re.findall(r"</html\s*>", structural, re.IGNORECASE))
    n_body_open = len(_BODY_OPEN.findall(structural))
    n_body_close = len(_BODY_CLOSE_LAST.findall(structural))

    if n_doctype != 1:
        problems.append(Problem(page, "struct", f"{n_doctype} doctype declarations, expected 1"))
    if n_html_open != 1 or n_html_close != 1:
        problems.append(Problem(
            page, "struct", f"{n_html_open} <html> / {n_html_close} </html>, expected 1 each"))
    if n_body_open != 1 or n_body_close != 1:
        problems.append(Problem(
            page, "struct", f"{n_body_open} <body> / {n_body_close} </body>, expected 1 each"))

    # Shared assets present
    for needed in ("assets/equations.css", "assets/sitenav.css",
                   "assets/katex/katex.min.css", "assets/equations.js",
                   "assets/sitenav.js", "assets/katex/katex.min.js"):
        if needed not in text:
            problems.append(Problem(page, "assets", f"missing reference to {needed}"))

    # Navigation strip present, exactly once.  Counted on the full text, not
    # the stripped text, because the strip is real markup.
    n_nav = text.count('<nav class="ailnav"')
    if n_nav != 1:
        problems.append(Problem(page, "nav", f"{n_nav} navigation strips, expected 1"))

    # Never two theme controls on one page
    n_theme = text.count('class="ailnav-theme"')
    owns = any(m in text for m in _THEME_MARKERS if m != "theme-btn") or \
        'class="theme-toggle"' in text
    if n_theme and owns and 'class="ailnav-theme"' in text:
        # The strip's button plus the page's own would be two controls.  Only
        # flag it when the page's own control is a real button, not just a
        # stray string in a comment.
        page_own = re.search(
            r'<button[^>]*class="[^"]*(theme-toggle|theme-btn)[^"]*"', text)
        if page_own:
            problems.append(Problem(
                page, "theme", "page has its own theme button and the strip added another"))

    if generated:
        if 'lang="en"' not in text:
            problems.append(Problem(page, "a11y", 'missing lang="en" on <html>'))
        if "<title>" not in text:
            problems.append(Problem(page, "meta", "missing <title>"))
        if 'name="description"' not in text:
            problems.append(Problem(page, "meta", "missing meta description"))
        if 'class="skip"' not in text:
            problems.append(Problem(page, "a11y", "missing skip link"))

    return problems


#: Class names the SHARED stylesheets style with an unscoped selector, and
#: which therefore must not appear on any pre-existing page.  This list exists
#: because the first build of this set used `.snav` for the navigation strip,
#: and llama-rpc-vulkan-guide.html already defined `.snav{flex:1;padding:...}`
#: for its own sidebar: the shared sheet silently repainted that page's
#: navigation.  The prefix is now `ailnav`, and this check is what keeps the
#: class from being reintroduced.
#:
#: `.pill` is NOT in this list, even though equations.css styles it, because
#: those rules are scoped to `.eq .pill` and `.ail .pill` precisely so they
#: cannot reach the monitoring page that uses `.pill` for its own badges.
#: `.info` is likewise scoped to `.eq .info`, since four pages use `.info` as
#: an admonition class.
_SHARED_GLOBAL_CLASSES = (
    "ailnav", "ailnav-inner", "ailnav-brand", "ailnav-ver", "ailnav-links",
    "ailnav-sep", "ailnav-theme", "ailnav-theme-icon", "ailnav-theme-label",
    "eq", "eq-head", "eq-title", "eq-tools", "eq-body", "eq-note",
    "vars", "deriv", "table-wrap", "cite", "eqc-callout", "info-label",
)


def page_class_names(text: str) -> set:
    """Return every class name a page uses in markup or defines in CSS."""
    names = set()
    for match in re.finditer(r'class="([^"]+)"', text):
        names.update(match.group(1).split())
    # CSS selectors in the page's own inline <style> blocks.
    for style in re.findall(r"(?is)<style\b[^>]*>(.*?)</style\s*>", text):
        for match in re.finditer(r"\.([A-Za-z][\w-]*)", style):
            names.add(match.group(1))
    return names


def verify_class_collisions(page: str, original: str) -> List[Problem]:
    """Fail if a pre-existing page uses a class the shared sheets style globally.

    Checked against the page's ORIGINAL text, before this script injected
    anything.  Checking the retrofitted output instead would require
    discounting the injected navigation markup, and getting that discount
    wrong is how a real collision gets hidden behind a false positive.  The
    original text answers the question directly: did the host page already use
    this name?

    Parameters
    ----------
    page
        Manifest filename, for the report.
    original
        The page's text as read from the source directory, before unwrapping
        or retrofitting.

    Returns
    -------
    list of Problem
        One entry per colliding class name.
    """
    problems: List[Problem] = []
    used = page_class_names(original)

    for name in _SHARED_GLOBAL_CLASSES:
        if name in used:
            problems.append(Problem(
                page, "collision",
                f"host page already uses .{name}, which a shared stylesheet "
                f"styles with an unscoped selector; rename the shared class "
                f"or scope its rules before shipping"))

    return problems


def verify_tables(page: str, text: str) -> List[Problem]:
    """Check every table has a caption and is wrapped for horizontal scroll.

    ``PATTERNS.md`` requires a caption on every table and requires the table
    to sit inside ``.table-wrap``.  Only generated pages are held to this;
    the pre-existing pages' tables are their authors' and are left alone.
    """
    problems: List[Problem] = []
    tables = re.findall(r"<table\b.*?</table>", text, re.DOTALL)
    for i, table in enumerate(tables, start=1):
        if "<caption" not in table:
            snippet = re.sub(r"\s+", " ", table[:90])
            problems.append(Problem(page, "table", f"table {i} has no <caption>: {snippet}..."))
    n_wrap = text.count('class="table-wrap"')
    if len(tables) > n_wrap:
        problems.append(Problem(
            page, "table",
            f"{len(tables)} tables but {n_wrap} .table-wrap containers"))
    return problems


def verify_links(out_dir: Path, page: str, text: str) -> List[Problem]:
    """Check every relative link and asset reference resolves on disk."""
    problems: List[Problem] = []
    page_dir = (out_dir / page).parent

    # href and src attributes, excluding absolute URLs, data URIs and anchors
    refs = re.findall(r'(?:href|src)="([^"]+)"', text)
    for ref in refs:
        if ref.startswith(("http://", "https://", "data:", "#", "mailto:")):
            continue
        target = ref.split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        resolved = (page_dir / target).resolve()
        if not resolved.exists():
            problems.append(Problem(page, "link", f"broken reference: {ref}"))
    return problems


def verify_anchors(out_dir: Path, page: str, text: str,
                   anchor_index: Dict[str, set]) -> List[Problem]:
    """Check that a cross-page ``#fragment`` exists on the target page."""
    problems: List[Problem] = []
    for ref in re.findall(r'href="([^"]*\.html)#([^"]+)"', text):
        target_file, frag = ref
        # Normalise to a manifest-style path
        key = str((Path(page).parent / target_file)).replace("\\", "/")
        key = key[2:] if key.startswith("./") else key
        if key in anchor_index and frag not in anchor_index[key]:
            problems.append(Problem(
                page, "anchor", f"links to {target_file}#{frag}, which has no such id"))
    return problems


# %% Orchestration -----------------------------------------------------------
def collect_anchor_index(pages: Dict[str, str]) -> Dict[str, set]:
    """Build a map of page -> set of element ids, for cross-page anchor checks."""
    index: Dict[str, set] = {}
    for name, text in pages.items():
        index[name] = set(re.findall(r'\sid="([^"]+)"', text))
    return index


def run(src: Path, out: Path, modules_dir: Path,
        verify_only: bool = False) -> int:
    """Generate and verify the page set.

    Returns
    -------
    int
        Process exit status: 0 when every check passed, 1 otherwise.
    """
    sys.path.insert(0, str(modules_dir))

    # Imported here, after the path is set, so the script can be read and
    # linted without the content modules present.
    import eq_library            # noqa: F401  (imported for its side effects)
    import page_local_build
    import page_meta
    import page_models
    import page_monitoring
    import page_sandbox
    import references

    references.validate()
    version = page_meta.current_version()

    def check_manifest_plaintext(specs) -> None:
        """Fail if a manifest string was pre-escaped as HTML.

        Every PageSpec string is escaped with html.escape() at the point of
        use, so an entity written here is escaped a second time and renders
        literally: nav_label="Build &amp; test" appears on the page as
        "Build &amp;amp; test".  That is a cosmetic bug that survives every
        other check in this script, because the markup is perfectly valid.
        """
        entities = ("&amp;", "&lt;", "&gt;", "&quot;", "&mdash;",
                    "&ndash;", "&nbsp;", "&middot;")
        bad = []
        for spec in specs:
            for field_name in ("nav_label", "title", "blurb", "description"):
                value = getattr(spec, field_name, "") or ""
                for entity in entities:
                    if entity in value:
                        bad.append(f"{spec.filename}.{field_name} contains "
                                   f"{entity!r}; manifest strings are plain text")
        if bad:
            raise ValueError("pre-escaped manifest strings:\n  "
                             + "\n  ".join(bad))

    # ---- the manifest ---------------------------------------------------
    manifest: List[PageSpec] = [
        PageSpec(
            filename="index.html",
            nav_label="Overview",
            title="Running AI on your own hardware, end to end",
            blurb="Landing page for the set, with a suggested build order and the "
                  "reading conventions used throughout.",
            group="meta",
            generated=True,
            is_new=True,
            icon="home",
            description="Landing page for the AI_Local set: deploying language models "
                        "across a home or lab network, and letting them build and test "
                        "code on hardware you own.",
        ),
        PageSpec(
            filename="local-code-build-test.html",
            nav_label="Build & test",
            title="Letting a local model build and test code on your own hardware",
            blurb="The execution backends Open WebUI offers, their full variable sets, "
                  "wiring in a named mamba environment, C++ and Python build paths, and "
                  "what each containment model actually contains.",
            group="build",
            generated=True,
            builder=page_local_build.build,
            is_new=True,
            icon="terminal",
            description="How to give a locally hosted model a real shell and a real "
                        "Python environment through Open WebUI, so it can write, compile "
                        "and test code on local hardware.",
        ),
        PageSpec(
            filename="ollama-model-selection.html",
            nav_label="Model choice",
            title="Which Ollama models are worth running for local code work",
            blurb="Tool-calling models in the Ollama library with every published size, "
                  "context window and benchmark figure cited, plus the memory and "
                  "throughput arithmetic that decides what will fit and run.",
            group="build",
            generated=True,
            builder=page_models.build,
            is_new=True,
            icon="chart",
            description="Selecting an Ollama model for local code generation and testing: "
                        "published sizes and capabilities, and the memory and bandwidth "
                        "arithmetic that decides whether a tag fits.",
        ),
        PageSpec(
            filename="claude-sandbox-local-env.html",
            nav_label="Sandbox access",
            title="Giving a sandboxed agent access to local mamba environments",
            blurb="The OS-enforced command sandbox: what it restricts, how it differs "
                  "from a container, the settings that grant environment access, and the "
                  "denial checks that prove a policy took effect.",
            group="build",
            generated=True,
            builder=page_sandbox.build,
            is_new=True,
            icon="lock",
            description="Granting a sandboxed agent prompt access to local mamba "
                        "environments for building and testing, and what the boundary "
                        "actually is.",
        ),

        PageSpec(
            filename="monitoring-sizing.html",
            nav_label="Monitor sizing",
            title="Sizing the monitoring stack, and getting the queries right",
            blurb="The four relations the monitoring install pages assume but never "
                  "state: retention disk cost, ingest rate, the range-vector window "
                  "lower bound, and counters versus gauges.",
            group="monitoring",
            generated=True,
            builder=page_monitoring.build,
            is_new=True,
            icon="chart",
            description="Prometheus storage and ingest sizing for a local AI "
                        "deployment, the PromQL range-window condition, and how to "
                        "treat counters and gauges correctly.",
        ),

        # --- pre-existing pages, retrofitted only ------------------------
        PageSpec(
            filename="llama-rpc-vulkan-guide.html",
            nav_label="llama.cpp RPC",
            title="llama.cpp RPC + Vulkan — 4-node home network guide",
            blurb="Building llama.cpp with RPC and Vulkan, and splitting a model across "
                  "four machines when it will not fit on one card.",
            group="inference",
        ),
        PageSpec(
            filename="Jupyter_Server_Setup_wsl.html",
            nav_label="Jupyter WSL2",
            title="Open WebUI + Jupyter GPU Server Setup (Windows 10/11 + WSL2)",
            blurb="A Jupyter GPU server under WSL2, wired to Open WebUI for code "
                  "execution.",
            group="build",
        ),
        PageSpec(
            filename="Dockler_Jupyter_withGPU_Passthru_nssm.html",
            nav_label="Docker Jupyter",
            title="Open WebUI + Dockerized Jupyter GPU Server (Windows 10/11)",
            blurb="The same Jupyter server in Docker with GPU passthrough, run as a "
                  "Windows service through NSSM.",
            group="build",
        ),
        PageSpec(
            filename="Promethius_Grafana_windows11-llama-monitoring-tutorial.html",
            nav_label="Monitoring W11",
            title="Windows 11 Prometheus + Grafana — Multi-Node llama-server",
            blurb="End-to-end monitoring of a multi-node llama-server deployment on "
                  "Windows 11.",
            group="monitoring",
        ),
        PageSpec(
            filename="GPU_monitoring_setup.html",
            nav_label="GPU metrics",
            title="Multi-Vendor GPU Monitoring Documentation",
            blurb="GPU exporters for NVIDIA and AMD, including the WSL2 bridge AMD "
                  "requires on Windows.",
            group="monitoring",
        ),
        PageSpec(
            filename="Grafana_Prometheus_install_windows.html",
            nav_label="Install (Win)",
            title="Install & Use Prometheus + Grafana on Windows / WSL2",
            blurb="Installing Prometheus, windows_exporter and Grafana on Windows, with "
                  "a WSL2 node_exporter alternative.",
            group="monitoring",
        ),
        PageSpec(
            filename="Grafan_Promethius_install_linux.html",
            nav_label="Install (Linux)",
            title="Install & Use Prometheus + Grafana on Node A",
            blurb="The same stack on a systemd Linux host, with node_exporter and a "
                  "first dashboard.",
            group="monitoring",
        ),

        # --- archived pages: retrofitted, kept out of the nav strip ------
        PageSpec(
            filename="Archive/Jupyter_Code_Eval_Setup.html",
            nav_label="Archive: Jupyter",
            title="Archived — Jupyter code-evaluation setup",
            blurb="Earlier revision of the Jupyter code-evaluation setup, kept for "
                  "reference.",
            group="build",
            in_nav=False,
        ),
        PageSpec(
            filename="Archive/Windows_Exporter_Grafana_dashboard.html",
            nav_label="Archive: dashboard",
            title="Archived — windows_exporter Grafana dashboard",
            blurb="Earlier revision of the windows_exporter dashboard notes, kept for "
                  "reference.",
            group="monitoring",
            in_nav=False,
        ),

        # --- generated meta pages ---------------------------------------
        PageSpec(
            filename="references.html",
            nav_label="References",
            title="Sources — AI_Local",
            blurb="One IEEE-format reference table for the whole set, with a "
                  "sourcing-confidence class per row and a list of the figures that "
                  "are estimates rather than citations.",
            group="meta",
            generated=True,
            builder=page_meta.build_references,
            is_new=True,
            icon="book",
            description="IEEE-format reference list for the AI_Local page set, with "
                        "sourcing confidence per reference.",
        ),
        PageSpec(
            filename="CHANGELOG.html",
            nav_label="Change log",
            title="Version history — AI_Local",
            blurb="What changed in each revision of the set, what was deliberately left "
                  "alone, and the candidates for the next revision.",
            group="meta",
            generated=True,
            builder=page_meta.build_changelog,
            is_new=True,
            icon="calendar",
            description="Version history for the AI_Local page set, following semantic "
                        "versioning from 0.0.1.",
        ),
    ]

    check_manifest_plaintext(manifest)

    # index.html's builder needs the manifest, so it is bound here rather
    # than in the manifest literal above.
    for spec in manifest:
        if spec.filename == "index.html":
            spec.builder = lambda m=manifest: page_meta.build_index(m)

    pages: Dict[str, str] = {}
    originals: Dict[str, str] = {}   # pre-retrofit text of each host page
    report: List[str] = []

    if not verify_only:
        out.mkdir(parents=True, exist_ok=True)
        (out / "Archive").mkdir(exist_ok=True)

        # ---- generate ---------------------------------------------------
        for spec in manifest:
            if not spec.generated:
                continue
            assert spec.builder is not None, f"{spec.filename} has no builder"
            text = wrap_page(spec, spec.builder(), manifest, version)
            (out / spec.filename).write_text(text, encoding="utf-8")
            pages[spec.filename] = text
            report.append(f"  generated  {spec.filename:58s} {len(text):7d} B")

        # ---- retrofit ---------------------------------------------------
        for spec in manifest:
            if spec.generated:
                continue
            source_path = src / spec.filename
            if not source_path.exists():
                report.append(f"  MISSING    {spec.filename}")
                continue

            raw = source_path.read_text(encoding="utf-8", errors="replace")
            # Kept for verify_class_collisions(), which must see the page as
            # it was before anything was injected into it.
            originals[spec.filename] = raw
            inner, unwrapped = unwrap_artifact_shell(raw)
            text, actions = retrofit_page(inner, spec, manifest, version)

            (out / spec.filename).parent.mkdir(parents=True, exist_ok=True)
            (out / spec.filename).write_text(text, encoding="utf-8")
            pages[spec.filename] = text

            notes = []
            if unwrapped:
                notes.append("unwrapped")
            if actions["legacy_dark_added"]:
                notes.append("dark-theme added")
            if not actions["owns_theme_control"]:
                notes.append("theme button added")
            report.append(
                f"  retrofit   {spec.filename:58s} {len(text):7d} B"
                f"  {', '.join(notes) if notes else '-'}"
            )
    else:
        for spec in manifest:
            path = out / spec.filename
            if path.exists():
                pages[spec.filename] = path.read_text(encoding="utf-8", errors="replace")
            # The collision check needs the pre-retrofit text, which in
            # verify-only mode still lives in the source directory.
            if not spec.generated:
                source_path = src / spec.filename
                if source_path.exists():
                    originals[spec.filename] = source_path.read_text(
                        encoding="utf-8", errors="replace")

    # ---- verify ---------------------------------------------------------
    valid_refs = references.numbers()
    anchor_index = collect_anchor_index(pages)
    problems: List[Problem] = []

    generated_names = {s.filename for s in manifest if s.generated}

    for name, text in sorted(pages.items()):
        problems += verify_structure(name, text, generated=name in generated_names)
        problems += verify_equation_blocks(name, text)
        problems += verify_dollar_math(name, text)
        problems += verify_citations(name, text, valid_refs)
        problems += verify_links(out, name, text)
        problems += verify_anchors(out, name, text, anchor_index)
        if name in originals:
            problems += verify_class_collisions(name, originals[name])
        if name in generated_names:
            problems += verify_tables(name, text)

    # ---- print the report ----------------------------------------------
    print("=" * 78)
    print(f"AI_Local page set  v{version}")
    print("=" * 78)
    for line in report:
        print(line)

    print("-" * 78)
    n_eq = sum(len(re.findall(r'<div class="eq" id=', t)) for t in pages.values())
    n_tab = sum(len(re.findall(r"<table\b", t)) for t in pages.values())
    n_cite = sum(len(re.findall(r"references\.html#r\d+", t)) for t in pages.values())
    cited = sorted({int(n) for t in pages.values()
                    for n in re.findall(r"references\.html#r(\d+)", t)})
    uncited = sorted(set(valid_refs) - set(cited))

    print(f"  pages       : {len(pages)}")
    print(f"  equations   : {n_eq}")
    print(f"  tables      : {n_tab}")
    print(f"  citations   : {n_cite} occurrences of {len(cited)} distinct references")
    print(f"  references  : {len(valid_refs)} defined, {len(uncited)} never cited"
          + (f" -> {uncited}" if uncited else ""))

    print("-" * 78)
    if problems:
        print(f"FAILED: {len(problems)} problem(s)")
        by_kind: Dict[str, List[Problem]] = {}
        for p in problems:
            by_kind.setdefault(p.kind, []).append(p)
        for kind in sorted(by_kind):
            print(f"\n  {kind} ({len(by_kind[kind])}):")
            for p in by_kind[kind][:40]:
                print(f"    {p.page}: {p.detail}")
            if len(by_kind[kind]) > 40:
                print(f"    ... and {len(by_kind[kind]) - 40} more")
        return 1

    print("PASSED: all structural, equation, citation, link and anchor checks")
    return 0


# %% Entry point -------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse arguments and run the build."""
    parser = argparse.ArgumentParser(
        description="Generate and verify the AI_Local page set.")
    parser.add_argument("--src", required=True, type=Path,
                        help="directory holding the ORIGINAL pages to retrofit")
    parser.add_argument("--out", required=True, type=Path,
                        help="output AI_Local directory (must not be --src)")
    parser.add_argument("--modules", type=Path, default=None,
                        help="directory holding the page-content modules "
                             "(default: this script's parent's parent)")
    parser.add_argument("--verify-only", action="store_true",
                        help="verify an already-built tree without generating")
    args = parser.parse_args(argv)

    src = args.src.resolve()
    out = args.out.resolve()
    if src == out:
        parser.error("--src and --out must differ; this script never writes "
                     "next to its inputs")

    modules = (args.modules or Path(__file__).resolve().parent.parent).resolve()

    return run(src, out, modules, verify_only=args.verify_only)


if __name__ == "__main__":
    raise SystemExit(main())
