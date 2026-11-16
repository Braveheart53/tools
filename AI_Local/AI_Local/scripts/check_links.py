#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_links.py -- verify every outbound link in the AI_Local page set.

Author  : William W. Wallace
Version : 0.0.2
Created : 2026-11-15

PURPOSE
-------
The pages point readers at installers, vendor documentation and source
repositories.  Those targets move: a GitHub project is renamed, an exporter is
deprecated in favour of another, a documentation tree is reorganised.  A
broken or stale download link is worse than no link, because a reader follows
it in good faith.  This script checks every outbound link in the set and
reports which ones no longer resolve, so the check can be repeated whenever
the pages are rebuilt rather than trusted once.

HOW EACH KIND OF LINK IS CHECKED
--------------------------------
GitHub is handled specially, because ``github.com`` web pages are often
rate-limited or blocked for scripts while the git transport is not:

    github.com/<owner>/<repo>                 git ls-remote (repo exists)
    github.com/<owner>/<repo>/blob/<ref>/<p>  raw.githubusercontent.com file
    github.com/<owner>/<repo>/tree/<ref>/<p>  git ls-remote (repo exists);
                                              the directory itself is not
                                              checked and is reported as such
    github.com/<owner>/<repo>/releases/...    git ls-remote (repo exists),
                                              plus the tag when one is named

Every other URL is requested over HTTP(S): HEAD first, then GET when a server
rejects HEAD, following redirects.  A 2xx or 3xx final status passes.  A 403
or 429 is reported as ``BLOCKED`` rather than ``BROKEN``: those mean the
server refused an automated client, not that the page is gone, and they need
a human to open the link.  A request that times out is reported as
``TIMEOUT`` for the same reason: some vendor sites (amd.com among them) stall
automated clients rather than refuse them, and both AMD pages that timed out
in the v0.0.6 run were confirmed to exist by opening them another way.

Templated URLs taken from code examples (``.../v${VERSION}/...``) cannot be
resolved and are skipped, with the count reported.

USAGE
-----
    python check_links.py --site ..            # check the page set
    python check_links.py --site .. --json report.json
    python check_links.py --site .. --workers 16 --timeout 20

Exit status is 0 when nothing is BROKEN, 1 otherwise.  BLOCKED and TIMEOUT
do not fail the run, because neither is evidence of a broken link.

REQUIREMENTS
------------
Python 3.9+ standard library only.  ``git`` on PATH is used for the GitHub
checks; without it, GitHub links fall back to plain HTTP.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import argparse
import concurrent.futures as futures
import html
import json
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# %% Constants ---------------------------------------------------------------

#: User agent sent with HTTP checks.  Generic on purpose: identifies the tool,
#: carries no personal contact detail.
USER_AGENT = "AI_Local-link-check/0.0.2 (+https://github.com/Braveheart53/tools)"

#: Hosts that are never real outbound links: private addresses, placeholders
#: and container-internal service names used in configuration examples.
SKIP_HOST_PATTERNS = (
    r"^localhost", r"^127\.", r"^0\.0\.0\.0", r"^192\.168\.", r"^10\.",
    r"^172\.(1[6-9]|2\d|3[01])\.", r"^host\.docker\.internal",
    r"example\.(com|org)$", r"^ollama_backend", r"^open-terminal",
    r"^node-", r"^<", r"^&lt;", r"^www\.w3\.org$",
    r"^fonts\.(googleapis|gstatic)\.com$",
)

#: Characters that mark a URL as a template rather than a real address.
TEMPLATE_MARKERS = ("$", "{", "}", "<", ">", "&lt;", "&gt;")

#: URL pattern for href attributes.  Only href targets are checked: a URL
#: that appears in a code block is an example command, not a link the reader
#: is invited to follow.
HREF_RE = re.compile(r"""href\s*=\s*["'](https?://[^"'#\s]+(?:#[^"'\s]*)?)["']""",
                     re.IGNORECASE)

#: GitHub URL decomposition.
GITHUB_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)"
    r"(?:/(?P<kind>blob|tree|releases|raw)(?:/(?P<rest>.*))?)?",
    re.IGNORECASE)


# %% Data model --------------------------------------------------------------
@dataclass
class LinkResult:
    """The outcome of checking one URL.

    Attributes
    ----------
    url : str
        The URL as it appears in the page (fragment removed).
    status : str
        ``OK``, ``BROKEN``, ``BLOCKED``, ``TIMEOUT`` or ``PARTIAL``
        (repository found but the specific path inside it could not be
        checked).
    detail : str
        HTTP code, git outcome or exception text.
    pages : list of str
        Every page that links to this URL.
    """

    url: str
    status: str
    detail: str
    pages: List[str]


# %% Extraction --------------------------------------------------------------
def collect_links(site_dir: Path) -> Tuple[Dict[str, Set[str]], int]:
    """Collect every outbound href in the set, mapped to the pages using it.

    Parameters
    ----------
    site_dir : Path
        The AI_Local directory.  Its own ``*.html`` and ``Archive/*.html`` are
        scanned; vendored assets are not, because they hold no reader links.

    Returns
    -------
    (dict, int)
        URL (fragment stripped) to the set of page names that link to it, and
        the number of templated URLs that were skipped.
    """
    links: Dict[str, Set[str]] = {}
    skipped_templates = 0
    pages = sorted(site_dir.glob("*.html")) + sorted(site_dir.glob("Archive/*.html"))

    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        for raw_url in HREF_RE.findall(text):
            url = html.unescape(raw_url).split("#", 1)[0].rstrip(".,;")
            if any(marker in url for marker in TEMPLATE_MARKERS):
                skipped_templates += 1
                continue
            host = re.sub(r"^https?://([^/:]+).*", r"\1", url).lower()
            if any(re.search(p, host) for p in SKIP_HOST_PATTERNS):
                continue
            links.setdefault(url, set()).add(page.relative_to(site_dir).as_posix())
    return links, skipped_templates


# %% Checkers ----------------------------------------------------------------
def http_status(url: str, timeout: float) -> Tuple[Optional[int], str]:
    """Return the final HTTP status of a URL, trying HEAD then GET.

    Some servers answer HEAD with 403/405 while serving GET normally, so a
    HEAD failure is retried as a small ranged GET before being believed.
    """
    last_error = ""
    for method in ("HEAD", "GET"):
        request = urllib.request.Request(url, method=method,
                                         headers={"User-Agent": USER_AGENT})
        if method == "GET":
            # Ask for one byte; the status is what matters, not the body.
            request.add_header("Range", "bytes=0-0")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, method
        except urllib.error.HTTPError as exc:
            last_error = f"{method} {exc.code}"
            if method == "HEAD" and exc.code in (400, 403, 405, 406, 429, 501):
                continue                      # retry as GET
            return exc.code, last_error
        except Exception as exc:              # DNS, TLS, timeout, reset
            last_error = f"{method} {type(exc).__name__}: {exc}"
            if method == "HEAD":
                continue
    return None, last_error


def git_repo_exists(owner: str, repo: str, timeout: float,
                    tag: Optional[str] = None) -> Tuple[bool, str]:
    """Check a GitHub repository (and optionally a tag) via git ls-remote.

    ``GIT_TERMINAL_PROMPT=0`` makes a missing or private repository fail
    immediately instead of prompting for credentials, which is what a
    non-existent public repository looks like to git.
    """
    repo = re.sub(r"\.git$", "", repo)
    command = ["git", "ls-remote", "--tags" if tag else "--heads",
               f"https://github.com/{owner}/{repo}"]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout,
            env={**_base_env(), "GIT_TERMINAL_PROMPT": "0"})
    except subprocess.TimeoutExpired:
        return False, "git ls-remote timed out"
    if result.returncode != 0:
        return False, "repository not found (git ls-remote failed)"
    if tag and f"refs/tags/{tag}" not in result.stdout:
        return False, f"repository exists but tag {tag!r} does not"
    return True, "git ls-remote ok" + (f", tag {tag} present" if tag else "")


def _base_env() -> Dict[str, str]:
    """Return the current environment, so git keeps any configured proxy."""
    import os
    return dict(os.environ)


def check_url(url: str, timeout: float, have_git: bool) -> Tuple[str, str]:
    """Classify one URL as OK, BROKEN, BLOCKED or PARTIAL."""
    match = GITHUB_RE.match(url)
    if match and have_git:
        owner, repo = match.group("owner"), match.group("repo")
        kind, rest = match.group("kind"), match.group("rest") or ""

        if kind == "blob" or kind == "raw":
            # blob/<ref>/<path> maps one-to-one onto the raw file host.
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{rest}"
            code, detail = http_status(raw_url, timeout)
            if code is not None and code < 400:
                return "OK", f"raw file {code}"
            exists, git_detail = git_repo_exists(owner, repo, timeout)
            if exists:
                return "BROKEN", f"repository exists but file missing ({detail})"
            return "BROKEN", git_detail

        tag = None
        if kind == "releases":
            # releases/tag/<tag> and releases/download/<tag>/<asset>
            parts = rest.split("/")
            if len(parts) >= 2 and parts[0] in ("tag", "download"):
                tag = parts[1]
        exists, git_detail = git_repo_exists(owner, repo, timeout, tag=tag)
        if not exists:
            return "BROKEN", git_detail
        if kind == "tree" and rest.count("/") >= 1:
            return "PARTIAL", git_detail + "; directory path not verified"
        if kind == "releases" and rest.startswith("download/"):
            return "PARTIAL", git_detail + "; release asset not verified"
        return "OK", git_detail

    code, detail = http_status(url, timeout)
    if code is None:
        # A timeout says the server did not answer in time, not that the page
        # is gone; DNS failures, refused connections and TLS errors do say so.
        if "timed out" in detail.lower() or "timeout" in detail.lower():
            return "TIMEOUT", detail + " (server too slow or stalling automated clients; open by hand)"
        return "BROKEN", detail
    if code < 400:
        return "OK", str(code)
    if code in (401, 403, 429, 503):
        return "BLOCKED", f"{code} (server refused an automated client; open by hand)"
    return "BROKEN", str(code)


# %% Reporting ---------------------------------------------------------------
def print_report(results: List[LinkResult], skipped_templates: int) -> None:
    """Print a compact table, problems first."""
    order = {"BROKEN": 0, "BLOCKED": 1, "TIMEOUT": 2, "PARTIAL": 3, "OK": 4}
    results = sorted(results, key=lambda r: (order[r.status], r.url))
    width = min(max((len(r.url) for r in results), default=20), 90)

    for result in results:
        if result.status == "OK":
            continue
        print(f"{result.status:8} {result.url[:width]:{width}}  {result.detail}")
        print(f"{'':8} used on: {', '.join(sorted(result.pages))}")

    counts = {status: sum(r.status == status for r in results) for status in order}
    print("-" * 78)
    print(f"checked {len(results)} distinct URLs: "
          + ", ".join(f"{k} {v}" for k, v in counts.items())
          + f"; {skipped_templates} templated URLs skipped")


# %% Entry point -------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    """Check every outbound link and return a process exit status."""
    parser = argparse.ArgumentParser(description="Check outbound links in AI_Local.")
    parser.add_argument("--site", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="AI_Local directory (default: the parent of scripts/)")
    parser.add_argument("--workers", type=int, default=12,
                        help="parallel checks (default 12; network-bound, not CPU-bound)")
    parser.add_argument("--timeout", type=float, default=25.0,
                        help="per-request timeout in seconds")
    parser.add_argument("--json", type=Path, help="also write the results as JSON")
    args = parser.parse_args(argv)

    links, skipped = collect_links(args.site)
    have_git = shutil.which("git") is not None
    if not have_git:
        print("git not found: GitHub links will be checked over HTTP only", file=sys.stderr)

    # Network-bound work, so threads rather than processes: each check spends
    # nearly all its time waiting on a socket.
    results: List[LinkResult] = []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(check_url, url, args.timeout, have_git): url for url in links}
        for job in futures.as_completed(jobs):
            url = jobs[job]
            try:
                status, detail = job.result()
            except Exception as exc:          # a checker bug must not hide others
                status, detail = "BROKEN", f"checker error: {exc}"
            results.append(LinkResult(url, status, detail, sorted(links[url])))

    print_report(results, skipped)
    if args.json:
        args.json.write_text(json.dumps([asdict(r) for r in results], indent=2),
                             encoding="utf-8")
    return 1 if any(r.status == "BROKEN" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
