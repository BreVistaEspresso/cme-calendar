# Updater layout
- updater/Data: events.csv (source of truth), registry.csv
- updater/Protocol/SKILL.md: the monthly update protocol (v0.2, sections 0-19)
- updater/build_kit/scripts: assemble.sh (use DATA_ONLY=1), build_data.py, build_site.py (Design E app), build_pwa.py (retired), calendar_template.jsx, validators
- updater/RUN_PROMPT.md: what the monthly scheduled task executes
- updater/runs: one report per run
- updater/build_kit/site_src: Design E app source (index.html, styles.css, app.js, fonts, img, icons)
- Repo root: the published PWA (index.html, styles.css, app.js, sw.js, manifest, icons, fonts/, img/, conferences.json) served by GitHub Pages
Run contract: pass the run date explicitly; publish only when build entries == rows, 0 failures, gates pass.
