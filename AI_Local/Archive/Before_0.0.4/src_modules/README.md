# Page-content source modules

These are the sources the pages are generated from. The HTML in the parent
directory is build output: edit a module here and re-run the build, rather
than editing the HTML.

| Module | Holds |
|---|---|
| `eq_library.py` | All 15 equation blocks, with their variable tables and derivations. One definition per equation, referenced by slug, so a symbol or a unit is corrected in one place. |
| `model_catalog.py` | The model shortlist as data: tag, size, context, quantisation, capabilities, citation and positioning, every value the figure published on that model's Ollama page. Read by the homepage planner AND checked against `ollama-model-selection.html` by the build, so the two cannot disagree. |
| `repo_inventory.py` | The repository's own structure as data: the five flow stages, every project and where it sits, the hardware tiers and the companion repositories. `page_home.py` renders it. |
| `page_home.py` | Body of the repository-root `index.html`. |
| `references.py` | The IEEE reference list, the category labels and the per-reference sourcing-confidence class. `validate()` enforces unique, gap-free numbering. |
| `page_local_build.py` | Body of `local-code-build-test.html`. |
| `page_models.py` | Body of `ollama-model-selection.html`. |
| `page_sandbox.py` | Body of `claude-sandbox-local-env.html`. |
| `page_monitoring.py` | Body of `monitoring-sizing.html`. |
| `page_meta.py` | Bodies of `index.html`, `references.html` and `CHANGELOG.html`, plus `RELEASES`, which is the source of the version stamp on every page. |
| `repo_inventory.py` | The whole repository as data: every project, the five-stage implementation flow, the hardware tiers and the companion repositories. The repository homepage is a rendering of this, so a project added here appears in its stage, in the toolbox table and in the repository map with no second edit. |
| `page_home.py` | Body of the repository-root `index.html`, one level above this directory. |

Build with:

```bash
python ../scripts/build_ai_local_site.py \
    --src       /path/to/original/AI_Local \
    --out       /path/to/output/AI_Local \
    --modules   . \
    --repo-root /path/to/output \
    --repo-tree /path/to/the/real/repository
```

`--repo-root` additionally writes the repository homepage there and adds a
**Repo home** back-link to every navigation strip in this set. Omit it to build
a self-contained AI_Local set with no outward links, which is what you want if
the set is ever published on its own.

`--repo-tree` points at the real repository so the homepage's links into
sibling projects are verified. Without it those links are skipped, and the skip
is reported rather than passing silently: the build output holds only this
directory, so they cannot resolve inside it.

Each module emits a **body fragment only**: no `<html>`, `<head>`, `<header>`,
`<nav>`, `<footer>`, `<style>` or `<script>`. The build script wraps it in the
shared page shell. That constraint comes from the authoring pattern in
`Educational/Atomic Theory Atlas.zip` → `PATTERNS.md`, which this set follows
for equation presentation and variable definitions.
