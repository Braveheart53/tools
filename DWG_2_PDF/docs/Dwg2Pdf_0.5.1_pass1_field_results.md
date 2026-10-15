---
title: dwg2pdf 0.5.1 — pass 1 field results on the 1762-drawing GBT archive
revision: 1.0.0
date: 2026-10-06
engine: dwg2pdf.py 0.5.1
host: bracca (Windows 11, AutoCAD 2025, conda env py3p12)
---

# dwg2pdf 0.5.1 — pass 1 field results (GBT ROSE_GBT archive)

First clean, complete measurement of the archive with a **single-backend
pass**. Run configuration:

```
python dwg2pdf.py C:\ATEMP\ROSE_GBT --out C:\ATEMP\GBT_PDF \
    --exclude Achive --layouts model --workers 4 \
    --backend libredwg+ezdxf -v --log-file C:\ATEMP\pass1.log
```

Archive staged to local disk (`C:\ATEMP\ROSE_GBT`) from OneDrive first, to
remove Files On-Demand hydration from the measurement.

## Headline result

| Metric | Value |
|---|---|
| Drawings found | 1762 |
| Converted (`ok`) | **806 (45.7 %)** |
| Failed | **956 (54.3 %)** |
| PDFs on disk | 806 — exact match, **zero output-path collisions** |
| Backend used | `libredwg+ezdxf` on all 1762 (single-backend pass) |
| Wall clock | ~6 min, 4 workers |

The AutoCAD fallback fraction is therefore
$f = 956/1762 = 54.3\,\%$ — **not the 2–5 % previously assumed**. Any cost
model for the accoreconsole tail must use this figure.

## Failure taxonomy

| Count | % of failures | Cause | Side |
|---|---|---|---|
| 564 | 59.0 % | `ERROR: Invalid EED size N > N` | decoder |
| 252 | 26.4 % | `ERROR: Invalid obj->size N changed to N` | decoder |
| 105 | 11.0 % | `ValueError: cannot convert float NaN to integer` | **engine** |
| 17 | 1.8 % | `nothing to render for --layouts 'model': Model (empty)` | **engine / flag** |
| 16 | 1.7 % | `ERROR: Duplicate handle` | decoder |
| 2 | 0.2 % | `DXFStructureError: Expected DXF entity TEXT` | decoder |

Rolled up:

| Group | Count | Share of failures |
|---|---|---|
| Decoder-side (`dwg2dxf` rc=1) | **832** | 87.0 % |
| Engine-side (fixable without AutoCAD) | **122** | 12.8 % |

## Timing

| Set | n | mean | median | max | total CPU |
|---|---|---|---|---|---|
| `ok` | 806 | 1.77 s | 1.16 s | 18.63 s | 1427.0 s |
| `failed` | 956 | 0.08 s | 0.04 s | 1.42 s | 74.5 s |

Failures are **essentially free** (78 ms mean). A `libredwg+ezdxf`-only
pass is therefore a cheap and definitive triage step: it costs ~6 minutes
to partition the whole archive.

Entity counts on converted sheets: mean 1078, median 886, max 7670.

## Implications

### 1. The staged-pass design is validated

With accoreconsole in the pass-1 chain, two workers wedged at drawing 36
and the counter never advanced (see
`dwg2pdf-0.5.1-accoreconsole-prompt-desync.md`). With a single-backend
pass, all 1762 completed in ~6 minutes. Confirms `--passes per-backend`
(0.5.2 item 10).

### 2. 122 drawings are recoverable with no AutoCAD at all

- **17 empty-model-space sheets.** These are title-block / notes sheets
  whose content lives entirely in paperspace. `--layouts auto` already
  handles this correctly in 0.5.1 (`paper_wins` is true when
  `model_entities == 0`), so re-running with `--layouts auto
  --skip-existing` recovers them at zero cost. Notably this includes
  `121722_01_X2 - Assembly Notes.dwg`, the drawing that wedged
  accoreconsole for a full day.
- **105 `NaN -> int` failures.** A genuine renderer defect: a non-finite
  coordinate reaches an integer conversion in the page-fit / render path.
  New 0.5.2 item.

This also re-opens the `--layouts` default question. 0.5.0 defaulted to
`auto` and regressed (picked a title block over a 400-entity model space);
0.5.1 reverted to `model` and now silently fails 17 legitimate sheets.
Neither default is right — `auto` with correct weighting is.

### 3. The decoder version is now the highest-value open question

816 of 956 failures (85 %) are `Invalid EED size` and `Invalid obj->size`
— both classic LibreDWG defect classes. The repository bundles LibreDWG
**0.14.8593** in `vendor/libredwg-win64/`, but conda-forge ships
**0.11.3876 (2020)**, and PATH order decides which wins. Six years of
decoder fixes separate them.

**Unresolved:** which decoder actually ran this pass. If 0.11 won, a
substantial fraction of the 832 decoder failures may be recoverable by
fixing PATH order alone — potentially hundreds of drawings that would
otherwise need AutoCAD.

### 4. Revised cost model for the AutoCAD tail

With $N = 956$ drawings needing accoreconsole and $W$ workers:

$$T = \frac{N \cdot t_{\text{drawing}}}{W}$$

| $t_{\text{drawing}}$ | $W = 2$ | $W = 4$ |
|---|---|---|
| 15 s | 2.0 h | 1.0 h |
| 30 s | 4.0 h | 2.0 h |
| 300 s (current broken state) | 39.8 h | 19.9 h |

The present accoreconsole path cannot complete this tail at all — see the
prompt-desynchronisation defect. Fixing it is now mandatory rather than an
optimisation.

## Open items

1. Capture the decoder-version line from `pass1.log` and confirm whether
   `vendor/libredwg-win64` or conda-forge 0.11 is in use.
2. Re-run with `--layouts auto --skip-existing` to bank the 17 paperspace
   sheets.
3. 0.5.2: fix `_plot_interactive` setup/plot phase separation (item 14),
   the `NaN -> int` renderer defect, worker logging, pre-attempt logging,
   staged passes, and the `--layouts auto` weighting.

## Source data

`manifest.csv` / `manifest.json`, 1762 rows, written by the run above to
`C:\ATEMP\GBT_PDF`.