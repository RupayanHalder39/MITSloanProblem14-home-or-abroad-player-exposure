"""Build PROCESSED datasets for PROBLEM 2 (domestic elite talent opportunity).

Outputs (dataset/processed/problem_2/):
  club_season.csv                  club-season table + elite-club flags (ELITE_A..E)
  player_club_season.csv           player x club x season with club context & minutes
  country_league_season.csv        per (country, season) domestic/foreign/young breakdown
  national_elite_exposure.csv      total elite exposure (domestic + abroad) per (country, season)
  elite_opportunity.csv            DEOI components + transparent baseline index
  cohesion_components.csv          what we can compute today (documented gaps)
  lagged_national_outcomes.csv     season-t features joined to t+1..t+5 NT outcomes

Conventions (docs/METHODOLOGY.md):
  * season t == season (t)/(t+1); a season labeled 2013 ends mid-2014 and is
    matched to national-team observations at calendar years t+lag.
  * minutes are league minutes for the five top divisions; UCL minutes are a
    separate column.
  * domestic player = country_of_citizenship equals club's league country code.
  * ELITE_A=top-4 finish, ELITE_B=top-6 finish, ELITE_C=UCL participant,
    ELITE_D=rolling-3-season PPG at >=80th pct within league (documented proxy),
    ELITE_E=rolling-3-season average position <= 4.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared.config import INTERIM, PROBLEM1, PROBLEM2, U21_AGE, U23_AGE  # noqa: E402
from shared.names import canonical_country_code  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402

log = setup_log("nti.problem2")
add_file_handler(log, REPO_ROOT / "records" / "build_problem2.log")

IT = INTERIM / "transfermarkt"

LAGS = [1, 2, 3, 4, 5]

# League-country canonical NT codes (national team joins).
COUNTRY_NT_CODE = {"Germany": "DE", "England": "EN", "Spain": "ES", "Italy": "IT", "France": "FR"}


def build_club_season() -> pd.DataFrame:
    cs = pd.read_csv(IT / "club_season.csv")
    eu = pd.read_csv(IT / "club_european.csv")
    df = cs.merge(eu, on=["club_id", "season"], how="left", suffixes=("", "_euro"))
    df["ppg"] = df["Pts"] / df["P"].replace(0, pd.NA)
    df["n_teams"] = df.groupby(["competition_id", "season"])["club_id"].transform("size")
    df["rank_pct"] = df["position"] / df["n_teams"]

    # ELITE_C flag from UCL participation
    df["ELITE_C"] = (df["champions_league_games"] > 0).astype(int)
    # ELITE_A / B
    df["ELITE_A"] = (df["position"] <= 4).astype(int)
    df["ELITE_B"] = (df["position"] <= 6).astype(int)

    # Rolling strength (multi-year) for ELITE_D / ELITE_E
    df = df.sort_values(["competition_id", "club_id", "season"])
    df["ppg_roll3"] = df.groupby(["competition_id", "club_id"])["ppg"].transform(
        lambda s: s.rolling(3, min_periods=1).mean())
    df["pos_roll3"] = df.groupby(["competition_id", "club_id"])["position"].transform(
        lambda s: s.rolling(3, min_periods=1).mean())
    df["ppg_roll3_pct"] = df.groupby(["competition_id", "season"])["ppg_roll3"].transform(
        lambda s: s.rank(pct=True))
    df["ELITE_D"] = (df["ppg_roll3_pct"] >= 0.8).astype(int)
    df["ELITE_E"] = (df["pos_roll3"] <= 4.0).astype(int)

    df["any_elite"] = ((df[["ELITE_A", "ELITE_B", "ELITE_C", "ELITE_D", "ELITE_E"]].sum(axis=1)) > 0).astype(int)
    out_cols = ["club_id", "club_name", "competition_id", "league_country", "season", "position",
                "rank_pct", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "ppg",
                "champions_league_games", "champions_league_wins", "champions_league_max_depth",
                "europa_league_games", "conference_league_games",
                "ELITE_A", "ELITE_B", "ELITE_C", "ELITE_D", "ELITE_E", "any_elite",
                "ppg_roll3", "pos_roll3", "ppg_roll3_pct"]
    df = df[[c for c in out_cols if c in df.columns]]
    df.to_csv(PROBLEM2 / "club_season.csv", index=False)
    log.info("club_season: %d rows", len(df))
    return df


def build_player_club_season(club_s: pd.DataFrame) -> pd.DataFrame:
    pc = pd.read_csv(IT / "player_club_season.csv").rename(columns={"player_club_id": "club_id"})
    ref = pd.read_csv(IT / "players_ref.csv")
    sq = pd.read_csv(IT / "player_season_squad.csv")
    cl = pd.read_csv(IT / "player_champions_league.csv")

    df = pc.merge(ref[["player_id", "position", "sub_position", "position_macro", "dob",
                       "country_of_citizenship", "citizenship_code", "height_in_cm"]],
                  on="player_id", how="left", suffixes=("", "_ref"))
    club_keys = ["club_id", "competition_id", "season"]
    df = df.merge(club_s[club_keys + ["position", "Pts", "ELITE_A", "ELITE_B", "ELITE_C",
                                      "ELITE_D", "ELITE_E", "any_elite", "rank_pct"]],
                  on=club_keys, how="left", suffixes=("", "_club"))
    df = df.merge(sq, on=["player_id", "club_id", "competition_id", "season"], how="left")
    df = df.merge(cl, on=["player_id", "season"], how="left")

    # Market value (transfermarkt, a PROXY) at club+season, and player-season fallback.
    val_club = pd.read_csv(IT / "player_club_season_valuation.csv").rename(
        columns={"current_club_id": "club_id"})
    val_season = pd.read_csv(IT / "player_season_valuation.csv")
    df = df.merge(val_club, on=["player_id", "club_id", "competition_id", "season"],
                  how="left", suffixes=("", "_val"))
    df = df.merge(val_season, on=["player_id", "season"], how="left", suffixes=("", "_any"))

    tm_min = df.groupby(["club_id", "competition_id", "season"])["minutes"].transform("sum")
    df["team_minutes"] = tm_min
    df["minutes_pct_of_team"] = (df["minutes"] / tm_min).fillna(0)
    df["elite_membership"] = df["any_elite"]  # club is elite by at least one definition
    df[["starts", "games_in_squad"]] = df[["starts", "games_in_squad"]].fillna(0)

    out = ["player_id", "name", "position", "sub_position", "position_macro",
           "country_of_citizenship", "citizenship_code", "age_season_end", "is_u21", "is_u23",
           "domestic", "club_id", "club_name" if "club_name" in df.columns else None,
           "competition_id", "league_country", "season",
           "minutes", "appearances", "goals", "assists", "yellow_cards", "red_cards",
           "starts", "games_in_squad", "team_minutes", "minutes_pct_of_team",
           "position_club", "Pts_club", "ELITE_A", "ELITE_B", "ELITE_C", "ELITE_D", "ELITE_E",
           "any_elite", "cl_minutes", "cl_appearances", "cl_goals",
           "market_value_eur", "market_value_eur_any_club"]
    keep = [c for c in out if c is not None and c in df.columns]
    df[[*keep, "rank_pct"]].to_csv(PROBLEM2 / "player_club_season.csv", index=False)
    log.info("player_club_season: %d rows, countries/seasons coverage: "
             "%d countries, %d seasons",
             len(df), df["league_country"].nunique(), df["season"].nunique())
    return df


def build_country_league_season(pcs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (country, season), sub in pcs.groupby(["league_country", "season"]):
        tot = sub["minutes"].sum()
        dom = sub[sub["domestic"]]
        for_ = sub[~sub["domestic"]]
        dom_u21 = dom[dom["is_u21"]]
        dom_u23 = dom[dom["is_u23"]]
        for_u21 = for_[for_["is_u21"]]
        for_u23 = for_[for_["is_u23"]]
        # elite club subsets
        dom_elite_a = dom[dom["ELITE_A"] == 1]
        dom_elite_b = dom[dom["ELITE_B"] == 1]
        dom_elite_c = dom[dom["ELITE_C"] == 1]
        # market value aggregates (PROXY; transfermarkt opinion); club-matched value
        # preferred, else any-club season value, else excluded from the sum.
        dom_val = dom["market_value_eur"].fillna(dom["market_value_eur_any_club"])
        for_val = for_["market_value_eur"].fillna(for_["market_value_eur_any_club"])
        dom_u23_eliteA = dom_u23.merge(
            dom_elite_a[["player_id", "club_id", "competition_id", "season"]].drop_duplicates(),
            on=["player_id", "club_id", "competition_id", "season"], how="inner")
        dom_u23_eliteA_val = dom_u23_eliteA["market_value_eur"].fillna(
            dom_u23_eliteA["market_value_eur_any_club"])
        rows.append({
            "country": country, "season": season,
            "total_minutes": int(tot),
            "domestic_minutes": int(dom["minutes"].sum()),
            "foreign_minutes": int(for_["minutes"].sum()),
            "domestic_share": 0.0 if tot == 0 else dom["minutes"].sum() / tot,
            "foreign_share": 0.0 if tot == 0 else for_["minutes"].sum() / tot,
            "domestic_u21_minutes": int(dom_u21["minutes"].sum()),
            "domestic_u23_minutes": int(dom_u23["minutes"].sum()),
            "foreign_u21_minutes": int(for_u21["minutes"].sum()),
            "foreign_u23_minutes": int(for_u23["minutes"].sum()),
            "domestic_u21_share": 0.0 if tot == 0 else dom_u21["minutes"].sum() / tot,
            "domestic_u23_share": 0.0 if tot == 0 else dom_u23["minutes"].sum() / tot,
            "n_domestic_players": int(dom["player_id"].nunique()),
            "n_foreign_players": int(for_["player_id"].nunique()),
            "n_domestic_u23_players": int(dom_u23["player_id"].nunique()),
            "n_foreign_u23_players": int(for_u23["player_id"].nunique()),
            "domestic_eliteA_minutes": int(dom_elite_a["minutes"].sum()),
            "domestic_eliteB_minutes": int(dom_elite_b["minutes"].sum()),
            "domestic_eliteC_minutes": int(dom_elite_c["minutes"].sum()),
            "domestic_u23_eliteA_minutes": int(dom_u23_eliteA["minutes"].sum()),
            "domestic_u23_eliteA_starts": int(dom_u23_eliteA["starts"].sum()),
            "domestic_u23_eliteB_minutes": int(dom_u23.merge(
                dom_elite_b[["player_id", "club_id", "competition_id", "season"]].drop_duplicates(),
                on=["player_id", "club_id", "competition_id", "season"], how="inner")["minutes"].sum()),
            "domestic_total_value_eur": int(dom_val.sum(skipna=True)),
            "foreign_total_value_eur": int(for_val.sum(skipna=True)),
            "domestic_eliteA_value_eur": int(dom_val[dom_elite_a.index].sum(skipna=True)),
            "domestic_u23_eliteA_value_eur": int(dom_u23_eliteA_val.sum(skipna=True)),
            "n_domestic_players_with_value": int(dom_val.notna().sum()),
        })
    df = pd.DataFrame(rows).sort_values(["country", "season"]).reset_index(drop=True)
    df.to_csv(PROBLEM2 / "country_league_season.csv", index=False)
    log.info("country_league_season: %d rows over %d countries",
             len(df), df["country"].nunique())
    return df


def build_exposure2(pcs: pd.DataFrame) -> pd.DataFrame:
    """Total elite exposure (domestic + abroad) per (country, season).

    For each focus country we look at every national (citizenship match) playing
    ANY top-5 league: minutes in home-league elite clubs (DOMESTIC ELITE
    OPPORTUNITY) vs minutes at elite clubs in the other four leagues (ABROAD).
    """
    rows = []
    for ctry in ["Germany", "England", "Spain", "Italy", "France"]:
        code = COUNTRY_NT_CODE[ctry]
        nat = pcs[pcs["citizenship_code"] == code]
        for (season,), g in nat.groupby(["season"]):
            home = g[g["league_country"] == ctry]
            abroad = g[g["league_country"] != ctry]
            home_elite = home[home["any_elite"] == 1]
            abroad_elite = abroad[abroad["any_elite"] == 1]
            home_u23_elite = home_elite[home_elite["is_u23"]]
            abroad_u23_elite = abroad_elite[abroad_elite["is_u23"]]
            home_u23 = home[home["is_u23"]]
            rows.append({
                "country": ctry, "season": season,
                "nat_team_code": code,
                "total_elite_exposure_minutes": int(home_elite["minutes"].sum())
                                                 + int(abroad_elite["minutes"].sum()),
                "domestic_elite_minutes": int(home_elite["minutes"].sum()),
                "abroad_elite_minutes": int(abroad_elite["minutes"].sum()),
                "abroad_elite_share": 0.0 if (len(home_elite) + len(abroad_elite)) == 0
                else abroad_elite["minutes"].sum() / (home_elite["minutes"].sum()
                                                      + abroad_elite["minutes"].sum()),
                "domestic_elite_nationals": int(home_elite["player_id"].nunique()),
                "abroad_elite_nationals": int(abroad_elite["player_id"].nunique()),
                "total_u23_elite_exposure_minutes": int(home_u23_elite["minutes"].sum())
                                                     + int(abroad_u23_elite["minutes"].sum()),
                "domestic_u23_elite_minutes": int(home_u23_elite["minutes"].sum()),
                "abroad_u23_elite_minutes": int(abroad_u23_elite["minutes"].sum()),
                "domestic_u23_total_minutes": int(home_u23["minutes"].sum()),
            })
    df = pd.DataFrame(rows).sort_values(["country", "season"]).reset_index(drop=True)
    df.to_csv(PROBLEM2 / "national_elite_exposure.csv", index=False)
    log.info("national_elite_exposure: %d rows", len(df))
    return df


def build_deoi(country_df: pd.DataFrame) -> pd.DataFrame:
    """DEOI + transparent normalized baseline (components preserved)."""
    df = country_df.copy()
    comps = ["domestic_u23_eliteA_minutes", "domestic_u23_eliteB_minutes",
             "domestic_u23_eliteA_starts"]
    std = {}
    for c in comps:
        s = df[c].astype(float)
        std[c] = (s - s.mean()) / (s.std(ddof=0) if s.std(ddof=0) > 0 else 1.0)
    # baseline index: unweighted average of standardized components (documented, no claim of truth)
    if std:
        df["DEOI_baseline_zscore"] = sum(std.values()) / len(std)
        df["DEOI_baseline_minmax"] = (df["DEOI_baseline_zscore"]
                                      - df["DEOI_baseline_zscore"].min()) / (
                                          df["DEOI_baseline_zscore"].max()
                                          - df["DEOI_baseline_zscore"].min())
    df.to_csv(PROBLEM2 / "elite_opportunity.csv", index=False)
    log.info("elite_opportunity (DEOI) components+baseline: %d rows; components=%s", len(df), comps)
    return df


def build_lagged() -> None:
    """Join country-season P2 features to future national-team outcomes (t+1..t+5).

    Uses processed/problem_1/national_team_season.csv (elo) and tournament_team.csv.
    NT year mapping: season t (t/t+1) -> calendar year t+lag.
    """
    p1 = pd.read_csv(PROBLEM1 / "national_team_season.csv")
    tourn = pd.read_csv(PROBLEM1 / "tournament_team.csv")
    country_df = pd.read_csv(PROBLEM2 / "country_league_season.csv")
    expos = pd.read_csv(PROBLEM2 / "national_elite_exposure.csv")
    deoi = pd.read_csv(PROBLEM2 / "elite_opportunity.csv")

    feat = country_df.merge(
        expos.rename(columns={"nat_team_code": "_x"}),
        on=["country", "season"], how="left", suffixes=("", "_exp"))
    feat = feat.merge(
        deoi[["country", "season", "DEOI_baseline_zscore", "DEOI_baseline_minmax",
              "domestic_u23_eliteA_minutes", "domestic_u23_eliteA_starts",
              "domestic_u23_eliteB_minutes"]],
        on=["country", "season"], how="left", suffixes=("", "_deoi"))
    rows = []
    for _, row in feat.iterrows():
        country = row["country"]
        code = COUNTRY_NT_CODE.get(country)
        if not code:
            continue
        t = int(row["season"])
        rec = {"country": country, "nat_team_code": code, "season": t,
               "DEOI_baseline_zscore": row.get("DEOI_baseline_zscore", float("nan")),
               "DEOI_baseline_minmax": row.get("DEOI_baseline_minmax", float("nan")),
               "domestic_u23_eliteA_minutes": row.get("domestic_u23_eliteA_minutes", 0),
               "domestic_u23_eliteB_minutes": row.get("domestic_u23_eliteB_minutes", 0),
               "domestic_u23_share": row.get("domestic_u23_share", 0),
               "domestic_share": row.get("domestic_share", 0),
               "total_elite_exposure_minutes": row.get("total_elite_exposure_minutes", 0),
               "domestic_elite_minutes": row.get("domestic_elite_minutes", 0),
               "abroad_elite_minutes": row.get("abroad_elite_minutes", 0),
               "abroad_elite_share": row.get("abroad_elite_share", 0)}
        for lag in LAGS:
            elo_t = p1[(p1["nat_team_code"] == code) & (p1["year"] == t)]
            elo_row = p1[(p1["nat_team_code"] == code) & (p1["year"] == t + lag)]
            if not elo_row.empty:
                rec[f"target_elo_t{lag}"] = elo_row.iloc[0]["elo"]
                base = elo_t.iloc[0]["elo"] if not elo_t.empty else None
                rec[f"target_elo_delta_{lag}y"] = (elo_row.iloc[0]["elo"] - base) if base is not None else None
            tour = tourn[(tourn["nat_team_code"] == code) & (tourn["tournament_year"] == t + lag)]
            if not tour.empty:
                rec[f"target_tournament_stage_t{lag}"] = tour.iloc[0]["round_reached"]
                rec[f"target_tournament_played_t{lag}"] = tour.iloc[0]["played"]
                rec[f"target_tournament_wins_t{lag}"] = tour.iloc[0]["wins"]
            rec[f"target_any_tournament_t{lag}"] = 1 if not tour.empty else 0
        rows.append(rec)
    df = pd.DataFrame(rows)
    # add raw elo level + change over window for convenience (documented as target columns)
    df.to_csv(PROBLEM2 / "lagged_national_outcomes.csv", index=False)
    log.info("lagged_national_outcomes: %d rows", len(df))


def main() -> None:
    PROBLEM2.mkdir(parents=True, exist_ok=True)
    club_s = build_club_season()
    pcs = build_player_club_season(club_s)
    cslc = build_country_league_season(pcs)
    build_exposure2(pcs)
    build_deoi(cslc)
    build_lagged()


if __name__ == "__main__":
    main()