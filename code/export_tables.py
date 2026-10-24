"""Write the published CSV tables from sciagent results and the novelty checks.

Usage: export_tables.py <work dir with results.json, candidates68.json, novelty files> <repo data dir>
"""
import csv, json, os, sys

work, out = sys.argv[1:3]
res = json.load(open(os.path.join(work, "results.json")))
cand = json.load(open(os.path.join(work, "candidates68.json")))
published = set(json.load(open(os.path.join(work, "published_vizier.json"))))
mpb = set(json.load(open(os.path.join(work, "mpb_hits.json")))) if os.path.exists(os.path.join(work, "mpb_hits.json")) else set()

# 1) New candidates: confident, not in LCDB (Oct 2023 via JPL), Durech & Hanus 2023, DAMIT, VizieR catalogs or MPB 2023-2026
rows = [c for c in cand if str(c["num"]) not in published and str(c["num"]) not in mpb]
with open(os.path.join(out, "candidates.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["number", "designation", "period_h", "alias_period_h", "amplitude_mag", "n_transits", "n_seasons", "span_days", "confidence"])
    for c in rows:
        w.writerow([c["num"], c["name"], f"{c['p_best']:.5f}", f"{c['p_second']:.5f}", f"{c['amp']:.2f}", c["n"], c["seasons"], f"{c['span_d']:.0f}", f"{c['score']:.3f}"])

# 2) Validation set: asteroids with JPL/LCDB periods
with open(os.path.join(out, "validation_known.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["number", "designation", "period_known_h", "period_found_h", "result", "confidence", "above_threshold"])
    thr = res["summary"]["threshold"]
    for k in res["known"]:
        w.writerow([k["num"], k.get("name", ""), k["p_known"], f"{k['p_best']:.5f}", k["cls"], f"{k['score']:.3f}", k["score"] >= thr])

# 3) Candidates later found in the literature: an independent accuracy check
lit = json.load(open(os.path.join(work, "novelty_vizier.json")))["hits"]
idcol = {"J/A+A/687/A277/tablea1": ("Name", "Prot", "Cellino et al. 2024"), "J/A+A/707/A131/tableb1": ("Number", "Prot", "MacLennan et al. 2026"),
         "J/AJ/166/152/final": ("Object", "Prot", "McNeill et al. 2023"), "J/A+A/688/A50/table3": ("MPC", "Per", "Liberato 2024")}
mine = {str(c["num"]): c for c in cand}
with open(os.path.join(out, "literature_check.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["number", "period_found_h", "period_literature_h", "source", "vizier_table", "relation"])
    for t, (ic, pc, src) in idcol.items():
        for h in lit.get(t, []):
            n = "".join(ch for ch in h[ic] if ch.isdigit())
            if n not in mine:
                continue
            p, q = mine[n]["p_best"], abs(float(h[pc]))
            rel = "agree" if abs(p - q) / q < 0.03 else ("half" if abs(2 * p - q) / q < 0.03 else ("double" if abs(p - 2 * q) / (2 * q) < 0.03 else "differ"))
            w.writerow([n, f"{p:.5f}", q, src, t, rel])
print("candidates:", len(rows), "| excluded as published:", len(cand) - len(rows))
