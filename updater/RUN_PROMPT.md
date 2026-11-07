# Monthly run prompt (standalone; the scheduled session has no other memory)

You are running the monthly update of the Global CME Calendar for Dr. Ritesh Mistry. Dry run was waived by him; this run is FULL AUTO.

1. Clone `https://github.com/BreVistaEspresso/cme-calendar` into /home/claude/cme-calendar (shallow, generous timeout ~10 min; one git operation at a time). Work only inside it. RUN_DATE=$(date +%F); pass it explicitly everywhere.
2. No npm install is needed: the app (Design E, plain JS) has no bundle step. Python 3 only.
3. Follow updater/Protocol/SKILL.md (sections 0-19) with these OVERRIDES: all paths are relative to updater/ (Data/events.csv, Data/registry.csv, build_kit/, runs/); backup Data into updater/Data/backups/<date>/ only if small, otherwise rely on git history; do NOT republish any claude.ai artifact.
4. Enforce gates G1-G8 and rule 8: no deletion without rule 8, no pruning other than the protocol's, no row set Verified without an organizer-domain quote. Prioritize series nearest in date; the WebSearch budget may cut the run short, so say what was skipped. JS-rendered sites cannot be read unattended: those rows stay Unverified.
5. Publish = `DATA_ONLY=1 bash updater/build_kit/scripts/assemble.sh updater/Data/events.csv updater/build_kit $RUN_DATE` then `python3 -I updater/build_kit/scripts/build_site.py updater/build_kit/site_src updater/build_kit/build/conferences.json updater/build_kit/site $RUN_DATE`, then copy the contents of updater/build_kit/site/ (including .nojekyll) to the repo root, commit, push to main. Only do this if build says entries == rows with FAILURES: 0 and all gates passed. Never touch repo-root files outside this step. (Old React/build_pwa.py output is retired; do not run build_pwa.py.)
6. On any failure: push NO site files. Always write updater/runs/$RUN_DATE_report.md (added, changed, removed, held, verified-through coverage, rows unreadable because sites need browser approval, searches used, skipped series, failures) and push it (plus updated Data CSVs only if gates passed).
7. Commit messages end with: Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
