# -*- coding: utf-8 -*-
"""
eq_library.py -- equation blocks for the AI_Local documentation set.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

PURPOSE
-------
Every equation shown anywhere in the AI_Local page set is defined exactly once
in this module and referenced by slug from ``build_ai_local_site.py``.  Keeping
them in one file means a symbol or a unit can be corrected in one place and the
correction propagates to every page that shows the equation.

MARKUP CONTRACT
---------------
The HTML emitted here follows the "Atomic Theory Atlas" authoring pattern
(``Educational/Atomic Theory Atlas.zip`` -> ``PATTERNS.md``) without deviation:

    <div class="eq" id="eq-SLUG">
      <div class="eq-head">
        <h3 class="eq-title">Name</h3>
        <div class="eq-tools">
          <span class="pill stated|derived|data">...</span>
          <button class="info" aria-controls="v-SLUG" aria-expanded="false">
            &#9432;&nbsp;<span class="info-label">Define variables</span></button>
        </div>
      </div>
      <div class="eq-body">\\[ ... \\]</div>
      <p class="eq-note">...</p>
      <div class="deriv"><ol>...</ol></div>      <- required when "derived"
      <div class="vars" id="v-SLUG" hidden>...</div>
    </div>

Rules carried over from PATTERNS.md and enforced by
``build_ai_local_site.py`` -> ``verify_equation_blocks()``:

* Display math uses ``\\[ ... \\]``; inline math uses ``\\( ... \\)``.
  A bare ``$`` is never a delimiter, because these pages are full of shell
  variables such as ``$env:USERPROFILE`` and ``${VERSION}``.
* ``aria-controls`` on the button must equal the ``id`` of the ``.vars`` block.
* A block tagged "Derived here" must carry a ``.deriv`` step list, placed
  after ``.eq-note`` and before ``.vars``.
* Every symbol that appears in the display math must appear in the variable
  table, with an SI or stated unit.
* Citations use ``<a class="cite" href="references.html#rNN">[NN]</a>`` and the
  number must exist in ``references.py``.

PYTHON CONVENTIONS
------------------
PEP 8 naming, module constant in UPPER_SNAKE_CASE, raw triple-quoted strings so
that LaTeX backslashes survive verbatim.  Spyder cell separators (``# %%``)
divide the module into the physical-domain groups the pages draw from.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from typing import Dict


# %% Model-footprint and memory equations ------------------------------------
# Drawn on by: ollama-model-selection.html, llama-rpc-vulkan-guide.html,
#              local-code-build-test.html
_MEMORY_EQUATIONS: Dict[str, str] = {}

_MEMORY_EQUATIONS["quant-footprint"] = r"""
<div class="eq" id="eq-quant-footprint">
  <div class="eq-head">
    <h3 class="eq-title">Quantised weight footprint of a local model</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-quant-footprint" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ S_{w} \;=\; \frac{P\,b_{q}}{8}\,\bigl(1+\varepsilon\bigr) \]</div>
  <p class="eq-note">This is the number to compare against free VRAM before pulling a tag. It accounts for the whole weight file, not just the quantised tensors, because a GGUF keeps token embeddings and normalisation weights at higher precision and adds tensor metadata.</p>
  <div class="deriv"><ol>
    <li>A model quantised to \( b_{q} \) bits per weight stores \( P\,b_{q} \) bits of weights in total.</li>
    <li>Convert bits to bytes: \( S_{w,\text{raw}} = P\,b_{q}/8 \).</li>
    <li>A GGUF container also carries per-tensor metadata and tensors deliberately left at a higher precision. Collect both as a fractional overhead \( \varepsilon \), giving \( S_{w} = (P b_{q}/8)(1+\varepsilon) \).</li>
    <li>Check against a published figure. Ollama lists <span class="mono">qwen3-coder:30b</span> at 19&nbsp;GB<a class="cite" href="references.html#r11">[11]</a>. Taking \( P = 30.5\times10^{9} \) and the mixed Q4_K_M rate \( b_{q}\approx 4.8\ \mathrm{bit/weight} \): \( (30.5\times10^{9})(4.8)/8 = 1.83\times10^{10}\ \mathrm{B} = 18.3\ \mathrm{GB} \), so \( \varepsilon \approx 0.04 \).</li>
    <li>Treat \( \varepsilon \in [0.03,\,0.08] \) as the working range. The Ollama tag page does not state the quantisation level, so the \( b_{q} \) above is the library default rather than a published figure; confirm with <span class="mono">ollama show &lt;tag&gt;</span> before relying on the result.</li>
  </ol></div>
  <div class="vars" id="v-quant-footprint" hidden><div class="table-wrap"><table>
    <caption>Symbols in the quantised-footprint relation, with the units used throughout this page set.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(S_{w}\)</td><td>On-disk and in-VRAM size of the weight file</td><td>B (byte)</td></tr>
      <tr><td>\(P\)</td><td>Total parameter count of the model, all experts included</td><td>dimensionless</td></tr>
      <tr><td>\(b_{q}\)</td><td>Average bits stored per weight for the chosen quantisation. Representative values: Q4_K_M \(\approx 4.8\), Q5_K_M \(\approx 5.7\), Q8_0 \(\approx 8.5\), BF16 \(= 16\)</td><td>bit&middot;weight<sup>&minus;1</sup></td></tr>
      <tr><td>\(\varepsilon\)</td><td>Container and high-precision-tensor overhead as a fraction of the raw weight bytes</td><td>dimensionless</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_MEMORY_EQUATIONS["moe-active"] = r"""
<div class="eq" id="eq-moe-active">
  <div class="eq-head">
    <h3 class="eq-title">Active parameter count of a routed mixture-of-experts model</h3>
    <div class="eq-tools"><span class="pill stated">Stated</span>
      <button class="info" aria-controls="v-moe-active" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ P_{\text{act}} \;=\; P_{\text{shared}} \;+\; k\,P_{\text{expert}} \]</div>
  <p class="eq-note">The distinction matters because the two halves of a sizing decision use different parameter counts: VRAM capacity is set by the total \( P \), while decode speed is set by \( P_{\text{act}} \). A 30B model that routes roughly 3B parameters per token occupies the card like a 30B model and streams like a 3B one.</p>
  <div class="vars" id="v-moe-active" hidden><div class="table-wrap"><table>
    <caption>Symbols in the active-parameter relation for a top-\(k\) routed mixture-of-experts transformer.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(P_{\text{act}}\)</td><td>Parameters read while producing one token</td><td>dimensionless</td></tr>
      <tr><td>\(P_{\text{shared}}\)</td><td>Parameters outside the expert blocks: attention, embeddings, normalisation, any always-on dense feed-forward</td><td>dimensionless</td></tr>
      <tr><td>\(k\)</td><td>Experts the router selects per token, out of \(E\) available</td><td>dimensionless</td></tr>
      <tr><td>\(P_{\text{expert}}\)</td><td>Parameters in a single expert block</td><td>dimensionless</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_MEMORY_EQUATIONS["kv-cache"] = r"""
<div class="eq" id="eq-kv-cache">
  <div class="eq-head">
    <h3 class="eq-title">Key/value cache footprint</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-kv-cache" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ S_{kv} \;=\; 2\,n_{\ell}\,n_{kv}\,d_{h}\,L_{\text{ctx}}\,n_{\text{seq}}\,b_{kv} \]</div>
  <p class="eq-note">The cache is the term people forget. It is linear in context length and linear in the number of concurrent sequences, so raising <span class="mono">--ctx-size</span> from 8192 to 32768 while also raising <span class="mono">--parallel</span> from 1 to 4 multiplies this term by sixteen.</p>
  <div class="deriv"><ol>
    <li>Autoregressive attention caches one key vector and one value vector for every token already generated, for every attention layer. That is the leading factor of 2.</li>
    <li>Grouped-query attention shares each key/value pair across several query heads, so the count that matters is \( n_{kv} \), the number of key/value heads, not the number of query heads.</li>
    <li>Each cached vector has \( d_{h} \) components, so one token costs \( 2\,n_{\ell}\,n_{kv}\,d_{h} \) elements.</li>
    <li>Multiply by the context length \( L_{\text{ctx}} \) that the cache is sized for, and by the number of concurrent sequences \( n_{\text{seq}} \) (<span class="mono">--parallel</span> in <span class="mono">llama-server</span>), each of which keeps its own cache.</li>
    <li>Multiply by the bytes per cached element \( b_{kv} \). Ollama exposes this as <span class="mono">OLLAMA_KV_CACHE_TYPE</span>, documented with a default of <span class="mono">f16</span> and options <span class="mono">q8_0</span> and <span class="mono">q4_0</span><a class="cite" href="references.html#r9">[9]</a>, giving \( b_{kv} = 2,\ 1,\ 0.5\ \mathrm{B} \) respectively.</li>
  </ol></div>
  <div class="vars" id="v-kv-cache" hidden><div class="table-wrap"><table>
    <caption>Symbols in the key/value cache relation. The architectural quantities are read from the model card or from <span class="mono">ollama show &lt;tag&gt;</span>; the operational ones are set on the command line.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(S_{kv}\)</td><td>Total key/value cache size held in VRAM or RAM</td><td>B</td></tr>
      <tr><td>\(n_{\ell}\)</td><td>Number of transformer layers</td><td>dimensionless</td></tr>
      <tr><td>\(n_{kv}\)</td><td>Key/value heads per layer (equal to the query-head count only when grouped-query attention is not used)</td><td>dimensionless</td></tr>
      <tr><td>\(d_{h}\)</td><td>Head dimension</td><td>dimensionless</td></tr>
      <tr><td>\(L_{\text{ctx}}\)</td><td>Context length the cache is allocated for, <span class="mono">--ctx-size</span> or <span class="mono">OLLAMA_CONTEXT_LENGTH</span> (Ollama default 4096)<a class="cite" href="references.html#r9">[9]</a></td><td>token</td></tr>
      <tr><td>\(n_{\text{seq}}\)</td><td>Concurrent sequences, <span class="mono">--parallel</span> in <span class="mono">llama-server</span> or <span class="mono">OLLAMA_NUM_PARALLEL</span></td><td>dimensionless</td></tr>
      <tr><td>\(b_{kv}\)</td><td>Bytes per cached element, set by the cache data type</td><td>B</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_MEMORY_EQUATIONS["ctx-budget"] = r"""
<div class="eq" id="eq-ctx-budget">
  <div class="eq-head">
    <h3 class="eq-title">Longest context a card can actually hold</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-ctx-budget" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ L_{\max} \;=\; \left\lfloor \frac{V_{\text{tot}} - S_{w} - V_{\text{rt}}}{2\,n_{\ell}\,n_{kv}\,d_{h}\,n_{\text{seq}}\,b_{kv}} \right\rfloor \]</div>
  <p class="eq-note">A model card advertising a 256K window is stating what the weights were trained to attend over, not what the card in the machine can allocate. This inverts the cache relation to give the second number, which is the one that decides whether a repository-scale prompt fits.</p>
  <div class="deriv"><ol>
    <li>Start from \( S_{kv} = 2\,n_{\ell}\,n_{kv}\,d_{h}\,L_{\text{ctx}}\,n_{\text{seq}}\,b_{kv} \) as derived above.</li>
    <li>The cache has to share the device with the weights \( S_{w} \) and with the runtime's own allocations \( V_{\text{rt}} \): compute scratch buffers, the CUDA or Vulkan context, and whatever the display driver has already reserved.</li>
    <li>Set the available remainder equal to the cache: \( V_{\text{tot}} - S_{w} - V_{\text{rt}} = S_{kv} \).</li>
    <li>Solve for \( L_{\text{ctx}} \) and take the floor, since a partial token cannot be cached.</li>
    <li>Round down further in practice. Allocators fragment, and on Windows the WDDM display driver can page VRAM out from under the runtime, so leave headroom rather than sizing to the last megabyte.</li>
  </ol></div>
  <div class="vars" id="v-ctx-budget" hidden><div class="table-wrap"><table>
    <caption>Symbols in the context-budget relation. Symbols shared with the cache relation keep the same meaning and units.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(L_{\max}\)</td><td>Largest context length that fits once weights and runtime are placed</td><td>token</td></tr>
      <tr><td>\(V_{\text{tot}}\)</td><td>Total device memory on the accelerator</td><td>B</td></tr>
      <tr><td>\(S_{w}\)</td><td>Weight footprint, from the quantised-footprint relation</td><td>B</td></tr>
      <tr><td>\(V_{\text{rt}}\)</td><td>Runtime, driver and compute-buffer reservation. Budget 0.8&ndash;1.5&nbsp;GB for a single-GPU llama.cpp or Ollama process and measure it rather than assuming</td><td>B</td></tr>
      <tr><td>\(n_{\ell},\,n_{kv},\,d_{h},\,n_{\text{seq}},\,b_{kv}\)</td><td>As defined for the key/value cache relation</td><td>&mdash;</td></tr>
    </tbody>
  </table></div></div>
</div>
"""


# %% Throughput and distribution equations -----------------------------------
# Drawn on by: llama-rpc-vulkan-guide.html, ollama-model-selection.html
_THROUGHPUT_EQUATIONS: Dict[str, str] = {}

_THROUGHPUT_EQUATIONS["bandwidth-bound"] = r"""
<div class="eq" id="eq-bandwidth-bound">
  <div class="eq-head">
    <h3 class="eq-title">Memory-bandwidth ceiling on single-stream decode rate</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-bandwidth-bound" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ r_{\max} \;=\; \frac{B_{\text{eff}}}{S_{\text{act}}} \qquad\text{and}\qquad r_{\text{obs}} \;\approx\; \eta\,r_{\max},\quad \eta \in [0.5,\,0.8] \]</div>
  <p class="eq-note">Token generation is bandwidth-bound, not compute-bound. This single ratio predicts which of two candidate models will feel usable in an agent loop more reliably than any benchmark score does, and it is why an 8-bit quantisation of a model is roughly half the speed of a 4-bit quantisation of the same model.</p>
  <div class="deriv"><ol>
    <li>Generating one token in the decode phase requires reading every active weight from memory exactly once; with a batch of one there is no reuse to amortise that read against.</li>
    <li>The time to read \( S_{\text{act}} \) bytes at an achieved bandwidth \( B_{\text{eff}} \) is \( S_{\text{act}}/B_{\text{eff}} \), so \( t_{\text{tok}} \ge S_{\text{act}}/B_{\text{eff}} \).</li>
    <li>Take the reciprocal: \( r_{\max} = B_{\text{eff}}/S_{\text{act}} \) tokens per second.</li>
    <li>For a dense model \( S_{\text{act}} = S_{w} \). For a routed mixture of experts, substitute \( P_{\text{act}} \) from the active-parameter relation into the quantised-footprint relation instead of \( P \).</li>
    <li>Worked example. A 19&nbsp;GB dense weight set on a card delivering \( B_{\text{eff}} = 450\ \mathrm{GB\,s^{-1}} \): \( r_{\max} = 450/19 = 23.7\ \mathrm{token\,s^{-1}} \), and with \( \eta = 0.65 \) expect about \( 15\ \mathrm{token\,s^{-1}} \).</li>
    <li>The same 19&nbsp;GB file spilled to system RAM at \( B_{\text{eff}} = 50\ \mathrm{GB\,s^{-1}} \) gives \( r_{\max} = 2.6\ \mathrm{token\,s^{-1}} \). That ninefold cliff is the reason the layer-offload count below is worth computing rather than guessing.</li>
  </ol></div>
  <div class="vars" id="v-bandwidth-bound" hidden><div class="table-wrap"><table>
    <caption>Symbols in the bandwidth-ceiling relation. \(B_{\text{eff}}\) is the achieved figure from a bandwidth test, not the number on the specification sheet.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(r_{\max}\)</td><td>Upper bound on sustained token generation rate</td><td>token&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(r_{\text{obs}}\)</td><td>Rate actually observed end to end</td><td>token&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(B_{\text{eff}}\)</td><td>Achieved memory bandwidth of the device holding the weights. Typically 0.7&ndash;0.9 of the theoretical peak</td><td>B&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(S_{\text{act}}\)</td><td>Bytes of weights read per token: the whole weight set for a dense model, the routed subset for a mixture of experts</td><td>B</td></tr>
      <tr><td>\(\eta\)</td><td>Realisation factor covering attention over the cache, sampling, and framework overhead</td><td>dimensionless</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_THROUGHPUT_EQUATIONS["ngl-layers"] = r"""
<div class="eq" id="eq-ngl-layers">
  <div class="eq-head">
    <h3 class="eq-title">Layer count to pass to <span class="mono">--n-gpu-layers</span></h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-ngl-layers" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ n_{\text{gpu}} \;=\; \left\lfloor \frac{\bigl(V_{\text{tot}} - V_{\text{rt}} - S_{kv}\bigr)\,n_{\ell}}{S_{w}} \right\rfloor, \qquad 0 \le n_{\text{gpu}} \le n_{\ell} \]</div>
  <p class="eq-note">The <span class="mono">-ngl</span> value in the service definitions on this page set was chosen by trial. This gives a starting value to try first, which matters because the failure mode of overshooting is an out-of-memory abort part-way through loading rather than a graceful fallback.</p>
  <div class="deriv"><ol>
    <li>llama.cpp offloads whole transformer blocks, so the granularity is one layer. Averaged over the stack, one layer is \( S_{w}/n_{\ell} \) bytes.</li>
    <li>The device must also hold the runtime reservation \( V_{\text{rt}} \) and the whole key/value cache \( S_{kv} \), both of which are allocated regardless of how many layers are resident.</li>
    <li>The bytes left for weights are therefore \( V_{\text{tot}} - V_{\text{rt}} - S_{kv} \).</li>
    <li>Divide by the per-layer size and take the floor: \( n_{\text{gpu}} = \lfloor (V_{\text{tot}} - V_{\text{rt}} - S_{kv})\,n_{\ell}/S_{w} \rfloor \).</li>
    <li>Clamp into \( [0,\,n_{\ell}] \), then subtract one or two before the first run. Layers are not uniform in size, the output projection is usually the largest single tensor, and allocator fragmentation costs real megabytes.</li>
    <li>If the result equals \( n_{\ell} \), pass <span class="mono">-ngl 999</span> rather than the exact count so the setting survives a change of model.</li>
  </ol></div>
  <div class="vars" id="v-ngl-layers" hidden><div class="table-wrap"><table>
    <caption>Symbols in the layer-offload relation. All memory symbols carry the meanings established in the cache and footprint relations.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(n_{\text{gpu}}\)</td><td>Layers to place on the accelerator, the <span class="mono">-ngl</span> argument</td><td>dimensionless</td></tr>
      <tr><td>\(n_{\ell}\)</td><td>Total transformer layers in the model</td><td>dimensionless</td></tr>
      <tr><td>\(V_{\text{tot}}\)</td><td>Total device memory</td><td>B</td></tr>
      <tr><td>\(V_{\text{rt}}\)</td><td>Runtime, driver and compute-buffer reservation</td><td>B</td></tr>
      <tr><td>\(S_{kv}\)</td><td>Key/value cache size for the chosen context and parallelism</td><td>B</td></tr>
      <tr><td>\(S_{w}\)</td><td>Total weight footprint</td><td>B</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_THROUGHPUT_EQUATIONS["rpc-token-time"] = r"""
<div class="eq" id="eq-rpc-token-time">
  <div class="eq-head">
    <h3 class="eq-title">Per-token wall clock across RPC workers</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-rpc-token-time" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ t_{\text{tok}} \;=\; \sum_{i=1}^{N}\frac{S_{i}}{B_{i}} \;+\; \sum_{i=1}^{N-1}\left(\frac{D_{\text{act}}}{R_{i}} + 2\tau_{i}\right), \qquad r \;=\; \frac{1}{t_{\text{tok}}} \]</div>
  <p class="eq-note">llama.cpp's RPC backend splits the layer stack across machines<a class="cite" href="references.html#r17">[17]</a>. This separates the part of a token's cost that the split reduces from the part it adds, which is the only way to answer whether a fourth node is worth switching on.</p>
  <div class="deriv"><ol>
    <li>Node \( i \) holds \( S_{i} \) bytes of the weight set and streams them from its own memory at \( B_{i} \), so its contribution to one token is \( S_{i}/B_{i} \) by the bandwidth-ceiling argument above.</li>
    <li>A pipeline split is sequential for a single token: layer \( j+1 \) cannot start before layer \( j \) has produced its output. The per-node times therefore add rather than overlap.</li>
    <li>At each of the \( N-1 \) boundaries the activation tensor of \( D_{\text{act}} \) bytes crosses the link at throughput \( R_{i} \), costing \( D_{\text{act}}/R_{i} \), plus \( 2\tau_{i} \) for the request and response legs.</li>
    <li>Summing both contributions gives \( t_{\text{tok}} \), and \( r = 1/t_{\text{tok}} \).</li>
    <li>Scale of the link term on a home network. One activation row for a hidden size of 4096 in <span class="mono">f16</span> is \( 4096 \times 2 = 8192\ \mathrm{B} \). Over gigabit Ethernet at an achieved \( R = 940\ \mathrm{Mbit\,s^{-1}} = 1.18\times10^{8}\ \mathrm{B\,s^{-1}} \) that is \( 69\ \mathrm{\mu s} \), against \( 2\tau \approx 400\ \mathrm{\mu s} \) for a typical switched round trip. Latency dominates transfer, so the number of hops matters more than the hidden size.</li>
    <li>Prompt processing behaves differently. It submits many tokens at once, so \( D_{\text{act}} \) scales with the batch and the transfer term stops being negligible.</li>
  </ol></div>
  <div class="vars" id="v-rpc-token-time" hidden><div class="table-wrap"><table>
    <caption>Symbols in the distributed per-token relation for an \(N\)-node llama.cpp RPC pipeline.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(t_{\text{tok}}\)</td><td>Wall-clock time to produce one token</td><td>s</td></tr>
      <tr><td>\(r\)</td><td>Sustained generation rate</td><td>token&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(N\)</td><td>Nodes in the pipeline, host included</td><td>dimensionless</td></tr>
      <tr><td>\(S_{i}\)</td><td>Weight bytes resident on node \(i\)</td><td>B</td></tr>
      <tr><td>\(B_{i}\)</td><td>Achieved memory bandwidth on node \(i\) for the memory actually holding those weights</td><td>B&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(D_{\text{act}}\)</td><td>Activation tensor crossing one boundary, hidden size times bytes per element</td><td>B</td></tr>
      <tr><td>\(R_{i}\)</td><td>Achieved link throughput at boundary \(i\)</td><td>B&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(\tau_{i}\)</td><td>One-way link latency at boundary \(i\)</td><td>s</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_THROUGHPUT_EQUATIONS["rpc-breakeven"] = r"""
<div class="eq" id="eq-rpc-breakeven">
  <div class="eq-head">
    <h3 class="eq-title">Break-even condition for adding an RPC worker</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-rpc-breakeven" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ \frac{S_{m}}{B_{\text{host}}} \;>\; \frac{S_{m}}{B_{\text{worker}}} \;+\; \frac{D_{\text{act}}}{R} + 2\tau \]</div>
  <p class="eq-note">Read as: moving \( S_{m} \) bytes of weights onto a worker pays only when the time the host stops spending on them exceeds the time the worker spends plus the cost of the extra hop. The condition is almost always satisfied when the bytes were spilling to host RAM, and almost never when they already fit in host VRAM.</p>
  <div class="deriv"><ol>
    <li>Write \( t_{\text{tok}} \) from the relation above for the configuration before the move, with \( S_{m} \) bytes still on the host: the host contributes \( S_{m}/B_{\text{host}} \).</li>
    <li>Write it again after the move: the worker contributes \( S_{m}/B_{\text{worker}} \), and one new boundary contributes \( D_{\text{act}}/R + 2\tau \).</li>
    <li>Every other term is common to both expressions and cancels.</li>
    <li>The move reduces \( t_{\text{tok}} \) exactly when the removed term exceeds the two added terms, which is the inequality stated.</li>
    <li>Case that pays. \( S_{m} = 6\ \mathrm{GB} \) spilling to host RAM at \( B_{\text{host}} = 50\ \mathrm{GB\,s^{-1}} \) costs \( 120\ \mathrm{ms} \) per token. On a worker GPU at \( B_{\text{worker}} = 400\ \mathrm{GB\,s^{-1}} \) it costs \( 15\ \mathrm{ms} \), plus roughly \( 0.5\ \mathrm{ms} \) of link cost from the figures above. The move saves about \( 105\ \mathrm{ms} \) per token.</li>
    <li>Case that does not. The same \( 6\ \mathrm{GB} \) already resident in host VRAM at \( 450\ \mathrm{GB\,s^{-1}} \) costs \( 13.3\ \mathrm{ms} \). A worker at \( 400\ \mathrm{GB\,s^{-1}} \) costs \( 15\ \mathrm{ms} \) plus the hop, so the move loses about \( 2.2\ \mathrm{ms} \) per token and adds a failure domain.</li>
  </ol></div>
  <div class="vars" id="v-rpc-breakeven" hidden><div class="table-wrap"><table>
    <caption>Symbols in the break-even condition. Link symbols carry the meanings established in the per-token relation.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(S_{m}\)</td><td>Weight bytes being moved from host to worker</td><td>B</td></tr>
      <tr><td>\(B_{\text{host}}\)</td><td>Achieved bandwidth of the host memory those bytes currently sit in</td><td>B&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(B_{\text{worker}}\)</td><td>Achieved bandwidth of the worker memory they would move to</td><td>B&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(D_{\text{act}}\)</td><td>Activation tensor crossing the new boundary</td><td>B</td></tr>
      <tr><td>\(R\)</td><td>Achieved link throughput to the worker</td><td>B&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(\tau\)</td><td>One-way link latency to the worker</td><td>s</td></tr>
    </tbody>
  </table></div></div>
</div>
"""


# %% Build and agent-loop equations ------------------------------------------
# Drawn on by: local-code-build-test.html
_BUILD_EQUATIONS: Dict[str, str] = {}

_BUILD_EQUATIONS["parallel-jobs"] = r"""
<div class="eq" id="eq-parallel-jobs">
  <div class="eq-head">
    <h3 class="eq-title">Safe parallel job count for a C++ build</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-parallel-jobs" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ j^{\star} \;=\; \min\!\left( n_{\text{cpu}},\; \left\lfloor \frac{M_{\text{avail}}}{M_{\text{job}}} \right\rfloor \right) \]</div>
  <p class="eq-note">Relevant because an agent told to "build the project" will reach for <span class="mono">-j$(nproc)</span>, and on a machine that is simultaneously holding a 19&nbsp;GB model resident the memory term, not the core count, is the binding constraint. Set <span class="mono">CMAKE_BUILD_PARALLEL_LEVEL</span> in the environment so the limit holds regardless of how the build is invoked<a class="cite" href="references.html#r28">[28]</a>.</p>
  <div class="deriv"><ol>
    <li>Compilation of independent translation units is embarrassingly parallel up to the core count, so \( j \le n_{\text{cpu}} \) is the first bound.</li>
    <li>Each concurrent compiler process holds a peak resident set \( M_{\text{job}} \). Heavily templated C++ and link-time optimisation push this well above the 300&ndash;500&nbsp;MB that plain C costs; 1.5&ndash;2.5&nbsp;GB per job is realistic for a template-heavy target.</li>
    <li>Exceeding available memory does not fail cleanly. The machine swaps, the build slows by an order of magnitude, and the resident model may be evicted. So \( j \le \lfloor M_{\text{avail}}/M_{\text{job}} \rfloor \) is the second bound.</li>
    <li>Take the smaller of the two bounds.</li>
    <li>Worked example for a machine running a local coding model. 16 logical cores, 64&nbsp;GB installed, 19&nbsp;GB pinned by the model server and 8&nbsp;GB by the operating system and editor, leaving \( M_{\text{avail}} = 37\ \mathrm{GB} \). At \( M_{\text{job}} = 2\ \mathrm{GB} \): \( \lfloor 37/2 \rfloor = 18 \), so \( j^{\star} = \min(16,\,18) = 16 \).</li>
    <li>Same machine with 32&nbsp;GB installed: \( M_{\text{avail}} = 5\ \mathrm{GB} \), \( \lfloor 5/2 \rfloor = 2 \), and \( j^{\star} = 2 \). The core count is irrelevant.</li>
  </ol></div>
  <div class="vars" id="v-parallel-jobs" hidden><div class="table-wrap"><table>
    <caption>Symbols in the parallel-job relation. \(M_{\text{avail}}\) is memory free after the model server and the operating system have taken their share, not installed memory.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(j^{\star}\)</td><td>Jobs to pass to <span class="mono">cmake --build . --parallel</span> or to <span class="mono">CMAKE_BUILD_PARALLEL_LEVEL</span></td><td>dimensionless</td></tr>
      <tr><td>\(n_{\text{cpu}}\)</td><td>Logical cores available to the build</td><td>dimensionless</td></tr>
      <tr><td>\(M_{\text{avail}}\)</td><td>System memory free with the model server already resident</td><td>B</td></tr>
      <tr><td>\(M_{\text{job}}\)</td><td>Peak resident set of one compiler process</td><td>B</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_BUILD_EQUATIONS["amdahl"] = r"""
<div class="eq" id="eq-amdahl">
  <div class="eq-head">
    <h3 class="eq-title">Amdahl speed-up of a parallel build</h3>
    <div class="eq-tools"><span class="pill stated">Stated</span>
      <button class="info" aria-controls="v-amdahl" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ S(j) \;=\; \frac{1}{(1-p) + \dfrac{p}{j}}, \qquad \lim_{j\to\infty} S(j) \;=\; \frac{1}{1-p} \]</div>
  <p class="eq-note">The serial fraction of a native build is the configure step and the final link, and a single-threaded link of a large binary can be tens of seconds. With \( p = 0.85 \) the ceiling is \( S_{\infty} = 6.7 \) no matter how many cores are added, which is worth knowing before an agent is allowed to raise the job count in a loop.</p>
  <div class="vars" id="v-amdahl" hidden><div class="table-wrap"><table>
    <caption>Symbols in Amdahl's relation as applied to a compile-and-link cycle.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(S(j)\)</td><td>Speed-up over a single-job build</td><td>dimensionless</td></tr>
      <tr><td>\(p\)</td><td>Fraction of total build time that parallelises, essentially the compile phase</td><td>dimensionless</td></tr>
      <tr><td>\(j\)</td><td>Concurrent jobs</td><td>dimensionless</td></tr>
      <tr><td>\(1-p\)</td><td>Serial fraction: configure, dependency scan, archive and link</td><td>dimensionless</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_BUILD_EQUATIONS["agent-loop"] = r"""
<div class="eq" id="eq-agent-loop">
  <div class="eq-head">
    <h3 class="eq-title">Wall clock of one write-build-test agent task</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-agent-loop" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ T_{\text{task}} \;=\; N_{\text{it}}\left( \frac{n_{\text{in}}}{r_{p}} \;+\; \frac{n_{\text{out}}}{r} \;+\; T_{\text{build}} \;+\; T_{\text{test}} \right) \]</div>
  <p class="eq-note">Sizing a local coding setup means deciding where the time goes. For a small edit on a fast build the model dominates and a bigger model is the wrong trade; for a cold C++ build the compiler dominates and model quality is nearly free, because a better model lowers \( N_{\text{it}} \) and \( N_{\text{it}} \) multiplies everything.</p>
  <div class="deriv"><ol>
    <li>One iteration of the loop is: read context, emit a patch, build, run tests. The agent cannot overlap these, because each step consumes the previous step's output.</li>
    <li>Reading \( n_{\text{in}} \) prompt tokens at prefill rate \( r_{p} \) takes \( n_{\text{in}}/r_{p} \). Prefill is compute-bound and batched, so \( r_{p} \) is typically one to two orders of magnitude above \( r \).</li>
    <li>Emitting \( n_{\text{out}} \) tokens at decode rate \( r \) takes \( n_{\text{out}}/r \), where \( r \) is bounded by the bandwidth ceiling derived above.</li>
    <li>Add the build and test times, then multiply by the number of iterations needed to converge.</li>
    <li>Worked example, Python edit. \( N_{\text{it}} = 3 \), \( n_{\text{in}} = 12000 \) at \( r_{p} = 900\ \mathrm{token\,s^{-1}} \), \( n_{\text{out}} = 800 \) at \( r = 15\ \mathrm{token\,s^{-1}} \), \( T_{\text{build}} = 0 \), \( T_{\text{test}} = 6\ \mathrm{s} \). Per iteration: \( 13.3 + 53.3 + 0 + 6 = 72.6\ \mathrm{s} \), total \( 218\ \mathrm{s} \). Generation is 73&nbsp;% of it, so a faster model wins.</li>
    <li>Worked example, C++ edit on an incremental build. Same model figures with \( T_{\text{build}} = 95\ \mathrm{s} \) and \( T_{\text{test}} = 40\ \mathrm{s} \): per iteration \( 201.6\ \mathrm{s} \), total \( 605\ \mathrm{s} \). Generation is now 26&nbsp;%, so spending that budget on a model that converges in two iterations instead of three saves more than any decode speed-up available.</li>
  </ol></div>
  <div class="vars" id="v-agent-loop" hidden><div class="table-wrap"><table>
    <caption>Symbols in the agent-iteration relation. Measure \(r\) and \(r_{p}\) with the probe script shipped alongside this page set rather than taking advertised figures.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(T_{\text{task}}\)</td><td>Wall clock from prompt to passing tests</td><td>s</td></tr>
      <tr><td>\(N_{\text{it}}\)</td><td>Iterations of the write-build-test loop needed to converge</td><td>dimensionless</td></tr>
      <tr><td>\(n_{\text{in}}\)</td><td>Prompt tokens read per iteration, including re-read source files</td><td>token</td></tr>
      <tr><td>\(r_{p}\)</td><td>Prefill (prompt evaluation) rate</td><td>token&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(n_{\text{out}}\)</td><td>Tokens generated per iteration, reasoning traces included</td><td>token</td></tr>
      <tr><td>\(r\)</td><td>Decode rate, bounded by the bandwidth ceiling</td><td>token&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(T_{\text{build}}\)</td><td>Compile and link time per iteration</td><td>s</td></tr>
      <tr><td>\(T_{\text{test}}\)</td><td>Test-suite run time per iteration</td><td>s</td></tr>
    </tbody>
  </table></div></div>
</div>
"""


# %% Monitoring and telemetry equations --------------------------------------
# Drawn on by: GPU_monitoring_setup.html, both Prometheus install pages,
#              Promethius_Grafana_windows11-llama-monitoring-tutorial.html
_MONITORING_EQUATIONS: Dict[str, str] = {}

_MONITORING_EQUATIONS["prom-disk"] = r"""
<div class="eq" id="eq-prom-disk">
  <div class="eq-head">
    <h3 class="eq-title">Prometheus on-disk size</h3>
    <div class="eq-tools"><span class="pill stated">Stated</span>
      <button class="info" aria-controls="v-prom-disk" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ D \;=\; T_{\text{ret}} \cdot \lambda \cdot \beta \]</div>
  <p class="eq-note">This is the sizing relation given in the Prometheus storage documentation, which also states that the server averages one to two bytes per stored sample and recommends setting a size-based retention limit to at most 80&ndash;85&nbsp;% of the allocated disk<a class="cite" href="references.html#r18">[18]</a>. Reducing the number of series is more effective than reducing the sample rate, because samples within a series compress well and each new series does not.</p>
  <div class="vars" id="v-prom-disk" hidden><div class="table-wrap"><table>
    <caption>Symbols in the Prometheus storage relation, named to match the documented form <span class="mono">needed_disk_space = retention_time_seconds * ingested_samples_per_second * bytes_per_sample</span>.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(D\)</td><td>Disk occupied by the time-series database at steady state</td><td>B</td></tr>
      <tr><td>\(T_{\text{ret}}\)</td><td>Retention window, <span class="mono">--storage.tsdb.retention.time</span>, default 15 d when no size limit is set<a class="cite" href="references.html#r18">[18]</a></td><td>s</td></tr>
      <tr><td>\(\lambda\)</td><td>Ingested samples per second across every scrape job</td><td>sample&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(\beta\)</td><td>Bytes per stored sample, documented as 1&ndash;2 on average<a class="cite" href="references.html#r18">[18]</a></td><td>B&middot;sample<sup>&minus;1</sup></td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_MONITORING_EQUATIONS["prom-ingest"] = r"""
<div class="eq" id="eq-prom-ingest">
  <div class="eq-head">
    <h3 class="eq-title">Ingested sample rate from the scrape configuration</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-prom-ingest" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ \lambda \;=\; \sum_{j} \frac{n_{j}}{T_{s,j}} \]</div>
  <p class="eq-note">Feeds the storage relation above. Worth computing before adding an exporter rather than after, because a GPU exporter publishing a few hundred series per card across four nodes is a larger step than it looks.</p>
  <div class="deriv"><ol>
    <li>Each scrape job \( j \) collects \( n_{j} \) distinct time series from its targets on every scrape.</li>
    <li>It scrapes once every \( T_{s,j} \) seconds, so it contributes \( n_{j}/T_{s,j} \) samples per second.</li>
    <li>Jobs are independent, so the total is the sum over jobs.</li>
    <li>Worked example for the four-node stack on this page set. <span class="mono">windows_exporter</span> publishing roughly 1500 series on each of 4 nodes at \( T_{s} = 15\ \mathrm{s} \) gives \( 6000/15 = 400\ \mathrm{sample\,s^{-1}} \). An <span class="mono">nvidia_gpu_exporter</span> adding about 120 series on each of 3 GPU nodes at 15&nbsp;s gives \( 360/15 = 24 \). <span class="mono">llama-server --metrics</span> adding roughly 30 series at 15&nbsp;s gives 2. Total \( \lambda \approx 426\ \mathrm{sample\,s^{-1}} \).</li>
    <li>Substituting into the storage relation with \( T_{\text{ret}} = 15\ \mathrm{d} = 1.296\times10^{6}\ \mathrm{s} \) and \( \beta = 2\ \mathrm{B} \): \( D = 1.296\times10^{6} \times 426 \times 2 = 1.10\times10^{9}\ \mathrm{B} \approx 1.1\ \mathrm{GB} \). Allow several times that for the write-ahead log, memory-mapped chunks and compaction headroom.</li>
    <li>The series counts above are order-of-magnitude figures for planning, not measurements. Replace them with <span class="mono">prometheus_tsdb_head_series</span> read from your own server once it has been running.</li>
  </ol></div>
  <div class="vars" id="v-prom-ingest" hidden><div class="table-wrap"><table>
    <caption>Symbols in the ingest-rate relation, summed over the scrape jobs defined in <span class="mono">prometheus.yml</span>.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(\lambda\)</td><td>Total ingested samples per second</td><td>sample&middot;s<sup>&minus;1</sup></td></tr>
      <tr><td>\(n_{j}\)</td><td>Distinct time series returned by every target of job \(j\) combined</td><td>dimensionless</td></tr>
      <tr><td>\(T_{s,j}\)</td><td>Scrape interval for job \(j\), <span class="mono">scrape_interval</span></td><td>s</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_MONITORING_EQUATIONS["rate-window"] = r"""
<div class="eq" id="eq-rate-window">
  <div class="eq-head">
    <h3 class="eq-title">Minimum range-vector window for <span class="mono">rate()</span></h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-rate-window" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ \left\lfloor \frac{w}{T_{s}} \right\rfloor \;\ge\; 2 + f \qquad\Longrightarrow\qquad w \;\ge\; (2+f)\,T_{s} \]</div>
  <p class="eq-note">The usual advice to make the window four times the scrape interval is this inequality with \( f = 2 \). Panels that go blank intermittently are nearly always a window too close to the scrape interval, not a broken exporter.</p>
  <div class="deriv"><ol>
    <li><span class="mono">rate()</span> is documented as the per-second average rate of increase across the range vector, computed between its first and last samples and extrapolated to the ends of the range to allow for missed scrapes<a class="cite" href="references.html#r19">[19]</a>. It therefore needs two samples inside the window to return anything. The PromQL function reference states that two-float-sample minimum explicitly only for <span class="mono">deriv</span> and <span class="mono">predict_linear</span>; for <span class="mono">rate</span> it is the observed behaviour rather than a documented guarantee, so treat this step as empirical.</li>
    <li>A window of width \( w \) at scrape interval \( T_{s} \) contains \( \lfloor w/T_{s} \rfloor \) samples when every scrape succeeds.</li>
    <li>Allowing \( f \) consecutive scrapes to fail or arrive late without the panel emptying requires \( 2+f \) slots rather than 2.</li>
    <li>Rearranging gives \( w \ge (2+f)T_{s} \).</li>
    <li>For the \( T_{s} = 15\ \mathrm{s} \) jobs on this page set, tolerating two missed scrapes gives \( w \ge 60\ \mathrm{s} \), which is why the dashboard expressions use <span class="mono">[1m]</span>.</li>
    <li>Raising \( T_{s} \) without raising \( w \) is the usual regression. Pin the relationship by templating the window from the scrape interval instead of hard-coding it.</li>
  </ol></div>
  <div class="vars" id="v-rate-window" hidden><div class="table-wrap"><table>
    <caption>Symbols in the range-window condition for PromQL rate and increase functions over counters.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(w\)</td><td>Range-vector window, the bracketed duration in <span class="mono">rate(metric[w])</span></td><td>s</td></tr>
      <tr><td>\(T_{s}\)</td><td>Scrape interval of the job producing the metric</td><td>s</td></tr>
      <tr><td>\(f\)</td><td>Consecutive failed or late scrapes to tolerate without the expression emptying</td><td>dimensionless</td></tr>
    </tbody>
  </table></div></div>
</div>
"""

_MONITORING_EQUATIONS["gpu-utilisation"] = r"""
<div class="eq" id="eq-gpu-utilisation">
  <div class="eq-head">
    <h3 class="eq-title">Utilisation from a cumulative busy-time counter</h3>
    <div class="eq-tools"><span class="pill derived">Derived here</span>
      <button class="info" aria-controls="v-gpu-utilisation" aria-expanded="false">&#9432;&nbsp;<span class="info-label">Define variables</span></button></div>
  </div>
  <div class="eq-body">\[ U(w) \;=\; \frac{c(t) - c(t-w)}{w} \;=\; \mathrm{rate}\bigl(c[w]\bigr), \qquad 0 \le U \le n_{\text{dev}} \]</div>
  <p class="eq-note">Worth stating explicitly because the GPU exporters publish both kinds of metric and they are not interchangeable: a cumulative busy-seconds counter must be differenced, while an instantaneous percentage gauge must not be. Applying <span class="mono">rate()</span> to a gauge, or omitting it on a counter, are the two failure modes that produce plausible-looking but wrong dashboards.</p>
  <div class="deriv"><ol>
    <li>A busy-time counter \( c(t) \) accumulates seconds during which the device was executing work, and only ever increases.</li>
    <li>Over a window \( w \) the device was busy for \( c(t) - c(t-w) \) seconds out of \( w \) seconds elapsed.</li>
    <li>The ratio of those two is the fraction of wall-clock time the device was busy, which is the definition of utilisation.</li>
    <li>That ratio is precisely what PromQL <span class="mono">rate()</span> computes over a counter. The function reference states that breaks in monotonicity, such as a counter reset when the exporter or driver restarts, are adjusted for automatically<a class="cite" href="references.html#r19">[19]</a>, which is why the raw difference must not be taken by hand.</li>
    <li>When the counter aggregates \( n_{\text{dev}} \) devices the result saturates at \( n_{\text{dev}} \) rather than 1, so divide by the device count before plotting a percentage.</li>
    <li>\( w \) must satisfy the window condition derived above, otherwise the panel empties whenever a scrape is missed.</li>
  </ol></div>
  <div class="vars" id="v-gpu-utilisation" hidden><div class="table-wrap"><table>
    <caption>Symbols in the counter-based utilisation relation, applicable to GPU busy time, CPU time and any other cumulative seconds counter.</caption>
    <thead><tr><th scope="col">Symbol</th><th scope="col">Meaning</th><th scope="col">Unit</th></tr></thead>
    <tbody>
      <tr><td>\(U(w)\)</td><td>Mean utilisation over the window</td><td>dimensionless (&times;100 for per cent)</td></tr>
      <tr><td>\(c(t)\)</td><td>Cumulative busy-seconds counter at time \(t\)</td><td>s</td></tr>
      <tr><td>\(w\)</td><td>Range-vector window</td><td>s</td></tr>
      <tr><td>\(n_{\text{dev}}\)</td><td>Devices or cores the counter aggregates</td><td>dimensionless</td></tr>
    </tbody>
  </table></div></div>
</div>
"""


# %% Public registry ----------------------------------------------------------
#: Every equation available to the build, keyed by slug.  The slug is also the
#: DOM id (prefixed ``eq-``) and the variable-table id (prefixed ``v-``), so a
#: page may deep-link to any equation as ``<page>.html#eq-<slug>``.
EQUATIONS: Dict[str, str] = {}
EQUATIONS.update(_MEMORY_EQUATIONS)
EQUATIONS.update(_THROUGHPUT_EQUATIONS)
EQUATIONS.update(_BUILD_EQUATIONS)
EQUATIONS.update(_MONITORING_EQUATIONS)


def get(slug: str) -> str:
    """Return the HTML for one equation block.

    Parameters
    ----------
    slug : str
        Key into :data:`EQUATIONS`, for example ``"kv-cache"``.

    Returns
    -------
    str
        The equation block's HTML, stripped of surrounding blank lines.

    Raises
    ------
    KeyError
        If the slug is not registered.  Raising rather than returning an empty
        string is deliberate: a typo in a page plan must stop the build instead
        of silently producing a page with a missing equation.
    """
    if slug not in EQUATIONS:
        raise KeyError(
            f"unknown equation slug {slug!r}; "
            f"registered slugs are: {sorted(EQUATIONS)}"
        )
    return EQUATIONS[slug].strip()


def render_group(slugs) -> str:
    """Concatenate several equation blocks in the order given.

    Parameters
    ----------
    slugs : Iterable[str]
        Equation slugs to emit.

    Returns
    -------
    str
        The blocks joined by a blank line, ready to drop into a page section.
    """
    return "\n\n".join(get(slug) for slug in slugs)
