# -*- coding: utf-8 -*-
"""
page_monitoring.py -- body content for monitoring-sizing.html

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

PURPOSE
-------
Holds the monitoring arithmetic that the four existing Prometheus and Grafana
pages assume but never state: how much disk a retention window costs, what the
scrape configuration actually ingests, why a range-vector window has a lower
bound, and the difference between a counter and a gauge when computing
utilisation.

WHY A SEPARATE PAGE RATHER THAN AN APPENDIX ON EACH
---------------------------------------------------
Four pages in the set cover monitoring: the Windows install, the Linux
install, the multi-node llama-server tutorial and the multi-vendor GPU page.
The same four relations apply to all of them.  Putting an appendix on each
would duplicate the material four times and guarantee that three copies go
stale; putting it on its own page, linked from the shared navigation, keeps
one copy.  It also keeps the promise the rebuild made to leave the existing
pages' content untouched.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import eq_library


# %% Body fragment -----------------------------------------------------------
def build() -> str:
    """Return the complete body fragment for monitoring-sizing.html."""
    return r"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">Monitoring arithmetic</div>
    <h1>Sizing the monitoring stack, and getting the queries right</h1>
    <p class="lead">The install pages in this set get Prometheus, the exporters and Grafana running. Four questions come up immediately afterwards and none of them are answered there: how much disk the retention window will cost, what the scrape configuration actually ingests, why a panel intermittently goes blank, and whether a given metric needs differencing before it means anything.</p>
    <p class="small muted">This page holds those four relations in one place rather than repeating them on each of the four monitoring pages. Every equation is tagged <span class="pill stated">Stated</span> or <span class="pill derived">Derived here</span> and carries an information button that opens a variable table with units.</p>
  </div>
</section>

<section id="on-this-page">
  <div class="container">
    <h2>On this page</h2>
    <ul class="toc">
      <li><a href="#storage">1. Disk cost of a retention window</a></li>
      <li><a href="#ingest">2. What the scrape configuration ingests</a></li>
      <li><a href="#windows">3. Why a panel goes blank, and the window that fixes it</a></li>
      <li><a href="#counters">4. Counters and gauges are not interchangeable</a></li>
      <li><a href="#apply">5. Applying this to the stack in this set</a></li>
    </ul>
  </div>
</section>

<section id="storage">
  <div class="container">
    <h2>1. Disk cost of a retention window</h2>

    <p>The Prometheus storage documentation gives the sizing relation directly, and two figures that make it usable: the server "stores an average of only 1-2 bytes per sample", and a size-based retention limit should be set "to, at most, 80-85% of your allocated Prometheus disk space"<a class="cite" href="references.html#r18">[18]</a>.</p>

    """ + eq_library.get("prom-disk") + r"""

    <div class="table-wrap">
      <table>
        <caption>Retention flags that interact with the relation above, with the documented defaults and behaviour quoted from the Prometheus storage documentation.</caption>
        <thead><tr><th scope="col">Flag</th><th scope="col">Documented default</th><th scope="col">Note</th></tr></thead>
        <tbody>
          <tr>
            <td class="mono">--storage.tsdb.path</td>
            <td class="mono">data/</td>
            <td>"Where Prometheus writes its database"<a class="cite" href="references.html#r18">[18]</a></td>
          </tr>
          <tr>
            <td class="mono">--storage.tsdb.retention.time</td>
            <td class="mono">15d</td>
            <td>The default applies only when neither this flag nor the size flag is set<a class="cite" href="references.html#r18">[18]</a></td>
          </tr>
          <tr>
            <td class="mono">--storage.tsdb.retention.size</td>
            <td class="mono">0</td>
            <td>Disabled by default. The write-ahead log and memory-mapped chunks count toward the total, so "the minimum requirement for the disk is the peak space taken by the <span class="mono">wal</span>"<a class="cite" href="references.html#r18">[18]</a></td>
          </tr>
          <tr>
            <td>Both set together</td>
            <td>&mdash;</td>
            <td>"whichever triggers first will be used"<a class="cite" href="references.html#r18">[18]</a></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>Reduce series before reducing sample rate.</strong> The documentation states that reducing the number of series is "likely more effective, due to compression of samples within a series"<a class="cite" href="references.html#r18">[18]</a>. The practical reading: lengthening the scrape interval loses resolution for a modest saving, while dropping a high-cardinality metric saves far more and loses nothing you were looking at. Per-process and per-disk-partition metrics are the usual offenders on a Windows host.</p>
    </div>
  </div>
</section>

<section id="ingest">
  <div class="container">
    <h2>2. What the scrape configuration ingests</h2>

    <p>The storage relation needs \( \lambda \), which is not published anywhere because it depends entirely on your own <span class="mono">prometheus.yml</span>. It follows from the job definitions.</p>

    """ + eq_library.get("prom-ingest") + r"""

    <div class="callout">
      <p><strong>The series counts in that derivation are planning estimates, not measurements.</strong> Roughly 1500 series for <span class="mono">windows_exporter</span>, 120 per GPU for <span class="mono">nvidia_gpu_exporter</span><a class="cite" href="references.html#r20">[20]</a> and 30 for <span class="mono">llama-server --metrics</span> are order-of-magnitude figures for planning only. Replace them with <span class="mono">prometheus_tsdb_head_series</span> read from your own server once it has run for a day:</p>
<pre><code># Total active series, which is the number the storage relation needs.
curl -s 'http://localhost:9090/api/v1/query?query=prometheus_tsdb_head_series'

# Series per job, which is how you find the expensive exporter.
curl -s --get 'http://localhost:9090/api/v1/query' \
  --data-urlencode 'query=count by (job) ({__name__=~".+"})'</code></pre>
    </div>

    <div class="table-wrap">
      <table>
        <caption>Worked ingest and storage estimate for the four-node stack documented in this page set, evaluated from the two relations above. Series counts are planning estimates; the arithmetic is exact given them.</caption>
        <thead><tr><th scope="col">Job</th><th scope="col">Targets</th><th scope="col">Series each</th><th scope="col">Interval</th><th scope="col">Samples&middot;s<sup>&minus;1</sup></th></tr></thead>
        <tbody>
          <tr><td class="mono">windows_exporter</td><td class="mono">4</td><td class="mono">~1500</td><td class="mono">15 s</td><td class="mono">400</td></tr>
          <tr><td class="mono">nvidia_gpu_exporter</td><td class="mono">3</td><td class="mono">~120</td><td class="mono">15 s</td><td class="mono">24</td></tr>
          <tr><td class="mono">llama-server</td><td class="mono">1</td><td class="mono">~30</td><td class="mono">15 s</td><td class="mono">2</td></tr>
          <tr><td colspan="4"><strong>Total \(\lambda\)</strong></td><td class="mono"><strong>426</strong></td></tr>
          <tr><td colspan="4">Disk at \(T_{\text{ret}} = 15\ \mathrm{d}\), \(\beta = 2\ \mathrm{B}\)</td><td class="mono"><strong>&asymp; 1.1 GB</strong></td></tr>
          <tr><td colspan="4">Disk to allocate, at the documented 80&ndash;85 % ceiling<a class="cite" href="references.html#r18">[18]</a>, with headroom for the write-ahead log and compaction</td><td class="mono"><strong>&asymp; 8&ndash;10 GB</strong></td></tr>
        </tbody>
      </table>
    </div>

    <p>The gap between 1.1&nbsp;GB of compacted blocks and 8&ndash;10&nbsp;GB of allocation is deliberate. The documentation notes the write-ahead log and memory-mapped chunks count toward the size limit and sets the peak <span class="mono">wal</span> as the disk minimum<a class="cite" href="references.html#r18">[18]</a>, and compaction needs transient space on top of the steady state.</p>
  </div>
</section>

<section id="windows">
  <div class="container">
    <h2>3. Why a panel goes blank, and the window that fixes it</h2>

    <p>A dashboard panel that works most of the time and empties occasionally is almost never a broken exporter. It is a range-vector window too close to the scrape interval.</p>

    """ + eq_library.get("rate-window") + r"""

    <div class="table-wrap">
      <table>
        <caption>Minimum range-vector window per scrape interval, evaluated from the condition above for two and three tolerated missed scrapes. The 15&nbsp;s column is the interval used throughout this page set.</caption>
        <thead><tr><th scope="col">Scrape interval \(T_{s}\)</th><th scope="col">Bare minimum, \(f = 0\)</th><th scope="col">Tolerating 2 misses</th><th scope="col">Tolerating 3 misses</th></tr></thead>
        <tbody>
          <tr><td class="mono">10 s</td><td class="mono">20 s</td><td class="mono">40 s</td><td class="mono">50 s</td></tr>
          <tr><td class="mono">15 s</td><td class="mono">30 s</td><td class="mono"><strong>60 s</strong></td><td class="mono">75 s</td></tr>
          <tr><td class="mono">30 s</td><td class="mono">60 s</td><td class="mono">120 s</td><td class="mono">150 s</td></tr>
          <tr><td class="mono">60 s</td><td class="mono">120 s</td><td class="mono">240 s</td><td class="mono">300 s</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong>The regression to guard against.</strong> Raising <span class="mono">scrape_interval</span> without raising every window that depends on it breaks panels that were previously fine, and it breaks them intermittently, which makes it hard to attribute. In Grafana, template the window from a dashboard variable rather than hard-coding <span class="mono">[1m]</span> in twenty expressions, so one edit moves all of them.</p>
    </div>

    <p>Two further documented properties are worth knowing. <span class="mono">rate()</span> extrapolates "to the ends of the time range, allowing for missed scrapes", and when combining it with an aggregation you should "always take a <span class="mono">rate()</span> first, then aggregate"<a class="cite" href="references.html#r19">[19]</a>. Aggregating first destroys the per-series counter-reset handling and silently produces a wrong number rather than an error.</p>
  </div>
</section>

<section id="counters">
  <div class="container">
    <h2>4. Counters and gauges are not interchangeable</h2>

    <p>The GPU exporters publish both kinds of metric, and applying the wrong treatment produces a plausible-looking panel rather than an obvious failure. That makes it the most expensive class of mistake in a monitoring setup.</p>

    """ + eq_library.get("gpu-utilisation") + r"""

    <div class="table-wrap">
      <table>
        <caption>How to treat each metric kind, and the symptom when the treatment is wrong. This is the check to run against every panel in a new dashboard.</caption>
        <thead><tr><th scope="col">Metric kind</th><th scope="col">Example</th><th scope="col">Correct treatment</th><th scope="col">Symptom if treated as the other kind</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>Counter</strong>, monotonically increasing</td>
            <td>Cumulative busy seconds, bytes transmitted, request count</td>
            <td><span class="mono">rate(metric[1m])</span></td>
            <td>Plotted raw it is a slowly rising ramp that looks like a memory leak and means nothing</td>
          </tr>
          <tr>
            <td><strong>Gauge</strong>, instantaneous</td>
            <td>GPU utilisation per cent, temperature, VRAM in use, fan speed</td>
            <td>Plot it directly</td>
            <td>Wrapped in <span class="mono">rate()</span> it returns a near-zero line, or nothing, because a gauge is not monotonic</td>
          </tr>
          <tr>
            <td><strong>Counter aggregating several devices</strong></td>
            <td>Busy seconds summed across GPUs or CPU cores</td>
            <td><span class="mono">rate(...)</span> then divide by \(n_{\text{dev}}\)</td>
            <td>Reads above 100 % and the axis looks broken</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>How to tell which you have.</strong> Open the exporter's own metrics endpoint and read the <span class="mono"># TYPE</span> line, which names the kind for every metric:</p>
<pre><code># The documented check for the NVIDIA exporter, which the set's existing
# pages install at port 9835.
Invoke-WebRequest http://localhost:9835/metrics |
  Select-Object -ExpandProperty Content |
  Select-String -Pattern '^# TYPE'</code></pre>
      <p>Do this once per exporter and write the kinds down. It takes a minute and it removes the whole class of mistake above.</p>
    </div>
  </div>
</section>

<section id="apply">
  <div class="container">
    <h2>5. Applying this to the stack in this set</h2>

    <div class="table-wrap">
      <table>
        <caption>Which relation on this page answers which question raised by each existing monitoring page in the set.</caption>
        <thead><tr><th scope="col">Page</th><th scope="col">Question it leaves open</th><th scope="col">Relation</th></tr></thead>
        <tbody>
          <tr>
            <td><a href="Grafana_Prometheus_install_windows.html">Install on Windows / WSL2</a></td>
            <td>How much disk to give the data directory</td>
            <td><a href="#eq-prom-disk">Storage</a> and <a href="#eq-prom-ingest">ingest rate</a></td>
          </tr>
          <tr>
            <td><a href="Grafan_Promethius_install_linux.html">Install on Node A (Linux)</a></td>
            <td>Same, plus whether the 15&nbsp;s default scrape interval is affordable</td>
            <td><a href="#eq-prom-ingest">Ingest rate</a></td>
          </tr>
          <tr>
            <td><a href="Promethius_Grafana_windows11-llama-monitoring-tutorial.html">Multi-node llama-server monitoring</a></td>
            <td>Why a panel empties intermittently</td>
            <td><a href="#eq-rate-window">Window condition</a></td>
          </tr>
          <tr>
            <td><a href="GPU_monitoring_setup.html">Multi-vendor GPU monitoring</a></td>
            <td>Whether a given GPU metric needs differencing</td>
            <td><a href="#eq-gpu-utilisation">Counter-based utilisation</a></td>
          </tr>
          <tr>
            <td><a href="ollama-model-selection.html">Model selection</a></td>
            <td>Whether a model quietly spilled to system RAM</td>
            <td>Not an equation: <span class="mono">ollama ps</span>, plus a VRAM gauge panel on the dashboard</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong>The one panel worth adding to an existing dashboard.</strong> Resident VRAM per node, as a gauge, next to decode rate. The ninefold throughput cliff described on the <a href="ollama-model-selection.html#speed">model selection page</a> is invisible in a chat window and obvious on that panel, and it is the failure that wastes the most time in a local deployment.</p>
    </div>
  </div>
</section>
"""
