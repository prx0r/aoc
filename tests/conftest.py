"""Isolate the SQLite store per test — builds must never touch store/aoc.db."""

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("AOC_DB", str(tmp_path / "aoc-test.db"))
    yield
    monkeypatch.delenv("AOC_DB", raising=False)
