"""Compiler shared context manifest and split-root file tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from kma.tools.builder import build_compiler_tools
from kma.tools.compiler_fs import create_compiler_file_tools, use_labelled_raw_paths
from kma.tools.ingest import (
    _write_manifest,
    create_compiler_manifest_tools,
)


def test_use_labelled_raw_paths_default_single() -> None:
    ctx = Path("/tmp/kma_ctx")
    roots = [("raw", Path("/tmp/kma_ctx/raw"))]
    assert use_labelled_raw_paths(roots, Path("/tmp/kma_ctx")) is False


def test_use_labelled_raw_paths_external_single(tmp_path: Path) -> None:
    ext = tmp_path / "docs"
    ext.mkdir()
    ctx = tmp_path / "context"
    ctx.mkdir()
    assert use_labelled_raw_paths([("studies", ext.resolve())], ctx) is True


def test_use_labelled_raw_paths_two_roots(tmp_path: Path) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    ctx = tmp_path / "c"
    ctx.mkdir()
    assert use_labelled_raw_paths([("a", a), ("b", b)], ctx) is True


def test_merged_read_manifest_two_roots(tmp_path: Path) -> None:
    ctx = tmp_path / "context"
    ctx.mkdir()
    r1 = tmp_path / "docs"
    r2 = ctx / "raw"
    r1.mkdir()
    r2.mkdir(parents=True)
    _write_manifest(
        ctx,
        [
            {
                "file_id": "studies:a.md",
                "file": "a.md",
                "title": "A",
                "source": "s",
                "ingested": "t",
                "compiled": False,
            },
            {
                "file_id": "ingested:b.md",
                "file": "b.md",
                "title": "B",
                "source": "s2",
                "ingested": "t2",
                "compiled": False,
            },
        ],
    )
    read_m, _ = create_compiler_manifest_tools(ctx, [("studies", r1), ("ingested", r2)])
    out = json.loads(read_m.entrypoint())
    assert len(out) == 2
    ids = {row["file_id"] for row in out}
    assert ids == {"studies:a.md", "ingested:b.md"}


def test_update_manifest_compiled_labelled(tmp_path: Path) -> None:
    ctx = tmp_path / "context"
    ctx.mkdir()
    r1 = tmp_path / "docs"
    r1.mkdir()
    _write_manifest(
        ctx,
        [
            {
                "file_id": "studies:a.md",
                "file": "a.md",
                "title": "A",
                "source": "s",
                "ingested": "t",
                "compiled": False,
            }
        ],
    )
    _, upd = create_compiler_manifest_tools(ctx, [("studies", r1)])
    assert "Marked" in upd.entrypoint(filename="studies:a.md")
    m = json.loads((ctx / ".manifest.json").read_text(encoding="utf-8"))
    assert m[0]["compiled"] is True


def test_compiler_file_tools_read_labelled(tmp_path: Path) -> None:
    ctx = tmp_path / "context"
    ctx.mkdir()
    wiki = ctx / "wiki"
    wiki.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "x.md").write_text("# X\n", encoding="utf-8")
    ing = ctx / "raw"
    ing.mkdir(parents=True)
    tools = create_compiler_file_tools(ctx, [("studies", docs), ("ingested", ing)])
    rf = next(t for t in tools if t.name == "read_file")
    assert "X" in rf.entrypoint(file_name="raw/studies/x.md")


def test_build_compiler_tools_multi_root_includes_file_and_manifest_tools(tmp_path: Path) -> None:
    ctx = tmp_path / "ctx"
    ctx.mkdir()
    (ctx / "raw").mkdir()
    (ctx / "wiki").mkdir()
    d1 = tmp_path / "docs"
    d1.mkdir()
    tools = build_compiler_tools(
        MagicMock(), context_dir=ctx, raw_roots=[("studies", d1), ("ingested", ctx / "raw")]
    )
    names = [getattr(t, "name", None) for t in tools]
    assert "read_file" in names
    assert "read_manifest" in names
    assert "update_manifest_compiled" in names


def test_compiler_file_tools_legacy_path(tmp_path: Path) -> None:
    ctx = tmp_path / "context"
    ctx.mkdir()
    raw = ctx / "raw"
    raw.mkdir()
    wiki = ctx / "wiki"
    wiki.mkdir()
    (raw / "n.md").write_text("body", encoding="utf-8")
    tools = create_compiler_file_tools(ctx, [("raw", raw)])
    rf = next(t for t in tools if t.name == "read_file")
    assert rf.entrypoint(file_name="raw/n.md") == "body"
