---
name: cme-calendar-monthly-update
description: Monthly update of Dr. Mistry's Global CME Calendar. Verifies every conference series against its official page, discovers new meetings, applies the pruning rules, writes a change report, and rebuilds and republishes the calendar. Use when asked to update, refresh or trial-run the CME calendar, or when the monthly scheduled task fires.
---

# Global CME Calendar: Monthly Update Protocol (v0.2, post-pilot)

This protocol runs in a fresh session with no memory of earlier chats. Everything needed is in this file and in the data files it names. Follow it in order. Do not improvise around a failed gate; hold the item and report it.

## 0. Principles

1. **Accuracy over coverage.** A missing meeting is a gap. A wrong date or a wrongly deleted meeting is an error. Prefer a gap.
2. **The official page wins.** Only the organizer's own page (society, university, hospital, or the named organizer's domain) can set a date, city or status to Verified. Aggregators, listing sites and social posts may only produce an Unverified lead.
3. **Never invent.** If a date, city or URL is not on a page you read this run, leave the field as it was and record "checked, not found".
4. **Every change is traceable.** Each change carries old value, new value, source URL and date checked.
5. **Destructive actions are conservative.** Ambiguous matches are kept and flagged, never auto-merged or deleted.
6. **Paraphrase.** Do not copy long passages from conference sites into notes. Facts (name, dates, city, URL) only.

## 1. Inputs and storage

Locate these in the connected folder "CME Calendar" (or the Project docs copy if the folder is not reachable). If neither is reachable, stop and report; never rebuild from memory.

| File | Role |
|---|---|
| `events.csv` | Upcoming events only, one row per occurrence (master list columns plus the additions in section 2) |
| `registry.csv` | One row per recurring series (section 2) |
| `scripts/` (build kit) | `build_data.py`, `calendar_template.jsx`, `assemble.sh` |
| `runs/YYYY-MM-DD_report.md` | Output of each run (section 9) |

Run parameters (state them at the top of the report):
- `TODAY`: the current date from the clock tool, not from memory.
- `WINDOW`: TODAY to TODAY + 12 months (the verified target).
- `LOOKAHEAD`: TODAY + 18 months (record early announcements; do not require them).
- `SCOPE`: `full`, or a list of specialties for a pilot.

## 2. Data model

### events.csv
Keep the master columns unchanged: Conference, Society, Start_Date, End_Date, Dates_Text, Location, Official_URL, Status, Last_Verified, Notes, Source, Conflict_Flag.
Add: `Series_ID`, `Specialty`, `Date_State` (Exact / Month-only / Not announced / Ongoing), `Verification` (Verified / Checked-not-announced / Unverified / Held). `Unverified` also covers "page silent": stored dates exist but the official page does not mention that edition (record in Notes, do not use Checked-not-announced), `Verified_On` (ISO date), `Verified_Source_URL`.
Do not rename existing Status values; the build scripts depend on them.

### registry.csv
`Series_ID, Name, Society, Specialty, Official_URL, URL_Status (ok / redirect / dead / missing), Cadence (annual / biennial / irregular / ongoing), Usual_Month, Last_Confirmed_Start, Last_Confirmed_End, Last_Confirmed_City, Last_Checked, Check_Result, Discontinued_Flag, Notes`

### Series_ID rules
Lowercase slug, hyphens, society or organizer plus meeting, no year, no city. Examples: `esc-congress`, `easd-annual`, `hms-update-hospital-medicine`. On a collision, prefix the society. IDs never change once assigned. Different city in a different year is the same series.

### Specialty
Use only the approved labels: Anesthesiology, Cardiology, Critical Care, Endocrinology, Family Medicine, Functional Medicine, Gastroenterology, Geriatrics, Geriatric Psychiatry, Hepatology, Hospital Medicine, Infectious Disease, Internal Medicine, Lifestyle Medicine, Longevity Medicine, Nephrology, Neurology, Neurosurgery, OB/GYN, Obesity Medicine, Oncology, Palliative Care, Psychiatry, Pulmonology, Radiology, Rheumatology, Sports Medicine, Urology, Vascular Surgery, plus Allergy & Immunology, Emergency Medicine, Hematology, Pediatrics. A new label is never created by this run; list the event under "Held: needs decision".

## 3. Inclusion and exclusion

Include any relevant CME meeting run by a society, university, hospital system, or a recognized CME organizer, including industry-supported ones where the program is accredited and independently run.

Exclude by default:
- Events run by a pharmaceutical, device or supplement company to promote its products.
- Satellite or product symposia held inside another congress.
- Sales events, webinars of under one day, and on-demand-only courses with no live component (the `Ongoing` series already in the master are kept).
- Anything with no official page showing a start date.

Include but flag `commercial organizer` in Notes: for-profit organizers (including CME-travel companies) whose program is otherwise a clinical meeting. Decision 2026-10-30: commercial CME-travel organizers are included. Add as `Unverified` until the organizer's own page has been read.

Audience rule (decision 2026-10-30): nurse, NP/PA and allied-health content is acceptable only if the main audience is physicians (MD). Exclude meetings whose title or page targets NPs/PAs/nurses/allied professionals as the primary audience (for example "Hospital Medicine for NPs & PAs", ACNAP). Exclude echocardiography and sonographer review courses. When the audience is unclear, add as Unverified and note it.

Course catalogues (Mayo, Cleveland, HMS): apply the audience rule per course; add each qualifying course as its own series.

## 4. Step 1: Prepare

1. Read `events.csv` and `registry.csv`. Count rows and statuses. Record in the report.
2. If `SCOPE` is a pilot, restrict steps 2 to 4 to series whose Specialty is in scope. Everything else is carried through unchanged.
3. If `registry.csv` does not exist, stop. Create it first from `events.csv` (one row per series, assigning Series_IDs by the rules above) and report ambiguous groupings for review.

## 5. Step 2: Registry pass

For each in-scope series:

0. **Search before fetch.** WebFetch refuses URLs that have not first appeared in a WebSearch result. For every series run one WebSearch (`<series name> <target year> <organizer domain>`), then fetch the organizer-domain result. Series that share one page (Mayo cveducation catalogue, ESC congresses list, AHA meetings list, SCAI) need only one search and fetch for the group.
1. **Fetch** `Official_URL` with WebFetch (after step 0). If it is missing, dead or redirects to an unrelated site, run one WebSearch for `<series name> <target year>`; accept only a result on the organizer's own domain; set `URL_Status` accordingly and record the new URL as a change.
2. **Target occurrences:** the next occurrence that ends on or after TODAY and within WINDOW; and, for annual series, the following one if it falls within LOOKAHEAD.
3. **Read the page** for that occurrence's start date, end date, city (or Online), and any cancellation or postponement notice. WebFetch returns a model summary, not raw text: for every value you intend to change, re-fetch once with a verbatim-quote prompt ("quote the exact line giving dates and venue") before recording the change.
4. **Classify:**
   - *Verified*: the official page states exact dates and location. Set Start/End, `Verification=Verified`, `Verified_On=TODAY`, `Verified_Source_URL`.
   - *Checked-not-announced*: the official page loads but gives no dates for the target occurrence (only an older year, "save the date", or a month). Record `Verification=Checked-not-announced`, `Verified_On=TODAY`, and the month if stated (`Date_State=Month-only`).
   - *Changed*: the page disagrees with the stored value. Apply per section 8.
   - *Page stale*: the page loads but shows only an older year (e.g. 2022 or 2024 content). Treat as unreachable for this occurrence; try one alternative organizer URL from search; otherwise record `Check_Result=stale page`.
   - *Page silent*: the organizer page is current but does not mention this edition while stored dates exist. Leave data unchanged, `Verification=Unverified`, note it.
   - *Affiliate domain*: dates on an organizer-affiliated site (e.g. tctmd.com for CRF) corroborate but cannot set Verified (rule 0.2). Record in Notes.
   - *Unreachable*: the page failed to load twice. Leave data unchanged, `Check_Result=unreachable`, retry next run.
5. Update the registry row: `Last_Checked`, `Check_Result`, and (when Verified) `Last_Confirmed_*`.

Work through series in batches and write results to disk after each batch so that an interrupted run loses nothing.

## 6. Step 3: Discovery sweep

Purpose: find meetings that are not in the registry.

1. Build a matrix of in-scope specialty × region. Regions: Canada, United States, Europe, Asia-Pacific, Online/global. Full run: all specialties × all regions.
2. For each cell run a WebSearch such as `<specialty> annual meeting <year> <region>` and, for hospital medicine and primary-care-adjacent specialties, also `<specialty> CME conference <region> <year>`. Use the year that falls inside WINDOW.
   Add sub-specialty queries per specialty (pilot recall was 2 of 10 with generic queries): Cardiology: imaging/echo/CT/nuclear, structural and interventional, heart failure, electrophysiology, transplant, preventive, cardio-oncology. Nephrology: dialysis, transplantation, pediatric nephrology, hypertension. Hospital Medicine: perioperative, pediatric hospital medicine, regional hospital medicine conferences, acute medicine.
3. Open each plausible organizer page. A candidate is accepted only if: it is a live meeting (not a past-year archive), the organizer's page states dates and a location, it passes section 3, and it is not already in the registry (match by official domain plus name similarity; when unsure, treat as already present and note it).
4. Add accepted candidates to `events.csv` and `registry.csv` with a new Series_ID, `Source=discovery`, `Verification=Verified` when the organizer's page gave exact dates, otherwise `Unverified`.
5. Log the search count and the number of new meetings per cell. Cells with no yield for two consecutive runs may be sampled less often (report it, do not skip silently).

## 7. Step 4: Quality gates

Every added or changed row must pass all gates. Failures go to "Held".

| Gate | Check |
|---|---|
| G1 | Official_URL is HTTPS and on the organizer's domain, not an aggregator |
| G2 | End_Date is on or after Start_Date; duration is 14 days or less (longer is flagged) |
| G3 | Start year is within the window; year in the name matches the dates |
| G4 | Specialty is on the approved list |
| G5 | Location parses to a city, or is exactly `Online` or `TBA` |
| G6 | No duplicate on Series_ID + year, and none on name + year + location |
| G7 | Month shift: a start more than 5 weeks from the series' Usual_Month is flagged for review (apply only if the official page states it) |
| G5b | Location "Live Online" is normalized to exactly `Online` |
| G8 | **Blast radius:** if more than 10% of in-scope rows would change, or more than 5 rows would be removed, apply no removals, apply only additions and verifications, and put the rest under Held with a note. **Exception:** a one-time baseline cleanup of legacy data may be approved by Dr. Mistry in writing. The cleanup for Hospital Medicine, Cardiology and Nephrology was approved and applied 2026-10-30; other specialties still need their own baseline pass (expect about 12% of legacy rows to need correction, so G8 will trip on the first pass). After a specialty has had its baseline cleanup, G8 applies normally. |

## 8. Step 5: Reconcile, prune and apply

Priority: official page, then previously Verified data, then Unverified data.

- **Verified change** (official page, passes gates): apply automatically. Keep the old value in Notes as `Previously: <value> (<date>)`.
- **Unverified lead** (non-official source): add as `Unverified`; never overwrite a Verified value.
- **Ambiguous or conflicting** (two plausible series, official page unclear, cancelled/postponed): hold, do not change.

**Pruning**
1. An event with `End_Date` before TODAY is removed from `events.csv` only if the registry holds a confirmed successor occurrence for the series, or the series is flagged Discontinued. Otherwise it is kept as Completed and listed in the report; its registry row drives next year's search.
2. Never remove an older occurrence that has not yet ended, even if a newer one is confirmed.
3. When a series has sequential-year entries, the newest confirmed entry becomes the registry's `Last_Confirmed_*` and the basis for next year's search. A different city does not matter.
4. Series matching: Series_ID first, then official URL and society. Ambiguous matches are kept and flagged.
5. **Discontinued check:** flag a series with no successor 18 months after its last occurrence (24 months if biennial). Remove only after 36 months and only with confirmation.
6. Past events are not archived in `events.csv`. The registry holds what the next search needs.

## 9. Step 6: Report

Write `runs/YYYY-MM-DD_report.md` and also state the headline in chat. Structure:

1. **Executive summary**: scope, TODAY, counts before and after, headline findings, anything needing a decision.
2. **Coverage**: "Verified through <latest date with Verified status>", count Verified / Checked-not-announced / Unverified / Held within WINDOW, and the percentage of in-window series with a Verified or Checked-not-announced status dated within this run.
3. **Changes**: tables for Added, Changed (old → new, source), Removed (reason), each with source URLs.
4. **Held / needs decision**: every held item with the reason and what would resolve it.
5. **Cost and performance**: wall-clock time, searches, page fetches, series checked per hour, series unreachable.
6. **Misses check** (pilot): see section 11.
7. **Next steps.**

## 10. Step 7: Rebuild and republish

Preconditions: gates passed; report written.

1. The scripts currently hard-code the run date (`TODAY` in `build_data.py`, `__ASOF__` in `assemble.sh`). Before the first scheduled run, change both to take the date as a parameter. Until then, do not run a rebuild on any other day without editing them.
2. Run `assemble.sh` against the updated master CSV. The earlier-only entries must have been folded into the master first, so the build no longer depends on the old 101-entry JSX.
3. Check `build_report.txt`: entry count equals `events.csv` rows, no parse failures, no unmapped specialties.
4. Publish the hosted page and the standalone HTML by updating the existing artifact in place (same URL), then save the CSV/JSON to the shared data location the phone app will read.
5. If any step fails, leave the previously published version in place and report the failure.

## 11. Pilot mode (first trial run; completed 2026-10-30)

Pilot results (see runs/2026-10-30_report.md): 36 of 65 series Verified, 14 not reached, 10 of 85 rows corrected, misses-check recall 2/10, 10/10 precision re-checks matched, about 1.7 calls per series. Use pilot mode again only for a new specialty batch before its baseline cleanup.

Scope: Hospital Medicine, Cardiology, Nephrology. Purpose: measure, not publish. Do not republish in pilot mode; produce the report and a diff only.

Measure and report:
- Time and tool calls per series checked, and an extrapolated cost for a full run.
- % of series Verified, Checked-not-announced, Unreachable.
- Discovery yield: new meetings found per search, and how many passed section 3.
- **Misses check:** before searching, list 10 real meetings in scope that are not in the data (seed with the Midwest Hospital Medicine Conference). After the run, report how many the sweep found. Low recall means the matrix needs more queries.
- Precision check: spot-check 10 changes against their cited pages.
- Whether nephrology's missing URLs were recoverable.

## 12. Hard rules

- Never delete a row without the rules in section 8.
- Never set Verified from a non-official source.
- Never create a new specialty label.
- Never email, post or share anything. Output is the files, the report and the republished calendar.
- If the clock tool or a data file is unavailable, stop and report.

## 13. Open items (v0.2)

- CRF / TCT-family meetings (TCT Plus regional courses, CRF fellows courses, THT, Complex Coronary Summit): organizer pages on crf.org / tctconference.com did not surface in search. Decide whether tctmd.com and tctconference.com count as the organizer's own domain under rule 0.2.
- Verify all Mayo ce.mayo.edu hospital-medicine rows first in the next run; every one checked in the pilot had a wrong city.
- ACC.27 and UK Kidney Week 2027 remain unconfirmed.
- Build kit: `build_data.py` still reads master.csv and the old JSX; it must read Data/events.csv before the first scheduled rebuild (section 10).
- Storage for scheduled runs (local folder vs Netlify) is undecided.


## 14. Decisions logged 2026-10-30 (baseline apply)
- CRF-family own domains accepted for Verified under rule 0.2: crf.org, tctconference.com, tctmd.com. Not accepted: thtmeeting.com; tct.crfconferences.com unchecked.
- Baseline cleanup applied to all specialties (backup: Data/backup_2026-10-30_pre-baseline/). Held items stay held: ATS/EASL 2028 (beyond LOOKAHEAD), ASGE courses, SSG ERCP/EUS, EHA other meetings, ESCMID 2028 and APLAR (no city), DDW 2027, ASGE-APGED Panama, Mayo NP/PA review, Mayo Sedona lead, TCT Plus Africa (city unconfirmed).
- Discovery searches for metabolic, GI/onc and primary-care cells to be rerun in a fresh turn (search budget).


## 15. Decisions logged 2026-10-30 (verification and held-item pass)
- **Display status:** a row shows Status=Confirmed only when Verification=Verified. Every other dated row must carry Status=Unverified (legacy "Confirmed + Unverified" rows were verified or reset on 2026-10-30; 20 stayed Unverified because organizer pages were unreachable or stale). Never add a row with Status=Confirmed and Verification=Unverified.
- **Unsupported stored dates:** when the organizer page shows only another year, clear the dates, set Status="Not yet released", Verification=Checked-not-announced, Date_State=Not announced, and keep the old values in Audit_Notes as "Previously: ...".
- **Notes columns:** events.csv now has `Audit_Notes` (internal audit trail: sources, quotes, Previously:, audience remarks, process wording) and `Notes` (PUBLIC, shown on the card). Public Notes may be filled only if the event's details are still pending AND the note concerns those pending details (dates, city/venue/format, registration, edition not confirmed); one short plain sentence, no process wording. Otherwise leave Notes empty. Never write audit text to Notes.
- **Verified badge:** the calendar shows a "Verified <date>" badge on every non-past row with Verification=Verified (verified_on drives the date). The footer explains it. Do not set Verified without an organizer-domain quote (rule 0.2).
- **Event-site domains:** a conference's own dedicated site for that edition (e.g. esgedays.org, apdw2026manila.com, itoc-conference.eu) was accepted as organizer domain by the 2026-10-30 pass; revisit if the user objects.
- **Policy questions still open (do not add until decided):** research-oriented meetings with no CME statement (CCRC, AACR Pancreatic, Keystone); congress-organizer/secretariat sites (JES 2027 Naha, ESA-SRB-NZSE 2026 Sydney); press-only commercial meetings (CALM 2027, Next Generation Medicine 2026); MCE Conferences commercial catalogue (53 courses); STFM Conference on Medical Student Education; other EHA meetings.
- **Fetch limits:** WebFetch often refuses organizer URLs not returned by a prior WebSearch, and asco.org, esmo.org, ddw.org, asge.org, a4m.com and several Canadian society sites were unreadable. Use the built-in browser (request_access) for these when the user approves the site.


## 16. Decisions logged 2026-10-30 (policy questions answered)
- Research-oriented meetings with no CME statement are INCLUDED (add as Unverified when the audience is unclear): CCRC, AACR Pancreatic Cancer, Keystone Symposia.
- Congress-organizer, secretariat (PCO) and host-committee microsites for the named event ARE accepted as organizer source under rule 0.2 (JES 2027 microsite, ASN Events for ESA-SRB-NZSE).
- Press-only meetings may be added as Unverified with the organizer's site as Official_URL and the press source recorded in Audit_Notes (CALM 2027, Next Generation Medicine 2026).
- EXCLUDED by decision, do not re-surface: MCE Conferences commercial catalogue (53 courses), STFM Conference on Medical Student Education.
- EHA (European Hematology Association) non-congress meetings: decision pending (see handover v8).
- Built-in browser access approved for asco.org, esmo.org, ddw.org, asge.org, a4m.com.


## 17. Built-in browser verification recipe (2026-10-30)
For JS-rendered organizer sites (esmo.org, asco.org, ddw.org, asge.org, a4m.com): request_access (scope once; approval is per page load) -> open an own tab with preview_start -> javascript_tool: wait ~3.5 s, then read document.title, meta description, document.body.innerText and Event JSON-LD. get_page_text alone returns only the footer. The ESMO/ASCO/DDW/ASGE/A4M domains are approved by the user for this. Repeated series use the SAME Series_ID across years (no year suffix). New A4M, ESMO and ASCO meetings found this way were added as Verified when the organizer page stated exact dates and city.


## 18. Decisions logged 2026-10-30 (final pass)
- NOT added by decision: the five non-congress EHA meetings (LATAM tutorial Santiago, Hemoglobinopathies preceptorships Athens/Verona, SWG Integrated Diagnostics Nice, SWG Iron and Erythropoiesis Prague); ASGE-SOBED Postgraduate Course (removed). Along with MCE catalogue and STFM (section 16) these are standing exclusions.
- Kept by decision: four A4M meetings (BHRT x2, IV Therapy, Women's Health Summit), filed under Longevity Medicine, commercial organizer.
- Browser-verified domains now approved for read-only verification: esmo.org, asco.org, ddw.org, asge.org, a4m.com, diabetes.org, pgcourse.org, gastro.org, obesityweek.org, anzsn.org.au, anzsnasm.com, nephrology.edu.au, ukkw.org, ukkidney.org, caepconference.ca, caep.ca, canadianconferenceondementia.org, canadiangeriatrics.ca, crf.org, tctmd.com, tctconference.com. Approval is per page load: request_access before each navigate.
- When an organizer page lists no edition for the stored year, clear the stored dates (Not yet released, Checked-not-announced) and put a public note "Dates not yet announced by the organizer." Used for ADA Advanced Postgraduate Course and AGA-ASGE Postgraduate Course 2027.


## 19. Decisions logged 2026-10-30 (late: removals and holds)
- New approved specialty label (explicit user exception to section 2 and rule 12): **Cardiothoracic Surgery**. Added to APPROVED in scripts/build_data.py. Filed under it: AATS 2027, STS 2027, ISMICS 2027. Surgeon-audience meetings are acceptable when they carry accredited CME or are research meetings.
- Standing removals (do not re-surface): Endocrine Society Center on Obesity Launch, Mayo IM Review for NPs/PAs/Primary, SCOPE Live/World Obesity placeholder, Gastroenterology/Hepatology/Digestive Diseases Summit placeholder, Cleveland Hospital Medicine Summit OnDemand, PAH M&M series, ASGE & Central American Postgraduate Course (Aug 2026, past, no successor).
- Audience rule applied: a course whose page lists athletic trainers/PTs first but is physician-led (MD faculty, AMA PRA Cat 1, MD fee tier) is KEPT (Mayo Sports Medicine Summit 2027, Verified).
- When an organizer page contradicts itself on dates, add the occurrence as Unverified using the structured fields and a public note 'Dates to be confirmed by the organizer.' (Mayo Care of the Older Adult 2027: Nov 15-19, Wailea).
