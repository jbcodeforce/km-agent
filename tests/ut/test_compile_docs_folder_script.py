"""Unit tests for scripts/compile_docs_folder.py selection helpers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from kma.tools.ingest import _write_manifest, sha256_file

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "compile_docs_folder.py"


def _load_compile_script():
    spec = importlib.util.spec_from_file_location("compile_docs_folder", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    src = str(REPO_ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    spec.loader.exec_module(mod)
    return mod


def test_should_skip_unchanged_respects_hash_and_recompile(tmp_path: Path) -> None:
    mod = _load_compile_script()
    ctx = tmp_path / "context"
    ctx.mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    path = docs / "a.md"
    path.write_text(
        "---\ntitle: A\nsource: t\ningested: 2026-01-01\ncompiled: false\n---\n\n# A\n",
        encoding="utf-8",
    )
    digest = sha256_file(path)
    file_id = "studies:a.md"
    _write_manifest(
        ctx,
        [{"file_id": file_id, "file": "a.md", "compiled": True, "sha256": digest}],
    )

    assert mod._should_skip_unchanged(ctx, file_id, path, recompile=False) is True
    assert mod._should_skip_unchanged(ctx, file_id, path, recompile=True) is False

    path.write_text(path.read_text(encoding="utf-8") + "\nedit\n", encoding="utf-8")
    assert mod._should_skip_unchanged(ctx, file_id, path, recompile=False) is False


def test_prepare_file_for_compile_clears_compiled(tmp_path: Path) -> None:
    mod = _load_compile_script()
    ctx = tmp_path / "context"
    ctx.mkdir()
    _write_manifest(
        ctx,
        [{"file_id": "studies:a.md", "file": "a.md", "compiled": True, "sha256": "old"}],
    )
    mod._prepare_file_for_compile(ctx, "studies:a.md")
    from kma.tools.ingest import manifest_entry_compiled

    assert manifest_entry_compiled(ctx, "studies:a.md") is False


def test_record_sha256_for_compiled(tmp_path: Path) -> None:
    mod = _load_compile_script()
    ctx = tmp_path / "context"
    ctx.mkdir()
    docs = tmp_path / "docs"
    path = docs / "sub" / "a.md"
    path.parent.mkdir(parents=True)
    path.write_text("# body\n", encoding="utf-8")
    _write_manifest(
        ctx,
        [{"file_id": "studies:sub/a.md", "file": "sub/a.md", "compiled": True}],
    )

    mod._record_sha256_for_compiled(
        ctx, docs, "studies", ["studies:sub/a.md", "ingested:other.md"]
    )
    from kma.tools.ingest import _read_manifest

    entry = _read_manifest(ctx)[0]
    assert entry["sha256"] == sha256_file(path)
