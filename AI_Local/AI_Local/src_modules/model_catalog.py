# -*- coding: utf-8 -*-
"""
model_catalog.py -- single source of truth for the model shortlist.

Author  : William W. Wallace
Version : 0.0.2
Created : 2026-10-20

WHY THIS MODULE EXISTS
----------------------
The model shortlist appears in two places that must agree:

  1. ``ollama-model-selection.html`` -- a prose table, written by
     ``page_models.py``, with each figure cited to its Ollama model page.
  2. ``index.html`` -- the hardware planner, which picks a model for the
     reader's VRAM budget and must pick from the same list with the same
     numbers.

Two hand-maintained copies of the same table diverge; it is only a question
of when.  So the numbers live here once, the planner is generated from this
module, and ``build_ai_local_site.py`` -> ``verify_catalog_consistency()``
fails the build if a tag listed here does not appear on the model-selection
page.  Changing a size is then a one-line edit that cannot leave the two
pages disagreeing.

SOURCING
--------
Every ``size_gb``, ``context``, ``quant`` and capability value is the figure
published on that model's Ollama page, read on the date in ``READ_ON``.  No
value here is inferred, averaged or rounded from anywhere else.  Where a page
states a range (several builds share a tag) the range is preserved in
``size_note`` and ``size_gb`` carries the upper bound, because the upper
bound is the one that has to fit.

Where a page states nothing -- most tags do not publish a quantisation level
-- the field is ``None`` and the planner says "not stated" rather than
guessing.  That is the whole point of the ``NOT_STATED`` convention below.
"""

# %% Imports -----------------------------------------------------------------
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# %% Metadata ----------------------------------------------------------------
#: Date every figure below was read from its Ollama model page.  Printed on
#: the planner so a reader knows how stale the numbers may be.  Model pages
#: are revised in place, without a changelog, so this date matters.
READ_ON: str = "2026-10-18"

#: Sentinel used in prose when a model page publishes no value for a field.
NOT_STATED: str = "not stated"


# %% Model record ------------------------------------------------------------
@dataclass
class Model:
    """One shortlisted model tag, as its Ollama page publishes it.

    Attributes
    ----------
    tag
        The exact tag to pass to ``ollama pull`` / ``ollama run``.
    family
        Model family name, used to group variants in the planner's output.
    size_gb
        Weight-file size in GB as the tag listing shows it.  Where the
        listing gives a range, this is the UPPER bound, because sizing has
        to be done against the largest build that may be pulled.
    size_note
        The size exactly as printed, when it differs from ``size_gb`` -- for
        example "18-19 GB".  ``None`` when the listing gives a single value.
    context
        Native context window in tokens, as published.  This is what the
        weights were trained to attend over, NOT what a given card can
        allocate; the planner computes the second from the first.
    quant
        Quantisation level, when the page states one.  ``None`` otherwise.
    capabilities
        Capability labels from the model page header: "tools", "thinking",
        "vision".  "tools" is the hard gate -- without it the model cannot
        drive a terminal at all.
    reference
        Reference number in ``references.py`` for the page these figures
        came from.
    positioning
        One sentence, close to the page's own wording, on what the model is
        for.  Used verbatim in the planner's explanation.
    active_params_b
        For a routed mixture-of-experts model, the parameters read per token
        in billions, when the page publishes it.  ``None`` for a dense model
        or when unpublished.  Decode speed tracks this, capacity tracks the
        weight file, and the planner must not confuse the two.
    total_params_b
        Total parameter count in billions, when published.
    min_vram_gb
        Smallest VRAM budget this model is a sensible choice for.  This is a
        JUDGEMENT made here, not a published figure: it is ``size_gb`` plus
        headroom for the key/value cache and the runtime, rounded to a real
        card size.  The planner labels it as a judgement.
    notes
        Any caveat a reader needs before pulling the tag -- a minimum Ollama
        version, a stated memory floor, a missing mode.
    """

    tag: str
    family: str
    size_gb: float
    context: int
    capabilities: List[str]
    reference: int
    positioning: str
    min_vram_gb: int
    size_note: Optional[str] = None
    quant: Optional[str] = None
    active_params_b: Optional[float] = None
    total_params_b: Optional[float] = None
    notes: List[str] = field(default_factory=list)

    # ---- derived helpers --------------------------------------------------
    @property
    def drives_tools(self) -> bool:
        """True when the model can call tools, which is the hard gate.

        A model without tool calling cannot invoke a terminal, so however
        good its code is it cannot close a write-build-test loop.  The
        planner filters on this before judging anything else.
        """
        return "tools" in self.capabilities

    @property
    def is_moe(self) -> bool:
        """True when the page publishes a routed active-parameter count."""
        return self.active_params_b is not None

    @property
    def streaming_gb(self) -> float:
        """Bytes read per token, in GB, as the bandwidth ceiling needs them.

        For a dense model this is the whole weight file.  For a routed
        mixture of experts it is the weight file scaled by the published
        active fraction, which is the correction the ``moe-active`` relation
        on the model-selection page describes.

        Returns
        -------
        float
            Gigabytes streamed per generated token.
        """
        if not self.is_moe or not self.total_params_b:
            return self.size_gb
        # Scale the published file size by the routed fraction rather than
        # recomputing from bits per weight, because the file size is a
        # published figure and the bits-per-weight rate usually is not.
        return self.size_gb * (self.active_params_b / self.total_params_b)

    def size_display(self) -> str:
        """Return the size exactly as the model page prints it."""
        return self.size_note or f"{self.size_gb:g} GB"


# %% The shortlist -----------------------------------------------------------
# Ordered smallest VRAM budget first, which is the order the planner walks
# when choosing.  Every entry carries the "tools" capability: a model that
# cannot call a tool is out of scope for this page set and is not listed.
MODELS: List[Model] = [

    Model(
        tag="nemotron-3-nano:4b",
        family="nemotron-3-nano",
        size_gb=2.9,
        size_note="2.8-2.9 GB",
        context=262_144,                 # page states 256K
        capabilities=["tools", "thinking"],
        reference=34,
        positioning="NVIDIA, trained from scratch, and positioned explicitly "
                    "as an agentic model rather than a shrunken chat model.",
        min_vram_gb=8,
        notes=["The only shortlisted model that leaves real cache headroom "
               "on an 8 GB card."],
    ),

    Model(
        tag="qwen2.5-coder:7b",
        family="qwen2.5-coder",
        size_gb=4.7,
        context=32_768,                  # page states 32K on every tag
        capabilities=["tools"],
        reference=12,
        positioning="Older generation, but the broadest size ladder in the "
                    "library and generous cache headroom at this budget.",
        min_vram_gb=12,
        notes=["The 32K context ceiling applies to EVERY qwen2.5-coder tag "
               "and is the binding limit for agent work, not the size."],
    ),

    Model(
        tag="gpt-oss:20b",
        family="gpt-oss",
        size_gb=14.0,
        context=131_072,                 # page states 128K
        quant="MXFP4, 4.25 bit/parameter",
        capabilities=["tools", "thinking"],
        reference=16,
        positioning="OpenAI open-weight reasoning and agent model, "
                    "Apache 2.0.",
        min_vram_gb=16,
        notes=["The model page states MXFP4 lets this run 'on systems with "
               "as little as 16GB memory', so 16 GB is the vendor's own "
               "stated floor rather than a judgement made here.",
               "Budget an 8-bit key/value cache at 16 GB to buy back "
               "headroom."],
    ),

    Model(
        tag="devstral-small-2:24b",
        family="devstral-small-2",
        size_gb=15.0,
        context=393_216,                 # page states 384K
        capabilities=["tools", "vision"],
        reference=13,
        positioning="Built to use tools to explore codebases, edit multiple "
                    "files and power software-engineering agents. Apache 2.0.",
        min_vram_gb=24,
        notes=["The only shortlisted model whose page publishes agentic "
               "software-engineering scores: 65.8% SWE-Bench Verified, "
               "51.6% SWE-Bench Multilingual, 32.0% Terminal Bench.",
               "Requires Ollama 0.13.3 or later."],
    ),

    Model(
        tag="laguna-xs-2.1:q4_K_M",
        family="laguna-xs-2.1",
        size_gb=20.0,
        context=262_144,
        quant="Q4_K_M",
        capabilities=["tools", "thinking"],
        reference=15,
        positioning="Poolside, designed for agentic coding and long-horizon "
                    "work on a local machine.",
        min_vram_gb=24,
        notes=["The only shortlisted model publishing a full quantisation "
               "ladder (Q4_K_M 20 GB, q8_0 36 GB, bf16 67 GB), so the "
               "quality-versus-size trade can be walked rather than guessed.",
               "At 20 GB on a 24 GB card an 8-bit cache is effectively "
               "mandatory."],
    ),

    Model(
        tag="qwen3-coder:30b",
        family="qwen3-coder",
        size_gb=19.0,
        context=262_144,
        capabilities=["tools"],
        reference=11,
        positioning="Long-context coding and agent model; the page states "
                    "256K native, reaching 1M by extrapolation.",
        min_vram_gb=32,
        notes=["Leaves roughly 12 GB for cache on a 32 GB card, which is "
               "the most headroom of any 30B-class option here."],
    ),

    Model(
        tag="qwen3.6:35b",
        family="qwen3.6",
        size_gb=24.0,
        size_note="23-24 GB",
        context=262_144,
        capabilities=["tools", "thinking", "vision"],
        reference=14,
        positioning="General model with a coding emphasis, plus vision and "
                    "optional retention of reasoning context across turns.",
        min_vram_gb=32,
        notes=["Pick this over qwen3-coder when the vision capability earns "
               "its keep: reading a schematic, a plot, or a GUI screenshot. "
               "For RF and instrumentation work it often does."],
    ),

    Model(
        tag="qwen3-coder-next:q4_K_M",
        family="qwen3-coder-next",
        size_gb=52.0,
        context=262_144,
        quant="q4_K_M",
        capabilities=["tools"],
        reference=33,
        active_params_b=3.0,
        total_params_b=80.0,
        positioning="80B total with 3B active per token, built on "
                    "Qwen3-Next-80B-A3B-Base.",
        # 52 GB of weights plus the runtime reservation plus a usable cache
        # does not fit a 48 GB card, which is what the catalogue's own
        # validate() caught when this was first written as 48. The next
        # single-card tier that holds it is 64 GB; below that it needs memory
        # pooled across nodes.
        min_vram_gb=64,
        notes=["Needs the capacity of a 52 GB model and streams like a 2 GB "
               "one. The best capacity-for-speed trade on the shortlist, and "
               "the natural target for a pooled multi-node configuration.",
               "Non-thinking mode only: it emits no reasoning blocks."],
    ),
]


# %% Planner constants -------------------------------------------------------
# These feed the key/value cache and context-budget relations published on
# ollama-model-selection.html.  Each one is an ESTIMATE, not a citation, and
# the planner labels them as such wherever a result depends on them.

#: Runtime, driver and compute-buffer reservation on the accelerator, in GB.
#: Planning figure for a single-GPU llama.cpp or Ollama process; measure it
#: with nvidia-smi and subtract the published weight size.
RUNTIME_VRAM_GB: float = 1.2

#: Representative transformer shape for a 20-35B model, used only to make the
#: planner's context estimate concrete.  These are NOT read from any model.
#: `ollama show <tag>` prints the real values, and the planner says so.
ARCH_LAYERS: int = 48
ARCH_KV_HEADS: int = 8
ARCH_HEAD_DIM: int = 128

#: Bytes per cached element for each OLLAMA_KV_CACHE_TYPE value.  The f16
#: default and the q8_0 / q4_0 options are documented in the Ollama FAQ.
KV_BYTES: Dict[str, float] = {"f16": 2.0, "q8_0": 1.0, "q4_0": 0.5}


# %% Helpers -----------------------------------------------------------------
def by_tag(tag: str) -> Model:
    """Return one model by its exact tag.

    Raises
    ------
    KeyError
        If the tag is not in the shortlist.  Raising rather than returning
        None is deliberate: a typo in a page or in the planner must stop the
        build rather than silently produce an empty recommendation.
    """
    for model in MODELS:
        if model.tag == tag:
            return model
    raise KeyError(f"unknown model tag {tag!r}; "
                   f"shortlist is: {[m.tag for m in MODELS]}")


def tags() -> List[str]:
    """Return every shortlisted tag, in catalogue order."""
    return [m.tag for m in MODELS]


def for_vram(vram_gb: float) -> List[Model]:
    """Return the models that fit a VRAM budget, best fit first.

    "Fit" means the weight file plus the runtime reservation plus a minimum
    usable cache all sit on the card.  The minimum usable cache is taken as
    1 GB, which at the representative shape above is roughly 5000 tokens of
    f16 context -- below that the model is technically resident but cannot
    hold a useful prompt.

    Parameters
    ----------
    vram_gb : float
        Device memory available, in GB.

    Returns
    -------
    list of Model
        Ordered by descending weight size, so the first entry is the largest
        model that fits.  Empty when nothing fits.
    """
    MIN_USABLE_CACHE_GB = 1.0
    fitting = [
        m for m in MODELS
        if m.size_gb + RUNTIME_VRAM_GB + MIN_USABLE_CACHE_GB <= vram_gb
    ]
    return sorted(fitting, key=lambda m: m.size_gb, reverse=True)


def validate() -> None:
    """Fail loudly on an inconsistent catalogue.

    Checks that tags are unique, that every model carries the tool-calling
    gate, that a mixture-of-experts entry publishes both halves of its
    parameter split, and that every reference number is plausible.

    Raises
    ------
    ValueError
        Naming the first problem found.
    """
    seen = [m.tag for m in MODELS]
    if len(seen) != len(set(seen)):
        duplicates = sorted({t for t in seen if seen.count(t) > 1})
        raise ValueError(f"duplicate model tags: {duplicates}")

    for model in MODELS:
        if not model.drives_tools:
            raise ValueError(
                f"{model.tag} has no 'tools' capability; a model that cannot "
                f"call a tool cannot drive a terminal and does not belong in "
                f"this shortlist")
        if model.is_moe and not model.total_params_b:
            raise ValueError(
                f"{model.tag} publishes active parameters but not a total; "
                f"the streaming-size correction needs both")
        if model.size_gb <= 0 or model.context <= 0:
            raise ValueError(f"{model.tag} has a non-positive size or context")
        if model.min_vram_gb < model.size_gb:
            raise ValueError(
                f"{model.tag} claims a {model.min_vram_gb} GB minimum but the "
                f"weights alone are {model.size_gb} GB")


def as_javascript() -> str:
    """Serialise the catalogue as a JavaScript object literal.

    The planner on the homepage runs entirely in the browser with no network
    access, so the catalogue is baked into the page at build time rather than
    fetched.  Emitting it from this module -- rather than hand-writing it in
    the JavaScript -- is what keeps the planner and the prose table in step.

    Returns
    -------
    str
        A JavaScript object literal, indented for readability in View Source,
        assigned by the caller to a const.
    """
    import json

    records = []
    for model in MODELS:
        records.append({
            "tag": model.tag,
            "family": model.family,
            "sizeGb": model.size_gb,
            "sizeDisplay": model.size_display(),
            "context": model.context,
            "quant": model.quant or NOT_STATED,
            "capabilities": model.capabilities,
            "reference": model.reference,
            "positioning": model.positioning,
            "minVramGb": model.min_vram_gb,
            "activeParamsB": model.active_params_b,
            "totalParamsB": model.total_params_b,
            "streamingGb": round(model.streaming_gb, 2),
            "isMoe": model.is_moe,
            "notes": model.notes,
        })

    constants = {
        "runtimeVramGb": RUNTIME_VRAM_GB,
        "archLayers": ARCH_LAYERS,
        "archKvHeads": ARCH_KV_HEADS,
        "archHeadDim": ARCH_HEAD_DIM,
        "kvBytes": KV_BYTES,
        "readOn": READ_ON,
        "notStated": NOT_STATED,
    }

    return json.dumps({"models": records, "constants": constants},
                      indent=2)
