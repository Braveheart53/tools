#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probe_model_throughput.py -- measure local model throughput against the
equations published on ollama-model-selection.html.

Author  : William W. Wallace
Version : 0.0.1
Created : 2026-10-18

WHY THIS EXISTS
---------------
Every rate quoted on ``ollama-model-selection.html`` is COMPUTED, from the
memory-bandwidth ceiling

    r_max = B_eff / S_act          and      r_obs ~= eta * r_max

A computed rate is a prediction.  This script measures the real prefill and
decode rates through the Ollama API, prints them beside the prediction, and
solves for the realisation factor ``eta`` so that the page's 0.5-0.8 planning
estimate can be replaced with a number measured on your own hardware.

It also reports the key/value cache footprint implied by the context length in
use, so the context-budget relation on the same page can be checked rather
than trusted.

WHAT IT MEASURES
----------------
Ollama's ``/api/generate`` response carries nanosecond timings, which is what
makes a trustworthy measurement possible without instrumenting the server:

    prompt_eval_count / prompt_eval_duration   -> prefill rate  r_p
    eval_count        / eval_duration          -> decode rate   r
    load_duration                              -> model load, excluded

The first call to a cold model pays the load cost, so run 1 of every repeat
set is discarded as a warm-up and is reported separately.

MEMORY BEHAVIOUR
----------------
The project convention is to be explicit about memory, and this script is
deliberately frugal:

* Responses are requested with ``"stream": false`` and only the small JSON
  summary is retained; generated text is discarded after its length is
  recorded, so a long generation does not accumulate in memory.
* Per-run records are plain dicts of scalars.  A full sweep of ten models at
  five repeats holds well under a megabyte.
* ``--out`` streams the result to JSON once at the end rather than keeping a
  growing serialised copy alongside the live data.

Nothing here needs a GPU, parallelism or a plotting library: it is a timing
harness, and adding threads would corrupt the measurement it exists to make.

PARALLELISM NOTE
----------------
Runs are deliberately SEQUENTIAL.  Issuing concurrent requests would measure
the server's batching behaviour rather than single-stream decode rate, which
is the quantity the page's equations predict.  Use ``--parallel-probe`` to
additionally measure the batched case, which starts the requested number of
generations at once and reports aggregate throughput.

USAGE
-----
    python probe_model_throughput.py --host http://192.168.7.27:11434 \
        --models devstral-small-2:24b qwen2.5-coder:7b \
        --repeat 3 --out results/throughput.json
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Nanoseconds per second.  Ollama reports every duration in nanoseconds.
NS_PER_S: float = 1.0e9

# Bytes per gibibyte, used only for display.
BYTES_PER_GIB: float = 1024.0 ** 3


# %% Prompt bank -------------------------------------------------------------
# Two prompts, chosen to separate the two rates the equations care about.
#
# The prefill prompt is long and asks for a one-word answer, so almost all of
# its time is prompt evaluation.  The decode prompt is short and asks for a
# long answer, so almost all of its time is generation.  Measuring both with
# one prompt gives a blended rate that matches neither term of the equation.
PROMPTS: Dict[str, Dict[str, Any]] = {
    "prefill": {
        "description": "Long prompt, one-word answer: isolates prompt evaluation.",
        # Repeated filler produces a large, cheap token count. The content is
        # irrelevant to the timing; only its length matters.
        "prompt": (
            "Below is a configuration fragment. Read all of it.\n\n"
            + ("# scrape_configs entry\n"
               "- job_name: 'windows'\n"
               "  scrape_interval: 15s\n"
               "  static_configs:\n"
               "    - targets: ['192.168.7.28:9182']\n") * 120
            + "\nReply with exactly one word: OK"
        ),
        "num_predict": 4,
    },
    "decode": {
        "description": "Short prompt, long answer: isolates token generation.",
        "prompt": (
            "Write a Python function that computes the key/value cache size in "
            "bytes for a transformer, given the layer count, key/value head "
            "count, head dimension, context length, sequence count and bytes "
            "per cached element. Include a full docstring and inline comments."
        ),
        "num_predict": 512,
    },
}


# %% Data model --------------------------------------------------------------
@dataclass
class RunResult:
    """Timings from one generation request.

    All rates are tokens per second.  ``None`` marks a figure the server did
    not report, which happens when a request is served from the prompt cache
    and so performs no prompt evaluation.
    """

    model: str
    prompt_kind: str
    run_index: int
    warmup: bool

    prompt_tokens: Optional[int] = None
    eval_tokens: Optional[int] = None

    prefill_rate: Optional[float] = None
    decode_rate: Optional[float] = None

    load_s: Optional[float] = None
    total_s: Optional[float] = None
    wall_s: Optional[float] = None

    response_chars: int = 0
    error: Optional[str] = None


@dataclass
class ModelSummary:
    """Aggregated result for one model across its non-warm-up runs."""

    model: str
    size_bytes: Optional[int] = None
    quantisation: Optional[str] = None
    context_length: Optional[int] = None

    prefill_median: Optional[float] = None
    decode_median: Optional[float] = None
    decode_stdev: Optional[float] = None

    # Bandwidth-ceiling check, populated only when --bandwidth is given.
    r_max: Optional[float] = None
    eta: Optional[float] = None

    runs: List[RunResult] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


# %% HTTP helpers ------------------------------------------------------------
def post_json(url: str, payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    """POST a JSON body and return the decoded JSON response.

    Uses ``urllib`` rather than ``requests`` so the script has no third-party
    dependency and will run in a bare environment, which matters when it is
    the first thing run on a freshly configured node.

    Parameters
    ----------
    url
        Absolute URL to POST to.
    payload
        JSON-serialisable request body.
    timeout
        Socket timeout in seconds.

    Returns
    -------
    dict
        The decoded response.

    Raises
    ------
    urllib.error.URLError
        On a transport failure.
    json.JSONDecodeError
        If the response is not JSON.
    """
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url: str, timeout: float) -> Dict[str, Any]:
    """GET a URL and return the decoded JSON response."""
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def safe_rate(count: Optional[int], duration_ns: Optional[int]) -> Optional[float]:
    """Return ``count / duration`` in tokens per second, or None.

    Guards the two cases Ollama actually produces: a missing field, and a
    zero duration for a request served entirely from cache.
    """
    if not count or not duration_ns:
        return None
    return float(count) / (float(duration_ns) / NS_PER_S)


# %% Measurement -------------------------------------------------------------
def probe_once(host: str, model: str, prompt_kind: str, run_index: int,
               warmup: bool, timeout: float,
               context_length: Optional[int]) -> RunResult:
    """Issue one generation request and extract its timings.

    Parameters
    ----------
    host
        Ollama base URL, for example ``http://192.168.7.27:11434``.
    model
        Model tag, for example ``devstral-small-2:24b``.
    prompt_kind
        Key into :data:`PROMPTS`.
    run_index
        1-based index within this model's repeat set, for the report.
    warmup
        True to mark the result as a discarded warm-up run.
    timeout
        Socket timeout in seconds.
    context_length
        Optional explicit ``num_ctx``.  Left unset, the server's own default
        applies, which Ollama documents as 4096 tokens unless
        ``OLLAMA_CONTEXT_LENGTH`` overrides it.

    Returns
    -------
    RunResult
        Populated on success; carrying ``error`` on failure.
    """
    spec = PROMPTS[prompt_kind]

    options: Dict[str, Any] = {
        "num_predict": spec["num_predict"],
        # Greedy decoding: sampling temperature does not change throughput,
        # but fixing it removes one source of run-to-run variation in the
        # number of tokens actually produced.
        "temperature": 0.0,
    }
    if context_length:
        options["num_ctx"] = context_length

    payload = {
        "model": model,
        "prompt": spec["prompt"],
        # Non-streaming: the response carries the full timing block, and
        # there is no partial output to accumulate in memory.
        "stream": False,
        "options": options,
    }

    result = RunResult(model=model, prompt_kind=prompt_kind,
                       run_index=run_index, warmup=warmup)

    started = time.perf_counter()
    try:
        data = post_json(f"{host.rstrip('/')}/api/generate", payload, timeout)
    except urllib.error.HTTPError as exc:
        result.error = f"HTTP {exc.code}: {exc.reason}"
        return result
    except urllib.error.URLError as exc:
        result.error = f"transport: {exc.reason}"
        return result
    except json.JSONDecodeError as exc:
        result.error = f"bad JSON: {exc}"
        return result
    except OSError as exc:                      # socket timeout lands here
        result.error = f"socket: {exc}"
        return result
    finally:
        result.wall_s = time.perf_counter() - started

    # Discard the generated text immediately; only its length is kept, so a
    # 512-token response does not sit in memory for the rest of the sweep.
    result.response_chars = len(data.get("response", "") or "")
    data.pop("response", None)
    data.pop("context", None)           # the token context can be large

    result.prompt_tokens = data.get("prompt_eval_count")
    result.eval_tokens = data.get("eval_count")
    result.prefill_rate = safe_rate(result.prompt_tokens,
                                    data.get("prompt_eval_duration"))
    result.decode_rate = safe_rate(result.eval_tokens, data.get("eval_duration"))

    if data.get("load_duration"):
        result.load_s = data["load_duration"] / NS_PER_S
    if data.get("total_duration"):
        result.total_s = data["total_duration"] / NS_PER_S

    return result


def probe_parallel(host: str, model: str, concurrency: int,
                   timeout: float) -> Dict[str, Any]:
    """Measure aggregate throughput with several generations in flight.

    Single-stream decode rate is what the page's equations predict, so the
    sequential measurement is the primary one.  This additional probe answers
    a different question: whether continuous batching is recovering any
    throughput when several requests overlap, which is what
    ``--parallel``/``OLLAMA_NUM_PARALLEL`` exists to do.

    Threads are appropriate here despite the GIL because every worker is
    blocked on a socket, not computing.

    Parameters
    ----------
    host, model, timeout
        As for :func:`probe_once`.
    concurrency
        Number of simultaneous generations.

    Returns
    -------
    dict
        Aggregate tokens, wall time and tokens per second across all workers.
    """
    def one(index: int) -> RunResult:
        return probe_once(host, model, "decode", index, warmup=False,
                          timeout=timeout, context_length=None)

    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = list(pool.map(one, range(1, concurrency + 1)))
    elapsed = time.perf_counter() - started

    total_tokens = sum(r.eval_tokens or 0 for r in results)
    failures = [r.error for r in results if r.error]

    return {
        "concurrency": concurrency,
        "wall_s": elapsed,
        "total_eval_tokens": total_tokens,
        "aggregate_tokens_per_s": (total_tokens / elapsed) if elapsed else None,
        "per_stream_tokens_per_s": (total_tokens / elapsed / concurrency)
                                   if elapsed and concurrency else None,
        "failures": failures,
    }


def model_metadata(host: str, model: str, timeout: float) -> Dict[str, Any]:
    """Fetch what the server knows about a model.

    The architecture fields returned here are exactly the inputs the
    key/value cache and context-budget relations need, and reading them from
    the server is the alternative to the placeholder values the page warns
    about.
    """
    out: Dict[str, Any] = {}
    try:
        data = post_json(f"{host.rstrip('/')}/api/show", {"model": model}, timeout)
    except Exception as exc:                     # noqa: BLE001 - reported, not raised
        out["error"] = f"{type(exc).__name__}: {exc}"
        return out

    details = data.get("details") or {}
    out["quantisation"] = details.get("quantization_level")
    out["parameter_size"] = details.get("parameter_size")
    out["family"] = details.get("family")

    # model_info keys are namespaced by architecture, e.g.
    # "qwen3.block_count", so they are matched by suffix.
    info = data.get("model_info") or {}
    wanted = {
        "block_count": "n_layers",
        "attention.head_count": "n_heads",
        "attention.head_count_kv": "n_kv_heads",
        "attention.key_length": "head_dim",
        "context_length": "context_length",
        "embedding_length": "embedding_length",
    }
    for key, value in info.items():
        for suffix, name in wanted.items():
            if key.endswith(suffix):
                out[name] = value

    return out


def kv_cache_bytes(n_layers: int, n_kv_heads: int, head_dim: int,
                   context: int, sequences: int, bytes_per_elem: float) -> float:
    """Return the key/value cache footprint in bytes.

    Implements the relation published on ``ollama-model-selection.html``:

        S_kv = 2 * n_layers * n_kv_heads * head_dim * L_ctx * n_seq * b_kv

    The leading 2 is one key vector plus one value vector per cached token.
    """
    return (2.0 * n_layers * n_kv_heads * head_dim
            * context * sequences * bytes_per_elem)


# %% Orchestration -----------------------------------------------------------
def run_sweep(host: str, models: Sequence[str], repeat: int, timeout: float,
              context_length: Optional[int],
              bandwidth_gb_s: Optional[float],
              parallel_probe: int) -> List[ModelSummary]:
    """Measure every model in turn and return one summary each."""
    summaries: List[ModelSummary] = []

    for model in models:
        print(f"\n{'=' * 74}\n{model}\n{'=' * 74}")
        summary = ModelSummary(model=model)

        meta = model_metadata(host, model, timeout)
        if "error" in meta:
            summary.notes.append(f"metadata unavailable: {meta['error']}")
        else:
            summary.quantisation = meta.get("quantisation")
            summary.context_length = meta.get("context_length")
            print(f"  quantisation     : {meta.get('quantisation', '?')}")
            print(f"  parameter size   : {meta.get('parameter_size', '?')}")
            print(f"  layers           : {meta.get('n_layers', '?')}")
            print(f"  kv heads         : {meta.get('n_kv_heads', '?')}")
            print(f"  head dim         : {meta.get('head_dim', '?')}")
            print(f"  trained context  : {meta.get('context_length', '?')}")

        # ---- sequential runs: the measurement the equations predict ------
        for kind in ("prefill", "decode"):
            print(f"\n  {kind}: {PROMPTS[kind]['description']}")
            for index in range(1, repeat + 1):
                # Run 1 of the first prompt kind pays the model load, so it
                # is always treated as a warm-up.
                warmup = (index == 1)
                result = probe_once(host, model, kind, index, warmup,
                                    timeout, context_length)
                summary.runs.append(result)

                if result.error:
                    print(f"    run {index}: FAILED - {result.error}")
                    continue

                tag = " (warm-up, discarded)" if warmup else ""
                rate = (result.prefill_rate if kind == "prefill"
                        else result.decode_rate)
                shown = f"{rate:8.2f} tok/s" if rate else "     n/a     "
                tokens = (result.prompt_tokens if kind == "prefill"
                          else result.eval_tokens)
                load = f", load {result.load_s:.2f} s" if result.load_s else ""
                print(f"    run {index}: {shown}  "
                      f"({tokens or 0} tokens, wall {result.wall_s:.2f} s{load}){tag}")

        # ---- aggregate the non-warm-up runs -----------------------------
        prefill = [r.prefill_rate for r in summary.runs
                   if r.prompt_kind == "prefill" and not r.warmup
                   and r.prefill_rate]
        decode = [r.decode_rate for r in summary.runs
                  if r.prompt_kind == "decode" and not r.warmup
                  and r.decode_rate]

        if prefill:
            summary.prefill_median = statistics.median(prefill)
        if decode:
            summary.decode_median = statistics.median(decode)
            if len(decode) > 1:
                summary.decode_stdev = statistics.stdev(decode)

        # ---- optional: check against the bandwidth ceiling --------------
        if bandwidth_gb_s and summary.decode_median:
            try:
                listed = get_json(f"{host.rstrip('/')}/api/tags", timeout)
                for entry in listed.get("models", []):
                    if entry.get("name") == model or entry.get("model") == model:
                        summary.size_bytes = entry.get("size")
                        break
            except Exception as exc:             # noqa: BLE001
                summary.notes.append(f"size lookup failed: {type(exc).__name__}")

            if summary.size_bytes:
                # r_max = B_eff / S_act, with S_act taken as the whole weight
                # file. For a routed mixture of experts this OVERSTATES the
                # bytes read per token and so understates r_max; the page's
                # moe-active relation gives the correction.
                b_eff = bandwidth_gb_s * 1.0e9        # GB/s as decimal GB
                summary.r_max = b_eff / summary.size_bytes
                summary.eta = summary.decode_median / summary.r_max

        # ---- optional: batched throughput -------------------------------
        if parallel_probe > 1:
            print(f"\n  batched probe, {parallel_probe} concurrent generations")
            batched = probe_parallel(host, model, parallel_probe, timeout)
            summary.notes.append(f"batched: {json.dumps(batched)}")
            agg = batched["aggregate_tokens_per_s"]
            per = batched["per_stream_tokens_per_s"]
            if agg:
                print(f"    aggregate   : {agg:8.2f} tok/s")
                print(f"    per stream  : {per:8.2f} tok/s")
                if summary.decode_median:
                    gain = agg / summary.decode_median
                    print(f"    vs single   : {gain:8.2f}x "
                          f"(1.0 means batching bought nothing)")
            for failure in batched["failures"]:
                print(f"    FAILED: {failure}")

        summaries.append(summary)

    return summaries


def print_report(summaries: Sequence[ModelSummary],
                 bandwidth_gb_s: Optional[float]) -> None:
    """Print the comparison table and the equation check."""
    print(f"\n{'=' * 74}\nSUMMARY\n{'=' * 74}")
    header = f"{'model':30s} {'prefill':>12s} {'decode':>12s} {'stdev':>9s}"
    print(header)
    print("-" * 74)
    for s in summaries:
        pf = f"{s.prefill_median:.1f}" if s.prefill_median else "n/a"
        dc = f"{s.decode_median:.2f}" if s.decode_median else "n/a"
        sd = f"{s.decode_stdev:.2f}" if s.decode_stdev else "-"
        print(f"{s.model[:30]:30s} {pf:>12s} {dc:>12s} {sd:>9s}")
    print("-" * 74)
    print("rates in tokens per second; median of the non-warm-up runs")

    if bandwidth_gb_s:
        print(f"\n{'=' * 74}")
        print("BANDWIDTH-CEILING CHECK   r_max = B_eff / S_act,  eta = r_obs / r_max")
        print(f"B_eff supplied: {bandwidth_gb_s:.1f} GB/s")
        print("=" * 74)
        print(f"{'model':30s} {'S_act':>10s} {'r_max':>10s} {'r_obs':>10s} {'eta':>8s}")
        print("-" * 74)
        for s in summaries:
            if not (s.r_max and s.decode_median):
                continue
            size = f"{s.size_bytes / BYTES_PER_GIB:.1f} GiB" if s.size_bytes else "?"
            print(f"{s.model[:30]:30s} {size:>10s} "
                  f"{s.r_max:10.2f} {s.decode_median:10.2f} {s.eta:8.3f}")
        print("-" * 74)
        print("eta is the realisation factor the model-selection page estimates")
        print("at 0.5-0.8. A measured eta replaces that estimate for YOUR hardware.")
        print("An eta well below 0.5 usually means weights spilled to system RAM:")
        print("check with 'ollama ps'.")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Parse arguments, run the sweep, print and optionally save the report."""
    parser = argparse.ArgumentParser(
        description="Measure Ollama model throughput against the equations "
                    "on ollama-model-selection.html.")
    parser.add_argument("--host", default="http://localhost:11434",
                        help="Ollama base URL (default: %(default)s)")
    parser.add_argument("--models", nargs="+", required=True,
                        help="model tags to probe, e.g. devstral-small-2:24b")
    parser.add_argument("--repeat", type=int, default=3,
                        help="runs per prompt kind; run 1 is a discarded "
                             "warm-up (default: %(default)s)")
    parser.add_argument("--timeout", type=float, default=600.0,
                        help="per-request socket timeout in seconds "
                             "(default: %(default)s)")
    parser.add_argument("--context-length", type=int, default=None,
                        help="explicit num_ctx; omit to use the server default, "
                             "which Ollama documents as 4096 tokens")
    parser.add_argument("--bandwidth", type=float, default=None,
                        metavar="GB_S",
                        help="achieved memory bandwidth in GB/s; supplying it "
                             "enables the r_max and eta check")
    parser.add_argument("--parallel-probe", type=int, default=0, metavar="N",
                        help="additionally measure aggregate throughput with N "
                             "concurrent generations (default: off)")
    parser.add_argument("--out", type=Path, default=None,
                        help="write the full result to this JSON file")
    args = parser.parse_args(argv)

    if args.repeat < 2:
        parser.error("--repeat must be at least 2: run 1 is a discarded warm-up")

    summaries = run_sweep(
        host=args.host,
        models=args.models,
        repeat=args.repeat,
        timeout=args.timeout,
        context_length=args.context_length,
        bandwidth_gb_s=args.bandwidth,
        parallel_probe=args.parallel_probe,
    )

    print_report(summaries, args.bandwidth)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        # Serialise once, at the end, rather than keeping a growing copy.
        payload = {
            "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "host": args.host,
            "context_length": args.context_length,
            "bandwidth_gb_s": args.bandwidth,
            "models": [asdict(s) for s in summaries],
        }
        args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")

    # Non-zero exit if nothing was measured, so this is usable in a check.
    measured = any(s.decode_median for s in summaries)
    if not measured:
        print("\nNo model produced a usable measurement.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
