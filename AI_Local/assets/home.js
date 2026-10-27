/* ==========================================================================
   home.js  --  interactive behaviour for the repository-root homepage
   --------------------------------------------------------------------------
   Author : William W. Wallace
   Version: 1.1.0

   Four independent features, each wired separately so a failure in one
   cannot disable the others:

     1. Hardware tier selector  -- dims stages the chosen setup does not need
     2. Progress tracker        -- counts completed stages, copyable summary
     3. Model-fit calculator    -- evaluates the published memory relations
     4. Model planner           -- names the models that fit the reader's
                                   card and loads one into the calculator

   DESIGN RULES THIS FILE FOLLOWS
   ------------------------------
   * NO BROWSER STORAGE. These pages are opened from local disk (file://) and
     sometimes inside sandboxed frames, where localStorage access throws
     rather than returning empty. Every piece of state below lives in a
     closure variable for the life of the page view. The "Copy progress"
     button exists precisely because of that: it is the supported way to keep
     a snapshot.
   * PROGRESSIVE ENHANCEMENT. Without JavaScript the page is still complete
     and readable: every stage is visible, no stage is dimmed, and the
     calculator is a form that simply does not compute. Nothing below hides
     content on load.
   * ARIA IS THE SOURCE OF TRUTH. Selection state lives in aria-pressed and
     the hidden attribute, which both the CSS and assistive technology read,
     rather than in a parallel class that can fall out of step.
   ========================================================================== */

(function () {
  'use strict';

  /* ======================================================================
     1. Hardware tier selector
     ====================================================================== */

  /**
   * Wire the tier buttons to the stage cards.
   *
   * Each stage card carries data-applies, a space-separated list of tier
   * keys. Selecting a tier dims every stage whose list does not contain it.
   * Dimming rather than hiding is deliberate: a reader should be able to see
   * what they are skipping, and read the stage's own "Why here" before
   * deciding to skip it.
   *
   * Clicking the selected tier again clears the selection, which is the
   * behaviour a toggle implies and which gives a way back to the full view.
   */
  function wireTierSelector() {
    var buttons = document.querySelectorAll('.tier[data-tier]');
    if (!buttons.length) { return; }

    var stages = document.querySelectorAll('.stage[data-applies]');
    var notes = document.querySelectorAll('[data-tier-note]');
    var selected = null;          // the chosen tier key, or null for "all"

    /** Apply the current selection to the stages and the note panels. */
    function paint() {
      Array.prototype.forEach.call(buttons, function (button) {
        button.setAttribute(
          'aria-pressed',
          String(button.getAttribute('data-tier') === selected));
      });

      Array.prototype.forEach.call(stages, function (stage) {
        if (!selected) {
          stage.classList.remove('dimmed');
          return;
        }
        // data-applies is a token list, so a substring test would match
        // "pair" inside a hypothetical "paired". Split and compare exactly.
        var applies = (stage.getAttribute('data-applies') || '').split(/\s+/);
        var needed = applies.indexOf(selected) !== -1;
        stage.classList.toggle('dimmed', !needed);
      });

      Array.prototype.forEach.call(notes, function (note) {
        var key = note.getAttribute('data-tier-note');
        var show = selected ? (key === selected) : (key === 'none');
        if (show) { note.removeAttribute('hidden'); }
        else { note.setAttribute('hidden', ''); }
      });
    }

    Array.prototype.forEach.call(buttons, function (button) {
      button.addEventListener('click', function () {
        var key = button.getAttribute('data-tier');
        selected = (selected === key) ? null : key;   // click again to clear
        paint();
      });
    });

    paint();
  }

  /* ======================================================================
     2. Progress tracker
     ====================================================================== */

  /**
   * Wire the per-stage "Done" checkboxes to the progress bar.
   *
   * The count is derived from the checkboxes on every update rather than
   * kept in a separate counter, so the displayed number cannot drift away
   * from the actual state of the controls.
   */
  function wireProgress() {
    var boxes = document.querySelectorAll('.stage-done input[data-stage]');
    if (!boxes.length) { return; }

    var bar = document.querySelector('.progress-bar');
    var fill = document.querySelector('.progress-fill');
    var text = document.querySelector('.progress-text');
    var copyButton = document.getElementById('copy-progress');
    var total = boxes.length;

    /** Recompute the bar, the label and each card's complete styling. */
    function update() {
      var done = 0;

      Array.prototype.forEach.call(boxes, function (box) {
        var card = box.closest('.stage');
        if (card) { card.classList.toggle('complete', box.checked); }
        if (box.checked) { done += 1; }
      });

      var percent = total ? Math.round((done / total) * 100) : 0;
      if (fill) { fill.style.width = percent + '%'; }
      if (bar) { bar.setAttribute('aria-valuenow', String(done)); }
      if (text) {
        text.textContent = done + ' of ' + total + ' stages marked done'
                         + (done === total ? ' — setup complete' : '');
      }
    }

    Array.prototype.forEach.call(boxes, function (box) {
      box.addEventListener('change', update);
    });

    /* ---- copyable snapshot ------------------------------------------
       Progress is in-memory and resets on reload, so this is the
       supported way to keep it. The text is plain and dated, ready to
       paste into a notes file. */
    if (copyButton) {
      copyButton.addEventListener('click', function () {
        var lines = ['AI_Local setup progress — ' +
                     new Date().toISOString().slice(0, 10), ''];

        Array.prototype.forEach.call(boxes, function (box) {
          var card = box.closest('.stage');
          var titleNode = card ? card.querySelector('.stage-title') : null;
          var numberNode = card ? card.querySelector('.stage-num') : null;
          var title = titleNode ? titleNode.textContent.trim() : box.getAttribute('data-stage');
          var number = numberNode ? numberNode.textContent.trim() : '?';
          lines.push((box.checked ? '[x] ' : '[ ] ') +
                     'Stage ' + number + ' — ' + title);
        });

        var payload = lines.join('\n');

        /** Restore the button label after a short confirmation. */
        function confirm(message) {
          var original = copyButton.textContent;
          copyButton.textContent = message;
          window.setTimeout(function () {
            copyButton.textContent = original;
          }, 1800);
        }

        // navigator.clipboard is unavailable on file:// in some browsers and
        // rejects without a user gesture in others, so the textarea fallback
        // is not optional here.
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(payload).then(
            function () { confirm('Copied'); },
            function () { fallbackCopy(payload, confirm); });
        } else {
          fallbackCopy(payload, confirm);
        }
      });
    }

    update();
  }

  /**
   * Copy text using a temporary textarea and document.execCommand.
   *
   * Deprecated, and still the only method that works on a file:// origin in
   * several browsers. Wrapped in try/catch because execCommand throws rather
   * than returning false in some configurations.
   *
   * @param {string} text   The text to place on the clipboard.
   * @param {function} done Called with a short status message.
   */
  function fallbackCopy(text, done) {
    var area = document.createElement('textarea');
    area.value = text;
    // Keep it out of view and out of the layout, but still focusable:
    // display:none or visibility:hidden would make the selection fail.
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.top = '-1000px';
    area.style.opacity = '0';
    document.body.appendChild(area);

    try {
      area.select();
      var ok = document.execCommand('copy');
      done(ok ? 'Copied' : 'Press Ctrl+C');
    } catch (err) {
      done('Press Ctrl+C');
    } finally {
      // Remove it whatever happened, so a failure does not leave a stray
      // node in the document.
      document.body.removeChild(area);
    }
  }

  /* ======================================================================
     3. Model-fit calculator
     ====================================================================== */

  /* Bytes per gibibyte. VRAM and model sizes are quoted in GB by vendors but
     allocated in GiB by drivers; this calculator works in GiB throughout and
     says so, because mixing the two is a 7 % error in the direction that
     makes a model look like it fits when it does not. */
  var BYTES_PER_GIB = 1024 * 1024 * 1024;

  /**
   * Key/value cache cost of a single token, in bytes.
   *
   * Implements the per-token part of the relation published on
   * ollama-model-selection.html:
   *
   *     S_kv = 2 * n_l * n_kv * d_h * L_ctx * n_seq * b_kv
   *
   * The leading 2 is one key vector plus one value vector per cached token.
   *
   * @param {number} layers    n_l,   transformer layers
   * @param {number} kvHeads   n_kv,  key/value heads per layer
   * @param {number} headDim   d_h,   head dimension
   * @param {number} sequences n_seq, concurrent sequences
   * @param {number} bytesPer  b_kv,  bytes per cached element
   * @returns {number} bytes of cache consumed per token of context
   */
  function cachePerToken(layers, kvHeads, headDim, sequences, bytesPer) {
    return 2 * layers * kvHeads * headDim * sequences * bytesPer;
  }

  /** Format a byte count as GiB with one decimal. */
  function gib(bytes) {
    return (bytes / BYTES_PER_GIB).toFixed(1);
  }

  /** Format an integer with thousands separators, locale-independently. */
  function thousands(value) {
    return String(Math.round(value)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
  }

  /**
   * Wire the calculator form to its output.
   *
   * Recomputes on every input event rather than on submit, so the form never
   * needs a button and never navigates. The <form> element has no action, and
   * submit is suppressed, so an Enter keypress cannot reload the page and
   * lose the reader's progress checkboxes.
   */
  function wireCalculator() {
    var form = document.getElementById('fit-calc');
    var out = document.getElementById('calc-out');
    if (!form || !out) { return; }

    var fields = {
      vram:     document.getElementById('c-vram'),
      weights:  document.getElementById('c-weights'),
      runtime:  document.getElementById('c-runtime'),
      layers:   document.getElementById('c-layers'),
      kvHeads:  document.getElementById('c-kvheads'),
      headDim:  document.getElementById('c-headdim'),
      parallel: document.getElementById('c-parallel'),
      kvType:   document.getElementById('c-kvtype')
    };

    // A missing field would make every later read NaN, so fail visibly and
    // early rather than producing a nonsense number.
    for (var key in fields) {
      if (Object.prototype.hasOwnProperty.call(fields, key) && !fields[key]) {
        out.className = 'calc-out error';
        out.textContent = 'Calculator field "' + key + '" is missing from the page.';
        return;
      }
    }

    /** Read one numeric field, returning NaN when it is empty or invalid. */
    function num(element) {
      var value = parseFloat(element.value);
      return isFinite(value) ? value : NaN;
    }

    function compute() {
      var vram     = num(fields.vram)    * BYTES_PER_GIB;
      var weights  = num(fields.weights) * BYTES_PER_GIB;
      var runtime  = num(fields.runtime) * BYTES_PER_GIB;
      var layers   = num(fields.layers);
      var kvHeads  = num(fields.kvHeads);
      var headDim  = num(fields.headDim);
      var parallel = num(fields.parallel);
      var bytesPer = parseFloat(fields.kvType.value);

      if ([vram, weights, runtime, layers, kvHeads, headDim, parallel, bytesPer]
            .some(function (v) { return !isFinite(v); })) {
        out.className = 'calc-out warn';
        out.innerHTML = '<span class="headline">Fill in every field</span>' +
          'All eight inputs are needed to evaluate the relation.';
        return;
      }

      var remainder = vram - weights - runtime;
      var perToken = cachePerToken(layers, kvHeads, headDim, parallel, bytesPer);

      /* ---- the weights do not fit at all --------------------------- */
      if (remainder <= 0) {
        var over = -remainder;
        out.className = 'calc-out error';
        out.innerHTML =
          '<span class="headline">Does not fit — over by ' + gib(over) + ' GiB</span>' +
          'The weights plus the runtime reserve already exceed the card, before any ' +
          'cache is allocated. Layers will be placed in system RAM and decode will ' +
          'run roughly nine times slower.' +
          '<ul>' +
            '<li>Choose a smaller tag, or a lower quantisation of the same model.</li>' +
            '<li>Or split it across machines — see the ' +
              '<a href="AI_Local/llama-rpc-vulkan-guide.html">llama.cpp RPC guide</a>, ' +
              'and check the break-even condition first: distribute to escape a spill, ' +
              'never to add bandwidth.</li>' +
          '</ul>';
        return;
      }

      var maxTokens = Math.floor(remainder / perToken);

      /* ---- fits, but with no useful context ------------------------ */
      if (maxTokens < 2048) {
        out.className = 'calc-out error';
        out.innerHTML =
          '<span class="headline">' + thousands(maxTokens) + ' tokens — too small to work with</span>' +
          'The weights fit, leaving ' + gib(remainder) + ' GiB, but that is only ' +
          thousands(maxTokens) + ' tokens of context. A single C++ compiler error with ' +
          'template backtraces can exceed that.' +
          '<ul>' +
            '<li>Switch the cache to <span class="mono">q8_0</span> to double it, with little quality cost.</li>' +
            '<li>Or drop to a smaller model: headroom matters more than parameter count here.</li>' +
          '</ul>';
        return;
      }

      /* ---- fits ----------------------------------------------------- */
      var cacheAtMax = (perToken * maxTokens) / BYTES_PER_GIB;
      var at32k = (perToken * 32768) / BYTES_PER_GIB;
      var fits32k = (perToken * 32768) <= remainder;

      // 8192 tokens is roughly the floor for agent work: source under edit,
      // plus a build log, plus the conversation.
      var headroomClass = maxTokens >= 32768 ? 'calc-out'
                        : (maxTokens >= 8192 ? 'calc-out' : 'calc-out warn');

      out.className = headroomClass;
      out.innerHTML =
        '<span class="headline">' + thousands(maxTokens) + ' tokens of context</span>' +
        'Weights ' + gib(weights) + ' GiB and runtime ' + gib(runtime) + ' GiB leave ' +
        '<strong>' + gib(remainder) + ' GiB</strong> for the cache, at ' +
        thousands(perToken) + ' bytes per token.' +
        '<ul>' +
          '<li>A 32k context would need <strong>' + at32k.toFixed(1) + ' GiB</strong> of cache — ' +
            (fits32k ? 'that fits.' : 'that does <strong>not</strong> fit here.') + '</li>' +
          '<li>At the maximum above the cache alone is ' + cacheAtMax.toFixed(1) + ' GiB.</li>' +
          (bytesPer === 2
            ? '<li>Switching <span class="mono">OLLAMA_KV_CACHE_TYPE</span> to ' +
              '<span class="mono">q8_0</span> would roughly double this.</li>'
            : '<li>Cache is already quantised, which is why the figure is this large.</li>') +
          (maxTokens < 8192
            ? '<li><strong>Below 8k is tight for agent work:</strong> source under edit, ' +
              'plus a build log, plus the conversation.</li>'
            : '') +
        '</ul>' +
        '<p class="xs faint" style="margin:.6rem 0 0">Allocators fragment and, on Windows, ' +
        'the display driver can page VRAM out from under the runtime. Treat this as an ' +
        'upper bound and leave headroom.</p>';
    }

    // 'input' rather than 'change' so the result follows typing. The handler
    // is cheap -- a few multiplications and a string build -- so there is no
    // need to debounce it.
    form.addEventListener('input', compute);

    // A <form> with no action still navigates on Enter, which would reload
    // the page and clear the progress checkboxes above.
    form.addEventListener('submit', function (event) { event.preventDefault(); });

    compute();
  }


  /* ======================================================================
     Model planner

     Reads the catalogue baked into the page by model_catalog.py and names
     the models that fit the reader's card. Choosing one loads its published
     weight size into the fit calculator below, so the two halves of the
     section always agree about which model is being evaluated.

     The catalogue is embedded as <script type="application/json"> rather
     than fetched: these pages open from local disk (file://), where fetch()
     is blocked by the browser's origin rules, and rather than assigned to a
     global by an inline script, so the page carries no inline executable
     code.
     ====================================================================== */

  /** Minimum cache, in GB, below which a resident model is not usable. */
  var MIN_USABLE_CACHE_GB = 1.0;

  /**
   * Parse the catalogue data island.
   *
   * @returns {?{models: Array, constants: Object}} the catalogue, or null
   *   when the island is absent or malformed. Null is handled by the caller
   *   as "no planner", never as an exception: a broken catalogue must not
   *   cost the reader the calculator.
   */
  function readCatalog() {
    var island = document.getElementById('model-catalog');
    if (!island) { return null; }
    try {
      var data = JSON.parse(island.textContent);
      return (data && data.models && data.models.length) ? data : null;
    } catch (err) {
      if (window.console && console.warn) {
        console.warn('[home.js] model catalogue is not valid JSON:', err);
      }
      return null;
    }
  }

  /**
   * Select the models that fit a VRAM budget.
   *
   * Mirrors model_catalog.for_vram() exactly: a model fits when its weight
   * file, the runtime reservation and a minimum usable cache all sit on the
   * card. Keeping the two definitions identical is why MIN_USABLE_CACHE_GB
   * is named here rather than inlined -- if the Python side changes, this is
   * the one line that has to follow it.
   *
   * @param {Array} models      catalogue entries
   * @param {number} runtimeGb  V_rt, the runtime reservation in GB
   * @param {number} vramGb     V_tot, device memory in GB
   * @returns {Array} fitting models, largest first
   */
  function modelsForVram(models, runtimeGb, vramGb) {
    return models
      .filter(function (m) {
        return m.sizeGb + runtimeGb + MIN_USABLE_CACHE_GB <= vramGb;
      })
      .sort(function (a, b) { return b.sizeGb - a.sizeGb; });
  }

  /**
   * Select models that miss the budget by a small margin.
   *
   * WHY THIS BAND EXISTS
   * --------------------
   * The fit rule above adds a 1 GB minimum usable cache on top of the
   * weights and the runtime reservation, which is stricter than a vendor's
   * own claim. gpt-oss:20b is the case that matters: its Ollama page states
   * MXFP4 lets it run "on systems with as little as 16GB memory", and at
   * 14 GB it misses a 16 GB budget here by 0.2 GB.
   *
   * Silently dropping it would make the planner contradict the model
   * selection page, which recommends exactly that model at 16 GB and calls
   * its headroom "tight". Naming the near misses, and saying by how much,
   * keeps the two consistent and tells the reader what their options are
   * rather than just what they are not.
   *
   * @param {Array} models      catalogue entries
   * @param {number} runtimeGb  V_rt, the runtime reservation in GB
   * @param {number} vramGb     V_tot, device memory in GB
   * @param {number} marginGb   how far short still counts as a near miss
   * @returns {Array} near-miss models, closest first, each with a .shortBy
   */
  function modelsNearMiss(models, runtimeGb, vramGb, marginGb) {
    return models
      .map(function (m) {
        var needed = m.sizeGb + runtimeGb + MIN_USABLE_CACHE_GB;
        return { model: m, shortBy: needed - vramGb };
      })
      .filter(function (e) { return e.shortBy > 0 && e.shortBy <= marginGb; })
      .sort(function (a, b) { return a.shortBy - b.shortBy; });
  }

  /**
   * Render one catalogue entry as a selectable card.
   *
   * @param {Object} model     a catalogue entry
   * @param {boolean} isPick   true for the recommended (largest fitting) one
   * @returns {string} HTML for one card
   */
  function modelCard(model, isPick) {
    // Mixture-of-experts models occupy the card like their total size but
    // stream like their active subset, so both numbers are shown: the
    // capacity number and the speed number answer different questions.
    var moe = model.isMoe
      ? '<div class="pm-moe">' + model.totalParamsB + 'B total, <strong>' +
        model.activeParamsB + 'B active</strong> per token &mdash; occupies ' +
        'the card like ' + model.sizeDisplay + ', streams like ' +
        model.streamingGb + '&nbsp;GB</div>'
      : '';

    var caps = (model.capabilities || []).map(function (c) {
      return '<span class="pm-cap">' + c + '</span>';
    }).join('');

    return '' +
      '<li class="pm-card' + (isPick ? ' pm-pick' : '') + '">' +
        (isPick ? '<span class="pm-badge">best fit</span>' : '') +
        '<div class="pm-tag mono">' + model.tag + '</div>' +
        '<div class="pm-meta">' +
          model.sizeDisplay + ' &middot; ' +
          thousands(model.context) + ' token context &middot; ' +
          'quant: ' + model.quant +
        '</div>' +
        '<div class="pm-caps">' + caps + '</div>' +
        moe +
        '<p class="pm-why">' + model.positioning +
          '<a class="cite" href="AI_Local/references.html#r' + model.reference +
          '">[' + model.reference + ']</a></p>' +
        '<button type="button" class="pm-use" data-size="' + model.sizeGb + '">' +
          'Use in the calculator' +
        '</button>' +
      '</li>';
  }

  /**
   * Wire the planner: VRAM in, fitting models out, selection into the
   * calculator.
   */
  function wirePlanner() {
    var catalog = readCatalog();
    var out = document.getElementById('planner-out');
    var vramInput = document.getElementById('p-vram');
    var form = document.getElementById('planner');
    if (!catalog || !out || !vramInput || !form) { return; }

    var runtimeGb = catalog.constants.runtimeVramGb;

    /** Recompute the list and repaint it. */
    function render() {
      var vram = parseFloat(vramInput.value);
      if (!isFinite(vram) || vram <= 0) {
        out.className = 'planner-out';
        out.innerHTML = '<p class="small muted">Enter the card&rsquo;s memory to see what fits.</p>';
        return;
      }

      var fitting = modelsForVram(catalog.models, runtimeGb, vram);

      if (!fitting.length) {
        // The smallest entry is the useful thing to name here: it tells the
        // reader how far short they are rather than just saying "no".
        var smallest = catalog.models.reduce(function (a, b) {
          return a.sizeGb <= b.sizeGb ? a : b;
        });
        var need = (smallest.sizeGb + runtimeGb + MIN_USABLE_CACHE_GB).toFixed(1);
        out.className = 'planner-out error';
        out.innerHTML =
          '<p><strong>Nothing in the shortlist fits ' + vram + '&nbsp;GB.</strong> ' +
          'The smallest entry, <span class="mono">' + smallest.tag + '</span>, needs about ' +
          need + '&nbsp;GB once the runtime reservation and a usable cache are counted. ' +
          'Below that, run on CPU and accept the rate, or use a smaller tag than this ' +
          'shortlist carries &mdash; the ' +
          '<a href="AI_Local/ollama-model-selection.html#shortlist">model selection page</a> ' +
          'lists the full size ladders.</p>';
        return;
      }

      out.className = 'planner-out';
      out.innerHTML =
        '<p class="small muted">' + fitting.length +
        (fitting.length === 1 ? ' model fits' : ' models fit') +
        ' ' + vram + '&nbsp;GB, largest first. The largest that fits is not ' +
        'automatically the right choice: a smaller model leaves more room for ' +
        'context, and context is what an agent loop consumes.</p>' +
        '<ul class="pm-list">' +
          fitting.map(function (m, i) { return modelCard(m, i === 0); }).join('') +
        '</ul>' +
        nearMissBlock(vram);
    }

    /**
     * Render the near-miss band, or an empty string when there is none.
     *
     * @param {number} vram the reader's budget in GB
     * @returns {string} HTML
     */
    function nearMissBlock(vram) {
      var NEAR_MISS_MARGIN_GB = 2.0;
      var near = modelsNearMiss(catalog.models, runtimeGb, vram,
                                NEAR_MISS_MARGIN_GB);
      if (!near.length) { return ''; }

      var items = near.map(function (e) {
        return '<li><span class="mono">' + e.model.tag + '</span> &mdash; ' +
               e.model.sizeDisplay + ', short by about ' +
               e.shortBy.toFixed(1) + '&nbsp;GB</li>';
      }).join('');

      return '' +
        '<div class="pm-near">' +
          '<p class="small"><strong>Just misses.</strong> These fit the ' +
          'weights but leave under 1&nbsp;GB for the cache, which is the ' +
          'threshold used above. A vendor may still list the card as ' +
          'supported &mdash; the gpt-oss page states MXFP4 lets the 20b ' +
          'model run on 16&nbsp;GB &mdash; and it will load. Expect a short ' +
          'context, and set <span class="mono">OLLAMA_KV_CACHE_TYPE=q8_0</span> ' +
          'to halve the cache and buy some of it back.</p>' +
          '<ul class="small">' + items + '</ul>' +
        '</div>';
    }

    // Selecting a model loads its size into the calculator and scrolls it
    // into view, so the reader sees the number change rather than wondering
    // whether the button did anything.
    out.addEventListener('click', function (event) {
      var button = event.target.closest ? event.target.closest('.pm-use') : null;
      if (!button) { return; }

      var weights = document.getElementById('c-weights');
      var vramField = document.getElementById('c-vram');
      if (!weights || !vramField) { return; }

      weights.value = button.getAttribute('data-size');
      vramField.value = vramInput.value;

      // 'input' rather than 'change': the calculator listens for input, and
      // setting .value programmatically fires neither event on its own.
      weights.dispatchEvent(new Event('input', { bubbles: true }));
      vramField.dispatchEvent(new Event('input', { bubbles: true }));

      var calc = document.getElementById('fit-calc');
      if (calc && calc.scrollIntoView) {
        calc.scrollIntoView({ block: 'center', behavior: 'smooth' });
      }

      // Mark which card is loaded, so the selection is visible after the
      // scroll moves the list out of view and back.
      var cards = out.querySelectorAll('.pm-card');
      Array.prototype.forEach.call(cards, function (card) {
        card.classList.remove('pm-loaded');
      });
      var card = button.closest('.pm-card');
      if (card) { card.classList.add('pm-loaded'); }
    });

    vramInput.addEventListener('input', render);
    form.addEventListener('submit', function (event) { event.preventDefault(); });

    render();
  }

  /* ======================================================================
     Start-up
     ====================================================================== */

  /**
   * Initialise every interactive feature on the page.
   *
   * Each is wrapped so that an exception in one does not prevent the others
   * from being wired. A broken calculator must not cost the reader the
   * navigation and progress features.
   *
   * Order matters in one place only: wirePlanner() runs after
   * wireCalculator(), so that the calculator is already listening when the
   * planner's initial render completes and the reader's first click on
   * "Use in the calculator" has somewhere to deliver its value.
   */
  function init() {
    [wireTierSelector, wireProgress, wireCalculator, wirePlanner].forEach(function (fn) {
      try {
        fn();
      } catch (err) {
        if (window.console && console.warn) {
          console.warn('[home.js] ' + fn.name + ' failed:', err);
        }
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
