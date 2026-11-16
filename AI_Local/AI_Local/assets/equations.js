/* ==========================================================================
   equations.js  --  AI_Local shared equation behaviour
   --------------------------------------------------------------------------
   Author : William W. Wallace
   Version: 1.0.0
   Purpose: 1) Render TeX written as \( ... \) and \[ ... \] with the vendored,
               offline copy of KaTeX.
            2) Wire the "Define variables" disclosure button on every .eq card
               to the matching .vars table.
            3) Expose a tiny helper so a host page can re-render after it
               injects markup dynamically.

   LOADING ORDER (enforced by the pages, not by this file):
       assets/katex/katex.min.css
       assets/katex/katex.min.js
       assets/katex/contrib/auto-render.min.js
       assets/equations.js          <- this file, last

   NO BROWSER STORAGE is used anywhere in this file.  These pages are opened
   straight off disk (file://) and sometimes inside sandboxed iframes where
   localStorage throws on access; avoiding it entirely removes that failure
   mode.  Theme state belongs to the host page, not to this component.
   ========================================================================== */

(function () {
  'use strict';

  /* ----------------------------------------------------------------------
     KaTeX delimiter configuration.

     The delimiter set deliberately matches the Atomic Theory Atlas:
         \[ ... \]   display math
         \( ... \)   inline math
     A bare '$' is NOT a delimiter.  These pages are full of shell snippets
     such as  $env:USERPROFILE  and  ${VERSION}  and PowerShell '$svcArgs',
     and treating '$' as math would mangle every one of them.

     'ignoredTags' additionally keeps KaTeX out of <pre> and <code>, so a
     literal backslash-bracket inside a command block is left alone.
     ---------------------------------------------------------------------- */
  var KATEX_OPTIONS = {
    delimiters: [
      { left: '\\[', right: '\\]', display: true },
      { left: '\\(', right: '\\)', display: false }
    ],
    ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option'],
    throwOnError: false
  };

  /**
   * Render all math inside a DOM subtree.
   *
   * @param {HTMLElement} [root] Subtree to scan. Defaults to document.body.
   * @returns {boolean} true when KaTeX was present and rendering ran.
   */
  function renderMath(root) {
    // renderMathInElement is supplied by katex/contrib/auto-render.min.js.
    // If the vendored copy is missing, the page must still be readable, so
    // this degrades to a no-op instead of throwing.
    if (typeof window.renderMathInElement !== 'function') { return false; }
    try {
      window.renderMathInElement(root || document.body, KATEX_OPTIONS);
      return true;
    } catch (err) {
      // A malformed expression on one page must not stop the rest of the
      // page's behaviour (notably the variable-table buttons below).
      if (window.console && console.warn) {
        console.warn('[equations.js] KaTeX rendering failed:', err);
      }
      return false;
    }
  }

  /**
   * Wire one "Define variables" button to the table it controls.
   *
   * The button carries aria-controls="<id of the .vars block>"; the .vars
   * block starts with the boolean [hidden] attribute.  Toggling [hidden]
   * rather than a CSS class keeps the collapsed state exposed to assistive
   * technology without any extra ARIA bookkeeping.
   *
   * @param {HTMLButtonElement} button The .info button inside an .eq card.
   */
  function wireDisclosure(button) {
    var targetId = button.getAttribute('aria-controls');
    if (!targetId) { return; }

    var target = document.getElementById(targetId);
    if (!target) {
      if (window.console && console.warn) {
        console.warn('[equations.js] no .vars block with id "' + targetId + '"');
      }
      return;
    }

    // Guard against double-wiring if a host page calls init() twice.
    if (button.getAttribute('data-eqc-wired') === 'true') { return; }
    button.setAttribute('data-eqc-wired', 'true');

    button.addEventListener('click', function () {
      var opening = target.hasAttribute('hidden');

      if (opening) {
        target.removeAttribute('hidden');
      } else {
        target.setAttribute('hidden', '');
      }

      button.setAttribute('aria-expanded', String(opening));

      // Swap the visible label so the control reads as a toggle.
      var label = button.querySelector('.info-label');
      if (label) {
        label.textContent = opening ? 'Hide variables' : 'Define variables';
      }
    });
  }

  /**
   * Initialise the component: render math, then wire every disclosure button.
   *
   * @param {HTMLElement} [root] Subtree to initialise. Defaults to document.
   */
  function init(root) {
    var scope = root || document;
    renderMath(scope === document ? document.body : scope);

    var buttons = scope.querySelectorAll('.eq .info[aria-controls]');
    Array.prototype.forEach.call(buttons, wireDisclosure);
  }

  /* ----------------------------------------------------------------------
     Public helper.  A page that injects equation markup after load (none do
     today, but the monitoring pages are the likely candidates) calls
     window.AILocalEquations.init(newSubtree) to pick it up.
     ---------------------------------------------------------------------- */
  window.AILocalEquations = {
    init: init,
    renderMath: renderMath,
    options: KATEX_OPTIONS
  };

  /* ----------------------------------------------------------------------
     Auto-start.  The scripts are loaded at the end of <body> on every page,
     so the DOM is normally already parsed; the readyState check covers the
     case where a page author moves the tags into <head> with defer.
     ---------------------------------------------------------------------- */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); });
  } else {
    init();
  }
})();
