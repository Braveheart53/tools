# -*- coding: utf-8 -*-
"""
references.py -- IEEE-style reference list for the AI_Local documentation set.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

PURPOSE
-------
Single source of truth for every citation in the page set.  ``references.html``
is generated from :data:`REFS`, and every ``<a class="cite" href=...>[NN]</a>``
anywhere in the set is checked against these numbers by
``build_ai_local_site.py`` -> ``verify_citations()``.  A citation to a number
that is not defined here fails the build rather than producing a dead link.

STRUCTURE
---------
Each entry is a 4-tuple:

    (number, ieee_citation_html, category_key, url)

* ``number`` -- the bracketed number used in the body text.  Numbers are
  permanent; a retired reference keeps its number and a new one takes the next
  free number, so that a cross-reference written on paper never goes stale.
* ``ieee_citation_html`` -- the citation rendered in IEEE style, as HTML.  Uses
  named entities (``&ldquo;``, ``&mdash;``) rather than raw characters so the
  file stays ASCII-safe through any downstream tooling.
* ``category_key`` -- a key of :data:`CAT_LABEL`, used to group the printed
  list and to colour the category chip.
* ``url`` -- the URL printed under the citation and used for the outbound link.

CONFIDENCE TAGGING
------------------
:data:`CONFIDENCE` records, per reference, how far the cited claim can be
leaned on.  This is published on ``references.html`` because a page that mixes
a BIPM-grade primary specification with a vendor model card ought to say which
is which.

    "primary"  Normative or first-party specification: the project's own
               documentation, a standards body, an official reference manual.
    "vendor"   First-party but commercial and subject to silent revision: a
               model card, a product page, a distribution listing.
    "derived"  A figure computed on these pages from a primary source.  The
               derivation is shown in the equation block.

IEEE STYLE NOTES
----------------
Web references follow the IEEE pattern for an online source: author or issuing
organisation, title in quotation marks, publication or site name in italics,
edition or version, and the access date.  Access dates are given once in
:data:`ACCESSED` rather than repeated in every entry, because every reference
in this set was checked on the same day.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from typing import Dict, List, Tuple


# %% Metadata ----------------------------------------------------------------
#: Date on which the original reference set was retrieved and its quoted
#: content confirmed.  Printed on references.html.
ACCESSED: str = "2026-10-18"

#: Date of the re-verification pass against the upstream documentation
#: repositories.  Three references were added on this date and several
#: figures elsewhere in the set were corrected against them; see the v0.0.4
#: changelog entry.  Carried separately from ACCESSED rather than replacing
#: it, because a reader checking a claim needs to know which date applies to
#: the reference they are looking at.
RECHECKED: str = "2026-10-26"

#: Display labels for the category keys used in :data:`REFS`.
CAT_LABEL: Dict[str, str] = {
    "openwebui":  "Open WebUI platform",
    "models":     "Models &amp; model distribution",
    "inference":  "Inference runtimes",
    "monitoring": "Monitoring &amp; telemetry",
    "agent":      "Agent harnesses &amp; sandboxing",
    "toolchain":  "Build &amp; environment toolchain",
    "web":        "Web typesetting",
}

#: Sourcing-confidence class per reference number.  See the module docstring.
CONFIDENCE: Dict[int, str] = {}


# %% Reference list ----------------------------------------------------------
# Ordered by category, then by first appearance across the page set.  Add new
# entries at the END with the next free number; never renumber.
REFS: List[Tuple[int, str, str, str]] = [

    # --- Open WebUI platform ------------------------------------------- 1-8
    (1,
     'Open WebUI, &ldquo;Python Code Execution,&rdquo; '
     '<em>Open WebUI Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/features/chat-conversations/chat-features/code-execution/python/'),

    (2,
     'Open WebUI, &ldquo;Jupyter Notebooks,&rdquo; '
     '<em>Open WebUI Documentation</em>, Integrations &mdash; Dev Tools. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/tutorials/integrations/dev-tools/jupyter/'),

    (3,
     'Open WebUI, &ldquo;Open Terminal,&rdquo; '
     '<em>Open WebUI Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/features/open-terminal'),

    (4,
     'Open WebUI, &ldquo;Open Terminal &mdash; Installation,&rdquo; '
     '<em>Open WebUI Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/features/open-terminal/setup/installation'),

    (5,
     'Open WebUI, &ldquo;Connecting Open Terminal to Open WebUI,&rdquo; '
     '<em>Open WebUI Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/features/open-terminal/setup/connecting'),

    (6,
     'Open WebUI, &ldquo;Open Terminal &mdash; Advanced Configuration,&rdquo; '
     '<em>Open WebUI Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/features/open-terminal/advanced/configuration'),

    (7,
     'Open WebUI, &ldquo;Environment Variable Configuration,&rdquo; '
     '<em>Open WebUI Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/getting-started/env-configuration'),

    (8,
     'Open WebUI, &ldquo;MCP Support&rdquo; (<span class="mono">mcpo</span> OpenAPI proxy), '
     '<em>Open WebUI Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/features/extensibility/plugin/tools/openapi-servers/mcp'),

    # --- Models and model distribution -------------------------------- 9-16
    (9,
     'Ollama, &ldquo;FAQ&rdquo; (server environment variables), '
     '<em>Ollama Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://docs.ollama.com/faq'),

    (10,
     'Ollama, &ldquo;Model Library,&rdquo; model index. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library'),

    (11,
     'Ollama, &ldquo;qwen3-coder,&rdquo; model card and tag listing. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/qwen3-coder'),

    (12,
     'Ollama, &ldquo;qwen2.5-coder,&rdquo; model card and tag listing. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/qwen2.5-coder'),

    (13,
     'Ollama, &ldquo;devstral-small-2,&rdquo; model card, tag listing and '
     'SWE-Bench / Terminal&nbsp;Bench figures published by Mistral&nbsp;AI. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/devstral-small-2'),

    (14,
     'Ollama, &ldquo;qwen3.6,&rdquo; model card and tag listing. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/qwen3.6'),

    (15,
     'Ollama, &ldquo;laguna-xs-2.1,&rdquo; model card and tag listing '
     '(Poolside, distributed by Ollama). '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/laguna-xs-2.1'),

    (16,
     'Ollama, &ldquo;gpt-oss,&rdquo; model card and tag listing '
     '(OpenAI open-weight models). '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/gpt-oss'),

    # --- Inference runtimes --------------------------------------------- 17
    (17,
     'ggml-org, &ldquo;RPC backend&rdquo; (<span class="mono">rpc-server</span>, '
     '<span class="mono">GGML_RPC</span>), <em>llama.cpp</em> source tree, '
     '<span class="mono">tools/rpc/README.md</span>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'inference',
     'https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md'),

    # --- Monitoring and telemetry ----------------------------------- 18-20
    (18,
     'Prometheus Authors, &ldquo;Storage,&rdquo; '
     '<em>Prometheus Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'monitoring',
     'https://prometheus.io/docs/prometheus/latest/storage/'),

    (19,
     'Prometheus Authors, &ldquo;Query functions,&rdquo; '
     '<em>Prometheus Documentation</em>, PromQL reference. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'monitoring',
     'https://prometheus.io/docs/prometheus/latest/querying/functions/'),

    (20,
     'U. Ozdemir, &ldquo;nvidia_gpu_exporter,&rdquo; '
     'Nvidia GPU exporter for Prometheus, GitHub repository. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'monitoring',
     'https://github.com/utkuozdemir/nvidia_gpu_exporter'),

    # --- Agent harnesses and sandboxing ----------------------------- 21-23
    (21,
     'Anthropic, &ldquo;Configure the sandboxed Bash tool,&rdquo; '
     '<em>Claude Code Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'agent',
     'https://code.claude.com/docs/en/sandboxing'),

    (22,
     'Anthropic, &ldquo;Settings reference,&rdquo; '
     '<em>Claude Code Documentation</em> '
     '(<span class="mono">sandbox</span> keys). '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'agent',
     'https://code.claude.com/docs/en/settings-reference'),

    (23,
     'Anthropic, &ldquo;Permissions,&rdquo; '
     '<em>Claude Code Documentation</em> '
     '(additional directories, permission rule syntax). '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'agent',
     'https://code.claude.com/docs/en/permissions'),

    # --- Build and environment toolchain ---------------------------- 24-30
    (24,
     'Anaconda Inc., &ldquo;conda env create,&rdquo; '
     '<em>conda Documentation</em>, command reference. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://docs.conda.io/projects/conda/en/stable/commands/env/create.html'),

    (25,
     'QuantStack and mamba contributors, &ldquo;micromamba user guide,&rdquo; '
     '<em>mamba Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html'),

    (26,
     'Docker Inc., &ldquo;GPU access,&rdquo; '
     '<em>Docker Docs</em>, Engine &mdash; containers. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://docs.docker.com/engine/containers/gpu/'),

    (27,
     'Kitware Inc., &ldquo;CMAKE_BUILD_PARALLEL_LEVEL,&rdquo; '
     '<em>CMake Documentation</em>, environment variable reference. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://cmake.org/cmake/help/latest/envvar/CMAKE_BUILD_PARALLEL_LEVEL.html'),

    (28,
     'H. Krekel and pytest-dev contributors, &ldquo;How to invoke pytest,&rdquo; '
     '<em>pytest Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://docs.pytest.org/en/stable/how-to/usage.html'),

    (29,
     'Project Jupyter, &ldquo;Running a public Jupyter Server,&rdquo; '
     '<em>Jupyter Server Documentation</em>. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://jupyter-server.readthedocs.io/en/latest/operators/public-server.html'),

    (30,
     'W. W. Wallace, &ldquo;Mamba on Windows &mdash; Install, Shell Setup, and '
     'YAML Environments,&rdquo; <em>Braveheart53/tools</em>, GitHub repository. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://github.com/Braveheart53/tools/blob/main/Mamba%20on%20Windows%20%E2%80%94%20Install%2C%20Shell%20Setup%2C%20and%20YAML%20Environments.md'),

    # --- Web typesetting ------------------------------------------------ 31
    (31,
     'KaTeX contributors, &ldquo;KaTeX &mdash; The fastest math typesetting '
     'library for the web,&rdquo; project documentation and supported-function '
     'list. [Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'web',
     'https://katex.org/docs/supported.html'),

    # --- Additional repository-local sources ---------------------------- 32
    (32,
     'W. W. Wallace, &ldquo;AI_Local &mdash; local AI deployment working set,&rdquo; '
     '<em>Braveheart53/tools</em>, GitHub repository. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'toolchain',
     'https://github.com/Braveheart53/tools/tree/main/AI_Local'),

    # --- Further model cards ---------------------------------------- 33-34
    (33,
     'Ollama, &ldquo;qwen3-coder-next,&rdquo; model card and tag listing '
     '(80B total / 3B active, built on Qwen3-Next-80B-A3B-Base). '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/qwen3-coder-next'),

    (34,
     'Ollama, &ldquo;nemotron-3-nano,&rdquo; model card and tag listing '
     '(NVIDIA). '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'models',
     'https://ollama.com/library/nemotron-3-nano'),

    # --- Re-verified 2026-10-26 against the upstream repositories ---- 35-37
    (35,
     'Ollama, &ldquo;Context length,&rdquo; <em>Ollama Documentation</em>, '
     '<span class="mono">docs/context-length.mdx</span>. '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED + '.',
     'models',
     'https://github.com/ollama/ollama/blob/main/docs/context-length.mdx'),

    (36,
     'Open WebUI, &ldquo;Security Best Practices&rdquo; (Open Terminal), '
     '<em>Open WebUI Documentation</em>, '
     '<span class="mono">docs/features/open-terminal/advanced/security.md</span>. '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED + '.',
     'openwebui',
     'https://github.com/open-webui/docs/blob/main/docs/features/open-terminal/advanced/security.md'),

    (37,
     'ggml-org, &ldquo;RPC backend&rdquo; '
     '(<span class="mono">ggml-rpc-server</span>), <em>llama.cpp</em> source '
     'tree, <span class="mono">tools/rpc/README.md</span>, re-read for the '
     'renamed binary, the upstream security warning and the RDMA transport. '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED + '.',
     'inference',
     'https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md'),
]


# %% Confidence assignment ---------------------------------------------------
# Assigned in bulk by category, then overridden where an individual reference
# differs from its category's norm.
for _num, _cite, _cat, _url in REFS:
    if _cat in ("openwebui", "inference", "monitoring", "agent", "toolchain", "web"):
        CONFIDENCE[_num] = "primary"
    else:
        CONFIDENCE[_num] = "vendor"

# Model cards are first-party but revise without notice: a tag's size and even
# its availability can change between reads.  Keep them "vendor" (set above)
# and note the consequence on the page that relies on them.

# The nvidia_gpu_exporter repository is a third-party community project rather
# than a vendor specification; it is primary for its own behaviour only.
CONFIDENCE[20] = "primary"

# Repository-local documents are this project's own notes, authoritative for
# what this deployment does and for nothing else.
CONFIDENCE[30] = "primary"
CONFIDENCE[32] = "primary"


# %% Helpers -----------------------------------------------------------------
def numbers() -> List[int]:
    """Return every defined reference number, ascending."""
    return sorted(num for num, _c, _k, _u in REFS)


def by_number() -> Dict[int, Tuple[int, str, str, str]]:
    """Return the reference list keyed by number for O(1) lookup."""
    return {num: entry for entry in REFS for num in (entry[0],)}


def domain_of(url: str) -> str:
    """Extract a short display host from a URL.

    Parameters
    ----------
    url : str
        Absolute http(s) URL.

    Returns
    -------
    str
        The host with any leading ``www.`` removed, suitable as link text.
    """
    host = url.split("//", 1)[-1].split("/", 1)[0]
    return host[4:] if host.startswith("www.") else host


def validate() -> None:
    """Fail loudly on a malformed reference list.

    Checks that numbers are unique and gap-free from 1, that every category
    key is known, that every URL is absolute https, and that every reference
    has a confidence class.

    Raises
    ------
    ValueError
        With a message naming the first problem found.
    """
    nums = [num for num, _c, _k, _u in REFS]

    if len(nums) != len(set(nums)):
        duplicates = sorted({n for n in nums if nums.count(n) > 1})
        raise ValueError(f"duplicate reference numbers: {duplicates}")

    expected = list(range(1, len(nums) + 1))
    if sorted(nums) != expected:
        missing = sorted(set(expected) - set(nums))
        raise ValueError(f"reference numbering has gaps; missing: {missing}")

    for num, _cite, cat, url in REFS:
        if cat not in CAT_LABEL:
            raise ValueError(f"reference [{num}] has unknown category {cat!r}")
        if not url.startswith("https://"):
            raise ValueError(f"reference [{num}] URL is not https: {url!r}")
        if num not in CONFIDENCE:
            raise ValueError(f"reference [{num}] has no confidence class")
