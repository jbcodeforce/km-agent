"""Unit tests for scripts/index_wiki.py file discovery (no Postgres)."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.index_wiki import discover_wiki_markdown


def test_discover_wiki_markdown_skips_lint_report(tmp_path: Path) -> None:
    wiki = tmp_path / "wiki"
    (wiki / "concepts").mkdir(parents=True)
    (wiki / "index.md").write_text("# Index\n")
    (wiki / "concepts" / "flink.md").write_text("# Flink\n")
    (wiki / "lint-report.md").write_text("# Lint\n")

    found = discover_wiki_markdown(wiki)
    names = {p.name for p in found}
    assert "index.md" in names
    assert "flink.md" in names
    assert "lint-report.md" not in names


def test_discover_wiki_markdown_empty_when_missing(tmp_path: Path) -> None:
    assert discover_wiki_markdown(tmp_path / "wiki") == []
