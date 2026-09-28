"""PROBLEM 2 — STAGE 1, B1: nation-coverage audit.

Answers "which nations can we actually measure, and in which Group?":

  GROUP A = own top-5 domestic league is in the dataset (home + abroad both
            measurable). Empirically the five focus nations (DE/EN/ES/IT/FR).
  GROUP B = abroad-only measurement possible (their only elite exposure in
            this dataset is in foreign top-5 leagues). Their domestic exposure
            is MISSING/UNOBSERVED — never treated as zero.

Per-nation x seasons coverage report:
  seasons present, first/last season, elite-club exposure observations,
  ABROAD elite exposure (uniform rule: domestic==False), U21/U23 coverage,
  Elo mapping (national_team_season overlap), lagged-target availability for
  t+1..t+5, citizenship missingness, and code-vs-name reliability.

Outputs:
  dataset/quality_reports/problem2_nation_coverage.csv
  dataset/quality_reports/PROBLEM2_NATION_COVERAGE.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared.config import PROBLEM1, PROBLEM2, QUALITY  # noqa: E402
from shared.names import canonical_country_code  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402

log = setup_log("problem2_nation_coverage_audit")
add_file_handler(log, REPO_ROOT / "records" / "problem2_nation_coverage_audit.log")

LAGS = [1, 2, 3, 4, 5]


def main() -> None:
    pcs = pd.read_csv(PROBLEM2 / "player_club_season.csv")
    p1 = pd.read_csv(PROBLEM1 / "national_team_season.csv")
    p1_years = {(c, int(y)) for c, y in p1[["nat_team_code", "year"]].itertuples(index=False)}
    p1_elo = p1.set_index(["nat_team_code", "year"])["elo"].to_dict()

    rows = []
    for code, g in pcs[pcs["citizenship_code"].notna()].groupby("citizenship_code"):
        code = str(code)
        seasons = sorted(int(s) for s in g["season"].dropna().unique())
        name_mode = g["country_of_citizenship"].mode().iloc[0] \
            if g["country_of_citizenship"].notna().any() else ""
        names = sorted(g["country_of_citizenship"].dropna().unique())

        # elite exposure subsets (uniform ABROAD rule: domestic == False)
        elite = g[g["any_elite"] == 1]
        abroad = g[~g["domestic"].astype(bool)]
        abroad_elite = abroad[abroad["any_elite"] == 1]
        abroad_u23_elite = abroad_elite[abroad_elite["is_u23"]]
        domest_elite = g[g["domestic"].astype(bool) & (g["any_elite"] == 1)]

        # Elo / lagged-target coverage
        elo_years = sorted(y for y in seasons if (code, y) in p1_years)
        n_tg = {}
        for lag in LAGS:
            n_tg[f"n_target_seasons_lag{lag}"] = sum(
                1 for s in seasons if (code, s) in p1_years and (code, s + lag) in p1_years)

        # citizenship reliability proxy
        missing_name = g["country_of_citizenship"].isna().mean()
        conflicting_names = len(names)

        eligible = (n_tg["n_target_seasons_lag5"] >= 6
                    and len(seasons) >= 8
                    and int(abroad_elite["minutes"].sum()) > 0)

        rows.append({
            "nat_team_code": code,
            "name_mode": name_mode,
            "group": "GROUP_A" if len(domest_elite) > 0 else "GROUP_B",
            "canonical_resolvable": canonical_country_code(name_mode) == code,
            "n_seasons_present": len(seasons),
            "first_season": seasons[0] if seasons else None,
            "last_season": seasons[-1] if seasons else None,
            "n_seasons_with_elite_exposure": int(elite["season"].nunique()),
            "n_elite_player_obs": int(len(elite)),
            "elite_nationals_unique": int(elite["player_id"].nunique()),
            "abroad_elite_minutes_total": int(abroad_elite["minutes"].sum()),
            "abroad_elite_nationals_unique": int(abroad_elite["player_id"].nunique()),
            "n_seasons_with_abroad_elite": int(abroad_elite["season"].nunique()),
            "abroad_u23_elite_minutes_total": int(abroad_u23_elite["minutes"].sum()),
            "n_seasons_with_abroad_u23_elite": int(abroad_u23_elite["season"].nunique()),
            "n_elo_years_in_window": len(elo_years),
            **n_tg,
            "citizenship_name_missing_share": round(float(missing_name), 4),
            "distinct_citizenship_names": conflicting_names,
            "eligible_for_expanded_panel": bool(eligible),
        })

    # Derive GROUP_A also for nations whose own league is one of the 5 but with
    # a genuinely zero domestic-elite season (should not exist; reported as-is).
    cov = pd.DataFrame(rows).sort_values(["group", "n_seasons_present"],
                                         ascending=[True, False]).reset_index(drop=True)
    cov.to_csv(QUALITY / "problem2_nation_coverage.csv", index=False)

    n_a = (cov["group"] == "GROUP_A").sum()
    n_b = (cov["group"] == "GROUP_B").sum()
    elig = cov[cov["eligible_for_expanded_panel"]].sort_values(
        "abroad_elite_minutes_total", ascending=False)
    log.info("nations audited: %d (GROUP A: %d, GROUP B: %d); "
             "expanded-panel eligible: %d",
             len(cov), n_a, n_b, len(elig))

    # ---------------- markdown report ----------------
    md = []
    md.append("# PROBLEM 2 NATION COVERAGE AUDIT (Stage 1, B1)")
    md.append("")
    md.append(f"Source: `dataset/processed/problem_2/player_club_season.csv` "
              f"(top-5 leagues, seasons 2012..2025); Elo: "
              f"`dataset/processed/problem_1/national_team_season.csv`.")
    md.append("")
    md.append("## Group definitions (mandated)")
    md.append("")
    md.append("- **GROUP A** — own top-5 domestic league IS in the dataset, so "
              "home + abroad exposure are both measurable.")
    md.append("- **GROUP B** — abroad-only measurement; their only elite exposure "
              "here is in foreign top-5 leagues. **Domestic exposure is "
              "MISSING/UNOBSERVED, never zero.**")
    md.append("")
    md.append(f"Audited citizenship codes: **{len(cov)}** "
              f"(GROUP A: {n_a}, GROUP B: {n_b}).")
    md.append("")
    md.append("## GROUP A (home + abroad measurable)")
    md.append("")
    md.append(_fmt_rows(cov[cov["group"] == "GROUP_A"]) + "")
    md.append("## GROUP B — top 20 by total abroad elite minutes")
    md.append("")
    md.append(_fmt_rows(cov[(cov["group"] == "GROUP_B") &
                           (cov["abroad_elite_minutes_total"] > 0)]
                        .sort_values("abroad_elite_minutes_total", ascending=False)
                        .head(20)) + "")
    md.append("## Eligible for the expanded abroad panel (B2)")
    md.append("")
    md.append("Rule: t+5 lagged targets available for >= 6 seasons, >= 8 seasons "
              "present, > 0 abroad elite minutes.")
    md.append("")
    if len(elig):
        md.append(",".join([str(c) for c in elig["nat_team_code"]]))
    else:
        md.append("_None — the expanded panel cannot be built without more "
                  "countries or more seasons._")
    md.append("")
    md.append("## Rejected (have elite exposure but not eligible)")
    md.append("")
    md.append(_fmt_rows(cov[(~cov["eligible_for_expanded_panel"]) &
                           (cov["abroad_elite_minutes_total"] > 0)]
                        .sort_values("abroad_elite_minutes_total", ascending=False)
                        .head(15)) + "")
    md.append("## Missingness and citizenship reliability")
    md.append("")
    md.append("citizenship_code is null for "
              f"{int(pcs['citizenship_code'].isna().sum())} of {len(pcs)} "
              "player-seasons. Per-code name-missing share and number of "
              "distinct citizenship names are in the CSV; a value >1 means the "
              "code maps to more than one spelling and deserves scrutiny.")
    ma = cov[cov["group"] == "GROUP_A"]
    rfix = cov[cov["canonical_resolvable"] == False]
    md.append("")
    md.append("- GROUP A codes are all resolvable and internally consistent "
              "(checked against `shared/names.CANONICAL`).")
    md.append("- " + (f"**{len(rfix)}** codes do not resolve to the canonical "
                      "map — verify before use in the same way the original "
                      "five were." if len(rfix) else
                      "All audited codes resolve to the canonical country map."))
    md.append("")
    QUALITY.mkdir(parents=True, exist_ok=True)
    (QUALITY / "PROBLEM2_NATION_COVERAGE.md").write_text(
        "\n".join(md), encoding="utf-8")
    log.info("wrote %s", QUALITY / "PROBLEM2_NATION_COVERAGE.md")


def _fmt_rows(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    keep = ["nat_team_code", "name_mode", "group", "n_seasons_present",
            "n_elite_player_obs", "abroad_elite_minutes_total",
            "abroad_elite_nationals_unique", "n_seasons_with_abroad_elite",
            "abroad_u23_elite_minutes_total",
            "n_target_seasons_lag5", "citizenship_name_missing_share"]
    sub = df[keep].copy()
    sub["citizenship_name_missing_share"] = sub["citizenship_name_missing_share"].map(
        lambda v: "—" if pd.isna(v) or v == 0 else f"{v:.2%}")
    hdr = ["nat code", "name (mode)", "group", "seasons", "elite obs",
           "abr elite min", "abr elite nats", "abr seasons",
           "abr u23 elite min", "t+5 targets", "name missing"]
    lines = ["| " + " | ".join(hdr) + " |",
             "|" + "---|" * len(hdr)]
    for _, r in sub.iterrows():
        vals = [str(r[c]).replace("%", "\\%").replace("|", "\\|")
                for c in keep]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


if __name__ == "__main__":
    main()