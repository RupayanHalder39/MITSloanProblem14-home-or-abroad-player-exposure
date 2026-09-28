"""Central path + convention configuration.

Every script should import paths from here so the project layout stays
consistent and easily changeable in one place.
"""

from pathlib import Path

from shared import PROJECT_ROOT

ROOT = PROJECT_ROOT

RAW = ROOT / "dataset" / "raw"
INTERIM = ROOT / "dataset" / "interim"
PROCESSED = ROOT / "dataset" / "processed"
PROBLEM1 = PROCESSED / "problem_1"
PROBLEM2 = PROCESSED / "problem_2"
PROCESSED_SHARED = PROCESSED / "shared"

METADATA = ROOT / "dataset" / "metadata"
MAPPINGS = METADATA / "mappings"
MANIFESTS = ROOT / "dataset" / "manifests"
SCHEMAS = ROOT / "dataset" / "schemas"
QUALITY = ROOT / "dataset" / "quality_reports"
DOCS = ROOT / "docs"
EDA_OUTPUTS = ROOT / "eda_outputs"
RECORDS = ROOT / "records"
SCRIPTS = ROOT / "scripts"

# ---------------------------------------------------------------------------
# Research conventions used across the project (documented in docs/METHODOLOGY.md)
# ---------------------------------------------------------------------------

# Focus countries (Problem 1 and Problem 2 scope). Codes follow the project's
# canonical national-team codes (eloratings.net style, ISO 3166-1 alpha-2 where
# available). England uses "EN" (not a sovereign-state ISO code).
FOCUS_COUNTRIES = ["Germany", "England", "Spain", "Italy", "France"]
FOCUS_COUNTRY_CODES = ["DE", "EN", "ES", "IT", "FR"]

# Problem 2: Top-5 European leagues (football-data.co.uk Div codes; Transfermarkt
# competition ids; canonical country).
TOP5_LEAGUES = {
    "D1": "Germany",      # Bundesliga      (football-data.co.uk division code)
    "E0": "England",      # Premier League  (football-data.co.uk division code)
    "SP1": "Spain",       # La Liga         (football-data.co.uk division code)
    "I1": "Italy",        # Serie A         (football-data.co.uk division code)
    "F1": "France",       # Ligue 1         (football-data.co.uk division code)
}

# Transfermarkt competition ids for the same five top divisions.
TOP5_TM_COMPS = {
    "L1": "Germany",    # Bundesliga
    "GB1": "England",   # Premier League
    "ES1": "Spain",     # La Liga
    "IT1": "Italy",     # Serie A
    "FR1": "France",    # Ligue 1
}

# Preferred analysis window (problems explicitly target ~2009/10 onwards,
# but raw coverage differs per source and is documented per source).
ANALYSIS_START_SEASON = 2009  # season label, e.g. 2009 == 2009/10

# Age cutoffs used for "youth" in problem 2.
U23_AGE = 23
U21_AGE = 21

# Temporal lags explored in problem 2.
LAGS = [1, 2, 3, 4, 5]

# Elite-club definitions (see docs/METHODOLOGY.md, STEP 9).
ELITE_DEFINITIONS = {
    "ELITE_A": "top-4 domestic league finish",
    "ELITE_B": "top-6 domestic league finish",
    "ELITE_C": "Champions League participant",
    "ELITE_D": "club Elo above threshold/percentile (sourcely dependent)",
    "ELITE_E": "domestic top-X by multi-year strength (moving 3-season rank avg)",
}