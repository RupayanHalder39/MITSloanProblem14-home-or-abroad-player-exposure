"""Robust HTTP downloader with caching, retries, backoff and checksums.

Used by every download script so that all acquisitions are resumable,
idempotent and verify-able (SHA-256). Never hammers servers: default to a
single pass with polite sleeps; concurrent passes are opt-in.
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

log = logging.getLogger("nti.downloader")

DEFAULT_HEADERS = {
    "User-Agent": "NationalTeamIntelligence/0.1 (academic research pipeline; contact: local)",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _retryable(err) -> bool:
    """True if a request exception looks transient (timeouts, 5xx, 429)."""
    if isinstance(err, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    resp = getattr(err, "response", None)
    if resp is not None and resp.status_code in (429,) or getattr(resp, "status_code", None) in (500, 502, 503, 504):
        return True
    return False


def download(
    url: str,
    dest: Path,
    *,
    expected_sha256: str | None = None,
    max_attempts: int = 4,
    retry_sleep: float = 5.0,
    backoff: float = 2.0,
    chunk: int = 1 << 20,
    timeout: int = 90,
    verbose_ok: bool = False,
) -> dict:
    """Download `url` to `dest` atomically.

    Returns a record dict: {url, path (str), size_bytes, sha256, status}.
    status in {"skipped" (already present & valid), "downloaded", "verified", "failed"}.
    """
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if dest.exists():
        actual = sha256_file(dest)
        if expected_sha256 is None or actual == expected_sha256:
            return {"url": url, "path": str(dest), "size_bytes": dest.stat().st_size,
                    "sha256": actual, "status": "skipped"}
        log.warning("Existing file %s has wrong checksum (%s != %s); re-downloading",
                    dest, actual, expected_sha256)
        dest.unlink()

    partial = dest.with_suffix(dest.suffix + ".part")
    attempt = 0
    while attempt < max_attempts:
        attempt += 1
        try:
            with requests.get(url, headers=DEFAULT_HEADERS, stream=True,
                              timeout=timeout, allow_redirects=True) as r:
                r.raise_for_status()
                total = 0
                with open(partial, "wb") as f:
                    for block in r.iter_content(chunk):
                        if block:
                            f.write(block)
                            total += len(block)
            actual = sha256_file(partial)
            if expected_sha256 is not None and actual != expected_sha256:
                raise RuntimeError(f"checksum mismatch after download: {actual}")
            partial.replace(dest)
            if verbose_ok:
                log.info("downloaded %s (%d bytes)", url, total)
            return {"url": url, "path": str(dest), "size_bytes": dest.stat().st_size,
                    "sha256": actual, "status": "downloaded"}
        except Exception as exc:  # noqa: BLE001 - any failure is retried below
            if partial.exists():
                partial.unlink(missing_ok=True)
            if attempt >= max_attempts or not _retryable(exc):
                log.error("download failed for %s (%d/%d): %s", url, attempt, max_attempts, exc)
                break
            sleep = retry_sleep * (backoff ** (attempt - 1))
            log.warning("transient failure %s, retry %d/%d in %.0fs: %s",
                        url, attempt, max_attempts, sleep, exc)
            time.sleep(sleep)

    return {"url": url, "path": str(dest), "size_bytes": -1, "sha256": "", "status": "failed"}


def fetch_text(url: str, *, timeout: int = 60) -> str:
    """Small helper for lightweight text/binary fetches with basic retries."""
    last = None
    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
            r.raise_for_status()
            return r.text
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt < 3:
                time.sleep(2 * attempt)
    raise RuntimeError(f"fetch_text failed for {url}: {last}")