"""Normalize eloratings yearly TSVs -> long tidy table.

Output (interim):
  dataset/interim/eloratings/elo_long.csv     (nat_team_code, year, elo, rank)
  dataset/interim/eloratings/elo_current.csv  (nat_team_code, elo, rank, name)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared.config import INTERIM  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402
from shared.tables import elo_team_names, elo_world, elo_year  # noqa: E402

log = setup_log("nti.norm_elo")
add_file_handler(log, REPO_ROOT / "records" / "normalize_eloratings.log")

YEARS = range(1901, 2027)  # yearly files we fetched


def main() -> None:
    out_dir = INTERIM / "eloratings"
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = []
    for y in YEARS:
        df = elo_year(y)
        if df.empty:
            continue
        df = df.copy()
        df["year"] = y
        df["elo"] = pd.to_numeric(df["elo"], errors="coerce")
        df = df.dropna(subset=["elo"])
        df["elo"] = df["elo"].astype(int)
        df = df[["code", "year", "rank", "elo"]]
        frames.append(df)
    long = pd.concat(frames, ignore_index=True)
    long = long.sort_values(["code", "year"]).reset_index(drop=True)

    names = elo_team_names()
    long["nat_team_name"] = long["code"].map(names)
    long.to_csv(out_dir / "elo_long.csv", index=False)
    log.info("elo_long: %d rows, %d teams, years %d-%d",
             len(long), long["code"].nunique(), long["year"].min(), long["year"].max())

    cur = elo_world()
    cur["elo"] = pd.to_numeric(cur["elo"], errors="coerce").astype("Int64")
    cur["nat_team_name"] = cur["code"].map(names)
    cur.to_csv(out_dir / "elo_current.csv", index=False)
    log.info("elo_current: %d rows", len(cur))

    # Coherence sanity: Germany should have plausible ratings in 2014 (peak era) and 2024.
    de = long[(long["code"] == "DE") & (long["year"].isin([2009, 2014, 2018, 2024]))]
    log.info("DE elo check:\n%s", de[["year", "rank", "elo"]].to_string(index=False))


if __name__ == "__main__":
    main()