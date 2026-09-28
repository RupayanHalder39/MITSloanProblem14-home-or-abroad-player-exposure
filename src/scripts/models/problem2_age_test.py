"""PROBLEM 2 — STAGE 1, B6: U23 vs ALL-AGE abroad exposure (expanded panel).

If ALL-AGE abroad exposure carries the predictive signal but the U23 (youth)
component does NOT, the "youth pathway" reading of the pipeline weakens. This
runs the age-isolation test and reports honestly either way.

Models (expanding-window OLS, t+1..t+5; negative delta = improvement over
Elo-only):
  P2-A0  Elo only
  P2-A1  Elo + abroad_elite_minutes (ALL-AGE abroad)
  P2-A2  Elo + abroad_u23_elite_minutes (U23 abroad)
  P2-A3  Elo + both

Outputs:
  eda_outputs/modeling/problem_2_expanded/P2_age_test.csv
  eda_outputs/modeling/problem_2_expanded/AGE-P2-01..02  (triplets)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared.config import PROCESSED, EDA_OUTPUTS  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402
from scripts.models.models_common import rollorigin_predictions, summarize_rollorigin  # noqa: E402
from scripts.eda.pub_common import emit, standard_md  # noqa: E402

log = setup_log("problem2_age_test")
add_file_handler(log, REPO_ROOT / "records" / "problem2_age_test.log")

MODELING = PROCESSED / "modeling"
OUT = EDA_OUTPUTS / "modeling" / "problem_2_expanded"
LAGS = [1, 2, 3, 4, 5]
MIN_TRAIN = 40

FEATURE_SETS = {
    "P2-A0_elo": ["elo"],
    "P2-A1_elo_allage": ["elo", "abroad_elite_minutes"],
    "P2-A2_elo_u23": ["elo", "abroad_u23_elite_minutes"],
    "P2-A3_elo_both": ["elo", "abroad_elite_minutes", "abroad_u23_elite_minutes"],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(MODELING / "problem2_expanded_abroad_panel.csv")

    rows = []
    for lag in LAGS:
        tgt = f"target_elo_delta_{lag}y"
        for name, feats in FEATURE_SETS.items():
            preds = rollorigin_predictions(df, tgt, feats, "season",
                                           min_train=MIN_TRAIN)
            s = summarize_rollorigin(preds)
            rows.append({
                "lag": lag, "model": name,
                "n_total": s["n_total"].iloc[0] if len(s) else np.nan,
                "mae_pooled": s["mae_pooled"].iloc[0] if len(s) else np.nan,
                "rmse_pooled": s["rmse_pooled"].iloc[0] if len(s) else np.nan,
                "pearson_pooled": s["pearson_pooled"].iloc[0] if len(s) else np.nan,
            })
            log.info("age %-18s lag %d mae=%.2f r=%.2f n=%.0f",
                     name, lag, rows[-1]["mae_pooled"],
                     rows[-1]["pearson_pooled"], rows[-1]["n_total"])
    cmp = pd.DataFrame(rows)
    ref = {lag: cmp[(cmp.lag == lag) & (cmp.model == "P2-A0_elo")]["mae_pooled"].iloc[0]
           for lag in LAGS}
    cmp["delta_mae_vs_elo"] = cmp.apply(lambda r: r["mae_pooled"] - ref[r["lag"]], axis=1)
    cmp.to_csv(OUT / "P2_age_test.csv", index=False)

    allage = cmp[cmp.model == "P2-A1_elo_allage"].sort_values("lag")
    u23 = cmp[cmp.model == "P2-A2_elo_u23"].sort_values("lag")
    both = cmp[cmp.model == "P2-A3_elo_both"].sort_values("lag")
    log.info("ALL-AGE delta vs elo: %s", allage["delta_mae_vs_elo"].round(2).tolist())
    log.info("U23      delta vs elo: %s", u23["delta_mae_vs_elo"].round(2).tolist())
    log.info("BOTH     delta vs elo: %s", both["delta_mae_vs_elo"].round(2).tolist())

    plot_mae(cmp)
    plot_delta(cmp)
    print("age test script complete ->", OUT)


def plot_mae(cmp: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = {"P2-A0_elo": "#9ca3af", "P2-A1_elo_allage": "#2563eb",
              "P2-A2_elo_u23": "#d97706", "P2-A3_elo_both": "#0f766e"}
    labels = {"P2-A0_elo": "Elo only", "P2-A1_elo_allage": "+ ALL-AGE abroad",
              "P2-A2_elo_u23": "+ U23 abroad",
              "P2-A3_elo_both": "+ both (all-age + U23)"}
    for m in labels:
        d = cmp[cmp.model == m].sort_values("lag")
        ax.plot(d["lag"], d["mae_pooled"], marker="o", lw=1.8,
                color=colors[m], label=labels[m])
    ax.set_xlabel("lag (years)")
    ax.set_ylabel("MAE (future Elo delta)")
    ax.set_title("AGE-P2-01 — all-age vs U23 abroad exposure (expanded panel)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    emit(OUT, "AGE-P2-01_mae_allage_vs_u23", cmp, fig,
         standard_md(
             "AGE-P2-01 all-age vs U23 abroad MAE",
             shows="Expanding-window MAE for Elo only, Elo+all-age abroad, "
                   "Elo+U23 abroad, Elo+both.",
             does_not_show="Which age band is 'driving' any effect causally.",
             supports="If the +U23 line sits at/below the +all-age line, the "
                      "youth component carries the abroad signal.",
             weakens="If U23 alone adds nothing while all-age does, the pipeline "
                      "interpretation weakens (reported honestly either way).",
             alternatives="Age bands are correlated with club exposure by "
                          "construction; interpreting the difference is model-"
                          "dependent.",
             limitations="OLS; expanded panel only."))


def plot_delta(cmp: pd.DataFrame) -> None:
    d = cmp[cmp.model != "P2-A0_elo"].pivot_table(
        index="model", columns="lag", values="delta_mae_vs_elo")
    labels = {"P2-A1_elo_allage": "ALL-AGE", "P2-A2_elo_u23": "U23",
              "P2-A3_elo_both": "BOTH"}
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for m, lab in labels.items():
        ax.plot(d.columns, d.loc[m], marker="o", label=lab)
    ax.axhline(0, color="0.4", ls="--", lw=1)
    ax.set_xlabel("lag (years)")
    ax.set_ylabel("ΔMAE vs Elo-only (negative = better)")
    ax.set_title("AGE-P2-02 — age-band delta MAE (negative = improvement)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    emit(OUT, "AGE-P2-02_delta_allage_vs_u23", d.reset_index(), fig,
         standard_md(
             "AGE-P2-02 age-band delta MAE",
             shows="Signed MAE difference vs Elo-only for the all-age, U23, and "
                   "combined abroad models.",
             does_not_show="Causation; club-vs-youth age overlap.",
             supports="A clearly negative U23 line would support a youth-pathway "
                      "reading of abroad exposure.",
             weakens="A clearly negative all-age line with a flat U23 line "
                      "weakens the youth-pathway reading (documented either way).",
             alternatives="Selection of who develops abroad vs who is bought.",
             limitations="OLS; expanded panel only."))


if __name__ == "__main__":
    main()