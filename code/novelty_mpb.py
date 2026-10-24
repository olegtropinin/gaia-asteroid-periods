import glob, json, re, sys
S = sys.argv[1]
cand = json.load(open(f"{S}/candidates68.json"))
pub = set(json.load(open(f"{S}/published_vizier.json")))
txt = {}
for f in sorted(glob.glob(f"{S}/mpb/*.txt")):
    t = open(f, errors="replace").read()
    if len(t) > 1000:
        txt[f.split("/")[-1][:-4]] = re.sub(r"\s+", " ", t)

def pattern(num, name):
    nm = re.sub(r"\s+", r"\\s*", re.escape(name.strip())) if name else None
    alts = [r"\(\s*" + str(num) + r"\s*\)"]
    if nm:
        alts.append(r"\b" + str(num) + r"\s+" + nm + r"\b")
    return re.compile("|".join(alts), re.I)

control = pattern(665, "Sabine")
print("issues:", len(txt), sorted(txt))
print("control '665 Sabine' found in:", [i for i, t in txt.items() if control.search(t)])
hits = {}
for c in cand:
    p = pattern(c["num"], c["name"])
    for i, t in txt.items():
        if p.search(t):
            hits.setdefault(str(c["num"]), []).append(i)
for n, i in hits.items():
    print("HIT", n, i, "(already excluded via VizieR)" if n in pub else "")
# Loose check for reporting: bare number anywhere (expect false positives)
loose = {str(c["num"]): [i for i, t in txt.items() if re.search(r"\b" + str(c["num"]) + r"\b", t)] for c in cand if str(c["num"]) not in pub}
print("bare-number mentions (for manual review):", {k: v for k, v in loose.items() if v})
json.dump(sorted(n for n in hits if n not in pub), open(f"{S}/mpb_hits.json", "w"))
