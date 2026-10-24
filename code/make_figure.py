"""Figure 1: period found from Gaia DR3 vs. the period known from other work, for every confident result
that can be checked. Usage: make_figure.py <work dir> <repo dir>"""
import csv, json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

work, repo = sys.argv[1:3]
res = json.load(open(os.path.join(work, "results.json")))
dh = {int(l.split("\t")[0]): float(l.split("\t")[1]) for l in open(os.path.join(work, "durech2023.tsv"))}
pairs = [(k["p_known"], k["p_best"]) for k in res["known"] if k["score"] >= res["summary"]["threshold"]]
pairs += [(dh[u["num"]], u["p_best"]) for u in res["unknown"] if u["confident"] and u["num"] in dh]
seen = set()
for r in csv.DictReader(open(os.path.join(repo, "data", "literature_check.csv"))):
    if r["number"] not in seen:
        seen.add(r["number"])
        pairs.append((float(r["period_literature_h"]), float(r["period_found_h"])))


def kind(known, found):
    if abs(found - known) / known < 0.03:
        return "match"
    if abs(found - known / 2) / (known / 2) < 0.03:
        return "half"
    return "other"


style = {"match": ("#2a78d6", "o", "matches (within 3%)"), "half": ("#eb6834", "s", "half of the known period"), "other": ("#7a8396", "^", "other")}
fig, ax = plt.subplots(figsize=(5.2, 4.6), dpi=200)
for k in ("other", "half", "match"):
    xs = [min(a, 1e4) for a, b in pairs if kind(a, b) == k]
    ys = [b for a, b in pairs if kind(a, b) == k]
    c, m, lab = style[k]
    ax.scatter(xs, ys, s=12, c=c, marker=m, edgecolors="white", linewidths=0.4, label=f"{lab} ({len(xs)})", zorder=3)
ax.plot([2, 100], [2, 100], c="#12161d", lw=0.8, zorder=2)
ax.plot([4, 200], [2, 100], c="#12161d", lw=0.8, ls="--", zorder=2)
ax.axhline(50, c="#7a8396", lw=0.6, ls=":", zorder=1)
ax.text(2.2, 53, "50 h: reliability drops", fontsize=7, color="#4a5263")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(1.8, 1.2e4); ax.set_ylim(1.8, 110)
ax.set_xlabel("Known period (h)"); ax.set_ylabel("Period from Gaia DR3, this work (h)")
ax.legend(fontsize=7, loc="upper left", frameon=False)
ax.grid(alpha=0.25, which="both", lw=0.4)
fig.tight_layout()
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(repo, "paper", f"figure1.{ext}"))
print("points:", len(pairs), {k: sum(kind(a, b) == k for a, b in pairs) for k in style})
