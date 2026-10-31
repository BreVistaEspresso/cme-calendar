#!/usr/bin/env python3
"""One-time bootstrap: master xlsx + build output -> Data/events.csv, Data/registry.csv, Data/registry_review.md
Usage: python3 bootstrap_registry.py <master.xlsx> <conferences.json> <out_dir> <run_date YYYY-MM-DD>
Series are grouped by normalized name. Different series are never auto-merged; near matches go to the review file."""
import json, re, csv, sys, collections, difflib, datetime as dt, urllib.parse as up
import pandas as pd
XLSX, JSON, OUT, RUN = sys.argv[1:5]
J = json.load(open(JSON, encoding="utf-8"))
df = pd.read_excel(XLSX).fillna("")
byname = {x["name"]: x for x in J}
STOP = set("annual meeting conference the of and for in congress".split())

def norm(n):
    n = re.sub(r"\(.*?\)", "", n)
    n = re.sub(r"[®™]", "", n)
    n = re.sub(r"\b20\d\d\b", "", n)
    n = re.sub(r"(?<=[A-Za-z])(20)?2\d\b", "", n)          # ACEP26, LM2026
    n = re.sub(r"\b\d+(st|nd|rd|th)\b", "", n, flags=re.I)
    return re.sub(r"\s+", " ", n).strip(" -–:|").lower()

def slug(n):
    t = [w for w in re.findall(r"[a-z0-9]+", norm(n)) if w not in STOP]
    return "-".join(t[:6]) or "series"

def domain(u):
    return up.urlparse(u).netloc.lower().replace("www.", "") if u else ""

rows = []
for _, r in df.iterrows():
    j = byname[r["Conference"]]
    sd = lambda v: str(v)[:10] if v != "" else ""
    rows.append(dict(Conference=r["Conference"], Society=r["Society"], Start_Date=sd(r["Start_Date"]), End_Date=sd(r["End_Date"]),
        Dates_Text=r["Dates_Text"], Location=r["Location"], Official_URL=r["Official_URL"], Status=r["Status"],
        Last_Verified=r["Last_Verified"], Notes=r["Notes"], Source="Master list v2", Conflict_Flag=r["Conflict_Flag"],
        Specialty=j["specialty"], prec=j["precision"], year=j["year"]))
for j in J:
    if j["source"] != "Earlier research list":
        continue
    rows.append(dict(Conference=j["name"], Society="", Start_Date=j["start"] or "", End_Date=j["end"] or "", Dates_Text=j["dates"],
        Location=j["location"], Official_URL=j["url"], Status=j["status"], Last_Verified="", Notes=j["notes"],
        Source="Earlier research list", Conflict_Flag="", Specialty=j["specialty"], prec=j["precision"], year=j["year"]))

groups = collections.OrderedDict()
for r in rows:
    groups.setdefault(norm(r["Conference"]), []).append(r)
used, sid_of = {}, {}
for k, g in groups.items():
    s = slug(g[0]["Conference"]); base = s; i = 2
    while s in used and used[s] != k:
        s = f"{base}-{i}"; i += 1
    used[s] = k; sid_of[k] = s
    for r in g:
        r["Series_ID"] = s

DS = {"exact": "Exact", "month": "Month-only", "tba": "Not announced", "ongoing": "Ongoing"}
for r in rows:
    r.update(Date_State=DS[r["prec"]], Verification="Unverified", Verified_On="", Verified_Source_URL="")
cols = ["Series_ID", "Conference", "Society", "Specialty", "Start_Date", "End_Date", "Dates_Text", "Date_State", "Location", "Official_URL",
        "Status", "Verification", "Verified_On", "Verified_Source_URL", "Last_Verified", "Notes", "Source", "Conflict_Flag"]
with open(f"{OUT}/events.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader()
    for r in sorted(rows, key=lambda r: (r["Series_ID"], r["Start_Date"] or "9999")):
        w.writerow(r)

reg, multi = [], []
for k, g in groups.items():
    s = sid_of[k]
    exact = sorted([r for r in g if r["Start_Date"]], key=lambda r: r["Start_Date"])
    years = sorted({int(r["year"]) for r in g if r["year"]})
    if any(r["prec"] == "ongoing" for r in g): cad = "ongoing"
    elif len(years) >= 2 and all(b - a == 1 for a, b in zip(years, years[1:])): cad = "annual"
    elif len(years) >= 2 and all(b - a == 2 for a, b in zip(years, years[1:])): cad = "biennial"
    elif len(years) >= 2: cad = "irregular"
    else: cad = "unknown"
    mon = collections.Counter(int(r["Start_Date"][5:7]) for r in exact)
    um = dt.date(2000, mon.most_common(1)[0][0], 1).strftime("%B") if mon else ""
    conf = [r for r in exact if r["Status"] in ("Confirmed", "Active/Ongoing")]
    last = conf[-1] if conf else None
    latest = (exact or g)[-1]
    url = next((r["Official_URL"] for r in reversed(exact or g) if r["Official_URL"]), "")
    doms = sorted({domain(r["Official_URL"]) for r in g if r["Official_URL"]})
    if len(doms) > 1: multi.append((s, doms))
    reg.append(dict(Series_ID=s, Name=re.sub(r"\s+", " ", re.sub(r"\b20\d\d\b", "", latest["Conference"])).strip(" -–:"),
        Society=next((r["Society"] for r in g if r["Society"]), ""), Specialty=latest["Specialty"], Official_URL=url,
        URL_Status="missing" if not url else "unchecked", Cadence=cad, Usual_Month=um,
        Last_Confirmed_Start=last["Start_Date"] if last else "", Last_Confirmed_End=last["End_Date"] if last else "",
        Last_Confirmed_City=last["Location"] if last else "", Last_Checked="", Check_Result="not yet checked by protocol",
        Discontinued_Flag="", Notes=("multiple URL domains: " + ", ".join(doms)) if len(doms) > 1 else "", Occurrences=len(g)))
with open(f"{OUT}/registry.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(reg[0].keys())); w.writeheader(); w.writerows(reg)

# review: near-duplicate series names (never auto-merged)
ids = [r["Series_ID"] for r in reg]; near = []
for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        a, b = ids[i], ids[j]
        if difflib.SequenceMatcher(None, a, b).ratio() >= 0.88:
            near.append((a, b, reg[i]["Official_URL"], reg[j]["Official_URL"]))
with open(f"{OUT}/registry_review.md", "w", encoding="utf-8") as f:
    f.write(f"# Registry bootstrap review ({RUN})\n\n{len(rows)} events -> {len(reg)} series. Nothing below was merged automatically.\n\n")
    f.write(f"## Near-duplicate series IDs ({len(near)})\nConfirm whether each pair is one series (merge) or two.\n\n")
    for a, b, ua, ub in near: f.write(f"- `{a}` vs `{b}`  ({ua or 'no URL'} | {ub or 'no URL'})\n")
    f.write(f"\n## Series with more than one URL domain ({len(multi)})\n\n")
    for s, d in multi: f.write(f"- `{s}`: {', '.join(d)}\n")
    f.write(f"\n## Missing data\n- Series with no official URL: {sum(1 for r in reg if not r['Official_URL'])}\n- Series with blank Society: {sum(1 for r in reg if not r['Society'])}\n- Series with unknown cadence (single occurrence): {sum(1 for r in reg if r['Cadence']=='unknown')}\n")
print("events", len(rows), "series", len(reg), "multi-occurrence", sum(1 for r in reg if r["Occurrences"] > 1))
print("cadence", dict(collections.Counter(r["Cadence"] for r in reg)))
print("near-dup pairs", len(near), "| multi-domain", len(multi))
