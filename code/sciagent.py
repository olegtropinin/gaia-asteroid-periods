#!/usr/bin/env python3
"""Autonomous rotation-period search for asteroids from Gaia DR3 sparse photometry.

Pipeline:
  select   - pick asteroids with the most Gaia observations; split into KNOWN (JPL has a
             rotation period) and UNKNOWN (no period in JPL SBDB).
  fetch    - download Gaia photometry (per transit) and JPL Horizons geometry seen from Gaia.
  analyze  - periodogram: reduced magnitude = season offsets + linear phase term + 2nd-order
             Fourier series in rotational phase; scan P = 2..100 h.
  calibrate- on KNOWN asteroids, measure how often the best period matches JPL, and pick the
             confidence threshold that keeps precision >= TARGET_PRECISION.
  report   - apply the threshold to UNKNOWN asteroids, write results.json.
Everything is cached under ./data so the run can be resumed.
"""
import csv, io, json, math, os, sys, time, urllib.parse, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
GAIA_TAP = "https://gea.esac.esa.int/tap-server/tap/sync"
HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
SBDB_QUERY = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
GAIA_EPOCH0 = 2455197.5          # Gaia DR3 SSO epochs are JD - 2455197.5
LIGHT_DAY_PER_AU = 0.0057755183  # light time, days per au
P_MIN_H, P_MAX_H = 2.0, 100.0
MIN_TRANSITS = 25
MATCH_TOL = 0.03                 # |P - P_known| / P_known counted as a match
TARGET_PRECISION = 0.8
ERR_FLOOR = 0.03
DOUBLE_TOL = 1.25             # take 2P when chi2(2P) < DOUBLE_TOL * chi2(P): most lightcurves are double-peaked
UA = {"User-Agent": "sciagent/0.1 (home research prototype)"}


def http(url, data=None, timeout=120, tries=4):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode()
        except Exception as e:  # network hiccups: back off and retry
            if k == tries - 1:
                raise
            time.sleep(5 * (k + 1))


def gaia(query):
    body = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query}).encode()
    return list(csv.DictReader(io.StringIO(http(GAIA_TAP, body, timeout=300))))


def path(*p):
    full = os.path.join(DATA, *p)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    return full


def log(msg):
    line = time.strftime("%H:%M:%S ") + msg
    print(line, flush=True)
    with open(path("run.log"), "a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------- select
def select(n_known=300, n_unknown=300, pool=6000):
    known_file = path("sbdb_known_periods.json")
    if not os.path.exists(known_file):
        q = {"fields": "spkid,pdes,full_name,rot_per", "sb-ns": "n", "sb-cdata": json.dumps({"AND": ["rot_per|DF"]})}
        d = json.loads(http(SBDB_QUERY + "?" + urllib.parse.urlencode(q), timeout=300))
        json.dump(d, open(known_file, "w"))
    d = json.load(open(known_file))
    known = {}
    for spkid, pdes, name, rot in d["data"]:
        try:
            known[int(pdes)] = (float(rot), name.strip())
        except (TypeError, ValueError):
            pass
    log(f"select: JPL has rotation periods for {len(known)} numbered asteroids")
    top = gaia(f"SELECT TOP {pool} number_mp, denomination, num_of_obs FROM gaiadr3.sso_source "
               f"WHERE number_mp IS NOT NULL ORDER BY num_of_obs DESC")
    k_sel, u_sel = [], []
    for r in top:
        n = int(r["number_mp"])
        row = {"num": n, "name": r["denomination"], "gaia_obs": int(r["num_of_obs"])}
        if n in known:
            p = known[n][0]
            if P_MIN_H <= p <= P_MAX_H and len(k_sel) < n_known:
                k_sel.append({**row, "p_known": p, "full_name": known[n][1]})
        elif len(u_sel) < n_unknown:
            u_sel.append(row)
    # Always include the two asteroids the home BOINC client is working on.
    for n in (174502, 174641):
        if n not in {r["num"] for r in u_sel}:
            u_sel.append({"num": n, "name": "", "gaia_obs": None, "boinc": True})
    json.dump({"known": k_sel, "unknown": u_sel}, open(path("selection.json"), "w"), indent=1)
    log(f"select: {len(k_sel)} known + {len(u_sel)} unknown chosen from the {pool} best-observed")


# ---------------------------------------------------------------- fetch
def fetch_one(num):
    out = path("obs", f"{num}.json")
    if os.path.exists(out):
        return json.load(open(out))
    rows = gaia(f"SELECT transit_id, epoch, g_mag, g_flux, g_flux_error FROM gaiadr3.sso_observation WHERE number_mp={num}")
    tr = {}
    for r in rows:
        if not r["g_mag"] or not r["g_flux"]:
            continue
        t = tr.setdefault(r["transit_id"], [])
        t.append((float(r["epoch"]), float(r["g_mag"]), float(r["g_flux"]), float(r["g_flux_error"] or 0)))
    obs = []
    for t in tr.values():
        ep = sum(x[0] for x in t) / len(t)
        mag = sum(x[1] for x in t) / len(t)
        rel = max((x[3] / x[2]) for x in t if x[2] > 0)
        obs.append([ep + GAIA_EPOCH0, mag, math.hypot(1.0857 * rel, ERR_FLOOR)])
    obs.sort()
    geo = []
    if len(obs) >= MIN_TRANSITS:
        for a in range(0, len(obs), 50):  # Horizons returns at most 80 epochs per TLIST request
            tl = " ".join(f"{o[0]:.6f}" for o in obs[a:a + 50])
            q = {"format": "json", "COMMAND": f"{num};", "EPHEM_TYPE": "OBSERVER", "CENTER": "500@-139479",
                 "TLIST": tl, "TLIST_TYPE": "JD", "QUANTITIES": "19,20,43", "CSV_FORMAT": "YES", "ANG_FORMAT": "DEG"}
            res = json.loads(http(HORIZONS, urllib.parse.urlencode(q).encode(), timeout=180)).get("result", "")
            if "$$SOE" in res:
                body = res.split("$$SOE")[1].split("$$EOE")[0]
                for line in body.strip().splitlines():
                    c = [x.strip() for x in line.split(",")]
                    geo.append([float(c[3]), float(c[5]), float(c[7]), float(c[8]), float(c[9])])  # r, delta, phase, PAB lon, lat
            time.sleep(1)  # be polite to Horizons
    rec = {"num": num, "obs": obs, "geo": geo}
    json.dump(rec, open(out, "w"))
    return rec


def fetch():
    sel = json.load(open(path("selection.json")))
    todo = sel["known"] + sel["unknown"]
    for i, r in enumerate(todo, 1):
        try:
            rec = fetch_one(r["num"])
            if i % 25 == 0 or i == len(todo):
                log(f"fetch: {i}/{len(todo)} (last {r['num']}: {len(rec['obs'])} transits, geometry {len(rec['geo'])})")
        except Exception as e:
            log(f"fetch: {r['num']} failed: {e}")


# ---------------------------------------------------------------- analyze
def periodogram(rec):
    obs, geo = np.array(rec["obs"]), np.array(rec["geo"])
    if len(obs) < MIN_TRANSITS or len(geo) != len(obs):
        return None
    r, delta, alpha = geo[:, 0], geo[:, 1], geo[:, 2]
    t = obs[:, 0] - delta * LIGHT_DAY_PER_AU       # light-time corrected
    y = obs[:, 1] - 5 * np.log10(r * delta)         # reduced magnitude
    w = 1 / obs[:, 2] ** 2
    # Robust clip of gross outliers against a simple phase-curve fit
    season = np.concatenate([[0], np.cumsum(np.diff(t) > 60)])
    S = np.eye(season.max() + 1)[season]
    base = np.column_stack([S, alpha])
    for _ in range(2):
        coef, *_ = np.linalg.lstsq(base * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)
        res = y - base @ coef
        mad = np.median(np.abs(res - np.median(res))) * 1.4826 + 1e-3
        keep = np.abs(res) < 5 * mad
        if keep.all():
            break
        t, y, w, alpha, base, S = t[keep], y[keep], w[keep], alpha[keep], base[keep], S[keep]
    n = len(t)
    if n < MIN_TRANSITS:
        return None
    chi_null = float(np.sum(w * (y - base @ np.linalg.lstsq(base * np.sqrt(w)[:, None], y * np.sqrt(w), rcond=None)[0]) ** 2))
    span = t.max() - t.min()
    df = 0.1 / span
    freqs = np.arange(24 / P_MAX_H, 24 / P_MIN_H, df)   # rotations per day
    chi = np.empty(len(freqs))
    sw = np.sqrt(w)
    for a in range(0, len(freqs), 4000):
        f = freqs[a:a + 4000]
        ph = 2 * np.pi * np.outer(f, t)                   # (F, N)
        cols = [np.broadcast_to(base, (len(f),) + base.shape)]
        cols += [np.cos(ph)[..., None], np.sin(ph)[..., None], np.cos(2 * ph)[..., None], np.sin(2 * ph)[..., None]]
        A = np.concatenate(cols, axis=2) * sw[None, :, None]
        b = y * sw
        AtA = np.einsum("fni,fnj->fij", A, A) + 1e-9 * np.eye(A.shape[2])
        Atb = np.einsum("fni,n->fi", A, b)
        x = np.linalg.solve(AtA, Atb[..., None])[..., 0]
        chi[a:a + 4000] = np.sum((np.einsum("fni,fi->fn", A, x) - b) ** 2, axis=1)
    def fit(f):
        ph = 2 * np.pi * f * t
        A = np.column_stack([base, np.cos(ph), np.sin(ph), np.cos(2 * ph), np.sin(2 * ph)])
        x = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)[0]
        return float(np.sum(w * (y - A @ x) ** 2)), x

    i = int(np.argmin(chi))
    f_best, chi_b = float(freqs[i]), float(chi[i])
    chi_double = fit(f_best / 2)[0]
    doubled = f_best / 2 >= freqs[0] and chi_double < DOUBLE_TOL * chi_b
    if doubled:
        f_best = f_best / 2
    # Second-best independent peak: away from the best frequency and its x2 / x0.5 aliases
    mask = np.ones(len(freqs), bool)
    for g in (f_best, 2 * f_best, f_best / 2):
        mask &= np.abs(freqs - g) > 5 / span
    j = int(np.argmin(np.where(mask, chi, np.inf)))
    dof = n - (base.shape[1] + 4)
    chi_at_best, x = fit(f_best)
    grid = np.linspace(0, 2 * np.pi, 200)
    four = x[-4] * np.cos(grid) + x[-3] * np.sin(grid) + x[-2] * np.cos(2 * grid) + x[-1] * np.sin(2 * grid)
    # Store a decimated periodogram for plotting
    step = max(1, len(freqs) // 1500)
    pg = [[round(24 / float(freqs[k]), 5), round(float(chi[k] / chi_null), 5)] for k in range(0, len(freqs), step)]
    return {"n": n, "seasons": int(S.shape[1]), "span_d": round(span, 1), "p_best": 24 / f_best, "p_second": 24 / freqs[j],
            "p_peak": 24 / float(freqs[i]), "doubled": bool(doubled), "double_ratio": chi_double / chi_b,
            "chi_null": chi_null, "chi_best": chi_b, "chi_second": float(chi[j]),
            "gain": chi_null / chi_b, "unique": float(chi[j] / chi_b), "rchi2": float(chi_b / max(dof, 1)),
            "amp": float(four.max() - four.min()), "pg": pg}


def analyze():
    sel = json.load(open(path("selection.json")))
    for group in ("known", "unknown"):
        for i, r in enumerate(sel[group], 1):
            out = path("pg", f"{r['num']}.json")
            if os.path.exists(out):
                continue
            src = path("obs", f"{r['num']}.json")
            if not os.path.exists(src):
                continue
            t0 = time.time()
            res = periodogram(json.load(open(src)))
            json.dump(res, open(out, "w"))
            if i % 25 == 0:
                log(f"analyze {group}: {i}/{len(sel[group])} ({time.time() - t0:.1f}s each)")


# ---------------------------------------------------------------- calibrate + report
def classify(p, pk):
    for k, label in ((1, "match"), (2, "double"), (0.5, "half")):
        if abs(p - pk * k) / (pk * k) < MATCH_TOL:
            return label
    return "miss"


def score(res):
    # Confidence: how much the rotation model beats the no-rotation model, times peak uniqueness
    return math.log(res["gain"]) * (res["unique"] - 1)


def final_period(res, tol):
    return res["p_peak"] * 2 if res["double_ratio"] < tol and res["p_peak"] * 2 <= P_MAX_H else res["p_peak"]


def tune_double_tol(rows):
    """Pick the doubling tolerance with 2-fold cross-validation on the KNOWN set.
    Returns the tolerance fitted on all rows and the held-out match rate (honest accuracy)."""
    grid = [1.0 + 0.05 * k for k in range(41)]           # 1.00 .. 3.00
    def best(sub):
        return max(grid, key=lambda g: sum(classify(final_period(r, g), r["p_known"]) == "match" for r in sub))
    a, b = rows[0::2], rows[1::2]
    held = sum(classify(final_period(r, best(a)), r["p_known"]) == "match" for r in b) + \
           sum(classify(final_period(r, best(b)), r["p_known"]) == "match" for r in a)
    return best(rows), held / max(len(rows), 1)


def calibrate_and_report():
    sel = json.load(open(path("selection.json")))
    raw = []
    for r in sel["known"]:
        f = path("pg", f"{r['num']}.json")
        res = json.load(open(f)) if os.path.exists(f) else None
        if res:
            raw.append({**r, **{k: v for k, v in res.items() if k != "pg"}})
    tol, cv_rate = tune_double_tol(raw)
    log(f"calibrate: doubling tolerance {tol:.2f}, cross-validated match rate {cv_rate:.1%}")
    known = []
    for r in sel["known"]:
        f = path("pg", f"{r['num']}.json")
        res = json.load(open(f)) if os.path.exists(f) else None
        if res:
            res["p_best"] = final_period(res, tol)
            known.append({**r, **{k: v for k, v in res.items() if k != "pg"}, "cls": classify(res["p_best"], r["p_known"]), "score": score(res)})
    known.sort(key=lambda k: -k["score"])
    # Precision curve: among the top-k by score, how many match
    curve, hits, thr = [], 0, None
    for i, k in enumerate(known, 1):
        hits += k["cls"] == "match"
        curve.append([round(k["score"], 4), i, round(hits / i, 3)])
    for s, cnt, prec in curve:
        if prec >= TARGET_PRECISION and cnt >= 10:
            thr = s
    counts = {c: sum(k["cls"] == c for k in known) for c in ("match", "double", "half", "miss")}
    log(f"calibrate: {len(known)} known analysed: {counts}; threshold for precision>={TARGET_PRECISION}: {thr}")
    unknown = []
    for r in sel["unknown"]:
        f = path("pg", f"{r['num']}.json")
        res = json.load(open(f)) if os.path.exists(f) else None
        if res:
            res["p_best"] = final_period(res, tol)
            unknown.append({**r, **res, "score": score(res), "confident": thr is not None and score(res) >= thr})
    unknown.sort(key=lambda u: -u["score"])
    for u in unknown:
        if not u.get("boinc") and not u["confident"]:
            u.pop("pg", None)  # keep periodograms only where they will be shown
    above = [k for k in known if thr is not None and k["score"] >= thr]
    summary = {"generated": time.strftime("%Y-%m-%d %H:%M"), "match_tol": MATCH_TOL, "target_precision": TARGET_PRECISION,
               "double_tol": tol, "cv_match_rate": round(cv_rate, 3),
               "threshold": thr, "known_counts": counts, "known_n": len(known),
               "known_above": len(above), "known_above_match": sum(k["cls"] == "match" for k in above),
               "unknown_n": len(unknown), "unknown_confident": sum(u["confident"] for u in unknown)}
    json.dump({"summary": summary, "curve": curve, "known": known, "unknown": unknown}, open(path("results.json"), "w"))
    log(f"report: {summary}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("select", "all") and not os.path.exists(path("selection.json")):
        select()
    if cmd in ("fetch", "all"):
        fetch()
    if cmd in ("analyze", "all"):
        analyze()
    if cmd in ("report", "all"):
        calibrate_and_report()
