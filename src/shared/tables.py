"""Cached loaders for the raw transfermarkt/eloratings CSVs (read-only)."""

from __future__ import annotations

import gzip
from functools import lru_cache
from pathlib import Path

import pandas as pd

RAW_TM = Path(__file__).resolve().parents[1] / "dataset" / "raw" / "transfermarkt-datasets"
RAW_ELO = Path(__file__).resolve().parents[1] / "dataset" / "raw" / "eloratings"


@lru_cache(maxsize=16)
def tm(table: str) -> pd.DataFrame:
    p = RAW_TM / f"{table}.csv.gz"
    return pd.read_csv(gzip.open(p, "rt", encoding="utf-8"), low_memory=False)


def elo_year(year: int) -> pd.DataFrame:
    p = RAW_ELO / f"{year}.tsv"
    if not p.exists():
        return pd.DataFrame(columns=["rank", "code", "elo"])
    rows = []
    txt = p.read_text(encoding="utf-8-sig", errors="replace")
    for line in txt.splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[2].strip():
            rows.append({"rank": parts[1], "code": parts[2], "elo": parts[3]})
    return pd.DataFrame(rows)


def elo_world() -> pd.DataFrame:
    p = RAW_ELO / "World.tsv"
    rows = []
    for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) >= 4 and parts[2].strip():
            rows.append({"rank": parts[1], "code": parts[2], "elo": parts[3]})
    return pd.DataFrame(rows)


def elo_team_names() -> dict[str, str]:
    p = RAW_ELO / "en.teams.tsv"
    out = {}
    for line in p.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0].strip():
            out[parts[0]] = parts[1]
    return out