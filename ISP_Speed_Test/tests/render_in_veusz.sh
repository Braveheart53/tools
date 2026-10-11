#!/usr/bin/env bash
# render_in_veusz.sh — version 1.1.0
# revision history (newest first)
#   1.1.0  2026-10-11  completion detected through a DONE marker, then Veusz is terminated
#                      (Veusz 4.2.x does not exit on Quit() in --listen mode; 1.0.x waited for the 180 s timeout)
#   1.0.1  2026-09-04  veusz binary taken from PATH / $VEUSZ_BIN (no hard-coded path)
#   1.0.0  2026-09-04  initial
# Usage: render_in_veusz.sh <file.vszh5> <outdir> [dpi]  — loads the document in real Veusz and renders every page to PNG
set -u
F="$(readlink -f "$1")"; OUT="$2"; DPI="${3:-80}"; VZ="${VEUSZ_BIN:-veusz}"   # set VEUSZ_BIN if veusz is not on PATH
mkdir -p "$OUT"; OUT="$(readlink -f "$OUT")"; rm -f "$OUT"/*.png "$OUT/DONE" "$OUT/veusz_log.txt"
cat > "$OUT/cmds.py" << PY
import veusz.document.loader as L
doc = Root._ci.document
L.loadHDF5Doc(doc, '$F')
print('DATASETS', len(doc.data))
print('TYPES', sorted(set(type(d).__name__ for d in doc.data.values())))
print('PAGES', [p.name for p in doc.basewidget.children])
exec("for i, p in enumerate(doc.basewidget.children): Export('$OUT/%02d_%s.png' % (i, p.name), page=[i], dpi=$DPI)")
print('EXPORT_DONE')
open('$OUT/DONE', 'w').write('ok')
Quit()
PY
export LC_ALL="${LC_ALL:-C.UTF-8}"; [ -z "${DISPLAY:-}" ] && export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
"$VZ" --listen --quiet < "$OUT/cmds.py" > "$OUT/veusz_log.txt" 2>&1 &
PID=$!
for _ in $(seq 1 "${RENDER_TIMEOUT_S:-180}"); do [ -f "$OUT/DONE" ] && break; kill -0 "$PID" 2>/dev/null || break; sleep 1; done
kill "$PID" 2>/dev/null; sleep 1; kill -9 "$PID" 2>/dev/null
grep -v -i "locale\|UTF-8\|SAMP\|reconfigure\|for more information" "$OUT/veusz_log.txt"
if [ -f "$OUT/DONE" ]; then rm -f "$OUT/DONE" "$OUT/cmds.py"; ls "$OUT"/*.png; else echo "RENDER FAILED (no DONE marker)"; exit 1; fi
