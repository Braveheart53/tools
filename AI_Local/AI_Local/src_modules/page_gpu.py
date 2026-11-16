# -*- coding: utf-8 -*-
"""
page_gpu.py -- body of gpu-configuration.html.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-11-15

PURPOSE
-------
Step 2 of the setup path.  Every other page in the set assumes the GPU is
already working; none of them says which driver, toolkit and compiler go with
which card, or what the runtime settings that decide GPU placement actually
do.  This page does, for NVIDIA, AMD, Intel and Apple hardware, and for both
runtimes in the set (Ollama and llama.cpp).

SOURCING
--------
Every setting name and default on this page was read from the runtime's own
source or documentation on 2026-11-15: Ollama's ``docs/gpu.mdx`` [40] and
``envconfig/config.go`` [41]; llama.cpp's ``docs/build.md`` [42],
``common/arg.cpp`` and ``common/common.h`` [43], and its CUDA CMake file [44].
Statements that combine sources, or read an option's description as a
condition, are marked as derived where they appear.

STRUCTURE
---------
``build()`` concatenates one function per section.  Each section function
returns plain HTML; equations come from ``eq_library`` so they are shared with
the PDF and cannot drift.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from typing import List, Tuple

import eq_library as eq

# %% Helpers -----------------------------------------------------------------
def _cite(*numbers: int) -> str:
    """Return IEEE citation anchors for one or more reference numbers."""
    return "".join(f'<a class="cite" href="references.html#r{n}">[{n}]</a>'
                   for n in numbers)


def _rows(rows: List[Tuple[str, ...]]) -> str:
    """Render table body rows; cells are trusted HTML from this module."""
    return "\n".join("      <tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
                     for row in rows)


def _table(caption: str, headers: Tuple[str, ...], rows: List[Tuple[str, ...]]) -> str:
    """Render a captioned, scrollable table in the house format."""
    head = "".join(f'<th scope="col">{h}</th>' for h in headers)
    return (f'<div class="table-wrap"><table>\n'
            f'    <caption>{caption}</caption>\n'
            f'    <thead><tr>{head}</tr></thead>\n'
            f'    <tbody>\n{_rows(rows)}\n    </tbody>\n  </table></div>')


def _m(text: str) -> str:
    """Wrap text in the monospace span used for commands and identifiers."""
    return f'<span class="mono">{text}</span>'


# %% Sections ----------------------------------------------------------------
def _hero() -> str:
    """Page title and the one-paragraph summary."""
    return f"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">Step 2 &middot; GPU configuration</div>
    <h1>Matching the GPU stack to the card, and the settings that decide placement</h1>
    <p class="lead">A model runs at GPU speed only when four things agree: the card's architecture, the driver, the toolkit the runtime was built with, and the runtime settings that decide how much of the model and its cache stay in video memory. This page sets out each of the four for NVIDIA, AMD, Intel and Apple hardware, for both runtimes in the set.</p>
    <p class="small muted">Everything here was read from the runtimes' own sources on 2026-11-15{_cite(40, 41, 42, 43)}. Two things changed recently enough to break older guides, including some pages in this set: CUDA 13 can no longer build for GTX 10-series cards{_cite(45, 44)}, and llama.cpp now fits a model to memory on its own unless you tell it not to{_cite(43)}.</p>
  </div>
</section>
"""


def _toc() -> str:
    """On-this-page list; the ids are linked from other pages, keep them stable."""
    items = [
        ("start", "1. Start from the card"),
        ("nvidia-matrix", "2. NVIDIA: driver, toolkit and compiler that go together"),
        ("amd", "3. AMD: ROCm, HIP, WSL and Vulkan"),
        ("intel-apple", "4. Intel, Apple and CPU-only machines"),
        ("vulkan", "5. Vulkan, the cross-vendor path"),
        ("devices", "6. Choosing which GPU a runtime uses"),
        ("ollama", "7. How Ollama places a model"),
        ("llamacpp", "8. How llama.cpp places a model"),
        ("moe", "9. Mixture-of-experts models on a small card"),
        ("kv", "10. Cache type and attention kernel"),
        ("multi", "11. More than one GPU"),
        ("docker", "12. GPUs inside containers"),
        ("monitor", "13. Reading GPU load into Prometheus"),
        ("trouble", "14. When the GPU is not being used"),
        ("gaps", "15. What this page does not settle"),
    ]
    links = "\n".join(f'      <li><a href="#{a}">{t}</a></li>' for a, t in items)
    return f"""
<section id="on-this-page">
  <div class="container">
    <h2>On this page</h2>
    <ul class="toc">
{links}
    </ul>
  </div>
</section>
"""


def _start() -> str:
    """Section 1: compute capability and what it decides."""
    rows = [
        ("12.0", "Blackwell", "RTX 5060 to RTX 5090", "Yes, toolkit 12.8 or newer" + _cite(44), "550"),
        ("8.9", "Ada", "RTX 4060 to RTX 4090", "Yes", "550"),
        ("8.6", "Ampere", "RTX 3060 to RTX 3090 Ti", "Yes", "550"),
        ("7.5", "Turing", "GTX 1650 Ti, RTX 2060 to RTX 2080 Ti, TITAN RTX", "Yes", "550"),
        ("7.0", "Volta", "TITAN V, V100", "<strong>No</strong>: use CUDA 12.x", "550"),
        ("6.1", "Pascal", "GTX 1050 to GTX 1080 Ti, TITAN Xp", "<strong>No</strong>: use CUDA 12.x", "<strong>570</strong>"),
        ("5.0, 5.2", "Maxwell", "GTX 750 to GTX 980 Ti", "<strong>No</strong>: use CUDA 12.x", "<strong>570</strong>"),
    ]
    table = _table(
        "NVIDIA architectures in the cards this set is likely to meet. Compute capability and example cards from Ollama's hardware table"
        + _cite(40) + " (NVIDIA's own list is " + _cite(49) + "); CUDA 13 support from the CUDA 13.5 release notes" + _cite(45)
        + " and llama.cpp's build file" + _cite(44) + "; driver minimums from Ollama" + _cite(40) + ".",
        ("Compute capability", "Architecture", "Example cards", "Can CUDA 13.5 build for it?", "Ollama minimum driver"),
        rows)
    return f"""
<section id="start">
  <div class="container">
    <h2>1. Start from the card</h2>
    <p>For NVIDIA cards the number that decides everything downstream is the <strong>compute capability</strong>: a version number for the GPU architecture. It decides which driver Ollama will accept, which CUDA toolkit can compile for the card, and which value goes into {_m("CMAKE_CUDA_ARCHITECTURES")} when llama.cpp is built for it. Look the card up in NVIDIA's list{_cite(49)} or in Ollama's table{_cite(40)} before downloading anything.</p>
    {table}
    <div class="callout danger">
      <p><strong>If your card is Pascal, Maxwell or Volta, CUDA 13 is the wrong toolkit for building.</strong> NVIDIA's release notes record the removal of Maxwell, Pascal and Volta support{_cite(45)}, and llama.cpp only adds its {_m("50-virtual 61-virtual 70-virtual")} targets when the toolkit is older than 13{_cite(44)}. The build notes in the deployment folder target {_m("CMAKE_CUDA_ARCHITECTURES=61")}, which is Pascal, so those machines stay on CUDA 12.x. Running Ollama is unaffected: it ships its own runtime and only needs a driver of version 570 or newer for these cards{_cite(40)}.</p>
    </div>
    <p>AMD, Intel and Apple hardware do not use compute capability. For AMD, what matters is whether the card is on ROCm's support list (section 3); everything else runs through Vulkan (section 5).</p>
  </div>
</section>
"""


def _nvidia_matrix() -> str:
    """Section 2: toolkit / driver / Visual Studio pairing and the build commands."""
    rows = [
        ("CUDA 13.5", "R620 branch" + _cite(45), "2019, 2022, 2026" + _cite(46), "7.5 and newer"),
        ("CUDA 13.0", "R580 branch" + _cite(45), "not checked", "7.5 and newer"),
        ("CUDA 12.9 Update 1", "576.57 or newer" + _cite(45), "2019, 2022 only" + _cite(47), "5.0 and newer" + _cite(44)),
        ("CUDA 12.8 GA", "570.65 or newer" + _cite(45), "not checked", "5.0 and newer; first with Blackwell" + _cite(44)),
        ("CUDA 12.6 Update 3", "561.17 or newer" + _cite(45), "not checked", "5.0 and newer"),
    ]
    table = _table(
        "CUDA toolkit lines, the minimum Windows driver each needs, the Visual Studio versions its "
        "installation guide lists as host compilers, and the architectures llama.cpp builds for with it. "
        "&ldquo;Not checked&rdquo; means that guide was not read, not that the pairing fails.",
        ("Toolkit", "Windows driver", "Visual Studio host compiler", "Builds for compute capability"),
        rows)
    return f"""
<section id="nvidia-matrix">
  <div class="container">
    <h2>2. NVIDIA: driver, toolkit and compiler that go together</h2>
    <p>Three version numbers have to agree on a build machine: the driver, the CUDA toolkit, and the Visual Studio compiler that {_m("nvcc")} hands host code to. Only the driver is needed to <em>run</em> Ollama or a prebuilt llama.cpp release.</p>
    {table}

    <h3>2.1 What to install</h3>
    <div class="table-wrap"><table>
      <caption>Install sets by situation. The driver ceiling for older cards comes from a press report of NVIDIA's schedule{_cite(59)} <span class="badge medium">secondary source</span>; the rest from the table above.</caption>
      <thead><tr><th scope="col">Situation</th><th scope="col">Driver</th><th scope="col">Toolkit</th><th scope="col">Compiler</th></tr></thead>
      <tbody>
        <tr><td>Running Ollama only, any supported card</td><td>550 or newer; 570 or newer for compute capability 5.0&ndash;6.2{_cite(40)}</td><td>none</td><td>none</td></tr>
        <tr><td>Building llama.cpp, Turing (7.5) or newer</td><td>Current, R620 branch for CUDA 13.5</td><td>CUDA 13.5</td><td>Build Tools 2026 or 2022</td></tr>
        <tr><td>Building llama.cpp, Pascal / Maxwell / Volta</td><td>570&ndash;580 series; R580 is reported as the last branch for these cards{_cite(59)}</td><td>CUDA 12.9 Update 1, or the 12.6 / 12.8 installers already in the folder</td><td><strong>Build Tools 2022</strong>; CUDA 12.9 does not list 2026{_cite(47)}</td></tr>
        <tr><td>Building for RTX 50-series (Blackwell)</td><td>Current</td><td>12.8 or newer; 13.5 preferred</td><td>2026 or 2022</td></tr>
      </tbody>
    </table></div>
    <p>In a cluster that mixes generations, for example an RTX 3090 serving node with GTX 1080 RPC workers, build each machine for its own card. Each RPC worker runs its own {_m("ggml-rpc-server")} binary, so nothing requires the builds to match. <span class="pill derived">Derived here</span> from the RPC design in {_cite(37)}.</p>

    <h3>2.2 Building llama.cpp with CUDA</h3>
    <p>The documented build is two commands{_cite(42)}. With {_m("GGML_NATIVE")} on (the default) and a recent CMake, llama.cpp builds for the GPU in the build machine and nothing else{_cite(44)}; set the architecture explicitly only when building for a different machine:</p>
<pre><code># In a "Developer PowerShell for VS 2022" (Pascal, CUDA 12.x) or VS 2026 (CUDA 13.5)
cmake -B build -DGGML_CUDA=ON
cmake --build build --config Release -j

# Building for another machine's card: name its compute capability without the dot.
# 61 = Pascal (GTX 10-series), 86 = RTX 30-series, 89 = RTX 40-series.
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES="61"</code></pre>
    <p class="small muted">The explicit-architecture form follows the documented example {_m('-DCMAKE_CUDA_ARCHITECTURES="86;89"')}{_cite(42)}. The {_m("scripts/build_cpp.ps1")} wrapper on the <a href="local-code-build-test.html#cpp">build-and-test page</a> sets up the Visual Studio environment for you.</p>

    <h3>2.3 CUDA settings at run time</h3>
    {_table("Runtime CUDA variables that llama.cpp documents" + _cite(42) + ".",
            ("Variable", "Effect", "When to use it"),
            [(_m("CUDA_VISIBLE_DEVICES"), "Hides devices from the process; llama.cpp's example uses " + _m('"-0"') + " to hide the first one", "Keep a display card or a second job's card out of the model"),
             (_m("GGML_CUDA_ENABLE_UNIFIED_MEMORY=1"), "On Linux, \"allows swapping to system RAM instead of crashing when the GPU VRAM is exhausted\"", "A model slightly too large for the card, accepting a large speed loss")])}
  </div>
</section>
"""


def _amd() -> str:
    """Section 3: AMD on Linux, Windows and WSL."""
    return f"""
<section id="amd">
  <div class="container">
    <h2>3. AMD: ROCm, HIP, WSL and Vulkan</h2>
    <p>AMD cards reach the runtimes by two routes. <strong>ROCm</strong> (and its HIP compiler) is AMD's compute stack and the faster route, but it supports a specific list of cards, and the list differs between Linux, Windows and WSL. Every other recent Radeon runs through <strong>Vulkan</strong>, which needs nothing beyond the normal driver on Windows{_cite(40)}.</p>

    {_table("Which AMD cards Ollama runs through ROCm, by platform" + _cite(40) + ", and which AMD supports for ROCm inside WSL" + _cite(52) + ". Cards outside a row's list fall back to Vulkan.",
            ("Platform", "Requirement", "Supported Radeon cards (abridged)"),
            [("Linux", "ROCm v7 driver, installed with " + _m("amdgpu-install"), "RX 9070 / 9060 series, RX 7900 to 7600 series, RX 6950 XT to 6800, Radeon PRO W7000 and W6000 series, Ryzen AI Max and HX series"),
             ("Windows", "ROCm v7 / HIP7-capable driver stack", "RX 7900 XTX, 7900 XT, 7900 GRE, 7800 XT, 7700 XT, 7600 XT, 7600; Radeon PRO W7900 to W7500"),
             ("WSL 2", "ROCm 7.2.1 with Adrenalin 26.1.1 for WSL2; Ubuntu 22.04 or 24.04", "RX 9070 / 9060 series, AI PRO R9700 / R9600D, RX 7900 XTX / XT / GRE, RX 7800 XT, RX 7700 / 7700 XT, PRO W7900 / W7800 / W7700")])}

    <h3>3.1 Cards just outside the Linux list</h3>
    <p>On Linux, Ollama can be told to treat an unsupported card as a close supported target with {_m("HSA_OVERRIDE_GFX_VERSION")}. Its own example maps an RX 5400 ({_m("gfx1034")}) onto {_m("gfx1030")} with {_m('HSA_OVERRIDE_GFX_VERSION="10.3.0"')}, and per-device forms ({_m("HSA_OVERRIDE_GFX_VERSION_0")}, {_m("_1")}) exist for mixed cards{_cite(40)}. This is a Linux mechanism; the older Jupyter pages in this set that compute it inside WSL are not following a documented procedure.</p>

    <h3>3.2 ROCm inside WSL, and what it cannot do</h3>
    <p>AMD's current WSL procedure is: install the Adrenalin driver version listed for your ROCm release, install WSL with Ubuntu 22.04 or 24.04, then install the ROCDXG user-mode library{_cite(87)}. It does not install Linux kernel modules: WSL runs Microsoft's kernel. The ROCDXG repository is itself marked deprecated, its source having moved into AMD's {_m("rocm-systems")} tree{_cite(88)}, so follow AMD's how-to page{_cite(87)} for the commands rather than any copy of them, this page included.</p>
    <div class="callout danger">
      <p><strong>{_m("amd-smi")} does not work under WSL.</strong> AMD's limitations page states that "due to WSL architectural limitations for native Linux User Kernel Interface (UKI), amd-smi is not supported"{_cite(53)}. Anything that reads AMD GPU metrics through {_m("amd-smi")} inside WSL, including {_m("amd_smi_exporter")}, cannot report the GPU there. Section 13 gives the route that works on Windows.</p>
    </div>

    <h3>3.3 Building llama.cpp with HIP</h3>
    <p>The documented Linux build{_cite(42)}; {_m("GPU_TARGETS")} "is optional, omitting it will build the code for all GPUs in the current system":</p>
<pre><code>HIPCXX="$(hipconfig -l)/clang" HIP_PATH="$(hipconfig -R)" \\
    cmake -S . -B build -DGGML_HIP=ON -DGPU_TARGETS=gfx1030 -DCMAKE_BUILD_TYPE=Release \\
    &amp;&amp; cmake --build build --config Release -- -j 16</code></pre>
    <p>Building natively on Windows needs AMD's HIP SDK{_cite(54)}. Neither is needed to run Ollama or a prebuilt llama.cpp HIP release.</p>
  </div>
</section>
"""


def _intel_apple() -> str:
    """Section 4: Intel, Apple, CPU."""
    return f"""
<section id="intel-apple">
  <div class="container">
    <h2>4. Intel, Apple and CPU-only machines</h2>
    {_table("The remaining hardware routes.",
            ("Hardware", "Ollama", "llama.cpp", "Notes"),
            [("Intel Arc and integrated GPUs", "Vulkan; bundled with the driver on Windows" + _cite(40), "Vulkan, or SYCL with " + _m("-DGGML_SYCL=ON") + " and the oneAPI toolkit" + _cite(42), "SYCL needs oneAPI on the build machine only"),
             ("Apple silicon", "Metal" + _cite(40), "Metal, on by default on macOS" + _cite(42), "Unified memory: the model shares RAM with the system"),
             ("CPU only", "Automatic when no GPU qualifies", "Default build", "Speed is bounded by system memory bandwidth; see the model page")])}
    <p>Intel and Apple machines are outside the hardware this set was written for. The routes above are documented by the runtimes, but none of the procedures on the other pages has been run on them.</p>
  </div>
</section>
"""


def _vulkan() -> str:
    """Section 5: Vulkan for every vendor."""
    return f"""
<section id="vulkan">
  <div class="container">
    <h2>5. Vulkan, the cross-vendor path</h2>
    <p>Vulkan is the route for any card that ROCm or CUDA does not cover, and the one the multi-node guide in this set builds on. In Ollama it "is enabled by default when the backend is installed", and on Windows "most GPU vendors drivers come bundled with Vulkan support and require no additional setup steps"{_cite(40)}. Linux needs the vendor's or Mesa's Vulkan driver, and on Linux Ollama needs {_m("cap_perfmon")} or root to read free VRAM through Vulkan; without it, it schedules from approximate model sizes{_cite(40)}.</p>
    <p>Building llama.cpp's Vulkan backend ({_m("-DGGML_VULKAN=ON")}) needs the Vulkan SDK on the build machine{_cite(42)}; running it needs only the driver. The SDK in the deployment folder is 1.4.350.0 and the current one is 1.4.363.1{_cite(63)}. Per-node device selection for AMD cards over Vulkan is covered in <a href="llama-rpc-vulkan-guide.html">the multi-node guide</a>.</p>
  </div>
</section>
"""


def _devices() -> str:
    """Section 6: device-selection variables."""
    return f"""
<section id="devices">
  <div class="container">
    <h2>6. Choosing which GPU a runtime uses</h2>
    <p>Each GPU library has its own visibility variable, and they do not affect one another: hiding a card from CUDA does not hide it from Vulkan.</p>
    {_table("Device-selection settings, by library. All of them are read when the server process starts, so set them in the service definition, not in an interactive shell.",
            ("Setting", "Applies to", "Values", "Source"),
            [(_m("CUDA_VISIBLE_DEVICES"), "NVIDIA (Ollama, llama.cpp)", "Comma-separated IDs; UUIDs from " + _m("nvidia-smi -L") + " are more reliable than indices; an invalid ID such as " + _m("-1") + " forces CPU", _cite(40, 42)),
             (_m("ROCR_VISIBLE_DEVICES"), "AMD ROCm (Ollama)", "IDs or " + _m("Uuid") + " from " + _m("rocminfo") + "; " + _m("-1") + " forces CPU", _cite(40)),
             (_m("GGML_VK_VISIBLE_DEVICES"), "Vulkan (Ollama, llama.cpp)", "Numeric IDs; " + _m("-1") + " disables all Vulkan GPUs. On iGPU + dGPU systems, set it to the discrete card", _cite(40)),
             (_m("OLLAMA_VULKAN=0"), "Ollama", "Disables the Vulkan backend entirely", _cite(40)),
             (_m("--device") + " / " + _m("--list-devices"), "llama.cpp", "Comma-separated device names to offload to (" + _m("none") + " = no offload); " + _m("--list-devices") + " prints the names", _cite(43))])}
  </div>
</section>
"""


def _ollama() -> str:
    """Section 7: Ollama's placement settings."""
    rows = [
        (_m("OLLAMA_FLASH_ATTENTION"), "Unset: used automatically where backend and device support it; " + _m("1") + " forces it on, " + _m("0") + " off" + _cite(9), "Precondition for a quantised cache"),
        (_m("OLLAMA_KV_CACHE_TYPE"), "Key/value cache type (default " + _m("f16") + ")", "Halves the cache at " + _m("q8_0") + "; see section 10"),
        (_m("OLLAMA_CONTEXT_LENGTH"), "Context length; " + _m("0") + " means pick from VRAM", "Explicit value overrides the VRAM tiers"),
        (_m("OLLAMA_NUM_PARALLEL"), "Maximum parallel requests; default 1", "Each slot needs its own cache"),
        (_m("OLLAMA_MAX_LOADED_MODELS"), "Maximum loaded models per GPU", "Two models need room for both"),
        (_m("OLLAMA_SCHED_SPREAD"), "Always schedule a model across all GPUs", "Multi-GPU machines; section 11"),
        (_m("OLLAMA_GPU_OVERHEAD"), "VRAM to reserve per GPU, in bytes; default 0", "A card that also drives displays"),
        (_m("OLLAMA_KEEP_ALIVE"), "How long models stay loaded; default " + _m("5m"), "Reload cost versus VRAM held"),
        (_m("OLLAMA_LLM_LIBRARY"), "Sets the runtime library, bypassing autodetection", "Diagnosis only"),
    ]
    return f"""
<section id="ollama">
  <div class="container">
    <h2>7. How Ollama places a model</h2>
    <p>Ollama decides placement itself from the VRAM each GPU library reports. The settings below change its inputs. Names and descriptions are from the server's own configuration source{_cite(41)} and its FAQ{_cite(9)}; set them on the server process, which on Windows means the user or system environment, then restart Ollama.</p>
    {_table("Ollama server settings that affect GPU placement" + _cite(41) + ".", ("Variable", "What it does", "Why it matters here"), rows)}
    <p>To see where a loaded model ended up, run {_m("ollama ps")}: the {_m("PROCESSOR")} column reads {_m("100% GPU")} when the whole model is in video memory, and shows a CPU/GPU split when part of it is not{_cite(9)}. A split is the single most common reason a model is slower than the model page predicts.</p>
    <p>When {_m("OLLAMA_CONTEXT_LENGTH")} is unset, Ollama picks the default context from total VRAM; the thresholds in the code are 23 and 47&nbsp;GiB rather than the 24 and 48 the prose states. The <a href="local-code-build-test.html#model-settings">build-and-test page</a> has the table{_cite(35, 38)}.</p>
  </div>
</section>
"""


def _llamacpp() -> str:
    """Section 8: llama.cpp placement, --fit and -ngl."""
    rows = [
        (_m("--fit on|off"), _m("LLAMA_ARG_FIT"), _m("on"), "Adjust unset arguments to fit device memory"),
        (_m("--fit-target MiB0,MiB1,..."), "&mdash;", "1024 per device", "Free margin to leave on each device"),
        (_m("--fit-ctx N"), _m("LLAMA_ARG_FIT_CTX"), "4096", "Smallest context --fit may choose"),
        (_m("--fit-print on|off"), "&mdash;", _m("off"), "Print the memory estimate"),
        (_m("-ngl, --n-gpu-layers"), _m("LLAMA_ARG_N_GPU_LAYERS"), _m("auto"), "An exact number, " + _m("auto") + " or " + _m("all")),
        (_m("-c, --ctx-size"), _m("LLAMA_ARG_CTX_SIZE"), _m("0") + " (from the model)", "Context length"),
        (_m("-np, --parallel"), _m("LLAMA_ARG_N_PARALLEL"), _m("-1") + " (auto)", "Server slots; each holds cache"),
    ]
    return f"""
<section id="llamacpp">
  <div class="container">
    <h2>8. How llama.cpp places a model</h2>
    <p>Current llama.cpp builds fit a model to memory automatically. With {_m("--fit on")}, the default, the server adjusts every argument you did not set, layer count and context included, until each device keeps a free margin{_cite(43)}. Options and defaults below are from {_m("common/arg.cpp")} and {_m("common/common.h")}{_cite(43)}.</p>
    {_table("llama.cpp placement options" + _cite(43) + ". Every option with an environment name can be set that way instead, which is convenient in an NSSM service definition.", ("Option", "Environment", "Default", "Meaning"), rows)}
    {eq.get("fit-margin")}
    <div class="callout">
      <p><strong>The service definitions in this set pass {_m("-ngl")} explicitly.</strong> An explicit value is held fixed, so those services do not benefit from {_m("--fit")} for the layer count. On a single machine, removing {_m("-ngl")} lets the server choose; keep an explicit value where you need placement to stay identical across restarts. Whether {_m("--fit")} accounts for RPC workers was not established from the option text, so keep explicit values on RPC clusters.</p>
    </div>
    <p>When you do set the layer count yourself, start from this:</p>
    {eq.get("ngl-layers")}
  </div>
</section>
"""


def _moe() -> str:
    """Section 9: MoE expert offload."""
    rows = [
        (_m("-cmoe, --cpu-moe"), _m("LLAMA_ARG_CPU_MOE"), "Keep all MoE weights in the CPU"),
        (_m("-ncmoe, --n-cpu-moe N"), _m("LLAMA_ARG_N_CPU_MOE"), "Keep the MoE weights of the first N layers in the CPU"),
        (_m("--moe-cache-mib N"), "&mdash;", "GPU cache for the experts kept in the CPU; default 0 (disabled)"),
        (_m("-ot, --override-tensor"), _m("LLAMA_ARG_OVERRIDE_TENSOR"), "Override the buffer type of tensors matching a name pattern; the general form of the options above"),
    ]
    return f"""
<section id="moe">
  <div class="container">
    <h2>9. Mixture-of-experts models on a small card</h2>
    <p>Most of the strongest open models in the shortlist are routed mixtures of experts: they occupy memory like their total size and stream like their active subset (<a href="ollama-model-selection.html#fit-moe">model page, section 3.3</a>). That asymmetry is what makes the options below worthwhile. Moving the expert weights to system memory frees the most VRAM for the least speed, because each token reads only the few experts it is routed to.</p>
    {_table("llama.cpp mixture-of-experts placement options" + _cite(43) + ".", ("Option", "Environment", "Meaning"), rows)}
    {eq.get("moe-cpu-offload")}
    <p>The practical method: let {_m("--fit")} place everything, and if the context it chooses is too short, raise {_m("--n-cpu-moe")} until the context you need fits, measuring token rate at each step with the probe script on the model page. Ollama does not expose these options.</p>
  </div>
</section>
"""


def _kv() -> str:
    """Section 10: cache type and Flash Attention."""
    return f"""
<section id="kv">
  <div class="container">
    <h2>10. Cache type and attention kernel</h2>
    <p>After the weights, the key/value cache is the largest allocation, and it grows linearly with context and with parallel slots:</p>
    {eq.get("kv-cache")}
    {_table("Cache and attention settings in both runtimes" + _cite(41, 43) + ".",
            ("Setting", "Runtime", "Default", "Notes"),
            [(_m("-fa, --flash-attn"), "llama.cpp", _m("auto"), "Picks the Flash Attention kernel where the backend supports it"),
             (_m("OLLAMA_FLASH_ATTENTION"), "Ollama", "automatic where supported" + _cite(9), "Must be in effect for a quantised cache to save memory"),
             (_m("-ctk / -ctv"), "llama.cpp", _m("f16"), "Separate K and V cache types"),
             (_m("OLLAMA_KV_CACHE_TYPE"), "Ollama", _m("f16"), _m("q8_0") + " about halves the cache, " + _m("q4_0") + " about quarters it; global to all models" + _cite(9)),
             (_m("-nkvo, --no-kv-offload"), "llama.cpp", "offload on", "Keeps the cache in system memory: frees VRAM, costs speed")])}
    <p>Halving the cache with {_m("q8_0")} has three conditions (Flash Attention must be on, the setting is global, and models with many query heads per key/value head lose more precision), set out on the <a href="ollama-model-selection.html#fit-q8">model page, section 3.2</a>.</p>
  </div>
</section>
"""


def _multi() -> str:
    """Section 11: multi-GPU."""
    return f"""
<section id="multi">
  <div class="container">
    <h2>11. More than one GPU</h2>
    <p>Within one machine, llama.cpp splits a model across cards in one of four ways{_cite(43)}:</p>
    {_table("llama.cpp split modes, " + _m("-sm, --split-mode") + _cite(43) + ".",
            ("Mode", "What is split", "Use"),
            [(_m("none"), "Nothing: one GPU only, chosen with " + _m("-mg"), "A model that fits on one card"),
             (_m("layer") + " (default)", "Layers and cache, pipelined", "The general case"),
             (_m("row"), "Weights by rows, in parallel; " + _m("-mg") + " holds intermediate results and cache", "Equal cards with a fast interconnect"),
             (_m("tensor"), "Weights and cache, in parallel; marked experimental", "Testing only")])}
    {eq.get("tensor-split")}
    <p>Ollama exposes none of these; it decides placement itself, and {_m("OLLAMA_SCHED_SPREAD")} forces it to spread a model over every GPU rather than keep it on one{_cite(41)}. Across machines the split is llama.cpp's RPC backend, covered on the <a href="llama-rpc-vulkan-guide.html">multi-node guide</a> and costed on the <a href="ollama-model-selection.html#distributed">model page</a>.</p>
  </div>
</section>
"""


def _docker() -> str:
    """Section 12: GPUs in containers."""
    return f"""
<section id="docker">
  <div class="container">
    <h2>12. GPUs inside containers</h2>
    <p>The build-and-test page runs Open WebUI, Open Terminal and Jupyter in containers. Whether those containers can see the GPU depends on the host:</p>
    {_table("GPU access from containers, by host.",
            ("Host", "NVIDIA", "AMD", "Source"),
            [("Windows, Docker Desktop", "Yes, through WSL 2 GPU paravirtualisation: needs the WSL 2 backend, a current NVIDIA driver with WSL 2 support, and " + _m("wsl --update") + ". Pass " + _m("--gpus=all"), "Not covered by Docker Desktop's " + _m("--gpus") + " support, which it describes for NVIDIA GPUs", _cite(51)),
             ("Linux, Docker Engine", "Install the NVIDIA Container Toolkit, run " + _m("sudo nvidia-ctk runtime configure --runtime=docker") + ", restart Docker, then pass " + _m("--gpus=all"), "Pass " + _m("--device /dev/kfd --device /dev/dri") + " and use a ROCm image such as " + _m("ollama/ollama:rocm"), _cite(50, 89))])}
<pre><code># Check that a container sees the NVIDIA GPU (Ollama's documented form)
docker run -d --gpus=all -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec ollama ollama ps        # after a request: PROCESSOR should read 100% GPU</code></pre>
    <p>Two consequences for the older pages in this set. On Windows, the AMD container route on the Docker Jupyter page has no documented support from Docker, and {_m("/dev/kfd")} is a Linux ROCm device that WSL does not provide (section 3.2). The working AMD-on-Windows routes are Ollama or llama.cpp running natively, or ROCm inside a WSL distro.</p>
  </div>
</section>
"""


def _monitor() -> str:
    """Section 13: GPU metrics per vendor and OS."""
    rows = [
        ("NVIDIA", "Windows", _m("nvidia_gpu_exporter") + ": " + _m("winget install --scope machine utkuozdemir.nvidia_gpu_exporter") + ", then " + _m("nvidia_gpu_exporter install --collect.backend=nvml") + "; port 9835; a native service, no NSSM", _cite(56)),
        ("NVIDIA", "Linux", _m("nvidia_gpu_exporter") + " from its " + _m(".deb") + ", " + _m(".rpm") + " or tarball", _cite(56)),
        ("AMD, Intel, NVIDIA", "Windows", _m("windows_exporter") + " with the " + _m("gpu") + " collector turned on; vendor-neutral, from the same Windows counters Task Manager reads", _cite(55, 86)),
        ("AMD", "WSL", "<strong>Not possible</strong>: " + _m("amd-smi") + " is unsupported under WSL", _cite(53)),
        ("AMD", "Linux", "AMD Device Metrics Exporter, which replaces " + _m("amd_smi_exporter") + "; its README describes Instinct accelerators and Radeon support was not confirmed", _cite(57, 58)),
        ("Any", "Any", _m("llama-server --metrics") + ": token rate, queue and cache use, which is load as the model sees it", _cite(39)),
    ]
    return f"""
<section id="monitor">
  <div class="container">
    <h2>13. Reading GPU load into Prometheus</h2>
    <p>Which exporter to run depends on vendor and operating system, and two common choices no longer work as older guides describe them.</p>
    {_table("GPU exporters that work, by vendor and host.", ("Vendor", "Host", "Exporter and install", "Source"), rows)}

    <h3>13.1 The Windows GPU collector</h3>
    <p>The {_m("gpu")} collector is off by default{_cite(55)}. Add it to the default set with the documented {_m("[defaults]")} placeholder{_cite(86)}:</p>
<pre><code># Command line (also the form for an NSSM or sc.exe service definition)
.\\windows_exporter.exe --collectors.enabled "[defaults],gpu"

# MSI install: the same list through the installer property
msiexec /i windows_exporter-0.32.1-amd64.msi --% ENABLED_COLLECTORS="[defaults],gpu"</code></pre>
    <p class="small muted">The MSI form passes the {_m("[defaults],gpu")} list through {_m("ENABLED_COLLECTORS")}, which the README describes as taking the same list as the flag{_cite(86)}. <span class="pill derived">Derived here</span>: the README's own MSI examples list collectors explicitly.</p>
    <p>Utilisation comes from a busy-time counter, so it needs {_m("rate()")}. The documented query{_cite(55)}:</p>
<pre><code>sum by (phys) (
  rate(windows_gpu_engine_time_seconds_total{{phys="0", engtype="3D"}}[1m])
) * 100</code></pre>
    <div class="callout">
      <p><strong>The metric was renamed between versions.</strong> It is {_m("windows_gpu_engine_time_seconds")} in 0.31.7, the version in the deployment folder, and {_m("windows_gpu_engine_time_seconds_total")} in 0.32.x{_cite(55)}. A panel written for one shows nothing on the other. Compute work may run on an engine other than {_m("3D")}; list the engine types your driver reports with {_m("count by (engtype) (windows_gpu_engine_time_seconds_total)")} before choosing one.</p>
    </div>
    {eq.get("gpu-utilisation")}
  </div>
</section>
"""


def _trouble() -> str:
    """Section 14: symptom table."""
    rows = [
        (_m("ollama ps") + " shows CPU or a CPU/GPU split", "Driver below the minimum for the card; card not on the ROCm list; model plus cache larger than VRAM", "Driver version against section 1; card against section 3; the fit relation on the model page", _cite(40, 9)),
        ("CUDA 13 build fails for a GTX 10-series card", "CUDA 13 cannot target compute capability below 7.5", "Use CUDA 12.x", _cite(45, 44)),
        (_m("nvcc") + " rejects the Visual Studio version", "CUDA 12.x with Visual Studio 2026", "Use Build Tools 2022 with CUDA 12.x", _cite(47)),
        ("llama.cpp context is smaller than requested", "--fit reduced it to meet the per-device margin", "Run with " + _m("--fit-print on") + "; raise " + _m("--n-cpu-moe") + " or quantise the cache", _cite(43)),
        ("Out-of-memory part-way through loading", "Explicit " + _m("-ngl") + " too high, so --fit does not adjust it", "Remove " + _m("-ngl") + ", or use the layer-count relation in section 8", _cite(43)),
        ("No AMD GPU metrics from inside WSL", _m("amd-smi") + " is unsupported under WSL", "Use the " + _m("windows_exporter") + " gpu collector on the Windows host", _cite(53, 55)),
        ("GPU panel empty after upgrading windows_exporter", "Metric renamed to " + _m("..._total") + " in 0.32", "Update the panel query", _cite(55)),
        ("Wrong card used on a machine with an iGPU", "Vulkan picked the integrated GPU", "Set " + _m("GGML_VK_VISIBLE_DEVICES") + " to the discrete card", _cite(40)),
        ("NVIDIA GPU lost after suspend on Linux", "Driver bug documented by Ollama", _m("sudo rmmod nvidia_uvm &amp;&amp; sudo modprobe nvidia_uvm"), _cite(40)),
    ]
    return f"""
<section id="trouble">
  <div class="container">
    <h2>14. When the GPU is not being used</h2>
    {_table("Symptoms, causes and checks.", ("Symptom", "Likely cause", "Check or fix", "Source"), rows)}
  </div>
</section>
"""


def _gaps() -> str:
    """Section 15: honest list of what was not established."""
    return f"""
<section id="gaps">
  <div class="container">
    <h2>15. What this page does not settle</h2>
    <ul>
      <li>The order in which {_m("--fit")} trades layers against context. The option text does not state it; {_m("--fit-print on")} shows the result for your model{_cite(43)}.</li>
      <li>Whether {_m("--fit")} accounts for RPC workers' memory.</li>
      <li>The driver ceiling for Pascal and older cards comes from a press report{_cite(59)}, not from NVIDIA's own page.</li>
      <li>Radeon support in AMD's Device Metrics Exporter{_cite(58)}.</li>
      <li>Which Windows GPU engine type llama.cpp's CUDA, HIP and Vulkan backends report their work under.</li>
      <li>The Visual Studio versions accepted by CUDA 12.6, 12.8 and 13.0; only the 12.9 and 13.5 guides were read{_cite(46, 47)}.</li>
    </ul>
  </div>
</section>
"""


# %% Entry point -------------------------------------------------------------
def build() -> str:
    """Return the body fragment of gpu-configuration.html."""
    return "".join([
        _hero(), _toc(), _start(), _nvidia_matrix(), _amd(), _intel_apple(),
        _vulkan(), _devices(), _ollama(), _llamacpp(), _moe(), _kv(), _multi(),
        _docker(), _monitor(), _trouble(), _gaps(),
    ])
