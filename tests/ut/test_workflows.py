"""Unit tests for workflow helpers (manifest, background scheduling)."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from kma.tools.ingest import list_uncompiled_file_ids
from kma.workflows.background import schedule_wiki_refresh


def test_list_uncompiled_file_ids(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    manifest = [
        {"file": "a.md", "compiled": False},
        {"file": "b.md", "compiled": True},
        {"file": "c.md", "compiled": False},
    ]
    (raw / ".manifest.json").write_text(json.dumps(manifest))

    ids = list_uncompiled_file_ids(raw)
    assert ids == ["a.md", "c.md"]


def test_list_uncompiled_file_ids_empty_manifest(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    assert list_uncompiled_file_ids(raw) == []


def test_schedule_wiki_refresh_dedup(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KMA_AUTO_COMPILE_AFTER_RESEARCH", "1")
    calls: list[list[str]] = []

    def fake_refresh(ctx: Path, file_ids: list[str]) -> None:
        calls.append(list(file_ids))
        time.sleep(0.05)

    monkeypatch.setattr("kma.workflows.background.refresh_wiki_from_raw", fake_refresh)

    msg1 = schedule_wiki_refresh(tmp_path, ["topic-a.md"])
    msg2 = schedule_wiki_refresh(tmp_path, ["topic-a.md"])
    assert "Scheduled" in msg1
    assert "already scheduled" in msg2

    deadline = time.time() + 2.0
    while len(calls) < 1 and time.time() < deadline:
        time.sleep(0.02)
    assert calls == [["topic-a.md"]]


def test_schedule_wiki_refresh_disabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KMA_AUTO_COMPILE_AFTER_RESEARCH", "0")
    monkeypatch.delenv("KMA_PARALLEL_API_KEY", raising=False)
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
    msg = schedule_wiki_refresh(tmp_path, ["x.md"])
    assert "disabled" in msg.lower()


def test_schedule_wiki_refresh_empty_ids(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("KMA_AUTO_COMPILE_AFTER_RESEARCH", "1")
    msg = schedule_wiki_refresh(tmp_path, [])
    assert "skipped" in msg.lower()
