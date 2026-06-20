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
    _coerce_tags,
    _do_ingest_text,
    _do_ingest_url,
    _read_manifest,
    _slugify,
    _write_manifest,
    apply_raw_frontmatter_to_text,
    append_manifest_entry,
    create_ingest_tools,
    first_h1_title,
    has_km_raw_frontmatter,
    has_yaml_frontmatter,
    iter_markdown_files,
    manifest_entry_compiled,
    mark_manifest_compiled,
    strip_yaml_frontmatter,
    sync_manifest_from_raw_markdown,
    title_from_markdown,
)


def test_coerce_tags_json_string() -> None:
    assert _coerce_tags('["apache-kafka", "event-streaming"]') == ["apache-kafka", "event-streaming"]


def test_coerce_tags_list() -> None:
    assert _coerce_tags(["a", "b"]) == ["a", "b"]


def test_coerce_tags_comma_separated() -> None:
    assert _coerce_tags("a, b, c") == ["a", "b", "c"]


def test_create_ingest_tools_ingest_text_accepts_json_tags(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    tools = create_ingest_tools(raw)
    ingest_text = tools[1]
    msg = ingest_text.entrypoint(
        title="Kafka",
        content="# Kafka\n",
        source="https://kafka.apache.org/intro/",
        tags='["apache-kafka", "event-streaming"]',
        doc_type="article",
    )
    assert "kafka.md" in msg.lower() or "Kafka" in msg
    text = (raw / "kafka.md").read_text(encoding="utf-8")
    assert "apache-kafka" in text


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
    monkeypatch.delenv(Env.KMA_PARALLEL_API_KEY, raising=False)
    monkeypatch.delenv("PARALLEL_API_KEY", raising=False)
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
    monkeypatch.setenv(Env.KMA_PARALLEL_API_KEY, "fake-key")
    raw = tmp_path / "raw"
    raw.mkdir()
    result_row = MagicMock()
    result_row.excerpts = ["# Extracted\n\nHello."]
    result_row.full_content = None
    mock_result = MagicMock()
    mock_result.results = [result_row]
    mock_parallel_cls.return_value.beta.extract.return_value = mock_result

    msg = _do_ingest_url(raw, "https://ex.com", "My Article", tags=["t"], doc_type="article")
    assert "content" in msg.lower() or "chars" in msg.lower()
    f = raw / "my-article.md"
    text = f.read_text(encoding="utf-8")
    assert "# Extracted" in text
    assert "Hello." in text
    mock_parallel_cls.return_value.beta.extract.assert_called_once()
    call_kwargs = mock_parallel_cls.return_value.beta.extract.call_args.kwargs
    assert call_kwargs["urls"] == ["https://ex.com"]
    assert call_kwargs["excerpts"] == {"max_chars_per_result": 8000}


def test_create_ingest_tools_read_manifest_empty(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    tools = create_ingest_tools(raw)
    assert len(tools) == 5
    read_manifest = next(t for t in tools if t.name == "read_manifest")
    out = read_manifest.entrypoint()
    assert "empty" in out.lower() or "No documents" in out


def test_mark_manifest_compiled_and_entry_compiled(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_manifest(raw, [{"file": "x.md", "title": "X", "source": "s", "ingested": "t", "compiled": False}])
    assert manifest_entry_compiled(raw, "x.md") is False
    assert manifest_entry_compiled(raw, "missing.md") is False
    assert mark_manifest_compiled(raw, "x.md") is True
    assert manifest_entry_compiled(raw, "x.md") is True
    assert mark_manifest_compiled(raw, "missing.md") is False


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


def test_has_yaml_frontmatter() -> None:
    assert has_yaml_frontmatter("---\ntitle: x\n---\n\n# Hi\n") is True
    assert has_yaml_frontmatter("# No frontmatter\n") is False


def test_has_km_raw_frontmatter() -> None:
    raw = "---\ntitle: T\nsource: s\ningested: 2026-01-01\ncompiled: false\n---\n\n# Body\n"
    assert has_km_raw_frontmatter(raw) is True
    assert has_km_raw_frontmatter("---\ntitle: wiki only\n---\n") is False


def test_strip_yaml_frontmatter() -> None:
    text = "---\ntitle: T\n---\n\n# Body\n"
    assert strip_yaml_frontmatter(text) == "# Body\n"
    assert strip_yaml_frontmatter("# Plain\n") == "# Plain\n"


def test_first_h1_title_and_title_from_markdown() -> None:
    assert first_h1_title("# Hello World\n") == "Hello World"
    assert first_h1_title("no heading") is None
    assert title_from_markdown("# Kafka\n", fallback_stem="fallback") == "Kafka"
    assert title_from_markdown("plain", fallback_stem="my-doc") == "My Doc"


def test_iter_markdown_files_skips_excluded_dirs(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.md").write_text("# A\n", encoding="utf-8")
    (root / "sub").mkdir()
    (root / "sub" / "b.md").write_text("# B\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "c.md").write_text("# C\n", encoding="utf-8")
    paths = iter_markdown_files(root)
    rels = {p.relative_to(root).as_posix() for p in paths}
    assert rels == {"a.md", "sub/b.md"}


def test_apply_raw_frontmatter_to_text() -> None:
    new_text, title, skip = apply_raw_frontmatter_to_text(
        "# Hello\n",
        source="local",
        tags=["a"],
        doc_type="article",
        fallback_title="Fallback",
    )
    assert skip is None
    assert title == "Hello"
    assert new_text is not None
    assert new_text.startswith("---\n")
    assert "compiled: false" in new_text
    assert "# Hello" in new_text

    _, _, skip2 = apply_raw_frontmatter_to_text(
        "---\ntitle: x\n---\n\n# Body\n",
        source="s",
        tags=[],
        doc_type="article",
        force=False,
    )
    assert skip2 == "already has YAML frontmatter"


def test_append_manifest_entry_updates_existing(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    _write_manifest(raw, [{"file": "a.md", "title": "Old", "source": "s", "ingested": "t", "compiled": True}])
    append_manifest_entry(raw, "a.md", "New", "src", reset_compiled=True)
    entry = _read_manifest(raw)[0]
    assert entry["title"] == "New"
    assert entry["source"] == "src"
    assert entry["compiled"] is False
