"""Manifest + checksum helpers.

Maintains dataset/manifests/sources.csv (STEP 4 of the project brief) and
per-raw-dir SHA256SUMS files. Raw data is never edited by anything here.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import pandas as pd

from shared.config import MANIFESTS

log = logging.getLogger("nti.catalog")

MANIFEST_PATH = MANIFESTS / "sources.csv"

MANIFEST_COLUMNS = [
    "source_id",
    "source_name",
    "source_url",
    "provider",
    "data_type",
    "problem_usage",
    "countries",
    "competitions",
    "start_date",
    "end_date",
    "retrieval_date",
    "retrieval_method",
    "license",
    "terms_notes",
    "raw_path",
    "checksum",
    "notes",
    "recorded_at",
]


def load_sources() -> pd.DataFrame:
    if MANIFEST_PATH.exists():
        return pd.read_csv(MANIFEST_PATH, dtype=str, keep_default_na=False)
    return pd.DataFrame(columns=MANIFEST_COLUMNS)


def upsert_source(record: dict) -> pd.DataFrame:
    """Insert or update (keyed on source_id) a source manifest row."""
    df = load_sources()
    for col in MANIFEST_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    rec = {c: record.get(c, "") or "" for c in MANIFEST_COLUMNS}
    df = df[df["source_id"] != rec["source_id"]]
    df = pd.concat([df, pd.DataFrame([rec])], ignore_index=True)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(MANIFEST_PATH, index=False)
    log.info("manifest upserted source_id=%s rows=%d", rec["source_id"], len(df))
    return df


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_sha256sums(directory: Path) -> Path:
    """Write a SHA256SUMS file listing every file in `directory` (recursive)."""
    directory = Path(directory)
    lines = []
    for p in sorted(directory.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{sha256_file(p)}  {p.relative_to(directory).as_posix()}\n")
    out = directory / "SHA256SUMS"
    out.write_text("".join(lines), encoding="utf-8")
    return out