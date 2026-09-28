"""Download the full World Football Elo Ratings history from eloratings.net.

Endpoints (public TSV snapshots, no auth, no JS required):
  - https://www.eloratings.net/World.tsv       current full table (all teams)
  - https://www.eloratings.net/<year>.tsv      end-of-year table for `year` (1901-...)
  - https://www.eloratings.net/en.teams.tsv    team-code -> printable name

Usage:
  .venv\\Scripts\\python.exe scripts\\download\\download_eloratings.py [--years 1901..2026]

Writes: dataset/raw/eloratings/{World.tsv, en.teams.tsv, <year>.tsv, SHA256SUMS}
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from shared import downloader as dl  # noqa: E402
from shared.catalog import upsert_source, write_sha256sums  # noqa: E402
from shared.config import RAW  # noqa: E402
from shared.logutil import add_file_handler, setup_log  # noqa: E402

log = setup_log("nti.eloratings")
add_file_handler(log, REPO_ROOT / "records" / "download_eloratings.log")

BASE = "https://www.eloratings.net"
DEST = RAW / "eloratings"

YEAR_FIRST = 1901
YEAR_LAST = datetime.now().year  # current year snapshot may be partial


def fetch_year(year: int, sleep_s: float = 0.5):
    url = f"{BASE}/{year}.tsv"
    dest = DEST / f"{year}.tsv"
    res = dl.download(url, dest, max_attempts=4, retry_sleep=3.0, verbose_ok=False)
    if res["status"] == "failed":
        log.error("year %s failed (removing if partial)", year)
        if dest.exists():
            dest.unlink()
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default=f"{YEAR_FIRST}..{YEAR_LAST}")
    args = ap.parse_args()

    a, _, b = args.years.partition("..")
    years = list(range(int(a), int(b) + 1))

    DEST.mkdir(parents=True, exist_ok=True)
    dl.download(f"{BASE}/en.teams.tsv", DEST / "en.teams.tsv")
    dl.download(f"{BASE}/World.tsv", DEST / "World.tsv")

    ok, failed = 0, []
    for y in years:
        res = fetch_year(y)
        if res["status"] == "failed":
            failed.append(y)
        else:
            ok += 1
        time.sleep(0.3)

    # Light sanity validation: parse each TSV into (code, elo)
    problems = []
    for f in sorted(DEST.glob("*.tsv")):
        if f.name in ("en.teams.tsv", "World.tsv"):
            continue
        try:
            txt = f.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            problems.append(f.name)
            continue
        n_teams = 0
        for line in txt.splitlines():
            parts = line.split("\t")
            if len(parts) >= 4 and parts[2].isprintable():
                n_teams += 1
        if n_teams < 100:
            problems.append(f"{f.name}:teams={n_teams}")

    checksum = write_sha256sums(DEST)
    upsert_source({
        "source_id": "eloratings",
        "source_name": "World Football Elo Ratings",
        "source_url": "https://www.eloratings.net/",
        "provider": "Kirill Bulygin / eloratings.net",
        "data_type": "national-team Elo ratings (year-end and live)",
        "problem_usage": "problem_1 (+ problem_2 national-team outcomes)",
        "countries": "worldwide (190+ active teams; historical incl. defunct)",
        "competitions": "all international A matches aggregated into ratings",
        "start_date": "1901",
        "end_date": str(YEAR_LAST),
        "retrieval_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "retrieval_method": "direct HTTPS GET of public TSV endpoints (0.3-0.5s delays)",
        "license": "permissive reuse policy documented by eloratings.net; credit required",
        "terms_notes": "Ratings derived from public sources (rsssf etc.). Site publishes the TSV endpoints used by its own front-end; keep request rate low.",
        "raw_path": "dataset/raw/eloratings",
        "checksum": f"SHA256SUMS at {checksum.relative_to(REPO_ROOT).as_posix()}",
        "notes": f"yearly TSVs {years[0]}-{years[-1]}; ok={ok} failed={failed}; sanity problems={problems}",
    })

    cov = {"years": years, "ok": ok, "failed": failed,
           "fetched_at": datetime.now().isoformat(timespec="seconds")}
    (DEST / "coverage.json").write_text(json.dumps(cov, indent=2), encoding="utf-8")
    log.info("elo download done: ok=%s failed=%s problems=%s", ok, failed, problems)
    return 0 if not failed and not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())