"""Second pass: scan every table of known asteroid-rotation catalogs (any period unit) for the candidates."""
import csv, io, json, re, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = sys.argv[1]
TAP = "https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync"
cand = json.load(open(f"{HERE}/candidates68.json"))
nums = {str(c["num"]) for c in cand}
names = {c["name"].lower().replace(" ", "").replace("_", ""): str(c["num"]) for c in cand if c["name"]}
ID_COLS = re.compile(r"^(Num|Number|No|MPC|Name|Ast|Asteroid|Object|ID|Desig|Design|SSO|MP|Nb|AstNum|Number_mp|number_mp|Target)$", re.I)
SKIP = re.compile(r"(LCNum|recno|Seq|Ref|Obs|Night|Npts|N$)", re.I)


def tap(q):
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "MAXREC": "3000000", "QUERY": q}).encode()
    with urllib.request.urlopen(urllib.request.Request(TAP, data=body), timeout=900) as r:
        return list(csv.reader(io.StringIO(r.read().decode("utf-8", "replace"))))


cats = set(l.split(",")[0].strip("\"'").rsplit("/", 1)[0] for l in open(f"{HERE}/vizier_ast_period_cols.csv").read().splitlines()[1:])
cats |= {"J/A+A/643/A59", "J/A+A/654/A48", "J/ApJS/247/26", "J/ApJS/241/6", "J/A+A/675/A24", "J/A+A/707/A131", "J/A+A/687/A277",
         "J/AJ/166/152", "J/A+A/693/A66", "J/A+A/703/A302", "J/ApJS/247/13", "J/ApJS/255/4", "J/A+A/631/A2", "J/A+A/617/A57"}
tables = []
for c in sorted(cats):
    for r in tap(f"SELECT table_name FROM TAP_SCHEMA.tables WHERE table_name LIKE '%{c}/%'")[1:]:
        tables.append(r[0].strip("'"))
print("catalogs:", len(cats), "tables:", len(tables), flush=True)


def check(t):
    try:
        # VizieR stores table names wrapped in single quotes ('J/A+A/.../tess'); only LIKE matches them
        pattern = "'%" + t + "_'"   # trailing _ = the closing quote, so tess does not also match tess2
        cols = [r[0] for r in tap("SELECT column_name FROM TAP_SCHEMA.columns WHERE table_name LIKE " + pattern)[1:]]
        cols = [c.strip("'") for c in cols]
        idc = [c for c in cols if ID_COLS.match(c) and not SKIP.search(c)]
        if not idc:
            return t, 0, [], "no id column: " + ",".join(cols[:12])
        per = [c for c in cols if re.match(r"^(Per|Period|Prot|P|Psyn|Psid|Per1)$", c)]
        sel = ", ".join(f'"{c}"' for c in idc + per)
        rows = tap(f'SELECT {sel} FROM "{t}"')
    except Exception as e:
        return t, 0, [], f"error: {e}"
    hdr, body = rows[0], rows[1:]
    hits = []
    for r in body:
        rec = dict(zip(hdr, r))
        for c in idc:
            v = (rec.get(c) or "").strip()
            m = re.match(r"^\(?0*(\d+)\)?(?:\s|$|[A-Za-z])", v + " ")
            key = re.sub(r"[()\s_]", "", v).lower()
            if (m and m.group(1) in nums) or key in names:
                hits.append(rec)
                break
    return t, len(body), hits, ""


with ThreadPoolExecutor(4) as ex:
    res = list(ex.map(check, tables))
out = {t: h for t, n, h, e in res if h}
for t, n, h, e in res:
    if e:
        print(f"  {t}: {e[:120]}")
    elif h:
        print(f"HIT {t} ({n} rows): {h}")
json.dump({"tables": len(tables), "scanned_rows": sum(n for t, n, h, e in res), "skipped": [(t, e) for t, n, h, e in res if e], "hits": out},
          open(f"{HERE}/novelty_catalogs.json", "w"), indent=1)
print("scanned rows:", sum(n for t, n, h, e in res), "tables with hits:", len(out))
