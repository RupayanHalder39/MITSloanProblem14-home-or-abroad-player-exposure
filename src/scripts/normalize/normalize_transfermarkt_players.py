"""Normalize transfermarkt appearances/players -> player-club-season tables (PROBLEM 2).

Stage 2 of transfermarkt normalization. Produces (dataset/interim/transfermarkt/):
  players_ref.csv          canonical player reference (dedup, attributes)
  player_club_season.csv   per (player, club, league-season) aggregates (league only)
  player_champions_league.csv  per (player, season) CL minutes/games
  player_season_squad.csv  per (player, season) squad presence/starts from lineups (league)

Conventions:
  * season = starting calendar year (2013 == 2013/14).
  * age computed at 30 June of the season-end year (season+1).
  * u21/u23 flags use U21_AGE/U23_AGE from shared.config (inclusive cutoffs).
  * "domestic" = country_of_citizenship == league country (documented proxy for
    national-team eligibility; see LIMITATIONS for ambiguity).
  * league minutes counted from top-5 league matches only; CL minutes are kept
    in a separate table.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared.config import INTERIM, TOP5_TM_COMPS, U21_AGE, U23_AGE  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402
from shared.names import canonical_country_code  # noqa: E402
from shared.tables import tm  # noqa: E402

log = setup_log("nti.norm_tm_players")
add_file_handler(log, REPO_ROOT / "records" / "normalize_transfermarkt_players.log")

OUT = INTERIM / "transfermarkt"
TOP5 = set(TOP5_TM_COMPS)

LEAGUE_COUNTRY_CODE = {"L1": "DE", "GB1": "EN", "ES1": "ES", "IT1": "IT", "FR1": "FR"}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    players = tm("players")
    app = tm("appearances")
    games = tm("games")[["game_id", "season", "competition_id"]]

    # ---- players_ref ----
    p = players.copy()
    p["dob"] = pd.to_datetime(p["date_of_birth"], errors="coerce")
    p["citizenship_code"] = p["country_of_citizenship"].map(canonical_country_code)
    p["birth_country_code"] = p["country_of_birth"].map(canonical_country_code)
    p["position_macro"] = p["position"].map({
        "Goalkeeper": "GK", "Defender": "DF", "Midfield": "MF", "Attack": "FW"}).fillna("UNK")
    ref = p[["player_id", "first_name", "last_name", "name", "position", "sub_position",
             "position_macro", "dob", "country_of_citizenship", "citizenship_code",
             "country_of_birth", "birth_country_code", "height_in_cm", "foot",
             "current_national_team_id", "market_value_in_eur", "highest_market_value_in_eur"]].copy()
    ref.to_csv(OUT / "players_ref.csv", index=False)
    log.info("players_ref: %d rows (citizenship mapped %.1f%%)",
             len(ref), 100 * ref["citizenship_code"].ne("").mean())

    # ---- appearances per-match snapshot (league) ----
    gm = games.rename(columns={"season": "season_tm", "competition_id": "comp_tm"})
    a = app.merge(gm, on="game_id", how="inner")
    a = a[a["competition_id"].isin(TOP5)].copy()
    a["season"] = a["season_tm"].astype(int)
    a = a.merge(ref[["player_id", "dob", "citizenship_code", "position_macro", "name"]],
                on="player_id", how="left")
    a["league_country"] = a["competition_id"].map(TOP5_TM_COMPS)

    log.info("league appearances rows: %d", len(a))
    a.to_csv(OUT / "player_appearance_league.csv", index=False)
    del a  # free memory

    # aggregations: per (player, club, league, season)
    agg = app.merge(gm[["game_id", "comp_tm", "season_tm"]], on="game_id", how="inner")
    agg = agg[agg["competition_id"].isin(TOP5)]
    agg["season"] = agg["season_tm"].astype(int)
    g = agg.groupby(["player_id", "player_club_id", "competition_id", "season"]).agg(
        minutes=("minutes_played", "sum"),
        appearances=("game_id", "size"),
        goals=("goals", "sum"),
        assists=("assists", "sum"),
        yellow_cards=("yellow_cards", "sum"),
        red_cards=("red_cards", "sum"),
    ).reset_index()
    g = g.merge(ref[["player_id", "dob", "citizenship_code", "position_macro", "name"]],
                on="player_id", how="left")
    g["league_country"] = g["competition_id"].map(TOP5_TM_COMPS)
    g["season_end"] = pd.to_datetime((g["season"] + 1).astype(str) + "-06-30")
    g["age_season_end"] = ((g["season_end"] - g["dob"]).dt.days / 365.25).round(2)
    g["is_u21"] = g["age_season_end"] <= U21_AGE
    g["is_u23"] = g["age_season_end"] <= U23_AGE

    def _dom(row) -> bool:
        return row["citizenship_code"] == LEAGUE_COUNTRY_CODE.get(row["competition_id"], "@@")

    g["domestic"] = g.apply(_dom, axis=1)
    g.to_csv(OUT / "player_club_season.csv", index=False)
    log.info("player_club_season: %d rows", len(g))

    # ---- Champions League player-season minutes ----
    cl = app.merge(gm[["game_id", "comp_tm", "season_tm"]], on="game_id", how="inner")
    cl = cl[cl["competition_id"] == "CL"]
    cl["season"] = cl["season_tm"].astype(int)
    if cl.empty:
        log.warning("no CL appearances found; check competition coverage")
    clg = cl.groupby(["player_id", "season"]).agg(
        cl_minutes=("minutes_played", "sum"),
        cl_appearances=("game_id", "size"),
        cl_goals=("goals", "sum"),
    ).reset_index()
    clg.to_csv(OUT / "player_champions_league.csv", index=False)
    log.info("player_champions_league: %d rows (seasons %s-%s)",
             len(clg), clg["season"].min(), clg["season"].max())

    # ---- squad presence / starts from lineups (league games) ----
    lin = tm("game_lineups")
    linm = lin.merge(games[["game_id", "competition_id", "season"]], on="game_id", how="inner")
    linm = linm[linm["competition_id"].isin(TOP5)]
    linm["season"] = linm["season"].astype(int)
    linm["is_starting"] = (linm["type"] == "starting_lineup").astype(int)
    sq = linm.groupby(["player_id", "club_id", "competition_id", "season"]).agg(
        games_in_squad=("game_id", "size"),
        starts=("is_starting", "sum"),
    ).reset_index()
    sq.to_csv(OUT / "player_season_squad.csv", index=False)
    log.info("player_season_squad: %d rows", len(sq))


if __name__ == "__main__":
    main()