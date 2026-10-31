# Global CME Calendar build kit

Source of truth: `../Data/events.csv` (one row per occurrence, 18 columns). Edit rows there, never in the JSX or JSON.
The old inputs (`inputs/merged_cme_master_list_v2.csv`, `inputs/old_calendar_101.jsx`) are no longer used by the build; the pre-change scripts are kept in `scripts/_orig_2026-10-30/`.

## Rebuild (needs Python 3 and Node)
1. One-time: `mkdir -p bundle && cd bundle && npm init -y && npm i react@18.3.1 react-dom@18.3.1 lucide-react@0.263.1 esbuild@0.21.5` (npm prints harmless EPERM cleanup warnings on the device VM).
2. Full build: `bash scripts/assemble.sh <path>/Data/events.csv <this folder> YYYY-MM-DD`
3. Data stage only (no Node): `DATA_ONLY=1 bash scripts/assemble.sh <events.csv> <this folder> YYYY-MM-DD`, or call the script directly: `python3 -I scripts/build_data.py <events.csv> <out_dir> YYYY-MM-DD`

Pass the run date explicitly in scheduled runs (it defaults to the system date). It drives: past/upcoming status, the "Data compiled <date>" text and, in the app, the subtitle year range.
Outputs in `build/`: conferences.json, brevista_conference_calendar.jsx, Global_CME_Calendar.html, hosted_page.html, build_report.txt.

## What build_data.py does
- One CSV row = one entry. Nothing is dropped. The build fails (exit 2, nothing bundled) on: unparseable ISO date, End before Start, unknown Status, specialty not in the approved list, Verification outside {Verified, Checked-not-announced, Unverified, Held}, or entry count != row count. Warnings (dates/URL oddities, possible duplicates) are listed but do not stop the build.
- Specialty: taken from the CSV; the keyword RULES apply only if the cell is blank.
- Status mapping (CSV -> app): Confirmed -> Confirmed; Completed -> Completed; Unverified -> Unverified; Confirmed Cycle (Dates TBA) -> Cycle; Not yet released -> Not yet released; Active/Ongoing -> Ongoing. The CSV value is kept in `status_raw`.
- Run-date rules (each adjustment is listed in build_report.txt): a dated row that ended before the run date becomes Completed; a row labelled Completed whose end date has not passed is re-opened (to its "Original status" note if present, else Unverified, or Confirmed if Verified) and flagged DATA ERROR so the CSV can be fixed; Verification=Verified with Status=Unverified is shown as Confirmed.
- Notes cleaning: drops "Original status", "Status derived", "No official URL", "LOOKAHEAD" and "Previously: ... (date)" change history; drops the stale "From earlier research list" sentence on Verified rows; Unverified rows with no note get "Dates, location and link not yet verified."
- New JSON fields for a later verified badge (UI unchanged): series_id, verification, verified_on, verified_source_url, date_state, status_raw. `verified` still holds the legacy Last_Verified text; `conflict` is always false now.

## Regression test
`python3 -I tests/equivalence_bridge.py "$PWD"` rebuilds the original 284 entries through the new script and compares every field with the original build (`build_test_orig/`). Expected: only `conflict` (7) and one `format` (PAH series) differ.
