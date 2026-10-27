/* ==========================================================================
   sitenav.js  --  AI_Local shared navigation behaviour
   --------------------------------------------------------------------------
   Author : William W. Wallace
   Version: 1.0.0
   Purpose: 1) Mark the current page in the shared navigation strip.
            2) Drive the strip's theme button, but only on pages that do not
               already carry a theme control of their own.

   The strip's markup is emitted into each page at build time by
   scripts/build_ai_local_site.py, so this file only has to attach behaviour.

   NO BROWSER STORAGE.  These pages are opened from disk and are sometimes
   embedded in sandboxed iframes where localStorage access throws.  The theme
   follows the operating-system preference and can be overridden for the
   current page view only.  That is the same contract the Atomic Theory Atlas
   uses, and it means a reader never gets a stale pinned theme.
   ========================================================================== */

(function () {
  'use strict';

  var root = document.documentElement;

  /* ----------------------------------------------------------------------
     1. Mark the active link.

     WHY FULL-PATH COMPARISON AND NOT JUST THE FILENAME
     --------------------------------------------------
     Comparing only the final path segment was the first implementation and
     it is wrong as soon as there are two index.html files. The repository
     homepage is /index.html and the AI_Local overview is
     /AI_Local/index.html; a filename comparison marks the AI_Local overview
     as the current page while the reader is actually on the repository
     homepage, which is actively misleading about where they are.

     Resolving each href against the document URL and comparing the resulting
     pathnames is exact. It also handles, for free, a page opened as a
     directory URL ("/AI_Local/"), with a query string, or with a fragment,
     because the URL constructor normalises all three.
     ---------------------------------------------------------------------- */

  /** Normalise a pathname for comparison: lower-case, directory -> index. */
  function normalisePath(pathname) {
    var path = (pathname || '').toLowerCase();
    // A directory URL serves its index page.
    if (path === '' || path.charAt(path.length - 1) === '/') {
      path += 'index.html';
    }
    return path;
  }

  function markActiveLink() {
    var here = normalisePath(window.location.pathname);
    var links = document.querySelectorAll('.ailnav-links a[href]');

    Array.prototype.forEach.call(links, function (a) {
      var there;
      try {
        // getAttribute, not a.href, as the input: the attribute is the
        // authored relative href, and resolving it explicitly against the
        // document URL is what makes the comparison meaningful.
        there = normalisePath(
          new URL(a.getAttribute('href'), window.location.href).pathname);
      } catch (err) {
        // A malformed href should not break the whole strip.
        a.removeAttribute('aria-current');
        return;
      }

      if (there === here) {
        a.setAttribute('aria-current', 'page');
      } else {
        a.removeAttribute('aria-current');
      }
    });
  }

  /* ----------------------------------------------------------------------
     2. Theme control.

     The build script injects the button only when the host page has no theme
     control of its own, so if the button is absent there is nothing to do
     and the page's existing toggle stays in sole charge of data-theme.
     ---------------------------------------------------------------------- */
  function wireTheme() {
    var button = document.querySelector('.ailnav-theme');
    if (!button) { return; }                 // page owns its own toggle

    var media = window.matchMedia('(prefers-color-scheme: dark)');
    var manual = false;                      // set once the reader clicks
    var theme = media.matches ? 'dark' : 'light';

    /** Apply the current theme to <html> and repaint the button. */
    function apply() {
      root.setAttribute('data-theme', theme);

      var icon = button.querySelector('.ailnav-theme-icon');
      var label = button.querySelector('.ailnav-theme-label');

      // U+2600 sun shows the action available in dark mode (go light);
      // U+263E moon shows the action available in light mode (go dark).
      if (icon)  { icon.textContent  = (theme === 'dark') ? '☀' : '☾'; }
      if (label) { label.textContent = (theme === 'dark') ? 'Light' : 'Dark'; }

      button.setAttribute(
        'aria-label',
        (theme === 'dark') ? 'Switch to light theme' : 'Switch to dark theme'
      );
      button.setAttribute('aria-pressed', String(theme === 'dark'));
    }

    apply();

    button.addEventListener('click', function () {
      manual = true;                         // stop following the OS
      theme = (theme === 'dark') ? 'light' : 'dark';
      apply();
    });

    // Follow the operating system until the reader takes manual control.
    // addEventListener on a MediaQueryList is the modern form; the older
    // addListener is kept as a fallback for long-lived browser builds.
    function onSystemChange(event) {
      if (manual) { return; }
      theme = event.matches ? 'dark' : 'light';
      apply();
    }

    if (typeof media.addEventListener === 'function') {
      media.addEventListener('change', onSystemChange);
    } else if (typeof media.addListener === 'function') {
      media.addListener(onSystemChange);
    }
  }

  /** Run both pieces of setup. */
  function init() {
    markActiveLink();
    wireTheme();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
