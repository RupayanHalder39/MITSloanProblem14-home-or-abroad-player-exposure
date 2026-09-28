"""PROBLEM 2 — STAGE 1, B2/B3: expanded multi-country ABROAD panel + models.

ANALYSIS B (NEVER merged with the original five-country ANALYSIS A).

Panel (`dataset/processed/modeling/problem2_expanded_abroad_panel.csv`) — one
row per (nation, season) for GROUP A nations and all eligible GROUP B nations
from `data/quality_reports/PROBLEM2_NATION_COVERAGE.md`:
  - abroad_elite_minutes / abroad_u23_elite_minutes / abroad_elite_nationals
    (uniform rule: elite-club minutes in top-5 leagues where the league country
    is NOT the player's own country; for GROUP B that is their entire top-5
    exposure)
  - total_top5_elite_minutes (domestic+abroad for GROUP A; abroad-only for
    GROUP B — every valid observation, never an invented domestic metric)
  - current Elo, season, future Elo deltas t+1..t+5
  - GROUP B domestic columns are NaN (unobserved), never 0.

Models (time-aware expanding-window, OLS):
  P2-E0  current Elo only
  P2-E1  abroad exposure only      [abroad_elite_minutes, abroad_u23_elite_minutes,
                                    abroad_elite_nationals]
  P2-E2  Elo + abroad              (E0 + E1 features)
  P2-E3  Elo + abroad U23          [elo, abroad_u23_elite_minutes]

Primary question (PART C, P2-Q2): does ABROAD add predictive information
BEYOND current Elo (E2 vs E0 on out-of-time MAE)?

Outputs (eda_outputs/modeling/problem_2_expanded/):
  problem2_expanded_abroad_panel.csv (copy of the panel for QA)
  P2_expanded_comparison.csv
  P2_expanded_loco_lag3.csv
  E-P2-01..04  (PNG+CSV+MD triplets)
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

from shared.config import PROCESSED, PROBLEM1, PROBLEM2, EDA_OUTPUTS  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402
from scripts.models.models_common import (  # noqa: E402
    pooled_metrics,
    rollorigin_predictions,
    summarize_rollorigin,
    loco_predictions,
    summarize_loco,
)
from scripts.eda.pub_common import emit, standard_md  # noqa: E402

log = setup_log("problem2_expanded_panel")
add_file_handler(log, REPO_ROOT / "records" / "problem2_expanded_panel.log")

MODELING = PROCESSED / "modeling"
OUT = EDA_OUTPUTS / "modeling" / "problem_2_expanded"
LAGS = [1, 2, 3, 4, 5]
MIN_TRAIN = 40

ABR_FEATURES = ["abroad_elite_minutes", "abroad_u23_elite_minutes",
                "abroad_elite_nationals"]

FEATURE_SETS = {
    "P2-E0_elo": ["elo"],
    "P2-E1_abroad": ABR_FEATURES,
    "P2-E2_elo_abroad": ["elo"] + ABR_FEATURES,
    "P2-E3_elo_abroad_u23": ["elo", "abroad_u23_elite_minutes"],
}
ORDER = ["P2-E0_elo", "P2-E1_abroad", "P2-E2_elo_abroad", "P2-E3_elo_abroad_u23"]
COLORS = {"P2-E0_elo": "#9ca3af", "P2-E1_abroad": "#e11d48",
          "P2-E2_elo_abroad": "#0f766e", "P2-E3_elo_abroad_u23": "#d97706"}


def build_panel() -> pd.DataFrame:
    pcs = pd.read_csv(PROBLEM2 / "player_club_season.csv")
    p1 = pd.read_csv(PROBLEM1 / "national_team_season.csv")
    cov = pd.read_csv(PROCESSED / ".." / "quality_reports" / "problem2_nation_coverage.csv")
    eligible = set(cov[cov["eligible_for_expanded_panel"]]["nat_team_code"])
    codes = list(eligible)

    p1 = p1.set_index(["nat_team_code", "year"])
    rows = []
    for code in codes:
        g = pcs[pcs["citizenship_code"] == code]
        if g.empty:
            continue
        name_mode = g["country_of_citizenship"].mode().iloc[0]
        for season in sorted(int(s) for s in g["season"].dropna().unique()):
            sg = g[g["season"] == season]
            abroad = sg[~sg["domestic"].astype(bool)]
            abroad_el = abroad[abroad["any_elite"] == 1]
            domestic_el = sg[sg["domestic"].astype(bool) & (sg["any_elite"] == 1)]
            has_own_league = bool(domestic_el.shape[0] > 0)
            elo = p1.loc[(code, season), "elo"] if (code, season) in p1.index else np.nan
            rec = {
                "country": name_mode, "nat_team_code": code, "season": season,
                "group": "GROUP_A" if has_own_league else "GROUP_B",
                "abroad_elite_minutes": float(abroad_el["minutes"].sum()),
                "abroad_u23_elite_minutes": float(
                    abroad_el[abroad_el["is_u23"]]["minutes"].sum()),
                "abroad_elite_nationals": int(abroad_el["player_id"].nunique()),
                "domestic_elite_minutes": (float(domestic_el["minutes"].sum())
                                           if has_own_league else np.nan),
                "elo": elo,
            }
            rec["total_top5_elite_minutes"] = (
                (rec["abroad_elite_minutes"]
                 + (rec["domestic_elite_minutes"] or 0.0))
                if has_own_league else rec["abroad_elite_minutes"])
            for lag in LAGS:
                rec[f"target_elo_delta_{lag}y"] = (
                    p1.loc[(code, season + lag), "elo"] - elo
                    if (code, season + lag) in p1.index else np.nan)
            rows.append(rec)
    df = pd.DataFrame(rows).sort_values(
        ["nat_team_code", "season"]).reset_index(drop=True)
    df.to_csv(MODELING / "problem2_expanded_abroad_panel.csv", index=False)
    log.info("expanded panel: %d nations, %d rows, seasons %s",
             df["nat_team_code"].nunique(), len(df),
             sorted(df["season"].unique()))
    return df


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = build_panel()

    cmp_rows = []
    preds_store = {}
    for lag in LAGS:
        tgt = f"target_elo_delta_{lag}y"
        for name, feats in FEATURE_SETS.items():
            preds = rollorigin_predictions(df, tgt, feats, "season",
                                           min_train=MIN_TRAIN)
            preds_store[f"{lag}__{name}"] = preds
            s = summarize_rollorigin(preds)
            cmp_rows.append({
                "lag": lag, "model": name,
                "n_total": s["n_total"].iloc[0] if len(s) else np.nan,
                "test_times": int(s["test_times"].iloc[0]) if len(s) else 0,
                "mae_pooled": s["mae_pooled"].iloc[0] if len(s) else np.nan,
                "rmse_pooled": s["rmse_pooled"].iloc[0] if len(s) else np.nan,
                "pearson_pooled": s["pearson_pooled"].iloc[0] if len(s) else np.nan,
                "spearman_pooled": s["spearman_pooled"].iloc[0] if len(s) else np.nan,
                "delta_mae_vs_E0": np.nan,
            })
            log.info("expanded %-22s lag %d mae=%.2f rmse=%.2f r=%.2f n=%.0f",
                     name, lag, cmp_rows[-1]["mae_pooled"],
                     cmp_rows[-1]["rmse_pooled"],
                     cmp_rows[-1]["pearson_pooled"], cmp_rows[-1]["n_total"])
    for r in cmp_rows:
        e0 = next(x for x in cmp_rows if x["lag"] == r["lag"]
                  and x["model"] == "P2-E0_elo")
        r["delta_mae_vs_E0"] = r["mae_pooled"] - e0["mae_pooled"]
    cmp = pd.DataFrame(cmp_rows)
    cmp.to_csv(OUT / "P2_expanded_comparison.csv", index=False)

    # ---------------- LOCO stability (lag 3 only; not forced beyond) --------
    loco_rows = []
    for name in FEATURE_SETS:
        lp = loco_predictions(df, "target_elo_delta_3y", FEATURE_SETS[name],
                              "country", sorted(df["country"].unique()))
        s_loco = summarize_loco(lp, sorted(df["country"].unique()))
        if len(s_loco):
            loco_rows.append({"model": name, "mae_loco_pooled": s_loco["mae_pooled"].iloc[0],
                              "rmse_loco_pooled": s_loco["rmse_pooled"].iloc[0],
                              "n_loco": s_loco["n_total"].iloc[0]})
            log.info("expanded LOCO lag3 %-22s mae=%.2f n=%d", name,
                     s_loco["mae_pooled"].iloc[0], s_loco["n_total"].iloc[0])
    loco_df = pd.DataFrame(loco_rows)
    loco_df.to_csv(OUT / "P2_expanded_loco_lag3.csv", index=False)

    # ---------------- charts ----------------
    plot_mae_by_lag(cmp)
    plot_delta_vs_e0(cmp)
    plot_oot(preds_store["3__P2-E2_elo_abroad"])
    plot_loco(loco_df)

    print("expanded panel script complete ->", OUT)
    log.info("E2 vs E0 delta_mae by lag: %s",
             cmp[cmp.model == "P2-E2_elo_abroad"].delta_mae_vs_E0.round(2).tolist())


# ---------------------------------------------------------------------------
def plot_mae_by_lag(cmp) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for m in ORDER:
        d = cmp[cmp.model == m].sort_values("lag")
        ax.plot(d["lag"], d["mae_pooled"], marker="o", lw=1.8, color=COLORS[m],
                label=m.replace("P2-E", "E"))
    ax.set_xlabel("lag (years)")
    ax.set_ylabel("MAE (future Elo delta)")
    ax.set_title("E-P2-01 — expanded panel: MAE by lag and model")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    emit(OUT, "E-P2-01_mae_by_lag", cmp, fig,
         standard_md(
             "E-P2-01 expanded-panel MAE by lag and model",
             shows="Expanding-window MAE for the four expanded-panel models "
                   "(Elo-only, abroad-only, Elo+abroad, Elo+abroad-U23) at "
                   "t+1..t+5 across ~90 nations.",
             does_not_show="Original five-country run (ANALYSIS B only, never "
                           "merged with ANALYSIS A).",
             supports="If E0 (Elo-only) sits below the abroad-bearing models, "
                      "abroad exposure does not beat current Elo here either.",
             weakens="Large pool, larger n: even modest MAE gaps are more "
                     "reliable than in the 5-country run.",
             alternatives="Between-country vs within-country variation "
                          "(decomposed separately).",
             limitations="OLS; expanding window; GROUP B domestic unobserved."))


def plot_delta_vs_e0(cmp) -> None:
    d = cmp[cmp.model != "P2-E0_elo"].pivot_table(
        index="model", columns="lag", values="delta_mae_vs_E0")
    d = d.reindex(index=["P2-E1_abroad", "P2-E2_elo_abroad", "P2-E3_elo_abroad_u23"])
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    for j, m in enumerate(d.index):
        ax.plot(d.columns, d.loc[m], marker="o", label=m.replace("P2-E", "E"),
                color=COLORS[m])
    ax.axhline(0, color="0.4", ls="--", lw=1)
    ax.set_xlabel("lag (years)")
    ax.set_ylabel("ΔMAE vs Elo-only (E0); positive = better than Elo")
    ax.set_title("E-P2-02 — does ABROAD add beyond current Elo? (expanded panel)")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)
    fig.tight_layout()
    emit(OUT, "E-P2-02_delta_vs_elo", d.reset_index(), fig,
         standard_md(
             "E-P2-02 delta MAE vs Elo-only",
             shows="Signed MAE difference vs the Elo-only model at each lag for "
                   "the abroad-bearing models.",
             does_not_show="RMSE/correlation (in CSV).",
             supports="Positive values mean the abroad model beats current Elo "
                      "on OOT MAE.",
             weakens="Negative values mean abroad exposure adds NO error "
                     "reduction beyond current Elo (mirrors the 5-country "
                     "ablation at short lags).",
             alternatives="Decomposition of between/within variation.",
             limitations="Pooled, not per-group."))


def plot_oot(preds) -> None:
    p = preds.dropna(subset=["actual", "pred"])
    fig, ax = plt.subplots(figsize=(8.5, 5))
    ax.scatter(p["actual"], p["pred"], s=6, alpha=0.4, color="#0f766e")
    lim = [p["actual"].min() - 5, max(p["actual"].max(), p["pred"].max()) + 5]
    ax.plot(lim, lim, ls="--", color="0.4", lw=1)
    r = float(np.corrcoef(p["actual"], p["pred"])[0, 1])
    ax.set_xlabel("actual future Elo delta (t+3)")
    ax.set_ylabel("predicted future Elo delta (E2)")
    ax.set_title(f"E-P2-03 — expanded-panel OOT predictions, t+3 (r={r:.2f})")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    emit(OUT, "E-P2-03_oot_predictions", p, fig,
         standard_md(
             "E-P2-03 OOT predictions",
             shows="E2 (Elo + abroad) expanding-window predictions of the t+3 "
                   "delta vs actual across the expanded pool.",
             does_not_show="Whether the abroad term itself is informative "
                           "(E-P2-02 answers that).",
             supports="A horizontal band implies crude predictions no better "
                      "than Elo persistence.",
             weakens="A 45-degree cloud supports genuine directional signal.",
             alternatives="Between/within decomposition.",
             limitations="Pooled OLS; all countries share one slope."))


def plot_loco(loco_df) -> None:
    d = loco_df.set_index("model").reindex(ORDER)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar([m.replace("P2-E", "E") for m in d.index], d["mae_loco_pooled"],
           color=[COLORS[m] for m in d.index], alpha=0.85)
    ax.set_ylabel("LOCO pooled MAE (t+3)")
    ax.set_title("E-P2-04 — leave-one-country-out stability (expanded, t+3)")
    ax.grid(axis="y", alpha=0.3)
    for i, (_, r) in enumerate(d.iterrows()):
        ax.text(i, r["mae_loco_pooled"] + 0.3, f"n={int(r['n_loco'])}",
                ha="center", fontsize=8)
    fig.tight_layout()
    emit(OUT, "E-P2-04_loco_stability", loco_df, fig,
         standard_md(
             "E-P2-04 LOCO stability",
             shows="Pooled MAE when each country is fully held out (t+3), "
                   "averaged across the pool.",
             does_not_show="Whether abroad adds value (see E-P2-02).",
             supports="Small within-model variation across held-out countries "
                      "indicates the pooled pattern is not one-country-driven.",
             weakens="If E0 and E2 are close under LOCO, any E2 advantage "
                     "shrinks when countries are truly unseen.",
             alternatives="Per-group (A vs B) splits.",
             limitations="One lag only; OLS."))


if __name__ == "__main__":
    main()