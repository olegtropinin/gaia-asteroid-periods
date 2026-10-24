"""Look for the candidate asteroids in every VizieR table that has an id column and a period column in hours."""
import csv, io, json, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = sys.argv[1]
TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"
cand = json.load(open(f"{HERE}/candidates68.json"))
nums = {str(c["num"]) for c in cand}
names = {c["name"].lower().replace(" ", ""): str(c["num"]) for c in cand if c["name"]}


def tap(q):
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "MAXREC": "2000000", "QUERY": q}).encode()
    with urllib.request.urlopen(urllib.request.Request(TAP, data=body), timeout=600) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8", "replace"))))


tables = {}
for row in csv.DictReader(open(f"{HERE}/vizier_pn.csv")):
    t = row["table_name"].strip("'")
    tables.setdefault(t, {"p": set(), "n": set()})
    tables[t]["p"].add(row["pcol"].strip("'"))
    tables[t]["n"].add(row["ncol"].strip("'"))


def check(item):
    t, cols = item
    sel = ", ".join(f'"{c}"' for c in sorted(cols["n"] | cols["p"]))
    try:
        rows = tap(f'SELECT {sel} FROM "{t}"')
    except Exception as e:
        return t, None, f"error: {e}"
    hdr, body = rows[0], rows[1:]
    hits = []
    for r in body:
        rec = dict(zip(hdr, r))
        for c in cols["n"]:
            v = (rec.get(c) or "").strip()
            key = re.sub(r"[()\s]", "", v).lower()
            num = re.match(r"^\(?(\d+)\)?", v)
            if (num and num.group(1) in nums and (len(v) == len(num.group(0)) or not v[len(num.group(0)):].strip().isdigit())) or key in names:
                hits.append({k: rec.get(k) for k in hdr})
                break
    return t, len(body), hits


with ThreadPoolExecutor(4) as ex:
    results = list(ex.map(check, tables.items()))
out = {}
for t, n, hits in results:
    if isinstance(hits, str):
        print(f"{t}: {hits}")
        continue
    if hits:
        out[t] = hits
        print(f"{t} ({n} rows): {len(hits)} hit(s) {hits[:3]}")
json.dump({"tables_checked": len(tables), "errors": [t for t, n, h in results if isinstance(h, str)],
           "rows_scanned": sum(n or 0 for t, n, h in results), "hits": out}, open(f"{HERE}/novelty_vizier.json", "w"), indent=1)
print("tables:", len(tables), "rows scanned:", sum(n or 0 for t, n, h in results), "tables with hits:", len(out))
