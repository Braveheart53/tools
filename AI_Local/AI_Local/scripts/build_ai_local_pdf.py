#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_ai_local_pdf.py -- LuaLaTeX source and bookmarked PDF for the AI_Local set.

Author  : William W. Wallace
Contact : adaptive.electrodynamics@gmail.com
Version : 0.0.2
Created : 2026-11-05

PURPOSE
-------
Produces the AI_Local documentation as a LuaLaTeX document and a bookmarked
PDF, from the SAME source modules the HTML pages are built from.  That shared
origin is the whole point: a hand-maintained LaTeX copy of a 17-page HTML set
would diverge within one revision, and the divergence would be invisible
because nothing compares the two.  Here an equation, a reference or a model
figure exists once, in ``eq_library.py``, ``references.py`` or
``model_catalog.py``, and both outputs are projections of it.

WHY LuaLaTeX AND NOT pdflatex
-----------------------------
LuaTeX is this project's stated preference, and it is also the right engine
here on the merits: ``fontspec`` and ``unicode-math`` let the document use
system OpenType fonts and set the mathematics in a real math font, and the
source can contain UTF-8 directly (the micro sign, the Angstrom, en dashes)
without input-encoding gymnastics.  ``pdflatex`` would need every one of
those escaped.

WHAT "BOOKMARKED" MEANS HERE
----------------------------
The PDF carries a four-level outline tree built by the ``bookmark`` package:
part, section, subsection and, for the equation catalogue and the reference
list, one bookmark per equation and per reference.  A reader looking for the
key/value cache relation or reference [27] finds it in the sidebar rather
than by scrolling.  ``hyperref`` is configured with ``bookmarksnumbered`` so
the outline carries the same numbers as the body, and ``bookmarksopen`` to
two levels so the tree is useful on first open without being overwhelming.

STRUCTURE OF THE OUTPUT
-----------------------
The PDF is deliberately NOT a transcription of the HTML.  A web page set and
a reference document want different shapes, so this is organised as a
reference manual:

    Part I   Implementation flow        the five stages, as a procedure
    Part II  Equation catalogue         all 16 relations, with derivations
                                        and variable tables, which is the
                                        part that benefits most from print
    Part III Model catalogue            the shortlist as a table
    Part IV  Configuration reference    the settings tables
    Part V   References                 IEEE, with sourcing confidence

CONVERSION APPROACH
-------------------
The equation bodies in ``eq_library.py`` are already LaTeX -- that was the
point of authoring them for KaTeX with ``\\[ ... \\]`` delimiters -- so they
pass through untouched.  The surrounding prose is HTML, and is converted by
``html_to_latex()`` below, which handles the specific subset of markup these
modules actually emit rather than attempting to be a general converter.  A
general HTML-to-LaTeX converter is a research project; this one needs to
handle fourteen tags and does.

USAGE
-----
    python build_ai_local_pdf.py --modules ../src_modules --out ../../pdf

Writes ``AI_Local_Reference.tex`` and, when LuaLaTeX is present, runs it
twice (for cross-references and the outline) and writes
``AI_Local_Reference.pdf`` beside it.  With ``--tex-only`` it emits the
source and stops, which is what to use on a machine with no TeX.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import argparse
import html as html_mod
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

# %% Constants ---------------------------------------------------------------

#: Characters LaTeX treats specially, mapped to their escaped forms.  Order
#: matters: the backslash must be replaced first or it would escape the
#: backslashes introduced by the later replacements.
_LATEX_ESCAPES: List[Tuple[str, str]] = [
    ("\\", r"\textbackslash{}"),
    ("&", r"\&"),
    ("%", r"\%"),
    ("$", r"\$"),
    ("#", r"\#"),
    ("_", r"\_"),
    ("{", r"\{"),
    ("}", r"\}"),
    ("~", r"\textasciitilde{}"),
    ("^", r"\textasciicircum{}"),
]

#: HTML named entities the page modules use, mapped to the literal character.
#: Resolved before escaping so that, for example, ``&amp;`` becomes ``\&``
#: rather than ``\&amp;``.  html.unescape() handles the numeric forms.
_ENTITIES: Dict[str, str] = {
    "&mdash;": "\u2014", "&ndash;": "\u2013", "&nbsp;": "\u00a0",
    "&ldquo;": "\u201c", "&rdquo;": "\u201d", "&lsquo;": "\u2018",
    "&rsquo;": "\u2019", "&middot;": "\u00b7", "&asymp;": "\u2248",
    "&ge;": "\u2265", "&le;": "\u2264", "&times;": "\u00d7",
    "&minus;": "\u2212", "&rarr;": "\u2192", "&larr;": "\u2190",
    "&sect;": "\u00a7", "&deg;": "\u00b0", "&micro;": "\u00b5",
    "&hellip;": "\u2026", "&copy;": "\u00a9", "&#10003;": "\u2713",
    "&#9432;": "\u24d8", "&amp;": "&", "&lt;": "<", "&gt;": ">",
    "&quot;": '"', "&#8315;": "\u207b", "&sup1;": "\u00b9",
}


# %% Conversion helpers ------------------------------------------------------
def escape_latex(text: str) -> str:
    """Escape LaTeX special characters in literal text.

    Parameters
    ----------
    text : str
        Plain text, with HTML entities already resolved.

    Returns
    -------
    str
        The text with every LaTeX-special character escaped.

    Notes
    -----
    Never call this on a string that already contains intentional LaTeX --
    it would escape the backslashes.  Mathematics is extracted and set aside
    by :func:`html_to_latex` before this is reached.
    """
    for char, replacement in _LATEX_ESCAPES:
        text = text.replace(char, replacement)
    return text


def resolve_entities(text: str) -> str:
    """Replace HTML entities with the literal characters they denote."""
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    # Catch anything the explicit table missed, such as a numeric reference.
    return html_mod.unescape(text)


def allow_identifier_breaks(text: str) -> str:
    r"""Insert zero-width break opportunities inside long identifiers.

    Names such as ``OPEN_TERMINAL_FILE_BROWSER_ROOT`` and
    ``CODE_INTERPRETER_JUPYTER_AUTH_TOKEN`` are a single unbreakable word to
    TeX: the underscores are ``\_``, a control sequence rather than a letter,
    so the hyphenation machinery sees no break point and the name runs
    straight past the right margin of its table column.  This is the same
    defect the HTML pages fixed with ``overflow-wrap: anywhere``; the LaTeX
    equivalent is an explicit ``\allowbreak`` after each separator.

    ``\allowbreak`` adds a permitted break with no penalty and no glue, so
    the name is unchanged when it fits and splits after a separator when it
    does not.  Nothing is inserted inside mathematics, which at this point
    in the pipeline is still held in placeholders.

    Parameters
    ----------
    text : str
        LaTeX body text, with mathematics stashed.

    Returns
    -------
    str
        The same text with break opportunities after underscores, and after
        hyphens that sit inside a longer run of identifier characters.
    """
    # After an escaped underscore, but not when one immediately follows
    # (a doubled separator is not a sensible break point).
    text = re.sub(r"\\_(?!\\_)", r"\\_\\allowbreak{}", text)
    # After a hyphen that joins two identifier-ish runs, such as
    # "qwen3-coder-next" or "ggml-rpc-server". A hyphen between words is
    # left alone: TeX already breaks there.
    text = re.sub(r"(?<=[A-Za-z0-9])-(?=[A-Za-z0-9]{3,})",
                  r"-\\allowbreak{}", text)
    # Dotted names ("permissions.additionalDirectories",
    # "--storage.tsdb.retention.time") and paths ("tools/rpc/README.md").
    # The lookahead requires a lower-case letter so that a sentence-ending
    # period, which is followed by a space or a capital, is never touched.
    text = re.sub(r"(?<=[A-Za-z0-9])\.(?=[a-z][A-Za-z0-9]{2,})",
                  r".\\allowbreak{}", text)
    text = re.sub(r"(?<=[A-Za-z0-9])/(?=[A-Za-z0-9])",
                  r"/\\allowbreak{}", text)
    # Fragment anchors ("page.html#section") and assignments
    # ("QT_QPA_PLATFORM=offscreen"), both of which appear as one long word.
    text = re.sub(r"(?<=[A-Za-z0-9])\\#(?=[A-Za-z0-9])",
                  r"\\#\\allowbreak{}", text)
    text = re.sub(r"(?<=[A-Za-z0-9])=(?=[A-Za-z0-9])",
                  r"=\\allowbreak{}", text)
    return text


def html_to_latex(fragment: str, *, cite_map: Optional[Dict[int, str]] = None
                  ) -> str:
    """Convert the HTML subset these page modules emit into LaTeX.

    Handles exactly the tags the modules use: ``<p>``, ``<strong>``,
    ``<em>``, ``<span class="mono">``, ``<code>``, ``<s>``, ``<sup>``,
    ``<sub>``, ``<ul>``/``<ol>``/``<li>``, ``<a class="cite">`` and plain
    ``<a href>``.  Everything else is dropped, with its text content kept.

    Mathematics is protected first.  ``\\[ ... \\]`` and ``\\( ... \\)`` are
    lifted out into placeholders before any escaping happens, then restored
    as ``\\[ ... \\]`` and ``$ ... $``, so the LaTeX inside them survives
    untouched.  That ordering is the single most important thing in this
    function: escaping first would destroy every equation in the document.

    Parameters
    ----------
    fragment : str
        An HTML fragment from one of the page modules.
    cite_map : dict, optional
        Maps a reference number to the LaTeX label to cite.  When given,
        ``<a class="cite" href="...#rNN">[NN]</a>`` becomes a hyperlink to
        that label; otherwise it becomes a plain bracketed number.

    Returns
    -------
    str
        LaTeX body text.
    """
    text = fragment

    # ---- 1. protect mathematics -------------------------------------------
    # Display first, so that an inline delimiter inside a display block is
    # not mistaken for the start of its own group.
    math_store: List[Tuple[str, str]] = []

    def _stash(match: "re.Match[str]", kind: str) -> str:
        token = f"@@MATH{len(math_store)}@@"
        math_store.append((token, match.group(1)))
        return token if kind == "display" else token

    def _stash_display(match: "re.Match[str]") -> str:
        return _stash(match, "display")

    def _stash_inline(match: "re.Match[str]") -> str:
        return _stash(match, "inline")

    # Track which stash entries were display so they can be restored
    # differently; the index order of math_store gives the mapping.
    display_tokens: set = set()

    def _stash_display_marked(match: "re.Match[str]") -> str:
        token = f"@@MATH{len(math_store)}@@"
        math_store.append((token, match.group(1)))
        display_tokens.add(token)
        return token

    text = re.sub(r"\\\[(.*?)\\\]", _stash_display_marked, text, flags=re.S)
    text = re.sub(r"\\\((.*?)\\\)", _stash_inline, text, flags=re.S)

    # ---- 2. citations, before the generic anchor rule ---------------------
    # A citation becomes \hyperref, which is LaTeX, so it must be STASHED
    # like the mathematics rather than written into the text here. Written
    # here it would reach step 6 and be escaped into visible rubbish:
    # "19 GB\textbackslash{}hyperref[ref:11]\{[11]\}" appeared in the body
    # of an earlier build, which compiled cleanly and was wrong on the page.
    raw_store: List[Tuple[str, str]] = []

    def _stash_raw(latex: str) -> str:
        token = f"@@RAW{len(raw_store)}@@"
        raw_store.append((token, latex))
        return token

    def _cite(match: "re.Match[str]") -> str:
        number = int(match.group(1))
        if cite_map and number in cite_map:
            return _stash_raw(r"\hyperref[" + cite_map[number]
                              + r"]{[" + str(number) + r"]}")
        return f"[{number}]"

    text = re.sub(
        r'<a\s+class="cite"\s+href="[^"]*#r(\d+)"\s*>\[\d+\]</a>',
        _cite, text)

    # ---- 3. block structure ----------------------------------------------
    # Lists become itemize/enumerate. Done before <p> so that a <p> inside a
    # list item does not open a paragraph break mid-item.
    text = re.sub(r"<ul[^>]*>", "@@BEGINITEMIZE@@", text)
    text = text.replace("</ul>", "@@ENDITEMIZE@@")
    text = re.sub(r"<ol[^>]*>", "@@BEGINENUM@@", text)
    text = text.replace("</ol>", "@@ENDENUM@@")
    text = re.sub(r"<li[^>]*>", "@@ITEM@@", text)
    text = text.replace("</li>", "")

    text = re.sub(r"<p[^>]*>", "", text)
    text = text.replace("</p>", "@@PAR@@")

    # ---- 4. inline formatting -------------------------------------------
    # Monospace spans and <code> become \texttt. The content may contain
    # characters that must still be escaped, which happens in step 6.
    text = re.sub(r'<span\s+class="mono"\s*>(.*?)</span>',
                  r"@@TT{\1}@@", text, flags=re.S)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"@@TT{\1}@@", text, flags=re.S)

    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"@@BF{\1}@@", text, flags=re.S)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"@@BF{\1}@@", text, flags=re.S)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"@@IT{\1}@@", text, flags=re.S)
    text = re.sub(r"<i[^>]*>(.*?)</i>", r"@@IT{\1}@@", text, flags=re.S)
    text = re.sub(r"<s[^>]*>(.*?)</s>", r"@@ST{\1}@@", text, flags=re.S)
    text = re.sub(r"<sup[^>]*>(.*?)</sup>", r"@@SUP{\1}@@", text, flags=re.S)
    text = re.sub(r"<sub[^>]*>(.*?)</sub>", r"@@SUB{\1}@@", text, flags=re.S)

    # External links: keep the text, footnote the URL. A printed document
    # cannot be clicked, so the URL has to be on the page somewhere.
    def _link(match: "re.Match[str]") -> str:
        href, label = match.group(1), match.group(2)
        if href.startswith(("http://", "https://")):
            return f"@@URLLINK{{{label}}}{{{href}}}@@"
        return label        # internal page link: drop it, keep the words

    text = re.sub(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', _link,
                  text, flags=re.S)

    # ---- 5. drop every remaining tag, keeping its text -------------------
    text = re.sub(r"<[^>]+>", "", text)

    # ---- 6. entities, then escaping --------------------------------------
    text = resolve_entities(text)
    text = escape_latex(text)

    # ---- 7. rebuild the LaTeX from the placeholders ----------------------
    # The placeholders were written with braces, which step 6 escaped, so the
    # patterns below match the escaped forms.
    text = re.sub(r"@@TT\\\{(.*?)\\\}@@", r"\\texttt{\1}", text, flags=re.S)
    text = re.sub(r"@@BF\\\{(.*?)\\\}@@", r"\\textbf{\1}", text, flags=re.S)
    text = re.sub(r"@@IT\\\{(.*?)\\\}@@", r"\\textit{\1}", text, flags=re.S)
    text = re.sub(r"@@ST\\\{(.*?)\\\}@@", r"\\sout{\1}", text, flags=re.S)
    text = re.sub(r"@@SUP\\\{(.*?)\\\}@@", r"\\textsuperscript{\1}", text, flags=re.S)
    text = re.sub(r"@@SUB\\\{(.*?)\\\}@@", r"\\textsubscript{\1}", text, flags=re.S)
    text = re.sub(r"@@URLLINK\\\{(.*?)\\\}\\\{(.*?)\\\}@@",
                  lambda m: m.group(1) + r"\footnote{\url{"
                            + m.group(2).replace(r"\_", "_")
                                        .replace(r"\&", "&")
                                        .replace(r"\%", "%")
                                        .replace(r"\#", "#") + r"}}",
                  text, flags=re.S)

    text = text.replace("@@BEGINITEMIZE@@", "\n\\begin{itemize}\n")
    text = text.replace("@@ENDITEMIZE@@", "\n\\end{itemize}\n")
    text = text.replace("@@BEGINENUM@@", "\n\\begin{enumerate}\n")
    text = text.replace("@@ENDENUM@@", "\n\\end{enumerate}\n")
    text = text.replace("@@ITEM@@", "\n  \\item ")
    text = text.replace("@@PAR@@", "\n\n")

    # ---- 8. restore stashed LaTeX and mathematics -----------------------
    for token, latex in raw_store:
        text = text.replace(token, latex)

    for token, body in math_store:
        if token in display_tokens:
            replacement = "\n\\[" + body + "\\]\n"
        else:
            replacement = "$" + body + "$"
        text = text.replace(token, replacement)

    # ---- 9. let long identifiers break ----------------------------------
    text = allow_identifier_breaks(text)

    # ---- 10. tidy whitespace --------------------------------------------
    # \item followed by a blank line starts a new paragraph inside the item,
    # which looks wrong; collapse those.
    text = re.sub(r"\\item\s*\n\s*\n", r"\\item ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_tags(fragment: str) -> str:
    r"""Return the plain text of an HTML fragment, escaped for LaTeX.

    Used for table cells and captions, where the full block converter would
    introduce paragraph breaks that a cell cannot contain.

    A symbol column sometimes lists several symbols in one inline-math run
    (``$n_{\ell},\,n_{kv},\,d_{h}$``).  TeX will not break a math list at a
    comma, so such a cell runs past the column; an explicit ``\allowbreak``
    after each thin space gives it somewhere to wrap.
    """
    text = html_to_latex(fragment).replace("\n\n", " ").strip()
    return text.replace(r",\,", r",\,\allowbreak ")


def _spell(number: int) -> str:
    """Spell a small count in words, as the prose around it needs.

    Only the range this document actually uses is covered; anything larger
    falls back to the digits, which reads acceptably in a sentence such as
    "21 relations" and is better than a wrong word.
    """
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
             6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
             11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
             15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
             19: "nineteen", 20: "twenty"}
    return words.get(number, str(number))


# %% Equation rendering ------------------------------------------------------
def pdf_safe_heading(title: str) -> str:
    r"""Wrap a heading so its PDF-outline form survives dash ligaturing.

    ``hyperref`` builds an outline entry by expanding the heading through
    ``\pdfstringdef``, which emulates TeX's dash ligatures: a command-line
    flag such as ``--n-gpu-layers`` arrives in the bookmark as
    ``–n-gpu-layers``, with an en dash where the reader needs two hyphen
    characters they can retype.  Measured on this toolchain:
    ``\texorpdfstring`` with ``\string-\string-`` does **not** help (it
    still ligatures), but an empty group between the hyphens does, so the
    PDF-string form is written with ``-{}-``.

    Parameters
    ----------
    title : str
        The heading as LaTeX, which may contain ``\texttt{--flag}``.

    Returns
    -------
    str
        The heading unchanged when it holds no double hyphen, otherwise a
        ``\texorpdfstring`` whose typeset form is the original and whose
        PDF-string form keeps the hyphens literal.
    """
    if "--" not in title:
        return title
    # The PDF-string form carries no markup: strip the LaTeX commands,
    # keeping their arguments, then break each dash pair with an empty group.
    plain = re.sub(r"\\(?:texttt|textbf|textit|textsf|mono)\{([^{}]*)\}",
                   r"\1", title)
    plain = plain.replace("--", "-{}-")
    return r"\texorpdfstring{" + title + "}{" + plain + "}"


def equation_block(slug: str, html: str, cite_map: Dict[int, str]) -> str:
    """Render one equation from ``eq_library`` as a LaTeX subsection.

    The HTML block has a fixed shape (see ``eq_library``'s docstring), so it
    is parsed by targeted regex rather than a DOM walk: title, provenance
    pill, display math, note, optional derivation list and variable table.

    Parameters
    ----------
    slug : str
        The equation's registry key, used to build its LaTeX label.
    html : str
        The equation block's HTML.
    cite_map : dict
        Reference number to LaTeX label, for citations in the prose.

    Returns
    -------
    str
        LaTeX for one equation: a subsection, the display math, the note,
        the derivation and the variable table.
    """
    out: List[str] = []

    title_m = re.search(r'<h3 class="eq-title">(.*?)</h3>', html, re.S)
    title = strip_tags(title_m.group(1)) if title_m else slug

    pill_m = re.search(r'<span class="pill (\w+)">(.*?)</span>', html)
    pill = pill_m.group(2) if pill_m else ""
    pill_kind = pill_m.group(1) if pill_m else "stated"

    # The subsection, plus a bookmark at the deepest level so every equation
    # is individually reachable from the PDF outline.
    out.append(r"\subsection{" + pdf_safe_heading(title) + r"}\label{eq:"
               + slug + "}")
    out.append(r"\provenance{" + pill_kind + r"}{" + pill + r"}")

    body_m = re.search(r'<div class="eq-body">(.*?)</div>', html, re.S)
    if body_m:
        math = re.search(r"\\\[(.*?)\\\]", body_m.group(1), re.S)
        if math:
            out.append(r"\begin{equation}")
            out.append(math.group(1).strip())
            out.append(r"\end{equation}")

    note_m = re.search(r'<p class="eq-note">(.*?)</p>', html, re.S)
    if note_m:
        out.append(html_to_latex(note_m.group(1), cite_map=cite_map))

    # Derivation: required whenever the pill reads "Derived here".
    deriv_m = re.search(r'<div class="deriv">(.*?)</div>', html, re.S)
    if deriv_m:
        out.append(r"\begin{derivation}")
        out.append(html_to_latex(deriv_m.group(1), cite_map=cite_map))
        out.append(r"\end{derivation}")

    # Variable table. Printed unconditionally: on screen it is behind a
    # disclosure button, but a printed equation with no symbol definitions is
    # useless, which is why the print stylesheet expands them too.
    vars_m = re.search(r'<div class="vars" id="[^"]*" hidden>(.*?)</div>\s*</div>\s*$',
                       html, re.S)
    if not vars_m:
        vars_m = re.search(r'<div class="vars"[^>]*>(.*?)$', html, re.S)
    if vars_m:
        # All three columns are given explicit widths. With bare `l`
        # columns the symbol and unit cells take their natural width and a
        # long unit ("tokens s^-1 per worker") pushed the table 41pt past
        # the right margin -- an `l` column cannot wrap, so it cannot be
        # made to fit.
        table = _table_to_latex(
            vars_m.group(1), cite_map,
            colspec=r"@{}p{0.13\linewidth} p{0.55\linewidth} "
                    r"p{0.24\linewidth}@{}")
        if table:
            out.append(table)

    return "\n".join(out)


def _table_to_latex(fragment: str, cite_map: Dict[int, str],
                    colspec: Optional[str] = None) -> str:
    """Convert one HTML ``<table>`` to a LaTeX ``longtable``.

    ``longtable`` rather than ``tabular`` because several of these tables run
    past a page, and a table that silently overflows the page is worse than
    one that breaks.  Column widths are given as a fraction of the line so
    cells wrap instead of running into the margin.

    Parameters
    ----------
    fragment : str
        HTML containing exactly one ``<table>``.
    cite_map : dict
        Reference number to LaTeX label.
    colspec : str, optional
        An explicit LaTeX column specification.  When omitted, one is derived
        from the header count, with the first column narrow and the rest
        sharing the remaining width.

    Returns
    -------
    str
        LaTeX, or an empty string when no table was found.
    """
    table_m = re.search(r"<table[^>]*>(.*?)</table>", fragment, re.S)
    if not table_m:
        return ""
    table = table_m.group(1)

    caption_m = re.search(r"<caption[^>]*>(.*?)</caption>", table, re.S)
    caption = strip_tags(caption_m.group(1)) if caption_m else ""

    header_cells = re.findall(r"<th[^>]*>(.*?)</th>", table, re.S)
    rows_html = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)

    body_rows: List[List[str]] = []
    for row in rows_html:
        if "<th" in row:
            continue
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if cells:
            body_rows.append([strip_tags(c) for c in cells])

    if not body_rows:
        return ""

    ncols = len(header_cells) or max(len(r) for r in body_rows)

    if colspec is None:
        # First column narrow (it is usually a key or a symbol), the rest
        # share what is left. p{} columns so long cells wrap.
        if ncols == 1:
            colspec = r"@{}p{0.95\linewidth}@{}"
        else:
            # The p{} widths must leave room for the inter-column gaps
            # (2 x \tabcolsep, about 0.026 of the line each), or a table with
            # many columns overruns: the five-column GPU tables sat 18pt past
            # the margin when the gaps were ignored.
            share = (0.93 - 0.026 * (ncols - 1)) / ncols
            colspec = "@{}" + " ".join(
                [r"p{%.3f\linewidth}" % (share * 0.8)]
                + [r"p{%.3f\linewidth}" % (share * 1.1)] * (ncols - 1)
            ) + "@{}"

    out: List[str] = [r"\begin{small}",
                      r"\begin{longtable}{" + colspec + "}"]
    if caption:
        out.append(r"\caption{" + caption + r"}\\")
    if header_cells:
        out.append(r"\toprule")
        out.append(" & ".join(r"\textbf{" + strip_tags(h) + "}"
                              for h in header_cells[:ncols]) + r" \\")
        out.append(r"\midrule")
        out.append(r"\endfirsthead")
        out.append(r"\toprule")
        out.append(" & ".join(r"\textbf{" + strip_tags(h) + "}"
                              for h in header_cells[:ncols]) + r" \\")
        out.append(r"\midrule")
        out.append(r"\endhead")
    out.append(r"\bottomrule")
    out.append(r"\endfoot")

    for row in body_rows:
        # Pad or truncate so every row has exactly ncols cells: a longtable
        # with a ragged row fails to compile, and a rowspan in the source
        # produces exactly that.
        cells = (row + [""] * ncols)[:ncols]
        out.append(" & ".join(cells) + r" \\")

    out.append(r"\end{longtable}")
    out.append(r"\end{small}")
    return "\n".join(out)


# %% Document assembly -------------------------------------------------------
def preamble(version: str, home_version: str, accessed: Sequence[str]) -> str:
    """Return the LaTeX preamble.

    Parameters
    ----------
    version : str
        The page set's version, for the title page and PDF metadata.
    home_version : str
        The homepage's own version.
    accessed : sequence of str
        The verification dates, newest last.

    Returns
    -------
    str
        Everything from ``\\documentclass`` to ``\\begin{document}``.
    """
    dates = ", ".join(accessed)
    return r"""% ===========================================================================
% AI_Local Reference -- generated document, do not edit by hand
% ---------------------------------------------------------------------------
% Author  : William W. Wallace
% Engine  : LuaLaTeX (required: fontspec and unicode-math need it)
% Source  : build_ai_local_pdf.py, from the same modules as the HTML pages
%
% Regenerate rather than edit:
%   python build_ai_local_pdf.py --modules ../src_modules --out ../../pdf
%
% Compile manually with:
%   lualatex AI_Local_Reference.tex   (twice, for refs and the outline)
% ===========================================================================
\documentclass[11pt,a4paper,oneside]{report}

% ---- Engine check ---------------------------------------------------------
% fontspec and unicode-math require LuaTeX or XeTeX. Failing here with a
% clear message beats several hundred lines of confusing font errors.
\usepackage{iftex}
\ifLuaTeX\else
  \ifXeTeX\else
    \errmessage{This document requires LuaLaTeX (or XeLaTeX). Run: lualatex AI_Local_Reference.tex}
  \fi
\fi

% ---- Page geometry --------------------------------------------------------
% Generous inner margin: the equation catalogue has wide variable tables, and
% a printed copy of this is likely to be punched or bound.
\usepackage[a4paper,margin=22mm,top=24mm,bottom=24mm,
            headheight=14pt,footskip=14mm]{geometry}

% ---- Fonts ----------------------------------------------------------------
% DejaVu is used because it is present on this build host and covers the
% symbols these pages use. Latin Modern Math sets the mathematics.
\usepackage{fontspec}
\usepackage{unicode-math}
\setmainfont{DejaVu Serif}[Scale=0.92]
\setsansfont{DejaVu Sans}[Scale=0.90]
\setmonofont{DejaVu Sans Mono}[Scale=0.84]
\setmathfont{Latin Modern Math}

\usepackage{amsmath}
\usepackage{microtype}

% ---- Tables ---------------------------------------------------------------
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
% Ragged-right in p{} columns: justified text in a narrow table column
% produces rivers and overfull boxes.
\usepackage{ragged2e}
\renewcommand{\arraystretch}{1.18}

% ---- Lists and rules ------------------------------------------------------
\usepackage{enumitem}
\setlist{nosep,leftmargin=*,topsep=3pt}
\usepackage[normalem]{ulem}   % \sout for struck-through text

% ---- Colour and callouts --------------------------------------------------
\usepackage{xcolor}
% The screen palette, carried over so the two outputs read as one document.
\definecolor{aiPrimary}{HTML}{0F5F66}
\definecolor{aiPrimarySoft}{HTML}{E3EFEF}
\definecolor{aiBlue}{HTML}{1C5B8F}
\definecolor{aiBlueSoft}{HTML}{E4EDF5}
\definecolor{aiOrange}{HTML}{A8560C}
\definecolor{aiOrangeSoft}{HTML}{F6EBDF}
\definecolor{aiViolet}{HTML}{5A3F8F}
\definecolor{aiVioletSoft}{HTML}{ECE7F6}
\definecolor{aiRed}{HTML}{A3242E}
\definecolor{aiRedSoft}{HTML}{F8E5E6}
\definecolor{aiRule}{HTML}{D6D2C9}
\definecolor{aiMuted}{HTML}{5F5C55}

\usepackage[breakable,skins]{tcolorbox}

% A provenance tag, mirroring the coloured pill on the web pages. Printed
% above each equation so the reader knows at a glance whether the result was
% quoted from a source or derived on these pages.
\newcommand{\provenance}[2]{%
  \nopagebreak\par\vspace{-2pt}%
  {\footnotesize\sffamily\bfseries
   \ifthenelse{\equal{#1}{derived}}{\color{aiOrange}}{%
   \ifthenelse{\equal{#1}{data}}{\color{aiViolet}}{\color{aiBlue}}}%
   \MakeUppercase{#2}}\par\vspace{2pt}%
}
\usepackage{ifthen}

% The derivation environment. Every "Derived here" result carries one, and
% the left rule makes it scannable in a document read mostly by jumping
% around rather than front to back.
\newenvironment{derivation}{%
  \begin{tcolorbox}[breakable,enhanced,
    colback=aiOrangeSoft!40,colframe=aiOrange,
    boxrule=0pt,leftrule=2.2pt,arc=1pt,
    left=8pt,right=6pt,top=5pt,bottom=5pt,
    before skip=7pt, after skip=8pt]%
  {\footnotesize\sffamily\bfseries\color{aiOrange}DERIVATION}\par\vspace{2pt}%
}{\end{tcolorbox}}

% ---- Headings -------------------------------------------------------------
\usepackage{titlesec}
% Headings are set ragged right. A justified display heading stretches the
% word spaces of a two-word line across the measure, and at \Huge there is
% often no break TeX can take at all: "Settings that decide whether this
% works" ran 13pt into the margin while justified.
\titleformat{\chapter}[display]
  {\sffamily\bfseries\Large\color{aiPrimary}\RaggedRight}
  {\MakeUppercase{\chaptertitlename}\ \thechapter}{8pt}{\Huge}
\titlespacing*{\chapter}{0pt}{0pt}{18pt}
\titleformat{\section}
  {\sffamily\bfseries\Large\color{aiPrimary}\RaggedRight}
  {\thesection}{0.6em}{}
\titleformat{\subsection}
  {\sffamily\bfseries\large\RaggedRight}{\thesubsection}{0.6em}{}
\titleformat{\subsubsection}
  {\sffamily\bfseries\normalsize\RaggedRight}{\thesubsubsection}{0.6em}{}

% ---- Running heads --------------------------------------------------------
\usepackage{fancyhdr}
\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\sffamily\color{aiMuted}AI\_Local Reference v""" + version + r"""}
\fancyhead[R]{\footnotesize\sffamily\color{aiMuted}\leftmark}
\fancyfoot[C]{\footnotesize\sffamily\thepage}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\headrule}{\hbox to\headwidth{\color{aiRule}\leaders\hrule height \headrulewidth\hfill}}

% ---- Code listings --------------------------------------------------------
\usepackage{listings}
\lstset{
  basicstyle=\ttfamily\scriptsize,
  breaklines=true,
  breakatwhitespace=false,
  columns=fullflexible,
  keepspaces=true,
  frame=leftline,
  framerule=1.6pt,
  rulecolor=\color{aiRule},
  framesep=7pt,
  xleftmargin=10pt,
  aboveskip=8pt, belowskip=8pt,
  showstringspaces=false,
  % The snippets are PowerShell, bash, YAML, JSON, TOML and Dockerfile mixed
  % together, so no single language setting fits. Plain text with sensible
  % breaking is more honest than a wrong highlighter.
  language=
}

% ---- Hyperlinks and the PDF outline --------------------------------------
% bookmarksnumbered so the outline carries the same numbering as the body;
% bookmarksopen to 2 levels so the tree is useful on first open without
% being a wall of entries. bookmark (loaded after hyperref) rebuilds the
% outline reliably and is what makes \bookmark available for the per-
% reference entries in Part V.
\usepackage[
  unicode=true,
  bookmarks=true,
  bookmarksnumbered=true,
  bookmarksopen=true,
  bookmarksopenlevel=2,
  breaklinks=true,
  colorlinks=true,
  linkcolor=aiPrimary,
  urlcolor=aiBlue,
  citecolor=aiPrimary
]{hyperref}
\usepackage{bookmark}
\usepackage{url}
% xurl lets a URL break after any character. Plain url breaks only at
% slashes and a few punctuation marks, so a long hyphenated article slug ran
% 457pt into the margin in the first v0.0.6 build.
\usepackage{xurl}

% Document metadata. Set with \hypersetup rather than as package options:
% in the option list the value is read with normal catcodes and an
% underscore is silently DROPPED, which produced a PDF titled
% "AILocal Reference" created by "buildailocalpdf.py". Inside \hypersetup
% the value goes through \pdfstringdef, where \_ expands to a real
% underscore. Verify after any change by reading /Title back out of the
% finished PDF -- the error is invisible in the typeset page.
\hypersetup{
  pdftitle={AI\_Local Reference},
  pdfauthor={William W. Wallace},
  pdfsubject={Deploying language models across a home or lab network:
              serving, distributing, monitoring, and local code generation
              and test},
  pdfkeywords={local AI, Ollama, Open WebUI, llama.cpp, Prometheus, Grafana,
               mamba, RF engineering},
  pdfcreator={build\_ai\_local\_pdf.py 0.0.2 (LuaLaTeX)}
}

% Deeper outline for the equation and reference catalogues.
\bookmarksetup{depth=4}

% ---- Spacing --------------------------------------------------------------
\setlength{\parskip}{5pt}
\setlength{\parindent}{0pt}
\linespread{1.06}
% Tables and equations should not be split from the text that introduces
% them more than necessary.
\widowpenalty=9000
\clubpenalty=9000
% Last-resort stretch. When a paragraph holds a long unbreakable run -- a
% URL, a flag, a file path -- TeX would rather overrun the right margin
% than loosen the word spacing. \emergencystretch gives it a final pass
% with extra give, so the line sets slightly loose instead of sticking out
% into the margin, which is the lesser of the two.
\setlength{\emergencystretch}{3em}

% ===========================================================================
\begin{document}
% ===========================================================================

\begin{titlepage}
\centering
\vspace*{3.2cm}
{\sffamily\bfseries\Huge\color{aiPrimary} AI\_Local}\\[6pt]
{\sffamily\LARGE Reference Manual}\\[22pt]
{\large Deploying language models across a home or lab network:\\
serving, distributing, monitoring, and local code generation and test}\\[30pt]
\rule{0.55\linewidth}{0.6pt}\\[14pt]
{\large William W. Wallace}\\[4pt]
{\small\ttfamily adaptive.electrodynamics@gmail.com}\\[22pt]
{\small Page set version \textbf{""" + version + r"""} \quad$\cdot$\quad
 Homepage version \textbf{""" + home_version + r"""}}\\[5pt]
{\small Sources verified: """ + dates + r"""}\\[26pt]
\begin{minipage}{0.80\linewidth}
\small
\textbf{How to read this document.} Every relation carries a provenance tag.
\textsc{stated} means the result is quoted from a cited source with no
algebra applied; \textsc{derived here} means the algebra was performed on
these pages and is shown in full in the derivation box that follows; and
\textsc{measured value} marks a tabulated experimental figure. Each relation
is followed by a table defining every symbol in it, with units. Bracketed
numbers link to the numbered reference list in Part~\ref{part:refs}, which
also records how far each source can be leaned on, and lists separately the
figures that are planning estimates rather than citations.

\vspace{6pt}
\textbf{This document is generated.} It and the HTML page set are built from
the same source modules, so an equation, a reference or a model figure exists
in exactly one place. Do not edit this file; regenerate it.
\end{minipage}
\vfill
{\footnotesize\sffamily\color{aiMuted}Generated by build\_ai\_local\_pdf.py with LuaLaTeX}
\end{titlepage}

\pdfbookmark[0]{Contents}{toc}
\tableofcontents
\clearpage
"""


def build_document(mods, out_dir: Path) -> str:
    """Assemble the complete LaTeX source.

    Parameters
    ----------
    mods : SimpleNamespace
        The imported source modules.
    out_dir : Path
        Where the document will be written, used only for messages.

    Returns
    -------
    str
        The whole ``.tex`` file.
    """
    refs = mods.references
    eq = mods.eq_library
    cat = mods.model_catalog
    inv = mods.repo_inventory
    meta = mods.page_meta

    refs.validate()
    cat.validate()

    # Reference number to LaTeX label, so a citation in the prose becomes a
    # working internal hyperlink in the PDF.
    cite_map = {num: f"ref:{num}" for num, _c, _k, _u in refs.REFS}

    dates = [refs.ACCESSED]
    for attr in ("RECHECKED", "RECHECKED_2", "RECHECKED_3"):
        if hasattr(refs, attr):
            dates.append(getattr(refs, attr))

    doc: List[str] = [preamble(meta.current_version(), inv.HOME_VERSION, dates)]

    # ---- Part I: the setup path ----------------------------------------
    # Generated from site_flow.STEPS, the same definition the start page and
    # every page's step bar use, so the printed order cannot differ from the
    # site's.  (v0.0.1 of this script printed the repository-wide stages from
    # repo_inventory instead; the AI_Local set now has its own path.)
    flow = mods.site_flow
    sw = mods.software_catalog
    doc.append(r"\part{The setup path}\label{part:flow}")
    doc.append(r"\chapter{" + str(len(flow.STEPS)) + r" steps, in order}")
    doc.append(r"""
Each step produces what the next one needs, so the order is a dependency chain
rather than a preference. Every step ends with a check; if it does not pass,
the next step will fail in a way that is harder to diagnose. Times are
estimates, not measurements.""")

    for index, step in enumerate(flow.STEPS, start=1):
        doc.append(r"\section{Step " + str(index) + ": " + escape_latex(step.title)
                   + r"}\label{step:" + step.key + "}")
        doc.append(r"\begin{description}[leftmargin=6.2em,style=nextline,"
                   r"font=\normalfont\sffamily\bfseries\small]")
        doc.append(r"\item[Goal] " + strip_tags(step.goal))
        doc.append(r"\item[Done when] " + strip_tags(step.done_when))
        tiers = []
        for tier in flow.TIERS:
            if tier in step.applies:
                label = flow.TIER_LABEL[tier].lower()
                tiers.append(label + (" (optional)" if tier in step.optional_for else ""))
        doc.append(r"\item[Applies to] " + escape_latex(", ".join(tiers)))
        doc.append(r"\item[Time] " + strip_tags(step.time) + " (estimate)")
        doc.append(r"\item[Page] \texttt{" + escape_latex(step.page) + "}")
        if step.alternatives:
            doc.append(r"\item[Alternatives] " + "; ".join(
                escape_latex(a.label) + r" (\texttt{" + escape_latex(a.page) + "}), if "
                + escape_latex(a.when) for a in step.alternatives))
        programs = sw.for_step(step.key)
        if programs:
            # The names link to their rows in the software chapter.  A
            # \ref to those labels would print the TABLE number (every row
            # sits in one longtable), so every program read "5.1".
            doc.append(r"\item[Software] " + ", ".join(
                r"\hyperref[sw:" + prog.key + "]{" + strip_tags(prog.name) + "}"
                for prog in programs)
                + r" (Chapter~\ref{ch:software})")
        doc.append(r"\end{description}")

    # ---- Part II: the equation catalogue --------------------------------
    doc.append(r"\part{Equation catalogue}\label{part:eq}")
    # The count is taken from the registry rather than written into the
    # prose. A hardcoded "Sixteen relations" was already wrong by one when
    # this was first drafted, and a sentence that miscounts the thing it
    # introduces undermines a document whose whole claim is that it cannot
    # drift from its source.
    doc.append(r"\chapter{Relations, derivations and symbol definitions}")
    doc.append(r"""
These are the relations the rest of the set depends on. Each is tagged with
its provenance, each derived result shows its steps, and each is followed by
a table defining every symbol with its unit. On the web pages the symbol
tables sit behind a disclosure button; here they are always printed, because
an equation without its definitions is not usable on paper.
""")
    doc.append(_spell(len(eq.EQUATIONS)).capitalize() + r""" relations,
grouped as they are in the source: model footprint and memory first, then
throughput and distribution, then build and agent-loop timing, then
monitoring.""")

    # Group the equations the way eq_library groups them internally, so the
    # printed order matches the module and a reader moving between them is
    # not reordered.
    groups: List[Tuple[str, List[str]]] = [
        ("Model footprint and memory",
         ["quant-footprint", "moe-active", "kv-cache", "ctx-budget"]),
        ("Throughput and distribution",
         ["bandwidth-bound", "ngl-layers", "rpc-token-time", "rpc-breakeven"]),
        ("Build and agent-loop timing",
         ["parallel-jobs", "amdahl", "agent-loop"]),
        ("Monitoring and telemetry",
         ["prom-disk", "prom-ingest", "rate-window", "gpu-utilisation"]),
        ("GPU placement",
         ["fit-margin", "moe-cpu-offload", "tensor-split"]),
    ]
    covered = {slug for _t, slugs in groups for slug in slugs}
    leftover = [s for s in eq.EQUATIONS if s not in covered]
    if leftover:
        groups.append(("Further relations", leftover))

    # Groups are sections of the one chapter, not chapters of their own.
    # As chapters with \subsection equations and no \section between, the
    # numbering came out "3.0.1", which looks like a defect in the document
    # and makes a cross-reference ambiguous.
    for heading, slugs in groups:
        doc.append(r"\section{" + heading + "}")
        for slug in slugs:
            if slug in eq.EQUATIONS:
                doc.append(equation_block(slug, eq.EQUATIONS[slug], cite_map))

    # ---- Part III: the model catalogue ----------------------------------
    doc.append(r"\part{Model catalogue}\label{part:models}")
    doc.append(r"""
\chapter{The shortlist}

Every model here carries tool-calling support, which is the hard gate: a
model that cannot call a tool cannot drive a build however good its code is.
Figures are those published on each model's distribution page on the date in
the reference list. Model pages are revised in place, so re-read a tag before
buying hardware on the strength of it.
""")
    doc.append(_model_table(cat))

    doc.append(r"\section{Fit by VRAM budget}")
    doc.append(r"""
Derived from the catalogue by the same rule the homepage planner applies: a
model fits when its weight file, the runtime reservation and at least 1\,GB
of cache all sit on the card. A model that is resident but cannot hold a
useful prompt is not a fit.
""")
    doc.append(_fit_table(cat))

    # ---- Part IV: configuration reference -------------------------------
    doc.append(r"\part{Configuration reference}\label{part:config}")
    doc.append(r"""
\chapter{Settings that decide whether this works}

Extracted from the page set. Every name is quoted from the vendor
documentation cited beside it; where a default is stated, it is the
documented default and not an assumption.
""")
    doc.append(_config_tables(mods, cite_map))
    doc.append(_software_chapter(mods, cite_map))

    # ---- Part V: references ---------------------------------------------
    doc.append(r"\part{References}\label{part:refs}")
    doc.append(_reference_list(refs))

    doc.append(r"\end{document}")
    return "\n\n".join(doc)


def _model_table(cat) -> str:
    """Render the model catalogue as a longtable."""
    rows: List[str] = []
    for m in cat.MODELS:
        caps = ", ".join(m.capabilities) if m.capabilities else "--"
        moe = (f"{m.total_params_b:g}B total / {m.active_params_b:g}B active"
               if getattr(m, "is_moe", False) else "dense")
        rows.append(" & ".join([
            r"\texttt{" + escape_latex(m.tag) + "}",
            escape_latex(m.size_display()),
            escape_latex(f"{m.context:,}"),
            escape_latex(str(m.quant)),
            escape_latex(caps),
            escape_latex(moe),
            f"[{m.reference}]",
        ]) + r" \\")

    return "\n".join([
        r"\begin{small}",
        r"\begin{longtable}{@{}p{0.185\linewidth} l r p{0.105\linewidth} "
        r"p{0.135\linewidth} p{0.165\linewidth} l@{}}",
        r"\caption{Tool-calling code and agent models, with the figures "
        r"published on each model's distribution page. Context is in tokens. "
        r"The Architecture column distinguishes a dense model, whose whole "
        r"weight set is read per token, from a routed mixture of experts, "
        r"which occupies the card like its total size and streams like its "
        r"active subset.}\\",
        r"\toprule",
        r"\textbf{Tag} & \textbf{Size} & \textbf{Context} & \textbf{Quant} & "
        r"\textbf{Capabilities} & \textbf{Architecture} & \textbf{Ref.} \\",
        r"\midrule \endfirsthead",
        r"\toprule",
        r"\textbf{Tag} & \textbf{Size} & \textbf{Context} & \textbf{Quant} & "
        r"\textbf{Capabilities} & \textbf{Architecture} & \textbf{Ref.} \\",
        r"\midrule \endhead",
        r"\bottomrule \endfoot",
        *rows,
        r"\end{longtable}",
        r"\end{small}",
    ])


def _fit_table(cat) -> str:
    """Render the VRAM fit ladder, computed from the catalogue."""
    rows: List[str] = []
    for vram in (8, 12, 16, 24, 32, 48, 64, 96):
        fitting = cat.for_vram(vram)
        if fitting:
            best = fitting[0]
            headroom = vram - best.size_gb - cat.RUNTIME_VRAM_GB
            rows.append(" & ".join([
                f"{vram}",
                str(len(fitting)),
                r"\texttt{" + escape_latex(best.tag) + "}",
                escape_latex(best.size_display()),
                f"{headroom:.1f}",
            ]) + r" \\")
        else:
            rows.append(f"{vram} & 0 & \\textit{{nothing fits}} & -- & -- \\\\")

    return "\n".join([
        r"\begin{small}",
        r"\begin{longtable}{@{}r r p{0.30\linewidth} l r@{}}",
        r"\caption{Models that fit each VRAM budget, computed from the "
        r"catalogue. Headroom is what remains for the key/value cache after "
        r"the weights and the runtime reservation, in GB. The largest model "
        r"that fits is not automatically the right choice: a smaller one "
        r"leaves more room for context, and context is what an agent loop "
        r"consumes.}\\",
        r"\toprule",
        r"\textbf{VRAM (GB)} & \textbf{Fit} & \textbf{Largest that fits} & "
        r"\textbf{Size} & \textbf{Headroom} \\",
        r"\midrule \endfirsthead",
        r"\toprule",
        r"\textbf{VRAM (GB)} & \textbf{Fit} & \textbf{Largest that fits} & "
        r"\textbf{Size} & \textbf{Headroom} \\",
        r"\midrule \endhead",
        r"\bottomrule \endfoot",
        *rows,
        r"\end{longtable}",
        r"\end{small}",
    ])


def _software_chapter(mods, cite_map: Dict[int, str]) -> str:
    """Software inventory and the corrections log, from their data modules.

    Two chapters in Part IV.  The inventory is ``software_catalog.SOFTWARE``
    as a longtable, one labelled row per program so Part I can cross-refer to
    it.  The corrections log lists every exact-span change made to the
    earlier pages (``legacy_corrections.CORRECTIONS``), so a printed copy
    records what was changed in pages it does not itself reproduce.
    """
    sw = mods.software_catalog
    out: List[str] = [r"\chapter{Software and downloads}\label{ch:software}", r"""
Every program the deployment uses, with its original creator's download page.
\emph{In the folder} is what the deployment folder held on """ + sw.VERIFIED + r""";
\emph{Current} is the newest release on that date, read from the publisher.
Rows marked \textsc{not in repo} must be fetched from the publisher by anyone
cloning the repository."""]
    repo_label = {"yes": "in repo", "no": r"\textsc{not in repo}",
                  "partial": r"\textsc{partly in repo}", "n/a": "publisher"}
    rows: List[str] = []
    for prog in sw.SOFTWARE:
        name = (r"\textbf{" + strip_tags(prog.name) + r"}\label{sw:" + prog.key + r"}"
                + (r" \emph{(optional)}" if not prog.required else "")
                + r"\newline{\footnotesize " + escape_latex(prog.publisher) + r"}")
        folder = (escape_latex(prog.in_folder) if prog.in_folder else "--")
        current = (strip_tags(prog.current) if prog.current else r"\emph{not checked}")
        url = prog.download.replace("%", r"\%").replace("#", r"\#")
        rows.append(name + " & " + strip_tags(prog.role) + r"\newline{\footnotesize\url{"
                    + url + r"}} & " + folder + r"\newline{\footnotesize "
                    + repo_label[prog.in_repo] + r"} & " + current
                    + r" \hyperref[ref:" + str(prog.ref) + r"]{[" + str(prog.ref) + r"]} \\")
    out.append("\n".join([
        r"\begin{small}",
        r"\begin{longtable}{@{}p{0.20\linewidth} p{0.36\linewidth} p{0.18\linewidth} p{0.18\linewidth}@{}}",
        r"\caption{Programs in the deployment, with download sources and versions.}\\",
        r"\toprule \textbf{Program} & \textbf{Role and download} & \textbf{In the folder} & \textbf{Current} \\ \midrule \endfirsthead",
        r"\toprule \textbf{Program} & \textbf{Role and download} & \textbf{In the folder} & \textbf{Current} \\ \midrule \endhead",
        r"\bottomrule \endfoot",
        *rows,
        r"\end{longtable}",
        r"\end{small}"]))

    lc = mods.legacy_corrections
    out.append(r"\chapter{Corrections made to the earlier pages}")
    out.append(r"""
The pages that predate this set are retrofitted rather than rewritten. Where
their content could not work as written, one exact span of the original page
was replaced, and the replacement is marked on the page. Each row below is one
such replacement, from \texttt{src\_modules/legacy\_corrections.py}.""")
    rows = []
    for c in lc.CORRECTIONS:
        refs_txt = ", ".join(r"\hyperref[ref:" + str(n) + r"]{[" + str(n) + "]}" for n in c.refs) or "--"
        rows.append(r"\texttt{" + allow_identifier_breaks(escape_latex(c.key)) + r"} & \texttt{"
                    + allow_identifier_breaks(escape_latex(c.page))
                    + r"} & " + escape_latex(c.why) + " & " + refs_txt + r" \\")
    out.append("\n".join([
        r"\begin{small}",
        r"\begin{longtable}{@{}p{0.18\linewidth} p{0.26\linewidth} p{0.29\linewidth} p{0.17\linewidth}@{}}",
        r"\caption{Exact-span corrections applied to the earlier pages in v0.0.6.}\\",
        r"\toprule \textbf{Key} & \textbf{Page} & \textbf{Why} & \textbf{Refs} \\ \midrule \endfirsthead",
        r"\toprule \textbf{Key} & \textbf{Page} & \textbf{Why} & \textbf{Refs} \\ \midrule \endhead",
        r"\bottomrule \endfoot",
        *rows,
        r"\end{longtable}",
        r"\end{small}"]))
    return "\n\n".join(out)


def _config_tables(mods, cite_map: Dict[int, str]) -> str:
    """Pull the settings tables out of the generated page bodies.

    Rather than maintaining a second copy of these tables, they are lifted
    from the page modules' own HTML by caption.  A table whose caption
    mentions a variable, a setting or a default is a configuration table.
    """
    wanted = re.compile(
        r"(variable|setting|environment|default|flag|option|condition)",
        re.I)

    out: List[str] = []
    # The GPU page is taken whole (filter None): every table on it is a
    # settings or compatibility table, and its captions do not all use the
    # words the filter looks for ("split modes", "exporters by vendor").
    for label, module, caption_filter in (
        ("GPU configuration", mods.page_gpu, None),
        ("Execution backends and environment", mods.page_local_build, wanted),
        ("Sandbox policy", mods.page_sandbox, wanted),
        ("Monitoring", mods.page_monitoring, wanted),
    ):
        body = module.build()
        tables = re.findall(r"<table[^>]*>.*?</table>", body, re.S)
        picked = [t for t in tables
                  if (m := re.search(r"<caption[^>]*>(.*?)</caption>", t, re.S))
                  and (caption_filter is None or caption_filter.search(m.group(1)))]
        if not picked:
            continue
        out.append(r"\section{" + label + "}")
        for table in picked:
            rendered = _table_to_latex(table, cite_map)
            if rendered:
                out.append(rendered)
    return "\n\n".join(out)


def _reference_list(refs) -> str:
    """Render the IEEE reference list, one PDF bookmark per entry."""
    conf_label = {"primary": "primary", "vendor": "vendor",
                  "derived": "derived", "secondary": "secondary"}

    out: List[str] = [r"\chapter{Numbered reference list}", r"""
IEEE style. Numbers are permanent: a retired reference keeps its number and a
new one takes the next free number, so a number written down elsewhere never
comes to mean something else. The confidence column records how far each
source can be leaned on. \textsc{primary} is a normative or first-party
specification; \textsc{vendor} is first-party but commercial and revised in
place, which every model card in this list is, so anything cited to one
should be re-read before hardware is bought on its strength.
"""]

    # Ragged right, which is the usual setting for a reference list and
    # also removes the cause of the remaining overfull lines: a citation is
    # mostly proper nouns and a long URL, so justification has very few
    # places to put the slack and overruns the margin instead.
    out.append(r"\begingroup\RaggedRight")
    out.append(r"\begin{description}[leftmargin=2.8em,style=sameline,"
               r"labelwidth=2.4em,itemsep=5pt]")
    for num, cite, _cat, url in sorted(refs.REFS, key=lambda e: e[0]):
        conf = conf_label.get(refs.CONFIDENCE.get(num, ""), "")
        # Each entry is assembled as ONE element joined by single newlines.
        # Appending its parts separately would put a blank line between the
        # citation and the URL, which ends the paragraph and makes the
        # following \\ an error ("There's no line here to end") -- LaTeX's
        # \\ needs a line in progress, and a blank line has already ended it.
        entry: List[str] = []
        # One bookmark per reference, so the outline is a usable index.
        entry.append(r"\bookmark[level=2,dest=ref:" + str(num) + "]{[" + str(num)
                     + "] " + _bookmark_safe(cite) + "}")
        entry.append(r"\item[\textbf{[" + str(num) + r"]}]\label{ref:" + str(num)
                     + "}%")
        entry.append(strip_tags(cite) + r"\newline")
        entry.append(r"{\footnotesize\url{" + url + r"}"
                     + (r"\quad$\cdot$\quad\textsc{" + conf + "}" if conf else "")
                     + r"}")
        out.append("\n".join(entry))
    out.append(r"\end{description}")
    out.append(r"\endgroup")

    # The uncited planning estimates, which must travel with the document.
    out.append(r"\chapter{Figures with no citation}")
    out.append(r"""
Some numbers in this document are not in any source, because no source
publishes them. They are planning estimates for this class of hardware,
listed here so they are not mistaken for cited facts. Each is stated as a
range at its point of use, and the relation that consumes it names it as an
estimate.

\begin{small}
\begin{longtable}{@{}p{0.30\linewidth} p{0.17\linewidth} p{0.43\linewidth}@{}}
\caption{Uncited planning estimates, with how to replace each with a
measurement taken on your own hardware.}\\
\toprule
\textbf{Quantity} & \textbf{Value used} & \textbf{How to measure it} \\
\midrule \endfirsthead
\toprule
\textbf{Quantity} & \textbf{Value used} & \textbf{How to measure it} \\
\midrule \endhead
\bottomrule \endfoot
GGUF container overhead $\varepsilon$ & 0.03--0.08 &
  Compare a published tag size against $P b_{q}/8$ for a model whose
  parameter count and quantisation you know \\
Throughput realisation factor $\eta$ & 0.5--0.8 &
  \texttt{probe\_model\_throughput.py}, then divide the measured rate by the
  computed bound \\
Runtime VRAM reservation $V_{\mathrm{rt}}$ & 0.8--1.5\,GB &
  \texttt{nvidia-smi} with a model loaded, minus the published weight size \\
Peak compiler resident set $M_{\mathrm{job}}$ & 1.5--2.5\,GB &
  Watch peak working set during a single-job build of your heaviest
  translation unit \\
Exporter series counts & $\sim$1500 / $\sim$120 &
  Query \texttt{prometheus\_tsdb\_head\_series} on your own server. The
  \texttt{llama-server} count is published and is not an estimate \\
Model architecture placeholders $n_{\ell}=48$, $n_{kv}=8$, $d_{h}=128$ &
  plausible shape only & \texttt{ollama show <tag>} \\
\end{longtable}
\end{small}
""")
    return "\n\n".join(out)


def _bookmark_safe(text: str) -> str:
    r"""Reduce a citation to text safe inside a PDF bookmark.

    A bookmark argument is expanded by ``\pdfstringdef``, which applies TeX
    catcodes before writing the string, so the characters LaTeX treats
    specially must still be escaped even though nothing is being typeset.
    Getting this wrong is quiet: an unescaped underscore is simply DROPPED,
    which turned ``nvidia_gpu_exporter`` into ``nvidiagpuexporter`` and
    ``GGML_RPC`` into ``GGMLRPC`` in the outline of an earlier build -- both
    of them names a reader is expected to type.  A dash pair needs the same
    treatment as a heading (see :func:`pdf_safe_heading`).

    Parameters
    ----------
    text : str
        An IEEE citation as HTML.

    Returns
    -------
    str
        Plain text, escaped for a PDF string and truncated to a length that
        keeps the outline readable.
    """
    plain = re.sub(r"<[^>]+>", "", text)
    plain = resolve_entities(plain)
    plain = re.sub(r"\s+", " ", plain)
    # Drop markup characters outright: they carry no meaning here.
    plain = plain.replace("\\", "").replace("{", "").replace("}", "")
    # Cut at the title, which is the useful part of an IEEE citation.
    plain = plain.split("[Online]")[0].strip().rstrip(".")
    plain = plain[:95]
    # Escape what \pdfstringdef would otherwise eat or misread.
    for char, replacement in (("_", r"\_"), ("&", r"\&"), ("%", r"\%"),
                              ("#", r"\#"), ("$", r"\$"),
                              ("~", r"\textasciitilde{}"),
                              ("^", r"\textasciicircum{}")):
        plain = plain.replace(char, replacement)
    return plain.replace("--", "-{}-")


# %% Compilation -------------------------------------------------------------
def compile_pdf(tex_path: Path, passes: int = 3) -> bool:
    """Run LuaLaTeX and report whether a PDF came out.

    Parameters
    ----------
    tex_path : Path
        The ``.tex`` file to compile.
    passes : int
        How many times to run.  Two is the minimum for cross-references and
        the outline, but two still ended with "Label(s) may have changed"
        because the longtables shift page breaks on the second pass and move
        the labels again; three settles it.  The run is checked for that
        warning afterwards rather than assumed.

    Returns
    -------
    bool
        True when a PDF exists afterwards.
    """
    engine = shutil.which("lualatex")
    if engine is None:
        print("  lualatex not found; wrote the .tex only", file=sys.stderr)
        return False

    for attempt in range(1, passes + 1):
        print(f"  lualatex pass {attempt}/{passes} ...", flush=True)
        result = subprocess.run(
            [engine, "-interaction=nonstopmode", "-halt-on-error",
             "-file-line-error", tex_path.name],
            cwd=tex_path.parent, capture_output=True, text=True)

        if result.returncode != 0:
            # Print the actual errors rather than the whole log: a LaTeX log
            # is thousands of lines and the useful part is the ! lines.
            print(f"  FAILED on pass {attempt} (exit {result.returncode})",
                  file=sys.stderr)
            lines = (result.stdout or "").splitlines()
            errors = [ln for ln in lines
                      if ln.startswith("!") or ":" in ln[:60] and "Error" in ln]
            for line in errors[:25]:
                print("    " + line, file=sys.stderr)
            if not errors:
                for line in lines[-25:]:
                    print("    " + line, file=sys.stderr)
            return False

    # Read the log rather than trusting the exit code. LaTeX exits 0 with
    # stale cross-references, an overfull line running into the margin, or
    # an undefined reference printed as "??" -- all of which are wrong on
    # the page and none of which fail the build.
    log = tex_path.with_suffix(".log")
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="replace")

        if "Rerun to get cross-references right" in text:
            print("  WARNING: cross-references had not settled after "
                  f"{passes} passes", file=sys.stderr)

        undefined = text.count("LaTeX Warning: Reference")
        if undefined:
            print(f"  WARNING: {undefined} undefined reference(s)",
                  file=sys.stderr)

        # Overfull boxes: anything over 2pt is visible in print. The count
        # is reported rather than failed on, because a long URL in a
        # reference entry cannot always be broken and a hard failure there
        # would be noise.
        overfull = re.findall(r"Overfull \\hbox \(([0-9.]+)pt", text)
        bad = [float(v) for v in overfull if float(v) > 2.0]
        if bad:
            print(f"  overfull lines: {len(bad)} over 2pt, "
                  f"worst {max(bad):.1f}pt")
        else:
            print("  overfull lines: none over 2pt")

    pdf = tex_path.with_suffix(".pdf")
    return pdf.exists()


def report_pdf(pdf: Path) -> None:
    """Print page count and outline depth, so the bookmarks are verified.

    A PDF that compiled is not necessarily a PDF with a usable outline, and
    the outline is the specific thing this document promises, so it is
    checked rather than assumed.
    """
    size = pdf.stat().st_size
    print(f"  {pdf.name}: {size:,} B ({size / 1048576:.2f} MiB)")

    # pdfinfo is part of poppler-utils and may not be installed; the raw
    # object scan below is the fallback and needs nothing.
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        out = subprocess.run([pdfinfo, str(pdf)], capture_output=True,
                             text=True).stdout
        for line in out.splitlines():
            if line.split(":")[0].strip() in {"Pages", "Title", "Author",
                                              "Subject", "Creator",
                                              "Producer", "PDF version"}:
                print("  " + line.strip())

    # Verify the OUTLINE, which is the specific thing this document
    # promises. Counting b"/Outlines" in the raw bytes does not work: a
    # PDF 1.5 file packs its objects into compressed object streams, so the
    # outline is real but invisible to a byte scan -- that check reported
    # "0 outline objects" for a PDF carrying 79 bookmarks. pypdf decompresses
    # and walks the tree, so it answers the question actually being asked.
    try:
        import pypdf
    except ImportError:
        print("  pypdf not installed; outline not verified")
        return

    reader = pypdf.PdfReader(str(pdf))
    meta = reader.metadata or {}

    def walk(items, depth: int = 0) -> Tuple[int, int]:
        """Return (bookmark count, deepest level) for an outline subtree."""
        count, deepest = 0, depth
        for item in items:
            if isinstance(item, list):
                sub_count, sub_depth = walk(item, depth + 1)
                count += sub_count
                deepest = max(deepest, sub_depth)
            else:
                count += 1
        return count, deepest

    total, depth = walk(reader.outline)
    print(f"  bookmarks: {total} across {depth + 1} outline levels")

    # The metadata underscore trap: hyperref drops an underscore given as a
    # package option, so the title is read back and checked rather than
    # assumed. A wrong title is invisible on the typeset page.
    title = str(meta.get("/Title", ""))
    creator = str(meta.get("/Creator", ""))
    print(f"  /Title   {title!r}")
    print(f"  /Creator {creator!r}")
    if "AI_Local" not in title:
        print("  WARNING: /Title lost its underscore -- check \\hypersetup",
              file=sys.stderr)

    if total == 0:
        print("  WARNING: the PDF has no outline", file=sys.stderr)


# %% Entry point -------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    """Generate the LaTeX source and, where possible, the PDF."""
    parser = argparse.ArgumentParser(
        description="Build the AI_Local reference manual as LuaLaTeX and PDF.")
    parser.add_argument("--modules", required=True, type=Path,
                        help="directory holding the page-content modules")
    parser.add_argument("--out", required=True, type=Path,
                        help="output directory for the .tex and .pdf")
    parser.add_argument("--tex-only", action="store_true",
                        help="write the .tex and skip compilation")
    parser.add_argument("--keep-aux", action="store_true",
                        help="keep .aux/.log/.out instead of removing them")
    args = parser.parse_args(argv)

    modules_dir = args.modules.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(modules_dir))
    from types import SimpleNamespace
    import importlib

    names = ["references", "eq_library", "model_catalog", "repo_inventory",
             "page_meta", "page_local_build", "page_models", "page_sandbox",
             "page_monitoring", "page_home", "page_gpu", "site_flow",
             "software_catalog", "legacy_corrections"]
    mods = SimpleNamespace(**{n: importlib.import_module(n) for n in names})

    print("=" * 74)
    print("AI_Local reference manual")
    print("=" * 74)

    source = build_document(mods, out_dir)
    tex_path = out_dir / "AI_Local_Reference.tex"
    tex_path.write_text(source, encoding="utf-8")
    print(f"  wrote {tex_path.name}: {len(source):,} chars, "
          f"{len(source.splitlines()):,} lines")

    if args.tex_only:
        print("  --tex-only: stopping before compilation")
        return 0

    if not compile_pdf(tex_path):
        return 1

    pdf = tex_path.with_suffix(".pdf")
    report_pdf(pdf)

    if not args.keep_aux:
        for suffix in (".aux", ".log", ".out", ".toc"):
            scratch = tex_path.with_suffix(suffix)
            if scratch.exists():
                scratch.unlink()

    print("-" * 74)
    print("PASSED: LuaLaTeX source and bookmarked PDF written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
