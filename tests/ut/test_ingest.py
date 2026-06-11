"""Unit tests for kma.tools.ingest helpers and ingest flows.

Documents behavior of _slugify, manifest I/O, frontmatter, ingest_text / ingest_url,
and the tool factory.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from kma.config import Env
from kma.tools import ingest as ingest_mod
from kma.tools.ingest import (
    _build_frontmatter,
    _do_ingest_text,
    _do_ingest_url,
    _read_manifest,
    _slugify,
    _write_manifest,
    create_ingest_tools,
    sync_manifest_from_raw_markdown,
)


def test_slugify_basic() -> None:
    assert _slugify("Hello World") == "hello-world"
    assert _slugify("  Foo_Bar  ") == "foo-bar"


def test_slugify_strips_punctuation_and_truncates() -> None:
    assert _slugify("RAG: Retrieval!?") == "rag-retrieval"
    long = "word-" * 30
    out = _slugify(long)
    assert len(out) <= 80
    assert out.endswith("word")


def test_read_manifest_missing_file(tmp_path: Path) -> None:
    assert _read_manifest(tmp_path) == []


def test_write_read_manifest_roundtrip(tmp_path: Path) -> None:
    data = [{"file": "a.md", "compiled": False}]
    _write_manifest(tmp_path, data)
    assert (tmp_path / ".manifest.json").read_text(encoding="utf-8").strip()
    assert _read_manifest(tmp_path) == data


def test_build_frontmatter_shape() -> None:
    fm = _build_frontmatter("My Title", "https://ex", ["x", "y"], "article")
    assert fm.startswith("---\n")
    assert 'title: "My Title"' in fm
    assert "source: https://ex" in fm
    assert "ingested:" in fm
    assert "tags: [x, y]" in fm
    assert "type: article" in fm
    assert "compiled: false" in fm
    assert fm.endswith("---\n\n")


@patch.object(ingest_mod, "datetime")
def test_build_frontmatter_uses_utc_date(mock_dt: MagicMock) -> None:
    class _Tz:
        pass

    mock_dt.now.return_value.strftime.return_value = "2030-01-15"
    mock_dt.timezone.utc = _Tz()
    fm = _build_frontmatter("T", "s", [], "notes")
    assert "ingested: 2030-01-15" in fm


def test_do_ingest_text_writes_file_and_manifest(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    msg = _do_ingest_text(raw, "Hello Doc", "# Body\n", source="user", tags=["a"], doc_type="notes")
    assert "hello-doc.md" in msg
    f = raw / "hello-doc.md"
    assert f.is_file()
    text = f.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "# Body" in text
    manifest = json.loads((raw / ".manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 1
    assert manifest[0]["file"] == "hello-doc.md"
    assert manifest[0]["title"] == "Hello Doc"
    assert manifest[0]["source"] == "user"
    assert manifest[0]["compiled"] is False


def test_do_ingest_url_without_parallel_key_writes_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ingest_mod, Env.KMA_PARALLEL_API_KEY, None, raising=False)
    raw = tmp_path / "raw"
    raw.mkdir()
    msg = _do_ingest_url(raw, "https://example.com/page", "Example Page", tags=None, doc_type="article")
    assert "stub" in msg.lower() or "Ingested" in msg
    f = raw / "example-page.md"
    assert f.is_file()
    body = f.read_text(encoding="utf-8")
    assert "https://example.com/page" in body
    manifest = _read_manifest(raw)
    assert manifest[0]["source"] == "https://example.com/page"


@patch("parallel.Parallel")
def test_do_ingest_url_with_parallel_writes_extracted(
    mock_parallel_cls: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("kma.config.PARALLEL_API_KEY", "fake-key", raising=False)
    raw = tmp_path / "raw"
    raw.mkdir()
    result_row = MagicMock()
    result_row.full_content = "# Extracted\n\nHello."
    mock_result = MagicMock()
    mock_result.results = [result_row]
    mock_parallel_cls.return_value.beta.extract.return_value = mock_result

    msg = _do_ingest_url(raw, "https://ex.com", "My Article", tags=["t"], doc_type="article")
    assert "content" in msg.lower() or "chars" in msg.lower()
    f = raw / "my-article.md"
    text = f.read_text(encoding="utf-8")
    assert "# Extracted" in text
    assert "Hello." in text


def test_create_ingest_tools_read_manifest_empty(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    tools = create_ingest_tools(raw)
    assert len(tools) == 5
    read_manifest = next(t for t in tools if t.name == "read_manifest")
    out = read_manifest.entrypoint()
    assert "empty" in out.lower() or "No documents" in out


def test_create_ingest_tools_update_manifest_compiled(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_manifest(raw, [{"file": "x.md", "title": "X", "source": "s", "ingested": "t", "compiled": False}])
    tools = create_ingest_tools(raw)
    upd = next(t for t in tools if t.name == "update_manifest_compiled")
    assert upd.entrypoint(filename="x.md") == "Marked as compiled: x.md"
    assert _read_manifest(raw)[0]["compiled"] is True
    assert "Not found" in upd.entrypoint(filename="missing.md")


def test_sync_manifest_from_raw_markdown(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "doc.md").write_text(
        "---\n"
        'title: "My Study"\n'
        "source: https://ex.test/page\n"
        "ingested: 2026-03-01\n"
        "compiled: false\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )
    msg = sync_manifest_from_raw_markdown(raw)
    assert "1" in msg
    m = _read_manifest(raw)
    assert len(m) == 1
    assert m[0]["file"] == "doc.md"
    assert m[0]["title"] == "My Study"
    assert m[0]["source"] == "https://ex.test/page"
    assert m[0]["ingested"] == "2026-03-01T00:00:00Z"
    assert m[0]["compiled"] is False


def test_sync_raw_manifest_from_disk_tool(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "a.md").write_text(
        "---\ntitle: A\nsource: s\ningested: 2026-01-02\ncompiled: true\n---\n",
        encoding="utf-8",
    )
    tools = create_ingest_tools(raw)
    sync_tool = next(t for t in tools if t.name == "sync_raw_manifest_from_disk")
    out = sync_tool.entrypoint()
    assert "Synced" in out
    assert _read_manifest(raw)[0]["compiled"] is True
