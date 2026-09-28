"""Shared helpers for publication-quality charts (PNG + CSV + MD sidecar).

Every chart is emitted as a triplet:
  <name>.png   -- the figure
  <name>.csv   -- the exact data plotted (long format, ready to re-plot)
  <name>.md    -- short interpretation: FACT / OBSERVATION / HYPOTHESIS,
                  supports/weakens, alternatives, limitations.

RULE (do not violate): descriptive only. No causality. Counterexamples are
kept and reported, never hidden.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

# Canonical citizenship -> analysis country (ONE place, validated).
# player_club_season / player_club_season_abroad carry citizenship as
# (country_of_citizenship name, citizenship_code code). Focus nations use
# codes DE/EN/ES/IT/FR. England is EN (not GB) in transfermarkt citizenship.
# Derived from citizenship, NEVER from league_country (where the player plays).
CITIZENSHIP_TO_COUNTRY = {
    "DE": "Germany",
    "EN": "England",
    "ES": "Spain",
    "IT": "Italy",
    "FR": "France",
}


def country_from_citizenship(df: pd.DataFrame,
                             code_col: str = "citizenship_code",
                             name_col: str = "country_of_citizenship") -> pd.DataFrame:
    """Add a canonical analysis `country` column from citizenship columns.

    Prefers the citizenship code (validated) and falls back to the citizenship
    name for any code that maps to a focus nation. Never infers country from
    league_country. Emits a validation sidecar (codes seen vs mapped).
    """
    out = df.copy()
    has_code = code_col in out.columns
    has_name = name_col in out.columns
    if has_code:
        out["country"] = out[code_col].astype(str).map(CITIZENSHIP_TO_COUNTRY)
    if has_name:
        name_map = dict(zip(out["country"].astype(str), out[name_col].astype(str)))
        # keep names for the focus set when code mapping is present
        out["country"] = out["country"].fillna(
            out[code_col].astype(str).map(
                {"DE": "Germany", "EN": "England", "ES": "Spain",
                 "IT": "Italy", "FR": "France"}))
    # unresolved focus citizens stay NaN so they are never silently dropped
    return out

# Citizenship_code -> canonical analysis country.
# VALIDATED against dataset/processed/problem_2/*.csv (distinct values confirmed
# present: DE, EN, ES, IT, FR). Do NOT derive country from league_country —
# a German playing in England must stay Germany.
CITIZENSHIP_COUNTRY = {
    "DE": "Germany",
    "EN": "England",
    "ES": "Spain",
    "IT": "Italy",
    "FR": "France",
}

CITIZENSHIP_NAME = {
    "DE": "Germany",
    "EN": "England",
    "ES": "Spain",
    "IT": "Italy",
    "FR": "France",
}

# Canonical mapping: citizenship_code -> analysis country.
# VALIDATED against dataset/processed/problem_2/player_club_season.csv
# (distinct codes present: DE, EN, ES, IT, FR).
# England uses EN in the source (not GB). Do NOT infer country from
# league_country for nationals-abroad analysis — league_country is where the
# player PLAYS, citizenship_code is who they ARE.
CITIZENSHIP_TO_COUNTRY = {
    "DE": "Germany",
    "EN": "England",
    "ES": "Spain",
    "IT": "Italy",
    "FR": "France",
}

FOCUS_COUNTRIES = ["Germany", "England", "Spain", "Italy", "France"]


def emit(folder: Path, name: str, data: pd.DataFrame,
         fig=None, md_text: str | None = None) -> list[Path]:
    """Save .csv (always) and optional .png/.md to `folder`.

    Returns the list of written paths.
    """
    folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if data is not None:
        csv_path = folder / f"{name}.csv"
        data.to_csv(csv_path, index=False)
        written.append(csv_path)
    if fig is not None:
        png_path = folder / f"{name}.png"
        fig.savefig(png_path, dpi=160, bbox_inches="tight")
        plt.close(fig)
        written.append(png_path)
    if md_text is not None:
        md_path = folder / f"{name}.md"
        md_path.write_text(md_text.strip() + "\n", encoding="utf-8")
        written.append(md_path)
    return written


def standard_md(title: str, *, shows: str, does_not_show: str,
                supports: str, weakens: str, alternatives: str,
                limitations: str) -> str:
    """Build the FACT/OBSERVATION/HYPOTHESIS interpretation text block."""
    return f"""# {title}

**FACT (what the data shows).** {shows}

**OBSERVATION (what the graph DOES NOT show).** {does_not_show}

**HYPOTHESIS (descriptive, not causal).** {supports}

**Where this WEAKENS the opportunity hypothesis.** {weakens}

**Alternative explanations.** {alternatives}

**Data limitations.** {limitations}
"""
