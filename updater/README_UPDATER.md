# Updater layout
- updater/Data: events.csv (source of truth), registry.csv
- updater/Protocol/SKILL.md: the monthly update protocol (v0.2, sections 0-19)
- updater/build_kit/scripts: assemble.sh, build_data.py, build_pwa.py, calendar_template.jsx, validators
- updater/RUN_PROMPT.md: what the monthly scheduled task executes
- updater/runs: one report per run
- Repo root: the published PWA (index.html, app.js, sw.js, manifest, icons, latest.json) served by GitHub Pages
Run contract: pass the run date explicitly; publish only when build entries == rows, 0 failures, gates pass.
