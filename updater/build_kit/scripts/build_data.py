#!/usr/bin/env python3
"""Build conferences.json for the Global CME Calendar from Data/events.csv.

Input  : Data/events.csv, the single source of truth (one row per occurrence, 18 columns).
Policy : - Every CSV row becomes exactly one entry. Nothing is dropped (expired rows stay, marked Completed).
         - Dates beat stale labels: a dated row whose end date is before the run date becomes Completed; a row labelled
           Completed whose end date is still ahead is re-opened (see reconcile_status). Every adjustment is listed in the report.
         - Specialty is read from the CSV and must be an approved label; the keyword RULES are only a fallback for a blank cell.
         - "Online" is its own city value; "TBA" is used when no city is given.
Status : Confirmed->Confirmed, Completed->Completed, Unverified->Unverified, Confirmed Cycle (Dates TBA)->Cycle,
         Not yet released->Not yet released, Active/Ongoing->Ongoing. Any other value is a hard failure.
         Verified rows labelled Unverified are shown as Confirmed (the CSV label is kept in status_raw).
New fields passed to the app (verification and verified_on drive the Verified badge): series_id, verification, verified_on, verified_source_url, date_state, status_raw.
         The older field "verified" still holds the legacy Last_Verified text.
Usage  : python3 build_data.py <events.csv> <out_dir> [YYYY-MM-DD]
         The optional date is the run date; it defaults to the system date. Pass it explicitly in scheduled runs.
Exit   : 0 = ok, 2 = hard validation failure (conferences.json is still written so the failure can be inspected).
"""
import csv, json, re, sys, datetime as dt, collections

if len(sys.argv) < 3:
    sys.exit("usage: build_data.py <events.csv> <out_dir> [YYYY-MM-DD]")
EVENTS, OUT = sys.argv[1], sys.argv[2]
TODAY = dt.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else dt.date.today()
MONTHS = "January February March April May June July August September October November December".split()
MON = {m: i for i, m in enumerate(MONTHS, 1)}
MON3 = {m[:3]: i for i, m in enumerate(MONTHS, 1)}

# ---------------------------------------------------------------- specialty rules
RULES = [
    (r"updates in neurology|neurology for|international stroke|\baan\b|neurolog", "Neurology"),
    (r"hospital medicine|hospital internal medicine|hospitalized patient|hospitalist|bedside medicine|perioperative", "Hospital Medicine"),
    (r"\baans\b|congress of neurological|\bcns annual", "Neurosurgery"),
    (r"asco|esmo|cosa|oncolog|cancer", "Oncology"),
    (r"\bash\b|hematolog|\beha\b|hsanz|blood 20", "Hematology"),
    (r"chest|\bats\b|pulmon|respir|thoracic|pleural", "Pulmonology"),
    (r"advances in cv critical", "Cardiology"),
    (r"resuscitation|critical care|\bsccm\b", "Critical Care"),
    (r"cardiometabolic", "Endocrinology"),
    (r"asge|digestive|\bddw|gastro|\bueg\b|\bbsg\b|\bgut\b|cddw|aga-asge", "Gastroenterology"),
    (r"liver|aasld|easl|\bpilm\b|hepatol", "Hepatology"),
    (r"kidney|\basn\b|anzsn|era congress|nephro|renal", "Nephrology"),
    (r"idweek|infectious", "Infectious Disease"),
    (r"rheumat|acr convergence|acr state-of-the-art", "Rheumatology"),
    (r"endocrin|\bendo\b|\bada\b|easd|diabet", "Endocrinology"),
    (r"acnem", "Functional Medicine"),
    (r"longevity|a4m|hlms|esaam", "Longevity Medicine"),
    (r"lifestyle|aclm|\blm2\d|bslm|elmc", "Lifestyle Medicine"),
    (r"obesity|\boma\b|\beco 20|ukco|anzos|scope", "Obesity Medicine"),
    (r"functional medicine|\bifm\b|aihm|integrative|bsem|ecological|acnem", "Functional Medicine"),
    (r"geriatric psychiatry|\bcagp\b|aagp", "Geriatric Psychiatry"),
    (r"geriatric|\bags\b|eugms|anzsgm|gerontology|dementia", "Geriatrics"),
    (r"palliative|aahpm|hospice", "Palliative Care"),
    (r"psychiatr|\bapa annual|\bcpa\b", "Psychiatry"),
    (r"anesthesi|\basa advance", "Anesthesiology"),
    (r"\bacep|emergency|caep", "Emergency Medicine"),
    (r"\baap\b|pediatric", "Pediatrics"),
    (r"aaaai|allergy", "Allergy & Immunology"),
    (r"aafp|family medicine|wonca|family-centered", "Family Medicine"),
    (r"\bacc\b|\baha\b|\besc\b|ehra|eacvi|eapci|pcr london|europcr|\bhrx\b|hfsa|heart rhythm|\bcrf\b|\btct\b|scai|\btht\b|cardio|heart|ecg|electrocardiography|arrhythmia|aspc|lipid|vascular discovery", "Cardiology"),
    (r"internal medicine|\becim|\bacp\b|pah medical morbidity|review for nps", "Internal Medicine"),
]

def specialty_for(text):
    t = text.lower()
    for rx, label in RULES:
        if re.search(rx, t):
            return label
    return None

# ---------------------------------------------------------------- location -> city
ONLINE_RX = re.compile(r"online|virtual|on-demand|live ?stream|hybrid", re.I)
VENUE_WORDS = re.compile(r"convention|westin|hotel|centre|center|auditorium|hall", re.I)
NOT_CITY = {"australia", "canada", "united states", "united kingdom", "usa", "uk", "location tbd", "not yet released",
            "to be announced", "tbd", "in-person & virtual", "united states / online", "united kingdom / online options"}
CITY_ALIAS = {"washington, d.c.": "Washington, DC", "washington": "Washington, DC", "new york city": "New York",
              "montréal": "Montreal", "snowmass village": "Snowmass", "málaga": "Malaga", "são paulo": "Sao Paulo",
              "london": "London"}

TBD_RX = re.compile(r"^(location\s+)?(tbd|tba|to be (announced|determined)|not yet released|details pending)\b", re.I)

def clean_city(raw):
    s = raw.strip()
    if TBD_RX.match(s):
        return "TBA"
    if s.lower().startswith("in-person"):
        return "TBA"
    base = re.sub(r"\(.*?\)", "", s)
    base = re.split(r"\s*/\s*|\s+&\s+|\s+and\s+Online", base)[0].strip().rstrip(",")
    parts = [p.strip() for p in base.split(",") if p.strip()]
    if not parts:
        return "TBA"
    first = parts[0]
    if VENUE_WORDS.search(first) and len(parts) > 1:
        first = parts[1]
    if first.lower().startswith("the westin ") and len(parts) > 1:
        first = parts[1]
    if first.lower() in NOT_CITY:
        return "TBA"
    if first.lower() == "washington" and len(parts) > 1 and parts[1].lower().replace(".", "") in ("dc", "d c"):
        return "Washington, DC"
    return CITY_ALIAS.get(first.lower(), first)

def location_info(raw):
    low = raw.lower().strip()
    online = bool(ONLINE_RX.search(raw))
    if low in ("online", "virtual", "live online", "online / virtual", "on-demand"):
        return "Online", "Online"
    city = clean_city(raw)
    if city == "TBA":
        return "TBA", ("Hybrid" if low.startswith("in-person") else "TBA")
    return city, ("Hybrid" if online else "In-person")

# ---------------------------------------------------------------- dates
def fmt_range(s, e):
    s_, e_ = dt.date.fromisoformat(s), dt.date.fromisoformat(e)
    m1, m2 = MONTHS[s_.month - 1][:3], MONTHS[e_.month - 1][:3]
    if s_ == e_:
        return f"{m1} {s_.day}, {s_.year}"
    if s_.year != e_.year:
        return f"{m1} {s_.day}, {s_.year} – {m2} {e_.day}, {e_.year}"
    if s_.month == e_.month:
        return f"{m1} {s_.day}–{e_.day}, {s_.year}"
    return f"{m1} {s_.day} – {m2} {e_.day}, {e_.year}"

def month_end(y, m):
    nxt = dt.date(y + (m == 12), (m % 12) + 1, 1)
    return nxt - dt.timedelta(days=1)

def text_dates(txt, name, date_state=""):
    """Return (precision, start, end, year, month, display) for rows without ISO dates."""
    t = txt.strip()
    ym = re.search(r"20\d\d", t) or re.search(r"20\d\d", name)
    year = int(ym.group(0)) if ym else None
    if date_state == "Ongoing" or re.search(r"monthly|enduring", t, re.I):
        return "ongoing", None, None, year, None, "On-demand / ongoing series"
    if re.match(r"(late|mid|early|spring|summer|fall|autumn|winter|spanning|q[1-4]\b)", t, re.I):
        disp = f"{year} · " + (t[0].upper() + t[1:] if "typically" in t.lower() else "dates to be announced")
        disp = re.sub(r"\(typically", "(typically", disp, flags=re.I)
        return "tba", None, None, year, None, disp
    m = re.match(r"([A-Za-z]+) (20\d\d)", t)
    if m and m.group(1) in MON:
        mo, y = MON[m.group(1)], int(m.group(2))
        return "month", dt.date(y, mo, 1).isoformat(), month_end(y, mo).isoformat(), y, mo, f"{m.group(1)} {y} · exact dates to be announced"
    return "tba", None, None, year, None, f"{year} · dates to be announced" if year else "Dates to be announced"


def clean_notes(raw, verification=""):
    """Keep only reader-useful text from the Notes column (internal markers and change history are dropped)."""
    out = []
    for part in [x.strip() for x in raw.split(" | ") if x.strip()]:
        low = part.lower()
        if low.startswith(("original status:", "status derived", "no official url", "original conference cell:", "lookahead")):
            continue
        part = re.sub(r";?\s*Previously:.*?\(\d{4}-\d{2}-\d{2}\)", "", part)  # change history written by the update protocol
        part = re.sub(r"^[;\s]+|[;\s]+$", "", part)
        if verification == "Verified" and part.lower().startswith("from earlier research list"):
            continue  # stale once the organizer page has been read
        part = re.sub(r"^(Core Clinical Updates \(B only\):|Focus:|Description:)\s*", "", part)
        part = re.sub(r"^(Confirmed|Recurring)\.\s*", "", part)
        if part:
            out.append(part)
    return " ".join(out)

# ---------------------------------------------------------------- status mapping
STATUS = {"Confirmed": "Confirmed", "Completed": "Completed", "Unverified": "Unverified",
          "Confirmed Cycle (Dates TBA)": "Cycle", "Not yet released": "Not yet released", "Active/Ongoing": "Ongoing"}
VERIFICATION = {"Verified", "Checked-not-announced", "Unverified", "Held"}
APPROVED = {label for _, label in RULES} | {"OB/GYN", "Radiology", "Sports Medicine", "Urology", "Vascular Surgery", "Cardiothoracic Surgery"}
REQUIRED = ["Series_ID", "Conference", "Society", "Specialty", "Start_Date", "End_Date", "Dates_Text", "Date_State", "Location", "Official_URL",
            "Status", "Verification", "Verified_On", "Verified_Source_URL", "Last_Verified", "Notes", "Source", "Conflict_Flag"]

def status_from_notes(raw):
    """Recover the pre-bootstrap status from an 'Original status:' note (used only when re-opening a wrongly Completed row)."""
    m = re.search(r"Original status:\s*([A-Za-z/ ]+)", raw)
    if not m:
        return None
    s = m.group(1).strip().lower()
    for key, val in (("confirmed cycle", "Cycle"), ("not yet released", "Not yet released"), ("active", "Ongoing"), ("confirmed", "Confirmed")):
        if s.startswith(key):
            return val
    return None

# ---------------------------------------------------------------- load + validate
FAIL, WARN, ADJ = [], [], []
rows = list(csv.DictReader(open(EVENTS, encoding="utf-8-sig", newline="")))
if not rows:
    sys.exit("events.csv has no rows")
absent = [c for c in REQUIRED if c not in rows[0]]
if absent:
    sys.exit(f"events.csv is missing columns: {absent}")

def iso_ok(s):
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None

entries, loc_table, spec_disagree = [], collections.OrderedDict(), []
TODAY_ISO = TODAY.isoformat()

for n, r in enumerate(rows, 2):  # n = spreadsheet line number (header is line 1)
    r = {k: (v or "").strip() for k, v in r.items()}
    name = re.sub(r"\s+", " ", r["Conference"]).strip()
    tag = f"line {n} [{r['Series_ID']}] {name[:60]}"
    if not name:
        FAIL.append(f"{tag}: blank Conference"); continue
    # ---- dates
    ds = r["Date_State"]
    if r["Start_Date"]:
        s, e = r["Start_Date"], r["End_Date"] or r["Start_Date"]
        sd, ed = iso_ok(s), iso_ok(e)
        if not sd or not ed:
            FAIL.append(f"{tag}: unparseable ISO date Start_Date={r['Start_Date']!r} End_Date={r['End_Date']!r}"); continue
        if ed < sd:
            FAIL.append(f"{tag}: End_Date before Start_Date ({s} > {e})")
        prec, year, mo, disp = "exact", sd.year, sd.month, fmt_range(s, e)
        if ds and ds != "Exact":
            WARN.append(f"{tag}: Date_State={ds!r} but ISO dates present; treated as exact")
    else:
        if ds == "Exact":
            WARN.append(f"{tag}: Date_State=Exact but Start_Date blank; parsed from Dates_Text {r['Dates_Text']!r}")
        prec, s, e, year, mo, disp = text_dates(r["Dates_Text"], name, ds)
    # ---- location
    raw_loc = re.sub(r"\s+", " ", r["Location"]).strip()
    city, fmt = location_info(raw_loc)
    is_tbd = bool(TBD_RX.match(raw_loc)) or not raw_loc
    if is_tbd:
        fmt = "TBA"
    if prec == "ongoing" and fmt == "TBA":  # on-demand series with no place; a named city stays In-person/Hybrid (e.g. a recurring M&M series)
        fmt = "Online"
    loc_disp = "Location to be announced" if raw_loc.lower() in ("", "not yet released", "to be announced", "tbd") else raw_loc  # keep detail such as "Location TBD (rotates ...)"
    loc_table.setdefault(raw_loc, (city, fmt))
    # ---- specialty
    spec_csv = r["Specialty"]
    spec_rule = specialty_for(name + " " + r["Society"])
    spec = spec_csv or spec_rule
    if not spec:
        FAIL.append(f"{tag}: unassigned specialty (CSV blank, no rule matches)")
    elif spec not in APPROVED:
        FAIL.append(f"{tag}: specialty {spec!r} is not an approved label")
    if spec_csv and spec_rule and spec_csv != spec_rule:
        spec_disagree.append((name, spec_csv, spec_rule))
    # ---- verification
    ver = r["Verification"]
    if ver not in VERIFICATION:
        FAIL.append(f"{tag}: Verification {ver!r} not one of {sorted(VERIFICATION)}")
    if ver == "Verified":
        if not iso_ok(r["Verified_On"]):
            WARN.append(f"{tag}: Verified but Verified_On={r['Verified_On']!r} is not an ISO date")
        if not r["Verified_Source_URL"].startswith("http"):
            WARN.append(f"{tag}: Verified but Verified_Source_URL is blank or not http(s)")
    elif r["Verified_On"] and not iso_ok(r["Verified_On"]):
        WARN.append(f"{tag}: Verified_On={r['Verified_On']!r} is not an ISO date")
    # ---- status (mapping, then reconcile against the run date)
    raw_status = r["Status"]
    status = STATUS.get(raw_status)
    if status is None:
        FAIL.append(f"{tag}: unknown Status {raw_status!r}"); status = raw_status
    if prec in ("exact", "month") and e:
        past = e < TODAY_ISO
        if past and status != "Completed":
            ADJ.append(f"{tag}: {raw_status!r} -> Completed (ended {e}, before run date)"); status = "Completed"
        elif not past and status == "Completed":
            new = status_from_notes(r["Notes"]) or ("Confirmed" if ver == "Verified" else "Unverified")
            ADJ.append(f"DATA ERROR {tag}: labelled Completed but ends {e} (on/after run date) -> {new}; fix Status in events.csv"); status = new
    if ver == "Verified" and status == "Unverified":
        ADJ.append(f"{tag}: Verification=Verified but Status=Unverified -> Confirmed"); status = "Confirmed"
    if prec == "tba" and year and year < TODAY.year and status != "Completed":
        WARN.append(f"{tag}: undated row for {year} is past the run year but status is {status}")
    # ---- notes
    notes = clean_notes(r["Notes"], ver)
    if status == "Unverified" and not notes:
        notes = "Dates, location and link not yet verified."
    url = r["Official_URL"]
    if url and not url.lower().startswith(("http://", "https://")):
        WARN.append(f"{tag}: Official_URL does not start with http(s): {url[:50]!r}")
    entries.append(dict(name=name, society=r["Society"], specialty=spec, precision=prec, start=s, end=e, year=year, month=mo, dates=disp,
                        location=loc_disp, city=city, format=fmt, url=url, status=status, verified=r["Last_Verified"], notes=notes,
                        conflict=False, source=r["Source"],
                        series_id=r["Series_ID"], verification=ver, verified_on=r["Verified_On"], verified_source_url=r["Verified_Source_URL"],
                        date_state=ds, status_raw=raw_status))

# ---------------------------------------------------------------- duplicates
def dup_report(keyfn, label):
    c = collections.defaultdict(list)
    for x in entries:
        k = keyfn(x)
        if k is not None:
            c[k].append(x["name"])
    for k, v in c.items():
        if len(v) > 1:
            WARN.append(f"possible duplicate ({label}): {k} x{len(v)}")
dup_report(lambda x: (x["name"].lower(), x["start"], x["end"], x["dates"]), "same name+dates")
dup_report(lambda x: (x["series_id"], x["start"]) if x["start"] and x["precision"] == "exact" else None, "same series+start")

# ---------------------------------------------------------------- sort + ids
def sort_key(x):
    if x["precision"] == "exact":
        return (x["start"], 0, x["name"])
    if x["precision"] == "month":
        return (x["end"], 1, x["name"])
    if x["precision"] == "tba":
        return (f"{x['year'] or 9999}-12-31", 2, x["name"])
    return ("9999-12-31", 3, x["name"])

entries.sort(key=sort_key)
for i, x in enumerate(entries, 1):
    x["id"] = i
if len(entries) != len(rows):
    FAIL.append(f"entry count {len(entries)} != events.csv rows {len(rows)}")

# ---------------------------------------------------------------- reports / checks
missing_year = [x["name"] for x in entries if not x["year"]]
print("run date:", TODAY.isoformat())
print("input:", EVENTS)
print("rows in events.csv:", len(rows))
print("entries:", len(entries), "(equals rows)" if len(entries) == len(rows) else "(MISMATCH)")
print("unassigned specialty:", [x["name"] for x in entries if not x["specialty"]])
print("missing year:", missing_year)
print("precision:", dict(collections.Counter(x["precision"] for x in entries)))
print("status:", dict(collections.Counter(x["status"] for x in entries)))
print("status_raw (CSV):", dict(collections.Counter(x["status_raw"] for x in entries)))
print("verification:", dict(collections.Counter(x["verification"] for x in entries)))
print("source:", dict(collections.Counter(x["source"] for x in entries)))
print("format:", dict(collections.Counter(x["format"] for x in entries)))
print("specialties:", dict(sorted(collections.Counter(str(x["specialty"]) for x in entries).items())))
print("cities (%d):" % len({x["city"] for x in entries}), sorted({x["city"] for x in entries}))
print("no url:", sum(1 for x in entries if not x["url"]))
print("not Completed:", sum(1 for x in entries if x["status"] != "Completed"))
print("blank Start_Date rows:", sum(1 for x in entries if x["precision"] != "exact"),
      dict(collections.Counter(x["precision"] for x in entries if x["precision"] != "exact")))
print("locations -> (city, format), %d distinct:" % len(loc_table))
for raw, (c, f) in loc_table.items():
    print(f"   {raw!r:70} -> {c!r}, {f}")
print("CSV specialty differs from keyword rules (CSV wins): %d" % len(spec_disagree))
for nm, a, b in spec_disagree:
    print(f"   {nm[:70]}: CSV={a} rule={b}")
print("status adjustments against run date: %d" % len(ADJ))
for a in ADJ:
    print("   ", a)
print("warnings: %d" % len(WARN))
for w in WARN:
    print("   ", w)
print("FAILURES: %d" % len(FAIL))
for f in FAIL:
    print("   ", f)
json.dump(entries, open(f"{OUT}/conferences.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if FAIL:
    sys.exit(2)
