# -*- coding: utf-8 -*-
"""
legacy_corrections.py -- corrections applied to the pre-existing pages at build time.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-11-15

PURPOSE
-------
The pre-existing pages are retrofitted, not rewritten: their layout, styling and
scripts are left as they were.  v0.0.6 found content in some of them that cannot
work as written -- download commands pointing at repositories that do not exist,
metric names no exporter publishes, an AMD-under-WSL procedure that installs
kernel modules into a kernel WSL does not let you change.  Each entry below
replaces one exact span of the ORIGINAL page with corrected text, and every
replacement carries a visible "Corrected in v0.0.6" marker with its sources, so
the reader can see what changed and why.

RULES
-----
* ``find`` is matched against the original page and must occur exactly once;
  the build fails otherwise, so a correction can never silently stop applying
  when a source page changes.
* ``replace`` is the corrected HTML.  It may use only the shared ``ailfix``
  classes (styled in ``assets/sitenav.css``) and the page's own existing classes.
* ``why`` is recorded in the change log; ``refs`` lists the reference numbers the
  replacement relies on.

This file was generated from the source pages so that every ``find`` string is
byte-exact.  Edit the entries by hand afterwards if needed; the build re-checks
each one.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


# %% Data model --------------------------------------------------------------
@dataclass(frozen=True)
class Correction:
    """One exact-span replacement in one original page."""

    key: str
    page: str
    find: str
    replace: str
    why: str
    refs: Tuple[int, ...]


# %% The corrections ---------------------------------------------------------
CORRECTIONS: List[Correction] = [
    Correction(
        key='gpu-nvidia-install',
        page='GPU_monitoring_setup.html',
        find='<pre><code># Download latest exporter\ncurl -LO https://github.com/prometheus-community/nvidia_gpu_exporter/releases/download/v1.5.0/nvidia_gpu_exporter-1.5.0.windows-amd64.zip\nExpand-Archive -Path nvidia_gpu_exporter-*.zip -DestinationPath C:\\nvidia-exporter\n\n# Register as Windows Service (persistent)\nNew-Service -Name "NVIDIA-GPU-Exporter" -BinaryPathName "C:\\nvidia-exporter\\nvidia_gpu_exporter.exe" `\n            -DisplayName "NVIDIA GPU Metrics Exporter" -StartupType Automatic\nStart-Service "NVIDIA-GPU-Exporter"</code></pre>',
        replace='<div class="ailfix" role="note"><span class="ailfix-tag">Corrected in v0.0.6</span><p>The previous command downloaded from <code>prometheus-community/nvidia_gpu_exporter</code>, a repository that does not exist. The exporter is <a href="https://github.com/utkuozdemir/nvidia_gpu_exporter">utkuozdemir/nvidia_gpu_exporter</a>. It installs through winget and registers itself as a native Windows service, so no NSSM or <code>New-Service</code> step is needed<a class="cite" href="references.html#r56">[56]</a>.</p></div>\n<pre><code># Install machine-wide, then register the native service with the NVML backend\nwinget install --scope machine utkuozdemir.nvidia_gpu_exporter\nnvidia_gpu_exporter install --collect.backend=nvml\nStart-Service nvidia_gpu_exporter\n\n# Let Prometheus on another machine on the subnet scrape port 9835\nNew-NetFirewallRule -DisplayName "Nvidia GPU Exporter" -Direction Inbound -Action Allow `\n    -Protocol TCP -LocalPort 9835 -Profile Private,Domain -RemoteAddress LocalSubnet</code></pre>',
        why="Download URL pointed at a nonexistent repository; service registration replaced by the exporter's own documented install.",
        refs=(56,),
    ),
    Correction(
        key='gpu-nvidia-metric-names',
        page='GPU_monitoring_setup.html',
        find='<li><code>nvidia_smi_power_usage_watts</code>, <code>nvidia_smi_temp_gpu</code></li>',
        replace='<li><code>nvidia_smi_power_draw_watts</code>, <code>nvidia_smi_temperature_gpu</code> <span class="ailfix-inline">names corrected in v0.0.6<a class="cite" href="references.html#r20">[20]</a></span></li>',
        why="Metric names did not match the exporter's documented names.",
        refs=(20,),
    ),
    Correction(
        key='gpu-amd-section',
        page='GPU_monitoring_setup.html',
        find='<p>Monitor ROCm-compatible RDNA 3 / CDNA architectures, including Ryzen AI, Radeon Pro W7000, and Instinct MI series. Requires ROCm 6.x+ runtime.</p>\n\n            <div class="vendor-grid">\n                <div class="vendor-card">\n                    <h3>📦 Exporter Setup</h3>\n                    <pre><code># Install ROCm drivers first, then exporter\ncurl -LO https://github.com/prometheus-community/amd-rocm-exporter/releases/download/v0.8.0/amd-rocm-exporter_0.8.0_windows_amd64.zip\nExpand-Archive -Path amd-rocm-exporter*.zip -DestinationPath C:\\amd-exporter\n\n# Start with ROCm collector enabled\nC:\\amd-exporter\\amd-rocm-exporter.exe --collector.rocm=true\n\n# Register as service\nNew-Service -Name "AMD-GPU-Exporter" -BinaryPathName "C:\\amd-exporter\\amd-rocm-exporter.exe" `\n            -StartupType Automatic</code></pre>\n                </div>\n                <div class="vendor-card">\n                    <h3>📊 Key Metrics</h3>\n                    <ul>\n                        <li><code>rocm_gpu_utilization</code> (% load per pipe)</li>\n                        <li><code>rocm_memory_used_bytes</code> / <code>rocm_memory_total_bytes</code></li>\n                        <li><code>rocm_power_sensor_watts</code>, <code>rocm_temperature_sensor</code></li>\n                        <li><code>rocm_ecc_errors_corrected</code> (if supported)</li>\n                    </ul>\n                </div>\n            </div>\n\n            <h3>Prometheus Target Config</h3>\n            <pre><code>- job_name: \'amd-rocm\'\n  static_configs: [{targets: [\'localhost:9295\']}</code></pre>\n            <div class="note">ℹ️ <strong>Note:</strong> AMD ROCm on Windows requires ROCm 6.1+ and compatible GPU drivers. Verify installation with <code>rocm-smi --showinfo</code>. Exporter defaults to port <code>:9295</code>.</div>',
        replace='<div class="ailfix" role="note"><span class="ailfix-tag">Corrected in v0.0.6</span><p>This section previously installed <code>prometheus-community/amd-rocm-exporter</code> and listed <code>rocm_*</code> metrics. That repository does not exist, and no exporter publishing those metric names could be found. AMD\'s own exporter, <code>amd_smi_exporter</code>, receives no further updates and is Linux-only<a class="cite" href="references.html#r57">[57]</a>, and <code>amd-smi</code> is not supported under WSL<a class="cite" href="references.html#r53">[53]</a>, so the WSL bridge in the folder\'s notes cannot report the GPU either. The route below works for AMD (and NVIDIA and Intel) GPUs on Windows. Full background: <a href="gpu-configuration.html#monitor">GPU configuration, section 13</a>.</p></div>\n            <div class="vendor-grid">\n                <div class="vendor-card">\n                    <h3>📦 Exporter Setup</h3>\n                    <pre><code># gpu collector: vendor-neutral Windows\n# GPU counters, off by default\n.\\windows_exporter.exe `\n  --collectors.enabled "[defaults],gpu"\n\n# Or from the MSI:\nmsiexec /i windows_exporter.msi `\n  --% ENABLED_COLLECTORS="[defaults],gpu"</code></pre>\n                </div>\n                <div class="vendor-card">\n                    <h3>📊 Key Metrics</h3>\n                    <ul>\n                        <li><code>windows_gpu_engine_time_seconds_total</code> (busy time per engine; use <code>rate()</code>)</li>\n                        <li><code>windows_gpu_adapter_memory_dedicated_bytes</code> and its usage counterparts</li>\n                        <li>Temperature and power sensors where the driver exposes them (0.32.x)</li>\n                    </ul>\n                </div>\n            </div>\n\n            <h3>Prometheus Target Config</h3>\n            <pre><code>- job_name: \'windows-gpu\'\n  static_configs: [{targets: [\'localhost:9182\']}]</code></pre>\n            <div class="note">ℹ️ <strong>Note:</strong> the engine counter is named <code>windows_gpu_engine_time_seconds</code> in windows_exporter 0.31.7 (the version in the folder) and gains <code>_total</code> in 0.32.x. On a Linux host with ROCm, use AMD\'s Device Metrics Exporter<a class="cite" href="references.html#r58">[58]</a> instead.</div>',
        why='Section described a nonexistent exporter and metric names; replaced with the documented windows_exporter gpu collector.',
        refs=(53, 55, 57, 58, 86),
    ),
    Correction(
        key='gpu-grafana-nvidia-id',
        page='GPU_monitoring_setup.html',
        find='<p><strong>Dashboard ID:</strong> <code>12574</code></p>',
        replace='<p><strong>Dashboard ID:</strong> <code>14574</code> <span class="ailfix-inline">corrected in v0.0.6: the exporter\'s README names 14574, plus 25547 for a multi-GPU overview<a class="cite" href="references.html#r20">[20]</a></span></p>',
        why='Dashboard id did not match the exporter README.',
        refs=(20,),
    ),
    Correction(
        key='gpu-grafana-amd-card',
        page='GPU_monitoring_setup.html',
        find='<p><strong>Dashboard ID:</strong> <code>16088</code> (Official ROCm/GPU)</p>\n                    <ol>\n                        <li>Repeat import steps above</li>\n                        <li>Maps to <code>rocm_*</code> metric namespace</li>\n                        <li>Supports multi-DIC/pipe aggregation out-of-the-box</li>\n                    </ol>',
        replace='<p><strong>No published dashboard confirmed.</strong> <span class="ailfix-inline">corrected in v0.0.6</span></p>\n                    <ol>\n                        <li>The earlier dashboard ID mapped to a <code>rocm_*</code> namespace no exporter publishes</li>\n                        <li>Build a panel from <code>sum by (phys) (rate(windows_gpu_engine_time_seconds_total{phys="0", engtype="3D"}[1m])) * 100</code><a class="cite" href="references.html#r55">[55]</a></li>\n                        <li>List the engine types your driver reports with <code>count by (engtype) (windows_gpu_engine_time_seconds_total)</code></li>\n                    </ol>',
        why='Dashboard targeted a nonexistent metric namespace.',
        refs=(55,),
    ),
    Correction(
        key='gpu-alert-gauge',
        page='GPU_monitoring_setup.html',
        find='rate(nvidia_smi_power_usage_watts[5m]) > 350</code> or <code>rocm_temperature_sensor > 85</code></li>',
        replace='nvidia_smi_power_draw_watts > 350</code> <span class="ailfix-inline">corrected in v0.0.6: power is a gauge, so <code>rate()</code> does not apply (see <a href="monitoring-sizing.html#counters">counters and gauges</a>); the <code>rocm_*</code> metric does not exist</span></li>',
        why='rate() applied to a gauge; nonexistent metric.',
        refs=(),
    ),
    Correction(
        key='gpu-footer-claim',
        page='GPU_monitoring_setup.html',
        find='<p>Designed for RF/Microwave & Automotive-grade GPU telemetry stacks. All configs validate against Prometheus v2.50+ & Grafana v10.x.</p>',
        replace='<p>Corrected in v0.0.6 against windows_exporter 0.32.1 and nvidia_gpu_exporter 1.19.0. Current versions of every component are on the <a href="downloads.html">downloads page</a>.</p>',
        why='Unverifiable validation claim against superseded versions.',
        refs=(),
    ),
    Correction(
        key='linux-gpu-section',
        page='Grafan_Promethius_install_linux.html',
        find='<p>Most NVIDIA GPUs expose metrics via the <code>nvidia-smi</code> command. To make those available to Prometheus, you can use the <a href="https://github.com/NVIDIA/gpu-prometheus-exporter">nvidia-gpu-prometheus-exporter</a>.</p>\n\n<h3>8.1 Quick install of the exporter</h3>\n<pre># Download latest release\nEXPORTER_VER=0.4.0\nwget https://github.com/NVIDIA/gpu-prometheus-exporter/releases/download/v${EXPORTER_VER}/gpu-prometheus-exporter-linux-amd64.tar.gz\ntar xvf gpu-prometheus-exporter-linux-amd64.tar.gz\nsudo mv gpu-prometheus-exporter-linux-amd64 /opt/gpu-exporter\nsudo ln -s /opt/gpu-exporter/gpu-prometheus-exporter /usr/local/bin/gpu-exporter\n\n# Run it as a service (listens on 9185)\ncat <<\'EOF\' | sudo tee /etc/systemd/system/gpu-exporter.service\n[Unit]\nDescription=NVIDIA GPU Prometheus Exporter\nWants=network-online.target\nAfter=network-online.target\n\n[Service]\nUser=root\nGroup=root\nExecStart=/opt/gpu-exporter/gpu-prometheus-exporter --web.listen-address=:9185\nRestart=always\n\n[Install]\nWantedBy=multi-user.target\nEOF\n\nsudo systemctl daemon-reload\nsudo systemctl enable gpu-exporter\nsudo systemctl start gpu-exporter</pre>\n\n<h3>8.2 Add the GPU exporter to Prometheus</h3>\n<pre># Edit /etc/prometheus/prometheus.yml and add another scrape target:\n- job_name: \'gpu\'\n  static_configs:\n    - targets: [\'localhost:9185\']\n</pre>\n\n<h3>8.3 Query GPU utilisation in Grafana</h3>\n<pre>avg by (instance) (nvidia_gpu_utilization{instance="node-B:9185"})</pre>\n\n<p>You can now plot GPU % alongside CPU, memory, and network charts.</p>',
        replace='<div class="ailfix" role="note"><span class="ailfix-tag">Corrected in v0.0.6</span><p>This section previously downloaded from <code>NVIDIA/gpu-prometheus-exporter</code>, which does not exist, and queried a metric no exporter publishes. The commands below follow the documented install of <a href="https://github.com/utkuozdemir/nvidia_gpu_exporter">nvidia_gpu_exporter</a><a class="cite" href="references.html#r56">[56]</a>.</p></div>\n\n<p>Most NVIDIA GPUs expose metrics via the <code>nvidia-smi</code> command and NVML. To make those available to Prometheus, use <a href="https://github.com/utkuozdemir/nvidia_gpu_exporter">nvidia_gpu_exporter</a>.</p>\n\n<h3>8.1 Quick install of the exporter</h3>\n<pre># Pick the release from https://github.com/utkuozdemir/nvidia_gpu_exporter/releases\nVERSION=1.19.0\nwget https://github.com/utkuozdemir/nvidia_gpu_exporter/releases/download/v${VERSION}/nvidia_gpu_exporter-nvml_${VERSION}_linux_x86_64.tar.gz\ntar -xvzf nvidia_gpu_exporter-nvml_${VERSION}_linux_x86_64.tar.gz\nsudo mv nvidia_gpu_exporter /usr/bin\n\n# Run it as a service with the unit file the project ships (listens on 9835)\nsudo useradd --system --no-create-home --shell /usr/sbin/nologin nvidia_gpu_exporter\nsudo wget -O /etc/systemd/system/nvidia_gpu_exporter.service \\\n  https://raw.githubusercontent.com/utkuozdemir/nvidia_gpu_exporter/master/install/systemd/nvidia_gpu_exporter.service\nsudo systemctl daemon-reload\nsudo systemctl enable --now nvidia_gpu_exporter</pre>\n\n<h3>8.2 Add the GPU exporter to Prometheus</h3>\n<pre># Edit /etc/prometheus/prometheus.yml and add another scrape target:\n- job_name: \'gpu\'\n  static_configs:\n    - targets: [\'localhost:9835\']\n</pre>\n\n<h3>8.3 Query GPU utilisation in Grafana</h3>\n<pre>avg by (instance) (nvidia_smi_utilization_gpu_ratio{instance="node-B:9835"}) * 100</pre>\n\n<p>You can now plot GPU % alongside CPU, memory, and network charts. AMD GPUs on Linux: see <a href="gpu-configuration.html#monitor">GPU configuration, section 13</a>.</p>',
        why="Nonexistent repository and metric; replaced with the exporter's documented Linux install.",
        refs=(56,),
    ),
    Correction(
        key='jupyter-wsl-amd',
        page='Jupyter_Server_Setup_wsl.html',
        find='AMD ROCm Path</h2>\n',
        replace='AMD ROCm Path</h2>\n<div class="ailfix" role="note"><span class="ailfix-tag">Corrected in v0.0.6</span><p>The steps below install kernel modules (<code>rocm-dkms</code>, <code>modprobe amdgpu</code>, <code>update-initramfs</code>) inside WSL. WSL runs Microsoft\'s kernel, and AMD\'s documented WSL procedure installs no kernel packages: Adrenalin driver, WSL with Ubuntu 22.04/24.04, then the ROCDXG user-mode library<a class="cite" href="references.html#r87">[87]</a>. <code>amd-smi</code> is not supported under WSL<a class="cite" href="references.html#r53">[53]</a>, and only the cards in AMD\'s WSL matrix are supported<a class="cite" href="references.html#r52">[52]</a>. <code>HSA_OVERRIDE_GFX_VERSION</code> is a native-Linux mechanism<a class="cite" href="references.html#r40">[40]</a>. The winget package IDs below were not confirmed. Follow AMD\'s how-to for the commands; <a href="gpu-configuration.html#amd">GPU configuration, section 3</a> has the support lists.</p></div>\n',
        why='AMD WSL path used native-Linux kernel steps that do not apply under WSL.',
        refs=(40, 52, 53, 87),
    ),
    Correction(
        key='docker-jupyter-amd',
        page='Dockler_Jupyter_withGPU_Passthru_nssm.html',
        find='AMD ROCm Container Path</h2>\n',
        replace='AMD ROCm Container Path</h2>\n<div class="ailfix" role="note"><span class="ailfix-tag">Corrected in v0.0.6</span><p>Docker Desktop\'s documented GPU passthrough on Windows (<code>--gpus</code>, through WSL 2 GPU paravirtualisation) is described for NVIDIA GPUs<a class="cite" href="references.html#r51">[51]</a>, and <code>/dev/kfd</code> is a native-Linux ROCm device that WSL does not provide<a class="cite" href="references.html#r87">[87]</a>. This container path has no documented support on a Windows host. The routes that work for AMD on Windows are Ollama or llama.cpp running natively, or ROCm inside a WSL distro: see <a href="gpu-configuration.html#docker">GPU configuration, section 12</a>.</p></div>\n',
        why='AMD container path relies on Docker GPU support that Docker documents for NVIDIA only.',
        refs=(51, 87),
    ),
    Correction(
        key='rpc-readme-path',
        page='llama-rpc-vulkan-guide.html',
        find='href="https://github.com/ggml-org/llama.cpp/blob/master/examples/rpc/README.md"',
        replace='href="https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md"',
        why='llama.cpp moved the RPC README from examples/ to tools/.',
        refs=(37,),
    ),
    Correction(
        key='rpc-kitemetric-dead',
        page='llama-rpc-vulkan-guide.html',
        find='<a href="https://kitemetric.com/blogs/remote-ollama-access-a-comprehensive-guide" target="_blank" rel="noopener">https://kitemetric.com/blogs/remote-ollama-access-a-comprehensive-guide</a>',
        replace='<span class="mono">https://kitemetric.com/blogs/remote-ollama-access-a-comprehensive-guide</span> <span class="ailfix-inline">returned HTTP 404 on 2026-11-15</span>',
        why='Cited page no longer exists.',
        refs=(),
    ),
]


# %% Helpers -----------------------------------------------------------------
def for_page(page: str) -> List[Correction]:
    """Return the corrections that apply to one page, in list order."""
    return [c for c in CORRECTIONS if c.page == page]


def apply(page: str, text: str) -> Tuple[str, List[str]]:
    """Apply every correction for ``page`` to ``text``.

    Returns
    -------
    (str, list of str)
        The corrected text and the keys applied.

    Raises
    ------
    ValueError
        When a ``find`` span does not occur exactly once.
    """
    applied: List[str] = []
    for correction in for_page(page):
        count = text.count(correction.find)
        if count != 1:
            raise ValueError(f"correction {correction.key!r} on {page}: find span occurs "
                             f"{count} times (expected exactly 1)")
        text = text.replace(correction.find, correction.replace)
        applied.append(correction.key)
    return text, applied
