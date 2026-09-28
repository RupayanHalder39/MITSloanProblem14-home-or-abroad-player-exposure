<p align="center">
  <b>Home or Abroad?</b><br>
  <b>Where Elite Player Exposure Adds Information About Future National-Team Strength</b><br><br>
  <i>MIT Sloan Sports Analytics Conference research project &middot; Soccer track &middot; Problem 14</i>
</p>

<p align="center">
  <b>Forecasting study.</b> All findings below are <b>predictive associations,
  not a causal effect</b>.
</p>

<p align="center">
  Elo is treated as a lagged match-result outcome rather than ground truth for
  national-team quality.
</p>

---

## The question

Federations debate whether to develop elite players domestically or to let
them move abroad. This repository does **not** answer that. It asks a narrower,
checkable forecasting question:

> **Does elite domestic or foreign playing exposure contain additional
> out-of-time information about future national-team Elo, once current Elo is
> already known?**

Predictive association is not a causal effect. A model that forecasts better is
not a policy recommendation, and nothing here says federations should do
anything differently. Section [10](#10-what-this-does-not-show) says what the
evidence cannot carry.

---

## The short answer

Mostly it does not, with one small exception that is real but much smaller than
it first appears.

1. **Current Elo is a strong baseline and is essentially not beaten.** From t+2
   to t+5 no development model improves on Elo alone. At t+1, the domestic
   opportunity index edges ahead by 0.19 MAE — 42.31 against 42.50, on a scale
   where the baseline's own error is 42 points. That margin is negligible and it
   does not persist at any later horizon.
2. **The original domestic hypothesis is not supported.** Domestic U23 elite
   opportunity did not improve the forecast at any horizon, and inside Germany
   the domestic-opportunity-to-future-Elo relationship is negative at every
   lag.
3. **Abroad exposure adds a small increment on top of Elo** across 90
   federations, worth 0.13 to 0.90 Elo points of MAE, consistent in sign across
   all five horizons and surviving leave-one-country-out.
4. **Most of that increment is compositional**, and compositional signal is
   exactly what you would expect from stronger federations both producing more
   elite players and having higher Elo.

---

## What is in this repository

| Path | Contents |
|---|---|
| [`docs/methodology.md`](docs/methodology.md) | The full method: variables, design, evaluation, decomposition, limits |
| [`results/`](results/study_design.csv) | Seven aggregate result tables, and the study-design table |
| [`figures/`](figures/) | Two project-generated charts |
| [`src/`](src/README.md) | Analytical and modelling code, copied verbatim |
| [`data/README.md`](data/README.md) | Input specification and the licensing position |
| [`NOTICE.md`](NOTICE.md) | Source-by-source terms, attribution, image rights |
| [`PUBLIC_RELEASE_AUDIT.md`](PUBLIC_RELEASE_AUDIT.md) | What was included, what was excluded, and why |
| [`paper/README.md`](paper/README.md) | Paper status: withheld, pending confirmation |
| [`Handoff.md`](Handoff.md) | Open items and the next steps |
| [`LICENSE`](LICENSE) | MIT, covering the code, figures and aggregate tables only |

**No football data is distributed here.** That is a licensing decision. See
[`NOTICE.md`](NOTICE.md) and [`data/README.md`](data/README.md).

---

## Design in one table

| | Stage A | Stage B |
|---|---|---|
| Sample | 5 federations: Germany, England, Spain, Italy, France | 90 federations |
| Federation-seasons | 70 | 1,216 |
| Group A / Group B | — | 5 / 85 |
| Seasons | 2012 to 2025 | 2012 to 2025 |
| Horizons | t+1 … t+5 | t+1 … t+5 |
| Domestic exposure | Observed | Observed for Group A only; **missing, never zero**, for all 1,146 Group B rows |
| Away exposure | Observed | Observed |

Seasons are labelled by starting year, so `2013` is 2013/14. A player is U23 if
they are 23 or under on 30 June of season t+1. Domestic and abroad are decided
by **citizenship**, never by current club. Elite means the club finished in the
top four of its league that season.

The Group B rule is load-bearing: an unobserved domestic pipeline is not a
measured zero, and never becomes one.

---

## What the numbers show

All figures are pooled **out-of-time** mean absolute error, in Elo points, lower
is better. Evaluation is expanding-window and rolling-origin: each model is
fitted only on strictly earlier data. There is no random split anywhere, because
a random split across calendar time leaks the future into the past.

### Stage A — five big-five federations

| Horizon | Elo only | Domestic only | Abroad only |
|---|---|---|---|
| t+1 | **42.50** | 50.38 | 47.28 |
| t+2 | **47.62** | 67.98 | 54.36 |
| t+3 | **55.42** | 82.36 | 65.50 |
| t+4 | **63.70** | 93.50 | 75.20 |
| t+5 | **67.11** | 111.15 | 80.05 |

Abroad beats domestic at every horizon. Both are far worse than Elo alone.

Drop-one ablation, from the combined model — positive means the removed family
was carrying information:

| Horizon | Remove domestic | Remove abroad |
|---|---|---|
| t+1 | −8.14 | −5.26 |
| t+2 | −8.01 | −7.33 |
| t+3 | −1.63 | **+5.20** |
| t+4 | +3.82 | **+3.28** |
| t+5 | −19.41 | **+18.92** |

The sign flips. At short range the away branch adds noise and removing it helps.
From t+3 onward removing it hurts, sharply at t+5. Removing domestic helps at
four horizons of five; t+4 is the exception.

### Stage B — 90 federations

Change in MAE versus Elo alone. Negative is better:

| Horizon | Elo only (MAE) | Elo + all-age abroad | Elo + U23 abroad |
|---|---|---|---|
| t+1 | 38.63 | −0.128 | −0.197 |
| t+2 | 55.42 | −0.507 | −0.708 |
| t+3 | 63.35 | −0.532 | −0.623 |
| t+4 | 69.40 | −0.172 | −0.725 |
| t+5 | 74.46 | −0.700 | −0.896 |

Leave-one-country-out at t+3: Elo alone 63.35, Elo + U23 abroad **62.70**. No
single federation carries the result.

The gains are consistent and they are small. Well under one Elo point, on a
scale where the Elo baseline's own error is 38 to 74 points. Away exposure on
its own does **not** beat Elo; the increment exists only on top of Elo.

### Where the signal actually is

This is the check that most constrains the claims. Splitting away minutes into
the country-level mean and the season's deviation from it:

| Horizon | Between-country | Within-country |
|---|---|---|
| t+1 | −0.44 | −0.26 |
| t+2 | −0.34 | +0.09 |
| t+3 | −0.72 | −0.40 |
| t+4 | −0.65 | −0.47 |
| t+5 | −1.06 | −0.62 |

The **between-country** component is larger at every horizon and helps at all
five. The within-country component is smaller throughout, is slightly worse than
Elo at t+2, and becomes more useful as the horizon lengthens.

Read plainly: most of the predictive signal is compositional. Federations that
characteristically send more players into elite foreign football differ
systematically from federations that send fewer. Decomposing the data does not
undo that. It tells you the increment is not the kind of thing you would bank on.

---

## What this does not show

- **Not causal.** Observational data, one common slope for all federations, and
  a largely compositional signal. Sending players abroad has not been shown to
  raise Elo, and no policy conclusion is offered.
- **Not a quality index.** Elo compresses match results. It is not a complete
  measure of national-team strength, and this study does not treat it as one.
- **Not a verdict on domestic youth development.** Domestic U23 elite opportunity
  did not improve the *forecast* of future Elo. That is a statement about the
  incremental predictive value of one measured feature in this dataset, at these
  horizons. It is **not** evidence that domestic youth development is
  ineffective, and it should not be read as a recommendation to change it.
  Development can be worthwhile for reasons this design cannot observe, such as
  long-run player quality, depth, or squad availability, none of which Elo
  change over one to five years measures.
- **Not a youth-development finding.** U23 and all-age away exposure give nearly
  identical profiles, and they are collinear by construction. Two similar
  results mean they cannot be told apart, not that a youth pathway is confirmed.
- **Not a breakthrough.** Sub-Elo-point improvements on a 38-to-74-point
  baseline, on a sample of 35 to 55 federation-season rows in Stage A.
- **Not validated on other sources.** League standings have no independent
  cross-check; football-data.co.uk was unreachable and was not bypassed. No
  FBref or StatsBomb data is used, and no coverage of either is claimed.

---

## Reproducibility: PARTIAL

**Public:** the code, the aggregate results, and
[`scripts/validate_public_package.py`](scripts/validate_public_package.py),
which re-checks every published headline number against the published tables and
reports the blockers below.

**Conditional:** rebuilding the inputs from lawful local copies of the sources,
then re-running the pipeline under [`src/`](src/README.md).

**Not provided:** the raw data, the row-level derived tables, and the
modelling-table builder, which also generates the other research problem's
table and would entangle the two problems.

Aggregate verification is not retraining. The validator confirms the published
numbers are internally consistent and match the frozen values. It does not
re-estimate a single model.

## Validation

```
python -m pip install -r requirements.txt
python scripts/validate_public_package.py
```

The validator uses only the standard library. It checks the package layout,
re-derives every headline number above from the tables in `results/`, verifies
that internal links and images resolve, and runs a conservative secret,
restricted-content and portability scan.

---

## Attribution

- Elo ratings: **eloratings.net**, by Kirill Bullygin.
- Club, player, appearance and valuation tables: the
  **transfermarkt-datasets** dataset by David Caribou, a CC0 mirror of data
  originating from transfermarkt.com. This project uses the published dataset
  and does not scrape transfermarkt.com.

Neither source's raw data is redistributed here. Full terms, including the
reasons each source is not published, are in [`NOTICE.md`](NOTICE.md).

## Author

<img src="assets/RupayanHalder.jpeg" width="120" alt="Rupayan Halder" align="right">

**Rupayan Halder** &mdash; University of Engineering & Management (UEM),
Kolkata.

**Authorship: CONFIRMED.** The researcher has confirmed that the complete author
list for this research release is Rupayan Halder. No other person may be added
as an author. Reviewer comments, project files, acknowledgements, related
projects, previous papers and the SoccerSolver collaboration were all
explicitly excluded as sources of authorship, and commenting on the abstract as
a reviewer does not establish it. See [`CITATION.cff`](CITATION.cff).

**Research collaboration:**

<img src="assets/SoccerSolverLogo.png" width="220" alt="SoccerSolver" align="left">

> This research was developed in collaboration with SoccerSolver. SoccerSolver
> currently works with more than 10 football clubs.

SoccerSolver is a research collaborator and acknowledgement, and is **not** an
author. It is not a funder, sponsor or owner of this research either, none of
which is claimed: no evidence establishes any of those relationships. Its mark
is used for identification only and its inclusion implies no endorsement, and
none of its data is used in any result published here.

---

## Publication status of this repository

| Question | Answer |
|---|---|
| Authorship | **CONFIRMED** &mdash; Rupayan Halder |
| Required assets present and digest-verified | **Yes** |
| Package complete and validating | **Yes** |
| Restricted-material scan | **Clear** |
| GitHub content ready | **YES** |
| Safe to push | **YES** |

## Licence

Project-controlled code, figures and aggregate tables: [MIT](LICENSE).
Underlying football data: not distributed, see [`NOTICE.md`](NOTICE.md).
