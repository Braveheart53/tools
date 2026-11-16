# -*- coding: utf-8 -*-
"""
software_catalog.py -- every program the AI_Local set installs or depends on.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-11-15

PURPOSE
-------
Single source of truth for the software inventory.  ``downloads.html`` and the
software chapter of the PDF reference manual are both generated from
:data:`SOFTWARE`, so a version or a download address is written once.

WHERE THE DATA CAME FROM
------------------------
Three sources, kept separate in the fields below because they mean different
things and a reader needs to know which is which:

``in_folder``
    What was found in the deployment folder ``tools/AI_Local`` on the
    maintainer's workstation on 2026-11-15, read from file names.  This is
    the version actually installed from, not a recommendation.

``in_repo``
    Whether the GitHub repository carries that installer.  The large vendor
    installers (CUDA, Docker Desktop, Grafana, Vulkan SDK, OpenSSL and the
    Prometheus executable) are not in the repository -- several exceed
    GitHub's 100 MB per-file limit -- so a reader cloning the repository has
    to fetch them from the publisher.  Those are the rows this page exists for.

``current``
    The newest release published by the original creator on 2026-11-15.
    GitHub-hosted projects were read from the repository's release tags with
    ``git ls-remote``; the others from the publisher's own download or
    release-notes page, cited in ``ref``.  ``None`` means it was not checked
    and the page says so rather than guessing.

ADDING A ROW
------------
Add a :class:`Program` to :data:`SOFTWARE`.  ``download`` must be the original
creator's page (or, where the creator publishes source only, the distributor
the creator's own documentation points to, with the reason in ``notes``).
:func:`validate` rejects a row with a non-https link, an unknown step key or
a reference number that does not exist.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# %% Constants ---------------------------------------------------------------

#: Date the ``current`` column was read.
VERIFIED: str = "2026-11-15"

#: Step keys, matching :data:`site_flow.STEPS`.  Duplicated as a tuple here
#: (rather than imported) so this module stays importable on its own;
#: :func:`validate` is what keeps the two in agreement.
STEP_KEYS: Tuple[str, ...] = ("software", "gpu", "model", "serve", "hands",
                              "boundary", "monitor", "gpu-metrics", "fleet",
                              "size")

#: GPU vendor tags used to filter the table.
VENDORS: Tuple[str, ...] = ("any", "nvidia", "amd", "intel")


# %% Data model --------------------------------------------------------------
@dataclass(frozen=True)
class Program:
    """One program in the deployment.

    Attributes
    ----------
    key : str
        Stable anchor id on ``downloads.html`` (``#sw-<key>``).
    name : str
        Display name.
    publisher : str
        The original creator.
    role : str
        One line: what it does in this deployment.  Plain text with HTML
        entities allowed.
    steps : tuple of str
        Setup-path steps that need it (keys of ``site_flow.STEPS``).
    platform : str
        ``Windows``, ``Linux``, ``Windows / Linux`` or ``WSL``.
    vendor : str
        One of :data:`VENDORS`: which GPU vendor's users need it.
    in_folder : str or None
        Version or file found in the deployment folder; ``None`` if absent.
    in_repo : str
        ``yes``, ``no``, ``partial`` or ``n/a`` (never shipped as a file).
    current : str or None
        Newest version on :data:`VERIFIED`; ``None`` when not checked.
    download : str
        The original creator's download page.
    ref : int
        Reference number in ``references.py`` supporting ``current``.
    notes : str
        HTML: anything a reader must know before installing.
    required : bool
        False for optional components and for programs in the folder that no
        page in the set uses.
    """

    key: str
    name: str
    publisher: str
    role: str
    steps: Tuple[str, ...]
    platform: str
    vendor: str
    in_folder: Optional[str]
    in_repo: str
    current: Optional[str]
    download: str
    ref: int
    notes: str = ""
    required: bool = True


# %% Inventory ---------------------------------------------------------------
# Grouped by setup step, in the order a reader installs them.
SOFTWARE: List[Program] = [

    # --- Step 1/2: drivers and GPU toolkits -------------------------------
    Program("nvidia-driver", "NVIDIA display driver", "NVIDIA",
            "Kernel driver and CUDA runtime for every NVIDIA path, including WSL and Docker.",
            ("software", "gpu"), "Windows / Linux", "nvidia",
            None, "n/a", "R620 branch (pairs with CUDA 13.5)",
            "https://www.nvidia.com/en-us/drivers/", 60,
            'Ollama needs driver 550 or newer, and 570 or newer for compute capability '
            '5.0&ndash;6.2 <a class="cite" href="references.html#r40">[40]</a>. '
            'The R580 branch is reported as the last to support Maxwell, Pascal and Volta '
            '(GTX 900/1000, Titan V) <a class="cite" href="references.html#r59">[59]</a> '
            '<span class="badge medium">secondary source</span>. Under WSL, install only '
            'the Windows driver: no Linux display driver goes inside WSL '
            '<a class="cite" href="references.html#r48">[48]</a>.'),

    Program("cuda", "CUDA Toolkit", "NVIDIA",
            "Compiler (<span class=\"mono\">nvcc</span>) and libraries for building llama.cpp with CUDA. "
            "Not needed to <em>run</em> Ollama.",
            ("gpu",), "Windows / Linux", "nvidia",
            "11.8.0, 12.5.0, 12.6.3, 12.8.2, 13.2.1 (installers)", "no",
            "13.5 (12.9 Update 1 is the newest 12.x)",
            "https://developer.nvidia.com/cuda-toolkit-archive", 61,
            'CUDA 13 removed Maxwell, Pascal and Volta '
            '<a class="cite" href="references.html#r45">[45]</a>, and llama.cpp only adds '
            'the <span class="mono">50/61/70</span> targets when the toolkit is older than 13 '
            '<a class="cite" href="references.html#r44">[44]</a>. A GTX 10-series card '
            '(<span class="mono">CMAKE_CUDA_ARCHITECTURES=61</span>) must be built with '
            'CUDA 12.x. CUDA 12.9 accepts Visual Studio 2019/2022 only '
            '<a class="cite" href="references.html#r47">[47]</a>; CUDA 13.5 also accepts 2026 '
            '<a class="cite" href="references.html#r46">[46]</a>. See '
            '<a href="gpu-configuration.html#nvidia-matrix">the version matrix</a>.'),

    Program("amd-driver", "AMD Software: Adrenalin Edition", "AMD",
            "Radeon driver on Windows; also supplies the ROCm runtime that WSL uses.",
            ("software", "gpu"), "Windows", "amd",
            None, "n/a", None,
            "https://www.amd.com/en/support/download/drivers.html", 62,
            'For ROCm under WSL, use the driver version AMD lists for your ROCm release in its '
            'WSL matrix <a class="cite" href="references.html#r52">[52]</a>. '
            '<span class="mono">amd-smi</span> does not work under WSL '
            '<a class="cite" href="references.html#r53">[53]</a>.'),

    Program("hip-sdk", "HIP SDK for Windows", "AMD",
            "HIP compiler for building llama.cpp's ROCm backend natively on Windows.",
            ("gpu",), "Windows", "amd",
            None, "n/a", None,
            "https://www.amd.com/en/developer/resources/rocm-hub/hip-sdk.html", 54,
            'Only for building from source. Ollama and the llama.cpp release binaries carry '
            'their own HIP runtime.', required=False),

    Program("vulkan-sdk", "Vulkan SDK", "LunarG",
            "Headers and <span class=\"mono\">glslc</span> needed to <em>build</em> llama.cpp's Vulkan backend.",
            ("gpu",), "Windows / Linux", "any",
            "1.4.350.0", "no", "1.4.363.1",
            "https://vulkan.lunarg.com/sdk/home", 63,
            'The Vulkan <em>runtime</em> ships with every current GPU driver; the SDK is '
            'needed only on the machine that compiles '
            '<a class="cite" href="references.html#r42">[42]</a>.'),

    Program("oneapi", "Intel oneAPI Base Toolkit", "Intel",
            "SYCL compiler for llama.cpp on Intel Arc and integrated GPUs.",
            ("gpu",), "Windows / Linux", "intel",
            None, "n/a", None,
            "https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit-download.html", 84,
            'Not used by any page beyond the GPU page. Intel GPUs also run llama.cpp through '
            'Vulkan, which needs no extra toolkit.', required=False),

    # --- Step 1: build host toolchain -------------------------------------
    Program("vs-buildtools", "Build Tools for Visual Studio 2022 / 2026", "Microsoft",
            "MSVC compiler, Windows SDK and the vcvars environment for C++ and CUDA builds.",
            ("software", "hands"), "Windows", "any",
            "vs_BuildTools_2022.exe, vs_BuildTools_2026.exe, VisualStudioSetup_2026.exe", "yes",
            "Visual Studio 2026",
            "https://visualstudio.microsoft.com/downloads/", 64,
            'Pair the compiler with the CUDA line: <strong>2022</strong> for CUDA 12.x (the '
            'Pascal path), <strong>2026</strong> or 2022 for CUDA 13.5 '
            '<a class="cite" href="references.html#r46">[46]</a> '
            '<a class="cite" href="references.html#r47">[47]</a>.'),

    Program("vc-redist", "Visual C++ Redistributable (x64)", "Microsoft",
            "Runtime DLLs for MSVC-built binaries on machines with no compiler installed.",
            ("software",), "Windows", "any",
            "VC_redist.x64_2022.exe", "yes", "latest supported (v14)",
            "https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist", 65,
            'Needed on worker nodes that run copied <span class="mono">llama-server</span> or '
            '<span class="mono">ggml-rpc-server</span> builds.'),

    Program("vs-remote", "Remote Tools for Visual Studio 2022 / 2026", "Microsoft",
            "Remote debugger for stepping through a build running on another node.",
            ("hands",), "Windows", "any",
            "VS_RemoteTools_2022.exe, VS_RemoteTools_2026.exe", "yes", None,
            "https://learn.microsoft.com/en-us/visualstudio/debugger/remote-debugging", 66,
            'Present in the folder; no page in the set uses it yet.', required=False),

    Program("git", "Git for Windows", "Git for Windows project",
            "Source control; fetches llama.cpp and this repository.",
            ("software",), "Windows", "any",
            None, "n/a", "2.56.1",
            "https://git-scm.com/downloads/win", 80),

    Program("cmake", "CMake", "Kitware",
            "Build-system generator used by llama.cpp and by <span class=\"mono\">build_cpp.ps1</span>.",
            ("hands",), "Windows / Linux", "any",
            None, "n/a", "4.5.0",
            "https://cmake.org/download/", 81,
            'Visual Studio and its Build Tools also install a CMake; a separate install is '
            'only needed for a newer one.'),

    Program("miniforge", "Miniforge (conda + mamba)", "conda-forge",
            "The mamba environment that every Python step runs in.",
            ("software", "hands"), "Windows / Linux", "any",
            None, "n/a", "26.9.4-2",
            "https://github.com/conda-forge/miniforge", 82),

    Program("openssl", "OpenSSL (Win64 build)", "OpenSSL Project; Windows build by Shining Light Productions",
            "TLS for llama.cpp's optional HTTPS features.",
            ("hands",), "Windows", "any",
            "Win64OpenSSL-4_0_0.exe", "no",
            "4.1 (Oct 23 2026); 4.0.3 supported to 14 May 2027; 3.5.9 LTS to 8 Apr 2030",
            "https://slproweb.com/products/Win32OpenSSL.html", 79,
            'The OpenSSL Project publishes source only '
            '<a class="cite" href="references.html#r78">[78]</a>; the Win64 installer is a '
            'third-party build. llama.cpp builds and runs without it, minus SSL '
            '<a class="cite" href="references.html#r42">[42]</a>. The folder\'s 4.0.0 is '
            'superseded within its own branch; for a host kept for years, the 3.5 LTS line '
            'has the longest support.', required=False),

    Program("wsl", "Windows Subsystem for Linux", "Microsoft",
            "Linux userland for the Jupyter-on-WSL route and for Docker Desktop's GPU support.",
            ("software", "hands"), "Windows", "any",
            None, "n/a", None,
            "https://learn.microsoft.com/en-us/windows/wsl/install", 67,
            'Install with <span class="mono">wsl --install</span>.'),

    Program("docker-desktop", "Docker Desktop", "Docker Inc.",
            "Runs Open WebUI, Open Terminal and Jupyter containers; passes the GPU through WSL 2.",
            ("serve", "hands"), "Windows", "any",
            "Docker Desktop Installer.exe (version not in file name)", "no", "4.99.0",
            "https://docs.docker.com/desktop/setup/install/windows-install/", 68,
            'GPU passthrough on Windows needs the WSL 2 backend and an NVIDIA driver with '
            'WSL 2 GPU-PV support; no container toolkit is installed on Windows '
            '<a class="cite" href="references.html#r51">[51]</a>.'),

    Program("nvidia-ctk", "NVIDIA Container Toolkit", "NVIDIA",
            "Gives Docker containers the GPU on a <em>Linux</em> host.",
            ("serve", "hands"), "Linux", "nvidia",
            None, "n/a", "1.20.2",
            "https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html", 50,
            'Linux Docker hosts only. Docker Desktop on Windows does not use it.',
            required=False),

    # --- Step 3/4: runtimes and front end ---------------------------------
    Program("ollama", "Ollama", "Ollama",
            "Model runtime and registry client on every serving node.",
            ("model", "serve"), "Windows / Linux", "any",
            None, "n/a", "0.40.16",
            "https://ollama.com/download", 69,
            'Bundles its own CUDA, ROCm and Vulkan runtimes; only the GPU driver is needed '
            '<a class="cite" href="references.html#r40">[40]</a>.'),

    Program("llama-cpp", "llama.cpp", "ggml-org",
            "<span class=\"mono\">llama-server</span> and <span class=\"mono\">ggml-rpc-server</span> for "
            "multi-machine serving and the <span class=\"mono\">/metrics</span> endpoint.",
            ("serve", "fleet"), "Windows / Linux", "any",
            None, "n/a", "b12428",
            "https://github.com/ggml-org/llama.cpp/releases", 70,
            'Release builds exist for CUDA 12, CUDA 13, HIP, Vulkan and CPU. Build from source '
            'for a Pascal card on CUDA 12.x or to enable RPC.'),

    Program("open-webui", "Open WebUI (+ Open Terminal, mcpo)", "Open WebUI",
            "Browser front end, code execution and the terminal tool server.",
            ("serve", "hands"), "Docker image", "any",
            None, "n/a", "Open WebUI 0.13.3; Open Terminal 0.17.17; mcpo 0.0.20",
            "https://github.com/open-webui/open-webui", 71,
            'Pulled as container images by <span class="mono">config/docker-compose.openwebui.yml</span>.'),

    Program("nginx", "nginx", "F5 / nginx",
            "Reverse proxy in front of Ollama or Open WebUI.",
            ("serve",), "Windows / Linux", "any",
            "1.30.2 (zip and extracted folder)", "yes", "stable 1.30.6; mainline 1.31.8",
            "https://nginx.org/en/download.html", 75,
            'The folder\'s 1.30.2 is on the stable branch and four patch releases behind.'),

    Program("nssm", "NSSM", "Iain Patterson",
            "Runs non-service executables (Prometheus, Grafana, llama-server, Jupyter) as Windows services.",
            ("serve", "monitor", "hands"), "Windows", "any",
            "2.24 and 2.24-101-g897c7ad (zip and extracted)", "yes",
            "2.24 (release); 2.24-101-g897c7ad (pre-release)",
            "https://nssm.cc/download", 76,
            'nssm.cc returned HTTP 503 on the download page during verification; the 2.24 '
            'release zip was reachable. Not needed for <span class="mono">nvidia_gpu_exporter</span> '
            'or <span class="mono">windows_exporter</span>, which register themselves as services '
            '<a class="cite" href="references.html#r56">[56]</a>.'),

    # --- Step 7-10: monitoring --------------------------------------------
    Program("prometheus", "Prometheus", "Prometheus Authors",
            "Time-series store that scrapes every exporter.",
            ("monitor", "fleet", "size"), "Windows / Linux", "any",
            "3.5.3 (zip and extracted with prometheus.exe)", "partial",
            "3.16.0; 3.13.5 LTS",
            "https://prometheus.io/download/", 72,
            'The repository holds the 3.5.3 folder\'s configuration and licence but not '
            '<span class="mono">prometheus.exe</span> or <span class="mono">promtool.exe</span> '
            '(over GitHub\'s 100 MB limit). 3.5 was the previous LTS line; the download page now '
            'marks 3.13 as LTS.'),

    Program("grafana", "Grafana", "Grafana Labs",
            "Dashboards over Prometheus.",
            ("monitor", "fleet"), "Windows / Linux", "any",
            "13.0.1+security-01 (MSI)", "no", "13.3.1",
            "https://grafana.com/grafana/download?platform=windows", 74),

    Program("windows-exporter", "windows_exporter", "Prometheus community",
            "Host metrics on Windows, and vendor-neutral GPU metrics through its <span class=\"mono\">gpu</span> collector.",
            ("monitor", "gpu-metrics", "fleet"), "Windows", "any",
            "0.31.7 (EXE and MSI)", "yes", "0.32.1",
            "https://github.com/prometheus-community/windows_exporter/releases", 73,
            'The <span class="mono">gpu</span> collector is off by default. Its utilisation '
            'counter is <span class="mono">windows_gpu_engine_time_seconds</span> in 0.31.7 and '
            '<span class="mono">windows_gpu_engine_time_seconds_total</span> in 0.32.x, so a '
            'dashboard written for one shows nothing on the other '
            '<a class="cite" href="references.html#r55">[55]</a>.'),

    Program("node-exporter", "node_exporter", "Prometheus Authors",
            "Host metrics on Linux nodes.",
            ("monitor", "fleet"), "Linux", "any",
            None, "n/a", "1.12.1",
            "https://prometheus.io/download/", 72),

    Program("nvidia-exporter", "nvidia_gpu_exporter", "Utku Ozdemir",
            "Per-GPU utilisation, memory, power and temperature for NVIDIA cards.",
            ("gpu-metrics",), "Windows / Linux", "nvidia",
            None, "n/a", "1.19.0",
            "https://github.com/utkuozdemir/nvidia_gpu_exporter/releases", 83,
            'Windows: <span class="mono">winget install utkuozdemir.nvidia_gpu_exporter</span> '
            'installs it as a native service on port 9835 '
            '<a class="cite" href="references.html#r56">[56]</a>.'),

    Program("amd-dme", "AMD Device Metrics Exporter", "AMD",
            "GPU metrics on <em>Linux</em> hosts with ROCm.",
            ("gpu-metrics",), "Linux", "amd",
            None, "n/a", None,
            "https://github.com/ROCm/device-metrics-exporter", 58,
            'AMD\'s named replacement for <span class="mono">amd_smi_exporter</span>, which '
            'receives no further updates <a class="cite" href="references.html#r57">[57]</a>. '
            'Its README describes Instinct accelerators; Radeon support was not confirmed. '
            'On Windows, use the <span class="mono">windows_exporter</span> gpu collector instead.',
            required=False),

    Program("go", "Go", "The Go Authors",
            "Compiler; only needed to build an exporter from source.",
            ("gpu-metrics",), "Windows / Linux", "any",
            "1.26.3 (MSI)", "yes", "1.27.4",
            "https://go.dev/dl/", 77,
            'The notes in the folder build <span class="mono">amd_smi_exporter</span> with Go '
            'inside WSL. That exporter cannot read the GPU under WSL '
            '<a class="cite" href="references.html#r53">[53]</a>, so this is no longer needed '
            'for the AMD path.', required=False),

    Program("alertmanager", "Alertmanager", "Prometheus Authors",
            "Routes Prometheus alerts to e-mail, chat or webhooks.",
            ("monitor",), "Windows / Linux", "any",
            "0.32.1", "yes", "0.35.0",
            "https://prometheus.io/download/", 72,
            'In the folder; no page in the set configures it yet.', required=False),

    Program("blackbox-exporter", "blackbox_exporter", "Prometheus Authors",
            "Probes HTTP endpoints (for example Ollama's port) from outside.",
            ("monitor",), "Windows / Linux", "any",
            "0.28.0", "yes", "0.29.1",
            "https://prometheus.io/download/", 72,
            'In the folder; no page in the set configures it yet.', required=False),

    Program("statsd-exporter", "statsd_exporter", "Prometheus Authors",
            "Bridges StatsD metrics into Prometheus.",
            ("monitor",), "Windows / Linux", "any",
            "0.29.0", "yes", "0.31.0",
            "https://github.com/prometheus/statsd_exporter/releases", 72,
            'In the folder; nothing in this deployment emits StatsD.', required=False),

    Program("graphite-exporter", "graphite_exporter", "Prometheus Authors",
            "Bridges Graphite metrics into Prometheus.",
            ("monitor",), "Windows / Linux", "any",
            "0.16.0", "yes", "0.17.0",
            "https://prometheus.io/download/", 72,
            'In the folder; nothing in this deployment emits Graphite.', required=False),

    Program("consul-exporter", "consul_exporter", "Prometheus Authors",
            "Exports Consul service health.",
            ("monitor",), "Windows / Linux", "any",
            "0.13.0", "yes", "0.13.0",
            "https://prometheus.io/download/", 72,
            'In the folder; this deployment does not run Consul.', required=False),

    Program("7zip", "7-Zip", "Igor Pavlov",
            "Extracts the release archives of this page set.",
            ("software",), "Windows", "any",
            None, "n/a", None,
            "https://www.7-zip.org/", 85, required=False),
]


# %% Helpers -----------------------------------------------------------------
def by_key(key: str) -> Program:
    """Return one program by key; raises ``KeyError`` on a typo."""
    for program in SOFTWARE:
        if program.key == key:
            return program
    raise KeyError(key)


def for_step(step: str) -> List[Program]:
    """Return the required programs for one setup step, in table order."""
    return [p for p in SOFTWARE if step in p.steps and p.required]


def not_in_repo() -> List[Program]:
    """Return the programs present in the folder but absent from GitHub."""
    return [p for p in SOFTWARE if p.in_folder and p.in_repo in ("no", "partial")]


def validate(reference_numbers: Optional[List[int]] = None,
             step_keys: Optional[Tuple[str, ...]] = None) -> None:
    """Fail loudly on a malformed row.

    Parameters
    ----------
    reference_numbers : list of int, optional
        Valid reference numbers; when given, every ``ref`` must be one.
    step_keys : tuple of str, optional
        Valid step keys; defaults to :data:`STEP_KEYS`.

    Raises
    ------
    ValueError
        Naming the first bad row.
    """
    steps = step_keys or STEP_KEYS
    seen = set()
    for program in SOFTWARE:
        if program.key in seen:
            raise ValueError(f"duplicate software key {program.key!r}")
        seen.add(program.key)
        if not program.download.startswith("https://"):
            raise ValueError(f"{program.key}: download link is not https")
        if program.vendor not in VENDORS:
            raise ValueError(f"{program.key}: unknown vendor {program.vendor!r}")
        if program.in_repo not in ("yes", "no", "partial", "n/a"):
            raise ValueError(f"{program.key}: bad in_repo {program.in_repo!r}")
        for step in program.steps:
            if step not in steps:
                raise ValueError(f"{program.key}: unknown step {step!r}")
        if reference_numbers is not None and program.ref not in reference_numbers:
            raise ValueError(f"{program.key}: reference [{program.ref}] is undefined")
