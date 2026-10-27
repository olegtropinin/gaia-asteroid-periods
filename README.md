# Candidate rotation periods for 34 main-belt asteroids from Gaia DR3 sparse photometry

**Author:** Oleg Tropynin (independent researcher, Kazakhstan)
**DOI:** [10.5281/zenodo.23624115](https://doi.org/10.5281/zenodo.23624115) (all versions; v1.0.0: [10.5281/zenodo.23624116](https://doi.org/10.5281/zenodo.23624116))  
**Status:** candidates. Not yet confirmed by dense lightcurves (see [Reliability](#reliability)).

**Update v1.3.0 (2026-10-27).** The RNAAS note (AAS82759) was revised at the editor's request so that the
method can be reproduced from the text: the model is written as an equation with its free parameters, and the
averaging, seasons, outlier cut, frequency grid, doubling rule, score and threshold are defined exactly. A table
of the 34 candidates replaces the figure; it also gives each candidate's tier in the full-DR3 analysis
(10.5281/zenodo.23638281): 18 A, 12 B, 4 below. The literature check is corrected to 15 of 25 agreements
(Liberato et al. 2024 give an astrometric wobble period, not a rotation period), so out of sample 96 of 122
(79 %) agree. The candidate list itself is unchanged.

**Update v1.2.0 (2026-10-26).** The list now has 34 candidates. A check against the SsODNet compilation
(Berthier et al. 2023, A&A 671, A151; snapshot of its ssoBFT table) found 11857 (1988 RK9) in Ďurech et al. 2022
(Front. Astron. Space Sci. 9, 809771; ATLAS), which is not in VizieR. Their period, 19.7181 h, agrees with ours
(19.710 h). The candidate is moved to `data/withdrawn_candidates.csv`. The other 34 were not found there.

**Update v1.1.0 (2026-10-25).** The list now has 35 candidates instead of 42.
- A full-DR3 reanalysis with a refined method ([gaia-dr3-rotation-catalog](https://github.com/olegtropinin/gaia-dr3-rotation-catalog), DOI [10.5281/zenodo.23638281](https://doi.org/10.5281/zenodo.23638281)) recovers the same period for all 35 remaining candidates.
- Seven earlier candidates are withdrawn and listed with the reason in `data/withdrawn_candidates.csv`:
  - 7699, 14372, 43014 and 104169 most likely have twice the listed period;
  - for 13686, 39932 and 109412 a slow solution is now preferred, so they are ambiguous.
- The novelty check no longer counts Liberato et al. 2024 as a source of rotation periods, because that table gives astrometric wobble periods. Agreement with the literature is now 16 of 25.

This repository contains rotation-period candidates for 34 numbered main-belt asteroids.
As of October 2026, none of them had a rotation period in any source we checked (listed under
[Novelty check](#novelty-check)). It also contains the code that produced them and the validation
that tells you how far to trust them.

| File | Contents |
|---|---|
| `data/candidates.csv` | The 34 candidates: period, the strongest alternative (alias) period, amplitude, amount of data, confidence score, reliability (high / low) |
| `data/validation_known.csv` | The same method run on 300 asteroids whose periods are already known (JPL SBDB / LCDB) |
| `data/literature_check.csv` | 26 of the original 68 candidates turned out to be published recently; our periods compared with theirs (one row per catalogue match; per asteroid, excluding the Liberato 2024 wobble periods: 16 agree, 5 half, 4 differ) |
| `data/withdrawn_candidates.csv` | The 8 withdrawn candidates (7 in v1.1.0, 1 in v1.2.0), with the reason |
| `code/sciagent.py` | Selection, data download, period search, calibration |
| `code/novelty_*.py`, `code/export_tables.py` | Novelty checks against VizieR and export of the tables |
| `NOTE.md` | Short research note (method, validation, results) |
| `paper/rnaas.tex`, `paper/figure1.*` | Submission version for Research Notes of the AAS (AASTeX 6.3.1) and its figure; `code/make_figure.py` rebuilds the figure |

## Method

1. **Sample.** The 6,000 numbered asteroids with the most Gaia DR3 Solar-System-object observations
   (`gaiadr3.sso_source`, ordered by `num_of_obs`). They are split into asteroids with a rotation period
   in JPL SBDB (validation set, 300 used) and without one (target set, 298 analysed).
2. **Photometry.** `gaiadr3.sso_observation`, averaged per transit. Error = relative flux error
   in quadrature with a 0.03 mag floor.
3. **Geometry.** For every transit, JPL Horizons gives the heliocentric distance *r*, the distance to Gaia Δ
   and the phase angle α, using Gaia as the observer (`CENTER=500@-139479`). Times are corrected for light time.
4. **Model.** Reduced magnitude `G − 5 log10(rΔ)` is fit with: one offset per observing season
   (gap > 60 d) + a linear phase term + a 2nd-order Fourier series in rotational phase. Weighted least squares,
   two rounds of 5·MAD outlier clipping.
5. **Period scan.** P from 2 to 100 h on a frequency grid with step 0.1/T, where T is the time span.
   The minimum χ² gives the period. If doubling the period raises χ² by less than a factor of 1.5, the
   doubled period is taken, because most asteroid lightcurves are double-peaked.
   The factor 1.5 was chosen by 2-fold cross-validation on the validation set.
6. **Confidence.** Score = ln(χ²_null / χ²_best) × (χ²_second / χ²_best − 1). Here χ²_second is the best
   minimum outside the main peak and its ×2 and ×½ aliases. The threshold (0.1604) is the lowest score
   at which precision on the validation set stays ≥ 80 %.

## Reliability

| Test | Result |
|---|---|
| Validation set, 2-fold cross-validated (300 asteroids, JPL periods, match = within 3 %) | **67.7 %** correct (full sample: 203 correct, 12 at half the period, 10 at double, 75 wrong) |
| Validation set, above the confidence threshold (in-sample, optimistic) | 172 / 214 = 80.4 % |
| Independent check 1: target-set asteroids above threshold that Ďurech & Hanuš (2023) solved from the same Gaia data | 81 / 97 = **83.5 %** agree |
| Independent check 2: candidates later found in Cellino et al. 2024, MacLennan et al. 2026, McNeill et al. 2023 and Liberato et al. 2024 | 17 / 26 = **65 %** agree; 5 at half their period; 4 differ |

**Known failure mode:** slow rotators. Three of the four disagreements in check 2 are asteroids
with periods of 214, 818 and about 4,600 h. That is outside the 2–100 h search range, so the method
returned a spurious short period.

**Accuracy depends on the period found.** We pooled every confident result whose true period is known:
the validation set above threshold, the Ďurech & Hanuš overlap and the post-2023 literature overlap,
337 asteroids in total.

| Period found | Correct |
|---|---|
| 2–10 h | 165 / 203 = 81 % |
| 10–30 h | 79 / 89 = 89 % |
| 30–50 h | 15 / 17 = 88 % |
| 50–100 h | 10 / 28 = **36 %** (usually half of the true period) |

`data/candidates.csv` therefore has a `reliability` column:

- `high` (P < 50 h, 30 asteroids): expect about 83 % to be correct;
- `low` (P ≥ 50 h, 4 asteroids): the true period is probably twice the value, or longer.

Use all of them as targets for confirmation, not as final values.

## Novelty check

The candidates are the asteroids that passed the confidence threshold and **do not** appear in any of:

- JPL SBDB `rot_per` (which follows LCDB, revision October 2023);
- LCDB V4.0 summary (PDS, 2021);
- Ďurech & Hanuš 2023, A&A 675, A24 (Gaia DR3 inversion, 8,596 asteroids);
- DAMIT (12,611 asteroids, export of October 2026);
- SsODNet (Berthier et al. 2023), via a snapshot of its ssoBFT table (October 2026); this includes Ďurech et al. 2022 (ATLAS, not in VizieR). The live SsODNet service returned errors on 2026-10-26, so the sources of a few periods in the snapshot could not be traced;
- VizieR, searched twice:
  (a) every table whose columns include an identifier and a period in hours (113 tables, 0.14 million rows);
  (b) every table of 29 asteroid-rotation catalogues (66 tables, 5.0 million rows, periods in any unit).
  These include Cellino et al. 2024, MacLennan et al. 2026, McNeill et al. 2023 (TESS), Vavilov & Carry 2025
  (TESS), Sergeyev et al. (K2), Erasmus et al. 2020 (ATLAS), Ďurech et al. 2018–2020 and Podlewska-Gaca et al. 2021;
- the Minor Planet Bulletin, volumes 50–53 (2023–2026), full text, matched on number + designation.
  No candidate was found (two bare-number matches were checked by hand and are unrelated: NGC 5897 and a period of 2.7699 h).

**Not checked:** papers outside these sources (for example single-object papers in other journals),
the Geneva Observatory (Behrend) lightcurve pages, and ZTF period catalogs not deposited in VizieR.

## Reproduce

```bash
python3 code/sciagent.py all      # downloads Gaia DR3 + Horizons data into ./data, ~1.5 h
```

Requires Python 3.10, numpy and scipy. Network access to the ESA Gaia archive and JPL Horizons is needed.

## Use of AI

The analysis was designed, coded and checked with the help of an AI assistant (Claude, Anthropic),
under the author's direction. The author is responsible for the content.

## Acknowledgements

This work has made use of data from the European Space Agency (ESA) mission *Gaia*
(https://www.cosmos.esa.int/gaia), processed by the Gaia Data Processing and Analysis Consortium (DPAC,
https://www.cosmos.esa.int/web/gaia/dpac/consortium). Funding for the DPAC has been provided by national
institutions, in particular the institutions participating in the Gaia Multilateral Agreement.
It also made use of JPL Horizons and the JPL Small-Body Database, the Asteroid Lightcurve Database (LCDB;
Warner, Harris & Pravec 2009), DAMIT (Ďurech et al. 2010) and the VizieR catalogue access tool, CDS,
Strasbourg, France.

## License

Code: MIT. Data tables: CC BY-SA 4.0 (they are derived from Gaia data, which is released under CC BY-SA 3.0 IGO).
