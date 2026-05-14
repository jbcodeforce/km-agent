"""Smoke tests for scripts/add_raw_frontmatter.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "add_raw_frontmatter.py"
FIXTURE = REPO_ROOT / "tests" / "external_raw" / "flink-sql-1.md"


def _body_without_yaml_frontmatter(text: str) -> str:
    """If text starts with YAML frontmatter, return body only; else return text."""
    if not text.startswith("---\n"):
        return text
    close = text.find("\n---\n", 4)
    if close == -1:
        return text
    return text[close + len("\n---\n") :].lstrip("\n")


def test_script_exists() -> None:
    assert SCRIPT.is_file()


@pytest.mark.skipif(not FIXTURE.is_file(), reason="fixture markdown missing")
def test_add_frontmatter_then_refuse_second_run(tmp_path: Path) -> None:
    dst = tmp_path / "flink-sql-1.md"
    raw = FIXTURE.read_text(encoding="utf-8")
    dst.write_text(_body_without_yaml_frontmatter(raw), encoding="utf-8")
    env = {**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    r1 = subprocess.run(
        [sys.executable, str(SCRIPT), str(dst), "--source", "flink-studies/docs/coding/flink-sql-1.md", "--tags", "flink,sql"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r1.returncode == 0, r1.stderr + r1.stdout
    text = dst.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "compiled: false" in text
    assert "# Create Table SQL" in text
    manifest = tmp_path / ".manifest.json"
    assert manifest.is_file()
    assert "flink-sql-1.md" in manifest.read_text(encoding="utf-8")

    r2 = subprocess.run(
        [sys.executable, str(SCRIPT), str(dst)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert r2.returncode == 1
    assert "already has YAML frontmatter" in r2.stderr
