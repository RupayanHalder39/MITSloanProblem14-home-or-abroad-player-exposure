"""Download the dcaribou/transfermarkt-datasets release (CC0).

This is the curated, weekly-refreshed dataset that backs the well-known
Kaggle dataset "Football Data from Transfermarkt" (davidcariboo/player-scores).
Official mirror endpoints used by the author's README.

  Base: https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data/<table>.csv.gz

Important caveats (documented in docs/):
  * The dataset is licensed CC0 by its author and redistributed openly; the
    *underlying* data originates from transfermarkt.com pages. Transfermarkt's
    own terms prohibit *direct* scraping and require a formal data request for
    scientific use. Using this CC0 mirror for research is common practice but
    the resulting legal status is not fully clear; see LIMITATIONS.md.
  * None of these tables contain playing minutes (Transfermarkt appearances
    lack minutes) -- appearances are one row per player per match.

Usage:
  .venv\\Scripts\\python.exe scripts\\download\\download_transfermarkt.py

Writes: dataset/raw/transfermarkt-datasets/*.csv.gz (+ SHA256SUMS)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared import downloader as dl  # noqa: E402
from shared.catalog import upsert_source, write_sha256sums  # noqa: E402
from shared.config import RAW  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402

log = setup_log("nti.transfermarkt")
add_file_handler(log, REPO_ROOT / "records" / "download_transfermarkt.log")

BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
DEST = RAW / "transfermarkt-datasets"

TABLES = [
    "competitions",
    "games",
    "clubs",
    "club_games",
    "players",
    "player_valuations",
    "appearances",
    "game_events",
    "game_lineups",
    "transfers",
    "countries",
    "national_teams",
]

# Optional full archive (single duckdb file with all 12 tables).
DUCKDB_URL = f"{BASE}/transfermarkt-datasets.duckdb"


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    results = {}
    for t in TABLES:
        url = f"{BASE}/{t}.csv.gz"
        res = dl.download(url, DEST / f"{t}.csv.gz", max_attempts=4, retry_sleep=5.0)
        results[t] = res["status"]
        log.info("table %s -> %s (%s bytes)", t, res["status"], res["size_bytes"])

    checksum = write_sha256sums(DEST)
    snapshot = {
        "retrieved_at": datetime.now().isoformat(timespec="seconds"),
        "base_url": BASE,
        "tables": results,
        "duckdb_alternative": DUCKDB_URL,
        "duckdb_not_downloaded": True,
    }
    (DEST / "snapshot.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    upsert_source({
        "source_id": "transfermarkt-datasets",
        "source_name": "transfermarkt-datasets (dcaribou) — Kaggle 'Football Data from Transfermarkt'",
        "source_url": "https://github.com/dcaribou/transfermarkt-datasets",
        "provider": "David Caribou (dataset curations); underlying data originates from transfermarkt.com",
        "data_type": "club/player/valuation/appearance/game/national-team tables (CSV)",
        "problem_usage": "problem_1 + problem_2 (squad value, player-club-season, elite exposure)",
        "countries": "worldwide; top-5 European leagues well covered",
        "competitions": "domestic leagues incl. big-5 + international/national team competitions",
        "start_date": "~2000 (valuations); ~2013-14 for full appearances (verification needed per competition)",
        "end_date": "2026-06/07 (author paused updates in mid-July 2026)",
        "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "retrieval_method": "direct HTTPS GET of official release mirror (R2)",
        "license": "CC0 1.0 (dataset as published by author) — see terms_notes",
        "terms_notes": "Dataset CC0 per author. UNDERLYING data originates from transfermarkt.com whose own ToS prohibit direct scraping/redistribution without written consent; scientific data requests offered by Transfermarkt. Legal status of this mirror is gray-area; do not redistribute raw files without advice. Appearances lack minutes.",
        "raw_path": "dataset/raw/transfermarkt-datasets",
        "checksum": f"SHA256SUMS at {checksum.relative_to(REPO_ROOT).as_posix()}",
        "notes": "12 tables fetched as csv.gz; duckdb full archive available but not downloaded. Updates paused by author since ~mid-July 2026.",
    })
    failed = [k for k, v in results.items() if v == "failed"]
    log.info("transfermarkt download done: failed=%s", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())