import csv, sys, re, datetime as dt, collections
from urllib.parse import urlparse
root = sys.argv[1]; today = dt.date(2026,10,30); look = dt.date(2028,4,30)
APPROVED = set("""Anesthesiology,Cardiology,Critical Care,Endocrinology,Family Medicine,Functional Medicine,Gastroenterology,Geriatrics,Geriatric Psychiatry,Hepatology,Hospital Medicine,Infectious Disease,Internal Medicine,Lifestyle Medicine,Longevity Medicine,Nephrology,Neurology,Neurosurgery,OB/GYN,Obesity Medicine,Oncology,Palliative Care,Psychiatry,Pulmonology,Radiology,Rheumatology,Sports Medicine,Urology,Vascular Surgery,Allergy & Immunology,Emergency Medicine,Hematology,Pediatrics""".split(","))
VER = {"Verified","Checked-not-announced","Unverified","Held"}
def rd(p): return list(csv.DictReader(open(p, encoding="utf-8", newline="")))
ev = rd(f"{root}/Data/events.csv"); reg = rd(f"{root}/Data/registry.csv")
STAT = {r["Status"] for r in ev}
evH = list(ev[0].keys()); regH = list(reg[0].keys())
regids = {r["Series_ID"] for r in reg}
exist_keys = {(r["Series_ID"], (r["Start_Date"] or r["Dates_Text"])[:4]) for r in ev}
exist_nameyr = {(re.sub(r"\W+","",r["Conference"].lower()), (r["Start_Date"] or "")[:4]) for r in ev}
def d(s):
    try: return dt.date.fromisoformat(s)
    except: return None
tot = collections.Counter()
for cell in ("metabolic","gionc","primary"):
    issues = []
    dif = rd(f"{root}/runs/discovery_{cell}_diff.csv"); rdf = rd(f"{root}/runs/discovery_{cell}_registry_diff.csv")
    with open(f"{root}/runs/discovery_{cell}_diff.csv", encoding="utf-8") as f: h = next(csv.reader(f))
    if h != evH: issues.append(f"HEADER events mismatch: {h}")
    with open(f"{root}/runs/discovery_{cell}_registry_diff.csv", encoding="utf-8") as f: h = next(csv.reader(f))
    if h != regH: issues.append(f"HEADER registry mismatch: {h}")
    newids = {r["Series_ID"] for r in rdf}
    for r in rdf:
        if r["Series_ID"] in regids: issues.append(f"registry dup existing: {r['Series_ID']}")
    seen = set()
    for r in dif:
        sid = r["Series_ID"]; tag = f"{sid}|{r['Conference'][:40]}"
        if r["Specialty"] not in APPROVED: issues.append(f"{tag}: specialty {r['Specialty']!r}")
        if r["Status"] not in STAT: issues.append(f"{tag}: status {r['Status']!r}")
        if r["Verification"] not in VER: issues.append(f"{tag}: verification {r['Verification']!r}")
        s, e = d(r["Start_Date"]), d(r["End_Date"])
        if r["Date_State"]=="Exact":
            if not s or not e: issues.append(f"{tag}: exact but unparsed dates")
            else:
                if e < s: issues.append(f"{tag}: end<start")
                if (e-s).days > 13: issues.append(f"{tag}: duration {(e-s).days+1}d")
                if e < today or s > look: issues.append(f"{tag}: outside range {s}..{e}")
        if not urlparse(r["Official_URL"]).scheme == "https": issues.append(f"{tag}: non-https URL {r['Official_URL'][:50]}")
        if r["Verification"]=="Verified" and not (r["Verified_Source_URL"].startswith("https://") and r["Verified_On"]): issues.append(f"{tag}: Verified w/o source/date")
        if r["Verification"]=="Verified" and r["Date_State"]!="Exact": issues.append(f"{tag}: Verified but Date_State {r['Date_State']}")
        if r["Verification"]=="Verified":
            if urlparse(r["Verified_Source_URL"]).netloc.split(".")[-2:] != urlparse(r["Official_URL"]).netloc.split(".")[-2:]: issues.append(f"{tag}: Verified source domain differs from Official_URL ({urlparse(r['Verified_Source_URL']).netloc} vs {urlparse(r['Official_URL']).netloc})")
        loc = r["Location"].strip()
        if not loc: issues.append(f"{tag}: empty location")
        yr = (r["Start_Date"] or r["Dates_Text"])[:4]
        if (sid,yr) in exist_keys: issues.append(f"{tag}: DUP existing Series_ID+year ({yr})")
        if (sid,yr) in seen: issues.append(f"{tag}: DUP within diff")
        seen.add((sid,yr))
        if (re.sub(r"\W+","",r["Conference"].lower()), (r["Start_Date"] or "")[:4]) in exist_nameyr: issues.append(f"{tag}: DUP existing name+year")
        if sid not in newids and sid not in regids: issues.append(f"{tag}: Series_ID in neither registry")
        if re.search(r"(?i)pediatric hospital medicine", r["Conference"]): issues.append(f"{tag}: PHM present!")
    ver = collections.Counter(r["Verification"] for r in dif)
    print(f"== {cell}: {len(dif)} event rows, {len(rdf)} registry rows, {dict(ver)}; issues={len(issues)}")
    for i in issues: print("  -", i)
    tot.update(ver)
print("TOTAL", dict(tot))
