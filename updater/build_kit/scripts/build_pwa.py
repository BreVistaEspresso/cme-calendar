#!/usr/bin/env python3
"""Build the installable PWA folder (build_kit/pwa/) from build/conferences.json.
Usage: python3 -I scripts/build_pwa.py <kit_root> YYYY-MM-DD
Run after assemble.sh (needs bundle/node_modules esbuild). Pass the run date explicitly."""
import sys, json, datetime as dt, subprocess, os, shutil
root, run = sys.argv[1], sys.argv[2]
d = dt.date.fromisoformat(run)
asof = f"{d:%B} {d.day}, {d.year}"
data = json.load(open(f"{root}/build/conferences.json", encoding="utf-8"))
tpl = open(f"{root}/scripts/calendar_template.jsx", encoding="utf-8").read()
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
jsx = (tpl.replace("/*__DATA__*/ []", blob).replace("__ASOF__", asof).replace("__ASOF_ISO__", run)
          .replace("/*__ICS__*/ true", "true").replace("/*__PWA__*/ false", "true"))
assert "const PWA = true;" in jsx
b = f"{root}/bundle"
open(f"{b}/calendar_pwa.jsx", "w", encoding="utf-8").write(jsx)
open(f"{b}/entry_pwa.jsx", "w", encoding="utf-8").write(
 "import React from 'react';\nimport { createRoot } from 'react-dom/client';\nimport Calendar from './calendar_pwa.jsx';\ncreateRoot(document.getElementById('root')).render(<Calendar />);\n")
out = f"{root}/pwa"; os.makedirs(out, exist_ok=True)
subprocess.run([f"{b}/node_modules/.bin/esbuild", "entry_pwa.jsx", "--bundle", "--minify", "--format=iife", "--jsx=automatic",
  '--define:process.env.NODE_ENV="production"', f"--outfile={out}/app.js", "--log-level=warning"], cwd=b, check=True)
open(f"{out}/index.html", "w", encoding="utf-8").write(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Global CME Calendar</title>
<meta name="theme-color" content="#3E1F47">
<link rel="manifest" href="manifest.webmanifest">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="icon-192.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap">
<style>html,body{{margin:0;background:#fff}}</style></head>
<body><div id="root"></div><script src="app.js?v={run}"></script>
<script>if('serviceWorker' in navigator){{window.addEventListener('load',function(){{navigator.serviceWorker.register('sw.js').catch(function(){{}})}})}}</script>
</body></html>""")
json.dump({"name":"Global CME Calendar","short_name":"CME Calendar","start_url":"./","scope":"./","display":"standalone",
  "background_color":"#ffffff","theme_color":"#3E1F47","icons":[
   {"src":"icon-192.png","sizes":"192x192","type":"image/png","purpose":"any"},
   {"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"any"},
   {"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]},
  open(f"{out}/manifest.webmanifest","w"), indent=1)
# service worker: cache the app shell; latest.json is always network-first
open(f"{out}/sw.js","w").write(f"""const C='cme-shell-{run}';
const SHELL=['./','index.html','app.js?v={run}','manifest.webmanifest','icon-192.png','icon-512.png'];
self.addEventListener('install',e=>{{e.waitUntil(caches.open(C).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))}});
self.addEventListener('activate',e=>{{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))).then(()=>self.clients.claim()))}});
self.addEventListener('fetch',e=>{{
  const u=new URL(e.request.url);
  if(e.request.method!=='GET'||u.origin!==location.origin)return;
  if(u.pathname.endsWith('latest.json')){{e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));return}}
  e.respondWith(fetch(e.request).then(r=>{{const cp=r.clone();caches.open(C).then(c=>c.put(e.request,cp));return r}}).catch(()=>caches.match(e.request).then(m=>m||caches.match('index.html'))));
}});
""")
json.dump({"asOf":asof,"asOfIso":run,"count":len(data),"entries":data},open(f"{out}/latest.json","w",encoding="utf-8"),ensure_ascii=False,separators=(",",":"))
open(f"{out}/_headers","w").write("/sw.js\n  Cache-Control: no-cache\n/latest.json\n  Cache-Control: no-cache\n/index.html\n  Cache-Control: no-cache\n")
from PIL import Image, ImageDraw, ImageFont
for n in (192,512):
    im=Image.new("RGB",(n,n),"#3E1F47"); g=ImageDraw.Draw(im)
    try: f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",int(n*0.30))
    except Exception: f=ImageFont.load_default()
    g.text((n/2,n*0.46),"CME",fill="#ffffff",font=f,anchor="mm")
    g.rounded_rectangle((n*0.28,n*0.68,n*0.72,n*0.72),radius=n*0.02,fill="#E8B84A")
    im.save(f"{out}/icon-{n}.png")
print("pwa built:", out, "entries", len(data), "asOf", asof)
