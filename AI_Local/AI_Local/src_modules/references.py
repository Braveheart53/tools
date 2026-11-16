# -*- coding: utf-8 -*-
"""
references.py -- IEEE-style reference list for the AI_Local documentation set.

Author  : William W. Wallace
Version : 0.0.2
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

#: Date of the second re-verification pass.  This one read the *implementation*
#: as well as the prose -- Ollama's ``server/routes.go`` and llama.cpp's server
#: README -- which is what surfaced the gap between the documented 24/48 GiB
#: context tiers and the 23/47 GiB thresholds the code actually tests, and the
#: Flash Attention precondition on cache quantisation that the prose mentions
#: only in passing.  See the v0.0.5 changelog entry.
RECHECKED_2: str = "2026-11-05"

#: Date of the third re-verification pass (v0.0.6).  This pass added the GPU
#: configuration and software download pages, so it read the GPU support
#: documents of every runtime in the set (Ollama's ``docs/gpu.mdx`` and
#: ``envconfig/config.go``; llama.cpp's ``docs/build.md``, ``common/arg.cpp``,
#: ``common/common.h`` and ``ggml/src/ggml-cuda/CMakeLists.txt``), NVIDIA's
#: CUDA 13.5 release notes and installation guides, AMD's ROCm-on-WSL
#: documents, and the release listings of every program in the deployment
#: folder.  Release versions of GitHub-hosted projects were read from the
#: repositories' tags with ``git ls-remote`` on this date.
RECHECKED_3: str = "2026-11-15"

#: Display labels for the category keys used in :data:`REFS`.
CAT_LABEL: Dict[str, str] = {
    "openwebui":  "Open WebUI platform",
    "models":     "Models &amp; model distribution",
    "inference":  "Inference runtimes",
    "monitoring": "Monitoring &amp; telemetry",
    "agent":      "Agent harnesses &amp; sandboxing",
    "toolchain":  "Build &amp; environment toolchain",
    "web":        "Web typesetting",
    "gpu":        "GPU drivers, toolkits &amp; hardware support",
    "software":   "Software distribution &amp; downloads",
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
     '<em>Open WebUI Documentation</em>. Moved from '
     '<span class="mono">/getting-started/env-configuration</span>; every '
     'variable cited from it was re-found at the new address on ' + RECHECKED_3 + '. '
     '[Online]. Available: see URL below. Accessed: ' + ACCESSED + '.',
     'openwebui',
     'https://docs.openwebui.com/reference/env-configuration'),

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

    # --- Re-verified 2026-11-05: implementation sources ------------- 38-39
    (38,
     'Ollama, <span class="mono">server/routes.go</span> '
     '(VRAM-tiered <span class="mono">defaultNumCtx</span> thresholds), '
     '<em>ollama/ollama</em> source tree. '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_2 + '.',
     'models',
     'https://github.com/ollama/ollama/blob/main/server/routes.go'),

    (39,
     'ggml-org, &ldquo;LLaMA.cpp HTTP Server,&rdquo; <em>llama.cpp</em> source '
     'tree, <span class="mono">tools/server/README.md</span> '
     '(<span class="mono">/metrics</span> exporter, CLI and '
     '<span class="mono">LLAMA_ARG_*</span> reference). '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_2 + '.',
     'inference',
     'https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md'),

    # --- Added 2026-11-15 (v0.0.6): GPU support and download sources -- 40-85
    (40,
     'Ollama, &ldquo;Hardware support,&rdquo; <em>ollama/ollama</em> source tree, <span class="mono">docs/gpu.mdx</span> (NVIDIA compute capability and driver minimums, AMD ROCm v7 targets, Vulkan, device selection) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://github.com/ollama/ollama/blob/main/docs/gpu.mdx'),

    (41,
     'Ollama, <span class="mono">envconfig/config.go</span> (server environment variables, defaults and descriptions), <em>ollama/ollama</em> source tree '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'inference',
     'https://github.com/ollama/ollama/blob/main/envconfig/config.go'),

    (42,
     'ggml-org, &ldquo;Build llama.cpp locally,&rdquo; <em>llama.cpp</em> source tree, <span class="mono">docs/build.md</span> (CUDA, HIP, Vulkan, SYCL and Metal builds; runtime CUDA variables) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'inference',
     'https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md'),

    (43,
     'ggml-org, <span class="mono">common/arg.cpp</span> and <span class="mono">common/common.h</span> (command-line options, environment names and defaults), <em>llama.cpp</em> source tree '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'inference',
     'https://github.com/ggml-org/llama.cpp/blob/master/common/arg.cpp'),

    (44,
     'ggml-org, <span class="mono">ggml/src/ggml-cuda/CMakeLists.txt</span> (default CUDA architecture list by toolkit version), <em>llama.cpp</em> source tree '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'inference',
     'https://github.com/ggml-org/llama.cpp/blob/master/ggml/src/ggml-cuda/CMakeLists.txt'),

    (45,
     'NVIDIA, &ldquo;CUDA Toolkit 13.5 Release Notes,&rdquo; <em>NVIDIA Documentation Hub</em> (driver branch per toolkit; removal of Maxwell, Pascal and Volta support) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html'),

    (46,
     'NVIDIA, &ldquo;CUDA Installation Guide for Microsoft Windows,&rdquo; CUDA 13.5 (supported Visual Studio host compilers) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/index.html'),

    (47,
     'NVIDIA, &ldquo;CUDA Installation Guide for Microsoft Windows,&rdquo; CUDA 12.9.1 archive (supported Visual Studio host compilers) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://docs.nvidia.com/cuda/archive/12.9.1/cuda-installation-guide-microsoft-windows/index.html'),

    (48,
     'NVIDIA, &ldquo;CUDA on WSL User Guide,&rdquo; <em>NVIDIA Documentation Hub</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://docs.nvidia.com/cuda/wsl-user-guide/index.html'),

    (49,
     'NVIDIA, &ldquo;CUDA GPU Compute Capability,&rdquo; <em>NVIDIA Developer</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://developer.nvidia.com/cuda-gpus'),

    (50,
     'NVIDIA, &ldquo;Installing the NVIDIA Container Toolkit,&rdquo; <em>NVIDIA Cloud Native Technologies</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html'),

    (51,
     'Docker Inc., &ldquo;GPU support in Docker Desktop for Windows,&rdquo; <em>Docker Docs</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'toolchain',
     'https://docs.docker.com/desktop/features/gpu/'),

    (52,
     'AMD, &ldquo;WSL support matrices by ROCm version,&rdquo; <em>ROCm on Radeon and Ryzen</em> documentation '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/compatibility/compatibilityrad/wsl/wsl_compatibility.html'),

    (53,
     'AMD, &ldquo;Limitations and recommended settings&rdquo; (Radeon, WSL section: <span class="mono">amd-smi</span> unsupported under WSL), <em>ROCm on Radeon and Ryzen</em> documentation, ROCm 7.2 '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://rocm.docs.amd.com/projects/radeon-ryzen/en/docs-7.2/docs/limitations/limitationsrad.html'),

    (54,
     'AMD, &ldquo;HIP SDK for Windows,&rdquo; <em>AMD ROCm Developer Hub</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://www.amd.com/en/developer/resources/rocm-hub/hip-sdk.html'),

    (55,
     'Prometheus community, &ldquo;gpu collector,&rdquo; <em>windows_exporter</em> v0.32.1, <span class="mono">docs/collector.gpu.md</span> (metric renamed from v0.31.7) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'monitoring',
     'https://github.com/prometheus-community/windows_exporter/blob/v0.32.1/docs/collector.gpu.md'),

    (56,
     'U. Ozdemir, &ldquo;Installation,&rdquo; <em>nvidia_gpu_exporter</em>, <span class="mono">docs/INSTALL.md</span> (winget, Scoop and native Windows service) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'monitoring',
     'https://github.com/utkuozdemir/nvidia_gpu_exporter/blob/master/docs/INSTALL.md'),

    (57,
     'AMD, &ldquo;AMD SMI Prometheus Exporter,&rdquo; <em>amd_smi_exporter</em> README (no further updates; superseded by the Device Metrics Exporter) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'monitoring',
     'https://github.com/amd/amd_smi_exporter/blob/master/README.md'),

    (58,
     'AMD, &ldquo;AMD Device Metrics Exporter,&rdquo; <em>ROCm/device-metrics-exporter</em> README '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'monitoring',
     'https://github.com/ROCm/device-metrics-exporter/blob/main/README.md'),

    (59,
     '<em>Tom&rsquo;s Hardware</em>, &ldquo;Nvidia to axe Maxwell, Pascal, and Volta GPUs with end of driver support &mdash; 580 series drivers will be the last to support GTX 900 and 1000 cards,&rdquo; Jul. 1, 2025 (reports NVIDIA&rsquo;s Unix driver deprecation schedule) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://www.tomshardware.com/pc-components/gpu-drivers/nvidia-to-axe-maxwell-pascal-and-volta-gpus-with-end-of-driver-support-580-series-drivers-will-be-the-last-to-support-gtx-900-and-1000-cards'),

    (60,
     'NVIDIA, &ldquo;Download The Official NVIDIA Drivers,&rdquo; <em>NVIDIA</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://www.nvidia.com/en-us/drivers/'),

    (61,
     'NVIDIA, &ldquo;CUDA Toolkit Downloads&rdquo; and &ldquo;CUDA Toolkit Archive,&rdquo; <em>NVIDIA Developer</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://developer.nvidia.com/cuda-toolkit-archive'),

    (62,
     'AMD, &ldquo;AMD Drivers and Support for Processors and Graphics,&rdquo; <em>AMD</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://www.amd.com/en/support/download/drivers.html'),

    (63,
     'LunarG, &ldquo;Vulkan SDK,&rdquo; <em>LunarXchange</em> (current SDK 1.4.363.1 by its <span class="mono">sdk/latest.json</span> listing) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://vulkan.lunarg.com/sdk/home'),

    (64,
     'Microsoft, &ldquo;Visual Studio downloads&rdquo; (Visual Studio 2026, Build Tools for Visual Studio 2026 and 2022) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://visualstudio.microsoft.com/downloads/'),

    (65,
     'Microsoft, &ldquo;Latest supported Visual C++ Redistributable downloads,&rdquo; <em>Microsoft Learn</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist'),

    (66,
     'Microsoft, &ldquo;Remote debugging,&rdquo; <em>Visual Studio documentation</em> (Remote Tools download) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://learn.microsoft.com/en-us/visualstudio/debugger/remote-debugging'),

    (67,
     'Microsoft, &ldquo;How to install Linux on Windows with WSL,&rdquo; <em>Microsoft Learn</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://learn.microsoft.com/en-us/windows/wsl/install'),

    (68,
     'Docker Inc., &ldquo;Install Docker Desktop on Windows&rdquo; and &ldquo;Docker Desktop release notes,&rdquo; <em>Docker Docs</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://docs.docker.com/desktop/setup/install/windows-install/'),

    (69,
     'Ollama, &ldquo;Download Ollama,&rdquo; <em>ollama.com</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://ollama.com/download'),

    (70,
     'ggml-org, <em>llama.cpp</em> releases (prebuilt CUDA, HIP, Vulkan and CPU binaries) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://github.com/ggml-org/llama.cpp/releases'),

    (71,
     'Open WebUI, <em>open-webui</em>, <em>open-terminal</em> and <em>mcpo</em> repositories and container images '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://github.com/open-webui/open-webui'),

    (72,
     'Prometheus Authors, &ldquo;Download,&rdquo; <em>prometheus.io</em> (Prometheus 3.16.0, 3.13.5 LTS, Alertmanager, exporters) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://prometheus.io/download/'),

    (73,
     'Prometheus community, <em>windows_exporter</em> releases '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://github.com/prometheus-community/windows_exporter/releases'),

    (74,
     'Grafana Labs, &ldquo;Download Grafana,&rdquo; <em>grafana.com</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://grafana.com/grafana/download?platform=windows'),

    (75,
     'F5 / nginx, &ldquo;nginx: download,&rdquo; <em>nginx.org</em> (mainline 1.31.8, stable 1.30.6) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://nginx.org/en/download.html'),

    (76,
     'I. Patterson, &ldquo;NSSM &mdash; the Non-Sucking Service Manager,&rdquo; <em>nssm.cc</em> (site intermittently unavailable when checked) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://nssm.cc/download'),

    (77,
     'The Go Authors, &ldquo;All releases,&rdquo; <em>go.dev</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://go.dev/dl/'),

    (78,
     'OpenSSL Project, &ldquo;Downloads,&rdquo; <em>openssl-library.org</em> (supported branches and end-of-support dates) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://openssl-library.org/source/'),

    (79,
     'Shining Light Productions, &ldquo;Win32/Win64 OpenSSL Installer for Windows,&rdquo; <em>slproweb.com</em> (third-party Windows builds) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://slproweb.com/products/Win32OpenSSL.html'),

    (80,
     'Git for Windows project, &ldquo;Download for Windows,&rdquo; <em>git-scm.com</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://git-scm.com/downloads/win'),

    (81,
     'Kitware Inc., &ldquo;Download CMake,&rdquo; <em>cmake.org</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://cmake.org/download/'),

    (82,
     'conda-forge, <em>Miniforge</em> installers (conda and mamba from conda-forge) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://github.com/conda-forge/miniforge'),

    (83,
     'U. Ozdemir, <em>nvidia_gpu_exporter</em> releases '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://github.com/utkuozdemir/nvidia_gpu_exporter/releases'),

    (84,
     'Intel, &ldquo;Intel oneAPI Base Toolkit,&rdquo; <em>Intel Developer Zone</em> (SYCL compiler for Intel GPUs) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit-download.html'),

    (85,
     'I. Pavlov, &ldquo;7-Zip,&rdquo; <em>7-zip.org</em> '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'software',
     'https://www.7-zip.org/'),

    (86,
     'Prometheus community, <em>windows_exporter</em> v0.32.1 README (command-line flags, <span class="mono">[defaults]</span> placeholder and MSI installer properties) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'monitoring',
     'https://github.com/prometheus-community/windows_exporter/blob/v0.32.1/README.md'),

    (87,
     'AMD, &ldquo;Install ROCm on WSL&rdquo; (ROCDXG-based procedure), <em>ROCm on Radeon and Ryzen</em> documentation '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/wsl/howto_wsl.html'),

    (88,
     'AMD, <em>librocdxg</em> README (WSL user-mode library; repository marked deprecated, source moved to <span class="mono">ROCm/rocm-systems</span>) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'gpu',
     'https://github.com/ROCm/librocdxg/blob/master/README.md'),

    (89,
     'Ollama, &ldquo;Docker,&rdquo; <em>ollama/ollama</em> source tree, <span class="mono">docs/docker.mdx</span> (NVIDIA and AMD container commands) '
     '[Online]. Available: see URL below. Accessed: ' + RECHECKED_3 + '.',
     'inference',
     'https://github.com/ollama/ollama/blob/main/docs/docker.mdx'),


]


# %% Confidence assignment ---------------------------------------------------
# Assigned in bulk by category, then overridden where an individual reference
# differs from its category's norm.
for _num, _cite, _cat, _url in REFS:
    if _cat in ("openwebui", "inference", "monitoring", "agent", "toolchain", "web",
                "gpu", "software"):
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

# A press report of a vendor announcement: useful context, but the primary
# NVIDIA schedule it reports was not itself retrieved, so it is marked
# "secondary" and the pages that cite it say so beside the citation.
CONFIDENCE[59] = "secondary"

# Third-party binary builds: authoritative for what the distributor ships,
# not for the upstream project.  Treated like a vendor listing.
CONFIDENCE[79] = "vendor"


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
