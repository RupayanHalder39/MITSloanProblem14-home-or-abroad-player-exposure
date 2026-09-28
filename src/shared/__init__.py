"""Shared utilities for the National Team Intelligence project."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_root() -> Path:
    return PROJECT_ROOT