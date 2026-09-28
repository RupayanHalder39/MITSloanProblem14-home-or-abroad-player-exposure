# Methodology

This document describes how the study was built and evaluated, in enough
detail to judge the evidence. It is a description of a **forecasting** study.

Throughout: **predictive association is not a causal effect.** The design is
observational and time-aware, and the decomposition reported in
[Section 8](#8-between-and-within-country-decomposition) shows that most of
the predictive signal is compositional — persistent differences *between*
federations — which is precisely the part of the evidence that cannot support a
within-federation causal reading.

---

## 1. The outcome variable

**World Football Elo Ratings**, from eloratings.net, by Kirill Bulygin.

Elo is **treated here as a lagged match-result outcome rather than ground
truth for national-team quality.** It summarises match results against rated
opponents and it is a reasonable, widely used way to compress "how did this
team actually do" into a number. It does **not** fully capture player quality,
tactics, coaching, federation development, or every other dimension of
national-team strength. It is not a complete quality index, and nothing in this
study treats it as one.

The target is the **future Elo change**, `Elo at t+lag − Elo at t`, for
`lag` in t+1 … t+5. Using the change rather than the level keeps the target
comparable across federations of very different strength, and it makes current
Elo the natural baseline: a model that predicts no change at all is exactly
"current Elo is the best guess".

---

## 2. Exposure variables

A season label `t` means the season `t/(t+1)`, so `2013` is 2013/14. A player
is U23 if they are 23 or under on **30 June of season t+1**.

"Domestic" and "abroad" are decided by **citizenship**, never by where the
player currently plays. A German playing in the Premier League is domestic to
nothing and abroad for Germany.

| Variable | Definition | Type |
|---|---|---|
| **Abroad elite minutes** | Minutes played by nationals of the federation at elite clubs in the **other four** top-5 European leagues | Measured |
| **Domestic elite minutes** | Minutes played by nationals at elite clubs in their **own** federation's top-5 league | Measured |
| **U23 abroad elite minutes** | The U23 subset of abroad elite minutes | Measured |
| **Domestic U23 ELITE_A minutes** | U23 nationals at clubs finishing in the **top 4** of their own league that season | Measured |
| **DEOI** | Unweighted mean of the z-scores of three domestic U23 components: ELITE_A minutes, ELITE_A starts, ELITE_B minutes | **Proxy** |

### Elite-club flags

| Flag | Definition | Type |
|---|---|---|
| `ELITE_A` | Finished in the top 4 of its league that season | Fact |
| `ELITE_B` | Finished in the top 6 | Fact |
| `ELITE_C` | Played at least one Champions League game that season | Fact |
| `ELITE_D` | Rolling 3-season points-per-game at or above the league 80th percentile | Proxy |
| `ELITE_E` | Rolling 3-season average league position of 4 or better | Proxy |

`any_elite` is the logical OR of the five. Quotes in this study use ELITE_A
where a domestic U23 figure is quoted, and say so.

DEOI is a **transparency aid, not a validated scalar.** Its weights are not
data-driven. All three components ship separately so the weighting can be
changed without rebuilding anything.

---

## 3. Two stages, and why

### Stage A — five big-five federations

Germany, England, Spain, Italy, France; seasons 2012–2025; 70 federation-season
rows. Both domestic and abroad elite minutes are observed, which makes this the
only stage where a clean domestic-versus-abroad comparison is possible.

| Model | Features |
|---|---|
| M0 | Current Elo only — the baseline |
| M1 | Domestic exposure only |
| M2 | Abroad exposure only |
| M3 | Domestic and abroad, as separate columns |
| M4 | DEOI only |
| M5 | Total exposure |

### Stage B — 90-federation expanded panel

90 federations, 1,216 team-season rows, same 14 seasons. Domestic exposure is
**not** observable for most of them.

The federations are split into two groups, and the split is load-bearing:

- **Group A (5 federations)** — own top-5 domestic league present in the data.
  Domestic and abroad both measurable.
- **Group B (85 federations)** — abroad measurable; domestic **unobserved**.

**Group B domestic exposure is missing, and is never coded as zero.** All 1,146
Group B rows carry a missing domestic value. Filling them with zero would assert
that those federations have no elite domestic pipeline, which is a claim about
the world, not a statement about the data. A federation without a top-5 league
is not a federation with zero elite minutes; it is a federation that was never
observed.

| Model | Features |
|---|---|
| E0 | Current Elo only — the baseline |
| E1 | Abroad exposure only |
| E2 | Elo + all-age abroad exposure |
| E3 | Elo + U23 abroad exposure, the U23 feature **replacing** the all-age feature |

E3 replaces rather than augments. U23 abroad minutes are a subset of all-age
abroad minutes, so including both would be close to collinear.

Stage A and Stage B are **never merged**. Different samples, different feature
availability, different questions.

---

## 4. Evaluation design

**Expanding-window, rolling-origin, time-aware out-of-time evaluation.** For
each test time, the model is fitted only on data from strictly earlier test
times and then predicts forward. There is no random train/test split anywhere in
this study, because a random split across calendar time leaks the future into
the past.

- Primary metric: **pooled out-of-time mean absolute error (MAE)**, in Elo
  points. Lower is better.
- Also reported: RMSE, pooled Pearson and Spearman.
- Models: ordinary least squares, implemented directly in NumPy. No
  regularisation, no model selection, no hyper-parameter tuning.

Sample sizes shrink with the horizon, because each extra year of forward target
removes a year of data. In Stage A the Elo baseline is evaluated on 65 rows at
t+1 down to 45 at t+5. In Stage B it is 1,132 rows at t+1 down to 786 at t+5.

**The Elo baseline is strong, and that is the point.** MAE differences of a
fraction of an Elo point on a 38–75 point scale are small. They are reported
because they are consistent and because they survive the checks below, not
because they are large.

---

## 5. Supporting checks

**Feature ablation (Stage A).** Starting from the combined Elo + domestic +
abroad model, remove one family at a time. `mae_delta_vs_full` is the removed
model's MAE minus the full model's MAE. Positive means the removal made
forecasting worse, so the removed family was carrying information.

**Leave-one-country-out (Stage B, t+3).** Refit with each federation held out in
turn, to check that no single country — Germany included — is driving the
result.

**Between/within decomposition (Section 8).**

**U23 versus all-age (Section 9).**

---

## 6. What Stage A shows

Three things, and the third is easy to lose behind the second.

1. **Current Elo is not meaningfully beaten.** No development model — M1 through
   M5 — achieves a lower MAE than M0 at t+2, t+3, t+4 or t+5. The single
   exception is M4, the domestic opportunity index, at t+1, where it is 42.309
   against M0's 42.502: a margin of 0.19 Elo points on a baseline error of 42
   points, at the shortest horizon, and it reverses at every later one. Calling
   that an improvement would overstate it.
2. **Abroad beats domestic, at every horizon.** At t+3, M2 is 65.5 against
   M1's 82.4. At t+5, 80.1 against 111.2.
3. **The original domestic-U23 hypothesis is not supported.** Domestic U23
   elite opportunity did not improve the forecast at any horizon. Within
   Germany, the domestic-opportunity-to-future-Elo relationship is negative at
   every lag.

Ablation points the same way, and its sign flips with the horizon — which is
informative rather than embarrassing. At t+1 and t+2, removing abroad *improves*
MAE (−5.3 and −7.3): at short range the branch adds noise. From t+3 onward,
removing abroad *worsens* MAE (+5.2, +3.3, +18.9). Removing domestic improves
MAE at four of the five horizons; t+4 is the exception.

The asymmetry is specifically a long-horizon phenomenon.

---

## 7. What Stage B shows

Adding abroad exposure to current Elo reduces MAE at every horizon — 0.128 to
0.700 Elo points for E2, 0.197 to 0.896 for E3. Leave-one-country-out at t+3
puts Elo alone at 63.35 and Elo + U23 abroad at 62.70.

The gains are real and small. Two guards keep them honest:

- **Abroad exposure alone does not beat Elo.** E1 is worse than E0 at t+1
  through t+4. The increment exists *on top of* Elo, not instead of it.
- **Leave-one-country-out holds.** No single federation carries the result.

A gain of well under one Elo point is not a forecasting breakthrough. It is a
small, consistent, out-of-time increment.

---

## 8. Between- and within-country decomposition

The most important check in the study, and the one that most limits what can be
claimed.

The pooled data cannot distinguish two very different stories:

- **Between-country (compositional).** Federations that characteristically send
  more players into elite foreign football differ systematically from federations
  that send fewer. The association is just picking up persistent differences.
- **Within-country (dynamic).** A federation's own departures from its own norm
  carry information about where it is heading.

Abroad minutes are split into a country-level expanding mean (BETWEEN) and the
season's deviation from that mean (WITHIN), both computed time-aware with a
one-season lag, and each is added to Elo in turn.

| Horizon | BETWEEN ΔMAE | WITHIN ΔMAE |
|---|---|---|
| t+1 | −0.44 | −0.26 |
| t+2 | −0.34 | +0.09 |
| t+3 | −0.72 | −0.40 |
| t+4 | −0.65 | −0.47 |
| t+5 | −1.06 | −0.62 |

The between-country component is the larger of the two at **every** horizon and
improves the forecast at all five. The within-country component is smaller
throughout, is slightly *worse* than Elo at t+2, and becomes more useful as the
horizon lengthens.

That is the honest summary: **most of the signal is compositional.** A
compositional signal is exactly what selection on ability produces. Strong
football nations produce more players good enough to be trusted abroad, and
strong football nations also have higher Elo. Decomposing the data does not
undo that. It tells you the increment is not the kind of thing you would bank on.

---

## 9. U23 versus all-age abroad

Adding U23 abroad exposure and adding all-age abroad exposure produce almost the
same profile at every horizon. Adding both is no better than either alone.

U23 minutes are a subset of all-age abroad minutes, so the two series are
collinear by construction. Two near-identical results therefore mean *we cannot
distinguish them*, not *we have confirmed a youth pathway*. No youth-development
mechanism is isolated or demonstrated here.

---

## 10. Design limits

- **Observational, one common slope.** All federations share a single OLS
  coefficient. Individual-federation heterogeneity is not modelled.
- **The domestic result is about forecast value, not development quality.**
  Domestic U23 elite opportunity did not improve the forecast of future Elo. That
  is a statement about the incremental predictive value of one measured feature,
  in this dataset, at these horizons. It is not evidence that domestic youth
  development is ineffective, and this study offers no recommendation about it.
- **Elo is the only outcome.** No other measure of national-team strength is
  used as a primary target.
- **A source gap inside season 2014/15.** Appearances data for Spain, England
  and Italy are incomplete that season, at roughly 0.89–0.95 of expected
  minutes. Rows straddling it should be read with that in mind.
- **Data ends mid-2026.** The upstream dataset's author paused updates around
  mid-July 2026, so season 2025 is slightly incomplete for valuations.
- **"Domestic" is a citizenship match.** A dual-national is counted under the
  first-listed country.
- **Market value is an opinion, not a price.** It appears in the feature tables
  as a proxy and is not a headline result.
- **Football-data.co.uk was unreachable** from the research environment and was
  not bypassed, so league standings have no independent cross-check.
- **No FBref or StatsBomb data is used.** Scraping FBref is prohibited; StatsBomb
  was not downloaded. No coverage of either is claimed.

---

## 11. Sources and attribution

- Elo ratings: eloratings.net, by Kirill Bulygin.
- Club, player, appearance and valuation tables: the transfermarkt-datasets CC0
  mirror by David Caribou. Underlying data originates from transfermarkt.com;
  this project uses the published dataset and does **not** scrape
  transfermarkt.com.

Neither source's raw data is redistributed here. See `../data/README.md` and
`../NOTICE.md`.
