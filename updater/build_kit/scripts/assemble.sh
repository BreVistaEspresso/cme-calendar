#!/usr/bin/env bash
# Rebuild everything: data -> JSX -> standalone HTML.
# Usage: assemble.sh <events.csv> <kit_root> [YYYY-MM-DD]
#   <events.csv>  the single source of truth (Data/events.csv)
#   <kit_root>    the build_kit folder (contains scripts/); build/ and bundle/ are created inside it
#   run date      defaults to today's system date. Pass it explicitly in scheduled runs.
# Set DATA_ONLY=1 to run only the data stage (writes build/conferences.json + build/build_report.txt, no node needed).
# A hard validation failure in build_data.py (exit 2) stops the build before any JSX or HTML is produced.
set -euo pipefail
[ "$#" -ge 2 ] || { echo "usage: assemble.sh <events.csv> <kit_root> [YYYY-MM-DD]" >&2; exit 64; }
EVENTS="$1"; ROOT="$2"; RUN_DATE="${3:-$(date +%F)}"
mkdir -p "$ROOT/build" "$ROOT/bundle"
python3 -I "$ROOT/scripts/build_data.py" "$EVENTS" "$ROOT/build" "$RUN_DATE" > "$ROOT/build/build_report.txt" || { echo "build_data.py failed; see $ROOT/build/build_report.txt" >&2; exit 2; }
grep -E "^(entries|FAILURES):" "$ROOT/build/build_report.txt"
[ "${DATA_ONLY:-0}" = "1" ] && { echo "DATA_ONLY=1: stopping after the data stage"; exit 0; }
[ -x "$ROOT/bundle/node_modules/.bin/esbuild" ] || { echo "esbuild missing: run the npm install in README.md step 1 first" >&2; exit 3; }
python3 -I - "$ROOT" "$RUN_DATE" <<'PY'
import json, sys, datetime as dt
root = sys.argv[1]
_d = dt.date.fromisoformat(sys.argv[2])
ASOF = f"{_d:%B} {_d.day}, {_d.year}"
data = json.load(open(f"{root}/build/conferences.json", encoding="utf-8"))
tpl = open(f"{root}/scripts/calendar_template.jsx", encoding="utf-8").read()
assert "/*__DATA__*/ []" in tpl and "__ASOF__" in tpl
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
def make(ics):
    return tpl.replace("/*__DATA__*/ []", blob).replace("__ASOF__", ASOF).replace("/*__ICS__*/ true", "true" if ics else "false")
out = make(True)
open(f"{root}/bundle/calendar_hosted.jsx", "w", encoding="utf-8").write(make(False))
open(f"{root}/build/brevista_conference_calendar.jsx", "w", encoding="utf-8").write(out)
print("jsx bytes:", len(out.encode("utf-8")), "entries:", len(data))
PY
cp "$ROOT/build/brevista_conference_calendar.jsx" "$ROOT/bundle/calendar.jsx"
cat > "$ROOT/bundle/entry.jsx" <<'JS'
import React from 'react';
import { createRoot } from 'react-dom/client';
import Calendar from './calendar.jsx';
createRoot(document.getElementById('root')).render(<Calendar />);
JS
cd "$ROOT/bundle"
sed "s#./calendar.jsx#./calendar_hosted.jsx#" entry.jsx > entry_hosted.jsx
./node_modules/.bin/esbuild entry_hosted.jsx --bundle --minify --format=iife --jsx=automatic --define:process.env.NODE_ENV=\"production\" --outfile=bundle_hosted.js --log-level=warning
./node_modules/.bin/esbuild entry.jsx --bundle --minify --format=iife --jsx=automatic --define:process.env.NODE_ENV=\"production\" --outfile=bundle.js --log-level=warning
python3 -I - "$ROOT" <<'PY'
import sys
root = sys.argv[1]
js = open(f"{root}/bundle/bundle.js", encoding="utf-8").read().replace("</script", "<\\/script")
html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Global CME Calendar</title>
<style>html,body{{margin:0;background:#fff}}</style></head>
<body><div id="root"></div><script>{js}</script></body></html>"""
open(f"{root}/build/Global_CME_Calendar.html", "w", encoding="utf-8").write(html)
hj = open(f"{root}/bundle/bundle_hosted.js", encoding="utf-8").read().replace("</script", "<\\/script")
hosted = f"""<title>Global CME Calendar</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap">
<style>:root{{--page-bg:#FFFFFF;--page-fg:#333333;color-scheme:light}}body{{background:var(--page-bg);color:var(--page-fg);margin:0}}</style>
<div id="root"></div>
<script>{hj}</script>
"""
open(f"{root}/build/hosted_page.html", "w", encoding="utf-8").write(hosted)
print("hosted bytes:", len(hosted.encode("utf-8")))
print("html bytes:", len(html.encode("utf-8")))
PY
