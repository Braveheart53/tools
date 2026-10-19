# Page-content source modules

These are the sources the pages are generated from. The HTML in the parent
directory is build output: edit a module here and re-run the build, rather
than editing the HTML.

| Module | Holds |
|---|---|
| `eq_library.py` | All 15 equation blocks, with their variable tables and derivations. One definition per equation, referenced by slug, so a symbol or a unit is corrected in one place. |
| `references.py` | The IEEE reference list, the category labels and the per-reference sourcing-confidence class. `validate()` enforces unique, gap-free numbering. |
| `page_local_build.py` | Body of `local-code-build-test.html`. |
| `page_models.py` | Body of `ollama-model-selection.html`. |
| `page_sandbox.py` | Body of `claude-sandbox-local-env.html`. |
| `page_monitoring.py` | Body of `monitoring-sizing.html`. |
| `page_meta.py` | Bodies of `index.html`, `references.html` and `CHANGELOG.html`, plus `RELEASES`, which is the source of the version stamp on every page. |

Build with:

```bash
python ../scripts/build_ai_local_site.py \
    --src   /path/to/original/AI_Local \
    --out   /path/to/output/AI_Local \
    --modules .
```

Each module emits a **body fragment only**: no `<html>`, `<head>`, `<header>`,
`<nav>`, `<footer>`, `<style>` or `<script>`. The build script wraps it in the
shared page shell. That constraint comes from the authoring pattern in
`Educational/Atomic Theory Atlas.zip` → `PATTERNS.md`, which this set follows
for equation presentation and variable definitions.
