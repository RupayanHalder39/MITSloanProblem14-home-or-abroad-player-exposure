# Code layout

This directory holds the analytical and modelling code for Problem 14, copied
**verbatim** from the research workspace. Nothing has been edited, so the code
that produced the published tables is the code you can read.

Nothing in this directory needs to be changed to use the layout in
`../data/README.md`.

## Where the code looks for data

`shared/__init__.py` sets the project root from its own location:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
```

`shared/config.py` builds every path from that root. Because this file lives at
`<root>/src/shared/config.py`, the root resolves to `<root>/src`, and the
inputs are therefore expected at:

```
src/
├── shared/
├── scripts/
└── dataset/            <-- create this; it is git-ignored
    ├── raw/
    ├── interim/
    └── processed/
        ├── problem_1/
        ├── problem_2/
        └── modeling/
```

`dataset/` is not shipped, because no football data is redistributable here.
`src/dataset/` is in `.gitignore`.

To re-run the pipeline, place a lawful local copy of the inputs there, from
sources you are permitted to use. `../data/README.md` documents the required
schemas and the exact filenames.

## Directory map

| Path | Role |
|---|---|
| `shared/config.py` | All paths and all research conventions in one place: focus countries, top-5 league and competition codes, `U23_AGE`, `LAGS`, the five `ELITE_*` definitions |
| `shared/catalog.py` | Dataset catalogue: which source supplies which table |
| `shared/downloader.py` | Download helper with checksum and manifest support |
| `shared/logutil.py` | Run logging, which writes to `src/records/` |
| `shared/names.py` | Country and team-name normalisation |
| `shared/tables.py` | Table read/write helpers |
| `scripts/download/` | Fetch the eloratings snapshots and the transfermarkt-datasets tables |
| `scripts/normalize/` | Normalise the raw sources into the project's shape |
| `scripts/features/build_problem2.py` | Build the Problem-14 feature tables |
| `scripts/analysis/problem2_nation_coverage_audit.py` | Audit which federations are covered by the data |
| `scripts/models/models_common.py` | The shared OLS and expanding-window rolling-origin evaluation harness |
| `scripts/models/problem2_baselines.py` | Stage A: models M0–M5, the drop-one ablation, and leave-one-country-out |
| `scripts/models/problem2_expanded_panel.py` | Stage B: models E0–E3 and leave-one-country-out at t+3 |
| `scripts/models/problem2_between_within.py` | Between/within decomposition, models W0–W3 |
| `scripts/models/problem2_age_test.py` | U23 versus all-age abroad, models A0–A3 |
| `scripts/eda/pub_common.py` | Shared helpers for the reporting and figure layer |

## Model naming

Model identifiers are stable across the code, the published tables and the
write-up. Keep them aligned if you extend the study.

| Stage | Models | Table |
|---|---|---|
| A | `P2-M0_elo`, `P2-M1_domestic`, `P2-M2_abroad`, `P2-M3_domestic_plus_abroad`, `P2-M4_deoi`, `P2-M5_total_exposure` | `five_country_model_comparison.csv` |
| A | `full_elo_dom_abr`, `remove_domestic`, `remove_abroad` | `five_country_feature_ablation.csv` |
| B | `P2-E0_elo`, `P2-E1_abroad`, `P2-E2_elo_abroad`, `P2-E3_elo_abroad_u23` | `expanded_panel_model_comparison.csv`, `expanded_panel_loco_t3.csv` |
| B | `P2-W0_elo`, `P2-W1_elo_between`, `P2-W2_elo_within`, `P2-W3_elo_between_within` | `between_within_decomposition.csv` |
| B | `P2-A0_elo`, `P2-A1_elo_allage`, `P2-A2_elo_u23`, `P2-A3_elo_both` | `u23_vs_all_age_abroad.csv` |

## What is deliberately absent

- **`scripts/models/build_modeling_tables.py`** is **not** published. It builds
  the modelling table for *both* research problems, so shipping it would
  entangle Problem 1 and Problem 14. The expanded-panel code still reads
  `dataset/processed/problem_1/national_team_season.csv` for the Elo series;
  that file is a shared input, described in `../data/README.md`.
- **No football data.** See `../NOTICE.md` for the source-by-source licence
  position and `../data/README.md` for what an authorised user must assemble.

## Installing

```
python -m venv .venv
.venv\Scripts\activate
pip install -r ..\requirements.txt
```

The `download/` scripts write to `src/dataset/raw/`. Run them only if you have
determined that you are permitted to fetch and retain the sources.
