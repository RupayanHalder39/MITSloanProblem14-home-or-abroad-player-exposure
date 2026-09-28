# Data

**No football data is distributed in this repository.**

That is a licensing decision, not an oversight. Access to a source is not a
redistribution licence, and the licence position for the underlying football
data is not clear enough to publish it. See `../NOTICE.md` for the source-by-
source position.

What *is* published is the researcher's own aggregate evidence: model-
comparison tables under `results/`, the study-design table, and the analytical
code under `../src/`.

## Where the results come from

Every published table is an aggregate over these two input families:

| Input | Provider | Used for | Published here |
|---|---|---|---|
| National-team Elo ratings | eloratings.net (Kirill Bulygin) | The outcome variable | No — raw series withheld |
| Club, player, appearance and valuation tables | transfermarkt-datasets (dcaribou, CC0 mirror of transfermarkt.com data) | Elite-club flags, elite minutes, starts | No — raw tables withheld |
| League standings cross-check | football-data.co.uk | Planned independent cross-check | No — not used in any published result |

## What a full re-run requires

Reproducing the models end to end is **not possible from this repository
alone**. An authorised user needs to assemble the inputs themselves, from
sources they are permitted to use:

```
<work_root>/
├── src/                      # this repository's src/ directory
│   ├── shared/
│   ├── scripts/
│   └── dataset/              # <-- the working data root the code expects
│       ├── raw/
│       │   ├── eloratings/            yearly TSV snapshots
│       │   └── transfermarkt-datasets/  the published CSV.GZ tables
│       ├── interim/
│       └── processed/
│           ├── problem_1/    national_team_season.csv  (Elo series)
│           ├── problem_2/    player_club_season.csv, club_season.csv, ...
│           └── modeling/     problem2_model_table.csv
└── records/                  # run logs (git-ignored)
```

`src/dataset/` is the location the code resolves, because the modules under
`src/shared/` and `src/scripts/` derive their project root from their own file
location. Nothing in `src/` needs editing to use this layout. See
`../src/README.md`.

**Note on `dataset/processed/problem_1/`:** the expanded-panel builder reads
`national_team_season.csv` from that directory to obtain the Elo series. That
table is a *shared input*, not part of the other research problem's analysis:
it is the same Elo source described above, normalised. The modelling-table
builder that generates it is not published here, because that script also
generates the other research problem's model table and publishing it would mix
the two problems.

## Schemas of the withheld inputs

Documented so an authorised user can rebuild them without guesswork.

### `problem2_model_table.csv` — five-federation modelling table

One row per federation × season. 70 rows (5 federations × 14 seasons,
2012–2025).

| Column | Type | Meaning |
|---|---|---|
| `country` | str | Germany, England, Spain, Italy, France |
| `nat_team_code` | str | DE, EN, ES, IT, FR |
| `season` | int | Season label `t`, meaning the season `t/(t+1)` |
| `elo` | float | Current national-team Elo |
| `domestic_u21_minutes` | int | Domestic minutes by U21 nationals |
| `domestic_u23_minutes` | int | Domestic minutes by U23 nationals |
| `domestic_u23_eliteA_minutes` | int | U23 domestic minutes at ELITE_A clubs |
| `domestic_u23_eliteA_starts` | int | Starts by the same population |
| `domestic_u23_eliteB_minutes` | int | U23 domestic minutes at ELITE_B clubs |
| `DEOI_baseline_zscore` | float | Domestic Elite Opportunity Index, z-scored |
| `abroad_elite_minutes` | int | All-age elite minutes in the other four top-5 leagues |
| `abroad_elite_share` | float | Abroad share of top-5 exposure |
| `abroad_u23_elite_minutes` | int | U23 subset of `abroad_elite_minutes` |
| `abroad_elite_nationals` | int | Nationals with abroad elite minutes |
| `total_elite_exposure_minutes` | int | Domestic + abroad elite minutes |
| `total_u23_elite_exposure_minutes` | int | U23 domestic + abroad elite minutes |
| `domestic_share`, `foreign_share` | float | Minute shares |
| `domestic_total_value_eur`, `foreign_total_value_eur` | int | Opinion-based valuations (proxy) |
| `target_elo_delta_1y` … `_5y` | float | Elo at `t+lag` minus Elo at `t` |

### `problem2_expanded_abroad_panel.csv` — 90-federation panel

One row per federation × season. 1,216 rows (90 federations × 14 seasons,
2012–2025).

| Column | Type | Meaning |
|---|---|---|
| `country`, `nat_team_code`, `season` | — | As above |
| `group` | str | `GROUP_A` (5) or `GROUP_B` (85) |
| `abroad_elite_minutes` | int | All-age elite minutes abroad |
| `abroad_u23_elite_minutes` | int | U23 subset |
| `abroad_elite_nationals` | int | Nationals with abroad elite minutes |
| `domestic_elite_minutes` | int | **Group B: missing in all 1,146 rows, never zero** |
| `elo` | float | Current national-team Elo |
| `total_top5_elite_minutes` | int | Group A: domestic + abroad. Group B: abroad only |
| `target_elo_delta_1y` … `_5y` | float | Elo at `t+lag` minus Elo at `t` |

`GROUP_A` federations have their own top-5 domestic league in the data.
`GROUP_B` federations do not, so their domestic exposure is **unobserved**. It
is not a measured zero and is never treated as one. This is a load-bearing
design rule, not a formatting detail.

## Aggregate evidence that *is* published

| File | Contents |
|---|---|
| `study_design.csv` | Federations, row counts, group split, season range, horizons, evaluation-row counts, feature definitions |
| `five_country_model_comparison.csv` | Models M0–M5 × t+1…t+5, pooled out-of-time MAE/RMSE/Pearson/Spearman, plus LOCO columns |
| `five_country_feature_ablation.csv` | Drop-one ablation of the Elo + domestic + abroad model |
| `expanded_panel_model_comparison.csv` | Models E0–E3 × t+1…t+5 on the 90-federation panel |
| `expanded_panel_loco_t3.csv` | Leave-one-country-out stability at t+3 |
| `between_within_decomposition.csv` | Models W0–W3, between/within decomposition |
| `u23_vs_all_age_abroad.csv` | Models A0–A3, U23 versus all-age abroad |

## Reproducibility classification: PARTIAL

- **Public:** the analytical code, the aggregate results, and a validator that
  re-checks every published headline number against those results.
- **Conditional:** rebuilding the inputs from lawful local copies of the
  sources, then re-running the pipeline under `src/`.
- **Not provided:** the raw data, the row-level derived tables, and the
  modelling-table builder (see above).

Aggregate verification is not retraining. `../scripts/validate_public_package.py`
confirms that the published numbers are internally consistent and match the
frozen values. It does not re-estimate a single model.
