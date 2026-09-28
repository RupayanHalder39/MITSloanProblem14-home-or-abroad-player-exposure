"""PROBLEM 2 — STAGE 1, B5(+B6 core): between-country vs within-country
decomposition of abroad elite exposure in the EXPANDED panel.

Motivation (PART C, P2-Q3 / hypothesis P2-H6): a country-level correlation
between abroad exposure and future strength can arise because (i) strong
football nations simply produce more top-5 abroad players BETWEEN countries,
or (ii) a country's own deviations from its norm WITHIN countries predict its
future Elo. Only within-country signal supports a dynamic "abroad exposure
helps" reading.

Decomposition (time-aware, no leakage):
  between(s,t)  = expanding country mean of abroad_elite_minutes over
                  seasons <= s (including s), shifted so only past obs count
  within(s)     = abroad_elite_minutes(s) - between-so-far(s)

Models (expanding-window OLS, t+1..t+5):
  P2-W0  Elo only
  P2-W1  Elo + between
  P2-W2  Elo + within
  P2-W3  Elo + between + within

If W1 ~= W3 and W2 adds nothing -> abroad signal is primarily BETWEEN-country.
If W2 is a genuine improvement -> within-country dynamics carry the signal.

Outputs:
  eda_outputs/modeling/problem_2_expanded/P2_between_within.csv
  eda_outputs/modeling/problem_2_expanded/BW-P2-01..02  (triplets)
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared.config import PROCESSED, EDA_OUTPUTS  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402
from scripts.models.models_common import (  # noqa: E402
    rollorigin_predictions,
    summarize_rollorigin,
)
from scripts.eda.pub_common import emit, standard_md  # noqa: E402

log = setup_log("problem2_between_within")
add_file_handler(log, REPO_ROOT / "records" / "problem2_between_within.log")

MODELING = PROCESSED / "modeling"
OUT = EDA_OUTPUTS / "modeling" / "problem_2_expanded"
LAGS = [1, 2, 3, 4, 5]
MIN_TRAIN = 40


def add_decomposition(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values(["nat_team_code", "season"]).copy()
    g = out.groupby("nat_team_code", sort=False)["abroad_elite_minutes"]
    prev_mean = g.transform(lambda s: s.expanding(min_periods=1).mean().shift(1))
    out["between_before"] = prev_mean
    out["within"] = out["abroad_elite_minutes"] - prev_mean
    return out


FEATURE_SETS = {
    "P2-W0_elo": ["elo"],
    "P2-W1_elo_between": ["elo", "between_before"],
    "P2-W2_elo_within": ["elo", "within"],
    "P2-W3_elo_between_within": ["elo", "between_before", "within"],
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(MODELING / "problem2_expanded_abroad_panel.csv")
    df = add_decomposition(raw)

    rows = []
    preds_store = {}
    for lag in LAGS:
        tgt = f"target_elo_delta_{lag}y"
        for name, feats in FEATURE_SETS.items():
            preds = rollorigin_predictions(df, tgt, feats, "season",
                                           min_train=MIN_TRAIN)
            preds_store[f"{lag}__{name}"] = preds
            s = summarize_rollorigin(preds)
            rows.append({
                "lag": lag, "model": name,
                "n_total": s["n_total"].iloc[0] if len(s) else np.nan,
                "mae_pooled": s["mae_pooled"].iloc[0] if len(s) else np.nan,
                "rmse_pooled": s["rmse_pooled"].iloc[0] if len(s) else np.nan,
                "pearson_pooled": s["pearson_pooled"].iloc[0] if len(s) else np.nan,
            })
            log.info("bw %-24s lag %d mae=%.2f r=%.2f n=%.0f",
                     name, lag, rows[-1]["mae_pooled"],
                     rows[-1]["pearson_pooled"], rows[-1]["n_total"])
    cmp = pd.DataFrame(rows)
    ref = {}
    for lag in LAGS:
        ref[lag] = cmp[(cmp.lag == lag) & (cmp.model == "P2-W0_elo")]["mae_pooled"].iloc[0]
    cmp["delta_mae_vs_elo"] = cmp.apply(lambda r: r["mae_pooled"] - ref[r["lag"]], axis=1)
    cmp.to_csv(OUT / "P2_between_within.csv", index=False)

    within = cmp[cmp.model == "P2-W2_elo_within"].sort_values("lag")
    across = cmp[cmp.model == "P2-W1_elo_between"].sort_values("lag")
    both = cmp[cmp.model == "P2-W3_elo_between_within"].sort_values("lag")
    log.info("WITHIN delta vs elo: %s", within["delta_mae_vs_elo"].round(2).tolist())
    log.info("BETWEEN delta vs elo: %s", across["delta_mae_vs_elo"].round(2).tolist())
    log.info("BOTH   delta vs elo: %s", both["delta_mae_vs_elo"].round(2).tolist())

    plot_bw(cmp)
    plot_delta(cmp)
    print("between/within script complete ->", OUT)


def plot_bw(cmp: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = {"P2-W0_elo": "#9ca3af", "P2-W1_elo_between": "#2563eb",
              "P2-W2_elo_within": "#e11d48",
              "P2-W3_elo_between_within": "#0f766e"}
    for m in ["P2-W0_elo", "P2-W1_elo_between", "P2-W2_elo_within",
              "P2-W3_elo_between_within"]:
        d = cmp[cmp.model == m].sort_values("lag")
        ax.plot(d["lag"], d["mae_pooled"], marker="o", lw=1.8,
                color=colors[m],
                label={"P2-W0_elo": "Elo only", "P2-W1_elo_between": "+ BETWEEN",
                       "P2-W2_elo_within": "+ WITHIN",
                       "P2-W3_elo_between_within": "+ BETWEEN + WITHIN"}[m])
    ax.set_xlabel("lag (years)")
    ax.set_ylabel("MAE (future Elo delta)")
    ax.set_title("BW-P2-01 — between vs within decomposition (expanded panel)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    emit(OUT, "BW-P2-01_between_within", cmp, fig,
         standard_md(
             "BW-P2-01 between vs within decomposition",
             shows="Expanding-window MAE for Elo-only, Elo+between-country mean, "
                   "Elo+within-country deviation, and both.",
             does_not_show="A causal reading of either component.",
             supports="The component whose addition lowers MAE most is where the "
                      "abroad signal lives (between-country vs within-country).",
             weakens="Between and within are correlated by construction (a team "
                     "rising from its mean also raises its mean).",
             alternatives="Country random effects; fixed-effects demeaning on "
                          "the full panel.",
             limitations="OLS pool; expanding means are as-of (no leakage); "
                          "expanded panel only."))


def plot_delta(cmp: pd.DataFrame) -> None:
    d = cmp[cmp.model != "P2-W0_elo"].pivot_table(
        index="model", columns="lag", values="delta_mae_vs_elo")
    labels = {"P2-W1_elo_between": "BETWEEN", "P2-W2_elo_within": "WITHIN",
              "P2-W3_elo_between_within": "BOTH"}
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for m, lab in labels.items():
        ax.plot(d.columns, d.loc[m], marker="o", label=lab)
    ax.axhline(0, color="0.4", ls="--", lw=1)
    ax.set_xlabel("lag (years)")
    ax.set_ylabel("ΔMAE vs Elo-only (negative = better)")
    ax.set_title("BW-P2-02 — delta MAE by component (negative = improvement)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    emit(OUT, "BW-P2-02_delta_by_component", d.reset_index(), fig,
         standard_md(
             "BW-P2-02 delta by component",
             shows="Signed MAE difference vs Elo-only for each component at each "
                   "lag; negative values are improvements.",
             does_not_show="Interaction effects beyond the linear model.",
             supports="A consistently negative WITHIN line documents genuine "
                      "within-country predictive dynamics.",
             weakens="If the WITHIN line stays at zero while BETWEEN is negative, "
                      "the abroad signal is mostly compositional.",
             alternatives="Time-variant country effects.",
             limitations="One decomposition scheme; OLS."))


if __name__ == "__main__":
    main()