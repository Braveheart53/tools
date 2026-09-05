#!/usr/bin/env bash
# render_in_veusz.sh — version 1.0.1
# revision history (newest first)
#   1.0.1  2026-09-04  veusz binary taken from PATH / $VEUSZ_BIN (no hard-coded path)
#   1.0.0  2026-09-04  initial
# Usage: render_in_veusz.sh <file.vszh5> <outdir>   — loads the document in real Veusz and renders every page to PNG
set -u
F="$1"; OUT="$2"; VZ="${VEUSZ_BIN:-veusz}"   # set VEUSZ_BIN if veusz is not on PATH
rm -rf "$OUT"; mkdir -p "$OUT"
(cat << PY
import veusz.document.loader as L
doc = Root._ci.document
L.loadHDF5Doc(doc, '$F')
print('DATASETS', len(doc.data))
print('TYPES', sorted(set(type(d).__name__ for d in doc.data.values())))
print('PAGES', [p.name for p in doc.basewidget.children])
exec("for i, p in enumerate(doc.basewidget.children): Export('$OUT/%02d_%s.png' % (i, p.name), page=[i], dpi=80)")
print('EXPORT_DONE')
Quit()
PY
) | QT_QPA_PLATFORM=offscreen timeout 180 "$VZ" --listen --quiet 2>&1 | grep -v -i "locale\|UTF-8\|SAMP\|reconfigure\|for more information"
ls "$OUT"
