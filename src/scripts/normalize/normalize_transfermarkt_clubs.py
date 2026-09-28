"""Normalize transfermarkt data to top-5 league club-season tables (PROBLEM 2).

Stage 1 of transfermarkt normalization. Produces (dataset/interim/transfermarkt/):
  top5_matches.csv     game-level rows for the five big leagues
  club_season.csv      recomputed final standings per (league, season)
  club_european.csv    per club-season European competition participation
  standings_validation.csv  comparison of recomputed vs game-level recorded positions

Convention: `season` is the STARTING calendar year (e.g., 2013 == 2013/14).
Position tie-breakers: points, goal difference, goals for (documented proxy;
official rules use head-to-head in some leagues).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared.config import INTERIM, TOP5_TM_COMPS  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402
from shared.tables import tm  # noqa: E402

log = setup_log("nti.norm_tm_clubs")
add_file_handler(log, REPO_ROOT / "records" / "normalize_transfermarkt_clubs.log")

OUT = INTERIM / "transfermarkt"
TOP5 = set(TOP5_TM_COMPS)
LEAGUE_COUNTRY = TOP5_TM_COMPS
EURO_COMPS = {
    "CL": "champions_league",
    "EL": "europa_league",
    "UCOL": "conference_league",
}

ROUND_DEPTH = {
    "Group": 0, "group stage": 0, "Group Stage": 0,
    "Round of 32": 1, "Round of 16": 2, "Eighth-finals": 2,
    "Quarter-finals": 3, "Semi-finals": 4, "Final": 5, "final": 5,
}


def _round_depth(s: str | None) -> int | None:
    if not s or pd.isna(s):
        return None
    return ROUND_DEPTH.get(str(s).strip())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    games = tm("games")
    clubs = tm("clubs")

    g = games[games["competition_id"].isin(TOP5)].copy()
    g["season"] = g["season"].astype(int)
    g["date"] = pd.to_datetime(g["date"], errors="coerce")
    log.info("top5 games: %d  seasons %s-%s", len(g), g["season"].min(), g["season"].max())

    matches = g[["game_id", "competition_id", "season", "round", "date",
                 "home_club_id", "away_club_id", "home_club_goals", "away_club_goals",
                 "home_club_name", "away_club_name", "attendance",
                 "home_club_position", "away_club_position"]].copy()
    matches["league_country"] = matches["competition_id"].map(LEAGUE_COUNTRY)
    matches.to_csv(OUT / "top5_matches.csv", index=False)

    # ---- recompute final standings ----
    recs = []
    for (comp, season), sub in g.groupby(["competition_id", "season"]):
        teams = sorted(set(sub["home_club_id"]) | set(sub["away_club_id"]))
        stats = {t: {"P": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0} for t in teams}
        for _, row in sub.iterrows():
            h, a = int(row["home_club_id"]), int(row["away_club_id"])
            hg, ag = int(row["home_club_goals"]), int(row["away_club_goals"])
            for club, gf, ga in ((h, hg, ag), (a, ag, hg)):
                s = stats[club]
                s["P"] += 1; s["GF"] += gf; s["GA"] += ga
                if gf > ga: s["W"] += 1; s["Pts"] += 3
                elif gf == ga: s["D"] += 1; s["Pts"] += 1
                else: s["L"] += 1
        table = pd.DataFrame(stats).T.reset_index().rename(columns={"index": "club_id"})
        table["GD"] = table["GF"] - table["GA"]
        table = table.sort_values(["Pts", "GD", "GF"], ascending=False).reset_index(drop=True)
        table["position"] = table.index + 1
        table["competition_id"] = comp
        table["season"] = season
        recs.append(table)
    final = pd.concat(recs, ignore_index=True)
    final["league_country"] = final["competition_id"].map(LEAGUE_COUNTRY)
    final["club_name"] = final["club_id"].map(clubs.set_index("club_id")["name"])
    final = final[["competition_id", "season", "league_country", "club_id", "club_name",
                   "position", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]]
    final.to_csv(OUT / "club_season.csv", index=False)
    log.info("club_season: %d rows  (team-seasons)", len(final))

    # ---- standings validation: compare final recomputed position vs positional columns ----
    val = []
    for (comp, season), sub in g.groupby(["competition_id", "season"]):
        try:
            last_date = sub["date"].max()
            last = sub[sub["date"] == last_date]
            for _, row in last.iterrows():
                for side in ("home", "away"):
                    val.append({
                        "competition_id": comp, "season": season,
                        "club_id": int(row[f"{side}_club_id"]),
                        "recorded_position": row[f"{side}_club_position"],
                    })
        except Exception:  # noqa: BLE001
            continue
    valdf = pd.DataFrame(val).merge(
        final[["competition_id", "season", "club_id", "position"]],
        on=["competition_id", "season", "club_id"], how="left")
    valdf["match"] = valdf["recorded_position"] == valdf["position"]
    valdf.to_csv(OUT / "standings_validation.csv", index=False)
    ok = valdf["match"].dropna().mean()
    log.info("standings check: %d records, recomputed==recorded for %.1f%%",
             len(valdf), 100 * ok)

# ---- European participation per club-season (big-5 clubs only) ----
    euro = games[games["competition_id"].isin(EURO_COMPS)].copy()
    euro["season"] = euro["season"].astype(int)
    lo, hi = g["season"].min(), g["season"].max()
    euro = euro[(euro["season"] >= lo) & (euro["season"] <= hi)]

    euro_rows = []
    for (comp, season), sub in g.groupby(["competition_id", "season"]):
        for club in (set(sub["home_club_id"]) | set(sub["away_club_id"])):
            euro_rows.append({"league_competition_id": comp, "season": int(season), "club_id": int(club)})
    big5_clubs = pd.DataFrame(euro_rows)
    big5_keys = set(zip(big5_clubs["club_id"], big5_clubs["season"]))

    parts = []
    for comp, col in EURO_COMPS.items():
        e = euro[euro["competition_id"] == comp][
            ["game_id", "season", "round", "date", "home_club_id", "away_club_id",
             "home_club_goals", "away_club_goals"]].copy()
        if e.empty:
            parts.append(pd.DataFrame(columns=["club_id", "season",
                                               f"{col}_games", f"{col}_wins", f"{col}_max_depth"]))
            continue
        ep = e.melt(id_vars=["game_id", "season", "round", "date", "home_club_goals", "away_club_goals"],
                    value_vars=["home_club_id", "away_club_id"], var_name="side", value_name="club_id")
        ep["club_id"] = ep["club_id"].astype(int)
        ep["season"] = ep["season"].astype(int)
        ep = ep.assign(key=list(zip(ep["club_id"], ep["season"])))
        ep = ep[ep["key"].isin(big5_keys)].drop(columns=["key"])
        if ep.empty:
            parts.append(pd.DataFrame(columns=["club_id", "season",
                                               f"{col}_games", f"{col}_wins", f"{col}_max_depth"]))
            continue
        ep["side_club_goals"] = ep.apply(
            lambda r: r["home_club_goals"] if r["side"] == "home_club_id" else r["away_club_goals"], axis=1)
        ep["opp_goals"] = ep.apply(
            lambda r: r["away_club_goals"] if r["side"] == "home_club_id" else r["home_club_goals"], axis=1)
        ep["win"] = ep["side_club_goals"] > ep["opp_goals"]
        ep["depth"] = ep["round"].map(_round_depth)
        agg = ep.groupby(["club_id", "season"]).agg(
            games=("game_id", "size"), wins=("win", "sum"), max_depth=("depth", "max")).reset_index()
        agg.columns = ["club_id", "season", f"{col}_games", f"{col}_wins", f"{col}_max_depth"]
        parts.append(agg)

    eur = big5_clubs
    for p in parts:
        eur = eur.merge(p, on=["club_id", "season"], how="left")
    eur = eur.fillna(0)
    int_cols = [c for c in eur.columns if c.endswith(("_games", "_wins"))]
    for c in int_cols:
        eur[c] = eur[c].astype(int)
    eur["club_name"] = eur["club_id"].map(clubs.set_index("club_id")["name"])
    eur.to_csv(OUT / "club_european.csv", index=False)
    log.info("club_european: %d rows", len(eur))


if __name__ == "__main__":
    main()