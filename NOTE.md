> **Superseded.** This is the original draft (42 candidates). The current note is `paper/rnaas.tex` (v3, 35 candidates); see the update at the top of README.md.

# Candidate Rotation Periods of 42 Main-Belt Asteroids from Gaia DR3 Sparse Photometry

Oleg Tropynin, Independent researcher, Kazakhstan

## Abstract

We searched Gaia DR3 sparse photometry for rotation periods of the 6,000 numbered asteroids that Gaia
observed most often. The method is a periodogram with season offsets, a linear phase term and a
second-order Fourier series, applied to reduced magnitudes. We calibrated it on 300 asteroids with
known periods: 67.7 % are recovered within 3 % under cross-validation. We applied a confidence threshold
set for 80 % precision. On asteroids that Ďurech & Hanuš (2023) solved from the same data, the method
agrees in 83.5 % of cases. We report 42 asteroids with no rotation period in LCDB, JPL SBDB, DAMIT,
the VizieR catalogues or the Minor Planet Bulletin 2023–2026, together with their candidate periods.
Accuracy depends on the period: 81–89 % below 50 h, 36 % above it, where the method usually returns
half of the true period. So we expect about 83 % of the 34 candidates below 50 h to be correct, while
the 8 above 50 h probably rotate twice as slowly. We offer them as targets for confirmation.
(The submission version of this note is `paper/rnaas.tex`.)

## Data and method

Photometry comes from `gaiadr3.sso_observation`, averaged per transit, with a 0.03 mag error floor.
For each transit, JPL Horizons provided the heliocentric and Gaia-centric distances (*r*, Δ) and the
phase angle α, with Gaia as the observer. Times were light-time corrected. The reduced magnitude
G − 5 log10(rΔ) was modelled as one offset per observing season, plus a linear phase term, plus a
second-order Fourier series in rotational phase. We scanned P = 2–100 h on a frequency grid with
step 0.1/T. The doubled period was adopted when doubling increased χ² by less than a factor of 1.5,
which favours double-peaked lightcurves; this factor was fixed by two-fold cross-validation. The
confidence score combines the χ² gain over a no-rotation model with the depth of the best minimum
relative to the next one outside the ×1, ×2 and ×½ aliases.

## Validation

On 300 asteroids with JPL/LCDB periods, the cross-validated recovery rate is 67.7 %. Above the
confidence threshold, 172 of 214 match (80.4 %, an in-sample and therefore optimistic figure).

We ran two independent checks:
(i) among confident target-set asteroids also solved by Ďurech & Hanuš (2023), 81 of 97 agree (83.5 %);
(ii) 26 of our initial 68 candidates appeared in catalogues published after our reference lists
(Cellino et al. 2024; MacLennan et al. 2026; McNeill et al. 2023; Liberato et al. 2024). Of these 26,
17 agree, 5 are at half the published period, and 4 differ.

Three of the four disagreements are slow rotators (214, 818 and about 4,600 h). Their periods lie
outside our search range, and the method returned spurious short periods for them. Users should
keep this failure mode in mind for low-amplitude candidates.

## Results

The 42 candidates are listed in `data/candidates.csv` with period, alias period, amplitude,
number of transits, time span and confidence score.

We checked their novelty against:
- JPL SBDB (LCDB revision October 2023) and LCDB V4.0;
- Ďurech & Hanuš (2023);
- DAMIT;
- VizieR: all tables with an identifier and a period in hours, plus all tables of 29 asteroid-rotation
  catalogues (about 180 tables, 5.1 million rows);
- the full text of the Minor Planet Bulletin, volumes 50–53.

Sources outside this list were not checked.

## Data availability

Code, tables and validation outputs: https://github.com/olegtropinin/gaia-asteroid-periods

## Use of AI

The analysis was designed, coded and checked with the help of an AI assistant (Claude, Anthropic),
under the author's direction.

## References

- Cellino et al. 2024, A&A, 687, A277
- Ďurech, J., & Hanuš, J. 2023, A&A, 675, A24
- Ďurech, J., Sidorin, V., & Kaasalainen, M. 2010, A&A, 513, A46 (DAMIT)
- Gaia Collaboration, Tanga, P., et al. 2023, A&A, 674, A12
- Liberato et al. 2024, A&A, 688, A50
- MacLennan et al. 2026, A&A, 707, A131
- McNeill et al. 2023, AJ, 166, 152
- Warner, B. D., Harris, A. W., & Pravec, P. 2009, Icarus, 202, 134 (LCDB)
