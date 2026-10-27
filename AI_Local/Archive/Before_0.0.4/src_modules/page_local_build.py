# -*- coding: utf-8 -*-
"""
page_local_build.py -- body content for local-code-build-test.html

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

PURPOSE
-------
Supplies the body fragment for the page that was missing from the AI_Local set:
how to let a locally hosted model generate code, then build and test that code
on local hardware, through Open WebUI.

The fragment is wrapped in the shared page shell by
``build_ai_local_site.py``; this module emits no ``<html>``, ``<head>``,
``<header>``, ``<nav>``, ``<footer>``, ``<style>`` or ``<script>``, exactly as
the Atomic Theory Atlas ``PATTERNS.md`` requires of a body fragment.

CONTENT SOURCING
----------------
Every environment-variable name, command and admin-panel path is quoted from
the Open WebUI, Ollama, Docker, CMake, conda, mamba, pytest and Jupyter
documentation cited in ``references.py``.  Figures that are not published
anywhere are computed in an equation block from ``eq_library.py`` with the
derivation shown, or are explicitly flagged as planning estimates.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import eq_library


# %% Body fragment -----------------------------------------------------------
def build() -> str:
    """Return the complete body fragment for local-code-build-test.html."""
    return r"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">Local software generation &amp; test</div>
    <h1>Letting a local model build and test code on your own hardware</h1>
    <p class="lead">The rest of this set gets a model answering on your network. This page closes the loop: giving that model a real shell and a real Python environment on a machine you own, so it can write code, compile it, run the tests, read the failures and try again &mdash; with nothing leaving the LAN.</p>
    <p class="small muted">Every equation is tagged <span class="pill stated">Stated</span>, <span class="pill derived">Derived here</span> or <span class="pill data">Measured value</span>, and every one carries an information button that opens a variable table with units. Settings names are quoted verbatim from the vendor documentation listed in <a href="references.html">References</a>.</p>
  </div>
</section>

<section id="on-this-page">
  <div class="container">
    <h2>On this page</h2>
    <ul class="toc">
      <li><a href="#decision">1. Which execution backend to use</a></li>
      <li><a href="#topology">2. Where each piece runs</a></li>
      <li><a href="#open-terminal">3. Open Terminal: the recommended backend</a></li>
      <li><a href="#jupyter">4. The Jupyter engine, for a mamba environment you already own</a></li>
      <li><a href="#mamba">5. Wiring a named mamba environment into the sandbox</a></li>
      <li><a href="#cpp">6. C++ builds: CMake, MSVC and llama.cpp itself</a></li>
      <li><a href="#python">7. Python: qt.py GUIs, Veusz output and GPU paths</a></li>
      <li><a href="#budget">8. Sizing the loop: memory, cores and wall clock</a></li>
      <li><a href="#model-settings">9. Model-side settings that decide whether any of this works</a></li>
      <li><a href="#security">10. Blast radius and what to lock down</a></li>
      <li><a href="#verify">11. Verification sequence</a></li>
      <li><a href="#gaps">12. Known gaps in the public documentation</a></li>
    </ul>
  </div>
</section>

<section id="decision">
  <div class="container">
    <h2>1. Which execution backend to use</h2>

    <p>Open WebUI can run code three ways, and they are not interchangeable. The published documentation marks both of the original Code Interpreter engines as legacy and recommends Open Terminal instead<a class="cite" href="references.html#r1">[1]</a>.</p>

    <div class="table-wrap">
      <table>
        <caption>The three execution backends Open WebUI offers, with the capability that decides between them. Column contents are quoted from the Open WebUI documentation for code execution, the Jupyter integration tutorial and the Open Terminal pages.</caption>
        <thead>
          <tr><th scope="col">Backend</th><th scope="col">Where code runs</th><th scope="col">Can install packages</th><th scope="col">Shell / compiler</th><th scope="col">Per-user isolation</th><th scope="col">Status</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Pyodide</strong></td>
            <td>The reader's browser, as WebAssembly</td>
            <td>No. A fixed package set loads on demand and the model cannot add to it<a class="cite" href="references.html#r1">[1]</a></td>
            <td>None</td>
            <td>Browser sandbox</td>
            <td>Legacy; documented as possibly deprecated<a class="cite" href="references.html#r1">[1]</a></td>
          </tr>
          <tr>
            <td><strong>Jupyter engine</strong></td>
            <td>A Jupyter server you run</td>
            <td>Yes, whatever that kernel's environment allows</td>
            <td>Through the kernel, so <span class="mono">subprocess</span> and <span class="mono">!</span> magics reach the host shell</td>
            <td>None by default. The documentation advises against it for multi-tenant production<a class="cite" href="references.html#r3">[3]</a></td>
            <td>Legacy<a class="cite" href="references.html#r1">[1]</a></td>
          </tr>
          <tr>
            <td><strong>Open Terminal</strong></td>
            <td>A Docker container, or bare metal on the host</td>
            <td>Yes, including system packages, git and ffmpeg<a class="cite" href="references.html#r3">[3]</a></td>
            <td>A full Linux shell; Windows is supported on bare metal through pywinpty<a class="cite" href="references.html#r4">[4]</a></td>
            <td>Per-user workspaces through the separate Terminals orchestrator<a class="cite" href="references.html#r3">[3]</a></td>
            <td>Recommended<a class="cite" href="references.html#r3">[3]</a></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>Recommendation for this deployment.</strong> Use <strong>Open Terminal in Docker</strong> as the default, because it is the only backend that can run a compiler, and it is the one the vendor documentation points at. Keep the <strong>Jupyter engine</strong> alongside it for the specific case covered in &sect;4: driving a <em>named mamba environment that already exists on the host</em>, with your instrument drivers, PySide6 and Veusz already solved. Leave Pyodide on only as a fallback for a reader with no backend at all.</p>
    </div>

    <p>One point that catches people out: <span class="mono">CODE_INTERPRETER_BLOCKED_MODULES</span> exists but the documentation states plainly that it "is not a security boundary" and only blocks direct top-level imports<a class="cite" href="references.html#r1">[1]</a>. Treat it as a guard rail against accidents, never as a containment mechanism.</p>
  </div>
</section>

<section id="topology">
  <div class="container">
    <h2>2. Where each piece runs</h2>

    <p>The four-node layout in the rest of this set has <span class="mono">NODE-A</span> as the inference host at <span class="mono">192.168.7.27</span>, with RPC workers at <span class="mono">.28</span>, <span class="mono">.45</span> and <span class="mono">.181</span><a class="cite" href="references.html#r32">[32]</a>. The execution backend does not have to live on the inference host, and there is a good argument for separating them: a build that saturates sixteen cores and twenty gigabytes of RAM will evict a resident model from page cache and stall token generation for every other user on the network.</p>

    <figure>
      <svg role="img" viewBox="0 0 760 330" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto">
        <title>Service topology: browser to Open WebUI to Ollama or llama-server for inference, and to Open Terminal or Jupyter for execution</title>

        <!-- Browser -->
        <rect x="16" y="130" width="120" height="58" rx="8" fill="none" stroke="currentColor" stroke-width="1.6"/>
        <text x="76" y="155" text-anchor="middle" font-size="13" fill="currentColor">Browser</text>
        <text x="76" y="173" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.72">:3000</text>

        <!-- Open WebUI -->
        <rect x="200" y="118" width="150" height="82" rx="8" fill="none" stroke="currentColor" stroke-width="2.2"/>
        <text x="275" y="146" text-anchor="middle" font-size="13" font-weight="700" fill="currentColor">Open WebUI</text>
        <text x="275" y="164" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.72">control plane</text>
        <text x="275" y="182" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.72">NODE-A :3000</text>

        <!-- Inference column -->
        <rect x="430" y="26" width="160" height="58" rx="8" fill="none" stroke="currentColor" stroke-width="1.6"/>
        <text x="510" y="50" text-anchor="middle" font-size="12" fill="currentColor">Ollama :11434</text>
        <text x="510" y="68" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.72">model serving</text>

        <rect x="430" y="98" width="160" height="58" rx="8" fill="none" stroke="currentColor" stroke-width="1.6"/>
        <text x="510" y="122" text-anchor="middle" font-size="12" fill="currentColor">llama-server :8080</text>
        <text x="510" y="140" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.72">+ RPC workers</text>

        <!-- Execution column -->
        <rect x="430" y="188" width="160" height="58" rx="8" fill="none" stroke="currentColor" stroke-width="2.2"/>
        <text x="510" y="212" text-anchor="middle" font-size="12" font-weight="700" fill="currentColor">Open Terminal :8000</text>
        <text x="510" y="230" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.72">shell + build</text>

        <rect x="430" y="260" width="160" height="58" rx="8" fill="none" stroke="currentColor" stroke-width="1.6"/>
        <text x="510" y="284" text-anchor="middle" font-size="12" fill="currentColor">Jupyter :8888</text>
        <text x="510" y="302" text-anchor="middle" font-size="10.5" fill="currentColor" opacity="0.72">mamba kernel</text>

        <!-- Worker hint -->
        <rect x="638" y="98" width="106" height="58" rx="8" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3"/>
        <text x="691" y="122" text-anchor="middle" font-size="11" fill="currentColor" opacity="0.8">workers</text>
        <text x="691" y="139" text-anchor="middle" font-size="10" fill="currentColor" opacity="0.65">:50052</text>

        <!-- Arrows -->
        <g stroke="currentColor" stroke-width="1.5" fill="none">
          <path d="M136 159 L198 159"/>
          <path d="M350 150 L400 150 L400 55 L428 55"/>
          <path d="M350 155 L410 155 L410 127 L428 127"/>
          <path d="M350 168 L400 168 L400 217 L428 217"/>
          <path d="M350 173 L410 173 L410 289 L428 289"/>
          <path d="M590 127 L636 127" stroke-dasharray="4 3"/>
        </g>
        <g fill="currentColor">
          <path d="M198 159 l-7 -3.4 v6.8 z"/>
          <path d="M428 55 l-7 -3.4 v6.8 z"/>
          <path d="M428 127 l-7 -3.4 v6.8 z"/>
          <path d="M428 217 l-7 -3.4 v6.8 z"/>
          <path d="M428 289 l-7 -3.4 v6.8 z"/>
          <path d="M636 127 l-7 -3.4 v6.8 z"/>
        </g>

        <text x="395" y="24" font-size="10.5" fill="currentColor" opacity="0.7">inference</text>
        <text x="395" y="330" font-size="10.5" fill="currentColor" opacity="0.7">execution</text>
      </svg>
      <figcaption class="small faint">Open WebUI is the control plane only. Inference and code execution are separate services reached over HTTP, so either can be moved to another node without touching the other. Port numbers follow the defaults used elsewhere in this set and the vendor defaults for Open Terminal (8000) and Jupyter (8888).</figcaption>
    </figure>

    <div class="table-wrap">
      <table>
        <caption>Listening ports introduced by this page, to add to the firewall rules already defined for this deployment.</caption>
        <thead><tr><th scope="col">Service</th><th scope="col">Port</th><th scope="col">Source of the default</th><th scope="col">Expose to</th></tr></thead>
        <tbody>
          <tr><td>Open Terminal API</td><td class="mono">8000/tcp</td><td>Documented default<a class="cite" href="references.html#r4">[4]</a></td><td>Open WebUI host only</td></tr>
          <tr><td>Jupyter server</td><td class="mono">8888/tcp</td><td>Tutorial compose file<a class="cite" href="references.html#r2">[2]</a></td><td>Open WebUI host only</td></tr>
          <tr><td><span class="mono">mcpo</span> OpenAPI proxy</td><td class="mono">8000/tcp</td><td>Documented examples<a class="cite" href="references.html#r8">[8]</a></td><td>Open WebUI host only; move off 8000 if Open Terminal already holds it</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong>Port collision.</strong> Open Terminal and <span class="mono">mcpo</span> both default to 8000. If you run both, publish one of them elsewhere &mdash; for example <span class="mono">-p 8010:8000</span> for <span class="mono">mcpo</span> &mdash; and use the published port in the Open WebUI connection URL.</p>
    </div>
  </div>
</section>

<section id="open-terminal">
  <div class="container">
    <h2>3. Open Terminal: the recommended backend</h2>

    <h3>3.1 Run the container</h3>

    <p>The documented Docker invocation is below. The volume at <span class="mono">/home/user</span> is what makes a workspace survive a container restart<a class="cite" href="references.html#r4">[4]</a>.</p>

    <p class="code-label">PowerShell, on the host that will run builds</p>
<pre><code># Open Terminal, with an explicit API key, resource caps, and the capability
# the egress allowlist requires.
#
# --cap-add NET_ADMIN is NOT optional once OPEN_TERMINAL_ALLOWED_DOMAINS is
# set: egress filtering installs dnsmasq and iptables inside the container,
# so without the capability the allowlist does not take effect. Setting the
# variable without the capability gives an unfiltered container that looks
# filtered, which is the worst of the three possible outcomes.
#
# --memory and --cpus are the documented way to stop a runaway build taking
# the host down with it.
docker run -d `
  --name open-terminal `
  --restart unless-stopped `
  -p 8000:8000 `
  --memory 24g `
  --cpus 8 `
  --cap-add NET_ADMIN `
  -v open-terminal:/home/user `
  -e OPEN_TERMINAL_API_KEY=replace-with-a-long-random-string `
  -e OPEN_TERMINAL_ALLOWED_DOMAINS="conda.anaconda.org,repo.anaconda.com,pypi.org,files.pythonhosted.org" `
  ghcr.io/open-webui/open-terminal

# Confirm the API is up. The documented check is the interactive API page.
# Expect the Open Terminal API documentation to render.
Start-Process http://localhost:8000/docs</code></pre>

    <div class="callout danger">
      <p><strong>The API key is no longer optional.</strong> As of v0.11.30 the server refuses to start without one: running <span class="mono">uvicorn</span> directly exits unless <span class="mono">OPEN_TERMINAL_API_KEY</span> is set, and the CLI auto-generates one when you do not supply your own<a class="cite" href="references.html#r36">[36]</a>. The documentation calls a generated key &ldquo;a starting point, not a password&rdquo;. Set your own, and in production keep it off the command line with a config file or a Docker secret &mdash; <span class="mono">OPEN_TERMINAL_API_KEY_FILE</span> reads it from one.</p>
    </div>

    <div class="callout ok">
      <p><strong>Confirm the egress firewall actually came up.</strong> It announces itself at start-up, and the absence of these lines is how you discover the missing capability<a class="cite" href="references.html#r36">[36]</a>:</p>
<pre><code>docker logs open-terminal

Egress: DNS whitelist &mdash; conda.anaconda.org,pypi.org
  &#10003; conda.anaconda.org (+ subdomains)
  &#10003; pypi.org (+ subdomains)
dnsmasq started (upstream: 1.1.1.1)
Egress firewall active &mdash; dropping CAP_NET_ADMIN permanently</code></pre>
      <p>Note the last line: the capability is dropped once the rules are installed, so the container does not keep it. On a host where it cannot be dropped, the container exits at start-up with <span class="mono">unable to raise CAP_SETPCAP for BSET changes</span>, and the documentation points at the host's seccomp and capability settings<a class="cite" href="references.html#r36">[36]</a>. Then test it from inside, which is &sect;11 step&nbsp;11:</p>
<pre><code>docker exec open-terminal curl -sS -m 5 https://pypi.org/simple/    # allowed
docker exec open-terminal curl -sS -m 5 https://example.com/        # DNS fails</code></pre>
    </div>

    <p>Verify the service from inside the Open WebUI container, which is the check the connection guide gives. A working connection prints <span class="mono">{"status": "ok"}</span><a class="cite" href="references.html#r5">[5]</a>.</p>

<pre><code>docker exec open-webui curl -s http://open-terminal:8000/health</code></pre>

    <h3>3.2 Pre-install the toolchain the model will need</h3>

    <p>Three Docker-only variables install packages at container start. The documentation notes that these reinstall on every container start, so a long list costs start-up time<a class="cite" href="references.html#r6">[6]</a>.</p>

    <div class="table-wrap">
      <table>
        <caption>Open Terminal package-installation variables, which apply to the Docker image only, with the values this deployment uses for C++ and Python work.</caption>
        <thead><tr><th scope="col">Variable</th><th scope="col">Installs</th><th scope="col">Value used here</th></tr></thead>
        <tbody>
          <tr><td class="mono">OPEN_TERMINAL_PACKAGES</td><td>System packages</td><td class="mono">build-essential cmake ninja-build git pkg-config</td></tr>
          <tr><td class="mono">OPEN_TERMINAL_PIP_PACKAGES</td><td>Python packages</td><td class="mono">pytest numpy scipy h5py</td></tr>
          <tr><td class="mono">OPEN_TERMINAL_NPM_PACKAGES</td><td>npm packages</td><td>unset</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong>Prefer a derived image for anything substantial.</strong> Because the package variables reinstall on every start, a toolchain of any size belongs in a <span class="mono">Dockerfile</span> that starts <span class="mono">FROM ghcr.io/open-webui/open-terminal</span>. Keep the variables for one or two late additions.</p>
    </div>

    <h3>3.3 Constrain it</h3>

    <p>Four configuration settings matter before this is pointed at a model. The precedence order is built-in defaults, then <span class="mono">/etc/open-terminal/config.toml</span>, then <span class="mono">~/.config/open-terminal/config.toml</span>, then <span class="mono">OPEN_TERMINAL_*</span> environment variables, then CLI flags<a class="cite" href="references.html#r6">[6]</a>.</p>

    <div class="table-wrap">
      <table>
        <caption>Open Terminal settings with a direct bearing on blast radius, with the documented default and the value recommended for a home network.</caption>
        <thead><tr><th scope="col">Setting</th><th scope="col">Default</th><th scope="col">Recommended</th><th scope="col">Why</th></tr></thead>
        <tbody>
          <tr><td class="mono">OPEN_TERMINAL_ALLOWED_DOMAINS</td><td>None</td><td>Your package indexes only, <strong>with <span class="mono">--cap-add NET_ADMIN</span></strong></td><td>An egress firewall: only the listed domains <em>and their subdomains</em> are reachable<a class="cite" href="references.html#r36">[36]</a>. Unset means unrestricted egress. <strong>It installs dnsmasq and iptables in the container, so it needs <span class="mono">NET_ADMIN</span>; set without it, the allowlist silently does nothing</strong></td></tr>
          <tr><td class="mono">OPEN_TERMINAL_CORS_ALLOWED_ORIGINS</td><td class="mono">*</td><td>Your Open WebUI origin</td><td>A start-up warning is emitted when it is unset<a class="cite" href="references.html#r6">[6]</a></td></tr>
          <tr><td class="mono">OPEN_TERMINAL_EXECUTE_TIMEOUT</td><td>Unset</td><td>Longer than your slowest clean build</td><td>Seconds to wait for command output<a class="cite" href="references.html#r6">[6]</a>. Unset plus a 40-minute build is an agent that appears to hang</td></tr>
          <tr><td class="mono">OPEN_TERMINAL_FILE_BROWSER_ROOT</td><td class="mono">home</td><td class="mono">/workspace</td><td>Accepts <span class="mono">home</span>, an explicit path, or <span class="mono">filesystem</span><a class="cite" href="references.html#r6">[6]</a>. <span class="mono">filesystem</span> exposes the whole container</td></tr>
          <tr><td class="mono">OPEN_TERMINAL_MAX_SESSIONS</td><td>16</td><td>2&ndash;4 for a single user</td><td>Caps concurrent terminal sessions<a class="cite" href="references.html#r6">[6]</a>, which also caps how many builds can be started at once</td></tr>
        </tbody>
      </table>
    </div>

    <p><span class="mono">OPEN_TERMINAL_EXECUTE_DESCRIPTION</span> is worth setting as well. It is documented as "custom text telling the AI about installed tools"<a class="cite" href="references.html#r6">[6]</a>, and it is the cheapest way to stop a model trying to <span class="mono">apt-get install</span> a compiler that is already present.</p>

    <h3>3.4 Connect it to Open WebUI</h3>

    <p>The connection steps are specific, and the documentation warns against the wrong panel: adding it under "External Tools" or "Tool Servers" skips the built-in file browser and terminal sidebar<a class="cite" href="references.html#r5">[5]</a>.</p>

    <ol>
      <li>Click your name at the bottom of the left sidebar, then <strong>Settings</strong>.</li>
      <li>Go to <strong>Admin &rarr; Integrations</strong>, not the personal Integrations entry. The Open Terminal section is greyed out if <span class="mono">ENABLE_TOOL_SERVERS</span> is <span class="mono">False</span><a class="cite" href="references.html#r5">[5]</a>.</li>
      <li>In the <strong>Open Terminal</strong> section, click <strong>+</strong> and enter the URL and API key. Leave <strong>Auth Type</strong> as Bearer.</li>
      <li>Save, and confirm the toggle is on. Optionally restrict the connection to a group with the access-control button.</li>
      <li>In <strong>Workspace &rarr; Models</strong>, edit your model and set <strong>Function Calling</strong> to <strong>Native</strong>, which is the default as of v0.10.0. Legacy mode uses prompt-based tool calling and may not trigger terminal commands at all<a class="cite" href="references.html#r5">[5]</a>.</li>
      <li>In a chat, click the terminal button and select the terminal under <strong>System</strong>.</li>
    </ol>

    <div class="table-wrap">
      <table>
        <caption>Connection URL to use for each deployment shape, quoted from the Open Terminal connection guide.</caption>
        <thead><tr><th scope="col">Shape</th><th scope="col">URL</th></tr></thead>
        <tbody>
          <tr><td>Docker Compose, same project</td><td class="mono">http://open-terminal:8000</td></tr>
          <tr><td>Separate containers</td><td class="mono">http://host.docker.internal:8000</td></tr>
          <tr><td>Same machine, no Docker</td><td class="mono">http://localhost:8000</td></tr>
          <tr><td>Another machine</td><td class="mono">http://&lt;that-machine-ip&gt;:8000</td></tr>
        </tbody>
      </table>
    </div>

    <p>To pre-seed the connection at start-up rather than clicking through the panel, the documentation names <span class="mono">TERMINAL_SERVER_CONNECTIONS</span>, but does not publish its format<a class="cite" href="references.html#r5">[5]</a>. That gap is recorded in &sect;12.</p>
  </div>
</section>

<section id="jupyter">
  <div class="container">
    <h2>4. The Jupyter engine, for a mamba environment you already own</h2>

    <p>Open Terminal is the better default, but it cannot see the host's mamba environments. When the point of the exercise is to run code against an environment that already has PySide6, Veusz, h5py and instrument drivers resolved &mdash; the <span class="mono">Py3p12</span> environments in this repository<a class="cite" href="references.html#r30">[30]</a> &mdash; the Jupyter engine pointed at a kernel in that environment is the shorter path.</p>

    <h3>4.1 The variables</h3>

    <p>Twelve variables, from the Jupyter integration tutorial<a class="cite" href="references.html#r2">[2]</a>. Three properties of them are easy to get wrong and each one produces a silent failure.</p>

    <div class="table-wrap">
      <table>
        <caption>Open WebUI variables for the Jupyter execution backend, with the values for a Jupyter server reachable at <span class="mono">host.docker.internal:8888</span>. Names and accepted values are quoted from the Jupyter integration tutorial.</caption>
        <thead><tr><th scope="col">Variable</th><th scope="col">Value</th><th scope="col">Note</th></tr></thead>
        <tbody>
          <tr><td class="mono">ENABLE_CODE_INTERPRETER</td><td class="mono">True</td><td>Global toggle, default <span class="mono">true</span><a class="cite" href="references.html#r1">[1]</a></td></tr>
          <tr><td class="mono">CODE_EXECUTION_ENGINE</td><td class="mono">jupyter</td><td>The manual Run button</td></tr>
          <tr><td class="mono">CODE_EXECUTION_JUPYTER_URL</td><td class="mono">http://host.docker.internal:8888</td><td>&mdash;</td></tr>
          <tr><td class="mono">CODE_EXECUTION_JUPYTER_AUTH</td><td class="mono">token</td><td>Accepts only <span class="mono">token</span> or <span class="mono">password</span>; any other value sends no credentials at all</td></tr>
          <tr><td class="mono">CODE_EXECUTION_JUPYTER_AUTH_TOKEN</td><td>your token</td><td>Must equal Jupyter's <span class="mono">JUPYTER_TOKEN</span></td></tr>
          <tr><td class="mono">CODE_EXECUTION_JUPYTER_TIMEOUT</td><td class="mono">60</td><td>Seconds; raise it for anything that compiles</td></tr>
          <tr><td class="mono">CODE_INTERPRETER_ENGINE</td><td class="mono">jupyter</td><td><strong>Set this explicitly.</strong> It defaults to <span class="mono">pyodide</span> and does <em>not</em> inherit from <span class="mono">CODE_EXECUTION_ENGINE</span></td></tr>
          <tr><td class="mono">CODE_INTERPRETER_JUPYTER_URL</td><td>same as above</td><td>Defaults to its <span class="mono">CODE_EXECUTION_*</span> counterpart</td></tr>
          <tr><td class="mono">CODE_INTERPRETER_JUPYTER_AUTH</td><td class="mono">token</td><td>Defaults to its counterpart</td></tr>
          <tr><td class="mono">CODE_INTERPRETER_JUPYTER_AUTH_TOKEN</td><td>your token</td><td>Defaults to its counterpart</td></tr>
          <tr><td class="mono">CODE_INTERPRETER_JUPYTER_TIMEOUT</td><td class="mono">60</td><td>Defaults to its counterpart</td></tr>
          <tr><td class="mono">ENABLE_ORJSON</td><td class="mono">True</td><td>On by default; speeds output on the Jupyter engine. Read at start-up, so restart after changing it</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout danger">
      <p><strong>Three traps, each of which fails silently.</strong></p>
      <p><strong>1. The engine variable does not inherit.</strong> <span class="mono">CODE_INTERPRETER_ENGINE</span> defaults to <span class="mono">pyodide</span> regardless of <span class="mono">CODE_EXECUTION_ENGINE</span>. Set both, or the model keeps running code in the browser while the manual Run button uses Jupyter, and the symptom is a model that cannot see files it just wrote.</p>
      <p><strong>2. These are persisted settings.</strong> An environment variable takes effect only on the first start with a fresh database; after that the saved value wins unless <span class="mono">ENABLE_PERSISTENT_CONFIG=False</span><a class="cite" href="references.html#r2">[2]</a>. On an existing install, change the values in <strong>Settings &rarr; Admin &rarr; Code Execution</strong>, not in <span class="mono">docker run</span>. <span class="mono">ENABLE_PERSISTENT_CONFIG</span> is documented as controlling "whether the system prioritizes configuration saved in the database over environment variables"<a class="cite" href="references.html#r7">[7]</a>.</p>
      <p><strong>3. The auth value is strict.</strong> Anything other than <span class="mono">token</span> or <span class="mono">password</span> sends no credentials, which presents as a connection that fails without a useful error.</p>
    </div>

    <h3>4.2 Kernel lifetime, and what that means for a build</h3>

    <p>The tutorial states that each run uses a fresh kernel which is deleted afterwards: variables do not persist between runs, but files written to disk do<a class="cite" href="references.html#r2">[2]</a>. That single property dictates how the model has to work.</p>

    <div class="table-wrap">
      <table>
        <caption>Consequences of per-run kernel disposal for a write-build-test loop on the Jupyter engine.</caption>
        <thead><tr><th scope="col">Consequence</th><th scope="col">What to do about it</th></tr></thead>
        <tbody>
          <tr><td>An object built in step 1 is gone by step 2</td><td>Persist state to disk between steps. HDF5 through <span class="mono">h5py</span>, or a pickle, is the natural choice for numeric work</td></tr>
          <tr><td>A <span class="mono">sys.path</span> edit does not carry forward</td><td>Install the package under test in editable mode once, from the shell, rather than patching the path per run</td></tr>
          <tr><td>A compile in step 1 and a link in step 2 share only the filesystem</td><td>Keep the whole build inside one cell, driven by <span class="mono">subprocess.run</span>, so it succeeds or fails as a unit</td></tr>
          <tr><td>Long builds hit the timeout</td><td>Raise both <span class="mono">*_JUPYTER_TIMEOUT</span> values above the slowest clean build, or fire the build off and poll a log file</td></tr>
        </tbody>
      </table>
    </div>

    <p>The Jupyter engine also uses Jupyter's own filesystem, which means the Open WebUI file browser and the <span class="mono">/mnt/uploads/</span> path are unavailable<a class="cite" href="references.html#r1">[1]</a>. Files have to be moved in and out through the Jupyter work directory.</p>
  </div>
</section>

<section id="mamba">
  <div class="container">
    <h2>5. Wiring a named mamba environment into the sandbox</h2>

    <p>This deployment's Python work lives in mamba environments created from YAML, with <span class="mono">CONDA_ENVS_DIRS</span> pointing at a chosen directory<a class="cite" href="references.html#r30">[30]</a>. Two routes expose such an environment to a model, and the choice follows from whether the environment must stay on the host.</p>

    <h3>5.1 Route A: environment on the host, reached through a Jupyter kernel</h3>

    <p>Register the environment as a named Jupyter kernel, then point the Jupyter engine at that server. Kernel registration is a one-time step per environment.</p>

    <p class="code-label">PowerShell, on the host holding the environment</p>
<pre><code># 1. Install the kernel machinery and the test runner INTO the target
#    environment. -n selects the environment by name; conda env create
#    documents -n/--name as "Name of environment".
mamba install -n Py3p12 ipykernel jupyter_server pytest -y

# 2. Register the environment as a Jupyter kernel. The --name is the kernel
#    id used in API calls; --display-name is what a human sees in a picker.
mamba run -n Py3p12 python -m ipykernel install --user `
  --name py3p12 `
  --display-name "Python 3.12 (Py3p12 mamba)"

# 3. Confirm it registered.
mamba run -n Py3p12 jupyter kernelspec list</code></pre>

    <p class="code-label">PowerShell &mdash; start the server Open WebUI will talk to</p>
<pre><code># ServerApp.ip and ServerApp.open_browser are the documented public-server
# options [29]; JUPYTER_TOKEN is the variable the Open WebUI tutorial sets on
# the Jupyter container [2], and it must match CODE_*_JUPYTER_AUTH_TOKEN.
$env:JUPYTER_TOKEN = "replace-with-a-long-random-string"

mamba run -n Py3p12 jupyter server `
  --ServerApp.ip='0.0.0.0' `
  --ServerApp.port=8888 `
  --ServerApp.open_browser=False `
  --ServerApp.root_dir="C:\ai_workspace"</code></pre>

    <p class="small muted">The Jupyter Server documentation gives <span class="mono">c.ServerApp.ip = '*'</span> as the way to "bind on all interfaces (ips) for the public server" and <span class="mono">c.ServerApp.open_browser = False</span> alongside it<a class="cite" href="references.html#r29">[29]</a>; <span class="mono">0.0.0.0</span> is used above because it is the form the Open WebUI container resolves against. The token is supplied through <span class="mono">JUPYTER_TOKEN</span>, which is the variable the Open WebUI integration tutorial sets<a class="cite" href="references.html#r2">[2]</a>, and it must equal the <span class="mono">CODE_*_JUPYTER_AUTH_TOKEN</span> values from &sect;4.1.</p>

    <div class="callout">
      <p><strong>Bind deliberately.</strong> <span class="mono">0.0.0.0</span> is required for the Open WebUI container to reach the server, and it also exposes the kernel to everything that can route to the host. Pair it with a firewall rule that admits only the Open WebUI host, in the same style as the rules already defined for this deployment: <span class="mono">-RemoteAddress 192.168.7.27</span> rather than the whole subnet.</p>
    </div>

    <p>Run it as a service with NSSM, exactly as the other services in this set are run, so it survives a reboot:</p>

<pre><code>C:\tools\nssm.exe install JupyterCodeEval `
  "C:\Users\&lt;you&gt;\miniforge3\envs\Py3p12\Scripts\jupyter.exe" `
  "server --ServerApp.ip=0.0.0.0 --ServerApp.port=8888 --ServerApp.open_browser=False --ServerApp.root_dir=C:\ai_workspace"

C:\tools\nssm.exe set JupyterCodeEval AppEnvironmentExtra JUPYTER_TOKEN=replace-with-a-long-random-string
C:\tools\nssm.exe set JupyterCodeEval Start SERVICE_AUTO_START
C:\tools\nssm.exe set JupyterCodeEval AppStdout C:\logs\jupyter-codeeval.log
C:\tools\nssm.exe set JupyterCodeEval AppStderr C:\logs\jupyter-codeeval-err.log
Start-Service JupyterCodeEval</code></pre>

    <h3>5.2 Route B: environment rebuilt inside Open Terminal</h3>

    <p>Keeps the host clean and gives the model a compiler. The environment is reproduced from the same YAML, so the two routes stay in step.</p>

    <p class="code-label">Dockerfile &mdash; Open Terminal with micromamba</p>
<pre><code>FROM ghcr.io/open-webui/open-terminal

# Build toolchain. Installed in the image rather than through
# OPEN_TERMINAL_PACKAGES, because that variable reinstalls on every start.
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential cmake ninja-build git ca-certificates bzip2 curl \
 && rm -rf /var/lib/apt/lists/*

# micromamba: a single static binary, no shell initialisation needed.
ENV MAMBA_ROOT_PREFIX=/opt/micromamba
RUN mkdir -p /opt/micromamba \
 && curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest \
      | tar -xvj -C /usr/local bin/micromamba

# Create the environment from the project's own YAML, so the container and
# the host resolve the same specification.
COPY Py3p12_Clean.yml /tmp/Py3p12_Clean.yml
RUN micromamba create -y -n Py3p12 -f /tmp/Py3p12_Clean.yml \
 && micromamba clean --all --yes

# Tell the model what it has, so it does not try to install a compiler.
ENV OPEN_TERMINAL_EXECUTE_DESCRIPTION="Debian with build-essential, cmake and ninja. Python lives in the micromamba environment 'Py3p12'; run Python as: micromamba run -n Py3p12 python ..."
ENV OPEN_TERMINAL_FILE_BROWSER_ROOT=/workspace

RUN mkdir -p /workspace &amp;&amp; chown -R user:user /workspace
USER user
WORKDIR /workspace</code></pre>

    <h3>5.3 The invocation that matters</h3>

    <p>Inside a sandbox, <span class="mono">mamba activate</span> is the wrong tool. Activation requires a shell hook, and each command the model issues may run in a fresh shell. <span class="mono">run</span> is the documented alternative; the micromamba user guide gives <span class="mono">micromamba run -p /tmp/env pytest myproject/tests</span> and notes it is useful in CI and Docker environments, "where running shell activation hooks is complicated"<a class="cite" href="references.html#r25">[25]</a>.</p>

    <div class="table-wrap">
      <table>
        <caption>Environment invocation forms, and which to put in a model's system prompt. The <span class="mono">-n</span>/<span class="mono">-p</span>/<span class="mono">-f</span> flags are documented in the conda command reference and the micromamba user guide.</caption>
        <thead><tr><th scope="col">Form</th><th scope="col">Behaviour</th><th scope="col">Use in a sandbox</th></tr></thead>
        <tbody>
          <tr><td class="mono">mamba activate Py3p12</td><td>Mutates the current shell; needs the shell hook installed</td><td>No. Fails or silently no-ops in a fresh shell</td></tr>
          <tr><td class="mono">mamba run -n Py3p12 &lt;cmd&gt;</td><td>Runs one command with the environment applied</td><td><strong>Yes.</strong> Stateless and the form to standardise on</td></tr>
          <tr><td class="mono">micromamba run -p /opt/envs/Py3p12 &lt;cmd&gt;</td><td>Same, selecting by full prefix path</td><td>Yes, when the environment is outside the configured <span class="mono">envs_dirs</span></td></tr>
          <tr><td class="mono">/opt/envs/Py3p12/bin/python</td><td>Calls the interpreter directly</td><td>Works, and is the most explicit. Misses environment variables an activation script would set</td></tr>
          <tr><td class="mono">mamba env create -f env.yml -n Py3p12</td><td>Creates from a YAML specification<a class="cite" href="references.html#r24">[24]</a></td><td>Setup only, not per task</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>Put the form in the system prompt.</strong> A model given a bare shell will reach for <span class="mono">python</span> and get the container's system interpreter, then report that <span class="mono">PySide6</span> is not installed. One sentence in <span class="mono">OPEN_TERMINAL_EXECUTE_DESCRIPTION</span> or the model's system prompt &mdash; "run Python only as <span class="mono">micromamba run -n Py3p12 python</span>" &mdash; removes an entire class of wasted iteration.</p>
    </div>
  </div>
</section>

<section id="cpp">
  <div class="container">
    <h2>6. C++ builds: CMake, MSVC and llama.cpp itself</h2>

    <p>The compiler invocations already recorded for this deployment pass absolute paths to <span class="mono">cl.exe</span> and <span class="mono">nvcc.exe</span>, with <span class="mono">-DCMAKE_CUDA_ARCHITECTURES=61</span><a class="cite" href="references.html#r32">[32]</a>. That is correct for a hand-driven build and poor material for a model: the MSVC toolset version is embedded in the path, so the command breaks after a Visual Studio update, and a model has no way to discover the new one.</p>

    <h3>6.1 Give the model a script, not a command line</h3>

    <p>A wrapper script makes the build one call with no arguments to get wrong, and gives a single place to fix a toolchain change.</p>

    <p class="code-label">scripts/build_cpp.ps1 (Windows, MSVC)</p>
<pre><code>&lt;#
.SYNOPSIS
    Configure and build a CMake project with a bounded job count.
.DESCRIPTION
    Written to be called by a model with no arguments. Discovers the MSVC
    toolchain with vswhere rather than hard-coding a toolset version, and
    caps parallelism from available memory so a build cannot evict a
    resident model from RAM.
.NOTES
    Author : William W. Wallace
    Version: 0.0.1
#&gt;
[CmdletBinding()]
param(
    [string]$SourceDir = ".",
    [string]$BuildDir  = "build",
    [ValidateSet("Debug","Release","RelWithDebInfo")]
    [string]$Config    = "Release",
    # 0 means "derive from cores and free memory" (see the equation on this page).
    [int]$Jobs         = 0,
    [double]$MemPerJobGB = 2.0
)

$ErrorActionPreference = "Stop"

# -- Locate the toolchain -------------------------------------------------
# vswhere ships with every VS 2017+ installer at a fixed path, so this is
# stable where a hard-coded MSVC toolset path is not.
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) {
    throw "vswhere not found at $vswhere. Install the VS Build Tools."
}
$vsRoot = &amp; $vswhere -latest -products * `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath
if (-not $vsRoot) { throw "No MSVC C++ toolset found by vswhere." }
Write-Host "MSVC toolchain: $vsRoot"

# -- Derive a safe job count ---------------------------------------------
if ($Jobs -le 0) {
    $cores = [Environment]::ProcessorCount
    # FreePhysicalMemory is in KiB; convert to GiB.
    $freeGB = (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB
    $byMem  = [Math]::Floor($freeGB / $MemPerJobGB)
    $Jobs   = [Math]::Max(1, [Math]::Min($cores, $byMem))
    Write-Host ("Jobs: {0} (cores {1}, free {2:N1} GiB at {3} GiB/job)" `
                -f $Jobs, $cores, $freeGB, $MemPerJobGB)
}

# CMAKE_BUILD_PARALLEL_LEVEL is equivalent to passing --parallel, and holds
# even if a nested script invokes the build without the flag.
$env:CMAKE_BUILD_PARALLEL_LEVEL = $Jobs

# -- Configure ------------------------------------------------------------
# Ninja Multi-Config is preferred over the VS generator: it is faster and
# its output is far easier for a model to parse than MSBuild's.
cmake -S $SourceDir -B $BuildDir -G "Ninja Multi-Config"
if ($LASTEXITCODE -ne 0) { throw "CMake configure failed ($LASTEXITCODE)." }

# -- Build ----------------------------------------------------------------
cmake --build $BuildDir --config $Config --parallel $Jobs
if ($LASTEXITCODE -ne 0) { throw "Build failed ($LASTEXITCODE)." }

Write-Host "Build succeeded: $BuildDir ($Config, $Jobs jobs)"</code></pre>

    <p>The parallel-level variable is documented as specifying "the maximum number of concurrent processes to use when building using the <span class="mono">cmake --build</span> command line Build Tool Mode", and setting it to 8 behaves as if <span class="mono">--parallel 8</span> had been passed<a class="cite" href="references.html#r27">[27]</a>. Setting it in the environment rather than only on the command line is what makes the cap survive a nested invocation.</p>

    <h3>6.2 The job count is a memory question, not a core question</h3>

    """ + eq_library.get("parallel-jobs") + r"""

    """ + eq_library.get("amdahl") + r"""

    <h3>6.3 Rebuilding llama.cpp from the sandbox</h3>

    <p>The CUDA and Vulkan configure line recorded for this deployment, with the absolute compiler paths removed so CMake discovers them<a class="cite" href="references.html#r32">[32]</a>:</p>

<pre><code># Run from a Developer PowerShell, so the MSVC environment is already set
# and CMake needs no explicit CMAKE_C_COMPILER / CMAKE_CXX_COMPILER.
# -DGGML_RPC=ON is what builds rpc-server for the distributed setup.
cmake -S . -B build `
  -G "Ninja Multi-Config" `
  -DGGML_VULKAN=ON `
  -DGGML_CUDA=ON `
  -DGGML_RPC=ON `
  -DGGML_CCACHE=OFF `
  -DCMAKE_CUDA_ARCHITECTURES=61

cmake --build build --config Release --parallel $env:CMAKE_BUILD_PARALLEL_LEVEL</code></pre>

    <div class="callout">
      <p><strong><span class="mono">CMAKE_CUDA_ARCHITECTURES=61</span> is specific to this hardware.</strong> 61 is Pascal. A model copying this line onto a different card produces binaries that will not run on it. State the target architecture in the system prompt, or set <span class="mono">native</span> and let CMake detect it.</p>
    </div>

    <h3>6.4 Making failures legible</h3>

    <p>A model's iteration count depends almost entirely on how good the error text is, and <span class="mono">N_{it}</span> multiplies every other term in the loop equation in &sect;8.</p>

    <div class="table-wrap">
      <table>
        <caption>Build-output settings that reduce the number of agent iterations, with the reason each one helps.</caption>
        <thead><tr><th scope="col">Setting</th><th scope="col">Effect</th></tr></thead>
        <tbody>
          <tr><td class="mono">-G "Ninja Multi-Config"</td><td>Ninja's errors are the compiler's own text. MSBuild interleaves project banners and timing that a model will try to interpret</td></tr>
          <tr><td class="mono">/diagnostics:caret</td><td>MSVC points at the offending column, which is what lets a model find the right line without re-reading the file</td></tr>
          <tr><td class="mono">-fdiagnostics-color=never</td><td>On GCC and Clang, strips ANSI escapes that otherwise reach the model as noise</td></tr>
          <tr><td class="mono">CMAKE_EXPORT_COMPILE_COMMANDS=ON</td><td>Writes <span class="mono">compile_commands.json</span>, so a model can read the exact flags for one file instead of guessing</td></tr>
          <tr><td class="mono">2&gt;&amp;1 | Tee-Object build.log</td><td>Keeps the failure on disk. Essential when the output is longer than the tool result the model is handed</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="python">
  <div class="container">
    <h2>7. Python: qt.py GUIs, Veusz output and GPU paths</h2>

    <h3>7.1 Test invocation</h3>

    <p>pytest is documented as invoked either as <span class="mono">pytest</span> or through the interpreter as <span class="mono">python -m pytest</span><a class="cite" href="references.html#r28">[28]</a>. Inside a sandbox the second form is the one to standardise on, because it removes any doubt about which interpreter is running.</p>

<pre><code># Whole suite, in the project's own environment.
micromamba run -n Py3p12 python -m pytest -q

# One module, then one test: the node-id forms documented in the pytest
# usage guide. Narrowing like this is how a model should iterate.
micromamba run -n Py3p12 python -m pytest tests/test_sparams.py -q
micromamba run -n Py3p12 python -m pytest tests/test_sparams.py::test_gating -q

# Select by name expression, also documented.
micromamba run -n Py3p12 python -m pytest -k "gating and not slow" -q</code></pre>

    <h3>7.2 A GUI cannot be tested in a headless sandbox the way it is run</h3>

    <p>Qt work in this repository uses the <span class="mono">qtpy</span> abstraction over PySide6<a class="cite" href="references.html#r30">[30]</a>. A container has no display, so a model that writes a Qt test and runs it will see an abort and will not know why.</p>

    <div class="table-wrap">
      <table>
        <caption>Approaches to exercising Qt code from a headless sandbox, in increasing order of fidelity and cost.</caption>
        <thead><tr><th scope="col">Approach</th><th scope="col">What it covers</th><th scope="col">Cost</th></tr></thead>
        <tbody>
          <tr><td>Keep the model out of GUI code</td><td>Nothing. Model works on the computation layer; widgets stay hand-written</td><td>None. The honest default</td></tr>
          <tr><td><span class="mono">QT_QPA_PLATFORM=offscreen</span></td><td>Construction, signals, slots, layout logic. No pixels</td><td>One environment variable</td></tr>
          <tr><td><span class="mono">pytest-qt</span> plus offscreen</td><td>The above plus event-loop interaction and signal waiting</td><td>One dependency</td></tr>
          <tr><td>Xvfb virtual display (Linux container)</td><td>Real rendering, so screenshots are possible</td><td>A package and a wrapper command</td></tr>
          <tr><td>Host-side run</td><td>Everything, on the real display</td><td>Needs Route A in &sect;5, and a human looking at it</td></tr>
        </tbody>
      </table>
    </div>

<pre><code># Offscreen Qt. The platform plugin is chosen by this variable, so the test
# command is otherwise unchanged.
OPEN_TERMINAL_PIP_PACKAGES="pytest pytest-qt"   # or put it in the image

QT_QPA_PLATFORM=offscreen micromamba run -n Py3p12 python -m pytest tests/test_gui.py -q</code></pre>

    <div class="callout info-box">
      <p><strong>Say so in the system prompt.</strong> "This container has no display. Qt tests must set <span class="mono">QT_QPA_PLATFORM=offscreen</span>; do not attempt to screenshot a window." Without that sentence a model will spend iterations rediscovering it, and may conclude the code is broken when the environment is.</p>
    </div>

    <h3>7.3 Veusz and plot output</h3>

    <p>Data-reduction work in this repository writes Veusz output, including the native <span class="mono">.vszh5</span> HDF5 container through <span class="mono">h5py</span><a class="cite" href="references.html#r30">[30]</a>. That is well suited to a sandbox: the artefact is a file, so it can be written in the container, checked by assertion, and retrieved through the file browser without any display.</p>

<pre><code># Verify a plot artefact structurally rather than visually. A model can
# assert on this; it cannot assert on a picture.
micromamba run -n Py3p12 python - &lt;&lt;'PY'
import h5py

# .vszh5 is an HDF5 container, so its structure is inspectable offline.
with h5py.File("out/run_001.vszh5", "r") as handle:
    keys = sorted(handle.keys())
    print("top-level groups:", keys)
    assert keys, "no datasets written"
PY</code></pre>

    <h3>7.4 GPU work inside the container</h3>

    <p>A container reaches the GPU only if it was started with access. Docker documents <span class="mono">--gpus all</span> for every device, <span class="mono">--gpus device=0</span> for one by index, and <span class="mono">--gpus '"device=0,2"'</span> for several, and names the NVIDIA Container Toolkit as the prerequisite alongside the host drivers<a class="cite" href="references.html#r26">[26]</a>.</p>

<pre><code># Open Terminal with one GPU, leaving the others for inference. The whole
# point of device= rather than all: a build or a CuPy test must not take
# the card the model itself is running on.
docker run -d `
  --name open-terminal `
  --restart unless-stopped `
  --gpus device=1 `
  -p 8000:8000 `
  -v open-terminal:/home/user `
  -e OPEN_TERMINAL_API_KEY=replace-with-a-long-random-string `
  open-terminal-mamba:0.0.1

# Confirm the device is visible from inside, per the documented example form.
docker exec open-terminal nvidia-smi</code></pre>

    <div class="callout">
      <p><strong>Do not hand the model the inference GPU.</strong> If the container shares the card that holds the model weights, a CuPy or PyTorch allocation inside a test can exhaust VRAM and abort the model server. Use <span class="mono">device=</span> to give the sandbox a different card, or no card at all.</p>
    </div>
  </div>
</section>

<section id="budget">
  <div class="container">
    <h2>8. Sizing the loop: memory, cores and wall clock</h2>

    <p>Deciding what hardware this needs means knowing where the time goes. The relation below separates the model's contribution from the toolchain's, and the two worked examples in its derivation reach opposite conclusions about where to spend.</p>

    """ + eq_library.get("agent-loop") + r"""

    <div class="table-wrap">
      <table>
        <caption>Where the wall clock goes for two representative tasks, computed in the derivation above from the same model figures. Model rates are the planning figures used throughout this set; substitute your own measurements.</caption>
        <thead><tr><th scope="col">Task</th><th scope="col">Per iteration</th><th scope="col">Generation share</th><th scope="col">Total, 3 iterations</th><th scope="col">Where to spend</th></tr></thead>
        <tbody>
          <tr><td>Python edit, fast tests</td><td class="mono">72.6 s</td><td class="mono">73 %</td><td class="mono">218 s</td><td>A faster model, or a smaller one</td></tr>
          <tr><td>C++ edit, incremental build</td><td class="mono">201.6 s</td><td class="mono">26 %</td><td class="mono">605 s</td><td>A better model that converges in fewer iterations; faster storage and ccache</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>The conclusion is not symmetric.</strong> For Python work, decode speed dominates and the smallest model that gets the answer right wins. For compiled work, the build dominates and model quality is nearly free, because a model that converges in two iterations instead of three saves more than any decode speed-up available locally. Match the model to the language, not to the machine.</p>
    </div>
  </div>
</section>

<section id="model-settings">
  <div class="container">
    <h2>9. Model-side settings that decide whether any of this works</h2>

    <p>Three settings outside the execution backend determine whether a model can use it at all. Each has a failure mode that looks like a broken sandbox.</p>

    <div class="table-wrap">
      <table>
        <caption>Model and server settings required for tool-driven code execution, with the symptom each produces when it is wrong.</caption>
        <thead><tr><th scope="col">Setting</th><th scope="col">Where</th><th scope="col">Required value</th><th scope="col">Symptom when wrong</th></tr></thead>
        <tbody>
          <tr>
            <td>Function Calling</td>
            <td>Workspace &rarr; Models &rarr; edit model</td>
            <td><strong>Native</strong>, the default as of v0.10.0</td>
            <td>Legacy mode uses prompt-based tool calling, is less reliable, and "may not trigger terminal commands"<a class="cite" href="references.html#r5">[5]</a></td>
          </tr>
          <tr>
            <td>Code Interpreter capability</td>
            <td>Settings &rarr; Admin &rarr; Models</td>
            <td>Enabled per model<a class="cite" href="references.html#r1">[1]</a></td>
            <td>The model writes code and never runs it</td>
          </tr>
          <tr>
            <td class="mono">ENABLE_CODE_EXECUTION</td>
            <td>Open WebUI environment</td>
            <td><span class="mono">true</span> only if you want the in-chat Run button</td>
            <td>Separate from <span class="mono">ENABLE_CODE_INTERPRETER</span>: this one governs executing code blocks in a response, that one governs the model running code as part of its reasoning. Both default to <span class="mono">true</span> on the Pyodide engine, and the hardening guidance is to set them <span class="mono">false</span> where code execution is not required<a class="cite" href="references.html#r36">[36]</a>. On a deployment driving Open Terminal, neither is needed</td>
          </tr>
          <tr>
            <td class="mono">OLLAMA_CONTEXT_LENGTH</td>
            <td>Ollama server environment</td>
            <td><strong>64000 or more</strong>, which is the figure Ollama's own documentation gives for agents and coding tools<a class="cite" href="references.html#r35">[35]</a></td>
            <td>The default is chosen from VRAM, not fixed: under 24&nbsp;GiB it is 4k, which a build log plus source plus history overruns immediately &mdash; the prompt is truncated and the model loses the error it was fixing. See the note below</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout danger">
      <p><strong>A short context window is the single most common cause of a local agent that "goes in circles".</strong> A C++ compiler error with template instantiation backtraces can be several thousand tokens by itself. Raise <span class="mono">OLLAMA_CONTEXT_LENGTH</span> before concluding a model is incapable &mdash; then size the result against VRAM with the context-budget relation on the <a href="ollama-model-selection.html#eq-ctx-budget">model selection page</a>, because the cache grows linearly with it.</p>
    </div>

    <div class="callout info-box">
      <p><strong>The default is no longer a single number, and the widely repeated &ldquo;4096&rdquo; is now only the bottom rung.</strong> Ollama selects a default context length from the available VRAM<a class="cite" href="references.html#r35">[35]</a>:</p>
    </div>

    <div class="table-wrap">
      <table>
        <caption>Ollama's VRAM-tiered default context length, quoted from its context-length documentation. The practical consequence is that the same <span class="mono">ollama serve</span> on two machines gives two different windows, so the default cannot be assumed from one node to another.</caption>
        <thead><tr><th scope="col">Available VRAM</th><th scope="col">Default context</th><th scope="col">Enough for an agent loop?</th></tr></thead>
        <tbody>
          <tr><td class="mono">&lt; 24 GiB</td><td class="mono">4k</td><td><strong>No.</strong> One compiler error can exhaust it</td></tr>
          <tr><td class="mono">24&ndash;48 GiB</td><td class="mono">32k</td><td>Workable for single-file edits, short of the documented 64000 for agent work</td></tr>
          <tr><td class="mono">&ge; 48 GiB</td><td class="mono">256k</td><td>Yes, and likely more than the cache budget actually allows &mdash; check it</td></tr>
        </tbody>
      </table>
    </div>

    <p>The documentation states plainly that &ldquo;tasks which require large context like web search, agents, and coding tools should be set to at least 64000 tokens&rdquo;, and that raising it increases the memory required<a class="cite" href="references.html#r35">[35]</a>. Those two sentences pull in opposite directions, which is exactly what the context-budget relation is for: 64000 tokens is the target, and the relation tells you whether the card can allocate it.</p>

    <div class="callout ok">
      <p><strong>Verify rather than assume, with one command.</strong> <span class="mono">ollama ps</span> now reports the allocated context alongside the processor split<a class="cite" href="references.html#r35">[35]</a>, so both failure modes &mdash; a window shorter than you set, and weights spilled to the CPU &mdash; are visible in the same output:</p>
<pre><code>ollama ps

NAME             ID              SIZE      PROCESSOR    CONTEXT    UNTIL
gemma4:latest    c6eb396dbd59    9.6 GB    100% GPU     131072     2 minutes from now</code></pre>
      <p>Read the <span class="mono">PROCESSOR</span> column for residency and the <span class="mono">CONTEXT</span> column for the window actually allocated. If <span class="mono">CONTEXT</span> is lower than the value you set, the server trimmed it to fit, which is the quiet version of the problem this section describes.</p>
    </div>

    <p>Also relevant: <span class="mono">OLLAMA_NUM_PARALLEL</span> has a documented default of 1<a class="cite" href="references.html#r9">[9]</a>. An agent loop is bursty rather than concurrent, so 1 is usually right; raising it multiplies the cache term in the same relation.</p>

    <div class="callout info-box">
      <p><strong>Native tool calling is already the default, and there is no variable named what you would expect.</strong> Open WebUI's own tool documentation notes that Native is the default and that only an explicit <span class="mono">legacy</span> opts out of it, so the per-model setting in &sect;9 is a check rather than a change. To set the mode globally the key lives inside a JSON blob &mdash; <span class="mono">DEFAULT_MODEL_PARAMS: '{"function_calling": "legacy"}'</span> &mdash; and the documentation states explicitly that <em>there is no standalone <span class="mono">FUNCTION_CALLING_MODE</span> variable</em>. If you went looking for one and could not find it, that is why.</p>
    </div>

    <p>For the model to reach tools other than the terminal, <span class="mono">mcpo</span> proxies an MCP server's stdio interface to REST and OpenAPI. The documented invocations are <span class="mono">uvx mcpo --port 8000 -- your_mcp_server_command</span> and the published image <span class="mono">ghcr.io/open-webui/mcpo:main</span><a class="cite" href="references.html#r8">[8]</a>, with interactive documentation served at <span class="mono">/docs</span>.</p>
  </div>
</section>

<section id="security">
  <div class="container">
    <h2>10. Blast radius and what to lock down</h2>

    <p>What is being set up here is remote code execution, requested by a language model, on a machine on your network. That is the feature. The question is what it can reach.</p>

    <div class="table-wrap">
      <table>
        <caption>Containment properties of each backend, drawn from the Open WebUI documentation's own statements about isolation.</caption>
        <thead><tr><th scope="col">Backend</th><th scope="col">Filesystem reach</th><th scope="col">Network reach</th><th scope="col">Host reach</th></tr></thead>
        <tbody>
          <tr>
            <td>Open Terminal in Docker</td>
            <td>Container filesystem; <span class="mono">OPEN_TERMINAL_FILE_BROWSER_ROOT</span> bounds the browser, and bind mounts are whatever you mounted</td>
            <td>Unrestricted unless <span class="mono">OPEN_TERMINAL_ALLOWED_DOMAINS</span> is set<a class="cite" href="references.html#r6">[6]</a></td>
            <td>None beyond the container, absent a mounted socket</td>
          </tr>
          <tr>
            <td>Open Terminal on bare metal</td>
            <td>Everything the launching user can read; <span class="mono">--cwd</span> sets the served directory but is not a boundary<a class="cite" href="references.html#r4">[4]</a></td>
            <td>Unrestricted unless allowed-domains is set</td>
            <td><strong>Full.</strong> The documentation calls bare metal a deliberate choice with a wider blast radius<a class="cite" href="references.html#r3">[3]</a></td>
          </tr>
          <tr>
            <td>Jupyter engine</td>
            <td>Everything the kernel's user can read</td>
            <td>Unrestricted</td>
            <td><strong>Full.</strong> A kernel can <span class="mono">subprocess</span> anything</td>
          </tr>
          <tr>
            <td>Pyodide</td>
            <td>Browser virtual filesystem only</td>
            <td>Browser-mediated</td>
            <td>None</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3>10.1 The stronger pattern: put it on a network with no route out</h3>

    <p>The egress allowlist is the right tool when the container genuinely needs to install packages. When it does not &mdash; and for a container that only builds and tests against an environment baked into the image, it does not &mdash; a private Docker network is a harder boundary than a domain list, because there is no list to get wrong.</p>

    <p class="code-label">docker-compose.yml &mdash; the documented network-isolation shape</p>
<pre><code>services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    networks: [public, internal]

  open-terminal:
    image: ghcr.io/open-webui/open-terminal
    # No ports published: nothing outside the compose project can reach it.
    networks: [internal]

networks:
  public:
  internal:
    internal: true   # no route to the internet from this network</code></pre>

    <p>With this shape Open WebUI reaches the terminal at <span class="mono">http://open-terminal:8000</span>, nothing on the network can reach the terminal, and the terminal cannot make outbound requests at all<a class="cite" href="references.html#r36">[36]</a>. Open WebUI sits on both networks, which is what lets it serve users and still reach the terminal.</p>

    <div class="callout info-box">
      <p><strong>Which to use.</strong> Start with <span class="mono">internal: true</span> and no allowlist. Move to the allowlist only when a task genuinely needs to fetch something, and then list the indexes and nothing else. The two are alternatives rather than layers: a container on an internal network has no egress to filter.</p>
    </div>

    <div class="callout danger">
      <p><strong>Do not mount the Docker socket.</strong> Mounting <span class="mono">/var/run/docker.sock</span> lets the model build images and run containers, and the documentation is unambiguous about what it costs: it gives the container full control over the host's Docker, which is &ldquo;effectively root access on your machine&rdquo;. Anyone with terminal access could run containers that mount the entire filesystem, reach the host network, and manage every container on the machine<a class="cite" href="references.html#r36">[36]</a>. On a workstation that also holds contracting and instrument material, that is not a trade worth making for the convenience of letting a model run <span class="mono">docker build</span>.</p>
    </div>

    <h3>10.2 Two more defaults worth knowing</h3>

    <div class="table-wrap">
      <table>
        <caption>Behaviour that is on or off by default in Open Terminal and is easy to miss, with what it means for this deployment.</caption>
        <thead><tr><th scope="col">Behaviour</th><th scope="col">Default</th><th scope="col">What it means</th></tr></thead>
        <tbody>
          <tr>
            <td>Port previews are sandboxed</td>
            <td>On</td>
            <td>When the model starts a server, the preview frame is a separate origin from Open WebUI, which keeps whatever is running away from your session. <strong>Settings &rarr; Interface &rarr; Terminal Preview Allow Same Origin</strong> relaxes it and is off unless you turn it on<a class="cite" href="references.html#r36">[36]</a>. Leave it off: the code being previewed is usually code the model just wrote</td>
          </tr>
          <tr>
            <td>Admin-configured connections</td>
            <td>Prefer them</td>
            <td>An admin-configured connection keeps the API key on the server and routes requests through Open WebUI's backend; a user-configured one stores the key in each user's browser and requires every user's machine to reach the terminal directly<a class="cite" href="references.html#r36">[36]</a>. This is why &sect;3.4 adds the connection under <strong>Admin &rarr; Integrations</strong></td>
          </tr>
          <tr>
            <td><span class="mono">OPEN_TERMINAL_MULTI_USER</span></td>
            <td><span class="mono">false</span></td>
            <td>Gives each user their own account and home folder inside one container, which keeps people and their agents out of each other's files. It is a workspace split, not an isolation boundary: everyone still shares the kernel<a class="cite" href="references.html#r36">[36]</a></td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3>10.3 Minimum set for a home network</h3>

    <ol>
      <li><strong>Run Open Terminal in Docker, not bare metal.</strong> The documentation's own guidance: use Docker for isolation, bare metal only when the agent should work directly on the host<a class="cite" href="references.html#r3">[3]</a>.</li>
      <li><strong>Set an API key explicitly.</strong> <span class="mono">OPEN_TERMINAL_API_KEY</span>, or <span class="mono">OPEN_TERMINAL_API_KEY_FILE</span> to read it from a Docker secret<a class="cite" href="references.html#r6">[6]</a>. An auto-generated key in a container log is not a managed secret.</li>
      <li><strong>Bound egress, and give it the capability it needs.</strong> Either put the container on an <span class="mono">internal: true</span> network, or set <span class="mono">OPEN_TERMINAL_ALLOWED_DOMAINS</span> to your package indexes <em>with</em> <span class="mono">--cap-add NET_ADMIN</span>, then confirm the firewall announced itself in the container log. Unset means a model can reach anything you can; set without the capability means the same thing while looking safe.</li>
      <li><strong>Cap CPU and memory.</strong> <span class="mono">--memory</span> and <span class="mono">--cpus</span> on the container, or <span class="mono">deploy.resources.limits</span> in compose. Docker throttles CPU and kills on memory, so a runaway build fails instead of taking the host down<a class="cite" href="references.html#r36">[36]</a>. Confirm with <span class="mono">docker stats --no-stream open-terminal</span>.</li>
      <li><strong>Pin CORS.</strong> <span class="mono">OPEN_TERMINAL_CORS_ALLOWED_ORIGINS</span> to your Open WebUI origin; the default is <span class="mono">*</span> and a start-up warning says so<a class="cite" href="references.html#r6">[6]</a>.</li>
      <li><strong>Firewall per host, not per subnet.</strong> Port 8000 admits the Open WebUI host only. The existing rules in this deployment use the whole <span class="mono">192.168.7.0/24</span> for several services; an execution endpoint deserves narrower.</li>
      <li><strong>Mount source read-write, credentials never.</strong> Mount the one project directory. Do not mount a home directory, and keep <span class="mono">.ssh</span>, cloud credentials and token files out of the container entirely.</li>
      <li><strong>Separate the sandbox from the inference host</strong> if the inference host serves anyone else.</li>
      <li><strong>Treat the workspace as untrusted output.</strong> Code a model wrote and a model ran has not been reviewed. Review before it leaves the sandbox.</li>
    </ol>

    <h3>10.4 A note on the other direction: agent harnesses that enforce a boundary</h3>

    <p>Open WebUI's backends are containment by deployment choice. A harness such as Claude Code takes the other approach and enforces a boundary at the operating-system level around shell commands, with filesystem and network allowlists in <span class="mono">settings.json</span><a class="cite" href="references.html#r21">[21]</a>. The <a href="claude-sandbox-local-env.html">companion page</a> covers that model and how it maps onto the same mamba environments, because the two can be run side by side against one project.</p>
  </div>
</section>

<section id="verify">
  <div class="container">
    <h2>11. Verification sequence</h2>

    <p>Run these in order. Each one isolates a single link, so the first failure names the thing to fix.</p>

    <div class="table-wrap">
      <table>
        <caption>End-to-end verification sequence, from the execution backend outwards to a model-driven build.</caption>
        <thead><tr><th scope="col">#</th><th scope="col">Check</th><th scope="col">Command or action</th><th scope="col">Expected</th></tr></thead>
        <tbody>
          <tr><td>1</td><td>Backend alive</td><td class="mono">docker exec open-webui curl -s http://open-terminal:8000/health</td><td class="mono">{"status": "ok"}</td></tr>
          <tr><td>2</td><td>API page renders</td><td class="mono">http://localhost:8000/docs</td><td>Open Terminal API documentation</td></tr>
          <tr><td>3</td><td>Toolchain present</td><td class="mono">docker exec open-terminal cmake --version</td><td>A version string</td></tr>
          <tr><td>4</td><td>Environment resolves</td><td class="mono">docker exec open-terminal micromamba run -n Py3p12 python -c "import sys; print(sys.version)"</td><td>Python 3.12.x</td></tr>
          <tr><td>5</td><td>Connection registered</td><td>Admin &rarr; Integrations &rarr; Open Terminal</td><td>Entry present, toggle on</td></tr>
          <tr><td>6</td><td>Native tool calling</td><td>Workspace &rarr; Models &rarr; edit model</td><td>Function Calling = Native</td></tr>
          <tr><td>7</td><td>Terminal selectable</td><td>New chat &rarr; terminal button</td><td>Your terminal listed under <strong>System</strong></td></tr>
          <tr><td>8</td><td>Model can run one command</td><td>Ask: "run <span class="mono">uname -a</span> and show the output"</td><td>Real output, not a description of what it would do</td></tr>
          <tr><td>9</td><td>Model can build</td><td>Ask: "configure and build this project, then report the first error"</td><td>CMake and compiler output</td></tr>
          <tr><td>10</td><td>Model can close the loop</td><td>Ask: "run the tests, fix the first failure, re-run"</td><td>Two test runs with an edit between them</td></tr>
          <tr><td>11a</td><td>Egress firewall came up at all</td><td class="mono">docker logs open-terminal | grep -i egress</td><td>The DNS whitelist and <span class="mono">Egress firewall active</span>. Nothing here means <span class="mono">NET_ADMIN</span> is missing</td></tr>
          <tr><td>11b</td><td>Egress is bounded</td><td class="mono">docker exec open-terminal curl -sS -m 5 https://example.com</td><td><strong>Failure</strong>, if allowed-domains took effect</td></tr>
          <tr><td>11c</td><td>An allowed host still works</td><td class="mono">docker exec open-terminal curl -sSI -m 10 https://pypi.org/simple/</td><td>Succeeds. Without this, 11b passing could just mean the container has no network at all</td></tr>
          <tr><td>12</td><td>Context is sufficient</td><td>Ask the model to summarise a 3000-line build log</td><td>Reference to content from both ends of the log</td></tr>
        </tbody>
      </table>
    </div>

    <p>Step 11 is the one most often skipped, and it is the one that fails. It is split into three parts for a reason: 11b passing on its own proves nothing, because a container with no working network at all also fails to reach <span class="mono">example.com</span>. 11a says the firewall started, 11b that it blocks, 11c that it still lets the indexes through. Confirm all three rather than assuming the variable took effect.</p>
  </div>
</section>

<section id="gaps">
  <div class="container">
    <h2>12. Known gaps in the public documentation</h2>

    <p>Recorded here so a reader does not waste time looking for something that is not published. Each row was confirmed against the cited page on """ + r"""2026-10-18 and re-checked against the upstream documentation repositories on 2026-10-26. The re-check closed the Ollama row below and left the rest standing.</p>

    <div class="table-wrap">
      <table>
        <caption>Gaps found in the vendor documentation while writing this page, with the workaround used instead.</caption>
        <thead><tr><th scope="col">Gap</th><th scope="col">Where it should be</th><th scope="col">Workaround</th></tr></thead>
        <tbody>
          <tr>
            <td><span class="mono">TERMINAL_SERVER_CONNECTIONS</span> format is not published</td>
            <td>Open Terminal connection guide names the variable and points at the environment reference, which does not show the format<a class="cite" href="references.html#r5">[5]</a></td>
            <td>Add the connection through Admin &rarr; Integrations once, then read the stored value out of the Open WebUI database if you need to template it</td>
          </tr>
          <tr>
            <td>No variable documented to enable Open Terminal itself</td>
            <td>The feature overview lists related variables but names none that turns it on<a class="cite" href="references.html#r3">[3]</a></td>
            <td>Enabling is the act of adding the connection; <span class="mono">ENABLE_TOOL_SERVERS</span> must not be <span class="mono">False</span><a class="cite" href="references.html#r5">[5]</a></td>
          </tr>
          <tr>
            <td>Allowed-commands and CPU/memory limits are not documented</td>
            <td>Open Terminal configuration page covers session, log and domain limits only<a class="cite" href="references.html#r6">[6]</a></td>
            <td>Use Docker's own <span class="mono">--cpus</span> and <span class="mono">--memory</span> on the container</td>
          </tr>
          <tr>
            <td>Compose <span class="mono">deploy.resources.reservations.devices</span> form for GPUs not on the GPU-access page</td>
            <td>Docker GPU access page covers <span class="mono">docker run --gpus</span> only<a class="cite" href="references.html#r26">[26]</a></td>
            <td>Use <span class="mono">docker run --gpus device=N</span>, or follow Docker's separate Compose GPU guide</td>
          </tr>
          <tr>
            <td><s>Ollama's context-length default and how to verify it</s> &mdash; <strong>closed</strong></td>
            <td>Previously only the FAQ's flat &ldquo;4096&rdquo;, with no guidance for agent work</td>
            <td><strong>Now documented.</strong> A context-length page gives the VRAM-tiered defaults, asks for at least 64000 for agents and coding tools, and shows the <span class="mono">CONTEXT</span> column of <span class="mono">ollama ps</span><a class="cite" href="references.html#r35">[35]</a>. &sect;9 was corrected against it</td>
          </tr>
          <tr>
            <td>Quantisation level is not stated on Ollama tag pages</td>
            <td>Tag listings give size and context but not bits per weight<a class="cite" href="references.html#r11">[11]</a><a class="cite" href="references.html#r14">[14]</a></td>
            <td>Read it from <span class="mono">ollama show &lt;tag&gt;</span>; the footprint equation flags the assumption</td>
          </tr>
          <tr>
            <td>Minimum sample count for PromQL <span class="mono">rate()</span> is not stated</td>
            <td>The function reference states the two-float-sample minimum for <span class="mono">deriv</span> and <span class="mono">predict_linear</span> only<a class="cite" href="references.html#r19">[19]</a></td>
            <td>The window relation on the monitoring pages marks that step as observed behaviour rather than documented</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>Figures that are estimates, not citations.</strong> Per-compiler memory (1.5&ndash;2.5&nbsp;GB), the realisation factor \( \eta \in [0.5,\,0.8] \), runtime VRAM reservation (0.8&ndash;1.5&nbsp;GB), GGUF container overhead \( \varepsilon \in [0.03,\,0.08] \) and the Prometheus series counts are planning estimates for this class of hardware. They are stated as ranges, and each equation block says which of its inputs are estimates. Measure them on your own machines before relying on a result.</p>
    </div>
  </div>
</section>
"""
