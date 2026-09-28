"""PROBLEM 2 — parallel baseline models: does ABROAD elite exposure add
predictive information beyond domestic DEOI / youth opportunity?

Models (for each lag t+1..t+5, outcome = future national-team Elo delta):
  P2-M0  current Elo only
  P2-M1  DOMESTIC only (u21/u23 minutes, U23 elite-A minutes/starts, elite-B)
  P2-M2  ABROAD only (elite minutes/share, u23 elite minutes, nationals)
  P2-M3  DOMESTIC + ABROAD as SEPARATE features (never summed)
  P2-M4  DEOI only
  P2-M5  TOTAL-EXPOSURE only (mandated to test summing dilution)

Evaluation (tiny dataset -> no random split):
  - expanding-window over seasons (min_train=4)
  - leave-one-country-out
  - country-specific pooled errors
Feature importance (Phase 8): drop-one ablation on [Elo + domestic + abroad].

Outputs:
  eda_outputs/modeling/problem_2/P2_baseline_comparison.csv
  eda_outputs/modeling/problem_2/P2_loco_per_country.csv
  eda_outputs/modeling/problem_2/P2_country_errors.csv
  eda_outputs/modeling/problem_2/P2_ablation.csv
  eda_outputs/modeling/problem_2/P2_std_coefs.csv
  eda_outputs/modeling/problem_2/P2_germany_errors.csv
  eda_outputs/modeling/problem_2/P2_M3_preds.csv
  eda_outputs/modeling/problem_2/M-P2-01..06  (PNG+CSV+MD triplets)
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
    pooled_metrics,
    rollorigin_predictions,
    summarize_rollorigin,
    loco_predictions,
    summarize_loco,
    ols_standardized_coefs,
)
from scripts.eda.pub_common import emit, standard_md  # noqa: E402

log = setup_log("problem2_baselines")
add_file_handler(log, REPO_ROOT / "records" / "problem2_baselines.log")

MODELING = PROCESSED / "modeling"
OUT = EDA_OUTPUTS / "modeling" / "problem_2"

MIN_TRAIN = 4
LAGS = [1, 2, 3, 4, 5]
COUNTRIES = ["Germany", "England", "Spain", "Italy", "France"]

DOM_FEATURES = ["domestic_u21_minutes", "domestic_u23_minutes",
                "domestic_u23_eliteA_minutes", "domestic_u23_eliteA_starts",
                "domestic_u23_eliteB_minutes"]
ABR_FEATURES = ["abroad_elite_minutes", "abroad_elite_share",
                "abroad_u23_elite_minutes", "abroad_elite_nationals"]

FEATURE_SETS = {
    "P2-M0_elo": ["elo"],
    "P2-M1_domestic": DOM_FEATURES,
    "P2-M2_abroad": ABR_FEATURES,
    "P2-M3_domestic_plus_abroad": DOM_FEATURES + ABR_FEATURES,
    "P2-M4_deoi": ["DEOI_baseline_zscore"],
    "P2-M5_total_exposure": ["total_elite_exposure_minutes",
                             "total_u23_elite_exposure_minutes"],
}

FULL_ABLATION = ["elo"] + DOM_FEATURES + ABR_FEATURES
ABLATION_VARIANTS = {
    "full_elo_dom_abr": FULL_ABLATION,
    "remove_domestic": ["elo"] + ABR_FEATURES,
    "remove_abroad": ["elo"] + DOM_FEATURES,
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(MODELING / "problem2_model_table.csv")

    # ---------------- baseline comparison ----------------
    cmp_rows = []
    loco_rows = []
    country_rows = []
    ger_rows = []
    preds_store = {}
    for lag in LAGS:
        tgt = f"target_elo_delta_{lag}y"
        for name, feats in FEATURE_SETS.items():
            preds = rollorigin_predictions(df, tgt, feats, "season",
                                           min_train=MIN_TRAIN)
            preds_store[f"{lag}__{name}"] = preds
            s = summarize_rollorigin(preds)
            lp = loco_predictions(df, tgt, feats, "country", COUNTRIES)
            s_loco = summarize_loco(lp, COUNTRIES)
            mae_loco = (s_loco["mae_pooled"].iloc[0] if len(s_loco) else np.nan)
            rmse_loco = (s_loco["rmse_pooled"].iloc[0] if len(s_loco) else np.nan)
            for _, rr in s_loco.iterrows():
                loco_rows.append({"lag": lag, "model": name,
                                  "left_out_country": rr["left_out_country"],
                                  "n": int(rr["n"]), "mae": rr["mae"],
                                  "rmse": rr["rmse"]})
            # country-specific pooled errors from rolling-origin preds
            for c in COUNTRIES:
                cp = preds[preds["country"] == c]
                if cp.empty:
                    continue
                cm = pooled_metrics(cp["actual"], cp["pred"])
                country_rows.append({"lag": lag, "model": name, "country": c,
                                     "n": cm["n"], "mae_c": cm["mae"],
                                     "rmse_c": cm["rmse"]})
            # Germany-specific
            gp = preds[preds["country"] == "Germany"]
            if not gp.empty:
                gm = pooled_metrics(gp["actual"], gp["pred"])
                ger_rows.append({"lag": lag, "model": name, "mae_de": gm["mae"],
                                 "rmse_de": gm["rmse"], "n_de": gm["n"]})
            cmp_rows.append({
                "lag": lag, "model": name,
                "n_total": s["n_total"].iloc[0] if len(s) else np.nan,
                "test_times": int(s["test_times"].iloc[0]) if len(s) else 0,
                "mae_pooled": s["mae_pooled"].iloc[0] if len(s) else np.nan,
                "rmse_pooled": s["rmse_pooled"].iloc[0] if len(s) else np.nan,
                "pearson_pooled": s["pearson_pooled"].iloc[0] if len(s) else np.nan,
                "spearman_pooled": s["spearman_pooled"].iloc[0] if len(s) else np.nan,
                "mae_loco_pooled": mae_loco, "rmse_loco_pooled": rmse_loco,
            })
            log.info("P2 lag %d %-28s mae=%.2f rmse=%.2f r=%.2f loco_mae=%.2f n=%d",
                     lag, name,
                     cmp_rows[-1]["mae_pooled"], cmp_rows[-1]["rmse_pooled"],
                     cmp_rows[-1]["pearson_pooled"], mae_loco,
                     cmp_rows[-1]["n_total"])
    cmp = pd.DataFrame(cmp_rows)
    cmp.to_csv(OUT / "P2_baseline_comparison.csv", index=False)
    pd.DataFrame(loco_rows).to_csv(OUT / "P2_loco_per_country.csv", index=False)
    pd.DataFrame(country_rows).to_csv(OUT / "P2_country_errors.csv", index=False)
    pd.DataFrame(ger_rows).to_csv(OUT / "P2_germany_errors.csv", index=False)

    # ---------------- ablation (Phase 8) + standardized coefs ----------------
    abl_rows = []
    full_ref = {}
    for lag in LAGS:
        tgt = f"target_elo_delta_{lag}y"
        for variant, feats in ABLATION_VARIANTS.items():
            preds = rollorigin_predictions(df, tgt, feats, "season",
                                           min_train=MIN_TRAIN)
            s = summarize_rollorigin(preds)
            abl_rows.append({"lag": lag, "variant": variant,
                             "mae_pooled": s["mae_pooled"].iloc[0] if len(s) else np.nan,
                             "rmse_pooled": s["rmse_pooled"].iloc[0] if len(s) else np.nan,
                             "pearson_pooled": s["pearson_pooled"].iloc[0] if len(s) else np.nan})
        full_ref[lag] = next(r for r in abl_rows if r["lag"] == lag
                             and r["variant"] == "full_elo_dom_abr")
    for r in abl_rows:
        r["mae_delta_vs_full"] = r["mae_pooled"] - full_ref[r["lag"]]["mae_pooled"]
    abl = pd.DataFrame(abl_rows)
    abl.to_csv(OUT / "P2_ablation.csv", index=False)
    log.info("ablation: remove_domestic pooled MAE loss vs full: %s",
             abl[abl.variant == "remove_domestic"].mae_delta_vs_full.round(2).tolist())
    log.info("ablation: remove_abroad  pooled MAE loss vs full: %s",
             abl[abl.variant == "remove_abroad"].mae_delta_vs_full.round(2).tolist())

    coef_rows = []
    for lag in LAGS:
        tgt = f"target_elo_delta_{lag}y"
        sub = df.dropna(subset=[tgt] + FULL_ABLATION)
        if len(sub) < 6:
            continue
        co = ols_standardized_coefs(sub[FULL_ABLATION],
                                    sub[tgt].to_numpy(dtype=float))
        for k, v in co.items():
            coef_rows.append({"lag": lag, "feature": k[len("std_coef_"):],
                              "std_coef": v})
    pd.DataFrame(coef_rows).to_csv(OUT / "P2_std_coefs.csv", index=False)

    # Save M3 lag-3 predictions for charts
    m3_l3 = preds_store["3__P2-M3_domestic_plus_abroad"]
    m3_l3.to_csv(OUT / "P2_M3_preds.csv", index=False)

    # ================= CHARTS =================
    plot_mae_by_lag(cmp)                      # M-P2-01
    plot_dom_vs_abroad(cmp)                   # M-P2-02
    plot_ablation(abl)                        # M-P2-03
    plot_oot_scatter(m3_l3)                   # M-P2-04
    plot_loco(cmp)                            # M-P2-05
    plot_germany(m3_l3, df)                   # M-P2-06

    print("P2 baseline script complete ->", OUT)


# ---------------------------------------------------------------------------
def order_models(cmp):
    order = ["P2-M0_elo", "P2-M1_domestic", "P2-M2_abroad",
             "P2-M3_domestic_plus_abroad", "P2-M4_deoi",
             "P2-M5_total_exposure"]
    return [m for m in order if m in list(cmp["model"].unique())]


def plot_mae_by_lag(cmp) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = {"P2-M0_elo": "#9ca3af", "P2-M1_domestic": "#2563eb",
              "P2-M2_abroad": "#e11d48", "P2-M3_domestic_plus_abroad": "#0f766e",
              "P2-M4_deoi": "#7c3aed", "P2-M5_total_exposure": "#d97706"}
    for m in order_models(cmp):
        d = cmp[cmp.model == m].sort_values("lag")
        ax.plot(d["lag"], d["mae_pooled"], marker="o", lw=1.8,
                color=colors[m], label=m.replace("P2-M", "M"))
    ax.set_xlabel("lag (years)")
    ax.set_ylabel("MAE (future Elo delta)")
    ax.set_xticks(cmp["lag"].unique())
    ax.set_title("M-P2-01 — MAE by lag and model (expanding-window, Problem 2)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    emit(OUT, "M-P2-01_mae_by_lag_and_model", cmp, fig,
         standard_md(
             "M-P2-01 MAE by lag and model",
             shows="Expanding-window MAE of the six baselines per lag 1..5.",
             does_not_show="Out-of-sample certainty at the country level.",
             supports="Any gap between M1 (domestic) and M2 (abroad) answers the core "
                      "research question directly.",
             weakens="MAE differences of a few Elo points are small relative to Elo "
                     "delta noise (sd ~ 40).",
             alternatives="Developmental lag time, transfer effects, selection bias.",
             limitations="5 nations x 14 seasons; OLS; no random splits."))


def plot_dom_vs_abroad(cmp) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    dom = cmp[cmp.model == "P2-M1_domestic"].sort_values("lag")
    abr = cmp[cmp.model == "P2-M2_abroad"].sort_values("lag")
    x = np.arange(len(dom))
    ax.bar(x - 0.18, dom["mae_pooled"], 0.36, label="DOMESTIC-only (M1)",
           color="#2563eb", alpha=0.85)
    ax.bar(x + 0.18, abr["mae_pooled"], 0.36, label="ABROAD-only (M2)",
           color="#e11d48", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([f"t+{l}" for l in dom["lag"]])
    ax.set_ylabel("MAE (future Elo delta)")
    ax.set_title("M-P2-02 — domestic-only vs abroad-only (expanding-window)")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    out = dom[["lag", "mae_pooled"]].merge(
        abr[["lag", "mae_pooled"]], on="lag", suffixes=("_domestic", "_abroad"))
    emit(OUT, "M-P2-02_domestic_vs_abroad", out, fig,
         standard_md(
             "M-P2-02 domestic-only vs abroad-only",
             shows="MAE of M1 (domestic minutes/starts only) vs M2 (abroad elite "
                   "minutes only) by lag.",
             does_not_show="Which feature 'causes' Elo; country subsets.",
             supports="If abroad-only MAE < domestic-only MAE at t+3..t+5, the abroad "
                      "branch carries more predictive information.",
             weakens="Small n; correlated features.",
             alternatives="Home-market pull of the flag, agent placement effects.",
             limitations="OLS; expanding window; 5 nations."))


def plot_ablation(abl) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.6))
    full = abl[abl.variant == "full_elo_dom_abr"].sort_values("lag")
    ndom = abl[abl.variant == "remove_domestic"].sort_values("lag")
    nabr = abl[abl.variant == "remove_abroad"].sort_values("lag")
    x = np.arange(len(full))
    ax.bar(x - 0.22, full["mae_pooled"], 0.22, label="Full: Elo+dom+abr",
           color="#0f766e")
    ax.bar(x, ndom["mae_pooled"], 0.22, label="Remove DOMESTIC",
           color="#d97706")
    ax.bar(x + 0.22, nabr["mae_pooled"], 0.22, label="Remove ABROAD",
           color="#7c3aed")
    ax.set_xticks(x)
    ax.set_xticklabels([f"t+{l}" for l in full["lag"]])
    ax.set_ylabel("MAE (future Elo delta)")
    ax.set_title("M-P2-03 — feature ablation: Elo + domestic + abroad")
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    emit(OUT, "M-P2-03_feature_ablation", abl, fig,
         standard_md(
             "M-P2-03 feature ablation",
             shows="Out-of-time MAE for [Elo+dom(estic)+abr(oad)] vs removing either "
                   "family.",
             does_not_show="Permutation of single features; average treatment effects.",
             supports="The family whose removal raises MAE most is the informative one.",
             weakens="Elasticity is small; dataset is 70 rows.",
             alternatives="Collinearity of domestic/abroad minutes.",
             limitations="OLS; expanding window; descriptive."))


def plot_oot_scatter(preds) -> None:
    p = preds.dropna(subset=["actual", "pred"])
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.scatter(p["actual"], p["pred"], s=40, alpha=0.7, color="#0f766e")
    lim = [min(p["actual"].min(), p["pred"].min()) - 5,
           max(p["actual"].max(), p["pred"].max()) + 5]
    ax.plot(lim, lim, ls="--", color="0.4", lw=1)
    r = float(np.corrcoef(p["actual"], p["pred"])[0, 1])
    ax.set_xlabel("actual future Elo delta (t+3)")
    ax.set_ylabel("predicted future Elo delta (M3)")
    ax.set_title(f"M-P2-04 — out-of-time predictions, t+3 (Pearson r = {r:.2f})")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    emit(OUT, "M-P2-04_oot_predictions", p, fig,
         standard_md(
             "M-P2-04 out-of-time predictions",
             shows="Expanding-window M3 (domestic + abroad features) predictions of "
                   "the t+3 Elo delta vs actual.",
             does_not_show="Dominance of any single country.",
             supports="If dots follow the 45deg line, the features carry signal; if "
                      "flat, they add nothing to chance.",
             weakens="Outliers from individual country-seasons.",
             alternatives="Season-to-season Elo noise.",
             limitations="n ~ 60; OLS."))


def plot_loco(cmp) -> None:
    loco = pd.read_csv(OUT / "P2_loco_per_country.csv")
    m = "P2-M3_domestic_plus_abroad"
    d = loco[(loco.model == m) & (loco.lag == 3)]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(d["left_out_country"], d["mae"], color="#0f766e", alpha=0.85)
    ax.set_ylabel("MAE when country held out (t+3)")
    ax.set_title("M-P2-05 — leave-one-country-out (M3, t+3)")
    ax.grid(axis="y", alpha=0.3)
    for i, rr in d.reset_index().iterrows():
        ax.text(i, rr["mae"] + 0.4, f"n={int(rr['n'])}", ha="center", fontsize=8)
    fig.tight_layout()
    emit(OUT, "M-P2-05_loco", d, fig,
         standard_md(
             "M-P2-05 leave-one-country-out",
             shows="MAE for each country predicted by a model trained on the other "
                   "four (M3, t+3).",
             does_not_show="A single pooled 'retrained' estimate of our research "
                           "hypothesis.",
             supports="Countries that predict poorly from the others expose "
                      "between-country vs within-country signal.",
             weakens="One country (e.g. France) carrying the pooled correlation "
                     "would show here as a big bar.",
             alternatives="Small sample drives the single-country error.",
             limitations="n=14 per country; OLS trained on 4x14."))


def plot_germany(preds, df) -> None:
    y3 = df[["country", "season", "elo", "target_elo_delta_3y"]].rename(
        columns={"target_elo_delta_3y": "actual_ref"})
    m = preds.merge(y3, on=["country", "season"], how="left")
    m["actual"] = m["actual_ref"]
    g = m[m["country"] == "Germany"].sort_values("season").dropna(
        subset=["actual", "pred"])
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(g["season"], g["elo"], lw=1.8, color="#111827", label="actual Elo")
    ax.plot(g["season"], g["elo"] + g["actual"], marker="o", lw=1.6,
            color="#1f3b6b", label="future Elo (actual), t+3")
    ax.plot(g["season"], g["elo"] + g["pred"], marker="s", ls="--", lw=1.3,
            color="#c8102e", label="future Elo (pred, M3), t+3")
    ax.set_title("M-P2-06 — Germany: actual future Elo vs predictions (M3, t+3)")
    ax.set_xlabel("season")
    ax.set_ylabel("Elo")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    emit(OUT, "M-P2-06_germany_future_elo", g, fig,
         standard_md(
             "M-P2-06 Germany future Elo",
             shows="Germany's Elo, its realised t+3 Elo, and M3 predictions from the "
                   "development features.",
             does_not_show="Causation; effects of injuries/qualification draws.",
             supports="Whether the model's trajectory matches the 2016-2020 decline.",
             weakens="Any single-country fit can be coincidental.",
             alternatives="Tournament shocks; regeneration years.",
             limitations="One country; OLS."))


if __name__ == "__main__":
    main()