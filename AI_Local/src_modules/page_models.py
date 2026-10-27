# -*- coding: utf-8 -*-
"""
page_models.py -- body content for ollama-model-selection.html

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

PURPOSE
-------
Supplies the body fragment for the page that identifies which models in the
Ollama library suit local code generation and testing, and how to size them
against the hardware in this deployment.

SOURCING POLICY FOR THIS PAGE
-----------------------------
Model facts on this page are of three kinds and are kept visibly distinct:

1. Figures published on an Ollama model page -- tag size, context window,
   capability labels, licence, benchmark scores published by the model's
   author.  Cited to that page.  Tagged "vendor" confidence in
   ``references.py`` because a model page is revised without notice.
2. Figures computed here from those published figures.  Shown with the
   derivation in an equation block.
3. Judgements about suitability.  Stated as judgements, with the reasoning
   given, never dressed up as measurements.

What is deliberately NOT on this page: throughput numbers for specific
hardware, quality rankings not published by the model's author, and
quantisation levels for tags that do not state them.  Those are measured, not
looked up, and the page says how to measure them.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import eq_library


# %% Body fragment -----------------------------------------------------------
def build() -> str:
    """Return the complete body fragment for ollama-model-selection.html."""
    return r"""
<section class="hero">
  <div class="container">
    <div class="eyebrow">Model selection</div>
    <h1>Which Ollama models are worth running for local code work</h1>
    <p class="lead">A model that writes good code and will not fit on the card is no use, and a model that fits but cannot call a tool cannot drive a build. This page works the constraint from both ends: what the library actually offers for code and agent work, and what the hardware will hold once the key/value cache is accounted for.</p>
    <p class="small muted">Sizes, context windows, capability labels and benchmark figures are quoted from the Ollama model pages cited inline and were read on 2026-10-18. Model pages are revised without notice, so re-check a tag before committing to it. Every computed figure is shown with its derivation.</p>
  </div>
</section>

<section id="on-this-page">
  <div class="container">
    <h2>On this page</h2>
    <ul class="toc">
      <li><a href="#criteria">1. What actually matters when choosing</a></li>
      <li><a href="#shortlist">2. The shortlist</a></li>
      <li><a href="#fit">3. Does it fit? The memory arithmetic</a></li>
      <li><a href="#speed">4. Will it be fast enough?</a></li>
      <li><a href="#recommend">5. Recommendations by VRAM budget</a></li>
      <li><a href="#distributed">6. When the model does not fit on one machine</a></li>
      <li><a href="#measure">7. Measure it yourself</a></li>
      <li><a href="#caveats">8. What this page does not tell you</a></li>
    </ul>
  </div>
</section>

<section id="criteria">
  <div class="container">
    <h2>1. What actually matters when choosing</h2>

    <p>Five properties decide whether a model can drive the build loop described on the <a href="local-code-build-test.html">local build and test page</a>. Only two of them are about code quality.</p>

    <div class="table-wrap">
      <table>
        <caption>Selection criteria for a model that will write, build and test code locally, in the order they eliminate candidates.</caption>
        <thead><tr><th scope="col">Property</th><th scope="col">Why it decides</th><th scope="col">How to check it</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>Tool calling</strong></td>
            <td>Without it the model cannot invoke the terminal at all. Open WebUI's terminal integration needs native function calling<a class="cite" href="references.html#r5">[5]</a>, and a model with no tool support cannot satisfy that however good its code is</td>
            <td>The <span class="mono">tools</span> capability label on the Ollama model page</td>
          </tr>
          <tr>
            <td><strong>Context window</strong></td>
            <td>Source under edit, plus a build log, plus the conversation. A template-heavy C++ error is thousands of tokens by itself</td>
            <td>Stated per tag on the model page. Then check it against VRAM with the relation in &sect;3 &mdash; the advertised window is not the one you get</td>
          </tr>
          <tr>
            <td><strong>Weight footprint</strong></td>
            <td>Weights plus cache plus runtime must fit, or layers spill to system RAM and throughput drops by roughly an order of magnitude</td>
            <td>Tag size on the model page, checked against the footprint relation</td>
          </tr>
          <tr>
            <td><strong>Active parameters</strong></td>
            <td>Decode rate tracks the parameters read per token, not the total. A routed mixture of experts occupies the card like its total size and streams like its active size</td>
            <td>Stated on the model page for some models, for example 80B total with 3B active<a class="cite" href="references.html#r33">[33]</a></td>
          </tr>
          <tr>
            <td><strong>Agentic training</strong></td>
            <td>Multi-step tool loops are a distinct skill from single-shot code completion. The Open Terminal documentation notes that small models often struggle with the multi-step loop<a class="cite" href="references.html#r3">[3]</a></td>
            <td>The model page's own description, and any SWE-Bench or Terminal&nbsp;Bench figure its author published</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout info-box">
      <p><strong>Tool calling is the hard gate.</strong> Of the criteria above, four are tradeable and one is not. A 32B model with excellent code completion and no tool support cannot drive a build at all, while a 4B model with reliable tool calling can &mdash; slowly, and with more iterations, but it closes the loop. Filter on <span class="mono">tools</span> first and judge quality among what survives.</p>
    </div>
  </div>
</section>

<section id="shortlist">
  <div class="container">
    <h2>2. The shortlist</h2>

    <p>Every row below carries the <span class="mono">tools</span> capability on its Ollama page, which is the gate from &sect;1. Sizes are the figures the tag listing shows.</p>

    <div class="table-wrap">
      <table>
        <caption>Code and agent models from the Ollama library that carry tool-calling support, with the figures published on each model page. Sizes are as listed; a tag listing may show a range where several builds share a tag. "Quant" is given only where the page states it.</caption>
        <thead>
          <tr><th scope="col">Model</th><th scope="col">Tag</th><th scope="col">Size</th><th scope="col">Context</th><th scope="col">Quant</th><th scope="col">Capabilities</th><th scope="col">Published positioning</th></tr>
        </thead>
        <tbody>
          <tr>
            <td rowspan="2"><strong>qwen3-coder</strong><a class="cite" href="references.html#r11">[11]</a></td>
            <td class="mono">30b</td><td class="mono">19 GB</td><td class="mono">256K</td><td class="faint">not stated</td><td>tools</td>
            <td rowspan="2">Long-context coding and agent model. Page states 256K native, reaching 1M "using extrapolation methods"</td>
          </tr>
          <tr><td class="mono">480b</td><td class="mono">290 GB</td><td class="mono">256K</td><td class="faint">not stated</td><td>tools</td></tr>
          <tr>
            <td><strong>qwen3-coder-next</strong><a class="cite" href="references.html#r33">[33]</a></td>
            <td class="mono">q4_K_M</td><td class="mono">52 GB</td><td class="mono">256K</td><td class="mono">q4_K_M</td><td>tools</td>
            <td>80B total, <strong>3B active per token</strong>. Built on Qwen3-Next-80B-A3B-Base. Page states non-thinking mode only</td>
          </tr>
          <tr>
            <td><strong>devstral-small-2</strong><a class="cite" href="references.html#r13">[13]</a></td>
            <td class="mono">24b</td><td class="mono">15 GB</td><td class="mono">384K</td><td class="faint">not stated</td><td>tools, vision</td>
            <td>"Excels at using tools to explore codebases, editing multiple files and power software engineering agents." Apache 2.0. Needs Ollama 0.13.3 or later</td>
          </tr>
          <tr>
            <td rowspan="3"><strong>laguna-xs-2.1</strong><a class="cite" href="references.html#r15">[15]</a></td>
            <td class="mono">q4_K_M</td><td class="mono">20 GB</td><td class="mono">256K</td><td class="mono">Q4_K_M</td><td>tools, thinking</td>
            <td rowspan="3">Poolside. "Designed for agentic coding and long-horizon work on a local machine." The only shortlisted model that publishes a full quantisation ladder</td>
          </tr>
          <tr><td class="mono">q8_0</td><td class="mono">36 GB</td><td class="mono">256K</td><td class="mono">8-bit</td><td>tools, thinking</td></tr>
          <tr><td class="mono">bf16</td><td class="mono">67 GB</td><td class="mono">256K</td><td class="mono">BF16</td><td>tools, thinking</td></tr>
          <tr>
            <td rowspan="2"><strong>qwen3.6</strong><a class="cite" href="references.html#r14">[14]</a></td>
            <td class="mono">27b</td><td class="mono">18&ndash;19 GB</td><td class="mono">256K</td><td class="faint">not stated</td><td>tools, thinking, vision</td>
            <td rowspan="2">General model with coding emphasis. Page cites better frontend workflows and repository-level reasoning, plus optional retention of reasoning context across turns</td>
          </tr>
          <tr><td class="mono">35b</td><td class="mono">23&ndash;24 GB</td><td class="mono">256K</td><td class="faint">not stated</td><td>tools, thinking, vision</td></tr>
          <tr>
            <td rowspan="2"><strong>gpt-oss</strong><a class="cite" href="references.html#r16">[16]</a></td>
            <td class="mono">20b</td><td class="mono">14 GB</td><td class="mono">128K</td><td class="mono">MXFP4, 4.25 bit</td><td>tools, thinking</td>
            <td rowspan="2">OpenAI open-weight reasoning and agent models. Apache 2.0. Page states MXFP4 lets the smaller model run "on systems with as little as 16GB memory" and the larger fit "on a single 80GB GPU"</td>
          </tr>
          <tr><td class="mono">120b</td><td class="mono">65 GB</td><td class="mono">128K</td><td class="mono">MXFP4, 4.25 bit</td><td>tools, thinking</td></tr>
          <tr>
            <td rowspan="2"><strong>nemotron-3-nano</strong><a class="cite" href="references.html#r34">[34]</a></td>
            <td class="mono">4b</td><td class="mono">2.8&ndash;2.9 GB</td><td class="mono">256K</td><td class="faint">not stated</td><td>tools, thinking</td>
            <td rowspan="2">NVIDIA, trained from scratch. "A new Standard for Efficient, Open, and Intelligent Agentic Models", unified for reasoning and non-reasoning tasks</td>
          </tr>
          <tr><td class="mono">30b</td><td class="mono">18&ndash;24 GB</td><td class="mono">1M</td><td class="faint">not stated</td><td>tools, thinking</td></tr>
          <tr>
            <td rowspan="3"><strong>qwen2.5-coder</strong><a class="cite" href="references.html#r12">[12]</a></td>
            <td class="mono">7b</td><td class="mono">4.7 GB</td><td class="mono">32K</td><td class="faint">not stated</td><td>tools</td>
            <td rowspan="3">Older generation, still the broadest size ladder: 0.5b, 1.5b, 3b, 7b, 14b, 32b. 32K context on every tag, which is the binding limit for agent work</td>
          </tr>
          <tr><td class="mono">14b</td><td class="mono">9.0 GB</td><td class="mono">32K</td><td class="faint">not stated</td><td>tools</td></tr>
          <tr><td class="mono">32b</td><td class="mono">20 GB</td><td class="mono">32K</td><td class="faint">not stated</td><td>tools</td></tr>
        </tbody>
      </table>
    </div>

    <h3>2.1 The one benchmark comparison the library publishes</h3>

    <p>Most model pages give no numbers. The <span class="mono">devstral-small-2</span> page is the exception among the shortlist: it publishes agentic software-engineering scores for itself, for the larger Devstral&nbsp;2, and for a proprietary comparator<a class="cite" href="references.html#r13">[13]</a>.</p>

    <div class="table-wrap">
      <table>
        <caption>Agentic software-engineering figures as published on the <span class="mono">devstral-small-2</span> Ollama model page. These are the model author's own published figures, reproduced for comparison; they were not measured here and no equivalent figures are published for the other shortlisted models.</caption>
        <thead><tr><th scope="col">Model</th><th scope="col">SWE-Bench Verified</th><th scope="col">SWE-Bench Multilingual</th><th scope="col">Terminal Bench</th><th scope="col">Runs locally?</th></tr></thead>
        <tbody>
          <tr><td>Devstral Small 2 (24B)</td><td class="mono">65.8 %</td><td class="mono">51.6 %</td><td class="mono">32.0 %</td><td>Yes, 15 GB</td></tr>
          <tr><td>Devstral 2 (123B)</td><td class="mono">72.2 %</td><td class="mono">61.3 %</td><td class="mono">40.5 %</td><td>Only with substantial VRAM</td></tr>
          <tr><td>Claude Sonnet 4.5 (comparator)</td><td class="mono">77.2 %</td><td class="faint">not listed</td><td class="faint">not listed</td><td>No</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong>Read these as the author's published claims, not as an independent comparison.</strong> They are the figures on the distribution page, measured by the model's author under its own harness. Scores from different authors under different harnesses are not comparable, which is precisely why no cross-vendor ranking is attempted on this page. The useful signal is the gap between the 24B and the 123B at the same harness: roughly six points of SWE-Bench Verified for a model eight times the size.</p>
    </div>

    <h3>2.2 Deliberately excluded</h3>

    <div class="table-wrap">
      <table>
        <caption>Models that appear when searching the library for coding, and the reason each is not shortlisted for this deployment.</caption>
        <thead><tr><th scope="col">Model</th><th scope="col">Reason</th></tr></thead>
        <tbody>
          <tr><td><span class="mono">deepseek-coder</span>, <span class="mono">starcoder2</span>, <span class="mono">codellama</span>, <span class="mono">codegemma</span>, <span class="mono">yi-coder</span>, <span class="mono">opencoder</span>, <span class="mono">dolphincoder</span>, <span class="mono">stable-code</span></td><td>Completion-oriented generations without a <span class="mono">tools</span> capability label on their library entries<a class="cite" href="references.html#r10">[10]</a>, so they cannot drive a terminal</td></tr>
          <tr><td><span class="mono">sqlcoder</span>, <span class="mono">duckdb-nsql</span></td><td>Single-domain text-to-SQL</td></tr>
          <tr><td><span class="mono">qwen3-coder:480b</span>, <span class="mono">devstral-2</span> (123b), <span class="mono">gpt-oss:120b</span></td><td>Listed for completeness. The 480b tag's page states a 250&nbsp;GB minimum of memory or unified memory to run locally<a class="cite" href="references.html#r11">[11]</a>; these are above a home deployment unless several nodes are pooled (&sect;6)</td></tr>
          <tr><td>Any tag ending <span class="mono">-cloud</span></td><td>Served remotely. The point of this page set is that nothing leaves the network</td></tr>
          <tr><td>Any tag ending <span class="mono">-mlx</span></td><td>Apple MLX builds. Irrelevant to the Windows and WSL2 nodes in this deployment</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</section>

<section id="fit">
  <div class="container">
    <h2>3. Does it fit? The memory arithmetic</h2>

    <p>Three terms compete for the same device memory: the weights, the key/value cache, and the runtime's own allocations. The published tag size is only the first of them, and the second is the one that moves when you change a command-line flag.</p>

    """ + eq_library.get("quant-footprint") + r"""

    """ + eq_library.get("moe-active") + r"""

    """ + eq_library.get("kv-cache") + r"""

    """ + eq_library.get("ctx-budget") + r"""

    <div class="callout info-box">
      <p><strong>Unit convention on this page: binary, throughout.</strong> Every quantity in GB below is a <em>gibibyte</em>, \(2^{30} = 1\,073\,741\,824\) bytes. This matters because the two conventions differ by 7&nbsp;%, which is comfortably enough to turn a model that does not fit into one that appears to. Binary is the right choice here because it is what the tools report: <span class="mono">nvidia-smi</span> reports MiB, and allocation happens in binary units. Treat a vendor's decimal "GB" as the optimistic figure and convert before comparing it against a card. The <a href="../index.html#fit">calculator on the repository homepage</a> uses this same convention, so its results and this page's agree.</p>
    </div>

    <h3>3.1 Worked fit, 24 GB card</h3>

    <p>Taking <span class="mono">qwen3-coder:30b</span> at its published 19&nbsp;GB<a class="cite" href="references.html#r11">[11]</a> on a 24&nbsp;GB card, with \( V_{\text{rt}} = 1.2\ \mathrm{GB} \), \( n_{\text{seq}} = 1 \) and <span class="mono">f16</span> cache so \( b_{kv} = 2\ \mathrm{B} \):</p>

    <div class="table-wrap">
      <table>
        <caption>Context budget on a 24&nbsp;GB card, evaluated from the context-budget relation above. The architectural quantities \(n_{\ell}\), \(n_{kv}\) and \(d_{h}\) are placeholders of a plausible shape for a 30B-class model and must be replaced with the values from <span class="mono">ollama show</span> before these numbers are trusted; the <em>method</em> is what this table demonstrates.</caption>
        <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Source</th></tr></thead>
        <tbody>
          <tr><td>\(V_{\text{tot}}\)</td><td class="mono">24 GB</td><td>Hardware</td></tr>
          <tr><td>\(S_{w}\)</td><td class="mono">19 GB</td><td>Published tag size<a class="cite" href="references.html#r11">[11]</a></td></tr>
          <tr><td>\(V_{\text{rt}}\)</td><td class="mono">1.2 GB</td><td><span class="badge medium">estimate</span> Planning figure; measure it</td></tr>
          <tr><td>Remainder for cache</td><td class="mono">3.8 GiB = 4.080&times;10<sup>9</sup> B</td><td>Derived: \(24 - 19 - 1.2\)</td></tr>
          <tr><td>Per-token cache cost at \(n_{\ell}=48,\ n_{kv}=8,\ d_{h}=128,\ b_{kv}=2\)</td><td class="mono">196 608 B</td><td>Derived: \(2 \times 48 \times 8 \times 128 \times 2\)</td></tr>
          <tr><td>\(L_{\max}\)</td><td class="mono">&asymp; 20 750 token</td><td>Derived: \(4.080\times10^{9} / 196\,608\)</td></tr>
          <tr><td>\(L_{\max}\) with <span class="mono">OLLAMA_KV_CACHE_TYPE=q8_0</span></td><td class="mono">&asymp; 41 500 token</td><td>Derived: \(b_{kv}\) halves to 1 B<a class="cite" href="references.html#r9">[9]</a></td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong>The 256K window on the model page is not available on this card.</strong> The page states 256K native<a class="cite" href="references.html#r11">[11]</a>; the arithmetic above gives roughly 21&nbsp;k tokens, or 41&nbsp;k with an 8-bit cache. The published figure describes what the weights were trained to attend over. The computed figure describes what the hardware can allocate. Both are correct and only the second one constrains your work.</p>
    </div>

    <h3>3.2 The mixture-of-experts case</h3>

    <p><span class="mono">qwen3-coder-next</span> publishes 80B total with 3B active per token<a class="cite" href="references.html#r33">[33]</a>, and its <span class="mono">q4_K_M</span> tag is 52&nbsp;GB. Substituting the active count into the footprint relation gives the bytes read per token:</p>

    <div class="table-wrap">
      <table>
        <caption>Capacity and streaming cost for a routed mixture-of-experts model, showing why the two numbers must be tracked separately. Derived from the published parameter split and the footprint relation.</caption>
        <thead><tr><th scope="col">Quantity</th><th scope="col">Value</th><th scope="col">Governs</th></tr></thead>
        <tbody>
          <tr><td>Total parameters \(P\)</td><td class="mono">80 &times; 10<sup>9</sup></td><td>&mdash;</td></tr>
          <tr><td>Weight footprint \(S_{w}\)</td><td class="mono">52 GB (published)<a class="cite" href="references.html#r33">[33]</a></td><td><strong>Capacity.</strong> Needs 52 GB plus cache plus runtime</td></tr>
          <tr><td>Active parameters \(P_{\text{act}}\)</td><td class="mono">3 &times; 10<sup>9</sup></td><td>&mdash;</td></tr>
          <tr><td>Active bytes per token \(S_{\text{act}}\)</td><td class="mono">&asymp; 1.95 GB</td><td><strong>Speed.</strong> Derived: \((3\times10^{9})(4.8)/8 \times 1.04\)</td></tr>
        </tbody>
      </table>
    </div>

    <p>So this model needs the capacity of a 52&nbsp;GB model and streams like a 2&nbsp;GB one. On a machine with enough aggregate memory it is a strong candidate; on a single 24&nbsp;GB card it does not load at all. That asymmetry is exactly what the distributed setup in &sect;6 exists to exploit.</p>
  </div>
</section>

<section id="speed">
  <div class="container">
    <h2>4. Will it be fast enough?</h2>

    """ + eq_library.get("bandwidth-bound") + r"""

    """ + eq_library.get("ngl-layers") + r"""

    <div class="callout info-box">
      <p><strong>The cliff is the thing to avoid.</strong> The derivation above shows the same 19&nbsp;GB weight set running about nine times slower from system RAM than from VRAM. Every other decision on this page &mdash; quantisation, cache type, context length, how many layers to offload &mdash; is in service of staying on the fast side of that cliff. A smaller model fully resident beats a larger model that spills, essentially always.</p>
    </div>
  </div>
</section>

<section id="recommend">
  <div class="container">
    <h2>5. Recommendations by VRAM budget</h2>

    <p>These are judgements, not measurements. The reasoning is given for each so it can be disagreed with.</p>

    <div class="table-wrap">
      <table>
        <caption>Suggested model per VRAM budget for local code generation and testing, with the reasoning. Sizes are the published tag sizes; headroom is what remains for the key/value cache and the runtime after the weights.</caption>
        <thead><tr><th scope="col">VRAM</th><th scope="col">First choice</th><th scope="col">Size</th><th scope="col">Headroom</th><th scope="col">Reasoning</th></tr></thead>
        <tbody>
          <tr>
            <td><strong>8 GB</strong></td>
            <td><span class="mono">nemotron-3-nano:4b</span></td>
            <td class="mono">2.8&ndash;2.9 GB<a class="cite" href="references.html#r34">[34]</a></td>
            <td class="mono">&asymp; 4 GB</td>
            <td>The only shortlisted model that leaves real cache headroom at this budget, and it carries both tools and thinking. Its page positions it explicitly as an agentic model rather than a shrunken chat model</td>
          </tr>
          <tr>
            <td><strong>12 GB</strong></td>
            <td><span class="mono">qwen2.5-coder:7b</span></td>
            <td class="mono">4.7 GB<a class="cite" href="references.html#r12">[12]</a></td>
            <td class="mono">&asymp; 6 GB</td>
            <td>Generous cache headroom, which matters more than parameter count at this budget. The 32K ceiling on every <span class="mono">qwen2.5-coder</span> tag is the real limit, and 32K is workable for single-file edits</td>
          </tr>
          <tr>
            <td><strong>16 GB</strong></td>
            <td><span class="mono">gpt-oss:20b</span></td>
            <td class="mono">14 GB<a class="cite" href="references.html#r16">[16]</a></td>
            <td class="mono">tight</td>
            <td>Its page states MXFP4 at 4.25 bit per parameter lets it run "on systems with as little as 16GB memory", so this is the vendor's own stated floor. 128K context and Apache 2.0. Budget an 8-bit cache to buy back headroom</td>
          </tr>
          <tr>
            <td><strong>24 GB</strong></td>
            <td><span class="mono">devstral-small-2:24b</span></td>
            <td class="mono">15 GB<a class="cite" href="references.html#r13">[13]</a></td>
            <td class="mono">&asymp; 8 GB</td>
            <td><strong>The best fit in the set.</strong> It is the only shortlisted model whose page publishes agentic software-engineering scores, its description is specifically about exploring codebases and editing multiple files, the 384K window is the largest on the shortlist, it is Apache 2.0, and at 15 GB it leaves roughly 8 GB for cache. Needs Ollama 0.13.3 or later</td>
          </tr>
          <tr>
            <td><strong>24 GB, alternative</strong></td>
            <td><span class="mono">laguna-xs-2.1:q4_K_M</span></td>
            <td class="mono">20 GB<a class="cite" href="references.html#r15">[15]</a></td>
            <td class="mono">tight</td>
            <td>Positioned for "agentic coding and long-horizon work on a local machine", and the only shortlisted model publishing a full quantisation ladder, so the quality-versus-size trade can be walked rather than guessed. At 20 GB on a 24 GB card an 8-bit cache is effectively mandatory</td>
          </tr>
          <tr>
            <td><strong>32 GB</strong></td>
            <td><span class="mono">qwen3-coder:30b</span> or <span class="mono">qwen3.6:35b</span></td>
            <td class="mono">19 GB / 23&ndash;24 GB<a class="cite" href="references.html#r11">[11]</a><a class="cite" href="references.html#r14">[14]</a></td>
            <td class="mono">&asymp; 12 GB / 7 GB</td>
            <td>Pick <span class="mono">qwen3-coder</span> for code-only work and the headroom. Pick <span class="mono">qwen3.6</span> when the vision capability earns its keep &mdash; reading a schematic, a plot or a GUI screenshot &mdash; which for RF and instrumentation work it often does</td>
          </tr>
          <tr>
            <td><strong>48 GB+ or pooled</strong></td>
            <td><span class="mono">qwen3-coder-next:q4_K_M</span></td>
            <td class="mono">52 GB<a class="cite" href="references.html#r33">[33]</a></td>
            <td>&mdash;</td>
            <td>80B total but only 3B active per token, so once it fits it streams like a small model. The best capacity-for-speed trade on the shortlist, and the natural target for the pooled configuration in &sect;6. Non-thinking mode only</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3>5.1 Two models, not one</h3>

    <p>Nothing requires a single choice. The loop equation on the <a href="local-code-build-test.html#eq-agent-loop">build page</a> shows that generation dominates fast Python iterations while the compiler dominates C++ ones, so a sensible local setup keeps two models loaded and routes by task.</p>

    <div class="table-wrap">
      <table>
        <caption>A two-model arrangement, with the Ollama setting that makes it work. Both models stay resident so there is no reload penalty on switching.</caption>
        <thead><tr><th scope="col">Role</th><th scope="col">Model</th><th scope="col">Used for</th></tr></thead>
        <tbody>
          <tr><td>Fast path</td><td><span class="mono">qwen2.5-coder:7b</span> or <span class="mono">nemotron-3-nano:4b</span></td><td>Single-file edits, test stubs, docstrings, quick refactors. Decode speed is what matters</td></tr>
          <tr><td>Deep path</td><td><span class="mono">devstral-small-2:24b</span></td><td>Multi-file changes, build failures, anything where converging in fewer iterations is worth waiting for</td></tr>
        </tbody>
      </table>
    </div>

    <p>Keeping both resident needs <span class="mono">OLLAMA_MAX_LOADED_MODELS</span>, documented with a default of "3 * the number of GPUs or 3 for CPU inference"<a class="cite" href="references.html#r9">[9]</a>, so the default already permits two. The binding constraint is VRAM: the two footprints and both caches must fit simultaneously, or Ollama will evict one and reload it on every switch. <span class="mono">OLLAMA_KEEP_ALIVE</span>, with a documented default of five minutes<a class="cite" href="references.html#r9">[9]</a>, controls how long an idle model stays loaded.</p>
  </div>
</section>

<section id="distributed">
  <div class="container">
    <h2>6. When the model does not fit on one machine</h2>

    <p>llama.cpp's RPC backend splits the layer stack across machines<a class="cite" href="references.html#r17">[17]</a>, which is how this deployment runs models larger than any single card. The <a href="llama-rpc-vulkan-guide.html">RPC and Vulkan guide</a> covers the mechanics; the arithmetic below decides whether a given split is worth doing.</p>

    <div class="callout danger">
      <p><strong>Read the upstream warning before exposing a worker.</strong> The RPC README marks the backend as a proof of concept and states plainly: &ldquo;the functionality is fragile and insecure. <strong>Never run the RPC server on an open network or in a sensitive environment!</strong>&rdquo;<a class="cite" href="references.html#r37">[37]</a> There is no authentication on the worker port. The firewall rules this deployment uses admit only the inference host by address, which is the minimum that makes this safe, and the workers should not be reachable from anywhere else on the network.</p>
    </div>

    <div class="callout info-box">
      <p><strong>The worker binary has been renamed.</strong> It is now <span class="mono">ggml-rpc-server</span>, not <span class="mono">rpc-server</span><a class="cite" href="references.html#r37">[37]</a>, and started with no arguments it exposes every accelerator it finds. Restrict that with <span class="mono">--device CUDA0</span> or <span class="mono">CUDA_VISIBLE_DEVICES</span>, which the README gives as equivalent:</p>
<pre><code>$ CUDA_VISIBLE_DEVICES=0 bin/ggml-rpc-server -p 50052
$ bin/ggml-rpc-server --device CUDA0 -p 50052</code></pre>
      <p>Two further options are worth knowing. <span class="mono">-c</span> enables a local tensor cache, which avoids re-transferring large tensors over the network and speeds model loading noticeably; it lives under <span class="mono">$HOME/.cache/llama.cpp/rpc</span> and follows <span class="mono">LLAMA_CACHE</span>. <span class="mono">GGML_RPC_DEBUG</span> raises log verbosity on either end when a split misbehaves<a class="cite" href="references.html#r37">[37]</a>.</p>
    </div>

    <div class="callout">
      <p><strong>The default split is proportional, not manual.</strong> llama.cpp distributes model weights <em>and the key/value cache</em> across every available device, local and remote, in proportion to each device's free memory, and <span class="mono">--tensor-split</span> overrides those proportions<a class="cite" href="references.html#r37">[37]</a>. This matters for the relations below: the per-node weight term \( S_{i} \) is something the runtime chooses for you unless you set it, and the cache is split too rather than sitting entirely on the host.</p>
    </div>

    """ + eq_library.get("rpc-token-time") + r"""

    """ + eq_library.get("rpc-breakeven") + r"""

    <div class="callout info-box">
      <p><strong>The rule the break-even condition reduces to.</strong> Distribute to escape a spill, never to add bandwidth. Moving weights that were spilling to host RAM onto a worker GPU is a large win; moving weights that already sat in host VRAM is a small loss plus a new failure domain. Check which case you are in before switching a worker on.</p>
    </div>
  </div>
</section>

<section id="measure">
  <div class="container">
    <h2>7. Measure it yourself</h2>

    <p>Every rate on this page is computed from a bandwidth figure, and a computed rate is a prediction. The script shipped with this page set, <span class="mono">scripts/probe_model_throughput.py</span>, measures the real thing through the Ollama API and prints the measured rates alongside what the relations predict.</p>

<pre><code># Measure the shortlisted models against the relations on this page.
# --repeat 3 is the minimum worth reporting: the first call pays the model
# load, so it is discarded as a warm-up.
micromamba run -n Py3p12 python scripts/probe_model_throughput.py `
  --host http://192.168.7.27:11434 `
  --models devstral-small-2:24b qwen2.5-coder:7b `
  --repeat 3 `
  --out results/throughput.json</code></pre>

    <div class="table-wrap">
      <table>
        <caption>What to read off a model before trusting any figure on this page, and the command that produces it.</caption>
        <thead><tr><th scope="col">Quantity</th><th scope="col">Command</th><th scope="col">Feeds</th></tr></thead>
        <tbody>
          <tr><td>Quantisation, layer count, head counts, head dimension</td><td class="mono">ollama show &lt;tag&gt;</td><td>\(b_{q}\), \(n_{\ell}\), \(n_{kv}\), \(d_{h}\) in every relation on this page</td></tr>
          <tr><td>Decode and prefill rate</td><td class="mono">scripts/probe_model_throughput.py</td><td>\(r\) and \(r_{p}\) in the loop equation</td></tr>
          <tr><td>Resident footprint, the processor split, and the context actually allocated</td><td class="mono">ollama ps</td><td>Confirms \(S_{w}\), reveals a CPU/GPU split, and reports \(L_{\text{ctx}}\) in its <span class="mono">CONTEXT</span> column<a class="cite" href="references.html#r35">[35]</a></td></tr>
          <tr><td>Device memory in use</td><td class="mono">nvidia-smi</td><td>\(V_{\text{rt}}\) by subtraction</td></tr>
        </tbody>
      </table>
    </div>

    <div class="callout">
      <p><strong><span class="mono">ollama ps</span> is the check that catches the expensive mistake.</strong> It reports whether a model is resident on the GPU or split with the CPU, and &mdash; in its <span class="mono">CONTEXT</span> column &mdash; the context length actually allocated<a class="cite" href="references.html#r35">[35]</a>. A quiet CPU/GPU split is exactly the ninefold slowdown in &sect;4; a <span class="mono">CONTEXT</span> value below what you asked for means the server trimmed the window to make the model fit. Both are invisible unless you look, and both are in this one output:</p>
<pre><code>NAME             ID              SIZE      PROCESSOR    CONTEXT    UNTIL
gemma4:latest    c6eb396dbd59    9.6 GB    100% GPU     131072     2 minutes from now</code></pre>
    </div>
  </div>
</section>

<section id="caveats">
  <div class="container">
    <h2>8. What this page does not tell you</h2>

    <div class="table-wrap">
      <table>
        <caption>Deliberate omissions, with the reason each figure is absent and what to do instead.</caption>
        <thead><tr><th scope="col">Not stated here</th><th scope="col">Why</th><th scope="col">Instead</th></tr></thead>
        <tbody>
          <tr>
            <td>Tokens per second for named hardware</td>
            <td>It depends on the card, the driver, the quantisation, the context, the batch and the build. A published number would be wrong for most readers</td>
            <td>Compute a bound with the relation in &sect;4, then measure with &sect;7</td>
          </tr>
          <tr>
            <td>A quality ranking across the shortlist</td>
            <td>Scores from different authors under different harnesses are not comparable. Only <span class="mono">devstral-small-2</span> publishes figures at all<a class="cite" href="references.html#r13">[13]</a></td>
            <td>Run your own tasks. Count iterations to convergence, which is the term that dominates the loop equation</td>
          </tr>
          <tr>
            <td>Quantisation level for most tags</td>
            <td><span class="mono">qwen3-coder</span>, <span class="mono">devstral-small-2</span>, <span class="mono">qwen3.6</span> and <span class="mono">nemotron-3-nano</span> state no per-tag quantisation; <span class="mono">laguna-xs-2.1</span>, <span class="mono">qwen3-coder-next</span> and <span class="mono">gpt-oss</span> do</td>
            <td><span class="mono">ollama show &lt;tag&gt;</span></td>
          </tr>
          <tr>
            <td>Which model is "best"</td>
            <td>It is task-dependent and the library changes monthly. The library index listed 256 models when this page was written<a class="cite" href="references.html#r10">[10]</a></td>
            <td>Apply the criteria in &sect;1 to the current library, and re-run the fit arithmetic in &sect;3</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="callout danger">
      <p><strong>This page has a shelf life.</strong> Model pages are revised in place: a tag's size changes when it is requantised, and tags are added and withdrawn. Every figure here was read on 2026-10-18 and is cited to the page it came from. Treat the <em>method</em> &mdash; the criteria in &sect;1 and the relations in &sect;3 and &sect;4 &mdash; as the durable part, and re-read the tag pages before committing hardware.</p>
    </div>
  </div>
</section>
"""
